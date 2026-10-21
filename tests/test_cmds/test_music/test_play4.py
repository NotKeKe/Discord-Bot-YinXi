"""`cmds/play4.py`：音樂播放指令。

`cmds/music_bot/play4/player.py` 需要 `websockets`，但目前 venv 與 `uv.lock` 都沒有，
所以整個模組會 skip；等依賴補上後這裡會自動開始跑。
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip(
    "websockets",
    reason="play4 需要 websockets（目前未安裝且不在 uv.lock），暫時無法 import",
)


def test_play4_registers_music_commands(bot: Any) -> None:
    import cmds.play4 as play4

    cog = play4.Music(bot)
    names = {str(command.name) for command in cog.get_commands()}

    assert {"play", "skip", "stop", "queue", "lyrics"} <= names
