import discord
from discord.ext import commands, tasks
from discord import app_commands
import scrapetube
import asyncio
import aiohttp
import aiofiles
import logging
import orjson
from bs4 import BeautifulSoup
from pathlib import Path
import io
import time
from collections import deque

from cmds.music_bot.play4.utils import is_url

from core.functions import create_basic_embed, is_testing_guild, is_KeJC
from core.classes import Cog_Extension
from core.translator import locale_str, load_translated

logger = logging.getLogger(__name__)

path = './cmds/data.json/sub_yt_channels.json'
libpath = Path(path)
if not libpath.exists() or not libpath.stat().st_size > 0:
    libpath.write_text('{}')

deleting_ytb = {}
starts_deleting_ytb = {}

# deleting_ytb = {
#     'channelID': DeleteYTB()
# }

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

class SaveYouTubeData:
    channels = None
    update = False

    example = {
        'ChannelID': [
            'url1',
            'url2'
        ]
    }

    @classmethod
    async def init_data(cls):
        if not cls.channels:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                cls.channels = orjson.loads(await f.read())
    
    @classmethod
    def update_data(cls, data = None):
        if data:
            cls.channels = data
        cls.update = True

    @classmethod
    async def write_data(cls):
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(orjson.dumps(cls.channels, option=orjson.OPT_INDENT_2).decode())
        cls.update = False

class DeleteYTB:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.channelID = str(channel.id)

    def clear(self):
        channelID = int(self.channelID)
        if channelID in deleting_ytb:
            del deleting_ytb[channelID]
        if channelID in starts_deleting_ytb:
            del starts_deleting_ytb[channelID]
        self.channel = None
        self.channelID = None

    def delete(self, url: str) -> bool:
        data: dict = SaveYouTubeData.channels
        channelID = self.channelID

        urls: list = data.get(channelID, [])
        if not urls: return False

        clean_url = url.strip()

        if clean_url in data[channelID]:
            data[channelID].remove(clean_url)
            if not data[channelID]:
                del data[channelID]
            SaveYouTubeData.update_data(data)
            return True
        else:
            logger.error(f'{url} not in data[{channelID}]')
            return False

class SubYT(Cog_Extension):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.videos = {}
        self.processed = {}
        self.processed.setdefault(str, deque(maxlen=20)) # channelID, deque[videoIDs]

    async def cog_load(self):
        logger.info(f'已載入「{__name__}」')
        await SaveYouTubeData.init_data()
        # await self.bot.wait_until_ready()
        self.write_data_task.start()
        self.update_sub_yt.start()
        self.deleting_outdate.start()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot: return
        if msg.channel.id not in deleting_ytb: return
        content = msg.content
        if not content.startswith('[! '): return
        url = content[3:]
        if not is_url(url): return

        deleteYTB: DeleteYTB = deleting_ytb.get(msg.channel.id)

        ctx = await self.bot.get_context(msg)
        async with ctx.typing():
            success = deleteYTB.delete(url)
            if not success:
                return await ctx.send( ( await self.bot.tree.translator.get_translate('send_sub_yt_cannot_delete', ctx=ctx, lang_code=ctx.guild.preferred_locale.value) ).format(url=url))
            deleteYTB.clear() # OC

            '''i18n'''
            send_message = await self.bot.tree.translator.get_translate('send_sub_yt_successfully_delete', ctx=ctx, lang_code=ctx.guild.preferred_locale.value)
            ''''''

            await ctx.send(send_message.format(ytb = (await get_channel_name(url))))

    @commands.hybrid_command(name=locale_str('sub_yt'), description=locale_str('sub_yt'))
    @app_commands.describe(url=locale_str('sub_yt_url'))
    async def sub_yt(self, ctx: commands.Context, url: str):
        async with ctx.typing():
            url = url.strip()
            if not is_url(url): return await ctx.send(await ctx.interaction.translate('send_sub_yt_invalid_url'), ephemeral=True)
            if not (await get_channel_name(url)): return await ctx.send(await ctx.interaction.translate('send_sub_yt_cannot_found_ytb'), ephemeral=True)

            channelID = str(ctx.channel.id)

            data = SaveYouTubeData.channels
            urls: list = data.get(channelID, [])
            urls.append(url)

            data[channelID] = urls
            SaveYouTubeData.update_data(data)
            await ctx.send( (await ctx.interaction.translate('send_sub_yt_successfully_save') ).format( ytb = (await get_channel_name(url) )))

    @commands.hybrid_command(name=locale_str('sub_yt_cancel'), description=locale_str('sub_yt_cancel'))
    async def sub_yt_cancel(self, ctx: commands.Context):
        async with ctx.typing():
            try:
                channelID = str(ctx.channel.id)
                data = SaveYouTubeData.channels
                urls: list = data.get(channelID, [])
                if not urls: return await ctx.send(await ctx.interaction.translate('send_sub_yt_cancel_no_url'))

                '''i18n'''
                eb_translated = await ctx.interaction.translate('embed_sub_yt_cancel')
                embed_translated: dict = (load_translated(eb_translated))[0]

                title = embed_translated.get('title')
                author = embed_translated.get('author')

                field: dict = embed_translated.get('fields')[0]
                eb_field1_name = field.get('name')
                ''''''

                # list every urls' user.
                value = '\n'.join( [f'{await get_channel_name(url)}: {url}' for url in urls] )
                file = None
                if len(value) >= 2000:
                    mem_file = io.BytesIO(value.encode())
                    file = discord.File(mem_file, 'sub_yt_cancel.txt')

                eb = create_basic_embed(title=title, 功能=author, color=ctx.author.color)
                if not file:
                    eb.add_field(name=eb_field1_name, value=value, inline=False)

                deleting_ytb[ctx.channel.id] = DeleteYTB(ctx.channel)
                starts_deleting_ytb[ctx.channel.id] = time.time()

                await ctx.send(embed=eb, file=file)
            except:
                logger.error('Error accured at sub_yt_cancel: ', exc_info=True)

    @commands.hybrid_command(name=locale_str('sub_yt_list'), description=locale_str('sub_yt_list'))
    async def sub_yt_list(self, ctx: commands.Context):
        async with ctx.typing():
            '''i18n'''
            eb = await ctx.interaction.translate('embed_sub_yt_list')
            eb = load_translated(eb)[0]
            author: str = eb.get('author')
            ''''''

            result = []
            for url in SaveYouTubeData.channels.get(str(ctx.channel.id), []):
                try: name = await get_channel_name(url)
                except: ...
                result.append(f'[{name}]({url})')

            descrip = ', '.join( result or ['None'] )

            eb = create_basic_embed(description=descrip, color=ctx.author.color, 功能=author.format(channelName=ctx.channel.name))
            await ctx.send(embed=eb)

    @commands.command(name='sub_yt_data')
    @is_testing_guild()
    async def send_sub_yt_data(self, ctx: commands.Context):
        if not is_KeJC(ctx.author.id): return
        str_bytes = orjson.dumps(SaveYouTubeData.channels, option=orjson.OPT_INDENT_2)
        mem_file = io.BytesIO(str_bytes)
        file = discord.File(mem_file, 'SaveYouTubeData_channels.json')

        await ctx.send(file=file)
        await ctx.send(str(deleting_ytb))

    @tasks.loop(minutes=1)
    async def write_data_task(self):
        if not SaveYouTubeData.update: return
        await SaveYouTubeData.write_data()

    @tasks.loop(minutes=1)
    async def deleting_outdate(self):
        '''刪除已經超過 10 分鐘的 取消訂閱 活動'''
        if not deleting_ytb and not starts_deleting_ytb: return

        now = time.time()
        for cnlID in starts_deleting_ytb:
            if cnlID not in deleting_ytb: # 避免兩者不一致的情況，此時cnlID in deleting_ytb
                del starts_deleting_ytb[cnlID]
                return
            
            start_time = starts_deleting_ytb[cnlID]
            if (now - start_time) > 10*60: # 10分鐘
                deleting_ytb[cnlID].clear()

    @tasks.loop(seconds=30)
    async def update_sub_yt(self):
        data: dict = SaveYouTubeData.channels
        if not data: return

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
        urls = set()
        urls = {url for item in data.values() for url in item}

        # 2. 遞迴取得每個 url 當前的 video ids
        current_video_ids = {}
        '''example
        {
            url: [video_ids...]
        }
        '''
        for url in urls:
            try:
                videos = await asyncio.to_thread(scrapetube.get_channel, channel_url=url, limit=5)
                if not videos: continue
                video_ids = [video["videoId"] for video in videos]
                current_video_ids[url] = video_ids
            except:
                continue
            finally:
                await asyncio.sleep(1)

        # 第一次不用執行，避免重複傳送 (因為會取得 5 個 videos)
        if self.update_sub_yt.current_loop == 0 or not self.videos:
            self.videos = current_video_ids
            return

        for cnlID in data:
            channel = self.bot.get_channel(int(cnlID)) or await self.bot.fetch_channel(int(cnlID))
            if not channel: continue

            guild = self.bot.get_guild(channel.guild.id) or await self.bot.fetch_guild(channel.guild.id)
            preferred_lang = guild.preferred_locale.value if guild else 'zh-TW'

            for url in data.get(cnlID, []):
                if ( self.videos.get(url, None) ) is None: continue # 避免新增頻道後 連續舊的影片   
                
                try:
                    old_video_ids = set(self.videos[url])
                    new_video_ids = set(current_video_ids[url])
                except:
                    continue
                
                if old_video_ids != new_video_ids:
                    print(old_video_ids, new_video_ids, sep='\n')
                    print(new_video_ids - old_video_ids)

                for video_id in new_video_ids - old_video_ids:
                    if video_id in self.processed.get(cnlID, []): continue

                    sent_url = f"https://youtu.be/{video_id}"
                    sent_message = await self.bot.tree.translator.get_translate('send_sub_yt_new_video', lang_code=preferred_lang)
                    await channel.send(sent_message.format(url=sent_url, name=await get_channel_name(url)))          

                    self.processed[cnlID].append(video_id)

        self.videos = current_video_ids


async def setup(bot):
    await bot.add_cog(SubYT(bot))

        