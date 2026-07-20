"""Redis connection pool (async)."""

import redis.asyncio as aioredis

from config.settings import settings

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns shared Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def close_redis():
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
