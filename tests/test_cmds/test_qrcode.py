"""`cmds/qrcode.py`：QR code 產生與掃描。"""

from __future__ import annotations

import importlib
import io
from typing import Any

import pytest
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode
from tests.helpers import last_call

URL = "https://example.com/petpet"


def _qr_png(data: str) -> bytes:
    code = qrcode.QRCode(version=1, box_size=6, border=2)
    code.add_data(data)
    code.make(fit=True)
    buffer = io.BytesIO()
    code.make_image().save(buffer, format="PNG")
    return buffer.getvalue()


def _blank_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 120), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.qrcode")


@pytest.fixture
def qr_cog(bot: Any, module: Any) -> Any:
    return module.QRcode(bot)


def test_qrcode_gen_creates_decodable_png(qr_cog: Any, tmp_cwd: Any) -> None:
    qr_cog.qrcode_gen(URL, "1234")

    path = tmp_cwd / "data" / "temp" / "qrcode_1234.png"

    assert path.exists()
    assert [item.data.decode() for item in decode(Image.open(path))] == [URL]


@pytest.mark.asyncio
async def test_img_sends_file_and_removes_temp_file(
    qr_cog: Any, module: Any, ctx_factory: Any, tmp_cwd: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeFile:
        """用假的 File 是為了讓測試在 Windows 開發機也能跑（discord.File 會鎖住檔案）；
        正式環境是 Linux，`cmds/qrcode.py` 的實作在那邊沒有問題。"""

        def __init__(self, fp: Any, filename: str | None = None, **kwargs: Any) -> None:
            self.fp = fp
            self.filename = filename

    monkeypatch.setattr(module.discord, "File", FakeFile)
    ctx = ctx_factory()

    await qr_cog.img.callback(qr_cog, ctx, url=URL)

    kwargs = last_call(ctx.send).kwargs
    assert kwargs["file"].filename == "qrcode.png"
    assert kwargs["embed"].title == URL
    assert not (tmp_cwd / "data" / "temp" / f"qrcode_{ctx.author.id}.png").exists()


@pytest.mark.asyncio
async def test_scanner_returns_decoded_text(qr_cog: Any, ctx_factory: Any) -> None:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    attachment = SimpleNamespace(content_type="image/png", read=AsyncMock(return_value=_qr_png(URL)))
    ctx = ctx_factory()

    await qr_cog.scanner.callback(qr_cog, ctx, image=attachment)

    ctx.send.assert_awaited_once()
    assert last_call(ctx.send).kwargs["embed"].description == URL


@pytest.mark.asyncio
async def test_scanner_rejects_non_image_attachment(qr_cog: Any, ctx_factory: Any) -> None:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    attachment = SimpleNamespace(content_type="text/plain", read=AsyncMock(return_value=b"hello"))
    ctx = ctx_factory()

    await qr_cog.scanner.callback(qr_cog, ctx, image=attachment)

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str)


@pytest.mark.asyncio
async def test_scanner_without_qrcode(qr_cog: Any, ctx_factory: Any) -> None:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    attachment = SimpleNamespace(content_type="image/png", read=AsyncMock(return_value=_blank_png()))
    ctx = ctx_factory()

    await qr_cog.scanner.callback(qr_cog, ctx, image=attachment)

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str)


@pytest.mark.asyncio
async def test_scanner_reports_broken_image(qr_cog: Any, ctx_factory: Any) -> None:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    attachment = SimpleNamespace(content_type="image/png", read=AsyncMock(return_value=b"not an image"))
    ctx = ctx_factory()

    await qr_cog.scanner.callback(qr_cog, ctx, image=attachment)

    ctx.send.assert_awaited_once()
    assert isinstance(last_call(ctx.send).args[0], str)
