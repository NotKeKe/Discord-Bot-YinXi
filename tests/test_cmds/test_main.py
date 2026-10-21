"""`cmds/main.py`：一般工具指令（ping / avatar / uuid / 分數計算 / petpet …）。"""

from __future__ import annotations

import importlib
import io
import re
import sqlite3
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from tests.helpers import make_channel, make_ctx, make_guild, make_user
from tests.helpers import last_call

OWNER_ID = 777


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    mod = importlib.import_module("cmds.main")
    monkeypatch.setattr(mod, "KeJCID", str(OWNER_ID))
    monkeypatch.setattr(mod, "admins", [])
    return mod


@pytest.fixture
def fake_bot(bot: Any) -> Any:
    """真正被測指令用的假 bot；`bot` fixture 只負責設定 global bot 供翻譯使用。"""

    fake = MagicMock()
    fake.latency = 0.123
    fake.fetch_user = AsyncMock()
    return fake


@pytest.fixture
def cog(module: Any, fake_bot: Any) -> Any:
    return module.Main(fake_bot)


@pytest.mark.asyncio
async def test_random_uuid(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog._random_uuid.callback(cog, ctx)

    value = last_call(ctx.send).args[0]
    assert uuid.UUID(value)


@pytest.mark.asyncio
async def test_ping_reports_latency(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.ping.callback(cog, ctx)

    embed = last_call(ctx.send).kwargs["embed"]
    assert "123" in embed.description


@pytest.mark.asyncio
async def test_avatar_uses_default_avatar(cog: Any, fake_bot: Any) -> None:
    member = MagicMock()
    member.avatar = None
    member.color = discord.Color.blue()
    member.default_avatar = SimpleNamespace(url="https://cdn.example/default.png")
    ctx = make_ctx(fake_bot)

    await cog.avatar.callback(cog, ctx, member=member)

    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.image.url == "https://cdn.example/default.png"


@pytest.mark.asyncio
async def test_avatar_without_any_avatar(cog: Any, fake_bot: Any) -> None:
    member = MagicMock()
    member.avatar = None
    member.default_avatar = None
    ctx = make_ctx(fake_bot)

    await cog.avatar.callback(cog, ctx, member=member)

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str) or last_call(ctx.send).kwargs


@pytest.mark.asyncio
async def test_get_system_channel(cog: Any, fake_bot: Any) -> None:
    channel = make_channel(555, name="system")
    guild = make_guild(system_channel=channel)
    ctx = make_ctx(fake_bot, guild=guild)

    await cog.systemChannel.callback(cog, ctx)

    ctx.send.assert_awaited_once_with(channel.mention)


@pytest.mark.asyncio
async def test_get_system_channel_without_channel(cog: Any, fake_bot: Any) -> None:
    guild = make_guild(system_channel=None)
    ctx = make_ctx(fake_bot, guild=guild)

    await cog.systemChannel.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str)


@pytest.mark.asyncio
async def test_get_system_channel_in_dm(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot, in_guild=False)

    await cog.systemChannel.callback(cog, ctx)

    ctx.send.assert_awaited_once_with("You are not in a server.")


@pytest.mark.asyncio
async def test_convert_timestamp(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.unixSecondToReadalbe.callback(cog, ctx, unix_second="1754562468")

    value = last_call(ctx.send).args[0]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value)


@pytest.mark.asyncio
async def test_convert_timestamp_accepts_milliseconds(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.unixSecondToReadalbe.callback(cog, ctx, unix_second="1754562468")
    seconds = last_call(ctx.send).args[0]
    await cog.unixSecondToReadalbe.callback(cog, ctx, unix_second="1754562468464")

    assert last_call(ctx.send).args[0] == seconds


@pytest.mark.asyncio
async def test_convert_timestamp_rejects_text(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.unixSecondToReadalbe.callback(cog, ctx, unix_second="not-a-number")

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str)


@pytest.mark.asyncio
async def test_server_info_embed(cog: Any, fake_bot: Any) -> None:
    members = [
        SimpleNamespace(bot=False, status=SimpleNamespace(), global_name="A"),
        SimpleNamespace(bot=True, status=None, global_name="B"),
    ]
    owner = SimpleNamespace(global_name="Owner", id=1)
    guild = make_guild(
        name="Guild X",
        members=members,
        channels=[make_channel(1, name="general")],
        owner=owner,
        system_channel=None,
    )
    ctx = make_ctx(fake_bot, guild=guild)

    await cog.get_server_info.callback(cog, ctx)

    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.fields[0].value == "Guild X"
    assert len(embed.fields) >= 5


@pytest.mark.asyncio
async def test_high_school_score_without_image(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.high_school_totalScore_calculate.callback(
        cog,
        ctx,
        國文=10,
        英文=20,
        數學=30,
        化學=1,
        生物=1,
        物理=1,
        歷史=1,
        地理=1,
        公民=1,
        體育=1,
    )

    embed = last_call(ctx.send).kwargs["embed"]
    assert embed.fields[0].value == "`254`"
    assert embed.fields[1].value == "`67`"


@pytest.mark.asyncio
async def test_high_school_score_image_requires_prompt(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)
    image = SimpleNamespace(url="https://cdn.example/exam.jpg")

    await cog.high_school_totalScore_calculate.callback(cog, ctx, image=image)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_petpet_without_image(cog: Any, fake_bot: Any) -> None:
    ctx = make_ctx(fake_bot)

    await cog.petpet.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_petpet_generates_gif(cog: Any, module: Any, fake_bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    petpet = MagicMock(return_value=io.BytesIO(b"GIF89a"))
    monkeypatch.setattr(module, "headpat_gif", SimpleNamespace(petpet=petpet))
    image = SimpleNamespace(read=AsyncMock(return_value=b"original-image"))
    ctx = make_ctx(fake_bot)

    await cog.petpet.callback(cog, ctx, image=image)

    petpet.assert_called_once()
    _, kwargs = petpet.call_args
    assert kwargs["overlay_offset"] == (0.0, 0.0)
    assert kwargs["loop"] is True
    assert last_call(ctx.send).kwargs["file"].filename == "petpet.gif"


@pytest.mark.asyncio
async def test_add_admin_appends_and_writes_json(
    cog: Any, module: Any, fake_bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_json = MagicMock()
    monkeypatch.setattr(module, "write_json", write_json)
    fake_bot.fetch_user = AsyncMock(return_value=SimpleNamespace(global_name="Newbie"))
    ctx = ctx_factory(author=make_user(OWNER_ID))

    await cog.add_admin.callback(cog, ctx, userID=4242)

    assert 4242 in module.admins
    write_json.assert_called_once()
    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_add_admin_rejects_duplicate(
    cog: Any, module: Any, fake_bot: Any, ctx_factory: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    module.admins.append(4242)
    fake_bot.fetch_user = AsyncMock(return_value=SimpleNamespace(global_name="Newbie"))
    ctx = ctx_factory(author=make_user(OWNER_ID))

    await cog.add_admin.callback(cog, ctx, userID=4242)

    ctx.send.assert_awaited_once()
    assert "已經是管理員" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_add_admin_requires_owner(cog: Any, fake_bot: Any, ctx_factory: Any) -> None:
    ctx = ctx_factory(author=make_user(OWNER_ID + 1))

    await cog.add_admin.callback(cog, ctx, userID=4242)

    ctx.send.assert_not_awaited()
    fake_bot.fetch_user.assert_not_awaited()


def _create_lang_db(root: Any) -> None:
    conn = sqlite3.connect(root / "data" / "user_lang.db")
    conn.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, lang TEXT)")
    conn.commit()
    conn.close()


def _read_lang(root: Any, user_id: int) -> str | None:
    conn = sqlite3.connect(root / "data" / "user_lang.db")
    row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None


@pytest.mark.asyncio
async def test_lang_rejects_invalid_language(cog: Any, fake_bot: Any, ctx_factory: Any, tmp_cwd: Any) -> None:
    _create_lang_db(tmp_cwd)
    ctx = ctx_factory(author=make_user(31337))

    await cog._lang.callback(cog, ctx, lang="fr-FR")

    ctx.send.assert_awaited_once()
    assert _read_lang(tmp_cwd, 31337) is None


@pytest.mark.asyncio
async def test_lang_stores_preference(cog: Any, fake_bot: Any, ctx_factory: Any, tmp_cwd: Any) -> None:
    _create_lang_db(tmp_cwd)
    ctx = ctx_factory(author=make_user(31337))

    await cog._lang.callback(cog, ctx, lang="en-US")

    assert _read_lang(tmp_cwd, 31337) == "en-US"
    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_lang_detects_same_language(cog: Any, fake_bot: Any, ctx_factory: Any, tmp_cwd: Any) -> None:
    _create_lang_db(tmp_cwd)
    conn = sqlite3.connect(tmp_cwd / "data" / "user_lang.db")
    conn.execute("INSERT INTO users (user_id, lang) VALUES (?, ?)", (31337, "en-US"))
    conn.commit()
    conn.close()
    ctx = ctx_factory(author=make_user(31337))

    await cog._lang.callback(cog, ctx, lang="en-US")

    ctx.send.assert_awaited_once()
    assert "en-US" in last_call(ctx.send).args[0]
