import discord
from discord.ext import commands, tasks

from core.functions import read_json, write_json, create_basic_embed, math_round

PATH = './cmds/data.json/counting.json'

example_data = {
    '123456789': {
        'user': 1516546515,
        'count': 0
    }
}

class Counting(commands.Cog):
    data = None
    is_update = False

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage_data_task.start()

    @classmethod
    def initdata(cls):
        if cls.data is None:
            cls.data = read_json(PATH)

    @classmethod
    def writeData(cls, data):
        if data is None:
            cls.data = data
        cls.is_update = True

    @classmethod
    def timedStorage(cls):
        write_json(cls.data, PATH)
        cls.is_update = False

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.initdata()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not message.content: return
        try: 
            content = float(message.content.strip())
            content = int(math_round(content))
        except: return
        self.initdata()
        channelID = str(message.channel.id)
        data = self.__class__.data
        if channelID not in data: return

        preUserID = data[channelID].get('user')
        count = data[channelID].get("count")
        eb = None
        userID = message.author.id

        if preUserID == userID:
            if str(content) == '6': return
            await message.add_reaction('❌')
            eb = create_basic_embed(f'❌ 你剛剛輸入過數字了，你不能一直輸入 \n下一個數字為 **1**', color=message.author.color, time=False)
            userID = 0
            count = 0
        elif count == 0 and content != 1:
            if str(content) == '6': return
            await message.add_reaction('⚠️')
            eb = create_basic_embed(f'⚠️ 請從 **1** 開始輸入，而不是 {content}', color=message.author.color, time=False)
            userID = 0
            count = 0
        elif content > count + 100: # 使用者輸入過大的數字
            await message.add_reaction('⚠️')
            eb = create_basic_embed(f'⚠️ 你輸入了過大的數字 **{content}**', color=message.author.color, time=False)
        elif content < count - 100:
            await message.add_reaction('⚠️')
            eb = create_basic_embed(f'⚠️ 你輸入了過小的數字 **{content}**', color=message.author.color, time=False)
        elif content != count + 1: # 使用者數錯
            if str(content) == '6': return
            await message.add_reaction('❌')
            eb = create_basic_embed(f'❌ 你輸入了錯誤的數字 **{content}**\n你應該輸入 **{count+1}**\n下一個數字為 **1**', color=message.author.color, time=False)
            userID = 0
            count = 0
        else: # 正常情況
            count += 1
            await message.add_reaction('✅')
        
        data[channelID]['count'] = count
        data[channelID]['user'] = userID
        self.writeData(data)
        if eb:
            await message.channel.send(message.author.mention, embed=eb)

    @commands.hybrid_command(name='數數頻道', description="Set a count channel.", aliases=['counting', 'count'])
    async def counting(self, ctx):
        self.initdata()
        data = self.__class__.data
        channelID = str(ctx.channel.id)
        if channelID in data: return await ctx.send(f'此頻道正在數數，數字為 {data[channelID]}')
        data[channelID] = {
            'user': 0,
            'count': 0
        }
        self.writeData(data)
        await ctx.send('此頻道已加入數字計數')

    @tasks.loop(minutes=1)
    async def storage_data_task(self):
        if not self.__class__.is_update: return
        self.timedStorage()

    @storage_data_task.before_loop
    async def storage_data_task_before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Counting(bot))