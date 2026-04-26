"""Vol-adaptive grid + trend pause per phase5-synthesis.md section 5.5.

Each replan cycle (default 5 min):
  - range_pct = max(range_bps_min, 3 * rolling_sigma_1h_bps)
  - 5 buy levels spaced `range_pct / grid_levels` below mid, 5 sell levels above
  - per-level size = balance * wallet_exposure_limit / grid_levels
  - if per-level notional < min_notional_usd, bump to min and log size_bumped
  - if |EMA_4h_slope_bps| > range_bps_min, pause OPEN_GRID submits (existing
    open orders stay cancelable)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from osbot.config import BaseConfig
from osbot.observability import get_logger
from osbot.strategy.tags import OrderIntent, OrderTag

log = get_logger("osbot.grid")

_MIN_SIGMA_SAMPLES = 8


@dataclass
class MarketState:
    """Rolling price store with 1-min-bucketed sigma + dual time-weighted EMA slope.

    Sigma:
      `sample()` is called every tick (~1s). Per-tick samples are dominated by
      noise, so we keep a parallel deque of (minute, last_price_in_that_minute)
      entries and compute sigma over log-returns of those minute closes. Eight
      minute-buckets minimum before we report a non-zero sigma.

    Slope:
      Two EMAs at different timescales (fast=30min, slow=4h), updated with
      time-aware alpha = 1 - exp(-dt / tau). The slope signal is the relative
      gap (fast - slow) / slow, in bps — a classic EMA-cross. Responds to
      fresh trend within minutes; warm-up gate prevents reporting until the
      slow EMA has accumulated at least slow_tau/4 of weight (~1h elapsed).
    """

    sigma_window_s: float = 3600.0  # 60 minute-buckets retained for sigma
    ema_fast_tau_s: float = 1800.0  # 30min — responsive to fresh trend
    ema_slow_tau_s: float = 14400.0  # 4h — long-run trend reference
    max_age_s: float = 14400.0  # raw-sample retention (audit/debug)
    _samples: deque[tuple[float, float]] = field(default_factory=deque)
    _minute_samples: deque[tuple[int, float]] = field(default_factory=deque)
    _ema_fast: float = 0.0
    _ema_slow: float = 0.0
    _last_ema_ts: float = 0.0
    _ema_initialized: bool = False

    def sample(self, ts: float, mid: float) -> None:
        if mid <= 0:
            return
        if self._samples and ts <= self._samples[-1][0]:
            return
        self._samples.append((ts, mid))
        cutoff = ts - self.max_age_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        # 1-min bucketed close series for sigma.
        minute = int(ts // 60)
        if not self._minute_samples or self._minute_samples[-1][0] != minute:
            self._minute_samples.append((minute, mid))
        else:
            # Same minute: keep the last-observed price as that minute's "close".
            self._minute_samples[-1] = (minute, mid)
        sigma_minute_cutoff = minute - int(self.sigma_window_s // 60)
        while self._minute_samples and self._minute_samples[0][0] < sigma_minute_cutoff:
            self._minute_samples.popleft()

        # Time-weighted dual-EMA for slope.
        if not self._ema_initialized:
            self._ema_fast = mid
            self._ema_slow = mid
            self._last_ema_ts = ts
            self._ema_initialized = True
            return
        dt = max(ts - self._last_ema_ts, 0.0)
        alpha_fast = 1.0 - math.exp(-dt / self.ema_fast_tau_s)
        alpha_slow = 1.0 - math.exp(-dt / self.ema_slow_tau_s)
        self._ema_fast += alpha_fast * (mid - self._ema_fast)
        self._ema_slow += alpha_slow * (mid - self._ema_slow)
        self._last_ema_ts = ts

    def sigma_bps(self, now: float) -> float:
        """Std-dev of log-returns over 1-min closes, expressed in bps.

        Returns 0.0 if fewer than 8 minute-buckets accumulated.
        """
        del now  # bucketing is self-contained
        if len(self._minute_samples) < _MIN_SIGMA_SAMPLES:
            return 0.0
        prices = [p for (_, p) in self._minute_samples]
        returns: list[float] = []
        for i in range(1, len(prices)):
            prev, cur = prices[i - 1], prices[i]
            if prev > 0 and cur > 0:
                returns.append(math.log(cur / prev))
        if not returns:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / max(len(returns) - 1, 1)
        return math.sqrt(var) * 10_000.0

    def ema_slope_bps(self, now: float) -> float:
        """Dual-EMA trend gauge: (fast - slow) / slow, in bps.

        Returns 0.0 during warm-up (slow EMA needs ~1h of samples to be
        meaningful) or when the slow EMA hasn't been initialised yet.
        """
        del now
        if not self._ema_initialized or self._ema_slow <= 0:
            return 0.0
        if not self._samples:
            return 0.0
        elapsed = self._last_ema_ts - self._samples[0][0]
        if elapsed < self.ema_slow_tau_s / 4.0:
            return 0.0
        return ((self._ema_fast - self._ema_slow) / self._ema_slow) * 10_000.0


@dataclass
class OrderSubmit:
    intent: OrderIntent
    side: str  # "buy" | "sell"
    size: float
    price: float
    cloid: str
    level: int
    reduce_only: bool = False
    tif: str = "Gtc"


@dataclass
class GridPlan:
    cancels: list[str] = field(default_factory=list)  # cloids
    submits: list[OrderSubmit] = field(default_factory=list)


def _round_size(notional_usd: float, mid: float, sz_decimals: int) -> float:
    factor: int = 10**sz_decimals
    rounded: int = round((notional_usd / mid) * factor)
    return rounded / factor


def _round_price(price: float) -> float:
    # BTC perp: round to whole dollar; under 5-sig-fig cap for prices < 100k.
    return float(round(price))


class GridStrategy:
    def __init__(self, cfg: BaseConfig, sz_decimals: int, strategy_id: int = 0xCAFE) -> None:
        self.cfg = cfg
        self.sz_decimals = sz_decimals
        self.strategy_id = strategy_id
        self.grid_levels = cfg.strategy.grid_levels
        self.wallet_exposure_limit = cfg.strategy.wallet_exposure_limit
        self.range_bps_min = float(cfg.strategy.range_bps_min)
        self.min_notional_usd = cfg.risk.min_notional_usd
        self._last_plan_ts: float = 0.0
        self._last_plan_was_paused: bool = False

    def should_replan(self, now: float, replan_interval_s: float, have_grid: bool) -> bool:
        if self._last_plan_ts == 0.0:
            return True
        if (now - self._last_plan_ts) >= replan_interval_s:
            return True
        if have_grid:
            return False
        # No live grid and within interval: only replan if the absence is due to
        # fills consuming the grid, not because we intentionally paused.
        return not self._last_plan_was_paused

    def plan(
        self,
        *,
        now: float,
        mid: float,
        market: MarketState,
        balance_usd: float,
        open_grid_cloids: list[str],
    ) -> GridPlan:
        """Build the next GridPlan. Always cancels existing OPEN_GRID cloids.

        If trend filter trips, returns cancels-only (pause adds).
        """
        sigma_bps = market.sigma_bps(now)
        slope_bps = market.ema_slope_bps(now)
        range_bps = max(self.range_bps_min, 3.0 * sigma_bps)
        spacing_bps = range_bps / self.grid_levels

        plan = GridPlan(cancels=list(open_grid_cloids))
        self._last_plan_ts = now

        if abs(slope_bps) > self.range_bps_min:
            log.info(
                "grid: trend pause (slope=%.1fbps > %.1fbps), cancel-only",
                slope_bps,
                self.range_bps_min,
            )
            self._last_plan_was_paused = True
            return plan
        self._last_plan_was_paused = False

        per_level_notional = (balance_usd * self.wallet_exposure_limit) / self.grid_levels
        bumped = False
        if per_level_notional < self.min_notional_usd:
            per_level_notional = self.min_notional_usd
            bumped = True
            log.warning(
                "grid: per-level notional bumped to min $%.2f (balance=%.2f wel=%.2f levels=%d)",
                self.min_notional_usd,
                balance_usd,
                self.wallet_exposure_limit,
                self.grid_levels,
            )

        level_size = _round_size(per_level_notional, mid, self.sz_decimals)
        if level_size <= 0:
            log.error("grid: level size rounded to 0; skipping submits")
            return plan

        for i in range(1, self.grid_levels + 1):
            offset = (spacing_bps * i) / 10_000.0
            buy_px = _round_price(mid * (1 - offset))
            sell_px = _round_price(mid * (1 + offset))
            buy_cloid = OrderTag(
                strategy_id=self.strategy_id, intent=OrderIntent.OPEN_GRID, level=i
            ).to_cloid()
            sell_cloid = OrderTag(
                strategy_id=self.strategy_id, intent=OrderIntent.OPEN_GRID, level=i
            ).to_cloid()
            plan.submits.append(
                OrderSubmit(
                    intent=OrderIntent.OPEN_GRID,
                    side="buy",
                    size=level_size,
                    price=buy_px,
                    cloid=buy_cloid,
                    level=i,
                )
            )
            plan.submits.append(
                OrderSubmit(
                    intent=OrderIntent.OPEN_GRID,
                    side="sell",
                    size=level_size,
                    price=sell_px,
                    cloid=sell_cloid,
                    level=i,
                )
            )

        log.info(
            "grid plan: sigma=%.1fbps slope=%.1fbps range=%.1fbps spacing=%.1fbps"
            " size=%s bumped=%s submits=%d cancels=%d",
            sigma_bps,
            slope_bps,
            range_bps,
            spacing_bps,
            level_size,
            bumped,
            len(plan.submits),
            len(plan.cancels),
        )
        return plan

    # Legacy interface retained so old callers don't break.
    def next_actions(self, state: dict[str, Any], mid: float) -> list[dict[str, Any]]:
        del state, mid
        raise NotImplementedError("use GridStrategy.plan(...) instead")
