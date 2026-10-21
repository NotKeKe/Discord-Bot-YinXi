"""`cmds/total_stats.py`：指令統計與機器狀態。"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import FakeCollection, make_ctx, make_interaction
from tests.helpers import last_call


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.total_stats")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    """`bot` fixture 負責設定 `core.classes` 的 global bot（get_translate 需要）。"""

    fake = MagicMock()
    fake.guilds = [SimpleNamespace(name="Guild A"), SimpleNamespace(name="Guild B")]
    return module.BotStats(fake)


def test_now_utc8_iso(module: Any) -> None:
    value = module.now_utc8_iso()

    parsed = datetime.fromisoformat(value)

    assert parsed.utcoffset() == timedelta(hours=8)


def test_cog_name_of_with_cog(module: Any) -> None:
    ctx = SimpleNamespace(cog=SimpleNamespace(__cog_name__="Main"))

    assert module.cog_name_of(ctx) == "Main"


def test_cog_name_of_without_cog(module: Any) -> None:
    assert module.cog_name_of(SimpleNamespace(cog=None)) == "Unknown"


@pytest.mark.asyncio
async def test_on_command_records_guild(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)
    ctx = SimpleNamespace(
        command=SimpleNamespace(name="ping"),
        author=SimpleNamespace(id=111),
        guild=SimpleNamespace(id=222),
        cog=SimpleNamespace(__cog_name__="Main"),
    )

    await cog.on_command(ctx)

    ops = last_call(collection.bulk_write).args[0]
    assert len(ops) == 3
    assert last_call(collection.bulk_write).kwargs["ordered"] is False


@pytest.mark.asyncio
async def test_on_command_without_guild(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)
    ctx = SimpleNamespace(
        command=SimpleNamespace(name="ping"),
        author=SimpleNamespace(id=111),
        guild=None,
        cog=None,
    )

    await cog.on_command(ctx)

    ops = last_call(collection.bulk_write).args[0]
    assert len(ops) == 2


@pytest.mark.asyncio
async def test_on_command_ignores_missing_command(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    await cog.on_command(SimpleNamespace(command=None))

    collection.bulk_write.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_command_error_ignores_missing_command(
    module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    await cog.on_command_error(SimpleNamespace(command=None), Exception("boom"))

    collection.find_one_and_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_machine_stats_builds_embed(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_psutil = SimpleNamespace(
        Process=lambda pid: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=100 * 1024 * 1024)),
        virtual_memory=lambda: SimpleNamespace(total=8 * 1024**3),
        cpu_percent=lambda interval: 12.5,
    )
    monkeypatch.setattr(module, "psutil", fake_psutil)
    ctx = make_ctx()
    ctx.defer = AsyncMock()

    await cog.machine_stats.callback(cog, ctx)

    ctx.defer.assert_awaited_once()
    embed = last_call(ctx.send).kwargs["embed"]
    assert len(embed.fields) == 2
    assert "12.5" in embed.fields[1].value
    assert embed.footer.text


@pytest.mark.asyncio
async def test_num_guilds(module: Any, cog: Any) -> None:
    ctx = make_ctx()

    await cog.num_guilds.callback(cog, ctx)

    assert ctx.send.await_count == 2
    assert ctx.send.await_args_list[0].args[0] == 2
    assert "Guild A" in ctx.send.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_bot_stats_embed(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    collection = FakeCollection()
    collection.find_one = AsyncMock(
        side_effect=[
            {"data": {"start_time": 1700000000}},
            {"data": {"bot_online_times": 3}},
            {"total_times": 10},
            {"data": {"total_times": 8}},
            {"data": {"total_times": 2}},
        ]
    )
    monkeypatch.setattr(module, "collection", collection)
    interaction = make_interaction()

    await cog.sum_stats.callback(cog, interaction)

    interaction.response.defer.assert_awaited_once()
    embed = last_call(interaction.followup.send).kwargs["embed"]
    assert len(embed.fields) == 4
    assert str(embed.fields[0].value) == "3"


@pytest.mark.asyncio
async def test_on_any_command_completion(module: Any, cog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    await cog.on_any_command_completion(SimpleNamespace())

    collection.find_one_and_update.assert_awaited_once()
    assert last_call(collection.find_one_and_update).kwargs["upsert"] is True
