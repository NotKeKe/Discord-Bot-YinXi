"""測試用的假 Discord 物件與小工具。

這裡只放「測試輔助」的東西，不會 import 任何 `cmds.*` 模組，
避免在 collection 階段就觸發需要 event loop 或外部服務的 import。
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Iterable, Sequence
from unittest.mock import AsyncMock, MagicMock

import discord
from discord.ext import commands

TEST_GUILD_ID = 3000
TEST_CHANNEL_ID = 2000
TEST_USER_ID = 1000


class NullAsyncContext:
    """假的 `async with` context manager（給 `ctx.typing()` 之類用）。"""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class RecordingBot:
    """只記錄 `add_cog` 呼叫的假 bot，用來驗證各模組的 `setup()`。

    刻意「不」實作真的 cog 註冊流程，所以 `cog_load()` / `tasks.loop` 都不會被觸發，
    測試因此不會碰到 MongoDB、Redis 或 Discord API。
    """

    def __init__(self) -> None:
        self.added_cogs: list[commands.Cog] = []
        self.cogs: dict[str, commands.Cog] = {}
        self.commands: dict[str, commands.Command[Any, Any, Any]] = {}
        self.guilds: list[discord.Guild] = []
        self.user = None
        self.tree = SimpleNamespace(translator=None)

    async def add_cog(self, cog: commands.Cog, /, *, override: bool = False) -> None:
        self.added_cogs.append(cog)
        self.cogs[type(cog).__name__] = cog


class FakeCursor:
    """模擬 motor 的 `AsyncIOMotorCursor`：支援 `sort()` / `limit()` 鏈式呼叫與 `async for`。"""

    def __init__(self, items: Iterable[Any]) -> None:
        self._items = list(items)

    def sort(self, *args: Any, **kwargs: Any) -> "FakeCursor":
        return self

    def limit(self, count: int) -> "FakeCursor":
        self._items = self._items[:count]
        return self

    def __aiter__(self) -> Any:
        async def generator():
            for item in self._items:
                yield item

        return generator()


class FakeCollection:
    """模擬 motor 的 collection，寫入類方法都是 `AsyncMock`。"""

    def __init__(
        self,
        *,
        docs: Iterable[Any] = (),
        find_one_result: Any = None,
    ) -> None:
        self.docs = list(docs)
        self.find_one = AsyncMock(return_value=find_one_result)
        self.find_one_and_delete = AsyncMock(return_value=find_one_result)
        self.find_one_and_update = AsyncMock(return_value=find_one_result)
        self.insert_one = AsyncMock()
        self.update_one = AsyncMock()
        self.update_many = AsyncMock()
        self.delete_one = AsyncMock()
        self.bulk_write = AsyncMock()

    def find(self, *args: Any, **kwargs: Any) -> FakeCursor:
        return FakeCursor(self.docs)


def make_user(
    user_id: int = TEST_USER_ID,
    *,
    name: str = "tester",
    global_name: str = "Tester",
    bot: bool = False,
) -> Any:
    user = MagicMock(spec=discord.Member)
    user.id = user_id
    user.name = name
    user.global_name = global_name
    user.display_name = global_name
    user.bot = bot
    user.mention = f"<@{user_id}>"
    user.color = discord.Color.blue()
    user.avatar = None
    user.default_avatar = SimpleNamespace(url="https://cdn.discordapp.com/embed/avatars/0.png")
    user.guild_permissions = discord.Permissions.all()
    user.roles = []
    user.send = AsyncMock()
    return user


def make_guild(
    guild_id: int = TEST_GUILD_ID,
    *,
    name: str = "Testing Guild",
    members: Sequence[Any] = (),
    channels: Sequence[Any] = (),
    system_channel: Any = None,
    owner: Any = None,
) -> Any:
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.preferred_locale = discord.Locale.taiwan_chinese
    guild.members = list(members)
    guild.channels = list(channels)
    guild.text_channels = [channel for channel in channels if isinstance(channel, discord.TextChannel)]
    guild.system_channel = system_channel
    guild.owner = owner
    guild.owner_id = owner.id if owner is not None else None
    guild.me = make_user(user_id=999, name="yinxi", global_name="音汐", bot=True)
    guild.icon_url = ""
    guild.get_member = MagicMock(return_value=None)
    guild.get_channel = MagicMock(return_value=None)
    guild.fetch_channel = AsyncMock(return_value=None)
    guild.fetch_member = AsyncMock(return_value=None)
    return guild


def make_channel(
    channel_id: int = TEST_CHANNEL_ID,
    *,
    name: str = "general",
    guild: Any = None,
    history: Iterable[Any] = (),
    read_message_history: bool = True,
) -> Any:
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = channel_id
    channel.name = name
    channel.mention = f"<#{channel_id}>"
    channel.guild = guild
    channel.type = discord.ChannelType.text
    channel.send = AsyncMock()
    channel.typing = MagicMock(side_effect=NullAsyncContext)
    channel.history = MagicMock(return_value=fake_async_iter(history))
    channel.permissions_for = MagicMock(
        return_value=discord.Permissions(
            read_messages=True,
            read_message_history=read_message_history,
            send_messages=True,
            manage_messages=True,
            administrator=True,
        )
    )
    return channel


def make_message(
    content: str = "",
    author: Any = None,
    *,
    channel: Any = None,
    guild: Any = None,
    attachments: Sequence[Any] = (),
    embeds: Sequence[Any] = (),
    message_id: int = 1,
) -> Any:
    message = MagicMock(spec=discord.Message)
    message.id = message_id
    message.content = content
    message.author = author if author is not None else make_user()
    message.channel = channel if channel is not None else make_channel(guild=guild)
    message.guild = guild if guild is not None else getattr(message.channel, "guild", None)
    message.attachments = list(attachments)
    message.embeds = list(embeds)
    message.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    message.add_reaction = AsyncMock()
    message.delete = AsyncMock()
    message.edit = AsyncMock()
    message.reply = AsyncMock()
    return message


def make_interaction(
    *,
    user: Any = None,
    channel: Any = None,
    guild: Any = None,
    locale: str = "zh-TW",
    data: dict[str, Any] | None = None,
    namespace: Any = None,
    message: Any = None,
) -> Any:
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = user if user is not None else make_user()
    interaction.channel = channel if channel is not None else make_channel(guild=guild)
    interaction.guild = guild if guild is not None else interaction.channel.guild
    interaction.locale = discord.Locale(locale)
    interaction.data = dict(data) if data is not None else {}
    interaction.namespace = namespace if namespace is not None else SimpleNamespace()
    interaction.message = message
    interaction.client = MagicMock()
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.edit_message = AsyncMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


def make_ctx(
    bot: Any = None,
    *,
    author: Any = None,
    channel: Any = None,
    guild: Any = None,
    interaction: Any = None,
    guild_id: int = TEST_GUILD_ID,
    channel_id: int = TEST_CHANNEL_ID,
    in_guild: bool = True,
) -> Any:
    """建立 `MagicMock(spec=commands.Context)`。

    注意：`MagicMock(spec=commands.Context)` 會通過 `isinstance(ctx, commands.Context)`，
    所以一定要有 `interaction` 屬性（`None` 代表前綴指令），
    否則 `core.translator.get_translate` 會在 `ctx.interaction` 上炸掉。
    """

    resolved_guild = guild if guild is not None else (make_guild(guild_id) if in_guild else None)
    resolved_channel = channel if channel is not None else make_channel(channel_id, guild=resolved_guild)
    resolved_author = author if author is not None else make_user()

    ctx = MagicMock(spec=commands.Context)
    ctx.bot = bot
    ctx.author = resolved_author
    ctx.channel = resolved_channel
    ctx.guild = resolved_guild
    ctx.message = make_message(channel=resolved_channel, guild=resolved_guild, author=resolved_author)
    ctx.interaction = interaction
    ctx.command = None
    ctx.cog = None
    ctx.args = ()
    ctx.kwargs = {}
    ctx.me = resolved_guild.me if resolved_guild is not None else None
    ctx.send = AsyncMock(return_value=make_message())
    ctx.reply = AsyncMock(return_value=make_message())
    ctx.typing = MagicMock(side_effect=NullAsyncContext)
    return ctx


def fake_async_iter(items: Iterable[Any]) -> Any:
    async def generator():
        for item in items:
            yield item

    return generator()


def cog_classes(module: Any) -> list[type[commands.Cog]]:
    """取得模組內定義的 Cog 子類（排除 import 進來的）。"""

    return [
        value
        for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, commands.Cog) and value.__module__ == module.__name__
    ]


def only_cog_class(module: Any) -> type[commands.Cog]:
    classes = cog_classes(module)
    assert len(classes) == 1, f"{module.__name__} 應該只有一個 Cog，實際: {classes}"
    return classes[0]


def prefix_command_names(cog: commands.Cog) -> set[str]:
    return {str(command.name) for command in cog.get_commands()}


def app_command_names(cog: commands.Cog | type[commands.Cog]) -> set[str]:
    names = set()
    for command in getattr(cog, "__cog_app_commands__", []):
        name = getattr(command, "name", None)
        names.add(str(getattr(name, "message", name)))
    return names


def listener_names(cog: commands.Cog | type[commands.Cog]) -> set[str]:
    return {name for name, _ in getattr(cog, "__cog_listeners__", [])}


def shutdown_play4_queue() -> None:
    """收掉 `cmds.music_bot.play4.utils.QUEUE` 的 worker tasks。

    `cmds.sub_yt` 在 import 時會連帶 import `cmds.music_bot.play4.utils`，
    而它會在 module 層級建立 `MyPriorityQueue()`，直接 `asyncio.create_task()`
    出 `os.cpu_count()` 個 worker。測試用不到這些 worker，
    留在 event loop 上只會在收尾時產生 pending task 警告。
    """

    play4_utils = sys.modules.get("cmds.music_bot.play4.utils")
    queue = getattr(play4_utils, "QUEUE", None)
    for worker_task in getattr(queue, "workers", None) or []:
        worker_task.cancel()


def import_cmds_module(name: str) -> Any:
    """在有 running loop 的 async 測試內 import `cmds.*`，並收拾 import 副作用。"""

    module = importlib.import_module(name)
    shutdown_play4_queue()
    return module


def last_call(mock: Any) -> Any:
    """取得 `AsyncMock` 最後一次被 await 的參數。

    `unittest.mock` 的靜態型別是 `_Call | None`，直接取 `.await_args.args`
    會被型別檢查器擋下來；這個 helper 順便斷言「真的有被呼叫」。
    """

    call = mock.await_args
    assert call is not None, "預期這個 mock 有被 await，但沒有"
    return call
