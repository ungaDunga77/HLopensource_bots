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
from osbot.config.base import PairOverrides
from osbot.observability import get_logger
from osbot.strategy.tags import OrderIntent, OrderTag

log = get_logger("osbot.grid")

_MIN_SIGMA_SAMPLES = 8
# Per-level notional must clear the exchange min-notional by this factor before we
# trade. Headroom absorbs price drift + size rounding so a level placed at/above the
# floor doesn't fall below it (and get rejected) before it can be reduced. Below this
# line the grid quotes nothing rather than bump-and-trap. See lessons: min-notional trap.
_MIN_NOTIONAL_HEADROOM = 1.3


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


def _allowed_price_decimals(price: float, sz_decimals: int) -> int:
    """HL perp price rule: at most 5 sig figs AND at most (6 - sz_decimals) decimals."""
    if price <= 0:
        return 0
    if price >= 1:
        int_digits = len(str(int(price)))
        sig_fig_decimals = max(0, 5 - int_digits)
    else:
        leading_zeros = max(0, -math.floor(math.log10(price)) - 1)
        sig_fig_decimals = leading_zeros + 5
    max_decimals_perp = max(0, 6 - sz_decimals)
    return min(sig_fig_decimals, max_decimals_perp)


def _round_price(price: float, sz_decimals: int) -> float:
    return round(price, _allowed_price_decimals(price, sz_decimals))


class GridStrategy:
    def __init__(
        self,
        cfg: BaseConfig,
        sz_decimals: int,
        strategy_id: int = 0xCAFE,
        *,
        overrides: PairOverrides | None = None,
    ) -> None:
        self.cfg = cfg
        self.sz_decimals = sz_decimals
        self.strategy_id = strategy_id
        s = cfg.strategy
        self.grid_levels = s.grid_levels
        self.wallet_exposure_limit = s.wallet_exposure_limit
        self.range_bps_min = float(s.range_bps_min)
        self.min_notional_usd = cfg.risk.min_notional_usd
        self.inventory_skew_gamma = float(s.inventory_skew_gamma)
        self.inventory_skew_horizon_s = float(s.inventory_skew_horizon_s)
        # v4: ALO (post-only) grid quotes so entries never pay taker. See cfg.strategy.post_only.
        self.order_tif = "Alo" if s.post_only else "Gtc"
        if overrides is not None:
            if overrides.grid_levels is not None:
                self.grid_levels = overrides.grid_levels
            if overrides.range_bps_min is not None:
                self.range_bps_min = float(overrides.range_bps_min)
            if overrides.inventory_skew_gamma is not None:
                self.inventory_skew_gamma = float(overrides.inventory_skew_gamma)
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

    def plan(  # noqa: PLR0915 — sequential grid builder; clearer flat than fragmented
        self,
        *,
        now: float,
        mid: float,
        market: MarketState,
        balance_usd: float,
        open_grid_cloids: list[str],
        position_signed_szi: float = 0.0,
        n_active_pairs: int = 1,
    ) -> GridPlan:
        """Build the next GridPlan. Always cancels existing OPEN_GRID cloids.

        If trend filter trips, returns cancels-only (pause adds).

        When `inventory_skew_gamma > 0` the grid is centered on an
        Avellaneda-Stoikov reservation price `r = mid * (1 - q*g*s^2*T)` rather
        than mid, where `q = position_notional / balance` is signed normalized
        inventory, `g` is `inventory_skew_gamma`, `s` is sigma_frac, and `T` is
        the horizon in minutes. Default g=0 keeps the grid symmetric around mid
        (legacy behavior). See todo section 10.
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

        per_pair_wel = self.wallet_exposure_limit / max(n_active_pairs, 1)
        per_level_notional = (balance_usd * per_pair_wel) / self.grid_levels

        # Viability guard: if the WEL-derived per-level notional is below the
        # exchange min-notional floor (with headroom), DO NOT bump-and-trade.
        # Bumping oversizes the grid past the position cap and builds positions
        # that cannot be unwound — reduce orders fall below min notional, get
        # rejected, and the bot bleeds to the daily-loss halt. Quote nothing
        # (cancel-only) until capital is adequate. See lessons: min-notional trap.
        min_viable = self.min_notional_usd * _MIN_NOTIONAL_HEADROOM
        if per_level_notional < min_viable:
            log.error(
                "grid: per-level $%.2f < %.1fx min notional $%.2f "
                "(balance=%.2f wel=%.3f pairs=%d levels=%d) — capital too small, "
                "quoting nothing (cancel-only)",
                per_level_notional, _MIN_NOTIONAL_HEADROOM, self.min_notional_usd,
                balance_usd, self.wallet_exposure_limit, n_active_pairs,
                self.grid_levels,
            )
            return plan  # cancel-only

        level_size = _round_size(per_level_notional, mid, self.sz_decimals)
        # Size rounding can drop the notional below the floor even when the
        # target was above it; bump up one tick so the order is never rejected.
        tick = 10.0 ** -self.sz_decimals
        if level_size > 0 and level_size * mid < self.min_notional_usd:
            level_size = round(level_size + tick, self.sz_decimals)
        if level_size <= 0:
            log.error("grid: level size rounded to 0; skipping submits")
            return plan

        # Position cap: limit increase-side levels to stay within WEL.
        max_position_coin = (balance_usd * per_pair_wel) / mid if mid > 0 else 0.0
        if position_signed_szi >= 0:
            room_buy = max(max_position_coin - position_signed_szi, 0.0)
            room_sell = max_position_coin + position_signed_szi
        else:
            room_buy = max_position_coin + abs(position_signed_szi)
            room_sell = max(max_position_coin - abs(position_signed_szi), 0.0)
        _tol = level_size * 0.01
        max_buy_levels = (
            min(self.grid_levels, int((room_buy + _tol) / level_size)) if level_size > 0 else 0
        )
        max_sell_levels = (
            min(self.grid_levels, int((room_sell + _tol) / level_size)) if level_size > 0 else 0
        )
        capped_buys = max_buy_levels < self.grid_levels
        capped_sells = max_sell_levels < self.grid_levels
        if capped_buys or capped_sells:
            log.warning(
                "grid: position cap active pos=%.5f max=%.5f — buy_levels=%d/%d sell_levels=%d/%d",
                position_signed_szi, max_position_coin,
                max_buy_levels, self.grid_levels, max_sell_levels, self.grid_levels,
            )

        # Avellaneda-Stoikov reservation-price skew. Defaults to mid when gamma=0.
        skew_frac = 0.0
        if self.inventory_skew_gamma > 0.0 and balance_usd > 0.0:
            q = (position_signed_szi * mid) / max(balance_usd, 1.0)
            sigma_frac = sigma_bps / 10_000.0
            t_min = self.inventory_skew_horizon_s / 60.0
            skew_frac = q * self.inventory_skew_gamma * (sigma_frac * sigma_frac) * t_min
        reservation_price = mid * (1.0 - skew_frac)

        buy_count = 0
        sell_count = 0
        for i in range(1, self.grid_levels + 1):
            offset = (spacing_bps * i) / 10_000.0
            buy_px = _round_price(reservation_price * (1 - offset), self.sz_decimals)
            sell_px = _round_price(reservation_price * (1 + offset), self.sz_decimals)
            if buy_count < max_buy_levels:
                buy_cloid = OrderTag(
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
                        tif=self.order_tif,
                    )
                )
                buy_count += 1
            if sell_count < max_sell_levels:
                sell_cloid = OrderTag(
                    strategy_id=self.strategy_id, intent=OrderIntent.OPEN_GRID, level=i
                ).to_cloid()
                plan.submits.append(
                    OrderSubmit(
                        intent=OrderIntent.OPEN_GRID,
                        side="sell",
                        size=level_size,
                        price=sell_px,
                        cloid=sell_cloid,
                        level=i,
                        tif=self.order_tif,
                    )
                )
                sell_count += 1

        log.info(
            "grid plan: sigma=%.1fbps slope=%.1fbps range=%.1fbps spacing=%.1fbps"
            " size=%s skew=%.2fbps submits=%d cancels=%d",
            sigma_bps,
            slope_bps,
            range_bps,
            spacing_bps,
            level_size,
            skew_frac * 10_000.0,
            len(plan.submits),
            len(plan.cancels),
        )
        return plan

    # Legacy interface retained so old callers don't break.
    def next_actions(self, state: dict[str, Any], mid: float) -> list[dict[str, Any]]:
        del state, mid
        raise NotImplementedError("use GridStrategy.plan(...) instead")
