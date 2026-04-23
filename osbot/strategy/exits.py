"""TripleBarrier exit evaluator.

For each open position, decide whether to close based on:
  - TP: mid crossed entry ± tp_pct
  - SL: mid crossed entry ± sl_pct
  - Time: position older than ttl_s

The `consecutive_breaches_required` gate (senpi-skills pattern) guards the
trailing/SL trigger against whipsaw: the breach must persist across N ticks
before firing. TP and TTL fire immediately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class PositionExitState:
    entry_price: float
    size: float
    side: str  # "long" | "short"
    opened_ts: float = field(default_factory=time.time)
    breach_count: int = 0


@dataclass
class ExitDecision:
    should_exit: bool
    reason: str


class TripleBarrier:
    def __init__(
        self,
        sl_pct: float,
        tp_pct: float,
        ttl_s: float,
        consecutive_breaches_required: int = 2,
    ) -> None:
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.ttl_s = ttl_s
        self.consecutive_breaches_required = consecutive_breaches_required

    def evaluate(
        self, pos: PositionExitState, mid: float, now: float | None = None
    ) -> ExitDecision:
        now = now if now is not None else time.time()
        if pos.entry_price <= 0 or mid <= 0:
            return ExitDecision(False, "invalid-price")
        if (now - pos.opened_ts) >= self.ttl_s:
            return ExitDecision(True, "ttl")

        delta_pct = (mid - pos.entry_price) / pos.entry_price
        is_long = pos.side == "long"
        tp_hit = delta_pct >= self.tp_pct if is_long else delta_pct <= -self.tp_pct
        sl_hit = delta_pct <= -self.sl_pct if is_long else delta_pct >= self.sl_pct

        if tp_hit:
            return ExitDecision(True, "tp")
        if sl_hit:
            pos.breach_count += 1
            if pos.breach_count >= self.consecutive_breaches_required:
                return ExitDecision(True, "sl")
            return ExitDecision(False, "sl-pending")

        pos.breach_count = 0
        return ExitDecision(False, "hold")

    # Back-compat stub.
    def should_exit(self, entry_price: float, mid: float, age_s: float) -> bool:
        pos = PositionExitState(entry_price=entry_price, size=0, side="long", opened_ts=0.0)
        return self.evaluate(pos, mid, now=age_s).should_exit
