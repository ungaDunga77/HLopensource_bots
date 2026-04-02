# Evaluation: Hyperliquid Grid Bot (SrDebiasi)

**Repo**: https://github.com/SrDebiasi/hyperliquid-grid-bot
**Evaluator**: Claude
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 1 | Private key stored in **plaintext in PostgreSQL** (`trade_instances.private_key VARCHAR(255)`). API endpoint (`PUT /trade-instance/:id/secrets`) accepts private keys over HTTP with **no authentication**. Docker entrypoint auto-generates `.env` with default `postgres/postgres` credentials. .env + .gitignore present, docs warn. |
| A2 | Dependency hygiene | 3 | 0 known vulnerabilities. `package-lock.json` present (unlike Copy Trading Bot). 21 runtime deps — moderate count. All use `^` ranges but lock file provides reproducibility. No dependabot/renovate. |
| A3 | Network surface | 2 | Fastify web server with `origin: true, credentials: true` CORS — **any origin can make authenticated requests**. Also: Hyperliquid API, Telegram API, Binance API (klines for backtest), healthchecks.io ping. All are documented/expected, but the open web server is the main concern. |
| A4 | Code transparency | 3 | Clear JavaScript, well-structured modules. No obfuscation. Good separation of concerns. Comments explain business logic. |
| A5 | Input validation | 1 | API endpoints accept raw `request.body` passed directly to Sequelize (`TradeOrder.create(body)`) — **mass assignment vulnerability**. No schema validation on prices, quantities, or trade parameters. Private key format only gets `0x` prefix normalization, no length/hex validation. |
| | **A average** | **2.00** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | Excellent README (400+ lines) with step-by-step grid logic, BTC example with numbers, backtest performance data, explanation of downtrend/uptrend behavior, capital protection concepts, and profit target recommendations. Best strategy docs of any Tier 2 bot. |
| B2 | Backtesting | 3 | Built-in backtester (`scripts/backtest.js`) using Binance klines. Grid simulation engine (`simulateGrid.js`, 342 lines) with per-level state tracking, fee accounting, daily reporting, and capital requirements. No optimization or out-of-sample validation. |
| B3 | Risk management | 3 | Spot-only (no leverage, no liquidation risk). Reserve order system blocks unused capital. Cleanup logic removes stale orders far from price. Configurable USD/base buffers. Rebuy logic for profit compounding. No stop-loss/take-profit, no max drawdown limit. |
| B4 | Configurability | 3 | Extensive `.env` + database-driven per-instance config. Multi-instance support (multiple coins/pairs simultaneously). Web dashboard for management. Testnet toggle. No dry-run mode. Testnet defaults to off (unsafe). |
| B5 | Monitoring | 4 | Telegram notifications via bot API. Healthchecks.io uptime monitoring with configurable ping interval. Web dashboard with TradingView charts (lightweight-charts). PM2 process management with ecosystem config. Console logging with color. |
| | **B average** | **3.60** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Zero tests. No test framework, no test files, no test scripts in package.json. |
| C2 | Error handling | 2 | Try/catch around order placement. But: **fire-and-forget DB updates** (`void updateTradeOrder().catch(...)`) create race conditions — in-memory state updated before DB persists, process restart loses order tracking. No exponential backoff on API failures (fixed 5s delay). Silent catch on Telegram message failures. No global unhandled rejection handler. |
| C3 | Documentation | 4 | Excellent README, separate docs for Docker (`README_DOCKER.md`), Telegram (`README_TELEGRAM.md`), and backtesting (`README_BACKTEST.md`). Well-documented `.env.example` with explanatory comments. Telegram group for support. |
| C4 | Code quality | 2 | Good module separation (exchange/, grid/, services/, api/, functions/). ESM modules. But: `init.js` is **1,809 lines** (god file containing entire trading loop). Plain JavaScript (no TypeScript). Only prettier configured, no linter. Two datetime libraries (luxon + moment). |
| C5 | Maintenance | 1 | Single commit ("Fix formatting in README for dashboard view link"). No CI/CD, no issues, no pull requests. Code dump. |
| | **C average** | **1.80** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 3 | Uses `@nktkas/hyperliquid` community SDK (v0.31.0). Well-encapsulated in `HyperliquidAdapter.js` (647 lines) with proper abstraction layer. Spot pair resolution via SDK metadata. More mature integration than Copy Trading Bot (typed responses, proper method calls, not guessed). |
| D2 | Testnet support | 2 | `HYPERLIQUID_TESTNET` env var, stored per-instance in DB. Correct testnet WebSocket/REST URLs. **Defaults to mainnet (0)** — unsafe default. No testnet-first docs. |
| D3 | HL features | 2 | Spot limit orders, cancel orders, open orders query, WebSocket aggregate trades subscription. **Spot-only** — intentionally does not support perps/futures. No vaults, subaccounts, or market orders (except rebuy). |
| | **D average** | **2.33** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (2.00 * 0.4) + (3.60 * 0.3) + (1.80 * 0.2) + (2.33 * 0.1)
      = 0.800 + 1.080 + 0.360 + 0.233
      = 2.47
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

The most feature-complete Tier 2 bot evaluated so far — a full-stack grid trading application with web dashboard, PostgreSQL persistence, backtester, Telegram integration, Docker deployment, and multi-instance support. The grid trading strategy is well-conceived (spot-only, no leverage, volatility harvesting) and the best-documented of any Tier 2 bot. However, the security posture is the worst we've seen: private keys stored in plaintext in the database, an unauthenticated REST API with wildcard CORS that accepts private key uploads, mass assignment vulnerabilities, and Docker defaults that set PostgreSQL to trust-all authentication. The engineering quality suffers from a 1,809-line god file, fire-and-forget database updates that create order-tracking race conditions, and zero tests. A useful reference for grid bot architecture and dashboard design, but needs fundamental security hardening before any use with real funds.

## Key Findings

### Strengths
- **Best strategy documentation of Tier 2**: Step-by-step grid logic, worked BTC example, backtest results (28.33% projected APR), up/downtrend behavior, capital protection concepts
- **Full-stack architecture**: Fastify web dashboard with TradingView charts, PostgreSQL persistence, Sequelize ORM, PM2 process management
- **Multi-instance design**: Database-driven config allows running multiple pairs/strategies simultaneously from one deployment
- **Built-in backtester**: Grid simulation engine with fee accounting, daily reporting, per-level state tracking using Binance historical klines
- **Capital protection**: Reserve order system blocks unused capital, cleanup logic removes stale orders, configurable USD/base asset buffers
- **Operational maturity**: Healthchecks.io uptime monitoring, Telegram alerts, Docker + docker-compose, PM2 ecosystem config
- **Solid SDK integration**: HyperliquidAdapter (647 lines) properly wraps `@nktkas/hyperliquid` with spot pair resolution, WebSocket management, and clean abstraction

### Concerns
- **Private keys in PostgreSQL plaintext**: `trade_instances.private_key VARCHAR(255)` — database compromise = total fund control. No encryption layer.
- **Unauthenticated API with wildcard CORS**: All endpoints open to any origin. `PUT /trade-instance/:id/secrets` accepts private keys with no auth. `POST /trade-order` has mass assignment vulnerability (`TradeOrder.create(body)` with no schema validation).
- **Docker entrypoint creates trust auth PostgreSQL**: `echo "host all all 0.0.0.0/0 trust"` — any network connection accepted without password. Auto-generates `.env` with default `postgres/postgres`.
- **Fire-and-forget database updates**: `void updateTradeOrder().catch(...)` — in-memory state updated before DB persists. Process restart = orphaned exchange orders not tracked in database.
- **1,809-line god file**: `src/functions/init.js` contains the entire trading loop, order management, cleanup, reserves, and rebuy logic. No decomposition.
- **No API rate limiting or backoff**: Fixed 5-second delay between cycles. If Hyperliquid API fails repeatedly, bot hammers it in a tight loop.
- **Zero tests**: No test infrastructure whatsoever.
- **Single commit**: Code dump with no development history.
- **Catalog discrepancy**: Listed as Python but is actually JavaScript/Node.js.

### Comparison with Chainstack Grid Bot (Tier 1, 3.60)

Both are grid trading bots for Hyperliquid, making comparison instructive:

| Aspect | SrDebiasi (2.47) | Chainstack (3.60) |
|--------|-------------------|-------------------|
| Language | JavaScript/Node.js | Python |
| SDK | Community (@nktkas) | Official SDK |
| Market type | Spot only | Perps |
| Key storage | Plaintext in DB + .env | .env only |
| Dashboard | Full web UI + charts | None |
| Backtesting | Built-in (Binance klines) | None |
| Database | PostgreSQL + Sequelize | None (stateless) |
| API security | None (open CORS) | No web API |
| Risk mgmt | Reserves + cleanup + buffers | SL/TP + max drawdown |
| Config validation | None | YAML schema |
| Tests | None | None |
| Testnet default | Off (mainnet) | On (testnet) |

Chainstack is simpler but safer: it uses the official SDK, has no web attack surface, defaults to testnet, and validates config. SrDebiasi is more feature-rich but trades security for functionality.

### Recommendations
- Do not use with real funds without fundamental security changes
- Reference the architecture: dashboard design, multi-instance database model, grid simulation engine, HyperliquidAdapter patterns
- If forking: (1) encrypt private keys at rest or use vault, (2) add API authentication + restrict CORS, (3) add input validation on all endpoints, (4) make DB updates synchronous before in-memory state changes, (5) split init.js into modules, (6) default testnet to on, (7) add tests
