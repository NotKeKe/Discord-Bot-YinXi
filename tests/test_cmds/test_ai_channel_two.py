"""`cmds/ai_channel_two.py`：AI 頻道（只測不連網的歷史整理）。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any

import pytest

from tests.helpers import make_channel, make_guild, make_message, make_user

BOT_USER_ID = 999


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.ai_channel_two")


def _prepare(
    module: Any, monkeypatch: pytest.MonkeyPatch, messages: list[Any], bot_user: Any
) -> Any:
    monkeypatch.setattr(module, "get_bot", lambda: SimpleNamespace(user=bot_user))
    guild = make_guild()
    return make_channel(1234, guild=guild, history=messages)


@pytest.mark.asyncio
async def test_to_history_merges_messages(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    user = make_user(111, global_name="Alice")
    bot_user = make_user(BOT_USER_ID, name="yinxi", bot=True)
    messages = [
        make_message("hello", user),
        make_message("world", user),
        make_message("answer", bot_user),
        make_message("more", bot_user),
        make_message("[system] skip me", user),
        make_message("third", make_user(112, global_name="Bob")),
    ]
    channel = _prepare(module, monkeypatch, messages, bot_user)

    histories = await module.to_history(channel, limit=10)

    # `channel.history()` 是新到舊，`to_history()` 會再 reverse 一次，所以結果是新到舊
    assert [item["role"] for item in histories] == ["user", "assistant", "user"]
    assert "third" in histories[0]["content"]
    assert histories[1]["content"] == "more\nanswer\n"
    assert "hello" in histories[2]["content"]
    assert "world" not in histories[2]["content"]  # 同一個使用者連續訊息會被覆蓋
    assert all("skip me" not in item["content"] for item in histories)


@pytest.mark.asyncio
async def test_to_history_returns_at_most_six(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    messages = [make_message(f"message {index}", make_user(100 + index)) for index in range(10)]
    channel = _prepare(module, monkeypatch, messages, make_user(BOT_USER_ID, bot=True))

    histories = await module.to_history(channel, limit=10)

    assert 0 < len(histories) <= 6


@pytest.mark.asyncio
async def test_to_history_asks_for_the_limit(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    channel = _prepare(
        module, monkeypatch, [make_message("hello", make_user(111))], make_user(BOT_USER_ID, bot=True)
    )

    await module.to_history(channel, limit=3)

    channel.history.assert_called_once_with(limit=3)
