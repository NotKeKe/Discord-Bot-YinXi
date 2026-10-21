"""`cmds/play4.py`：音樂播放指令的介面。

`cmds.play4` 會連帶 import `cmds.music_bot.play4.utils`（module 層級建立
`MyPriorityQueue`，需要 running event loop），所以只能在 async 測試內 import。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.helpers import import_cmds_module

pytest.importorskip("websockets", reason="play4 的 player.py 需要 websockets")

EXPECTED_COMMANDS = {
    "play",
    "add",
    "skip",
    "back",
    "pause",
    "resume",
    "stop",
    "loop",
    "nowplaying",
    "queue",
    "remove",
    "clear",
    "leave",
    "lyrics",
    "volume",
    "play_custom_list",
    "add_custom_list",
    "show_custom_list",
    "delete_custom_list",
    "clear_play_web",
}


@pytest.mark.asyncio
async def test_play4_registers_music_commands(bot: Any) -> None:
    play4 = import_cmds_module("cmds.play4")
    cog = play4.Music(bot)

    names = {str(command.name) for command in cog.get_commands()}

    assert EXPECTED_COMMANDS <= names


@pytest.mark.asyncio
async def test_play4_has_prefix_only_player_commands(bot: Any) -> None:
    play4 = import_cmds_module("cmds.play4")
    cog = play4.Music(bot)

    names = {str(command.name) for command in cog.get_commands()}

    assert {"show_players", "curr_player", "clear_players"} <= names


@pytest.mark.asyncio
async def test_play4_releases_priority_queue_workers(bot: Any) -> None:
    """import 後 helper 會把 `QUEUE` 的 worker tasks 收掉，不會留下 pending task。"""

    play4 = import_cmds_module("cmds.play4")
    queue = play4.utils.QUEUE

    assert all(task.cancelled() or task.done() or task.cancelling() for task in queue.workers)
