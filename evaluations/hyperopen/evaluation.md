# Evaluation: hyperopen

**Repo**: https://github.com/thegeronimo/hyperopen
**Evaluator**: Claude (static eval, Phase 5 honorable mentions batch)
**Date**: 2026-04-22
**Language**: ClojureScript (compiles to JS via shadow-cljs), targets browser
**License**: AGPL-3.0
**Commit evaluated**: `7aed07c` (2026-04-21)
**Tier**: 2

---

## Orientation note

hyperopen is **not a bot in the automated-trading sense**. It is a community-built, full-featured ClojureScript *web frontend* for Hyperliquid (trade UI, orderbook, portfolio tearsheets, vault analytics, funding flows). The user runs it in a browser; the "bot"-like surfaces are order submission and vault deposit/withdraw, both human-initiated. It is included in this honorable-mentions batch for two novelty axes: (a) a stack no other evaluated project uses (Clojure/JVM + Replicant + Nexus + shadow-cljs), and (b) first-class **HL vault analytics** (performance tearsheets, benchmarking against BTC/HYPE/HLP with CAGR, Sharpe, drawdown). Evaluated statically only; no code was executed.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 4 | Agent-session model with passkey-based unlock (WebAuthn PRF extension) via `wallet/agent_lockbox.cljs`. Private key is never the mainnet wallet key — it is an agent wallet the user approves on HL. Keys never hit the server (pure static frontend). Explicit policy in `docs/SECURITY.md`: "MUST keep signing diagnostics non-sensitive… MUST NOT log raw private keys." Dedicated `agent_safety.cljs` prevents destructive invalidation on ambiguous errors. Minor: agent key ultimately decrypted into JS memory in-browser, which inherits browser-tab threat model. |
| A2 | Dependency hygiene | 4 | `package.json` is small (9 runtime deps, notably `@noble/secp256k1` for signing — audited library, good choice). `audit_deps.py` reports 0 known vulnerabilities; 10 LOW findings are all caret-range pinning notes. `deps.edn` has minimal Clojure deps. Note: `@openai/agents` is pulled in — likely for LLM copilot features; not executed in hot trading paths from what I could see. |
| A3 | Network surface | 4 | Talks directly to `api.hyperliquid.xyz/exchange` and `/info` from the browser. No custom backend proxy (except an optional HyperUnit proxy for funding flows and verify:deployment-headers for CSP/CSRF posture at deploy time). Explicit `_headers` policy file generated on build (CSP, anti-framing, cache rules). WebSocket runtime has an explicit ACL layer (`websocket/acl/hyperliquid.cljs`) normalizing payloads before they enter domain state. |
| A4 | Code transparency | 5 | Exceptional. Architecture, reliability, security, browser-storage, quality, and product docs are all in-repo and maintained. 186 ADRs. Every domain has a `BOUNDARY.md`. Contributor-facing; nothing is hidden behind obfuscated builds. |
| A5 | Input validation | 4 | `schema/contracts.cljs` + runtime assertions (`contracts/assert-exchange-response!`) validate exchange responses at the boundary. `vaults/domain/transfer_policy.cljs` uses typed parsing (e.g. `parse-usdc-micros` guards against `Number.MAX_SAFE_INTEGER` overflow and integer fidelity — a genuinely mature pattern). `hl_signing.cljs` enforces integer fidelity for `oid`, nonces, asset indexes. |
| | **A average** | **4.2** | |

Secret-scan findings (1349 MEDIUM, 42 CRITICAL) are **all test fixtures, Portfolio/workbench scenes, or generated docs** (dummy keys like `0xaaaa…aaaa`, `0xcccc…cccc`). No real secrets present.

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 2 | N/A — this is a trading UI, not an automated strategy. Order entry is human-driven. Deterministic state machines for the order form (`trading/order_form_*.cljs`) are well-modeled but embody no strategy. |
| B2 | Backtesting | 3 | No backtester, but vault **performance tearsheets** with CAGR, Sharpe, drawdown, and benchmark-vs-BTC/HYPE/HLP (`vaults/detail/performance.cljs`, `benchmarks.cljs`) are essentially offline analytics — the closest analogue. |
| B3 | Risk management | 3 | TP/SL policy in `trading/order_form_tpsl_policy.cljs`; `submit_policy.cljs` gates submissions. No automated risk loop — it's UI-enforced guards (min notional, balance checks, deposit allowlist for vaults via `vault-transfer-deposit-allowed?`). |
| B4 | Configurability | 3 | Config surface is feature flags and preferences (`config.cljs`, `trading_settings.cljs`). Good for a UI, limited for a bot analogue. |
| B5 | Monitoring | 4 | Dedicated `telemetry.cljs` + telemetry namespace, structured websocket runtime with explicit lifecycle stages, and reliability invariants documented as gates that CI enforces. |
| | **B average** | **3.0** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 5 | 562 `.cljs` test files vs 629 source files — near-parity. Badges in README for tests-total and assertions-total. Playwright smoke + SEO suites. `test:websocket` dedicated suite. Test/source ratio is the highest seen across all 19 bots evaluated. |
| C2 | Error handling | 5 | Errors normalized at a single boundary into typed categories (`api/errors.cljs`), explicit nonce-error detection, idempotent effect handlers by policy, explicit credential-invalidation rules with "do not destructively invalidate on ambiguous errors." |
| C3 | Documentation | 5 | README, ARCHITECTURE.md, 17 docs under `docs/`, 186 ADRs, per-module `BOUNDARY.md` files. Design, reliability, security, storage, and quality all documented. Top of class. |
| C4 | Code quality | 4 | Strict architecture governance: <500 LOC per namespace, <80 LOC per function, enforced via `npm run check`. Pure/effect separation (Replicant + Nexus) is textbook DDD + hexagonal. Minus 1 because Clojure pool is small — operational bus factor risk. |
| C5 | Maintenance | 5 | Most recent commit: 2026-04-21 (yesterday). Active Telegram community, CI badges, issue tracker via beads (`bd`). |
| | **C average** | **4.8** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 4 | No Clojure HL SDK exists, so they rolled their own: EIP-712 signing via `@noble/secp256k1` + custom msgpack + keccak in `utils/hl_signing.cljs` (478 LOC). Explicitly cross-references three reference SDKs (nktkas, nomeida, official Python SDK) and requires parity tests for any signing change. |
| D2 | Testnet support | 3 | chainId 1337 for L1 signing; exchange URL is hard-coded to mainnet `api.hyperliquid.xyz`. Testnet would need a flag (not obvious one exists). `debug_exchange_simulator.cljs` provides an offline simulator for tests. |
| D3 | HL features | 5 | Broadest HL-feature coverage of any bot evaluated: perps trading, orderbook, charting, portfolio, funding, **vaults (deposit/withdraw + analytics + leader policy)**, staking, leaderboard, api-wallets (agent wallets), usd-class-transfer, token-delegate, c-deposit/c-withdraw, withdraw, send-asset. The EIP-712 field definitions in `hl_signing.cljs` enumerate nearly the full HL exchange action surface. |
| | **D average** | **4.0** | |

---

## Final Score

```
Final = (4.2 * 0.4) + (3.0 * 0.3) + (4.8 * 0.2) + (4.0 * 0.1)
      = 1.68 + 0.90 + 0.96 + 0.40
      = 3.94
```

**Tier 2** (3.0–3.9). Right at the Tier 1 boundary; functionality score drops it because it is a UI client, not a strategy engine — on pure engineering and HL coverage it is stronger than most Tier 1 entries.

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [x] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [ ] < 2.0: Avoid

## Summary

hyperopen is a mature, well-architected open-source *trading frontend* for Hyperliquid, not an automated bot. It is the strongest engineering effort in the entire corpus evaluated so far: ~1:1 test-to-source ratio, 186 ADRs, strict DDD boundaries enforced by CI, passkey-based agent-wallet lockbox, and EIP-712 signing implemented from scratch with parity-testing discipline against three reference SDKs. As a "bot" analogue it scores modestly (no strategy, no backtester), but as a **reference implementation of the HL exchange action surface and vault integration** it is exceptional.

## Key Findings

### Strengths
- Best-in-class engineering practices: strict architecture governance, test parity, ADRs, boundary docs
- Full HL action surface implemented (including vaults, staking, sub-accounts, sends, delegation, c-deposit/withdraw)
- Novel key-management: WebAuthn passkey + PRF-derived lockbox for agent-session keys, instead of raw key storage
- Vault analytics (performance tearsheet, CAGR/Sharpe/drawdown, benchmark-vs-HLP) is unique among evaluated bots

### Concerns
- AGPL-3.0: direct reuse in a proprietary custom bot is blocked; patterns only
- Clojure/JVM stack is niche — bus-factor and maintenance-contributor risk
- Not a bot: no automated strategy loop; any automation use requires pairing it with a separate executor
- Exchange URL hard-coded to mainnet; testnet switching is not a first-class flag
- Browser-tab threat model inherent to any in-browser signer (passkey unlock mitigates but does not eliminate)

### Recommendations
- Include hyperopen in the custom-bot design-notes consolidation as the reference for HL exchange-action coverage and EIP-712 signing field definitions
- Do not attempt direct code reuse; port patterns only (AGPL)
- Worth revisiting quarterly — velocity is very high (daily commits), vault tooling likely to deepen

## Tooling gaps hit

1. **`audit_deps.py` detected only the Node side** (`package.json`) and silently ignored `deps.edn` (Clojure/JVM manifest). Confirmed by inspecting output: `"languages": ["node"]`. For Clojure bots we currently have no dependency vulnerability signal. Adding `deps.edn` / `project.clj` parsing (mapping to nvd.clojars.org or a maven-central lookup) is the obvious next step.
2. **`scan_secrets.py` very noisy on this codebase** (1349 MEDIUM, 42 CRITICAL, 22 HIGH). Every finding was in test fixtures, `portfolio/workbench/` UI mock scenes, or generated docs — the patterns `0xaaaa…aaaa`, `0xbbbb…bbbb`, `0xcccc…cccc`, `0xdddd…dddd` are clearly test placeholders. A simple "all-same-digit" heuristic would filter 100% of the criticals here. (This is a known item in the user's `feedback_tooling_improvements.md` memory.)
3. Two-stage clone gate rejected the repo on Stage 2 (as expected for any repo with realistic test vectors) — the fallback documented behavior (keep clone, manual review) worked correctly.

---

## Patterns for custom bot

Do NOT modify `docs/custom-bot-design-notes.md`; listing here for session consolidation.

1. **Agent-wallet + passkey lockbox (A1/A3)**. hyperopen never holds the user's main wallet key. User approves an *agent wallet* on HL, the agent private key is encrypted with a WebAuthn PRF-derived key, and unlock requires a passkey touch. Python analogue: agent wallet approved via SDK, stored encrypted-at-rest via `cryptography.fernet` keyed from OS keyring (macOS Keychain / Linux Secret Service / `pass`), unlocked once per session. This is strictly better than dotenv-style `PRIVATE_KEY=…`.
2. **EIP-712 field dictionary as ground truth (D1/D3)**. `hl_signing.cljs` enumerates every HL signable action (`approve-agent`, `usd-class-transfer`, `send-asset`, `c-deposit`, `c-withdraw`, `token-delegate`, `withdraw`, plus L1 action types). Port this list to a `docs/hl_action_surface.md` so our custom bot's action coverage is a checklist, not an emergent property.
3. **"Nonce-error predicate" for retry policy (A3/B3)**. `nonce-error-response?` parses exchange error text for "nonce" and routes to a dedicated refresh-and-retry path instead of generic error handling. Different from normal errors because nonce errors are benign-but-requires-re-sync. Our bot should classify exchange errors into `{retry, refresh+retry, user-intervention, hard-fail}` and act accordingly.
4. **Integer fidelity invariant (A5)**. "MUST preserve integer fidelity for signing-critical fields" — `oid`, nonces, asset indexes, sizes. Their `parse-usdc-micros` guards against `MAX_SAFE_INTEGER` before allowing a signed message. Python: use `int` everywhere, validate against `sys.maxsize`, never let `float` touch a signable field.
5. **Vault analytics surface (D3)**. Tearsheet metrics (CAGR, Sharpe, drawdown, benchmark) computed from fill history — directly applicable as a post-trade analytics module in our bot. `vaults/detail/performance.cljs` shows the shape.
6. **ADR-per-boundary workflow (C3/C4)**. 186 ADRs. Our project should adopt at least lightweight ADRs for each architecture seam (e.g. key-management, order-flow state machine, risk-engine policy).
7. **Contracts at the boundary (A5/C2)**. `schema/contracts.cljs` + `contracts/assert-exchange-response!` validate every exchange payload at the ACL layer before it enters domain state. Python analogue: `pydantic` models at the SDK boundary, `model_validate` on every response, with a feature flag to disable validation in hot paths once stable.
8. **Explicit ACL namespace for HL payload normalization (A5)**. Raw HL websocket/exchange shapes are messy; hyperopen normalizes them once in `websocket/acl/hyperliquid.cljs` so the rest of the system sees clean domain records. Our bot: do the same in a single `hl_adapter.py` layer; never let a raw dict from `info.user_state()` leak past that layer.
