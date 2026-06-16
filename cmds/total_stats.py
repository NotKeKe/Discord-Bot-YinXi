"""
這是用來記錄各種數據的 Cog，最終會將資料存在 MongoDB
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import logging
from datetime import datetime, timezone, timedelta
import psutil
import platform
import os
from pymongo import UpdateOne

from core.classes import Cog_Extension
from core.functions import (
    mongo_db_client,
    create_basic_embed,
    is_testing_guild,
    secondToReadable,
)
from core.translator import locale_str, load_translated, get_translate

logger = logging.getLogger(__name__)

db_key = "bot_collect_stats"
db = mongo_db_client[db_key]
collection = db["stats"]


def now_utc8_iso() -> str:
    """產生 UTC+8 時區的 ISO 格式時間字串"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat()


def cog_name_of(ctx: commands.Context) -> str:
    """取得 ctx 對應 cog 的名稱（fallback: 'Unknown'）"""
    return ctx.cog.__cog_name__ if ctx.cog else "Unknown"


class BotStats(Cog_Extension):
    async def cog_load(self):
        print(f"已載入「{__name__}」")

        if not (await collection.find_one({"type": "custom", "name": "TOP_STATUS"})):
            await collection.insert_one(
                {
                    "type": "custom",
                    "name": "TOP_STATUS",
                    "data": {"start_time": datetime.now().timestamp()},
                }
            )

    @commands.Cog.listener()
    async def on_ready(self):
        await collection.find_one_and_update(
            {"type": "on_ready"},
            {
                "$inc": {"data.bot_online_times": 1},
                "$set": {"last_update": now_utc8_iso()},
                "$setOnInsert": {
                    "type": "on_ready",
                    "name": "Bot ready times",
                },
            },
            upsert=True,
        )

    # command
    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if not ctx.command:
            return

        ops: list[UpdateOne] = [
            UpdateOne(
                {"type": "on_command", "name": "Command called times"},
                {
                    "$inc": {
                        "total_times": 1,
                        f"data.{cog_name_of(ctx)}.{ctx.command.name}": 1,
                    },
                    "$set": {"last_update": now_utc8_iso()},
                    "$setOnInsert": {
                        "type": "on_command",
                        "name": "Command called times",
                    },
                },
                upsert=True,
            ),
            UpdateOne(
                {"type": "on_command", "name": "Command called times by a user"},
                {
                    "$inc": {f"data.{ctx.author.id}": 1},
                    "$set": {"last_update": now_utc8_iso()},
                    "$setOnInsert": {
                        "type": "on_command",
                        "name": "Command called times by a user",
                    },
                },
                upsert=True,
            ),
        ]

        if ctx.guild:
            ops.append(
                UpdateOne(
                    {"type": "on_command", "name": "Command called times by a guild"},
                    {
                        "$inc": {f"data.{ctx.guild.id}": 1},
                        "$set": {"last_update": now_utc8_iso()},
                        "$setOnInsert": {
                            "type": "on_command",
                            "name": "Command called times by a guild",
                        },
                    },
                    upsert=True,
                )
            )

        await collection.bulk_write(ops, ordered=False)

    async def on_any_command_completion(self, ctx: commands.Context):
        await collection.find_one_and_update(
            {
                "type": "on_command_completion, on_app_command_completion",
                "name": "Completed command times",
            },
            {
                "$inc": {"data.total_times": 1},
                "$set": {"last_update": now_utc8_iso()},
                "$setOnInsert": {
                    "type": "on_command_completion, on_app_command_completion",
                    "name": "Completed command times",
                },
            },
            upsert=True,
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        await self.on_any_command_completion(ctx)

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, inter: Interaction, command: app_commands.Command
    ):
        await self.on_any_command_completion((await self.bot.get_context(inter)))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if not ctx.command:
            return
            
        await collection.find_one_and_update(
            {"type": "on_command_error"},
            {
                "$inc": {
                    "data.total_times": 1,
                    f"data.commands.{ctx.command.name}": 1,
                },
                "$set": {"last_update": now_utc8_iso()},
                "$setOnInsert": {
                    "type": "on_command_error",
                    "name": "Command error times",
                },
            },
            upsert=True,
        )

    @app_commands.command(
        name=locale_str("bot_stats"), description=locale_str("bot_stats")
    )
    async def sum_stats(self, inter: Interaction):
        await inter.response.defer(thinking=True)

        start_time = (
            await collection.find_one({"type": "custom", "name": "TOP_STATUS"})
        ) or {}
        on_ready = (await collection.find_one({"type": "on_ready"})) or {}
        on_command = (
            await collection.find_one(
                {"type": "on_command", "name": "Command called times"}
            )
        ) or {}
        on_command_completion = (
            await collection.find_one(
                {
                    "type": "on_command_completion, on_app_command_completion",
                    "name": "Completed command times",
                }
            )
        ) or {}
        on_command_error = (
            await collection.find_one({"type": "on_command_error"})
        ) or {}

        """i18n"""
        eb_obj = load_translated(await get_translate("embed_bot_stats", inter))[0]
        author = eb_obj.get("author")
        fields = eb_obj.get("fields")
        start_time_text = fields[0].get("name")
        start_count_text = fields[1].get("name")
        command_call_text = fields[2].get("name")
        command_complete_text = fields[3].get("name")
        command_error_text = fields[4].get("name")
        footer = eb_obj.get("footer")
        """"""

        eb = create_basic_embed(功能=author, time=False)
        eb.add_field(
            name=start_count_text,
            value=on_ready.get("data", {}).get("bot_online_times"),
        )
        eb.add_field(name=command_call_text, value=on_command.get("total_times"))
        eb.add_field(
            name=command_complete_text,
            value=on_command_completion.get("data", {}).get("total_times"),
        )
        eb.add_field(
            name=command_error_text,
            value=on_command_error.get("data", {}).get("total_times"),
        )

        eb.set_footer(text=footer)
        eb.timestamp = datetime.fromtimestamp(
            start_time.get("data", {}).get("start_time")
        )

        await inter.followup.send(embed=eb)

    @commands.hybrid_command(
        name=locale_str("machine_stats"), description=locale_str("machine_stats")
    )
    async def machine_stats(self, ctx: commands.Context):
        await ctx.defer()
        from newbot2 import start_time

        discord_version = discord.__version__
        process = psutil.Process(os.getpid())

        # 記憶體
        mem_info = process.memory_info()
        mem_used_mb = mem_info.rss / (1024 * 1024)  # 轉成 MB
        mem_total_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)  # 轉成 GB

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)  # CPU 使用率 in 1 second

        # 系統名稱
        os_name = platform.system()

        """i18n"""
        eb_obj = load_translated(await get_translate("embed_machine_stats", ctx))[0]
        title = eb_obj.get("title")
        fields = eb_obj.get("fields")
        field_1 = fields[0]
        bot_info_name = field_1.get("name")
        bot_info_value = field_1.get("value").format(
            discord_version=discord_version,
            time=secondToReadable(datetime.now().timestamp() - start_time),
        )
        field_2 = fields[1]
        system_info_name = field_2.get("name")
        system_info_value = field_2.get("value").format(
            mem_mb=f"{mem_used_mb:.2f}",
            mem_gb=f"{mem_total_gb:.1f}",
            cpu_percent=f"{cpu_percent:.1f}",
            os_name=os_name,
        )
        footer = eb_obj.get("footer")
        """"""

        eb = create_basic_embed(title, color=discord.Color.random())
        eb.add_field(name=bot_info_name, value=bot_info_value, inline=False)
        eb.add_field(name=system_info_name, value=system_info_value, inline=False)
        eb.set_footer(text=footer)

        await ctx.send(embed=eb)

    @commands.command(name="num_guilds")
    @is_testing_guild()
    async def num_guilds(self, ctx: commands.Context):
        await ctx.send(len(self.bot.guilds))
        await ctx.send(", ".join([guild.name for guild in self.bot.guilds]))


async def setup(bot):
    await bot.add_cog(BotStats(bot))
