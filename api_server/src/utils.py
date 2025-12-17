from urllib.parse import urlparse

from .redis_client import redis_client
from .config import PLAY_WEBSITE_KEY

def is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
async def check_vaild_uuid(guild_id: str, uuid: str) -> bool:
    '''確認 uuid 是否來自 discord'''
    return bool(await redis_client.sismember('musics_player_ids', f'{guild_id}:{uuid}')) # type: ignore

async def check_vaild_PLAY_WEBSITE_KEY(KEY: str) -> bool: # 想不到更好的做法
    return PLAY_WEBSITE_KEY == KEY