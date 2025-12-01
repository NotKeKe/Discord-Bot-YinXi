from discord.ext import commands, tasks
from discord import app_commands, Interaction
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
import time
from typing import Optional, List, Tuple
from datetime import datetime
import yt_dlp
from concurrent.futures import ProcessPoolExecutor
# import scrapetube

from cmds.music_bot.play4.utils import is_url, get_video_id

from core.functions import create_basic_embed, redis_client
from core.classes import Cog_Extension
from core.translator import locale_str, load_translated
from core.mongodb import MongoDB_DB
from core.scrapetube import scrapetube

logger = logging.getLogger(__name__)

db = MongoDB_DB.sub_yt

# YouTube 先前更新了 shorts 的 JSON tree，但 pypi 上的 scrapetube 一直沒有更新
# https://github.com/dermasmid/scrapetube/issues/65
# scrapetube.scrapetube.type_property_map['shorts'] = 'reelWatchEndpoint'

async def get_channel_name(url: str) -> str:
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url) as resp:
            if resp.status != 200: return None
            text = await resp.text()

    soup = BeautifulSoup(text, 'html.parser')
    meta_tag = soup.find("meta", itemprop="name")
    if meta_tag:
        channel_name = meta_tag.get('content', None)
        return channel_name
    
    return None

# def fetch_video_ids(urls: dict):
#     current_video_ids = {}
#     for url in urls:
#         try:
#             videos = scrapetube.get_channel(channel_url=url, limit=5)
#             shorts = scrapetube.get_channel(channel_url=url, limit=8, content_type='shorts')
#             # streams = scrapetube.get_channel(channel_url=url, limit=5, content_type='streams')
#             if not videos: continue
#             video_ids = [video["videoId"] for video in videos] + [short["videoId"] for short in shorts]
#             current_video_ids[url] = video_ids
#         except:
#             continue
#         finally:
#             time.sleep(1)
#     return current_video_ids

async def fetch_video_ids(urls: dict):
    current_video_ids = {}
    for url in urls:
        try:
            videos = scrapetube.get_channel(channel_url=url, limit=5)
            shorts = scrapetube.get_channel(channel_url=url, limit=8, content_type='shorts')
            # streams = scrapetube.get_channel(channel_url=url, limit=5, content_type='streams')
            if not videos: continue
            video_ids = [video["videoId"] async for video in videos] + [short["videoId"] async for short in shorts]
            current_video_ids[url] = video_ids
        except:
            continue
        finally:
            await asyncio.sleep(1)
    return current_video_ids

def _get_upload_date(url: str):
    ydl_opts = {
        'quiet': True,             # 不輸出進度
        'skip_download': True,     # 跳過下載
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        
        # 'YYYYMMDD'
        upload_date_str = info_dict.get('upload_date')
        live_status = info_dict.get("live_status")
        if live_status != 'not_live': return # 只回傳正常影片

        
        if not upload_date_str:
            return

        upload_datetime = datetime.strptime(upload_date_str, '%Y%m%d')
        
        return upload_datetime

async def get_upload_date(url: str) -> datetime | None:
    _BASE_REDIS_KEY = 'sub_yt_upload_time:{}'
    video_id = get_video_id(url)
    if not video_id: return

    upload_time = await redis_client.get(_BASE_REDIS_KEY.format(video_id))
    if upload_time:
        return datetime.fromisoformat(upload_time)

    # loop = asyncio.get_running_loop()
    # async with Semaphore_multi_processing_pool:
    #     with ProcessPoolExecutor() as executor:
    #         try:
    #             result = await loop.run_in_executor(executor, _get_upload_date, url)
    #         except:
    #             import traceback
    #             traceback.print_exc() # temp
    #             return

    try:
        result = await asyncio.to_thread(_get_upload_date, url)
    except:
        import traceback
        traceback.print_exc()
        return

    if not result: return
    await redis_client.set(_BASE_REDIS_KEY.format(video_id), result.isoformat())
    return result
                

async def sub_urls_autocomplete(inter: Interaction, current: str) -> List[app_commands.Choice[str]]:
    collection = db[str(inter.channel.id)]
    data: List[Tuple[str, str]] = [(d.get('sub_url'), d.get('channelName')) async for d in collection.find()]

    if current:
        data = [item for item in data if current.lower().strip() in item[1].lower().strip() or current.lower().strip() in item[0].lower().strip()]
    
    return [app_commands.Choice(name=d[1], value=d[0]) for d in data]

async def add_to_all(url: str):
    try:
        collection = db['ALL']
        await collection.update_one({'urls': {'$exists': True}}, {'$addToSet': {'urls': url}}, upsert=True)
    except:
        logger.error(f'Error while add {url} to sub_yt ALL: ', exc_info=True)

class SubYT(Cog_Extension):
    async def cog_load(self):
        logger.info(f'已載入「{__name__}」')
        self.update_sub_yt.start()

    @commands.hybrid_command(name=locale_str('sub_yt'), description=locale_str('sub_yt'))
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(url=locale_str('sub_yt_url'))
    async def sub_yt(self, ctx: commands.Context, url: str):
        async with ctx.typing():
            url = url.strip()
            if not is_url(url): return await ctx.send(await ctx.interaction.translate('send_sub_yt_invalid_url'), ephemeral=True)
            channel_name = await get_channel_name(url)
            if not (channel_name): return await ctx.send(await ctx.interaction.translate('send_sub_yt_cannot_found_ytb'), ephemeral=True)

            collection = db[str(ctx.channel.id)]
            exist = await collection.find_one({'sub_url': url})
            if exist: return await ctx.send('Already exist')

            await collection.insert_one({'sub_url': url, 'channelName': channel_name, 'createAt': datetime.now().timestamp()})

            await ctx.send( (await ctx.interaction.translate('send_sub_yt_successfully_save') ).format( ytb = (await get_channel_name(url) )))
            asyncio.create_task(add_to_all(url))

        # initial_videos = await asyncio.to_thread(fetch_video_ids, [url])
        initial_videos = await fetch_video_ids([url])
        initial_video_ids = initial_videos.get(url, [])
        try:
            if initial_video_ids:
                channelID = str(ctx.channel.id)
                redis_key = f"sub_yt_processed_videos:{channelID}"
                current_timestamp = int(time.time())
                
                mapping = {video_id: current_timestamp for video_id in initial_video_ids}
                await redis_client.zadd(redis_key, mapping)
        except:
            logger.error('Error accured at sub_yt: ', exc_info=True)
            await ctx.send('Warning: Unable to initialize video_ids for this channel, etc. may send 10 messages at once (this exception will only occur this time)')

    @commands.hybrid_command(name=locale_str('sub_yt_cancel'), description=locale_str('sub_yt_cancel'))
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.autocomplete(ytb=sub_urls_autocomplete)
    async def sub_yt_cancel(self, ctx: commands.Context, ytb: str):
        async with ctx.typing():
            try:
                # ytb = sub_url
                collection = db[str(ctx.channel.id)]
                d = await collection.find_one_and_delete({'sub_url': ytb})

                await ctx.send((await ctx.interaction.translate('send_sub_yt_cancel_successfully')).format(name=d.get('channelName'), url=d.get('sub_url')))
            except:
                logger.error('Error accured at sub_yt_cancel: ', exc_info=True)
                await ctx.send('Cannot cancel the YouTuber, please /report this issue')

    @commands.hybrid_command(name=locale_str('sub_yt_list'), description=locale_str('sub_yt_list'))
    async def sub_yt_list(self, ctx: commands.Context):
        async with ctx.typing():
            '''i18n'''
            eb = await ctx.interaction.translate('embed_sub_yt_list')
            eb = load_translated(eb)[0]
            author: str = eb.get('author')
            ''''''

            result = [f"[{item.get('channelName', 'None')}]({item.get('sub_url', 'None')})" async for item in db[str(ctx.channel.id)].find()]

            descrip = ', '.join( result or ['None'] )

            eb = create_basic_embed(description=descrip, color=ctx.author.color, 功能=author.format(channelName=ctx.channel.name))
            await ctx.send(embed=eb)

    @tasks.loop(minutes=10)
    async def update_sub_yt(self):
        '''
        1. 先取得全部 url's video ids
        {
            url: [video_ids...]
        }
            1. 取得 data 內全部 url，並存進 set 當中
            2. 遞迴取得每個 url 當前的 video ids

        比對現有 self.videos
        {
            url: [old_video_ids...]
        }

        每次將兩者對比
        有區別就發送訊息
        '''

        # 1. 取得 data 內全部 url
        all_urls = await db['ALL'].find_one({'urls': {'$exists': True}})
        if not all_urls: return
        urls = set(all_urls.get('urls'))

        # 2. 遞迴取得每個 url 當前的 video ids
        '''example
        {
            url: [video_ids...]
        }
        '''
        # current_video_ids: dict = await asyncio.to_thread(fetch_video_ids, urls)
        current_video_ids: dict = await fetch_video_ids(urls)
        all_dc_channel_id = [item for item in (await db.list_collection_names()) if item != 'ALL']

        for cnlID in all_dc_channel_id:
            channel = self.bot.get_channel(int(cnlID)) or await self.bot.fetch_channel(int(cnlID))
            if not channel: continue

            # get prefer lang
            guild = self.bot.get_guild(channel.guild.id) or await self.bot.fetch_guild(channel.guild.id)
            preferred_lang = guild.preferred_locale.value if guild else 'zh-TW'
            
            # redis
            redis_key = f"sub_yt_processed_videos:{str(cnlID)}"
            # 清理過期 video ids
            ts = int(time.time()) - (60*60*24*30)
            await redis_client.zremrangebyscore(redis_key, 0, ts)

            # get sub_urls
            sub_urls = [item.get('sub_url') async for item in db[str(cnlID)].find()]

            for url in sub_urls:
                latest_video_ids = current_video_ids.get(url, [])
                if not latest_video_ids: continue

                # 判斷元素是否在 redis 當中的 redis_key 內，如果在的話(results[i] is not None)就代表已經被處理過
                pipe = redis_client.pipeline()
                for video_id in latest_video_ids:
                    pipe.zscore(redis_key, video_id)
                result: list[Optional[float]] = await pipe.execute()

                new_video_ids = [latest_video_ids[i] for i, score in enumerate(result) if score is None]
                current_ts = int(time.time())
                if not new_video_ids: continue
                if len(new_video_ids) >= 5: # 可能因為第一次初始化失敗而造成一次傳送5個 (畢竟應該沒有人會30秒內一次傳送5個影片)
                    for video_id in new_video_ids:
                        await redis_client.zadd(redis_key, {video_id: current_ts})
                    return
                
                for video_id in reversed(new_video_ids):
                    sent_url = f"https://youtu.be/{video_id}"

                    publish_time = await get_upload_date(sent_url)
                    if not publish_time: continue
                    await redis_client.zadd(redis_key, {video_id: current_ts})
                    if (datetime.now() - publish_time).total_seconds() > 60*60*24*2: # 大於2天
                        continue

                    sent_message: str = await self.bot.tree.translator.get_translate('send_sub_yt_new_video', lang_code=preferred_lang)
                    await channel.send(sent_message.format(url=sent_url, name=await get_channel_name(url)))          



async def setup(bot):
    await bot.add_cog(SubYT(bot))

        