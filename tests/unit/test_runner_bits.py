"""Runner helper tests — pure-logic bits that can run offline."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from osbot.connector.errors import AppError, AuthError, ErrorCategory, StructuralError
from osbot.connector.hl_client import HLClient
from osbot.observability.health import HealthState
from osbot.risk.manager import RiskManager
from osbot.runner import _apply_plan, _reconcile_orders, _RetryState, _submit_one
from osbot.strategy.grid import GridPlan, OrderSubmit
from osbot.strategy.tags import OrderIntent


def _client_with_user_state(**extra: Any) -> HLClient:
    c = HLClient(mode="testnet", account_address="0x0000000000000000000000000000000000000000")
    state = {
        "marginSummary": {"accountValue": "1000"},
        "withdrawable": "1000",
        **extra,
    }
    c.user_state = AsyncMock(return_value=state)  # type: ignore[method-assign]
    return c


def _submit(cloid: str, level: int = 1, side: str = "buy") -> OrderSubmit:
    return OrderSubmit(
        intent=OrderIntent.OPEN_GRID,
        side=side,
        size=0.001,
        price=60_000.0,
        cloid=cloid,
        level=level,
    )


@pytest.mark.asyncio
async def test_submit_one_returns_cloid_on_success() -> None:
    c = _client_with_user_state()
    c.place_order = AsyncMock(return_value={"status": "ok"})  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    sub = _submit("0xaaa")
    result = await _submit_one(c, "BTC", sub, rm, HealthState())
    assert result == "0xaaa"


@pytest.mark.asyncio
async def test_submit_one_skips_when_margin_insufficient() -> None:
    c = _client_with_user_state(withdrawable="0.01")
    c.place_order = AsyncMock()  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    sub = OrderSubmit(
        intent=OrderIntent.OPEN_GRID,
        side="buy",
        size=1.0,
        price=60_000.0,
        cloid="0xbbb",
        level=1,
    )
    result = await _submit_one(c, "BTC", sub, rm, HealthState())
    assert result is None
    c.place_order.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_submit_one_absorbs_structural_error() -> None:
    c = _client_with_user_state()
    c.place_order = AsyncMock(side_effect=StructuralError("min notional"))  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    h = HealthState()
    result = await _submit_one(c, "BTC", _submit("0xccc"), rm, h)
    assert result is None
    assert h.errors == 1


@pytest.mark.asyncio
async def test_submit_one_reraises_auth() -> None:
    c = _client_with_user_state()
    c.place_order = AsyncMock(side_effect=AuthError("signature"))  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    with pytest.raises(AuthError):
        await _submit_one(c, "BTC", _submit("0xddd"), rm, HealthState())


@pytest.mark.asyncio
async def test_submit_one_counts_retryable_error() -> None:
    c = _client_with_user_state()
    c.place_order = AsyncMock(side_effect=AppError("timeout"))  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    h = HealthState()
    result = await _submit_one(c, "BTC", _submit("0xeee"), rm, h)
    assert result is None
    assert h.errors == 1


@pytest.mark.asyncio
async def test_apply_plan_cancels_then_submits() -> None:
    c = _client_with_user_state()
    c.cancel_by_cloid = AsyncMock(return_value={"status": "ok"})  # type: ignore[method-assign]
    c.place_order = AsyncMock(return_value={"status": "ok"})  # type: ignore[method-assign]
    rm = RiskManager(c, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3)
    plan = GridPlan(
        cancels=["0xold1", "0xold2"],
        submits=[_submit("0xnew1"), _submit("0xnew2", side="sell")],
    )
    live = await _apply_plan(c, "BTC", plan, rm, HealthState())
    assert live == ["0xnew1", "0xnew2"]
    assert c.cancel_by_cloid.call_count == 2  # type: ignore[attr-defined]
    assert c.place_order.call_count == 2  # type: ignore[attr-defined]


def test_retry_state_no_backoff_for_structural() -> None:
    r = _RetryState()
    assert r.on_error(ErrorCategory.STRUCTURAL) == 0.0
    assert r.consecutive == 0


def test_retry_state_no_backoff_for_auth() -> None:
    r = _RetryState()
    assert r.on_error(ErrorCategory.AUTH) == 0.0


def test_retry_state_exponential_for_rate_limit() -> None:
    r = _RetryState()
    assert r.on_error(ErrorCategory.RATE_LIMIT) == 2.0
    assert r.on_error(ErrorCategory.RATE_LIMIT) == 4.0
    assert r.on_error(ErrorCategory.RATE_LIMIT) == 8.0
    assert r.on_error(ErrorCategory.RATE_LIMIT) == 16.0


def test_retry_state_caps_at_60s() -> None:
    r = _RetryState()
    for _ in range(10):
        last = r.on_error(ErrorCategory.NETWORK)
    assert last == 60.0


def test_retry_state_resets_on_success() -> None:
    r = _RetryState()
    r.on_error(ErrorCategory.NETWORK)
    r.on_error(ErrorCategory.NETWORK)
    assert r.consecutive == 2
    r.on_success()
    assert r.consecutive == 0
    # Next error starts from base again.
    assert r.on_error(ErrorCategory.NETWORK) == 2.0


@pytest.mark.asyncio
async def test_reconcile_orders_drops_missing() -> None:
    c = _client_with_user_state()
    c.open_orders = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {"coin": "BTC", "cloid": "0xa", "oid": 1},
            {"coin": "ETH", "cloid": "0xb", "oid": 2},
        ]
    )
    kept = await _reconcile_orders(c, "BTC", ["0xa", "0xb", "0xmissing"])
    assert kept == ["0xa"]
