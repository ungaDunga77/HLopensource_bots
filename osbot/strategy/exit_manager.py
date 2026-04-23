"""Per-position exit manager.

Holds `PositionExitState` keyed by pair and evaluates `TripleBarrier` each tick
against the HL `assetPositions` payload. On a triggered exit, submits a
reduce-only market close via `HLClient.market_close`.

`opened_ts` isn't reported by HL — we stamp it the first tick we observe a
non-zero `szi` for the pair. If the position flips flat (szi=0), we drop state
so a subsequent re-entry starts fresh.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from osbot.connector.errors import AppError, AuthError, StructuralError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger
from osbot.observability.health import HealthState
from osbot.strategy.exits import PositionExitState, TripleBarrier

log = get_logger("osbot.exits")


@dataclass
class ExitManager:
    client: HLClient
    pair: str
    triple_barrier: TripleBarrier
    _state: dict[str, PositionExitState] | None = None

    def _ensure_state(self) -> dict[str, PositionExitState]:
        if self._state is None:
            self._state = {}
        return self._state

    def _extract_position(self, user_state: dict[str, Any]) -> tuple[float, float] | None:
        """Return (szi, entry_price) for the configured pair, or None if flat."""
        for p in user_state.get("assetPositions") or []:
            pos = p.get("position") or {}
            if pos.get("coin") != self.pair:
                continue
            try:
                szi = float(pos.get("szi", "0"))
                entry = float(pos.get("entryPx", "0"))
            except (TypeError, ValueError):
                return None
            if szi == 0.0:
                return None
            return szi, entry
        return None

    async def evaluate_and_act(
        self,
        user_state: dict[str, Any],
        mid: float,
        health: HealthState,
        now: float | None = None,
    ) -> bool:
        """Returns True if a close was submitted."""
        now = now if now is not None else time.time()
        state = self._ensure_state()
        live = self._extract_position(user_state)

        if live is None:
            if self.pair in state:
                log.info("exit: position flat, dropping state for %s", self.pair)
                state.pop(self.pair, None)
            return False

        szi, entry = live
        side = "long" if szi > 0 else "short"
        existing = state.get(self.pair)
        if existing is None or existing.side != side:
            state[self.pair] = PositionExitState(
                entry_price=entry, size=abs(szi), side=side, opened_ts=now
            )
            log.info(
                "exit: tracking new %s position entry=%.2f size=%.5f",
                side,
                entry,
                abs(szi),
            )
            return False

        existing.size = abs(szi)
        decision = self.triple_barrier.evaluate(existing, mid, now=now)
        if not decision.should_exit:
            return False

        log.warning(
            "exit: triggering market_close (%s) reason=%s entry=%.2f mid=%.2f",
            side,
            decision.reason,
            existing.entry_price,
            mid,
        )
        try:
            await self.client.market_close(self.pair)
        except StructuralError as e:
            log.warning("exit: market_close structural: %s", e.message)
            health.errors += 1
            return False
        except AuthError:
            raise
        except AppError as e:
            log.warning("exit: market_close retryable: %s (%s)", e.message, e.category)
            health.errors += 1
            return False

        state.pop(self.pair, None)
        return True
