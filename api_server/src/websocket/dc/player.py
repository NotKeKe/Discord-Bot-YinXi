from fastapi import WebSocket
import asyncio
from typing import TypedDict, Literal, Optional
import logging
from pydantic import BaseModel, ValidationError

from src.player.player import get_or_create_player, get_player, delete_player

from src.utils import get_client_ip

logger = logging.getLogger(__name__)

item = {
    'guild_id': {
        'uuid': '',
        'ws': WebSocket
    }
}
del item

class RowGuildIDConnection(TypedDict):
    uuid: str
    ws: WebSocket
GuildID = str

class DataType(BaseModel):
    guild_id: int
    uuid: str
    title: str
    audio_url: str
    duration: int
    srts: dict[str, str]
    current_time: Optional[int] = None
    is_paused: Optional[bool] = None



class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[GuildID, RowGuildIDConnection] = {}

    async def connect(self, websocket: WebSocket, guild_id: str, uuid: str):
        '''accept websocket and run'''
        await websocket.accept()
        if guild_id in self.active_connections:
            await self.disconnect(guild_id)

        self.active_connections[guild_id] = {
            "uuid": uuid,
            "ws": websocket
        }

        logger.info(f"DC Player WS connected: guild_id={guild_id} | ip={get_client_ip(websocket)}")

        await self.run(guild_id, uuid)

    async def disconnect(self, guild_id: str):
        if guild_id in self.active_connections:
            try:
                websocket = self.active_connections[guild_id]["ws"]
                ip = get_client_ip(websocket)
                await websocket.close()
                logger.info(f"DC Player WS disconnected: guild_id={guild_id} | ip={ip}")
            except Exception:
                pass
            
            self.active_connections.pop(guild_id, None)

        player = get_player(guild_id)
        if player: 
            delete_player(guild_id)

    async def run(self, guild_id: str, uuid: str): # run for one guild
        while True:
            if guild_id not in self.active_connections: break
                
            player = get_or_create_player(guild_id, uuid)

            websocket = self.active_connections[guild_id]['ws']

            try:
                data = await websocket.receive_json()
                data = DataType(**data)
            except ValidationError:
                logger.warning('Dc sent a invalid json', exc_info=True)
                continue
            except Exception:
                break

            # 更新給 player
            player.update_state(
                **data.model_dump()
            )

        await self.disconnect(guild_id)
            

dc_player_connection_manager = ConnectionManager()
