"""Single-trip round trip: open + close one $15-notional BTC position on testnet.

Used for M2 acceptance. Runs the full startup sequence, opens a marketable IOC
buy, verifies fill, closes via reduce-only IOC sell, verifies flat. Kill-switch
in `finally` attempts a best-effort market_close + cancel-all on any error.

This is *not* the strategy loop — it's a one-shot smoke that proves the entire
write-path (signing, throttler, error classification, fill reconcile) works
end-to-end against real testnet infrastructure.
"""

from __future__ import annotations

import asyncio

from osbot.config import BaseConfig
from osbot.connector.errors import AppError
from osbot.connector.hl_client import HLClient
from osbot.observability import get_logger
from osbot.startup import StartupContext, run_startup
from osbot.state.fills import FillEventsManager
from osbot.strategy.tags import OrderIntent, OrderTag

log = get_logger("osbot.roundtrip")

NOTIONAL_USD = 15.0
PAIR = "BTC"
SLIPPAGE_PCT = 0.005  # 0.5% — IOC limit will cross
SETTLE_DELAY_S = 2.0  # let HL clearinghouse propagate the fill


def _round_size(notional_usd: float, mid: float, sz_decimals: int) -> float:
    raw = notional_usd / mid
    factor: int = 10**sz_decimals
    rounded: int = round(raw * factor)
    return rounded / factor


def _format_price(price: float) -> float:
    # HL accepts up to 5 significant figures for perp prices. Round to integer
    # for BTC (price ~$60k) — way under the sig-fig cap.
    return float(round(price))


async def _verify_flat(client: HLClient, pair: str) -> tuple[int, int]:
    state = await client.user_state()
    positions = [
        p
        for p in (state.get("assetPositions") or [])
        if (p.get("position") or {}).get("coin") == pair
        and float((p.get("position") or {}).get("szi", "0")) != 0.0
    ]
    open_orders = [o for o in await client.open_orders() if o.get("coin") == pair]
    return len(positions), len(open_orders)


async def _kill_switch(client: HLClient, pair: str) -> None:
    log.error("kill-switch: best-effort cancel-all + market_close for %s", pair)
    try:
        for o in await client.open_orders():
            if o.get("coin") != pair:
                continue
            oid = o.get("oid")
            if oid is not None:
                try:
                    await client.cancel(pair, int(oid))
                except AppError as e:
                    log.error("kill-switch cancel failed: %s", e.message)
        try:
            await client.market_close(pair)
        except AppError as e:
            log.error("kill-switch market_close failed: %s", e.message)
    except Exception as e:
        log.error("kill-switch outer failure: %s", e)


async def _open_leg(ctx: StartupContext, mid: float) -> str:
    size = _round_size(NOTIONAL_USD, mid, ctx.sz_decimals)
    if size <= 0:
        raise AppError(f"computed size <= 0 (mid={mid}, notional={NOTIONAL_USD})")
    px = _format_price(mid * (1 + SLIPPAGE_PCT))
    cloid = OrderTag(strategy_id=0xCAFE, intent=OrderIntent.OPEN_GRID, level=0).to_cloid()
    log.info("round-trip: opening BUY %s @ %s (cloid=%s)", size, px, cloid)
    result = await ctx.client.place_order(
        PAIR, is_buy=True, size=size, price=px, tif="Ioc", reduce_only=False, cloid=cloid
    )
    log.info("round-trip: open response status=%s", result.get("status"))
    return cloid


async def _close_leg(ctx: StartupContext, mid: float, position_size: float) -> str:
    # Reduce-only IOC sell at a price below mid to ensure cross.
    px = _format_price(mid * (1 - SLIPPAGE_PCT))
    cloid = OrderTag(strategy_id=0xCAFE, intent=OrderIntent.CLOSE_GRID, level=0).to_cloid()
    log.info("round-trip: closing SELL %s @ %s (cloid=%s)", position_size, px, cloid)
    result = await ctx.client.place_order(
        PAIR,
        is_buy=False,
        size=position_size,
        price=px,
        tif="Ioc",
        reduce_only=True,
        cloid=cloid,
    )
    log.info("round-trip: close response status=%s", result.get("status"))
    return cloid


async def _current_position_size(client: HLClient, pair: str) -> float:
    state = await client.user_state()
    for p in state.get("assetPositions") or []:
        pos = p.get("position") or {}
        if pos.get("coin") == pair:
            return abs(float(pos.get("szi", "0")))
    return 0.0


async def run_round_trip(cfg: BaseConfig) -> int:
    ctx = await run_startup(cfg)
    client = ctx.client
    fills = FillEventsManager(client=client)
    # Drain any pre-existing fills so dedup state is current.
    await fills.reconcile()

    try:
        mids = await client.all_mids()
        mid_str = mids.get(PAIR)
        if not mid_str:
            log.error("no mid price for %s", PAIR)
            return 1
        mid = float(mid_str)
        log.info("round-trip: %s mid=%.2f", PAIR, mid)

        await _open_leg(ctx, mid)
        await asyncio.sleep(SETTLE_DELAY_S)

        new_open_fills = await fills.reconcile()
        log.info("round-trip: %d new fills after open", len(new_open_fills))
        for f in new_open_fills:
            ctx.shadow.record_fill(str(f.get("tid", "")), f)

        position_size = await _current_position_size(client, PAIR)
        if position_size <= 0:
            log.error("round-trip: open leg produced no position; aborting")
            return 1
        log.info("round-trip: position open size=%s", position_size)

        await _close_leg(ctx, mid, position_size)
        await asyncio.sleep(SETTLE_DELAY_S)

        new_close_fills = await fills.reconcile()
        log.info("round-trip: %d new fills after close", len(new_close_fills))
        for f in new_close_fills:
            ctx.shadow.record_fill(str(f.get("tid", "")), f)

        n_positions, n_orders = await _verify_flat(client, PAIR)
        if n_positions != 0 or n_orders != 0:
            log.error(
                "round-trip: not flat (positions=%d orders=%d) — invoking kill-switch",
                n_positions,
                n_orders,
            )
            await _kill_switch(client, PAIR)
            return 1

        final_state = await client.user_state()
        final_value = float((final_state.get("marginSummary") or {}).get("accountValue", "0"))
        delta = final_value - ctx.initial_account_value
        log.info(
            "round-trip OK: start=%.6f end=%.6f delta=%+.6f",
            ctx.initial_account_value,
            final_value,
            delta,
        )
        ctx.shadow.snapshot(
            "round_trip_complete",
            {
                "start_value": ctx.initial_account_value,
                "end_value": final_value,
                "delta": delta,
                "open_fills": len(new_open_fills),
                "close_fills": len(new_close_fills),
            },
        )
        return 0
    except AppError as e:
        log.error("round-trip aborted: %s (%s)", e.message, e.category)
        await _kill_switch(client, PAIR)
        return 1
    except Exception as e:
        log.error("round-trip aborted: unexpected %s: %s", type(e).__name__, e)
        await _kill_switch(client, PAIR)
        raise
