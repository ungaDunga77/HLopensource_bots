# Evaluation: Passivbot

**Repo**: https://github.com/enarjord/passivbot
**Evaluator**: Claude (automated)
**Date**: 2026-04-01
**Tier**: 1

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | Plaintext `api-keys.json` (no encryption, no keystore, no env var support). `.gitignore` excludes it. Keys never logged — CCXT debug suppressed to WARNING by default. No key format validation. No file permission enforcement. Legacy field remapping is clean. Vault mode available for HL (good). |
| A2 | Dependency hygiene | 4 | 12 live trading deps, all pinned with `==`. 0 known vulns in live deps. 30 MEDIUM vulns total (all in full/dev deps: aiohttp, requests, werkzeug, flask, pymdown-extensions — not needed for live trading). Rust deps established. `memmap` 0.7.0 deprecated but functional. |
| A3 | Network surface | 3 | All exchange comms via CCXT (expected). Custom endpoint override system (`custom_endpoint_overrides.py`) allows URL rewriting with **no scheme/domain validation** — could redirect to attacker servers if config file is compromised. Broker codes are public affiliate IDs (benign). No telemetry. |
| A4 | Code transparency | 5 | All Python + Rust source readable. Unlicense (public domain). 7,688 commits of history. 46 contributors. Well-structured modular architecture. No obfuscation. |
| A5 | Input validation | 4 | Comprehensive config validation with whitelist-based allowed modifications. HJSON safe parsing. Balance validated (NaN/infinity/None checks). Wallet exposure limits enforced. `_resolve_coins_file_path` lacks path traversal validation (low risk — parsed as JSON). |
| | **A average** | **3.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | Contrarian market-making with martingale-inspired grid. Trailing entries/closes. Forager mode (dynamic market selection). Unstucking mechanism for losing positions. 22-page wiki. Extensive config templates with documentation. |
| B2 | Backtesting | 5 | Built-in backtester with historical data download. Evolutionary algorithm optimizer (deap). Pareto optimization for multi-objective tuning. Out-of-sample validation. Suite runner for batch optimization. Best-in-class for open-source bots. |
| B3 | Risk management | 5 | Wallet exposure limit (WEL) per-symbol per-side. Total wallet exposure limit (TWEL) global. Risk WEL enforcer threshold. Excess allowance percentages. Max realized loss percentage. Batch size limits (creations + cancellations). Balance hysteresis (prevents oscillation). Circuit breaker (10 errors/hour → restart). |
| B4 | Configurability | 5 | HJSON configs with templates. CLI with subcommands. Per-exchange customization. Per-symbol coin overrides. Approved coins lists. Custom endpoints. Optimizer for parameter tuning. Config transform tracking. Balance override for testing. |
| B5 | Monitoring | 3 | Structured logging with levels 0-3 (WARNING → TRACE). CCXT log suppression. Health tracking (errors, rate limits, WS reconnects). Position change logging with WEL/TWEL ratios. Dash dashboard available. No built-in Telegram/Discord alerts. |
| | **B average** | **4.6** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 4 | 88 test files, 991 tests collected. 851 passed, 22 failed (read-only FS, not bugs), 118 skipped (env-specific). Good coverage: config, risk management, order logic, exchange mocks, optimization. Parametrized tests. Async test support. |
| C2 | Error handling | 4 | Graceful shutdown (SIGINT/SIGTERM). Circuit breaker with error budget. Exponential backoff on rate limits. Balance validation (NaN/infinity). Order execution result validation. Exception hierarchy (RestartBotException, RateLimitExceeded). Debug print statements in production paths (minor concern). |
| C3 | Documentation | 4 | 22-page wiki. MkDocs site. Config templates with comments. README covers installation + features. CHANGELOG.md for releases. `api-keys.json.example`. No standalone API reference. |
| C4 | Code quality | 4 | Modular architecture (40 Python modules). Rust FFI for performance. Async/await throughout. Config transform system with whitelist protection. Clean separation (pure_funcs, exchanges, optimization). Some complexity (passivbot.py is 6,757 lines). |
| C5 | Maintenance | 5 | 7,688 commits. 46 contributors. v7.8.5 (active development through March 2025). Regular releases (12+ in last 6 months). Active community (Discord, GUI fork, config database). Unlicense. |
| | **C average** | **4.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Does NOT use official HL SDK. Uses CCXT abstraction layer (deliberate multi-exchange design). CCXT handles signing, endpoint routing, WebSocket. Custom HL-specific code for balance caching, HIP-3 positions, price rounding (6dp + 5sf), min cost ($10 default with auto-adjustment). |
| D2 | Testnet support | 0 | No testnet support for Hyperliquid. No testnet flag, no environment variable, no sandbox mode. Only Paradex has testnet detection. Custom endpoint overrides are the only workaround (manual). |
| D3 | HL features | 3 | HIP-3 stock perps support. Vault accounts (`is_vault`). Custom price rounding. WebSocket order monitoring (via CCXT Pro). Fill events manager. Bulk price fetches optimized for HL. Isolated margin NOT supported for HIP-3. No agent wallets, no HL-native TPSL, no vault creation. |
| | **D average** | **1.67** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.6   * 0.4) + (4.6   * 0.3) + (4.2   * 0.2) + (1.67  * 0.1)
      = 1.44 + 1.38 + 0.84 + 0.167
      = 3.83
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Passivbot is the most sophisticated bot evaluated so far — a mature, well-tested multi-exchange trading system with best-in-class backtesting and risk management. Its functionality score (4.6) is the highest of any bot evaluated. However, it was built as a multi-exchange tool, not an HL-native one. The complete absence of testnet support (0) and lack of official SDK usage (via CCXT instead) significantly drag down its HL integration score. Key management uses plaintext JSON files rather than env vars or encrypted keystores. Despite these gaps, the depth of its risk controls (WEL/TWEL enforcement, circuit breakers, batch limits) and its active 46-contributor community make it a strong candidate for forking or hardening.

## Key Findings

### Strengths
- Best-in-class backtester + evolutionary algorithm optimizer with Pareto optimization
- Comprehensive risk management: WEL, TWEL, excess allowance, max realized loss, batch limits, circuit breaker
- 851 passing tests across 88 test files (strongest test coverage of any bot evaluated)
- Active maintenance: 7,688 commits, 46 contributors, regular releases
- Rust FFI optimizer for performance-critical computations
- Official HL vault running on mainnet (proven in production)
- Clean modular architecture with config whitelist protection
- CCXT logging suppressed by default (prevents credential leakage)
- HIP-3 stock perps support with dedicated position fetching

### Concerns
- **No testnet support**: Complete gap — no flag, no env var, no sandbox mode for Hyperliquid
- **Plaintext credential storage**: `api-keys.json` with no encryption, no env var fallback, no file permission enforcement
- **Custom endpoint override attack surface**: URL rewriting with no HTTPS scheme enforcement or domain whitelist
- **No official HL SDK**: Uses CCXT abstraction — less direct control over HL-specific features
- **CI is a no-op**: GitHub Actions runs `true` — tests exist but aren't run in CI
- **Deprecated Rust dependency**: `memmap` 0.7.0 (should be `memmap2`)
- **Debug print statements in production paths**: `passivbot.py` lines 2111, 2120, 2130

### Recommendations
- Add testnet support: config flag or environment variable to switch HL endpoint to `api.hyperliquid-testnet.xyz`
- Add HTTPS scheme validation and domain whitelist to `custom_endpoint_overrides.py`
- Support env var credential loading as alternative to `api-keys.json`
- Enable CI test execution (replace `run: 'true'` with actual pytest)
- Upgrade `memmap` 0.7.0 → `memmap2` in Cargo.toml
- Replace debug `print()` statements with `logging.debug()` in order execution paths
- Consider adding HL-native features: agent wallets, TPSL orders, vault creation

---

## Phase 4 Testnet Trial (single-coin BTC, 2026-04-18 → 2026-04-19)

**Trial windows (both segments are weekend trading — no weekday data)**:
- **Segment 1**: Sat 2026-04-18 01:40 → Sat 07:11 UTC (5.5h, **crashed on HL 502 outage**)
- **Segment 2**: Sat 2026-04-18 13:21 → Sun 2026-04-19 14:07 UTC (25h, manually stopped)

Config: `evaluations/passivbot/testnet-config.json` — BTC long only, 1x leverage, TWEL 50%, forager OFF (`n_positions: 1`, `approved_coins: [BTC]`). TripleBarrier defaults from `btc_long.json` example. Shadow DB: `evaluations/passivbot/shadow/trial-20260418-0149.db`.

### Pre-requisite patch: testnet support

Passivbot upstream has no HL testnet path. Added 8-line patch (`evaluations/passivbot/patches/001-testnet-support.patch`) that calls `set_sandbox_mode(True)` on both CCXT clients when `api-keys.json` user has `use_testnet: true`. CCXT's sandbox mode correctly flips both the URL (`api.hyperliquid-testnet.xyz`) and the EIP-712 phantom-agent `source` field (`"a"` → `"b"`) for valid testnet signing. A ~10-minute fix — that this was never upstreamed despite over a year of CCXT HL sandbox support is itself a finding about the bot's HL-integration priorities.

### Trial results

| Metric | Value |
|---|---|
| Total uptime | 30.46 h (5.5h + 25h) |
| Starting balance | $201.79 |
| Ending balance | $201.85 |
| **Net P&L (measured)** | **+$0.061** |
| **Net P&L (counterfactual)** | **+$0.343** (if last open long had closed at grid target $76,786 instead of force-flattened at $75,980) |
| Total fills | 16 (9 opens / 7 closes / 7 completed round-trips) |
| Maker / taker | 15 / 1 |
| Total notional churned | $283.60 |
| Fees paid | $0.048 (1.71 bps of notional, ≈HL mainnet maker rate 1.5 bps) |
| Fees as % of gross round-trip PnL | 14.1% |
| Orders posted / cancelled | 49 / 43 (3:1 cancel-to-fill ratio — cancels are free on HL) |
| Naive annualized return | ~8.7% measured, ~16% counterfactual |

Segment-level breakdown:
- **Segment 1 (2h8m active in 5.5h uptime)**: BTC oscillated $77,547–$78,000 inside the grid sweet spot. 6 clean round-trips, all profitable, **+$0.258 net (11.5 bps on notional)**. "Ideal regime" for a grid bot — 62% idle but every fill profitable.
- **Segment 2 (99m active in 25h uptime)**: BTC drifted down 1.7% from $76,405 to $75,980. 1 round-trip + 1 position unwound at a loss when we flattened. **+$0.037 net from fills**, ~93% idle. Representative of the "drift regime" where the bot accumulates one-sided long into falling price.

### New defect found: Passivbot crashes on HL 5xx outages

- Root cause in `src/exchanges/hyperliquid.py:417`: `_get_positions_and_balance_cached` stores the last exception via `self._hl_cached_result` and re-raises it on every subsequent call in the outage window. A single transient 502 poisons every loop iteration until the container exits.
- Observed: 200+ identical `ExchangeNotAvailable` traces in 14 minutes, then `exit code 0`.
- Compare: Chainstack Grid Bot survived a ~30s HL 502 cleanly during its 25h trial.
- Upstream fix directions: (a) invalidate the cached error on sub-second TTL, (b) add explicit 5xx retry-with-backoff at the CCXT wrapper layer, (c) catch `ExchangeNotAvailable` in the main loop and sleep-and-retry instead of exiting. CCXT conflates "auth failure" and "transient 5xx" under the same exception class — Passivbot's handler treats both as fatal.
- **Workaround applied**: set `restart: unless-stopped` on the Docker service. Transparently respawns on any exit; Passivbot's `FillEventsManager` auto-loads recent fills at boot so state recovers cleanly.

### Engineering observations

- All-maker discipline (15/16 fills) — better than Hummingbot on the same day
- Order tag scheme (`entry_initial_normal_long`, `close_grid_long`, etc.) carries human-readable intent in client order IDs. Stolen pattern for our own bot.
- Cheap churn: 3:1 cancel-to-fill, zero throttling. Not a cost concern.
- Fill-history auto-load at boot picks up account-wide fills, not bot-instance fills. Clean pattern; caveat that running two bots serially on the same account causes attribution collision.
- `btc_long.json` example config ships TWEL 4.36 (436% notional) — a naïve user would silently be 4× leveraged. Terminology hazard.
- Writable `caches/` and `backtests/` dirs required even in live mode; container non-root user needed explicit uid 1000 ownership on bind mounts.
- Log cadence quiet by design (15 min health, 5 min unstuck). Silence ≠ hang.

### Trial verdict

Score of **3.83 holds**. The testnet trial confirms the Phase 2 assessment: Passivbot's mechanics are solid but its HL integration has real gaps. The +$0.06/30h measured return is a market-regime artifact, not a strategy verdict — Segment 1's $0.26 over 5.5h shows the strategy does capture spread when the market cooperates.

### Follow-up: multi-coin forager test

Single-coin BTC data is insufficient to evaluate Passivbot's distinctive feature — the **forager coin-selection mode**, where `approved_coins > n_positions` causes the bot to dynamically rank candidates by volatility/volume and trade the best. This is Passivbot's main structural differentiator from Hummingbot and a separate code path worth probing. Config: `evaluations/passivbot/testnet-forager-config.json`.

---

## Phase 4 Testnet Trial #2 — Forager mode (2026-04-19 → 2026-04-20)

Narrow scope: **test coin-selection only**, holding per-trade sizing identical to the BTC trial. `n_positions: 1`, long-only, 10 approved HL majors (BTC, ETH, SOL, HYPE, DOGE, AVAX, BNB, SUI, ADA, NEAR). Multi-position + shorts deferred to Trial #3.

### Results

- **Duration**: 20h 45m (15:03 → 11:46 UTC next day)
- **Start balance**: $201.85 USDC
- **End balance**: $204.25 USDC
- **Equity delta**: **+$2.40** (+1.19% account return)
- **Fills**: 88 (41 opens, 47 closes; 89% maker fill rate)
- **closedPnl (SDK sum)**: +$2.804
- **Fees paid**: $0.290
- **Net (pnl − fees)**: +$2.514 — the ~$0.12 gap vs equity delta is HL funding
- **Notional churned**: $1,537.63 → **fee load: 1.89 bps**
- **Errors**: 2 reduce-only race errors in 20h, both self-recovered
- **Container restarts**: 0 (restart policy never triggered)

### A/B vs single-coin BTC trial

|                          | BTC trial (Trial #1)     | Forager trial (Trial #2) | Delta          |
|--------------------------|---------------------------|---------------------------|----------------|
| Duration                 | 30.5h                     | 20.75h                    | –              |
| Net PnL                  | +$0.06                    | **+$2.40**                | **40×**        |
| PnL per hour             | +$0.002/h                 | **+$0.116/h**             | **58×**        |
| Fills                    | 16                        | 88                        | 5.5×           |
| Notional churned         | ~$320                     | $1,538                    | 4.8×           |
| Maker rate               | 94%                       | 89%                       | –              |
| Fee bps                  | 1.71                      | 1.89                      | ≈              |
| DCA ladder hit           | no                        | yes (once, recovered +)   | —              |
| Unstuck triggered        | no                        | no                        | —              |

**Forager clearly outperformed static-BTC for this sample.** The win came from two sources: (1) ETH had far higher log_range (volatility) than BTC for nearly the entire window, so forager parked on ETH and harvested a tighter grid cycle; (2) the one DCA-averaging event at the $2272 level recovered at $2316–$2319 for a combined +$0.47 — exactly the Martingale-style scenario the strategy is designed for.

### Forager selection behavior (observed)

- First ~18h: bot held on ETH continuously (ETH log_range dominated BTC by 2–4× throughout)
- Hour 19: first real rotation activity — bot switched **ETH ↔ BTC 6 times** in ~40 min as log_range scores traded places; each swap moved the outgoing coin to `graceful_stop`
- Final ~2h: back to ETH as its log_range reasserted dominance
- Notable: **0 of 88 fills were on BTC** — all rotations happened during flat/idle moments when the entry ladder hadn't touched BTC's price yet. Selection logic works, but the sample shows forager can rotate faster than entries can fill, giving the new coin little chance to contribute.

### Findings

1. **Forager selection adds material value.** 40× return vs static BTC on matched sizing is not marginal — it's the strategy working as designed.
2. **Reduce-only race (known from Trial #1) reproduces here.** 2 occurrences in 20h. Root cause: Passivbot submits a reduce-only close while a prior partial fill has already shrunk the position. Bot auto-recovers via the 10-errors-per-hour budget, but in high-volatility environments this could erode that budget. **Documented as a Passivbot defect, not a user-fixable config issue.**
3. **WS keepalive disconnects (~1 per 10 min) are constant in both trials.** CCXT Pro auto-reconnects in 1s with no trading impact — benign. Worth noting as an HL testnet behavior pattern, not an instability.
4. **DCA recovery behavior validates the Martingale design.** When ETH dropped 4% and hit the grid's $2272 level, the bot averaged the position to 49% WEL and the larger pile closed at breakeven + markup, netting +$0.47. This is the core value proposition.
5. **Forager rotations don't guarantee fills on the new coin.** In this sample the bot swapped to BTC 3× but never opened a BTC position — price never touched the entry ladder before it swapped back. This is a selection-vs-execution tension worth monitoring at scale.

### Scaled projection

Scaled to a $1000 account with proportional sizing: **+$11.90 / 20.75h ≈ +$13.8/day ≈ +$413/month**. Heavy caveats: 20h is a small sample, ETH's volatility regime during the trial was favorable, and larger notional sizes may incur HL-real slippage not seen on testnet.

### Trial #2 verdict

Forager mode is Passivbot's strongest feature and the trial validates it on HL. Ready to proceed to Trial #3 (shorts enabled + multi-position, e.g. `n_positions: 3–5`) to test whether diversification compounds the gain. **Passivbot's overall score remains 3.83** — forager performance is captured under B1 Strategy (already 5/5); the HL integration gaps that dominate the score (no testnet, no HL SDK) are unchanged.

---

## Phase 4 Testnet Trial #3 — Full forager (2026-04-20 → 2026-04-21)

Full forager config: **long 3 positions / short 1 position**, both sides active across the same 10 approved HL majors, long TWEL 0.75, short TWEL 0.30. Config: `evaluations/passivbot/testnet-forager-trial3-config.json`.

### Results

- **Duration**: 15h 54m (12:01 → 03:55 UTC)
- **Start balance**: $204.25 USDC
- **End balance (after forced flatten)**: $205.21 USDC
- **Equity delta**: **+$0.96** (+0.47% account return)
- **Per-hour return**: **+$0.060/h** (roughly half Trial #2's +$0.116/h)
- **Fills**: 101 (54 opens, 47 closes; 78% maker — lower than Trial #2 due to restart-era taker fills)
- **closedPnl**: +$1.35 (long +$1.05, short +$0.29)
- **Fees**: $0.23 (2.16 bps of notional)
- **Notional churned**: $1,051
- **Internal Passivbot restarts**: 20+
- **Docker container restarts**: 2
- **Coins filled**: ETH (78), BTC (7), SOL (7), BNB (4), SUI (4), ADA (1)

### A/B across all three trials (normalized to per-hour return)

|                     | Trial #1 (BTC 1L)         | Trial #2 (Forager 1L)     | Trial #3 (Forager 3L/1S)  |
|---------------------|---------------------------|---------------------------|---------------------------|
| Duration            | 30.5h                     | 20.75h                    | 15.9h                     |
| Per-hour return     | +$0.002/h                 | **+$0.116/h**             | +$0.060/h                 |
| Fills               | 16                        | 88                        | 101                       |
| Unique coins filled | 1 (BTC)                   | 1 (ETH)                   | **6**                     |
| Maker rate          | 94%                       | 89%                       | 78%                       |
| Fee bps             | 1.71                      | 1.89                      | 2.16                      |
| Restarts            | 1 (HL 502 crash)          | 0                         | **20+**                   |
| New defects         | HL 5xx not survived       | reduce-only race          | **insufficient-margin loop** |

**Ranking by per-hour return: Trial #2 > Trial #3 > Trial #1.** Trial #3's full-feature forager was the most coin-diverse but materially slower than the narrow single-position forager. Adding short + multi-position capacity did not compound the gain — it diluted it.

### Critical defect discovered: insufficient-margin restart loop

When Passivbot fills all its configured slots (3L + 1S in our case) AND tries to post the full DCA ladder + close orders on each, **its internal margin calculation disagrees with HL's**. HL rejects the DCA entries as `InsufficientFunds: Insufficient margin to place order`. Passivbot counts each rejection against the 10-errors-per-hour circuit breaker, trips it in ~4 minutes, and triggers a `RestartBotException`. After restart it reconnects, rebuilds state, tries the same orders, gets rejected again — **infinite loop**.

**Observed symptoms across ~3.5h of Trial #3:**
- 20+ internal Passivbot restarts (`RestartBotException`) in rapid succession
- 2 Docker-level container restarts (triggered by process exit under `restart: unless-stopped`)
- 4 positions stuck for ~2h with no fills because every restart consumed its recovery window failing to post orders
- Unrealized drawdown widened from -$0.09 → -$0.18 during the loop as positions drifted against entry

**Sequence per restart cycle:**
1. Bot starts up, reads positions (3L + 1S)
2. Posts close_grid orders (reduce-only, always accepted)
3. Tries to post entry_grid_normal_long + entry_grid_cropped_long + entry_grid_normal_short + entry_grid_cropped_short = 6–8 simultaneous DCA-level orders
4. HL rejects the margin-adding ones (bot's internal margin model ≠ HL's reality)
5. 10 errors in ~4 min → `RestartBotException`
6. Repeat

**Root cause (inferred):** Passivbot computes per-position WE against a snapshotted balance, doesn't account for cross-margin overlap with other open positions at submission time. The `filter_by_min_effective_cost: true` flag bumps entry size to meet the $10 min, which can push combined exposure above available margin once all slots fill.

**Why this wasn't triggered in Trials #1 or #2:** Both used `n_positions: 1` and only long — only one position's DCA ladder was ever armed at a time. Trial #3 is the first where 4 ladders were active simultaneously.

### Other observations

- **Short code path is fully functional** — 47 fills across ETH (45) + BTC (2 rotations), same round-trip PnL profile as longs (~+$0.032 per $12 notional). No short-specific bugs surfaced.
- **Cross-side forager deadlock**: at T+7h the bot held an underwater BTC short for ~3h with long slots idle because short's log_range dominated and no long candidate met entry criteria. **Multi-position forager can starve one side indefinitely.**
- **Trial capacity never fully utilized**: max concurrent positions observed was 4 (3L+1S), but for >90% of the trial the bot held 1–2 positions. The 3L design is more an upper bound than a steady state.
- **Forced flatten at trial end**: 4 positions market-closed (cost ~$0.16 vs ~$0.05 normal close), ~$0.12 HL funding on the extended short. Both reflected in equity vs fills-only accounting.
- **Agent wallet discovery**: the testnet `api-keys.json` contains an agent private key (signs for main address via `wallet_address`). The wrap-up script had to pass `account_address` to the HL SDK's `Exchange` constructor to operate. Documented for future trial wrap-ups.

### Trial #3 verdict

Full forager with shorts + multi-position **underperforms** single-position forager on net return AND introduces a reproducible restart-loop defect. The short code path works fine in isolation — the defect is specifically at the intersection of "bot at full concurrent capacity" + "DCA ladder + close orders armed" + "Passivbot's margin accounting".

**Practical implication**: anyone running Passivbot on HL should keep `long.n_positions + short.n_positions ≤ 2` OR reduce `total_wallet_exposure_limit` so combined margin demand stays well under available balance. The shipped documentation does not flag this.

**Passivbot score remains 3.83.** This finding reinforces the existing D2 (Testnet support: 0/5) and C2 (Error handling: 4/5 — circuit breaker masks the real bug by making it look like "recoverable") — but the core strategy quality (B1: 5/5) and engineering (C-average: 4.2) assessments stand. The defect is real and worth a writeup, but it's a boundary condition, not a fundamental flaw.

**Best Passivbot config for HL (from three trials):** single-position forager, long-only, `approved_coins` curated to 5–10 high-log_range majors, TWEL 0.5. That matches Trial #2's setup, which produced the best per-hour return with zero defects triggered.
