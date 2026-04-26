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
from dataclasses import dataclass
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

log = get_logger("osbot.runner")


DEFAULT_TICK_INTERVAL_S = 2.0
DEFAULT_REPLAN_INTERVAL_S = 300.0
DEFAULT_RECONCILE_EVERY = 30
DEFAULT_EQUITY_SNAPSHOT_EVERY = 60
DEFAULT_FILL_RECONCILE_EVERY = 30  # REST safety-net cadence (WS is primary)

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


async def _tick(
    *,
    ctx: StartupContext,
    cfg: BaseConfig,
    market: MarketState,
    grid: GridStrategy,
    risk: RiskManager,
    fills_mgr: FillEventsManager,
    exit_mgr: ExitManager,
    health: HealthState,
    ws: WsSubscriber | None,
    state: dict[str, Any],
    tick_idx: int,
) -> None:
    pair = cfg.strategy.pair
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

    # Prefer WS-fed cached mid; fall back to REST when stale or missing.
    mid_str = client.cached_mid(pair)
    if mid_str is None:
        mids = await client.all_mids()
        mid_str = mids.get(pair)
    if not mid_str:
        log.warning("tick %d: no mid for %s", tick_idx, pair)
        return
    mid = float(mid_str)
    market.sample(now, mid)

    await risk.precheck()

    user_state = await client.user_state()
    closed = await exit_mgr.evaluate_and_act(user_state, mid, health, now=now)
    if closed:
        shadow.snapshot("exit_close", {"tick": tick_idx, "mid": mid})
        health.position_count = 0

    tracked: list[str] = state["tracked_cloids"]
    if grid.should_replan(
        now, state["replan_interval_s"], have_grid=bool(tracked)
    ):
        plan = grid.plan(
            now=now,
            mid=mid,
            market=market,
            balance_usd=risk.last_equity,
            open_grid_cloids=tracked,
        )
        shadow.snapshot(
            "grid_plan",
            {
                "tick": tick_idx,
                "mid": mid,
                "cancels": len(plan.cancels),
                "submits": len(plan.submits),
                "equity": risk.last_equity,
            },
        )
        state["tracked_cloids"] = await _apply_plan(client, pair, plan, risk, health)

    if tick_idx % state["reconcile_every"] == 0:
        state["tracked_cloids"] = await _reconcile_orders(
            client, pair, state["tracked_cloids"]
        )
        health.open_order_count = len(state["tracked_cloids"])

    if tick_idx % state["equity_snapshot_every"] == 0:
        shadow.snapshot(
            "equity",
            {"tick": tick_idx, "value": risk.last_equity, "mid": mid},
        )


@dataclass
class _RunnerState:
    ctx: StartupContext
    cfg: BaseConfig
    market: MarketState
    grid: GridStrategy
    risk: RiskManager
    fills_mgr: FillEventsManager
    exit_mgr: ExitManager
    health: HealthState
    server: HealthServer
    ws: WsSubscriber | None
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
                market=rs.market,
                grid=rs.grid,
                risk=rs.risk,
                fills_mgr=rs.fills_mgr,
                exit_mgr=rs.exit_mgr,
                health=health,
                ws=rs.ws,
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
    enable_ws: bool = True,
    max_ticks: int | None = None,
) -> int:
    ctx = await run_startup(cfg)
    market = MarketState()
    grid = GridStrategy(cfg, ctx.sz_decimals)
    risk = RiskManager(
        ctx.client,
        baseline_equity=ctx.initial_account_value,
        max_daily_loss_pct=cfg.risk.max_daily_loss_pct,
        leverage=cfg.strategy.leverage,
    )
    fills_mgr = FillEventsManager(client=ctx.client)
    await fills_mgr.reconcile()

    triple_barrier = TripleBarrier(
        sl_pct=cfg.strategy.sl_pct,
        tp_pct=cfg.strategy.tp_pct,
        ttl_s=float(cfg.strategy.exit_ttl_s),
        consecutive_breaches_required=cfg.strategy.sl_consecutive_breaches,
    )
    exit_mgr = ExitManager(client=ctx.client, pair=cfg.strategy.pair, triple_barrier=triple_barrier)

    health = HealthState()
    server = HealthServer(cfg.observability.health_port, health)
    await server.start()
    _install_signal_handlers(health)

    ws: WsSubscriber | None = None
    if enable_ws:
        ws = WsSubscriber(mode=cfg.mode, account_address=cfg.account_address)
        ws.subscribe_all_mids(ctx.client.update_mids)
        ws.subscribe_user_fills(lambda f: (fills_mgr.ingest(f), None)[1])
        log.info("runner: WS subscriber started (allMids + userFills)")

    rs = _RunnerState(
        ctx=ctx,
        cfg=cfg,
        market=market,
        grid=grid,
        risk=risk,
        fills_mgr=fills_mgr,
        exit_mgr=exit_mgr,
        health=health,
        server=server,
        ws=ws,
        tick_state={
            "tracked_cloids": [],
            "replan_interval_s": replan_interval_s,
            "reconcile_every": reconcile_every,
            "equity_snapshot_every": equity_snapshot_every,
            "fill_reconcile_every": fill_reconcile_every,
        },
    )

    exit_code = 0
    try:
        exit_code = await _run_loop(rs, tick_interval_s, max_ticks)
    finally:
        await _graceful_shutdown(ctx.client, cfg.strategy.pair, rs.tick_state["tracked_cloids"])
        if ws is not None:
            ws.stop()
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
