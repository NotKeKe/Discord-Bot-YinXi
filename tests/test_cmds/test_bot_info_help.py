"""`cmds/bot_info_help.py`：`/help` 的 Cog 與指令自動完成。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.bot_info_help")


@pytest.fixture
def fake_bot() -> SimpleNamespace:
    alpha_commands = [SimpleNamespace(name="alpha_cmd"), SimpleNamespace(name="omega_cmd")]
    return SimpleNamespace(
        cogs={"Beta": object(), "Alpha": object(), "Gamma": object()},
        commands={name: object() for name in ("ping", "avatar", "help")},
        get_cog=lambda name: SimpleNamespace(get_commands=lambda: alpha_commands) if name == "Alpha" else None,
    )


@pytest.mark.asyncio
async def test_cog_name_autocomplete_sorted(module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)

    choices = await module.cogName_autocomplete(SimpleNamespace(), "")

    assert [choice.name for choice in choices] == ["Alpha", "Beta", "Gamma"]


@pytest.mark.asyncio
async def test_cog_name_autocomplete_filters(module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)

    choices = await module.cogName_autocomplete(SimpleNamespace(), "ga")

    assert [choice.name for choice in choices] == ["Gamma"]


@pytest.mark.asyncio
async def test_cog_name_autocomplete_limits(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bot = SimpleNamespace(cogs={f"cog_{index:02d}": object() for index in range(40)})
    monkeypatch.setattr(module, "bot", fake_bot)

    choices = await module.cogName_autocomplete(SimpleNamespace(), "")

    assert len(choices) == 25


@pytest.mark.asyncio
async def test_cog_name_autocomplete_handles_error(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenBot:
        @property
        def cogs(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(module, "bot", BrokenBot())

    assert await module.cogName_autocomplete(SimpleNamespace(), "") == []


@pytest.mark.xfail(
    strict=True,
    reason="bot.commands 是 dict，[c.name for c in cmds] 會對 key（str）取 .name 而 AttributeError；"
    "未帶 cog_name 的自動完成目前是壞的（詳見 I-SEE-ERRORS.md）",
)
@pytest.mark.asyncio
async def test_cmd_name_autocomplete_all_commands(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name=None))

    choices = await module.cmdName_autocomplete(interaction, "")

    assert [choice.name for choice in choices] == ["avatar", "help", "ping"]


@pytest.mark.asyncio
async def test_cmd_name_autocomplete_for_specific_cog(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name="Alpha"))

    choices = await module.cmdName_autocomplete(interaction, "")

    assert [choice.name for choice in choices] == ["alpha_cmd", "omega_cmd"]


@pytest.mark.asyncio
async def test_cmd_name_autocomplete_unknown_cog(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name="Nope"))

    assert await module.cmdName_autocomplete(interaction, "") == []


@pytest.mark.xfail(
    strict=True,
    reason="bot.commands 是 dict，[c.name for c in cmds] 會對 key（str）取 .name 而 AttributeError；"
    "未帶 cog_name 的自動完成目前是壞的（詳見 I-SEE-ERRORS.md）",
)
@pytest.mark.asyncio
async def test_cmd_name_autocomplete_filters(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name=None))

    choices = await module.cmdName_autocomplete(interaction, "he")

    assert [choice.name for choice in choices] == ["help"]
