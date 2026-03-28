# Bot Evaluation Rubric

## Scoring

Each criterion scored 0-5. Final score = weighted average across categories.

| Score | Meaning |
|-------|---------|
| 0 | Absent or failing |
| 1 | Minimal / dangerous |
| 2 | Below acceptable |
| 3 | Acceptable |
| 4 | Good |
| 5 | Excellent |

## Verdict Thresholds

| Score | Verdict |
|-------|---------|
| >= 4.0 | Strong candidate for testnet trials |
| 3.0 - 3.9 | Worth investigating, needs hardening |
| 2.0 - 2.9 | Reference only, significant concerns |
| < 2.0 | Avoid, potential risk |

---

## A. Security (weight: 40%)

| # | Criterion | 0 | 3 | 5 |
|---|-----------|---|---|---|
| A1 | Key management | Hardcoded keys or logged | .env with .gitignore, docs warn | Vault/keyring, never in memory longer than needed |
| A2 | Dependency hygiene | Known vulns, no lockfile | Clean audit, pinned versions | Clean audit + dependabot/renovate + minimal deps |
| A3 | Network surface | Unexplained outbound calls | All endpoints documented | Only exchange API, no telemetry, verifiable |
| A4 | Code transparency | Obfuscated or minified code | Clear code, some docs | Well-documented, clear audit trail |
| A5 | Input validation | No validation | Config validated | Full validation + safe defaults + bounds checking |

## B. Functionality (weight: 30%)

| # | Criterion | 0 | 3 | 5 |
|---|-----------|---|---|---|
| B1 | Strategy clarity | No docs | Strategy documented | Full strategy docs + rationale + edge thesis |
| B2 | Backtesting | None | Built-in backtester | Backtester + optimization + out-of-sample validation |
| B3 | Risk management | None | SL/TP + position sizing | Full risk framework (max drawdown, exposure limits) |
| B4 | Configurability | Hardcoded params | Config file with docs | Full config + validation + defaults + dry-run mode |
| B5 | Monitoring | None | Structured logging | Logging + alerts (Telegram/Discord) + dashboards |

## C. Engineering Quality (weight: 20%)

| # | Criterion | 0 | 3 | 5 |
|---|-----------|---|---|---|
| C1 | Tests | None | >50% coverage | >80% coverage + integration tests |
| C2 | Error handling | Crashes on errors | Graceful degradation | Retry + circuit breaker + alerting |
| C3 | Documentation | None | Setup + usage docs | Full docs + examples + troubleshooting |
| C4 | Code quality | Spaghetti | Well-structured | Clean architecture + typed + linted |
| C5 | Maintenance | Abandoned (>6 months) | Regular commits | Active + responsive maintainer + CI/CD |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | 0 | 3 | 5 |
|---|-----------|---|---|---|
| D1 | SDK usage | Raw HTTP / custom wrapper | Official SDK | Official SDK + proper error handling + rate limiting |
| D2 | Testnet support | None | Testnet flag | Testnet default + easy switching + docs |
| D3 | HL features | Basic orders only | + cancel/modify + account state | Full API coverage (vaults, subaccounts, WebSocket) |

---

## Scoring Formula

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
```

Where `X_avg` = mean of all criteria scores in category X.
