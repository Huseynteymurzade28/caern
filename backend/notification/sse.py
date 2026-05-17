"""Server-Sent Events broadcast via Redis pub/sub."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

import redis.asyncio as aioredis

from common_utils.config import settings
from common_utils.logger import get_logger

log = get_logger(__name__)

_redis_pool: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


def _channel(job_id: str) -> str:
    return f"job_progress:{job_id}"


async def broadcast_progress(job_id: str, progress: float, message: str = "") -> None:
    """Publish progress event to Redis channel."""
    payload = json.dumps({"progress": progress, "message": message})
    try:
        await _get_redis().publish(_channel(job_id), payload)
    except Exception as exc:
        log.warning("sse_publish_failed", job_id=job_id, exc=str(exc))


async def stream_progress(job_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings from Redis pub/sub."""
    redis = _get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(_channel(job_id))

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            yield f"data: {data}\n\n"
            parsed = json.loads(data)
            if parsed.get("progress", 0) >= 100 or "FAILED" in parsed.get("message", ""):
                break
    finally:
        await pubsub.unsubscribe(_channel(job_id))
        await pubsub.close()
