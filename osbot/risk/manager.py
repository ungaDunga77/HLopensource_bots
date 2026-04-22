"""Risk precheck interface (stub)."""

from __future__ import annotations

from typing import Any


class RiskManager:
    def precheck(self) -> None:
        raise NotImplementedError("RiskManager wired in M2")

    def margin_ok(self, action: dict[str, Any]) -> bool:
        del action
        raise NotImplementedError("margin_ok wired in M2")
