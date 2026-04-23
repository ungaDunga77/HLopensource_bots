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
    m = MarketState()
    for i in range(30):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 100.0)
    slope = m.ema_slope_bps(now=30 * 60)
    assert slope > 400  # ~483bps over the window


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
    for i in range(60):
        m.sample(ts=float(i * 60), mid=60_000.0 + i * 50.0)  # ~5000bps climb
    plan = g.plan(
        now=60 * 60, mid=63_000.0, market=m, balance_usd=10_000.0, open_grid_cloids=["0xa"]
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


@pytest.mark.parametrize("side,mid,expected", [
    ("short", 59_700.0, "tp"),
    ("short", 62_000.0, "sl-pending"),
])
def test_short_exits(side: str, mid: float, expected: str) -> None:
    tb = TripleBarrier(sl_pct=0.03, tp_pct=0.005, ttl_s=86400)
    pos = PositionExitState(entry_price=60_000.0, size=0.001, side=side, opened_ts=0.0)
    d = tb.evaluate(pos, mid=mid, now=10.0)
    assert d.reason == expected
