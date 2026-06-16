import logging
import platform
import time
from datetime import datetime, timedelta, timezone

import discord
import orjson
import psutil
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks

from core.functions import is_KeJC, redis_client, testing_guildID, START_TIME
from core.mongodb import MongoDB_DB
from core.translator import locale_str

logger = logging.getLogger(__name__)

db = MongoDB_DB.bot_collect_stats
coll = db["stats"]


async def fetch_mongo_data() -> dict:
    cursor = coll.find(
        {
            "$or": [
                {"type": "custom", "name": "TOP_STATUS"},
                {"type": "on_command", "name": "Command called times"},
                {"type": "on_command", "name": "Command called times by a user"},
                {"type": "custom", "name": "Status String"},
            ]
        }
    )

    results = {doc["name"]: doc async for doc in cursor}

    return {
        "top_status": results.get("TOP_STATUS"),
        "command_called_times": results.get("Command called times"),
        "command_called_by_user": results.get("Command called times by a user"),
        "status_string": results.get("Status String"),
    }


def find_top_3_command(data: dict[str, dict[str, int]]) -> dict[str, int]:
    # 這裡列舉了幾個我常用 但不該被紀錄的 command name
    ignore_cmd_names = [
        "restart",
        "reload",
        "reload_all",
        "show_players",
        "curr_player",
        "clear_players",
    ]

    list_commands = data.values()  # [{'restart': 681, 'reload': 144}]
    _commands = {
        k: v for item in list_commands for k, v in item.items()
    }  # {'restart': 981, 'reload': 144, 'reload2': 155}

    _commands = filter(
        lambda x: x[0] not in ignore_cmd_names and x[1] > 0, _commands.items()
    )
    top_three = sorted(_commands, key=lambda x: x[1], reverse=True)[:3]

    return {k: v for k, v in top_three}


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        logger.info(f"已載入「{__name__}」")

        d = await coll.find_one({"type": "custom", "name": "Status String"})
        if not d:
            await coll.insert_one(
                {
                    "type": "custom",
                    "name": "Status String",
                    "data": {
                        "api": "operational",
                        "bot": "operational",
                        "update_time": datetime.now(timezone.utc)
                        .astimezone()
                        .isoformat(),
                    },
                }
            )

        self.update_bot_status.start()

    async def cog_unload(self):
        self.update_bot_status.cancel()

    @commands.hybrid_command(
        name=locale_str("change_status_str"),
        description=locale_str("change_status_str"),
    )
    @app_commands.guilds(discord.Object(id=testing_guildID))
    @app_commands.choices(
        where=[
            Choice(name="bot", value="bot"),
            Choice(name="api_server", value="api_server"),
        ],
        status=[
            Choice(name="🟢 Operational", value="operational"),  # 正常運作
            Choice(name="🛠️ Maintenance", value="maintenance"),  # 維修中
            Choice(name="🔴 Offline", value="offline"),  # 離線
        ],
    )
    async def change_status(self, ctx: commands.Context, where: str, *, status: str):
        if not is_KeJC(ctx.author.id):
            return

        async with ctx.typing(ephemeral=True):
            ori_data: dict = await coll.find_one_and_update(
                {"type": "custom", "name": "Status String"},
                {
                    "$set": {
                        f"data.{where}": status,
                        "data.update_time": datetime.now(timezone.utc)
                        .astimezone()
                        .isoformat(),
                    }
                },
                upsert=True,
            )

            ori_status: str = ori_data.get("data", {}).get(where, "Unknown")
            await ctx.send(
                f"Done.\nChanged `{where}` status from `{ori_status}` to `{status}`",
                ephemeral=True,
            )

    @tasks.loop(seconds=30)
    async def update_bot_status(self):
        await self.bot.wait_until_ready()

        # pre fetch data
        mongo_data = await fetch_mongo_data()

        # system
        system = {
            "python_version": platform.python_version(),
            "discord_py_version": discord.__version__,
            "uptime": round(time.time() - START_TIME, 2),
            "current_time": datetime.now(timezone.utc).astimezone().isoformat(),
        }

        # bot
        bot = {
            "guild_count": len(self.bot.guilds),
            "user_count": len(mongo_data["command_called_by_user"]["data"]),
            "voice_connections": len(self.bot.voice_clients),
            "latency_ms": round(self.bot.latency * 1000, 2),
        }

        # command
        command_called_times_data = mongo_data["command_called_times"]["data"]
        top_3_command = find_top_3_command(command_called_times_data)
        total_times: int = mongo_data["command_called_times"]["total_times"]
        command = {
            "top_3_command": orjson.dumps(top_3_command).decode("utf-8"),
            "command_called_total_times": total_times,
            "command_record_from": datetime.fromtimestamp(
                mongo_data["top_status"]["data"]["start_time"]
            )
            .astimezone(timezone(timedelta(hours=8)))
            .isoformat(),
        }

        # status str
        status_str_data: dict = mongo_data.get("status_string", {})
        status_str_inner: dict = status_str_data.get("data", {})

        status_str = {
            "api": status_str_inner.get("api", "Unknown"),
            "bot": status_str_inner.get("bot", "Unknown"),
            "status_str_last_update": status_str_data.get(
                "last_update", "Unknown"
            ),  # isoformat utc+8
        }

        # 整合進 status
        status = {}
        status.update(system)
        status.update(bot)
        status.update(command)
        status.update(status_str)

        await redis_client.hset("bot_status", mapping=status)  # type: ignore


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
