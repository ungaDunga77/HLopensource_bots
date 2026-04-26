"""Tests for the WS layer: mid cache, fills ingestion, WsSubscriber."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from osbot.connector.hl_client import HLClient
from osbot.connector.ws_subscriber import WsSubscriber
from osbot.state.fills import FillEventsManager


def _client() -> HLClient:
    return HLClient(mode="testnet", account_address="0x0000000000000000000000000000000000000000")


# ---------- HLClient mid cache ----------


def test_cached_mid_returns_none_when_empty() -> None:
    c = _client()
    assert c.cached_mid("BTC") is None


def test_cached_mid_returns_fresh() -> None:
    c = _client()
    c.update_mids({"BTC": "60000.0", "ETH": "3000.0"})
    assert c.cached_mid("BTC") == "60000.0"
    assert c.cached_mid("ETH") == "3000.0"


def test_cached_mid_returns_none_when_stale() -> None:
    c = _client()
    c.update_mids({"BTC": "60000.0"})
    # Inject an old timestamp.
    with c._mid_cache_lock:
        c._mid_cache["BTC"] = (time.time() - 30.0, "60000.0")
    assert c.cached_mid("BTC", max_age_s=5.0) is None


def test_cached_mid_returns_none_for_missing_coin() -> None:
    c = _client()
    c.update_mids({"BTC": "60000.0"})
    assert c.cached_mid("SOL") is None


# ---------- FillEventsManager WS path ----------


def test_ingest_adds_new_fill_to_buffer() -> None:
    fm = FillEventsManager()
    assert fm.ingest({"tid": "abc", "px": "1"})
    assert fm.drain_ws_buffer() == [{"tid": "abc", "px": "1"}]


def test_ingest_dedups_repeats() -> None:
    fm = FillEventsManager()
    assert fm.ingest({"tid": "abc"})
    assert not fm.ingest({"tid": "abc"})
    assert len(fm.drain_ws_buffer()) == 1


def test_ingest_skips_when_no_tid() -> None:
    fm = FillEventsManager()
    assert not fm.ingest({"px": "1"})
    assert fm.drain_ws_buffer() == []


def test_drain_clears_buffer() -> None:
    fm = FillEventsManager()
    fm.ingest({"tid": "a"})
    fm.ingest({"tid": "b"})
    assert len(fm.drain_ws_buffer()) == 2
    assert fm.drain_ws_buffer() == []


def test_rest_reconcile_dedups_against_ws_ingested_tids() -> None:
    """If a fill arrived via WS, REST reconcile shouldn't duplicate it."""
    c = _client()
    c.user_fills = AsyncMock(  # type: ignore[method-assign]
        return_value=[{"tid": "a", "px": "1"}, {"tid": "b", "px": "2"}]
    )
    fm = FillEventsManager(client=c)
    fm.ingest({"tid": "a", "px": "1"})
    fm.drain_ws_buffer()
    new = asyncio.run(fm.reconcile())
    # Only "b" should come from REST since "a" was already seen via WS.
    assert [f["tid"] for f in new] == ["b"]


# ---------- WsSubscriber ----------


@pytest.fixture
def fake_info() -> Any:
    """Stub the SDK Info so no real WS connection happens."""
    with patch("osbot.connector.ws_subscriber.Info") as mock_info_cls:
        instance = MagicMock()
        instance.subscribe = MagicMock(side_effect=lambda sub, cb: 42)
        instance.ws_manager = MagicMock()
        mock_info_cls.return_value = instance
        yield instance


def test_ws_subscriber_starts_disconnected(fake_info: Any) -> None:
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    assert not ws.is_connected()
    assert ws.last_message_ts == 0.0
    del fake_info  # silence unused


def test_ws_subscriber_subscribe_all_mids_records_message(fake_info: Any) -> None:
    received: list[dict[str, str]] = []
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    ws.subscribe_all_mids(received.append)

    # Capture the wrapper the SDK was called with, then invoke it as the SDK would.
    sub_call = fake_info.subscribe.call_args_list[0]
    wrapper = sub_call.args[1]
    wrapper({"channel": "allMids", "data": {"mids": {"BTC": "60000", "ETH": "3000"}}})

    assert received == [{"BTC": "60000", "ETH": "3000"}]
    assert ws.is_connected(max_age_s=5.0)
    assert ws.last_message_ts > 0


def test_ws_subscriber_user_fills_unwraps_each(fake_info: Any) -> None:
    received: list[dict[str, Any]] = []
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    ws.subscribe_user_fills(received.append)

    wrapper = fake_info.subscribe.call_args_list[0].args[1]
    wrapper(
        {
            "channel": "userFills",
            "data": {"fills": [{"tid": "1"}, {"tid": "2"}]},
        }
    )
    assert [f["tid"] for f in received] == ["1", "2"]


def test_ws_subscriber_handles_malformed_message(fake_info: Any) -> None:
    received: list[Any] = []
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    ws.subscribe_all_mids(received.append)
    wrapper = fake_info.subscribe.call_args_list[0].args[1]

    # Various malformed shapes should not raise nor invoke callback.
    wrapper(None)
    wrapper("garbage")
    wrapper({"data": {}})
    wrapper({"data": {"mids": "not-a-dict"}})
    assert received == []


def test_ws_subscriber_stop_calls_ws_manager(fake_info: Any) -> None:
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    ws.stop()
    fake_info.ws_manager.stop.assert_called_once()


def test_ws_subscriber_is_connected_stale_after_threshold(fake_info: Any) -> None:
    ws = WsSubscriber(mode="testnet", account_address="0xabc")
    # Manually set an old ts.
    with ws._lock:
        ws._last_message_ts = time.time() - 60.0
    assert not ws.is_connected(max_age_s=30.0)
    del fake_info
