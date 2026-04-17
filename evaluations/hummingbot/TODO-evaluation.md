# Hummingbot evaluation — items to address at trial wrap-up

## Risk/reward asymmetry in `pmm_simple_btc.yml` (2026-04-17 trial)
- `take_profit: 0.005` (50 bps, LIMIT → maker)
- `stop_loss: 0.02` (200 bps, MARKET → taker, ~2.5 bps fee)
- 1:4 risk/reward → need ~80% TP-hit rate just to break even on that leg alone.
- Spreads (10/30 bps) easily clear maker fees, but Triple Barrier dominates P&L.
- **Action:** when analyzing the trial DB tomorrow, compute:
  - % executors that hit TP vs SL vs time-limit
  - Realized P&L broken down by exit reason
  - Fee paid vs maker-rebate earned (HL sends rebates as `closedPnl` deltas on fills)
  - Whether a symmetric or inverted SL/TP would have been net-positive

## Fee modeling
- Hummingbot hardcodes maker = 0 in `hyperliquid_perpetual_utils.py:DEFAULT_FEES`.
  Real HL: maker is often a small rebate (−0.2 to +0.4 bps depending on volume tier).
- Bot's own P&L reporting will under-count earnings slightly vs HL truth.
- **Action:** compare shadow `fills.closedPnl` sum vs bot's reported total.

## Nonce collision in connector
- Connector stamps nonce = `int(time.time() * 1000)`; sibling orders in same ms collide.
- V2 `PositionExecutor` masks this with retry-up-to-10. V1 scripts lose the order.
- Count retries in trial logs → if non-negligible, file upstream PR proposing
  `nonce = max(now_ms, last_nonce + 1)` in the submit path.

## Leverage defaults
- Hummingbot doesn't call `set_leverage` on startup; HL account default applies.
- We manually set 1x before this trial. Production deployments on fresh accounts
  would silently inherit whatever the exchange has configured.
- **Action:** note in evaluation.md as a safety concern. The V2 `leverage` field
  in config only affects budget sizing, not exchange-side leverage.
