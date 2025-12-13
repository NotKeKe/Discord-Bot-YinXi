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
import motor.motor_asyncio

from core.functions import read_json, thread_pool, KeJCID, create_basic_embed, MONGO_URL, split_str_by_len_and_backtick

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

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

        
    @commands.command()
    async def testtemp(self, ctx):
        await ctx.send("hello, this is testtemp", ephemeral=True)

    @commands.hybrid_command(name='取得所有指令名稱')
    async def get_all_commands(self, ctx: commands.Context):
        await ctx.send((', '.join(sorted(list(self.bot.all_commands)))) + f'\n共有 `{len(self.bot.all_commands)}` 個指令')

    @commands.command()
    async def embedtest(self, ctx):
        try:
            embed=discord.Embed(title="title", description="description", color=0xff0000, timestamp=datetime.now())
            embed.set_author(name="name", url="https://discord.gg/MhtxWJu")
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

    @commands.command()
    async def test(self, ctx: commands.Context):
        eb = create_basic_embed(description='hi', 功能='hi')
        await ctx.send(embed=eb)

    @commands.command()
    async def mongo_test(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
                db = client['test']
                collection = db[str(ctx.author.id)]

                await collection.insert_one({
                    'title': 'abcdefg',
                    'user': ctx.author.id,
                    'messages': [
                        {'role': 'user', 'content': 'prompt'},
                        {'role': 'assistant', 'content': 'wdym'}
                    ],
                    'createAt': datetime.now().timestamp()
                })

                await ctx.send(f"現在伺服器上的資料庫: {await client.list_database_names()}")
                await ctx.send(f"在 'test' 中的 collections: {await db.list_collection_names()}")
                await ctx.send(f'找到 {await collection.find_one({'user': ctx.author.id})}')
                async for d in collection.find({'user': ctx.author.id}):
                    await ctx.send(f'找到一項數據: {d}')
                await collection.update_one({
                    'title': 'abcdefg'
                },
                {
                    '$set': {
                        'messages': [
                            {'role': 'user', 'content': 'prompt2'},
                            {'role': 'assistant', 'content': 'wdym2'}
                        ]
                    }
                }
                )
        finally:
            if client:
                # client.drop_database('test')
                client.close()

    @commands.command()
    async def split_text_test(self, ctx: commands.Context):
        original_text = '''
不好意思，我剛才用了 Markdown 表格，違反了「禁止使用表格」的規則。下面把先前的比較內容改成純文字的項目符號版，讓你可以直接閱讀。\n\n---\n\n## 為什麼會想換成 MongoDB？\n\n- **多使用者同時存取**  \n  - JSON 同時被多個指令讀寫時會出現檔案鎖定或競爭條件。MongoDB 原生支援並發連線，寫入、讀取都是 atomic 的。  \n\n- **資料量漸增**  \n  - 若開始記錄使用者統計、排行榜或每日活動紀錄，JSON 檔案會變得又大又慢。MongoDB 會自行建立索引、分片，查詢速度不會因資料量變大而退化。  \n\n- **靈活的查詢**  \n  - 例如「找出過去 7 天內發言次數最高的 10 位使用者」可以直接在資料庫用 filter、aggregation 完成，不必一次把整個檔案載入記憶體。  \n\n- **備份與恢復**  \n  - MongoDB 可以設定自動快照、備份腳本，甚至使用雲端 Atlas 的一鍵還原。JSON 若只靠手動備份或 git，有遺失風險。  \n\n- **可擴充的結構**  \n  - 想在未來加新欄位（等級、勳章、偏好設定）時，BSON 允許文件自行增減欄位；JSON 則需要搬遷程式或重新寫入。  \n\n---\n\n## 為什麼還可以繼續使用 JSON？\n\n- **簡單、零成本**  \n  - 只要有一個檔案就能跑，部署到 Heroku、Replit、Docker 都不需要額外資料庫服務。  \n\n- **開發門檻低**  \n  - 讀寫只需要 `json.load` / `json.dump`，不必學 async driver、連線池、錯誤處理。  \n\n- **資料量真的很小**  \n  - 若 Bot 只存設定檔、冷卻時間、少量使用者偏好，幾 KB–MB 的檔案毫無壓力。  \n\n- **部署環境限制**  \n  - 有些免費的 Discord Bot 托管平台只允許本機磁碟，這時 JSON 是唯一選擇。  \n\n---\n\n## 把 JSON 換成 MongoDB 的實作要點（使用 Motor – async）\n\n1. **建立連線（放在 bot 初始化時）**  \n   ```python\n   from motor.motor_asyncio import AsyncIOMotorClient\n\n   client = AsyncIOMotorClient(\"mongodb://localhost:27017\")   # 或 Atlas 連線字串\n   db = client[\"discord_bot\"]\n   col_user = db[\"user_data\"]          # 存每位使用者的設定\n   ```\n\n2. **讀取資料**  \n   ```python\n   async def get_user_data(user_id: int) -> dict:\n       doc = await col_user.find_one({\"_id\": str(user_id)})\n       if doc is None:                     # 若無資料就給預設值\n           return {\"_id\": str(user_id), \"xp\": 0, \"level\": 1}\n       return doc\n   ```\n\n3. **更新資料（upsert）**  \n   ```python\n   async def set_user_data(user_id: int, data: dict):\n       await col_user.update_one(\n           {\"_id\": str(user_id)},\n           {\"$set\": data},\n           upsert=True\n       )\n   ```\n\n4. **範例指令（discord.py）**  \n   ```python\n   @bot.command()\n   async def xp(ctx, amount: int):\n       user = await get_user_data(ctx.author.id)\n       user[\"xp\"] += amount\n       await set_user_data(ctx.author.id, user)\n       await ctx.send(f\"{ctx.author.mention} 獲得了 {amount} XP！\")\n   ```\n\n- **全程 async**：Motor 本身是非同步的，配合 `discord.py` 不會阻塞事件迴圈。  \n- **`_id` 使用字串**：MongoDB 必須唯一，直接把 Discord user ID 轉成字串最簡單。  \n- **`upsert=True`**：一次指令就能「新增或更新」，不必先判斷是否存在。  \n\n---\n\n## 成本與部署注意（純文字列點）\n\n- **伺服器資源**  \n  - JSON：無額外需求。  \n  - 自行部署 MongoDB：需要一台可以跑 `mongod` 的機器（CPU、記憶體）。  \n  - MongoDB Atlas（Free Tier）：雲端託管，免費配額有限（約 512 MiB 儲存、500 MB 傳輸）。\n\n- **連線延遲**  \n  - JSON：本機讀寫，毫秒級。  \n  - 自己部署的 MongoDB：內網或遠端，視網路而定。  \n  - Atlas：跨區域仍在 100‑200 ms 左右，對大多數 Bot 來說足夠。\n\n- **資料備份**  \n  - JSON：手動備份或透過 Git commit。  \n  - MongoDB：可使用 `mongodump`、cron 排程備份。  \n  - Atlas：自動快照與每日備份功能。\n\n- **安全性**  \n  - JSON：靠檔案權限保護。  \n  - MongoDB（自行部署）：需要設定認證、IP 白名單。  \n  - Atlas：內建使用者/密碼、IP 過濾。\n\n- **成本**  \n  - JSON：完全免費。  \n  - 自行部署 MongoDB：需自行負擔伺服器或 VPS 費用。  \n  - Atlas（Free Tier）：免費，但有配額上限；若超出需付費。\n\n---\n\n## 小結與建議（項目符號）\n\n- **先評估規模**  \n  - 每日寫入次數 < 10‑20 次、使用者 < 100，JSON 完全足夠。  \n  - 使用者數超過幾千、需要排行榜或跨伺服器同步時，考慮搬遷到 MongoDB。  \n\n- **抽象資料存取層**  \n  - 把讀寫封裝成 `get_user_data / set_user_data`（async），日後只要改成 MongoDB，其他指令不需要大幅調整。  \n\n- **先測試**  \n  - 在本機安裝 MongoDB（或用 Docker `docker run -d -p 27017:27017 mongo`），跑上面的範例感受延遲與程式碼變動量。  \n\n- **定期備份**  \n  - 無論選 JSON 或 MongoDB，都要記得 **定期備份**（JSON → Git commit，MongoDB → `mongodump`），避免資料遺失。  \n\n---\n\n如果你決定要搬遷，或是想在現有 JSON 上再加上檔案鎖定機制（例如 `filelock`）來避免同時寫入衝突，我可以提供簡易範例。  \n或是想看看在 MongoDB 裡做聚合、排行榜的程式碼，也隨時告訴我喔！祝你的 Bot 越玩越順、資料越安全～ (✿◠‿◠)
'''.strip()
        for item in split_str_by_len_and_backtick(original_text):
            await ctx.send(item)

    @commands.command()
    async def check_playwright_connect(self, ctx: commands.Context):
        from core.playwright import contexts
        await ctx.send(contexts)
        
    # async def on_select(interaction: discord.Interaction):
    # game_count = sb.get_current_player_counts()

    # if game_count['success'] is False:
    #     await interaction.response.send_message("API error")
    #     return
    
    # # label可能不存在
    # result = interaction.data["label"][0]
    # await interaction.response.send_message(result)
    # embed=discord.Embed(title="title", description="description", color=discord.Color.blue(), timestamp=datetime.now())
    # embed.set_author(name="hypixel 遊戲遊玩人數")
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
    #         # embed.set_author(name="hypixel 遊戲遊玩人數")
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