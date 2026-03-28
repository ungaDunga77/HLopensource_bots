# Security Evaluation Framework

These are unknown codebases that handle private keys and real money. Every bot is treated as potentially hostile until proven otherwise.

## Core Principles

1. **Never execute code before auditing it**
2. **Testnet only** — no mainnet keys anywhere in the project
3. **Sandboxed execution** — Docker containers with network isolation
4. **Defense in depth** — multiple layers of scanning (automated + manual)

---

## Phase 1: Reconnaissance (no code download)

Before cloning anything, gather intelligence from the web:

- [ ] **Repo metadata**: stars, forks, contributors, issue activity, last commit date
- [ ] **README review**: read on GitHub web UI (don't clone yet)
- [ ] **Contributor profiles**: real accounts with history, or throwaway accounts?
- [ ] **Red flag scan**:
  - Keyword-stuffed descriptions (listing every possible strategy/feature)
  - Repository name squatting or impersonation
  - Zero-day-old GitHub accounts
  - Excessive promises with no documentation
  - No license
- [ ] **Decision**: proceed to clone or reject

### Rejection criteria (any one = reject)
- Contributor accounts created within 30 days
- Obfuscated or minified source visible in GitHub file browser
- Keyword-stuffed README with no actual documentation
- Claims that are too good to be true (guaranteed profits, etc.)

---

## Phase 2: Clone & Static Audit (code downloaded, never executed)

```bash
# Shallow clone into gitignored directory
git clone --depth 1 <repo> bots/<name>
# Do NOT run any install commands
```

### 2a. Automated Secret Scanning

```bash
# Private key patterns
grep -rn "0x[a-fA-F0-9]\{64\}" bots/<name>/
grep -rn "private.key\|api.key\|api.secret\|password\|secret" bots/<name>/

# All URLs (check for unexpected endpoints)
grep -rn "https\?://[^/]*\." bots/<name>/

# Expected HL endpoints (whitelist):
#   api.hyperliquid.xyz
#   api.hyperliquid-testnet.xyz
#   app.hyperliquid.xyz
# Anything else needs investigation.
```

### 2b. Dependency Audit

```bash
# Python
pip-audit -r bots/<name>/requirements.txt --desc
safety check -r bots/<name>/requirements.txt

# Node.js (do NOT run npm install first — inspect package.json manually)
# Check for suspicious postinstall scripts in package.json
cat bots/<name>/package.json | grep -A5 "scripts"

# Rust
cd bots/<name> && cargo audit
```

### 2c. Manual Code Review Checklist

| # | Check | Pass/Fail | Notes |
|---|-------|-----------|-------|
| 1 | No hardcoded credentials | | |
| 2 | .env/.gitignore properly configured | | |
| 3 | Private key only used for signing, never logged or printed | | |
| 4 | No unexpected outbound network calls (telemetry, analytics) | | |
| 5 | No obfuscated or minified source code | | |
| 6 | No suspicious post-install scripts (npm postinstall, setup.py) | | |
| 7 | No dynamic code execution (eval, exec, __import__, Function()) | | |
| 8 | No file system access outside expected directories | | |
| 9 | Dependencies pinned to specific versions | | |
| 10 | No dependency confusion risk (private package names on public registries) | | |
| 11 | WebSocket connections only to expected HL endpoints | | |
| 12 | Order amounts and prices have sanity bounds | | |
| 13 | Rate limiting implemented | | |
| 14 | Error handling does not leak sensitive information | | |
| 15 | No subprocess/shell execution with user-controlled input | | |

### 2d. Output

Document all findings in `evaluations/<name>/security-audit.md`.

---

## Phase 3: Sandboxed Build (code built, not connected to exchange)

Build inside Docker container:

```bash
# Build with no network access
docker build --network=none -f sandbox/Dockerfile.<lang> -t bot-<name> bots/<name>/
```

Checks:
- [ ] Compiles/installs without errors
- [ ] Run included tests (pytest, npm test, cargo test)
- [ ] Check for any post-build hooks or startup scripts
- [ ] Monitor for unexpected network activity during build
- [ ] Verify no files written outside container

---

## Phase 4: Testnet Trial (code runs against HL testnet only)

**Prerequisites**:
- Security audit passed (Phase 2)
- Build succeeded (Phase 3)
- Docker sandbox configured with network isolation
- Testnet wallet funded with test tokens
- `HL_TESTNET=true` enforced in environment

**Safeguards**:
- Docker container with bridge network (only HL testnet API allowed)
- Resource limits (512MB RAM, 1 CPU)
- Read-only config mount
- No host filesystem access
- Testnet keys only (never mainnet)
- `tools/clone_bot.sh` refuses to proceed if mainnet key patterns detected

**Monitoring during trial**:
- Log all trades, positions, errors
- Monitor network traffic (expected: only HL testnet endpoints)
- Check resource usage (CPU, memory, disk)
- Run for 24-48 hours minimum

---

## Known Hyperliquid API Endpoints (whitelist)

| Endpoint | Purpose |
|----------|---------|
| `api.hyperliquid.xyz` | Mainnet REST API |
| `api.hyperliquid-testnet.xyz` | Testnet REST API |
| `app.hyperliquid.xyz` | Web app (not used by bots) |

Any outbound connection to other endpoints is suspicious and must be investigated.
