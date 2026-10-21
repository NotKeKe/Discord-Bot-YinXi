"""`cmds/apiCog.py`：外部 API 指令的介面（不呼叫任何 API）。"""

from __future__ import annotations

import importlib
from typing import Any

import pytest


@pytest.fixture
def module() -> Any:
    return importlib.import_module("cmds.apiCog")


@pytest.fixture
def cog(module: Any, bot: Any) -> Any:
    return module.ApiCog(bot)


def test_commands_with_choices_expose_them(cog: Any) -> None:
    by_name = {str(command.name): command for command in cog.get_commands()}

    for name in ("news", "minecraft_server_status"):
        parameters = by_name[name].app_command.parameters
        assert any(parameter.choices for parameter in parameters), f"{name} 應該有 choices"


def test_yt_downloader_is_restricted_to_testing_guild(cog: Any) -> None:
    by_name = {str(command.name): command for command in cog.get_commands()}

    guild_ids = getattr(by_name["yt_downloader"].app_command, "_guild_ids", None)
    assert guild_ids


def test_all_commands_have_descriptions(cog: Any) -> None:
    for command in cog.get_commands():
        assert command.app_command.description, f"{command.name} 缺少 description"
