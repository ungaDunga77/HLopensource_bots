# Evaluation: XEMM Pacifica ↔ Hyperliquid

**Repo**: https://github.com/djienne/XEMM_CROSS_EXCHANGE_MARKET_MAKING_PACIFICA_HYPERLIQUID
**Evaluator**: Claude (OSS bot review)
**Date**: 2026-04-19
**Tier**: 2 (Priority #2 — XEMM is a structurally different pattern from the delta-neutral arb already reviewed)
**Commit reviewed**: `95f2a98` ("Harden correctness, trim hot path, add tests+benches")

---

## Summary of What This Bot Does

Cross-Exchange Market Making: place a post-only limit order on Pacifica (maker side, 1.5 bps maker fee) priced from Hyperliquid's best bid/ask minus a configurable edge (`profit_rate_bps`, default 15 bps), and when Pacifica fills, immediately market-hedge the opposite side on Hyperliquid (taker, 4 bps). The bot is *single-cycle*: it exits after one complete fill+hedge, and a wrapper shell script relaunches it in a loop. Written in Rust (~6.7k LoC), 10 concurrent async tasks, 5-layer fill detection with explicit deduplication and aggregation.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | `.env` loaded via `dotenv` at startup; `HL_PRIVATE_KEY` raw hex, `API_PRIVATE` base58. No agent-wallet pattern for Hyperliquid (uses full wallet key — mainnet only); Pacifica does use an agent-wallet model (`SOL_WALLET` main + `API_PUBLIC`/`API_PRIVATE` for agent key), which is the correct pattern. Secret-scan clean (0 CRIT/HIGH/MED; 857 INFO findings are tx-hash noise in docs/). No key echoing found. No hardcoded keys. Downside: README uses `HL_PRIVATE_KEY=0x...` with full spending authority. |
| A2 | Dependency hygiene | 4 | Modern, well-known crates only: `tokio`, `ethers`, `ed25519-dalek`, `reqwest`, `rmp-serde`, `parking_lot`. `Cargo.lock` committed. 25 runtime deps. `cargo audit` deferred to Docker sandbox (host lacks cargo). No exotic or vendored crypto. |
| A3 | Network surface | 4 | Outbound only: `api.hyperliquid.xyz`, `api.pacifica.fi`, and their WS counterparts, plus testnet URLs. No inbound servers in the core bot. The optional `dashboard_js/` does open an HTTP server and uses SSH to a remote — scoped to that opt-in subfolder. |
| A4 | Code transparency | 4 | Clean module boundaries, no obfuscation, no off-by-default telemetry, no unexplained binaries. One small concern: an `output.log` and `_trades.csv` are written locally; no remote exfiltration. Referral codes appear in README (informational). |
| A5 | Input validation | 3 | `Config::validate()` checks symbol/agg_level/ping range but nothing deeper; `hyperliquid_slippage` defaulting to 5% is loose. `prices_valid()` check before each opportunity eval; `hl_bid > 0 && hl_ask > 0` re-verified in hedge path. Numeric parsing uses `fast_float::parse` with `.unwrap_or(0.0)` fallbacks — silent degradation rather than hard fail in a couple of places. |
| | **A average** | **3.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | XEMM formula is explicit, documented in README, and isolated in `strategy/opportunity.rs`. Buy: `(HL_bid·(1−taker)) / (1+maker+profit)`; Sell: `(HL_ask·(1+taker)) / (1−maker−profit)`. Round buy-down / sell-up to tick, recompute actual post-rounding profit and reject if not strictly positive. `pick_best_opportunity` prefers the side closer to Pacifica mid, breaking ties by profit. |
| B2 | Backtesting | 1 | None. Only `xemm_calculator.rs` example for live what-if. Real P&L measured post-trade by `trade_fetcher` reconciling against both exchanges' actual fills. |
| B3 | Risk management | 4 | Very thoughtful for a single-cycle MM: (a) `profit_cancel_threshold_bps=3` auto-cancels if edge decays; (b) `order_refresh_interval_secs=60` kills stale quotes; (c) hedge has exponential retry (250ms, 750ms) alternating WS/REST; (d) `OrderStatus::Resting` on an IOC hedge treated as terminal error and shuts bot down (good); (e) post-hedge position verification with 3-retry loop checks both exchanges are net-flat and prints a loud WARN if delta > 0.01; (f) `FillAggregator` has an "emergency notional" breach (2× order size) to force emit if exchange loses the terminal event; (g) final safety `cancel_all_orders` on every shutdown path. Missing: no daily loss limit, no inventory drift ceiling across cycles (relies on single-cycle + external restart). |
| B4 | Configurability | 4 | Single `config.json`, sensible defaults. 15 parameters covering fees, edge, size, cancel thresholds, refresh interval, slippage ceiling, WS-vs-REST hedge toggle, poll intervals. Missing: per-symbol overrides, dynamic sizing by liquidity, no multi-symbol support (one bot = one symbol). |
| B5 | Monitoring | 4 | Colorized `tracing` logs with task-tagged sections; per-cycle "BOT CYCLE COMPLETE" summary with expected-vs-actual bps; `csv_logger` writes every trade async (non-blocking writer thread, good pattern); separate Node.js web dashboard and Python terminal dashboard in `dashboard_js/` and `standalone-utils/`; `check_logs.py` to scrape `output.log`. No metrics endpoint (Prometheus/OTEL). |
| | **B average** | **3.6** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 3 | 2 integration tests (`tests/fill_pipeline.rs`, `tests/state_and_strategy.rs`) plus unit tests inside most modules (config, opportunity, state, fill_dedup). Criterion benches for opportunity eval and price-quote. Tests specifically cover multi-detector dedup, partial-then-full fill aggregation, emergency-notional breach, and idle flush — exactly the correctness-critical concurrency edges. No network-mocked integration of full bot loop. |
| C2 | Error handling | 4 | `anyhow::Result` throughout, `.context(...)` on most fallible calls. Hedge path explicitly distinguishes transport errors (retryable) from HL `OrderStatus::Error`/`Resting` (terminal), and bails to shutdown rather than leaving exposure. `unwrap()/expect()` count (35 across 11 files) is low for a 6.7k-LoC Rust codebase, mostly in test / bin / numeric-parse-with-default contexts. |
| C3 | Documentation | 4 | README is 600 lines, includes schema image, explicit XEMM formulas, 5-layer detection explanation, full config table, ops runbook (nohup / loop / kill). Inline doc comments on most public items. A `docs/` folder includes full HL API and WS reference dumps for offline lookup. Missing: ADR-style "why these design choices" doc. |
| C4 | Code quality | 4 | Clean module tree: `connector/{pacifica,hyperliquid}/`, `services/`, `strategy/`, `bot/`, `util/`. Producer/consumer separation: fill detectors push `HedgeEvent` into bounded mpsc; dedicated `HedgeService` single-consumer. `FillDedup` and `FillAggregator` are concurrency-safe and bounded (4096 cap, FIFO eviction — no unbounded growth). Atomic status (`AtomicU8`) used for lock-free hot-path checks alongside `RwLock` for mutation. Pre-computed fee factors in opportunity eval to minimize FP ops. `hedge.rs` is 1078 lines — too long, should split summary/verification out. |
| C5 | Maintenance | 2 | Only one commit in the git history we cloned (squashed at 2026-04-19). This is a single-author project, actively evolving as of the commit date, but limited external contribution signal. Docker image present, `Dockerfile` + `docker-compose.yml` at repo root. |
| | **C average** | **3.4** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | No CCXT, no Python SDK — direct EIP-712 signing via `ethers::signers::LocalWallet`, msgpack payload via `rmp-serde`, matching HL's native wire format. Implements meta cache, L2 snapshot fetch, user state fetch, user fills, `build_market_order_request` shared between REST and WS paths. Dedicated hot WebSocket trading connection for hedge (post `action` over WS) with REST fallback. Well-structured connector. |
| D2 | Testnet support | 2 | `HyperliquidTrading::new` accepts `is_testnet: bool` and switches to testnet URLs (`api.hyperliquid-testnet.xyz`, `wss://api.hyperliquid-testnet.xyz/ws`). Pacifica likewise (`wss://test-ws.pacifica.fi/ws`). However, every construction site in the code (`app.rs:190`, `app.rs:187`, `bin/check_balance.rs:46`, `bin/rebalance.rs:47`) passes `false` hardcoded. README says "Mainnet only". No config flag, no CLI flag — to run on testnet you must patch source. |
| D3 | HL features | 4 | Uses market IOC orders with explicit slippage ceiling; consumes L2 orderbook via WS; user-state and user-fills APIs for post-trade reconciliation; builder-code field (`source="a"` mainnet, `"b"` testnet); WS `post` trading. Does not use: vaults, spot, TWAP, scheduled cancels, subaccounts. Reasonable scope for XEMM. |
| | **D average** | **3.3** | |

---

## Final Score

```
Final = (3.6 * 0.4) + (3.6 * 0.3) + (3.4 * 0.2) + (3.3 * 0.1)
      = 1.44 + 1.08 + 0.68 + 0.33
      = 3.53
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Score **3.53/5** — the highest-quality Rust codebase I've reviewed on this study so far. Architecture is genuinely production-minded: bounded channels, lock-free atomic status on the hot path, pre-signed reusable WS connection for hedge execution, five independent fill detectors unified through a `FillDedup` + `FillAggregator` pair that handles partials, duplicates, and lost terminal events. Critical correctness invariants (hedge exactly once per fill, emit on emergency notional breach, reject IOC-that-rested) are pinned down by integration tests. Main deductions: (1) no native testnet switch — `false` is hardcoded at every construction site, which directly conflicts with our testnet-only policy; (2) single-cycle design means risk management on cross-cycle inventory is delegated to the wrapper shell script; (3) no backtest harness — only post-hoc profit reconciliation.

## Key Findings

### Strengths (transferable patterns)
- **Fill detection as a pipeline of producers + 1 consumer.** 5 detector tasks (WS orders / WS positions / REST orders / REST positions / monitor safety-check) all funnel into an unbounded-semantically-but-bounded-in-practice mpsc; `HedgeService` is the single consumer. Producers never block — if the hedge is slow, fill detection still runs at full speed. This is the right shape for any HL MM.
- **Dedup + Aggregator split.** `FillDedup` (bounded FIFO keyed on `OrderId | Cloid`, cap=4096) is separate from `FillAggregator` (per-order partial accumulator with terminal / notional-breach / idle-timeout emission rules). The aggregator lets you correctly handle "WS saw 0.3, REST saw 0.7 terminal" without double-hedging or missing size.
- **Hedge retry with transport switching.** 3 attempts (initial + 2 retries at 250ms, 750ms), alternating WS/REST, with explicit distinction between retryable transport errors and terminal HL `OrderStatus::Error`/`Resting`. Refreshes HL price between retries so the slippage ceiling is recomputed.
- **Hot WS trading connection kept warm.** At startup, `HedgeService` opens a Hyperliquid trading WS and pings every 5s; hedge order is an already-signed action wrapped in a WS `post`. Saves a TLS handshake + TCP RTT on every hedge. Same signing code path as REST, so no code duplication.
- **Post-trade reconciliation via exchange trade history.** After hedge + 20s wait, fetch actual fills and fees from both venues rather than trusting fill-event data. Separate fallback path if history API is unavailable. CSV log uses dedicated async writer thread so disk latency doesn't stall hedge service.
- **Post-hedge position verification.** Explicitly queries both venues and sums signed positions; fires a loud WARN banner if `|net| >= 0.01`. Great operational safety net we should copy.
- **Maker-quote-from-taker-venue formula.** Clear, simple, testable: `pac_buy = (hl_bid·(1−tk))/(1+mk+edge)`, round down to tick, recompute actual post-rounding profit, reject if ≤0. Any ambiguity is resolved by the post-rounding recompute.
- **Profit-deviation auto-cancel (3 bps) + age-based refresh (60s).** Keeps quotes from going stale while you wait for a fill. Simple, cheap, effective.

### Concerns / Defects
- **No testnet plumbing.** `is_testnet` parameter exists at every connector but is hardcoded `false` at every call site. README says "Mainnet only". To evaluate in our sandbox we'd need a minimal patch.
- **Hedge uses full wallet key on Hyperliquid.** No agent-wallet pattern on the HL side (Pacifica side does use agent). For an MM that hedges automatically, HL agent wallet should be used.
- **`hedge.rs` is 1078 LoC.** Mixes hedge execution, profit calculation, CSV logging, and post-hedge verification. Will get harder to maintain.
- **Single-cycle design.** Relies on `run_bot_loop_cargo.sh` (shell-based outer loop with 20s sleep) for continuous operation — no in-process state carry-over between cycles, no cumulative P&L or inventory drift tracking.
- **Slippage default 5%.** Configurable but 5% for a market-IOC hedge is very loose. Saves you from failed hedges on thin books, but during a flash move you can eat into the entire edge.
- **No multi-symbol.** One bot = one symbol. Scale-out = N processes.
- **`fast_float::parse(...).unwrap_or(0.0)` pattern in a few places.** Silent degradation: a malformed "amount" string becomes position=0.0. In verification, this could mask a real position.

### Recommendations for Our Custom Bot
- **Steal the fill-detection topology wholesale.** 5 layers is probably more than we need for a Drift-style delta-neutral bot, but the producers-to-bounded-mpsc-to-single-consumer shape with `FillDedup` (bounded FIFO, OrderId|Cloid enum key) + `FillAggregator` (with emergency-notional-breach and idle-flush fallbacks) is the right primitive.
- **Steal the hot WS trading connection + REST fallback.** Build the signed payload once, send over WS for latency, fall back to REST on transport error, retry with transport switch and fresh price.
- **Steal the post-hedge position verification.** Always query both legs and compare signed positions after a cross-venue trade; alert if net ≠ 0 by tolerance.
- **Steal the maker-from-taker price formula.** For any XEMM-style extension we add, this is the canonical form. Precompute fee factors; round conservatively; recompute post-rounding profit; reject if not strictly positive.
- **Skip the single-cycle model.** Build a persistent in-process loop so we can track cumulative P&L, inventory drift, per-symbol rate limits, and per-day loss caps properly.
- **Don't copy:** the hardcoded `false` testnet path, the 5% default slippage, the monolithic `hedge.rs` structure.
- **Is the XEMM pattern worth incorporating?** Yes — it's a structurally different edge (your own maker quote on a less-liquid venue vs. taker on a deeper one) that composes cleanly with HL as the hedge leg. For our custom bot, XEMM-on-HL-as-maker is probably not viable (HL is already the deep venue), but XEMM-with-HL-as-hedge is viable against any less-liquid HL competitor (Pacifica, Paradex, Drift spot) and the mechanics here translate almost 1:1.

## Companion Bot Note (djienne's DELTA_NEUTRAL_HYPERLIQUID_PERP_SPOT)
Not cloned in this pass. Based on the naming it's an HL-only perp-vs-spot funding-capture bot. Worth a follow-up scan if we decide to build a funding-capture module, since the same author's code quality here suggests the companion is also high-quality and would reuse most of the connector code.
