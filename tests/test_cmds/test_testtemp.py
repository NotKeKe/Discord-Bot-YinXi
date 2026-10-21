"""`cmds/testtemp.py`：開發用測試指令。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import make_channel, make_ctx, make_guild, make_interaction
from tests.helpers import last_call

OWNER_ID = 42


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    mod = importlib.import_module("cmds.testtemp")
    monkeypatch.setattr(mod, "KeJCID", str(OWNER_ID))
    return mod


@pytest.fixture
def cog(module: Any) -> Any:
    bot = MagicMock()
    bot.all_commands = {"ping": object(), "avatar": object()}
    bot.cogs = {"Main": MagicMock()}
    return module.TestTemp(bot)


def test_promision_check_true(module: Any) -> None:
    interaction = SimpleNamespace(user=SimpleNamespace(id=OWNER_ID))

    assert module.promision_check(interaction) is True


def test_promision_check_false(module: Any) -> None:
    interaction = SimpleNamespace(user=SimpleNamespace(id=OWNER_ID + 1))

    assert module.promision_check(interaction) is False


def test_persistent_view_custom_ids(module: Any) -> None:
    view = module.PersistentView()

    custom_ids = {item.custom_id for item in view.children}

    assert custom_ids == {"persistent_view:green", "persistent_view:red", "persistent_view:grey"}


@pytest.mark.asyncio
async def test_get_all_commands(cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot)

    await cog.get_all_commands.callback(cog, ctx)

    message = last_call(ctx.send).args[0]
    assert message.startswith("avatar, ping")
    assert "2" in message


@pytest.mark.asyncio
async def test_get_cog_name(cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot)

    await cog.get_cog_name.callback(cog, ctx)

    ctx.send.assert_awaited_once_with(["Main"])


@pytest.mark.asyncio
async def test_getguildid(cog: Any, bot: Any) -> None:
    guild = make_guild(1234)
    ctx = make_ctx(bot, guild=guild)

    await cog.getguildid.callback(cog, ctx)

    ctx.send.assert_awaited_once_with(1234)


@pytest.mark.asyncio
async def test_membernametest_sends_all_name_variants(cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot)

    await cog.membernametest.callback(cog, ctx)

    assert ctx.send.await_count == 4
    messages = [call.args[0] for call in ctx.send.await_args_list]
    assert messages[0] == "nametester"
    assert messages[1] == "global nameTester"
    assert messages[2] == "display nameTester"


@pytest.mark.asyncio
async def test_systemchannel_requires_owner(module: Any, cog: Any, bot: Any) -> None:
    ctx = make_ctx(bot, author=SimpleNamespace(id=OWNER_ID + 1))

    await cog.systemchannel.callback(cog, ctx)

    ctx.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_systemchannel_without_system_channel(module: Any, cog: Any, bot: Any) -> None:
    guild = make_guild(system_channel=None)
    ctx = make_ctx(bot, guild=guild, author=SimpleNamespace(id=OWNER_ID))

    await cog.systemchannel.callback(cog, ctx)

    ctx.send.assert_awaited_once_with("這個伺服器沒有system channel")


@pytest.mark.asyncio
async def test_mytest_exports_cog_commands(cog: Any, bot: Any) -> None:
    main_cog = MagicMock()
    main_cog.__cog_name__ = "Main"
    main_cog.get_commands.return_value = [SimpleNamespace(name="ping")]
    cog.bot.cogs = {"Main": main_cog}
    ctx = make_ctx(bot)

    await cog.mytest.callback(cog, ctx)

    file = last_call(ctx.send).kwargs["file"]
    assert file.filename == "cogs.txt"
