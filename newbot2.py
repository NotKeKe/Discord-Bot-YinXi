import discord
from discord.ext import commands, tasks
from pretty_help import PrettyHelp
import json
import os
from dotenv import load_dotenv
import asyncio
import time
import traceback
import logging
import sys
# import gc

from core.functions import math_round, current_time, testing_guildID, create_basic_embed, thread_pool
from core.translator import i18n, MockInteraction
from core.setup_log import setup_logging, StreamToLogger
from cmds.AIsTwo.others.decide import ActivitySelector
from core.classes import set_bot

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')
online_time = None
start_time = time.time()

# log setup
setup_logging()
root_logger = logging.getLogger()
sys.stdout = StreamToLogger(root_logger, logging.INFO)
sys.stderr = StreamToLogger(root_logger, logging.ERROR)
root_logger.info('輸出已被重導向至 `/logs`')
# gc.set_debug(gc.DEBUG_LEAK)

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
set_bot(bot)
# tree = app_bot.CommandTree(bot)

# Bot's help default command
ending_note = "這是 {ctx.bot.user.name} 的commands help\n輸入 {help.clean_prefix}{help.invoked_with} 或是 [helping 來尋求幫助"
# bot.help_command = PrettyHelp(color=discord.Color.blue(), ending_note=ending_note)
bot.help_command = None

@bot.event
async def setup_hook():
    try:
        translator = i18n()
        await bot.tree.set_translator(translator)
        synced_bot_guild = await bot.tree.sync(guild=discord.Object(id=testing_guildID))
        synced_bot = await bot.tree.sync()
        print(f'Synced {len(synced_bot + synced_bot_guild)} commands.')
    except Exception as e:
        print("出錯 when synced: ", e)

    # user = await bot.fetch_user(KeJC_ID)
    # await user.send("我上線了")
    global online_time
    online_time = current_time()
    
@bot.before_invoke
async def before_invoke(ctx: commands.Context):
    """
    在任何指令執行前被呼叫，用於填充 ctx.interaction。
    """
    if ctx.interaction is None:  
        try:
            ctx.interaction = MockInteraction(ctx)
        except:
            traceback.print_exception()

# 錯誤追蹤
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if ctx.command is None: return
    await ctx.invoke(bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=error, user_send=False, ephemeral=True)

#上線通知
@bot.event
async def on_ready():
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

    @commands.command()
    async def 改變狀態(self, ctx: commands.Context, activity_code: int = 1):
        async with ctx.typing():
            try:
                if ctx.author.id != KeJC_ID: return
                # activity changing
                # from cmds.AIsTwo.others.decide import ActivitySelector
                activity = await thread_pool(ActivitySelector.activity_select, activity_code)
                await self.bot.change_presence(activity=activity)

                # user
                user = await ctx.guild.fetch_member(self.bot.user.id) or ctx.guild.get_member(self.bot.user.id)
                if not user: return await ctx.send('Cannot get user', ephemeral=True)

                # get activity name
                if not user.activity: 
                    await ctx.send("Cannot fetch user's activity, trying to `get` bot", ephemeral=True)
                    user = ctx.guild.get_member(self.bot.user.id)
                    if not user.activity: return await ctx.send("Cannot get user's activity", ephemeral=True)

                await ctx.send(f'Successfully changed user activity to `{user.activity.name}`', ephemeral=True)
            finally:
                if ctx.guild.me.guild_permissions.manage_messages:
                    await ctx.message.delete()
            
    @tasks.loop(minutes=1)
    async def update_status(self):
        channel = self.bot.get_channel(int(jdata['status_channel']['channel_ID']))
        if not channel: return root_logger.error(f'Cannot find channel ({channel=}): ', exc_info=True)
        message = await channel.fetch_message(int(jdata['status_channel']['message_ID']))       
        embed = create_basic_embed(title='Bot狀態', description=':green_circle:')
        embed.add_field(name='上線時間', value=online_time)
        embed.set_footer(text='最後更新時間')
        await message.edit(content=None, embed=embed)

    @tasks.loop(hours=1)
    async def change_activity(self):
        try:
            # from cmds.AIsTwo.others.decide import ActivitySelector
            activity = await thread_pool(ActivitySelector.activity_select)
            await self.bot.change_presence(activity=activity)
        except Exception as e:
            print(f'無法更新狀態，原因: {e}')
        
    @update_status.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1)

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
        now = time.time()
        try:
            if filename.endswith('.py'):
                await bot.load_extension(f'cmds.{filename[:-3]}')
                print(f'嘗試載入cmds.{filename} (cost: {math_round(time.time()-now, 2)})')
        except Exception as e:
            # traceback.print_exc()
            root_logger.warning(f'出錯 When loading extension: {e} (cost: {math_round(time.time()-now, 2)})', exc_info=True)
    
        
async def main():
    async with bot:
        await load()
        await load_another()
        print(f'開啟共花費了: {math_round(time.time() - start_time, 2)}')
        await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        from core.functions import mongo_db_client
        if mongo_db_client:
            mongo_db_client.close()