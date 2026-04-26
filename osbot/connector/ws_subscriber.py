"""WebSocket subscriber for HL `allMids` and `userFills` with auto-reconnect.

Wraps a separate `Info(skip_ws=False)` whose only job is to host the SDK's
`WebsocketManager` thread. The read-path `Info` we use for REST stays at
`skip_ws=True` — keeps WS blast radius contained.

Callbacks run in the WS thread; consumers must be thread-safe. We only mutate
the receiver's state via methods documented as thread-safe
(`HLClient.update_mids`, `FillEventsManager.ingest`).

Reconnect:
  HL closes WS connections periodically (observed: `Expired` close after ~10
  min). The SDK's `WebsocketManager` does not auto-reconnect. We run an async
  watchdog that detects either a dead `ws_manager` thread or a stale
  `last_message_ts`, tears the old `Info` down, constructs a fresh one, and
  replays every recorded subscription. Reconnect attempts back off
  exponentially up to a 60s cap; resets on a successful re-subscribe.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections.abc import Callable
from typing import Any, cast

from hyperliquid.info import Info

from osbot.connector.endpoints import api_url
from osbot.observability import get_logger

log = get_logger("osbot.ws")

AllMidsCallback = Callable[[dict[str, str]], None]
UserFillsCallback = Callable[[dict[str, Any]], None]

_WATCHDOG_INTERVAL_S = 10.0
_STALE_THRESHOLD_S = 60.0
_RECONNECT_BACKOFF_BASE_S = 1.0
_RECONNECT_BACKOFF_CAP_S = 60.0


class WsSubscriber:
    def __init__(self, mode: str, account_address: str, *, timeout: float = 10.0) -> None:
        self.mode = mode
        self.account_address = account_address
        self.timeout = timeout
        self._lock = threading.Lock()
        self._last_message_ts: float = 0.0
        # Subscriptions are stored so the watchdog can replay them on reconnect.
        # Each entry is (subscription_dict, wrapper_fn) — the SDK only knows
        # about the wrapper; we keep the original callback alive via the closure.
        self._subscriptions: list[tuple[dict[str, Any], Callable[[Any], None]]] = []
        self._stopping = False
        self._reconnect_attempts = 0
        self._info = self._make_info()
        self._watchdog_task: asyncio.Task[None] | None = None

    def _make_info(self) -> Info:
        # SDK 0.22.0 testnet spot_meta bug — same workaround as HLClient.
        spot_meta_stub: Any = {"universe": [], "tokens": []}
        return Info(
            base_url=api_url(self.mode),
            skip_ws=False,
            timeout=self.timeout,
            spot_meta=spot_meta_stub,
        )

    @property
    def last_message_ts(self) -> float:
        with self._lock:
            return self._last_message_ts

    def is_connected(self, max_age_s: float = 30.0) -> bool:
        with self._lock:
            if self._last_message_ts == 0.0:
                return False
            return (time.time() - self._last_message_ts) < max_age_s

    def _record_message(self) -> None:
        with self._lock:
            self._last_message_ts = time.time()

    def _make_all_mids_wrapper(self, callback: AllMidsCallback) -> Callable[[Any], None]:
        def wrapper(msg: Any) -> None:
            self._record_message()
            data = msg.get("data") if isinstance(msg, dict) else None
            mids = data.get("mids") if isinstance(data, dict) else None
            if isinstance(mids, dict):
                callback(cast(dict[str, str], mids))

        return wrapper

    def _make_user_fills_wrapper(self, callback: UserFillsCallback) -> Callable[[Any], None]:
        def wrapper(msg: Any) -> None:
            self._record_message()
            data = msg.get("data") if isinstance(msg, dict) else None
            fills = data.get("fills") if isinstance(data, dict) else None
            if isinstance(fills, list):
                for fill in fills:
                    if isinstance(fill, dict):
                        callback(cast(dict[str, Any], fill))

        return wrapper

    def subscribe_all_mids(self, callback: AllMidsCallback) -> int:
        sub: dict[str, Any] = {"type": "allMids"}
        wrapper = self._make_all_mids_wrapper(callback)
        self._subscriptions.append((sub, wrapper))
        return int(self._info.subscribe(sub, wrapper))

    def subscribe_user_fills(self, callback: UserFillsCallback) -> int:
        sub: dict[str, Any] = {"type": "userFills", "user": self.account_address}
        wrapper = self._make_user_fills_wrapper(callback)
        self._subscriptions.append((sub, wrapper))
        return int(self._info.subscribe(sub, wrapper))

    def _ws_alive(self) -> bool:
        ws_manager = getattr(self._info, "ws_manager", None)
        if ws_manager is None:
            return False
        is_alive = getattr(ws_manager, "is_alive", None)
        return bool(is_alive()) if callable(is_alive) else False

    def reconnect(self) -> None:
        """Tear down the current Info, build a fresh one, replay subscriptions.

        Synchronous (the SDK's WS lifecycle is thread-based, not async). Safe
        to call from the watchdog. Caller is responsible for backoff.
        """
        old = getattr(self._info, "ws_manager", None)
        if old is not None:
            try:
                old.stop()
            except Exception as e:
                log.warning("ws reconnect: old stop() raised %s", e)
        self._info = self._make_info()
        for sub, wrapper in self._subscriptions:
            self._info.subscribe(sub, wrapper)
        log.info("ws reconnected: %d subscriptions replayed", len(self._subscriptions))

    async def _watchdog(self) -> None:
        log.info("ws watchdog started")
        while not self._stopping:
            try:
                await asyncio.sleep(_WATCHDOG_INTERVAL_S)
            except asyncio.CancelledError:
                break
            if self._stopping:
                break
            stale = not self.is_connected(max_age_s=_STALE_THRESHOLD_S)
            dead = not self._ws_alive()
            if not (stale or dead):
                self._reconnect_attempts = 0
                continue
            self._reconnect_attempts += 1
            backoff = min(
                _RECONNECT_BACKOFF_CAP_S,
                _RECONNECT_BACKOFF_BASE_S * (2 ** (self._reconnect_attempts - 1)),
            )
            log.warning(
                "ws watchdog: stale=%s dead=%s, attempt=%d backoff=%.1fs",
                stale,
                dead,
                self._reconnect_attempts,
                backoff,
            )
            try:
                await asyncio.to_thread(self.reconnect)
            except Exception as e:
                log.error("ws reconnect failed: %s; will retry after backoff", e)
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                break
        log.info("ws watchdog stopped")

    def start_watchdog(self) -> None:
        """Schedule the reconnect watchdog on the running event loop."""
        if self._watchdog_task is not None:
            return
        self._watchdog_task = asyncio.create_task(self._watchdog())

    async def stop(self) -> None:
        """Tear down: stop watchdog, then SDK ws_manager."""
        self._stopping = True
        if self._watchdog_task is not None:
            self._watchdog_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watchdog_task
            self._watchdog_task = None
        ws_manager = getattr(self._info, "ws_manager", None)
        if ws_manager is None:
            return
        try:
            ws_manager.stop()
        except Exception as e:
            log.warning("ws_subscriber stop failed: %s", e)
