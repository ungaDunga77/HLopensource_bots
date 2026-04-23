"""Tiny /health endpoint served by aiohttp.

The runner updates `HealthState` each tick; the server reads that dict and emits
JSON. Used by process supervisors / curl checks during the 24h testnet run.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from aiohttp import web

from osbot.observability import get_logger

log = get_logger("osbot.health")

_STALE_TICK_S = 30.0


@dataclass
class HealthState:
    started_ts: float = field(default_factory=time.time)
    last_tick_ts: float = 0.0
    account_value: float = 0.0
    position_count: int = 0
    open_order_count: int = 0
    tick_count: int = 0
    errors: int = 0
    ws_connected: bool = False
    graceful_stop: bool = False

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        last_tick_age = now - self.last_tick_ts if self.last_tick_ts else None
        healthy = (
            not self.graceful_stop
            and self.last_tick_ts > 0
            and (now - self.last_tick_ts) < _STALE_TICK_S
        )
        return {
            "status": "healthy" if healthy else "unhealthy",
            "uptime_s": now - self.started_ts,
            "last_tick_age_s": last_tick_age,
            "tick_count": self.tick_count,
            "errors": self.errors,
            "account_value": self.account_value,
            "position_count": self.position_count,
            "open_order_count": self.open_order_count,
            "ws_connected": self.ws_connected,
            "graceful_stop": self.graceful_stop,
        }


class HealthServer:
    def __init__(self, port: int, state: HealthState) -> None:
        self.port = port
        self.state = state
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/health", self._handle)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host="127.0.0.1", port=self.port)
        await site.start()
        log.info("health server listening on 127.0.0.1:%d", self.port)

    async def stop(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle(self, request: web.Request) -> web.Response:
        del request
        snap = self.state.snapshot()
        status_code = 200 if snap["status"] == "healthy" else 503
        return web.json_response(snap, status=status_code)
