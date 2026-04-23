"""Unit tests for M2 write-path scaffolding.

These tests verify the *plumbing* (no-wallet guards, size rounding, password
resolution) without hitting the network or signing. The real testnet round
trip is exercised by `python -m osbot --round-trip-test` and is gated by
acceptance, not unit tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import SecretStr

from osbot.auth.keyfile import load_keyfile, save_keyfile
from osbot.config.testnet import TestnetConfig
from osbot.connector.errors import AuthError
from osbot.connector.hl_client import HLClient
from osbot.roundtrip import _format_price, _round_size
from osbot.startup import KEYFILE_PASSWORD_ENV, _resolve_password


def _make_cfg(*, secret: str = "") -> TestnetConfig:
    return TestnetConfig(
        mode="testnet",
        account_address="0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88",
        keyfile_path="./nope.json",
        keyfile_password=SecretStr(secret),
    )


def test_round_size_btc_5dp() -> None:
    # $15 / $60_000 mid = 0.00025 BTC, rounded to 5dp.
    assert _round_size(15.0, 60_000.0, 5) == 0.00025


def test_round_size_below_min_step() -> None:
    # If notional / mid is smaller than the smallest step, we still produce a
    # non-negative number (caller is responsible for rejecting <= 0).
    assert _round_size(0.001, 60_000.0, 5) == 0.0


def test_format_price_rounds_to_int_for_btc() -> None:
    assert _format_price(60_123.45) == 60_123.0


@pytest.mark.asyncio
async def test_place_order_without_wallet_raises_auth_error() -> None:
    client = HLClient(mode="testnet", account_address="0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88")
    with pytest.raises(AuthError, match="without a wallet"):
        await client.place_order("BTC", is_buy=True, size=0.001, price=60_000.0)


@pytest.mark.asyncio
async def test_set_leverage_without_wallet_raises_auth_error() -> None:
    client = HLClient(mode="testnet", account_address="0x0d3Bc6B8BA597c1AC2a0E8a2d2C969372f1B4e88")
    with pytest.raises(AuthError, match="without a wallet"):
        await client.set_leverage("BTC", 3)


def test_resolve_password_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEYFILE_PASSWORD_ENV, "from-env")
    cfg = _make_cfg(secret="from-config")
    assert _resolve_password(cfg) == "from-env"


def test_resolve_password_falls_back_to_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KEYFILE_PASSWORD_ENV, raising=False)
    cfg = _make_cfg(secret="from-config")
    assert _resolve_password(cfg) == "from-config"


def test_resolve_password_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KEYFILE_PASSWORD_ENV, raising=False)
    cfg = _make_cfg(secret="")
    with pytest.raises(AuthError, match="keyfile password not set"):
        _resolve_password(cfg)


def test_keyfile_round_trip(tmp_path: Path) -> None:
    """Sanity: we can encrypt+decrypt a key with our wrapper."""
    # Deterministic 32-byte key; never used on mainnet.
    key = bytes.fromhex("11" * 32)
    path = tmp_path / "test.keyfile"
    save_keyfile(path, key, "hunter2")
    decoded = load_keyfile(path, "hunter2")
    assert decoded == key
    # Wrong password rejected.
    with pytest.raises(AuthError):
        load_keyfile(path, "wrong")
    assert os.path.exists(path)
