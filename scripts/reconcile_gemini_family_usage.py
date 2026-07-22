#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


MODEL_BY_TEXT = {
    "router-gemini-flash": "gemini-flash",
    "arm-router-gemini-flash": "gemini-flash",
    "gemini-flash": "gemini-flash",
    "gemini/gemini-3.5-flash": "gemini-flash",
    "gemini-3.5-flash": "gemini-flash",
    "router-gemini-3.1-pro": "gemini-3.1-pro",
    "arm-router-gemini-3.1-pro": "gemini-3.1-pro",
    "gemini-3.1-pro": "gemini-3.1-pro",
    "gemini/gemini-3.1-pro": "gemini-3.1-pro",
}

RUN_DIR_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")


@dataclass
class BillingRow:
    service_description: str
    cost: Decimal
    unrounded_subtotal: Decimal
    subtotal: Decimal


@dataclass
class MonitoringPoint:
    timestamp: str
    response_code: str
    raw_value: float
    approx_count_if_hourly_rate: float


@dataclass
class SessionRow:
    input_tokens: int = 0
    cache_tokens: int = 0
    output_tokens: int = 0
    assistant_messages: int = 0


@dataclass
class AggregateRow:
    date: str
    arm: str
    model: str
    n_total_trials: int
    n_completed_trials: int
    n_errored_trials: int
    n_input_tokens: int
    n_cache_tokens: int
    n_output_tokens: int
    estimated_cost: float
    path: str


def intish(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(Decimal(str(value)))
    except Exception:
        return 0


def floatish(value: Any) -> float:
    if value in (None, "", "undefined"):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "$0.000000"
    return f"${float(value):.6f}"


def fmt_int(value: int | None) -> str:
    return f"{int(value or 0):,}"


def fmt_float(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{round(value):,}"
    return f"{value:,.3f}"


def infer_model_from_text(text: str) -> str | None:
    low = text.lower()
    for needle, model in MODEL_BY_TEXT.items():
        if needle in low:
            return model
    if "gemini" in low and "flash" in low:
        return "gemini-flash"
    if "gemini" in low and "pro" in low:
        return "gemini-3.1-pro"
    return None


def infer_arm_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("arm-router-gemini-"):
            return part.removeprefix("arm-")
        if part.startswith("router-gemini-"):
            return part
    model = infer_model_from_text(str(path)) or "unknown"
    return f"router-{model}"


def run_date_from_path(path: Path) -> str | None:
    for part in path.parts:
        if RUN_DIR_RE.fullmatch(part):
            return part.split("__", 1)[0]
    return None


def logical_artifact_key(path: Path) -> str:
    parts = list(path.parts)
    for idx, part in enumerate(parts):
        if part == "results" and idx + 1 < len(parts) and parts[idx + 1] == "phase3":
            return Path(*parts[idx:]).as_posix()
    return path.as_posix()


def parse_utc_date_from_message(obj: dict[str, Any], fallback_path: Path) -> str | None:
    candidates: list[Any] = [obj.get("timestamp"), obj.get("created_at"), obj.get("time")]

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
            continue

    return run_date_from_path(fallback_path)


def read_billing_csv(path: Path) -> list[BillingRow]:
    rows: list[BillingRow] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            service = (r.get("Service description") or "").strip()
            if service != "Gemini API":
                continue
            rows.append(
                BillingRow(
                    service_description=service,
                    cost=Decimal(str(r.get("Cost ($)") or "0")),
                    unrounded_subtotal=Decimal(str(r.get("Unrounded subtotal ($)") or "0")),
                    subtotal=Decimal(str(r.get("Subtotal ($)") or "0")),
                )
            )
    return rows


def read_monitoring_csv(path: Path) -> list[MonitoringPoint]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if not rows:
        return []

    header = rows[0]
    response_codes: dict[int, str] = {}

    for row in rows[1:]:
        if not row:
            continue
        if row[0] == "response_code":
            for idx, value in enumerate(row[1:], start=1):
                if value and value != "undefined":
                    response_codes[idx] = value
            break

    points: list[MonitoringPoint] = []
    for row in rows[1:]:
        if not row:
            continue
        if not row[0] or not row[0][0].isalpha() or "GMT" not in row[0]:
            continue

        timestamp = row[0]
        for idx, value in enumerate(row[1:], start=1):
            if idx not in response_codes:
                continue
            raw = floatish(value)
            if raw == 0:
                continue
            # The Cloud Monitoring CSV uses fractional chart-aligned values even
            # though the title says request_count [SUM]. Preserve raw values and
            # include this approximate hourly-rate conversion only as context.
            points.append(
                MonitoringPoint(
                    timestamp=timestamp,
                    response_code=response_codes[idx],
                    raw_value=raw,
                    approx_count_if_hourly_rate=raw * 3600.0,
                )
            )

    return points


def scan_session_jsonl(artifact_roots: list[Path]) -> dict[tuple[str, str], SessionRow]:
    rows: dict[tuple[str, str], SessionRow] = defaultdict(SessionRow)
    seen_logical_paths: set[str] = set()

    for root in artifact_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("agent/sessions/projects/-app/*.jsonl")):
            if "gemini" not in str(path).lower():
                continue

            logical_key = logical_artifact_key(path)
            if logical_key in seen_logical_paths:
                continue
            seen_logical_paths.add(logical_key)

            path_model = infer_model_from_text(str(path))
            seen_message_ids: set[str] = set()

            for line in path.read_text(errors="replace").splitlines():
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                msg = obj.get("message")
                if not isinstance(msg, dict) or msg.get("role") != "assistant":
                    continue

                model = infer_model_from_text(str(msg.get("model") or "")) or path_model
                if not model:
                    continue

                msg_id = str(msg.get("id") or "")
                if msg_id:
                    if msg_id in seen_message_ids:
                        continue
                    seen_message_ids.add(msg_id)

                usage = msg.get("usage") or {}
                if not isinstance(usage, dict):
                    continue

                date = parse_utc_date_from_message(obj, path)
                if not date:
                    continue

                input_tokens = intish(usage.get("input_tokens") or usage.get("prompt_tokens"))
                output_tokens = intish(usage.get("output_tokens") or usage.get("completion_tokens"))
                cache_tokens = intish(
                    usage.get("cache_read_input_tokens")
                    or usage.get("cached_tokens")
                    or usage.get("cache_tokens")
                )

                row = rows[(date, model)]
                row.input_tokens += input_tokens
                row.cache_tokens += cache_tokens
                row.output_tokens += output_tokens
                row.assistant_messages += 1

    return dict(rows)


def scan_aggregate_results(artifact_roots: list[Path]) -> list[AggregateRow]:
    out: list[AggregateRow] = []
    seen_logical_paths: set[str] = set()

    for root in artifact_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("result.json")):
            if "gemini" not in str(path).lower():
                continue

            logical_key = logical_artifact_key(path)
            if logical_key in seen_logical_paths:
                continue
            seen_logical_paths.add(logical_key)

            model = infer_model_from_text(str(path))
            if not model:
                continue

            try:
                data = json.loads(path.read_text())
            except Exception:
                continue

            stats = data.get("stats") if isinstance(data, dict) else None
            if not isinstance(stats, dict):
                continue

            n_total_trials = data.get("n_total_trials", stats.get("n_total_trials"))
            if n_total_trials is None:
                continue

            date = run_date_from_path(path) or "unknown"
            arm = infer_arm_from_path(path)

            out.append(
                AggregateRow(
                    date=date,
                    arm=arm,
                    model=model,
                    n_total_trials=intish(n_total_trials),
                    n_completed_trials=intish(stats.get("n_completed_trials")),
                    n_errored_trials=intish(stats.get("n_errored_trials")),
                    n_input_tokens=intish(stats.get("n_input_tokens")),
                    n_cache_tokens=intish(stats.get("n_cache_tokens")),
                    n_output_tokens=intish(stats.get("n_output_tokens")),
                    estimated_cost=float(stats.get("cost_usd") or stats.get("cost") or stats.get("total_cost") or 0),
                    path=path.as_posix(),
                )
            )

    return sorted(out, key=lambda r: (r.date, r.arm, r.path))


def write_markdown(
    out_path: Path,
    billing_rows: list[BillingRow],
    monitoring_points: list[MonitoringPoint],
    sessions: dict[tuple[str, str], SessionRow],
    aggregates: list[AggregateRow],
) -> None:
    artifact_estimated_cost = sum(Decimal(str(row.estimated_cost)) for row in aggregates)
    billing_total = sum((row.unrounded_subtotal for row in billing_rows), Decimal("0"))

    monitoring_by_code: dict[str, dict[str, float]] = defaultdict(lambda: {"raw_value_sum": 0.0, "approx_count_if_hourly_rate_sum": 0.0})
    for point in monitoring_points:
        monitoring_by_code[point.response_code]["raw_value_sum"] += point.raw_value
        monitoring_by_code[point.response_code]["approx_count_if_hourly_rate_sum"] += point.approx_count_if_hourly_rate

    lines: list[str] = []
    lines.append("# Gemini Family Usage Reconciliation")
    lines.append("")
    lines.append("This report reconciles available Google/Gemini billing evidence against Phase 3 Gemini benchmark artifacts.")
    lines.append("")
    lines.append("AI Studio detailed request logging was off, so provider-side model/token attribution is unavailable. The available provider evidence is service-level Google Cloud Billing plus a coarse Cloud Monitoring request-count export by response code.")
    lines.append("")
    lines.append("Raw Google project identifiers and service IDs from exports are intentionally omitted. Raw billing/monitoring CSV exports should not be committed.")
    lines.append("")
    lines.append("Session rows are grouped by assistant-message timestamp converted to UTC date, because provider billing is UTC-date based while benchmark run directory names may differ.")
    lines.append("")

    lines.append("## Provider billing summary")
    lines.append("")
    lines.append("| Service | Unrounded subtotal | Rounded subtotal |")
    lines.append("|---|---:|---:|")
    for row in billing_rows:
        lines.append(f"| {row.service_description} | {money(row.unrounded_subtotal)} | {money(row.subtotal)} |")
    lines.append("")
    lines.append(f"- Provider-billed Gemini API total in uploaded June billing export: **{money(billing_total)}**.")
    lines.append(f"- Artifact-side internal estimated Gemini cost across retained canary/smoke aggregates: **{money(artifact_estimated_cost)}**.")
    lines.append("- Because AI Studio detailed logging was off, the provider total cannot be split by Gemini model or token class from these exports.")
    lines.append("")

    lines.append("## Cloud Monitoring request activity")
    lines.append("")
    lines.append("The monitoring export contains response-code time buckets. The raw chart values are fractional, so the approximate-count column is shown only as contextual activity evidence, not as billing truth.")
    lines.append("")
    lines.append("| Response code | Raw value sum | Approx count if hourly-rate values |")
    lines.append("|---:|---:|---:|")
    for code, row in sorted(monitoring_by_code.items()):
        lines.append(f"| {code} | {fmt_float(row['raw_value_sum'])} | {fmt_float(row['approx_count_if_hourly_rate_sum'])} |")
    lines.append("")

    lines.append("## Session-side token totals")
    lines.append("")
    lines.append("| UTC date | Model/arm family | Input | Cache | Output | Assistant messages |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for (date, model), row in sorted(sessions.items()):
        lines.append(
            f"| {date} | `{model}` | {fmt_int(row.input_tokens)} | {fmt_int(row.cache_tokens)} | "
            f"{fmt_int(row.output_tokens)} | {fmt_int(row.assistant_messages)} |"
        )
    lines.append("")

    lines.append("## Benchmark aggregate artifacts included")
    lines.append("")
    lines.append("| Date | Arm | Model | Trials | Completed | Errors | Input | Cache | Output | Est. cost | Path |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in aggregates:
        lines.append(
            f"| {row.date} | `{row.arm}` | `{row.model}` | {row.n_total_trials} | "
            f"{row.n_completed_trials} | {row.n_errored_trials} | {fmt_int(row.n_input_tokens)} | "
            f"{fmt_int(row.n_cache_tokens)} | {fmt_int(row.n_output_tokens)} | "
            f"{money(row.estimated_cost)} | `{row.path}` |"
        )
    lines.append("")

    lines.append("## Interpretation notes")
    lines.append("")
    lines.append("- Treat the Google Cloud Billing total as the provider-side cost source of truth for Gemini spend to date.")
    lines.append("- Treat benchmark aggregate costs as internal estimates; they are not provider-billed costs and currently exceed the available service-level billing total.")
    lines.append("- Detailed model/token reconciliation is blocked because AI Studio logging was off and the billing export is service-level.")
    lines.append("- The monitoring export is useful for confirming request activity timing and response-code mix, but it does not expose model/token/cost dimensions.")
    lines.append("- Dashboard implication: store run start time, run end time, run directory timestamp, session message UTC dates, and provider billing UTC date separately.")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))


def write_json(
    out_path: Path,
    billing_csv: Path,
    monitoring_csv: Path,
    billing_rows: list[BillingRow],
    monitoring_points: list[MonitoringPoint],
    sessions: dict[tuple[str, str], SessionRow],
    aggregates: list[AggregateRow],
) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "billing_export": billing_csv.name,
        "monitoring_export": monitoring_csv.name,
        "provider_billing_rows": [
            {
                "service_description": row.service_description,
                "unrounded_subtotal": float(row.unrounded_subtotal),
                "subtotal": float(row.subtotal),
            }
            for row in billing_rows
        ],
        "monitoring_response_code_summary": {},
        "session_totals": [
            {
                "date": date,
                "model": model,
                **asdict(row),
            }
            for (date, model), row in sorted(sessions.items())
        ],
        "aggregate_artifacts": [asdict(row) for row in aggregates],
        "notes": [
            "AI Studio detailed logging was off; provider-side model/token attribution is unavailable.",
            "Raw Google project identifiers and service IDs are intentionally omitted.",
            "Raw billing/monitoring CSV exports should not be committed.",
        ],
    }

    summary: dict[str, dict[str, float]] = defaultdict(lambda: {"raw_value_sum": 0.0, "approx_count_if_hourly_rate_sum": 0.0})
    for point in monitoring_points:
        summary[point.response_code]["raw_value_sum"] += point.raw_value
        summary[point.response_code]["approx_count_if_hourly_rate_sum"] += point.approx_count_if_hourly_rate
    payload["monitoring_response_code_summary"] = dict(sorted(summary.items()))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile Gemini billing exports against benchmark artifacts.")
    parser.add_argument("--billing-csv", type=Path, required=True)
    parser.add_argument("--monitoring-csv", type=Path, required=True)
    parser.add_argument("--artifact-root", action="append", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    billing_rows = read_billing_csv(args.billing_csv)
    monitoring_points = read_monitoring_csv(args.monitoring_csv)
    sessions = scan_session_jsonl(args.artifact_root)
    aggregates = scan_aggregate_results(args.artifact_root)

    write_markdown(args.out_md, billing_rows, monitoring_points, sessions, aggregates)
    write_json(args.out_json, args.billing_csv, args.monitoring_csv, billing_rows, monitoring_points, sessions, aggregates)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
