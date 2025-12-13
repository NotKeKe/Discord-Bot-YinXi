import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.app_commands import Choice
from core.classes import Cog_Extension
import os
import json
from datetime import datetime
import re
import traceback
import asyncio
from dotenv import load_dotenv

from cmds.skyblock_commands_foldor import skyblock_commands, skyblock_events

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
api_key = os.getenv('tmp_hypixel_api_key')

current_directory = os.getcwd()
with open(f"{current_directory}/setting.json", "r") as jfile:
    jdata = json.load(jfile)

sb = skyblock_commands.Skyblock(api_key=api_key)

def remove_color_codes(text): # 此段函式由Copliot生成
    return re.sub(r'§.', '', text)

def get_dict() -> dict:
    events = skyblock_events.show_next_events()
    return events

class skyblock_main(Cog_Extension):

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @tasks.loop(hours=2)  # 每 2 小時執行一次
    async def update_embed_task(self):
        try:
            messsage_channel = int(jdata['skyblock_events'])
            channel = self.bot.get_channel(messsage_channel)
        except:
            try: 
                user = await self.bot.fetch_user(int(jdata['KeJC_ID']))
                await user.send("無法取得頻道") 
                return
            except discord.Forbidden: 
                return
        # await self.bot.get_user(int(jdata['KeJC_ID'])).send("已開始追蹤New Year Celebration活動")

        delay = sb.time_until_new_year_celebration()
        if delay < 7200:
            await asyncio.sleep(delay)
            await channel.send("New Year Cake!")
        

    @commands.hybrid_command(name="uuid", description="取得玩家的uuid")
    @discord.app_commands.describe(username="輸入使用者名稱(ID)")
    async def uuid(self, ctx, username: str):
        try:
            await ctx.send(sb.get_uuid(player_name=username))
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False)

    @commands.command()
    async def test_apikey(self, ctx):
        a = sb.get_player_status(player_name="KeJC")
        await ctx.send(type(a['success']))
        await ctx.send(a['success'])
        await ctx.send(type(a['cause']))
        await ctx.send(a['cause'])
    
    @commands.hybrid_command(name="status", description="獲得 skyblock 玩家在線狀態")
    @discord.app_commands.describe(username="輸入使用者名稱(ID)")
    async def playerstatus(self, ctx, username: str):
        try:
            a = sb.get_player_status(player_name=username)

            if a['success'] is False:
                embed=discord.Embed(title="錯誤", description=a['cause'], color=discord.Color.blue(), timestamp=datetime.now())
                await ctx.send(embed=embed)
                return

            embed=discord.Embed(title="Player Name", description=sb.get_player_name(username), color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="玩家狀態", url=None)
            embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')
            embed.add_field(name="狀態", value=a["session"]["online"], inline=True)
            embed.add_field(name="註: ", value="資訊是從hypixel-api得來的，可能不準確")
            # embed.set_footer(text="footer")
            await ctx.send(embed=embed)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, exception=exception, user_send=False)

    @commands.hybrid_command(name="guild_name", description="取得 skyblock 玩家的公會名稱")
    @discord.app_commands.describe(username="輸入使用者名稱(ID)")
    async def player_guild(self, ctx, username: str):
        try:
            a = (sb.get_guild_info(username))

            if a['success'] is False:
                embed=discord.Embed(title="錯誤", description=a['cause'], color=discord.Color.blue(), timestamp=datetime.now())
                await ctx.send(embed=embed)
                return
            
            # file = discord.File("./image/discord_embed_author.png")
            embed=discord.Embed(title="Player Name", description=sb.get_player_name(username), color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="取得公會名稱", url=None)
            embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')
            embed.add_field(name="公會名稱", value=f'**{a["guild"]["name"]}**', inline=False)
            # embed.set_footer(text="footer")
            await ctx.send(embed=embed)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, exception=exception, user_send=False)

    @commands.hybrid_command(name="mayor", description="取得當前skyblock的市長")
    async def get_mayor(self, ctx):
        try:
            mayor, minister, lastUpdated = sb.get_mayor()
            mayor_info = sb.get_mayor_information()
            minister_info = sb.get_minister_information()
            mayor_perks_info = sb.get_mayor_perks_description()
            minister_perk_info = sb.get_minister_perk_description()

            """下三行代碼為Copliot生成"""
            """清除mayor_perks_info中的 '§' 符號"""
            cleaned_mayor_perks_info = [remove_color_codes(info) for info in mayor_perks_info]
            combined_info = [f"{info}\n- {perk}" for info, perk in zip(mayor_info, cleaned_mayor_perks_info)]
            output = "\n".join(combined_info)

            """清除minister_perk_info中的cleaned_mayor_perks_info '§' 符號"""
            if minister is not None:
                cleaned_minister_perks_info = remove_color_codes(minister_perk_info)

            embed=discord.Embed(title=mayor, description=output, color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="取得現在的skyblock市長 以及副市長", url=None)
            # embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')
            if minister is not None:
                embed.add_field(name=minister, value=f'{minister_info}\n- {cleaned_minister_perks_info}', inline=False)
            embed.set_footer(text=f"API 更新時間{lastUpdated}")
            await ctx.send(embed=embed)
        except Exception as exception:
            traceback.print_exc()

    @commands.hybrid_command()
    async def events(self, ctx):
        try:
            events = get_dict()
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=True, ephemeral=False)

        embed=discord.Embed(title="Events", color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name="取得skyblock活動")
        embed.add_field(name=event, value=f"**Skyblock Year**: {events['sb_year']}", inline=False)
        for event in events:
            embed.add_field(name=event, value=f"開始時間: {events[event]['Start']}\n結束時間: {events[event]['End']}", inline=False)

            #
        await ctx.send(embed=embed)

    @commands.hybrid_command(name = "hypixel_game_count", description = "取得hypixel遊戲的遊玩人數")
    @app_commands.describe(game = "輸入一個遊戲，未輸入則為hypixel當前遊玩總人數")
    @app_commands.choices(
        game = [
            Choice(name = 'MAIN_LOBBY', value = '1'),
            Choice(name = 'SMP', value = '2'),
            Choice(name = 'LEGACY', value = '3'),
            Choice(name = 'ARCADE', value = '4'),
            Choice(name = 'DUELS', value = '5'),
            Choice(name = 'UHC', value = '6'),
            Choice(name = 'HOUSING', value = '7'),
            Choice(name = 'WALLS3', value = '8'),
            Choice(name = 'PROTOTYPE', value = '9'),
            Choice(name = 'MURDER_MYSTERY', value = '10'),
            Choice(name = 'MCGO', value = '11'),
            Choice(name = 'REPLAY', value = '12'),
            Choice(name = 'WOOL_GAMES', value = '13'),
            Choice(name = 'PIT', value = '14'),
            Choice(name = 'SKYWARS', value = '15'),
            Choice(name = 'TNTGAMES', value = '16'),
            Choice(name = 'BEDWARS', value = '17'),
            Choice(name = 'SKYBLOCK', value = '18'),
            Choice(name = 'BATTLEGROUND', value = '19'),
            Choice(name = 'SUPER_SMASH', value = '20'),
            Choice(name = 'BUILD_BATTLE', value = '21'),
            Choice(name = 'SURVIVAL_GAMES', value = '22'),
            Choice(name = 'LIMBO', value = '23'),
            Choice(name = 'IDLE', value = '24'),
            Choice(name = 'QUEUE', value = '25')
        ]
    )
    async def hypixel_count(self, ctx, game: Choice[str] = None):
        try:
            game_count = sb.get_current_player_counts()

            if game_count['success'] is False:
                embed=discord.Embed(title="錯誤", description=game_count['cause'], color=discord.Color.blue(), timestamp=datetime.now())
                await ctx.send(embed=embed)
                return
            
            embed=discord.Embed(color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="hypixel 遊戲遊玩人數")
            if game is None:
                embed.add_field(name="總人數", value=game_count['playerCount'], inline=False)
            else:
                game = game.name
                embed.add_field(name=game, value=game_count['games'][game]['players'], inline=False)

            await ctx.send(embed=embed)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False)

    @commands.hybrid_command(name="auction", description="取得 skyblock 玩家當前正在拍賣的物品")
    @discord.app_commands.describe(username="輸入使用者名稱(ID)")
    async def player_auction(self, ctx, username: str):
        try:
            a = sb.get_player_auctions(username) # dict

            if a['success'] is False:
                embed=discord.Embed(title="錯誤", description=a['cause'], color=discord.Color.blue(), timestamp=datetime.now())
                await ctx.send(embed=embed)
                return

            embed=discord.Embed(title="Player Name", description=sb.get_player_name(username), color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="取得玩家的auction", url=None)
            embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')

            for i in range(len(a["auctions"])):
                if a['auctions'][i]['claimed'] is False and 'bin' in a['auctions'][i]: # 如果未領取才輸出結果
                    embed.add_field(name="物品名稱: ", value=a["auctions"][i]["item_name"], inline=False)

                    if not a["auctions"][i]["claimed_bidders"]: # 售出狀態, 未售出
                        embed.add_field(name="售出狀態:", value=":x: 未售出", inline=False)

                        if int(a['auctions'][i]["end"]) > sb.time_now_disconversion(): # 過期狀態
                            embed.add_field(name="過期狀態: ", value=":white_check_mark: 未過期", inline=False)
                        else:
                            embed.add_field(name="過期狀態: ", value=":x: 過期", inline=False)
                    else:
                        embed.add_field(name="售出狀態:", value=":white_check_mark: 售出, 請記得領取", inline=False)

                    if a['auctions'][i]['highest_bid_amount'] != 0: embed.add_field(name='最高標價', value="{:,}".format(a['auctions'][i]['highest_bid_amount']), inline=False)
                    embed.add_field(name=" ", value=' ', inline=True)

                
                if a['auctions'][i]['claimed'] is False and 'bin' not in a['auctions'][i]: # 如果未領取才輸出結果
                    embed.add_field(name="物品名稱: ", value=a["auctions"][i]["item_name"], inline=False)

                    if a["auctions"][i]["claimed_bidders"]: # 售出狀態, 已售出
                        embed.add_field(name="售出狀態:", value=":white_check_mark: 售出, 請記得領取", inline=False)
                        embed.add_field(name="領取狀態:", value=":x: 未領取", inline=False)
                    elif int(a['auctions'][i]["end"]) > sb.time_now_disconversion():
                        
                        embed.add_field(name="過期狀態: ", value=":white_check_mark: 未過期", inline=False)

                    if int(a['auctions'][i]["end"]) <= sb.time_now_disconversion(): # 過期
                        embed.add_field(name="過期狀態: ", value=":x: 過期", inline=False)

                    if a['auctions'][i]['highest_bid_amount'] != 0: embed.add_field(name='最高標價', value="{:,}".format(a['auctions'][i]['highest_bid_amount']), inline=False)
                    embed.add_field(name=" ", value=' ', inline=True)
            # embed.set_footer(text="footer")
            await ctx.send(embed=embed)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False)


async def setup(bot):
    await bot.add_cog(skyblock_main(bot))