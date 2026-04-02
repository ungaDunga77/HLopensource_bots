# Evaluation: Hyperliquid Copy Trader

**Repo**: https://github.com/MaxIsOntoSomething/Hyperliquid_Copy_Trader
**Evaluator**: Claude (automated)
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | Private key via `os.getenv('HYPERLIQUID_PRIVATE_KEY')`. Comprehensive .gitignore covers `.env`, `config/config.json`. Key never logged. `.env.example` with empty values. Not encrypted/keystore. Dockerfile `COPY .env .env` bakes credentials into image layer. |
| A2 | Dependency hygiene | 2 | All deps pinned to exact versions (`==`) — good. But 26 CVEs in `aiohttp==3.9.1`, 3 CVEs in `requests==2.31.0`. No lockfile. No dependabot/renovate. Test deps mixed into main requirements.txt. |
| A3 | Network surface | 4 | All trading calls to `api.hyperliquid.xyz`. Telegram to `api.telegram.org` (expected). No telemetry. All endpoints configurable via env vars. No unexpected outbound. |
| A4 | Code transparency | 3 | All plain Python. MIT license. No obfuscation. Dead code left in (`executor_old.py`). Clear module structure. |
| A5 | Input validation | 4 | Pydantic models for config. Min position size $10 (HL requirement). Max position size/exposure caps. Asset-specific max leverage (30 assets). Entry quality check (deviation %). Blocked assets list. Max open trades/orders limits. Auto-pause on equity limit. |
| | **A average** | **3.2** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | Copy trading strategy well-documented in README. Proportional and fixed sizing modes explained. Leverage adjustment documented. Blocked assets explained with use cases. Position sizing example. |
| B2 | Backtesting | 0 | None. Not typical for copy trading bots, but absent per rubric. |
| B3 | Risk management | 4 | Dry-run mode (default on). Max position size, max total exposure, max concurrent positions, max daily loss (all configurable). Asset-specific max leverage caps (30 assets hardcoded). Entry quality check. Blocked assets. Min position size enforcement. Auto-pause on equity limit. Custom SL available but disabled by default. |
| B4 | Configurability | 4 | 20+ env vars. Pydantic validation. Two sizing modes (proportional/fixed). Dry-run mode prominent. Blocked assets. Telegram optional. Docker ready. `.env.example` provided. |
| B5 | Monitoring | 4 | loguru with file rotation (100MB, 30-day retention, zip). Telegram bot with 7 commands (/status, /positions, /orders, /pnl, /pause, /resume, /stop). Hourly reports. Trade/error/startup/shutdown notifications. Simulated tag on dry-run notifications. |
| | **B average** | **3.2** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | pytest + pytest-asyncio + pytest-mock in requirements.txt. Zero test files. Zero coverage. |
| C2 | Error handling | 3 | Try/catch in all critical paths. WebSocket auto-reconnect (5s fixed delay). Callback error isolation. Graceful shutdown (KeyboardInterrupt + finally block). No retry with exponential backoff. No rate limiting. |
| C3 | Documentation | 3 | Good README: setup, config, Docker, Telegram, leverage, blocked assets, position sizing. `.env.example`. No API docs, no troubleshooting, no inline docstrings beyond basic. |
| C4 | Code quality | 3 | Clean modular structure (config, copy_engine, hyperliquid, telegram_bot, utils). Pydantic + dataclass models. Type hints throughout. BUT: dead code (`executor_old.py`), global state in main.py, `on_new_order` has wrong method signature (TypeError at runtime), `dry_run=True` hardcoded ignoring settings. |
| C5 | Maintenance | 1 | Shallow clone shows 1 commit (2026-01-15, ~2.5 months stale). Single contributor. No CI/CD. No issues/PRs activity visible. |
| | **C average** | **2.0** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Custom HTTP integration with EIP-712 signing (executor.py). Official SDK was used in executor_old.py but abandoned. Official SDK not in requirements.txt. Custom executor's order payload format appears incorrect (`"a"` = wallet address instead of asset index, `"c"` = symbol not in standard API). Live trading path likely broken. |
| D2 | Testnet support | 1 | No testnet flag. Default is mainnet (`api.hyperliquid.xyz`). API URL changeable via env var but no testnet docs. No testnet-first design. |
| D3 | HL features | 3 | Market orders (IoC), limit orders (GTC/ALO), cancel, cancel all, leverage update (cross/isolated), clearinghouseState, WebSocket (userEvents, trades, allMids), meta API. Missing: TPSL, vaults, subaccounts, agent wallets, spot, HIP-3. |
| | **D average** | **2.0** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.2   * 0.4) + (3.2   * 0.3) + (2.0   * 0.2) + (2.0   * 0.1)
      = 1.28 + 0.96 + 0.40 + 0.20
      = 2.84
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Hyperliquid Copy Trader is a well-structured copy trading bot with strong risk management and monitoring features (Telegram bot, configurable limits, dry-run default). However, it has critical gaps: zero tests, no testnet support, 29 vulnerable dependencies, and a live trading code path that appears broken (incorrect API payload format in the custom executor). The bot currently only works in simulation mode — `dry_run=True` is hardcoded in `main.py` regardless of settings. For copy trading evaluation purposes, the architecture and risk management design are worth studying, but the bot cannot trade in its current state.

## Key Findings

### Strengths
- Comprehensive risk management: max position/exposure/leverage caps, entry quality checks, blocked assets, auto-pause on equity limit
- Dry-run mode enabled by default — safe design choice
- Telegram bot with 7 commands (status, positions, orders, PnL, pause, resume, stop) plus hourly reports
- Clean modular architecture (config, copy_engine, hyperliquid, telegram_bot, utils)
- Pydantic configuration with env vars and validation
- Position sizing with proportional and fixed modes
- Asset-specific leverage limits for 30 assets
- Comprehensive .gitignore and .env.example

### Concerns
- **Live trading broken**: Custom executor has incorrect HL API payload format; dry_run hardcoded to True
- **29 vulnerable deps**: aiohttp 3.9.1 (26 CVEs) and requests 2.31.0 (3 CVEs) — HTTP libraries used for all API communication
- **Zero tests**: pytest in requirements but no test files
- **No testnet support**: Defaults to mainnet, no testnet flag or docs
- **on_new_order bug**: Calls `position_sizer.calculate_size()` with wrong argument names — would TypeError at runtime
- **Dockerfile bakes .env**: `COPY .env .env` embeds credentials in Docker image layer
- **No rate limiting**: API calls have no throttling; could hit rate limits during high activity
- **Dead code**: executor_old.py references modules that don't exist (official SDK not installed)

### Recommendations
- Reference the risk management design (position limits, leverage capping, entry quality, blocked assets, auto-pause)
- Reference the Telegram bot architecture (command handler + notification service pattern)
- Do not use for live trading without: fixing executor API payload, adding testnet support, updating vulnerable deps, adding rate limiting
- The WebSocket monitoring + callback architecture is clean and reusable
