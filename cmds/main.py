import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
import json
from datetime import datetime
import random
import os
from dotenv import load_dotenv
import uuid
import asyncio

from cmds.AIsTwo.others.func import image_read
from cmds.AIsTwo.utils import image_url_to_base64

from core.classes import Cog_Extension
from core.functions import thread_pool, admins, KeJCID, write_json, create_basic_embed, UnixToReadable, download_image, UnixNow

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')


#setting.json
with open('setting.json', 'r', encoding = 'utf8') as jfile:
        #(檔名，mode=read)
    jdata = json.load(jfile)


class Main(Cog_Extension):

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    #Owner ID回覆
    @commands.hybrid_command(aliases=['ownerid'], name = "管理員id回覆", description = "OwnerID")
    async def ownerid(self, ctx):
        '''
        [管理員id回覆
        會傳個訊息跟你說這群的群主名字 跟他的ID
        '''
        guild_owner = await self.bot.fetch_user(int(ctx.guild.owner_id))
        embed=discord.Embed(title="Owner名字", description=guild_owner.mention, color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name="管理員是誰?", icon_url=embed_link)
        embed.add_field(name='Owner ID', value=ctx.guild.owner_id, inline=False)
        await ctx.send(embed=embed)

    #取得延遲
    @commands.hybrid_command(name="ping", description="取得延遲")
    async def ping(self, ctx):
        '''
        [ping
        傳送延遲(我也不知道這延遲是怎麼來的)
        '''
        embed = discord.Embed(
        color=discord.Color.red(), 
        title="延遲", 
        description=f'**{round(self.bot.latency*1000)}** (ms)', 
        timestamp=datetime.now()
        )

        await ctx.send(embed = embed)

    #重複我說的話
    @commands.hybrid_command(name = "重複你說的話", description = "Repeat you")
    @discord.app_commands.describe(arg = '你要bot說的話')
    async def test(self, ctx, *, arg):
        '''
        [重複你說的話 arg(然後打你要的字)
        沒啥用的功能，如果你想要bot重複你說的話就用吧
        '''
        await ctx.send(arg)

    #我在哪
    @commands.hybrid_command(name = "我在哪裡", description = "Where are you, 說出你在的伺服器名稱以及頻道")
    async def whereAmI(self, ctx):
        '''
        [我在哪裡
        說出你在哪 會有伺服器名稱跟頻道的名稱
        '''
        embed = discord.Embed(
        color=discord.Color.blue(),
        title="Where Are You?",
        description=f"你在 「{ctx.guild.name}」的 {ctx.channel.mention} 頻道當中",
        timestamp=datetime.now()
        )

        await ctx.send(embed=embed)

    #回傳使用者頭貼
    @commands.hybrid_command()
    async def avatar(self, ctx, member: discord.Member = None):
        '''
        [avatar member
        member的話能tag人，或是都沒輸入的話就回傳你自己的頭貼
        '''
        if member is None:
            member = ctx.author

        try:        
            embed=discord.Embed(title=member, color=member.color).set_image(url=member.avatar.url)
        except:
            await ctx.send(f"使用者「 {member} 」沒有頭貼")
            return
        embed.set_author(name="name", icon_url=embed_link)
        await ctx.send(embed=embed)
    
    #獲得該guild的system channel
    @commands.hybrid_command(name='取得伺服器預設頻道', description='Get the system channel')
    async def systemChannel(self, ctx):
        channel = await self.bot.fetch_channel(ctx.guild.system_channel.id)
        if channel is None:
            await ctx.send('此伺服器沒有預設頻道')
        else:
            await ctx.send(channel.mention)

    @commands.command(name='add_admin')
    async def add_admin(self, ctx: commands.Context, userID: int = None):
        if str(ctx.author.id) != KeJCID: return

        global admins
        if not userID: userID = ctx.author.id
        userName = (await self.bot.fetch_user(userID)).global_name

        if userID in admins: return await ctx.send(f'{userName} ({userID=}) 已經是管理員了', ephemeral=True)
        admins.append(userID)
        data = {'admins': admins}
        write_json(data, './cmds/data.json/admins.json')
        await ctx.send(f'已將 {userName} ({userID=}) 加入管理員', ephemeral=True)

    @commands.hybrid_command(name='伺服器資訊', description='Server info')
    async def get_server_info(self, ctx: commands.Context):
        if not ctx.guild: return await ctx.send('你不在伺服器當中')

        name = ctx.guild.name
        id = ctx.guild.id
        total_member_counts = len(ctx.guild.members)
        true_member_counts = len([m for m in ctx.guild.members if not m.bot])
        bot_counts = total_member_counts - true_member_counts
        channel_counts = len(ctx.guild.channels)
        owner = ctx.guild.owner.global_name
        ownerID = ctx.guild.owner.id
        online_member_counts = len([m for m in ctx.guild.members if m.status not in (discord.Status.offline, discord.Status.invisible)])
        # items = []
        # for m in ctx.guild.members:
        #     items.append(f'{m.name}: {m.status}\n')
        # await ctx.send(''.join(items))
        system_channel = ctx.guild.system_channel or 'None'

        eb = create_basic_embed(f'**{name}** 伺服器資訊', color=ctx.author.color)

        eb.add_field(name='📌 伺服器名稱', value=name)
        eb.add_field(name='🆔 伺服器ID', value=id)
        eb.add_field(name='👥 伺服器總人數', value=total_member_counts)
        eb.add_field(name='👤 成員數量', value=true_member_counts)
        eb.add_field(name='🤖 Bot數量', value=bot_counts)
        eb.add_field(name='📢 頻道數量', value=channel_counts)
        eb.add_field(name='👑 Owner', value=owner)
        eb.add_field(name='🆔 Owner ID', value=ownerID)
        eb.add_field(name='🟢 在線人數', value=online_member_counts)
        eb.add_field(name='📣 系統頻道', value=system_channel.mention)
        await ctx.send(embed=eb)

    @commands.hybrid_command(name='convert_timestamp', description='Convert Unix(or timestamp) to readable string')
    async def unixSecondToReadalbe(self, ctx: commands.Context, unix_second: str):
        async with ctx.typing():
            try: unix_second = int(unix_second)
            except: return await ctx.send('請輸入有效的數字')
            readable = UnixToReadable(unix_second)
            await ctx.send(readable)

    @commands.hybrid_command(name='高中生總分計算機', description='This function is for Taiwan high school students to calculate their total score')
    @app_commands.describe(image='上傳一張圖片', prompt='你想讓AI幫你什麼(僅在你有上傳圖片時，會使用此欄)')
    async def high_school_totalScore_calculate(self, ctx: commands.Context, 國文: float = 0.0, 英文: float = 0.0, 數學: float = 0.0, 化學: float = 0.0, 生物: float = 0.0, 物理: float = 0.0, 歷史: float = 0.0, 地理: float = 0.0, 公民: float = 0.0, 體育: float = 0.0, image: discord.Attachment = None, prompt: str = None):
        async with ctx.typing():
            eb = create_basic_embed(功能='總分計算機', color=ctx.author.color, time=False)

            if not image:
                weight_total = (國文 + 數學 + 英文) * 4 + (化學 + 生物 + 物理 + 歷史 + 地理 + 公民 + 體育) * 2
                total = 國文 + 數學 + 英文 + 化學 + 生物 + 物理 + 歷史 + 地理 + 公民 + 體育
                eb.add_field(name='加權總分', value=f'`{weight_total}`')
                eb.add_field(name='未加權總分', value=f'`{total}`')
                await ctx.send(embed=eb)
            else:
                if not prompt: return await ctx.send('請輸入你要讓AI幹嘛的`prompt`', ephemeral=True)
                os.makedirs('./data/upload', exist_ok=True)
                path = f'./data/upload/{ctx.author.id}_{UnixNow()}_{uuid.uuid4()}.jpg'
                absolute_path = os.path.abspath(path)
                final_url = f'https://yinxi.keketw.dpdns.org/api/image/?path={absolute_path}'
                await ctx.send(final_url)

                await download_image(image.url, path=path)

                result = await thread_pool(image_read, prompt, final_url)
                eb.add_field(name='**AI response**', value=result)
                eb.set_footer(text='Powered by glm-4v-flash')
                await ctx.send(embed=eb)

                await asyncio.sleep(300)
                os.remove(path)

    @commands.hybrid_command(name = "random_number", description = "從範圍中隨機選取整數")
    @app_commands.describe(range1 = '輸入你要隨機取數的起始數字', range2 = '輸入你要隨機取數的終止數字', times = "你要在這個範圍內隨機選出多少數字 (未輸入則預設為1)")
    async def random_number(self, ctx: commands.Context, range1: int, range2: int, times:int = None):
        async with ctx.typing():
            if times is None:
                times = 1

            if range1 > range2: # 如果使用者輸入將起始跟終止順序寫反了
                range1, range2 = range2, range1

            if times > range2-range1+1:
                await ctx.send(f'你無法在{range1}~{range2}中選出{times}個數字 (太多了!)')
                return

            def for_loop(times, range1, range2):
                result = []
                for _ in range(times):
                    while True:
                        num = random.randint(range1, range2)
                        if num not in result:
                            result.append(num)
                            break
                return result
            
            result = await thread_pool(for_loop, times, range1, range2)

            resultStr = ', '.join(map(str, result))
            await ctx.send(resultStr)

async def setup(bot):
    await bot.add_cog(Main(bot))
