#!/usr/bin/env python3
"""Generate Phase 3 qualitative artifact-review evidence inventories."""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import quote


DEFAULT_SUITE_ID = "phase3-full-20"
DEFAULT_OUTPUT_DIR = Path("results/phase3/reporting")
DEFAULT_DOCS_DIR = Path("docs/reports/phase3")

ANOMALY_FLAGS = {
    "exception",
    "exception_with_success",
    "suspect_noop_zero_token",
    "normal_failed_trial",
}
EXCEPTION_FLAGS = {"exception", "exception_with_success"}
SUSPECT_NOOP_FLAG = "suspect_noop_zero_token"

SONNET_RUN_LABEL = "router-anthropic-sonnet/2026-06-27__01-30-11"
SONNET_EXPECTED_COUNTS = {
    "trials": 60,
    "successes": 28,
    "exception_failures": 23,
    "normal_failures": 9,
    "missing_cost_trials": 22,
}

TRIAL_EVIDENCE_HEADERS = [
    "suite_id",
    "arm_id",
    "run_label",
    "task_id",
    "attempt_index",
    "trial_id",
    "quality_flag",
    "reward",
    "exception_type",
    "exception_summary",
    "runtime_seconds",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "missing_cost",
    "validity_status",
    "invalid_reason",
    "artifact_count",
    "artifact_types_present",
    "has_result",
    "has_exception",
    "has_agent_transcript",
    "has_trajectory",
    "has_trial_log",
    "has_verifier_stdout",
    "has_verifier_ctrf",
    "has_verifier_reward",
    "first_artifact_dashboard_path",
    "trial_dashboard_path",
]

ARM_TASK_HEADERS = [
    "arm_id",
    "task_id",
    "attempt_count",
    "success_count",
    "normal_failure_count",
    "exception_count",
    "suspect_noop_count",
    "missing_cost_count",
    "representative_exception_type",
    "review_status",
    "qualitative_summary",
]

ARM_SUMMARY_HEADERS = [
    "arm_id",
    "trial_count",
    "success_count",
    "exception_count",
    "suspect_noop_count",
    "normal_failure_count",
    "missing_cost_count",
    "dominant_exception_type",
    "review_priority",
    "qualitative_summary",
]

TASK_SUMMARY_HEADERS = [
    "task_id",
    "arm_count",
    "trial_count",
    "success_count",
    "exception_count",
    "suspect_noop_count",
    "normal_failure_count",
    "review_priority",
    "qualitative_summary",
]

EXCEPTION_REVIEW_TARGET_HEADERS = [
    "suite_id",
    "arm_id",
    "run_label",
    "task_id",
    "attempt_index",
    "trial_id",
    "exception_artifact_id",
    "trial_dashboard_path",
    "exception_artifact_dashboard_path",
    "exception_type",
    "missing_cost",
    "validity_status",
    "invalid_reason",
    "reward",
    "runtime_seconds",
    "r2_uri",
    "size_bytes",
]


@dataclass(frozen=True)
class GeneratedFiles:
    trial_evidence: Path
    exception_audit: Path
    suspect_noop_audit: Path
    arm_task_matrix: Path
    arm_summary: Path
    task_summary: Path
    exception_review_targets: Path
    markdown_review: Path

    def as_list(self) -> list[Path]:
        return [
            self.trial_evidence,
            self.exception_audit,
            self.suspect_noop_audit,
            self.arm_task_matrix,
            self.arm_summary,
            self.task_summary,
            self.exception_review_targets,
            self.markdown_review,
        ]


def utc_datestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def require_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(
            "psycopg[binary] is required. Source .secrets/supabase.env, then run with "
            "`uv run --with 'psycopg[binary]' python scripts/generate_phase3_qualitative_audit.py ...` "
            "if it is not already installed in the project environment."
        ) from exc
    return psycopg, dict_row


def connect() -> Any:
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL is required; source .secrets/supabase.env before running.")
    psycopg, dict_row = require_psycopg()
    return psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10)


def as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def is_success(row: dict[str, Any]) -> bool:
    reward = as_decimal(row.get("reward"))
    return reward is not None and reward > 0


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float, Decimal)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def missing_cost(row: dict[str, Any]) -> bool:
    if "missing_cost" in row:
        return bool_value(row.get("missing_cost"))
    return row.get("cost_usd") is None


def quality_flag(row: dict[str, Any]) -> str:
    return str(row.get("quality_flag") or "")


def is_exception(row: dict[str, Any]) -> bool:
    return quality_flag(row) in EXCEPTION_FLAGS or bool(row.get("exception_type"))


def is_suspect_noop(row: dict[str, Any]) -> bool:
    return quality_flag(row) == SUSPECT_NOOP_FLAG


def is_normal_failure(row: dict[str, Any]) -> bool:
    return quality_flag(row) == "normal_failed_trial"


def count_rows(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    return {
        "trial_count": len(rows),
        "success_count": sum(1 for row in rows if is_success(row)),
        "exception_count": sum(1 for row in rows if is_exception(row)),
        "suspect_noop_count": sum(1 for row in rows if is_suspect_noop(row)),
        "normal_failure_count": sum(1 for row in rows if is_normal_failure(row)),
        "missing_cost_count": sum(1 for row in rows if missing_cost(row)),
    }


def most_common_exception_type(rows: Sequence[dict[str, Any]]) -> str:
    counts = Counter(
        str(row.get("exception_type") or "")
        for row in rows
        if is_exception(row) and row.get("exception_type")
    )
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def review_priority(summary: dict[str, int]) -> str:
    high_signal = summary.get("exception_count", 0) + summary.get("suspect_noop_count", 0)
    if high_signal >= 5:
        return "high"
    if high_signal > 0:
        return "medium"
    if summary.get("normal_failure_count", 0) > summary.get("success_count", 0):
        return "medium"
    return "low"


def filter_evidence_rows(rows: Sequence[dict[str, Any]], *, include_successes: bool = False) -> list[dict[str, Any]]:
    if include_successes:
        return list(rows)
    return [
        row
        for row in rows
        if quality_flag(row) in ANOMALY_FLAGS or not is_success(row)
    ]


def build_arm_task_matrix(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("arm_id") or ""), str(row.get("task_id") or ""))].append(row)

    matrix: list[dict[str, Any]] = []
    for (arm_id, task_id), group in sorted(grouped.items()):
        summary = count_rows(group)
        matrix.append(
            {
                "arm_id": arm_id,
                "task_id": task_id,
                "attempt_count": summary["trial_count"],
                "success_count": summary["success_count"],
                "normal_failure_count": summary["normal_failure_count"],
                "exception_count": summary["exception_count"],
                "suspect_noop_count": summary["suspect_noop_count"],
                "missing_cost_count": summary["missing_cost_count"],
                "representative_exception_type": most_common_exception_type(group),
                "review_status": "pending",
                "qualitative_summary": "",
            }
        )
    return matrix


def build_arm_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("arm_id") or "")].append(row)

    summaries: list[dict[str, Any]] = []
    for arm_id, group in sorted(grouped.items()):
        summary = count_rows(group)
        summaries.append(
            {
                "arm_id": arm_id,
                "trial_count": summary["trial_count"],
                "success_count": summary["success_count"],
                "exception_count": summary["exception_count"],
                "suspect_noop_count": summary["suspect_noop_count"],
                "normal_failure_count": summary["normal_failure_count"],
                "missing_cost_count": summary["missing_cost_count"],
                "dominant_exception_type": most_common_exception_type(group),
                "review_priority": review_priority(summary),
                "qualitative_summary": "",
            }
        )
    return summaries


def build_task_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("task_id") or "")].append(row)

    summaries: list[dict[str, Any]] = []
    for task_id, group in sorted(grouped.items()):
        summary = count_rows(group)
        summaries.append(
            {
                "task_id": task_id,
                "arm_count": len({str(row.get("arm_id") or "") for row in group}),
                "trial_count": summary["trial_count"],
                "success_count": summary["success_count"],
                "exception_count": summary["exception_count"],
                "suspect_noop_count": summary["suspect_noop_count"],
                "normal_failure_count": summary["normal_failure_count"],
                "review_priority": review_priority(summary),
                "qualitative_summary": "",
            }
        )
    return summaries


def clean_tsv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_tsv(path: Path, rows: Iterable[dict[str, Any]], headers: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(headers),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({header: clean_tsv_value(row.get(header)) for header in headers})


def fetch_trial_rows(
    conn: Any,
    *,
    suite_id: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
) -> list[dict[str, Any]]:
    params: list[Any] = [suite_id]
    focus_clause = ""
    if focus_arms:
        params.append(list(focus_arms))
        focus_clause = "and q.arm_id = any(%s)"

    valid_clause = "" if include_invalid else "and invalid.id is null"

    sql = f"""
        select
          q.suite_id,
          q.arm_id,
          q.run_label,
          q.task_id,
          q.attempt_index::int as attempt_index,
          q.trial_id::text as trial_id,
          q.quality_flag,
          q.reward,
          q.exception_type,
          q.exception_summary,
          q.runtime_seconds,
          q.input_tokens,
          q.output_tokens,
          q.cost_usd,
          (q.cost_usd is null) as missing_cost,
          case
            when invalid.id is null then 'valid'
            else coalesce(invalid.raw_metadata ->> 'category', 'invalid')
          end as validity_status,
          invalid.reason as invalid_reason,
          coalesce(art.artifact_count, 0)::int as artifact_count,
          coalesce(art.artifact_types_present, '') as artifact_types_present,
          coalesce(art.has_result, false) as has_result,
          coalesce(art.has_exception, false) as has_exception,
          coalesce(art.has_agent_transcript, false) as has_agent_transcript,
          coalesce(art.has_trajectory, false) as has_trajectory,
          coalesce(art.has_trial_log, false) as has_trial_log,
          coalesce(art.has_verifier_stdout, false) as has_verifier_stdout,
          coalesce(art.has_verifier_ctrf, false) as has_verifier_ctrf,
          coalesce(art.has_verifier_reward, false) as has_verifier_reward,
          case
            when art.first_artifact_id is null then ''
            else '/artifacts/' || art.first_artifact_id
          end as first_artifact_dashboard_path,
          '/trials/' || q.trial_id::text as trial_dashboard_path
        from benchmark.v_trial_quality_flags q
        join benchmark.benchmark_trials t
          on t.id = q.trial_id
        left join benchmark.benchmark_invalid_arm_runs invalid
          on invalid.suite_id = q.suite_id
         and invalid.arm_id = q.arm_id
         and invalid.run_label = q.run_label
        left join lateral (
          select
            count(a.id)::int as artifact_count,
            string_agg(distinct a.artifact_type, ',' order by a.artifact_type) as artifact_types_present,
            bool_or(a.artifact_type = 'result') as has_result,
            bool_or(a.artifact_type = 'exception') as has_exception,
            bool_or(a.artifact_type = 'agent_transcript') as has_agent_transcript,
            bool_or(a.artifact_type = 'trajectory') as has_trajectory,
            bool_or(a.artifact_type = 'log') as has_trial_log,
            bool_or(a.artifact_type = 'verifier_stdout') as has_verifier_stdout,
            bool_or(a.artifact_type = 'verifier_ctrf') as has_verifier_ctrf,
            bool_or(a.artifact_type = 'verifier_reward') as has_verifier_reward,
            (array_agg(a.id::text order by a.created_at nulls last, a.artifact_type, a.id::text))[1] as first_artifact_id
          from benchmark.benchmark_artifacts a
          where a.trial_id = q.trial_id
        ) art on true
        where q.suite_id = %s
          {focus_clause}
          {valid_clause}
        order by q.arm_id, q.run_label, q.task_id, q.attempt_index, q.trial_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())


def fetch_invalid_runs(conn: Any, *, suite_id: str, focus_arms: Sequence[str]) -> list[dict[str, Any]]:
    params: list[Any] = [suite_id]
    focus_clause = ""
    if focus_arms:
        params.append(list(focus_arms))
        focus_clause = "and arm_id = any(%s)"
    sql = f"""
        select
          suite_id,
          arm_id,
          run_label,
          provider_run_id,
          coalesce(raw_metadata ->> 'category', 'invalid') as validity_status,
          reason
        from benchmark.benchmark_invalid_arm_runs
        where suite_id = %s
          {focus_clause}
        order by arm_id, run_label
    """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())


def fetch_exception_review_targets(
    conn: Any,
    *,
    suite_id: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
) -> list[dict[str, Any]]:
    params: list[Any] = [suite_id]
    focus_clause = ""
    if focus_arms:
        params.append(list(focus_arms))
        focus_clause = "and q.arm_id = any(%s)"

    valid_clause = "" if include_invalid else "and invalid.id is null"

    sql = f"""
        select
          q.suite_id,
          q.arm_id,
          q.run_label,
          q.task_id,
          q.attempt_index::int as attempt_index,
          q.trial_id::text as trial_id,
          art.id::text as exception_artifact_id,
          '/trials/' || q.trial_id::text as trial_dashboard_path,
          '/artifacts/' || art.id::text as exception_artifact_dashboard_path,
          q.exception_type,
          (q.cost_usd is null) as missing_cost,
          case
            when invalid.id is null then 'valid'
            else coalesce(invalid.raw_metadata ->> 'category', 'invalid')
          end as validity_status,
          invalid.reason as invalid_reason,
          q.reward,
          q.runtime_seconds,
          art.r2_uri,
          art.size_bytes::int
        from benchmark.v_trial_quality_flags q
        join lateral (
          select a.*
          from benchmark.benchmark_artifacts a
          where a.trial_id = q.trial_id
            and a.artifact_type = 'exception'
          order by a.created_at nulls last, a.id
          limit 1
        ) art on true
        left join benchmark.benchmark_invalid_arm_runs invalid
          on invalid.suite_id = q.suite_id
         and invalid.arm_id = q.arm_id
         and invalid.run_label = q.run_label
        where q.suite_id = %s
          {focus_clause}
          {valid_clause}
          and q.quality_flag in ('exception', 'exception_with_success')
        order by q.arm_id, q.run_label, q.task_id, q.attempt_index, q.trial_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())


def top_exception_types(rows: Sequence[dict[str, Any]], limit: int = 8) -> list[tuple[str, int]]:
    counts = Counter(
        str(row.get("exception_type") or "unspecified")
        for row in rows
        if is_exception(row)
    )
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]


def top_task_signals(task_summary: Sequence[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        anomaly = (
            int(row.get("exception_count") or 0)
            + int(row.get("suspect_noop_count") or 0)
            + int(row.get("normal_failure_count") or 0)
        )
        return (
            -anomaly,
            -int(row.get("exception_count") or 0),
            -int(row.get("suspect_noop_count") or 0),
            str(row.get("task_id") or ""),
        )

    return sorted(task_summary, key=key)[:limit]


def dashboard_path(path: str) -> str:
    return path


def display_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def build_generation_command(
    *,
    suite_id: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
    include_successes: bool,
) -> str:
    parts = [
        "uv",
        "run",
        "--with",
        "'psycopg[binary]'",
        "python",
        "scripts/generate_phase3_qualitative_audit.py",
        "--suite-id",
        suite_id,
    ]
    for arm in focus_arms:
        parts.extend(["--focus-arm", arm])
    if include_invalid:
        parts.append("--include-invalid")
    if include_successes:
        parts.append("--include-successes")
    return " ".join(parts)


def build_markdown(
    *,
    path: Path,
    suite_id: str,
    datestamp: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
    rows: Sequence[dict[str, Any]],
    evidence_rows: Sequence[dict[str, Any]],
    invalid_runs: Sequence[dict[str, Any]],
    task_summary: Sequence[dict[str, Any]],
    generated_files: GeneratedFiles,
    include_successes: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = count_rows(rows)
    evidence_summary = count_rows(evidence_rows)
    artifact_count = sum(int(row.get("artifact_count") or 0) for row in rows)
    rows_with_artifacts = sum(1 for row in rows if int(row.get("artifact_count") or 0) > 0)
    sonnet_rows = [row for row in rows if row.get("run_label") == SONNET_RUN_LABEL]
    sonnet_summary = count_rows(sonnet_rows)
    sonnet_label = quote(SONNET_RUN_LABEL, safe="")

    source_lines = "\n".join(f"- `{display_path(generated)}`" for generated in generated_files.as_list())
    exception_lines = "\n".join(
        f"- `{name}`: {count}"
        for name, count in top_exception_types(rows)
    ) or "- No exception types were present in the selected rows."
    task_lines = "\n".join(
        "- `{task_id}`: trials={trial_count}, successes={success_count}, "
        "exceptions={exception_count}, suspect_noops={suspect_noop_count}, "
        "normal_failures={normal_failure_count}, priority={review_priority}".format(**row)
        for row in top_task_signals(task_summary)
    ) or "- No task rows were generated."
    invalid_lines = "\n".join(
        f"- `{row.get('arm_id')}` / `{row.get('run_label')}`: {row.get('reason')}"
        for row in invalid_runs
    ) or "- No invalid/quarantined runs matched this suite and focus-arm selection."

    focus_text = ", ".join(f"`{arm}`" for arm in focus_arms) if focus_arms else "all arms"
    invalid_scope = "included and labeled" if include_invalid else "excluded from generated trial rows"
    generation_command = build_generation_command(
        suite_id=suite_id,
        focus_arms=focus_arms,
        include_invalid=include_invalid,
        include_successes=include_successes,
    )

    body = f"""# Phase 3 Artifact Qualitative Review {datestamp}

## Purpose

Prepare a reproducible evidence inventory for the Phase 3 qualitative investigation pass. This scaffold is focused on Sonnet exceptions and suspect no-op zero-token trials first, while preserving dashboard links into the artifact browser and trial evidence pages.

Do not run Haiku or Fable from this scaffold. Those runs remain gated on drilldown readiness and ingestion automation.

## Source Files Generated

{source_lines}

## Review Method

- Suite: `{suite_id}`.
- Focus arms: {focus_text}.
- Invalid/quarantined runs: {invalid_scope}.
- Generation command:

```bash
{generation_command}
```

- Start with exception and suspect no-op rows, then compare against normal failures and representative successes only when needed.
- Use `/artifacts/<artifact_id>` for R2-backed content preview and `/trials/<trial_id>` for trial evidence context.
- Record whether each anomaly appears to be model behavior, provider behavior, harness behavior, or ingestion/reporting behavior.

## Initial Aggregate Observations

- Selected trial rows: {summary['trial_count']}.
- Evidence-audit rows emitted: {evidence_summary['trial_count']}.
- Successes in selected rows: {summary['success_count']}.
- Exceptions in selected rows: {summary['exception_count']}.
- Suspect no-op rows in selected rows: {summary['suspect_noop_count']}.
- Normal failures in selected rows: {summary['normal_failure_count']}.
- Missing-cost rows in selected rows: {summary['missing_cost_count']}.
- Artifact references indexed: {artifact_count} artifacts across {rows_with_artifacts} selected trials.

## Sonnet Exception Review

### `{SONNET_RUN_LABEL}`

Planned first focus counts:

- Trials: {SONNET_EXPECTED_COUNTS['trials']}.
- Successes: {SONNET_EXPECTED_COUNTS['successes']}.
- Exception failures: {SONNET_EXPECTED_COUNTS['exception_failures']}.
- Normal failures: {SONNET_EXPECTED_COUNTS['normal_failures']}.
- Missing-cost trials: {SONNET_EXPECTED_COUNTS['missing_cost_trials']}.

Generated row check for this run in the current inventory:

- Rows: {sonnet_summary['trial_count']}.
- Successes: {sonnet_summary['success_count']}.
- Exceptions: {sonnet_summary['exception_count']}.
- Normal failures: {sonnet_summary['normal_failure_count']}.
- Missing-cost rows: {sonnet_summary['missing_cost_count']}.

Use `phase3_exception_review_targets_{datestamp}.tsv` for direct exception.txt artifact links.

Dashboard starting links:

- [Sonnet exception artifacts]({dashboard_path(f"/artifacts?run_label={sonnet_label}&quality_flag=exception")}).
- [Sonnet run detail]({dashboard_path(f"/runs/{sonnet_label}")}).
- [Sonnet trial quality]({dashboard_path(f"/trial-quality?run_label={sonnet_label}")}).

Review notes:

- Pending: classify representative exception artifacts by root cause.
- Pending: compare exception summaries against R2 preview contents.
- Pending: check whether missing-cost rows line up with exception boundaries or ingestion gaps.

## Suspect No-op Review

- Start from `phase3_suspect_noop_audit_{datestamp}.tsv`.
- For each row, open `trial_dashboard_path`, then `first_artifact_dashboard_path` when present.
- Confirm whether zero tokens/cost reflects provider non-start, harness no-op, ingestion omission, or legitimate empty accounting.

## Gemini Flash Review

- Pending after the Sonnet exception pass.
- Use the exception and suspect no-op inventories to select representative Gemini Flash rows.
- Keep invalid/quarantined evidence labeled if `--include-invalid` is used for a follow-up pass.

## Invalid/Quarantined Run Review

{invalid_lines}

## Cross-arm Exception Patterns

{exception_lines}

## Task-level Observations

{task_lines}

## Open Questions and Recommended Actions

- Confirm whether task text is available for each reviewed trial; if not, keep task text ingestion on the qualitative-review readiness checklist.
- Decide whether any invalid/quarantined labels or reasons need refinement before final Phase 3 reporting.
- Capture representative artifact links for each root-cause category before resuming paid full runs.
- Do not run Haiku or Fable until drilldown review and ingestion automation are ready.
"""
    path.write_text(body, encoding="utf-8")


def generated_paths(output_dir: Path, docs_dir: Path, datestamp: str) -> GeneratedFiles:
    return GeneratedFiles(
        trial_evidence=output_dir / f"phase3_trial_evidence_audit_{datestamp}.tsv",
        exception_audit=output_dir / f"phase3_exception_audit_{datestamp}.tsv",
        suspect_noop_audit=output_dir / f"phase3_suspect_noop_audit_{datestamp}.tsv",
        arm_task_matrix=output_dir / f"phase3_arm_task_qualitative_matrix_{datestamp}.tsv",
        arm_summary=output_dir / f"phase3_arm_qualitative_summary_{datestamp}.tsv",
        task_summary=output_dir / f"phase3_task_qualitative_summary_{datestamp}.tsv",
        exception_review_targets=output_dir / f"phase3_exception_review_targets_{datestamp}.tsv",
        markdown_review=docs_dir / f"PHASE3_ARTIFACT_QUALITATIVE_REVIEW_{datestamp}.md",
    )


def generate_outputs(
    *,
    suite_id: str,
    datestamp: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
    include_successes: bool,
    output_dir: Path,
    docs_dir: Path,
) -> GeneratedFiles:
    files = generated_paths(output_dir, docs_dir, datestamp)
    with connect() as conn:
        rows = fetch_trial_rows(
            conn,
            suite_id=suite_id,
            focus_arms=focus_arms,
            include_invalid=include_invalid,
        )
        invalid_runs = fetch_invalid_runs(conn, suite_id=suite_id, focus_arms=focus_arms)
        exception_review_targets = fetch_exception_review_targets(
            conn,
            suite_id=suite_id,
            focus_arms=focus_arms,
            include_invalid=include_invalid,
        )

    evidence_rows = filter_evidence_rows(rows, include_successes=include_successes)
    exception_rows = [row for row in rows if is_exception(row)]
    suspect_rows = [row for row in rows if is_suspect_noop(row)]
    arm_task_matrix = build_arm_task_matrix(rows)
    arm_summary = build_arm_summary(rows)
    task_summary = build_task_summary(rows)

    write_tsv(files.trial_evidence, evidence_rows, TRIAL_EVIDENCE_HEADERS)
    write_tsv(files.exception_audit, exception_rows, TRIAL_EVIDENCE_HEADERS)
    write_tsv(files.suspect_noop_audit, suspect_rows, TRIAL_EVIDENCE_HEADERS)
    write_tsv(files.arm_task_matrix, arm_task_matrix, ARM_TASK_HEADERS)
    write_tsv(files.arm_summary, arm_summary, ARM_SUMMARY_HEADERS)
    write_tsv(files.task_summary, task_summary, TASK_SUMMARY_HEADERS)
    write_tsv(files.exception_review_targets, exception_review_targets, EXCEPTION_REVIEW_TARGET_HEADERS)
    build_markdown(
        path=files.markdown_review,
        suite_id=suite_id,
        datestamp=datestamp,
        focus_arms=focus_arms,
        include_invalid=include_invalid,
        rows=rows,
        evidence_rows=evidence_rows,
        invalid_runs=invalid_runs,
        task_summary=task_summary,
        generated_files=files,
        include_successes=include_successes,
    )
    return files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-id", default=DEFAULT_SUITE_ID)
    parser.add_argument("--date", default=utc_datestamp(), help="UTC datestamp in YYYYMMDD format.")
    parser.add_argument("--focus-arm", action="append", default=[], help="Arm to include. Repeatable.")
    parser.add_argument("--include-invalid", action="store_true", help="Include invalid/quarantined rows and label them.")
    parser.add_argument(
        "--include-successes",
        action="store_true",
        help="Include success rows in the trial evidence audit TSV; summaries always include selected successes.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    files = generate_outputs(
        suite_id=args.suite_id,
        datestamp=args.date,
        focus_arms=args.focus_arm,
        include_invalid=args.include_invalid,
        include_successes=args.include_successes,
        output_dir=args.output_dir,
        docs_dir=args.docs_dir,
    )
    for path in files.as_list():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
