"""`cmds/` 各模組的載入契約（setup / Cog 類別）。

只涵蓋「模組最底部有有效 `setup()`」的檔案：
- `cool.py` 依需求排除。
- `giveaway.py` 沒有 `setup`。
- `events_recording.py` 的 `setup` 被註解掉了。
- `play4.py` 雖然有 `setup`，但目前環境缺少 `websockets` 而無法 import
  （見 `test_play4_imports_when_websockets_available`）。
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import RecordingBot, cog_classes, import_cmds_module

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CMDS_DIR = PROJECT_ROOT / "cmds"
SETTING_JSON = PROJECT_ROOT / "setting.json"

# 有 setup 且可測試的模組 → 預期 Cog 類別名稱
SETUP_MODULES: dict[str, str] = {
    "cmds.ai_channel_two": "AIChannelTwo",
    "cmds.ai_three": "AIChat",
    "cmds.apiCog": "ApiCog",
    "cmds.bot_info_help": "BotInfoAndHelp",
    "cmds.bot_status": "Status",
    "cmds.cambridge_channel": "CambridgeChannel",
    "cmds.channel_history": "ChannelHistory",
    "cmds.counting": "Counting",
    "cmds.error": "ErrorHandler",
    "cmds.giveaway2": "Giveaway2",
    "cmds.join_leave_guild": "OnJoinLeave",
    "cmds.keep": "Keep",
    "cmds.load": "Load",
    "cmds.main": "Main",
    "cmds.pjsk": "PJSK",
    "cmds.qrcode": "QRcode",
    "cmds.skyblock_main": "skyblock_main",
    "cmds.skyblock_mayor": "skyblock_mayor",
    "cmds.sub_yt": "SubYT",
    "cmds.suggest_report": "SuggestReport",
    "cmds.testtemp": "TestTemp",
    "cmds.tic_tac_toe": "TicTacToe",
    "cmds.total_stats": "BotStats",
    "cmds.translator": "Translator",
    "cmds.world_chat": "WorldChat",
    "cmds.x_downloader": "XDownloader",
}

# 這些模組在 import 時會讀 `setting.json`，缺少時直接 skip。
SETTING_JSON_REQUIRED = {"cmds.skyblock_main", "cmds.skyblock_mayor"}

# 依需求排除 / 目前無法 import 的模組
UNTESTED_MODULES = {"cmds.cool", "cmds.play4"}


def _param(module_name: str) -> Any:
    marks = []
    if module_name in SETTING_JSON_REQUIRED and not SETTING_JSON.exists():
        marks.append(pytest.mark.skip(reason="缺少 setting.json，這個模組無法 import"))
    return pytest.param(module_name, id=module_name, marks=marks)


def _setup_modules_on_disk() -> set[str]:
    """用 AST 掃出「模組層級確實有 def setup」的檔案（不 import，避免副作用）。"""

    found: set[str] = set()
    for path in sorted(CMDS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "setup"
            for node in tree.body
        ):
            found.add(f"cmds.{path.stem}")
    return found


def test_all_setup_modules_are_covered() -> None:
    """避免之後新增模組卻忘了加測試。"""

    covered: set[str] = set(SETUP_MODULES) | UNTESTED_MODULES
    assert _setup_modules_on_disk() == covered


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SETUP_MODULES])
async def test_module_exposes_coroutine_setup(module_name: str) -> None:
    module = import_cmds_module(module_name)

    assert inspect.iscoroutinefunction(module.setup)


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SETUP_MODULES])
async def test_module_defines_expected_cog(module_name: str) -> None:
    module = import_cmds_module(module_name)
    expected_cog = SETUP_MODULES[module_name]

    classes = {cog.__name__: cog for cog in cog_classes(module)}

    assert expected_cog in classes, f"{module_name} 應該定義 {expected_cog}，實際: {sorted(classes)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SETUP_MODULES])
async def test_setup_registers_exactly_one_cog(module_name: str, fake_bot: RecordingBot) -> None:
    module = import_cmds_module(module_name)
    expected_cog = SETUP_MODULES[module_name]

    await module.setup(fake_bot)

    assert len(fake_bot.added_cogs) == 1
    registered = fake_bot.added_cogs[0]
    assert type(registered).__name__ == expected_cog
    assert list(fake_bot.cogs) == [expected_cog]


@pytest.mark.asyncio
async def test_setup_contract_does_not_start_cog_load(fake_bot: RecordingBot) -> None:
    """RecordingBot 只記錄 add_cog，不會觸發 cog_load（避免 Mongo / tasks.loop 副作用）。"""

    module = import_cmds_module("cmds.counting")

    await module.setup(fake_bot)

    assert module.Counting.storage_data_task.is_running() is False


def test_play4_imports_when_websockets_available() -> None:
    pytest.importorskip(
        "websockets",
        reason="play4 的 player.py 需要 websockets，但目前 venv 與 uv.lock 都沒有這個套件",
    )

    import cmds.play4  # noqa: F401
