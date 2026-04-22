"""Interval-aligned sleep helper.

Pattern from memlabs-hl-bot: sleep until the next bar boundary rather than
`sleep(interval)`, so tick phase doesn't drift across restarts.
"""

from __future__ import annotations

import asyncio
import time


async def aligned_sleep(interval_s: float, *, epoch: float = 0.0) -> None:
    """Sleep until the next multiple of `interval_s` since `epoch`."""
    if interval_s <= 0:
        raise ValueError("interval_s must be > 0")
    now = time.time()
    elapsed = now - epoch
    remainder = elapsed % interval_s
    delay = interval_s - remainder if remainder > 0 else interval_s
    await asyncio.sleep(delay)
