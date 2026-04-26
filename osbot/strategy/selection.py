"""Forager-style pair selection.

Per Passivbot's `forager` mode (lessons.md:205, custom-bot-design-notes.md:139).
Each candidate is scored by:

  score = log_range_window * volume_24h_usd

`log_range_window` is `max(log p) - min(log p)` over a rolling window of
1-minute price buckets — a clean, scale-free volatility signal. Volume comes
from HL's `dayNtlVlm` field on `meta_and_asset_ctxs` (already a smoothed 24h
window — we don't need to EMA it ourselves).

Selector is pure: it owns its own minute-bucketed price history per candidate
and a snapshot of the latest asset_ctx. The runner pumps `update_mid()` on
each tick and `update_asset_ctxs()` on each `meta_and_asset_ctxs` fetch, then
calls `rank()` at rotation boundaries.

Filter: pairs with `volume_24h_usd < min_volume_usd_24h` are excluded; pairs
with fewer than `_MIN_BUCKETS` minute samples are excluded (cold start).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from osbot.connector.errors import AppError, StructuralError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger

log = get_logger("osbot.selection")

_MIN_BUCKETS = 4  # minimum minute samples before a pair is rankable


@dataclass
class PairScore:
    pair: str
    log_range: float
    volume_24h_usd: float
    score: float


@dataclass
class _PairHistory:
    """Per-pair rolling minute-bucketed prices for log_range computation."""

    window_min: int
    buckets: deque[tuple[int, float]] = field(default_factory=deque)

    def sample(self, ts: float, mid: float) -> None:
        if mid <= 0:
            return
        minute = int(ts // 60)
        if self.buckets and self.buckets[-1][0] == minute:
            self.buckets[-1] = (minute, mid)
        else:
            self.buckets.append((minute, mid))
        cutoff = minute - self.window_min
        while self.buckets and self.buckets[0][0] <= cutoff:
            self.buckets.popleft()

    def log_range(self) -> float | None:
        if len(self.buckets) < _MIN_BUCKETS:
            return None
        prices = [p for _, p in self.buckets]
        return math.log(max(prices)) - math.log(min(prices))


class ForagerSelector:
    def __init__(
        self,
        candidates: list[str],
        *,
        log_range_window_min: int = 16,
        min_volume_usd_24h: float = 10_000.0,
    ) -> None:
        if not candidates:
            raise ValueError("candidates cannot be empty")
        self.candidates: list[str] = list(candidates)
        self.min_volume_usd_24h = min_volume_usd_24h
        self._history: dict[str, _PairHistory] = {
            p: _PairHistory(window_min=log_range_window_min) for p in candidates
        }
        self._volume: dict[str, float] = {}

    def update_mids(self, ts: float, mids: dict[str, str | float]) -> None:
        """Update per-pair minute-bucketed history from a mids dict."""
        for pair, h in self._history.items():
            raw = mids.get(pair)
            if raw is None:
                continue
            try:
                price = float(raw)
            except (TypeError, ValueError):
                continue
            h.sample(ts, price)

    def update_asset_ctxs(
        self, universe: list[dict[str, Any]], ctxs: list[dict[str, Any]]
    ) -> None:
        """Snapshot the 24h notional volume per candidate from meta_and_asset_ctxs."""
        for asset, ctx in zip(universe, ctxs, strict=False):
            name = asset.get("name")
            if name not in self._history:
                continue
            try:
                self._volume[name] = float(ctx.get("dayNtlVlm", 0.0))
            except (TypeError, ValueError):
                continue

    def rank(self) -> list[PairScore]:
        """Rank candidates by log_range * volume_24h. Returns sorted list (best first).

        Pairs with insufficient samples or below min volume are excluded.
        """
        scored: list[PairScore] = []
        for pair in self.candidates:
            lr = self._history[pair].log_range()
            if lr is None:
                continue
            vol = self._volume.get(pair, 0.0)
            if vol < self.min_volume_usd_24h:
                continue
            scored.append(
                PairScore(pair=pair, log_range=lr, volume_24h_usd=vol, score=lr * vol)
            )
        scored.sort(key=lambda s: -s.score)
        return scored

    def top_n(self, n: int) -> list[str]:
        return [s.pair for s in self.rank()[:n]]


async def prepare_forager_pairs(
    client: HLClient,
    candidates: list[str],
    leverage: int,
) -> dict[str, int]:
    """Validate candidate pairs against HL meta + set isolated leverage on each.

    Returns a `pair → szDecimals` map containing only pairs that exist in HL's
    universe. Pairs missing from the venue are dropped with a warning rather
    than raising — the forager is resilient to partial-universe deployments
    (e.g. some HL pairs are mainnet-only).
    """
    meta = await client.meta()
    universe = {u["name"]: int(u.get("szDecimals", 0)) for u in meta.get("universe", [])}
    valid: dict[str, int] = {}
    for pair in candidates:
        if pair not in universe:
            log.warning("forager: candidate %s not in HL universe; dropping", pair)
            continue
        valid[pair] = universe[pair]
    if not valid:
        raise StructuralError("forager: no candidate pairs found on HL")
    for pair in valid:
        try:
            await client.set_leverage(pair, leverage, is_cross=False)
        except AppError as e:
            raise StructuralError(
                f"forager: set_leverage failed for {pair}: {e.message}", cause=e
            ) from e
    log.info("forager: prepared %d pairs (leverage=%dx isolated)", len(valid), leverage)
    return valid
