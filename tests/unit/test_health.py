"""HealthServer tests: real aiohttp server on an ephemeral port."""

from __future__ import annotations

import socket
import time

import aiohttp
import pytest

from osbot.observability.health import HealthServer, HealthState


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.asyncio
async def test_health_returns_unhealthy_when_no_ticks() -> None:
    state = HealthState()
    server = HealthServer(port=_free_port(), state=state)
    await server.start()
    try:
        async with (
            aiohttp.ClientSession() as s,
            s.get(f"http://127.0.0.1:{server.port}/health") as r,
        ):
                assert r.status == 503
                body = await r.json()
                assert body["status"] == "unhealthy"
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_health_returns_healthy_after_tick() -> None:
    state = HealthState()
    state.last_tick_ts = time.time()
    state.tick_count = 1
    state.account_value = 908.01
    server = HealthServer(port=_free_port(), state=state)
    await server.start()
    try:
        async with (
            aiohttp.ClientSession() as s,
            s.get(f"http://127.0.0.1:{server.port}/health") as r,
        ):
                assert r.status == 200
                body = await r.json()
                assert body["status"] == "healthy"
                assert body["tick_count"] == 1
                assert body["account_value"] == 908.01
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_health_unhealthy_when_graceful_stop() -> None:
    state = HealthState()
    state.last_tick_ts = time.time()
    state.graceful_stop = True
    server = HealthServer(port=_free_port(), state=state)
    await server.start()
    try:
        async with (
            aiohttp.ClientSession() as s,
            s.get(f"http://127.0.0.1:{server.port}/health") as r,
        ):
                assert r.status == 503
    finally:
        await server.stop()
