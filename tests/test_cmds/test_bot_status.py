"""`cmds/bot_status.py`：Mongo 資料整理與狀態字串切換。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from discord.ext import commands

from cmds.bot_status import find_top_3_command, handle_bot_status_string
from tests.helpers import last_call


@pytest.fixture
def mock_coll() -> Any:
    async def async_gen():
        yield {
            "_id": "1",
            "type": "custom",
            "name": "TOP_STATUS",
            "data": {"start_time": 1754562468.464611},
        }
        yield {
            "_id": "2",
            "type": "on_command",
            "name": "Command called times",
            "data": {"Load": {"restart": 682}},
            "total_times": 2953,
        }
        yield {
            "_id": "3",
            "type": "on_command",
            "name": "Command called times by a user",
            "data": {"703877871256731678": 2316},
        }

    class MockCursor:
        def __aiter__(self):
            return async_gen()

    coll = MagicMock()
    coll.find.return_value = MockCursor()
    return coll


@pytest.mark.asyncio
async def test_fetch_mongo_data(mock_coll: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from cmds.bot_status import fetch_mongo_data

    monkeypatch.setattr("cmds.bot_status.coll", mock_coll)

    result = await fetch_mongo_data()

    assert result["top_status"]["name"] == "TOP_STATUS"
    assert result["command_called_times"]["name"] == "Command called times"
    assert result["command_called_by_user"]["name"] == "Command called times by a user"


def test_find_top_3_command_ignores_internal_commands() -> None:
    data = {
        "Load": {"restart": 682, "reload": 144, "ping": 12},
        "Other": {"reload_all": 300, "show_players": 200, "avatar": 30},
    }

    assert find_top_3_command(data) == {"ping": 12, "avatar": 30}


def test_find_top_3_command_sorts_and_limits() -> None:
    data = {"a": {"cmd_a": 1, "cmd_b": 50, "cmd_c": 7, "cmd_d": 99}}

    result = find_top_3_command(data)

    assert list(result) == ["cmd_d", "cmd_b", "cmd_c"]


def test_find_top_3_command_merges_sources() -> None:
    data = {"a": {"ping": 5}, "b": {"pong": 9}}

    assert find_top_3_command(data) == {"pong": 9, "ping": 5}


def test_find_top_3_command_later_source_wins() -> None:
    data = {"a": {"ping": 5}, "b": {"ping": 9}}

    assert find_top_3_command(data) == {"ping": 9}


def test_find_top_3_command_filters_non_positive() -> None:
    data = {"a": {"zero": 0, "negative": -3}}

    assert find_top_3_command(data) == {}


def test_find_top_3_command_keeps_tie_order() -> None:
    data = {"a": {"first": 5, "second": 5}}

    assert list(find_top_3_command(data)) == ["first", "second"]


class _FakeLoop:
    def __init__(self, running: bool = False) -> None:
        self.running = running
        self.started = False
        self.cancelled = False

    def is_running(self) -> bool:
        return self.running

    def start(self) -> None:
        self.started = True
        self.running = True

    def cancel(self) -> None:
        self.cancelled = True
        self.running = False


@pytest.mark.asyncio
async def test_operational_starts_activity_loop() -> None:
    loop = _FakeLoop(running=False)
    cog = SimpleNamespace(change_activity=loop)
    bot = MagicMock()
    bot.change_presence = AsyncMock()

    await handle_bot_status_string("operational", cast(commands.Cog, cog), cast(commands.Bot, bot))

    assert loop.started is True
    bot.change_presence.assert_not_awaited()


@pytest.mark.asyncio
async def test_operational_does_not_restart_running_loop() -> None:
    loop = _FakeLoop(running=True)
    cog = SimpleNamespace(change_activity=loop)
    bot = MagicMock()
    bot.change_presence = AsyncMock()

    await handle_bot_status_string("operational", cast(commands.Cog, cog), cast(commands.Bot, bot))

    assert loop.started is False
    bot.change_presence.assert_not_awaited()


@pytest.mark.asyncio
async def test_maintenance_cancels_loop_and_sets_presence() -> None:
    loop = _FakeLoop(running=True)
    cog = SimpleNamespace(change_activity=loop)
    bot = MagicMock()
    bot.change_presence = AsyncMock()

    await handle_bot_status_string("maintenance", cast(commands.Cog, cog), cast(commands.Bot, bot))

    assert loop.cancelled is True
    bot.change_presence.assert_awaited_once()
    activity = last_call(bot.change_presence).kwargs["activity"]
    assert "維護中" in activity.name


@pytest.mark.asyncio
async def test_maintenance_without_running_loop_still_sets_presence() -> None:
    loop = _FakeLoop(running=False)
    cog = SimpleNamespace(change_activity=loop)
    bot = MagicMock()
    bot.change_presence = AsyncMock()

    await handle_bot_status_string("maintenance", cast(commands.Cog, cog), cast(commands.Bot, bot))

    assert loop.cancelled is False
    bot.change_presence.assert_awaited_once()
