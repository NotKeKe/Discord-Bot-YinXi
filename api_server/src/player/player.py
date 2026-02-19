from __future__ import annotations

from uuid import uuid4
from httpx import AsyncClient, Limits
from collections import defaultdict

from fastapi import HTTPException

from .audio_urls import get_token

_limit = Limits(max_keepalive_connections=100, max_connections=100)
HTTPX_CLIENT = AsyncClient(limits=_limit)

players: dict[int, Player] = {}
'''用於儲存全部的 player
[guild_id, Player]
'''

class Player:
    '''用於紀錄單一 player 的狀態'''
    def __init__(self, guild_id: str, uuid: str):
        # 不變
        self.guild_id = guild_id
        self.uuid = uuid

        # 歌曲資訊
        self.title = "Waiting for Signal..."
        self.subtitle = ""
        self.audio_url = ""
        self.srts: dict[str, list] = defaultdict(list)

        # 歌曲播放狀態
        self.current_time = 0
        self.is_paused = False
        self.duration: int = 0
        
    def update_state(self, title: str | None, audio_url: str, srts: dict[str, list], duration: int, current_time: int, is_paused: bool, **kwargs):
        if title:
            self.title = title
        self.audio_url = audio_url
        self.srts = srts
        self.duration = duration
        if current_time is not None:
            self.current_time = current_time
        if is_paused is not None:
            self.is_paused = is_paused

    def get_state(self, lang: str = '', user_id: str = '') -> dict:
        '''取得給 frontend 的狀態'''
        target_srt = ''
        if lang:
            if lang in self.srts:
                target_srt = self.srts[lang]
            elif len(self.srts) > 0:
                # find first lang
                target_srt = self.srts[list(self.srts.keys())[0]]
            
        return {
            "uuid": self.uuid,
            "title": self.title,
            "audio_url": f'/api/player/stream?token={get_token(self.audio_url, self.guild_id)}&guild_id={self.guild_id}&uuid={self.uuid}&user_id={user_id}',
            "srt_content": target_srt,
            'languages': list(self.srts.keys()),
            'current_time': self.current_time,
            'is_paused': self.is_paused,
            'duration': self.duration
        }

def is_player_exist(guild_id: str, uuid: str = '') -> bool:
    player = players.get(int(guild_id))
    if not player:
        return False
    if uuid and player.uuid != uuid:
        return False
    return True

def get_player(guild_id: str) -> Player | None:
    '''用於檢查 player 是否存在，同時也可以使用 player 實例'''
    return players.get(int(guild_id))

def get_or_create_player(guild_id: str, uuid: str) -> Player:
    '''用於在 /upload_song 時創建 player，也可以避免重複創建'''
    player = players.get(int(guild_id))
    if not player:
        player = Player(guild_id, uuid)
        players[int(guild_id)] = player
    else:
        if player.uuid != uuid: # player exist, but request the wrong uuid
            raise HTTPException(status_code=400, detail=f"Session not found, guild_id: {guild_id}, uuid: {uuid}")

    return player

def delete_player(guild_id: str):
    players.pop(int(guild_id))