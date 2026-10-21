"""`cmds/translator.py`：`/translate` 指令。"""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import make_ctx, make_interaction
from tests.helpers import last_call


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.translator")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    return module.Translator(bot)


@pytest.mark.asyncio
async def test_translate_uses_guild_locale(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    translate = AsyncMock(return_value=("translated", "model-x"))
    monkeypatch.setattr(module, "translate", translate)
    ctx = ctx_factory()

    await cog.translate.callback(cog, ctx, content="hello", target="en-US")

    assert last_call(translate).kwargs["user_lang_code"] == "zh-TW"
    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.description == "translated"
    assert "model-x" in embed.footer.text


@pytest.mark.asyncio
async def test_translate_uses_interaction_locale(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    translate = AsyncMock(return_value=("translated", "model-y"))
    monkeypatch.setattr(module, "translate", translate)
    interaction = make_interaction(locale="en-US")
    interaction.translate = AsyncMock(return_value="YinXi")
    ctx = ctx_factory(interaction=interaction)

    await cog.translate.callback(cog, ctx, content="hello")

    assert last_call(translate).kwargs["user_lang_code"] == "en-US"
    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.author.name == ctx.author.name


@pytest.mark.asyncio
async def test_translate_falls_back_to_default_model(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    translate = AsyncMock(return_value=("translated", None))
    monkeypatch.setattr(module, "translate", translate)
    ctx = ctx_factory()

    await cog.translate.callback(cog, ctx, content="hello")

    embed = last_call(ctx.send).kwargs["embed"]
    assert module.DEFAULT_MODEL in embed.footer.text


@pytest.mark.asyncio
async def test_translate_in_dm_has_no_user_locale(
    module: Any, cog: Any, bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    translate = AsyncMock(return_value=("translated", "model-z"))
    monkeypatch.setattr(module, "translate", translate)
    ctx = ctx_factory(in_guild=False)

    await cog.translate.callback(cog, ctx, content="hello")

    assert "user_lang_code" not in last_call(translate).kwargs
