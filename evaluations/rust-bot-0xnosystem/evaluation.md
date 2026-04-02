# Evaluation: Hyperliquid Rust Bot (0xNoSystem)

**Repo**: https://github.com/0xNoSystem/hyperliquid_rust_bot
**Evaluator**: Claude
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | **Best of any Tier 2 bot.** Agent private keys encrypted at rest with AES-256-GCM (master key from env). EIP-712 agent approval flow — user signs with Metamask, server never sees user's main private key. Nonce-based challenge-response prevents replay. 6-month agent validity with expiration. Keys never transmitted to frontend. Weaknesses: master key in env var (not a secret manager), decrypted keys in memory not zeroed (`zeroize` crate not used). |
| A2 | Dependency hygiene | 3 | Cargo.lock present. 31 direct deps, 657 total (large tree). 0 known vulns (cargo audit deferred). Two custom git forks (`hyperliquid_rust_sdk`, `kwant`) — supply chain trust on author's branches. No dependabot/renovate. |
| A3 | Network surface | 3 | Hyperliquid API (trading), Binance/Bybit/MEXC/HTX/Coinbase (backtest klines), Axum web server. All documented and expected. No telemetry. Hardcoded mainnet endpoint (`https://api.hyperliquid.xyz/exchange`) without certificate pinning. |
| A4 | Code transparency | 4 | Well-structured Rust with clear module boundaries. Type safety enforced by compiler. No obfuscation. Good separation of concerns. ~11,300 LOC of readable Rust. |
| A5 | Input validation | 3 | Strategy scripts compiled before persistence (syntax checked). Rhai sandbox limits: max 100k operations, expression depth 64, string size 4KB, array size 1024. Signature format validated (65 bytes, v normalization). Address parsed via Alloy. Backtest params validated. Concern: Rhai `eval()` may be available in stdlib. Some SQL error messages leak internal details. |
| | **A average** | **3.40** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 2 | README is 2 lines: "Migrating to multi user app / README coming soon." The Rhai DSL strategy system (`on_idle`, `on_open`, `on_busy` hooks) is powerful but entirely undocumented externally. Strategy logic exists in code and default strategies in the editor, but a user cloning this repo has no guidance. |
| B2 | Backtesting | 4 | Multi-exchange kline fetching (Binance, Bybit, MEXC, HTX, Coinbase). Spot + futures support. Rate-limited with exponential backoff. Candle aggregation across timeframes. WebSocket streaming of backtest progress. No out-of-sample validation or optimization. |
| B3 | Risk management | 4 | Leverage clamped to exchange max per asset. Free margin validation before order placement. Position consistency checks (can't open long while short). Armed state with timeout before entry. Reduce-only TP/SL triggers. Min order value validation ($10). Per-user margin allocation across assets. No max drawdown limit. |
| B4 | Configurability | 3 | Rhai scripting DSL = ultimate configurability (user-written trading logic). Per-asset strategy assignment, indicator selection, timeframe selection. Web UI for all management. No dry-run mode. **No testnet support** (hardcoded mainnet). |
| B5 | Monitoring | 3 | WebSocket live updates to web dashboard. Trades persisted in PostgreSQL with P&L tracking. env_logger for server-side logging. No Telegram/Discord/email alerts. No external uptime monitoring. |
| | **B average** | **3.20** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | `ci.sh` runs `cargo test` but no test files found in source. Zero tests. |
| C2 | Error handling | 3 | `Result<T, Error>` throughout with comprehensive error enum (from SDK). API endpoints return meaningful HTTP status codes, no stack traces exposed. User-facing error messages appropriate. Some `unwrap()`/`expect()` calls remain (e.g., `address.parse().unwrap()`, `expect("noop script must compile")`). No circuit breaker pattern. |
| C3 | Documentation | 0 | README is 2 lines. No setup guide, no usage docs, no API docs, no architecture docs, no troubleshooting. For a complex multi-user platform with PostgreSQL, Rhai scripting, EIP-712 auth, and React frontend, this is a critical gap. |
| C4 | Code quality | 4 | Well-structured Rust with proper module separation (signal/, exec/, backtest/, backend/, broadcast/). Async/await throughout with tokio. Type safety via Rust's ownership system. Rhai domain types prevent invalid orders. Some dead code (`#[allow(unused_variables)]`), clone overhead in async spawns. No linting config visible. Best code quality of any Tier 2 bot. |
| C5 | Maintenance | 1 | Single commit ("make default strategy editor view only"). No CI/CD pipeline, no issues, no PRs. Code dump. |
| | **C average** | **1.60** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 3 | Custom fork of `hyperliquid_rust_sdk`. InfoClient (candles, user state, positions, margins), ExchangeClient (order, market_open, cancel, leverage), WebSocket (UserEvents: fills + funding, Candle subscriptions). Well-integrated but fork = supply chain risk and may lag upstream. |
| D2 | Testnet support | 0 | **No testnet support.** `BaseUrl::Mainnet` hardcoded. EIP-712 domain uses chainId=1 (Ethereum mainnet). No environment variable to switch. |
| D3 | HL features | 3 | Market + limit orders, cancel, leverage management, user events WebSocket (fills + funding), candle subscriptions, positions, margins. No vaults, subaccounts, or spot support. Perps-only. |
| | **D average** | **2.00** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.40 * 0.4) + (3.20 * 0.3) + (1.60 * 0.2) + (2.00 * 0.1)
      = 1.360 + 0.960 + 0.320 + 0.200
      = 2.84
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

By far the most technically sophisticated Tier 2 bot — a full multi-user SaaS trading platform with EIP-191 wallet authentication, AES-256-GCM encrypted key storage, Rhai scripting DSL for custom strategies, multi-exchange backtesting, PostgreSQL persistence, and a React web dashboard. The security architecture (agent approval via EIP-712 signatures, encrypted keys, JWT auth, nonce replay prevention) is the best of any Tier 2 bot and approaches Tier 1 quality. The Rust codebase is well-structured with proper error handling and type safety. However, the bot is crippled by zero documentation (README says "coming soon"), zero tests, no testnet support (hardcoded to mainnet), and a single commit. It's clearly an active work-in-progress that was open-sourced prematurely. A valuable reference for Rust trading bot architecture and Hyperliquid integration patterns, but unusable without significant effort to understand and deploy.

## Key Findings

### Strengths
- **Best security architecture of Tier 2**: AES-256-GCM encrypted keys at rest, EIP-712 agent approval (user signs with wallet, server generates agent key), JWT auth with nonce replay prevention, per-user data isolation
- **Rhai scripting DSL**: User-written trading strategies with `on_idle`/`on_open`/`on_busy` hooks, pre-registered domain types (Side, Intent, Price, Triggers), sandbox limits (100k operations, depth 64)
- **Signal engine state machine**: Idle → Armed → Opening → Open → Closing, with timeout handling and force-cancel logic
- **Multi-exchange backtester**: Binance, Bybit, MEXC, HTX, Coinbase klines with rate limiting, exponential backoff, spot+futures, candle aggregation
- **Rust type safety**: Compiler-enforced ownership prevents data races, null pointers. ~11,300 LOC of well-structured async Rust
- **Multi-user architecture**: Per-user strategies, margin allocation, trade history, WebSocket broadcasting to multiple devices
- **Risk management**: Leverage clamping, free margin checks, position consistency, armed state with timeout, reduce-only TP/SL, min order value validation

### Concerns
- **Zero documentation**: README is "Migrating to multi user app / README coming soon." No setup, no usage, no architecture, no API docs for a complex platform requiring PostgreSQL, Rhai knowledge, and wallet integration
- **No testnet support**: `BaseUrl::Mainnet` hardcoded. This is the only Tier 2 bot with absolutely no testnet capability. Dangerous for a bot that handles real keys.
- **Zero tests**: `ci.sh` calls `cargo test` but no tests exist. For a platform with this complexity, this is a serious risk.
- **Custom SDK fork**: `hyperliquid_rust_sdk` from author's branch. Supply chain risk — no way to verify modifications vs upstream. May lag behind official updates.
- **Rhai sandbox concerns**: `eval()` may be accessible in Rhai stdlib. User scripts compiled and executed server-side — DoS or information disclosure possible despite sandbox limits.
- **In-memory key exposure**: Decrypted `PrivateKeySigner` held in memory without `zeroize`. Core dump or debugger access reveals keys.
- **Single commit code dump**: No development history, no CI/CD, no issues, no PRs.
- **Floating point for financial data**: `f64` throughout for prices, sizes, P&L. Rounding via `format!("{:.N}", value).parse()` — slow and imprecise for financial calculations.

### Comparison with Other Tier 2 Bots

| Aspect | Rust Bot (2.84) | Grid Bot SrDebiasi (2.47) | Copy Trading Bot (2.87) |
|--------|-----------------|---------------------------|-------------------------|
| Architecture | Multi-user SaaS platform | Full-stack single-user | Single-purpose copy trader |
| Key security | AES-256-GCM encrypted + EIP-712 | Plaintext in PostgreSQL | Plaintext in .env |
| Auth | JWT + EIP-191 wallet sig | None | None |
| Strategy | Rhai DSL (user scripts) | Fixed grid logic | Fixed copy logic |
| Backtesting | Multi-exchange, multi-timeframe | Binance klines, grid sim | None |
| Documentation | None (2-line README) | Excellent (4 READMEs) | Extensive |
| Tests | None | None | None |
| Testnet | None (hardcoded mainnet) | Flag (defaults off) | Flag (defaults off) |

The Rust Bot has the best technical foundations but the worst documentation. It's the opposite of Copy Trading Bot (good docs, speculative code).

### Recommendations
- Do not deploy as-is — no documentation, no testnet, zero tests
- **High-value reference** for: Rust trading bot architecture, Rhai strategy DSL design, EIP-712 agent approval flow, AES-256-GCM key management, multi-exchange backtester patterns, signal engine state machine
- If forking: (1) add testnet support (trivial — env var for BaseUrl), (2) write setup and usage docs, (3) add tests for signal engine and executor, (4) audit Rhai stdlib (disable eval), (5) add `zeroize` for private keys, (6) replace f64 with decimal type for financial data, (7) add Telegram/Discord alerts
