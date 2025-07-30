import discord
from discord.ext import commands, tasks
from discord import app_commands
import scrapetube
import asyncio
import aiohttp
import aiofiles
import logging
import orjson
from typing import Union
from bs4 import BeautifulSoup
from pathlib import Path

from cmds.music_bot.play4.utils import is_url

from core.functions import create_basic_embed
from core.classes import Cog_Extension
from core.translator import locale_str

logger = logging.getLogger(__name__)

path = './cmds/data.json/sub_yt_channels.json'
Path(path).write_text('{}')

deleting_ytb = {}

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
        self.channel = None
        self.channelID = None
        del deleting_ytb[int(self.channelID)]

    def delete(self, url: str) -> Union[bool, None]:
        data = SaveYouTubeData.channels
        channelID = self.channelID

        urls: list = data.get(channelID, [])
        if not urls: return False

        data[channelID].remove(url)
        SaveYouTubeData.update_data(data)

class SubYT(Cog_Extension):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.videos = {}

    async def cog_load(self):
        logger.info(f'已載入「{__name__}」')
        await SaveYouTubeData.init_data()
        # await self.bot.wait_until_ready()
        self.write_data_task.start()
        self.update_sub_yt.start()
        
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component: return
        if not interaction.message: return

        if interaction.message.author.id not in deleting_ytb: return
        content = interaction.message.content
        if not content.startswith('[! '): return
        url = content[3:-1]
        if not is_url(url): return
                
        deleteYTB: DeleteYTB = deleting_ytb.get(interaction.channel.id)
        if not deleteYTB: return

        deleteYTB.delete(url)
        deleteYTB.clear() # OC

        '''i18n'''
        send_message = await interaction.translate('send_sub_yt_successfully_delete')
        # 已刪除 {ytb}
        ''''''
        
        await interaction.response.send_message(send_message.format(ytb = (await get_channel_name(url))), ephemeral=True)
        await asyncio.sleep(10)
        await interaction.message.delete()

    @commands.hybrid_command(name=locale_str('sub_yt'), description=locale_str('sub_yt'))
    @app_commands.describe(url=locale_str('sub_yt_url'))
    async def sub_yt(self, ctx: commands.Context, url: str):
        async with ctx.typing():
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
            channelID = str(ctx.channel.id)
            data = SaveYouTubeData.channels
            urls: list = data.get(channelID, [])
            if not urls: return await ctx.send(await ctx.interaction.translate('send_sub_yt_cancel_url_not_found'))

            '''i18n'''
            title = '使用 `[! URL_HERE` 來取消訂閱該 YouTuber'
            author = 'hello'
            ''''''

            # list every urls' user.
            eb = create_basic_embed(title=title, 功能=author, color=ctx.author.color)
            eb.add_field(name=', '.join( [f'{await get_channel_name(url)}: {url}' for url in urls] ))
            deleting_ytb
            await ctx.send(embed=eb)

    @tasks.loop(minutes=1)
    async def write_data_task(self):
        if not SaveYouTubeData.update: return
        await SaveYouTubeData.write_data()

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

        # 第一次不用執行，避免重複傳送 (因為會取得 5 個 videos)
        if self.update_sub_yt.current_loop == 0:
            self.videos = current_video_ids
            return

        for cnlID in data:
            channel = self.bot.get_channel(int(cnlID)) or await self.bot.fetch_channel(int(cnlID))
            if not channel: continue

            guild = self.bot.get_guild(channel.guild.id) or await self.bot.fetch_guild(channel.guild.id)
            preferred_lang = guild.preferred_locale.value if guild else 'zh-TW'

            for url in data.get(cnlID, []):
                if ( self.videos.get(url, None) ) is None: continue # 避免新增頻道後 連續舊的影片   

                old_video_ids = set(self.videos.get(url, []))
                new_video_ids = set(current_video_ids.get(url, []))

                for video_id in new_video_ids - old_video_ids:
                    sent_url = f"https://youtu.be/{video_id}"
                    sent_message = await self.bot.tree.translator.get_translate('send_sub_yt_new_video', lang_code=preferred_lang)
                    await channel.send(sent_message.format(url=sent_url, name=await get_channel_name(url)))          

        self.videos = current_video_ids


async def setup(bot):
    await bot.add_cog(SubYT(bot))

        