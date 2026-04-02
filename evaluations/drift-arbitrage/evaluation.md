# Evaluation: Hyperliquid-Drift Arbitrage Bot (rustjesty)

**Repo**: https://github.com/rustjesty/hyperliquid-drift-arbitrage-bot
**Evaluator**: Claude
**Date**: 2026-04-02
**Tier**: 2

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | Keys loaded from environment variables (not config files). README explicitly warns YAML should not contain secrets. Pydantic validates required fields before startup. Drift Solana keypair and Hyperliquid API key both from env. No encryption, no vault, no zeroize — but correct operational separation. |
| A2 | Dependency hygiene | 1 | **42 known vulnerabilities** — aiohttp (16 CVEs), urllib3 (9 CVEs), certifi (4), protobuf (2), others. `hyperliquid-python-sdk` unpinned. `eth-account` unversioned. driftpy pinned at 0.8.63 (older). No lock file. |
| A3 | Network surface | 3 | Only exchange APIs: Hyperliquid REST, Drift Solana RPC + DLOB. No web server, no dashboard, no telemetry. All outbound calls are to expected endpoints. |
| A4 | Code transparency | 4 | Clean Python with clear module separation. No obfuscation. Good docstrings. Pydantic config validation. Well-commented strategy logic. |
| A5 | Input validation | 3 | Pydantic validates all config at startup. Strategy checks slippage bounds. Engine validates fill detection. Amount/price range not validated against exchange limits. |
| | **A average** | **2.80** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 4 | README explains cross-exchange arbitrage concept clearly. Two strategies documented: basis (price) and funding rate. Architecture diagram in README. Strategy logic well-commented with profit calculations. |
| B2 | Backtesting | 0 | None. Dry-run mode logs opportunities but doesn't simulate execution or estimate historical performance. |
| B3 | Risk management | 3 | Safe-mode activation on execution failure (blocks new orders). Slippage bounds per leg (configurable bps). Atomic execution with rollback on partial fill. Configurable max leverage (though unused in code). No stop-loss, no max drawdown, no position size limits. |
| B4 | Configurability | 4 | YAML config with Pydantic validation. Env var fallback for secrets. Per-strategy parameters (poll interval, min profit, max slippage, fees). Dry-run mode. Configurable timeouts. Multi-strategy support via runner. |
| B5 | Monitoring | 2 | JSONL logging for trades, opportunities, and events. Python logging module. No Telegram/Discord alerts, no dashboards, no external monitoring. Safe-mode requires manual intervention. |
| | **B average** | **2.60** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 3 | **637 lines of tests across 6 modules** — first Tier 2 bot with actual tests! pytest + pytest-asyncio. Mocked connectors. Tests cover config loading, RPC retry logic, strategy signal generation, execution rollback, slippage alerts. Missing: integration tests, edge cases (empty books, API failures). |
| C2 | Error handling | 3 | Try-except around all exchange calls. Safe-mode failover on execution failure. Rollback on partial fill. Retry logic for Drift RPC (5 attempts, 2s sleep). But: broad `except Exception` catches, no custom exception types, safe-mode requires manual reset. |
| C3 | Documentation | 4 | Comprehensive README (125 lines) with architecture overview, setup guide, config examples, usage instructions. Example YAML config. Docstrings on key functions. Missing: API docs, troubleshooting guide. |
| C4 | Code quality | 4 | Clean architecture: connectors (abstract base + two implementations), strategies (base + two implementations), execution engine, storage. Async-first with proper await. Pydantic for config. ~1,450 LOC production code — well-scoped. Some loose typing (`Dict[str, Any]`). |
| C5 | Maintenance | 1 | Single commit ("refac: engine.py by https://t.me/soljesty"). MIT license. No CI/CD, no issues, no PRs. |
| | **C average** | **3.00** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 3 | Uses `hyperliquid-python-sdk` (official). ConnectorBase abstraction allows clean SDK wrapping. Order placement, position fetching, order book, funding rates, cancel. Proper error handling on SDK calls. |
| D2 | Testnet support | 1 | `api_url` configurable (could point to testnet). But no explicit testnet flag, no testnet documentation, and Drift side is hardcoded to mainnet (`env="mainnet"`). Not usable for safe testing. |
| D3 | HL features | 2 | Limit orders, cancel, order book fetching, funding rates, position tracking. No WebSocket (REST polling only), no vaults, no subaccounts, no market orders. |
| | **D average** | **2.00** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (2.80 * 0.4) + (2.60 * 0.3) + (3.00 * 0.2) + (2.00 * 0.1)
      = 1.120 + 0.780 + 0.600 + 0.200
      = 2.70
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

The best-engineered Tier 2 bot and the only one with actual tests. A modular, async-first cross-exchange arbitrage platform that monitors price and funding rate discrepancies between Drift (Solana) and Hyperliquid, executing atomically hedged trades with rollback on partial fills. The architecture is clean (abstract base connectors, strategy pattern, execution engine with safe-mode), the config system is excellent (Pydantic + YAML + env vars), and the 637 lines of pytest coverage demonstrate real software engineering discipline. However, it's dragged down by 42 dependency vulnerabilities (aiohttp, urllib3), no testnet support (Drift hardcoded to mainnet), and the inherent complexity of cross-exchange arbitrage (fill detection relies on position polling, not truly atomic execution). The catalog listed it as Rust — it's actually Python. A valuable reference for cross-exchange arbitrage architecture and the standard other Tier 2 bots should aspire to.

## Key Findings

### Strengths
- **Only Tier 2 bot with tests**: 637 lines across 6 modules — config, connectors, strategies, engine, runner. Mocked dependencies, async test support.
- **Best architecture of Tier 2**: Clean separation — abstract `ConnectorBase`, two strategy implementations (basis + funding), execution engine with safe-mode, JSONL storage. ~1,450 LOC, well-scoped.
- **Pydantic config validation**: Structured YAML + env var fallback. Required fields validated before startup. Secrets explicitly kept out of config files.
- **Atomic execution with rollback**: Both legs placed async, fill detection via position polling, rollback and safe-mode if one leg fails.
- **Two genuine strategies**: Basis arbitrage (price discrepancy) and funding rate arbitrage (rate spread). Both with configurable thresholds, fee accounting, slippage bounds.
- **MIT license**: Only Tier 2 bot besides HyperLiquidAlgoBot and copy traders with a clear open-source license.
- **Dry-run mode**: Logs opportunities without executing — safe for research.

### Concerns
- **42 dependency vulnerabilities**: aiohttp 16 CVEs, urllib3 9 CVEs, certifi 4, protobuf 2, others. Most are medium severity but volume is high.
- **Not truly atomic**: Two independent async order placements. No guarantee of simultaneous execution. Drift finality (~0.4s) differs from Hyperliquid. If first fills and second fails, position is briefly unhedged until rollback completes.
- **Fill detection via position polling**: Checks position delta every 1s for 10s. Could miss fills if API lags, or confirm false fills from other orders on the same account.
- **No testnet**: Drift hardcoded to `env="mainnet"`. Hyperliquid `api_url` theoretically configurable but not documented for testnet.
- **Funding rate unit confusion**: Drift rate divided by 1e9 (nanosecond precision?), Hyperliquid used raw. Different units could cause magnitude errors in funding arbitrage calculations.
- **Safe-mode is a dead end**: Once triggered, bot stops. No auto-recovery, no alerting, no monitoring integration. Requires manual intervention.
- **Single commit**: Code dump despite having tests — suggesting it was developed elsewhere and published as-is.
- **Catalog mislabeled as Rust**: Actually Python. The author's handle "rustjesty" likely caused the confusion.

### Comparison with Other Tier 2 Bots

| Aspect | Drift Arb (2.70) | Rust Bot (2.84) | Copy Trading Bot (2.87) |
|--------|-------------------|-----------------|-------------------------|
| Tests | **637 lines (best)** | None | None |
| Architecture | Clean modular | Complex SaaS | Good modular |
| Config validation | Pydantic (best) | None visible | Zod |
| Error handling | Safe-mode + rollback | Result<T, E> | Custom error hierarchy |
| Dep vulns | 42 (worst) | 0 | 0 |
| Documentation | Good README | None | Extensive |
| Strategy type | Cross-exchange arb | User scripted | Copy trading |
| Testnet | No (Drift mainnet) | No (HL mainnet) | Flag (defaults off) |
| License | MIT | None | MIT |

### Recommendations
- Do not use for live trading without fixing dependency vulnerabilities and adding testnet support
- **High-value reference** for: cross-exchange arbitrage architecture, abstract connector pattern, Pydantic config validation, execution engine with rollback, pytest patterns for async trading bots
- If forking: (1) update all deps (especially aiohttp, urllib3), (2) add testnet support for both exchanges, (3) validate funding rate units with real data, (4) replace position polling with order status confirmation, (5) add monitoring/alerting, (6) implement auto-recovery from safe-mode
