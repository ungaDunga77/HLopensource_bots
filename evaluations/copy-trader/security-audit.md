# Security Audit: Hyperliquid Copy Trader

**Repo**: https://github.com/MaxIsOntoSomething/Hyperliquid_Copy_Trader
**Date**: 2026-04-02
**Auditor**: Claude (automated)
**Phase**: 2 (Static Audit)

---

## Automated Scan Results

### Secret Scan
- **CRITICAL**: 0
- **HIGH**: 10 (all false positives — env var reads via `os.getenv('HYPERLIQUID_PRIVATE_KEY')` and parameter declarations)
- **MEDIUM**: 11 (5 non-whitelisted URLs in README — hyperfoundation.org, cryptoninjas.net, opensource.org, docker.com, api.telegram.org; 6 trufflehog entropy findings on .env.example, README, settings.py — all false positives)

### Dependency Audit
- **Vulnerabilities**: 29 (26 in aiohttp 3.9.1, 3 in requests 2.31.0) — all MEDIUM
- **Runtime deps**: 10 (python-dotenv, aiohttp, websockets, requests, eth-account, web3, python-telegram-bot, sqlalchemy, alembic, loguru, pydantic)
- **Dev deps**: 3 (pytest, pytest-asyncio, pytest-mock) — mixed into requirements.txt
- **Pinning**: All exact versions (`==`) — good practice
- **No lockfile**: No pip-compile output or poetry.lock

---

## Manual Code Review Checklist

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | No hardcoded credentials | PASS | Keys read from env vars only. Default `target_wallet` is a public address (not a secret). |
| 2 | .env/.gitignore configured | PASS | Comprehensive .gitignore (50 lines). Covers `.env`, `config/config.json`, `data/`, `logs/`. `.env.example` provided with empty values. |
| 3 | Private key never logged | PASS | Grep for log/print with key/private/secret: 0 matches. Key passed to `Account.from_key()`, stored as `self.private_key`, never logged. |
| 4 | No unexpected outbound calls | PASS | All trading calls via aiohttp to `api.hyperliquid.xyz`. Telegram to `api.telegram.org`. No telemetry. No analytics. |
| 5 | No obfuscated/minified code | PASS | All plain Python. MIT license. |
| 6 | No suspicious post-install scripts | PASS | No setup.py, no pyproject.toml build scripts. |
| 7 | No dynamic code execution | PASS | No eval, exec, __import__, subprocess, or shell execution. |
| 8 | No unexpected filesystem access | PASS | Writes limited to `logs/` (loguru) and `data/` (SQLite). Both gitignored. |
| 9 | Dependencies pinned | PASS | All `==` exact versions. No lockfile though. |
| 10 | No dependency confusion risk | PASS | All deps are well-known public packages. |
| 11 | WebSocket only to expected HL endpoints | PASS | WebSocket via custom client to `wss://api.hyperliquid.xyz/ws` (configurable). |
| 12 | Order amounts have sanity bounds | PASS | Min $10 (HL requirement). Max position size configurable. Max total exposure. Max leverage per asset. Entry quality check. |
| 13 | Rate limiting implemented | FAIL | No rate limiting on API calls. WebSocket reconnect uses fixed 5s delay (no backoff). |
| 14 | Error handling doesn't leak sensitive info | PASS | Errors logged with message only. No credential exposure in error paths. |
| 15 | No subprocess with user-controlled input | PASS | No subprocess usage at all. |

---

## Key Security Findings

### 1. Vulnerable Dependencies (MEDIUM RISK)
`aiohttp==3.9.1` has 26 known CVEs including request smuggling (CVE-2024-52304), infinite loop DoS (CVE-2024-30251), path traversal (PYSEC-2024-24), and memory exhaustion (CVE-2026-22815). `requests==2.31.0` has 3 CVEs including credential leakage (CVE-2024-47081). These are the HTTP libraries used for all API communication.

### 2. Dockerfile Bakes .env into Image (MEDIUM RISK)
`Dockerfile` line 10: `COPY .env .env` copies the environment file (containing private key) into the Docker image layer. Even if the `.env` is overridden at runtime via the docker-compose volume mount, the credentials persist in the image layer. Should use `docker-compose.yml` `env_file` directive instead and remove the COPY.

### 3. Live Trading Path Hardcoded Off (INFO)
`main.py:847` always creates executor with `dry_run=True` regardless of `settings.simulated_trading`. Comment says "Always start in dry run mode for safety!" This means live trading is impossible without code modification, which is safe but means the live trading code path is untested.

### 4. Custom Executor May Have Incorrect API Payload (MEDIUM RISK)
`executor.py` builds order actions with `"a": self.wallet_address` (should be integer asset index per HL API) and `"c": symbol` (not a standard HL API field). EIP-712 signing uses `chainId: 1337` which may not match Hyperliquid's expected chain ID. The live trading path through this executor would likely fail silently or be rejected by the API.

### 5. No Rate Limiting (LOW RISK)
API calls to Hyperliquid have no rate limiting. The `monitor.get_current_state()` is called on every fill and position update, which could trigger rate limits during high-activity periods. WebSocket reconnect uses a fixed 5-second delay with no exponential backoff.

### 6. on_new_order Callback Has Wrong Signature (BUG)
`main.py:342` calls `position_sizer.calculate_size(target_size=..., symbol=..., current_exposure=...)` but `PositionSizer.calculate_size()` expects `(target_position, target_wallet_balance, your_wallet_balance, your_current_exposure)`. This would raise a TypeError at runtime when a new order is detected.

### 7. Dead Code (executor_old.py) (INFO)
`executor_old.py` imports `from hyperliquid.exchange import Exchange` and `from hyperliquid.info import Info` — these are official SDK classes that don't exist in the project's `src/hyperliquid/` module and the official SDK isn't in requirements.txt. This file would fail on import.

---

## Network Endpoints

| Source | Endpoint | Purpose |
|--------|----------|---------|
| HyperliquidClient | api.hyperliquid.xyz/info | User state, market data, meta |
| TradeExecutor | api.hyperliquid.xyz/exchange | Order execution, leverage |
| HyperliquidWebSocket | wss://api.hyperliquid.xyz/ws | Real-time user event subscriptions |
| TelegramBot | api.telegram.org | Bot commands, notifications |

All endpoints configurable via environment variables. No unexpected outbound connections.

---

## Verdict

**Proceed to scoring** — no critical security issues. Main concerns: 29 vulnerable dependencies (aiohttp, requests), Dockerfile baking .env into image, broken live trading code path, and a runtime bug in order copy callback. The bot's default dry-run mode and comprehensive input validation are strong safety features.
