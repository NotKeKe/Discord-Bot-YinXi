"""檢查 `cmds/` 用到的 locale key，在 `core/locales/*.json` 都存在。

`get_translate()` / `locale_str()` 找不到 key 時會直接回傳 key 本身，
使用者就會在 Discord 上看到 `send_xxx` 這種字串，所以这里做靜態檢查。

key 的歸屬區塊跟 `core/translator.py` 的行為一致：
- `name=`       -> `name`
- `description=`-> `description`
- `@app_commands.describe(...)` -> `params_desc`
- `Choice(name=...)` 與其他（含 `get_translate`） -> `components`
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CMDS_DIR = PROJECT_ROOT / "cmds"
LOCALES_DIR = PROJECT_ROOT / "core" / "locales"
LOCALE_NAMES = ("en-US", "zh-TW", "zh-CN")

# `get_translate(f'keep_frequency_{freq_str}')` 這種動態組合的 key
DYNAMIC_KEYS = (
    "keep_frequency_minutely",
    "keep_frequency_hourly",
    "keep_frequency_daily",
    "keep_frequency_weekly",
    "keep_frequency_monthly",
    "keep_frequency_yearly",
)


def _call_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _classify(ancestors: list[ast.AST]) -> str:
    nearest_keyword: str | None = None
    for ancestor in ancestors:
        if isinstance(ancestor, ast.keyword) and nearest_keyword is None:
            nearest_keyword = ancestor.arg
        name = _call_name(ancestor)
        if name == "Choice":
            return "components"
        if name == "describe":
            return "params_desc"
        if name in ("hybrid_command", "command", "group"):
            if nearest_keyword == "name":
                return "name"
            if nearest_keyword == "description":
                return "description"
    return "components"


def _collect_usage() -> dict[str, dict[str, list[str]]]:
    usage: dict[str, dict[str, list[str]]] = {
        "name": {},
        "description": {},
        "params_desc": {},
        "components": {},
    }
    for path in sorted(CMDS_DIR.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def record(section: str, key: str, node: ast.Call) -> None:
            usage[section].setdefault(key, []).append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

        for node in ast.walk(tree):
            name = _call_name(node)
            if name == "get_translate" and isinstance(node, ast.Call) and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    record("components", argument.value, node)
                elif isinstance(argument, ast.JoinedStr):
                    record("components", "<f-string>", node)
            elif name == "locale_str" and isinstance(node, ast.Call) and node.args:
                argument = node.args[0]
                if not (isinstance(argument, ast.Constant) and isinstance(argument.value, str)):
                    continue
                ancestors: list[ast.AST] = []
                current: ast.AST = node
                while current in parents:
                    current = parents[current]
                    ancestors.append(current)
                record(_classify(ancestors), argument.value, node)
    return usage


USAGE = _collect_usage()


@pytest.fixture(scope="module")
def locales() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for locale_name in LOCALE_NAMES:
        path = LOCALES_DIR / f"{locale_name}.json"
        data[locale_name] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("locale_name", LOCALE_NAMES)
def test_locale_file_is_valid_json(locale_name: str) -> None:
    json.loads((LOCALES_DIR / f"{locale_name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("locale_name", LOCALE_NAMES)
@pytest.mark.parametrize("section", sorted(USAGE))
def test_cmds_keys_exist(locale_name: str, section: str, locales: dict[str, dict[str, Any]]) -> None:
    available = locales[locale_name].get(section, {})
    missing = {key: where for key, where in USAGE[section].items() if key not in available and key != "<f-string>"}

    assert not missing, f"{locale_name}.json 的 {section} 缺少: " + "; ".join(
        f"{key} ({where[0]})" for key, where in sorted(missing.items())
    )


@pytest.mark.parametrize("locale_name", LOCALE_NAMES)
def test_dynamic_keys_exist(locale_name: str, locales: dict[str, dict[str, Any]]) -> None:
    components = locales[locale_name]["components"]

    missing = [key for key in DYNAMIC_KEYS if key not in components]

    assert not missing, f"{locale_name}.json 缺少動態組合的 key: {missing}"
