from redis.asyncio import ConnectionPool, Redis

from .config import REDIS as REDIS_CONFIG

pool = ConnectionPool(
    **REDIS_CONFIG,
    db=0,
    max_connections=50,
    decode_responses=True,
)

redis_client = Redis(connection_pool=pool)