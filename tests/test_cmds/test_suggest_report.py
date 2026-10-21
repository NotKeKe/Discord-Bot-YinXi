"""`cmds/suggest_report.py`：建議與錯誤回報流程。"""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import FakeCollection, FakeCursor, make_ctx, make_interaction
from tests.helpers import last_call

REPORT_UUID = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.suggest_report")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    instance = module.SuggestReport(bot)
    instance.SUGGEST_COLL = FakeCollection()
    instance.REPORT_COLL = FakeCollection()
    instance.CHANNEL = None
    return instance


def test_report_status_values(module: Any) -> None:
    assert {member.value for member in module.ReportStatusType} == {
        "pending",
        "confirmed",
        "in_progress",
        "resolved",
        "closed",
    }
    assert module.ReportStatusType.PENDING.value == "pending"


@pytest.mark.asyncio
async def test_suggest_writes_document(cog: Any, ctx_factory: Any) -> None:
    ctx = ctx_factory()

    await cog.suggest.callback(cog, ctx, text="add a feature")

    doc = last_call(cog.SUGGEST_COLL.insert_one).args[0]
    assert doc["text"] == "add a feature"
    assert doc["user_id"] == ctx.author.id
    assert "create_time" in doc
    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_suggest_notifies_log_channel(cog: Any, ctx_factory: Any) -> None:
    log_channel = MagicMock()
    log_channel.send = AsyncMock()
    cog.CHANNEL = log_channel
    ctx = ctx_factory()

    await cog.suggest.callback(cog, ctx, text="hello")

    log_channel.send.assert_awaited_once()
    assert "hello" in last_call(log_channel.send).args[0]


@pytest.mark.asyncio
async def test_suggest_when_channel_send_fails(cog: Any, ctx_factory: Any) -> None:
    log_channel = MagicMock()
    log_channel.send = AsyncMock(side_effect=Exception("boom"))
    cog.CHANNEL = log_channel
    ctx = ctx_factory()

    await cog.suggest.callback(cog, ctx, text="hello")

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_report_writes_pending_document(cog: Any, ctx_factory: Any) -> None:
    ctx = ctx_factory()

    await cog.report.callback(cog, ctx, text="something broke")

    doc = last_call(cog.REPORT_COLL.insert_one).args[0]
    assert doc["status"] == "pending"
    assert doc["reason"] == "PENDING"
    assert len(doc["uuid"]) == 32
    ctx.send.assert_awaited_once()
    embed = last_call(ctx.send).kwargs["embed"]
    assert len(embed.fields) == 3
    assert embed.fields[2].value == doc["uuid"]


@pytest.mark.asyncio
async def test_report_trace_not_found(cog: Any, ctx_factory: Any) -> None:
    cog.REPORT_COLL.find_one = AsyncMock(return_value=None)
    ctx = ctx_factory()

    await cog.report_trace.callback(cog, ctx, report_uuid=REPORT_UUID)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_report_trace_found(cog: Any, ctx_factory: Any) -> None:
    cog.REPORT_COLL.find_one = AsyncMock(
        return_value={
            "uuid": REPORT_UUID,
            "text": "trace me",
            "status": "confirmed",
            "reason": "looking",
        }
    )
    ctx = ctx_factory()

    await cog.report_trace.callback(cog, ctx, report_uuid=REPORT_UUID)

    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.fields[1].value == REPORT_UUID
    assert "CONFIRMED" in embed.fields[2].value


@pytest.mark.asyncio
async def test_set_report_status_not_found(cog: Any, module: Any, ctx_factory: Any) -> None:
    cog.REPORT_COLL.find_one = AsyncMock(return_value=None)
    ctx = ctx_factory()

    await cog.set_report_status.callback(cog, ctx, REPORT_UUID, module.ReportStatusType.CONFIRMED)

    ctx.send.assert_awaited_once()
    assert "not found" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_set_report_status_updates_closed_time(cog: Any, module: Any, ctx_factory: Any) -> None:
    cog.REPORT_COLL.find_one = AsyncMock(return_value={"uuid": REPORT_UUID})
    ctx = ctx_factory()

    await cog.set_report_status.callback(
        cog, ctx, REPORT_UUID, module.ReportStatusType.CLOSED, "fixed"
    )

    update = last_call(cog.REPORT_COLL.update_one).args[1]["$set"]
    assert update["status"] == "closed"
    assert update["reason"] == "fixed"
    assert update["closed_time"]


@pytest.mark.asyncio
async def test_set_report_status_clears_closed_time(cog: Any, module: Any, ctx_factory: Any) -> None:
    cog.REPORT_COLL.find_one = AsyncMock(return_value={"uuid": REPORT_UUID})
    ctx = ctx_factory()

    await cog.set_report_status.callback(
        cog, ctx, REPORT_UUID, module.ReportStatusType.IN_PROGRESS
    )

    update = last_call(cog.REPORT_COLL.update_one).args[1]["$set"]
    assert update["closed_time"] == ""


@pytest.mark.asyncio
async def test_uuid_autocomplete_sorts_resolved_last(cog: Any, module: Any) -> None:
    cog.REPORT_COLL.find = MagicMock(
        return_value=FakeCursor(
            [
                {"uuid": "resolved-uuid", "text": "aaa", "status": "resolved"},
                {"uuid": "pending-uuid", "text": "bbb", "status": "pending"},
            ]
        )
    )

    choices = await cog.set_report_status_uuid_autocomplete(make_interaction(), "")

    assert [choice.value for choice in choices] == ["pending-uuid", "resolved-uuid"]


@pytest.mark.asyncio
async def test_uuid_autocomplete_limits_to_25(cog: Any) -> None:
    cog.REPORT_COLL.find = MagicMock(
        return_value=FakeCursor(
            [{"uuid": f"uuid-{index:02d}", "text": "x", "status": "pending"} for index in range(40)]
        )
    )

    choices = await cog.set_report_status_uuid_autocomplete(make_interaction(), "")

    assert len(choices) == 25
