"""`cmds/skyblock_main.py`：Hypixel SkyBlock 指令（只測不連網的部分）。"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / "setting.json").exists(),
    reason="skyblock_main 在 import 時會讀 setting.json",
)


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.skyblock_main")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("§aGreen", "Green"),
        ("§e§lLegendary", "Legendary"),
        ("no-codes", "no-codes"),
        ("§x§F§F§0§0§0§0Color", "Color"),
        ("", ""),
    ],
)
def test_remove_color_codes(module: Any, raw: str, expected: str) -> None:
    assert module.remove_color_codes(raw) == expected


def test_get_dict_forwards_events(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    events = {"upcoming": [{"name": "Fishing Festival"}]}
    monkeypatch.setattr(module.skyblock_events, "show_next_events", lambda: events)

    assert module.get_dict() == events
