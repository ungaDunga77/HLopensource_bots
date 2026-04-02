# Evaluation: HyperLiquidAlgoBot

**Repo**: https://github.com/SimSimButDifferent/HyperLiquidAlgoBot
**Evaluator**: Claude (automated)
**Date**: 2026-04-01
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | Private key via `process.env.AGENT_PRIVATE_KEY_TEST` (.env). Not encrypted, no keystore, no password. .env in .gitignore. Key passed to SDK constructor, never logged. Minimal .gitignore (3 entries). |
| A2 | Dependency hygiene | 2 | 0 known vulns. 15 runtime deps all `^` ranges. `package-lock.json` committed. Unused `@dydxprotocol/v4-client-js` and `axios` add attack surface. Dependabot active (1 merged PR). |
| A3 | Network surface | 3 | All calls via `hyperliquid` npm SDK to HL endpoints. No telemetry. `axios` imported but unused. `cdn.plot.ly` in HTML output only. No unexpected outbound. |
| A4 | Code transparency | 3 | All JavaScript, no obfuscation. MIT license. Embedded Python script in ml_optimizer (string template) is transparent. HTML files are backtest visualizations. |
| A5 | Input validation | 2 | Quantity validated (parseFloat + NaN + > 0). Price validated. No max order size. No config bounds checking. Default 20x leverage uncapped. Market orders use GTC instead of IOC (dangerous). |
| | **A average** | **2.4** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | BBRSI strategy well-documented: Bollinger+RSI+ADX with Pine Script references. Entry/exit conditions clearly coded and commented. Two strategies (BBRSI + EMA scalping). ML-enhanced variant documented. |
| B2 | Backtesting | 3 | Built-in backtester with equity curve, trade history, Sharpe, drawdown, win rate, profit factor. Liquidation modeling. ML optimizer framework. BUT: ML feature extraction uses `Math.random()` placeholders — ML component is non-functional. |
| B3 | Risk management | 2 | RiskManager class with max drawdown, Kelly criterion, anti-martingale, pyramiding, volatility adjustment. BUT: RiskManager only used in backtesting, NOT in live trading. Live has only take-profit limits, no stop loss, no max position enforcement. |
| B4 | Configurability | 3 | JSON configs (default.json, backtest.json) via `config` npm package. Configurable indicators, leverage, position size, timeframe. `testMode` flag exists but unchecked. No config validation. No dry-run mode. |
| B5 | Monitoring | 2 | Winston logger with console + file transports. Configurable log levels. Backtest HTML reports with plotly. No Telegram/Discord alerts, no dashboards. |
| | **B average** | **2.8** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | Jest in devDeps, `npm test` script, 0 test files. Zero coverage. |
| C2 | Error handling | 3 | Try/catch in all trade functions. `withRetry` with exponential backoff. SDK pool with connection timeout. Consecutive error counter (max 5). Bug: `getUserOpenOrders()` throw outside catch block. No SIGINT/SIGTERM handling. |
| C3 | Documentation | 3 | Comprehensive README (strategy, setup, usage, project structure). Config params documented. .cursorrules for AI assistants. No JSDoc. README acknowledges "not fully implemented yet." |
| C4 | Code quality | 2 | Plain JS despite TS config/deps. Entry point `src/index.ts` doesn't exist. Package named "dydx-scalping-bot." Dead imports (axios). Commented-out code throughout. ML features use Math.random(). Inconsistent testnet: `getCandles()` hardcodes mainnet, `getUserOpenPositions()` hardcodes testnet. Reasonable module separation. |
| C5 | Maintenance | 1 | Last commit: 2026-01-22 (~2 months stale). 2 contributors (author + dependabot). 1 merged PR. No CI/CD. Self-described as incomplete. |
| | **C average** | **1.8** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 3 | Uses `hyperliquid` npm package (unofficial community SDK). Proper placeOrder, cancelOrder, updateLeverage, getCandleSnapshot, getClearinghouseState. Rate limiter. SDK pool pattern. |
| D2 | Testnet support | 2 | `NETWORK_TYPE` env var controls testnet flag. BUT: `getCandles()` hardcodes mainnet, `getUserOpenPositions()` hardcodes testnet. No testnet-first docs. No separate testnet/mainnet key config. |
| D3 | HL features | 2 | Uses: limit orders, cancel, leverage, candle snapshots, user state, open orders, WS candle subscription. Missing: IOC/market orders, TPSL native, vaults, subaccounts, agent wallets, HIP-3, spot. |
| | **D average** | **2.33** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (2.4   * 0.4) + (2.8   * 0.3) + (1.8   * 0.2) + (2.33  * 0.1)
      = 0.96 + 0.84 + 0.36 + 0.233
      = 2.39
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

HyperLiquidAlgoBot is a repurposed dYdX bot with a well-documented Bollinger+RSI+ADX strategy and an ambitious but non-functional ML optimization framework. The trading layer has critical issues: market orders sent as GTC limits, inconsistent testnet handling (candles from mainnet, positions from testnet), and risk management only present in backtesting — not in live trading. The bot self-describes as "not fully implemented yet," which is accurate.

## Key Findings

### Strengths
- Clear strategy documentation with Pine Script references
- Built-in backtester with comprehensive metrics (Sharpe, drawdown, win rate)
- Rate limiting and retry logic with exponential backoff
- RiskManager class with advanced features (Kelly criterion, anti-martingale, pyramiding)
- Good module separation (strategy, HL integration, backtesting, application)

### Concerns
- **Market orders use GTC limits** — orders can sit on the book indefinitely
- **Testnet handling inconsistent** — getCandles() hardcodes mainnet, getUserOpenPositions() hardcodes testnet
- **Repurposed without cleanup** — dYdX name, deps, and missing entry point
- **ML optimization non-functional** — feature extraction uses Math.random() placeholders
- **RiskManager not used in live trading** — no stop loss, no max position enforcement in production
- **Zero tests** despite Jest configuration
- **Bug**: getUserOpenOrders() has throw outside catch block
- **Incomplete**: README says "not fully implemented yet"

### Recommendations
- Reference the backtesting framework design and RiskManager class (well-structured)
- Do not use for live trading without major rewrites
- The BBRSI strategy logic itself is reasonable — could be extracted and reused
