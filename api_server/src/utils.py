from urllib.parse import urlparse
import logging
from fastapi import HTTPException
from starlette.requests import HTTPConnection
from typing import Optional, TypedDict, NotRequired

from .redis_client import redis_client
from .config import DC_BOT_PASSED_KEY

from .player.player import is_player_exist

logger = logging.getLogger(__name__)

def check_DC_BOT_PASSED_KEY(key: str | None) -> bool:
    return bool(key and (DC_BOT_PASSED_KEY == key))

def is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
async def check_vaild_user_id(guild_id: str, uuid: str, user_id: str) -> bool:
    '''確認 uuid 是否來自 discord'''
    return bool(await redis_client.sismember(f'musics_player_user_ids:{guild_id}:{uuid}', user_id)) # type: ignore

class SecurityParams(TypedDict, total=False): # key optional
    guild_id: str
    uuid: str
    user_id: str
    key: Optional[str]

class SecurityCheck(TypedDict):
    player: Optional[bool]
    dc_key: Optional[bool]
    user_id: Optional[bool]

async def security_check(params: SecurityParams, to_check: SecurityCheck) -> bool:
    guild_id = params.get('guild_id', '')
    uuid = params.get('uuid', '')
    user_id = params.get('user_id', '')
    key = params.get('key', '')

    if to_check.get('player', False):
        if not is_player_exist(guild_id, uuid):
            raise HTTPException(status_code=404, detail=f"Player not found, guild_id: {guild_id}")

    if to_check.get('dc_key', False):
        if not check_DC_BOT_PASSED_KEY(key):
            raise HTTPException(status_code=401, detail="Invalid API key")

    if to_check.get('user_id', False):
        if not await check_vaild_user_id(guild_id, uuid, user_id):
            raise HTTPException(status_code=401, detail=f"Invalid user_id: `{user_id}`")

    return True

def get_client_ip(websocket: HTTPConnection) -> Optional[str]:
    if websocket.client:
        host = websocket.client.host
        if host != '127.0.0.1' and not host.startswith('172.26'):
            return f"{host}:{websocket.client.port}"

    if forwarded := websocket.headers.get("x-forwarded-for") or websocket.headers.get('X-Forwarded-For'):
        # X-Forwarded-For 可能包含多個代理 IP，第一個通常是真實 Client IP
        real_ip = forwarded.split(",")[0]
        return real_ip
        

async def close_event():
    try:
        await redis_client.close()
        logger.info("Successfully closed redis client")
    except Exception:
        logger.error("Cannot closing redis client", exc_info=True)

    try:
        from src.player.player import HTTPX_CLIENT
        await HTTPX_CLIENT.aclose()
        logger.info("Successfully closed src.player.player httpx client")
    except Exception:
        logger.error("Cannot closing src.player.player httpx client", exc_info=True)

    try:
        from src.tasks import close_all_tasks
        await close_all_tasks()
        logger.info("Successfully closed all tasks")
    except Exception:
        logger.error("Cannot closing all tasks", exc_info=True)