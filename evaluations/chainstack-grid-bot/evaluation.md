# Evaluation: Chainstack Grid Bot

**Repo**: https://github.com/chainstacklabs/hyperliquid-trading-bot
**Evaluator**: Claude (automated)
**Date**: 2026-03-29
**Tier**: 1

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Hierarchical key resolution (env vars, key files, config). Separate testnet/mainnet paths. Key validated before use. Warns on keys in YAML but doesn't reject. Never logged. |
| A2 | Dependency hygiene | 4 | 8 runtime deps, all established. 0 known vulns. Official SDK used. uv.lock committed. Version ranges use `>=` without upper bound. |
| A3 | Network surface | 5 | Only HL endpoints (public + optional Chainstack). Endpoint router with health checks. Exchange ops forced to public endpoint (correct for signing). No telemetry. |
| A4 | Code transparency | 5 | All Python, clean architecture, well-documented. Apache-2.0 license. YAML config with `safe_load`. No obfuscation. |
| A5 | Input validation | 4 | Comprehensive config validation with cross-checks (enhanced_config.py). Key format validation. YAML safe_load. Missing per-order max size validation. |
| | **A average** | **4.4** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | Grid strategy well-documented in YAML comments and code. Geometric spacing, auto/manual price range, rebalancing threshold. Clear config with conservative/aggressive guidance. |
| B2 | Backtesting | 0 | No backtesting capability |
| B3 | Risk management | 3 | Stop loss, take profit, max drawdown, max position size — all configurable. Disabled by default (safe). Drawdown uses unrealized PnL, not peak-to-trough. Rule-based extensible architecture. |
| B4 | Configurability | 5 | YAML config with rich documentation. Auto-discover active configs. Validate-only mode. Separate testnet/mainnet. Env var overrides. All params have ranges and defaults. |
| B5 | Monitoring | 2 | Python logging with configurable level. Print statements for status. No structured logging, no Telegram/Discord alerts, no dashboards. |
| | **B average** | **2.8** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | No test suite despite CLAUDE.md mentioning "test driven development" |
| C2 | Error handling | 4 | Custom exception hierarchy (ConfigurationError, ExchangeError, OrderError, etc). Graceful shutdown on SIGINT/SIGTERM. Engine catches and logs all errors without crashing. |
| C3 | Documentation | 4 | Extensive CLAUDE.md, AGENTS.md, README. YAML config fully commented. .env.example well-documented. 15+ learning examples with docstrings. No standalone API docs. |
| C4 | Code quality | 4 | SOLID architecture. Interface-based design (ExchangeAdapter, TradingStrategy). Async/await. Dataclasses. Type hints. Clean module separation. Some hardcoded values (BTC precision). |
| C5 | Maintenance | 3 | 43 commits on main. Corporate-backed (Chainstack). Created Aug 2025. Last activity recent. 2 contributors. No CI/CD pipeline visible. |
| | **C average** | **3.0** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | Uses official `hyperliquid-python-sdk`. Proper `Info` + `Exchange` initialization via adapter. Endpoint router for smart routing. BTC price/size rounding hardcoded (should query metadata). |
| D2 | Testnet support | 5 | Testnet-first design. Separate testnet/mainnet keys. Config default `testnet: true`. Env var `HYPERLIQUID_TESTNET=true`. All docs emphasize testnet. |
| D3 | HL features | 3 | Uses: orders (limit), cancel, user_state, all_mids. WebSocket for price feeds. Does NOT use: modify orders, TPSL, bulk operations, vaults, subaccounts, agent wallets. |
| | **D average** | **4.0** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (4.4   * 0.4) + (2.8   * 0.3) + (3.0   * 0.2) + (4.0   * 0.1)
      = 1.76 + 0.84 + 0.60 + 0.40
      = 3.60
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Chainstack Grid Bot is a well-architected, security-conscious grid trading bot with excellent configurability and testnet-first design. Its main weaknesses are the complete absence of tests, no backtesting, and incomplete order fill tracking. The grid strategy logic is correct but unproven in live conditions due to the fill tracking gap. Good candidate for testnet trials after verifying order execution works end-to-end.

## Key Findings

### Strengths
- Excellent YAML-based configuration with validation and documentation
- Testnet-first design with separate key management paths
- Clean SOLID architecture (interfaces, adapters, strategies)
- Smart endpoint routing with health checks and Chainstack fallback
- Corporate-backed (Chainstack) with educational materials (15+ learning examples)
- Graceful shutdown handling

### Concerns
- **No tests** despite claiming TDD in CLAUDE.md
- **Order fill tracking incomplete**: engine assumes immediate execution, doesn't actually verify fills
- **BTC-specific hardcoding**: price rounding (whole dollars, should be 2 decimals), size precision (5 decimals), min size (0.0001) all hardcoded for BTC only
- **No backtesting**: can't validate grid strategy parameters before live trading
- **Drawdown calculation simplified**: uses unrealized PnL, not peak-to-trough
- **WebSocket reconnection exists** but WS URL hardcoded (doesn't use endpoint router)

### Recommendations
- Implement actual order status tracking (query `info.open_orders()` periodically)
- Fix BTC price precision (use market metadata, not hardcoded whole dollars)
- Make size/precision dynamic from market metadata for multi-asset support
- Add basic test suite (at minimum: config validation, grid level generation, risk rules)
- Track high water mark for proper drawdown calculation
- Consider adding TPSL orders via SDK for risk management instead of polling
