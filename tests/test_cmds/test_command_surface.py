"""`cmds/` 指令介面（指令名稱、aliases、app command、listener）的回歸測試。

命令名稱是「真的會被 Discord 看到」的介面，改名或漏註冊都應該被這裡擋下來。
期望值以目前的程式碼為基準（locale_str 的 key 就是註冊名稱）。
"""

from __future__ import annotations

from typing import Any

import pytest
from discord.ext import commands

from tests.helpers import (
    app_command_names,
    import_cmds_module,
    listener_names,
    prefix_command_names,
)

# module -> {cog, commands, app_commands, aliases, listeners}
SURFACE: dict[str, dict[str, Any]] = {
    "cmds.ai_channel_two": {
        "cog": "AIChannelTwo",
        "commands": {
            "set_ai_channel",
            "cancel_ai_channel",
            "change_ai_channel_model",
            "change_ai_channel_system_prompt",
            "show_ai_channel_model",
            "set_chat_human",
            "cancel_chat_human",
        },
        "listeners": {"on_message"},
    },
    "cmds.ai_three": {
        "cog": "AIChat",
        "commands": {"chat", "image_generate", "video_generate"},
        "listeners": {"on_ready"},
    },
    "cmds.apiCog": {
        "cog": "ApiCog",
        "commands": {
            "joke",
            "news",
            "cat_fact",
            "nasa",
            "number_history",
            "unsplash_image",
            "get_gifs",
            "tiangou",
            "minecraft_server_status",
            "yiyan",
            "toxic_jacket_soup",
            "lovelive",
            "yt_downloader",
            "codlin_meme",
        },
        "aliases": {
            "joke": {"jokes"},
            "news": {"新聞"},
            "cat_fact": {"貓貓冷知識", "cat", "catfact"},
            "nasa": {"nasa每日圖片"},
            "number_history": {"num_history", "n_history"},
            "unsplash_image": {"photo", "image", "看圖"},
            "get_gifs": {"gif"},
            "tiangou": {"舔狗"},
            "minecraft_server_status": {"mc_status"},
            "yiyan": {"一言"},
            "toxic_jacket_soup": {"毒雞湯"},
            "lovelive": {"love"},
            "yt_downloader": {"yt_download", "ytdownload", "影片下載"},
            "codlin_meme": {"meme", "codlin"},
        },
        "listeners": set(),
    },
    "cmds.bot_info_help": {
        "cog": "BotInfoAndHelp",
        "commands": {"botinfo", "help"},
        "aliases": {"help": {"helping"}},
        "listeners": {"on_ready"},
    },
    "cmds.bot_status": {
        "cog": "Status",
        "commands": {"change_status_str"},
        "listeners": set(),
    },
    "cmds.cambridge_channel": {
        "cog": "CambridgeChannel",
        "commands": {"cambridge_channel", "daily_test", "test_daily_test"},
        "listeners": {"on_message"},
    },
    "cmds.channel_history": {
        "cog": "ChannelHistory",
        "commands": {"output_chat_history"},
        "listeners": set(),
    },
    "cmds.counting": {
        "cog": "Counting",
        "commands": {"counting"},
        "aliases": {"counting": {"count"}},
        "listeners": {"on_message", "on_ready"},
    },
    "cmds.error": {
        "cog": "ErrorHandler",
        "commands": {"errorresponse"},
        "listeners": set(),
    },
    "cmds.giveaway2": {
        "cog": "Giveaway2",
        "commands": {"giveaway"},
        "listeners": {"on_ready"},
    },
    "cmds.join_leave_guild": {
        "cog": "OnJoinLeave",
        "commands": {"join_leave_message", "delete_spam_messages"},
        "listeners": {"on_guild_join", "on_member_join", "on_member_remove", "on_ready"},
    },
    "cmds.keep": {
        "cog": "Keep",
        "commands": {"check_keepdata"},
        "app_commands": {"keep", "keep_frequency", "del_keep", "show_keep"},
        "listeners": {"on_ready"},
    },
    "cmds.load": {
        "cog": "Load",
        "commands": {
            "reload",
            "全部重載",
            "重載sync",
            "reload_all",
            "restart",
            "清除日誌",
            "系統指令",
            "del_msg",
        },
        "listeners": {"on_ready"},
    },
    "cmds.main": {
        "cog": "Main",
        "commands": {
            "owner_id",
            "ping",
            "avatar",
            "get_system_channel",
            "add_admin",
            "server_info",
            "convert_timestamp",
            "tw_high_school_score_calculator",
            "lang",
            "image_to_base64",
            "random_uuid",
            "petpet",
        },
        "aliases": {"owner_id": {"ownerid"}},
        "listeners": set(),
    },
    "cmds.pjsk": {
        "cog": "PJSK",
        "commands": {"pjsk_new_song", "pjsk_search_song", "pjsk_new_song_notify"},
        "listeners": set(),
    },
    "cmds.qrcode": {
        "cog": "QRcode",
        "commands": {"qrcode_generator", "qrcode_scanner"},
        "aliases": {"qrcode_generator": {"qr", "QR", "qrcode"}},
        "listeners": {"on_ready"},
    },
    "cmds.skyblock_main": {
        "cog": "skyblock_main",
        "commands": {
            "uuid",
            "test_apikey",
            "status",
            "guild_name",
            "mayor",
            "events",
            "hypixel_game_count",
            "auction",
        },
        "listeners": {"on_ready"},
    },
    "cmds.skyblock_mayor": {
        "cog": "skyblock_mayor",
        "commands": {"開始mayor更新", "停止mayor更新"},
        "aliases": {"開始mayor更新": {"start_mayor"}, "停止mayor更新": {"stop_mayor"}},
        "listeners": set(),
    },
    "cmds.sub_yt": {
        "cog": "SubYT",
        "commands": {"sub_yt", "sub_yt_cancel", "sub_yt_list"},
        "listeners": set(),
    },
    "cmds.suggest_report": {
        "cog": "SuggestReport",
        "commands": {"suggest", "report", "report_trace", "set_report_status"},
        "aliases": {"report": {"error"}},
        "listeners": {"on_ready"},
    },
    "cmds.testtemp": {
        "cog": "TestTemp",
        "commands": {
            "testtemp",
            "取得所有指令名稱",
            "embedtest",
            "get_cog_name",
            "get_command_name",
            "errortest",
            "systemchannel",
            "fromidtoname",
            "getguildid",
            "buttontest",
            "cmd",
            "membernametest",
            "getchannels",
            "mytest",
        },
        "listeners": {"on_ready"},
    },
    "cmds.tic_tac_toe": {
        "cog": "TicTacToe",
        "commands": {"tictactoe"},
        "listeners": {"on_interaction", "on_ready"},
    },
    "cmds.total_stats": {
        "cog": "BotStats",
        "commands": {"machine_stats", "num_guilds"},
        "app_commands": {"bot_stats"},
        "listeners": {
            "on_app_command_completion",
            "on_command",
            "on_command_completion",
            "on_command_error",
            "on_ready",
        },
    },
    "cmds.translator": {
        "cog": "Translator",
        "commands": {"translate"},
        "listeners": {"on_ready"},
    },
    "cmds.world_chat": {
        "cog": "WorldChat",
        "commands": {"world_chat", "report_bad_image"},
        "listeners": {"on_message", "on_ready"},
    },
    "cmds.x_downloader": {
        "cog": "XDownloader",
        "commands": {"x_download"},
        "listeners": set(),
    },
}


def _param(module_name: str) -> Any:
    marks = []
    if module_name in {"cmds.skyblock_main", "cmds.skyblock_mayor"}:
        from pathlib import Path

        if not (Path(__file__).resolve().parents[2] / "setting.json").exists():
            marks.append(pytest.mark.skip(reason="缺少 setting.json，這個模組無法 import"))
    return pytest.param(module_name, id=module_name, marks=marks)


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SURFACE])
async def test_prefix_and_hybrid_command_names(module_name: str, bot: Any) -> None:
    spec = SURFACE[module_name]
    module = import_cmds_module(module_name)
    cog = getattr(module, spec["cog"])(bot)

    assert prefix_command_names(cog) == spec["commands"]


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SURFACE])
async def test_app_only_commands(module_name: str, bot: Any) -> None:
    spec = SURFACE[module_name]
    module = import_cmds_module(module_name)
    cog_class = getattr(module, spec["cog"])

    assert app_command_names(cog_class) == spec.get("app_commands", set())


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SURFACE])
async def test_command_aliases(module_name: str, bot: Any) -> None:
    spec = SURFACE[module_name]
    module = import_cmds_module(module_name)
    cog = getattr(module, spec["cog"])(bot)
    by_name = {str(command.name): command for command in cog.get_commands()}

    for name, expected_aliases in spec.get("aliases", {}).items():
        assert name in by_name, f"{module_name} 缺少指令 {name}"
        assert set(by_name[name].aliases) == expected_aliases


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SURFACE])
async def test_listeners(module_name: str, bot: Any) -> None:
    spec = SURFACE[module_name]
    module = import_cmds_module(module_name)
    cog_class = getattr(module, spec["cog"])

    assert listener_names(cog_class) == spec["listeners"]


@pytest.mark.asyncio
@pytest.mark.parametrize("module_name", [_param(name) for name in SURFACE])
async def test_hybrid_commands_have_matching_app_commands(module_name: str, bot: Any) -> None:
    spec = SURFACE[module_name]
    module = import_cmds_module(module_name)
    cog = getattr(module, spec["cog"])(bot)

    for command in cog.get_commands():
        assert isinstance(command.name, str), f"{module_name}: 指令名稱不該是 {type(command.name)}"
        if isinstance(command, commands.HybridCommand):
            assert command.app_command.name == command.name
            assert command.app_command.description
