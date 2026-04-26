"""WebSocket subscriber for HL `allMids` and `userFills`.

Wraps a separate `Info(skip_ws=False)` whose only job is to host the SDK's
`WebsocketManager` thread. The read-path `Info` we use for REST stays at
`skip_ws=True` — keeps the WS blast radius contained.

Callbacks run in the WS thread; consumers must be thread-safe. We only mutate
the receiver's state via methods documented as thread-safe (`HLClient.update_mid`,
`FillEventsManager.ingest`).

Reconnection: the underlying SDK does not auto-reconnect. The runner's
watchdog reads `last_message_ts`; when stale (>30s), `ws_connected` flips to
False and the runner falls back to REST. A future revision can add a
reconnect loop; for now, the design degrades cleanly.
"""

from __future__ import annotations

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


class WsSubscriber:
    def __init__(self, mode: str, account_address: str, *, timeout: float = 10.0) -> None:
        self.mode = mode
        self.account_address = account_address
        self._lock = threading.Lock()
        self._last_message_ts: float = 0.0
        # SDK 0.22.0 testnet spot_meta bug — same workaround as HLClient.
        spot_meta_stub: Any = {"universe": [], "tokens": []}
        self._info = Info(
            base_url=api_url(mode),
            skip_ws=False,
            timeout=timeout,
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

    def subscribe_all_mids(self, callback: AllMidsCallback) -> int:
        def wrapper(msg: Any) -> None:
            self._record_message()
            data = msg.get("data") if isinstance(msg, dict) else None
            mids = data.get("mids") if isinstance(data, dict) else None
            if isinstance(mids, dict):
                callback(cast(dict[str, str], mids))

        return int(self._info.subscribe({"type": "allMids"}, wrapper))

    def subscribe_user_fills(self, callback: UserFillsCallback) -> int:
        def wrapper(msg: Any) -> None:
            self._record_message()
            data = msg.get("data") if isinstance(msg, dict) else None
            fills = data.get("fills") if isinstance(data, dict) else None
            if isinstance(fills, list):
                for fill in fills:
                    if isinstance(fill, dict):
                        callback(cast(dict[str, Any], fill))

        sub: dict[str, Any] = {"type": "userFills", "user": self.account_address}
        return int(self._info.subscribe(sub, wrapper))

    def stop(self) -> None:
        """Best-effort tear-down. SDK's ws_manager has its own stop()."""
        ws_manager = getattr(self._info, "ws_manager", None)
        if ws_manager is None:
            return
        try:
            ws_manager.stop()
        except Exception as e:
            log.warning("ws_subscriber stop failed: %s", e)
