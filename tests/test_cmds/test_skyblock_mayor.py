"""`cmds/skyblock_mayor.py`：市長更新指令（只測不連網的部分）。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / "setting.json").exists(),
    reason="skyblock_mayor 在 import 時會讀 setting.json",
)

CHANNELS_FILE = "cmds/data.json/skyblock_events_channels.json"


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.skyblock_mayor")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("§aGreen", "Green"),
        ("§e§lLegendary", "Legendary"),
        ("plain", "plain"),
    ],
)
def test_remove_color_codes(module: Any, raw: str, expected: str) -> None:
    assert module.remove_color_codes(raw) == expected


def test_remove_events_channel_removes_key(module: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / CHANNELS_FILE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"123": {"channel": "x"}, "456": {"channel": "y"}}), encoding="utf-8")
    monkeypatch.setattr(module, "current_directory", str(tmp_path))

    assert module.remove_events_channel(123) is True
    assert json.loads(target.read_text(encoding="utf-8")) == {"456": {"channel": "y"}}


def test_remove_events_channel_missing_key(module: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / CHANNELS_FILE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"456": {"channel": "y"}}), encoding="utf-8")
    monkeypatch.setattr(module, "current_directory", str(tmp_path))

    assert module.remove_events_channel(123) is False
    assert json.loads(target.read_text(encoding="utf-8")) == {"456": {"channel": "y"}}
