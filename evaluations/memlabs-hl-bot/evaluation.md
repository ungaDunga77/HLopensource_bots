# Evaluation: memlabs-hl-bot (hyperliquid-trading-bot)

**Repo**: https://github.com/memlabs-research/hyperliquid-trading-bot
**Evaluator**: claude-opus-4-7
**Date**: 2026-04-22
**Tier**: 3 (honorable mention / low-signal repo, 28 stars, no description)

---

## Triage Summary

- **11 files, ~1,649 LoC** across 6 Python modules + 1 Jupyter notebook + 1 conda env file.
- **Single commit** dump ("fix missing import") — not active development, uploaded as a snapshot.
- README present (246 lines — the brief's claim of "no README" was incorrect at clone time).
- `.idea/` directory present (PyCharm project leftovers, minor hygiene issue).
- **Secret scan**: clean (0 critical, 0 high, 0 findings).
- **Dep audit**: no recognized manifest (uses a conda `.yml`, which `audit_deps.py` does not parse — **tooling gap**).
- **Real HL code**: yes. Uses `hyperliquid-python-sdk`, the official WebSocket endpoint, `Info`/`Exchange` clients, `candleSnapshot` REST, and `eth_account` for signing. Not scraped boilerplate.

**Verdict**: SUBSTANTIVE but TOY-SCALE. Proceed with abbreviated full eval. Not a skip — the code is real and clean — but clearly a personal research snippet, not a production bot.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | Reads `HL_SECRET` / `HL_WALLET` from env vars; no `.env` committed; scan clean. No agent-wallet guidance in README. |
| A2 | Dependency hygiene | 2 | Conda env file lists deps unpinned (`numpy`, `pandas`, `scikit-learn`, `hyperliquid-python-sdk`, etc. all floating). No `requirements.txt`, no lockfile. Audit tool could not parse `.yml`. |
| A3 | Network surface | 4 | Single outbound WebSocket to `api.hyperliquid.xyz` + REST to `/info`. No inbound ports, no RPC, no DB. Clean surface. |
| A4 | Code transparency | 5 | All code human-readable, no obfuscation, no binaries, no network fetches at runtime beyond HL. ~1.6k LoC easily auditable in one sitting. |
| A5 | Input validation | 2 | Interval validated against `TIME_INTERVALS`. Otherwise, no validation on price inputs, trade sizes, or WS message structure — `last_price = float(last_trade['px'])` will throw on malformed messages, but no circuit breakers. No position or PnL limits. |
| | **A average** | **3.2** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 3 | Strategy is explicit: 1-feature linear regression on lag-1 log return → sign-of-forecast determines buy/sell. Mean-reversion with fixed, tiny coefficients (`weight=-0.0001`, `bias=-2e-7`). Clearly toy; no edge expected. |
| B2 | Backtesting | 3 | `research.py` + `research.ipynb` provide an AR-lag dataset builder + `eval_linreg` with train/test split + win-rate + cum-return plot. Basic but real. No walk-forward, no out-of-sample reporting pipeline. |
| B3 | Risk management | 1 | None. No stop-loss, no max-position, no slippage guard, no drawdown halt. Strategy **always trades every interval** (closes then reopens) — pays 2x taker fees per bar regardless of signal strength. Thresholdless sign-based execution will churn fees. |
| B4 | Configurability | 2 | `params` dict in `main.py` (sym, interval, model.weight, model.bias); `trade_sz` hardcoded (0.0002 BTC) inside `create_strategy()`. No YAML/JSON config; edit-source-to-change. |
| B5 | Monitoring | 2 | `print()` statements only. No structured logging, no metrics, no alerting, no persistent tick recording (`TickReplay` is returned and discarded). |
| | **B average** | **2.2** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Zero test files. No pytest, no unittest, no assertions outside models. |
| C2 | Error handling | 2 | Try/except around `market_close`/`market_open` (swallow + print). WS reconnect with exponential backoff (1s → 30s, good). But errors in feature calc, model predict, or `dl_prices_ts` crash the bot. No poison-pill handling. |
| C3 | Documentation | 4 | Every module and function has thorough docstrings (arguably over-commented for the LoC). README is clear with architecture diagram, install steps, config example, and disclaimer. Surprising given the single-commit nature. |
| C4 | Code quality | 4 | Clean separation (stream / models / strategy / hl / main). ABC `Tick` base class. Dataclasses for `Order`/`TickReplay`. Type hints throughout. Good OO design for the size. |
| C5 | Maintenance | 1 | Single commit, no releases, no CI, no issues tracker activity, no contributor guide. Snapshot-only. |
| | **C average** | **2.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | Uses `hyperliquid-python-sdk` properly: `Info`, `Exchange`, `eth_account.Account.from_key`, `market_open`/`market_close`. Pre-flight checks `marginSummary.accountValue` and `spot_user_state.balances` before trading. |
| D2 | Testnet support | 4 | `hl.init(main_net=False)` default points to `constants.TESTNET_API_URL`. Flag exists to flip to mainnet. README advises paper/testnet first. No automated testnet smoke-test scaffolding. |
| D3 | HL features | 2 | Only `trades` WS subscription + `candleSnapshot` REST + perp `market_open`/`market_close`. No L2 book, no funding, no vault/HLP, no spot, no TWAP, no builder codes. |
| | **D average** | **3.3** | |

---

## Final Score

```
Final = (3.2 * 0.4) + (2.2 * 0.3) + (2.2 * 0.2) + (3.3 * 0.1)
      = 1.28 + 0.66 + 0.44 + 0.33
      = 2.71
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: **Reference only**
- [ ] < 2.0: Avoid

**Tier 3 / honorable-mention. No testnet trial warranted.**

## Summary

A clean, well-documented, toy linear-regression trader uploaded as a single commit by a research group. Code quality and HL SDK usage are good, but there is zero risk management, zero tests, a churning every-bar trade loop that guarantees fee bleed, and a model with hardcoded coefficients so small they encode no meaningful edge. Useful as a minimal reference for "how to wire an HL WS + periodic taker strategy in ~300 LoC", but not something to run unmodified.

## Key Findings

### Strengths
- Clean modular design (stream / models / strategy / hl / main) with ABC `Tick` base — easy to port patterns to a custom bot.
- Testnet-by-default via `hl.init(main_net=False)`.
- Exponential-backoff WebSocket reconnection loop is textbook-correct (1s → 30s cap, reset on clean exit).
- Pre-flight equity check before trading (reject zero-value account with actionable error message).
- Thorough docstrings despite being a single-commit dump.

### Concerns
- **Strategy always trades**: `np.sign(y_hat) == 1` → buy, else sell. No dead-zone / threshold. `BasicTakerStrat.execute` closes then reopens every bar, paying double taker fees. On 1m interval this would bleed out quickly.
- **No risk controls**: no stop-loss, no max-position, no daily-loss halt, no max-leverage clamp. `leverage=1.0` param exists but is unused.
- **Unpinned conda deps** in `hyperliquid-trading.yml` — fully floating versions including the HL SDK itself.
- **Zero tests** in a trading bot that signs transactions.
- **Hardcoded coefficients** (`weight=-0.0001`, `bias=-2e-7`) with no instructions to retrain; the README suggests copy-pasting new values from `research.eval_linreg` but provides no pipeline to promote them.
- **Single commit, no maintenance** — not a living project.

### Recommendations
- Do not use as-is. If patterns are useful, lift the `stream.py` sliding-window/log-return classes and the reconnect loop for reference into a custom bot (see below).
- Skip full testnet trial; score is sub-3.0.

---

## Patterns for custom bot (harvested)

Three things worth copying / adapting:

1. **Streaming feature classes** (`stream.py`): `Window` (deque-based O(1) sliding window returning evicted element), `LogReturn`, `Lags`. Small, correct, reusable. About 80 LoC.
2. **WS + periodic-scheduler pattern** (`main.py:trade_periodically`): aligns executions to interval boundaries (`mins_past = now.minute % period_mins`, sleep to `(period_mins - mins_past)*60 - now.second`), with a `+0.001` buffer to cross the boundary. Ideal for a 1h/15m cron-style bot.
3. **Pre-flight equity check** in `hl.init`: refuse to start if `marginSummary.accountValue == 0` and no spot balances — catches the "wrong address" / "agent wallet vs main wallet" class of errors with a clear message. Worth copying verbatim.

## Tooling gaps observed

- `tools/audit_deps.py` does not parse **conda `environment.yml` / `.yml` files**. It returned "No recognized language manifests found" despite a valid conda env with pip deps embedded. Adding conda-yml support (or at least extracting the `pip:` block) would improve coverage — several OSS HL bots ship conda-only. Logging as a `tooling_improvements` candidate.
