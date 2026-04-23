"""Integration tests for HLClient read-only path.

Uses VCR cassettes so CI replays HTTP without hitting testnet. To (re)record,
delete the cassette file and run the test with network access.
"""

from __future__ import annotations

import pytest
import vcr.cassette

from osbot.connector.hl_client import HLClient
from osbot.state.fills import FillEventsManager

# Testnet master wallet — read-only queries only, no signing.
TESTNET_ACCOUNT = "0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88"


@pytest.mark.asyncio
async def test_user_state_testnet(vcr_cassette: vcr.cassette.Cassette) -> None:
    client = HLClient(mode="testnet", account_address=TESTNET_ACCOUNT)
    state = await client.user_state()
    assert "marginSummary" in state
    assert "assetPositions" in state
    assert vcr_cassette.play_count >= 1 or len(vcr_cassette.data) >= 1


@pytest.mark.asyncio
async def test_all_mids_testnet(vcr_cassette: vcr.cassette.Cassette) -> None:
    client = HLClient(mode="testnet", account_address=TESTNET_ACCOUNT)
    mids = await client.all_mids()
    assert isinstance(mids, dict)
    assert len(mids) > 0
    assert vcr_cassette.play_count >= 1 or len(vcr_cassette.data) >= 1


@pytest.mark.asyncio
async def test_fill_manager_reconcile(vcr_cassette: vcr.cassette.Cassette) -> None:
    client = HLClient(mode="testnet", account_address=TESTNET_ACCOUNT)
    mgr = FillEventsManager(client=client)
    first = await mgr.reconcile()
    # Running reconcile twice must yield no additional new fills (dedup).
    second = await mgr.reconcile()
    assert second == []
    assert isinstance(first, list)
    assert vcr_cassette.play_count >= 1 or len(vcr_cassette.data) >= 1
