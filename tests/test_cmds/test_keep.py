"""`cmds/keep.py`：提醒事項的建立 / 刪除 / 查詢。"""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from tests.helpers import FakeCollection, make_ctx, make_interaction
from tests.helpers import last_call


class FakeDB:
    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def __getitem__(self, key: str) -> Any:
        return self.collection


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    mod = importlib.import_module("cmds.keep")
    monkeypatch.setattr(mod, "_KeepUtils", mod._KeepUtils)
    return mod


@pytest.fixture
def keep(module: Any, bot: Any) -> Any:
    return module.Keep(bot)


@pytest.fixture
def collection(module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch) -> FakeCollection:
    """`bot` fixture 設定 global bot，讓 get_translate 有 translator 可用。"""

    coll = FakeCollection()
    monkeypatch.setattr(module, "DB", FakeDB(coll))
    monkeypatch.setattr(module, "reminder_tasks", {})
    return coll


@pytest.mark.parametrize(
    "freq_str,freq_int,expected",
    [
        ("minutely", 5, datetime(2026, 1, 1, 0, 5)),
        ("hourly", 2, datetime(2026, 1, 1, 2, 0)),
        ("daily", 3, datetime(2026, 1, 4, 0, 0)),
        ("weekly", 1, datetime(2026, 1, 8, 0, 0)),
        ("monthly", 1, datetime(2026, 2, 1, 0, 0)),
        ("yearly", 1, datetime(2027, 1, 1, 0, 0)),
    ],
)
def test_next_send_at(module: Any, freq_str: str, freq_int: int, expected: datetime) -> None:
    assert module._KeepUtils.next_send_at(datetime(2026, 1, 1), freq_str, freq_int) == expected


def test_next_send_at_month_end(module: Any) -> None:
    assert module._KeepUtils.next_send_at(datetime(2026, 1, 31), "monthly", 1) == datetime(2026, 2, 28)


def test_next_send_at_unknown_frequency(module: Any) -> None:
    with pytest.raises(ValueError):
        module._KeepUtils.next_send_at(datetime(2026, 1, 1), "sometimes", 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_time,freq_str,freq_int",
    [
        ("not-a-date", None, None),
        ("2000-01-01 00:00", None, None),
        ("9999-01-01 00:00", None, None),
        ("2099-01-01 00:00", "daily", 0),
        ("2099-01-01 00:00", "yearly", 100000),
    ],
)
async def test_create_rejects_invalid_input(
    module: Any, collection: FakeCollection, raw_time: str, freq_str: str | None, freq_int: int | None
) -> None:
    interaction = make_interaction()

    await module._KeepUtils.create(collection, interaction, "test event", raw_time, freq_str, freq_int)

    collection.insert_one.assert_not_awaited()
    interaction.followup.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_reports_forbidden_dm(
    module: Any, collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeForbidden(Exception):
        pass

    monkeypatch.setattr(module, "dc_errors", type("Errors", (), {"Forbidden": FakeForbidden}))
    interaction = make_interaction()
    interaction.user.send = AsyncMock(side_effect=FakeForbidden())

    await module._KeepUtils.create(collection, interaction, "test event", "2099-01-01 00:00")

    collection.insert_one.assert_not_awaited()
    interaction.followup.send.assert_awaited_once()
    assert last_call(interaction.followup.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_create_stores_reminder(
    module: Any, collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule = MagicMock()
    monkeypatch.setattr(module._KeepUtils, "schedule", schedule)
    interaction = make_interaction()

    await module._KeepUtils.create(collection, interaction, "buy milk", "2099-01-01 00:00")

    doc = last_call(collection.insert_one).args[0]
    assert doc["event"] == "buy milk"
    assert doc["channelID"] == interaction.channel.id
    assert len(doc["uuid"]) == 36
    assert doc["sendAt"] > datetime.now().timestamp()
    schedule.assert_called_once()
    embed = last_call(interaction.followup.send).kwargs["embed"]
    assert embed.description == "**buy milk**"


@pytest.mark.asyncio
async def test_create_with_frequency_stores_frequency(
    module: Any, collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module._KeepUtils, "schedule", MagicMock())
    interaction = make_interaction()

    await module._KeepUtils.create(collection, interaction, "water plants", "2099-01-01 00:00", "weekly", 2)

    doc = last_call(collection.insert_one).args[0]
    assert doc["freq_str"] == "weekly"
    assert doc["freq_int"] == 2


@pytest.mark.asyncio
async def test_del_keep_rejects_invalid_payload(
    module: Any, keep: Any, collection: FakeCollection
) -> None:
    interaction = make_interaction()

    await keep.del_keep.callback(keep, interaction, keep_event="not-json")

    interaction.followup.send.assert_awaited_once()
    assert last_call(interaction.followup.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_del_keep_cancels_task(
    module: Any, keep: Any, collection: FakeCollection, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = {"uuid": "u-1", "channelID": 123, "event": "buy milk", "sendAt": 4102444800}
    collection.find_one_and_delete = AsyncMock(return_value=record)
    task = MagicMock()
    monkeypatch.setattr(module, "reminder_tasks", {"u-1": task})
    interaction = make_interaction()

    await keep.del_keep.callback(keep, interaction, keep_event=orjson.dumps(["u-1", 123]).decode())

    task.cancel.assert_called_once()
    interaction.followup.send.assert_awaited_once()
    assert "buy milk" in last_call(interaction.followup.send).args[0]


@pytest.mark.asyncio
async def test_show_keep_lists_at_most_ten(
    module: Any, keep: Any, collection: FakeCollection
) -> None:
    collection.docs = [
        {"uuid": f"uuid-{index:02d}", "event": f"event-{index:02d}", "sendAt": 4102444800, "channelID": 1}
        for index in range(12)
    ]
    interaction = make_interaction()

    await keep.show_keep.callback(keep, interaction)

    embed = last_call(interaction.followup.send).kwargs["embed"]
    assert embed.description.count("### ") == 10
    assert "event-00" in embed.description
    assert "uuid-00" in embed.description


@pytest.mark.asyncio
async def test_check_keepdata_requires_owner(
    module: Any, keep: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "is_KeJC", lambda user_id: False)
    ctx = ctx_factory()

    await keep.check_keepdata.callback(keep, ctx)

    ctx.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_keepdata_reports_tasks(
    module: Any, keep: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "is_KeJC", lambda user_id: True)
    monkeypatch.setattr(module, "reminder_tasks", {"u-1": "task"})
    ctx = ctx_factory()

    await keep.check_keepdata.callback(keep, ctx)

    ctx.send.assert_awaited_once_with(str({"u-1": "task"}))
