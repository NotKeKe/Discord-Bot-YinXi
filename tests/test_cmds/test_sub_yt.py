"""`cmds/sub_yt.py`：YouTube 訂閱通知。

這個模組在 import 時就會建立 `MyPriorityQueue`（需要 running event loop），
所以 fixture 必須是 async 的，並在 import 後收掉 worker tasks。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from tests.helpers import FakeCollection, make_ctx, import_cmds_module
from tests.helpers import last_call

CHANNEL_URL = "https://www.youtube.com/@example"


class FakeDB:
    def __init__(self, collection: Any) -> None:
        self.collection = collection

    def __getitem__(self, key: str) -> Any:
        return self.collection


@pytest_asyncio.fixture
async def module() -> Any:
    return import_cmds_module("cmds.sub_yt")


@pytest_asyncio.fixture
async def collection(module: Any, monkeypatch: pytest.MonkeyPatch) -> FakeCollection:
    coll = FakeCollection()
    monkeypatch.setattr(module, "db", FakeDB(coll))
    monkeypatch.setattr(
        module,
        "redis_client",
        SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock(), zadd=AsyncMock()),
    )
    return coll


class _FakeYDL:
    def __init__(self, info: dict[str, Any] | None) -> None:
        self._info = info

    def __call__(self, *args: Any, **kwargs: Any) -> "_FakeYDL":
        return self

    def __enter__(self) -> "_FakeYDL":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any] | None:
        return self._info


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "info,expected",
    [
        ({"upload_date": "20240102", "live_status": "not_live"}, datetime(2024, 1, 2)),
        ({"upload_date": "20240102", "live_status": "is_live"}, None),
        ({"live_status": "not_live"}, None),
        (None, None),
    ],
)
async def test_get_upload_date_from_ytdlp(
    module: Any, monkeypatch: pytest.MonkeyPatch, info: dict[str, Any] | None, expected: datetime | None
) -> None:
    monkeypatch.setattr(module.yt_dlp, "YoutubeDL", _FakeYDL(info))

    assert module._get_upload_date("https://youtu.be/abc") == expected


@pytest.mark.asyncio
async def test_upload_date_uses_redis_cache(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "redis_client",
        SimpleNamespace(get=AsyncMock(return_value="2024-01-02T00:00:00"), set=AsyncMock()),
    )

    assert await module.get_upload_date("https://youtu.be/abc") == datetime(2024, 1, 2)


@pytest.mark.asyncio
async def test_upload_date_stores_result(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    redis = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
    monkeypatch.setattr(module, "redis_client", redis)
    monkeypatch.setattr(module.asyncio, "to_thread", AsyncMock(return_value=datetime(2024, 1, 2)))

    result = await module.get_upload_date("https://youtu.be/abc")

    assert result == datetime(2024, 1, 2)
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,html,expected",
    [
        (200, '<meta itemprop="name" content="Example Channel">', "Example Channel"),
        (404, '<meta itemprop="name" content="Example Channel">', None),
        (200, "<html></html>", None),
    ],
)
async def test_get_channel_name(
    module: Any, monkeypatch: pytest.MonkeyPatch, status: int, html: str, expected: str | None
) -> None:
    class FakeResponse:
        async def __aenter__(self) -> "FakeResponse":
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        def __init__(self) -> None:
            self.status = status

        async def text(self) -> str:
            return html

    class FakeSession:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        def get(self, url: str) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(module.aiohttp, "ClientSession", FakeSession)

    assert await module.get_channel_name(CHANNEL_URL) == expected


@pytest.mark.asyncio
async def test_sub_yt_rejects_invalid_url(module: Any, collection: FakeCollection, bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "is_url", lambda url: False)
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt.callback(cog, ctx, url="not-a-url")

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_sub_yt_requires_channel_name(
    module: Any, collection: FakeCollection, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "is_url", lambda url: True)
    monkeypatch.setattr(module, "get_channel_name", AsyncMock(return_value=None))
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt.callback(cog, ctx, url=CHANNEL_URL)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_sub_yt_saves_new_channel(
    module: Any, collection: FakeCollection, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "is_url", lambda url: True)
    monkeypatch.setattr(module, "get_channel_name", AsyncMock(return_value="Example Channel"))
    monkeypatch.setattr(module, "fetch_video_ids", AsyncMock(return_value={}))
    add_to_all = AsyncMock()
    monkeypatch.setattr(module, "add_to_all", add_to_all)
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt.callback(cog, ctx, url=CHANNEL_URL)

    doc = last_call(collection.insert_one).args[0]
    assert doc["sub_url"] == CHANNEL_URL
    assert doc["channelName"] == "Example Channel"
    ctx.send.assert_awaited_once()
    assert "Example Channel" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_sub_yt_rejects_duplicate(
    module: Any, collection: FakeCollection, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "is_url", lambda url: True)
    monkeypatch.setattr(module, "get_channel_name", AsyncMock(return_value="Example Channel"))
    collection.find_one = AsyncMock(return_value={"sub_url": CHANNEL_URL})
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt.callback(cog, ctx, url=CHANNEL_URL)

    collection.insert_one.assert_not_awaited()
    ctx.send.assert_awaited_once_with("Already exist")


@pytest.mark.asyncio
async def test_sub_yt_cancel_reports_missing(
    module: Any, collection: FakeCollection, bot: Any
) -> None:
    collection.find_one_and_delete = AsyncMock(return_value=None)
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt_cancel.callback(cog, ctx, ytb=CHANNEL_URL)

    ctx.send.assert_awaited_once()
    assert "Cannot cancel" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_sub_yt_cancel_removes_channel(
    module: Any, collection: FakeCollection, bot: Any
) -> None:
    collection.find_one_and_delete = AsyncMock(
        return_value={"sub_url": CHANNEL_URL, "channelName": "Example Channel"}
    )
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt_cancel.callback(cog, ctx, ytb=CHANNEL_URL)

    ctx.send.assert_awaited_once()
    assert "Example Channel" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_sub_yt_list(module: Any, collection: FakeCollection, bot: Any) -> None:
    collection.docs = [{"sub_url": CHANNEL_URL, "channelName": "Example Channel"}]
    cog = module.SubYT(bot)
    ctx = make_ctx(bot)

    await cog.sub_yt_list.callback(cog, ctx)

    embed = last_call(ctx.send).kwargs["embed"]
    assert "Example Channel" in embed.description
    assert CHANNEL_URL in embed.description


@pytest.mark.asyncio
async def test_sub_urls_autocomplete(module: Any, collection: FakeCollection) -> None:
    collection.docs = [
        {"sub_url": CHANNEL_URL, "channelName": "Example Channel"},
        {"sub_url": "https://www.youtube.com/@other", "channelName": "Other"},
    ]
    interaction = SimpleNamespace(channel=SimpleNamespace(id=2000))

    choices = await module.sub_urls_autocomplete(interaction, "exam")

    assert [choice.name for choice in choices] == ["Example Channel"]
    assert choices[0].value == CHANNEL_URL
