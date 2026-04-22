"""Position cache (stub for M0)."""

from __future__ import annotations

from typing import Any


class PositionCache:
    """<1s TTL cache of marginSummary + positions. Wired in M1."""

    def __init__(self, ttl_s: float = 1.0) -> None:
        self.ttl_s = ttl_s

    async def current(self) -> dict[str, Any]:
        raise NotImplementedError("PositionCache wired in M1")
