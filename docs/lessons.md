# Lessons Learned

## Security Findings
<!-- Populated as audits progress. Document vulnerabilities, patterns of concern, and good practices found. -->

## Good Patterns
<!-- Approaches, architectures, or techniques worth reusing from evaluated bots. -->

## Bad Patterns
<!-- Anti-patterns, dangerous practices, or design mistakes to avoid. -->

## HL-Specific Gotchas
<!-- Hyperliquid API quirks, SDK issues, testnet vs mainnet differences. -->

## Tooling Notes

- **scan_secrets.py regex is noisy on env var reads**: Patterns like `private_key = os.getenv(...)` and `if not private_key:` trigger HIGH. These are safe env var lookups, not hardcoded secrets. Consider adding an `os.getenv`/`os.environ` exclusion filter.
- **audit_deps.py needs pyproject.toml support**: Chainstack bot uses `pyproject.toml` instead of `requirements.txt`. Currently flags for manual review but doesn't extract/audit deps from it.
- **trufflehog v2 (pip) output is messy**: ANSI color codes in output, separator-based parsing is fragile. Works but v3 (Go binary) would be cleaner if needed.
- **URL whitelist needs tuning**: Non-whitelisted URL check flags benign domains (apache.org, chainstack docs, gitbook). Could maintain a broader safe-domains list.
- **Smoke test on Chainstack Grid Bot passed**: clone_bot.sh -> scan_secrets.py -> audit_deps.py pipeline works end-to-end. Zero CRITICAL findings, zero vulnerabilities.
