#!/usr/bin/env python3
"""Dependency auditor for cloned bot repositories.

Auto-detects project type (Python/Node/Rust) and runs appropriate audits.
Never executes install commands — only inspects manifest files.

Usage:
    python tools/audit_deps.py bots/<name>/
    python tools/audit_deps.py bots/<name>/ --format markdown
    python tools/audit_deps.py bots/<name>/ --output evaluations/<name>/dep-audit.json
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

INFO = "INFO"
LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
CRITICAL = "CRITICAL"

# Suspicious npm lifecycle scripts
SUSPICIOUS_SCRIPTS = {"preinstall", "postinstall", "preuninstall", "postuninstall"}


@dataclass
class DepFinding:
    severity: str
    category: str  # "vulnerability", "pinning", "script", "note"
    package: str
    description: str
    details: str = ""


@dataclass
class AuditResult:
    target: str
    languages: list[str] = field(default_factory=list)
    findings: list[DepFinding] = field(default_factory=list)

    @property
    def vuln_count(self) -> int:
        return sum(1 for f in self.findings if f.category == "vulnerability")

    @property
    def has_critical(self) -> bool:
        return any(f.severity == CRITICAL for f in self.findings)


def detect_languages(target: Path) -> list[str]:
    """Detect project languages by probing for manifest files."""
    languages = []
    python_markers = ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "setup.cfg"]
    if any((target / m).exists() for m in python_markers):
        languages.append("python")
    if (target / "package.json").exists():
        languages.append("node")
    if (target / "Cargo.toml").exists():
        languages.append("rust")
    return languages


def check_version_pinning(lines: list[str]) -> list[DepFinding]:
    """Check if Python dependencies are pinned to specific versions."""
    findings = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Pinned: package==1.2.3, acceptable: package>=1.2.3,<2.0
        # Unpinned: package, package>=1.0
        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].split("[")[0].strip()
        if not pkg:
            continue
        if "==" not in line:
            findings.append(DepFinding(
                severity=LOW,
                category="pinning",
                package=pkg,
                description=f"Dependency not pinned to exact version: {line}",
            ))
    return findings


def audit_python(target: Path) -> list[DepFinding]:
    """Audit Python dependencies using pip-audit and safety."""
    findings = []

    req_files = list(target.glob("requirements*.txt"))
    if not req_files:
        # Check pyproject.toml / setup.py
        for alt in ["pyproject.toml", "setup.py", "setup.cfg"]:
            if (target / alt).exists():
                findings.append(DepFinding(
                    severity=INFO, category="note", package="",
                    description=f"Python deps defined in {alt} (not requirements.txt). Manual review needed.",
                ))
        if (target / "Pipfile").exists():
            findings.append(DepFinding(
                severity=INFO, category="note", package="",
                description="Uses Pipfile. Check Pipfile.lock for pinned versions.",
            ))
        return findings

    for req_file in req_files:
        rel = str(req_file.relative_to(target))

        # Version pinning check
        try:
            lines = req_file.read_text().splitlines()
            findings.extend(check_version_pinning(lines))
        except OSError:
            pass

        # pip-audit
        try:
            result = subprocess.run(
                ["pip-audit", "-r", str(req_file), "--desc", "--format", "json"],
                capture_output=True, text=True, timeout=120,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for dep in data.get("dependencies", []):
                    for vuln in dep.get("vulns", []):
                        sev = MEDIUM
                        fix = vuln.get("fix_versions", [])
                        findings.append(DepFinding(
                            severity=sev,
                            category="vulnerability",
                            package=dep.get("name", "unknown"),
                            description=f"[pip-audit] {vuln.get('id', 'unknown')}: {vuln.get('description', '')[:200]}",
                            details=f"Installed: {dep.get('version', '?')}, Fix: {', '.join(fix) if fix else 'none'}",
                        ))
        except FileNotFoundError:
            findings.append(DepFinding(
                severity=INFO, category="note", package="",
                description="pip-audit not installed",
            ))
        except subprocess.TimeoutExpired:
            findings.append(DepFinding(
                severity=INFO, category="note", package="",
                description=f"pip-audit timed out on {rel}",
            ))
        except (json.JSONDecodeError, KeyError):
            pass

        # safety
        try:
            result = subprocess.run(
                ["safety", "check", "-r", str(req_file), "--output", "json"],
                capture_output=True, text=True, timeout=120,
            )
            if result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])
                    for vuln in vulns:
                        if isinstance(vuln, dict):
                            pkg = vuln.get("package_name", vuln.get("package", "unknown"))
                            desc = vuln.get("advisory", vuln.get("vulnerability_id", ""))
                            findings.append(DepFinding(
                                severity=MEDIUM,
                                category="vulnerability",
                                package=pkg,
                                description=f"[safety] {str(desc)[:200]}",
                            ))
                except json.JSONDecodeError:
                    pass
        except FileNotFoundError:
            findings.append(DepFinding(
                severity=INFO, category="note", package="",
                description="safety not installed",
            ))
        except subprocess.TimeoutExpired:
            findings.append(DepFinding(
                severity=INFO, category="note", package="",
                description=f"safety timed out on {rel}",
            ))

    return findings


def audit_node(target: Path) -> list[DepFinding]:
    """Audit Node.js project — static inspection only, never runs npm install."""
    findings = []
    pkg_json = target / "package.json"
    if not pkg_json.exists():
        return findings

    try:
        data = json.loads(pkg_json.read_text())
    except (json.JSONDecodeError, OSError) as e:
        findings.append(DepFinding(
            severity=INFO, category="note", package="",
            description=f"Cannot parse package.json: {e}",
        ))
        return findings

    # Check for suspicious lifecycle scripts
    scripts = data.get("scripts", {})
    for script_name in SUSPICIOUS_SCRIPTS:
        if script_name in scripts:
            findings.append(DepFinding(
                severity=HIGH,
                category="script",
                package="",
                description=f"Suspicious lifecycle script: {script_name}",
                details=scripts[script_name][:200],
            ))

    # Check dependency counts and report for awareness
    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    findings.append(DepFinding(
        severity=INFO, category="note", package="",
        description=f"Node dependencies: {len(deps)} runtime, {len(dev_deps)} dev",
    ))

    # Check for version pinning (ranges vs exact)
    for dep_name, version in deps.items():
        if version.startswith("^") or version.startswith("~") or version == "*" or version == "latest":
            findings.append(DepFinding(
                severity=LOW,
                category="pinning",
                package=dep_name,
                description=f"Dependency uses version range: {version}",
            ))

    # Check for lock file
    if not (target / "package-lock.json").exists() and not (target / "yarn.lock").exists():
        findings.append(DepFinding(
            severity=MEDIUM,
            category="pinning",
            package="",
            description="No lock file found (package-lock.json or yarn.lock)",
        ))

    # Note: full npm audit requires npm install, deferred to Docker sandbox
    findings.append(DepFinding(
        severity=INFO, category="note", package="",
        description="Full npm audit deferred to Docker sandbox (requires npm install)",
    ))

    return findings


def audit_rust(target: Path) -> list[DepFinding]:
    """Audit Rust project — parse Cargo.toml, flag build.rs. Full cargo audit deferred to Docker."""
    findings = []
    cargo_toml = target / "Cargo.toml"
    if not cargo_toml.exists():
        return findings

    try:
        import tomllib
        data = tomllib.loads(cargo_toml.read_text())
    except Exception as e:
        findings.append(DepFinding(
            severity=INFO, category="note", package="",
            description=f"Cannot parse Cargo.toml: {e}",
        ))
        return findings

    # Check for build.rs (custom build script)
    if (target / "build.rs").exists():
        findings.append(DepFinding(
            severity=MEDIUM,
            category="script",
            package="",
            description="build.rs found — custom build script requires manual review",
        ))

    # Count dependencies
    deps = data.get("dependencies", {})
    build_deps = data.get("build-dependencies", {})
    findings.append(DepFinding(
        severity=INFO, category="note", package="",
        description=f"Rust dependencies: {len(deps)} runtime, {len(build_deps)} build",
    ))

    # Check for Cargo.lock
    if not (target / "Cargo.lock").exists():
        findings.append(DepFinding(
            severity=MEDIUM,
            category="pinning",
            package="",
            description="No Cargo.lock found — versions not pinned",
        ))

    # Note about cargo audit
    findings.append(DepFinding(
        severity=INFO, category="note", package="",
        description="cargo audit deferred to Docker sandbox (cargo not on host)",
    ))

    return findings


def run_audit(target: Path) -> AuditResult:
    """Run dependency audit for all detected languages."""
    result = AuditResult(target=str(target))
    result.languages = detect_languages(target)

    if not result.languages:
        result.findings.append(DepFinding(
            severity=INFO, category="note", package="",
            description="No recognized language manifests found",
        ))
        return result

    for lang in result.languages:
        if lang == "python":
            result.findings.extend(audit_python(target))
        elif lang == "node":
            result.findings.extend(audit_node(target))
        elif lang == "rust":
            result.findings.extend(audit_rust(target))

    # Sort by severity
    severity_order = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}
    result.findings.sort(key=lambda f: severity_order.get(f.severity, 99))
    return result


def format_json(result: AuditResult) -> str:
    return json.dumps({
        "target": result.target,
        "languages": result.languages,
        "vulnerability_count": result.vuln_count,
        "has_critical": result.has_critical,
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "package": f.package,
                "description": f.description,
                "details": f.details,
            }
            for f in result.findings
        ],
    }, indent=2)


def format_markdown(result: AuditResult) -> str:
    lines = [
        f"# Dependency Audit: {result.target}",
        "",
        f"**Languages detected**: {', '.join(result.languages) or 'none'}",
        f"**Vulnerabilities found**: {result.vuln_count}",
        "",
    ]

    if result.findings:
        lines.append("## Findings")
        lines.append("")
        lines.append("| Severity | Category | Package | Description |")
        lines.append("|----------|----------|---------|-------------|")
        for f in result.findings:
            lines.append(f"| {f.severity} | {f.category} | {f.package} | {f.description} |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit bot repository dependencies")
    parser.add_argument("target", help="Path to cloned bot directory")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", dest="fmt")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = run_audit(target)

    output = format_json(result) if args.fmt == "json" else format_markdown(result)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output)

    sys.exit(1 if result.has_critical else 0)


if __name__ == "__main__":
    main()
