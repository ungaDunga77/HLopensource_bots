"""Hyperliquid client wrapper.

M1 wraps the HL SDK `Info` (read-only) and maps errors to our `AppError`
hierarchy via `classify()`. Exchange (write-path) lands in M2.

SDK calls are synchronous; we wrap them in `asyncio.to_thread` so the rest of
the bot can stay async-first without blocking the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from hyperliquid.info import Info

from osbot.connector.endpoints import api_url
from osbot.connector.errors import AppError, classify


class HLClient:
    def __init__(self, mode: str, account_address: str, *, timeout: float = 10.0) -> None:
        self.mode = mode
        self.account_address = account_address
        # SDK 0.22.0 testnet spot_meta bug: universe references missing token
        # indices. Pass an empty spot_meta to skip spot-asset mapping (we don't
        # trade spot). See docs/lessons.md.
        spot_meta_stub: Any = {"universe": [], "tokens": []}
        self._info = Info(
            base_url=api_url(mode),
            skip_ws=True,
            timeout=timeout,
            spot_meta=spot_meta_stub,
        )

    async def _call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except AppError:
            raise
        except Exception as e:
            raise classify(e) from e

    async def user_state(self) -> dict[str, Any]:
        result = await self._call(self._info.user_state, self.account_address)
        return dict(result)

    async def open_orders(self) -> list[dict[str, Any]]:
        result = await self._call(self._info.open_orders, self.account_address)
        return list(result)

    async def all_mids(self) -> dict[str, str]:
        result = await self._call(self._info.all_mids)
        return dict(result)

    async def user_fills(self) -> list[dict[str, Any]]:
        result = await self._call(self._info.user_fills, self.account_address)
        return list(result)

    async def place_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        raise NotImplementedError("HLClient write-path wired in M2")
