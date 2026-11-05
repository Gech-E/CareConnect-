"""Redis client for caching, rate limiting, and session management."""

import hmac

import redis.asyncio as aioredis
from fastapi import HTTPException

from app.core import get_settings

settings = get_settings()

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
    health_check_interval=30,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


async def limit_auth_account(email: str) -> None:
    """Throttle each account even when requests arrive through a shared BFF IP."""
    identity = hmac.digest(
        settings.JWT_SECRET_KEY.encode(), email.strip().lower().encode(), "sha256"
    ).hex()
    try:
        count, ttl = await redis_client.eval(
            RATE_LIMIT_SCRIPT, 1, f"rate-limit:account:{identity}", 60
        )
    except Exception as exc:
        raise HTTPException(
            503, "Service temporarily unavailable.", headers={"Retry-After": "30"}
        ) from exc
    if count > settings.RATE_LIMIT_AUTH_ACCOUNT_PER_MINUTE:
        raise HTTPException(
            429,
            "Too many requests. Please try again later.",
            headers={"Retry-After": str(max(int(ttl), 1))},
        )


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency returning the shared Redis client."""
    return redis_client
