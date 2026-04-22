# Evaluation: OctoBot Market Making

**Repo**: https://github.com/Drakkar-Software/OctoBot-Market-Making
**Evaluator**: Claude (automated)
**Date**: 2026-04-19
**Tier**: 2

---

## Important Scope Note

This repository is a **distribution wrapper / launcher**, not a standalone market-making bot. It contains:

- `start.py` (20 lines, mostly license header)
- `octobot_market_making/cli.py` (27 lines) — invokes `octobot.cli.main` with a pre-baked default config
- `octobot_market_making/constants.py` (21 lines) — path constants + version
- `octobot_market_making/__init__.py` (20 lines) — `PROJECT_NAME`, `AUTHOR`, `VERSION="2.1.1"`
- `octobot_market_making/config/default_config.json` (24 lines) — sets `"profile": "market_making"`, `"distribution": "market_making"`
- `tests/cli_test.py` (32 lines) — single test asserting `octobot.cli.main` is called with the bundled config path
- `Dockerfile` (7 lines) — overlays config onto `drakkarsoftware/octobot:marketmaking-stable`
- `requirements.txt` — one line: `OctoBot[full]==2.1.1`

**Total module Python: ~120 LOC**, of which ~80 is license boilerplate. There is no strategy code, no order-book logic, no HL-specific integration — those live in the OctoBot core (5.7k stars) and its "tentacles" plugin tree, neither of which are in this repo. The actual market-making strategy is part of the OctoBot `market_making` profile selected by the shipped `default_config.json`.

Scoring is therefore constrained to what is observable **in this repo only**, with charitable interpretation where the parent framework is clearly responsible. Criteria that can't meaningfully be graded for a 120-LOC launcher are noted inline.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | No key handling in this repo — fully delegated to OctoBot core (which stores exchange API creds in `user/config.json` under `"exchanges"` per default_config schema). Scored neutrally because the delegation is clean (no ad-hoc env-var reading, no key logging surface introduced here). Not auditable without pulling OctoBot core. |
| A2 | Dependency hygiene | 2 | One single exact-pinned top-level dep: `OctoBot[full]==2.1.1`. The `[full]` extra transitively pulls a very large surface. `pip-audit` flagged 13 vulnerabilities (0 critical, all MEDIUM) mostly in `aiohttp 3.13.3` (fix in 3.13.4) — classic upstream aiohttp CVE cluster. Pin is good; transitive exposure is large and entirely OctoBot-controlled. |
| A3 | Network surface | 3 | This repo opens no sockets. `docker-compose.yml` binds the OctoBot web UI to host port 80 by default (not 127.0.0.1) — a mild concern for home deployments. Default config auto-opens the web UI in a browser (`"auto-open-in-web-browser": true`). Framework handles exchange connections. |
| A4 | Code transparency | 5 | GPL-3.0. Pure Python, no obfuscation, no compiled artifacts. Parent project (5.7k stars, active since 2018, Drakkar-Software) is well-known. Secret scan: one HIGH hit in `.github/workflows/docker.yml` line 21 (`3e26d6750975d678acb8fa35a0f69237881576b0`) — this is a git SHA pin in a GitHub Action, a **false positive** by detect-secrets. No real secrets. |
| A5 | Input validation | 3 | No user input is handled in this repo — it's a one-function CLI forwarder. Default config accepts user edits via the OctoBot web UI (validation is framework-side, unauditable from here). |
| | **A average** | **3.2** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 2 | Strategy is **not in this repo**. README describes it as a reference-price-anchored grid/ladder: configurable number of bids/asks, configurable price range around a "fair market price" sourced either from the local exchange or from a more liquid reference exchange. The bot cancels/replaces orders when the reference moves — an **arbitrage-protection** pattern. No Avellaneda-Stoikov, no inventory skew, no volatility-adaptive spread documented. Closer to a symmetric grid MM than a proper quote-driven MM. Lower score reflects: (a) algorithm code not in this repo, (b) described strategy is simpler than Hummingbot V2's `pmm_simple`/`pmm_dynamic` (no inventory skew, no Avellaneda). |
| B2 | Backtesting | 3 | `default_config.json` has a `"backtesting"` section (empty file list). README mentions a built-in paper-trading simulator ("trading simulator"). Framework-side; not exercised here. |
| B3 | Risk management | 2 | This repo adds no risk controls. README explicitly steers advanced risk management ("protecting your funds from unexpected market events") to the paid **OctoBot Cloud Market Making** upsell. The OSS distribution's risk management appears limited to what the default profile provides — position sizing via budget, but no stop-loss, no inventory limits documented in the open-source config. |
| B4 | Configurability | 3 | The open-source config schema is the 24-line `default_config.json` plus whatever the `market_making` OctoBot profile exposes via the web UI. README says spread/order-count/price-range are configurable. Richer configs (formula-based fair-price, dynamic computation) are gated behind OctoBot Cloud. For an OSS user the contract is thin but adequate for a basic ladder. |
| B5 | Monitoring | 4 | Web UI (port 80 → 5001) provides dashboard, order visualization, trade history. Notifications config (`price-alerts`, `trades`, `trading-script-alerts`) wired up by default. Screenshots in `docs/` show a polished dashboard. Probably the strongest observability story of the modular Python MM bots evaluated — comparable to Hummingbot's TUI, with the added benefit of a browser UI. |
| | **B average** | **2.8** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 2 | Exactly **one** test: `tests/cli_test.py::test_start_octobot_with_market_making_config` asserts that `octobot.cli.main` is called with the bundled config path. That's all that's testable in a 120-LOC launcher, but the score reflects absolute thinness. No integration tests, no config-schema validation tests. |
| C2 | Error handling | 2 | No error handling code in this repo (nothing to handle). `cli.main()` forwards to `octobot.cli.main()` with no try/except, no argv validation. |
| C3 | Documentation | 4 | README is polished, well-illustrated (4 docs images), explains the strategy's design goals clearly, includes install instructions for both Docker and Python, hardware requirements, disclaimer. CHANGELOG present and in sync with OctoBot versions. CONTRIBUTING and CODE_OF_CONDUCT present. Strong docs given the thin scope. |
| C4 | Code quality | 4 | What little code exists is clean: copyright headers, `pathlib` for paths, clear separation of `cli`/`constants`/`__init__`. Python >=3.10. Proper `setup.py` with `entry_points`. No smells. |
| C5 | Maintenance | 4 | Parent OctoBot: 5.7k stars, active since 2018. This module: v2.0.10 alpha (2025-03-25) → v2.1.1 (2026-03-30) — **11 releases in 12 months**, tracking upstream OctoBot tightly. Only 31 stars but it's a derivative. CI badge present and live. Very much alive. |
| | **C average** | **3.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 1 | No HL-specific code in this repo. HL is listed as one of "15+ supported exchanges" via OctoBot core, which uses CCXT under the hood (based on the generic multi-exchange framing). Does not use the official `hyperliquid-python-sdk`. |
| D2 | Testnet support | 1 | No HL testnet configuration visible in this repo. `default_config.json` has `"exchanges": {}`. Testnet config would have to be added manually via the OctoBot web UI using whatever CCXT Hyperliquid exposes. No documented testnet workflow. |
| D3 | HL features | 1 | README treats HL as just another CEX — pitches HL as a way to "farm volume-based DEX points for crypto airdrops, like the Hyperliquid HYPE airdrops". No mention of HL-native features: maker rebates, $10 min notional, TPSL trigger orders, HIP-3 builder-deployed perps, vaults, API wallets, leverage API, funding rate awareness. The MM strategy is exchange-agnostic — it does not exploit anything HL-specific. |
| | **D average** | **1.0** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (3.2   * 0.4) + (2.8   * 0.3) + (3.2   * 0.2) + (1.0   * 0.1)
      = 1.28 + 0.84 + 0.64 + 0.10
      = 2.86
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

OctoBot Market Making scores **2.86 — reference only**. The repo itself is a 120-LOC Docker/CLI launcher around OctoBot core; the actual MM logic lives upstream. The described strategy is a simpler reference-price-anchored grid (no inventory skew, no Avellaneda-Stoikov) that is exchange-agnostic and not HL-aware. The polished web UI and tight release cadence are real strengths; the thin OSS surface (advanced risk management gated behind the paid Cloud tier) and zero HL-specific integration are the main weaknesses for our use case.

## Key Findings

### Strengths
- **Web UI + notifications** shipped by default — strongest observability of any Python MM bot evaluated
- **Clean distribution wrapper pattern** — the `default_config.json` + CLI-forwarder approach is a tidy way to ship opinionated profiles of a larger framework
- **Release cadence** (11 releases in 12 months) tracking upstream OctoBot tightly

### Concerns
- **Freemium model**: advanced risk management and dynamic fair-price computation are explicitly steered to the paid OctoBot Cloud — the OSS version is deliberately minimal
- **Zero HL awareness**: HL is just another CCXT exchange; no maker-rebate logic, no TPSL, no vault support, no HIP-3, no API wallets
- **Strategy is simpler than Hummingbot V2's `pmm_dynamic`**: symmetric grid around a reference price vs Hummingbot's price-ceiling/floor, inventory skew, and Avellaneda-Stoikov controllers
- **13 MEDIUM aiohttp CVEs** pulled transitively via `OctoBot[full]==2.1.1` (fix available in 3.13.4; requires upstream bump)
- **Nothing to audit here**: a real security review requires cloning and auditing OctoBot core + tentacles — out of scope for this bot

### Top 3 Patterns vs Hummingbot V2
1. **(−) Strategy sophistication**: Hummingbot V2 ships `pmm_simple`, `pmm_dynamic`, Avellaneda-Stoikov, and a controller composition framework. OctoBot-MM ships a single reference-price grid with paid-tier upsell for anything fancier.
2. **(+) UX**: OctoBot's browser dashboard + notification system is more approachable than Hummingbot's TUI for non-terminal users. Useful UX reference for our custom bot.
3. **(−) HL integration depth**: Hummingbot has dedicated HL spot + perp connectors with HIP-3, vaults, TPSL, candle feeds (D_avg 4.0). OctoBot-MM treats HL as a generic CEX (D_avg 1.0).

### Recommendations
- **Do not run on testnet**: not worth the setup effort given the 2.86 score and zero HL-native awareness.
- **OctoBot ecosystem verdict**: **Not a viable Hummingbot alternative** for HL-focused work. It's a mature framework for generic multi-exchange retail trading with a clean UI, but the freemium model pushes serious MM capability behind paid cloud, and the HL integration is shallow. Hummingbot V2 remains the reference Python MM stack for HL.
- **Patterns worth borrowing for our custom bot**:
  - The **profile/distribution pattern** (a tiny launcher that pre-wires a config into a larger framework) is a useful deployment idiom.
  - The **web-dashboard-by-default** with notification wiring is a UX bar worth matching.
- **Evaluate fully**: a complete rubric pass would require cloning `Drakkar-Software/OctoBot` + tentacles and scoring the actual strategy implementation. Out of scope for the current HL-focused survey.
