# Hyperliquid Open-Source Bot Catalog

## Summary

| # | Name | Repo | Lang | Strategy | Tier | Status |
|---|------|------|------|----------|------|--------|
| 1 | Passivbot | enarjord/passivbot | Python/Rust | Market-making, contrarian grid | 1 | **3.83** |
| 2 | Hummingbot | hummingbot/hummingbot | Python | Market-making platform | 1 | **4.18** |
| 3 | Chainstack Grid Bot | chainstacklabs/hyperliquid-trading-bot | Python | YAML grid trading | 1 | **3.60** |
| 4 | HyperLiquidAlgoBot | SimSimButDifferent/HyperLiquidAlgoBot | JS/Python | Bollinger+RSI+ADX, ML | 2 | **2.39** |
| 5 | Copy Trader | MaxIsOntoSomething/Hyperliquid_Copy_Trader | Python | WebSocket copy trading | 2 | **2.84** |
| 6 | Copy Trading Bot | gamma-trade-lab/Hyperliquid-Copy-Trading-Bot | TS/Node | Copy trading w/ risk params | 2 | **2.87** |
| 7 | Grid Bot | SrDebiasi/hyperliquid-grid-bot | JS/Node | Spot grid trading | 2 | **2.47** |
| 8 | Market Maker | Novus-Tech-LLC/Hyperliquid-Market-Maker | Rust/React | RSI scalping (mislabeled) | 2 | **1.47** |
| 9 | Rust Bot | 0xNoSystem/hyperliquid_rust_bot | Rust/React | Rhai DSL platform | 2 | **2.84** |
| 10 | Drift Arbitrage | rustjesty/hyperliquid-drift-arbitrage-bot | Python | Cross-exchange arb | 2 | **2.70** |
| 11 | AI Trading Bot | hyperliquid-ai-trading-bot/hyperliquid-ai-trading-bot | Python | AI-powered (claims) | 3 | Not started |
| 12 | Hypercopy-xyz | artiya4u/hypercopy-xyz | — | Copy trading | 3 | Not started |
| 13 | LSTM Bot | redm3/HYPERLIQUID | Python | LSTM ML | 3 | Not started |
| 14 | AI Crypto Bot | wen82fastik/ai-crypto-cryptocurrency-trading-bot | Python | Multi-exchange AI | 3 | Not started |
| 15 | Bybit-HL Arb | Jackhuang166/hyberliquid-arbitrage | Rust | Price gap tracking | 3 | Not started |
| 16 | Rust Bot (RUBE40) | RUBE40/hyperliquid-trading-bot-rust | Rust | Multi-market perps | 3 | Not started |
| 17 | Rust Bot (0xTan) | 0xTan1319/hyperliquid-trading-bot-rust | Rust | Automated trading | 3 | Not started |
| 18 | Telegram Info Bot | aggstam/telegram-bot-hyperliquid | Python | Info retrieval (not trading) | 3 | Skipped — not a trading bot |

### Phase 5 expanded-search batch (2026-04-21)

| # | Name | Repo | Lang | Strategy / Purpose | Score |
|---|------|------|------|--------------------|-------|
| 19 | **hypersdk** | infinitefield/hypersdk | Rust | Community Rust SDK (full HIP-3/HIP-4/multisig/EVM) | **4.34** |
| 20 | **go-hyperliquid** | sonirico/go-hyperliquid | Go | Community Go SDK | **3.95** |
| 21 | **freqtrade-titouan** | titouannwtt/freqtrade-fork | Python | Freqtrade HL fork with liquidation detection + hyperopt samplers | **3.75** |
| 22 | **XEMM Pacifica-HL** | djienne/XEMM_CROSS_EXCHANGE_MARKET_MAKING_PACIFICA_HYPERLIQUID | Rust | Cross-exchange MM: make on Pacifica, hedge on HL | **3.53** |
| 23 | OctoBot MM | Drakkar-Software/OctoBot-Market-Making | Python | MM plugin for OctoBot framework | 2.86 |
| 24 | Hyper-Alpha-Arena | HammerGPT/Hyper-Alpha-Arena | Python | LLM multi-agent trading platform | 2.81 |
| 25 | Nova funding hub | SoYuCry/Nova_funding_hub | Python | Multi-DEX funding-rate aggregator (no execution) | 2.80 |
| 26 | Avellaneda MM | djienne/AVELLANEDA_MARKET_MAKING_FREQTRADE | Python | Avellaneda-Stoikov MM on Freqtrade | 2.59 |

### Phase 5b honorable-mentions batch (2026-04-22)

Static eval only (no testnet trials). Parallel sub-agent evaluations. See `evaluations/{hyperopen,senpi-skills,vnpy-hyperliquid,memlabs-hl-bot,redm3-lstm,xlev-hl-bot}/evaluation.md`.

| # | Name | Repo | Lang | Strategy / Purpose | Score |
|---|------|------|------|--------------------|-------|
| 27 | **hyperopen** | thegeronimo/hyperopen | ClojureScript | HL trading UI (perps+vaults+portfolio). Not a bot — frontend | **3.94** |
| 28 | **senpi-skills** | Senpi-ai/senpi-skills | Python | 52+ strategy "animals" behind Senpi's closed runtime — not OSS-runnable | **3.79** |
| 29 | **vnpy-hyperliquid** | Macrohegder/vnpy-hyperliquid | Python | HL gateway for VeighNa (vnpy) — 1-day old, mainnet-hardcoded | **3.00** |
| 30 | memlabs-hl-bot | memlabs-research/hyperliquid-trading-bot | Python | Linear-regression scalper, every-bar churn | 2.71 |
| 31 | redm3-lstm | redm3/HYPERLIQUID | Python | LSTM on 2023 CSV, inference-at-import — toy | 1.06 |
| 32 | **xlev-hl-bot** (MALWARE) | xlev-v/Hyperliquid-Trading-Bot | PowerShell | **Wallet drainer** — `iwr...\|iex` + private-key dotenv. 79 stars. Do not clone | **0.23** |

Tier 3 bots skipped with written rationale (see `docs/phase5-synthesis.md` §1): AI Trading Bot, Hypercopy-xyz, AI Crypto Bot, Bybit-HL Arb, Rust Bot (RUBE40), Rust Bot (0xTan), Telegram Info Bot. (LSTM Bot moved from skipped → evaluated as redm3-lstm in 5b.) Reasons: hype-driven wrappers, duplicates of already-reviewed patterns (3rd copy trading, 3rd/4th Rust bot), or non-trading (Telegram info).

**Reference**: hyperliquid-dex/hyperliquid-python-sdk (official SDK, baseline) — **Evaluated 2026-03-29** | Stars: 1,489 | Forks: 512 | MIT | v0.22.0 (Feb 2026) | Score: 3.73

---

## Tier 1 — Well-established, actively maintained

### 1. Passivbot
- **Repo**: https://github.com/enarjord/passivbot
- **Language**: Python + Rust (optimizer)
- **Strategy**: Market-making with contrarian grid. Creates and cancels limit orders on perpetual futures. Long positions: enters below price, short positions: enters above price.
- **Key features**: Evolutionary algorithm optimizer, built-in backtester, multi-exchange (Bybit, Bitget, OKX, GateIO, Binance, Kucoin, Hyperliquid), extensive wiki documentation
- **License**: Unlicense (public domain)
- **Stars**: 1,900 | Forks: 639 | Contributors: 46
- **Commits**: 7,688 on main
- **Created**: Well-established, active through v7.8.5 (March 2025)
- **HL support**: Via CCXT abstraction. HIP-3 stock perps, vault accounts, custom price rounding. No official SDK. No testnet support.
- **Security notes**: Audited 2026-04-01. Plaintext api-keys.json, custom endpoint override lacks URL validation. Zero vulns in live deps.
- **Evaluation priority**: 3rd (after SDK baseline and Chainstack) — **Evaluated 2026-04-01** | Score: 3.83

### 2. Hummingbot
- **Repo**: https://github.com/hummingbot/hummingbot
- **Website**: https://hummingbot.org
- **Language**: Python
- **Strategy**: Market-making platform with multiple strategy types. HL perp and spot connectors.
- **Key features**: Institutional-grade, Hyperliquid Foundation sponsorship, HIP-3 market support, funding rate arbitrage, vault creation
- **License**: Apache-2.0
- **Stars**: 17,896 | Forks: 4,563 | Contributors: 100+
- **Commits**: Active (last HL connector: Feb 2026)
- **HL support**: Dual spot + perp connectors with custom EIP-712 signing. HIP-3 markets, vault support, API wallet mode, TPSL, testnet, candle feeds, rate oracle. Broker ID: HBOT.
- **Security notes**: Audited 2026-04-01. AES-CTR encrypted keyfiles (best key mgmt of all bots). Pydantic SecretStr. No custom endpoint overrides. Nonce divergence between spot/perp auth (spot has thread-safe NonceManager, perp does not).
- **Evaluation priority**: 4th (large codebase, focus on HL connector) — **Evaluated 2026-04-01** | Score: 4.18

### 3. Chainstack Grid Bot
- **Repo**: https://github.com/chainstacklabs/hyperliquid-trading-bot
- **Language**: Python
- **Strategy**: YAML-configurable grid trading. Maintains buy/sell order grid within a price band. Auto-rebuilds grid if price exits band.
- **Key features**: Real-time WebSocket price streams, account state management, configurable risk management (SL/TP/max drawdown — disabled by default), testnet-first design, pre-configured BTC conservative strategy
- **License**: Apache-2.0
- **Stars**: 49, Forks: 22
- **Commits**: 43 on main
- **Created**: August 2025
- **HL support**: Uses official hyperliquid-python-sdk. REST API + WebSocket.
- **Package manager**: `uv`
- **Security notes**: Pre-audit. Corporate-backed (Chainstack). All exit strategies disabled by default. Good .env practices documented.
- **Tutorials**: [Build a Hyperliquid Trading Bot](https://chainstack.com/how-to-build-a-hyperliquid-trading-bot/), [Testnet Faucet](https://chainstack.com/hyperliquid-faucet/)
- **Evaluation priority**: 2nd (simplest Tier 1, uses official SDK, good starting point)

---

## Tier 2 — Focused, reasonable quality

### 4. HyperLiquidAlgoBot
- **Repo**: https://github.com/SimSimButDifferent/HyperLiquidAlgoBot
- **Language**: JavaScript (all source is .js despite TS deps). HTML is backtesting output.
- **Strategy**: Bollinger Bands + RSI + ADX indicators for automated trading, 15-minute timeframes or less
- **Key features**: Backtesting framework, ML optimization framework (non-functional — uses Math.random() for features), performance visualization
- **License**: MIT
- **Stars**: 44
- **Contributors**: 2 (SimSimButDifferent + dependabot)
- **Commits**: Last 2026-01-22. Single merged PR (dependabot).
- **HL support**: Uses `hyperliquid` npm package (unofficial community SDK). Custom integration in `src/hyperliquid/` (marketInfo.js, trade.js, websocket.js). Inconsistent testnet handling.
- **Security notes**: Audited 2026-04-01. Private key via .env (not encrypted). Market orders use GTC limits (dangerous). Repurposed from dYdX bot (unused deps remain). No tests. 0 vulnerabilities in deps.
- **Evaluation priority**: 1st Tier 2 bot — **Evaluated 2026-04-01** | Score: 2.39

### 5. Hyperliquid Copy Trader
- **Repo**: https://github.com/MaxIsOntoSomething/Hyperliquid_Copy_Trader
- **Language**: Python
- **Strategy**: Mirrors trades from any wallet in real-time. Automatic position sizing based on account balance ratio.
- **Key features**: WebSocket real-time trading, integer leverage, market/limit orders, Telegram notifications (7 commands + hourly reports), dry-run mode (default on), proportional/fixed sizing, blocked assets, entry quality checks
- **License**: MIT
- **Stars**: N/A | Contributors: 1 (MaxIsOntoSomething)
- **Commits**: 1 visible (shallow clone). Last: 2026-01-15.
- **HL support**: Custom HTTP with EIP-712 signing (not official SDK). REST + WebSocket (userEvents, trades, allMids). No testnet support.
- **Security notes**: Audited 2026-04-02. 29 vulns in deps (aiohttp 3.9.1, requests 2.31.0). Dockerfile bakes .env into image. Live trading path likely broken (incorrect API payload format). Dry-run hardcoded to True in main.py. Good risk management design.
- **Evaluation priority**: 2nd Tier 2 bot — **Evaluated 2026-04-02** | Score: 2.84

### 6. Hyperliquid Copy Trading Bot
- **Repo**: https://github.com/gamma-trade-lab/Hyperliquid-Copy-Trading-Bot
- **Language**: TypeScript/Node.js
- **Strategy**: Copy trading — mirrors target wallet fills via WebSocket, proportional sizing by equity ratio
- **Key features**: Equity-ratio position sizing, Zod config validation, custom error hierarchy with retry/backoff, WebSocket auto-reconnect, health check drift detection, Telegram notifications (7 types), winston rotating logs (5 categories), dry-run mode
- **License**: MIT
- **Stars**: N/A | Contributors: 1 (gamma-trade-lab)
- **Commits**: 1 ("Update README.md") on 2026-03-09. Code dump.
- **HL support**: References `@nktkas/hyperliquid` community SDK but integration is speculative — `any` types everywhere, constructor params guessed, comments say "adjust based on actual SDK." Would likely fail on first run. No official SDK. Testnet flag with different URLs.
- **Security notes**: Audited 2026-04-02. 0 dep vulns but no lock file (gitignored). `.env.example` is from a completely different project (Solana/Twitter/Discord/GROQ keys). DRY_RUN defaults to false. `capPositionSize` has unit mismatch (base units vs USD).
- **Evaluation priority**: 3rd Tier 2 bot — **Evaluated 2026-04-02** | Score: 2.87

### 7. Hyperliquid Grid Bot
- **Repo**: https://github.com/SrDebiasi/hyperliquid-grid-bot
- **Language**: JavaScript/Node.js (catalog previously listed Python — corrected)
- **Strategy**: Spot grid trading — volatility harvesting with limit orders across configurable price range. Buy low, sell high repeatedly. Spot-only, no leverage.
- **Key features**: Fastify web dashboard with TradingView charts, PostgreSQL persistence (Sequelize ORM), multi-instance support, built-in backtester (Binance klines), reserve order system (capital blocking), cleanup logic, rebuy/compounding, Telegram notifications, healthchecks.io uptime monitoring, PM2 process management, Docker deployment
- **License**: Not specified in package.json
- **Stars**: N/A | Contributors: 1 (SrDebiasi)
- **Commits**: 1 ("Fix formatting in README for dashboard view link"). Code dump.
- **HL support**: Uses `@nktkas/hyperliquid` community SDK (v0.31.0). Well-wrapped HyperliquidAdapter (647 lines). Spot pairs only (no perps). WebSocket for aggregate trades. Testnet flag with correct URLs.
- **Security notes**: Audited 2026-04-02. **Critical**: private keys stored plaintext in PostgreSQL. Unauthenticated REST API with wildcard CORS accepts key uploads. Docker entrypoint sets PostgreSQL trust auth (`host all all 0.0.0.0/0 trust`). Mass assignment vulnerability in API endpoints. 0 dep vulnerabilities. Testnet defaults to off.
- **Evaluation priority**: 4th Tier 2 bot — **Evaluated 2026-04-02** | Score: 2.47

### 8. Hyperliquid Market Maker
- **Repo**: https://github.com/Novus-Tech-LLC/Hyperliquid-Market-Maker (404 — recovered from fork [nvampx/Hyperliquid-Market-Maker](https://github.com/nvampx/Hyperliquid-Market-Maker))
- **Language**: Rust (~1,595 LOC) + React/TypeScript (frontend)
- **Strategy**: RSI-based scalping (mislabeled as "market maker"). RSI + StochRSI + SMA-on-RSI with configurable risk levels. Time-based exits (420s fixed duration). Perps-only, market orders with 1% slippage.
- **Key features**: Multi-market async orchestration (per-asset signal engine + executor), 7 indicator types via `kwant` library, React web dashboard with real-time WebSocket updates, margin allocation system, 200+ perp assets cataloged
- **License**: **None** (cannot legally use or redistribute)
- **Stars**: 37 | Forks: 18 | Contributors: 1 (novustch)
- **Commits**: 7 (all on 2025-10-15, code dump + 1 README update 2025-11-18)
- **HL support**: Custom fork of `hyperliquid_rust_sdk` (0xNoSystem's branch, same as #9). InfoClient + ExchangeClient + WebSocket. Market orders only. **No testnet** (hardcoded mainnet). No Cargo.lock.
- **Security notes**: Audited 2026-04-02. 32 unwrap/panic/expect calls including `panic!("THIS IS INSANE")` on exchange data. No Cargo.lock. 90% margin per trade with no stop-loss. All state in-memory (lost on crash). `unsafe impl Send`. No API auth, wildcard CORS. Published by contract dev shop (Novus-Tech-LLC, Telegram/WhatsApp contacts). Shares 0xNoSystem's libraries but is significantly less mature than #9.
- **Evaluation priority**: 5th Tier 2 bot — **Evaluated 2026-04-02** | Score: 1.47 (Avoid)

### 9. Hyperliquid Rust Bot
- **Repo**: https://github.com/0xNoSystem/hyperliquid_rust_bot
- **Language**: Rust (~11,300 LOC) + React/TypeScript (web UI)
- **Strategy**: Multi-user SaaS trading platform with Rhai scripting DSL. User-written strategies via `on_idle`/`on_open`/`on_busy` hooks. Signal engine state machine (Idle → Armed → Opening → Open → Closing). Perps-only.
- **Key features**: EIP-191 wallet auth + JWT, AES-256-GCM encrypted agent keys, Rhai scripting with sandbox limits, multi-exchange backtester (Binance/Bybit/MEXC/HTX/Coinbase), PostgreSQL persistence, React web dashboard, per-user margin allocation, WebSocket live updates, PM2-style process management
- **License**: Not specified
- **Stars**: N/A | Contributors: 1 (0xNoSystem)
- **Commits**: 1 ("make default strategy editor view only"). Code dump.
- **HL support**: Custom fork of `hyperliquid_rust_sdk`. InfoClient + ExchangeClient + WebSocket (UserEvents, Candles). Market + limit orders, cancel, leverage. Perps only, no spot. **No testnet support** (hardcoded mainnet).
- **Security notes**: Audited 2026-04-02. Best security architecture of Tier 2: AES-256-GCM encrypted keys at rest, EIP-712 agent approval, JWT auth, nonce replay prevention. Concerns: keys in memory not zeroed, custom SDK fork (supply chain), Rhai eval() may be accessible, no rate limiting. 0 dep vulns (deferred). Zero documentation, zero tests.
- **Evaluation priority**: 5th Tier 2 bot — **Evaluated 2026-04-02** | Score: 2.84

### 10. Hyperliquid-Drift Arbitrage Bot
- **Repo**: https://github.com/rustjesty/hyperliquid-drift-arbitrage-bot
- **Language**: Python (catalog previously listed Rust — corrected; author handle "rustjesty" caused confusion)
- **Strategy**: Cross-exchange arbitrage between Drift Protocol (Solana) and Hyperliquid perpetuals. Two strategies: basis (price discrepancy) and funding rate (rate spread). Long on cheaper exchange, short on more expensive. Atomic execution with rollback on partial fill.
- **Key features**: Abstract connector pattern (Drift + Hyperliquid), Pydantic config validation with env var fallback, execution engine with safe-mode failover, JSONL trade/opportunity logging, dry-run mode, pytest test suite (637 lines), MIT license
- **License**: MIT
- **Stars**: N/A | Contributors: 1 (rustjesty / soljesty)
- **Commits**: 1 ("refac: engine.py by https://t.me/soljesty"). Code dump.
- **HL support**: Uses `hyperliquid-python-sdk` (official, unpinned). Limit orders, cancel, order book, funding rates, position tracking. REST only (no WebSocket). No testnet docs.
- **Security notes**: Audited 2026-04-02. **42 dependency vulnerabilities** (aiohttp 16 CVEs, urllib3 9, certifi 4, protobuf 2). Keys from env vars (correct separation). Drift hardcoded to mainnet. Fill detection via position polling (not truly atomic). Best test coverage of Tier 2 (637 lines pytest).
- **Evaluation priority**: 7th Tier 2 bot — **Evaluated 2026-04-02** | Score: 2.70

---

## Tier 3 — Experimental / red flags

### 11. AI Trading Bot
- **Repo**: https://github.com/hyperliquid-ai-trading-bot/hyperliquid-ai-trading-bot
- **Language**: Python
- **Claims**: Fully autonomous, connects any LLM (ChatGPT, DeepSeek, Qwen, Gemini, Grok)
- **RED FLAGS**: Heavily keyword-stuffed descriptions. Lists every possible bot type (arbitrage, scalping, market making, signal bot, quant trader). Suspicious marketing. Possible honeypot/scam.
- **Recommendation**: Code-only audit. Never run.

### 12. Hypercopy-xyz
- **Repo**: https://github.com/artiya4u/hypercopy-xyz
- **Description**: Copy trading service, self-described as "hyper stupid"
- **RED FLAGS**: Proof-of-concept stage, minimal documentation.

### 13. LSTM Bot
- **Repo**: https://github.com/redm3/HYPERLIQUID
- **Language**: Python
- **Strategy**: LSTM machine learning Bitcoin trading
- **RED FLAGS**: Limited documentation. Research/experimental only.

### 14. AI Crypto Trading Bot
- **Repo**: https://github.com/wen82fastik/ai-crypto-cryptocurrency-trading-bot
- **Language**: Python
- **Claims**: Multi-exchange (25+ exchanges), LLM agents, copy trading, arbitrage, DCA, grid, scalping, backtesting
- **RED FLAGS**: Feature bloat. Claims too many features for a single project = likely shallow implementations.

### 15. Bybit-HL Arbitrage
- **Repo**: https://github.com/Jackhuang166/hyberliquid-arbitrage
- **Language**: Rust
- **Strategy**: Price gap tracking between Bybit and Hyperliquid with real-time alerts
- **Notes**: Alert-only, not auto-trading. Limited scope.

### 16. Rust Bot (RUBE40)
- **Repo**: https://github.com/RUBE40/hyperliquid-trading-bot-rust
- **Language**: Rust
- **Strategy**: Multi-market perpetual trading with customizable strategies
- **Notes**: Limited information available.

### 17. Rust Bot (0xTan)
- **Repo**: https://github.com/0xTan1319/hyperliquid-trading-bot-rust
- **Language**: Rust
- **Strategy**: Automated trading
- **Notes**: Limited information available.

### 18. Telegram Info Bot
- **Repo**: https://github.com/aggstam/telegram-bot-hyperliquid
- **Language**: Python
- **Strategy**: Not a trading bot — retrieves Hyperliquid information via Telegram
- **Notes**: Utility only. May be useful as a monitoring companion.
