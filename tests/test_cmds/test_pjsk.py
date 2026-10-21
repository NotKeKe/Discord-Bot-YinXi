"""`cmds/pjsk.py`：歌曲資訊 embed 的組裝。"""

from __future__ import annotations

import importlib
import re
from typing import Any

ITEM = {
    "songName": "Test Song",
    "musicChartUrl": {"EASY": "https://sekai.best/easy", "NORMAL": "https://sekai.best/normal"},
    "musicDifficulty": {
        "EASY": {"level": 5, "noteCount": 100},
        "NORMAL": {"level": 10, "noteCount": 250},
    },
    "imageUrl": "https://sekai.best/cover.png",
    "musicVideoUrl": "https://youtu.be/video",
    "musicTag": ["tag-1", "tag-2"],
    "publishAt": 1700000000,
    "lyricist": "Lyricist",
    "composer": "Composer",
    "arranger": "Arranger",
}

TEMPLATE = (
    "{song_name}|{difficulty}|{image_url}|{video_url}|{music_tag}|{publish_at}|"
    "{lyricist}|{composer}|{arranger}"
)


def test_get_descrip_of_info_embed() -> None:
    module = importlib.import_module("cmds.pjsk")
    descrips: list[str] = []

    module.get_descrip_of_info_embed(ITEM, descrips, TEMPLATE)

    assert len(descrips) == 1
    rendered = descrips[0]
    assert rendered.startswith("Test Song|")
    assert "[EASY](https://sekai.best/easy) | Lv.5 | 🎵 100" in rendered
    assert "[NORMAL](https://sekai.best/normal) | Lv.10 | 🎵 250" in rendered
    assert "tag-1\ntag-2" in rendered
    assert rendered.endswith("|Lyricist|Composer|Arranger")
    assert re.search(r"\|2023-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\|", rendered)


def test_get_descrip_of_info_embed_appends() -> None:
    module = importlib.import_module("cmds.pjsk")
    descrips = ["existing"]

    module.get_descrip_of_info_embed(ITEM, descrips, TEMPLATE)

    assert len(descrips) == 2
    assert descrips[0] == "existing"
