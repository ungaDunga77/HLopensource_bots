# Roadmap

## Phase 0: Foundation
- [x] Create project structure (dirs, .gitignore)
- [x] Write bot catalog (docs/catalog.md)
- [x] Write evaluation rubric (docs/rubric.md)
- [x] Write security framework (docs/security-framework.md)
- [x] Write testing workflow (docs/testing-workflow.md)
- [x] Create evaluation template (evaluations/_template/)
- [x] Rewrite CLAUDE.md as lean hub
- [x] Create .env.example for testnet keys

## Phase 1: Security Tooling
- [x] Install audit tools into venv (pip-audit, safety, trufflehog, detect-secrets)
- [x] Write tools/clone_bot.sh (standardized clone + initial scan)
- [x] Write tools/scan_secrets.py (secret scanner wrapper)
- [x] Write tools/audit_deps.py (dependency auditor, auto-detects project type)
- [x] Write requirements.txt
- [x] Create sandbox/Dockerfile.python
- [x] Create sandbox/Dockerfile.node
- [x] Create sandbox/Dockerfile.rust
- [x] Create sandbox/docker-compose.yml (network isolation, resource limits)

## Phase 2: Tier 1 Evaluations
- [x] Clone + review Official SDK (hyperliquid-python-sdk) as reference baseline
- [x] Clone + audit Chainstack Grid Bot
- [ ] Clone + audit Passivbot
- [ ] Clone + audit Hummingbot (HL connector only)
- [ ] Complete evaluation scorecards for all Tier 1 bots

## Phase 3: Tier 2 Evaluations
- [ ] Evaluate HyperLiquidAlgoBot
- [ ] Evaluate Copy Trader (MaxIsOntoSomething)
- [ ] Evaluate Copy Trading Bot (gamma-trade-lab)
- [ ] Evaluate Grid Bot (SrDebiasi)
- [ ] Evaluate Market Maker (Novus-Tech-LLC)
- [ ] Evaluate Rust Bot (0xNoSystem)
- [ ] Evaluate Drift Arbitrage Bot (rustjesty)
- [ ] Comparative analysis of Tier 2

## Phase 4: Testnet Trials
- [ ] Set up HL testnet wallet
- [ ] Obtain testnet tokens (Chainstack faucet)
- [ ] Run top-scoring bots on testnet in Docker sandbox
- [ ] Collect performance data (24-48 hour minimum per bot)
- [ ] Document testnet results

## Phase 5: Synthesis
- [ ] Final rankings with scores
- [ ] Lessons learned compilation
- [ ] Decision: which bots to build upon / fork / combine
- [ ] Architecture plan for production bot(s)
