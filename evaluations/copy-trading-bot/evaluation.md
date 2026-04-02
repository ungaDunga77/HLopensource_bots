# Evaluation: Hyperliquid Copy Trading Bot (gamma-trade-lab)

**Repo**: https://github.com/gamma-trade-lab/Hyperliquid-Copy-Trading-Bot
**Evaluator**: Claude
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | .env + .gitignore, README warns. BUT: `.env.example` is from a completely different project (Solana/Twitter/Discord/GROQ keys) — confusing and dangerous. Plain text private key via ethers Wallet, no encryption or vault. |
| A2 | Dependency hygiene | 2 | 0 known vulns, 8 runtime deps (reasonable). BUT: **no lock file** — `package-lock.json` is gitignored! Builds non-reproducible. All deps use `^` ranges. |
| A3 | Network surface | 4 | Only Hyperliquid API (REST + WebSocket) and Telegram API. No telemetry, no unexplained outbound calls. Endpoints documented in code. |
| A4 | Code transparency | 3 | Clean TypeScript, well-structured, extensive comments. But heavily AI-generated without evidence of actual testing. |
| A5 | Input validation | 4 | Zod schema for all config. Trade params validated before execution (blocked assets, min notional, max position size, leverage cap). DRY_RUN defaults to `false` (not safe default). |
| | **A average** | **3.00** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | Copy trading well-documented. Position sizing formula explained with numerical example. Risk management layers listed. |
| B2 | Backtesting | 0 | None. Somewhat expected for copy trading, but no historical analysis or simulation capabilities. |
| B3 | Risk management | 4 | Multiple layers: equity-ratio sizing, SIZE_MULTIPLIER, MAX_LEVERAGE cap, MAX_POSITION_SIZE_PERCENT, MIN_NOTIONAL, MAX_CONCURRENT_TRADES, BLOCKED_ASSETS, reduceOnly on closes. DRY_RUN mode available. |
| B4 | Configurability | 4 | Zod-validated .env config with comprehensive docs. Dry-run mode, testnet toggle, 14 configurable parameters. Good defaults for most. |
| B5 | Monitoring | 4 | Winston with daily rotation (5 log categories: combined, error, trading, exceptions, rejections). Telegram notifications (7 types: trade, startup, shutdown, error, health check, summary, warning). Health checks with drift detection. |
| | **B average** | **3.20** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Zero tests. tsconfig excludes `**/*.test.ts` but none exist. |
| C2 | Error handling | 4 | Custom error hierarchy (AppError > SDKError, NetworkError, WebSocketError, TradingError, ValidationError, etc.). retryWithBackoff utility with exponential backoff. WebSocket auto-reconnect. Retryable vs non-retryable classification. Telegram error alerts. |
| C3 | Documentation | 3 | Extensive README (520 lines), code comments, setup guide, troubleshooting. BUT: `.env.example` is from a different project entirely (Solana meme token bot with Twitter/Discord/GROQ keys). |
| C4 | Code quality | 3 | TypeScript strict mode, ESLint configured, modular architecture (8 source files). BUT: extensive `any` types in hyperliquidClient.ts. SDK integration is speculative (comments: "adjust based on actual SDK"). |
| C5 | Maintenance | 1 | Single commit ("Update README.md") on 2026-03-09. No CI/CD, no issues, no PRs. Code dump. |
| | **C average** | **2.20** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | References `@nktkas/hyperliquid` community SDK. BUT: integration is speculative — dynamic imports with fallback, `any` types everywhere, constructor params guessed. Comments: "Placeholder for SDK imports — adjust based on your chosen SDK." Would likely fail on first run. |
| D2 | Testnet support | 3 | TESTNET flag with different API URLs. Testnet faucet documented. DRY_RUN available but defaults to `false`. |
| D3 | HL features | 3 | WebSocket subscription for userFills, market orders, leverage management, account state queries, position tracking, health check drift detection. No vaults, subaccounts, cancel/modify, or spot support. |
| | **D average** | **2.67** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.00 * 0.4) + (3.20 * 0.3) + (2.20 * 0.2) + (2.67 * 0.1)
      = 1.200 + 0.960 + 0.440 + 0.267
      = 2.87
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

A well-architected copy trading bot on paper — good modular design, comprehensive risk management layers, solid Telegram integration, and professional error handling. However, it is almost certainly AI-generated and never actually run. The SDK integration is speculative (`any` types, guessed constructor params, "adjust imports" comments), the `.env.example` belongs to a completely different project (Solana meme token bot), there are zero tests, and the repo has a single commit. The architecture is a useful reference for copy trading design patterns, but the code cannot be trusted to work.

## Key Findings

### Strengths
- Well-designed risk management: equity-ratio sizing, leverage caps, position limits, min notional, blocked assets, concurrent trade limits
- Professional error handling hierarchy with retryable classification and exponential backoff
- Comprehensive Telegram notifications (7 types) and structured logging (5 rotating log categories)
- Zod config validation with typed schema
- Clean TypeScript architecture with sensible module separation
- Health check system that detects position drift between our and target wallets

### Concerns
- **SDK integration is speculative**: `hyperliquidClient.ts` uses `any` everywhere, dynamically imports SDK, guesses constructor params. Comments say "adjust based on actual SDK." Would not run as-is.
- **`.env.example` is from a completely different project**: Contains Solana blockchain settings, Twitter API keys, Discord tokens, GROQ API keys, Redis config — none used by this bot. Dangerous if users fill in credentials unnecessarily.
- **.gitignore excludes `package-lock.json`**: No reproducible builds, supply chain risk with `^` version ranges.
- **Zero tests**: No unit tests, integration tests, or test infrastructure.
- **Single commit, no development history**: Code dump with no iteration, review, or CI.
- **DRY_RUN defaults to `false`**: Unsafe default for a trading bot.
- **`capPositionSize` compares raw size to equity**: The function at `risk.ts:43-49` caps `calculatedSize` (base units) against `ourEquity * percent / 100` (USD) — unit mismatch. Would either over-constrain or under-constrain depending on asset price.

### Recommendations
- Do not use as-is — SDK integration will fail
- Reference the architecture patterns (risk management layers, error hierarchy, health checks) when building a copy trader
- If forking: rewrite `hyperliquidClient.ts` against the actual SDK API, fix `.env.example`, add lock file, add tests, default DRY_RUN to `true`
