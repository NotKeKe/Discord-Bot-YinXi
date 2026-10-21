"""`cmds/join_leave_guild.py`：成員加入／離開通知與頻道自動完成。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import make_channel, make_ctx, make_guild, make_user
from tests.helpers import last_call


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.join_leave_guild")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    module.OnJoinLeave.data = {}
    return module.OnJoinLeave(bot)


@pytest.mark.asyncio
async def test_channel_autocomplete_without_guild(module: Any) -> None:
    interaction = SimpleNamespace(guild=None)

    assert await module.channel_autocomplete(interaction, "") == []


@pytest.mark.asyncio
async def test_channel_autocomplete_filters_and_sorts(module: Any) -> None:
    guild = SimpleNamespace(
        channels=[SimpleNamespace(name="general"), SimpleNamespace(name="gaming"), SimpleNamespace(name="random")]
    )
    interaction = SimpleNamespace(guild=guild)

    choices = await module.channel_autocomplete(interaction, "ga")

    assert [choice.name for choice in choices] == ["gaming"]


@pytest.mark.asyncio
async def test_channel_autocomplete_limits_to_25(module: Any) -> None:
    guild = SimpleNamespace(channels=[SimpleNamespace(name=f"channel-{index:02d}") for index in range(40)])
    interaction = SimpleNamespace(guild=guild)

    choices = await module.channel_autocomplete(interaction, "")

    assert len(choices) == 25


@pytest.mark.asyncio
async def test_channel_autocomplete_returns_empty_on_error(module: Any) -> None:
    class BrokenGuild:
        @property
        def channels(self):
            raise RuntimeError("boom")

    interaction = SimpleNamespace(guild=BrokenGuild())

    assert await module.channel_autocomplete(interaction, "") == []


def test_init_data_reads_json(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    module.OnJoinLeave.data = None
    monkeypatch.setattr(module, "read_json", MagicMock(return_value={"1": {"joinChannel": 2}}))

    module.OnJoinLeave.init_data()

    assert module.OnJoinLeave.data == {"1": {"joinChannel": 2}}


def test_write_data_persists(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    module.OnJoinLeave.data = {"1": {"joinChannel": 2}}

    module.OnJoinLeave.write_data()

    write_json.assert_called_once_with({"1": {"joinChannel": 2}}, module.PATH)


@pytest.mark.asyncio
async def test_set_join_leave_requires_guild(module: Any, cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot, in_guild=False)

    await cog.set_join_leave_message.callback(cog, ctx)

    ctx.send.assert_awaited_once_with("You are not in a server.")


@pytest.mark.asyncio
async def test_set_join_leave_prompts_before_overwrite(
    module: Any, cog: Any, bot: Any, ctx_factory: Any
) -> None:
    module.OnJoinLeave.data = {"3000": {"joinChannel": 1, "leaveChannel": 2}}
    ctx = ctx_factory()

    await cog.set_join_leave_message.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    view = last_call(ctx.send).kwargs["view"]
    assert len(view.children) == 2


@pytest.mark.asyncio
async def test_set_join_leave_creates_configuration(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    guild = make_guild()
    join_channel = make_channel(501, name="join", guild=guild)
    leave_channel = make_channel(502, name="leave", guild=guild)
    system_channel = make_channel(500, name="system", guild=guild)
    guild.channels = [join_channel, leave_channel, system_channel]
    guild.system_channel = join_channel
    ctx = ctx_factory(guild=guild)

    await cog.set_join_leave_message.callback(cog, ctx, join_channel="join", leave_channel="leave")

    assert module.OnJoinLeave.data[str(guild.id)] == {"joinChannel": 501, "leaveChannel": 502}
    write_json.assert_called_once()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_member_join_message(module: Any, cog: Any, bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    guild = make_guild()
    channel = make_channel(501, guild=guild)
    bot.fetch_channel = AsyncMock(return_value=channel)
    module.OnJoinLeave.data = {str(guild.id): {"joinChannel": 501, "leaveChannel": 502}}
    member = SimpleNamespace(id=1, name="Alice", guild=guild)

    await cog.on_member_join(member)

    channel.send.assert_awaited_once()
    assert "Alice" in last_call(channel.send).args[0]


@pytest.mark.asyncio
async def test_member_remove_message(module: Any, cog: Any, bot: Any) -> None:
    guild = make_guild()
    channel = make_channel(502, guild=guild)
    bot.fetch_channel = AsyncMock(return_value=channel)
    module.OnJoinLeave.data = {str(guild.id): {"joinChannel": 501, "leaveChannel": 502}}
    member = SimpleNamespace(id=1, name="Alice", guild=guild)

    await cog.on_member_remove(member)

    channel.send.assert_awaited_once()
    assert "Alice" in last_call(channel.send).args[0]


@pytest.mark.asyncio
async def test_member_join_ignores_unconfigured_guild(module: Any, cog: Any, bot: Any) -> None:
    guild = make_guild()
    bot.fetch_channel = AsyncMock()
    module.OnJoinLeave.data = {}
    member = SimpleNamespace(id=1, name="Alice", guild=guild)

    await cog.on_member_join(member)

    bot.fetch_channel.assert_not_awaited()
