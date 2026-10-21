"""`cmds/load.py`：擴充套件自動完成與 /reload 系列指令。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import make_ctx
from tests.helpers import last_call

OWNER_ID = 1000


def _prepare_cmds_dir(tmp_cwd: Any, names: list[str]) -> Any:
    cmds_dir = tmp_cwd / "cmds"
    cmds_dir.mkdir(exist_ok=True)
    for name in names:
        (cmds_dir / name).write_text("", encoding="utf-8")
    return cmds_dir


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.load")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    return module.Load(bot)


@pytest.mark.asyncio
async def test_load_autocomplete_lists_python_files(module: Any, tmp_cwd: Any) -> None:
    _prepare_cmds_dir(tmp_cwd, ["b.py", "a.py", "notes.txt"])

    choices = await module.load_autocomplete(SimpleNamespace(), "")

    assert [choice.name for choice in choices] == ["a", "b"]


@pytest.mark.asyncio
async def test_load_autocomplete_filters(module: Any, tmp_cwd: Any) -> None:
    _prepare_cmds_dir(tmp_cwd, ["counting.py", "play4.py", "main.py"])

    choices = await module.load_autocomplete(SimpleNamespace(), "MA")

    assert [choice.name for choice in choices] == ["main"]


@pytest.mark.asyncio
async def test_load_autocomplete_limits_to_25(module: Any, tmp_cwd: Any) -> None:
    _prepare_cmds_dir(tmp_cwd, [f"module_{index:02d}.py" for index in range(40)])

    choices = await module.load_autocomplete(SimpleNamespace(), "")

    assert len(choices) == 25


@pytest.mark.asyncio
async def test_reload_rejects_non_owner(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "KeJCID", "999")
    bot.reload_extension = AsyncMock()
    ctx = ctx_factory()

    await cog.reload.callback(cog, ctx, "counting")

    ctx.send.assert_awaited_once_with("你沒有權限使用該指令")
    bot.reload_extension.assert_not_awaited()


@pytest.mark.asyncio
async def test_reload_success(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "KeJCID", str(OWNER_ID))
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    bot.reload_extension = AsyncMock()
    ctx = ctx_factory()

    await cog.reload.callback(cog, ctx, "counting")

    bot.reload_extension.assert_awaited_once_with("cmds.counting")
    assert ctx.send.await_count == 2
    ctx.send.return_value.delete.assert_awaited()


@pytest.mark.asyncio
async def test_reload_failure(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "KeJCID", str(OWNER_ID))
    bot.reload_extension = AsyncMock(side_effect=Exception("boom"))
    ctx = ctx_factory()

    await cog.reload.callback(cog, ctx, "counting")

    assert ctx.send.await_count == 2
    assert "未被重載" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_reloadall_iterates_python_files(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, tmp_cwd: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "KeJCID", str(OWNER_ID))
    _prepare_cmds_dir(tmp_cwd, ["a.py", "b.py", "notes.txt"])
    bot.reload_extension = AsyncMock()
    ctx = ctx_factory()

    await cog.reloadall.callback(cog, ctx)

    assert bot.reload_extension.await_count == 2
    ctx.send.assert_awaited_once()
