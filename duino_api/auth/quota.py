"""
Duino API — Rate Limiter
Sliding-window quota enforcement backed by Redis.
Falls back to in-memory counters when Redis is unavailable.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from duino_api.config import settings


@dataclass
class QuotaTier:
    name: str
    rpm: int          # requests per minute
    rph: int          # requests per hour
    rpd: int          # requests per day
    max_tokens: int   # max tokens per single request
    burst: int        # max concurrent requests


TIERS: dict[str, QuotaTier] = {
    "free": QuotaTier("free", rpm=10,  rph=100,   rpd=500,    max_tokens=512,  burst=2),
    "pro":  QuotaTier("pro",  rpm=60,  rph=1_000, rpd=10_000, max_tokens=4096, burst=10),
    "enterprise": QuotaTier(
        "enterprise", rpm=300, rph=10_000, rpd=100_000, max_tokens=8192, burst=50
    ),
}


class RateLimitExceeded(Exception):
    def __init__(self, window: str, limit: int, current: int):
        self.window = window
        self.limit = limit
        self.current = current
        super().__init__(f"Rate limit exceeded ({window}: {current}/{limit})")


# ─── Redis sliding-window ─────────────────────────────────────────────────────

class RedisRateLimiter:
    def __init__(self, redis):
        self._r = redis

    async def check(self, key_id: str, tier: QuotaTier) -> dict:
        """
        Check quota. Raises RateLimitExceeded if over limit.
        Returns remaining counts.
        """
        now = time.time()
        windows = {
            "minute": (60, tier.rpm),
            "hour":   (3600, tier.rph),
            "day":    (86400, tier.rpd),
        }

        pipe = self._r.pipeline()
        for window_name, (window_sec, _) in windows.items():
            rk = f"rl:{key_id}:{window_name}"
            pipe.zremrangebyscore(rk, 0, now - window_sec)
            pipe.zcard(rk)
            pipe.zadd(rk, {str(now): now})
            pipe.expire(rk, window_sec)

        results = await pipe.execute()
        remaining = {}

        for i, (window_name, (_, limit)) in enumerate(windows.items()):
            count = results[i * 4 + 1]
            if count >= limit:
                raise RateLimitExceeded(window_name, limit, count)
            remaining[window_name] = limit - count

        return remaining


# ─── In-memory fallback ───────────────────────────────────────────────────────

class InMemoryRateLimiter:
    """Notebook-mode fallback — per-process, no cross-instance sharing."""

    def __init__(self):
        self._windows: dict[str, list[float]] = {}

    async def check(self, key_id: str, tier: QuotaTier) -> dict:
        now = time.time()
        windows = {
            "minute": (60, tier.rpm),
            "hour":   (3600, tier.rph),
            "day":    (86400, tier.rpd),
        }
        remaining = {}
        for window_name, (window_sec, limit) in windows.items():
            k = f"{key_id}:{window_name}"
            self._windows.setdefault(k, [])
            cutoff = now - window_sec
            self._windows[k] = [t for t in self._windows[k] if t > cutoff]
            count = len(self._windows[k])
            if count >= limit:
                raise RateLimitExceeded(window_name, limit, count)
            self._windows[k].append(now)
            remaining[window_name] = limit - count - 1
        return remaining
