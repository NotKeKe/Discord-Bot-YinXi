"""`cmds/giveaway2.py`：抽獎建立、參加 / 取消與開獎流程。"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import FakeCollection, make_channel, make_ctx, make_guild, make_interaction, make_message, make_user
from tests.helpers import last_call

PRIZE = "Steam key"
# 明確帶 +08:00，否則 `astimezone(+08:00)` 會先假設「本機時區」，
# 在 CI（UTC）跑出來的小時就和開發機（+08:00）不同。
TZ_TAIPEI = timezone(timedelta(hours=8))
END_TIME = datetime(2099, 1, 1, 12, 0, tzinfo=TZ_TAIPEI)


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.giveaway2")


@pytest.fixture
def collection(module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch) -> FakeCollection:
    """`bot` fixture 設定 global bot，讓 get_translate 有 translator 可用。"""

    coll = FakeCollection()
    monkeypatch.setattr(module, "COLL", coll)
    return coll


@pytest.mark.asyncio
async def test_write_giveaway_info(module: Any, collection: FakeCollection) -> None:
    await module.Utils.write_giveaway_info(
        channel_id=1,
        message_id=2,
        hosted_user_id=3,
        prize=PRIZE,
        end_time=END_TIME,
        winners_total=5,
    )

    doc = last_call(collection.insert_one).args[0]
    assert doc["channel_id"] == 1
    assert doc["message_id"] == 2
    assert doc["prize"] == PRIZE
    assert doc["winners_total"] == 5
    assert doc["participant_ids"] == []
    parsed = datetime.fromisoformat(doc["end_time"])
    assert parsed.utcoffset() == timedelta(hours=8)
    assert parsed.hour == 12


@pytest.mark.asyncio
async def test_button_callback_without_message(module: Any, collection: FakeCollection) -> None:
    interaction = make_interaction(message=None)

    await module.Utils.button_callback(interaction)

    interaction.response.send_message.assert_not_awaited()
    collection.find_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_button_callback_unknown_giveaway(module: Any, collection: FakeCollection) -> None:
    collection.find_one = AsyncMock(return_value=None)
    interaction = make_interaction(message=make_message())

    await module.Utils.button_callback(interaction)

    interaction.response.send_message.assert_awaited_once()
    assert last_call(interaction.response.send_message).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_button_callback_expired_giveaway(module: Any, collection: FakeCollection) -> None:
    collection.find_one = AsyncMock(
        return_value={"end_time": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    )
    interaction = make_interaction(message=make_message())

    await module.Utils.button_callback(interaction)

    interaction.response.send_message.assert_awaited_once()
    collection.update_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_button_callback_join(module: Any, collection: FakeCollection) -> None:
    user = make_user(999)
    embed = MagicMock()
    embed.fields = [MagicMock(), MagicMock()]
    embed.fields[1].value = "4"
    message = make_message(embeds=[embed])
    interaction = make_interaction(user=user, message=message)
    collection.find_one = AsyncMock(
        return_value={"end_time": END_TIME.replace(tzinfo=timezone.utc).isoformat(), "participant_ids": []}
    )

    await module.Utils.button_callback(interaction)

    update = last_call(collection.update_one).args[1]
    assert "$addToSet" in update
    assert embed.set_field_at.call_args.args[0] == 1
    assert embed.set_field_at.call_args.kwargs["value"] == "5"
    message.edit.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_callback_leave(module: Any, collection: FakeCollection) -> None:
    user = make_user(999)
    embed = MagicMock()
    embed.fields = [MagicMock(), MagicMock()]
    embed.fields[1].value = "4"
    message = make_message(embeds=[embed])
    interaction = make_interaction(user=user, message=message)
    collection.find_one = AsyncMock(
        return_value={"end_time": END_TIME.replace(tzinfo=timezone.utc).isoformat(), "participant_ids": [999]}
    )

    await module.Utils.button_callback(interaction)

    update = last_call(collection.update_one).args[1]
    assert "$pull" in update
    assert embed.set_field_at.call_args.kwargs["value"] == "3"


@pytest.mark.asyncio
async def test_giveaway_rejects_bad_date(module: Any, ctx_factory: Any) -> None:
    cog = module.Giveaway2(MagicMock())
    ctx = ctx_factory()

    await cog.giveaway.callback(cog, ctx, winners=1, prize=PRIZE, date="tomorrow", time="12:00")

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_giveaway_rejects_past_time(module: Any, ctx_factory: Any) -> None:
    cog = module.Giveaway2(MagicMock())
    ctx = ctx_factory()

    await cog.giveaway.callback(cog, ctx, winners=1, prize=PRIZE, date="2000-01-01", time="00:00")

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_giveaway_creates_message_and_record(
    module: Any, collection: FakeCollection, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    cog = module.Giveaway2(MagicMock())
    write_info = AsyncMock()
    wait_task = AsyncMock()
    monkeypatch.setattr(module.Utils, "write_giveaway_info", write_info)
    monkeypatch.setattr(module.Utils, "wait_task", wait_task)
    ctx = ctx_factory()
    ctx.send.return_value = make_message(message_id=321)

    await cog.giveaway.callback(cog, ctx, winners=2, prize=PRIZE, date="2099-01-01", time="12:00")

    kwargs = last_call(ctx.send).kwargs
    assert kwargs["embed"].title == f"**{PRIZE}**"
    assert kwargs["view"] is not None
    write_info.assert_awaited_once()
    assert last_call(write_info).kwargs["message_id"] == 321
    assert last_call(write_info).kwargs["winners_total"] == 2
    wait_task.assert_awaited_once()
