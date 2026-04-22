# Evaluation: Hummingbot (HL Connector)

**Repo**: https://github.com/hummingbot/hummingbot
**Evaluator**: Claude (automated)
**Date**: 2026-04-01
**Tier**: 1

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Pydantic `SecretStr` for address and private key fields. `is_secure: True` hides credentials in TUI. Platform-level AES-CTR encrypted keyfiles via `config_crypt.py` (password-protected, uses `eth_keyfile`). `eth_account.Account.from_key()` keeps key in memory as Account object — never logged, never serialized to API payloads (only r,s,v signature emitted). Vault mode with `HL:` prefix stripping. Two auth modes: `arb_wallet` (Arbitrum private key) and `api_wallet` (HL API wallet key). Spot auth has `approve_agent()` for API wallet registration. |
| A2 | Dependency hygiene | 3 | 34 `install_requires` with version ranges (`>=`), not exact pins. HL connector needs ~6 deps (eth-account, msgpack, aiohttp, pydantic, cryptography, safe-pysha3). Platform pulls in heavy deps not needed for HL: injective-py, xrpl-py, web3, numba, scipy, TA-Lib. Conda `environment.yml` as primary env manager. `pip-audit` could not be run directly (no `requirements.txt`); manual review found no known CVEs in HL-critical deps. |
| A3 | Network surface | 5 | Hardcoded endpoints: mainnet `api.hyperliquid.xyz`, testnet `api.hyperliquid-testnet.xyz`. No custom endpoint override system (unlike Passivbot — simpler and safer). WS endpoints also hardcoded. Rate limiting: 1,200 req/min global with linked per-endpoint limits via `AsyncThrottler`. Broker ID `HBOT` (benign affiliate tracking). No telemetry. No outbound calls beyond HL API. |
| A4 | Code transparency | 5 | Apache-2.0 license. 17,896 stars, 100+ contributors. Foundation-backed (Hyperliquid Foundation sponsorship). All source readable Python. Cython stubs are empty placeholders (`cdef class dummy(): pass`). No obfuscation. |
| A5 | Input validation | 4 | Pydantic config validation with `field_validator` for mode, vault, address fields. Min notional $10 enforced in perp connector. Market order slippage capped at 5%. `float_to_wire()` validates precision (raises on rounding > 1e-12). Trading rules loaded from exchange metadata. Spot connector lacks explicit `min_notional_size` enforcement. |
| | **A average** | **4.2** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | Platform with rich strategy framework: V2 controllers for market-making, arbitrage, directional. `v2_funding_rate_arb.py` script (funding rate arbitrage). Strategy composition via controllers. Well-documented strategy patterns. |
| B2 | Backtesting | 4 | Hummingbot V2 has backtesting framework with candle data feeds. HL-specific candle feeds for both spot (`hyperliquid_spot_candles/`) and perp (`hyperliquid_perpetual_candles/`). Not as mature as Passivbot's evolutionary optimizer but functional. |
| B3 | Risk management | 3 | Platform-level order tracking and position management. Perp connector enforces ONEWAY position mode only. Leverage API integration with cross/isolated margin. Position deduplication and cleanup on empty positions. No per-connector circuit breaker or wallet exposure limits (relies on platform-level controls). |
| B4 | Configurability | 5 | Separate mainnet/testnet config classes. Two wallet modes (arb/api). Vault toggle. HIP-3 market enable/disable flag. Pydantic models with interactive prompts. Rich platform-level config system. |
| B5 | Monitoring | 4 | Hummingbot TUI with real-time status. Structured logging via `HummingbotLogger`. Position/balance tracking. Order status updates via WebSocket. Telegram integration at platform level. Fill tracking via both REST polling and WS. |
| | **B average** | **4.2** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 5 | 274 tests, all passing, 0 failures. 14 test files totaling 7,866 lines. Comprehensive mock-based tests using `aioresponses`. Tests cover: auth/signing, order placement/cancellation, order book data source, user stream, WebSocket, utils, config validation, HIP-3 markets, leverage, position management, trading rules. 9.15s execution time. |
| C2 | Error handling | 4 | `IOError` raised on order failures with descriptive messages. Order-not-found detection and processing. WebSocket error handling with reconnection via platform base class. Heartbeat ping at 30s intervals. `asyncio.CancelledError` properly re-raised. Graceful handling of unmapped coins in position updates. Debug logging on non-critical failures. |
| C3 | Documentation | 3 | Platform-level docs at hummingbot.org. HL connector has inline docstrings on key methods. Config fields have interactive prompts. No standalone connector-specific API reference. Platform docs cover general usage but HL connector specifics are sparse. |
| C4 | Code quality | 4 | Clean architecture: separate auth, constants, web_utils, exchange, order book, user stream per connector. Inherits from platform base classes (`ExchangePyBase`, `PerpetualDerivativePyBase`). Proper use of `bidict` for symbol mapping. Async/await throughout. **Concern**: Significant code duplication between spot and perp connectors (auth, utils, web_utils are near-identical). MD5 for order ID formatting (not cryptographic, acceptable). |
| C5 | Maintenance | 5 | 17,896 stars. 100+ contributors. Foundation-backed with dedicated team. Last HL connector commit: Feb 2026. Active CI/CD. HIP-3 support added Jan 2026 (recent HL-native feature). Regular releases. |
| | **C average** | **4.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Does NOT use official HL SDK. Custom EIP-712 signing implementation (direct, not via CCXT abstraction). Implements own `action_hash()` with msgpack + keccak, `sign_l1_action()` with phantom agent construction. Signing matches official SDK pattern but is independently implemented. |
| D2 | Testnet support | 5 | Full testnet support: separate `HyperliquidTestnetConfigMap` / `HyperliquidPerpetualTestnetConfigMap` config classes. Dedicated testnet domains (`hyperliquid_testnet`, `hyperliquid_perpetual_testnet`). Testnet URLs in constants. Chain source `"b"` for testnet phantom agent. Best testnet support of all evaluated bots. |
| D3 | HL features | 5 | Spot + perp connectors (dual connector). HIP-3 builder-deployed perp DEXs with correct asset ID mapping (offset + index). Vault support. API wallet mode with `approve_agent()`. Funding rate data feed. Candle data feeds for both spot and perp. Rate oracle sources. TPSL order types (trigger orders with take-profit/stop-loss). `reduceOnly` for position close. Leverage API with cross/isolated margin. HBOT broker ID. |
| | **D average** | **4.0** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (4.2   * 0.4) + (4.2   * 0.3) + (4.2   * 0.2) + (4.0   * 0.1)
      = 1.68 + 1.26 + 0.84 + 0.40
      = 4.18
```

## Verdict

- [x] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Hummingbot's HL connector is the strongest evaluated bot, scoring 4.18 — the first to clear the testnet trial threshold. It combines institutional-grade security (encrypted keyfiles, SecretStr, no custom endpoint overrides) with the most comprehensive HL feature set (dual spot+perp, HIP-3, vaults, API wallets, testnet, TPSL, candle feeds). 274 tests all passing. The main weaknesses are code duplication between spot and perp connectors and the perp auth's lack of thread-safe nonce management.

## Key Findings

### Strengths
- Best-in-class testnet support (separate config classes, dedicated domains)
- Most comprehensive HL feature coverage (HIP-3, vaults, API wallets, spot+perp, TPSL, candle feeds)
- Password-encrypted credential storage (AES-CTR via eth_keyfile) — best key management of all evaluated bots
- 274 tests all passing with comprehensive coverage including HIP-3 edge cases
- Foundation-backed with active maintenance

### Concerns
- **Nonce divergence**: Spot auth has thread-safe `_NonceManager` (collision-free), but perp auth uses raw `time.time() * 1e3` — potential nonce collision under concurrent signing
- **Code duplication**: Auth, utils, and web_utils are near-identical between spot and perp (maintenance risk — divergence could mean one connector gets fixes the other misses)
- **Large dependency footprint**: 34 install_requires, most not needed for HL. Attack surface is platform-wide, not connector-scoped
- **MD5 for order IDs**: `hashlib.md5()` used to convert client order IDs to hex format. Not a cryptographic use (collision probability negligible at practical order volumes) but technically deprecated

### Recommendations
- Port `_NonceManager` from spot auth to perp auth (simple fix, high impact)
- Consider extracting shared HL base classes to reduce duplication
- Audit `is_exchange_information_valid()` — always returns `True`, meaning no filtering of disabled/delisted pairs at exchange info level (relies on downstream checks)

---

## Phase 4 Testnet Trial (2026-04-17 → 2026-04-18)

### V1 `simple_pmm` script — smoke run only
- Surfaced 5 upstream defects (detailed in `docs/lessons.md`): HIP-3 `split(':')` crash, case-sensitive dedup mismatch, HIP-3 fetch path bugs, sample script uses non-perp `OrderCandidate`, and nonce-collision in order submission (~50% rejection rate for simultaneous symmetric quotes).
- Position flattened at **−$0.024**. Shadow DB: `shadow/trial-20260417-1818.db`.
- Not a performance test — just enough runtime to catch the connector bugs.

### V2 `pmm_simple` controller — 5.5h trial (BTC-USD)
Config: $80 quote budget, 2 spread levels (10/30 bps), 1x leverage, SL 200 bps / TP 50 bps / time_limit 1800s, refresh 60s. DB: `shadow/trial-v2-20260417-1908.db`.

| Metric | Value |
|---|---|
| Fills | 134 (68 buys / 66 sells) over 5.52h |
| Rate | 24 fills/hr |
| Total notional churned | $2,248 |
| Avg trade size | 0.00022 BTC (~$16.78 notional) |
| Gross edge captured | ~14 bps on notional |
| Fees paid | $0.44 (~2 bps) |
| Realized PnL (matched) | $2.15 |
| Net inventory drift | −0.002 BTC short (stuck executors) |
| Total PnL incl. MTM | $3.06 |
| Price range (intraday) | $77,494 – $78,442 (122 bps) |

**Scale estimate for a $1,000 account, same rotation**: ~$117/day gross ceiling in a friendly regime. Realistic steady-state after mainnet adverse-selection haircut, real fees, inventory drift, and bug throttle: **$3–10/day expected**, with **−$30 to −$200 on trending days**. Annualized ~10–30% APR when conditions cooperate, negative when they don't. PMM on one pair has inherently low Sharpe (~0.5–1.0).

### New defect found: V2 PositionExecutor ↔ HL reduce-only sync bug
- After ~5.5h: 15,303 `Reduce only order would increase position` rejections; 5,006 take-profit failures; multiple executors hit `Retrying 10/10` cap → bot alive but not placing new orders.
- Root cause: V2 `pmm_simple` submits take-profits as reduce-only LIMIT. Hummingbot's internal position state lags HL's actual state; when executor thinks it's long but HL view is already flat (settlement delay between fill event and position-snapshot refresh), HL rejects.
- V2 masks the V1 nonce-collision via retry, but introduces this *new* defect via TripleBarrier exit logic.
- Upstream fix direction: reconcile against `clearinghouseState` before reduce-only submit, or fall back to regular LIMIT on reduce-only failure.

### Strategy coverage — what was **not** tested
Hummingbot ships ~15 HL-applicable strategies. This evaluation tested 2:
- **V1 tested**: `simple_pmm` (smoke)
- **V2 tested**: `pmm_simple` (5.5h trial)
- **V1 untested**: `pure_market_making`, `perpetual_market_making`, `avellaneda_market_making`, `cross_exchange_market_making` (XEMM), `spot_perpetual_arbitrage`, `twap`
- **V2 untested**: `pmm_dynamic`, `dman_v3`, `bollinger_v1`, `macd_bb_v1`, `supertrend_v1`, `stat_arb`, `xemm_multiple_levels`

Current data supports a verdict on the *bot* and the *PMM family*, not the strategy framework as a whole. XEMM is the most important gap — hedging inventory on an external venue would materially change the risk profile vs the drift observed here.

### Trial verdict
Score of 4.18 holds. Strategy mechanically captures spread; engineering defects are real but documentable and upstream-fixable. "Lots of trades, tiny P&L" is a **scale** story (tiny testnet account, $10 HL min notional forces $17/fill), not a strategy failure. Call the bot-evaluation done after this trial; further Hummingbot work belongs to *strategy research* scope, not *bot evaluation* scope.
