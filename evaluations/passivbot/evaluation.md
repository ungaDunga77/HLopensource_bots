# Evaluation: Passivbot

**Repo**: https://github.com/enarjord/passivbot
**Evaluator**: Claude (automated)
**Date**: 2026-04-01
**Tier**: 1

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 2 | Plaintext `api-keys.json` (no encryption, no keystore, no env var support). `.gitignore` excludes it. Keys never logged — CCXT debug suppressed to WARNING by default. No key format validation. No file permission enforcement. Legacy field remapping is clean. Vault mode available for HL (good). |
| A2 | Dependency hygiene | 4 | 12 live trading deps, all pinned with `==`. 0 known vulns in live deps. 30 MEDIUM vulns total (all in full/dev deps: aiohttp, requests, werkzeug, flask, pymdown-extensions — not needed for live trading). Rust deps established. `memmap` 0.7.0 deprecated but functional. |
| A3 | Network surface | 3 | All exchange comms via CCXT (expected). Custom endpoint override system (`custom_endpoint_overrides.py`) allows URL rewriting with **no scheme/domain validation** — could redirect to attacker servers if config file is compromised. Broker codes are public affiliate IDs (benign). No telemetry. |
| A4 | Code transparency | 5 | All Python + Rust source readable. Unlicense (public domain). 7,688 commits of history. 46 contributors. Well-structured modular architecture. No obfuscation. |
| A5 | Input validation | 4 | Comprehensive config validation with whitelist-based allowed modifications. HJSON safe parsing. Balance validated (NaN/infinity/None checks). Wallet exposure limits enforced. `_resolve_coins_file_path` lacks path traversal validation (low risk — parsed as JSON). |
| | **A average** | **3.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | Contrarian market-making with martingale-inspired grid. Trailing entries/closes. Forager mode (dynamic market selection). Unstucking mechanism for losing positions. 22-page wiki. Extensive config templates with documentation. |
| B2 | Backtesting | 5 | Built-in backtester with historical data download. Evolutionary algorithm optimizer (deap). Pareto optimization for multi-objective tuning. Out-of-sample validation. Suite runner for batch optimization. Best-in-class for open-source bots. |
| B3 | Risk management | 5 | Wallet exposure limit (WEL) per-symbol per-side. Total wallet exposure limit (TWEL) global. Risk WEL enforcer threshold. Excess allowance percentages. Max realized loss percentage. Batch size limits (creations + cancellations). Balance hysteresis (prevents oscillation). Circuit breaker (10 errors/hour → restart). |
| B4 | Configurability | 5 | HJSON configs with templates. CLI with subcommands. Per-exchange customization. Per-symbol coin overrides. Approved coins lists. Custom endpoints. Optimizer for parameter tuning. Config transform tracking. Balance override for testing. |
| B5 | Monitoring | 3 | Structured logging with levels 0-3 (WARNING → TRACE). CCXT log suppression. Health tracking (errors, rate limits, WS reconnects). Position change logging with WEL/TWEL ratios. Dash dashboard available. No built-in Telegram/Discord alerts. |
| | **B average** | **4.6** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 4 | 88 test files, 991 tests collected. 851 passed, 22 failed (read-only FS, not bugs), 118 skipped (env-specific). Good coverage: config, risk management, order logic, exchange mocks, optimization. Parametrized tests. Async test support. |
| C2 | Error handling | 4 | Graceful shutdown (SIGINT/SIGTERM). Circuit breaker with error budget. Exponential backoff on rate limits. Balance validation (NaN/infinity). Order execution result validation. Exception hierarchy (RestartBotException, RateLimitExceeded). Debug print statements in production paths (minor concern). |
| C3 | Documentation | 4 | 22-page wiki. MkDocs site. Config templates with comments. README covers installation + features. CHANGELOG.md for releases. `api-keys.json.example`. No standalone API reference. |
| C4 | Code quality | 4 | Modular architecture (40 Python modules). Rust FFI for performance. Async/await throughout. Config transform system with whitelist protection. Clean separation (pure_funcs, exchanges, optimization). Some complexity (passivbot.py is 6,757 lines). |
| C5 | Maintenance | 5 | 7,688 commits. 46 contributors. v7.8.5 (active development through March 2025). Regular releases (12+ in last 6 months). Active community (Discord, GUI fork, config database). Unlicense. |
| | **C average** | **4.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 2 | Does NOT use official HL SDK. Uses CCXT abstraction layer (deliberate multi-exchange design). CCXT handles signing, endpoint routing, WebSocket. Custom HL-specific code for balance caching, HIP-3 positions, price rounding (6dp + 5sf), min cost ($10 default with auto-adjustment). |
| D2 | Testnet support | 0 | No testnet support for Hyperliquid. No testnet flag, no environment variable, no sandbox mode. Only Paradex has testnet detection. Custom endpoint overrides are the only workaround (manual). |
| D3 | HL features | 3 | HIP-3 stock perps support. Vault accounts (`is_vault`). Custom price rounding. WebSocket order monitoring (via CCXT Pro). Fill events manager. Bulk price fetches optimized for HL. Isolated margin NOT supported for HIP-3. No agent wallets, no HL-native TPSL, no vault creation. |
| | **D average** | **1.67** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.6   * 0.4) + (4.6   * 0.3) + (4.2   * 0.2) + (1.67  * 0.1)
      = 1.44 + 1.38 + 0.84 + 0.167
      = 3.83
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Passivbot is the most sophisticated bot evaluated so far — a mature, well-tested multi-exchange trading system with best-in-class backtesting and risk management. Its functionality score (4.6) is the highest of any bot evaluated. However, it was built as a multi-exchange tool, not an HL-native one. The complete absence of testnet support (0) and lack of official SDK usage (via CCXT instead) significantly drag down its HL integration score. Key management uses plaintext JSON files rather than env vars or encrypted keystores. Despite these gaps, the depth of its risk controls (WEL/TWEL enforcement, circuit breakers, batch limits) and its active 46-contributor community make it a strong candidate for forking or hardening.

## Key Findings

### Strengths
- Best-in-class backtester + evolutionary algorithm optimizer with Pareto optimization
- Comprehensive risk management: WEL, TWEL, excess allowance, max realized loss, batch limits, circuit breaker
- 851 passing tests across 88 test files (strongest test coverage of any bot evaluated)
- Active maintenance: 7,688 commits, 46 contributors, regular releases
- Rust FFI optimizer for performance-critical computations
- Official HL vault running on mainnet (proven in production)
- Clean modular architecture with config whitelist protection
- CCXT logging suppressed by default (prevents credential leakage)
- HIP-3 stock perps support with dedicated position fetching

### Concerns
- **No testnet support**: Complete gap — no flag, no env var, no sandbox mode for Hyperliquid
- **Plaintext credential storage**: `api-keys.json` with no encryption, no env var fallback, no file permission enforcement
- **Custom endpoint override attack surface**: URL rewriting with no HTTPS scheme enforcement or domain whitelist
- **No official HL SDK**: Uses CCXT abstraction — less direct control over HL-specific features
- **CI is a no-op**: GitHub Actions runs `true` — tests exist but aren't run in CI
- **Deprecated Rust dependency**: `memmap` 0.7.0 (should be `memmap2`)
- **Debug print statements in production paths**: `passivbot.py` lines 2111, 2120, 2130

### Recommendations
- Add testnet support: config flag or environment variable to switch HL endpoint to `api.hyperliquid-testnet.xyz`
- Add HTTPS scheme validation and domain whitelist to `custom_endpoint_overrides.py`
- Support env var credential loading as alternative to `api-keys.json`
- Enable CI test execution (replace `run: 'true'` with actual pytest)
- Upgrade `memmap` 0.7.0 → `memmap2` in Cargo.toml
- Replace debug `print()` statements with `logging.debug()` in order execution paths
- Consider adding HL-native features: agent wallets, TPSL orders, vault creation
