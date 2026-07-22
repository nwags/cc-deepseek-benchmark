#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


DEEPSEEK_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro"}

MODEL_BY_TEXT = {
    "deepseek-v4-flash": "deepseek-v4-flash",
    "router-deepseek-flash": "deepseek-v4-flash",
    "arm-router-deepseek-flash": "deepseek-v4-flash",
    "deepseek-flash": "deepseek-v4-flash",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "router-deepseek-pro": "deepseek-v4-pro",
    "arm-router-deepseek-pro": "deepseek-v4-pro",
    "deepseek-pro": "deepseek-v4-pro",
}

RUN_DIR_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")


@dataclass
class ProviderRow:
    cache_hit_input: int = 0
    cache_miss_input: int = 0
    output_tokens: int = 0
    request_count: int = 0
    provider_cost: Decimal = Decimal("0")


@dataclass
class SessionRow:
    cache_hit_input: int = 0
    cache_miss_input: int = 0
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


def money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "$0.000000"
    return f"${float(value):.6f}"


def fmt_int(value: int | None) -> str:
    return f"{int(value or 0):,}"


def infer_model_from_text(text: str) -> str | None:
    low = text.lower()
    for needle, model in MODEL_BY_TEXT.items():
        if needle in low:
            return model
    return None


def infer_arm_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("arm-router-deepseek-"):
            return part.removeprefix("arm-")
        if part.startswith("router-deepseek-"):
            return part
    model = infer_model_from_text(str(path)) or "unknown"
    return model.replace("deepseek-v4-", "router-deepseek-")


def run_date_from_path(path: Path) -> str | None:
    for part in path.parts:
        if RUN_DIR_RE.fullmatch(part):
            return part.split("__", 1)[0]
    return None


def logical_artifact_key(path: Path) -> str:
    """Deduplicate copied GitHub artifacts against checked-out results.

    A downloaded artifact may contain the same logical result/session path as
    results/phase3. Compare from the first results/phase3 component onward.
    """
    parts = list(path.parts)
    for idx, part in enumerate(parts):
        if part == "results" and idx + 1 < len(parts) and parts[idx + 1] == "phase3":
            return Path(*parts[idx:]).as_posix()
    return path.as_posix()


def parse_utc_date_from_message(obj: dict[str, Any], fallback_path: Path) -> str | None:
    candidates: list[Any] = [
        obj.get("timestamp"),
        obj.get("created_at"),
        obj.get("time"),
    ]

    msg = obj.get("message")
    if isinstance(msg, dict):
        candidates.extend([
            msg.get("timestamp"),
            msg.get("created_at"),
            msg.get("time"),
        ])

    for value in candidates:
        if value in (None, ""):
            continue

        try:
            if isinstance(value, (int, float)):
                # Milliseconds if it looks too large for seconds.
                seconds = float(value) / 1000.0 if float(value) > 1e12 else float(value)
                return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()

            if isinstance(value, str):
                s = value.strip()
                if not s:
                    continue
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).date().isoformat()
        except Exception:
            continue

    return run_date_from_path(fallback_path)


def read_csv_rows_from_zip(zip_path: Path, member_name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as z:
        with z.open(member_name) as f:
            return list(csv.DictReader((line.decode("utf-8-sig", errors="replace") for line in f)))


def scan_provider_archives(usage_zips: list[Path]) -> dict[tuple[str, str], ProviderRow]:
    provider: dict[tuple[str, str], ProviderRow] = defaultdict(ProviderRow)

    for zip_path in usage_zips:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()

        for name in names:
            base = Path(name).name.lower()
            if not base.endswith(".csv"):
                continue

            rows = read_csv_rows_from_zip(zip_path, name)

            if base.startswith("cost-"):
                for r in rows:
                    date = (r.get("utc_date") or "").strip()
                    model = (r.get("model") or "").strip()
                    if not date or model not in DEEPSEEK_MODELS:
                        continue
                    provider[(date, model)].provider_cost += Decimal(str(r.get("cost") or "0"))

            if base.startswith("amount-"):
                for r in rows:
                    date = (r.get("utc_date") or "").strip()
                    model = (r.get("model") or "").strip()
                    kind = (r.get("type") or "").strip()
                    amount = intish(r.get("amount"))

                    if not date or model not in DEEPSEEK_MODELS:
                        continue

                    row = provider[(date, model)]
                    if kind == "input_cache_hit_tokens":
                        row.cache_hit_input += amount
                    elif kind == "input_cache_miss_tokens":
                        row.cache_miss_input += amount
                    elif kind == "output_tokens":
                        row.output_tokens += amount
                    elif kind == "request_count":
                        row.request_count += amount

    return dict(provider)


def scan_session_jsonl(artifact_roots: list[Path]) -> dict[tuple[str, str], SessionRow]:
    rows: dict[tuple[str, str], SessionRow] = defaultdict(SessionRow)
    seen_logical_paths: set[str] = set()

    for root in artifact_roots:
        if not root.exists():
            continue

        for path in sorted(root.rglob("agent/sessions/projects/-app/*.jsonl")):
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
                if model not in DEEPSEEK_MODELS:
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

                # DeepSeek through the Anthropic-compatible path reports provider-side
                # cache misses as the normal input token count plus cache-creation input.
                cache_hit = intish(
                    usage.get("cache_read_input_tokens")
                    or usage.get("input_cache_hit_tokens")
                    or usage.get("cache_hit_input_tokens")
                )
                cache_creation = intish(usage.get("cache_creation_input_tokens"))
                input_tokens = intish(usage.get("input_tokens"))
                cache_miss = input_tokens + cache_creation
                output_tokens = intish(usage.get("output_tokens"))

                row = rows[(date, model)]
                row.cache_hit_input += cache_hit
                row.cache_miss_input += cache_miss
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
            logical_key = logical_artifact_key(path)
            if logical_key in seen_logical_paths:
                continue
            seen_logical_paths.add(logical_key)

            model = infer_model_from_text(str(path))
            if model not in DEEPSEEK_MODELS:
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
                # Skip per-trial result.json files in this aggregate table.
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


def status_for(provider: ProviderRow, session: SessionRow) -> str:
    provider_has_usage = any([
        provider.cache_hit_input,
        provider.cache_miss_input,
        provider.output_tokens,
        provider.request_count,
        provider.provider_cost,
    ])
    session_has_usage = any([
        session.cache_hit_input,
        session.cache_miss_input,
        session.output_tokens,
        session.assistant_messages,
    ])

    if provider_has_usage and not session_has_usage:
        return "provider usage outside retained artifacts"

    if provider_has_usage and session_has_usage:
        exact = (
            provider.cache_hit_input == session.cache_hit_input
            and provider.cache_miss_input == session.cache_miss_input
            and provider.output_tokens == session.output_tokens
        )
        if exact:
            return "session tokens confirmed"

        session_is_subset = (
            session.cache_hit_input <= provider.cache_hit_input
            and session.cache_miss_input <= provider.cache_miss_input
            and session.output_tokens <= provider.output_tokens
        )
        if session_is_subset:
            return "partial retained artifacts / additional same-day provider usage"

        return "token mismatch"

    if session_has_usage and not provider_has_usage:
        return "token mismatch"

    return "no usage"


def make_reconciliation_rows(
    provider: dict[tuple[str, str], ProviderRow],
    sessions: dict[tuple[str, str], SessionRow],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for key in sorted(set(provider) | set(sessions)):
        date, model = key
        p = provider.get(key, ProviderRow())
        s = sessions.get(key, SessionRow())

        rows.append({
            "date": date,
            "model": model,
            "provider_cache_hit_input": p.cache_hit_input,
            "session_cache_hit_input": s.cache_hit_input,
            "cache_hit_diff": p.cache_hit_input - s.cache_hit_input,
            "provider_cache_miss_input": p.cache_miss_input,
            "session_cache_miss_input": s.cache_miss_input,
            "cache_miss_diff": p.cache_miss_input - s.cache_miss_input,
            "provider_output_tokens": p.output_tokens,
            "session_output_tokens": s.output_tokens,
            "output_diff": p.output_tokens - s.output_tokens,
            "provider_request_count": p.request_count,
            "session_assistant_messages": s.assistant_messages,
            "provider_cost": float(p.provider_cost),
            "status": status_for(p, s),
        })

    return rows


def write_markdown(
    out_path: Path,
    provider: dict[tuple[str, str], ProviderRow],
    rec_rows: list[dict[str, Any]],
    aggregates: list[AggregateRow],
) -> None:
    lines: list[str] = []

    lines.append("# DeepSeek Family Usage Reconciliation")
    lines.append("")
    lines.append("This report reconciles DeepSeek provider-dashboard archive exports against benchmark result artifacts.")
    lines.append("")
    lines.append("Raw provider identifiers from archive exports are intentionally omitted. Provider ZIP archives should not be committed.")
    lines.append("")
    lines.append("Session rows are grouped by assistant-message timestamp converted to UTC date, because provider billing is UTC-date based while benchmark run directory names may not be.")
    lines.append("")
    lines.append("For DeepSeek Anthropic-compatible usage, session cache-miss input is calculated as `input_tokens + cache_creation_input_tokens`; cache-hit input is `cache_read_input_tokens`.")
    lines.append("")

    lines.append("## Provider family totals")
    lines.append("")
    lines.append("| Date | Model | Cache-hit input | Cache-miss input | Total input | Output | Requests | Provider cost |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for (date, model), row in sorted(provider.items()):
        total_input = row.cache_hit_input + row.cache_miss_input
        lines.append(
            f"| {date} | `{model}` | {fmt_int(row.cache_hit_input)} | {fmt_int(row.cache_miss_input)} | "
            f"{fmt_int(total_input)} | {fmt_int(row.output_tokens)} | {fmt_int(row.request_count)} | "
            f"{money(row.provider_cost)} |"
        )
    lines.append("")

    lines.append("## Session-level reconciliation")
    lines.append("")
    lines.append("| Date | Model | Provider cache-hit | Session cache-hit | Hit diff | Provider cache-miss | Session cache-miss | Miss diff | Provider output | Session output | Output diff | Provider requests | Session messages | Provider cost | Status |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rec_rows:
        lines.append(
            f"| {r['date']} | `{r['model']}` | "
            f"{fmt_int(r['provider_cache_hit_input'])} | {fmt_int(r['session_cache_hit_input'])} | {fmt_int(r['cache_hit_diff'])} | "
            f"{fmt_int(r['provider_cache_miss_input'])} | {fmt_int(r['session_cache_miss_input'])} | {fmt_int(r['cache_miss_diff'])} | "
            f"{fmt_int(r['provider_output_tokens'])} | {fmt_int(r['session_output_tokens'])} | {fmt_int(r['output_diff'])} | "
            f"{fmt_int(r['provider_request_count'])} | {fmt_int(r['session_assistant_messages'])} | "
            f"{money(r['provider_cost'])} | {r['status']} |"
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
    lines.append("- Reconcile DeepSeek at the API-key/provider-family level first, then split by provider model when the archive exposes model rows.")
    lines.append("- Provider cost is the funding source of truth because it reflects provider-side cache-hit/cache-miss billing.")
    lines.append("- Session JSONL assistant-message usage is the preferred token source for billing reconciliation, especially for timeout-edge trials.")
    lines.append("- Current retained June smoke artifacts should reconcile exactly for `2026-06-15 deepseek-v4-flash` and `2026-06-16 deepseek-v4-pro`.")
    lines.append("- Older May rows may remain historical/provider-family usage that is only partially covered, or not covered, by retained benchmark artifacts.")
    lines.append("- Dashboard implication: store run start time, run end time, run directory timestamp, and provider billing UTC date separately.")
    lines.append("- Harbor aggregate `result.json` costs remain useful as internal estimates, but they may diverge from provider-billed costs.")
    lines.append("- Raw provider identifiers, API key names, masked API-key strings, user IDs, and raw provider ZIP exports are intentionally omitted from this report and JSON output.")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))


def write_json(
    out_path: Path,
    usage_zips: list[Path],
    provider: dict[tuple[str, str], ProviderRow],
    sessions: dict[tuple[str, str], SessionRow],
    rec_rows: list[dict[str, Any]],
    aggregates: list[AggregateRow],
) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "usage_archives": [p.name for p in usage_zips],
        "provider_family_totals": [
            {
                "date": date,
                "model": model,
                "cache_hit_input": row.cache_hit_input,
                "cache_miss_input": row.cache_miss_input,
                "total_input": row.cache_hit_input + row.cache_miss_input,
                "output_tokens": row.output_tokens,
                "request_count": row.request_count,
                "provider_cost": float(row.provider_cost),
            }
            for (date, model), row in sorted(provider.items())
        ],
        "session_totals": [
            {
                "date": date,
                "model": model,
                **asdict(row),
            }
            for (date, model), row in sorted(sessions.items())
        ],
        "reconciliation": rec_rows,
        "aggregate_artifacts": [asdict(row) for row in aggregates],
        "notes": [
            "Raw provider identifiers are intentionally omitted.",
            "Provider ZIP archives should not be committed.",
            "Session dates are grouped by assistant-message timestamp converted to UTC.",
            "DeepSeek session cache-miss input is input_tokens + cache_creation_input_tokens.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile DeepSeek provider archive usage against benchmark artifacts.")
    parser.add_argument("--usage-zip", action="append", type=Path, required=True, help="DeepSeek provider archive ZIP; repeatable.")
    parser.add_argument("--artifact-root", action="append", type=Path, required=True, help="Benchmark artifact root; repeatable.")
    parser.add_argument("--out-md", type=Path, required=True, help="Markdown report output.")
    parser.add_argument("--out-json", type=Path, required=True, help="JSON reconciliation output.")
    args = parser.parse_args()

    for p in args.usage_zip:
        if not p.exists():
            raise FileNotFoundError(p)

    provider = scan_provider_archives(args.usage_zip)
    sessions = scan_session_jsonl(args.artifact_root)
    aggregates = scan_aggregate_results(args.artifact_root)
    rec_rows = make_reconciliation_rows(provider, sessions)

    write_markdown(args.out_md, provider, rec_rows, aggregates)
    write_json(args.out_json, args.usage_zip, provider, sessions, rec_rows, aggregates)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
