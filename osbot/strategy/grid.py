"""Vol-adaptive grid (stub for M0). Full strategy per synthesis §5.5 lands in M2+."""

from __future__ import annotations

from typing import Any


class GridStrategy:
    """Wired in M2. Interface only at M0."""

    def next_actions(self, state: dict[str, Any], mid: float) -> list[dict[str, Any]]:
        del state, mid
        raise NotImplementedError("GridStrategy wired in M2")
