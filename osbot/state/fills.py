"""FillEventsManager (stub for M0).

Designed per XEMM Pacifica-HL 5-layer fill-detection pipeline (REST + WS + retry
+ post-hedge verification) and vnpy-hyperliquid's `userEvents` ↔ `userFills`
dedup via bounded tid set. M1 wires the read-only path; M2 the write path.
"""

from __future__ import annotations

from collections import deque
from typing import Any


class FillEventsManager:
    def __init__(self, dedup_capacity: int = 4096) -> None:
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
        raise NotImplementedError("Fill reconciliation wired in M1")
