"""Per-endpoint async rate limiter.

Adapted from Hummingbot's `AsyncThrottler` pattern (Apache-2.0). Vendored with
attribution per design notes §4. Token-bucket per limit-id, awaitable acquire.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimit:
    limit_id: str
    capacity: int
    period_s: float


class AsyncThrottler:
    def __init__(self, limits: list[RateLimit]) -> None:
        self._limits: dict[str, RateLimit] = {limit.limit_id: limit for limit in limits}
        self._timestamps: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def acquire(self, limit_id: str) -> None:
        limit = self._limits.get(limit_id)
        if limit is None:
            raise KeyError(f"Unknown throttler limit_id: {limit_id}")
        while True:
            async with self._lock:
                now = time.monotonic()
                window_start = now - limit.period_s
                ts = self._timestamps[limit_id]
                while ts and ts[0] < window_start:
                    ts.popleft()
                if len(ts) < limit.capacity:
                    ts.append(now)
                    return
                wait = ts[0] + limit.period_s - now
            await asyncio.sleep(max(wait, 0.001))
