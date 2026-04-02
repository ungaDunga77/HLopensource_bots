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
| 7 | Grid Bot | SrDebiasi/hyperliquid-grid-bot | Python | Grid trading | 2 | Not started |
| 8 | Market Maker | Novus-Tech-LLC/Hyperliquid-Market-Maker | — | Market making | 2 | Not started |
| 9 | Rust Bot | 0xNoSystem/hyperliquid_rust_bot | Rust/React | Indicator-driven | 2 | Not started |
| 10 | Drift Arbitrage | rustjesty/hyperliquid-drift-arbitrage-bot | Rust | Cross-exchange arb | 2 | Not started |
| 11 | AI Trading Bot | hyperliquid-ai-trading-bot/hyperliquid-ai-trading-bot | Python | AI-powered (claims) | 3 | Not started |
| 12 | Hypercopy-xyz | artiya4u/hypercopy-xyz | — | Copy trading | 3 | Not started |
| 13 | LSTM Bot | redm3/HYPERLIQUID | Python | LSTM ML | 3 | Not started |
| 14 | AI Crypto Bot | wen82fastik/ai-crypto-cryptocurrency-trading-bot | Python | Multi-exchange AI | 3 | Not started |
| 15 | Bybit-HL Arb | Jackhuang166/hyberliquid-arbitrage | Rust | Price gap tracking | 3 | Not started |
| 16 | Rust Bot (RUBE40) | RUBE40/hyperliquid-trading-bot-rust | Rust | Multi-market perps | 3 | Not started |
| 17 | Rust Bot (0xTan) | 0xTan1319/hyperliquid-trading-bot-rust | Rust | Automated trading | 3 | Not started |
| 18 | Telegram Info Bot | aggstam/telegram-bot-hyperliquid | Python | Info retrieval (not trading) | 3 | Not started |

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
- **Language**: Python
- **Strategy**: Configurable grid trading with dynamic exposure tracking
- **Key features**: Weighted entry-based PnL calculations, Telegram reporting, micro-range generation for profit targeting
- **Security notes**: Pre-audit.

### 8. Hyperliquid Market Maker
- **Repo**: https://github.com/Novus-Tech-LLC/Hyperliquid-Market-Maker
- **Language**: Not determined
- **Strategy**: High-performance automated perpetual trading, market making
- **Security notes**: Pre-audit. Limited info available.

### 9. Hyperliquid Rust Bot
- **Repo**: https://github.com/0xNoSystem/hyperliquid_rust_bot
- **Language**: Rust + React/TypeScript (frontend)
- **Strategy**: Indicator-driven (RSI, StochRSI, EMA cross, ADX, ATR, SMA/EMA)
- **Key features**: Per-market timeframes, strategy presets, margin orchestration
- **Security notes**: Pre-audit. Rust code is harder to audit without Rust expertise.

### 10. Hyperliquid-Drift Arbitrage Bot
- **Repo**: https://github.com/rustjesty/hyperliquid-drift-arbitrage-bot
- **Language**: Rust
- **Strategy**: Market-neutral arbitrage between Drift Protocol (Solana) and Hyperliquid perpetuals. Long on lower-cost exchange, short on higher-cost.
- **Security notes**: Pre-audit. Cross-exchange = more complex attack surface.

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
