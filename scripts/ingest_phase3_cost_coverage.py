from __future__ import annotations

import argparse
import csv
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest adjusted Phase 3 cost coverage TSV into Supabase.")
    parser.add_argument("--trial-cost-tsv", required=True, type=Path)
    parser.add_argument("--cost-coverage-run-id", required=True)
    parser.add_argument("--db-url", default=os.environ.get("SUPABASE_DB_URL"))
    return parser.parse_args()


def blank_to_none(value: Any) -> Any:
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def decimal_or_none(value: Any) -> Decimal | None:
    value = blank_to_none(value)
    if value is None:
        return None
    return Decimal(str(value))


def int_or_none(value: Any) -> int | None:
    value = blank_to_none(value)
    if value is None:
        return None
    return int(float(str(value)))


UPSERT = """
insert into benchmark.benchmark_trial_cost_coverage (
    trial_id,
    suite_id,
    arm_id,
    run_label,
    backend_model,
    provider,
    task_id,
    attempt_index,
    reward,
    exception_type,
    runtime_seconds,
    input_tokens,
    cache_tokens,
    output_tokens,
    recorded_cost_usd,
    token_reconstructed_cost_usd,
    empirical_reconstructed_cost_usd,
    adjusted_cost_usd,
    cost_source,
    cost_confidence,
    cost_gap_reason,
    outcome_bucket,
    cost_coverage_run_id,
    source_path,
    raw_metadata
)
values (
    %(trial_id)s,
    %(suite_id)s,
    %(arm_id)s,
    %(run_label)s,
    %(backend_model)s,
    %(provider)s,
    %(task_id)s,
    %(attempt_index)s,
    %(reward)s,
    %(exception_type)s,
    %(runtime_seconds)s,
    %(input_tokens)s,
    %(cache_tokens)s,
    %(output_tokens)s,
    %(recorded_cost_usd)s,
    %(token_reconstructed_cost_usd)s,
    %(empirical_reconstructed_cost_usd)s,
    %(adjusted_cost_usd)s,
    %(cost_source)s,
    %(cost_confidence)s,
    %(cost_gap_reason)s,
    %(outcome_bucket)s,
    %(cost_coverage_run_id)s,
    %(source_path)s,
    %(raw_metadata)s
)
on conflict (trial_id) do update set
    suite_id = excluded.suite_id,
    arm_id = excluded.arm_id,
    run_label = excluded.run_label,
    backend_model = excluded.backend_model,
    provider = excluded.provider,
    task_id = excluded.task_id,
    attempt_index = excluded.attempt_index,
    reward = excluded.reward,
    exception_type = excluded.exception_type,
    runtime_seconds = excluded.runtime_seconds,
    input_tokens = excluded.input_tokens,
    cache_tokens = excluded.cache_tokens,
    output_tokens = excluded.output_tokens,
    recorded_cost_usd = excluded.recorded_cost_usd,
    token_reconstructed_cost_usd = excluded.token_reconstructed_cost_usd,
    empirical_reconstructed_cost_usd = excluded.empirical_reconstructed_cost_usd,
    adjusted_cost_usd = excluded.adjusted_cost_usd,
    cost_source = excluded.cost_source,
    cost_confidence = excluded.cost_confidence,
    cost_gap_reason = excluded.cost_gap_reason,
    outcome_bucket = excluded.outcome_bucket,
    cost_coverage_run_id = excluded.cost_coverage_run_id,
    source_path = excluded.source_path,
    raw_metadata = excluded.raw_metadata,
    updated_at = now()
"""


def row_params(row: dict[str, str], *, source_path: Path, cost_coverage_run_id: str) -> dict[str, Any]:
    return {
        "trial_id": row["trial_id"],
        "suite_id": row["suite_id"],
        "arm_id": row["arm_id"],
        "run_label": row["run_label"],
        "backend_model": blank_to_none(row.get("backend_model")),
        "provider": blank_to_none(row.get("provider")),
        "task_id": row["task_id"],
        "attempt_index": int_or_none(row.get("attempt_index")),
        "reward": decimal_or_none(row.get("reward")),
        "exception_type": blank_to_none(row.get("exception_type")),
        "runtime_seconds": decimal_or_none(row.get("runtime_seconds")),
        "input_tokens": int_or_none(row.get("input_tokens")) or 0,
        "cache_tokens": int_or_none(row.get("cache_tokens")) or 0,
        "output_tokens": int_or_none(row.get("output_tokens")) or 0,
        "recorded_cost_usd": decimal_or_none(row.get("recorded_cost_usd")),
        "token_reconstructed_cost_usd": decimal_or_none(row.get("token_reconstructed_cost_usd")),
        "empirical_reconstructed_cost_usd": decimal_or_none(row.get("empirical_reconstructed_cost_usd")),
        "adjusted_cost_usd": decimal_or_none(row.get("adjusted_cost_usd")),
        "cost_source": row["cost_source"],
        "cost_confidence": row["cost_confidence"],
        "cost_gap_reason": blank_to_none(row.get("cost_gap_reason")),
        "outcome_bucket": row["outcome_bucket"],
        "cost_coverage_run_id": cost_coverage_run_id,
        "source_path": str(source_path),
        "raw_metadata": Json({"source": "scripts/ingest_phase3_cost_coverage.py"}),
    }


def main() -> None:
    args = parse_args()
    if not args.db_url:
        raise SystemExit("SUPABASE_DB_URL is required via --db-url or environment.")

    with args.trial_cost_tsv.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    params = [
        row_params(row, source_path=args.trial_cost_tsv, cost_coverage_run_id=args.cost_coverage_run_id)
        for row in rows
    ]

    with psycopg.connect(args.db_url) as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT, params)
        conn.commit()

    print(f"ingested_cost_coverage_rows={len(params)}")
    print(f"cost_coverage_run_id={args.cost_coverage_run_id}")


if __name__ == "__main__":
    main()
