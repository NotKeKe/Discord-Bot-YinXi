import discord
from discord.ext import commands
import traceback

from core.classes import Cog_Extension
from core.functions import create_basic_embed, read_json, write_json, thread_pool, KeJCID

path = './cmds/data.json/levels.json'

# (等級, MsgCount)
標準 = [(n, 3**n) for n in range(50)]
名稱 = ['新手', '一般玩家', '大佬', '巨佬', '小辣雞', '大辣雞', '萌新']

ex_data = {
    'GUILDID':{
        'USERID': ['LEVEL', 124569]
    }
}

ex_標準 = [(1, 2), (2, 4), (3, 8)]

def for_loop(標準, MsgCount):
    '''回傳計算後user的等級(1~50等)'''
    level = 0
    for index, item in enumerate(標準):
        if index == 0: continue

        if 標準[index-1][1] <= MsgCount < 標準[index][1]:
            level = 標準[index-1][0]
    return level

def sortMsgCount(data):
    '''data = data[guildID]'''
    # 儲存 userid 和對應的值
    userid_values = []

    # 遍歷資料
    for user_id, values in data.items():
        userid_values.append((user_id, values[0], values[1]))

    # 根據值進行排序（由大到小）
    userid_values.sort(key=lambda x: x[1], reverse=True)

    return userid_values[:10]

class Levels(Cog_Extension):
    data = None

    @classmethod
    def initdata(cls):
        if cls.data is None:
            cls.data = read_json(path)

    @classmethod
    def savedata(cls, data):
        if cls.data is not None:
            cls.data = data
            write_json(cls.data, path)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.initdata()

    @commands.Cog.listener()
    async def on_message(self, ctx):
        try:
            if ctx.author.bot: return
            if not ctx.guild: return

            self.initdata()
            data = self.__class__.data

            guildID = str(ctx.guild.id)
            userID = str(ctx.author.id)

            # 針對guild做初始化
            if guildID not in data:
                data[guildID] = {
                    userID: [0, 0]
                }
            else: # 針對一個已經有資料的guild 中的user做初始化
                if userID not in data[guildID]:
                    data[guildID][userID] = [0, 0]
            
            data[guildID][userID][1] += 1

            MsgCount = data[guildID][userID][1]
            
            level = await thread_pool(for_loop, 標準, MsgCount)

            # await ctx.channel.send(f'{level=}')
            # await ctx.channel.send(f'{data[guildID][userID][0]=}')

            if data[guildID][userID][0] != level:
                await ctx.channel.send(f'你的長度變成{level}公分了')
                data[guildID][userID][0] = level

            self.savedata(data)
        except:
            traceback.print_exc()

    @commands.hybrid_command(aliases=['rank', 'ranks', '等級'], name='聊天等級')
    async def rank(self, ctx):
        self.initdata()
        guildID = str(ctx.guild.id)
        userID = str(ctx.author.id)
        data = self.__class__.data

        if data is None: await ctx.send('尚未儲存任何聊天等級'); return
        if guildID not in data: await ctx.send('此伺服器尚未儲存任何聊天等級資訊'); return


        MsgCount = data[guildID][userID][1]
        level = await thread_pool(for_loop, 標準, MsgCount)

        if userID not in data[guildID] or level == 0: await ctx.send('你尚未在此伺服器傳送足夠的訊息'); return
                    
        embed = create_basic_embed(title=ctx.author.display_name, description=f"你現在是 {名稱[level-1] if level-1 <= len(名稱)-1 else '萌新'} ({level}等)",
                                   color=ctx.author.color)

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['levels', 'level', '排行'], name='伺服器聊天等級排行')
    async def levels(self, ctx):
        self.initdata()
        data = self.__class__.data
        guildID = str(ctx.guild.id)

        if data is None: await ctx.send('尚未儲存任何聊天等級'); return
        if guildID not in data: await ctx.send('此伺服器尚未儲存任何聊天等級資訊'); return

        embed:discord.Embed = create_basic_embed(title=' ', color=ctx.author.color, 功能='伺服器等級排行', time=False)

        userID_values = sortMsgCount(data[guildID])

        for i, (user_id, level, count) in enumerate(userID_values):
            user = await self.bot.fetch_user(int(user_id))
            if i == 0:
                embed.set_footer(text=f"{user.display_name}獲得了第一名🎉🎉🎉", icon_url=user.avatar.url)
            embed.add_field(name=f"{i+1}. {user.display_name} ({level}等，{count}則訊息)", value=' ', inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='強制leveldata')
    async def force_level_data(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        data = self.__class__.data
        
        if data is None: await ctx.send('data is none'); return

        write_json(self.__class__.data, path)
    


async def setup(bot):
    await bot.add_cog(Levels(bot))