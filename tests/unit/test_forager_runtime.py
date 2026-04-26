"""Forager runtime — prepare_forager_pairs + rotation diff + price rounding."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from osbot.connector.errors import StructuralError
from osbot.connector.hl_client import HLClient
from osbot.runner import _build_pair_runtime, _rotate_forager, _strategy_id_for
from osbot.strategy.grid import _allowed_price_decimals, _round_price
from osbot.strategy.selection import ForagerSelector, prepare_forager_pairs


def _client() -> HLClient:
    return HLClient(mode="testnet", account_address="0x" + "0" * 40)


@pytest.mark.asyncio
async def test_prepare_forager_pairs_drops_missing_and_sets_leverage() -> None:
    c = _client()
    c.meta = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "universe": [
                {"name": "BTC", "szDecimals": 5},
                {"name": "ETH", "szDecimals": 4},
            ]
        }
    )
    c.set_leverage = AsyncMock(return_value={})  # type: ignore[method-assign]
    out = await prepare_forager_pairs(c, ["BTC", "ETH", "MISSING"], leverage=3)
    assert out == {"BTC": 5, "ETH": 4}
    # set_leverage called for each valid pair
    assert c.set_leverage.await_count == 2
    called_pairs = sorted(call.args[0] for call in c.set_leverage.await_args_list)
    assert called_pairs == ["BTC", "ETH"]


@pytest.mark.asyncio
async def test_prepare_forager_pairs_raises_when_none_valid() -> None:
    c = _client()
    c.meta = AsyncMock(return_value={"universe": []})  # type: ignore[method-assign]
    c.set_leverage = AsyncMock()  # type: ignore[method-assign]
    with pytest.raises(StructuralError):
        await prepare_forager_pairs(c, ["BTC"], leverage=3)


def test_strategy_id_stable_per_pair_and_distinct() -> None:
    assert _strategy_id_for("BTC") == _strategy_id_for("BTC")
    assert _strategy_id_for("BTC") != _strategy_id_for("ETH")
    # All strategy IDs fit in 16 bits
    for p in ["BTC", "ETH", "SOL", "HYPE", "DOGE", "ARB", "AVAX", "BNB"]:
        sid = _strategy_id_for(p)
        assert 0 < sid <= 0xFFFF


def test_price_rounder_btc_whole_dollars() -> None:
    # BTC szDec=5 → max 1 decimal allowed by sd-rule; 5 sig figs at $100k → 0
    assert _allowed_price_decimals(100123.45, 5) == 0
    assert _round_price(100123.45, 5) == 100123.0


def test_price_rounder_eth_one_decimal() -> None:
    # ETH szDec=4 → max 2 decimals; 5 sig figs at $3050 → 1 decimal
    assert _allowed_price_decimals(3050.12, 4) == 1
    assert _round_price(3050.12, 4) == 3050.1


def test_price_rounder_doge_subdollar() -> None:
    # DOGE szDec=0 → max 6 decimals; 5 sig figs at $0.10567 → 5 decimals
    assert _allowed_price_decimals(0.10567, 0) == 5
    assert _round_price(0.10567, 0) == 0.10567


def test_price_rounder_hype_three_decimals() -> None:
    # HYPE szDec=2 → max 4 decimals; 5 sig figs at $15.43 → 3 decimals
    assert _allowed_price_decimals(15.4321, 2) == 3
    assert _round_price(15.4321, 2) == 15.432


def _mk_cfg() -> Any:
    """Minimal config-like object used by _build_pair_runtime + _rotate_forager."""
    cfg = MagicMock()
    cfg.strategy.pair = "BTC"
    cfg.strategy.leverage = 3
    cfg.strategy.grid_levels = 7
    cfg.strategy.wallet_exposure_limit = 0.30
    cfg.strategy.range_bps_min = 30
    cfg.strategy.tp_pct = 0.0015
    cfg.strategy.sl_pct = 0.015
    cfg.strategy.exit_ttl_s = 86400
    cfg.strategy.sl_consecutive_breaches = 2
    cfg.risk.min_notional_usd = 10.0
    cfg.forager.top_n = 1
    return cfg


def _mk_ctx() -> Any:
    ctx = MagicMock()
    ctx.client = _client()
    ctx.client.cancel_by_cloid = AsyncMock(return_value={})  # type: ignore[method-assign]
    return ctx


@pytest.mark.asyncio
async def test_rotation_adds_pair_when_empty() -> None:
    cfg = _mk_cfg()
    ctx = _mk_ctx()
    selector = ForagerSelector(candidates=["BTC", "ETH"], log_range_window_min=4)
    selector.update_asset_ctxs(
        [{"name": "BTC"}, {"name": "ETH"}],
        [{"dayNtlVlm": "1000000"}, {"dayNtlVlm": "5000000"}],
    )
    # ETH wins: wider range times higher volume
    for m in range(5):
        selector.update_mids(float(m * 60), {"BTC": 100.0 + m * 0.01, "ETH": 3000.0 + m * 30})
    pairs: dict = {}
    pair_meta = {"BTC": 5, "ETH": 4}
    await _rotate_forager(
        ctx=ctx, cfg=cfg, pairs=pairs, selector=selector, pair_meta=pair_meta, now=0.0
    )
    assert list(pairs.keys()) == ["ETH"]
    assert not pairs["ETH"].draining


@pytest.mark.asyncio
async def test_rotation_drains_dropped_pair() -> None:
    cfg = _mk_cfg()
    ctx = _mk_ctx()
    selector = ForagerSelector(candidates=["BTC", "ETH"], log_range_window_min=4)
    selector.update_asset_ctxs(
        [{"name": "BTC"}, {"name": "ETH"}],
        [{"dayNtlVlm": "1000000"}, {"dayNtlVlm": "5000000"}],
    )
    for m in range(5):
        selector.update_mids(float(m * 60), {"BTC": 100.0, "ETH": 3000.0 + m * 30})
    # Pre-existing BTC pair with tracked cloids
    pair_meta = {"BTC": 5, "ETH": 4}
    pairs = {"BTC": _build_pair_runtime(cfg, ctx, "BTC", 5, _strategy_id_for("BTC"))}
    pairs["BTC"].tracked_cloids = ["0xABC1", "0xABC2"]
    await _rotate_forager(
        ctx=ctx, cfg=cfg, pairs=pairs, selector=selector, pair_meta=pair_meta, now=0.0
    )
    # BTC was drained, then GC'd (no orders, no position) — same rotation.
    # ETH activated. cancel_by_cloid called twice for the two BTC orders.
    assert "BTC" not in pairs
    assert "ETH" in pairs and not pairs["ETH"].draining
    assert ctx.client.cancel_by_cloid.await_count == 2


@pytest.mark.asyncio
async def test_rotation_reactivates_drained_pair() -> None:
    cfg = _mk_cfg()
    ctx = _mk_ctx()
    selector = ForagerSelector(candidates=["BTC"], log_range_window_min=4)
    selector.update_asset_ctxs([{"name": "BTC"}], [{"dayNtlVlm": "1000000"}])
    for m in range(5):
        selector.update_mids(float(m * 60), {"BTC": 100.0 + m * 0.5})
    pair_meta = {"BTC": 5}
    pairs = {"BTC": _build_pair_runtime(cfg, ctx, "BTC", 5, _strategy_id_for("BTC"))}
    pairs["BTC"].draining = True  # was previously rotated out
    await _rotate_forager(
        ctx=ctx, cfg=cfg, pairs=pairs, selector=selector, pair_meta=pair_meta, now=0.0
    )
    assert pairs["BTC"].draining is False
