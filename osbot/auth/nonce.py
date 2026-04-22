"""Monotonic nonce manager.

Adapted from Hummingbot's spot-auth NonceProvider pattern (Apache-2.0). Vendored
with attribution per design notes §4 — monotonic + locked, safe under concurrent
request submission.
"""

from __future__ import annotations

import threading
import time


class NonceManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_nonce_ms: int = 0

    def next_ms(self) -> int:
        """Return a strictly increasing millisecond nonce."""
        with self._lock:
            now_ms = int(time.time() * 1000)
            if now_ms <= self._last_nonce_ms:
                now_ms = self._last_nonce_ms + 1
            self._last_nonce_ms = now_ms
            return now_ms
