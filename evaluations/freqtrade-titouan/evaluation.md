# Evaluation: freqtrade-titouan (Freqtrade France fork)

**Repo**: https://github.com/titouannwtt/freqtrade-fork (based on freqtrade/freqtrade v2026.3)
**Evaluator**: osbots research pipeline
**Date**: 2026-04-19
**Tier**: 2 (priority #3 for pattern harvesting)

> **Scope note.** This fork is ~137 kLOC but the author explicitly scopes the delta: 27 files, +832 / −213 lines vs. upstream `freqtrade/stable`. Where possible, scores below reflect the **fork's delta**; where a criterion can only be meaningfully assessed at the framework level, the evidence column flags it as inherited from upstream Freqtrade.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Fork keeps upstream Freqtrade's key handling (env vars, config file). `.gitignore` extended (+32 lines) to strip `live_configs/`, `backtest_configs/`, `database/`, `*access*.json`, `*credentials*`, `*secret*`, `*.key`, `*.pem`, `.claude/`. No new key-handling code; fork does not introduce regressions. Live config templates use placeholders. |
| A2 | Dependency hygiene | 2 | `audit_deps.py` reports **67 MEDIUM CVEs, 2 LOW pinning issues, 0 CRITICAL/HIGH**. All MEDIUMs are transitive CVEs in upstream-pinned deps (aiohttp suite: CVE-2026-34514/18/19/20/25, cryptography, etc.). This is an upstream Freqtrade exposure the fork inherits unchanged; no added deps. Not disqualifying for research, but a production bot would need an aiohttp bump. |
| A3 | Network surface | 3 | Upstream Freqtrade surface (REST/WS to exchanges, Telegram, optional REST API server exposing FreqUI). Fork does **not** add new network endpoints. Inherits upstream's JWT-auth REST API and known bind defaults. `install-ui` now pulls FreqUI from the author's personal fork (`titouannwtt/frequi-fork`) — a supply-chain trust shift from the Freqtrade org to a single maintainer. Flag as amber. |
| A4 | Code transparency | 5 | README is unusually honest: explicit file-by-file diff table listing all 27 changed files with line counts and purpose. Exceeds most evaluated bots for this criterion. Marketing claims ("ADL detection", "liquidation detection", "TrendRegularityFilter", "custom hyperopt loss", "`--sampler`") **all map to concrete, readable code paths** verified below. No dark logic. |
| A5 | Input validation | 4 | New code validates well: `fetch_liquidation_fills()` (hyperliquid.py L335-397) explicitly checks for NaN/≤0 on `liq_price/price/amount` and logs malformed fills; `_handle_external_close()` (freqtradebot.py L668-734) validates `close_price` (`<=0 or isnan or isinf`) and wraps cancel paths in try/except with rollback+refresh on failure. `TrendRegularityFilter` guards `denom==0`, `ss_tot==0`, NaN clamping. Fork-added code is clearly defensive. |
| | **A average** | **3.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 3 | Fork ships **no strategies**. `user_data/` has no `strategies/` dir. "Aggressive DCA" mentioned in README is just reuse of upstream Freqtrade's `adjust_trade_position` DCA primitive — no bundled DCA strategy, no anti-martingale ladder logic in this repo. Strategies live in the author's three companion repos (VWAP, KAC-Index, `freqtrade_basics`) and behind a paid Discord. For this fork, B1 is strictly the strategy framework inherited from Freqtrade (excellent), but users must bring their own strategy. |
| B2 | Backtesting | 5 | Full upstream Freqtrade backtest + hyperopt framework. Fork adds ready-to-use `backtest_configs/` for 6 exchanges including `futures_hyperliquid_*.json`, plus `download.sh` to pre-fetch 10 days of candles. Hyperopt loss (`MyProfitDrawDownHyperOptLoss`) is real, 54 LOC, penalizes drawdown via `profit − (relative_account_drawdown × profit) × (1 − DRAWDOWN_MULT)` with a hard cutoff at −45% DD. Unlike Passivbot's evolutionary (NSGA-II / Optuna) approach, this fork *composes* with Optuna samplers — the new `--sampler` CLI flag (cli_options.py +21 lines) exposes NSGA-II/III, TPE, CMA-ES, GP, QMC. A real, useful orthogonal capability. |
| B3 | Risk management | 4 | Real, novel contributions: (a) `fetch_liquidation_fills()` polls `fetch_my_trades` for entries with non-null `liquidationMarkPx` (the HL-specific marker in the raw fills info dict) and closes the DB trade at the actual liquidation mark price; (b) `_handle_external_close()` detects positions gone from the exchange without a liquidation marker (ADL or manual UI close), cancels remaining orders, closes at current market price with `exit_reason="external_close"`. Both are triggered from `freqtradebot.py` L575-582 only in futures mode when `total==0`. Addresses a real DEX failure mode (DB desync → infinite loop) that most evaluated bots ignore. **Caveats**: polling-based (no WS liquidation subscription); no anti-martingale guard on DCA beyond upstream Freqtrade's `max_entry_position_adjustment`. `TrendRegularityFilter` is a sensible regime filter for short-only strategies but not a general regime classifier. |
| B4 | Configurability | 5 | Upstream Freqtrade is extremely configurable; fork adds schema entries for new features (config_schema.py +12 lines) and exposes `--sampler` at CLI. `TrendRegularityFilter` exposes `lookback_timeframe`, `lookback_period`, `min_r2`, `refresh_period`. |
| B5 | Monitoring | 4 | Upstream Telegram + REST API extended: new Telegram messages for `external_close` and liquidation events (telegram.py +9), exit-reason exposed via RPC/API schema (rpc.py +19, api_schemas.py +2). Companion FreqUI fork (not evaluated) adds fleet monitoring. `launch_bot.sh` auto-restart loop with 60 s grace; `launch_dashboard.sh` for UI-only mode. |
| | **B average** | **4.2** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 2 | Upstream Freqtrade has a large test suite including `tests/exchange/test_hyperliquid.py`. The fork adds **no tests** for any of its new features: no tests for `_handle_external_close`, `_handle_liquidation`, `fetch_liquidation_fills`, `TrendRegularityFilter`, or `MyProfitDrawDownHyperOptLoss` (grep for those symbols under `tests/` returns nothing). Inherited coverage is strong; delta coverage is zero. |
| C2 | Error handling | 4 | New code paths consistently catch `ccxt.DDoSProtection` → `DDosProtection`, `ccxt.OperationFailed/ExchangeError` → `TemporaryError`, `ccxt.BaseError` → `OperationalException`. `_handle_external_close` / `_handle_liquidation` both rollback + refresh the SQLAlchemy session on failure (freqtradebot.py L663-665, L732-733) to avoid inconsistent DB state — a subtle correctness detail many bots miss. |
| C3 | Documentation | 5 | README is bilingual (EN/FR), gives exact `+lines/−lines` deltas per file, usage examples for `--sampler` and `TrendRegularityFilter`, strong legal disclaimer section, and acknowledges PSAN regulatory context for French users. One of the best-documented fork deltas in our evaluation pool. |
| C4 | Code quality | 4 | Fork code follows upstream conventions, uses type hints, decorators (`@retrier`), PEP-compliant line lengths. `TrendRegularityFilter` implements linear regression inline via numpy sums (no scipy dependency) with explicit NaN/denom guards — tidy. Minor smell: `import math` inside `fetch_liquidation_fills` loop body (L362) rather than at module top. |
| C5 | Maintenance | 3 | Single-author fork; git log in clone shows a single squashed commit (`4fec0e3 docs: translate scripts to English…`), not the full upstream history — the fork was presumably rebased/pushed as a snapshot. Author claims "4 years running Freqtrade in production". Upstream dep recency is v2026.3. No CI/CHANGELOG in the delta. Sustainability depends on one person. |
| | **C average** | **3.6** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | Uses upstream Freqtrade's `freqtrade/exchange/hyperliquid.py` (ccxt-based, 446 LOC, extensively developed upstream) **plus** a +77 line delta adding `fetch_liquidation_fills()`. ccxt abstraction rather than the official `hyperliquid-python-sdk` — consistent with Freqtrade's architecture. HIP-3 DEX handling, unified-account detection, isolated-margin liquidation-price calc all present (inherited + some polish in the delta). |
| D2 | Testnet support | 2 | Nothing testnet-specific in the fork delta. Upstream Freqtrade supports arbitrary exchange endpoints via config but there is no HL-testnet preset, no sandbox toggle, no testnet docs in the fork. One concerning default: `backtest_configs/futures_hyperliquid_100.json` ships with `"dry_run": false`, which is a footgun if a user loads it as a live config without reading it. |
| D3 | HL features | 4 | Liquidation & ADL detection specifically leverage HL-native semantics: `liquidationMarkPx` field on fills, `userAbstraction` info endpoint for unified-account detection, HIP-3 DEX enumeration with per-DEX balance/position aggregation, HL-specific liquidation-price formula validated against 196 real ccxt outputs (avg deviation 0.00029%, inline comment block L255-264). This is the most HL-idiomatic implementation seen in the evaluation pool after Passivbot. |
| | **D average** | **3.3** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.6   * 0.4) + (4.2   * 0.3) + (3.6   * 0.2) + (3.3   * 0.1)
      = 1.44 + 1.26 + 0.72 + 0.33
      = 3.75
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening — **harvest patterns, optional short testnet trial**
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Honest, well-scoped fork of Freqtrade whose 832-line delta adds four concrete, correctly-implemented capabilities: HL liquidation detection via `liquidationMarkPx` polling, external-close (ADL / manual UI) reconciliation, a short-biased pairlist regime filter, and a custom profit × drawdown hyperopt loss with a pluggable Optuna sampler CLI. All four README claims map to real, defensive code — no marketing fluff. No aggressive-DCA strategy is actually bundled; "aggressive DCA" refers to use of upstream Freqtrade's DCA primitives in the author's separate (partly paywalled) strategy repos. Inherits upstream Freqtrade's large dependency surface (67 MEDIUM CVEs, mostly aiohttp) and extensive test suite, but the fork delta itself ships **zero tests**. Best pattern source in the evaluation pool so far for DEX position-reconciliation logic.

## Key Findings

### Strengths
- **HL liquidation detection** (`freqtrade/exchange/hyperliquid.py` L335-397): pattern of polling `fetch_my_trades` for non-null `liquidationMarkPx` info fields, with explicit NaN/≤0 guards on price/amount. Directly reusable in the custom bot.
- **External-close reconciliation** (`freqtrade/freqtradebot.py` L668-734): detects ADL or manual UI closes, cancels dangling orders, marks trade `external_close`, and critically **rolls back the DB session on failure** to avoid desync. This is the class of bug that silently kills bots on DEXes.
- **Liquidation-price formula** (hyperliquid.py L238-312): HL-specific maintenance-margin calc validated against 196 real positions (avg deviation 0.00029%) with an inline derivation from the HL docs. Copy-paste quality for the custom bot's dry-run risk surface.
- **`--sampler` CLI** (cli_options.py, hyperopt_optimizer.py): decouples hyperopt search algorithm from strategy code. Complements Passivbot's hardcoded NSGA-II approach — useful A/B pattern for comparing convergence on single-objective vs Pareto losses.
- **`TrendRegularityFilter`**: clean inline linear-regression with R² for regime filtering; replicable without scipy.
- **Exceptional delta documentation**: per-file line-count README table is a model others should copy.

### Concerns
- **Zero tests for the fork delta** — all new code paths (liquidation, external close, filter, loss) are unit-test-free. Inherited upstream tests do not exercise them.
- **Polling-based liquidation detection** — not WebSocket-subscribed; the detection window is bounded by bot loop cadence. Fine for low-frequency DCA, potentially stale for HFT.
- **No anti-martingale safety** on DCA beyond upstream Freqtrade's `max_entry_position_adjustment`; the author's "aggressive DCA" ethos is in separate, partly paywalled strategy repos and not auditable here.
- **`backtest_configs/futures_hyperliquid_100.json` ships `"dry_run": false`** — footgun if a new user copies it as a live template.
- **Supply-chain trust shift**: `freqtrade install-ui` now pulls from `titouannwtt/frequi-fork` instead of the Freqtrade org repo — single-maintainer UI in front of a trading REST API.
- **67 MEDIUM CVEs** inherited from upstream pins (aiohttp, cryptography); not fork-specific but relevant if running live.
- **Single-commit git history in clone** — no upstream lineage visible, making it harder to diff cleanly.

### Recommendations
- **Harvest, don't run wholesale.** Three patterns belong in the custom bot:
  1. `fetch_liquidation_fills()` polling pattern (NaN-guarded) for HL.
  2. External-close reconciliation with SQLAlchemy `rollback + refresh` on failure.
  3. HL liquidation-price closed-form formula from `dry_run_liquidation_price()`.
- **Optional short testnet trial** (lower priority than Passivbot/Hummingbot): use a minimal bundled strategy with `TrendRegularityFilter` + `MyProfitDrawDownHyperOptLoss` to shadow-validate the external-close path under real ADL conditions. Budget: 24 h, $20 notional, isolated margin 2x. Not necessary if the goal is only pattern extraction.
- **Do not adopt the `install-ui` redirect** if running this fork — pin to upstream FreqUI.
- **Audit or bump aiohttp** before any live run.

---

## Phase 5 Testnet Trial A (2026-04-21 → 2026-04-22, ~24h total runtime)

Minimal smoke trial to validate the fork's HL exchange module + the `_handle_external_close` path on a real HL testnet account. Not a PnL-measurement run.

### Setup
- **Strategy**: `HLSmokeStrategy.py` (committed in `evaluations/freqtrade-titouan/strategies/`) — RSI + EMA-crossover signals, 20 bps TP, 300 bps SL, 1× leverage, $12 stake
- **Pair**: BTC/USDC:USDC perp (testnet)
- **Testnet enablement**: patched `freqtrade/exchange/hyperliquid.py` to call CCXT's `set_sandbox_mode(True)` in overridden `_init_ccxt` when `exchange.use_testnet=true` in config. `set_sandbox_mode` flips both the base URL (to `api.hyperliquid-testnet.xyz`) AND the EIP-712 phantom-agent `source` field (`"a"` → `"b"`). Patch + patched file saved in `evaluations/freqtrade-titouan/patches/`.
- **Container**: `sandbox-bot-testnet-freqtrade-titouan` (compose service in `sandbox/docker-compose.yml`)

### Trial phases

**Phase 1 — aggressive strategy (enter_long every bar), ~12h.**
Deliberately neutered entry logic to guarantee open trades for the external-close test. 3 round-trips on BTC perp.

| Trade | Open | Close | Mechanism | PnL |
|---|---|---|---|---|
| 1 | $75631 | $75631 (market close via SDK) | **External force-close** | ~breakeven |
| 2 | $75961 | $76113 (LIMIT_SELL) | Organic TP hit after ~8h hold | +20 bps |
| 3 | $76349 | $76501 (LIMIT_SELL) | Organic TP hit after ~1h | +20 bps |

**Phase 2 — moderate strategy (RSI<45 + EMA_fast > EMA_slow), ~12h.**
Restored a real signal-driven entry. Only 1 entry signal fired over 12h of uptrending BTC (RSI stayed above 45 in the trend). The one entry's passive limit (`entry_pricing.price_side: same`) didn't cross before the 5-minute unfilledtimeout cancelled it. **Zero fills under moderate strategy.**

### Results
- **Duration**: ~24h
- **Start → End balance**: $205.207 → $205.287 = **+$0.080** (+0.04%)
- **Fills (whole trial)**: 6 (3 opens, 3 closes) — all from Phase 1
- **closedPnl sum**: +$0.099
- **Fees paid**: $0.017 (2.50 bps of $68 notional — 67% maker, higher taker rate than Passivbot's ~90% because the `populate_exit` path went through Freqtrade's default market-close fallback on Phase 1's first cycle)
- **HL funding cost** on long 8h+ hold: ~$0.002
- **Internal bot restarts**: 0

### Observations

1. **`_handle_external_close` fires correctly.** Force-closed Trade id=1 at 15:10 via the HL SDK. Freqtrade detected the missing position within ~10 seconds:
   - 15:10:47 WARN: `Not enough BTC in wallet to exit Trade(id=1, ...)` (benign — bot tried its normal exit, saw empty wallet)
   - 15:10:53 INFO: `LIMIT_SELL fulfilled for Trade id=1` + `Marking Trade(id=1) as closed as the trade is fulfilled and found no open orders for it`
   - DB state consistent after reconciliation. **No phantom open-trade state.** The SQLAlchemy rollback+refresh pattern (flagged as a key pattern in the static eval) works as designed.

2. **Testnet patch (~15 lines override `_init_ccxt`) is sufficient for full HL testnet operation.** Upstream Freqtrade has no HL testnet support; our patch is the minimum necessary addition. Same situation we patched for Passivbot — confirms this is a family pattern across CCXT-based HL integrations.

3. **Bootstrap latency: ~4.5 min per container start.** Bulk of the delay is Freqtrade's per-market `fetch_market_leverage_tiers` call across ~500+ HL markets (roughly 500 sequential REST requests). Caches on disk after first run but the `user_data/` bind-mount ownership issue (see below) prevented the cache from being re-read on subsequent starts. HL's `uses_leverage_tiers=False` flag in the fork's `_ft_has_futures` is defined but never checked by Freqtrade core — would short-circuit this delay if wired up.

4. **WS reconnect cadence matches the Passivbot and Hummingbot findings: ~2 disconnects per 30-min window** (`NetworkError: Connection closed by remote server, closing code 1000`). All self-recovered in <2s, zero trading impact. Confirmed this is HL testnet behavior, not a fork defect.

5. **`_ft_has['uses_leverage_tiers'] = False`** in the HL module is an unused flag — Freqtrade core loads leverage tiers unconditionally for futures. Worth an upstream PR.

6. **Config schema strictness: `telegram` and `api_server` sections required all their sub-fields even when `enabled: false`.** Had to remove both sections entirely. This is upstream Freqtrade behavior; worth noting for any testnet-config authoring.

7. **`user_data/` bind-mount fails chown** inside the container because `no-new-privileges:true` blocks `sudo chown` in the Freqtrade entrypoint. Warnings are harmless (app continues) but the leverage-tiers cache doesn't persist across restarts. For v1 we'd either pre-chown the mount host-side or relax the security flag.

8. **Passive limit entry doesn't fill in a trending market** (Phase 2 observation). `entry_pricing.price_side: same` + 5-min `unfilledtimeout` combined with HL's moderate mean-reversion on 5m candles means limit orders at best-bid rarely cross when the market is directional. Real use would need either `price_side: other` (cross the spread) or longer timeouts — both introduce their own costs.

### Trial verdict

**What we validated on HL testnet:**
- ✅ Testnet patch and CCXT sandbox-mode flip.
- ✅ HL exchange module boot + market load + leverage tier load.
- ✅ `_handle_external_close` DB reconciliation.
- ✅ Organic TP exit via LIMIT_SELL.
- ✅ WS reconnect under HL testnet drops.
- ✅ 5-min `unfilledtimeout` cancels non-filling limits cleanly.

**What we did NOT validate:**
- ❌ Organic-signal-driven entries reliably filling (passive-limit + trending market = 0 fills in Phase 2).
- ❌ Liquidation detection in the wild (can't generate cascades on testnet).
- ❌ DCA / aggressive position adjustment (no strategy ships using it in this fork).
- ❌ The hyperopt samplers (backtesting feature, not live-observable).

**Score holds at 3.75.** Trial confirmed the fork-specific patterns that matter for our custom bot:
- Liquidation-price closed-form formula (code-validated only — needs stress test with a real cascade to fire-validate).
- `_handle_external_close` rollback+refresh (**fire-validated**).
- `fetch_liquidation_fills` with NaN guards (code-validated only).

The recommendation stays: harvest the three patterns, do not run the fork wholesale.

### Wrap-up
- Container stopped 2026-04-22.
- Final HL state: balance $205.287, 0 positions, 0 open orders.
- No forced flattens needed (account was flat when the stop signal came).
- Cron `03f9a751` deleted.
- Patch preserved at `evaluations/freqtrade-titouan/patches/hyperliquid.py.patched`.
- Strategy preserved at `evaluations/freqtrade-titouan/user_data/strategies/HLSmokeStrategy.py` (and mirror in `evaluations/freqtrade-titouan/strategies/`).
- `testnet-config-live.json` is gitignored (contains private key); scaffold `testnet-config.json` committed.
