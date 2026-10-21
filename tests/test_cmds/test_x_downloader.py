"""`cmds/x_downloader.py`：X/Twitter 影音下載的 URL 判斷與 cookie 處理。"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from tests.helpers import make_ctx
from tests.helpers import last_call

COOKIE_JSON = [
    {
        "name": "auth_token",
        "value": "secret",
        "domain": ".x.com",
        "expirationDate": 1893456000.5,
    },
    {
        "name": "ct0",
        "value": "csrf",
        "domain": ".x.com",
        "path": "/home",
        "secure": True,
        "httpOnly": True,
    },
]


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.x_downloader")


@pytest.fixture
def downloader(module: Any) -> Any:
    return module.Donwloader()


@pytest.mark.parametrize(
    "url,headers,expected",
    [
        ("https://video.twimg.com/a.mp4", {}, True),
        ("https://cdn.example/a.webm", {}, True),
        ("https://cdn.example/a.m3u8", {}, True),
        ("https://cdn.example/a.jpg", {"content-type": "video/mp4"}, True),
        ("https://cdn.example/a.jpg", {"content-type": "application/x-mpegurl"}, True),
        ("https://cdn.example/a.jpg", {"content-type": "image/jpeg"}, False),
        ("https://cdn.example/a.jpg", {}, False),
    ],
)
def test_is_video_request(downloader: Any, url: str, headers: dict[str, str], expected: bool) -> None:
    request = SimpleNamespace(url=url, headers=headers)

    assert downloader.is_video_request(request) is expected


@pytest.mark.asyncio
async def test_get_cookie_converts_browser_export(
    module: Any, downloader: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    cookie_path = tmp_path / "x.json"
    cookie_path.write_bytes(orjson.dumps(COOKIE_JSON))
    monkeypatch.setattr(module, "COOKIE_FILE_PATH", cookie_path)

    cookies = await downloader.get_cookie()

    assert isinstance(cookies, list)
    assert cookies[0] == {
        "name": "auth_token",
        "value": "secret",
        "domain": ".x.com",
        "path": "/",
        "secure": False,
        "httpOnly": False,
        "sameSite": "None",
        "expires": 1893456000,
    }
    assert cookies[1]["path"] == "/home"
    assert cookies[1]["secure"] is True


@pytest.mark.asyncio
async def test_get_cookie_returns_false_for_storage_state(
    module: Any, downloader: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    cookie_path = tmp_path / "x.json"
    cookie_path.write_bytes(orjson.dumps({"cookies": [], "origins": []}))
    monkeypatch.setattr(module, "COOKIE_FILE_PATH", cookie_path)

    assert await downloader.get_cookie() is False


@pytest.mark.asyncio
async def test_get_cookie_missing_file_raises(module: Any, downloader: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "COOKIE_FILE_PATH", tmp_path / "missing.json")

    with pytest.raises(FileNotFoundError):
        await downloader.get_cookie()


@pytest.mark.asyncio
async def test_write_cookie_roundtrip(
    module: Any, downloader: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    cookie_path = tmp_path / "x.json"
    monkeypatch.setattr(module, "COOKIE_FILE_PATH", cookie_path)

    await downloader.write_cookie(COOKIE_JSON)

    assert orjson.loads(cookie_path.read_bytes()) == COOKIE_JSON


@pytest.mark.asyncio
async def test_download_video_strips_query_string(
    module: Any, downloader: Any, tmp_cwd: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        async def aiter_bytes(self, chunk_size: int = 8192):
            yield b"abc"
            yield b"def"

    class FakeStream:
        async def __aenter__(self) -> FakeResponse:
            return FakeResponse()

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        def stream(self, method: str, url: str) -> FakeStream:
            return FakeStream()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)

    await downloader.download_video("https://cdn.example/video.mp4?tag=1")

    downloaded = tmp_cwd / "videos" / "video.mp4"
    assert downloaded.exists()
    assert downloaded.read_bytes() == b"abcdef"


@pytest.mark.asyncio
async def test_clean_browser_without_session(module: Any, downloader: Any) -> None:
    await downloader.clean_browser()

    assert downloader.context is None
    assert downloader.browser is None
    assert downloader.playwright is None


@pytest.mark.asyncio
async def test_x_download_rejects_non_x_url(module: Any, bot: Any) -> None:
    cog = module.XDownloader(bot)
    ctx = make_ctx(bot)

    await cog.x_download.callback(cog, ctx, url="https://youtube.com/watch?v=1", type="image")

    ctx.send.assert_awaited_once()
    assert "Invalid URL" in last_call(ctx.send).args[0]


@pytest.mark.asyncio
async def test_x_download_forwards_result(module: Any, bot: Any) -> None:
    cog = module.XDownloader(bot)
    ctx = make_ctx(bot)
    run = AsyncMock(return_value="https://cdn.example/final.mp4")
    original = module.x_downloader
    module.x_downloader = SimpleNamespace(run=run)
    try:
        await cog.x_download.callback(cog, ctx, url="https://x.com/user/status/1", type="video")
    finally:
        module.x_downloader = original

    run.assert_awaited_once_with("https://x.com/user/status/1", "video")
    ctx.send.assert_awaited_once_with("https://cdn.example/final.mp4")
