# Evaluation: Nova Funding Hub

**Repo**: https://github.com/SoYuCry/Nova_funding_hub
**Evaluator**: Claude (Opus 4.7)
**Date**: 2026-04-19
**Tier**: 2 (priority #4, data-hub reference for custom HL bot's funding-arb layer)

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 5 | Purely read-only public-API aggregator. No private keys, no signing, no wallet handling. `EDGEX_COOKIES` is the only secret-shaped env var (optional Cloudflare bypass). Secret scan clean (0/0/0). |
| A2 | Dependency hygiene | 3 | Deps under-pinned: only `pandas==2.1.3` is pinned; `aiohttp`, `requests`, `streamlit`, `websockets`, `matplotlib` are floating. 0 known CVEs at audit time, but reproducibility is weak. No lockfile. |
| A3 | Network surface | 4 | Outbound-only HTTPS to 7 exchange APIs + one WS (EdgeX). No inbound surface beyond local Streamlit (`localhost:8501`). Cloudflare handling via UA spoof + cookies is a risk signal but functionally contained. |
| A4 | Code transparency | 5 | Small codebase (~1.2k LOC Python), single repo, no binary blobs, no obfuscation. Data cache files (`*_intervals.json`, `*_last_next.json`) are plaintext JSON checked into the repo. |
| A5 | Input validation | 3 | Symbol normalization is defensive (snap/clamp). JSON schema assumptions are loose — heavy use of `.get()` with silent `None`. Caches have range-checks (`MIN_INTERVAL_H`–`MAX_INTERVAL_H`) to reject bad values. Would fail ungracefully on malformed WS frames, but no attack surface since no execution. |
| | **A average** | **4.0** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 3 | **Charitable score for intended purpose**: this is a data hub, not a trading bot. For its scope, purpose is clear — aggregate funding rates across 7 venues, compute APY + cross-venue max spread, display. No execution layer, no spot-perp hedging, no order router. Zero strategy logic beyond "max APY spread highlight". |
| B2 | Backtesting | 0 | None. No historical storage beyond small on-disk JSON caches of `nextFundingTime` (used only for interval inference, not analytics). No time-series DB, no replay, no PnL sim. |
| B3 | Risk management | 0 | N/A — no positions to manage. Rate clamping and `catchup_flags` are data sanity, not trading risk. |
| B4 | Configurability | 2 | Hardcoded 60s poll, hardcoded exchange list, `USE_MOCK_DATA` boolean, `EDGEX_COOKIES`/`PARADEX_BASE_URL` envs. No config file. Streamlit UI has no user config anymore (gear removed per code comment). |
| B5 | Monitoring | 3 | Python `logging` used across adapters (per-fetch success/duration, warnings on anomalies/cache-fallback). Streamlit displays last-update timestamp. No metrics, alerts, or structured logs. |
| | **B average** | **1.6** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 1 | One live-network smoke test against Binance (`test.py`). No unit tests, no mocked adapter tests, no CI. |
| C2 | Error handling | 4 | `fetch_all_raw` isolates per-exchange exceptions (one bad venue doesn't kill the page). Binance/Aster have explicit catchup-flag state machine for anomalous `nextFundingTime` jumps — best-in-class for interval inference. EdgeX has Cloudflare retry/backoff with skip-on-block. Silent `.get()` swallowing is the main weak spot. |
| C3 | Documentation | 2 | README is ~60 lines, Chinese-only, covers install + features. Zero docstrings on exchange adapters. No API schema docs. Architecture is discoverable because codebase is tiny. |
| C4 | Code quality | 4 | Clean `Exchange` ABC with uniform `get_funding_rate`/`get_all_funding_rates`. Each adapter is self-contained, ~100–300 LOC, idiomatic `async`/`aiohttp`. Sensible concurrency via per-adapter `asyncio.Semaphore` (Aster 5, Backpack 10, EdgeX 2, Binance 3). Symbol normalization centralised in `funding_core.normalize_symbol`. Light code duplication between Binance and Aster interval-inference (near-identical logic). |
| C5 | Maintenance | 2 | Single-author repo, last visible commit `23403f4 fix: remove delist symbol in hyperliquid`. Single contributor (SoYuCry / @0xYuCry). No tagged releases, no CHANGELOG, no CI. Deployed live demo (`nova-btc.xyz`) suggests active use. |
| | **C average** | **2.6** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | No `hyperliquid-python-sdk` dependency. Raw `aiohttp` POST to `/info` with `{"type": "metaAndAssetCtxs"}`. For read-only funding ingestion this is actually fine (SDK would add weight) — but it means zero reuse of SDK types/schemas. |
| D2 | Testnet support | 1 | Mainnet URL hardcoded (`https://api.hyperliquid.xyz`). No env override for testnet. Irrelevant for a pure data hub but counts against the rubric. |
| D3 | HL features | 3 | Treats HL as one of N venues, not first-class. Notable: handles both main perps universe **and** `dex=xyz` (equity markets, e.g. NVDA) — shows awareness of HL's recent equity-perp product. Correctly identifies HL funding cadence as 1h (hardcoded). Filters `isDelisted`. No use of HL-unique data (predicted funding, open interest, L2 book, spot-perp basis). |
| | **D average** | **2.0** | |

---

## Final Score

```
Final = (4.0 * 0.4) + (1.6 * 0.3) + (2.6 * 0.2) + (2.0 * 0.1)
      = 1.60 + 0.48 + 0.52 + 0.20
      = 2.80
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Nova Funding Hub is a clean, small multi-venue funding-rate aggregator (Streamlit dashboard) covering HL, Aster, EdgeX, Lighter, Backpack, Binance, Paradex. It is explicitly **just a data hub** — no execution, no positions, no backtesting, no forecast. Score (2.80) is dragged down by the B/C pillars that assume a trading bot; as a reference implementation of a cross-venue funding substrate it punches well above that number. Security pillar is strong precisely because there's nothing to compromise (no keys, no signing). The real value is in the adapter-layer patterns, not the app itself.

## Key Findings

### Strengths
- **Uniform adapter ABC** (`exchanges/base.py`): every venue exposes `get_funding_rate(symbol)` + `get_all_funding_rates()` returning the same dict shape `{exchange, symbol, rate, timestamp, interval_hours, [nextFundingTime, fundingInterval]}`. Single point of symbol normalization in `funding_core.normalize_symbol`.
- **APY normalization**: `calculate_apy(rate, interval_hours) = rate * (24/interval_hours) * 365 * 100` — the right move for comparing 1h (HL/Lighter/Backpack), 4h (EdgeX), and 8h (Binance/Aster/Paradex) cadences on one axis.
- **Interval inference state machine** (Binance + Aster): infers funding period from deltas between successive `nextFundingTime` values, snaps to {1,4,8}h, persists last-seen value to disk, and enters a "catchup" mode on anomalous jumps instead of corrupting the cache. This is genuinely good defensive engineering for a world where exchanges occasionally shift cadence mid-symbol.
- **Per-venue concurrency control**: each adapter sets its own `asyncio.Semaphore` sized to that API's tolerance (EdgeX 2 due to Cloudflare, Backpack 10, Binance 3, Aster 5). Graceful degradation — one venue failing doesn't take out the page (`fetch_all_raw` catches per-task).
- **HL equity-perp awareness**: HL adapter queries both default universe and `dex=xyz` to include equity markets (NVDA etc.) — reflects a currently-live HL feature our own bot should plan around.
- **Background-fetch + snapshot pattern**: UI reads from a thread-local `data_store` + `lock`, never hitting exchange APIs on render. Clean separation of polling cadence from user-facing refresh.

### Concerns
- **No predictive funding / next-funding forecast**: only current-period observations. For a real funding-arb strategy you need expected funding at next settlement (HL publishes predicted funding; other venues infer from premium index). This is the single biggest gap vs. an arb-substrate.
- **No execution layer at all**: not a negative for its scope, but means zero reusable order-routing, hedging, or spot-perp pairing logic.
- **No persistence**: funding history is not stored. On-disk JSON is only for interval-inference state, not a time-series. Any backtest or funding-trend analysis requires bolting on a DB.
- **Treats HL as one of many**: no use of HL-native features (L2 book, predicted funding, OI, insurance-fund-style context), no testnet mode, no SDK. Fine for a dashboard; insufficient as an HL-first substrate.
- **Dep pinning is loose** (only pandas pinned). Streamlit/aiohttp breaking changes could silently break it.
- **No real tests**: one live-network smoke test. Adapters have zero mocked coverage despite being the most fragile surface (each exchange can change JSON shape at any time).
- **Single-maintainer repo, Chinese-only docs**: accessibility and bus-factor concerns.

### Recommendations

**Build on it? No — reimplement, but port the patterns.** The code is too small, too coupled to Streamlit, and too lean on persistence/forecasting to be a foundation. For our custom HL bot's funding-arb layer, **reimplement a clean substrate** that borrows these three transferable patterns:

1. **Adapter ABC with uniform `{rate, interval_hours, nextFundingTime}` return shape + central `normalize_symbol` + `calculate_apy`.** Exact structure from `exchanges/base.py` + `funding_core.py`. This is the right seam.
2. **Interval inference state machine with catchup flag** (from `binance.py::_infer_interval_from_payload` and `aster.py::_infer_interval`). Port verbatim — this is the non-obvious defensive logic that would take us a week to rediscover the hard way.
3. **Per-venue semaphore + `asyncio.gather` with per-task exception isolation** (`funding_core.fetch_all_raw`). Each venue has its own rate-limit personality; per-adapter concurrency sizing is the right pattern.

Extensions our substrate needs on top: (a) predicted-next-funding (HL native + premium-index-derived for others), (b) persistent time-series storage (SQLite/Parquet), (c) HL-first treatment including testnet base-URL switching and SDK-typed responses, (d) spot-perp basis alongside perp-perp funding to enable full carry strategies.

**Patches applied**: none (not run — pure data tool, no execution to sandbox).
**Secret scan**: 0 high / 0 medium / 0 low (see `secret-scan.json`).
**Dep audit**: 0 CVEs, 6 LOW findings (under-pinned deps).
