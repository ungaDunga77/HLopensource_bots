# Testing Workflow: Clone to Score

Step-by-step pipeline for evaluating a single bot. Each phase has a gate — the bot must pass before advancing.

---

## Pipeline Overview

```
RECON → CLONE & AUDIT → SANDBOXED BUILD → TESTNET TRIAL → SCORING
  |          |                |                 |              |
  |     never executed   built, not         runs against    fill rubric,
  |                      connected           testnet        update catalog
  |
  no code downloaded
```

---

## Phase 1: RECON

**Goal**: Decide whether to clone based on public information only.

1. Check GitHub repo metadata (stars, forks, contributors, last commit)
2. Read README and docs on GitHub web UI
3. Check contributor profiles for legitimacy
4. Scan for red flags (see security-framework.md)
5. **Gate**: Decide proceed or reject

**Output**: Update `docs/catalog.md` entry with metadata and status.

**Time**: ~15 minutes per bot.

---

## Phase 2: CLONE & STATIC AUDIT

**Goal**: Inspect source code without executing anything.

1. `git clone --depth 1 <repo> bots/<name>/`
2. Run secret scanning (grep for keys, URLs)
3. Run dependency audit (pip-audit / npm audit / cargo audit)
4. Manual code review using checklist (security-framework.md)
5. Document all network endpoints the bot connects to
6. Review order execution logic for safety (max size, rate limits, sanity bounds)
7. **Gate**: Decide proceed to build or reject

**Output**: `evaluations/<name>/security-audit.md`

**Time**: 30-60 minutes for simple bots, 2-4 hours for complex ones (Passivbot, Hummingbot).

---

## Phase 3: SANDBOXED BUILD

**Goal**: Verify the code builds and passes its own tests, without connecting to any exchange.

1. Build in Docker container with `--network=none`
2. Run included tests (pytest / npm test / cargo test)
3. Check for suspicious build hooks or startup scripts
4. Verify no unexpected files created
5. **Gate**: Build succeeds, tests pass, no suspicious activity

**Output**: `evaluations/<name>/build-notes.md`

**Time**: 15-30 minutes.

---

## Phase 4: TESTNET TRIAL

**Goal**: Run the bot against Hyperliquid testnet and observe behavior.

**Prerequisites**:
- Passed phases 1-3
- Docker sandbox configured
- Testnet wallet funded
- `HL_TESTNET=true` enforced

Steps:
1. Configure bot for testnet (dry-run first if available)
2. Start with minimal testnet capital
3. Monitor for 24-48 hours minimum
4. Log all trades, positions, errors
5. Verify network traffic (only HL testnet endpoints)
6. Check resource usage (CPU, memory)
7. **Gate**: Bot behaves as documented, no unexpected activity

**Output**: `evaluations/<name>/testnet-results.md`

**Time**: 24-48 hours (mostly passive monitoring).

---

## Phase 5: SCORING

**Goal**: Fill out the evaluation rubric and produce a final verdict.

1. Copy `evaluations/_template/evaluation.md` to `evaluations/<name>/evaluation.md`
2. Score each criterion based on evidence from phases 1-4
3. Calculate weighted final score
4. Write summary assessment
5. Update `docs/catalog.md` status column
6. Add any lessons to `docs/lessons.md`

**Output**: `evaluations/<name>/evaluation.md` (completed)

**Time**: 30 minutes.

---

## Evaluation Priority Order

| Priority | Bot | Rationale |
|----------|-----|-----------|
| 1 | Official SDK (hyperliquid-python-sdk) | Reference baseline, understand the API |
| 2 | Chainstack Grid Bot | Simplest Tier 1, uses official SDK, good docs |
| 3 | Passivbot | Most sophisticated, has optimizer + backtester |
| 4 | Hummingbot | Institutional quality, focus on HL connector only |
| 5 | Tier 2 bots | Parallel evaluation after learning from Tier 1 |
| 6 | Tier 3 bots | Quick reject most after Phase 1-2 |

---

## Directory Structure Per Bot

After full evaluation, each bot has:

```
evaluations/<name>/
  evaluation.md      — scored rubric (from template)
  security-audit.md  — Phase 2 findings
  build-notes.md     — Phase 3 results
  testnet-results.md — Phase 4 data (if bot reached this phase)
  notes.md           — freeform observations (optional)
```
