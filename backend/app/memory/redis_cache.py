"""Redis client for rate limits, recommendation cache, pending exercise payloads."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    try:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
        _client.ping()
        return _client
    except redis.RedisError as e:
        logger.warning("Redis unavailable: %s — using in-memory fallback", e)
        return None


class MemoryFallback:
    """Minimal dict backend when Redis is down."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self._data[key] = value

    def incr(self, key: str) -> int:
        cur = int(self._data.get(key, "0"))
        cur += 1
        self._data[key] = str(cur)
        return cur

    def expire(self, _key: str, _ttl: int) -> None:
        pass

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


_fallback = MemoryFallback()


def rate_limit_check(student_id: uuid.UUID, bucket: str, limit_per_hour: int) -> None:
    """Raise if over limit (uses Redis INCR with TTL)."""
    from fastapi import HTTPException, status

    r = get_redis()
    key = f"rl:{bucket}:{student_id}"
    if r:
        n = r.incr(key)
        if n == 1:
            r.expire(key, 3600)
    else:
        n = _fallback.incr(key)
        _fallback.expire(key, 3600)

    if n > limit_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {bucket}",
        )


def cache_get_json(key: str) -> Any | None:
    r = get_redis()
    raw = r.get(key) if r else _fallback.get(key)
    if not raw:
        return None
    return json.loads(raw)


def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    r = get_redis()
    payload = json.dumps(value)
    if r:
        r.setex(key, ttl_seconds, payload)
    else:
        _fallback.setex(key, ttl_seconds, payload)


def pending_exercise_set(exercise_id: uuid.UUID, payload: dict, ttl_seconds: int = 7200) -> None:
    key = f"exercise:{exercise_id}"
    cache_set_json(key, payload, ttl_seconds)


def pending_exercise_get(exercise_id: uuid.UUID) -> dict | None:
    key = f"exercise:{exercise_id}"
    return cache_get_json(key)


def pending_exercise_delete(exercise_id: uuid.UUID) -> None:
    r = get_redis()
    key = f"exercise:{exercise_id}"
    if r:
        r.delete(key)
    else:
        _fallback.delete(key)
