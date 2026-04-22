"""Order intent vocabulary + dual-ID (cloid ↔ oid) tracking.

Pattern: vnpy-hyperliquid maintains `local_id ↔ cloid ↔ oid` with three dicts and
cancels by cloid to dodge the oid-race where HL's oid hasn't propagated. We bake
that into the `OrderTag` type so every submit carries both identifiers through
the state layer.

Cloid format: 16-byte hex string prefixed `0x`, per HL spec. We encode the tag
(strategy_id + intent + level) into the first 8 bytes; the remaining 8 bytes are
a monotonic counter so two grid-level-0 re-plants never collide.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final


class OrderIntent(StrEnum):
    OPEN_GRID = "og"
    CLOSE_GRID = "cg"
    STOP_LOSS = "sl"
    TAKE_PROFIT = "tp"
    UNSTUCK = "un"


_COUNTER: itertools.count[int] = itertools.count(1)
_STRATEGY_ID_WIDTH: Final[int] = 4  # hex chars
_INTENT_WIDTH: Final[int] = 2
_LEVEL_WIDTH: Final[int] = 2
_COUNTER_WIDTH: Final[int] = 16


@dataclass(frozen=True)
class OrderTag:
    strategy_id: int
    intent: OrderIntent
    level: int

    def to_cloid(self) -> str:
        sid = f"{self.strategy_id & 0xFFFF:0{_STRATEGY_ID_WIDTH}x}"
        intent_code = {
            OrderIntent.OPEN_GRID: "01",
            OrderIntent.CLOSE_GRID: "02",
            OrderIntent.STOP_LOSS: "03",
            OrderIntent.TAKE_PROFIT: "04",
            OrderIntent.UNSTUCK: "05",
        }[self.intent]
        lvl = f"{self.level & 0xFF:0{_LEVEL_WIDTH}x}"
        ctr = f"{next(_COUNTER) & 0xFFFF_FFFF_FFFF_FFFF:0{_COUNTER_WIDTH}x}"
        return f"0x{sid}{intent_code}{lvl}00000000{ctr}"


@dataclass
class OrderIntentTracker:
    """Three-map tracking: local_id ↔ cloid ↔ oid.

    Design per vnpy-hyperliquid. `oid` populates only after HL confirms the submit;
    `cancel_by_cloid` should be used whenever oid is unknown.
    """

    local_to_cloid: dict[str, str] = field(default_factory=dict)
    cloid_to_local: dict[str, str] = field(default_factory=dict)
    cloid_to_oid: dict[str, str] = field(default_factory=dict)
    oid_to_cloid: dict[str, str] = field(default_factory=dict)

    def register(self, local_id: str, cloid: str) -> None:
        self.local_to_cloid[local_id] = cloid
        self.cloid_to_local[cloid] = local_id

    def bind_oid(self, cloid: str, oid: str) -> None:
        self.cloid_to_oid[cloid] = oid
        self.oid_to_cloid[oid] = cloid

    def forget(self, cloid: str) -> None:
        local = self.cloid_to_local.pop(cloid, None)
        if local is not None:
            self.local_to_cloid.pop(local, None)
        oid = self.cloid_to_oid.pop(cloid, None)
        if oid is not None:
            self.oid_to_cloid.pop(oid, None)
