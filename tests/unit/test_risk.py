"""RiskManager unit tests — no network, HLClient stubbed."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from osbot.connector.errors import StructuralError
from osbot.connector.hl_client import HLClient
from osbot.risk.manager import Action, RiskManager


def _fake_client(state: dict[str, Any]) -> HLClient:
    client = HLClient(mode="testnet", account_address="0x0000000000000000000000000000000000000000")
    client.user_state = AsyncMock(return_value=state)  # type: ignore[method-assign]
    return client


def _state(account_value: float, withdrawable: float | None = None) -> dict[str, Any]:
    s: dict[str, Any] = {"marginSummary": {"accountValue": str(account_value)}}
    if withdrawable is not None:
        s["withdrawable"] = str(withdrawable)
    return s


@pytest.mark.asyncio
async def test_precheck_passes_within_drawdown() -> None:
    client = _fake_client(_state(950.0))
    rm = RiskManager(client, baseline_equity=1000.0, max_daily_loss_pct=0.1, leverage=3)
    await rm.precheck()  # 5% drawdown, limit 10%
    assert rm.last_equity == 950.0


@pytest.mark.asyncio
async def test_precheck_breaches_on_excess_drawdown() -> None:
    client = _fake_client(_state(800.0))
    rm = RiskManager(client, baseline_equity=1000.0, max_daily_loss_pct=0.1, leverage=3)
    with pytest.raises(StructuralError, match="daily loss limit"):
        await rm.precheck()


@pytest.mark.asyncio
async def test_margin_ok_allows_reduce_only_without_balance() -> None:
    client = _fake_client(_state(10.0, withdrawable=0.0))
    rm = RiskManager(client, baseline_equity=10.0, max_daily_loss_pct=0.5, leverage=3)
    assert await rm.margin_ok(Action(side="sell", size=1.0, price=100.0, reduce_only=True))


@pytest.mark.asyncio
async def test_margin_ok_rejects_when_insufficient() -> None:
    client = _fake_client(_state(100.0, withdrawable=5.0))
    rm = RiskManager(client, baseline_equity=100.0, max_daily_loss_pct=0.5, leverage=3)
    # notional 300 / leverage 3 = 100, *1.1 buffer = 110 required, have 5.
    assert not await rm.margin_ok(Action(side="buy", size=3.0, price=100.0))


@pytest.mark.asyncio
async def test_margin_ok_uses_ttl_cache() -> None:
    client = _fake_client(_state(1000.0, withdrawable=1000.0))
    rm = RiskManager(
        client, baseline_equity=1000.0, max_daily_loss_pct=0.5, leverage=3, cache_ttl_s=5.0
    )
    await rm.margin_ok(Action(side="buy", size=0.001, price=100.0))
    await rm.margin_ok(Action(side="buy", size=0.001, price=100.0))
    await rm.precheck()
    assert client.user_state.call_count == 1  # type: ignore[attr-defined]
