"""`cmds/error.py`：統一錯誤回報。"""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.helpers import make_ctx, make_user
from tests.helpers import last_call


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    mod = importlib.import_module("cmds.error")
    monkeypatch.setattr(mod, "KeJCID", None)
    return mod


@pytest.mark.asyncio
async def test_errorresponse_reports_translated_message(module: Any, bot: Any) -> None:
    cog = module.ErrorHandler(bot)
    ctx = make_ctx(bot)

    await cog.errorresponse.callback(
        cog,
        ctx,
        檔案名稱="cmds.counting",
        指令名稱="counting",
        exception=ValueError("boom"),
    )

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).kwargs["content"], str)
    # KeJCID 為 None 時不該去 fetch user
    bot.fetch_user = AsyncMock()
    bot.fetch_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_errorresponse_uses_traceback_when_available(module: Any, bot: Any) -> None:
    cog = module.ErrorHandler(bot)
    ctx = make_ctx(bot)

    try:
        raise RuntimeError("kaboom")
    except RuntimeError as exc:
        await cog.errorresponse.callback(cog, ctx, 檔案名稱="cmds.x", 指令名稱="y", exception=exc)

    assert ctx.send.await_count == 1


@pytest.mark.asyncio
async def test_errorresponse_sends_dm_to_owner(module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "KeJCID", "123456")
    owner = make_user(123456)
    bot.fetch_user = AsyncMock(return_value=owner)
    cog = module.ErrorHandler(bot)
    ctx = make_ctx(bot)

    await cog.errorresponse.callback(
        cog,
        ctx,
        檔案名稱="cmds.x",
        指令名稱="y",
        exception=ValueError("boom"),
        user_send=True,
    )

    bot.fetch_user.assert_awaited_once_with(123456)
    owner.send.assert_awaited_once()
    assert "cmds.x" in last_call(owner.send).args[0]


@pytest.mark.asyncio
async def test_errorresponse_ephemeral_flag(module: Any, bot: Any) -> None:
    cog = module.ErrorHandler(bot)
    ctx = make_ctx(bot)

    await cog.errorresponse.callback(
        cog,
        ctx,
        檔案名稱="cmds.x",
        指令名稱="y",
        exception=ValueError("boom"),
        ephemeral=True,
    )

    assert last_call(ctx.send).kwargs["ephemeral"] is True
