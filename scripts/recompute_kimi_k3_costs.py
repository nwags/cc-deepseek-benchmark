#!/usr/bin/env python3
"""Recompute official Kimi K3 cost estimates from Harbor result.json files.

This does not modify raw benchmark artifacts. It scans Kimi K3 result.json
files recursively because Harbor run-level and trial-level schemas can nest
token/cost fields at different depths.

It emits both:
- observed_cost_usd from the artifact
- official estimate assuming n_input_tokens includes cached tokens
- official estimate assuming n_input_tokens excludes cached tokens
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


INPUT_COST = 0.000003       # $3.00 / 1M input tokens
CACHE_READ_COST = 0.0000003 # $0.30 / 1M cache-hit input tokens
OUTPUT_COST = 0.000015      # $15.00 / 1M output tokens


def as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def iter_objects(value: Any, path: str = "$") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from iter_objects(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_objects(child, f"{path}[{index}]")


def file_role(path: Path) -> str:
    if path.name != "result.json":
        return "unknown"

    parent = path.parent.name
    if "__" in parent and not parent.startswith("2026-"):
        return "trial_result"

    return "run_result"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        type=Path,
        help="Root directory to scan, e.g. /tmp/kimi-k3-canary-29931863183",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/phase3/reporting/kimi_k3_cost_recompute.tsv"),
    )
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, int, int, str]] = set()

    for path in sorted(args.root.rglob("result.json")):
        if "arm-router-kimi-k3" not in str(path):
            continue

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue

        for json_path, obj in iter_objects(data):
            n_input = as_int(obj.get("n_input_tokens"))
            n_cache = as_int(obj.get("n_cache_tokens"))
            n_output = as_int(obj.get("n_output_tokens"))
            observed = as_float(obj.get("cost_usd"))

            if n_input is None or n_cache is None or n_output is None:
                continue

            trial_name = str(obj.get("trial_name") or data.get("trial_name") or "")
            reward = obj.get("reward", data.get("reward", ""))

            identity = (
                str(path),
                json_path,
                n_input,
                n_cache,
                n_output,
                "" if observed is None else f"{observed:.12f}",
            )
            if identity in seen:
                continue
            seen.add(identity)

            uncached_if_input_includes_cache = max(n_input - n_cache, 0)

            official_if_input_includes_cache = (
                uncached_if_input_includes_cache * INPUT_COST
                + n_cache * CACHE_READ_COST
                + n_output * OUTPUT_COST
            )

            official_if_input_excludes_cache = (
                n_input * INPUT_COST
                + n_cache * CACHE_READ_COST
                + n_output * OUTPUT_COST
            )

            rows.append(
                {
                    "path": str(path),
                    "json_path": json_path,
                    "record_type": file_role(path),
                    "trial_name": trial_name,
                    "reward": reward,
                    "n_input_tokens": n_input,
                    "n_cache_tokens": n_cache,
                    "n_output_tokens": n_output,
                    "observed_cost_usd": "NA" if observed is None else f"{observed:.12f}",
                    "official_k3_if_input_includes_cache_usd": f"{official_if_input_includes_cache:.12f}",
                    "official_k3_if_input_excludes_cache_usd": f"{official_if_input_excludes_cache:.12f}",
                    "delta_observed_vs_includes_cache_usd": "NA"
                    if observed is None
                    else f"{observed - official_if_input_includes_cache:.12f}",
                    "delta_observed_vs_excludes_cache_usd": "NA"
                    if observed is None
                    else f"{observed - official_if_input_excludes_cache:.12f}",
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "path",
        "json_path",
        "record_type",
        "trial_name",
        "reward",
        "n_input_tokens",
        "n_cache_tokens",
        "n_output_tokens",
        "observed_cost_usd",
        "official_k3_if_input_includes_cache_usd",
        "official_k3_if_input_excludes_cache_usd",
        "delta_observed_vs_includes_cache_usd",
        "delta_observed_vs_excludes_cache_usd",
    ]

    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {args.output}")
    print(f"rows={len(rows)}")
    if not rows:
        raise SystemExit("No Kimi K3 token/cost rows found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
