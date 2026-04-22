"""Hardcoded HL endpoint URLs. No override — design notes §1."""

from __future__ import annotations

from typing import Final

TESTNET_API_URL: Final[str] = "https://api.hyperliquid-testnet.xyz"
TESTNET_WS_URL: Final[str] = "wss://api.hyperliquid-testnet.xyz/ws"
MAINNET_API_URL: Final[str] = "https://api.hyperliquid.xyz"
MAINNET_WS_URL: Final[str] = "wss://api.hyperliquid.xyz/ws"


def api_url(mode: str) -> str:
    if mode == "testnet":
        return TESTNET_API_URL
    if mode == "mainnet":
        return MAINNET_API_URL
    raise ValueError(f"Unknown mode: {mode!r}")


def ws_url(mode: str) -> str:
    if mode == "testnet":
        return TESTNET_WS_URL
    if mode == "mainnet":
        return MAINNET_WS_URL
    raise ValueError(f"Unknown mode: {mode!r}")
