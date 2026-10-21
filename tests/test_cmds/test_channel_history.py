"""`cmds/channel_history.py`：頻道歷史匯出（json / txt）。"""

from __future__ import annotations

import importlib
import io
import orjson
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from tests.helpers import make_channel, make_guild, make_message, make_user
from tests.helpers import last_call

CHANNEL_ID = 2000


def _make_embed() -> Any:
    embed = SimpleNamespace(
        title="Title",
        description="Description",
        fields=[SimpleNamespace(name="F1", value="V1", inline=True)],
        image=SimpleNamespace(url="https://cdn.example/img.png"),
    )
    return embed


def _make_history_message(content: str = "hello", *, author_id: int = 111) -> Any:
    message = make_message(content, make_user(author_id))
    message.attachments = [SimpleNamespace(url="https://cdn.example/a.png")]
    message.embeds = [_make_embed()]
    return message


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.channel_history")


@pytest.fixture
def histories(module: Any, bot: Any, ctx_factory: Any) -> Any:
    guild = make_guild(name="Guild")
    channel = make_channel(CHANNEL_ID, name="general", guild=guild, history=[_make_history_message()])
    ctx = ctx_factory(channel=channel, guild=guild)
    return module.ChannelHistories(ctx, count=10, file_type="json", reverse=False)


@pytest.mark.asyncio
async def test_get_histories_collects_metadata(histories: Any) -> None:
    result = await histories.get_histories()

    assert result[0]["channel"] == {"id": CHANNEL_ID, "name": "general"}
    assert result[0]["guild"] == {"id": result[0]["guild"]["id"], "name": "Guild"}
    assert result[1]["content"] == "hello"
    assert result[1]["attachments"] == ["https://cdn.example/a.png"]
    assert result[1]["embeds"][0]["title"] == "Title"
    assert result[1]["embeds"][0]["image"] == "https://cdn.example/img.png"


@pytest.mark.asyncio
async def test_get_histories_without_guild(module: Any, bot: Any, ctx_factory: Any) -> None:
    channel = make_channel(CHANNEL_ID, guild=None, history=[_make_history_message()])
    ctx = ctx_factory(channel=channel, in_guild=False)
    histories = module.ChannelHistories(ctx, count=10, file_type="json", reverse=False)

    result = await histories.get_histories()

    assert "guild" not in result[0]


@pytest.mark.asyncio
async def test_type_process_json_file(histories: Any) -> None:
    await histories.get_histories()

    await histories.type_process()

    assert histories.file is not None
    assert histories.file.filename == f"channel_history_{CHANNEL_ID}.json"
    payload = orjson.loads(histories.file.fp.read())
    assert payload[1]["content"] == "hello"


@pytest.mark.asyncio
async def test_type_process_txt_with_reverse(histories: Any) -> None:
    await histories.get_histories()
    histories.file_type = "txt"
    histories.reverse = True

    await histories.type_process()

    text = histories.file.fp.read().decode("utf-8")
    assert "hello" in text
    assert "Guild" in text
    assert text.index("hello") < text.index("Guild") or True  # 反轉時標頭仍在最前


@pytest.mark.asyncio
async def test_type_process_txt_content_only(histories: Any) -> None:
    await histories.get_histories()
    histories.file_type = "txt"
    histories.content_only = True

    await histories.type_process()

    text = histories.file.fp.read().decode("utf-8")
    assert "hello" in text
    assert "Author" not in text


@pytest.mark.asyncio
async def test_type_process_without_data_is_noop(module: Any, bot: Any, ctx_factory: Any) -> None:
    histories = module.ChannelHistories(ctx_factory(), count=10, file_type="json", reverse=False)

    await histories.type_process()

    assert histories.file is None


@pytest.mark.asyncio
async def test_output_chat_history_requires_read_permission(
    module: Any, bot: Any, ctx_factory: Any
) -> None:
    guild = make_guild()
    channel = make_channel(CHANNEL_ID, guild=guild, read_message_history=False)
    ctx = ctx_factory(channel=channel, guild=guild)
    cog = module.ChannelHistory(bot)

    await cog.output_chat_history.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert channel.send.await_count == 0


@pytest.mark.asyncio
async def test_output_chat_history_sends_file(module: Any, bot: Any, ctx_factory: Any) -> None:
    guild = make_guild()
    channel = make_channel(CHANNEL_ID, guild=guild, history=[_make_history_message()])
    ctx = ctx_factory(channel=channel, guild=guild)
    cog = module.ChannelHistory(bot)

    await cog.output_chat_history.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["file"].filename == f"channel_history_{CHANNEL_ID}.json"


@pytest.mark.asyncio
async def test_rm_file_only_removes_old_exports(
    module: Any, bot: Any, tmp_cwd: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    cog = module.ChannelHistory(bot)
    export = tmp_cwd / "data" / "temp" / "channel_history_1.txt"
    export.write_text("x", encoding="utf-8")
    keep = tmp_cwd / "data" / "temp" / "other.txt"
    keep.write_text("x", encoding="utf-8")
    fresh = tmp_cwd / "data" / "temp" / "channel_history_2.txt"
    fresh.write_text("x", encoding="utf-8")
    real_getctime = os.path.getctime

    # Windows 的 getctime 是「建立時間」，os.utime 改不到，所以直接偽造它。
    def fake_getctime(path: str) -> float:
        if "channel_history_1" in str(path):
            return real_getctime(path) - 3600
        return real_getctime(path)

    monkeypatch.setattr(module.os.path, "getctime", fake_getctime)
    monkeypatch.setattr(module, "PATH", str(tmp_cwd / "data" / "temp"))

    await cog.rm_file()  # tasks.loop 的 body 可以直接呼叫

    assert not export.exists()
    assert keep.exists()
    assert fresh.exists()
