"""ForagerSelector — pure ranker tests."""

from __future__ import annotations

import pytest

from osbot.strategy.selection import _MIN_BUCKETS, ForagerSelector


def _feed_minutes(sel: ForagerSelector, pair: str, prices: list[float]) -> None:
    """Feed one price per minute starting at ts=0, advancing 60s each step."""
    for i, p in enumerate(prices):
        sel.update_mids(float(i * 60), {pair: p})


def test_rank_excludes_cold_pairs() -> None:
    sel = ForagerSelector(candidates=["BTC", "ETH"], log_range_window_min=16)
    sel.update_asset_ctxs(
        [{"name": "BTC"}, {"name": "ETH"}],
        [{"dayNtlVlm": "1000000"}, {"dayNtlVlm": "500000"}],
    )
    # Only 2 minute-buckets — below _MIN_BUCKETS=4, so neither rankable
    _feed_minutes(sel, "BTC", [100.0, 101.0])
    _feed_minutes(sel, "ETH", [100.0, 101.0])
    assert sel.rank() == []


def test_rank_orders_by_logrange_times_volume() -> None:
    sel = ForagerSelector(candidates=["BTC", "ETH", "DOGE"], log_range_window_min=16)
    sel.update_asset_ctxs(
        [{"name": "BTC"}, {"name": "ETH"}, {"name": "DOGE"}],
        [
            {"dayNtlVlm": "1000000"},  # BTC
            {"dayNtlVlm": "500000"},   # ETH
            {"dayNtlVlm": "2000000"},  # DOGE
        ],
    )
    # BTC: tight range; ETH: medium; DOGE: tight but high vol
    _feed_minutes(sel, "BTC", [100.0, 100.1, 100.0, 100.1, 100.05])
    _feed_minutes(sel, "ETH", [3000.0, 3030.0, 3000.0, 3030.0, 3015.0])  # ~1% range
    _feed_minutes(sel, "DOGE", [0.10, 0.1001, 0.10, 0.1001, 0.10005])
    ranked = sel.rank()
    assert [s.pair for s in ranked] == ["ETH", "DOGE", "BTC"]
    assert sel.top_n(1) == ["ETH"]


def test_min_volume_filter_excludes_thin_pairs() -> None:
    sel = ForagerSelector(
        candidates=["BTC", "THIN"],
        log_range_window_min=16,
        min_volume_usd_24h=100_000.0,
    )
    sel.update_asset_ctxs(
        [{"name": "BTC"}, {"name": "THIN"}],
        [{"dayNtlVlm": "1000000"}, {"dayNtlVlm": "5000"}],  # THIN below floor
    )
    _feed_minutes(sel, "BTC", [100.0, 101.0, 100.0, 101.0, 100.5])
    _feed_minutes(sel, "THIN", [1.0, 1.1, 1.0, 1.1, 1.05])  # large pct range
    ranked = sel.rank()
    assert [s.pair for s in ranked] == ["BTC"]


def test_same_minute_overwrites_not_appends() -> None:
    """Multiple samples in the same minute keep only the latest (last-write-wins)."""
    sel = ForagerSelector(candidates=["BTC"], log_range_window_min=16)
    sel.update_asset_ctxs([{"name": "BTC"}], [{"dayNtlVlm": "1000000"}])
    # Spam many samples within the same first minute
    for sub in range(20):
        sel.update_mids(float(sub), {"BTC": 100.0 + sub * 0.001})
    # Then advance through minutes 1..4 with stable prices
    for m in range(1, 5):
        sel.update_mids(float(m * 60), {"BTC": 100.05})
    hist = sel._history["BTC"]
    assert len(hist.buckets) == 5  # one per minute, not 24


def test_window_eviction() -> None:
    """Buckets older than `window_min` are dropped."""
    sel = ForagerSelector(candidates=["BTC"], log_range_window_min=4)
    sel.update_asset_ctxs([{"name": "BTC"}], [{"dayNtlVlm": "1000000"}])
    # Feed 10 minutes; only the last 4 should remain
    _feed_minutes(sel, "BTC", [100.0 + i for i in range(10)])
    hist = sel._history["BTC"]
    assert len(hist.buckets) == 4
    minutes = [m for m, _ in hist.buckets]
    assert minutes == [6, 7, 8, 9]


def test_unknown_pair_in_mids_ignored() -> None:
    sel = ForagerSelector(candidates=["BTC"], log_range_window_min=16)
    sel.update_mids(0.0, {"BTC": 100.0, "RANDOM": 50.0})
    assert "RANDOM" not in sel._history


def test_invalid_price_skipped() -> None:
    sel = ForagerSelector(candidates=["BTC"], log_range_window_min=16)
    sel.update_mids(0.0, {"BTC": "not-a-number"})  # type: ignore[dict-item]
    sel.update_mids(60.0, {"BTC": -1.0})
    assert len(sel._history["BTC"].buckets) == 0


def test_empty_candidates_rejected() -> None:
    with pytest.raises(ValueError):
        ForagerSelector(candidates=[])


def test_min_buckets_constant_is_reasonable() -> None:
    # Sanity guard so future tweaks don't accidentally make the gate trivial.
    assert 2 <= _MIN_BUCKETS <= 16
