
import discord
from discord.ext import commands, tasks
from discord import app_commands
import scrapetube
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from cmds.music_bot.play4.utils import is_url
from core.functions import read_json, write_json

path = './cmds/data.json/youtube_update_channels.json'
    
async def 取得頻道名稱(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200: return 1
            text = await resp.text()
    
    soup = BeautifulSoup(text, 'html.parser') 
    meta_tag = soup.find("meta", itemprop="name")
    if meta_tag:
        channel_name = meta_tag.get('content', 3)
        return channel_name
    else: 
        return 2
    
class Save_YoutubeNT:
    channels = None
    update = False

    example = {
        "1327962986257842216": {
            "設定人": [
                703877871256731678
            ],
            "artist": [
                "https://youtube.com/@iamkh",
                "https://youtube.com/@kejc13",
                "https://youtube.com/@kejc130",
                "https://youtube.com/@codm?si=AbSJz974tbr9Jp6A",
                "https://youtube.com/@wuhu1",
                "https://youtube.com/@tabbypac"
            ],
            "Error_times": 0
        }
    }

    @classmethod
    def initdata(cls):
        if not cls.channels:
            cls.channels = read_json(path)

    @classmethod
    def savedata(cls, data=None):
        if data:
            cls.channels = data
        cls.update = True
    
    @classmethod
    def writedata(cls):
        write_json(cls.channels, path)
        cls.update = False

class YoutubeNotification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.videos = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.check.start()
        self.write_data_task.start()

    @tasks.loop(seconds=120)
    async def check(self):
        try:
            Save_YoutubeNT.initdata()
            j = Save_YoutubeNT.channels
            if not j: return

            for channel_id in j:
                discord_channel = await self.bot.fetch_channel(int(channel_id))
                yt_channels = j[channel_id]['artist']

                for yt_channel in yt_channels:
                    # print(yt_channel)
                    try:
                        videos = await asyncio.to_thread(scrapetube.get_channel, channel_url=yt_channel, limit=5)
                        if not videos: continue
                        video_ids = [video["videoId"] for video in videos]
                    except:
                        continue

                    if self.check.current_loop == 0:
                        self.videos[yt_channel] = video_ids
                        continue

                    for video_id in video_ids:
                        if video_id not in self.videos[yt_channel]:
                            # print('not')
                            url = f"https://youtu.be/{video_id}"
                            yt_name = await 取得頻道名稱(yt_channel)
                            await discord_channel.send(f"**{yt_name}** 發送了影片\n\n{url}")

                    self.videos[yt_channel] = video_ids
        except Exception as e:
            print(e)

    @commands.hybrid_command(name='設定yt通知', description='Set YT notification')
    @commands.has_permissions(administrator=True)
    @app_commands.describe(youtuber = '貼上你要通知的youtuber的連結')
    async def ytnotice(self, ctx: commands.Context, youtuber: str = None):
        '''
        [設定yt通知 youtuber(貼上你要的youtuber的連結)
        '''
        Save_YoutubeNT.initdata()
        j = Save_YoutubeNT.channels
        channel_id = str(ctx.channel.id)

        # 使用者要新增
        if youtuber is not None:
            if not is_url(youtuber): await ctx.send('請使用正常的YouTube連結', ephemeral=True); return
            if youtuber in j[channel_id]['artist']: await ctx.send('此頻道已經被設定過'); return
            channel_name = await 取得頻道名稱(youtuber)

            if channel_name == 1: 
                await ctx.send('請輸入有效的連結', ephemeral=True)
                return
            elif channel_name == 2:
                e = "無法找到頻道名稱的 meta 標籤"
                await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=e, user_send=False, ephemeral=True)
                return
            elif channel_name == 3:
                e = '未知的頻道名稱'
                await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=e, user_send=False, ephemeral=True)
                return

            if channel_id not in j: 
                j[channel_id] = {
                    '設定人': [ctx.author.id],
                    'artist': [youtuber],
                    "Error_times": 0
                }
            else: # 有人設定過
                if ctx.author.id not in j[channel_id]['設定人']: # 如果是新的人設定
                    j[channel_id]['設定人'].append(ctx.author.id)
                
                j[channel_id]['artist'].append(youtuber)
                
            Save_YoutubeNT.savedata(j)
            await ctx.send(f'已開啟對 「{channel_name}」 的通知')

        else:
            if not j[channel_id]['artist']: await ctx.send('你尚未設置任何的YouTuber通知', ephemeral=True); return

            async def select_callback(interaction: discord.Interaction):
                youtuber = interaction.data['values'][0]
                j[str(ctx.channel.id)]['artist'].remove(youtuber)
                if not j[str(ctx.channel.id)]['artist']: del j[str(ctx.channel.id)]
                Save_YoutubeNT.savedata(j)
                await interaction.response.send_message(content=f'已取消對「{await 取得頻道名稱(youtuber)}」的通知')
                view.stop()

            select = discord.ui.Select(placeholder='選擇一個你要刪除通知的YouTuber', 
                    options=[discord.SelectOption(label=url, description=(await 取得頻道名稱(url))) for url in j[str(ctx.channel.id)]['artist']],
                    min_values=1,
                    max_values=1
                )
            select.callback = select_callback

            view = discord.ui.View(timeout=60)
            view.add_item(select)

            await ctx.send(content='選擇一你要取消的YouTuber', view=view)

    @tasks.loop(seconds=30)
    async def write_data_task(self):
        if not Save_YoutubeNT.update: return
        Save_YoutubeNT.writedata()

async def setup(bot):
    await bot.add_cog(YoutubeNotification(bot))