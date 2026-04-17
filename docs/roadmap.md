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
- [x] Clone + audit Passivbot
- [x] Clone + audit Hummingbot (HL connector only)
- [x] Complete evaluation scorecards for all Tier 1 bots

## Phase 3: Tier 2 Evaluations
- [x] Evaluate HyperLiquidAlgoBot
- [x] Evaluate Copy Trader (MaxIsOntoSomething)
- [x] Evaluate Copy Trading Bot (gamma-trade-lab)
- [x] Evaluate Grid Bot (SrDebiasi)
- [x] Evaluate Market Maker (Novus-Tech-LLC) — recovered from fork, scored 1.47
- [x] Evaluate Rust Bot (0xNoSystem)
- [x] Evaluate Drift Arbitrage Bot (rustjesty)
- [x] Comparative analysis of Tier 2

## Phase 4: Testnet Trials
- [x] Set up HL testnet wallet (MetaMask master, not agent)
- [x] Obtain testnet tokens (official drip, $999 mock USDC)
- [x] Add uv support to Dockerfile.python (Python 3.13)
- [x] Add bot-testnet-chainstack service to docker-compose.yml
- [x] Patch SDK spot_meta bug in Chainstack adapter
- [x] Chainstack Grid Bot: live on testnet, 5-level BTC grid placing orders
- [x] Build shadow-data tooling (tools/shadow_collector.py, tools/shadow_analyze.py) — independent ground-truth P&L from `user_fills` since bot's own reporting is broken (see testnet-results Issues #5, #6)
- [x] Chainstack Grid Bot: 25h trial complete, 2 fills, report at evaluations/chainstack-grid-bot/shadow/report-20260416-final.md
- [x] Document Chainstack testnet results
- [x] Hummingbot testnet trial prep: compose service, seed script, script config
- [ ] Hummingbot testnet trial: build image, seed conf, smoke test, 24h run
- [ ] Passivbot testnet trial (needs testnet support patched in)
- [ ] Reuse shadow-data tooling for Hummingbot + Passivbot trials (collector is bot-agnostic; only `--bot-container` changes)

## Phase 5: Synthesis
- [ ] Final rankings with scores
- [ ] Lessons learned compilation
- [ ] Decision: which bots to build upon / fork / combine
- [ ] Architecture plan for production bot(s)
