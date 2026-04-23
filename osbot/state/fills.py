"""FillEventsManager.

Designed per XEMM Pacifica-HL 5-layer fill-detection pipeline (REST + WS + retry
+ post-hedge verification) and vnpy-hyperliquid's `userEvents` ↔ `userFills`
dedup via bounded tid set. M1 wires the REST-only read path; M2 adds WS + write.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from osbot.connector.hl_client import HLClient


class FillEventsManager:
    def __init__(self, client: HLClient | None = None, dedup_capacity: int = 4096) -> None:
        self._client = client
        self._seen_tids: deque[str] = deque(maxlen=dedup_capacity)
        self._seen_set: set[str] = set()

    def is_new(self, tid: str) -> bool:
        if tid in self._seen_set:
            return False
        if len(self._seen_tids) == self._seen_tids.maxlen:
            evicted = self._seen_tids[0]
            self._seen_set.discard(evicted)
        self._seen_tids.append(tid)
        self._seen_set.add(tid)
        return True

    async def reconcile(self) -> list[dict[str, Any]]:
        """REST-only reconciliation: fetch fills, return only the new ones."""
        if self._client is None:
            raise RuntimeError("FillEventsManager has no HLClient; cannot reconcile")
        fills = await self._client.user_fills()
        new_fills: list[dict[str, Any]] = []
        for fill in fills:
            tid = str(fill.get("tid", ""))
            if tid and self.is_new(tid):
                new_fills.append(fill)
        return new_fills
