#!/usr/bin/env python3
"""Secret scanner for cloned bot repositories.

Combines regex pattern matching, detect-secrets, and trufflehog
to find credentials, private keys, and suspicious URLs.

Usage:
    python tools/scan_secrets.py bots/<name>/
    python tools/scan_secrets.py bots/<name>/ --format markdown
    python tools/scan_secrets.py bots/<name>/ --output evaluations/<name>/secret-scan.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Severity levels
CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
INFO = "INFO"

# Expected Hyperliquid endpoints (whitelist)
HL_WHITELIST = {
    "api.hyperliquid.xyz",
    "api.hyperliquid-testnet.xyz",
    "app.hyperliquid.xyz",
}

# Binary/generated file extensions to skip
SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".dat",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".doc", ".docx",
    ".lock",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".tox", ".mypy_cache",
    "venv", ".venv", "env", ".env",
    "dist", "build", "target",
}


@dataclass
class Finding:
    severity: str
    scanner: str
    file: str
    line: int | None
    description: str
    match: str = ""


@dataclass
class ScanResult:
    target: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == CRITICAL for f in self.findings)

    @property
    def counts(self) -> dict[str, int]:
        counts = {CRITICAL: 0, HIGH: 0, MEDIUM: 0, INFO: 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


def iter_files(target: Path):
    """Yield text files in target, skipping binary/generated content."""
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in SKIP_EXTENSIONS:
                continue
            yield fpath


def scan_regex(target: Path) -> list[Finding]:
    """Scan for secrets using regex patterns from security-framework.md."""
    findings = []
    patterns = [
        (CRITICAL, r"0x[a-fA-F0-9]{64}", "Potential private key (64-char hex)"),
        (HIGH, r"(?i)private[_.\s-]?key\s*[:=]", "Private key assignment"),
        (HIGH, r"(?i)api[_.\s-]?key\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (HIGH, r"(?i)api[_.\s-]?secret\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded API secret"),
        (HIGH, r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (HIGH, r"(?i)secret\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
        (HIGH, r"(?i)mnemonic\s*[:=]", "Mnemonic phrase reference"),
    ]
    url_pattern = re.compile(r"https?://([^/\s'\"<>]+)")

    for fpath in iter_files(target):
        try:
            text = fpath.read_text(errors="ignore")
        except (OSError, PermissionError):
            continue

        rel = str(fpath.relative_to(target))
        for lineno, line in enumerate(text.splitlines(), 1):
            # Check secret patterns
            for severity, pattern, desc in patterns:
                if re.search(pattern, line):
                    # Skip .env.example and template files
                    if ".example" in rel or "_template" in rel:
                        continue
                    # Skip comments in config examples
                    stripped = line.strip()
                    if stripped.startswith("#") and severity != CRITICAL:
                        continue
                    findings.append(Finding(
                        severity=severity,
                        scanner="regex",
                        file=rel,
                        line=lineno,
                        description=desc,
                        match=stripped[:120],
                    ))

            # Check URLs against whitelist
            for m in url_pattern.finditer(line):
                hostname = m.group(1).rstrip("/.")
                if hostname not in HL_WHITELIST and not hostname.startswith("github.com"):
                    # Skip common safe domains
                    safe = {"pypi.org", "npmjs.com", "crates.io", "docs.rs",
                            "python.org", "readthedocs.io", "shields.io",
                            "badge.fury.io", "img.shields.io",
                            "stackoverflow.com", "medium.com"}
                    if not any(hostname.endswith(s) for s in safe):
                        findings.append(Finding(
                            severity=MEDIUM,
                            scanner="regex",
                            file=rel,
                            line=lineno,
                            description=f"Non-whitelisted URL: {hostname}",
                            match=m.group(0)[:120],
                        ))

    return findings


def scan_detect_secrets(target: Path) -> list[Finding]:
    """Run detect-secrets scan on target directory."""
    findings = []
    try:
        result = subprocess.run(
            ["detect-secrets", "scan", str(target), "--all-files"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            findings.append(Finding(
                severity=INFO,
                scanner="detect-secrets",
                file="",
                line=None,
                description=f"detect-secrets exited with code {result.returncode}: {result.stderr[:200]}",
            ))
            return findings

        data = json.loads(result.stdout)
        for filepath, secrets in data.get("results", {}).items():
            rel = filepath
            if filepath.startswith(str(target)):
                rel = str(Path(filepath).relative_to(target))
            for secret in secrets:
                findings.append(Finding(
                    severity=HIGH,
                    scanner="detect-secrets",
                    file=rel,
                    line=secret.get("line_number"),
                    description=f"detect-secrets: {secret.get('type', 'unknown')}",
                    match=secret.get("hashed_secret", "")[:40],
                ))
    except FileNotFoundError:
        findings.append(Finding(
            severity=INFO, scanner="detect-secrets", file="", line=None,
            description="detect-secrets not installed",
        ))
    except subprocess.TimeoutExpired:
        findings.append(Finding(
            severity=INFO, scanner="detect-secrets", file="", line=None,
            description="detect-secrets timed out after 120s",
        ))
    except (json.JSONDecodeError, KeyError) as e:
        findings.append(Finding(
            severity=INFO, scanner="detect-secrets", file="", line=None,
            description=f"detect-secrets parse error: {e}",
        ))

    return findings


def scan_trufflehog(target: Path) -> list[Finding]:
    """Run trufflehog entropy scan on target directory."""
    findings = []
    try:
        result = subprocess.run(
            ["trufflehog", "--regex", "--entropy=True", str(target)],
            capture_output=True, text=True, timeout=120,
        )
        # trufflehog v2 outputs findings to stdout, one per block
        if result.stdout.strip():
            # Each finding is separated by ~~ or similar markers
            for block in result.stdout.split("~"*20):
                block = block.strip()
                if not block:
                    continue
                findings.append(Finding(
                    severity=MEDIUM,
                    scanner="trufflehog",
                    file="",
                    line=None,
                    description="trufflehog entropy/regex finding",
                    match=block[:200],
                ))
    except FileNotFoundError:
        findings.append(Finding(
            severity=INFO, scanner="trufflehog", file="", line=None,
            description="trufflehog not installed",
        ))
    except subprocess.TimeoutExpired:
        findings.append(Finding(
            severity=INFO, scanner="trufflehog", file="", line=None,
            description="trufflehog timed out after 120s",
        ))

    return findings


def run_scan(target: Path) -> ScanResult:
    """Run all scanners and combine results."""
    result = ScanResult(target=str(target))
    result.findings.extend(scan_regex(target))
    result.findings.extend(scan_detect_secrets(target))
    result.findings.extend(scan_trufflehog(target))
    # Sort: CRITICAL first, then HIGH, MEDIUM, INFO
    severity_order = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, INFO: 3}
    result.findings.sort(key=lambda f: severity_order.get(f.severity, 99))
    return result


def format_json(result: ScanResult) -> str:
    return json.dumps({
        "target": result.target,
        "pass": result.passed,
        "counts": result.counts,
        "findings": [
            {
                "severity": f.severity,
                "scanner": f.scanner,
                "file": f.file,
                "line": f.line,
                "description": f.description,
                "match": f.match,
            }
            for f in result.findings
        ],
    }, indent=2)


def format_markdown(result: ScanResult) -> str:
    lines = [
        f"# Secret Scan: {result.target}",
        "",
        f"**Result**: {'PASS' if result.passed else 'FAIL'}",
        "",
        "## Summary",
        "",
    ]
    for sev, count in result.counts.items():
        if count > 0:
            lines.append(f"- **{sev}**: {count}")
    if all(c == 0 for c in result.counts.values()):
        lines.append("No findings.")

    if result.findings:
        lines.extend(["", "## Findings", ""])
        lines.append("| Severity | Scanner | File | Line | Description |")
        lines.append("|----------|---------|------|------|-------------|")
        for f in result.findings:
            line_str = str(f.line) if f.line else "-"
            lines.append(f"| {f.severity} | {f.scanner} | {f.file} | {line_str} | {f.description} |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan bot repository for secrets and credentials")
    parser.add_argument("target", help="Path to cloned bot directory")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", dest="fmt")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = run_scan(target)

    output = format_json(result) if args.fmt == "json" else format_markdown(result)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output)

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
