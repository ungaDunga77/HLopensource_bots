"""Grid + exits unit tests."""

from __future__ import annotations

import math

import pytest
from pydantic import SecretStr

from osbot.config.testnet import TestnetConfig
from osbot.strategy.exits import PositionExitState, TripleBarrier
from osbot.strategy.grid import GridStrategy, MarketState, _round_size
from osbot.strategy.tags import OrderIntent


def _cfg(**strategy: object) -> TestnetConfig:
    strategy_defaults = {
        "pair": "BTC",
        "leverage": 3,
        "grid_levels": 5,
        "wallet_exposure_limit": 0.1,
        "range_bps_min": 50,
    }
    strategy_defaults.update(strategy)
    return TestnetConfig(
        mode="testnet",
        account_address="0x066d06A6D0a00821575651f6Afeac14ba5a75B31",
        keyfile_path="./nope.json",
        keyfile_password=SecretStr("x"),
        strategy=strategy_defaults,  # type: ignore[arg-type]
    )


def test_market_sigma_empty_is_zero() -> None:
    m = MarketState()
    assert m.sigma_bps(now=0.0) == 0.0


def test_market_sigma_constant_series_is_zero() -> None:
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)
    assert m.sigma_bps(now=19 * 60) == 0.0


def test_market_sigma_volatile_series_is_positive() -> None:
    m = MarketState()
    for i in range(30):
        mid = 60_000.0 * (1 + 0.001 * ((i % 2) * 2 - 1))
        m.sample(ts=float(i * 60), mid=mid)
    assert m.sigma_bps(now=30 * 60) > 0


def test_market_ema_slope_detects_trend() -> None:
    """Need >=1h elapsed (slow_tau/4 warm-up) before slope is meaningful."""
    m = MarketState()
    # Climb 60_000 -> 72_000 over 4h (240 minutes); fast EMA should lead slow.
    for i in range(241):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 50.0)
    slope = m.ema_slope_bps(now=241 * 60)
    assert slope > 100  # fast > slow during a sustained uptrend


def test_market_ema_slope_zero_during_warmup() -> None:
    m = MarketState()
    for i in range(30):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 100.0)
    # Only 30min of samples; slow_tau/4 = 60min warm-up not met.
    assert m.ema_slope_bps(now=30 * 60) == 0.0


def test_market_ema_slope_zero_on_constant_series() -> None:
    m = MarketState()
    for i in range(241):
        m.sample(ts=float(i * 60), mid=60_000.0)
    assert m.ema_slope_bps(now=241 * 60) == 0.0


def test_market_minute_bucketing_keeps_last_price() -> None:
    """Multiple sub-minute samples collapse to one bucket holding the last price."""
    m = MarketState()
    # Three samples within the same minute boundary; sigma should see only one.
    m.sample(ts=0.0, mid=60_000.0)
    m.sample(ts=20.0, mid=60_100.0)
    m.sample(ts=50.0, mid=60_200.0)
    # Move to next minute.
    m.sample(ts=60.0, mid=60_300.0)
    assert len(m._minute_samples) == 2
    # First minute bucket should hold the last price observed in that minute.
    assert m._minute_samples[0] == (0, 60_200.0)
    assert m._minute_samples[1] == (1, 60_300.0)


def test_grid_plan_submits_ten_orders_when_flat() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)
    plan = g.plan(
        now=20 * 60, mid=60_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=[]
    )
    assert len(plan.submits) == 10
    buys = [s for s in plan.submits if s.side == "buy"]
    sells = [s for s in plan.submits if s.side == "sell"]
    assert len(buys) == 5 and len(sells) == 5
    # Buys below mid, sells above.
    assert all(s.price < 60_000 for s in buys)
    assert all(s.price > 60_000 for s in sells)
    assert all(s.intent == OrderIntent.OPEN_GRID for s in plan.submits)


def test_grid_plan_cancels_existing() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)
    existing = ["0xabc", "0xdef"]
    plan = g.plan(
        now=20 * 60, mid=60_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=existing
    )
    assert plan.cancels == existing


def test_grid_plan_pauses_on_trend() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    # Need >1h for slope warm-up; sustained climb gives a clear EMA-cross signal.
    for i in range(241):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 50.0)
    plan = g.plan(
        now=241 * 60, mid=72_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=["0xa"]
    )
    assert plan.submits == []
    assert plan.cancels == ["0xa"]


def test_grid_plan_bumps_to_min_notional() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)
    # balance 100 * 0.1 / 5 = $2, below $10 min; should bump.
    plan = g.plan(
        now=20 * 60, mid=60_000.0, market=m, balance_usd=100.0, open_grid_cloids=[]
    )
    assert len(plan.submits) == 10
    # $10 / $60k mid = 0.000167 → rounded to 5dp = 0.00017
    assert math.isclose(plan.submits[0].size, 0.00017, abs_tol=1e-5)


def test_round_size_basic() -> None:
    assert _round_size(15.0, 60_000.0, 5) == 0.00025


def test_grid_skew_disabled_by_default_keeps_symmetry_with_position() -> None:
    """gamma=0 (default) ⇒ grid is symmetric around mid regardless of position."""
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    # Inject vol so sigma_bps > 0 — would otherwise zero out skew_frac too.
    for i in range(30):
        mid_i = 60_000.0 * (1 + 0.001 * ((i % 2) * 2 - 1))
        m.sample(ts=float(i * 60), mid=mid_i)
    plan = g.plan(
        now=30 * 60,
        mid=60_000.0,
        market=m,
        balance_usd=10_000.0,
        open_grid_cloids=[],
        position_signed_szi=0.5,  # large long; would skew if gamma>0
    )
    buys = sorted([s.price for s in plan.submits if s.side == "buy"], reverse=True)
    sells = sorted([s.price for s in plan.submits if s.side == "sell"])
    # Symmetric: each sell-mid distance == matching buy-mid distance.
    assert math.isclose(sells[0] - 60_000.0, 60_000.0 - buys[0], rel_tol=1e-4)


def test_grid_skew_long_inventory_shifts_grid_down() -> None:
    """gamma>0 + long position ⇒ reservation price < mid, both sides shift down."""
    g = GridStrategy(
        _cfg(inventory_skew_gamma=10_000.0, inventory_skew_horizon_s=300.0),
        sz_decimals=5,
    )
    m = MarketState()
    for i in range(30):
        mid_i = 60_000.0 * (1 + 0.001 * ((i % 2) * 2 - 1))
        m.sample(ts=float(i * 60), mid=mid_i)
    plan_flat = g.plan(
        now=30 * 60, mid=60_000.0, market=m, balance_usd=10_000.0,
        open_grid_cloids=[], position_signed_szi=0.0,
    )
    # New instance to reset replan state.
    g2 = GridStrategy(
        _cfg(inventory_skew_gamma=10_000.0, inventory_skew_horizon_s=300.0),
        sz_decimals=5,
    )
    plan_long = g2.plan(
        now=30 * 60, mid=60_000.0, market=m, balance_usd=10_000.0,
        open_grid_cloids=[], position_signed_szi=0.5,
    )
    # Long inventory ⇒ all prices shift downward (sells closer to mid, buys further).
    sells_flat = sorted([s.price for s in plan_flat.submits if s.side == "sell"])
    sells_long = sorted([s.price for s in plan_long.submits if s.side == "sell"])
    assert sells_long[0] < sells_flat[0]
    buys_flat = sorted([s.price for s in plan_flat.submits if s.side == "buy"], reverse=True)
    buys_long = sorted([s.price for s in plan_long.submits if s.side == "buy"], reverse=True)
    assert buys_long[0] < buys_flat[0]


def test_grid_skew_short_inventory_shifts_grid_up() -> None:
    """gamma>0 + short position ⇒ reservation price > mid, both sides shift up."""
    g_flat = GridStrategy(
        _cfg(inventory_skew_gamma=10_000.0, inventory_skew_horizon_s=300.0),
        sz_decimals=5,
    )
    g_short = GridStrategy(
        _cfg(inventory_skew_gamma=10_000.0, inventory_skew_horizon_s=300.0),
        sz_decimals=5,
    )
    m = MarketState()
    for i in range(30):
        mid_i = 60_000.0 * (1 + 0.001 * ((i % 2) * 2 - 1))
        m.sample(ts=float(i * 60), mid=mid_i)
    plan_flat = g_flat.plan(
        now=30 * 60, mid=60_000.0, market=m, balance_usd=10_000.0,
        open_grid_cloids=[], position_signed_szi=0.0,
    )
    plan_short = g_short.plan(
        now=30 * 60, mid=60_000.0, market=m, balance_usd=10_000.0,
        open_grid_cloids=[], position_signed_szi=-0.5,
    )
    sells_flat = sorted([s.price for s in plan_flat.submits if s.side == "sell"])
    sells_short = sorted([s.price for s in plan_short.submits if s.side == "sell"])
    assert sells_short[0] > sells_flat[0]
    buys_flat = sorted([s.price for s in plan_flat.submits if s.side == "buy"], reverse=True)
    buys_short = sorted([s.price for s in plan_short.submits if s.side == "buy"], reverse=True)
    assert buys_short[0] > buys_flat[0]


def test_tp_fires_long() -> None:
    tb = TripleBarrier(sl_pct=0.03, tp_pct=0.005, ttl_s=86400)
    pos = PositionExitState(entry_price=60_000.0, size=0.001, side="long", opened_ts=0.0)
    d = tb.evaluate(pos, mid=60_301.0, now=100.0)
    assert d.should_exit and d.reason == "tp"


def test_sl_requires_consecutive_breaches() -> None:
    tb = TripleBarrier(sl_pct=0.03, tp_pct=0.005, ttl_s=86400, consecutive_breaches_required=2)
    pos = PositionExitState(entry_price=60_000.0, size=0.001, side="long", opened_ts=0.0)
    d1 = tb.evaluate(pos, mid=58_000.0, now=10.0)
    assert not d1.should_exit and d1.reason == "sl-pending"
    d2 = tb.evaluate(pos, mid=57_500.0, now=20.0)
    assert d2.should_exit and d2.reason == "sl"


def test_ttl_fires() -> None:
    tb = TripleBarrier(sl_pct=0.03, tp_pct=0.005, ttl_s=100)
    pos = PositionExitState(entry_price=60_000.0, size=0.001, side="long", opened_ts=0.0)
    d = tb.evaluate(pos, mid=60_010.0, now=200.0)
    assert d.should_exit and d.reason == "ttl"


def test_should_replan_initial_call_is_true() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    assert g.should_replan(now=100.0, replan_interval_s=300.0, have_grid=False)


def test_should_replan_respects_pause_within_interval() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    # Need >1h for slope warm-up before the trend-pause branch triggers.
    for i in range(241):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 50.0)
    g.plan(now=241 * 60, mid=72_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=[])
    # Just paused; even though have_grid=False, do not replan within interval.
    assert not g.should_replan(now=241 * 60 + 60, replan_interval_s=300.0, have_grid=False)


def test_should_replan_after_interval_when_paused() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(241):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 50.0)
    g.plan(now=241 * 60, mid=72_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=[])
    # Past the interval, replan even if still paused.
    assert g.should_replan(now=241 * 60 + 400, replan_interval_s=300.0, have_grid=False)


def test_should_replan_when_grid_lost_to_fills() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)  # flat -> no pause
    g.plan(now=20 * 60, mid=60_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=[])
    # Last plan submitted; if grid is now empty, that means fills consumed it.
    assert g.should_replan(now=20 * 60 + 60, replan_interval_s=300.0, have_grid=False)


def test_should_replan_skips_within_interval_when_grid_alive() -> None:
    g = GridStrategy(_cfg(), sz_decimals=5)
    m = MarketState()
    for i in range(20):
        m.sample(ts=float(i * 60), mid=60_000.0)
    g.plan(now=20 * 60, mid=60_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=[])
    assert not g.should_replan(now=20 * 60 + 60, replan_interval_s=300.0, have_grid=True)


@pytest.mark.parametrize("side,mid,expected", [
    ("short", 59_700.0, "tp"),
    ("short", 62_000.0, "sl-pending"),
])
def test_short_exits(side: str, mid: float, expected: str) -> None:
    tb = TripleBarrier(sl_pct=0.03, tp_pct=0.005, ttl_s=86400)
    pos = PositionExitState(entry_price=60_000.0, size=0.001, side=side, opened_ts=0.0)
    d = tb.evaluate(pos, mid=mid, now=10.0)
    assert d.reason == expected
