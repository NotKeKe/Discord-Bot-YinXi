"""pytest 共用 fixture。

這個檔案在 test module 被 import 之前載入，所以 module 頂層先補上
`cmds.*` / `core.*` import 時需要的環境變數預設值，
讓沒有 `.env` 的機器也能完成 collection。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_ENV_DEFAULTS = {
    "DISCORD_TOKEN": "test-token",
    "KeJC_ID": "0",
    "tmp_hypixel_api_key": "test-hypixel-key",
    "MONGO_USER": "test",
    "MONGO_PASSWORD": "test",
    "news_api_KEY": "test-news-key",
    "nasa_api_KEY": "test-nasa-key",
    "unsplash_api_access_KEY": "test-unsplash-key",
    "GIPHY_KEY": "test-giphy-key",
    "GENIUS_ACCESS_TOKEN": "test-genius-token",
    # `cmds/ai_chat/utils/client.py` 會在 import 時替所有 provider 建 OpenAI client，
    # 少任何一個 key 都會在 collection 階段炸掉（CI 沒有 .env，所以這裡一定要補齊）。
    "zhipuAI_KEY": "test-zhipu-key",
    "openrouter_KEY": "test-openrouter-key",
    "huggingFace_KEY": "test-huggingface-key",
    "gemini_KEY": "test-gemini-key",
    "cerebras_KEY": "test-cerebras-key",
    "ai_local_KEY": "test-ai-local-key",
    "yinxi_base_url": "https://example.invalid",
}

for _key, _value in _ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import json
from typing import Any, Callable, Iterator
from unittest.mock import AsyncMock

import discord
import orjson
import pytest
import pytest_asyncio
from discord.ext import commands

from core import classes
from core.translator import i18n

from tests.helpers import RecordingBot, make_ctx

LOCALES_DIR = PROJECT_ROOT / "core" / "locales"
LOCALES = ("en-US", "zh-TW", "zh-CN")

# 乾淨 checkout（CI）沒有 .gitignore 掉的資料檔，但有些模組在 import 時就會讀：
# - core/functions.py 需要 ./cmds/data.json/admins.json，否則 `admins` 不會被定義
# - cmds/testtemp.py 在 import 時會 open('./setting.json')
_DATA_DIR = PROJECT_ROOT / "cmds" / "data.json"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_ADMINS_FILE = _DATA_DIR / "admins.json"
if not _ADMINS_FILE.exists():
    _ADMINS_FILE.write_text('{"admins": []}', encoding="utf-8")

_SETTING_FILE = PROJECT_ROOT / "setting.json"
if not _SETTING_FILE.exists():
    _SETTING_FILE.write_text(
        json.dumps(
            {
                "testing_guildID": 123456789,
                "DEVICE_IP": "127.0.0.1",
                "OLLAMA_IP": "127.0.0.1",
                "AI_IP": "127.0.0.1",
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture(scope="session")
def translations() -> dict[str, dict[str, Any]]:
    """直接讀 `core/locales/*.json`，避免每個測試都重跑 `i18n.load()`。"""

    data: dict[str, dict[str, Any]] = {}
    for lang in LOCALES:
        locale_file = LOCALES_DIR / f"{lang}.json"
        if not locale_file.exists():
            pytest.skip(f"缺少 locale 檔: {locale_file}")
        data[lang] = orjson.loads(locale_file.read_bytes())
    return data


@pytest.fixture
def translator(translations: dict[str, dict[str, Any]]) -> i18n:
    """每個測試一份。

    `commands.Client.close()` 會呼叫 `i18n.unload()` 清空 `translations`，
    所以不能讓多個測試共用同一個 dict（會把 session 快取也清掉）。
    """

    instance = i18n()
    instance.translations = dict(translations)
    instance.load = AsyncMock()  # type: ignore[method-assign]
    return instance


@pytest_asyncio.fixture
async def bot(translator: i18n) -> Any:
    """真的 `commands.Bot`（不連線），讓 `get_translate` / `load_translated` 走真實 locale。"""

    instance = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    await instance.tree.set_translator(translator)

    previous = classes.get_bot()
    classes.set_bot(instance)
    try:
        yield instance
    finally:
        classes.set_bot(previous)
        await instance.close()


@pytest.fixture
def fake_bot() -> RecordingBot:
    return RecordingBot()


@pytest.fixture
def ctx_factory(bot: Any) -> Callable[..., Any]:
    def factory(**kwargs: Any) -> Any:
        return make_ctx(bot, **kwargs)

    return factory


@pytest.fixture
def tmp_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把工作目錄換到 tmp，並建立程式會用到的 `data/` 子目錄。"""

    (tmp_path / "data" / "temp").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "upload").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path
