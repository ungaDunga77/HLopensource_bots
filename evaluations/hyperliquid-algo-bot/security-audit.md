# Security Audit: HyperLiquidAlgoBot

**Repo**: https://github.com/SimSimButDifferent/HyperLiquidAlgoBot
**Date**: 2026-04-01
**Auditor**: Claude (automated)
**Phase**: 2 (Static Audit)

---

## Automated Scan Results

### Secret Scan
- **CRITICAL**: 0
- **HIGH**: 7 (all false positives — env var reads via `process.env.AGENT_PRIVATE_KEY_TEST`)
- **MEDIUM**: 712 (mostly URLs in HTML visualization files — cdn.plot.ly in backtest output)

### Dependency Audit
- **Vulnerabilities**: 0
- **Runtime deps**: 15 (node)
- **Dev deps**: 9
- **Pinning**: All use `^` ranges, no exact pinning. `package-lock.json` committed.
- **Note**: Full npm audit deferred to Docker sandbox (requires npm install)

---

## Manual Code Review Checklist

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | No hardcoded credentials | PASS | Keys read from env vars only |
| 2 | .env/.gitignore configured | WARN | `.env` in .gitignore but .gitignore is minimal (3 entries). Doesn't cover `.env.local`, `*.pem`, `*.key`, etc. |
| 3 | Private key never logged | PASS | Grep for console.log with key/private/secret patterns: 0 matches |
| 4 | No unexpected outbound calls | PASS | All network calls via `hyperliquid` npm SDK. `axios` imported in marketInfo.js but never used (dead import). `cdn.plot.ly` in backtest HTML output only. |
| 5 | No obfuscated/minified code | PASS | All plain JavaScript |
| 6 | No suspicious post-install scripts | PASS | package.json scripts: start, test, build, lint, backtest — all standard |
| 7 | No dynamic code execution | WARN | `child_process.exec()` in ml_optimizer.js (lines 96, 628) — runs `python` with string-interpolated paths. Paths come from internal constants, not user input. Used only for ML training. |
| 8 | No unexpected filesystem access | PASS | Writes limited to backtest output files, ML model files, and logs |
| 9 | Dependencies pinned | FAIL | All `^` ranges. Dependabot active but doesn't compensate for range-based installs. |
| 10 | No dependency confusion risk | PASS | All deps are well-known public packages |
| 11 | WebSocket only to expected HL endpoints | PASS | WebSocket via `hyperliquid` SDK — delegates endpoint selection |
| 12 | Order amounts have sanity bounds | FAIL | No max order size validation. `positionSize` from config used directly without bounds checking. Default leverage: 20x. |
| 13 | Rate limiting implemented | PASS | Custom `RateLimiter` class (1 req/10s) + `withRetry` with exponential backoff for 429 errors |
| 14 | Error handling doesn't leak sensitive info | PASS | Errors logged with message only, no credential exposure |
| 15 | No subprocess with user-controlled input | PASS | `exec()` in ml_optimizer uses internal constants only |

---

## Key Security Findings

### 1. Market Orders Sent as GTC Limits (HIGH RISK)
`trade.js` "market" orders use `tif: "Gtc"` (Good-Till-Cancelled) with +-0.5% price offset:
```js
const limitPrice = parseFloat((currentPrice * 1.005).toFixed(0))  // openLong
const limitPrice = parseFloat((currentPrice * 0.995).toFixed(0))  // closeLong
```
This means a "market buy" is actually a limit order sitting on the book at +0.5% above current price. If not filled immediately, it persists indefinitely. Should use `tif: "Ioc"` (Immediate-or-Cancel) for market-like behavior.

### 2. Inconsistent Testnet Handling
- `trade.js`: Uses `process.env.NETWORK_TYPE` to set `testnet` flag
- `marketInfo.js getCandles()`: Hardcodes `testnet: false` (always mainnet)
- `marketInfo.js getUserOpenPositions()`: Hardcodes `testnet: true` (always testnet)
- This mismatch means live trading would fetch candles from mainnet but query positions on testnet

### 3. Repurposed dYdX Bot (LEFT OVER CODE)
- `package.json` name: `"dydx-scalping-bot"`, description: `"A scalping trading bot for dYdX v4"`
- `@dydxprotocol/v4-client-js` still in runtime dependencies (unused, adds attack surface)
- `main` field points to `src/index.ts` which doesn't exist
- Bot was clearly repurposed from a dYdX project without cleanup

### 4. No Max Position Size or Leverage Bounds
Config default is 20x leverage. No code validates:
- Maximum position size
- Maximum leverage
- Account balance before ordering
- Order count limits

### 5. Bug in getUserOpenOrders()
`marketInfo.js:172`: `throw new Error(...)` is outside the catch block, will always throw `ReferenceError: error is not defined`.

### 6. ML exec() Usage
`ml_optimizer.js` uses `child_process.exec()` to run Python scripts. While paths come from internal constants (not user input), this is worth noting. The embedded Python script is generated as a template string with `JSON.stringify()` interpolation of parameter ranges — not exploitable but unusual.

---

## Network Endpoints

| Source | Endpoint | Purpose |
|--------|----------|---------|
| `hyperliquid` SDK | api.hyperliquid.xyz / api.hyperliquid-testnet.xyz | All trading + data APIs |
| visualization.js | cdn.plot.ly | Plotly charting library (HTML output only) |

No unexpected outbound connections detected.

---

## Verdict

**Proceed to scoring** — no blocking security issues, but multiple concerns that significantly reduce the bot's security posture: GTC market orders, inconsistent testnet handling, unused dYdX dependency, no order bounds validation. Bot self-describes as "not fully implemented yet" in README.
