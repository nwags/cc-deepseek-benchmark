from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    rows: list[dict[str, Any]] = []
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def count_tool_names_from_jsonl(path: str | Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for obj in load_jsonl(path):
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        content = msg.get("content") if isinstance(msg.get("content"), list) else []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                name = str(item.get("name") or "unknown")
                counts[name] += 1
    return counts


def classify_failure(success: bool, exception_type: str | None = None) -> str:
    if success:
        return "success"
    if exception_type == "AgentTimeoutError":
        return "timed-out"
    if exception_type in {"NonZeroAgentExitCodeError", "RuntimeError"}:
        return "ran-out-of-budget"
    return "produced-wrong-output"
