"""Hyperliquid client wrapper (stub for M0). Wraps SDK Info + Exchange in M1."""

from __future__ import annotations

from typing import Any


class HLClient:
    """Stub. M1 wires `hyperliquid-python-sdk` Info + Exchange under here."""

    def __init__(self, mode: str, account_address: str) -> None:
        self.mode = mode
        self.account_address = account_address

    async def user_state(self) -> dict[str, Any]:
        raise NotImplementedError("HLClient read-path wired in M1")

    async def place_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("HLClient write-path wired in M2")
