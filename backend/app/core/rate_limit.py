"""Atomic Redis sliding windows across replicas; memory backend for local tests."""
from __future__ import annotations

import hashlib
import math
import time
import uuid
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock

from fastapi import HTTPException, Request
from redis import Redis, RedisError

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


_WINDOW = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - tonumber(ARGV[1]))
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return math.max(1, math.ceil(tonumber(oldest[2]) + tonumber(ARGV[1]) - now))
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[1])
return 0
"""


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        distributed = settings.RATE_LIMIT_BACKEND == "redis" or (
            settings.RATE_LIMIT_BACKEND == "auto" and settings.is_production
        )
        if distributed:
            try:
                retry_after = int(get_redis().eval(
                    _WINDOW, 1, "trainu:rl:" + hashlib.sha256(key.encode()).hexdigest(),
                    window_seconds, limit, uuid.uuid4().hex,
                ))
            except RedisError:
                raise HTTPException(503, detail="Service temporarily unavailable", headers={"Retry-After": "5"})
        else:
            with self._lock:
                now = time.monotonic()
                if len(self._hits) > 10000:
                    self._hits = defaultdict(deque, {k: v for k, v in self._hits.items() if v and now-v[-1] < window_seconds})
                bucket = self._hits[key]
                while bucket and now - bucket[0] >= window_seconds:
                    bucket.popleft()
                retry_after = max(1, math.ceil(bucket[0] + window_seconds - now)) if len(bucket) >= limit else 0
                if not retry_after:
                    bucket.append(now)
        if retry_after:
            raise HTTPException(429, detail="Rate limit exceeded. Please try again shortly.",
                                headers={"Retry-After": str(retry_after)})


rate_limiter = SlidingWindowRateLimiter()


def client_key(request: Request) -> str:
    # Proxy headers are trusted only by Uvicorn's configured proxy allowlist.
    return request.client.host if request.client else "unknown"
