"""`cmds/bot_info_help.py`：`/help` 的 Cog 與指令自動完成。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from discord.ext import commands


class _NamedCommand:
    """假的 `commands.Command`：只需要 `.name`，而且要可 hash（Bot.commands 是 set）。"""

    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.bot_info_help")


@pytest.fixture
def fake_bot() -> SimpleNamespace:
    alpha_commands = [SimpleNamespace(name="alpha_cmd"), SimpleNamespace(name="omega_cmd")]
    return SimpleNamespace(
        cogs={"Beta": object(), "Alpha": object(), "Gamma": object()},
        # discord.py 的 Bot.commands 是 set[Command]，不是 dict
        commands={_NamedCommand(name) for name in ("ping", "avatar", "help")},
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


@pytest.mark.asyncio
async def test_cmd_name_autocomplete_all_commands(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name=None))

    choices = await module.cmdName_autocomplete(interaction, "")

    assert [choice.name for choice in choices] == ["avatar", "help", "ping"]


@pytest.mark.asyncio
async def test_cmd_name_autocomplete_with_real_bot(
    module: Any, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Bot.commands` 是 `set[Command]`（discord.py 2.7 的 property），不是 dict。"""

    async def callback(ctx: Any) -> None:
        return None

    bot.add_command(commands.Command(callback, name="ping"))
    bot.add_command(commands.Command(callback, name="avatar"))
    monkeypatch.setattr(module, "bot", bot)
    assert all(hasattr(command, "name") for command in bot.commands)

    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name=None))

    choices = await module.cmdName_autocomplete(interaction, "")

    names = [choice.name for choice in choices]
    assert "ping" in names and "avatar" in names
    assert names == sorted(names)


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


@pytest.mark.asyncio
async def test_cmd_name_autocomplete_filters(
    module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "bot", fake_bot)
    interaction = SimpleNamespace(namespace=SimpleNamespace(cog_name=None))

    choices = await module.cmdName_autocomplete(interaction, "he")

    assert [choice.name for choice in choices] == ["help"]
