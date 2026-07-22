#!/usr/bin/env python3
"""Audit benchmark artifacts for actual web-tool usage.

This scanner is intentionally conservative:

- It reports actual WebSearch/WebFetch tool-use records.
- It separately counts Claude Code init records where WebSearch/WebFetch were
  merely available in the tool list.
- It does not treat tool availability as usage.
- It exits nonzero in --strict mode if actual web-tool use is found.

The goal is to support benchmark-contamination review before scored runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

WEB_TOOLS = {"WebSearch", "WebFetch"}
SKIP_DIRS = {
    ".git",
    ".venv",
    ".secrets",
    ".tools",
    "__pycache__",
    ".pytest_cache",
    "terminal-bench",
    "node_modules",
}
CANDIDATE_NAMES = {"trajectory.json", "claude-code.txt"}
CANDIDATE_SUFFIXES = {".jsonl"}
TOOL_NAME_KEYS = {"name", "tool", "tool_name", "toolName", "toolUseName"}

TEXT_TOOL_RE = re.compile(
    r'"(?:name|tool|tool_name|toolName|toolUseName)"\s*:\s*"(WebSearch|WebFetch)"'
)


@dataclass(frozen=True)
class ToolEvent:
    path: str
    line: int | None
    tool: str
    kind: str


@dataclass(frozen=True)
class AuditReport:
    scanned_files: int
    actual_events: list[ToolEvent]
    init_availability_events: list[ToolEvent]


def should_skip(path: Path) -> bool:
    return bool(set(path.parts) & SKIP_DIRS)


def is_candidate(path: Path) -> bool:
    if should_skip(path):
        return False
    if path.name in CANDIDATE_NAMES:
        return True
    if path.suffix in CANDIDATE_SUFFIXES:
        return True
    return False


def iter_candidate_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if is_candidate(root):
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_file() and is_candidate(path):
                yield path


def find_events_in_obj(obj: Any, path: Path, line: int | None) -> tuple[list[ToolEvent], list[ToolEvent]]:
    actual: list[ToolEvent] = []
    availability: list[ToolEvent] = []

    def walk(value: Any) -> None:
        nonlocal actual, availability

        if isinstance(value, dict):
            tools = value.get("tools")
            if value.get("type") == "system" and value.get("subtype") == "init" and isinstance(tools, list):
                for tool in tools:
                    if tool in WEB_TOOLS:
                        availability.append(
                            ToolEvent(str(path), line, str(tool), "available-in-init")
                        )

            for key in TOOL_NAME_KEYS:
                tool = value.get(key)
                if tool in WEB_TOOLS:
                    actual.append(
                        ToolEvent(str(path), line, str(tool), "actual-tool-use")
                    )

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return actual, availability


def scan_json_file(path: Path) -> tuple[list[ToolEvent], list[ToolEvent]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return scan_text_file(path)

    return find_events_in_obj(obj, path, None)


def scan_jsonl_file(path: Path) -> tuple[list[ToolEvent], list[ToolEvent]]:
    actual: list[ToolEvent] = []
    availability: list[ToolEvent] = []

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return actual, availability

    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            for match in TEXT_TOOL_RE.finditer(line):
                actual.append(
                    ToolEvent(str(path), lineno, match.group(1), "actual-tool-use")
                )
            continue

        a, b = find_events_in_obj(obj, path, lineno)
        actual.extend(a)
        availability.extend(b)

    return actual, availability


def scan_text_file(path: Path) -> tuple[list[ToolEvent], list[ToolEvent]]:
    actual: list[ToolEvent] = []
    availability: list[ToolEvent] = []

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return actual, availability

    for lineno, line in enumerate(lines, start=1):
        try:
            obj = json.loads(line)
        except Exception:
            for match in TEXT_TOOL_RE.finditer(line):
                actual.append(
                    ToolEvent(str(path), lineno, match.group(1), "actual-tool-use")
                )
            continue

        a, b = find_events_in_obj(obj, path, lineno)
        actual.extend(a)
        availability.extend(b)

    return actual, availability


def audit_roots(roots: Iterable[str | Path]) -> AuditReport:
    root_paths = [Path(root) for root in roots]
    scanned = 0
    actual: list[ToolEvent] = []
    availability: list[ToolEvent] = []

    for path in iter_candidate_files(root_paths):
        scanned += 1
        if path.suffix == ".jsonl":
            a, b = scan_jsonl_file(path)
        elif path.suffix == ".json":
            a, b = scan_json_file(path)
        else:
            a, b = scan_text_file(path)

        actual.extend(a)
        availability.extend(b)

    return AuditReport(
        scanned_files=scanned,
        actual_events=actual,
        init_availability_events=availability,
    )


def print_report(report: AuditReport) -> None:
    print(f"Scanned candidate files: {report.scanned_files}")
    print(f"Actual WebSearch/WebFetch tool-use events: {len(report.actual_events)}")
    print(f"Init records with WebSearch/WebFetch available: {len(report.init_availability_events)}")

    if report.actual_events:
        print()
        print("Actual web-tool usage:")
        for event in report.actual_events:
            loc = f"{event.path}:{event.line}" if event.line is not None else event.path
            print(f"  {loc}: {event.tool} ({event.kind})")

    if report.init_availability_events:
        print()
        print("Note: Web tools were available in some Claude Code init records.")
        print("Tool availability is not counted as tool usage by this audit.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit result artifacts for WebSearch/WebFetch tool use.")
    parser.add_argument(
        "roots",
        nargs="*",
        default=["results/phase1", "results/phase2", "results/phase3"],
        help="Files or directories to scan. Defaults to results/phase1 results/phase2 results/phase3.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero if actual WebSearch/WebFetch usage is found.",
    )
    parser.add_argument(
        "--fail-on-available",
        action="store_true",
        help="Exit nonzero if WebSearch/WebFetch are present in Claude Code init tool lists.",
    )
    args = parser.parse_args(argv)

    report = audit_roots(args.roots)
    print_report(report)

    if args.strict and report.actual_events:
        return 1
    if args.fail_on_available and report.init_availability_events:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
