"""/health endpoint (stub for M0)."""

from __future__ import annotations


class HealthServer:
    def __init__(self, port: int) -> None:
        self.port = port

    async def start(self) -> None:
        raise NotImplementedError("HealthServer wired in M3")
