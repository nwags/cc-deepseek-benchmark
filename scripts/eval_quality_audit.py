#!/usr/bin/env python3
"""Summarize and audit eval-suite quality rows from Supabase/Postgres."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "benchmark"
EXCEPTION_FLAGS = ("exception", "exception_with_success", "suspect_noop_zero_token")


@dataclass(frozen=True)
class SchemaInfo:
    columns: dict[str, set[str]]

    def has_relation(self, relation: str) -> bool:
        return relation in self.columns

    def has_column(self, relation: str, column: str) -> bool:
        return column in self.columns.get(relation, set())

    def relation_columns(self, relation: str) -> set[str]:
        return self.columns.get(relation, set())


@dataclass(frozen=True)
class InvalidRun:
    suite_id: str
    arm_id: str
    run_label: str | None
    provider_run_id: str | None
    reason: str


def parse_words(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in value.replace("\n", " ").split(" ") if part.strip()]


def require_suite_id(args: argparse.Namespace) -> str:
    if not args.suite_id:
        raise SystemExit("SUITE_ID is required; pass --suite-id or set SUITE_ID in the environment.")
    return args.suite_id


def load_invalid_runs_file(path: Path, suite_id: str) -> list[InvalidRun]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return []

    reader = csv.DictReader(lines, delimiter="\t")
    fieldnames = set(reader.fieldnames or [])
    required = {"suite_id", "arm_id", "reason"}
    missing = sorted(required - fieldnames)
    if missing:
        raise SystemExit(f"{path}: missing required column(s): {', '.join(missing)}")
    if "run_label" not in fieldnames and "provider_run_id" not in fieldnames and "github_run_id" not in fieldnames:
        raise SystemExit(f"{path}: expected run_label or provider_run_id/github_run_id column")

    invalid_runs: list[InvalidRun] = []
    for lineno, row in enumerate(reader, start=2):
        row_suite_id = (row.get("suite_id") or "").strip()
        if row_suite_id != suite_id:
            continue

        arm_id = (row.get("arm_id") or "").strip()
        run_label = (row.get("run_label") or "").strip() or None
        provider_run_id = (
            (row.get("provider_run_id") or "").strip()
            or (row.get("github_run_id") or "").strip()
            or None
        )
        reason = (row.get("reason") or "").strip()
        if not arm_id:
            raise SystemExit(f"{path}:{lineno}: arm_id is required")
        if not run_label and not provider_run_id:
            raise SystemExit(f"{path}:{lineno}: run_label or provider_run_id/github_run_id is required")
        if not reason:
            raise SystemExit(f"{path}:{lineno}: reason is required")
        invalid_runs.append(
            InvalidRun(
                suite_id=row_suite_id,
                arm_id=arm_id,
                run_label=run_label,
                provider_run_id=provider_run_id,
                reason=reason,
            )
        )
    return invalid_runs


def load_invalid_runs_from_args(args: argparse.Namespace) -> list[InvalidRun]:
    path_text = getattr(args, "invalid_runs_file", None)
    if not path_text:
        if getattr(args, "valid_only", False):
            raise SystemExit("--invalid-runs-file is required for valid-only summaries")
        return []

    path = Path(path_text)
    if not path.exists():
        if getattr(args, "missing_invalid_runs_ok", False):
            print(f"invalid_runs_file_missing\t{path}", file=sys.stderr)
            return []
        raise SystemExit(f"Invalid-runs file not found: {path}")

    invalid_runs = load_invalid_runs_file(path, require_suite_id(args))
    print(f"invalid_run_exclusions_loaded\t{len(invalid_runs)}\t{path}", file=sys.stderr)
    return invalid_runs


def require_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(
            "psycopg[binary] is required. Run with: "
            "uv run --with 'psycopg[binary]' python scripts/eval_quality_audit.py ..."
        ) from exc
    return psycopg, dict_row


def connect(db_url: str | None) -> Any:
    db_url = db_url or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL is required; source .secrets/supabase.env or pass --db-url")
    psycopg, dict_row = require_psycopg()
    return psycopg.connect(db_url, row_factory=dict_row)


def load_schema_info(conn: Any) -> SchemaInfo:
    with conn.cursor() as cur:
        cur.execute(
            """
            select table_name, column_name
            from information_schema.columns
            where table_schema = %s
            order by table_name, ordinal_position
            """,
            (SCHEMA,),
        )
        columns: dict[str, set[str]] = {}
        for row in cur.fetchall():
            columns.setdefault(row["table_name"], set()).add(row["column_name"])
    return SchemaInfo(columns=columns)


def ensure_relations(schema: SchemaInfo, *relations: str) -> None:
    missing = [relation for relation in relations if not schema.has_relation(relation)]
    if missing:
        raise SystemExit(f"Missing required benchmark relation(s): {', '.join(missing)}")


def select_expr(columns: set[str], column: str, relation_alias: str, sql_type: str = "text") -> str:
    if column in columns:
        return f"{relation_alias}.{column} as {column}"
    return f"null::{sql_type} as {column}"


def view_select_expr(columns: set[str], column: str, sql_type: str = "text") -> str:
    if column in columns:
        return column
    return f"null::{sql_type} as {column}"


def any_filter(column_sql: str, values: list[str], params: list[Any]) -> str:
    if not values:
        return ""
    params.append(values)
    return f" and {column_sql} = any(%s)"


def append_json_text_match(
    matchers: list[str],
    matcher_params: list[Any],
    *,
    schema: SchemaInfo,
    relation: str,
    alias: str,
    key: str,
    value: str,
) -> None:
    if schema.has_column(relation, "raw_metadata"):
        matchers.append(f"({alias}.raw_metadata ->> %s) = %s")
        matcher_params.extend([key, value])


def invalid_run_filter(schema: SchemaInfo, args: argparse.Namespace, params: list[Any]) -> str:
    invalid_runs: list[InvalidRun] = getattr(args, "_invalid_runs", [])
    if not invalid_runs:
        return ""

    clauses: list[str] = []
    unsupported: list[str] = []
    run_cols = schema.relation_columns("benchmark_runs")
    arm_run_cols = schema.relation_columns("benchmark_arm_runs")

    for invalid in invalid_runs:
        matchers: list[str] = []
        matcher_params: list[Any] = []
        if invalid.run_label:
            if "run_label" in run_cols:
                matchers.append("r.run_label = %s")
                matcher_params.append(invalid.run_label)

        if invalid.provider_run_id:
            if "provider_run_id" in arm_run_cols:
                matchers.append("ar.provider_run_id = %s")
                matcher_params.append(invalid.provider_run_id)
            if "github_run_id" in arm_run_cols:
                matchers.append("ar.github_run_id = %s")
                matcher_params.append(invalid.provider_run_id)
            if "provider_run_id" in run_cols:
                matchers.append("r.provider_run_id = %s")
                matcher_params.append(invalid.provider_run_id)
            if "github_run_id" in run_cols:
                matchers.append("r.github_run_id = %s")
                matcher_params.append(invalid.provider_run_id)
            append_json_text_match(
                matchers,
                matcher_params,
                schema=schema,
                relation="benchmark_arm_runs",
                alias="ar",
                key="provider_run_id",
                value=invalid.provider_run_id,
            )
            append_json_text_match(
                matchers,
                matcher_params,
                schema=schema,
                relation="benchmark_arm_runs",
                alias="ar",
                key="github_run_id",
                value=invalid.provider_run_id,
            )
            append_json_text_match(
                matchers,
                matcher_params,
                schema=schema,
                relation="benchmark_runs",
                alias="r",
                key="provider_run_id",
                value=invalid.provider_run_id,
            )
            append_json_text_match(
                matchers,
                matcher_params,
                schema=schema,
                relation="benchmark_runs",
                alias="r",
                key="github_run_id",
                value=invalid.provider_run_id,
            )

        if not matchers:
            unsupported.append(f"{invalid.suite_id}\t{invalid.arm_id}\tno supported exclusion key")
            continue

        clauses.append(f"(ar.suite_id = %s and ar.arm_id = %s and ({' or '.join(matchers)}))")
        params.extend([invalid.suite_id, invalid.arm_id, *matcher_params])

    if unsupported:
        raise SystemExit("invalid-run exclusions could not be applied:\n" + "\n".join(unsupported))
    return " and not (" + " or ".join(clauses) + ")"


def rows_for_query(conn: Any, sql: str, params: Iterable[Any]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())


def suite_summary_from_view(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    view = "v_suite_arm_quality_summary"
    cols = schema.relation_columns(view)
    params: list[Any] = [args.suite_id]
    selected = [
        view_select_expr(cols, "phase"),
        view_select_expr(cols, "logical_mode"),
        view_select_expr(cols, "storage_mode"),
        view_select_expr(cols, "suite_id"),
        view_select_expr(cols, "arm_id"),
        view_select_expr(cols, "arm_run_count", "integer"),
        view_select_expr(cols, "trial_count", "integer"),
        view_select_expr(cols, "success_count", "integer"),
        view_select_expr(cols, "raw_pass_rate", "numeric"),
        view_select_expr(cols, "suspect_noop_count", "integer"),
        view_select_expr(cols, "exception_count", "integer"),
        view_select_expr(cols, "normal_failed_count", "integer"),
        view_select_expr(cols, "qualified_trial_count", "integer"),
        view_select_expr(cols, "qualified_success_count", "integer"),
        view_select_expr(cols, "qualified_pass_rate", "numeric"),
        view_select_expr(cols, "recorded_cost_usd", "numeric"),
        view_select_expr(cols, "missing_cost_count", "integer"),
    ]
    sql = f"""
        select {", ".join(selected)}
        from {SCHEMA}.{view}
        where suite_id = %s
        {any_filter("arm_id", parse_words(args.arms), params)}
        order by arm_id
    """
    return rows_for_query(conn, sql, params)


def trial_join(schema: SchemaInfo) -> str:
    trial_cols = schema.relation_columns("benchmark_trials")
    if "arm_run_id" in trial_cols:
        return "join benchmark.benchmark_arm_runs ar on ar.id = t.arm_run_id"
    if "arm_id" in trial_cols:
        return "join benchmark.benchmark_arm_runs ar on ar.run_id = t.run_id and ar.arm_id = t.arm_id"
    return "join benchmark.benchmark_arm_runs ar on ar.run_id = t.run_id"


def success_expr(trial_cols: set[str]) -> str:
    if "reward" in trial_cols:
        return "coalesce(t.reward, 0) > 0"
    return "false"


def exception_expr(trial_cols: set[str]) -> str:
    if "exception_type" in trial_cols:
        return "t.exception_type is not null"
    return "false"


def suspect_expr(trial_cols: set[str]) -> str:
    required = {"input_tokens", "output_tokens", "cost_usd"}
    if not required.issubset(trial_cols):
        return "false"
    parts = [
        "coalesce(t.input_tokens, 0) = 0",
        "coalesce(t.output_tokens, 0) = 0",
        "coalesce(t.cost_usd, 0) = 0",
    ]
    if "exception_type" in trial_cols:
        parts.append("t.exception_type is null")
    if "reward" in trial_cols:
        parts.append("coalesce(t.reward, 0) = 0")
    return "(" + " and ".join(parts) + ")"


def suite_summary_from_base(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    ensure_relations(schema, "benchmark_runs", "benchmark_trials", "benchmark_arm_runs")
    ar_cols = schema.relation_columns("benchmark_arm_runs")
    t_cols = schema.relation_columns("benchmark_trials")
    for col in ("suite_id", "arm_id"):
        if col not in ar_cols:
            raise SystemExit(f"benchmark_arm_runs.{col} is required for suite summary")

    params: list[Any] = [args.suite_id]
    is_success = success_expr(t_cols)
    is_exception = exception_expr(t_cols)
    is_suspect = suspect_expr(t_cols)
    cost_sum = "coalesce(sum(t.cost_usd), 0)" if "cost_usd" in t_cols else "null::numeric"
    missing_cost = "count(*) filter (where t.cost_usd is null)" if "cost_usd" in t_cols else "null::integer"
    task_count = "count(distinct t.task_id)::int" if "task_id" in t_cols else "null::integer"
    logical_mode = "ar.logical_mode" if "logical_mode" in ar_cols else "null::text"
    storage_mode = "ar.storage_mode" if "storage_mode" in ar_cols else "null::text"
    arm_filter = any_filter("ar.arm_id", parse_words(args.arms), params)
    invalid_filter = invalid_run_filter(schema, args, params)

    sql = f"""
        select
          r.phase,
          {logical_mode} as logical_mode,
          {storage_mode} as storage_mode,
          ar.suite_id,
          ar.arm_id,
          count(distinct ar.id)::int as arm_run_count,
          {task_count} as task_count,
          count(t.id)::int as trial_count,
          count(t.id) filter (where {is_success})::int as success_count,
          round((count(t.id) filter (where {is_success}))::numeric / nullif(count(t.id), 0), 4) as raw_pass_rate,
          count(t.id) filter (where {is_suspect})::int as suspect_noop_count,
          count(t.id) filter (where {is_exception})::int as exception_count,
          count(t.id) filter (where not ({is_success}) and not ({is_exception}) and not ({is_suspect}))::int as normal_failed_count,
          count(t.id) filter (where not ({is_suspect}))::int as qualified_trial_count,
          count(t.id) filter (where not ({is_suspect}) and ({is_success}))::int as qualified_success_count,
          round(
            (count(t.id) filter (where not ({is_suspect}) and ({is_success})))::numeric
            / nullif(count(t.id) filter (where not ({is_suspect})), 0),
            4
          ) as qualified_pass_rate,
          {cost_sum} as recorded_cost_usd,
          {missing_cost}::int as missing_cost_count
        from benchmark.benchmark_trials t
        join benchmark.benchmark_runs r on r.id = t.run_id
        {trial_join(schema)}
        where ar.suite_id = %s
        {arm_filter}
        {invalid_filter}
        group by r.phase, logical_mode, storage_mode, ar.suite_id, ar.arm_id
        order by ar.arm_id
    """
    return rows_for_query(conn, sql, params)


def command_suite_summary(args: argparse.Namespace) -> int:
    require_suite_id(args)
    args._invalid_runs = load_invalid_runs_from_args(args)
    with connect(args.db_url) as conn:
        schema = load_schema_info(conn)
        if schema.has_relation("v_suite_arm_quality_summary") and not args._invalid_runs:
            rows = suite_summary_from_view(conn, schema, args)
        else:
            rows = suite_summary_from_base(conn, schema, args)
    print_rows(rows)
    return 0


def arm_run_summary_from_view(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    view = "v_arm_run_quality_summary"
    cols = schema.relation_columns(view)
    params: list[Any] = [args.suite_id]
    selected = [
        view_select_expr(cols, "run_id"),
        view_select_expr(cols, "arm_run_id"),
        view_select_expr(cols, "phase"),
        view_select_expr(cols, "logical_mode"),
        view_select_expr(cols, "storage_mode"),
        view_select_expr(cols, "suite_id"),
        view_select_expr(cols, "arm_id"),
        view_select_expr(cols, "run_label"),
        view_select_expr(cols, "trial_count", "integer"),
        view_select_expr(cols, "success_count", "integer"),
        view_select_expr(cols, "raw_pass_rate", "numeric"),
        view_select_expr(cols, "suspect_noop_count", "integer"),
        view_select_expr(cols, "exception_count", "integer"),
        view_select_expr(cols, "normal_failed_count", "integer"),
        view_select_expr(cols, "qualified_trial_count", "integer"),
        view_select_expr(cols, "qualified_success_count", "integer"),
        view_select_expr(cols, "qualified_pass_rate", "numeric"),
        view_select_expr(cols, "recorded_cost_usd", "numeric"),
        view_select_expr(cols, "missing_cost_count", "integer"),
    ]
    sql = f"""
        select {", ".join(selected)}
        from {SCHEMA}.{view}
        where suite_id = %s
        {any_filter("arm_id", parse_words(args.arms), params)}
        order by arm_id, run_label
    """
    return rows_for_query(conn, sql, params)


def arm_run_summary_from_base(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    ensure_relations(schema, "benchmark_runs", "benchmark_trials", "benchmark_arm_runs")
    ar_cols = schema.relation_columns("benchmark_arm_runs")
    t_cols = schema.relation_columns("benchmark_trials")
    if "suite_id" not in ar_cols or "arm_id" not in ar_cols:
        raise SystemExit("benchmark_arm_runs.suite_id and benchmark_arm_runs.arm_id are required")

    params: list[Any] = [args.suite_id]
    is_success = success_expr(t_cols)
    is_exception = exception_expr(t_cols)
    is_suspect = suspect_expr(t_cols)
    cost_sum = "coalesce(sum(t.cost_usd), 0)" if "cost_usd" in t_cols else "null::numeric"
    missing_cost = "count(*) filter (where t.cost_usd is null)" if "cost_usd" in t_cols else "null::integer"
    artifact_join = ""
    artifact_select = "null::integer as artifact_count, null::integer as r2_artifact_count"
    if schema.has_relation("benchmark_artifacts"):
        artifact_join = """
        left join (
          select run_id,
                 count(*)::int as artifact_count,
                 count(*) filter (where r2_uri is not null)::int as r2_artifact_count
          from benchmark.benchmark_artifacts
          group by run_id
        ) art on art.run_id = r.id
        """
        artifact_select = "coalesce(max(art.artifact_count), 0)::int as artifact_count, coalesce(max(art.r2_artifact_count), 0)::int as r2_artifact_count"
    if "arm_run_id" in t_cols:
        trial_on = "t.arm_run_id = ar.id"
    elif "arm_id" in t_cols:
        trial_on = "t.arm_id = ar.arm_id"
    else:
        trial_on = "true"
    arm_filter = any_filter("ar.arm_id", parse_words(args.arms), params)
    invalid_filter = invalid_run_filter(schema, args, params)

    sql = f"""
        select
          r.id as run_id,
          ar.id as arm_run_id,
          r.phase,
          {"ar.logical_mode" if "logical_mode" in ar_cols else "null::text"} as logical_mode,
          {"ar.storage_mode" if "storage_mode" in ar_cols else "null::text"} as storage_mode,
          ar.suite_id,
          ar.arm_id,
          r.run_label,
          {"ar.status" if "status" in ar_cols else "r.status"} as status,
          count(t.id)::int as trial_count,
          count(t.id) filter (where {is_success})::int as success_count,
          round((count(t.id) filter (where {is_success}))::numeric / nullif(count(t.id), 0), 4) as raw_pass_rate,
          count(t.id) filter (where {is_suspect})::int as suspect_noop_count,
          count(t.id) filter (where {is_exception})::int as exception_count,
          count(t.id) filter (where not ({is_success}) and not ({is_exception}) and not ({is_suspect}))::int as normal_failed_count,
          count(t.id) filter (where not ({is_suspect}))::int as qualified_trial_count,
          count(t.id) filter (where not ({is_suspect}) and ({is_success}))::int as qualified_success_count,
          round(
            (count(t.id) filter (where not ({is_suspect}) and ({is_success})))::numeric
            / nullif(count(t.id) filter (where not ({is_suspect})), 0),
            4
          ) as qualified_pass_rate,
          {cost_sum} as recorded_cost_usd,
          {missing_cost}::int as missing_cost_count,
          {artifact_select}
        from benchmark.benchmark_runs r
        join benchmark.benchmark_arm_runs ar on ar.run_id = r.id
        left join benchmark.benchmark_trials t on t.run_id = r.id
          and ({trial_on})
        {artifact_join}
        where ar.suite_id = %s
        {arm_filter}
        {invalid_filter}
        group by r.id, ar.id
        order by ar.arm_id, r.run_label
    """
    return rows_for_query(conn, sql, params)


def command_arm_run_summary(args: argparse.Namespace) -> int:
    require_suite_id(args)
    args._invalid_runs = load_invalid_runs_from_args(args)
    with connect(args.db_url) as conn:
        schema = load_schema_info(conn)
        if schema.has_relation("v_arm_run_quality_summary") and not args._invalid_runs:
            rows = arm_run_summary_from_view(conn, schema, args)
        else:
            rows = arm_run_summary_from_base(conn, schema, args)
    print_rows(rows)
    return 0


def exception_audit_query_from_view(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    view = "v_trial_quality_flags"
    q_cols = schema.relation_columns(view)
    t_cols = schema.relation_columns("benchmark_trials")
    params: list[Any] = [args.suite_id]
    if "exception_summary" in q_cols and "exception_summary" in t_cols:
        exception_summary_select = "coalesce(q.exception_summary, t.exception_summary) as exception_summary"
    elif "exception_summary" in q_cols:
        exception_summary_select = "q.exception_summary as exception_summary"
    elif "exception_summary" in t_cols:
        exception_summary_select = "t.exception_summary as exception_summary"
    else:
        exception_summary_select = "null::text as exception_summary"

    filters: list[str] = []
    if "quality_flag" in q_cols:
        filters.append("q.quality_flag = any(%s)")
    if "exception_type" in q_cols:
        filters.append("q.exception_type is not null")
    if not filters:
        raise SystemExit("v_trial_quality_flags lacks quality_flag and exception_type; cannot audit exceptions")

    order_cols = [
        column
        for column in ("arm_id", "run_label", "task_id", "attempt_index")
        if column in q_cols
    ]
    order_by = ", ".join(f"q.{column}" for column in order_cols) or "q.trial_id"

    selected = [
        "q.trial_id",
        "q.run_id",
        select_expr(q_cols, "arm_run_id", "q"),
        select_expr(q_cols, "phase", "q"),
        select_expr(q_cols, "logical_mode", "q"),
        select_expr(q_cols, "storage_mode", "q"),
        select_expr(q_cols, "suite_id", "q"),
        select_expr(q_cols, "arm_id", "q"),
        select_expr(q_cols, "run_label", "q"),
        select_expr(q_cols, "task_id", "q"),
        select_expr(q_cols, "attempt_index", "q", "integer"),
        select_expr(q_cols, "reward", "q", "numeric"),
        select_expr(q_cols, "quality_flag", "q"),
        select_expr(q_cols, "exception_type", "q"),
        exception_summary_select,
        select_expr(q_cols, "input_tokens", "q", "bigint"),
        select_expr(q_cols, "output_tokens", "q", "bigint"),
        select_expr(q_cols, "cost_usd", "q", "numeric"),
        select_expr(q_cols, "runtime_seconds", "q", "numeric"),
        select_expr(t_cols, "result_local_path", "t"),
    ]
    sql = f"""
        select {", ".join(selected)}
        from benchmark.v_trial_quality_flags q
        join benchmark.benchmark_trials t on t.id = q.trial_id
        where q.suite_id = %s
        {any_filter("q.arm_id", parse_words(args.arms), params)}
          and ({" or ".join(filters)})
        order by {order_by}
    """
    if "quality_flag" in q_cols:
        params.append(list(EXCEPTION_FLAGS))
    return rows_for_query(conn, sql, params)


def exception_audit_query_from_base(conn: Any, schema: SchemaInfo, args: argparse.Namespace) -> list[dict[str, Any]]:
    ensure_relations(schema, "benchmark_runs", "benchmark_trials", "benchmark_arm_runs")
    ar_cols = schema.relation_columns("benchmark_arm_runs")
    t_cols = schema.relation_columns("benchmark_trials")
    params: list[Any] = [args.suite_id]
    is_exception = exception_expr(t_cols)
    is_suspect = suspect_expr(t_cols)
    quality_flag = (
        f"case when {is_exception} then 'exception' "
        f"when {is_suspect} then 'suspect_noop_zero_token' "
        "else 'trial_attention' end"
    )
    selected = [
        "t.id as trial_id",
        "t.run_id",
        "ar.id as arm_run_id",
        "r.phase",
        "ar.logical_mode" if "logical_mode" in ar_cols else "null::text as logical_mode",
        "ar.storage_mode" if "storage_mode" in ar_cols else "null::text as storage_mode",
        "ar.suite_id",
        "ar.arm_id",
        "r.run_label",
        select_expr(t_cols, "task_id", "t"),
        select_expr(t_cols, "attempt_index", "t", "integer"),
        select_expr(t_cols, "reward", "t", "numeric"),
        f"{quality_flag} as quality_flag",
        select_expr(t_cols, "exception_type", "t"),
        select_expr(t_cols, "exception_summary", "t"),
        select_expr(t_cols, "input_tokens", "t", "bigint"),
        select_expr(t_cols, "output_tokens", "t", "bigint"),
        select_expr(t_cols, "cost_usd", "t", "numeric"),
        select_expr(t_cols, "runtime_seconds", "t", "numeric"),
        select_expr(t_cols, "result_local_path", "t"),
    ]
    sql = f"""
        select {", ".join(selected)}
        from benchmark.benchmark_trials t
        join benchmark.benchmark_runs r on r.id = t.run_id
        {trial_join(schema)}
        where ar.suite_id = %s
        {any_filter("ar.arm_id", parse_words(args.arms), params)}
          and (({is_exception}) or ({is_suspect}))
        order by ar.arm_id, r.run_label, task_id, attempt_index
    """
    return rows_for_query(conn, sql, params)


def command_exception_audit(args: argparse.Namespace) -> int:
    require_suite_id(args)
    with connect(args.db_url) as conn:
        schema = load_schema_info(conn)
        if schema.has_relation("v_trial_quality_flags"):
            rows = exception_audit_query_from_view(conn, schema, args)
        else:
            rows = exception_audit_query_from_base(conn, schema, args)

    if args.inspect_local:
        local_roots = [Path(root) for root in args.local_root]
        result_index = build_result_index(local_roots) if local_roots else {}
        for row in rows:
            if not row.get("exception_summary"):
                row["local_exception_detail"] = local_exception_detail(
                    row.get("result_local_path"),
                    local_roots,
                    result_index,
                    args.local_detail_chars,
                )
            else:
                row["local_exception_detail"] = ""

    print_rows(rows)
    return 0


def result_suffix(path: str | Path | None) -> str | None:
    if not path:
        return None
    parts = Path(str(path)).parts
    if "results" not in parts:
        return None
    i = parts.index("results")
    return Path(*parts[i:]).as_posix()


def build_result_index(roots: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("result.json"):
            suffix = result_suffix(path)
            if suffix:
                index.setdefault(suffix, path)
    return index


def resolve_local_result_path(
    result_local_path: str | None,
    roots: list[Path],
    result_index: dict[str, Path],
) -> Path | None:
    if result_local_path:
        direct = Path(result_local_path)
        if direct.exists():
            return direct
        suffix = result_suffix(result_local_path)
        if suffix and suffix in result_index:
            return result_index[suffix]
        if suffix:
            for root in roots:
                candidate = root / suffix
                if candidate.exists():
                    return candidate
    return None


def one_line(text: str, limit: int) -> str:
    cleaned = " ".join(text.replace("\t", " ").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 0)] + "..."


def local_exception_detail(
    result_local_path: str | None,
    roots: list[Path],
    result_index: dict[str, Path],
    limit: int,
) -> str:
    result_path = resolve_local_result_path(result_local_path, roots, result_index)
    if result_path is None:
        return ""
    trial_dir = result_path.parent
    exception_path = trial_dir / "exception.txt"
    if exception_path.exists():
        return one_line(exception_path.read_text(encoding="utf-8", errors="replace"), limit)

    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    for key in ("exception_summary", "exception_type", "exception_info", "error"):
        value = data.get(key)
        if value:
            return one_line(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value, limit)
    result = data.get("result")
    if isinstance(result, dict):
        for key in ("exception", "error", "status"):
            value = result.get(key)
            if value:
                return one_line(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value, limit)
    return ""


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value).replace("\t", " ").replace("\n", " ")


def print_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("no_rows")
        return
    headers = list(rows[0].keys())
    print("\t".join(headers))
    for row in rows:
        print("\t".join(clean_value(row.get(header)) for header in headers))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"))
    sub = parser.add_subparsers(dest="command", required=True)

    def add_db_summary_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--suite-id", default=os.getenv("SUITE_ID"))
        p.add_argument("--arms", default=os.getenv("ARMS"))
        p.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"))
        p.add_argument("--invalid-runs-file", default=os.getenv("INVALID_RUNS_FILE"))
        p.add_argument("--missing-invalid-runs-ok", action="store_true")

    p = sub.add_parser("suite-summary", help="Summarize suite quality by arm from Supabase.")
    add_db_summary_args(p)
    p.set_defaults(func=command_suite_summary, valid_only=False)

    p = sub.add_parser("suite-summary-valid", help="Summarize suite quality excluding locally listed invalid runs.")
    add_db_summary_args(p)
    p.set_defaults(func=command_suite_summary, valid_only=True)

    p = sub.add_parser("arm-run-summary", help="Summarize each ingested arm run from Supabase.")
    add_db_summary_args(p)
    p.set_defaults(func=command_arm_run_summary, valid_only=False)

    p = sub.add_parser("arm-run-summary-valid", help="Summarize each ingested arm run excluding locally listed invalid runs.")
    add_db_summary_args(p)
    p.set_defaults(func=command_arm_run_summary, valid_only=True)

    p = sub.add_parser("exception-audit", help="List exception and suspect trials from Supabase.")
    add_db_summary_args(p)
    p.add_argument("--inspect-local", action="store_true", default=os.getenv("INSPECT_LOCAL", "").lower() in {"1", "true", "yes"})
    p.add_argument(
        "--local-root",
        action="append",
        default=parse_words(os.getenv("LOCAL_ROOTS")) or [],
        help="Local artifact root to inspect for exception.txt/result.json. Repeatable.",
    )
    p.add_argument("--local-detail-chars", type=int, default=int(os.getenv("LOCAL_DETAIL_CHARS", "500")))
    p.set_defaults(func=command_exception_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
