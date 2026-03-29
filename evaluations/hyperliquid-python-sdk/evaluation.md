# Evaluation: hyperliquid-python-sdk (Official SDK Baseline)

**Repo**: https://github.com/hyperliquid-dex/hyperliquid-python-sdk
**Evaluator**: Claude (automated)
**Date**: 2026-03-29
**Tier**: Reference baseline (not a bot)

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Key loaded from config file or encrypted keystore. Never logged or transmitted — only signature (r,s,v) sent. Uses `secrets.token_hex()` for agent keys. Not 5 because config.json stores key in plaintext (no vault/keyring). |
| A2 | Dependency hygiene | 4 | 5 runtime deps, all established. 0 known vulns. Poetry lockfile committed. Range-pinned (not exact). No dependabot/renovate. |
| A3 | Network surface | 5 | Only connects to `api.hyperliquid.xyz`, `api.hyperliquid-testnet.xyz`, or `localhost:3001`. WebSocket derived from same base URL. Zero telemetry/analytics. |
| A4 | Code transparency | 5 | All Python source readable, well-structured. No obfuscation. MIT license. SECURITY.md with responsible disclosure process. |
| A5 | Input validation | 3 | `float_to_wire` and `float_to_int` validate precision/rounding. `Cloid` validates format. No max order size bounds. No rate limiting. |
| | **A average** | **4.2** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | N/A | SDK, not a trading bot — no strategy |
| B2 | Backtesting | N/A | SDK, not a trading bot |
| B3 | Risk management | N/A | SDK, not a trading bot |
| B4 | Configurability | 4 | `config.json.example` with secret_key or keystore path options. Base URL configurable (mainnet/testnet/local). Vault address, account address, timeout all configurable. |
| B5 | Monitoring | 2 | Python `logging` module used (debug level). No structured logging, no alerting, no dashboards. |
| | **B average** | **3.0** | (B4 + B5 only, N/A items excluded) |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 3 | Signing test vectors + VCR-recorded info endpoint tests. Coverage configured. No integration tests against live API. |
| C2 | Error handling | 3 | `ClientError`/`ServerError` exceptions with status codes. JSON parse fallback. No retry logic or circuit breaker. |
| C3 | Documentation | 3 | Docstrings on major Info methods with arg/return types. README exists. No comprehensive API docs site. Examples cover most functionality. |
| C4 | Code quality | 4 | TypedDict types throughout. mypy configured (strict). pre-commit hooks. isort + black formatting. Clean module structure. |
| C5 | Maintenance | 4 | Active development (v0.22.0, Feb 2026). 20+ contributors. CI/CD pipelines. Regular releases. Last gap ~3 months (Nov 2025 to Feb 2026). |
| | **C average** | **3.4** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 5 | This IS the official SDK |
| D2 | Testnet support | 4 | `TESTNET_API_URL` constant. Mainnet/testnet determined by base_url. No testnet-default mode — defaults to mainnet. |
| D3 | HL features | 5 | Full API coverage: orders, cancels, modify, bulk ops, TPSL, market orders, leverage, vaults, subaccounts, staking, WebSocket (13+ subscription types), spot, perps, EVM, multi-sig, builder-deployed DEXs, schedule cancel, agent approval, USD/spot transfers, withdrawals, validator ops |
| | **D average** | **4.67** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (4.2   * 0.4) + (3.0   * 0.3) + (3.4   * 0.2) + (4.67  * 0.1)
      = 1.68 + 0.90 + 0.68 + 0.467
      = 3.73
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

**Note**: As a reference baseline SDK (not a bot), the verdict categories don't directly apply. The score reflects SDK quality for bot evaluation purposes. The B-category N/A items (strategy, backtesting, risk management) lower the score because the rubric is designed for bots, not libraries.

## Summary

The official Hyperliquid Python SDK is a well-built, security-conscious library with comprehensive API coverage. It provides the reference implementation for key management (config file, signing-only key usage), API communication (REST + WebSocket), and all HL features. Its main gaps — no built-in rate limiting, no retry logic, no order size bounds — are reasonable for an SDK that delegates those concerns to consuming applications.

## Key Findings

### Strengths
- Minimal, focused dependency tree (5 runtime deps)
- Complete HL API coverage (perps, spot, vaults, subaccounts, staking, EVM, multi-sig)
- Key never leaves the signing function — only r/s/v signature transmitted
- Clean TypedDict-based type system with mypy strict mode
- 13+ WebSocket subscription types with clean pub/sub interface
- EIP-712 typed data signing (industry standard)

### Concerns
- Defaults to mainnet (should arguably default to testnet for safety)
- No client-side rate limiting
- No retry/backoff logic for transient failures
- `config.json` stores key in plaintext (keystore option available as alternative)
- WebSocket manager runs as daemon thread without reconnection logic

### Recommendations
- Bots using this SDK should implement their own rate limiting, retry logic, and order size bounds
- Bots should use `TESTNET_API_URL` by default and require explicit opt-in for mainnet
- The keystore option (encrypted key + password prompt) is preferred over plaintext config
- WebSocket consumers should handle disconnection/reconnection at the application level
