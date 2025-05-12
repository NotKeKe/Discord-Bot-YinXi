import discord
from discord.ext import commands, tasks
from pretty_help import PrettyHelp
import json
import os
from dotenv import load_dotenv
import asyncio
import time
import traceback

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')

#setting.json
with open('setting.json', 'r', encoding = 'utf8') as jfile:
        #(檔名，mode=read)
    jdata = json.load(jfile)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True


bot = commands.Bot(command_prefix='[', intents=intents)
# tree = app_bot.CommandTree(bot)

# Bot's help default command
ending_note = "這是 {ctx.bot.user.name} 的commands help\n輸入 {help.clean_prefix}{help.invoked_with} 或是 [helping 來尋求幫助"
# bot.help_command = PrettyHelp(color=discord.Color.blue(), ending_note=ending_note)
bot.help_command = None

# 錯誤追蹤
@bot.event
async def on_command_error(ctx, error):
    if ctx.command is None: return
    await ctx.invoke(bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=error, user_send=False, ephemeral=True)

#上線通知
@bot.event
async def on_ready():
    # now = time.strftime("%Y/%m/%d %H:%M:%S")
    # game = discord.Game(f"所以說機器人怎麼做... 上線時間: {now}")
    # # discord.Status. (online, idle(閒置), dnd(勿擾), invisible)
    # await bot.change_presence(status=discord.Status.online, activity=game)

    try:
        synced_bot = await bot.tree.sync()
        print(f'Synced {len(synced_bot)} commands.')
    except Exception as e:
        print("出錯 when synced: ", e)

    # user = await bot.fetch_user(KeJC_ID)
    # await user.send("我上線了")
    print('我上線了窩\n')

#讓私訊也能被處理
@bot.event
async def on_message(message):
    # 忽略機器人自己的消息
    if message.author == bot.user:
        return

    # 處理私訊中的指令
    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
    else:
        # 處理伺服器中的指令
        await bot.process_commands(message)

class UpdateStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_status.start()
        self.change_activity.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「UpdateStatus」')

    @tasks.loop(minutes=1)
    async def update_status(self):
        from core.functions import create_basic_embed
        channel = self.bot.get_channel(int(jdata['status_channel']['channel_ID']))
        message = await channel.fetch_message(int(jdata['status_channel']['message_ID']))       
        embed = create_basic_embed(title='Bot狀態', description=':green_circle:')
        embed.set_footer(text='最後更新時間')
        await message.edit(content=None, embed=embed)

    @tasks.loop(hours=1)
    async def change_activity(self):
        try:
            from cmds.AIsTwo.others.decide import ActivitySelector
            from core.functions import thread_pool
            activity = await thread_pool(ActivitySelector.activity_select)
            await self.bot.change_presence(activity=activity)
        except Exception as e:
            print(f'無法更新狀態，原因: {e}')
        
    @update_status.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()

    @change_activity.before_loop
    async def before_change_activity(self):
        await self.bot.wait_until_ready()

async def load_another():
    try:
        await bot.add_cog(UpdateStatus(bot))
        print('嘗試載入UpdateStatus')
    except Exception as e:
        print(f'出錯 When loading extension: {e}')


async def load():
    for filename in os.listdir('./cmds'):
        try:
            if filename.endswith('.py'):
                await bot.load_extension(f'cmds.{filename[:-3]}')
                print(f'嘗試載入cmds.{filename}')
        except Exception as e:
            # traceback.print_exc()
            print(f'出錯 When loading extension: {e}')
    
        
async def main():
    async with bot:
        await load()
        await load_another()
        await bot.start(TOKEN)

asyncio.run(main())