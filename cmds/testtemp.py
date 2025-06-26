import discord
from discord.ext import commands
from discord import app_commands, SelectOption
from discord.app_commands import Choice
from discord.ui import Select, View
from core.classes import Cog_Extension
import json
import os
import time
from datetime import datetime
import random
import typing
from typing import Optional
import asyncio
import traceback
from dotenv import load_dotenv
import aiohttp

from core.functions import read_json, thread_pool, embed_link, KeJCID, create_basic_embed

# get env
load_dotenv()

with open("setting.json", 'r', encoding='utf8') as jfile:
    jdata = json.load(jfile)

async def on_select(interaction: discord.Interaction):
    result = interaction.data["values"][0]
    await interaction.response.send_message(result)

class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Green', style=discord.ButtonStyle.green, custom_id='persistent_view:green')
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is green.', ephemeral=True)

    @discord.ui.button(label='Red', style=discord.ButtonStyle.red, custom_id='persistent_view:red')
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is red.', ephemeral=True)

    @discord.ui.button(label='Grey', style=discord.ButtonStyle.grey, custom_id='persistent_view:grey')
    async def grey(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is grey.', ephemeral=True)

def promision_check(interaction: discord.Interaction,):
    return str(interaction.user.id) == KeJCID

class TestTemp(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.message_test_data: discord.message.Message

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

        
    @commands.command()
    async def testtemp(self, ctx):
        await ctx.send("hello, this is testtemp", ephemeral=True)

    @commands.command()
    async def embedtest(self, ctx):
        try:
            embed=discord.Embed(title="title", description="description", color=0xff0000, timestamp=datetime.now())
            embed.set_author(name="name", url="https://discord.gg/MhtxWJu", icon_url=embed_link)
            embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/584213384409382953/4438fe5d2f91ddd873407e759ff23116.png?size=512")
            embed.add_field(name="field", value="- value", inline=False)
            embed.set_footer(text="footer")
            await ctx.send(embed=embed)
        except Exception as e:
            print("Error: ", e)

    @commands.command()
    async def get_cog_name(self, ctx):
        lst = [filename for filename in self.bot.cogs]
        await ctx.send(lst)

    @commands.command()
    async def get_command_name(self, ctx):
        try:
            lst = [command.name for command in self.bot.get_cog('TestTemp').get_commands()]
            await ctx.send(lst)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.command()
    async def errortest(self, ctx):
        try:
            raise Exception("testing")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=True)
            
    @commands.command()
    async def systemchannel(self, ctx):
        if str(ctx.author.id) != KeJCID: return

        channel = ctx.guild.system_channel
        if channel is None:
            await ctx.send('這個伺服器沒有system channel')
        else:
            await ctx.send('have')
            if not channel.permissions_for(ctx.guild.me).send_messages: await ctx.send('預設頻道沒有權限讓我發送訊息'); return
            await channel.send("hi")

    @commands.command()
    async def select(self, ctx: commands.Context):
        # 創建選項
        select = discord.ui.Select(
            placeholder="選擇一個選項...",
            options=[
                discord.SelectOption(label="選項1", description="這是選項1"),
                discord.SelectOption(label="選項2", description="這是選項2"),
                discord.SelectOption(label="選項3", description="這是選項3"),
            ]
        )

        # 將 select 添加到 view
        view = discord.ui.View()
        view.add_item(select)

        # select call back
        select.callback = on_select

        # 发送带有选项的消息
        await ctx.send("請選擇一個選項：", view=view)

        # 定义检查函数
        def check(interaction):
            return interaction.user == ctx.author and interaction.data['component_type'] == discord.ComponentType.select

        # 等待用戶做出選擇
        interaction = await self.bot.wait_for("interaction", check=check)
        
        # 取得選擇的值
        selected_value = interaction.data['values'][0]
        
        await ctx.send(f"你選擇了: {selected_value}")
        # 在這裡繼續執行其他邏輯
        await ctx.send("繼續執行你的邏輯...")

    @commands.command()
    async def message_test2(self, ctx):
        try:
            await self.message_test_data.edit(content='edited')
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.command()
    async def fromidtoname(self, ctx, id):
        '''
        從user id 獲得名字
        '''
        user = await self.bot.fetch_user(id)
        await ctx.send(content=user.name, ephemeral=True)

    @commands.command()
    async def getguildid(self, ctx: commands.Context):
        await ctx.send(ctx.guild.id)

    @commands.command()
    async def buttontest(self, ctx):
        view = PersistentView()
        await ctx.send("請選擇一個按鈕", view=view)

    @commands.command()
    async def cmd(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        print('hello\n')

    @commands.command()
    async def membernametest(self, ctx):
        member = ctx.author
        await ctx.send('name' + member.name)
        await ctx.send('global name' + member.global_name)
        await ctx.send('display name' + member.display_name)
        await ctx.send('str(member)' + str(member))

    @commands.command()
    async def getchannels(self, ctx):
        guild = ctx.guild
        channels = [channel.name for channel in guild.channels if str(channel.type) == 'text']
        await ctx.send(', '.join(channels))

    # async def on_select(interaction: discord.Interaction):
    # game_count = sb.get_current_player_counts()

    # if game_count['success'] is False:
    #     await interaction.response.send_message("API error")
    #     return
    
    # # label可能不存在
    # result = interaction.data["label"][0]
    # await interaction.response.send_message(result)
    # embed=discord.Embed(title="title", description="description", color=discord.Color.blue(), timestamp=datetime.now())
    # embed.set_author(name="hypixel 遊戲遊玩人數", icon_url=embed_link)
    # embed.add_field(name="總人數", value=game_count['playerCount'], inline=False)
    # embed.add_field(name=result, value=game_count['games'][result]['players'], inline=False)

    # await interaction.response.send_message(embed=embed)



#僅個人可見command
    # @app_commands.command()
    # async def testephemeral(self, interaction: discord.Interaction):
    #     try:
    #         await interaction.response.send_message("Yo", ephemeral=True)
    #     except Exception as e:
    #         print("Error with: " + e)

    # @commands.hybrid_command()
    # async def testephemeralt(self, ctx):
    #     try:
    #         await ctx.send("Yo", ephemeral=True)
    #     except Exception as e:
    #         print("Error with: " + e)
    


#---------------------------------------------------

    #Testing commands

#---------------------------------------------------

    #發送本地圖片
    #無圖片
    # @commands.command()
    # async def 圖片(self, ctx):
    #     pic1 = discord.file(jdata['pic1'])
    #     await ctx.send(file=pic1)

    # @commands.command()
    # async def BOTname(self, ctx):
    #     await ctx.send(f'{self.AppInfo.name}')

    # #每日簽到
    # @commands.command()
    # #name = "每日簽到", description = "每日簽到(如果更改使用者ID則每日簽到記錄會重製)"
    # async def signin(self, ctx):
    #     try:
    #         path = f"./cmds/new_folder/player.txt"
    #         #從path中的file存取list
    #         file = open(path, mode = 'rt', encoding = "utf8")
    #         lst = list()
    #         lst = file.read()
    #         lst = lst[]
    #         for i in lst:
    #             if i == ctx.author:
    #                 lst[i+1] += 1
    #                 break
    #             else:
    #                 lst.append(str(ctx.author))
    #                 a = 0
    #                 lst.append(a)
    #                 break
    #         file.close()
    #         #將已改的list存入file中
    #         file = open(path, mode = 'at', encoding = "utf8")
    #         file.write(str(lst))
    #         file.close()

    #         await ctx.send(f'您已在「{time.strftime("%Y/%m/%d/ %H:%M:%S")}」時簽到')
    #     except Exception as e:
    #         print(f'出錯when: {e}')

    # # hypixel人數，遊戲選單
    # @commands.command()
    # async def hypixel_count(self, ctx):
    #     try:
            
    #         # embed=discord.Embed(title="title", description="description", color=discord.Color.blue(), timestamp=datetime.now())
    #         # embed.set_author(name="hypixel 遊戲遊玩人數", icon_url=embed_link)
    #         # embed.add_field(name="總人數", value=game_count['playerCount'], inline=False)
    #         # for game in game_count['games']:
    #         #     embed.add_field(name=game, value=game_count['games'][game]['players'], inline=False)
    #         # await ctx.send(embed=embed)

    #         view = discord.ui.View()
    #         select = discord.ui.Select(
    #             placeholder="選擇一個遊戲",
    #             options = [
    #                 discord.SelectOption(label='MAIN_LOBBY', value='1'),
    #                 discord.SelectOption(label='SMP', value='2'),
    #                 discord.SelectOption(label='LEGACY', value='3'),
    #                 discord.SelectOption(label='DUELS', value='4'),
    #                 discord.SelectOption(label='ARCADE', value='5'),
    #                 discord.SelectOption(label='UHC', value='6'),
    #                 discord.SelectOption(label='HOUSING', value='7'),
    #                 discord.SelectOption(label='WALLS3', value='8'),
    #                 discord.SelectOption(label='PROTOTYPE', value='9'),
    #                 discord.SelectOption(label='MURDER_MYSTERY', value='10'),
    #                 discord.SelectOption(label='MCGO', value='11'),
    #                 discord.SelectOption(label='REPLAY', value='12'),
    #                 discord.SelectOption(label='WOOL_GAMES', value='13'),
    #                 discord.SelectOption(label='PIT', value='14'),
    #                 discord.SelectOption(label='SKYWARS', value='15'),
    #                 discord.SelectOption(label='TNTGAMES', value='16'),
    #                 discord.SelectOption(label='BEDWARS', value='17'),
    #                 discord.SelectOption(label='SKYBLOCK', value='18'),
    #                 discord.SelectOption(label='BATTLEGROUND', value='19'),
    #                 discord.SelectOption(label='SUPER_SMASH', value='20'),
    #                 discord.SelectOption(label='BUILD_BATTLE', value='21'),
    #                 discord.SelectOption(label='SURVIVAL_GAMES', value='22'),
    #                 discord.SelectOption(label='LIMBO', value='23'),
    #                 discord.SelectOption(label='IDLE', value='24'),
    #                 discord.SelectOption(label='QUEUE', value='25')
    #             ],
    #         )
    #         select.callback = on_select
    #         view.add_item(select)
    #         await ctx.send("來看看 Select 吧", view=view)
    #         await view.on_timeout()

    #     except Exception as e:
    #         print("Error: ", e)
    #         await ctx.send("程式出錯，請稍後再試 或尋求幫助")

    # #回覆現在時間
    # @tasks.loop(hours=1, count=1)
    # async def ocloak(self, ctx):
    #     channel = ctx.guild.system_channel
        
    #     if channel.permissions_for(ctx.guild.me).send_messages:
    #         await channel.send(f'現在時間: {time.strftime("%Y/%m/%d %H:%M:%S")}')

    # def yt(url):
    #     yt = YouTube(url)
    #     # 獲取所有音訊
    #     audio_streams = yt.streams.filter(only_audio=True)
    #     # 找到最高的abr
    #     highest_abr_stream = max(audio_streams, key=lambda stream: int(stream.abr[:-4]))
    #     # 獲取音訊流的URL
    #     audio_url = highest_abr_stream.url
    #     return audio_url






async def setup(bot):
    await bot.add_cog(TestTemp(bot))