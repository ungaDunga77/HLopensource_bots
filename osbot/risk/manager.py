"""Risk precheck + live margin gate with a short TTL cache.

`precheck()` is called once per tick. It reads the account value and raises
`StructuralError` if drawdown from the session baseline exceeds the configured
`max_daily_loss_pct`. The runner catches that and enters graceful_stop.

`margin_ok(action)` is called before each submit. It caches the marginSummary
for `cache_ttl_s` (default 0.5s) so a burst of grid submits in one tick doesn't
spam `user_state()`. The check is conservative: a placed limit order consumes
`notional / leverage * (1 + buffer)` of withdrawable balance.
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import Any

from osbot.connector.errors import StructuralError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger

log = get_logger("osbot.risk")


@dataclass
class Action:
    side: str  # "buy" | "sell"
    size: float
    price: float
    reduce_only: bool = False


class RiskManager:
    def __init__(
        self,
        client: HLClient,
        *,
        baseline_equity: float,
        max_daily_loss_pct: float,
        leverage: int,
        margin_buffer: float = 0.1,
        cache_ttl_s: float = 0.5,
        unified_account: bool = False,
    ) -> None:
        self._client = client
        self.baseline_equity = baseline_equity
        self.max_daily_loss_pct = max_daily_loss_pct
        self.leverage = leverage
        self.margin_buffer = margin_buffer
        self.cache_ttl_s = cache_ttl_s
        self._unified = unified_account
        self._last_state: dict[str, Any] | None = None
        self._last_spot_state: dict[str, Any] | None = None
        self._last_state_ts: float = 0.0
        self._last_equity: float = baseline_equity

    @property
    def last_equity(self) -> float:
        return self._last_equity

    async def _get_state(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._last_state is not None and (now - self._last_state_ts) < self.cache_ttl_s:
            return self._last_state
        state = await self._client.user_state()
        self._last_state = state
        self._last_state_ts = now
        if self._unified:
            self._last_spot_state = await self._client.spot_user_state()
            self._update_unified_equity()
        else:
            margin = state.get("marginSummary") or {}
            with contextlib.suppress(TypeError, ValueError):
                self._last_equity = float(margin.get("accountValue", self._last_equity))
        return state

    def _update_unified_equity(self) -> None:
        """Best-effort equity update from cached spot state.

        In unified mode, spot USDC total already includes margin held for
        perps, so we do NOT add perp accountValue (that would double-count).
        """
        if self._last_spot_state is None:
            return
        for bal in self._last_spot_state.get("balances", []):
            if bal.get("coin") == "USDC":
                with contextlib.suppress(TypeError, ValueError):
                    self._last_equity = float(bal.get("total", self._last_equity))
                return

    async def precheck(self) -> None:
        state = await self._get_state()
        equity = self._last_equity
        drawdown = (self.baseline_equity - equity) / self.baseline_equity
        if drawdown >= self.max_daily_loss_pct:
            log.error(
                "risk precheck: drawdown %.4f exceeds max %.4f (baseline=%.2f equity=%.2f)",
                drawdown,
                self.max_daily_loss_pct,
                self.baseline_equity,
                equity,
            )
            raise StructuralError(
                f"daily loss limit breached: drawdown={drawdown:.4f} "
                f"max={self.max_daily_loss_pct:.4f}"
            )
        del state

    async def margin_ok(self, action: Action) -> bool:
        if action.reduce_only:
            return True
        state = await self._get_state()
        try:
            withdrawable = self._get_withdrawable(state)
        except (TypeError, ValueError):
            return False
        notional = action.size * action.price
        required = (notional / max(self.leverage, 1)) * (1 + self.margin_buffer)
        ok = withdrawable >= required
        if not ok:
            log.warning(
                "margin_ok: insufficient withdrawable=%.2f required=%.2f",
                withdrawable,
                required,
            )
        return ok

    def _get_withdrawable(self, state: dict[str, Any]) -> float:
        if self._unified and self._last_spot_state is not None:
            for token, avail in self._last_spot_state.get("tokenToAvailableAfterMaintenance", []):
                if token == 0:
                    return float(avail)
        margin = state.get("marginSummary") or {}
        return float(state.get("withdrawable") or margin.get("accountValue", "0"))
