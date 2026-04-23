"""ExitManager tests — stubbed HLClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from osbot.connector.hl_client import HLClient
from osbot.observability.health import HealthState
from osbot.strategy.exit_manager import ExitManager
from osbot.strategy.exits import TripleBarrier


def _fake_client() -> HLClient:
    return HLClient(mode="testnet", account_address="0x0000000000000000000000000000000000000000")


def _user_state(szi: float, entry: float, coin: str = "BTC") -> dict[str, Any]:
    return {
        "assetPositions": [
            {"position": {"coin": coin, "szi": str(szi), "entryPx": str(entry)}}
        ]
    }


def _flat_state() -> dict[str, Any]:
    return {"assetPositions": []}


def _em(tp: float = 0.005, sl: float = 0.03, ttl: float = 86_400) -> ExitManager:
    c = _fake_client()
    c.market_close = AsyncMock(return_value={"status": "ok"})  # type: ignore[method-assign]
    tb = TripleBarrier(sl_pct=sl, tp_pct=tp, ttl_s=ttl, consecutive_breaches_required=1)
    return ExitManager(client=c, pair="BTC", triple_barrier=tb)


@pytest.mark.asyncio
async def test_flat_returns_false_and_no_state() -> None:
    em = _em()
    assert not await em.evaluate_and_act(_flat_state(), mid=60_000.0, health=HealthState())


@pytest.mark.asyncio
async def test_first_observation_tracks_no_close() -> None:
    em = _em()
    closed = await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_010.0, health=HealthState(), now=100.0
    )
    assert not closed
    em.client.market_close.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_tp_fires_on_long() -> None:
    em = _em(tp=0.005)
    await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_000.0, health=HealthState(), now=100.0
    )
    closed = await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_400.0, health=HealthState(), now=200.0
    )
    assert closed
    em.client.market_close.assert_awaited_once_with("BTC")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_ttl_fires() -> None:
    em = _em(ttl=60.0)
    await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_000.0, health=HealthState(), now=100.0
    )
    closed = await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_050.0, health=HealthState(), now=200.0
    )
    assert closed


@pytest.mark.asyncio
async def test_flip_side_resets_state() -> None:
    em = _em()
    await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_000.0, health=HealthState(), now=100.0
    )
    # Flip short: should re-track, not close.
    closed = await em.evaluate_and_act(
        _user_state(-0.001, 59_000.0), mid=59_000.0, health=HealthState(), now=150.0
    )
    assert not closed


@pytest.mark.asyncio
async def test_drops_state_when_position_flattens() -> None:
    em = _em()
    await em.evaluate_and_act(
        _user_state(0.001, 60_000.0), mid=60_000.0, health=HealthState(), now=100.0
    )
    await em.evaluate_and_act(_flat_state(), mid=60_100.0, health=HealthState(), now=200.0)
    # Next active position re-tracks from scratch (new opened_ts).
    closed = await em.evaluate_and_act(
        _user_state(0.001, 60_050.0), mid=60_050.0, health=HealthState(), now=300.0
    )
    assert not closed
