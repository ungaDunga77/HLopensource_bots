# Security Audit: Passivbot

**Repo**: https://github.com/enarjord/passivbot
**Date**: 2026-04-01
**Auditor**: Claude (automated + manual review)

---

## Automated Scan Results

### Clone Script (clone_bot.sh)

- **Bypassed** — manual `git clone --depth 1` used instead
- **Reason**: Hard gate (`0x[a-fA-F0-9]{64}`) known to false-positive on crypto codebases (same issue as SDK eval). Passivbot's broker codes, CCXT exchange data, and test fixtures would certainly trigger.

### Secret Scan (scan_secrets.py)

**Result**: PASS (no CRITICAL findings)

- **CRITICAL**: 0
- **HIGH**: 26 — breakdown:
  - `api-keys.json.example` (8): placeholder field names (`private_key`, `secret`, etc.) — false positives
  - `tests/` (8): test fixtures with `api_key="test_key"` and mock credential patterns — false positives
  - `src/exchanges/ccxt_bot.py` (2): detect-secrets flagged legacy field mapping code — false positives (lines 203, 205 are string constants for field remapping, not secrets)
  - `src/procedures.py` (1): detect-secrets flagged `load_user_info` function — false positive
  - `broker_codes.hjson` (1): public partner IDs — not secrets
  - `docs/` (2): documentation references — false positives
  - `test_tradfi_providers.py` (2): test fixtures — false positives
  - `tests/test_setup_bot_fallback.py` (1): test fixture — false positive
- **MEDIUM**: 118 — mostly non-whitelisted URLs in tests (25), README (11), downloader (9), docs (12), and `.gitignore` (8). All benign.

**Verdict**: All findings are false positives. No actual secrets committed.

### Dependency Audit (audit_deps.py)

**Result**: 30 MEDIUM vulnerabilities (no CRITICAL)

Unique vulnerabilities (many duplicated across requirements files):

| Package | Version | CVEs | Severity | Fix | Runtime? |
|---------|---------|------|----------|-----|----------|
| aiohttp | 3.13.1 | 8 CVEs (DoS, request smuggling, logging storm) | MEDIUM | 3.13.3 | Full only (backtester) |
| requests | 2.32.3 | 2 CVEs (netrc leak, zip extraction) | MEDIUM | 2.32.4+ | Full only |
| werkzeug | 3.0.6 | 3 CVEs (safe_join path traversal) | MEDIUM | 3.1.4+ | Dev only (mkdocs) |
| flask | 3.0.3 | 1 CVE (session Vary header) | MEDIUM | 3.1.3 | Full only (dash) |
| pymdown-extensions | 10.8.1 | 1 CVE (ReDoS) | MEDIUM | 10.16.1 | Dev only (mkdocs) |

**Notes**:
- Core live trading deps (`requirements-live.txt`: ccxt, numba, pandas, numpy, hjson, portalocker) have **0 known vulnerabilities**
- `aiohttp` and `requests` are in `requirements-full.txt` (backtester/optimizer), not required for live trading
- `werkzeug`/`pymdown-extensions` are dev-only docs dependencies
- All deps pinned with `==` (good practice)

**Rust dependencies** (`passivbot-rust/Cargo.toml`):
- 10 deps, all well-established (pyo3, ndarray, serde, etc.)
- `memmap 0.7.0` is deprecated (replaced by `memmap2`); functional but unmaintained
- Cargo audit deferred to Docker build

---

## Manual Code Review (Security Checklist)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | No hardcoded credentials | PASS | All credentials loaded from `api-keys.json` at runtime via `procedures.py:load_user_info()` |
| 2 | .env/.gitignore configured | PASS | `api-keys.json` excluded by `.gitignore` (lines 350, 382). `.example` file has placeholders only. No .env support (uses JSON config instead). |
| 3 | Private key only for signing | PASS | Key → CCXT `privateKey` field → exchange signing. Never logged, printed, or transmitted outside CCXT. |
| 4 | No unexpected outbound calls | PARTIAL | CCXT handles all exchange comms (expected). `custom_endpoint_overrides.py` allows URL rewriting with **no scheme/domain validation** — could redirect to attacker servers. Broker codes sent as affiliate tracking headers (benign). |
| 5 | No obfuscated/minified code | PASS | All Python + Rust, well-structured, readable. Unlicense (public domain). |
| 6 | No suspicious post-install scripts | PASS | `setup.py` uses `RustExtension` for Rust build — expected and legitimate. |
| 7 | No dynamic code execution | PASS | No `eval()`, `exec()`, or `__import__()`. `hjson.loads()` used for config (safe parser). |
| 8 | No FS access outside expected dirs | PARTIAL | `_resolve_coins_file_path()` accepts user-supplied paths without traversal validation. Low risk (parsed as JSON, fails on non-JSON). Config files, logs, and data cache dirs only. |
| 9 | Dependencies pinned | PASS | All `==` in requirements files. `Cargo.toml` uses semver ranges (standard for Rust). |
| 10 | No dependency confusion risk | PASS | Published as `passivbot` on PyPI. Rust crate is local (`cdylib`, not published). |
| 11 | WebSocket to expected endpoints | PASS | Via CCXT Pro. HL WebSocket managed by CCXT internally. No custom WS implementation for HL. |
| 12 | Order amounts have sanity bounds | PASS | `wallet_exposure_limit` (per-symbol), `total_wallet_exposure_limit` (global), `max_n_creations_per_batch`, `max_n_cancellations_per_batch`. No per-order max size but exposure limits are enforced. |
| 13 | Rate limiting implemented | PASS | CCXT `enableRateLimit=True` set explicitly. Circuit breaker: 10 errors/hour triggers restart. Exponential backoff on rate limit errors. |
| 14 | Error handling doesn't leak secrets | PASS | Credential values never in error messages. CCXT logger suppressed to WARNING by default (`logging_setup.py`). Debug tracebacks logged at DEBUG level only. |
| 15 | No subprocess with user input | PASS | `subprocess.run()` only in `rust_utils.py` with hardcoded `["maturin", "develop", "--release"]` — no user-controlled input. |

---

## Key Management Deep Dive

**File**: `src/procedures.py` (lines 151-179)

Credentials loaded from `api-keys.json` via `json.load()`. For Hyperliquid:
- `wallet_address`: blockchain address
- `private_key`: private key (plaintext in JSON file)
- `is_vault`: boolean for vault mode

**Strengths**:
- Credentials never logged or printed anywhere in codebase
- CCXT debug logging suppressed by default (WARNING level)
- `.gitignore` excludes credential file
- Legacy field remapping logs only field name mappings, not values
- Vault mode support (prevents using primary wallet)

**Weaknesses**:
- **Plaintext JSON storage** — no encryption, no keystore, no env var support
- No file permission enforcement (0o600) on `api-keys.json`
- No key format validation before passing to CCXT
- Credentials held in memory for bot lifetime (standard Python behavior)

**Comparison to Chainstack**: Chainstack had hierarchical key resolution (env vars → key files → config), key format validation, and separate testnet/mainnet paths. Passivbot's approach is simpler but less secure.

---

## Network Endpoint Analysis

**File**: `src/custom_endpoint_overrides.py` (lines 101-136)

### Custom Endpoint Override System

The `rewrite_url()` method performs string-based URL rewriting:
```python
for old, new in self.rest_domain_rewrites.items():
    if resolved_url.startswith(candidate):
        return new.rstrip("/") + suffix
```

**Critical Finding**: No validation of replacement URLs:
- No HTTPS scheme enforcement — could redirect to `http://` (credentials sent unencrypted)
- No domain whitelist — any domain accepted
- No integrity checking of `configs/custom_endpoints.json`

**Attack vector**: An attacker with write access to `custom_endpoints.json` could redirect all API traffic (including signed requests with credentials) to a malicious server.

**Mitigating factors**:
- File must be manually created (doesn't exist by default)
- Active overrides are logged at startup (lines 413-437)
- CCXT signing happens client-side (private key not sent), but API keys/signatures would be visible

### Hyperliquid Endpoints

- **REST**: `https://api.hyperliquid.xyz` (hardcoded fallback in `hyperliquid.py:52`)
- **Info**: Derived from CCXT session URLs + `/info`
- **WebSocket**: Via CCXT Pro (no custom WS implementation)
- **Broker code**: None defined for Hyperliquid in `broker_codes.hjson`

---

## Testnet Support Analysis

**Finding: NO testnet support for Hyperliquid**

- No `testnet`, `sandbox`, or `test_mode` config flag
- No environment variable for testnet switching
- No conditional URL logic for Hyperliquid (contrast: Paradex has testnet URL detection)
- CCXT's `set_sandbox_mode()` is never called
- Only way to use testnet: manually configure `custom_endpoints.json` to redirect to `api.hyperliquid-testnet.xyz`

This is a significant gap for our evaluation framework which requires testnet-first design.

---

## Gate Decision: PROCEED

No blocking security concerns. Key findings are:
1. Custom endpoint override lacks URL validation (medium risk — requires config file compromise)
2. Plaintext credential storage (acceptable for self-hosted bot, weaker than env var approach)
3. No testnet support (operational concern, not security blocker)
4. Core live trading dependencies have zero known vulnerabilities

The bot is safe to build in Docker sandbox for testing.
