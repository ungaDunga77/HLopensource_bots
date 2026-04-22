# Evaluation: Hyper Alpha Arena (HammerGPT)

**Repo**: https://github.com/HammerGPT/Hyper-Alpha-Arena
**Evaluator**: Claude (automated)
**Date**: 2026-04-19
**Tier**: 2 (stars = 961; novelty: LLM-orchestrated agent platform)

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 3 | HL private keys encrypted with Fernet (`utils/encryption.py`), key auto-generated/persisted under `/app/data/.encryption_key` in Docker volume, or `HYPERLIQUID_ENCRYPTION_KEY` env. Supports agent-wallet mode (`key_type="agent_key"` with `master_wallet_address`) and strict testnet/mainnet env validation on every call (`EnvironmentMismatchError`). Keys never logged. Key file on shared volume is the weak spot: permissions not enforced in compose, single Fernet key for all users. |
| A2 | Dependency hygiene | 2 | `uv.lock` present (good), but no `package-lock.json` in frontend root (audit_deps flagged MEDIUM). 36 runtime Python deps, many unpinned `>=`. Heavy surface: `ccxt`, `hyperliquid-python-sdk`, `tavily-python`, `trafilatura`, `python-telegram-bot`, `discord.py`, `pandas-ta` beta (`0.4.67b0`). `eth-account >= 0.10.0` unpinned. No SBOM, no Dependabot config, no CI scanning. |
| A3 | Network surface | 2 | Large: FastAPI on :8802, PostgreSQL on :5432 exposed to host, outbound to HL API, Binance, Tavily web search, arbitrary OpenAI-compatible endpoints (user-configurable base URL — prompt-exfiltration vector), Telegram, Discord, Hyper Insight SaaS (`hyper.akooi.com`), news feeds, `trafilatura` web scraping. LLM can be pointed at attacker-controlled endpoint and given full trading context. |
| A4 | Code transparency | 3 | Apache-2.0, all sources readable. No obfuscation. BUT: single squashed commit ("Add Hyper AI harness safeguards" by "Admin", 2026-04-15) — entire 254-file Python backend and frontend arrived in one commit with no prior history. Upstream claims to be a fork of `etrobot/open-alpha-arena` but history was wiped. Repackaging from an unpublished internal fork is a supply-chain concern. `.backup` file committed (`hyperliquid_trading_client.py.backup`). |
| A5 | Input validation | 3 | LLM output: `json.loads` with markdown stripping + regex fallback for `operation/symbol/target_portion/reason` — no JSON-schema or function-calling enforcement. However, downstream gate is reasonable: operation enum `{buy,sell,hold,close}`, symbol whitelist check against watchlist, `0 < target_portion <= 1`, leverage clamped to `default_leverage` if out of `[1, max_leverage]`, price bounds enforced against market price (`_enforce_price_bounds`), invalid decisions saved with `executed=False`. `program_trader/validator.py` uses AST walk to block `os/sys/subprocess/eval/exec/open/__import__/getattr/...` and restricted builtins dict — decent but AST filters are bypassable (e.g. `().__class__.__mro__` gadgetry not blocked). |
| | **A average** | **2.6** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 2 | **LLM-angle**: "strategy" = natural-language prompt user writes describing intent, fed to an OpenAI-compatible model with a loosely specified JSON-output contract. Prompt assembly injects portfolio, positions, klines, news, factors, regime — lots of variables (`_parse_factor_variables`, `_parse_kline_indicator_variables`). Decision schema is *described in English inside the prompt*, not enforced with tools/function-calling/response_format. No guarantee the model obeys the schema; parser has triple-fallback (json → cleaned-json → regex-field-extract) which masks hallucinations instead of failing closed. Multi-agent claim (Hyper AI, Signal AI, Prompt AI, Program AI, Attribution AI) is configuration/UX routing — not independent agents that vote; no conflict resolution, no ensembling. |
| B2 | Backtesting | 3 | Dedicated `backend/backtest/` + `prompt_backtest_service.py` + `program_trader/backtest.py`. Factor effectiveness (IC/ICIR, win rate, decay half-life) via `factor_effectiveness_service.py`. Realistic — uses historical klines. Program-trader backtester validates before live. Prompt backtesting for LLM strategies is approximation only (model replay nondeterministic). |
| B3 | Risk management | 2 | Position-size cap via `target_portion <= 1.0` of available balance, leverage clamp, max/min price bounds with deviation logging, TP/SL via native HL trigger orders (maker-first then market fallback), `_tpsl_cache` to prevent duplicate TPSL. BUT: no account-level max drawdown, no daily loss limit, no circuit breaker, no per-symbol concentration limit, no LLM cost/budget cap, no rate limit on decision frequency beyond APScheduler period. Hallucination guard relies entirely on the symbol whitelist; a model saying `"buy $1,000,000 notional"` is caught only because `target_portion` is bounded (if the model obeys the field name). |
| B4 | Configurability | 4 | Very flexible: multi-account, per-account watchlists, leverage settings per HL wallet, testnet/mainnet per wallet, arbitrary OpenAI-compatible models (GPT-5 / Claude / Deepseek / Gemini with thinking budget), 86 built-in factors + expression engine, signal triggers (CVD, OI, funding), per-strategy prompts. Configuration surface is enormous. |
| B5 | Monitoring | 4 | `AIDecisionLog` persists every decision with `_reasoning_snapshot`, `_raw_decision_text`, `_prompt_snapshot`, executed flag, realized PnL — strong audit trail. Trade attribution by symbol / trigger / factor. Telegram + Discord bots for proactive alerts. System logger, analytics routes, asset-curve snapshots. Verbose logging throughout. |
| | **B average** | **3.0** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 1 | Only `program_trader/test_module.py` (a single file) and `scripts/validate_program_api.py`. No pytest suite despite `pytest` in dev deps. No CI. 254 Python files, ~1 test file. `verify_trades_display.py` is a manual verification script, not a test. |
| C2 | Error handling | 3 | **LLM-angle**: hallucinated ticker → caught by `symbol not in symbol_whitelist` → logged + `save_ai_decision(executed=False)`; does not crash trader. Invalid JSON → three-level fallback (cleanup → regex extraction); if all fail, returns `None` and skips cycle. Missing `max_price`/`min_price` → uses market price with a WARNING log (called "AI COMPLIANCE ISSUE") but still executes — soft enforcement. Network errors, CCXT exceptions, and SDK failures wrapped in try/except with logging. Weak spots: `float(decision.get("target_portion_of_balance", 0))` crashes on non-numeric; no timeout on LLM call is visible in the snippets; TPSL cache silently masks API latency issues. |
| C3 | Documentation | 3 | Marketing-heavy README (English + Chinese), docs hosted on `akooi.com`, `HYPERLIQUID_UPGRADE_GUIDE.md`, `HYPERLIQUID_FRONTEND_IMPLEMENTATION.md`. Docstrings on most services. No architecture doc mapping the 80+ services, no prompt-contract reference, no threat model. |
| C4 | Code quality | 2 | ~9.5k lines across the four critical files alone (`ai_decision_service.py` 3538 LoC, `hyperliquid_trading_client.py` 3574, `trading_commands.py` 1764). God-files, deep branching, duplicated buy/sell/close blocks, leftover `.backup` file committed. `auto_trader.py` is a 36-line re-export shim for back-compat — signals recent refactor mid-flight. Chinese+English log/comment mix. No type-checker config. Variable names reasonable, dataclasses used in `program_trader`. |
| C5 | Maintenance | 2 | Single squashed commit in public repo = effectively zero public maintenance history. Commercial product backing (akooi.com, paid Hyper Insight integration, Discord/Telegram community) suggests active *private* development but the OSS release cadence and transparency are poor. Version `0.9.10`. Apache-2.0 plus NOTICE file. |
| | **C average** | **2.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | Uses official `hyperliquid-python-sdk>=0.20.0` plus `ccxt.hyperliquid` as fallback for balance/positions. Custom EIP-712 signing logic with `eth_account` version-compat shim (`encode_typed_data` vs `encode_structured_data`). Testnet/mainnet URLs hardcoded correctly. Address lowercased per HL docs. Rate limit 100ms between CCXT calls. HIP-3 markets explicitly disabled. |
| D2 | Testnet support | 5 | First-class: `EnvironmentMismatchError` raised if account env doesn't match client env; testnet and mainnet wallets are separate DB rows with independent keys; builder-fee config only applies on mainnet; CCXT `sandbox=True` plumbed correctly; README leads with testnet paper trading. |
| D3 | HL features | 4 | **HL-angle**: This is NOT a generic-exchange-with-HL-sticker bot. Actively uses: native TP/SL trigger orders with maker-first + market fallback (`tp_execution`/`sl_execution`), builder fees (premium-rate = 0 code path for specific addresses), agent wallet mode (`master_wallet_address` + signing key separation), per-symbol leverage configuration, TIF (Ioc/Gtc), cross/isolated margin awareness via `unifiedAccount`/`portfolioMargin` modes, liquidation-price warnings (claimed in README). Missing: vaults, subaccounts, HIP-3, spot, TWAP, scheduled cancel. Binance Futures is the co-equal venue, so HL isn't uniquely exploited, but HL-specific primitives are clearly first-class. |
| | **D average** | **4.3** | |

---

## Final Score

```
Final = (A_avg * 0.4) + (B_avg * 0.3) + (C_avg * 0.2) + (D_avg * 0.1)
      = (2.6   * 0.4) + (3.0   * 0.3) + (2.2   * 0.2) + (4.3   * 0.1)
      = 1.04 + 0.90 + 0.44 + 0.43
      = 2.81
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [x] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

Hyper Alpha Arena is an ambitious, feature-dense LLM trading platform (FastAPI + React + Postgres, 254 Python files, Docker-first) with genuinely deep Hyperliquid integration — native TP/SL trigger orders, builder fees, agent wallets, strict testnet/mainnet isolation — and comprehensive decision telemetry. However, the LLM decision pipeline is free-text JSON parsed with a triple-fallback (json → cleanup → regex), not schema-enforced via function-calling or `response_format`; multi-agent architecture is marketing language for task-routed chatbots rather than an ensemble; and the public repo is a single squashed "Admin" commit, masking the real development history of a commercial product (`akooi.com`). Downstream validation (symbol whitelist, target_portion bounds, price deviation, leverage clamp) prevents the worst hallucinations from reaching the exchange, but there is no account-level risk ceiling, no LLM cost budget, and essentially no automated tests. Useful as a reference for HL-feature coverage and decision-logging schema; not recommended as a foundation for a custom bot.

## Key Findings

### Strengths
- **HL-native feature use**: TP/SL trigger orders (limit-first, market fallback) via SDK, builder-fee plumbing, agent-wallet mode with separate signing/query addresses, strict `EnvironmentMismatchError` across the client.
- **Decision telemetry**: every LLM decision persisted to `AIDecisionLog` with prompt snapshot, raw response, reasoning, executed flag, and realized PnL — excellent post-hoc analysis surface.
- **Program Trader sandbox**: AST-based validator for user Python (forbidden imports/functions, restricted builtins dict, timeout via ThreadPoolExecutor) is a reasonable first line of defense.
- **Fernet-encrypted private keys** at rest, agent-wallet support, testnet/mainnet DB-row separation.
- **Backtest layer for LLM prompts and program strategies**, plus factor IC/ICIR effectiveness scoring.

### Concerns
- **Single squashed commit** (`Admin`, 2026-04-15) on a 961-star repo — full development history wiped. Claims to fork `etrobot/open-alpha-arena` but carries none of that lineage. Supply-chain opacity.
- **LLM output is not schema-enforced**: no function-calling, no `response_format={"type":"json_object"}`, no pydantic validation of decisions before the symbol/portion gates. Regex fallback for missing JSON can fabricate a decision from any prose containing the right quoted keys.
- **Prompt-injection surface is wide**: news feeds, web-search results (Tavily + trafilatura), Hyper Insight wallet data, and user-configurable OpenAI base URL all flow into prompts; a malicious base-URL config can exfiltrate prompts+context to any attacker endpoint.
- **Default `temperature=0.7`** for decision LLM — no determinism, no seed, no sampling controls surfaced. Same market state → different trades.
- **No LLM cost budget, rate limit, or daily-loss circuit breaker**. Risk management is per-order only.
- **"Multi-agent" is routing, not ensemble**: no voting, no conflict resolution, no independent verifiers on the trade path.
- **God-files** (3.5k LoC ai_decision_service, 3.5k LoC HL client), .backup file committed, 1 test file across 254 Python files, mid-refactor shim (`auto_trader.py`).
- **Soft "AI compliance" warnings**: when the model omits `max_price`/`min_price`, the system logs a warning and executes at market anyway — the design nudges rather than enforces.
- **Broad outbound surface** (Tavily, Telegram, Discord, Hyper Insight SaaS, arbitrary LLM endpoints, news/web scrapers) makes network-isolation sandboxing mandatory.

### Recommendations
- **Reference only**. Don't run outside Docker with network egress restricted.
- Two worthwhile patterns to adopt in the custom bot:
  1. **`AIDecisionLog` schema** (prompt snapshot + raw response + reasoning + executed flag + realized PnL) — clean separation of *intended* vs *executed* decision, ideal for post-hoc analysis.
  2. **Environment-mismatch invariant** — raising on every client call if account env ≠ client env is a cheap, high-value guard that eliminates an entire class of testnet↔mainnet mistakes.
- If building an LLM-driven bot: use function-calling / structured outputs (OpenAI `tools` or Anthropic `tool_use`) with pydantic validation, set `temperature=0`, budget calls, log everything, and never let regex fallbacks fabricate decisions.
- Do **not** adopt this platform's prompt-assembly pipeline — the "inject news/factors/klines as plaintext into the system prompt" pattern is a live prompt-injection channel.
- The 961 stars correlate with marketing reach (akooi.com brand, nof1 Alpha Arena framing, Chinese+English community), not engineering rigor. Discount accordingly.
