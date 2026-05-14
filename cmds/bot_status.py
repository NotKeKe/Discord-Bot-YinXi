import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone
import psutil
import platform
import time

from core.functions import redis_client, mongo_db_client, is_KeJC, testing_guildID
from core.mongodb import MongoDB_DB
from core.translator import locale_str

logger = logging.getLogger(__name__)

db = MongoDB_DB.bot_collect_stats
coll = db['stats']

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        logger.info(f'已載入「{__name__}」')

        d = await coll.find_one({'type': 'status_str'})
        if not d:
            await coll.insert_one({
                'type': 'status_str', 
                'api': 'operational', 
                'bot': 'operational', 
                'update_time': datetime.now(timezone.utc).astimezone().isoformat()
            })

        self.update_bot_status.start()

    async def cog_unload(self):
        self.update_bot_status.cancel()


    @commands.hybrid_command(name=locale_str('change_status_str'), description=locale_str('change_status_str'))
    @app_commands.guilds(discord.Object(id=testing_guildID))
    @app_commands.choices(
        where=[
            Choice(name='bot', value='bot'),
            Choice(name='api_server', value='api_server'),
        ],
        status=[
            Choice(name='🟢 Operational', value='operational'), # 正常運作
            Choice(name='🛠️ Maintenance', value='maintenance'), # 維修中
            Choice(name='🔴 Offline', value='offline'), # 離線
        ]
    )
    async def change_status(self, ctx: commands.Context, where: str, *, status: str):
        if not is_KeJC(ctx.author.id): return

        async with ctx.typing(ephemeral=True):
            await coll.update_one(
                {'type': 'status_str'}, 
                {'$set': {
                    where: status, 
                    'update_time': datetime.now(timezone.utc).astimezone().isoformat()
                }}, 
                upsert=True
            )

            await ctx.send('Done', ephemeral=True)

    @tasks.loop(seconds=30)
    async def update_bot_status(self):
        await self.bot.wait_until_ready()

        # system
        system = {
            'python_version': platform.python_version(),
            'discord_py_version': discord.__version__,
            'uptime': round(time.time() - psutil.Process().create_time(), 2),
            'current_time': datetime.now(timezone.utc).astimezone().isoformat(),
        }

        # bot
        bot = {
            'guild_count': len(self.bot.guilds),
            'user_count': len(self.bot.users), # how much users i can see
            'voice_connections': len(self.bot.voice_clients),
            'latency_ms': round(self.bot.latency * 1000, 2),
        }

        # command
        command_call_time_data: dict = await coll.find_one({'type': 'on_command_completion'}) or {}
        record_from_data: dict = await coll.find_one({'type': 'TOP_STATS'}) or {}

        command_call_time: int = command_call_time_data.get('total_times', -1)
        record_from = datetime.fromtimestamp(record_from_data.get('start_time', -1))

        command = {
            'command_call_time': command_call_time,
            'command_record_from': record_from.astimezone().isoformat(),
        }

        # status str
        status_str_data: dict = await coll.find_one({'type': 'status_str'}) or {}

        status_str = {
            'api': status_str_data.get('api', 'Unknown'),
            'bot': status_str_data.get('bot', 'Unknown'),
            'status_str_update_time': status_str_data.get('update_time', 'Unknown'),
        }

        # 整合進 status
        status = {}
        status.update(system)
        status.update(bot)
        status.update(command)
        status.update(status_str)

        await redis_client.hset('bot_status', mapping=status) # type: ignore




async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))