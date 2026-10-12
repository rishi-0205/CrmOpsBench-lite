#!/usr/bin/env python3
"""Scan trajectory files to verify no API keys or secrets are leaked."""

from __future__ import annotations

import re
import sys
from pathlib import Path

COMMON_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key
    re.compile(r"gsk_[0-9A-Za-z]{30,}"),   # Groq API key
    re.compile(r"sk-[0-9A-Za-z]{30,}"),    # OpenAI API key
]


def load_env_secrets(env_path: Path) -> list[str]:
    secrets = []
    if not env_path.is_file():
        return secrets
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        _, val = line.split("=", 1)
        val = val.strip().strip("'\"")
        if len(val) >= 10:
            secrets.append(val)
    return secrets


def scan_file(file_path: Path, known_secrets: list[str]) -> list[str]:
    findings = []
    content = file_path.read_text(encoding="utf-8", errors="replace")

    for secret in known_secrets:
        if secret in content:
            findings.append(f"Found known secret matching .env in {file_path}")

    for pattern in COMMON_SECRET_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            findings.append(f"Found pattern match ({pattern.pattern}) in {file_path}")

    return findings


def main() -> int:
    workspace_root = Path(__file__).resolve().parent.parent
    env_file = workspace_root / ".env"
    known_secrets = load_env_secrets(env_file)

    target_files = list((workspace_root / "jobs").glob("**/trajectory.json"))
    results_traj = list((workspace_root / "results").glob("**/*.json"))
    target_files.extend(results_traj)

    if not target_files:
        print("No trajectory files found to scan.")
        return 0

    print(f"Scanning {len(target_files)} trajectory file(s)...")
    total_findings = 0
    for target in target_files:
        findings = scan_file(target, known_secrets)
        if findings:
            total_findings += len(findings)
            for f in findings:
                print(f"[FAIL] {f}")
        else:
            print(f"[OK] Clean: {target.relative_to(workspace_root)}")

    if total_findings > 0:
        print(f"\nScan failed with {total_findings} secret finding(s)!")
        return 1

    print("\nAll scanned trajectory files are clean. No secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
