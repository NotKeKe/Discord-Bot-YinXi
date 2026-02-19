from fastapi import WebSocket
import asyncio
from typing import TypedDict
import logging

from src.tasks import add_task
from src.player.player import get_player

from src.utils import get_client_ip

logger = logging.getLogger(__name__)

item = {
    'guild_id': {
        'uuid': '',
        'connections': {
            'user_id': WebSocket
        }
    }
}
del item

class RowConnection(TypedDict):
    ws: WebSocket
    lang: str

class RowGuildIDConnection(TypedDict):
    uuid: str
    connections: dict[str, RowConnection]

GuildID = str

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[GuildID, RowGuildIDConnection] = {}

    async def connect(self, websocket: WebSocket, guild_id: str, uuid: str, user_id: str):
        await websocket.accept()
        if guild_id not in self.active_connections:
            self.active_connections[guild_id] = {
                "uuid": uuid,
                "connections": {}
            }

            add_task(asyncio.create_task(
                self.run(guild_id)
            ))

        self.active_connections[guild_id]["connections"][user_id] = {
            "ws": websocket,
            "lang": "original"
        }

        logger.info(f"Web Player WS connected: guild_id={guild_id} | user_id={user_id} | ip={get_client_ip(websocket)}")
        
        # Send initial state
        player = get_player(guild_id)
        if player:
            await self.send_json(websocket, player.get_state(user_id=user_id))

    def set_user_lang(self, guild_id: str, user_id: str, lang: str):
        if guild_id in self.active_connections:
            if user_id in self.active_connections[guild_id]["connections"]:
                self.active_connections[guild_id]["connections"][user_id]["lang"] = lang
                logger.debug(f"Set lang for user {user_id} in guild {guild_id} to {lang}")

    async def disconnect(self, guild_id: str, user_id: str):
        if guild_id in self.active_connections:
            try:
                conn_info = self.active_connections[guild_id]["connections"][user_id]
                websocket = conn_info["ws"]
                ip = get_client_ip(websocket)
                await websocket.close()
                logger.info(f"Web Player WS disconnected: guild_id={guild_id} | user_id={user_id} | ip={ip}")
            except Exception:
                pass
            
            connections = self.active_connections[guild_id]["connections"]

            # 刪除 guild_id-connections-{user_id}
            connections.pop(user_id, None)
            
            # 刪除 guild_id-connections (如果空了)
            if not connections:
                self.active_connections.pop(guild_id, None)

    async def send_json(self, websocket: WebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False

    async def run(self, guild_id: str): # run for one guild
        while True:
            if guild_id not in self.active_connections: break
                
            player = get_player(guild_id)
            if player is None: break

            for user_id, conn_info in self.active_connections[guild_id]["connections"].items():
                lang = conn_info["lang"]
                state = player.get_state(lang=lang, user_id=user_id) # Get state with specific user_id and lang
                r = await self.send_json(conn_info["ws"], state)
                if not r:
                    await self.disconnect(guild_id, user_id)

            await asyncio.sleep(2)

web_player_connection_manager = ConnectionManager()
