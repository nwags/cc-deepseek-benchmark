#!/usr/bin/env python3
"""Reconcile OpenAI provider-dashboard exports against Phase 3 benchmark artifacts.

The script intentionally does not print raw API-key IDs, project IDs, organization IDs,
user emails, or organization/project names from the provider CSV exports.

Example:
  python scripts/reconcile_openai_family_usage.py \
    --usage-csv ~/Downloads/completions_usage_2026-05-18_2026-06-17.csv \
    --cost-csv ~/Downloads/'cost_2026-05-18_2026-06-17 (1).csv' \
    --artifact-root results/phase3 \
    --artifact-root /tmp/phase3-openai-smoke-27641152143 \
    --out-md docs/reports/phase3/OPENAI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md \
    --out-json results/phase3/supplemental/openai_family_reconciliation_2026-06-17.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


MODEL_RE = re.compile(r"^(gpt-\d+(?:\.\d+)?)")
ARM_RE = re.compile(r"arm-(router-gpt-[^/]+)")
RUN_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})__\d{2}-\d{2}-\d{2}")


@dataclass
class ProviderModelUsage:
    date: str
    model: str
    cached_input_tokens: int = 0
    uncached_input_tokens: int = 0
    output_tokens: int = 0
    cached_input_cost: float = 0.0
    uncached_input_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def input_tokens(self) -> int:
        return self.cached_input_tokens + self.uncached_input_tokens

    @property
    def cost_usd(self) -> float:
        return self.cached_input_cost + self.uncached_input_cost + self.output_cost


@dataclass
class ProviderFamilyUsage:
    date: str
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    uncached_input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class BenchmarkAggregate:
    date: str
    arm_id: str
    model: str
    path: str
    n_total_trials: int = 0
    n_completed_trials: int = 0
    n_errored_trials: int = 0
    input_tokens: int = 0
    cache_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


def parse_date(value: str) -> str:
    return value[:10]


def safe_int(value: Any) -> int:
    if value in (None, "", "nan"):
        return 0
    try:
        return int(float(value))
    except Exception:
        return 0


def safe_float(value: Any) -> float:
    if value in (None, "", "nan"):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def normalize_provider_model(line_item: str) -> str | None:
    match = MODEL_RE.search(line_item.strip())
    return match.group(1) if match else None


def normalize_arm_model(arm_id: str) -> str:
    return arm_id.replace("router-", "", 1)


def parse_provider_family_usage(usage_csv: Path, total_cost_by_date: dict[str, float]) -> dict[str, ProviderFamilyUsage]:
    by_date: dict[str, ProviderFamilyUsage] = {}
    with usage_csv.expanduser().open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            date = parse_date(row.get("start_time_iso", ""))
            input_tokens = safe_int(row.get("input_tokens"))
            output_tokens = safe_int(row.get("output_tokens"))
            cached = safe_int(row.get("input_cached_tokens"))
            uncached = safe_int(row.get("input_uncached_tokens"))
            requests = safe_int(row.get("num_model_requests"))
            if not any([input_tokens, output_tokens, cached, uncached, requests]):
                continue
            by_date[date] = ProviderFamilyUsage(
                date=date,
                requests=requests,
                input_tokens=input_tokens,
                cached_input_tokens=cached,
                uncached_input_tokens=uncached,
                output_tokens=output_tokens,
                cost_usd=total_cost_by_date.get(date, 0.0),
            )
    return by_date


def parse_total_costs(cost_csv: Path) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    with cost_csv.expanduser().open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            amount = safe_float(row.get("amount_value"))
            if not amount:
                continue
            date = parse_date(row.get("start_time_iso", ""))
            totals[date] += amount
    return dict(totals)


def parse_provider_model_costs(cost_csv: Path) -> dict[tuple[str, str], ProviderModelUsage]:
    by_date_model: dict[tuple[str, str], ProviderModelUsage] = {}
    with cost_csv.expanduser().open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            amount = safe_float(row.get("amount_value"))
            quantity = safe_int(row.get("quantity"))
            line_item = row.get("line_item") or ""
            if not amount or not quantity or not line_item:
                continue

            date = parse_date(row.get("start_time_iso", ""))
            model = normalize_provider_model(line_item)
            if not date or not model:
                continue

            key = (date, model)
            entry = by_date_model.setdefault(key, ProviderModelUsage(date=date, model=model))

            line_item_lower = line_item.lower()
            if "cached input" in line_item_lower:
                entry.cached_input_tokens += quantity
                entry.cached_input_cost += amount
            elif "output" in line_item_lower:
                entry.output_tokens += quantity
                entry.output_cost += amount
            elif "input" in line_item_lower:
                entry.uncached_input_tokens += quantity
                entry.uncached_input_cost += amount

    return by_date_model


def extract_arm_id(path: Path, data: dict[str, Any]) -> str | None:
    match = ARM_RE.search(path.as_posix())
    if match:
        return match.group(1)

    config = data.get("config")
    if isinstance(config, dict):
        agent = config.get("agent")
        if isinstance(agent, dict):
            model_name = agent.get("model_name")
            if isinstance(model_name, str) and model_name.startswith("router-gpt-"):
                return model_name

    return None


def extract_run_date(path: Path) -> str | None:
    match = RUN_DATE_RE.search(path.as_posix())
    return match.group(1) if match else None


def parse_benchmark_aggregates(artifact_roots: list[Path]) -> list[BenchmarkAggregate]:
    aggregates: list[BenchmarkAggregate] = []
    seen_paths: set[Path] = set()

    for root in artifact_roots:
        root = root.expanduser()
        if not root.exists():
            continue

        for path in sorted(root.rglob("result.json")):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            try:
                data = json.loads(path.read_text())
            except Exception:
                continue

            if not isinstance(data, dict) or not isinstance(data.get("stats"), dict):
                continue

            arm_id = extract_arm_id(path, data)
            if not arm_id or not arm_id.startswith("router-gpt-"):
                continue

            date = extract_run_date(path)
            if not date:
                continue

            stats = data["stats"]
            aggregates.append(
                BenchmarkAggregate(
                    date=date,
                    arm_id=arm_id,
                    model=normalize_arm_model(arm_id),
                    path=path.as_posix(),
                    n_total_trials=safe_int(data.get("n_total_trials")),
                    n_completed_trials=safe_int(stats.get("n_completed_trials")),
                    n_errored_trials=safe_int(stats.get("n_errored_trials")),
                    input_tokens=safe_int(stats.get("n_input_tokens")),
                    cache_tokens=safe_int(stats.get("n_cache_tokens")),
                    output_tokens=safe_int(stats.get("n_output_tokens")),
                    cost_usd=safe_float(stats.get("cost_usd")),
                )
            )

    return aggregates


def aggregate_benchmarks(aggregates: list[BenchmarkAggregate]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for aggregate in aggregates:
        key = (aggregate.date, aggregate.model)
        row = grouped.setdefault(
            key,
            {
                "date": aggregate.date,
                "model": aggregate.model,
                "arms": set(),
                "runs": 0,
                "n_total_trials": 0,
                "n_completed_trials": 0,
                "n_errored_trials": 0,
                "input_tokens": 0,
                "cache_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "paths": [],
            },
        )
        row["arms"].add(aggregate.arm_id)
        row["runs"] += 1
        row["n_total_trials"] += aggregate.n_total_trials
        row["n_completed_trials"] += aggregate.n_completed_trials
        row["n_errored_trials"] += aggregate.n_errored_trials
        row["input_tokens"] += aggregate.input_tokens
        row["cache_tokens"] += aggregate.cache_tokens
        row["output_tokens"] += aggregate.output_tokens
        row["cost_usd"] += aggregate.cost_usd
        row["paths"].append(aggregate.path)

    for row in grouped.values():
        row["arms"] = sorted(row["arms"])

    return grouped


def money(value: float) -> str:
    return f"${value:,.6f}"


def integer(value: int) -> str:
    return f"{value:,}"


def generate_markdown(
    provider_family: dict[str, ProviderFamilyUsage],
    provider_models: dict[tuple[str, str], ProviderModelUsage],
    benchmark_models: dict[tuple[str, str], dict[str, Any]],
    aggregates: list[BenchmarkAggregate],
) -> str:
    dates = sorted(set(provider_family) | {date for date, _ in provider_models} | {date for date, _ in benchmark_models})
    model_keys = sorted(set(provider_models) | set(benchmark_models))

    lines: list[str] = []
    lines.append("# OpenAI Family Usage Reconciliation")
    lines.append("")
    lines.append("This report reconciles OpenAI provider-dashboard exports against benchmark result artifacts.")
    lines.append("")
    lines.append("Raw provider identifiers from CSV exports are intentionally omitted.")
    lines.append("")
    lines.append("## Provider family totals")
    lines.append("")
    lines.append("| Date | Requests | Input | Cached input | Uncached input | Output | Provider cost |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for date in dates:
        row = provider_family.get(date)
        if not row:
            continue
        lines.append(
            f"| {date} | {integer(row.requests)} | {integer(row.input_tokens)} | "
            f"{integer(row.cached_input_tokens)} | {integer(row.uncached_input_tokens)} | "
            f"{integer(row.output_tokens)} | {money(row.cost_usd)} |"
        )

    lines.append("")
    lines.append("## Model-level reconciliation")
    lines.append("")
    lines.append("| Date | Model | Provider input | Benchmark input | Input diff | Provider output | Benchmark output | Output diff | Provider cost | Benchmark cost | Cost diff | Status |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    for key in model_keys:
        date, model = key
        provider = provider_models.get(key)
        benchmark = benchmark_models.get(key)

        provider_input = provider.input_tokens if provider else 0
        provider_output = provider.output_tokens if provider else 0
        provider_cost = provider.cost_usd if provider else 0.0

        benchmark_input = int(benchmark["input_tokens"]) if benchmark else 0
        benchmark_output = int(benchmark["output_tokens"]) if benchmark else 0
        benchmark_cost = float(benchmark["cost_usd"]) if benchmark else 0.0

        input_diff = provider_input - benchmark_input
        output_diff = provider_output - benchmark_output
        cost_diff = provider_cost - benchmark_cost

        if provider and benchmark and input_diff == 0 and output_diff == 0:
            status = "tokens confirmed"
        elif provider and not benchmark:
            status = "provider usage missing benchmark artifact"
        elif benchmark and not provider:
            status = "benchmark artifact missing provider row"
        else:
            status = "token mismatch"

        lines.append(
            f"| {date} | `{model}` | {integer(provider_input)} | {integer(benchmark_input)} | "
            f"{integer(input_diff)} | {integer(provider_output)} | {integer(benchmark_output)} | "
            f"{integer(output_diff)} | {money(provider_cost)} | {money(benchmark_cost)} | "
            f"{money(cost_diff)} | {status} |"
        )

    lines.append("")
    lines.append("## Benchmark aggregate artifacts included")
    lines.append("")
    lines.append("| Date | Arm | Trials | Completed | Errors | Input | Output | Cost | Path |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
    for row in sorted(aggregates, key=lambda item: (item.date, item.arm_id, item.path)):
        lines.append(
            f"| {row.date} | `{row.arm_id}` | {row.n_total_trials} | {row.n_completed_trials} | "
            f"{row.n_errored_trials} | {integer(row.input_tokens)} | {integer(row.output_tokens)} | "
            f"{money(row.cost_usd)} | `{row.path}` |"
        )

    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("")
    lines.append("- Reconcile provider dashboards at the API-key/project/family level first.")
    lines.append("- Use model-level provider breakdowns when available to attribute family usage to benchmark arms.")
    lines.append("- Provider cost is the funding source of truth because it accounts for cached input billing and other provider-side billing rules.")
    lines.append("- Benchmark cost remains useful as an internal estimator but may differ from provider-billed cost.")
    lines.append("- If provider usage appears without a benchmark artifact, download the corresponding GitHub Actions artifact and rerun this script.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usage-csv", required=True, type=Path)
    parser.add_argument("--cost-csv", required=True, type=Path, help="Detailed model/line-item cost CSV if available.")
    parser.add_argument("--artifact-root", action="append", default=[], type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args()

    total_cost_by_date = parse_total_costs(args.cost_csv)
    provider_family = parse_provider_family_usage(args.usage_csv, total_cost_by_date)
    provider_models = parse_provider_model_costs(args.cost_csv)
    aggregates = parse_benchmark_aggregates(args.artifact_root)
    benchmark_models = aggregate_benchmarks(aggregates)

    markdown = generate_markdown(provider_family, provider_models, benchmark_models, aggregates)

    payload = {
        "provider_family": {date: asdict(row) for date, row in provider_family.items()},
        "provider_models": {f"{date}/{model}": asdict(row) for (date, model), row in provider_models.items()},
        "benchmark_aggregates": [asdict(row) for row in aggregates],
        "benchmark_models": {
            f"{date}/{model}": row for (date, model), row in benchmark_models.items()
        },
    }

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(markdown)
    else:
        print(markdown)

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
