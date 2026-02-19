from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from pathlib import Path

from src.websocket.player import web_player_connection_manager
from src.websocket.dc.player import dc_player_connection_manager
from src.utils import security_check

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/player'
)

MUSIC_DIR = Path(__file__).parent.parent / "static" / "player" / "musics"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory="templates")

@router.get("/{guild_id}_{uuid}", response_class=HTMLResponse)
async def player_page(request: Request, guild_id: str, uuid: str, user_id: str):
    '''用於獲取播放器頁面'''
    await security_check(
        params={
            'guild_id': guild_id,
            'uuid': uuid,
            'user_id': user_id
        },
        to_check={
            'player': True,
            'dc_key': False,
            'user_id': True
        }
    )

    return templates.TemplateResponse("player.html", {
        "request": request, 
        "guild_id": guild_id,
        'uuid': uuid,
        'user_id': user_id
    })

@router.websocket("/{guild_id}_{uuid}")
async def websocket_endpoint(websocket: WebSocket, guild_id: str, uuid: str, user_id: str):
    await security_check(
        params={
            'guild_id': guild_id,
            'uuid': uuid,
            'user_id': user_id,
        },
        to_check={
            'player': True,
            'dc_key': False,
            'user_id': True
        }
    )
    
    await web_player_connection_manager.connect(websocket, guild_id, uuid, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "set_lang":
                web_player_connection_manager.set_user_lang(guild_id, user_id, data.get("payload"))
    except WebSocketDisconnect:
        await web_player_connection_manager.disconnect(guild_id, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for guild {guild_id}: {e}")
        await web_player_connection_manager.disconnect(guild_id, user_id)

@router.websocket("/dc/{guild_id}/{uuid}")
async def ws_player(websocket: WebSocket, guild_id: str, uuid: str):
    await security_check(
        params={
            'guild_id': guild_id,
            'uuid': uuid,
            'key': websocket.headers.get('DC-BOT-API-KEY')
        },
        to_check={
            'player': False,
            'dc_key': True,
            'user_id': False
        }
    )

    await dc_player_connection_manager.connect(websocket, guild_id, uuid)

@router.get('/test')
async def test():
    from src.player.player import players

    return {
        'players': [{'guild_id': p.guild_id, 'uuid': p.uuid} for p in players.values()]
    }