# Phase 6 M3 — Strategy Loop, Live Run Results, and Iteration Log

**Status as of 2026-04-26:** M3 acceptance passed (24h zero-crash); cumulative live testnet runtime ~85h+ across two unbounded runs; +1.27% equity gain; all six post-M3 quality fixes shipped.

## 1. M3 acceptance (first unbounded run, 2026-04-23 to 2026-04-26)

- **Duration:** 70h continuous (Apr 23 05:46 → Apr 26 03:48 UTC+2)
- **Ticks:** 113,221 at 2s cadence
- **Equity:** $908.01 → $919.10 = **+$11.09 (+1.22%)** on $908 baseline
- **Fills:** 484 ($4,516 buys + $4,604 sells = $9,120 round-trip turnover)
- **Per-trade capture:** ~14bps net per round-trip after fees
- **TripleBarrier exits:** 17 (3.5% of fills triggered TB; 96% mean-reverted naturally)
- **Trend pauses:** triggered through every directional move >50bps; zero accumulated one-sided inventory at any 2h check
- **Errors:** 179 total = 0.158% rate, all retryable, all auto-recovered
  - Clustered in 8 distinct ~2-min HL testnet outage windows (transient 502s, network timeouts, 429s)
  - Zero unhandled exceptions, zero halts
- **Acceptance criteria** (synthesis §5.6 M3 row): zero unhandled exceptions ✓, /health reports healthy throughout ✓, shadow log has equity+fills ✓ — **passed cleanly within first 24h, then ran 46h longer**

## 2. Post-M3 quality fixes (six commits, 2026-04-26)

Run was stopped, fixes applied in order, smoke-tested, relaunched.

| # | Commit | What | Why |
|---|---|---|---|
| 1 | `8746ea0` | Trend-pause replan thrash fix | `should_replan(have_grid=False)` conflated "lost grid to fills" with "paused on purpose" → 30,119 redundant log lines in 70h |
| 2 | `c2d0a7e` | Exponential backoff on retryable errors | 8 outage windows × ~30 retries each at full tick cadence both polluted error counter and contributed to HL's 429 storm. 2s → 4s → 8s → … → 60s cap; resets on success |
| 3 | `a86eeef` | WS subscriptions (`allMids` + `userFills`) with REST fallback | Cuts ~70% of REST baseline traffic; FillEventsManager now ingests via WS callback with shared dedup |
| 4 | `385ec0c` | WS auto-reconnect watchdog | HL closes WS every ~10min with `Expired` close code; SDK doesn't auto-reconnect. Async watchdog detects dead/stale connection, tears down, replays subscriptions. Verified 67+ live reconnects, 0 failures |
| 5 | `385ec0c` | Strategy parameter tweaks | range_bps_min 50→30, grid_levels 5→7, WEL 0.10→0.20, tp_pct 30→15bps, tick 2s→1s — leans further into fast/quick mean-reversion |
| 6 | `7af206c` | 1-min sigma + dual-EMA slope | Per-tick sigma was dominated by 1-2s tick noise; first-vs-last slope was crude. Now bucketed 1-min closes for sigma, time-weighted 30min/4h dual-EMA for slope |

After these fixes, the second unbounded run (Apr 26 05:03 → present) has held healthy throughout, processing HL's periodic WS drops transparently.

## 3. Strategy verdict

We are firmly in **fast/quick mean-reversion** territory:
- ~$0.05 per fill, ~$0.10 per round-trip pair, ~$0.35/h sustained on $920 testnet wallet
- Per-trade is genuinely tiny by construction — a grid at 4.3bps spacing physically cannot capture more than ~8bps net per round-trip after fees
- This IS the strategy, not a defect. Compare to other passive strategies (HODL, funding-arb, options selling)
- Going wider on TP doesn't necessarily increase PnL — product (per-trade × frequency) is roughly conserved across reasonable parameter ranges in a ranging market
- Real PnL multipliers are: more capital deployed, more pairs (forager), or different strategy class entirely

## 4. Operational observations

- **HL testnet WS lifecycle:** connection closed by server every ~10min with `Expired` close code (1000). Auto-reconnect via watchdog is mandatory for steady-state operation.
- **HL testnet REST outages:** ~2-min windows roughly every 4-8h, mix of network timeouts, 502 Bad Gateway, and 429s. Exponential backoff on retryable categories is mandatory.
- **HL testnet $10 min-notional:** enforced strictly. Our `min_notional_usd` config bumps when computed level size falls below; `size_bumped` warning fires.
- **Position carry-over across restarts:** graceful_shutdown cancels orders only, not positions. ExitManager re-tracks any non-zero `szi` on first tick after restart and applies TripleBarrier.
- **Cron monitoring is session-only:** the every-2h `/loop` cron we used to monitor the long run dies with the Claude session. New session needs fresh cron arming.
