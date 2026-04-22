# Evaluation: AVELLANEDA_MARKET_MAKING_FREQTRADE

**Repo**: https://github.com/djienne/AVELLANEDA_MARKET_MAKING_FREQTRADE
**Evaluator**: Claude (Opus 4.7)
**Date**: 2026-04-19
**Tier**: 2 (picked for academic-strategy coverage — only A-S implementation on HL in our catalog)

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | `exchange.key`/`secret` are plaintext strings in `user_data/config.json`, following the default Freqtrade pattern (no env-var or keystore layer). The shipped config is fine (`"key": ""`, `dry_run: true`), but there is no documented path to secure storage, and the bot inherits Freqtrade's habit of storing secrets in a mounted JSON. Hyperliquid requires a private key (not an API key), which makes in-file storage more dangerous than, say, a Binance key. No agent-wallet pattern. |
| A2 | Dependency hygiene | 3 | `scripts/requirements.txt` and `HL_data_collector/requirements.txt` both pin only lower bounds (`pandas>=1.5.0`, `arch>=5.0.0`, `hyperliquid-python-sdk` unpinned). `audit_deps.py` found no recognized manifests in the root (files live one level down). Relying on Freqtrade's pinned base image (`freqtradeorg/freqtrade:2025.7`) partially mitigates. `arch`, `numba`, `scipy` are heavy deps; no lockfile. |
| A3 | Network surface | 2 | `api_server` enabled by default on `0.0.0.0:8080` (mapped to `127.0.0.1:3004` in compose, good) with `force_entry_enable: true`, `forcebuy_enable: true`, and **hardcoded `username: "MM"`, `password: "MM"`** plus a **hardcoded JWT secret** checked into git. `show_PnL.py` also hardcodes `USERNAME = "MM"` / `PASSWORD = "MM"` (line 20-21). Anyone on the host (or if the bind is misconfigured, the LAN) can hit `/forcebuy`. Data collector opens outbound-only WS to `api.hyperliquid.xyz`. |
| A4 | Code transparency | 4 | No obfuscation, no sketchy network calls, no telemetry. `get-docker.sh` (official Docker install script) is vendored — not malicious, but unusual to ship inside a bot repo and inflates the secret-scan noise (15 HIGH hits are almost all the install script and the research notebook). Strategy logic is readable (~540 lines, one file). Small OLD/ directory with legacy scripts. |
| A5 | Input validation | 2 | Params JSON is loaded and keys are indexed with `.get(..., default)` in some places but direct `['market_data']['sigma']` elsewhere — a malformed file crashes `bot_start`. No sanity bounds on `gamma`, `sigma`, `k` before they're fed into `np.log(1 + gamma/k)` (division/log of non-positives). `get_mid_price` handles empty orderbook. Pair is derived via `replace("/USDC:USDC","")` with no validation. The backtest's MIN_SPREAD_PCT clamp exists in the *offline* quote generator but **not in the live `calculate_optimal_spreads`** in `avellaneda.py`. |
| | **A average** | **2.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | README explains the A-S model with equations; code comments reference the 2008 paper. `calculate_optimal_spreads` is a clean 40-line function that mirrors the spec. Parameter estimation pipeline (`volatility.py` GARCH(1,1)-t, `intensity.py` Poisson MLE for `A·exp(-k·δ)`, `backtest.py` grid search for `(γ, T)`) is the most rigorous A-S param stack we've seen in the catalog. |
| B2 | Backtesting | 3 | `scripts/backtest.py` (737 lines) runs a grid over `γ × T` evaluating realized PnL on historical fills, estimates bid/ask separately, uses the tick grid via `deltalist`. Research notebook `Francesco_Mangia_Avellaneda_BTC.ipynb` documents the derivation. But: no Freqtrade-native `hyperopt` integration beyond one `best_hyperopt.py` stub; no walk-forward validation; the backtester replays from the bot's own collected data, not from an independent source. |
| B3 | Risk management | 1 | **Critical defect**: `q_inventory_exposure = 0.0` is hardcoded in all three price hooks (lines 473, 494, 515). The reservation-price skew — the *entire point* of Avellaneda-Stoikov inventory management — is disabled. The bot quotes symmetric spreads around mid regardless of position, then relies on `max_open_trades: 1` + `minimal_roi: {"0": -1}` + `custom_exit: "always_exit"` to flatten. Stoploss is `-0.85` (85%!), no trailing, `MaxDrawdown` protection is commented out. Long-only, ping-pong — one directional move and you're stuck bagholding. No emergency kill switch beyond `cancel_open_orders_on_exit`. |
| B4 | Configurability | 3 | Pair switch is a one-line edit (pair_whitelist → auto-derives ticker → auto-loads param file). `AVELLANEDA_PARAMS_DIR` env var for Docker. Parameter recalc cadence (15 min lock file, 10-loop trigger) is hardcoded in the strategy. Maker fee hardcoded as `0.02/100.0` — not read from the exchange. `stake_amount`, `dry_run`, etc. are standard Freqtrade config. |
| B5 | Monitoring | 4 | Dedicated `mm_logger` writes Avellaneda inputs/outputs (γ, σ, k, r, spreads) to `log_ave_mm.txt` on every quote. Freqtrade REST/Web UI on :8080. `show_PnL.py` is a nice CLI aggregator that discovers all `MM_*` containers via `docker ps` and queries their APIs — genuinely useful pattern. Parameter JSON is written each recalc with timestamps for inspection. |
| | **B average** | **3.0** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 1 | Two files called "test": `test_env.py` (6 lines, just imports) and `user_data/strategies/test_load_ave_config.py`. No pytest suite, no CI. |
| C2 | Error handling | 3 | `load_configs` has a layered-fallback search path with reasonable exception handling. GARCH fit wrapped in try/except with rolling-σ fallback (sensible). MLE fit wrapped in try/except. `bot_start` calls `sys.exit()` if whitelist != 1 — brutal but explicit. No retries around orderbook/wallet calls in `get_mid_price`. |
| C3 | Documentation | 4 | README is well-written, includes math, explains parameter recalc cadence, data-collection requirement, pair-switching workflow. AGENTS.md present. Docstrings on most functions. |
| C4 | Code quality | 3 | Strategy is one 540-line file with three near-identical `custom_entry_price` / `custom_exit_price` / `adjust_entry_price` blocks (copy-paste, ripe for a helper). `calculate_avellaneda_parameters.py` has formatting issues (huge blank-line gaps suggesting messy merges). `backtest.py` at 737 lines could be split. Overall readable, Pythonic, uses dataclasses in the collector. Numba `@jit` used selectively for the grid search hot path. |
| C5 | Maintenance | 2 | Single-maintainer (djienne); 1 commit visible in our clone's `git log` (shallow), last activity Dec 2025 (~4 months stale by our date). No issues/PRs workflow obvious. Freqtrade-based so it inherits upstream maintenance for the harness. |
| | **C average** | **2.6** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | The *bot itself* uses HL only via ccxt through Freqtrade (`exchange.name: "hyperliquid"`). The separate `HL_data_collector` uses `hyperliquid-python-sdk` directly for WS market data, which is correct. No order routing goes through the native SDK — so no access to HL-specific order types. |
| D2 | Testnet support | 1 | Nothing. Config has no testnet URL toggle, no env-var plumbing. The vendored `hyperliquid_sdk.txt` *documents* TESTNET_API_URL but the bot doesn't use it. Would need a Freqtrade ccxt override to point at testnet — not wired. Ships with `dry_run: true` as the safety net instead. |
| D3 | HL features | 1 | No native TPSL triggers, no agent wallets, no vault address, no HIP-3, no builder codes beyond a README referral link. Stop-loss set to `stoploss_on_exchange: false` (pure bot-side). Uses `USDC:USDC` perp pair. |
| | **D average** | **1.3** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (2.6   * 0.4) + (3.0   * 0.3) + (2.6   * 0.2) + (1.3   * 0.1)
      = 1.04 + 0.90 + 0.52 + 0.13
      = 2.59
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

The most mathematically serious Avellaneda-Stoikov implementation in our HL catalog — GARCH(1,1)-t volatility, MLE-fitted Poisson intensity per side, grid-optimized (γ, T), parameters hot-reloaded from JSON. But the live strategy **hardcodes inventory `q = 0`, disabling the reservation-price skew that is the entire value proposition of A-S**, and the Freqtrade API server ships with hardcoded `MM/MM` credentials and a committed JWT secret. Harvest the math; do not trial the bot as-shipped.

## Key Findings

### Strengths
- **Offline parameter estimation is textbook-quality**: `volatility.py` does GARCH(1,1) with Student's-t innovations, rescales returns for numerical stability, falls back to EWMA-smoothed rolling σ with a 2× divergence sanity check. `intensity.py` fits `λ(δ) = A·exp(-k·δ)` via MLE of a Poisson process with a sensible log-linear initial guess. `backtest.py` optimizes (γ, T) jointly on a log-spaced grid.
- **Clean parameter-producer / consumer split**: offline `calculate_avellaneda_parameters.py` writes `avellaneda_parameters_{TICKER}.json`; live strategy reads it, locked to 15-min recalc cadence via a file-based mutex. This decouples slow optimization from hot-path quoting and makes parameters auditable — we should adopt this pattern.
- **Effective mid-price from $1000 depth walk** (`get_mid_price`, lines 400–456): rather than BBO midpoint, it walks the book until cumulative notional ≥ \$1k and averages the effective bid/ask. Robust to tight-top spoofing — worth copying.
- **Dedicated `mm_logger` → `log_ave_mm.txt`** writing every quote's γ/σ/k/r/spread is exactly the observability a MM bot needs for post-mortem diagnosis.
- **`show_PnL.py` container-discovery pattern**: queries `docker ps`, filters by name prefix, pulls metrics from each Freqtrade API. Nice ops tooling for multi-pair deployments.

### Concerns
- **Inventory risk aversion is not implemented.** `q_inventory_exposure = 0.0` is hardcoded in all three price hooks; the computed-but-unused `total_quote_position` variable above each hardcode is a tell. The bot's behavior under adverse selection is identical to a naive symmetric-spread bot. `gamma` still controls total spread width via the half-spread term `0.5·γ·σ²·T + (1/γ)·ln(1 + γ/k)`, so it's not vestigial, but the core inventory-aware pricing is gone.
- **API server credentials are hardcoded secrets** in `user_data/config.json`: `username: "MM"`, `password: "MM"`, `jwt_secret_key: "d1654caf3c530f6b037ae59a999d9d9328dec66bdd68799112cf1ba7d65276a3"`, with `force_entry_enable: true`. Same `MM/MM` in `show_PnL.py:20-21`. If the listen port ever escapes the 127.0.0.1 binding (misconfigured compose, reverse proxy), this is an immediate RCE-equivalent (force an entry, drain).
- **Long-only, ping-pong, no drawdown protection.** `stoploss = -0.85`, `MaxDrawdown` protection commented out, `custom_exit` always returns `"always_exit"` relying on the sell-side quote to fill. In a one-way market you sit on inventory until the reservation price (unskewed!) crosses back.
- **No testnet path.** Ships with `dry_run: true` as the only safety net. A real testnet trial would require hand-patching ccxt endpoints.
- **Maker fee hardcoded** (`0.02/100.0`) — HL's tier/volume-based fees are not read from the exchange; stale value → miscomputed half-spreads.
- **No input validation on loaded params**: a corrupted `avellaneda_parameters_PAXG.json` with `gamma=0` or negative `k` will pass through to `np.log(1 + gamma/k)` and produce NaN quotes. The offline backtest has a `MIN_SPREAD_PCT = 0.0004` clamp; the live path does not.
- **Secret-scan noise**: 15 HIGH findings (mostly `get-docker.sh` and the research notebook's embedded b64 image data), plus 1 real hit (the `MM/MM` password). Author shipping the vendored Docker install script is unusual.

### Recommendations
- **Harvest, don't run.** Copy `volatility.py`, `intensity.py`, and the grid-optimization pattern from `backtest.py` into our custom bot's offline research stack. They are the cleanest worked implementation of A-S parameter estimation in the catalog.
- **When we implement A-S ourselves, actually compute `q`**: normalized inventory (position notional / capital, signed), and feed it to `r = s - q·γ·σ²·T`. This is 3 lines to uncomment and is the only reason to use A-S over a simpler constant-spread quoter.
- **Adopt the producer/consumer split**: slow parameter optimization writes JSON with a timestamp; live loop reads JSON with a recency check; file-based mutex rate-limits recalculation. Add a schema validation step we don't have here.
- **Adopt the `$1k depth effective mid` pattern** — better than naive BBO.
- **Adopt dedicated MM logger** with one line per quote (γ, σ, k, q, r, δ_b, δ_a, mid).
- **Do not adopt**: Freqtrade-wrapped API server defaults, hardcoded fee constants, the single 540-line strategy file with copy-pasted hooks.
