import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.app_commands import Choice
import typing
import traceback
from zhipuai.core._errors import APIRequestFailedError, APITimeoutError, APIStatusError

from cmds.AIs.zhipu import response, image_generate, video_generate, summarize, gener_title, video_read, image_read, search, code_response
from cmds.AIs.info import *
from core.classes import Cog_Extension
from core.functions import create_basic_embed, thread_pool, read_json, write_json, KeJCID

HISTORY_DATA_PATH = './cmds/data.json/chat_history.json'
HISTORY_DATA_FORCHANNEL_PATH = './cmds/data.json/chat_history_forchannel.json'

example_chat_history = {
    'ctx.author.id': {
        'name1': [
            {'role': 'user', 
             'content': 'hi'
            }
        ],
        'name2': [
            ...
        ]
    },
    'ctx.author.id2': ...
}

example_chat_channelHistory = {
    'ctx.channel.id': [
        {
            'role': 'user',
            'content': 'hi',
            'user': 123456 # ctx.author.id
        },

    ]
}

class ZhiPuAI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.appendHistoryForChannel = HistoryData.appendHistoryForChannel
        self.appendHistory = HistoryData.appendHistory
        self.initdata = HistoryData.initdata
        self.writedata = HistoryData.writeUser
        self.writeChannelHistoryData = HistoryData.writeChannel

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.initdata()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if error not in (APIRequestFailedError, APIStatusError, APITimeoutError): return
        await ctx.send(f'無法請求API, reason: {error}')

    @commands.hybrid_command(name='chat', description='使用AI跟你聊天')
    @app_commands.autocomplete(歷史紀錄=chat_autocomplete)
    async def chat(self, ctx: commands.Context, * , 輸入文字: str, 歷史紀錄:str = None, 搜尋功能:bool = False):
        try:
            async with ctx.typing():
                self.initdata()
                history = get_history(ctx, 歷史紀錄)
                if not 搜尋功能:
                    result = await thread_pool(response, 輸入文字, history)
                    embed = create_result_embed(ctx, result, 'glm-4-flash')
                else:
                    result = await thread_pool(search, 輸入文字)
                    embed = create_result_embed(ctx, result, 'glm-4-alltools')

                await ctx.send(embed=embed)
                self.appendHistory(ctx.author.id, 輸入文字, result, 歷史紀錄)
        except Exception as e:
            await ctx.send(f'生成失敗, reason: {e}', ephemeral=True)
            traceback.print_exc()

    @commands.hybrid_command(name='code助手')
    @app_commands.autocomplete(歷史紀錄=chat_autocomplete)
    async def code_helper(self, ctx: commands.Context, * , 輸入文字: str, 歷史紀錄:str = None):
        try:
            async with ctx.typing():
                self.initdata()
                history = get_history(ctx, 歷史紀錄)

                result = await thread_pool(code_response, 輸入文字, history)
                embed = create_result_embed(ctx, result, 'glm-4-alltools')
                await ctx.send(embed=embed)
                self.appendHistory(ctx.author.id, 輸入文字, result, 歷史紀錄)
        except Exception as e:
            await ctx.send(f'生成失敗, reason: {e}', ephemeral=True)
            traceback.print_exc()

    @commands.hybrid_command(name='圖片判讀', description='使用AI判別你的圖片')
    @app_commands.describe(圖片連結 = '這邊提供一個小技巧，把圖片傳到discord之後就能直接複製圖片連結')
    async def image_read(self, ctx: commands.Context, * , 需求: str, 圖片連結: str):
        try:
            async with ctx.typing():
                result = await thread_pool(image_read, 需求, 圖片連結)
                embed = create_basic_embed(title='AI圖片判讀', color=ctx.author.color)
                embed.add_field(name=' ', value=result)
                embed.set_footer(text='Powered by glm-4v-flash')
                await ctx.send(embed=embed)
        except:
            ...

    @commands.hybrid_command(name='影片判讀', description='使用AI判別你的影片')
    @app_commands.describe(影片連結 = '這邊提供一個小技巧，把圖片傳到discord之後就能直接複製影片連結')
    async def video_read(self, ctx: commands.Context, * , 需求: str, 影片連結: str):
        try:
            async with ctx.typing():
                result = await thread_pool(video_read, 需求, 影片連結)
                embed = create_basic_embed(title='AI影片判讀', color=ctx.author.color)
                embed.add_field(name=' ', value=result)
                embed.set_footer(text='Powered by glm-4v-flash')
                await ctx.send(embed=embed)
        except:
            traceback.print_exc()

    @commands.hybrid_command(name='圖片生成', description='使用AI生成圖片')
    async def image(self, ctx: commands.Context, * , 輸入文字: str):
        try:
            async with ctx.typing():
                url, time = await thread_pool(image_generate, 輸入文字)
                embed = create_basic_embed(title='AI圖片生成', color=ctx.author.color)
                embed.set_image(url=url)
                embed.add_field(name='花費時間(秒)', value=int(time))
                embed.set_footer(text='Powered by cogview-3-flash')
                await ctx.send(embed=embed)
        except:
            await ctx.send('生成失敗', ephemeral=True)

    @commands.hybrid_command(name='影片生成', description='使用AI生成影片')
    @app_commands.choices(
        size = [
            Choice(name='720x480', value='720x480'),
            Choice(name='1024x1024', value='1024x1024'),
            Choice(name='1280x960', value='1280x960'),
            Choice(name='960x1280', value='960x1280'),
            Choice(name='1920x1080', value='1920x1080'),
            Choice(name='1080x1920', value='1080x1920'),
            Choice(name='2048x1080', value='2048x1080'),
            Choice(name='3840x2160', value='3840x2160')
        ],
        fps = [
            Choice(name=30, value=30),
            Choice(name=60, value=60)
        ],
        是否要聲音 = [
            Choice(name='要', value='要'),
            Choice(name='不要', value='不要')
        ]
    )
    @app_commands.describe(fps='預設為60，可選30 or 60', 影片時長='單位為秒, 預設為5, 最高為10')
    async def video(self, ctx: commands.Context, * , 輸入文字: str, 圖片連結: str = None, size: str = None, fps: int = 60, 是否要聲音 = '要', 影片時長:int = 5):
        try:
            async with ctx.typing():
                if 影片時長 > 10:
                    await ctx.send('最高只能幫你生成10秒的圖片 要怪就怪cogvideox-flash...', ephemeral=True) 
                    影片時長 = 10

                if fps not in (30, 60):
                    fps = 60

                if 是否要聲音 == '要':
                    是否要聲音 = True
                else:
                    是否要聲音 = False
                url = await thread_pool(video_generate, 輸入文字, 圖片連結, size, fps, 是否要聲音, 影片時長)
                string = f'影片生成 (Power by cogvideox-flash) \n {url}'
                await ctx.send(string)
        except Exception:
            await ctx.send(f'生成失敗, reason: {Exception}', ephemeral=True)
            traceback.print_exc()


    @commands.command()
    async def print_chatdata(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        await ctx.send(HistoryData.user)


async def setup(bot):
    await bot.add_cog(ZhiPuAI(bot))