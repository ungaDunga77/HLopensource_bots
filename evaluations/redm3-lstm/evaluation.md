# Evaluation: redm3-lstm (HYPERLIQUID)

**Repo**: https://github.com/redm3/HYPERLIQUID
**Evaluator**: Claude (static review, no execution)
**Date**: 2026-04-22
**Original tier**: 3 (#13)

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 1 | `secret_key` loaded via `utils.get_config()` from a local `config.json` (never included); raw `eth_account.Account.from_key` used with `constants.MAINNET_API_URL` hardcoded. No agent-wallet pattern, no env var, no docs warning against mainnet. |
| A2 | Dependency hygiene | 1 | No `requirements.txt`, no `pyproject.toml`, no pinning. Imports span `keras`, `tensorflow` (implied), `ccxt`, `pandas_datareader`, `hyperliquid`, `schedule`, `sklearn`. Dep audit found nothing to audit. |
| A3 | Network surface | 2 | Outbound only: hyperliquid REST, binance (ccxt), coinbasepro (ccxt). No listeners. Prints full API responses to stdout (leaks L2 book data, fills, account value). |
| A4 | Code transparency | 3 | Single-author, readable, ~1,250 LOC across 6 files, no obfuscation. Dead code and commented blocks present but no hidden logic. |
| A5 | Input validation | 1 | No validation on API responses (`l2_data[0][0]['px']` unguarded), no retry/timeout on `requests.post`, bare `except:` wrapping `schedule.run_pending()`. Hardcoded Windows path `C:/Users/macmw/...` will crash outside author's machine. |
| | **A average** | **1.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 1 | Two disconnected strategies stapled together: (a) LSTM predicts BTC close from last 60 closes on a stale 2023 CSV; (b) supply/demand zones computed from 1h OHLCV. LSTM output is a single boolean `long` computed ONCE at module import (line 120), never refreshed inside `bot()`. Thesis reduces to "stale model says up = only place buy orders at S/D zones." No edge narrative. |
| B2 | Backtesting | 0 | None. `ml_ltsm.py` trains/evals RMSE in-sample but there is no PnL backtest, no walk-forward, no out-of-sample validation of the trading rule. |
| B3 | Risk management | 1 | Has `max_loss`, `target`, `min_acct_value`, ATR "no-trade" filter, and a `kill_switch`. But: `max_loss = -0.01` compared against `pnl = pnl_perc * pos_size` — units are mixed (percent × coin size), so the threshold is meaningless. `pnl_close` compares to `target=0.2` and `-max_loss=0.01` in the same expression with a sign inversion bug (`elif pnl <= -max_loss` means `pnl <= 0.01`, not a loss floor). Kill switch uses top-of-book as both ask and bid (`bid = float(l2_data[0][0]['px']); ask = float(l2_data[0][0]['px'])`) — both sides identical, not a real spread. |
| B4 | Configurability | 1 | Magic numbers at top of file; no CLI, no config schema, no per-symbol settings. |
| B5 | Monitoring | 1 | `print()` only. No logging, no metrics, no alerts. |
| | **B average** | **0.8** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Zero test files. |
| C2 | Error handling | 1 | Bare `except:` in main loop; unhandled JSON/key errors elsewhere; retry loop with `sleep(10)` and no backoff. |
| C3 | Documentation | 0 | README is 8 lines: title, one sentence, a Colab link, two media embeds. No setup, no config, no risk disclaimer. |
| C4 | Code quality | 1 | Typo in filename (`ml_ltsm.py`), unused imports, hardcoded absolute Windows paths, `no_trading` used as both variable and column name inside `no_trading()` (line 370–372, will raise `UnboundLocalError`), `binance_symbol = 'BTC/USD'` passed to `coinbase.fetch_ohlcv` (wrong exchange's symbol format). |
| C5 | Maintenance | 0 | Single commit (`Update README.md`, 2023-05-22). No issues/PRs activity expected. Model file `btc_model7.h5` and `BTC-USD-actual.csv` frozen at 2023 data. |
| | **C average** | **0.4** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Uses official `hyperliquid` Python SDK (`Info`, `Exchange`) plus raw `requests` to `/info` endpoint for meta and L2 book. Duplicative. |
| D2 | Testnet support | 0 | `constants.MAINNET_API_URL` hardcoded in 3 functions. No testnet flag. |
| D3 | HL features | 1 | Perp order placement via `exchange.order` with `Gtc` TIF and `reduce_only` flag. No builder codes, no vault, no spot, no websockets, no bulk orders. |
| | **D average** | **1.0** | |

---

## Final Score

```
Final = (1.6 * 0.4) + (0.8 * 0.3) + (0.4 * 0.2) + (1.0 * 0.1)
      = 0.64 + 0.24 + 0.08 + 0.10
      = 1.06
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [x] < 2.0: Avoid

**Tier: 3 (confirmed, low end).**

## Summary

As suspected: a solo ML experiment extracted from a Colab notebook. Technically wired end-to-end (LSTM inference → boolean gate → supply/demand limit orders on Hyperliquid mainnet), but the bridge is superficial — the LSTM output is computed ONCE at module import using a stale 2023 CSV with hardcoded Windows paths, and the risk controls contain unit/sign bugs that make the stated thresholds meaningless. No backtesting, no tests, one commit, hardcoded mainnet URL. Avoid.

## Key Findings

### Strengths
- Uses the official `hyperliquid` SDK with correct `Gtc` TIF and `reduce_only` flag patterns for close-outs.
- Has the *shape* of a real bot: position inspection, kill switch, ATR no-trade filter, PnL exit — useful as a negative-example reference.

### Concerns
- LSTM gate is computed exactly once at import from a stale on-disk CSV; never refreshed inside the `bot()` loop. The "ML bot" label is essentially marketing.
- Hardcoded `MAINNET_API_URL` × 3, hardcoded Windows absolute paths, bare `except:`, identical bid/ask assignment from L2 book level 0, sign-flipped max-loss comparison. Would not survive a first testnet run without patches.

### Recommendations
- Do not run, even on testnet, without substantial patching. Not worth the patch budget.
- Treat as a case study in ML→execution anti-patterns when designing our own bot.

---

## Patterns for custom bot

### Anti-patterns (what NOT to do)

1. **Inference at import, not at decision time.** `long = ml_price_prediction()` at module level (line 120) means the model runs once when Python imports the file; the scheduled `bot()` loop every 900s reuses that stale boolean forever. For our custom bot: inference must live inside the tick handler, co-located with the order decision, with an explicit "prediction timestamp" logged alongside each order.

2. **Training data and inference data in different units/sources.** Trained on `BTC-USD-actual.csv` (Yahoo-style daily?), inferred against `ccxt.binance().fetch_ticker('BTC/USD')['last']`. Scaler fit on stale CSV, not on rolling live data. Classic distribution-shift footgun. Our bot: fit scalers on a rolling window of the same data source used at inference, or use stateless features (returns, z-scores) instead of raw prices.

3. **Risk thresholds with mismatched units.** `pnl = pnl_perc * pos_size` then compared to `target = 0.2` and `max_loss = -0.01` — percent × coin-size against a scalar. No unit test would catch this because there are no tests. Our bot: wrap PnL math in a typed function with explicit dollar/percent/bps suffixes on every constant.

4. **Single boolean gate from a regressor.** LSTM predicts *price*, code collapses to `pred > current → long`. A 0.01% predicted move and a 10% predicted move produce the same trade. Our bot: if we use a predictor, size must scale with predicted magnitude and confidence interval, and there must be a dead-zone around "no prediction."

5. **Same-price bid/ask.** `bid = ask = l2_data[0][0]['px']` — literally identical. This is the bug that turns a market-touch kill-switch into a limit order that sits. Our bot: always read both sides of the book, assert `ask > bid`, and have explicit slippage/crossing logic.

### Patterns worth keeping (the skeleton, not the strategy)

- `get_position()` return tuple `(positions, in_pos, size, sym, entry_px, pnl_perc, long)` is a reasonable state snapshot to pass between decision stages.
- Separate `pnl_close()` / `kill_switch()` / `bot()` decision layers — OK structure, bad implementation.
- `get_sz_decimals()` querying `/info` `meta` endpoint is the right way to learn per-symbol precision rather than hardcoding.

### Tooling gaps observed

- `audit_deps.py` found nothing to audit because the repo has no `requirements.txt` / `pyproject.toml`. For bots with only in-file imports, the auditor could optionally fall back to extracting `import` statements and listing them as an unpinned-deps warning. Low priority but matches the `feedback_tooling_improvements.md` note.
- `scan_secrets.py` passed cleanly (repo has no secrets of any kind). No new noise.
