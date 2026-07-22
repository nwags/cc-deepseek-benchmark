#!/usr/bin/env python3
"""Recompute official Kimi K3 cost estimates from Harbor result.json files.

This does not modify raw benchmark artifacts. It reads any result.json files
under the supplied root that contain Kimi K3 token fields and emits a TSV with:

- observed_cost_usd from the artifact
- official estimate assuming n_input_tokens includes cached tokens
- official estimate assuming n_input_tokens excludes cached tokens

The two interpretations are kept separate because Harbor/Claude Code result
schemas may differ by provider/router path.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


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


def record_type(data: dict[str, Any], path: Path) -> str:
    if data.get("trial_name"):
        return "trial"
    if "modernize-scientific-stack__" in str(path):
        return "trial"
    return "run"


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

    for path in sorted(args.root.rglob("result.json")):
        if "arm-router-kimi-k3" not in str(path):
            continue

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue

        n_input = as_int(data.get("n_input_tokens"))
        n_cache = as_int(data.get("n_cache_tokens"))
        n_output = as_int(data.get("n_output_tokens"))
        observed = as_float(data.get("cost_usd"))

        if n_input is None or n_cache is None or n_output is None:
            continue

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
                "record_type": record_type(data, path),
                "trial_name": data.get("trial_name", ""),
                "reward": data.get("reward", ""),
                "n_input_tokens": n_input,
                "n_cache_tokens": n_cache,
                "n_output_tokens": n_output,
                "observed_cost_usd": "" if observed is None else f"{observed:.12f}",
                "official_k3_if_input_includes_cache_usd": f"{official_if_input_includes_cache:.12f}",
                "official_k3_if_input_excludes_cache_usd": f"{official_if_input_excludes_cache:.12f}",
                "delta_observed_vs_includes_cache_usd": ""
                if observed is None
                else f"{observed - official_if_input_includes_cache:.12f}",
                "delta_observed_vs_excludes_cache_usd": ""
                if observed is None
                else f"{observed - official_if_input_excludes_cache:.12f}",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "path",
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
        writer = csv.DictWriter(f, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {args.output}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
