"""Funding APY tracking — shadow logger schema + HLClient parsing + health surface."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from osbot.connector.hl_client import HLClient
from osbot.observability.health import HealthState
from osbot.observability.shadow import ShadowLogger


def test_record_funding_rate_persists(tmp_path: Path) -> None:
    db = tmp_path / "shadow.sqlite"
    s = ShadowLogger(db)
    s.record_funding_rate("BTC", 0.0000125)
    s.record_funding_rate("BTC", -0.0000300)
    with sqlite3.connect(db) as conn:
        rows = list(conn.execute("SELECT pair, rate FROM funding_rate ORDER BY ts"))
    assert rows == [("BTC", 0.0000125), ("BTC", -0.0000300)]


@pytest.mark.asyncio
async def test_funding_rate_picks_correct_pair() -> None:
    c = HLClient(mode="testnet", account_address="0x0000000000000000000000000000000000000000")
    payload = (
        {"universe": [{"name": "SOL"}, {"name": "BTC"}, {"name": "ETH"}]},
        [
            {"funding": "0.0000800799"},
            {"funding": "0.0000125"},
            {"funding": "-0.0000050"},
        ],
    )
    c._info_call = AsyncMock(return_value=payload)  # type: ignore[method-assign]
    rate = await c.funding_rate("BTC")
    assert rate == pytest.approx(0.0000125)
    rate_eth = await c.funding_rate("ETH")
    assert rate_eth == pytest.approx(-0.0000050)
    missing = await c.funding_rate("DOGE")
    assert missing is None


def test_health_surfaces_apy() -> None:
    h = HealthState()
    h.last_tick_ts = 1.0
    h.funding_rate_hourly = 0.0000125
    snap = h.snapshot()
    assert snap["funding_rate_hourly"] == pytest.approx(0.0000125)
    # APY = hourly * 24 * 365 * 100  → 10.95% for 0.00125%/h
    assert snap["funding_apy_pct"] == pytest.approx(0.0000125 * 24 * 365 * 100)


def test_health_apy_none_when_unset() -> None:
    h = HealthState()
    h.last_tick_ts = 1.0
    snap = h.snapshot()
    assert snap["funding_rate_hourly"] is None
    assert snap["funding_apy_pct"] is None
