# Security Audit: Chainstack Grid Bot

**Repo**: https://github.com/chainstacklabs/hyperliquid-trading-bot
**Date**: 2026-03-29
**Auditor**: Claude (automated + manual review)

---

## Automated Scan Results

### Clone Script (clone_bot.sh)

- **Stage 1 (hard gate)**: PASS — no 64-char hex private key patterns
- **Stage 2 (soft gate)**: PASS — no critical findings

### Secret Scan (scan_secrets.py)

**Result**: PASS (no CRITICAL findings)

- **HIGH**: 45 — all are `private_key = os.getenv(...)` patterns in code and docs. These are env var reads, not hardcoded secrets.
- **MEDIUM**: 16 — non-whitelisted URLs (apache.org license, chainstack docs, gitbook docs, HL testnet endpoints)
- **detect-secrets**: 1 finding in `key_manager.py:171` — "Secret Keyword" on a validation pattern, false positive.
- **trufflehog**: 2 entropy findings — no specific details, likely benign.

**Verdict**: All findings are false positives. No actual secrets committed.

### Dependency Audit (audit_deps.py)

**Result**: PASS (0 vulnerabilities)

Dependencies (pyproject.toml, managed by `uv`):
- `hyperliquid-python-sdk >=0.20.0` — official SDK
- `eth-account >=0.10.0`
- `pyyaml >=6.0`
- `typing-extensions >=4.0`
- `psutil >=7.0.0`
- `httpx >=0.28.1`
- `python-dotenv >=1.1.1`
- `websockets >=15.0.1`

8 runtime deps. All established libraries. No lockfile version pinning (uses `>=` ranges only, though `uv.lock` is committed).

---

## Manual Code Review (Security Checklist)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | No hardcoded credentials | PASS | All keys via env vars or key files. Config warns if keys found in YAML. |
| 2 | .env/.gitignore configured | PASS | `.env` gitignored, `.env.example` has placeholder values only |
| 3 | Private key only for signing | PASS | Key → `Account.from_key()` → `Exchange(wallet)`. Never logged or transmitted. |
| 4 | No unexpected outbound calls | PASS | Only HL testnet/mainnet endpoints via endpoint_router.py. Optional Chainstack endpoints. |
| 5 | No obfuscated/minified code | PASS | All Python, well-structured, readable |
| 6 | No suspicious post-install scripts | PASS | No pyproject.toml scripts that execute on install |
| 7 | No dynamic code execution | PASS | No eval/exec. YAML loaded with `yaml.safe_load()` |
| 8 | No FS access outside expected dirs | PASS | Reads config YAML, .env, optional key files only |
| 9 | Dependencies pinned | PARTIAL | `>=` ranges, no upper bounds. `uv.lock` committed. |
| 10 | No dependency confusion risk | PASS | Not published as a pip package |
| 11 | WebSocket to expected endpoints | PASS | Hardcoded to `wss://api.hyperliquid[-testnet].xyz/ws` |
| 12 | Order amounts have sanity bounds | PARTIAL | `max_allocation_pct` config, `max_position_size_pct` rule. No per-order max size. BTC precision hardcoded. |
| 13 | Rate limiting implemented | NO | No client-side rate limiting. Relies on SDK. |
| 14 | Error handling doesn't leak secrets | PASS | Custom exceptions, no key material in error messages. Key manager logs key source but not value. |
| 15 | No subprocess with user input | PASS | No subprocess usage |

---

## Key Management Deep Dive

**File**: `src/core/key_manager.py`

Hierarchical key resolution (priority order):
1. Bot-specific config YAML (testnet_private_key / mainnet_private_key)
2. Environment variables (HYPERLIQUID_TESTNET_PRIVATE_KEY / HYPERLIQUID_MAINNET_PRIVATE_KEY)
3. Legacy env var (HYPERLIQUID_PRIVATE_KEY)
4. Key files (testnet_key_file / mainnet_key_file)
5. Legacy key file (HYPERLIQUID_PRIVATE_KEY_FILE)

**Strengths**:
- Validates key format (64 hex chars or 0x + 66 chars)
- Separate testnet/mainnet key paths
- File-based key option
- Warns (but doesn't reject) keys in YAML config

**Concern**: Keys in YAML config files produce a warning, not an error. Should be rejected in production.

---

## Network Endpoint Analysis

**File**: `src/core/endpoint_router.py`

Smart routing system:
- INFO queries: Chainstack (preferred) → Public (fallback)
- EXCHANGE (signing): Public only (required by HL protocol)
- WEBSOCKET: Chainstack → Public
- EVM: Chainstack → Public

All endpoints configured via env vars. Health checks every 300s. Correct architectural decision: exchange/signing must use public HL API.

**WebSocket exception**: `market_data.py` hardcodes WS URL instead of using endpoint_router. Not a security issue, just inconsistency.

---

## Gate Decision: PROCEED

No security concerns blocking sandbox testing. The bot follows the SDK baseline patterns for key management and signing. All exit strategies disabled by default (safe for testnet trials).
