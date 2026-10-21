"""`cmds/world_chat.py`：跨頻道同步與世界頻道設定。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from discord import app_commands

from tests.helpers import make_channel, make_guild, make_message, make_user
from tests.helpers import last_call

WORLD_CHANNEL_ID = 2000
OTHER_CHANNEL_IDS = (3001, 3002)


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.world_chat")


@pytest.fixture
def world(module: Any, bot: Any) -> Iterator[Any]:
    cog = module.WorldChat(bot)
    module.WorldChat.channels = {
        "channels": [WORLD_CHANNEL_ID, *OTHER_CHANNEL_IDS],
        "History": [],
    }
    try:
        yield cog
    finally:
        module.WorldChat.channels = None


def _sync_targets(bot: Any, guild: Any) -> dict[int, Any]:
    targets = {channel_id: make_channel(channel_id, guild=guild) for channel_id in OTHER_CHANNEL_IDS}
    bot.get_channel = MagicMock(side_effect=lambda channel_id: targets.get(channel_id))
    return targets


@pytest.mark.asyncio
async def test_bot_message_is_ignored(world: Any, bot: Any) -> None:
    guild = make_guild()
    targets = _sync_targets(bot, guild)
    message = make_message("hi", make_user(bot=True), channel=make_channel(WORLD_CHANNEL_ID, guild=guild), guild=guild)

    await world.on_message(message)

    for channel in targets.values():
        channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_message_outside_world_chat_is_ignored(world: Any, bot: Any) -> None:
    guild = make_guild()
    targets = _sync_targets(bot, guild)
    message = make_message("hi", channel=make_channel(9999, guild=guild), guild=guild)

    await world.on_message(message)

    for channel in targets.values():
        channel.send.assert_not_awaited()


@pytest.mark.xfail(
    strict=True,
    reason="on_message 把 translations 內的 list 直接丟給 load_translated()，"
    "轉發時會 AttributeError 並被 except Exception 吞掉（詳見 I-SEE-ERRORS.md）",
)
@pytest.mark.asyncio
async def test_message_is_forwarded_to_other_channels(
    world: Any, module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guild = make_guild()
    targets = _sync_targets(bot, guild)
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    author = make_user(global_name="Alice")
    message = make_message(
        "hello world",
        author,
        channel=make_channel(WORLD_CHANNEL_ID, guild=guild),
        guild=guild,
    )

    await world.on_message(message)

    for channel in targets.values():
        channel.send.assert_awaited_once()
        embed = last_call(channel.send).kwargs["embed"]
        assert "Alice" in embed.fields[0].name
    history = module.WorldChat.channels["History"]
    assert len(history) == 1
    assert "Alice: hello world" in history[0]
    write_json.assert_called_once()


@pytest.mark.xfail(
    strict=True,
    reason="on_message 把 translations 內的 list 直接丟給 load_translated()，"
    "轉發時會 AttributeError 並被 except Exception 吞掉（詳見 I-SEE-ERRORS.md）",
)
@pytest.mark.asyncio
async def test_image_attachments_are_forwarded_separately(
    world: Any, module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guild = make_guild()
    targets = _sync_targets(bot, guild)
    monkeypatch.setattr(module, "write_json", MagicMock())
    attachment = SimpleNamespace(url="https://cdn.example/a.png", content_type="image/png")
    author = make_user(global_name="Alice")
    message = make_message(
        "",
        author,
        channel=make_channel(WORLD_CHANNEL_ID, guild=guild),
        guild=guild,
        attachments=[attachment],
    )

    await world.on_message(message)

    for channel in targets.values():
        assert channel.send.await_count == 2
        assert channel.send.await_args_list[1].args[0] == attachment.url
    history = module.WorldChat.channels["History"]
    assert attachment.url in history[0]


@pytest.mark.asyncio
async def test_message_history_is_recorded(
    world: Any, module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    guild = make_guild()
    _sync_targets(bot, guild)
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    message = make_message(
        "hello world",
        make_user(global_name="Alice"),
        channel=make_channel(WORLD_CHANNEL_ID, guild=guild),
        guild=guild,
    )

    await world.on_message(message)

    history = module.WorldChat.channels["History"]
    assert len(history) == 1
    assert "Alice: hello world" in history[0]
    write_json.assert_called_once()


@pytest.mark.asyncio
async def test_setworldchannel_adds_channel(
    world: Any, module: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    module.WorldChat.channels = {"channels": [], "History": []}
    ctx = ctx_factory(channel_id=WORLD_CHANNEL_ID)

    await world.setworldchannel.callback(world, ctx, 是否取消=None)

    assert WORLD_CHANNEL_ID in module.WorldChat.channels["channels"]
    ctx.send.assert_awaited_once()
    write_json.assert_called_once()


@pytest.mark.asyncio
async def test_setworldchannel_already_set(
    world: Any, module: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    ctx = ctx_factory(channel_id=WORLD_CHANNEL_ID)

    await world.setworldchannel.callback(world, ctx, 是否取消=None)

    assert module.WorldChat.channels["channels"].count(WORLD_CHANNEL_ID) == 1
    ctx.send.assert_awaited_once()
    write_json.assert_not_called()


@pytest.mark.asyncio
async def test_setworldchannel_cancel(
    world: Any, module: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "write_json", MagicMock())
    ctx = ctx_factory(channel_id=WORLD_CHANNEL_ID)

    await world.setworldchannel.callback(world, ctx, 是否取消=SimpleNamespace(value=2))

    assert WORLD_CHANNEL_ID not in module.WorldChat.channels["channels"]
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_setworldchannel_cancel_not_a_world_channel(
    world: Any, module: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    ctx = ctx_factory(channel_id=9999)

    await world.setworldchannel.callback(world, ctx, 是否取消=SimpleNamespace(value=2))

    ctx.send.assert_awaited_once()
    write_json.assert_not_called()


@pytest.mark.asyncio
async def test_report_bad_image_sends_log(world: Any, bot: Any, ctx_factory: Any) -> None:
    log_channel = make_channel(7777, guild=make_guild())
    bot.fetch_channel = AsyncMock(return_value=log_channel)
    ctx = ctx_factory()

    await world.report.callback(world, ctx, author="Bob", 舉報原因="inappropriate")

    log_channel.send.assert_awaited_once()
    log_message = last_call(log_channel.send).args[0]
    assert "Bob" in log_message
    assert "inappropriate" in log_message
    ctx.send.assert_awaited_once()
