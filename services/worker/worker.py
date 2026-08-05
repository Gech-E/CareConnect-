import os
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def send_notification(ctx, user_id: str, message: str):
    print(f"[{ctx['job_id']}] Sending notification to {user_id}: {message}")
    # Simulate network delay
    await asyncio.sleep(1)
    return True

async def startup(ctx):
    print("Worker starting up...")

async def shutdown(ctx):
    print("Worker shutting down...")

class WorkerSettings:
    functions = [send_notification]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
