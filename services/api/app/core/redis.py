"""Redis client for caching, rate limiting, and session management."""

import redis.asyncio as aioredis

from app.core import get_settings

settings = get_settings()

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency returning the shared Redis client."""
    return redis_client
