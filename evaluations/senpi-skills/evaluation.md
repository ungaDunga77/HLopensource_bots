# Evaluation: senpi-skills

**Repo**: https://github.com/Senpi-ai/senpi-skills
**Evaluator**: Claude (automated triage)
**Date**: 2026-04-22
**Tier**: 3 (classification: substantively HL-related but NOT a runnable OSS bot — open-source *strategy catalog* for a proprietary MCP/runtime platform)
**Stars**: 70

---

## Triage verdict

**Upgraded from honorable-mention "skip" to a light full eval.** The repo turned out to be much more HL-native than the adjacency risk suggested. It is Senpi's publicly open-sourced *strategy library* — 52+ "animal" agents (cobra, grizzly, polar, scorpion…) authored as scanner scripts + `runtime.yaml` that plug into Senpi's proprietary **plugin runtime + DSL exit engine + Hyperfeed data layer** and trade live on Hyperliquid. ~48K Python LOC, MIT.

**Key constraint for us:** the skills are *not* runnable outside the Senpi platform. Execution requires (a) an OpenClaw agent host, (b) Senpi MCP access token (48 tools), (c) Hyperfeed proprietary data feed, and (d) the closed-source position_tracker + DSL plugin. The Python scanners are `stdlib-only` scoring scripts that emit JSON decisions for the runtime to execute via MCP. There is no private-key handling, no HL SDK call, no testnet path — all of that lives in the closed runtime.

So: **no testnet trial possible, D score will be artificially low, but the design patterns are valuable** — especially for the LLM-orchestration question raised by Hyper-Alpha-Arena's `AIDecisionLog` pattern.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 5 | No private keys handled in this repo at all. Scanners are pure-Python scoring functions. All key material lives in the closed Senpi runtime, outside scope. `secret-scan.json`: 0 critical, 0 high, 0 total findings. |
| A2 | Dependency hygiene | 5 | `No external dependencies — all scanners use stdlib only` (README, line 297). No `requirements.txt`, no `package.json`, no `pyproject.toml`. Attack surface is minimal. |
| A3 | Network surface | 5 | Scanners don't open sockets. They read stdin/env, print JSON to stdout. Runtime does all networking via MCP. |
| A4 | Code transparency | 4 | Scanner logic is fully open and readable. But the *execution layer* (Senpi runtime, DSL engine, MCP tool implementations, Hyperfeed data pipeline) is all closed. You can inspect the thesis, not the trader. |
| A5 | Input validation | 3 | Scanner inputs come from Senpi MCP tool outputs (trusted-ish). Defensive `safe_float`, `try/except` on JSON decode and state files. XYZ asset banning at parse level. No adversarial input hardening because threat model assumes MCP is trusted. |
| | **A average** | **4.4** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 5 | Each skill has a SKILL.md with explicit thesis, entry rules, leverage/margin, DSL config, and CRITICAL AGENT RULES block. Example: cobra's "ONE position, #1 SM asset, $400 @ 10x, 3 entries/day, 90-min cooldown." Exceptionally well-documented thesis per agent. |
| B2 | Backtesting | 2 | No backtests in the repo. `_analysis/fleet-dossiers.md` and `experiment-registry.md` are observational fleet analytics from live trading, not reproducible backtests. Strategies are validated by running real capital on Arena. |
| B3 | Risk management | 5 | Strong and shared across agents: two-phase DSL trailing stop (Phase 1 loss protection with `consecutiveBreachesRequired: 3` to suppress noise, Phase 2 profit ratchet tiers), hard timeout, dead-weight-cut, weak-peak-cut, `FEE_OPTIMIZED_LIMIT` maker-first execution, per-asset cooldowns, daily entry caps, XYZ-equity parse-level bans. Architectural rule "scanners enter, DSL exits, never both" is well-reasoned. |
| B4 | Configurability | 5 | 52+ drop-in strategies with varied theses (single-asset lifecycle, multi-asset SM scanners, Arena-optimized, intelligence-signal, specialized fading/funding/volume). `runtime.yaml` exposes DSL tiers, intervals, budget, slots, margin, leverage. `catalog.json` drives UX. |
| B5 | Monitoring | 4 | Telegram alerts configured via runtime, [strategies.senpi.ai](https://strategies.senpi.ai) fleet tracker (external), per-skill performance attribution via `skill_name`/`skill_version` on every `strategy_create` call. No in-repo logs/metrics code — observability is a runtime responsibility. |
| | **B average** | **4.2** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | No test suite. No `tests/` dir, no `pytest.ini`. Strategies are validated in production against live capital. |
| C2 | Error handling | 3 | Scanners defensively wrap JSON parse, state-file IO, float coercion. Failures degrade to NO_REPLY rather than bad trades. But no structured logging, no retry strategy visible in-repo. |
| C3 | Documentation | 5 | Exceptional. Top-level README (306 lines) is a fleet primer; every skill has SKILL.md + README + `references/`. DSL has its own spec documents (`dsl-high-water-implementation-spec.md`, etc.). CLAUDE.md even documents conventions for AI editors of the repo. |
| C4 | Code quality | 4 | Readable, docstrings everywhere, clear module structure. Shared helpers in `shared/hyperfeed_scoring.py`. Some redundancy across 52 scanners is inevitable. No linter/formatter config though. |
| C5 | Maintenance | 4 | Actively maintained (recent additions: Hyperfeed v2 scoring fields 2026-04-06, catalog.json updated 2026-03-11, v2.0+ agent family). MIT license. 70 stars is modest. |
| | **C average** | **3.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 1 | Zero direct use of `hyperliquid-python-sdk` or any HL SDK. All HL interaction is proxied through Senpi MCP (closed source). Positions created via `strategy_create_custom_strategy` MCP tool. |
| D2 | Testnet support | 0 | No testnet path. Runtime is production-mainnet oriented; strategy wallets are real funded wallets. No way to dry-run. |
| D3 | HL features | 3 | Indirectly uses HL features through Senpi: FEE_OPTIMIZED_LIMIT (maker-first + taker fallback), leverage management, cross-margin buffer math. But usage is opaque — you can't audit the actual order construction. |
| | **D average** | **1.3** | |

---

## Final Score

```
Final = (4.4 * 0.4) + (4.2 * 0.3) + (3.2 * 0.2) + (1.3 * 0.1)
      = 1.76 + 1.26 + 0.64 + 0.13
      = 3.79
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening — **but NOT runnable OSS; value is pattern harvesting, not deployment**
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

senpi-skills is a genuinely impressive open-source *strategy catalog* for a closed-source Hyperliquid platform. The 52+ agent designs, the "scanners enter, DSL exits, never both" architectural rule, and the `runtime.yaml` + DSL preset schema are all high-quality design artifacts worth studying. But as a self-contained OSS bot for our evaluation pipeline it's a non-starter: execution requires the Senpi runtime, Senpi MCP, Hyperfeed data, and a funded mainnet wallet — none of which are OSS or testnet-accessible. Score 3.79 is dragged down by D (no SDK use, no testnet) and C1 (no tests); it would be ~4.4 if scored purely as a strategy library.

## Key Findings

### Strengths
- **Clean separation of concerns**: scanners (entry logic, stdlib-only, stateless per run) vs DSL engine (exits, shared, timer-driven) vs runtime (execution via MCP). Each agent is a single Python file + YAML.
- **DSL two-phase trailing stop** with `consecutiveBreachesRequired` noise-suppression is a nicely thought-out risk primitive — directly portable to our own bot.
- **`FEE_OPTIMIZED_LIMIT`** (maker-first with taker fallback at 30s) is a ~50% fee reduction vs naive taker and a pattern worth cloning.
- **Scanner output schema is uniform**: every agent emits the same DSL-state JSON (`highWaterPrice: null`, `absoluteFloorRoe: null`, tiers array). This canonical shape is the connective tissue between 52 diverse strategies and one exit engine.
- **Attribution protocol** (`skill_name` + `skill_version` on every `strategy_create*` call) is a clean way to track fleet performance back to thesis.

### Concerns
- **Not OSS-runnable.** Everything that actually touches HL is behind Senpi MCP. You can read the thesis but not run it.
- **No tests, no backtests.** Strategies are validated with live capital on the Arena. That's fine for Senpi but unusable for us.
- **Prompt-injection channel risk is likely present** in the broader Senpi platform (LLM-driven orchestration consumes MCP outputs), but not visible in this repo because the LLM-orchestration layer is closed source. This is the same pattern to be wary of per Hyper-Alpha-Arena's lesson.
- **Mainnet-only.** No testnet scaffolding for skill authors — a skill "works" or it doesn't once deployed with real capital.

### Recommendations
- **Do not run.** No sandbox/testnet trial possible; no reason to even try.
- **Harvest patterns for the custom bot design notes**:
  1. **DSL Phase-1/Phase-2 state machine** with null-sentinel initialization (`highWaterPrice: null`, `absoluteFloorRoe: null`) and consecutive-breach counter → adopt as our own exit primitive.
  2. **Scanner/executor separation** as a structural rule: decision code never calls the exchange, and position management never re-evaluates thesis. Pair with a tested executor module.
  3. **Fee-optimized maker-first-then-taker** order wrapper — cheap to implement against `hyperliquid-python-sdk` and immediately yields measurable PnL.
  4. **Per-strategy cooldown + daily entry cap** state files (with graceful reset on `date` rollover). Small, easy, prevents churn bugs.
  5. **Uniform decision-output JSON schema** across strategies → one executor, many strategies. This is the architectural complement to Hyper-Alpha-Arena's `AIDecisionLog` (decision_in vs decision_executed separation).
- **Adjacency line for future searches:** repos that are (a) "skill catalogs" or "strategy packs" for closed platforms, or (b) "agent skills" frameworks without direct exchange SDK usage, are **triage-only** — worth a read-through for patterns but not a full eval or testnet trial. senpi-skills is the high watermark for this category; most such repos will score lower on A-C.

### Relationship to Hyper-Alpha-Arena's AIDecisionLog question

The honorable-mentions plan asked whether senpi-skills is worth reviewing "if HAA's `AIDecisionLog` pattern suggests LLM-orchestration is a direction we want to explore deeper." Answer after this triage: **senpi-skills is not the LLM-orchestration reference we were looking for** — the actual LLM loop is in Senpi's closed runtime, not in this repo. What senpi-skills *does* provide is the complementary piece: a clean **strategy catalog schema** and a **shared exit engine** to pair with any decision layer (LLM or rule-based). So the two sources complement rather than overlap: HAA = how to log/structure LLM decisions; senpi-skills = how to structure N thesis-diverse strategies behind one executor + exit engine. Both patterns are worth carrying into the custom bot design.
