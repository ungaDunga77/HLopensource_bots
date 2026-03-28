# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Systematic evaluation of open-source Hyperliquid trading bots. Research project, not production deployment. Python 3.12 with venv.

## Setup

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Key Docs

- [docs/catalog.md](docs/catalog.md) — Bot registry (18 bots, tiered 1-3)
- [docs/rubric.md](docs/rubric.md) — Evaluation scoring (security 40%, functionality 30%, engineering 20%, HL integration 10%)
- [docs/roadmap.md](docs/roadmap.md) — Phased TODO
- [docs/lessons.md](docs/lessons.md) — Accumulated findings
- [docs/security-framework.md](docs/security-framework.md) — Security audit methodology
- [docs/testing-workflow.md](docs/testing-workflow.md) — Clone-to-score pipeline

## Repo Layout

- `bots/` — Cloned repos (gitignored, ephemeral — never committed)
- `evaluations/` — Scored results per bot (version controlled)
- `evaluations/_template/` — Blank scoring template
- `tools/` — Audit and scanning scripts
- `sandbox/` — Docker configs for isolated testing

## Rules

- NEVER use mainnet keys. Testnet only.
- NEVER run cloned bot code outside Docker sandbox.
- NEVER commit cloned bot code (bots/ is gitignored).
- Security audit BEFORE any code execution.
- All evaluation results go in `evaluations/<bot-name>/`.
