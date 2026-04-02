# Tier 2 Comparative Analysis

**Date**: 2026-04-02
**Bots evaluated**: 7 (6 scored, 1 recovered from fork after repo deleted)
**Score range**: 1.47 – 2.87

---

## Rankings

| Rank | Bot | Lang | Strategy | Score | Verdict |
|------|-----|------|----------|-------|---------|
| 1 | Copy Trading Bot (gamma-trade-lab) | TS/Node | Copy trading | 2.87 | Reference only |
| 2 | Copy Trader (MaxIsOntoSomething) | Python | Copy trading | 2.84 | Reference only |
| 3 | Rust Bot (0xNoSystem) | Rust/React | Rhai DSL platform | 2.84 | Reference only |
| 4 | Drift Arbitrage (rustjesty) | Python | Cross-exchange arb | 2.70 | Reference only |
| 5 | Grid Bot (SrDebiasi) | JS/Node | Spot grid | 2.47 | Reference only |
| 6 | HyperLiquidAlgoBot (SimSimButDifferent) | JS | Bollinger+RSI scalp | 2.39 | Reference only |
| 7 | Market Maker (Novus-Tech-LLC) | Rust/React | RSI scalp (mislabeled) | 1.47 | Avoid |

No Tier 2 bot reached 3.0 ("Worth investigating"). For comparison, all four Tier 1 bots scored 3.60–4.18.

---

## Category Breakdown

### A. Security (40% weight)

| Bot | A1 Keys | A2 Deps | A3 Network | A4 Transparency | A5 Validation | Avg |
|-----|---------|---------|------------|-----------------|---------------|-----|
| Rust Bot | **4** | 3 | 3 | **4** | 3 | **3.40** |
| Drift Arb | 3 | 1 | 3 | **4** | 3 | 2.80 |
| Copy Trading | 2 | 2 | **4** | 3 | **4** | 3.00 |
| Copy Trader | 2 | 1 | 3 | 3 | 3 | 2.40 |
| HLAlgoBot | 2 | 3 | 3 | 2 | 1 | 2.20 |
| Grid Bot | 1 | 3 | 2 | 3 | 1 | 2.00 |
| Market Maker | 2 | 1 | 2 | 3 | 1 | 1.80 |

**Winner: Rust Bot (3.40)** — AES-256-GCM encrypted keys, EIP-712 agent approval, JWT auth. The only Tier 2 bot that approaches Tier 1 security levels. Hummingbot (Tier 1) scored highest overall with AES-CTR encrypted keyfiles, but the Rust Bot's agent approval flow is a more modern pattern.

**Worst: Market Maker (1.80)** — Plaintext keys, no Cargo.lock, 32 panics in critical paths, unsafe impl.

**Pattern**: Key management spans the full range (1–4). Most bots use .env + .gitignore (score 2). Only the Rust Bot encrypts at rest.

### B. Functionality (30% weight)

| Bot | B1 Strategy | B2 Backtest | B3 Risk | B4 Config | B5 Monitor | Avg |
|-----|-------------|-------------|---------|-----------|------------|-----|
| Grid Bot | **5** | 3 | 3 | 3 | **4** | **3.60** |
| Copy Trading | 4 | 0 | 4 | 4 | 4 | 3.20 |
| Rust Bot | 2 | **4** | **4** | 3 | 3 | 3.20 |
| HLAlgoBot | 3 | 2 | 2 | 2 | 2 | 2.20 |
| Drift Arb | 4 | 0 | 3 | 4 | 2 | 2.60 |
| Copy Trader | 3 | 0 | 3 | 3 | 3 | 2.40 |
| Market Maker | 2 | 0 | 1 | 2 | 2 | 1.40 |

**Winner: Grid Bot (3.60)** — Best strategy docs of any Tier 2 bot (worked BTC example, backtest results, up/downtrend behavior), full web dashboard with TradingView charts, Telegram + healthchecks.io monitoring.

**Backtesting**: Only Grid Bot (Binance klines + grid sim) and Rust Bot (multi-exchange candle fetching) have functional backtesters. HLAlgoBot has a framework but uses `Math.random()` for ML features.

**Pattern**: Strategy documentation quality doesn't correlate with code quality. The best-documented bots (Grid Bot, Copy Trading Bot) have the worst security.

### C. Engineering Quality (20% weight)

| Bot | C1 Tests | C2 Errors | C3 Docs | C4 Code | C5 Maint | Avg |
|-----|----------|-----------|---------|---------|----------|-----|
| Drift Arb | **3** | 3 | 4 | 4 | 1 | **3.00** |
| Copy Trading | 0 | **4** | 3 | 3 | 1 | 2.20 |
| Copy Trader | 0 | 2 | 3 | 3 | 1 | 1.80 |
| Grid Bot | 0 | 2 | **4** | 2 | 1 | 1.80 |
| Rust Bot | 0 | 3 | 0 | **4** | 1 | 1.60 |
| HLAlgoBot | 0 | 1 | 2 | 2 | 1 | 1.20 |
| Market Maker | 0 | 1 | 1 | 2 | 1 | 1.00 |

**Winner: Drift Arb (3.00)** — The only Tier 2 bot with actual tests (637 lines, 6 modules, pytest + pytest-asyncio, mocked deps). Also cleanest architecture (~1,450 LOC, abstract connector pattern, Pydantic config).

**Tests**: 6 out of 7 bots have zero tests. This is the single most consistent deficiency across Tier 2.

**Maintenance**: All scored 1 — single commits, code dumps, no CI/CD, no issue trackers.

**Pattern**: There's an inverse relationship between feature count and code quality. The most feature-rich bots (Grid Bot, Rust Bot) have the most sprawling codebases and the worst engineering discipline.

### D. Hyperliquid Integration (10% weight)

| Bot | D1 SDK | D2 Testnet | D3 Features | Avg |
|-----|--------|------------|-------------|-----|
| Copy Trading | 2 | 3 | 3 | 2.67 |
| Copy Trader | 2 | 2 | 3 | 2.33 |
| Grid Bot | 3 | 2 | 2 | 2.33 |
| HLAlgoBot | 2 | 2 | 2 | 2.00 |
| Rust Bot | 3 | **0** | 3 | 2.00 |
| Drift Arb | 3 | 1 | 2 | 2.00 |
| Market Maker | 2 | **0** | 2 | 1.33 |

**No clear winner.** All Tier 2 bots underperform Tier 1 on HL integration (Tier 1 avg: ~3.6).

**Testnet**: Two bots (Rust Bot, Market Maker) have zero testnet support — hardcoded to mainnet. This is the most dangerous deficiency for a trading bot. The rest have a flag but default to mainnet.

**SDK**: Three use the official `hyperliquid-python-sdk` (Drift Arb, Copy Trader via custom signing, HLAlgoBot via npm). Three use the `@nktkas/hyperliquid` community SDK (Copy Trading Bot, Grid Bot, Rust Bot via fork). One uses a custom fork of the Rust SDK (Market Maker).

---

## Cross-Cutting Findings

### 1. The Code Dump Problem

Every Tier 2 bot has 1–7 commits, all deposited in a single day. None have:
- Pull request history
- Issue trackers
- CI/CD pipelines
- Release tags or versioning
- Contributor diversity (all single-author)

This means none have undergone peer review. The code represents one person's first-pass implementation, published without iteration. This explains why scores cluster 2.0–2.9 despite diverse strategies and architectures.

### 2. Catalog Accuracy

Three out of seven had incorrect language listings:
- Grid Bot (SrDebiasi): listed Python, actually **JavaScript/Node.js**
- Market Maker (Novus): listed "Not determined", actually **Rust**
- Drift Arbitrage: listed Rust, actually **Python**

Lesson: don't trust GitHub language detection or repo descriptions. Always clone and inspect.

### 3. Strategy Diversity vs Quality

Tier 2 covers five distinct strategy types:

| Strategy | Bots | Best Reference |
|----------|------|----------------|
| Copy trading | 2 | Copy Trading Bot (architecture), Copy Trader (risk design) |
| Grid trading | 1 | Grid Bot (full-stack, but Chainstack Tier 1 is safer) |
| Indicator scalping | 2 | Rust Bot (Rhai DSL), HLAlgoBot (backtesting framework) |
| Cross-exchange arb | 1 | Drift Arb (only option, clean architecture) |
| Market making | 0 | Novus is mislabeled — no actual market making in Tier 2 |

Despite the variety, none are production-ready. The most useful are as design references for specific patterns.

### 4. Shared Ecosystem: 0xNoSystem Libraries

Two bots (#8 Market Maker, #9 Rust Bot) depend on 0xNoSystem's custom libraries:
- `hyperliquid-rust-sdk` (fork of official Rust SDK)
- `kwant` / `Indicators_rs` (technical indicator library)

The Rust Bot is the evolved form; the Market Maker is an earlier, simpler version published by a different team (Novus-Tech-LLC, a contract dev shop). This means the real ecosystem is smaller than it appears — two "independent" bots share a single developer's libraries.

### 5. Security Architecture Spectrum

| Pattern | Bots | Score Range |
|---------|------|-------------|
| Encrypted keys + auth | Rust Bot | A1: 4 |
| Env vars + validation | Drift Arb | A1: 3 |
| .env + .gitignore | Copy Trading, Copy Trader, HLAlgoBot, Market Maker | A1: 2 |
| Plaintext in database | Grid Bot | A1: 1 |

Only one bot (Rust Bot) encrypts keys at rest. The rest rely on operational discipline (.env files not committed). Grid Bot is the worst — private keys stored in plaintext PostgreSQL and exposed via an unauthenticated API.

### 6. The Test Desert

| Tests | Bots |
|-------|------|
| 637 lines (pytest) | Drift Arb |
| 0 | All others |

The Drift Arb bot's 637 lines of tests (config, connectors, strategies, engine) are the exception that proves the rule. Its tests demonstrate that testing is feasible even for a small trading bot — mocked connectors, async test patterns, strategy signal validation. The other six bots simply never invested in testing.

---

## Best-in-Class by Dimension

Each Tier 2 bot excels in exactly one area while failing in others:

| Dimension | Best Bot | What to Reference |
|-----------|----------|-------------------|
| **Security architecture** | Rust Bot (0xNoSystem) | AES-256-GCM key encryption, EIP-712 agent approval, JWT + nonce auth |
| **Strategy documentation** | Grid Bot (SrDebiasi) | Worked examples, backtest results, uptrend/downtrend behavior |
| **Testing** | Drift Arbitrage | pytest patterns for async trading bots, mocked connectors |
| **Config validation** | Drift Arbitrage | Pydantic + YAML + env var separation |
| **Error handling** | Copy Trading Bot | Custom error hierarchy with retryable classification, exponential backoff |
| **Risk management design** | Copy Trader | Entry quality checks, proportional sizing, blocked assets, Telegram controls |
| **Web dashboard** | Grid Bot (SrDebiasi) | Fastify + TradingView charts, multi-instance PostgreSQL |
| **Backtesting** | Rust Bot (0xNoSystem) | Multi-exchange klines (5 exchanges), candle aggregation, WebSocket streaming |
| **Strategy flexibility** | Rust Bot (0xNoSystem) | Rhai scripting DSL with on_idle/on_open/on_busy hooks |
| **Execution engine** | Drift Arbitrage | Atomic hedged execution, rollback on partial fill, safe-mode failover |

No single bot combines even three of these. A production bot would cherry-pick patterns from multiple sources.

---

## Tier 2 vs Tier 1 Gap Analysis

| Criterion | Tier 1 Avg | Tier 2 Avg | Gap |
|-----------|------------|------------|-----|
| A. Security | 3.30 | 2.46 | -0.84 |
| B. Functionality | 3.25 | 2.63 | -0.62 |
| C. Engineering | 2.85 | 1.80 | **-1.05** |
| D. HL Integration | 3.58 | 2.09 | **-1.49** |
| **Overall** | **3.79** | **2.52** | **-1.27** |

The biggest gaps are in **engineering quality** (-1.05) and **HL integration** (-1.49). Tier 1 bots have CI/CD, multi-contributor development, version history, and proper SDK usage. Tier 2 bots are single-author code dumps without tests or maintenance infrastructure.

The security and functionality gaps are smaller — some Tier 2 bots match or exceed individual Tier 1 bots in specific areas (e.g., Rust Bot's key encryption rivals Hummingbot's, Copy Trading Bot's error hierarchy is among the best).

---

## Recommendations for Phase 4+

### What to Carry Forward from Tier 2

None of these bots should be run on testnet. Instead, extract patterns for the eventual production bot:

1. **From Drift Arb**: Test infrastructure (pytest + async + mocks), Pydantic config, abstract connector pattern, execution engine with rollback
2. **From Rust Bot**: Key encryption (AES-256-GCM), agent approval flow, Rhai-style strategy DSL concept, multi-exchange backtester
3. **From Copy Trading Bot**: Zod/Pydantic config validation, retryable error hierarchy, structured logging categories
4. **From Copy Trader**: Telegram operational controls (pause/resume/stop), entry quality checks, proportional position sizing
5. **From Grid Bot**: Dashboard architecture (if UI needed), multi-instance database model, grid simulation engine

### What to Avoid

- Storing private keys in databases (Grid Bot)
- Unauthenticated web APIs with wildcard CORS (Grid Bot, Market Maker)
- Hardcoded mainnet without testnet option (Rust Bot, Market Maker)
- Custom EIP-712 signing that doesn't match the official SDK wire format (Copy Trader)
- Fire-and-forget database updates in trading loops (Grid Bot)
- `panic!()` in exchange data handlers (Market Maker)
- Gitignoring lock files (Copy Trading Bot)

### Phase 4 Focus

Testnet trials should focus exclusively on Tier 1 bots (Hummingbot 4.18, Passivbot 3.83, Chainstack 3.60). No Tier 2 bot is safe enough to run, even on testnet.
