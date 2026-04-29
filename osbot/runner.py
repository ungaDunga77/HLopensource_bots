"""Strategy-loop runner — the M3 main tick per phase5-synthesis.md section 5.4.

One asyncio task owns the loop. Each tick:
  1. Reconcile fills via REST (WS upgrade deferred to M4).
  2. Pull mid from `all_mids`, sample into `MarketState`.
  3. `risk.precheck()` — raises StructuralError on daily-loss breach.
  4. Every `replan_interval_s`: re-plan grid (cancel + submit).
  5. Periodic reconciliation sweep + equity snapshot.

Error handling:
  - `AuthError` -> graceful_stop.
  - `StructuralError` from precheck -> graceful_stop.
  - `StructuralError` from submit -> drop the single action, continue.
  - `NetworkError` / `RateLimitError` -> count, continue (retry next tick).

Signal handling: SIGINT/SIGTERM set graceful_stop; the loop exits at the next
tick boundary and runs a best-effort cancel-all in `finally`.

For M3 this is a plain grid — no exit logic per-position; reliance on mean
reversion for inventory to unwind. Proper TripleBarrier-driven exits land in
M4 (docs/phase5-synthesis.md 5.5).
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import time
from dataclasses import dataclass, field
from typing import Any

from osbot.config import BaseConfig
from osbot.connector.errors import AppError, AuthError, ErrorCategory, StructuralError
from osbot.connector.hl_client import HLClient
from osbot.connector.ws_subscriber import WsSubscriber
from osbot.observability import get_logger
from osbot.observability.health import HealthServer, HealthState
from osbot.risk.manager import Action, RiskManager
from osbot.startup import StartupContext, run_startup
from osbot.state.fills import FillEventsManager
from osbot.strategy.exit_manager import ExitManager
from osbot.strategy.exits import TripleBarrier
from osbot.strategy.grid import GridPlan, GridStrategy, MarketState, OrderSubmit
from osbot.strategy.selection import ForagerSelector, prepare_forager_pairs

log = get_logger("osbot.runner")


DEFAULT_TICK_INTERVAL_S = 1.0
DEFAULT_REPLAN_INTERVAL_S = 300.0
DEFAULT_RECONCILE_EVERY = 60  # tick-count counts double now (1s ticks)
DEFAULT_EQUITY_SNAPSHOT_EVERY = 120
DEFAULT_FILL_RECONCILE_EVERY = 60  # REST safety-net cadence (WS is primary)
DEFAULT_FUNDING_SAMPLE_EVERY = 60  # ~1 min at 1s ticks

_BACKOFF_BASE_S = 2.0
_BACKOFF_CAP_S = 60.0
_BACKOFF_CATEGORIES: frozenset[ErrorCategory] = frozenset(
    {ErrorCategory.NETWORK, ErrorCategory.RATE_LIMIT}
)


@dataclass
class _RetryState:
    """Exponential-backoff counter for retryable upstream errors.

    HL testnet has periodic ~2-min outage windows; without backoff the runner
    hammers the API at full tick cadence the entire window, both polluting the
    error counter and contributing to the 429 storm. Backoff doubles per
    consecutive retryable failure (network or rate_limit) up to a 60s cap;
    other categories are unaffected.
    """

    consecutive: int = 0

    def on_error(self, category: ErrorCategory) -> float:
        if category not in _BACKOFF_CATEGORIES:
            return 0.0
        self.consecutive += 1
        return float(min(_BACKOFF_CAP_S, _BACKOFF_BASE_S * (2 ** (self.consecutive - 1))))

    def on_success(self) -> None:
        self.consecutive = 0


async def _cancel_cloid(client: HLClient, pair: str, cloid: str) -> None:
    try:
        await client.cancel_by_cloid(pair, cloid)
    except AppError as e:
        log.warning("cancel_by_cloid %s failed: %s (%s)", cloid, e.message, e.category)


async def _submit_one(
    client: HLClient,
    pair: str,
    sub: OrderSubmit,
    risk: RiskManager,
    health: HealthState,
) -> str | None:
    action = Action(side=sub.side, size=sub.size, price=sub.price, reduce_only=sub.reduce_only)
    if not await risk.margin_ok(action):
        return None
    try:
        await client.place_order(
            pair,
            is_buy=(sub.side == "buy"),
            size=sub.size,
            price=sub.price,
            tif=sub.tif,
            reduce_only=sub.reduce_only,
            cloid=sub.cloid,
        )
    except StructuralError as e:
        log.warning("submit dropped: %s level=%d side=%s", e.message, sub.level, sub.side)
        health.errors += 1
        return None
    except AuthError:
        raise
    except AppError as e:
        log.warning("submit retryable fail: %s (%s)", e.message, e.category)
        health.errors += 1
        return None
    return sub.cloid


async def _apply_plan(
    client: HLClient,
    pair: str,
    plan: GridPlan,
    risk: RiskManager,
    health: HealthState,
) -> list[str]:
    for cloid in plan.cancels:
        await _cancel_cloid(client, pair, cloid)
    live: list[str] = []
    for sub in plan.submits:
        result = await _submit_one(client, pair, sub, risk, health)
        if result is not None:
            live.append(result)
    return live


async def _reconcile_orders(
    client: HLClient, pair: str, tracked: list[str]
) -> list[str]:
    live_orders = await client.open_orders()
    live_cloids: set[str] = {
        str(o.get("cloid"))
        for o in live_orders
        if o.get("coin") == pair and o.get("cloid")
    }
    return [c for c in tracked if c in live_cloids]


async def _graceful_shutdown(client: HLClient, pair: str, tracked: list[str]) -> None:
    log.info("runner: graceful shutdown — cancelling %d tracked orders", len(tracked))
    for cloid in tracked:
        await _cancel_cloid(client, pair, cloid)
    # Also sweep any stray orders for the pair.
    try:
        live = await client.open_orders()
    except AppError as e:
        log.warning("graceful shutdown: open_orders failed: %s", e.message)
        return
    for o in live:
        if o.get("coin") != pair:
            continue
        oid = o.get("oid")
        if oid is None:
            continue
        try:
            await client.cancel(pair, int(oid))
        except AppError as e:
            log.warning("graceful shutdown: cancel oid=%s failed: %s", oid, e.message)


def _install_signal_handlers(health: HealthState) -> None:
    loop = asyncio.get_running_loop()

    def handler(signame: str) -> None:
        log.info("runner: received %s, setting graceful_stop", signame)
        health.graceful_stop = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, handler, sig.name)


@dataclass
class _PairRuntime:
    """Per-pair runtime state. One instance per actively-traded pair.

    Forager v1 keeps a dict of these on _RunnerState. When forager.enabled is
    False, the dict has exactly one entry (cfg.strategy.pair) and behavior is
    identical to single-pair mode.

    `draining=True` marks a pair the forager has rotated out of: its tracked
    grid is cancelled and `_tick_pair` skips replanning. ExitManager keeps
    running so any open position exits naturally via TripleBarrier.
    """

    pair: str
    sz_decimals: int
    market: MarketState
    grid: GridStrategy
    exit_mgr: ExitManager
    tracked_cloids: list[str] = field(default_factory=list)
    draining: bool = False


def _build_pair_runtime(
    cfg: BaseConfig, ctx: StartupContext, pair: str, sz_decimals: int, strategy_id: int
) -> _PairRuntime:
    triple_barrier = TripleBarrier(
        sl_pct=cfg.strategy.sl_pct,
        tp_pct=cfg.strategy.tp_pct,
        ttl_s=float(cfg.strategy.exit_ttl_s),
        consecutive_breaches_required=cfg.strategy.sl_consecutive_breaches,
    )
    grid = GridStrategy(cfg, sz_decimals, strategy_id=strategy_id)
    exit_mgr = ExitManager(client=ctx.client, pair=pair, triple_barrier=triple_barrier)
    return _PairRuntime(
        pair=pair, sz_decimals=sz_decimals, market=MarketState(), grid=grid, exit_mgr=exit_mgr
    )


def _strategy_id_for(pair: str) -> int:
    """Stable per-pair cloid prefix so concurrent pairs get attributable fills."""
    h = 0
    for ch in pair:
        h = (h * 131 + ord(ch)) & 0xFFFF
    return h or 0xCAFE


def _extract_signed_szi(user_state: dict[str, Any], pair: str) -> float:
    """Signed position size for `pair` from HL user_state, or 0.0 if flat/missing."""
    for p in user_state.get("assetPositions") or []:
        pos = p.get("position") or {}
        if pos.get("coin") != pair:
            continue
        try:
            return float(pos.get("szi", "0"))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


async def _tick_pair(
    pr: _PairRuntime,
    *,
    ctx: StartupContext,
    risk: RiskManager,
    health: HealthState,
    state: dict[str, Any],
    tick_idx: int,
    now: float,
) -> None:
    """Per-pair work: mid sample, exit evaluation, replan/submit, reconcile."""
    client = ctx.client
    shadow = ctx.shadow

    mid_str = client.cached_mid(pr.pair)
    if mid_str is None:
        mids = await client.all_mids()
        mid_str = mids.get(pr.pair)
    if not mid_str:
        log.warning("tick %d: no mid for %s", tick_idx, pr.pair)
        return
    mid = float(mid_str)
    pr.market.sample(now, mid)

    user_state = await client.user_state()
    closed = await pr.exit_mgr.evaluate_and_act(user_state, mid, health, now=now)
    if closed:
        shadow.snapshot("exit_close", {"tick": tick_idx, "pair": pr.pair, "mid": mid})
        health.position_count = 0

    if pr.draining:
        return

    if pr.grid.should_replan(now, state["replan_interval_s"], have_grid=bool(pr.tracked_cloids)):
        position_signed_szi = _extract_signed_szi(user_state, pr.pair)
        plan = pr.grid.plan(
            now=now,
            mid=mid,
            market=pr.market,
            balance_usd=risk.last_equity,
            open_grid_cloids=pr.tracked_cloids,
            position_signed_szi=position_signed_szi,
        )
        shadow.snapshot(
            "grid_plan",
            {
                "tick": tick_idx,
                "pair": pr.pair,
                "mid": mid,
                "cancels": len(plan.cancels),
                "submits": len(plan.submits),
                "equity": risk.last_equity,
            },
        )
        pr.tracked_cloids = await _apply_plan(client, pr.pair, plan, risk, health)

    if tick_idx % state["reconcile_every"] == 0:
        pr.tracked_cloids = await _reconcile_orders(client, pr.pair, pr.tracked_cloids)


async def _rotate_forager(
    *,
    ctx: StartupContext,
    cfg: BaseConfig,
    pairs: dict[str, _PairRuntime],
    selector: ForagerSelector,
    pair_meta: dict[str, int],
    now: float,
) -> None:
    """Run one forager rotation: drain pairs no longer in top_n, add new ones."""
    desired = set(selector.top_n(cfg.forager.top_n))
    if not desired:
        log.warning("forager: rank produced empty top_n; skipping rotation")
        return
    active = {p for p, pr in pairs.items() if not pr.draining}
    to_add = desired - active
    to_drop = active - desired

    for p in to_drop:
        pr = pairs[p]
        pr.draining = True
        for cloid in list(pr.tracked_cloids):
            await _cancel_cloid(ctx.client, p, cloid)
        pr.tracked_cloids = []
        log.info("forager: draining %s (rotated out)", p)

    for p in to_add:
        if p in pairs:
            pairs[p].draining = False
            log.info("forager: re-activating %s", p)
            continue
        if p not in pair_meta:
            log.warning("forager: cannot add %s — no szDecimals (skipped)", p)
            continue
        pr = _build_pair_runtime(cfg, ctx, p, pair_meta[p], _strategy_id_for(p))
        pairs[p] = pr
        log.info("forager: added %s (szDec=%d)", p, pair_meta[p])

    # GC fully-drained pairs (draining + no orders + no position-state).
    to_remove: list[str] = []
    for p, pr in pairs.items():
        if not pr.draining:
            continue
        if pr.tracked_cloids:
            continue
        # ExitManager keeps state while a position exists; once flat it clears.
        if pr.exit_mgr._state and pr.exit_mgr._state.get(p) is not None:
            continue
        to_remove.append(p)
    for p in to_remove:
        log.info("forager: removed %s (drained + flat)", p)
        del pairs[p]

    log.info(
        "forager rotation: active=%s drained=%s now=%.0f",
        sorted(p for p, pr in pairs.items() if not pr.draining),
        sorted(p for p, pr in pairs.items() if pr.draining),
        now,
    )


async def _tick(  # noqa: PLR0912
    *,
    ctx: StartupContext,
    cfg: BaseConfig,
    pairs: dict[str, _PairRuntime],
    risk: RiskManager,
    fills_mgr: FillEventsManager,
    health: HealthState,
    ws: WsSubscriber | None,
    selector: ForagerSelector | None,
    pair_meta: dict[str, int],
    state: dict[str, Any],
    tick_idx: int,
) -> None:
    client = ctx.client
    shadow = ctx.shadow
    now = time.time()

    health.ws_connected = ws is not None and ws.is_connected()

    # Drain WS-buffered fills first (thread-safe, no I/O), then REST safety net
    # at a slower cadence to catch anything WS missed.
    ws_fills = fills_mgr.drain_ws_buffer()
    for f in ws_fills:
        shadow.record_fill(str(f.get("tid", "")), f)
    if tick_idx % state["fill_reconcile_every"] == 0:
        rest_fills = await fills_mgr.reconcile()
        for f in rest_fills:
            shadow.record_fill(str(f.get("tid", "")), f)
        ws_fills = ws_fills + rest_fills
    if ws_fills:
        log.info("tick %d: %d new fills", tick_idx, len(ws_fills))

    await risk.precheck()

    # Forager: feed selector with mids each tick (cheap), update ctxs at the
    # funding cadence, rotate at rotate_every_s.
    if selector is not None and cfg.forager.enabled:
        # Pull all_mids once per tick when selector is active. For non-active
        # candidates we don't have cached_mid (no per-pair caching beyond WS).
        try:
            all_mids = await client.all_mids()
            selector.update_mids(now, all_mids)  # type: ignore[arg-type]
        except AppError as e:
            log.warning("forager: all_mids failed: %s (selector starved this tick)", e.message)
        if tick_idx % state["funding_sample_every"] == 0:
            try:
                meta_ctxs = await client.meta_and_asset_ctxs()
                selector.update_asset_ctxs(meta_ctxs[0].get("universe", []), meta_ctxs[1])
            except AppError as e:
                log.warning("forager: meta_and_asset_ctxs failed: %s", e.message)
        last_rot = state.get("last_rotate_ts", 0.0)
        if (now - last_rot) >= cfg.forager.rotate_every_s:
            state["last_rotate_ts"] = now
            await _rotate_forager(
                ctx=ctx, cfg=cfg, pairs=pairs, selector=selector,
                pair_meta=pair_meta, now=now,
            )

    for pr in list(pairs.values()):
        await _tick_pair(
            pr, ctx=ctx, risk=risk, health=health, state=state, tick_idx=tick_idx, now=now
        )

    health.open_order_count = sum(len(pr.tracked_cloids) for pr in pairs.values())

    if tick_idx % state["equity_snapshot_every"] == 0:
        # Account-level snapshot. Pick a ref pair for context; tolerate empty
        # pairs dict (forager warm-up window before selector has enough data).
        ref_pair: str | None = None
        if cfg.strategy.pair in pairs:
            ref_pair = cfg.strategy.pair
        elif pairs:
            ref_pair = next(iter(pairs))
        ref_mid = client.cached_mid(ref_pair) if ref_pair else None
        shadow.snapshot(
            "equity",
            {
                "tick": tick_idx,
                "value": risk.last_equity,
                "pair": ref_pair,
                "mid": float(ref_mid) if ref_mid else None,
            },
        )

    if tick_idx % state["funding_sample_every"] == 0 and pairs:
        for pair_name in pairs:
            rate = await client.funding_rate(pair_name)
            if rate is not None:
                shadow.record_funding_rate(pair_name, rate)
        primary = cfg.strategy.pair if cfg.strategy.pair in pairs else next(iter(pairs))
        primary_rate = await client.funding_rate(primary)
        if primary_rate is not None:
            health.funding_rate_hourly = primary_rate


@dataclass
class _RunnerState:
    ctx: StartupContext
    cfg: BaseConfig
    pairs: dict[str, _PairRuntime]
    risk: RiskManager
    fills_mgr: FillEventsManager
    health: HealthState
    server: HealthServer
    ws: WsSubscriber | None
    selector: ForagerSelector | None
    pair_meta: dict[str, int]
    tick_state: dict[str, Any]


async def _run_loop(rs: _RunnerState, tick_interval_s: float, max_ticks: int | None) -> int:
    tick_idx = 0
    exit_code = 0
    health = rs.health
    retry = _RetryState()
    while not health.graceful_stop:
        tick_idx += 1
        tick_start = time.monotonic()
        backoff_s = 0.0
        try:
            await _tick(
                ctx=rs.ctx,
                cfg=rs.cfg,
                pairs=rs.pairs,
                risk=rs.risk,
                fills_mgr=rs.fills_mgr,
                health=health,
                ws=rs.ws,
                selector=rs.selector,
                pair_meta=rs.pair_meta,
                state=rs.tick_state,
                tick_idx=tick_idx,
            )
            retry.on_success()
            health.tick_count = tick_idx
            health.last_tick_ts = time.time()
            health.account_value = rs.risk.last_equity
        except AuthError as e:
            log.error("runner: AUTH failure, halting: %s", e.message)
            health.graceful_stop = True
            exit_code = 2
            break
        except StructuralError as e:
            log.error("runner: structural breach, halting: %s", e.message)
            health.graceful_stop = True
            exit_code = 3
            break
        except AppError as e:
            backoff_s = retry.on_error(e.category)
            log.warning(
                "runner tick %d: %s (%s, retryable=%s, backoff=%.1fs)",
                tick_idx,
                e.message,
                e.category,
                e.retryable,
                backoff_s,
            )
            health.errors += 1
        except Exception:
            log.exception("runner tick %d: unhandled", tick_idx)
            health.errors += 1
        if max_ticks is not None and tick_idx >= max_ticks:
            log.info("runner: max_ticks=%d reached, stopping", max_ticks)
            break
        elapsed = time.monotonic() - tick_start
        sleep_s = max(tick_interval_s - elapsed, 0.0) + backoff_s
        await asyncio.sleep(sleep_s)
    rs.tick_state["final_ticks"] = tick_idx
    return exit_code


async def run(
    cfg: BaseConfig,
    *,
    tick_interval_s: float = DEFAULT_TICK_INTERVAL_S,
    replan_interval_s: float = DEFAULT_REPLAN_INTERVAL_S,
    reconcile_every: int = DEFAULT_RECONCILE_EVERY,
    equity_snapshot_every: int = DEFAULT_EQUITY_SNAPSHOT_EVERY,
    fill_reconcile_every: int = DEFAULT_FILL_RECONCILE_EVERY,
    funding_sample_every: int = DEFAULT_FUNDING_SAMPLE_EVERY,
    enable_ws: bool = True,
    max_ticks: int | None = None,
) -> int:
    ctx = await run_startup(cfg)
    risk = RiskManager(
        ctx.client,
        baseline_equity=ctx.initial_account_value,
        max_daily_loss_pct=cfg.risk.max_daily_loss_pct,
        leverage=cfg.strategy.leverage,
    )
    fills_mgr = FillEventsManager(client=ctx.client)
    await fills_mgr.reconcile()

    # Build the pairs dict. Forager-disabled (default) → exactly one entry
    # for cfg.strategy.pair. Forager-enabled → start empty; first rotation
    # at tick 1 fills it with top_n picks.
    selector: ForagerSelector | None = None
    pair_meta: dict[str, int] = {}
    pairs: dict[str, _PairRuntime] = {}

    if cfg.forager.enabled:
        pair_meta = await prepare_forager_pairs(
            ctx.client, cfg.forager.candidate_pairs, cfg.strategy.leverage
        )
        selector = ForagerSelector(
            candidates=list(pair_meta.keys()),
            log_range_window_min=cfg.forager.log_range_window_min,
            min_volume_usd_24h=cfg.forager.min_volume_usd_24h,
        )
        log.info("runner: forager enabled — %d candidate pairs prepared", len(pair_meta))
    else:
        pairs[cfg.strategy.pair] = _build_pair_runtime(
            cfg, ctx, cfg.strategy.pair, ctx.sz_decimals, _strategy_id_for(cfg.strategy.pair)
        )

    health = HealthState()
    server = HealthServer(cfg.observability.health_port, health)
    await server.start()
    _install_signal_handlers(health)

    ws: WsSubscriber | None = None
    if enable_ws:
        ws = WsSubscriber(mode=cfg.mode, account_address=cfg.account_address)
        ws.subscribe_all_mids(ctx.client.update_mids)
        ws.subscribe_user_fills(lambda f: (fills_mgr.ingest(f), None)[1])
        ws.start_watchdog()
        log.info("runner: WS subscriber started (allMids + userFills, with reconnect)")

    rs = _RunnerState(
        ctx=ctx,
        cfg=cfg,
        pairs=pairs,
        risk=risk,
        fills_mgr=fills_mgr,
        health=health,
        server=server,
        ws=ws,
        selector=selector,
        pair_meta=pair_meta,
        tick_state={
            "replan_interval_s": replan_interval_s,
            "reconcile_every": reconcile_every,
            "equity_snapshot_every": equity_snapshot_every,
            "fill_reconcile_every": fill_reconcile_every,
            "funding_sample_every": funding_sample_every,
            # Force initial rotation on first tick: last_rotate_ts=0 makes
            # (now - last_rotate_ts) >= rotate_every_s trivially true.
            "last_rotate_ts": 0.0,
        },
    )

    exit_code = 0
    try:
        exit_code = await _run_loop(rs, tick_interval_s, max_ticks)
    finally:
        for pr in rs.pairs.values():
            await _graceful_shutdown(ctx.client, pr.pair, pr.tracked_cloids)
        if ws is not None:
            await ws.stop()
        await server.stop()
        ctx.shadow.snapshot(
            "runner_exit",
            {
                "ticks": rs.tick_state.get("final_ticks", 0),
                "errors": health.errors,
                "final_equity": risk.last_equity,
                "exit_code": exit_code,
            },
        )
    return exit_code
