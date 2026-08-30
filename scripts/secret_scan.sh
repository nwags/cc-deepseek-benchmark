#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOTS = [Path("scripts"), Path("docs"), Path("configs"), Path("results"), Path(".env.example"), Path("README.md"), Path("AGENTS.md")]
SKIP_DIRS = {".git", ".venv", ".secrets", "__pycache__", "terminal-bench"}
SKIP_SUFFIXES = {".lock", ".png", ".jpg", ".jpeg", ".pdf", ".pyc"}

TOKEN_PATTERNS = [
    re.compile(r"sk-ant-api\d+-[A-Za-z0-9_-]{40,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
]

ENV_ASSIGN_RE = re.compile(
    r"\b(ANTHROPIC_API_KEY|ANTHROPIC_ADMIN_API_KEY|ANTHROPIC_AUTH_TOKEN|DEEPSEEK_API_KEY|OPENAI_API_KEY|GEMINI_API_KEY|XAI_API_KEY)\s*=\s*([^\s'\"`]+)"
)

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return False

def is_placeholder(value: str) -> bool:
    value = value.strip().strip('"').strip("'")
    if not value:
        return True
    if "..." in value:
        return True
    if "$" in value:
        return True
    if value.startswith("<") and value.endswith(">"):
        return True
    if value.lower() in {"from_secret", "redacted", "example", "changeme"}:
        return True
    return False

findings: list[str] = []

for root in ROOTS:
    if not root.exists():
        continue

    paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for path in paths:
        if should_skip(path):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in TOKEN_PATTERNS:
                for match in pat.finditer(line):
                    token = match.group(0)
                    if not is_placeholder(token):
                        findings.append(f"{path}:{lineno}: possible raw token: {token[:12]}...")

            for match in ENV_ASSIGN_RE.finditer(line):
                name, value = match.groups()
                if not is_placeholder(value) and len(value.strip().strip('"').strip("'")) >= 20:
                    findings.append(f"{path}:{lineno}: possible secret assignment for {name}")

if findings:
    print("Possible secrets found:")
    for finding in findings:
        print(finding)
    sys.exit(1)

print("No apparent raw secrets found.")
PY

git check-ignore -v .secrets/anthropic.env .secrets/deepseek.env .env >/dev/null

echo "secret scan passed"
