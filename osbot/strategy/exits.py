"""TripleBarrier exits (stub for M0). senpi-skills two-phase trailing stop pattern.

Design: trailing stop requires `consecutive_breaches_required` consecutive ticks
past the trigger before firing — eliminates whipsaw on thin books.
"""

from __future__ import annotations


class TripleBarrier:
    def __init__(self, sl_pct: float, tp_pct: float, ttl_s: float) -> None:
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.ttl_s = ttl_s

    def should_exit(self, entry_price: float, mid: float, age_s: float) -> bool:
        raise NotImplementedError("TripleBarrier wired in M2")
