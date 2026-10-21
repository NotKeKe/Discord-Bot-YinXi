"""`cmds/counting.py`：數數接龍的狀態機（純邏輯，不碰 Discord API、不寫檔）。"""

from __future__ import annotations

import importlib
from typing import Any, Iterator

import pytest

from tests.helpers import make_channel, make_guild, make_message, make_user
from tests.helpers import last_call

CHANNEL_ID = 2000
AUTHOR_ID = 111
OTHER_ID = 222
COUNTING_PATH_KEY = str(CHANNEL_ID)


def _make_message(content: str, *, author_id: int = AUTHOR_ID, channel_id: int = CHANNEL_ID) -> Any:
    guild = make_guild()
    channel = make_channel(channel_id, guild=guild)
    return make_message(content, make_user(author_id), channel=channel, guild=guild)


@pytest.fixture
def counting(bot: Any) -> Iterator[Any]:
    module = importlib.import_module("cmds.counting")
    module.Counting.data = {COUNTING_PATH_KEY: {"user": 0, "count": 0}}
    module.Counting.is_update = False
    cog = module.Counting(bot)
    try:
        yield cog, module
    finally:
        module.Counting.data = None
        module.Counting.is_update = False


@pytest.mark.asyncio
async def test_first_number_keeps_counting(counting: Any) -> None:
    cog, module = counting

    message = _make_message("1")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": AUTHOR_ID, "count": 1}
    message.add_reaction.assert_awaited_once_with("✅")
    message.channel.send.assert_not_awaited()
    assert module.Counting.is_update is True


@pytest.mark.asyncio
async def test_same_user_twice_resets_counter(counting: Any) -> None:
    cog, module = counting
    module.Counting.data[COUNTING_PATH_KEY] = {"user": AUTHOR_ID, "count": 3}

    message = _make_message("4")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_awaited_once_with("⚠️")
    embed = last_call(message.channel.send).kwargs["embed"]
    assert embed.title
    message.channel.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_must_start_from_one(counting: Any) -> None:
    cog, module = counting

    message = _make_message("3")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_awaited_once_with("⚠️")
    embed = last_call(message.channel.send).kwargs["embed"]
    assert "1" in embed.title


@pytest.mark.asyncio
async def test_too_large_number_keeps_state(counting: Any) -> None:
    cog, module = counting
    module.Counting.data[COUNTING_PATH_KEY] = {"user": OTHER_ID, "count": 10}

    message = _make_message("111")
    await cog.on_message(message)

    # 過大的數字只會提醒，不會歸零；user 仍會被更新成當前發話者
    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": AUTHOR_ID, "count": 10}
    message.add_reaction.assert_awaited_once_with("⚠️")
    assert last_call(message.channel.send).kwargs["embed"].title


@pytest.mark.asyncio
async def test_too_small_number_keeps_state(counting: Any) -> None:
    cog, module = counting
    module.Counting.data[COUNTING_PATH_KEY] = {"user": OTHER_ID, "count": 200}

    message = _make_message("99")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": AUTHOR_ID, "count": 200}
    message.add_reaction.assert_awaited_once_with("⚠️")


@pytest.mark.asyncio
async def test_wrong_number_resets_counter(counting: Any) -> None:
    cog, module = counting
    module.Counting.data[COUNTING_PATH_KEY] = {"user": OTHER_ID, "count": 10}

    message = _make_message("12")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_awaited_once_with("❌")
    assert last_call(message.channel.send).kwargs["embed"].title


@pytest.mark.asyncio
async def test_number_six_is_ignored_for_same_user(counting: Any) -> None:
    cog, module = counting
    module.Counting.data[COUNTING_PATH_KEY] = {"user": AUTHOR_ID, "count": 5}

    message = _make_message("6")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": AUTHOR_ID, "count": 5}
    message.add_reaction.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_number_six_is_ignored_when_counter_is_zero(counting: Any) -> None:
    cog, module = counting

    message = _make_message("6")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_not_awaited()
    message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_rounds_float_input(counting: Any) -> None:
    """`math_round` 會把 1.4 視為 1、2.6 視為 3。"""

    cog, module = counting

    message = _make_message("1.4")
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": AUTHOR_ID, "count": 1}


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["abc", "", "  "])
async def test_non_numeric_content_is_ignored(counting: Any, content: str) -> None:
    cog, module = counting

    message = _make_message(content)
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_message_is_ignored(counting: Any) -> None:
    cog, module = counting

    message = _make_message("1")
    message.author.bot = True
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_channel_without_counter_is_ignored(counting: Any) -> None:
    cog, module = counting

    message = _make_message("1", channel_id=9999)
    await cog.on_message(message)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    message.add_reaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_counting_command_removes_existing_channel(counting: Any, ctx_factory: Any) -> None:
    cog, module = counting
    ctx = ctx_factory(channel_id=CHANNEL_ID)

    await cog.counting.callback(cog, ctx)

    assert COUNTING_PATH_KEY not in module.Counting.data
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_counting_command_adds_new_channel(counting: Any, ctx_factory: Any) -> None:
    cog, module = counting
    module.Counting.data = {"9999": {"user": 0, "count": 0}}
    ctx = ctx_factory(channel_id=CHANNEL_ID)

    await cog.counting.callback(cog, ctx)

    assert module.Counting.data[COUNTING_PATH_KEY] == {"user": 0, "count": 0}
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_counting_command_without_data(counting: Any, ctx_factory: Any) -> None:
    cog, module = counting
    module.Counting.data = {}
    ctx = ctx_factory(channel_id=CHANNEL_ID)

    # `initdata()` 只在 data is None 時才讀檔，這裡用空 dict 模擬「讀不到資料」。
    await cog.counting.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert "No data loaded" in last_call(ctx.send).args[0]
    assert module.Counting.data == {}
