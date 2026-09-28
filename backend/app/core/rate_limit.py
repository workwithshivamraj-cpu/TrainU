"""Very small in-process sliding-window rate limiter.

For a single-process local/demo deployment this is sufficient and requires no
extra infrastructure. In production this should be backed by Redis (the
connection is already available via `app.core.config.settings.REDIS_URL`) so
limits are enforced across multiple API replicas.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down and try again shortly.",
            )
        bucket.append(now)


rate_limiter = SlidingWindowRateLimiter()


def client_key(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"
