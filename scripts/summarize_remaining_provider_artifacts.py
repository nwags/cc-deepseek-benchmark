#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_DIR_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")

MODEL_PATTERNS = {
    "grok-build-0.1": "grok",
    "grok-3": "grok",
    "kimi-k2.6": "kimi",
    "kimi-k2.5": "kimi",
    "qwen-3.7-plus": "qwen",
    "qwen-3.5": "qwen",
    "glm-5.1": "glm",
    "glm-5": "glm",
}


@dataclass
class AggregateRow:
    run: str
    date: str
    provider_family: str
    arm: str
    trials: int
    completed: int
    errors: int
    input_tokens: int
    cache_tokens: int
    output_tokens: int
    estimated_cost: float
    path: str


@dataclass
class SessionRow:
    date: str
    provider_family: str
    arm: str
    input_tokens: int = 0
    cache_tokens: int = 0
    output_tokens: int = 0
    assistant_messages: int = 0


def intish(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(value))
    except Exception:
        return 0


def money(value: float | int | None) -> str:
    return f"${float(value or 0):.6f}"


def fmt_int(value: int | None) -> str:
    return f"{int(value or 0):,}"


def logical_artifact_key(path: Path) -> str:
    parts = list(path.parts)
    for i, part in enumerate(parts):
        if part == "results" and i + 1 < len(parts) and parts[i + 1] == "phase3":
            return Path(*parts[i:]).as_posix()
    return path.as_posix()


def infer_arm(path: Path) -> str:
    for part in path.parts:
        if part.startswith("arm-router-"):
            return part.removeprefix("arm-")
    return "unknown"


def infer_provider_family(text: str) -> str | None:
    low = text.lower()
    for pattern, family in MODEL_PATTERNS.items():
        if pattern in low:
            return family
    for family in ("grok", "kimi", "qwen", "glm"):
        if family in low:
            return family
    return None


def run_from_path(path: Path) -> str:
    for part in path.parts:
        if RUN_DIR_RE.fullmatch(part):
            return part
    return "unknown"


def date_from_path(path: Path) -> str:
    run = run_from_path(path)
    return run.split("__", 1)[0] if "__" in run else "unknown"


def parse_utc_date_from_message(obj: dict[str, Any], fallback_path: Path) -> str:
    candidates = [obj.get("timestamp"), obj.get("created_at"), obj.get("time")]
    msg = obj.get("message")
    if isinstance(msg, dict):
        candidates.extend([msg.get("timestamp"), msg.get("created_at"), msg.get("time")])

    for value in candidates:
        if value in (None, ""):
            continue
        try:
            if isinstance(value, (int, float)):
                seconds = float(value) / 1000.0 if float(value) > 1e12 else float(value)
                return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()
            if isinstance(value, str):
                s = value.strip()
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).date().isoformat()
        except Exception:
            pass

    return date_from_path(fallback_path)


def scan_aggregates(roots: list[Path]) -> list[AggregateRow]:
    rows: list[AggregateRow] = []
    seen: set[str] = set()

    for root in roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("result.json")):
            family = infer_provider_family(str(path))
            if not family:
                continue

            key = logical_artifact_key(path)
            if key in seen:
                continue
            seen.add(key)

            try:
                data = json.loads(path.read_text())
            except Exception:
                continue

            stats = data.get("stats") or {}
            if not isinstance(stats, dict):
                continue

            n_total = data.get("n_total_trials", stats.get("n_total_trials"))
            if n_total is None:
                continue

            rows.append(
                AggregateRow(
                    run=run_from_path(path),
                    date=date_from_path(path),
                    provider_family=family,
                    arm=infer_arm(path),
                    trials=intish(n_total),
                    completed=intish(stats.get("n_completed_trials")),
                    errors=intish(stats.get("n_errored_trials")),
                    input_tokens=intish(stats.get("n_input_tokens")),
                    cache_tokens=intish(stats.get("n_cache_tokens")),
                    output_tokens=intish(stats.get("n_output_tokens")),
                    estimated_cost=float(stats.get("cost_usd") or stats.get("cost") or stats.get("total_cost") or 0),
                    path=key,
                )
            )

    return sorted(rows, key=lambda r: (r.provider_family, r.arm, r.run, r.path))


def scan_sessions(roots: list[Path]) -> list[SessionRow]:
    rows: dict[tuple[str, str, str], SessionRow] = {}
    seen_paths: set[str] = set()

    for root in roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("agent/sessions/projects/-app/*.jsonl")):
            family = infer_provider_family(str(path))
            if not family:
                continue

            key = logical_artifact_key(path)
            if key in seen_paths:
                continue
            seen_paths.add(key)

            arm = infer_arm(path)
            seen_msg_ids: set[str] = set()

            for line in path.read_text(errors="replace").splitlines():
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                msg = obj.get("message")
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue

                msg_id = str(msg.get("id") or "")
                if msg_id:
                    if msg_id in seen_msg_ids:
                        continue
                    seen_msg_ids.add(msg_id)

                usage = msg.get("usage") or {}
                if not isinstance(usage, dict):
                    continue

                date = parse_utc_date_from_message(obj, path)
                row_key = (date, family, arm)
                if row_key not in rows:
                    rows[row_key] = SessionRow(date=date, provider_family=family, arm=arm)

                rows[row_key].input_tokens += intish(usage.get("input_tokens") or usage.get("prompt_tokens"))
                rows[row_key].cache_tokens += intish(usage.get("cache_read_input_tokens") or usage.get("cached_tokens") or usage.get("cache_tokens"))
                rows[row_key].output_tokens += intish(usage.get("output_tokens") or usage.get("completion_tokens"))
                rows[row_key].assistant_messages += 1

    return sorted(rows.values(), key=lambda r: (r.provider_family, r.arm, r.date))


def write_report(out_md: Path, out_json: Path, aggregates: list[AggregateRow], sessions: list[SessionRow]) -> None:
    provider_totals = defaultdict(lambda: {"runs": 0, "trials": 0, "errors": 0, "input": 0, "cache": 0, "output": 0, "cost": 0.0})
    for row in aggregates:
        t = provider_totals[row.provider_family]
        t["runs"] += 1
        t["trials"] += row.trials
        t["errors"] += row.errors
        t["input"] += row.input_tokens
        t["cache"] += row.cache_tokens
        t["output"] += row.output_tokens
        t["cost"] += row.estimated_cost

    lines = []
    lines.append("# Remaining Provider Artifact Status")
    lines.append("")
    lines.append("This report summarizes Phase 3 artifact-side evidence for Grok, Kimi, Qwen, and GLM.")
    lines.append("")
    lines.append("Provider billing/usage exports have not yet been reconciled for these families, so the costs below are benchmark/internal estimates, not provider-billed source-of-truth costs.")
    lines.append("")
    lines.append("## Provider-family aggregate summary")
    lines.append("")
    lines.append("| Provider family | Aggregate runs | Trials | Errors | Input | Cache | Output | Internal est. cost | Reconciliation status |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for family, t in sorted(provider_totals.items()):
        lines.append(
            f"| {family} | {t['runs']} | {t['trials']} | {t['errors']} | "
            f"{fmt_int(t['input'])} | {fmt_int(t['cache'])} | {fmt_int(t['output'])} | "
            f"{money(t['cost'])} | provider export pending |"
        )

    lines.append("")
    lines.append("## Aggregate artifacts")
    lines.append("")
    lines.append("| Run | Provider | Arm | Trials | Completed | Errors | Input | Cache | Output | Internal est. cost | Path |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in aggregates:
        lines.append(
            f"| {row.run} | {row.provider_family} | `{row.arm}` | {row.trials} | {row.completed} | {row.errors} | "
            f"{fmt_int(row.input_tokens)} | {fmt_int(row.cache_tokens)} | {fmt_int(row.output_tokens)} | "
            f"{money(row.estimated_cost)} | `{row.path}` |"
        )

    lines.append("")
    lines.append("## Session-side token totals")
    lines.append("")
    lines.append("| UTC date | Provider | Arm | Input | Cache | Output | Assistant messages |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for row in sessions:
        lines.append(
            f"| {row.date} | {row.provider_family} | `{row.arm}` | {fmt_int(row.input_tokens)} | "
            f"{fmt_int(row.cache_tokens)} | {fmt_int(row.output_tokens)} | {fmt_int(row.assistant_messages)} |"
        )

    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("")
    lines.append("- This is artifact-side status only. Provider-family billing should be added when export data becomes available.")
    lines.append("- Reconcile provider family totals first; split by model only when provider exports expose reliable model-level rows.")
    lines.append("- Dashboard implication: keep run directory timestamp, run start/end, session message UTC dates, provider billing UTC date, routed arm, observed backend, internal estimate, provider billed cost, and reconciliation status as separate fields.")
    lines.append("- These artifacts are enough to characterize smoke-run behavior and internal estimated spend, but not enough to validate external provider invoices.")
    lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines))

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "artifact-side only; provider export pending",
        "provider_family_totals": dict(provider_totals),
        "aggregate_artifacts": [asdict(r) for r in aggregates],
        "session_totals": [asdict(r) for r in sessions],
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", action="append", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    aggregates = scan_aggregates(args.artifact_root)
    sessions = scan_sessions(args.artifact_root)
    write_report(args.out_md, args.out_json, aggregates, sessions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
