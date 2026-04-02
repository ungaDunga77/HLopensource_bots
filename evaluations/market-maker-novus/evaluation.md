# Evaluation: Hyperliquid Market Maker (Novus-Tech-LLC)

**Repo**: https://github.com/Novus-Tech-LLC/Hyperliquid-Market-Maker (404 — recovered from fork nvampx/Hyperliquid-Market-Maker)
**Evaluator**: Claude
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | Private key in `.env` (plaintext), `.env` in `.gitignore`. Optional `AGENT_KEY` for agent wallets. No encryption, no zeroize crate, no vault. Standard pattern but no protections beyond gitignore. |
| A2 | Dependency hygiene | 1 | **No Cargo.lock** — builds non-reproducible. 31 direct deps, 2 custom git forks (`0xNoSystem/hyperliquid-rust-sdk`, `0xNoSystem/Indicators_rs`) not pinned to specific commits — supply chain risk. 0 known vulns (deferred to sandbox). |
| A3 | Network surface | 2 | Hyperliquid API (trading). actix-web server on `localhost:8090` with **`allow_any_origin()` CORS** — any browser can send commands. No auth on API endpoints. No telemetry. |
| A4 | Code transparency | 3 | Clear Rust with good module separation. But: **1 `unsafe impl Send`** (`signal/types.rs:98`), 32 unwrap/panic/expect calls throughout critical trading paths. |
| A5 | Input validation | 1 | No pre-trade validation (position size, leverage bounds, margin sufficiency not checked before order). Hardcoded 1% slippage. `f64::from_bits(1)` used as sentinel value instead of `Option`. `panic!("THIS IS INSANE")` on unexpected liquidation side. |
| | **A average** | **1.80** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 2 | README is marketing/contact-focused (Telegram group, "implementation assistance"). Strategy is RSI-based scalping (not market-making despite the name). `config.toml` documents risk/style/stance options. Indicator logic in code only, no user-facing strategy docs. |
| B2 | Backtesting | 0 | `backtest.rs` is a 23-line skeleton (just an async fn signature and a panic). Not functional. |
| B3 | Risk management | 1 | **Dangerous defaults**: 90% of margin allocated per trade, 20x default leverage, no stop-loss, no take-profit — exits only by time (420-second fixed duration). No max drawdown. Margin allocation system exists but no dynamic rebalancing. Liquidation detection present but response is just position reset. |
| B4 | Configurability | 2 | `config.toml` (style: Scalp/Swing, risk: Low/Normal/High, stance: Bull/Bear/Neutral). Multi-market via web UI with per-market indicator selection. No dry-run mode. No testnet. Indicator thresholds hardcoded (StochRSI 80/20, duration 420s). |
| B5 | Monitoring | 2 | WebSocket live updates to React dashboard (price, PnL, indicators, strategy params). env_logger for server-side logs. **All state in-memory** — trade history, positions, margin all lost on crash. No Telegram/Discord alerts, no external monitoring. |
| | **B average** | **1.40** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Zero tests. `src/bin/test.rs` is an empty file (0 bytes). `enginetest.rs` is an interactive test harness, not automated tests. |
| C2 | Error handling | 1 | **32 unwrap/panic/expect calls** across critical paths: order fill parsing, candle processing, address validation, liquidation handling. `panic!("THIS IS INSANE")` on unexpected liquidation side value. `panic!("ASSET ISN'T TRADABLE")` on missing asset. No retry logic, no circuit breaker, no graceful shutdown signal handling. |
| C3 | Documentation | 1 | README is mostly marketing (Telegram contact, "implementation assistance or integration support"). Config options in `config.toml`. No architecture docs, no setup guide, no API docs, no troubleshooting. |
| C4 | Code quality | 2 | Good module separation (bot/market/executor/strategy/signal). Async/await with tokio. Channel-based communication (flume + mpsc). But: 32 panics, 1 unsafe impl, `f64::from_bits(1)` sentinel, magic numbers throughout, no structured error types (String errors), println! debug output. |
| C5 | Maintenance | 1 | 7 commits all on 2025-10-15 (code dump) + 1 README update a month later. No CI/CD, no issues, no PRs. Original repo now 404. **No license** — legally cannot be used or redistributed. |
| | **C average** | **1.00** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Custom fork of `hyperliquid_rust_sdk` (0xNoSystem's branch, not pinned). InfoClient for market data + user state. ExchangeClient for market orders. Also depends on `hyperliquid` crate v0.2.4 (separate package). No error handling on SDK calls in several places. |
| D2 | Testnet support | 0 | **No testnet support.** `BaseUrl::Mainnet` hardcoded in executor.rs. Must modify source and recompile to switch. No env var, no config option. |
| D3 | HL features | 2 | Market orders only (no limit orders). Leverage updates. WebSocket subscriptions (candles, user fills for liquidation detection). 200+ perp assets cataloged. No vaults, subaccounts, cancel/modify, or spot. |
| | **D average** | **1.33** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (1.80 * 0.4) + (1.40 * 0.3) + (1.00 * 0.2) + (1.33 * 0.1)
      = 0.720 + 0.420 + 0.200 + 0.133
      = 1.47
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [x] < 2.0: Avoid

## Summary

A Rust perpetual futures trading bot misnamed as "market maker" — it actually implements RSI-based scalping with time-based exits. The original repo was deleted (404) but recovered from forks. Published by a contract development shop (Novus-Tech-LLC) with a marketing-heavy README and contact info for paid support. Despite decent architectural patterns (async multi-market management, channel-based communication, indicator engine), the implementation is dangerous: 32 unwrap/panic calls across critical trading paths including `panic!("THIS IS INSANE")` on unexpected exchange data, no Cargo.lock, 90% margin per trade with no stop-loss, all state in-memory (lost on crash), no testnet, no tests, and no license. The lowest-scoring bot evaluated so far, and the only one in "Avoid" territory.

## Key Findings

### Strengths
- **Multi-market architecture**: Per-asset pipelines with independent signal engines, executors, and WebSocket subscriptions running as tokio tasks
- **Channel-based communication**: flume bounded channels + tokio mpsc for decoupled components
- **Indicator library**: 7 indicator types (RSI, StochRSI, SMA-on-RSI, EMA, EMA Cross, ADX, ATR, SMA) via `kwant` crate with per-market timeframe configuration
- **React web dashboard**: Real-time market cards with price, PnL, indicators, add/remove/pause market controls
- **Margin allocation system**: Per-market margin tracking with on-chain sync every 2 seconds
- **200+ perp assets**: Full Hyperliquid universe cataloged in `assets.rs`

### Concerns
- **32 unwrap/panic/expect calls**: Including `panic!("THIS IS INSANE")` on liquidation side parsing and `panic!("ASSET ISN'T TRADABLE")` on missing asset. Bot will crash on unexpected exchange data.
- **No Cargo.lock**: Non-reproducible builds. Custom git fork deps not pinned to commits.
- **Dangerous risk defaults**: 90% of margin per trade, 20x leverage, no stop-loss, no take-profit — time-based exit only (420s). No max drawdown.
- **All state in-memory**: Trade history, positions, margin allocations all lost on crash. No database, no persistence.
- **No testnet**: `BaseUrl::Mainnet` hardcoded. Must edit source to switch.
- **No license**: Cannot legally use, modify, or redistribute.
- **`unsafe impl Send for Handler`**: Bypasses Rust's thread safety for indicator trait objects.
- **`f64::from_bits(1)` as sentinel**: Used instead of `Option` for uninitialized values — obscure and error-prone.
- **Marketing-focused README**: Contact info (Telegram, WhatsApp, Discord) and "implementation assistance" — contract dev shop, not community project.
- **Repo deleted**: Original Novus-Tech-LLC repo now 404. Only accessible via forks.

### Relationship to Rust Bot (0xNoSystem, #9)

Both share the same DNA:
- Same custom `hyperliquid_rust_sdk` fork (0xNoSystem's branch)
- Same `kwant` indicators library (0xNoSystem's Indicators_rs)
- Similar architectural patterns (bot/market/executor/strategy/signal modules)
- Similar async/tokio patterns, channel communication

But the Novus version is **significantly less mature**:
| Aspect | Novus (1.47) | 0xNoSystem (2.84) |
|--------|-------------|-------------------|
| Auth | None | EIP-191 + JWT + nonce |
| Key storage | Plaintext .env | AES-256-GCM encrypted |
| Strategy | Hardcoded RSI scalp | User-written Rhai DSL |
| Database | None (in-memory) | PostgreSQL |
| Multi-user | No | Yes |
| Error handling | 32 panics | Result<T, E> throughout |
| Backtesting | Skeleton only | Multi-exchange, functional |
| License | None | Not specified |

The Novus bot appears to be an earlier/simpler version built on 0xNoSystem's libraries, published by a different team as a commercial offering. The 0xNoSystem version is the evolved form.

### Recommendations
- **Avoid** — do not use, even for reference. The 0xNoSystem Rust Bot (#9) is strictly superior in every dimension and shares the same libraries.
- If anything here is of interest: the multi-market channel architecture and indicator configuration patterns are worth studying, but they exist in better form in #9.
- The only unique element is the `enginetest.rs` interactive test harness, which demonstrates a pattern for manual strategy testing.
