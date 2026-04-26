"""Hyperliquid client wrapper.

Wraps the HL SDK `Info` (read-only) and `Exchange` (write-path) and maps errors
to our `AppError` hierarchy via `classify()`.

SDK calls are synchronous; we wrap them in `asyncio.to_thread` so the rest of
the bot can stay async-first without blocking the event loop. Write-path calls
go through an `AsyncThrottler` (token bucket, per limit-id) to respect HL's
posted rate limits; the throttler is shared with the read path.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.types import Cloid

from osbot.connector.endpoints import api_url
from osbot.connector.errors import AppError, AuthError, classify
from osbot.connector.throttler import AsyncThrottler, RateLimit

# Limit IDs for AsyncThrottler. HL publishes ~1200 req/min/IP across info+exchange;
# we budget conservatively per-bucket. Tune later if we measure 429s.
LIMIT_INFO = "info"
LIMIT_EXCHANGE = "exchange"

DEFAULT_LIMITS: list[RateLimit] = [
    RateLimit(limit_id=LIMIT_INFO, capacity=20, period_s=1.0),
    RateLimit(limit_id=LIMIT_EXCHANGE, capacity=10, period_s=1.0),
]


class HLClient:
    def __init__(
        self,
        mode: str,
        account_address: str,
        *,
        timeout: float = 10.0,
        wallet: LocalAccount | None = None,
        throttler: AsyncThrottler | None = None,
    ) -> None:
        self.mode = mode
        self.account_address = account_address
        self._throttler = throttler or AsyncThrottler(DEFAULT_LIMITS)
        # SDK 0.22.0 testnet spot_meta bug: universe references missing token
        # indices. Pass an empty spot_meta to skip spot-asset mapping (we don't
        # trade spot). See docs/lessons.md.
        spot_meta_stub: Any = {"universe": [], "tokens": []}
        base_url = api_url(mode)
        self._info = Info(
            base_url=base_url,
            skip_ws=True,
            timeout=timeout,
            spot_meta=spot_meta_stub,
        )
        self._exchange: Exchange | None = None
        if wallet is not None:
            self._exchange = Exchange(
                wallet=wallet,
                base_url=base_url,
                account_address=account_address,
                spot_meta=spot_meta_stub,
                timeout=timeout,
            )
        # WS-fed mid cache. Updated from WS callbacks (worker thread); read
        # from the runner tick (asyncio thread). Lock keeps the dict consistent.
        self._mid_cache: dict[str, tuple[float, str]] = {}
        self._mid_cache_lock = threading.Lock()

    # ---- mid cache (thread-safe) ----

    def update_mids(self, mids: dict[str, str]) -> None:
        """Bulk-update the mid cache. Safe to call from a non-asyncio thread."""
        ts = time.time()
        with self._mid_cache_lock:
            for coin, price in mids.items():
                self._mid_cache[coin] = (ts, price)

    def cached_mid(self, coin: str, max_age_s: float = 5.0) -> str | None:
        """Read a mid if cached within `max_age_s`, else None."""
        with self._mid_cache_lock:
            entry = self._mid_cache.get(coin)
        if entry is None:
            return None
        ts, price = entry
        if (time.time() - ts) > max_age_s:
            return None
        return price

    # ---- read path ----

    async def _info_call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        await self._throttler.acquire(LIMIT_INFO)
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except AppError:
            raise
        except Exception as e:
            raise classify(e) from e

    def _require_exchange(self) -> Exchange:
        if self._exchange is None:
            raise AuthError("HLClient was constructed without a wallet; write path disabled")
        return self._exchange

    async def _exchange_call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        if self._exchange is None:
            raise AuthError("HLClient was constructed without a wallet; write path disabled")
        await self._throttler.acquire(LIMIT_EXCHANGE)
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except AppError:
            raise
        except Exception as e:
            raise classify(e) from e

    async def user_state(self) -> dict[str, Any]:
        result = await self._info_call(self._info.user_state, self.account_address)
        return dict(result)

    async def open_orders(self) -> list[dict[str, Any]]:
        result = await self._info_call(self._info.open_orders, self.account_address)
        return list(result)

    async def all_mids(self) -> dict[str, str]:
        result = await self._info_call(self._info.all_mids)
        return dict(result)

    async def user_fills(self) -> list[dict[str, Any]]:
        result = await self._info_call(self._info.user_fills, self.account_address)
        return list(result)

    async def meta(self) -> dict[str, Any]:
        result = await self._info_call(self._info.meta)
        return dict(result)

    async def funding_rate(self, pair: str) -> float | None:
        """Fetch current hourly funding rate for `pair`. Returns None if not found.

        Uses meta_and_asset_ctxs (one info call) and reads the rate from the
        asset context whose universe entry matches `pair`. HL publishes funding
        as an hourly rate; APY = rate * 24 * 365.
        """
        result = await self._info_call(self._info.meta_and_asset_ctxs)
        universe = result[0].get("universe", [])
        ctxs = result[1] if len(result) > 1 else []
        for asset, ctx in zip(universe, ctxs, strict=False):
            if asset.get("name") == pair:
                rate = ctx.get("funding")
                return float(rate) if rate is not None else None
        return None

    # ---- write path ----

    async def set_leverage(self, coin: str, leverage: int, *, is_cross: bool = False) -> Any:
        exchange = self._require_exchange()
        return await self._exchange_call(
            exchange.update_leverage, leverage, coin, is_cross
        )

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        *,
        tif: str = "Gtc",
        reduce_only: bool = False,
        cloid: str | None = None,
    ) -> dict[str, Any]:
        exchange = self._require_exchange()
        order_type: dict[str, Any] = {"limit": {"tif": tif}}
        cloid_obj = Cloid.from_str(cloid) if cloid else None
        result = await self._exchange_call(
            exchange.order,
            coin,
            is_buy,
            size,
            price,
            order_type,
            reduce_only,
            cloid_obj,
        )
        return dict(result)

    async def market_close(self, coin: str, *, slippage: float = 0.05) -> dict[str, Any]:
        exchange = self._require_exchange()
        result = await self._exchange_call(
            exchange.market_close, coin, None, None, slippage
        )
        return dict(result)

    async def cancel_by_cloid(self, coin: str, cloid: str) -> dict[str, Any]:
        exchange = self._require_exchange()
        cloid_obj = Cloid.from_str(cloid)
        result = await self._exchange_call(exchange.cancel_by_cloid, coin, cloid_obj)
        return dict(result)

    async def cancel(self, coin: str, oid: int) -> dict[str, Any]:
        exchange = self._require_exchange()
        result = await self._exchange_call(exchange.cancel, coin, oid)
        return dict(result)
