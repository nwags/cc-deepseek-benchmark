#!/usr/bin/env python3
"""Generate a local, read-only comprehensive benchmark evidence review.

Supabase and R2 are source inputs only. The script opens a read-only database
transaction, performs bounded R2 reads, delegates classification to the same
TypeScript analyzer used by the dashboard, and writes only local derived files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ANALYZER_VERSION = "artifact-evidence-v1.3.2"
GENERATOR_VERSION = "comprehensive-evidence-review-v1.3.2"
# Serialization revision: v1.3.2 outputs are LF-only and reject trailing
# horizontal whitespace; analyzer semantics and classification rules are unchanged.
MANIFEST_SCHEMA_VERSION = "comprehensive-evidence-review-manifest-v2"
DEFAULT_OUTPUT = Path("results/manual_verification/comprehensive_review_20260731")
DEFAULT_CHECKPOINT = Path(".review-cache/comprehensive_review_20260731/review_checkpoint.jsonl")
DEFAULT_SUITE = "phase3-full-20"
DEFAULT_STREAM_CAP = 8 * 1024 * 1024
ABSOLUTE_STREAM_CAP = 32 * 1024 * 1024
READ_LIMITS = {
    "agent_transcript": DEFAULT_STREAM_CAP,
    "trajectory": DEFAULT_STREAM_CAP,
    "verifier_stdout": 2 * 1024 * 1024,
    "verifier_ctrf": 2 * 1024 * 1024,
    "exception": 1024 * 1024,
    "result": 1024 * 1024,
    "config": 1024 * 1024,
}
ANALYSIS_TYPES = tuple(READ_LIMITS)
CANONICAL_TYPES = (
    "agent_transcript", "config", "log", "result", "trajectory",
    "verifier_ctrf", "verifier_reward", "verifier_stdout",
)
ROUTER_TYPES = ("router_log", "router_log_slice")
SECRET_KEY_RE = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|auth(?:entication|orization)?|access[_-]?key|"
    r"secret(?:[_-]?access)?[_-]?key|client[_-]?secret|token|password|passwd|"
    r"credential|private[_-]?key|database[_-]?url|db[_-]?url|dsn|cookie|session|signed[_-]?url)(?:$|[_-])",
    re.I,
)
SECRET_QUERY_RE = re.compile(
    r"^(?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|"
    r"signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)$",
    re.I,
)
REDACTED = "[REDACTED]"
SECRET_ASSIGNMENT_KEY = (
    r"(?:--?)?(?:[A-Za-z0-9.]+[_-])*(?:api[_-]?key|auth(?:entication|orization)?|access[_-]?key|"
    r"secret(?:[_-]?access)?[_-]?key|client[_-]?secret|refresh[_-]?token|"
    r"private[_-]?token|token|cookie|session|signed[_-]?url|password|passwd|"
    r"credential|private[_-]?key|database[_-]?url|db[_-]?url|dsn)(?:[_-][A-Za-z0-9.]+)*"
)
SECRET_ASSIGNMENT_PREFIX = (
    rf"(?P<prefix>(?<![A-Za-z0-9_.-])(?:export\s+)?[\"']?{SECRET_ASSIGNMENT_KEY}[\"']?\s*[:=]\s*)"
)
SECRET_DOUBLE_QUOTED_ASSIGNMENT_RE = re.compile(
    SECRET_ASSIGNMENT_PREFIX + r'"(?:\\.|[^"\\])*"', re.I | re.M,
)
SECRET_SINGLE_QUOTED_ASSIGNMENT_RE = re.compile(
    SECRET_ASSIGNMENT_PREFIX + r"'(?:\\.|[^'\\])*'", re.I | re.M,
)
SECRET_REDACTED_ASSIGNMENT_RE = re.compile(
    SECRET_ASSIGNMENT_PREFIX + r"\[(?:redacted)\]", re.I | re.M,
)
SECRET_UNQUOTED_ASSIGNMENT_RE = re.compile(
    SECRET_ASSIGNMENT_PREFIX + r"(?![\"']|\[(?:redacted)\])[^\s,;\]})]+", re.I | re.M,
)
SECRET_EMPTY_ASSIGNMENT_RE = re.compile(
    SECRET_ASSIGNMENT_PREFIX + r"(?![\"']\[(?:redacted)\][\"'])(?=$|[\r\n,;\]})\"'`])", re.I | re.M,
)
PASSWORD_ASSIGNMENT_AUDIT_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:export\s+)?[\"']?[A-Za-z0-9_.-]*(?:password|passwd)[A-Za-z0-9_.-]*[\"']?\s*[:=]\s*"
    r"(?!(?:\"\[REDACTED\]\"|'\[REDACTED\]'|\[REDACTED\](?=$|[^A-Za-z0-9_])))"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}\]]+)",
    re.I | re.M,
)
SUPPORTED_SECRET_ASSIGNMENT_AUDIT_RE = re.compile(
    rf"(?<![A-Za-z0-9_.-])(?:export\s+)?[\"']?{SECRET_ASSIGNMENT_KEY}[\"']?\s*[:=]\s*"
    r"(?!(?:\"\[REDACTED\]\"|'\[REDACTED\]'|\[REDACTED\](?=$|[^A-Za-z0-9_])))"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}\]]+)",
    re.I | re.M,
)
BEARER_AUDIT_RE = re.compile(r"\b(?:Bearer|Basic)\s+(?!\[REDACTED\])\S+", re.I)
URL_USERINFO_AUDIT_RE = re.compile(r"[a-z][a-z0-9+.-]*://[^/@\s]+@", re.I)
SECRET_QUERY_AUDIT_RE = re.compile(
    r"[?&](?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|"
    r"signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)="
    r"(?!%5BREDACTED%5D|\[REDACTED\])[^&#\s]*",
    re.I,
)
REASONING_RE = re.compile(r"thinking|reasoning", re.I)
SYNTHETIC_RETRY = "Your previous response had no visible output"
PROVIDER_KEY_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|xai-[A-Za-z0-9_-]{12,}|pplx-[A-Za-z0-9_-]{12,}|"
    r"gsk_[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9_-]{12,}|gh[opusr]_[A-Za-z0-9_]{12,}|"
    r"(?:AKIA|ASIA)[A-Z0-9]{12,}|AIza[A-Za-z0-9_-]{12,})\b",
    re.I,
)
VISIBLE_EXCERPT_CHARS = 480
VERIFIER_EXCERPT_CHARS = 2400
EXCEPTION_EXCERPT_CHARS = 1200
MAX_PACKET_TOOL_CALLS = 100
MAX_PACKET_CTRF_TESTS = 100
STRICT_SCAN_OUTPUT_NAMES = (
    "run_review.csv", "trial_review.csv", "trial_evidence.jsonl", "review_queue.csv",
    "manual_control_sample.csv", "task_disagreement_review.csv", "arm_review_summary.csv",
    "targeted_evidence_packet.csv", "targeted_evidence_bundle.jsonl",
    "targeted_evidence_bundle_manifest.json", "review_coverage.json", "review_manifest.json", "README.md",
)


RUN_DISCOVERY_SQL = """
with suite_scope as (
  select suite_id, count(*) filter (where required)::int as required_task_count
  from benchmark.benchmark_eval_suite_items
  where suite_id = %s
  group by suite_id
), trial_scope as (
  select arm_run_id, count(*)::int as actual_trial_count,
         count(distinct task_id)::int as actual_task_count
  from benchmark.benchmark_trials
  group by arm_run_id
)
select
  ars.arm_run_id::text,
  ars.run_id::text,
  ars.run_label,
  ars.arm_id,
  ars.suite_id,
  ars.suite_type,
  ars.logical_mode,
  ars.storage_mode,
  ars.status,
  ars.started_at,
  ars.finished_at,
  coalesce(ts.actual_trial_count, 0)::int as trial_count,
  coalesce(ts.actual_task_count, 0)::int as task_count,
  coalesce(ss.required_task_count, 0)::int as required_task_count,
  r.raw_metadata as run_metadata,
  invalid.reason as invalid_reason,
  invalid.invalidated_at,
  invalid.invalidated_by
from benchmark.v_arm_run_summary ars
join benchmark.benchmark_runs r on r.id = ars.run_id
left join suite_scope ss on ss.suite_id = ars.suite_id
left join trial_scope ts on ts.arm_run_id = ars.arm_run_id
left join benchmark.benchmark_invalid_arm_runs invalid
  on invalid.suite_id = ars.suite_id
 and invalid.arm_id = ars.arm_id
 and invalid.run_label = ars.run_label
where ars.suite_id = %s
  and ars.suite_type = 'full'
  and ars.logical_mode = 'full'
order by ars.arm_id, ars.finished_at desc nulls last, ars.run_label
"""

TRIAL_SQL = """
with positioned as (
  select t.*,
    row_number() over (
      partition by t.run_id, t.task_id
      order by t.attempt_index nulls last, t.id
    )::int as task_attempt,
    count(*) over (partition by t.run_id, t.task_id)::int as task_attempt_count
  from benchmark.benchmark_trials t
  where t.run_id = any(%s::uuid[])
), first_positions as (
  select run_id, task_id, min(attempt_index) as first_position
  from benchmark.benchmark_trials
  where run_id = any(%s::uuid[]) and task_id is not null
  group by run_id, task_id
), task_positions as (
  select run_id, task_id,
    row_number() over (partition by run_id order by first_position nulls last, task_id)::int as task_ordinal,
    count(*) over (partition by run_id)::int as run_task_count
  from first_positions
)
select
  t.id::text as trial_id,
  t.run_id::text,
  r.run_label,
  ar.suite_id,
  t.arm_id,
  t.task_id,
  t.task_attempt,
  t.task_attempt_count,
  t.attempt_index::int as run_trial_ordinal,
  tp.task_ordinal,
  tp.run_task_count,
  t.reward,
  t.runtime_seconds,
  t.cost_usd,
  t.input_tokens,
  t.cache_tokens,
  t.output_tokens,
  t.exception_type,
  t.exception_summary,
  t.started_at,
  t.finished_at
from positioned t
join benchmark.benchmark_runs r on r.id = t.run_id
join benchmark.benchmark_arm_runs ar on ar.id = t.arm_run_id
left join task_positions tp on tp.run_id = t.run_id and tp.task_id = t.task_id
order by r.run_label, t.attempt_index nulls last, t.id
"""

ARTIFACT_SQL = """
select id::text as artifact_id, run_id::text, trial_id::text, artifact_type,
       local_path, r2_uri, github_uri, sha256, size_bytes, created_at
from benchmark.benchmark_artifacts
where trial_id = any(%s::uuid[])
order by trial_id, artifact_type, created_at desc, id
"""


@dataclass(frozen=True)
class ReadResult:
    text: str | None
    completeness: str
    bytes_read: int
    total_bytes: int | None
    malformed: bool = False
    stored_total_bytes: int | None = None
    remote_total_bytes: int | None = None
    size_metadata_status: str = "unknown"
    read_availability: str = "unavailable"
    integrity_status: str = "unavailable"


@dataclass(frozen=True)
class Scope:
    runs: list[dict[str, Any]]
    eligible_runs: list[dict[str, Any]]
    trials: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=json_default))


def numeric(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def is_secret_key(key: str) -> bool:
    normalized = re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower()
    return bool(SECRET_KEY_RE.search(key.lower()) or SECRET_KEY_RE.search(normalized))


def sanitize_uri(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc:
            host = parsed.hostname or ""
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            if parsed.port:
                host = f"{host}:{parsed.port}"
            query = urlencode([
                (key, REDACTED if SECRET_QUERY_RE.match(key) or is_secret_key(key) else item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            ])
            return urlunsplit((parsed.scheme, host, parsed.path, query, ""))
    except (ValueError, UnicodeError):
        pass
    value = re.sub(r"([a-z][a-z0-9+.-]*://)([^/@\s:]+)(?::[^/@\s]*)?@", r"\1", value, flags=re.I)
    return re.sub(
        r"([?&](?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|"
        r"signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)=)[^&#\s]*",
        rf"\1{REDACTED}", value, flags=re.I,
    )


def redact_structured(value: Any, *, environment: bool = False) -> Any:
    if isinstance(value, list):
        return [redact_text(item) if isinstance(item, str) else redact_structured(item, environment=environment) for item in value]
    if not isinstance(value, dict):
        return redact_text(value) if isinstance(value, str) else value
    output: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if is_secret_key(key_text):
            output[key_text] = REDACTED
            continue
        nested_environment = environment or key_text.lower() in {"env", "environment", "environment_variables", "variables"}
        if REASONING_RE.search(key_text):
            output[key_text] = "[hidden reasoning not retained]"
        elif isinstance(item, (dict, list)):
            output[key_text] = redact_structured(item, environment=nested_environment)
        elif nested_environment and isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9+/=_-]{40,}", item):
            output[key_text] = REDACTED
        else:
            output[key_text] = redact_text(item) if isinstance(item, str) else item
    return output


def redact_text(text: str) -> str:
    text = re.sub(r"\b(Bearer|Basic)\s+(?!\[REDACTED\])\S+", rf"\1 {REDACTED}", text, flags=re.I)
    text = SECRET_DOUBLE_QUOTED_ASSIGNMENT_RE.sub(lambda match: f'{match.group("prefix")}"{REDACTED}"', text)
    text = SECRET_SINGLE_QUOTED_ASSIGNMENT_RE.sub(lambda match: f"{match.group('prefix')}'{REDACTED}'", text)
    text = SECRET_REDACTED_ASSIGNMENT_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}", text)
    text = SECRET_UNQUOTED_ASSIGNMENT_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}", text)
    text = SECRET_EMPTY_ASSIGNMENT_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}", text)
    text = PROVIDER_KEY_RE.sub(REDACTED, text)
    return sanitize_uri(text)


def sanitize_evidence_output(value: Any) -> Any:
    """Final sink for every retained/published derived evidence value.

    This returns a new recursively sanitized value. Immutable artifact bytes and
    raw download responses never pass through this derived-output helper.
    """
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        normalized = "\n".join(line.rstrip(" \t") for line in normalized.split("\n"))
        return redact_text(normalized)
    if isinstance(value, list):
        return [sanitize_evidence_output(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_evidence_output(item) for item in value)
    if not isinstance(value, dict):
        return value
    return {
        str(key): REDACTED if is_secret_key(str(key)) else sanitize_evidence_output(item)
        for key, item in value.items()
    }


def _strict_scan_value(value: Any, rules: set[str], *, key: str | None = None) -> None:
    """Apply independent audit expressions without retaining candidate values."""
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_key_text = str(child_key)
            if (
                REASONING_RE.search(child_key_text)
                and child_key_text not in {"thinking_event_count", "thinking_events", "hidden_reasoning_retained"}
                and child not in (None, False, 0, "", [], {}, REDACTED, "[hidden reasoning not retained]")
            ):
                rules.add("hidden_reasoning_content")
            _strict_scan_value(child, rules, key=child_key_text)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _strict_scan_value(item, rules, key=key)
        return
    if not isinstance(value, str):
        return
    if PASSWORD_ASSIGNMENT_AUDIT_RE.search(value):
        rules.add("password_assignment")
    if (
        SUPPORTED_SECRET_ASSIGNMENT_AUDIT_RE.search(value)
        or BEARER_AUDIT_RE.search(value)
        or PROVIDER_KEY_RE.search(value)
        or URL_USERINFO_AUDIT_RE.search(value)
        or SECRET_QUERY_AUDIT_RE.search(value)
    ):
        rules.add("supported_credential_pattern")


def strict_scan_output_directory(
    output_dir: Path, filenames: Iterable[str] = STRICT_SCAN_OUTPUT_NAMES,
) -> dict[str, list[str]]:
    """Return only affected filenames and rule names; never candidate values."""
    findings: dict[str, list[str]] = {}
    for filename in filenames:
        path = output_dir / filename
        if not path.exists():
            findings[filename] = ["missing_output"]
            continue
        rules: set[str] = set()
        try:
            raw = path.read_bytes()
            if b"\r" in raw:
                rules.add("carriage_return")
            text = raw.decode("utf-8")
            if re.search(r"[ \t](?:\r?\n|$)", text):
                rules.add("trailing_whitespace")
            if path.suffix == ".jsonl":
                values = [json.loads(line) for line in text.splitlines() if line.strip()]
                _strict_scan_value(values, rules)
            elif path.suffix == ".json":
                _strict_scan_value(json.loads(text), rules)
            elif path.suffix == ".csv":
                _strict_scan_value(list(csv.DictReader(io.StringIO(text, newline=""))), rules)
            else:
                _strict_scan_value(text, rules)
        except (csv.Error, json.JSONDecodeError, OSError, UnicodeDecodeError):
            rules.add("malformed_output")
        if rules:
            findings[filename] = sorted(rules)
    return findings


def definite_workspace_change(name: str, tool_input: Any) -> bool:
    if name in {"Write", "Edit", "NotebookEdit", "MultiEdit", "apply_patch"}:
        return True
    if name != "Bash" or not isinstance(tool_input, dict):
        return False
    command = str(tool_input.get("command") or "")
    return bool(re.search(
        r"(^|[;&|]\s*)(touch|mkdir|cp|mv|rm|install|patch|git\s+apply)\b|"
        r"(^|\s)(sed\s+-i|tee\b)|>{1,2}\s*[^&]", command, re.M,
    ))


def bounded_excerpt(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    sanitized = redact_text(value.strip())
    return sanitized if len(sanitized) <= limit else sanitized[:limit].rstrip() + "…"


def usage_fields(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed = {
        "input_tokens", "uncached_input_tokens", "cache_read_input_tokens",
        "cache_creation_input_tokens", "output_tokens", "cost_usd", "total_cost_usd",
    }
    result = {key: value[key] for key in allowed if key in value}
    return result or None


def sanitize_transcript_record(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    output: dict[str, Any] = {"type": record.get("type"), "subtype": record.get("subtype")}
    for key in (
        "api_refusal_category", "refusal_category", "terminal_reason", "stop_reason",
        "api_error_status", "status", "duration_api_ms", "duration_ms", "total_cost_usd",
        "id", "request_id", "usage_mode", "usage_is_cumulative",
    ):
        if key in record:
            output[key] = record[key]
    record_type = record.get("type")
    if record_type == "system":
        if record.get("subtype") == "thinking_tokens":
            output["estimated_tokens"] = record.get("estimated_tokens")
            output["estimated_tokens_delta"] = record.get("estimated_tokens_delta")
        if record.get("subtype") == "init":
            output["model"] = record.get("model")
            output["claude_code_version"] = record.get("claude_code_version") or record.get("claudeCodeVersion")
        return output
    if record_type == "user":
        serialized = json.dumps(record.get("message") or record.get("content") or "", default=json_default)
        return {"type": "user", "message": {"content": f"[{SYNTHETIC_RETRY}.]"}} if SYNTHETIC_RETRY in serialized else {"type": "user", "visible_content_omitted": True}
    if record_type == "assistant":
        message = record.get("message") if isinstance(record.get("message"), dict) else record
        safe_content: list[dict[str, Any]] = []
        for item in message.get("content") or []:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "")
            if REASONING_RE.search(item_type):
                safe_content.append({"type": item_type or "hidden_reasoning", "hidden_content_omitted": True})
            elif item_type == "text":
                content = str(item.get("text") or "")
                safe_content.append({
                    "type": "text",
                    "text": "API Error:" if content.startswith("API Error:") else "[visible assistant content]" if content.strip() else "",
                    "visible_excerpt": bounded_excerpt(content, VISIBLE_EXCERPT_CHARS),
                })
            elif item_type == "tool_use":
                name = str(item.get("name") or "")
                safe_content.append({"type": "tool_use", "name": name, "input": {"workspace_changing": definite_workspace_change(name, item.get("input"))}})
        output["message"] = {
            "id": message.get("id"), "stop_reason": message.get("stop_reason"),
            "usage": usage_fields(message.get("usage")), "content": safe_content,
        }
        output["usage"] = usage_fields(record.get("usage"))
        return output
    if record_type == "result":
        if "result" in record:
            output["result"] = "[visible result]" if isinstance(record.get("result"), str) and record["result"].strip() else ""
            output["visible_result_excerpt"] = bounded_excerpt(record.get("result"), VISIBLE_EXCERPT_CHARS)
        output["usage"] = usage_fields(record.get("usage"))
        if isinstance(record.get("modelUsage"), dict):
            output["modelUsage"] = {str(model): usage_fields(usage) for model, usage in record["modelUsage"].items()}
        return output
    return output


def sanitize_transcript(raw: bytes) -> tuple[str | None, bool]:
    lines: list[str] = []
    malformed = False
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line.decode("utf-8"))
            safe = sanitize_transcript_record(record)
            if safe is not None:
                lines.append(json.dumps(redact_structured(safe), sort_keys=True, separators=(",", ":")))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            malformed = True
    return ("\n".join(lines) or None, malformed)


def newline_aligned(head: bytes, tail: bytes) -> bytes:
    head_end = head.rfind(b"\n")
    tail_start = tail.find(b"\n")
    return (head[: head_end + 1] if head_end >= 0 else b"") + (tail[tail_start + 1 :] if tail_start >= 0 else b"")


def require_runtime_dependencies() -> tuple[Any, Any, Any]:
    try:
        import boto3
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(
            "boto3 and psycopg[binary] are required; run with "
            "`uv run --with boto3 --with 'psycopg[binary]' python scripts/generate_comprehensive_evidence_review.py`"
        ) from exc
    return boto3, psycopg, dict_row


def connect_read_only(db_url: str, psycopg: Any, dict_row: Any) -> Any:
    connection = psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10)
    connection.execute("begin transaction read only")
    connection.execute("set local statement_timeout = '120s'")
    return connection


def discover_scope(connection: Any, suite_id: str) -> Scope:
    runs = [dict(row) for row in connection.execute(RUN_DISCOVERY_SQL, (suite_id, suite_id)).fetchall()]
    for run in runs:
        expected_trials = int(run["required_task_count"] or 0) * 3
        run["full_suite_complete"] = bool(
            expected_trials
            and int(run["task_count"] or 0) == int(run["required_task_count"] or 0)
            and int(run["trial_count"] or 0) == expected_trials
        )
        run["valid"] = run.get("invalid_reason") is None
        run["selected"] = False

    latest_valid: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not run["valid"] or not run["full_suite_complete"]:
            continue
        latest_valid.setdefault(str(run["arm_id"]), run)
    eligible = sorted(latest_valid.values(), key=lambda row: (str(row["arm_id"]), str(row["run_label"])))
    for run in eligible:
        run["selected"] = True

    run_ids = [str(run["run_id"]) for run in eligible]
    if not run_ids:
        return Scope(runs=runs, eligible_runs=[], trials=[], artifacts=[])
    trials = [dict(row) for row in connection.execute(TRIAL_SQL, (run_ids, run_ids)).fetchall()]
    trial_ids = [str(trial["trial_id"]) for trial in trials]
    artifacts = [dict(row) for row in connection.execute(ARTIFACT_SQL, (trial_ids,)).fetchall()] if trial_ids else []
    return Scope(runs=runs, eligible_runs=eligible, trials=trials, artifacts=artifacts)


def r2_client(args: argparse.Namespace, boto3: Any) -> Any:
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=args.r2_endpoint_url,
        aws_access_key_id=args.r2_access_key_id,
        aws_secret_access_key=args.r2_secret_access_key,
        region_name=args.r2_region,
        config=Config(connect_timeout=5, read_timeout=args.read_timeout, retries={"max_attempts": 2, "mode": "standard"}),
    )


def parse_r2_uri(uri: str) -> tuple[str, str]:
    parsed = urlsplit(uri)
    if parsed.scheme != "r2" or not parsed.hostname or not parsed.path.lstrip("/"):
        raise ValueError("invalid_r2_uri")
    return parsed.hostname, parsed.path.lstrip("/")


def get_range(client: Any, uri: str, start: int, end: int, limit: int) -> tuple[bytes, int | None, bool]:
    bucket, key = parse_r2_uri(uri)
    response = client.get_object(Bucket=bucket, Key=key, Range=f"bytes={start}-{end}")
    body = response["Body"]
    try:
        data = body.read(limit + 1)
    finally:
        body.close()
    exceeded = len(data) > limit
    retained = data[:limit]
    total: int | None = None
    content_range = str(response.get("ContentRange") or "")
    match = re.fullmatch(r"bytes\s+(\d+)-(\d+)/(\d+)", content_range, re.I)
    if match:
        total = int(match.group(3))
    elif not content_range and response.get("ContentLength") is not None:
        # No Content-Range means the endpoint ignored Range. ContentLength is
        # the full returned body length, not a verified byte-range total.
        total = int(response["ContentLength"])
    range_honored = bool(match and int(match.group(1)) == start)
    return retained, total, range_honored


def compare_size_metadata(stored: int | None, remote: int | None) -> str:
    if stored is None and remote is None:
        return "unknown"
    if stored is None:
        return "stored_missing"
    if remote is None:
        return "remote_unverified"
    if stored == remote:
        return "consistent"
    return "stored_underreported" if stored < remote else "stored_overreported"


def read_artifact(client: Any, artifact: dict[str, Any], stream_cap: int) -> ReadResult:
    artifact_type = str(artifact.get("artifact_type") or "")
    uri = artifact.get("r2_uri")
    stored_total = int(artifact["size_bytes"]) if artifact.get("size_bytes") is not None else None
    if not uri:
        return ReadResult(
            None, "unavailable", 0, stored_total,
            stored_total_bytes=stored_total, size_metadata_status="remote_unverified",
            read_availability="unavailable", integrity_status="unavailable",
        )
    configured_limit = stream_cap if artifact_type in {"agent_transcript", "trajectory"} else READ_LIMITS.get(artifact_type, 1024 * 1024)
    limit = min(max(int(configured_limit), 1), ABSOLUTE_STREAM_CAP)
    is_jsonl = artifact_type == "agent_transcript"
    is_structured = artifact_type in {"trajectory", "result", "config", "verifier_ctrf"}

    try:
        head_limit = max(limit // 2, 1)
        head, remote_total, head_ok = get_range(client, str(uri), 0, head_limit - 1, head_limit)
        total = remote_total if remote_total is not None else stored_total
        size_status = compare_size_metadata(stored_total, remote_total)
        size_conflict = size_status in {"stored_underreported", "stored_overreported"}
        fully_read = False

        if total is not None and total > limit:
            tail_limit = max(limit - len(head), 0)
            tail_start = max(total - tail_limit, 0)
            tail, tail_total, tail_ok = get_range(client, str(uri), tail_start, total - 1, tail_limit) if tail_limit else (b"", remote_total, True)
            if remote_total is not None and tail_total is not None and tail_total != remote_total:
                size_conflict = True
                size_status = "remote_range_conflict"
            raw = newline_aligned(head, tail) if head_ok and tail_ok else head
            completeness = "head_tail_only" if head_ok and tail_ok else "truncated"
            bytes_read = len(head) + len(tail)
        else:
            raw = head
            bytes_read = len(head)
            if total is not None and len(raw) < total:
                remainder_limit = min(total - len(raw), max(limit - bytes_read, 0))
                remainder, remainder_total, remainder_ok = get_range(
                    client, str(uri), len(raw), total - 1, remainder_limit,
                ) if remainder_limit else (b"", remote_total, False)
                bytes_read += len(remainder)
                if remote_total is not None and remainder_total is not None and remainder_total != remote_total:
                    size_conflict = True
                    size_status = "remote_range_conflict"
                if remainder_ok:
                    raw += remainder
                fully_read = remainder_ok and len(raw) >= total
            elif total is not None:
                raw = raw[:total]
                fully_read = len(raw) >= total
            completeness = "complete" if fully_read and remote_total is not None and not size_conflict else "truncated"

        expected_hash = str(artifact.get("sha256") or "").strip().lower()
        if fully_read:
            actual_hash = hashlib.sha256(raw).hexdigest()
            integrity_status = "verified" if expected_hash and actual_hash == expected_hash else "mismatch" if expected_hash else "not_verifiable"
        else:
            integrity_status = "not_checked_incomplete"
        if integrity_status == "mismatch":
            completeness = "malformed"

        if artifact_type == "agent_transcript":
            text, malformed = sanitize_transcript(raw)
            if malformed and completeness == "complete":
                completeness = "malformed"
            return ReadResult(
                text, completeness, bytes_read, total, malformed,
                stored_total, remote_total, size_status,
                "available" if completeness == "complete" else "partial",
                integrity_status,
            )
        decoded = raw.decode("utf-8")
        if is_structured:
            if not fully_read:
                return ReadResult(
                    None, completeness, bytes_read, total,
                    stored_total_bytes=stored_total, remote_total_bytes=remote_total,
                    size_metadata_status=size_status, read_availability="partial",
                    integrity_status=integrity_status,
                )
            try:
                parsed = json.loads(decoded)
            except json.JSONDecodeError:
                if artifact_type == "config":
                    return ReadResult(
                        redact_text(decoded), completeness, bytes_read, total,
                        stored_total_bytes=stored_total, remote_total_bytes=remote_total,
                        size_metadata_status=size_status, read_availability="available",
                        integrity_status=integrity_status,
                    )
                return ReadResult(
                    None, "malformed", bytes_read, total, True,
                    stored_total, remote_total, size_status, "partial", integrity_status,
                )
            return ReadResult(
                json.dumps(redact_structured(parsed), sort_keys=True), completeness, bytes_read, total,
                stored_total_bytes=stored_total, remote_total_bytes=remote_total,
                size_metadata_status=size_status, read_availability="available",
                integrity_status=integrity_status,
            )
        return ReadResult(
            redact_text(decoded), completeness, bytes_read, total,
            stored_total_bytes=stored_total, remote_total_bytes=remote_total,
            size_metadata_status=size_status,
            read_availability="available" if completeness == "complete" else "partial",
            integrity_status=integrity_status,
        )
    except Exception as exc:  # noqa: BLE001
        # Exception details can include signed endpoints or credentials. They are
        # deliberately not retained in checkpoint/output records.
        _ = exc
        return ReadResult(
            None, "unavailable", 0, stored_total,
            stored_total_bytes=stored_total, size_metadata_status="remote_unverified",
            read_availability="unavailable", integrity_status="unavailable",
        )


class AnalyzerBridge:
    def __init__(self, repo_root: Path) -> None:
        self.process = subprocess.Popen(
            ["node", str(repo_root / "apps/dashboard/src/lib/trial-analysis-bridge.mjs")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
        )

    def classify(self, request: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(request, separators=(",", ":"), default=json_default) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("analyzer_bridge_closed")
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError("analyzer_bridge_error")
        return response["analysis"]

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        self.process.wait(timeout=10)


def router_observability(artifacts: list[dict[str, Any]], run_metadata: Any) -> str:
    if any(artifact.get("artifact_type") in ROUTER_TYPES for artifact in artifacts):
        return "retained"
    if isinstance(run_metadata, dict):
        retention = run_metadata.get("router_log_retention") or run_metadata.get("router_observability")
        if retention in {False, "not_retained", "disabled"}:
            return "not_retained"
    return "unknown"


def retained_result_reports_exception(reads: list[dict[str, Any]]) -> bool:
    result_read = next((item for item in reads if item.get("artifactType") == "result"), None)
    if not result_read or not result_read.get("text") or result_read.get("completeness") != "complete":
        return False
    try:
        value = json.loads(str(result_read["text"]))
    except json.JSONDecodeError:
        return False
    if not isinstance(value, dict):
        return False
    if value.get("exception") is True or value.get("exception_type") or value.get("exceptionType"):
        return True
    for key in ("exception_info", "exceptionInfo", "exception"):
        if isinstance(value.get(key), dict) and value[key]:
            return True
    for key in ("agent_result", "agentResult"):
        nested = value.get(key)
        if isinstance(nested, dict) and (nested.get("exception_type") or nested.get("exceptionType")):
            return True
    return False


def select_artifacts(artifacts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    selected: dict[str, dict[str, Any]] = {}
    duplicate = False
    for artifact in sorted(
        artifacts,
        key=lambda item: (
            str(item.get("artifact_type") or ""),
            0 if item.get("r2_uri") else 1,
            str(item.get("created_at") or ""),
            str(item.get("artifact_id") or ""),
        ),
    ):
        artifact_type = str(artifact.get("artifact_type") or "")
        if artifact_type not in ANALYSIS_TYPES:
            continue
        if artifact_type in selected:
            duplicate = True
            continue
        selected[artifact_type] = artifact
    return list(selected.values()), duplicate


def implementation_source_hashes(repo_root: Path) -> dict[str, str]:
    return {
        "analyzer": sha256(repo_root / "apps/dashboard/src/lib/trial-analysis-core.ts"),
        "generator": sha256(Path(__file__).resolve()),
    }


def generator_options(args: argparse.Namespace) -> dict[str, Any]:
    endpoint_hash = hashlib.sha256(str(args.r2_endpoint_url or "").encode("utf-8")).hexdigest()
    return {
        "suite_id": str(args.suite_id),
        "workers": int(args.workers),
        "stream_cap": int(args.stream_cap),
        "absolute_stream_cap": ABSOLUTE_STREAM_CAP,
        "read_limits": dict(sorted(READ_LIMITS.items())),
        "read_timeout_seconds": int(args.read_timeout),
        "sample_per_class": int(args.sample_per_class),
        "resume_requested": bool(args.resume),
        "r2_region": str(args.r2_region),
        "r2_endpoint_sha256": endpoint_hash,
    }


def run_configuration_fingerprint(run: dict[str, Any]) -> str:
    payload = {
        "run_id": run.get("run_id"),
        "arm_run_id": run.get("arm_run_id"),
        "run_label": run.get("run_label"),
        "arm_id": run.get("arm_id"),
        "suite_id": run.get("suite_id"),
        "suite_type": run.get("suite_type"),
        "logical_mode": run.get("logical_mode"),
        "storage_mode": run.get("storage_mode"),
        "status": run.get("status"),
        "started_at": iso(run.get("started_at")),
        "finished_at": iso(run.get("finished_at")),
        "run_metadata": json_safe(run.get("run_metadata")),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=json_default).encode()).hexdigest()


def fingerprint(
    trial: dict[str, Any], artifacts: list[dict[str, Any]], stream_cap: int,
    source_hashes: dict[str, str], reader_and_generator_options: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
) -> str:
    payload = {
        "analyzer": ANALYZER_VERSION,
        "generator": GENERATOR_VERSION,
        "source_hashes": source_hashes,
        "stream_cap": stream_cap,
        "reader_and_generator_options": reader_and_generator_options or {},
        "run_configuration_fingerprint": run_configuration_fingerprint(run) if run else None,
        "trial": {key: json_safe(trial.get(key)) for key in (
            "trial_id", "reward", "runtime_seconds", "cost_usd", "input_tokens",
            "cache_tokens", "output_tokens", "exception_type",
        )},
        "database_exception_summary_sha256": hashlib.sha256(
            str(trial.get("exception_summary") or "").encode("utf-8")
        ).hexdigest(),
        "artifacts": [{
            "id": item.get("artifact_id"), "type": item.get("artifact_type"),
            "sha256": item.get("sha256"), "size": item.get("size_bytes"), "r2": bool(item.get("r2_uri")),
        } for item in artifacts],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=json_default).encode()).hexdigest()


def scope_fingerprint(
    scope: Scope, source_hashes: dict[str, str], options: dict[str, Any], suite_id: str,
) -> tuple[str, dict[str, Any]]:
    selected_run_ids = sorted(str(run["run_id"]) for run in scope.eligible_runs)
    trial_ids = sorted(str(trial["trial_id"]) for trial in scope.trials)
    artifact_inventory = sorted((
        str(item.get("artifact_id")), str(item.get("trial_id")), str(item.get("artifact_type")),
        str(item.get("sha256") or ""), numeric(item.get("size_bytes")), bool(item.get("r2_uri")),
    ) for item in scope.artifacts)
    run_fingerprints = {
        str(run["run_id"]): run_configuration_fingerprint(run)
        for run in sorted(scope.eligible_runs, key=lambda item: str(item["run_id"]))
    }
    payload = {
        "suite_id": suite_id,
        "selected_run_ids": selected_run_ids,
        "trial_ids": trial_ids,
        "artifact_inventory": artifact_inventory,
        "source_hashes": source_hashes,
        "reader_and_generator_options": options,
        "run_configuration_fingerprints": run_fingerprints,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=json_default).encode()
    descriptor = {
        "selected_run_count": len(selected_run_ids),
        "trial_count": len(trial_ids),
        "artifact_count": len(artifact_inventory),
        "trial_ids_sha256": hashlib.sha256("\n".join(trial_ids).encode()).hexdigest(),
        "artifact_inventory_sha256": hashlib.sha256(json.dumps(artifact_inventory, separators=(",", ":"), default=json_default).encode()).hexdigest(),
        "source_hashes": source_hashes,
        "reader_and_generator_options": options,
        "run_configuration_fingerprints": run_fingerprints,
    }
    return hashlib.sha256(serialized).hexdigest(), descriptor


def prepare_trial(
    client: Any,
    trial: dict[str, Any],
    artifacts: list[dict[str, Any]],
    run: dict[str, Any],
    stream_cap: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected, duplicate = select_artifacts(artifacts)
    reads: list[dict[str, Any]] = []
    bytes_read = 0
    oversized = 0
    unavailable = 0
    read_results: list[ReadResult] = []
    for artifact in selected:
        result = read_artifact(client, artifact, stream_cap)
        read_results.append(result)
        bytes_read += result.bytes_read
        oversized += int(result.completeness in {"head_tail_only", "truncated"})
        unavailable += int(result.completeness == "unavailable")
        reads.append({
            "artifactType": artifact.get("artifact_type"),
            "artifactId": artifact.get("artifact_id"),
            "text": result.text,
            "available": result.text is not None,
            "truncated": result.completeness != "complete",
            "malformed": result.malformed,
            "completeness": result.completeness,
            "bytesRead": result.bytes_read,
            "totalBytes": result.total_bytes,
        })

    present = {str(item.get("artifact_type")) for item in artifacts}
    expects_exception = bool(
        trial.get("exception_type")
        or trial.get("exception_summary")
        or "exception" in present
        or retained_result_reports_exception(reads)
    )
    expected = set(CANONICAL_TYPES) | ({"exception"} if expects_exception else set())
    canonical_present = len(expected & present)
    r2_present = len({kind for kind in expected if any(item.get("artifact_type") == kind and item.get("r2_uri") for item in artifacts)})
    size_statuses = [item.size_metadata_status for item in read_results]
    if any(status in {"stored_underreported", "stored_overreported", "remote_range_conflict"} for status in size_statuses):
        size_metadata_status = "conflict"
    elif size_statuses and all(status == "consistent" for status in size_statuses):
        size_metadata_status = "consistent"
    elif size_statuses:
        size_metadata_status = "partial"
    else:
        size_metadata_status = "unknown"
    availabilities = [item.read_availability for item in read_results]
    r2_read_availability = "available" if availabilities and all(item == "available" for item in availabilities) \
        else "unavailable" if not availabilities or all(item == "unavailable" for item in availabilities) else "partial"
    integrities = [item.integrity_status for item in read_results]
    if "mismatch" in integrities:
        analyzed_artifact_integrity_status = "mismatch"
    elif integrities and all(item == "verified" for item in integrities):
        analyzed_artifact_integrity_status = "verified"
    elif not integrities or all(item == "unavailable" for item in integrities):
        analyzed_artifact_integrity_status = "unavailable"
    elif any(item in {"not_checked_incomplete", "unavailable"} for item in integrities):
        analyzed_artifact_integrity_status = "partial"
    else:
        analyzed_artifact_integrity_status = "not_verifiable"
    request = {
        "reward": numeric(trial.get("reward")),
        "runtimeSeconds": numeric(trial.get("runtime_seconds")),
        "exceptionType": redact_text(str(trial["exception_type"])) if trial.get("exception_type") else None,
        "databaseExceptionSummary": redact_text(str(trial["exception_summary"])) if trial.get("exception_summary") else None,
        "databaseInputTokens": numeric(trial.get("input_tokens")),
        "databaseCacheTokens": numeric(trial.get("cache_tokens")),
        "databaseOutputTokens": numeric(trial.get("output_tokens")),
        "databaseCostUsd": numeric(trial.get("cost_usd")),
        "routerObservability": router_observability(artifacts, run.get("run_metadata")),
        "canonicalEvidenceComplete": canonical_present == len(expected),
        "artifactSelectionAmbiguous": duplicate,
        "artifacts": reads,
    }
    metadata = {
        "bytes_read": bytes_read,
        "oversized": oversized,
        "unavailable": unavailable,
        "canonical_present": canonical_present,
        "canonical_expected": len(expected),
        "r2_present": r2_present,
        "r2_expected": len(expected),
        "r2_read_availability": r2_read_availability,
        "analyzed_artifact_integrity_status": analyzed_artifact_integrity_status,
        "size_metadata_status": size_metadata_status,
        "artifact_read_status": {
            str(artifact.get("artifact_id")): {
                "artifact_id": str(artifact.get("artifact_id")),
                "artifact_type": str(artifact.get("artifact_type")),
                "completeness": result.completeness,
                "read_availability": result.read_availability,
                "integrity_status": result.integrity_status,
                "size_metadata_status": result.size_metadata_status,
                "stored_total_bytes": result.stored_total_bytes,
                "remote_total_bytes": result.remote_total_bytes,
                "bytes_read": result.bytes_read,
                "expected_sha256": str(artifact.get("sha256") or "") or None,
            }
            for artifact, result in zip(selected, read_results)
        },
        "supporting_artifact_ids": [str(item.get("artifact_id")) for item in selected],
        "duplicate_artifacts": duplicate,
    }
    return request, metadata


def request_artifact(request: dict[str, Any], artifact_type: str) -> dict[str, Any] | None:
    return next((item for item in request.get("artifacts", []) if item.get("artifactType") == artifact_type), None)


def transcript_packet_facts(request: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    artifact = request_artifact(request, "agent_transcript")
    visible_excerpts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    result_excerpts: list[str] = []
    if artifact and artifact.get("text"):
        for line in str(artifact["text"]).splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            message = record.get("message") if isinstance(record.get("message"), dict) else {}
            for item in message.get("content") or []:
                if not isinstance(item, dict):
                    continue
                excerpt = bounded_excerpt(item.get("visible_excerpt"), VISIBLE_EXCERPT_CHARS)
                if excerpt and len(visible_excerpts) < 12:
                    visible_excerpts.append(excerpt)
                if item.get("type") == "tool_use" and len(tool_calls) < MAX_PACKET_TOOL_CALLS:
                    tool_calls.append({
                        "name": redact_text(str(item.get("name") or "unknown")),
                        "workspace_changing": bool((item.get("input") or {}).get("workspace_changing")) if isinstance(item.get("input"), dict) else False,
                    })
            result_excerpt = bounded_excerpt(record.get("visible_result_excerpt"), VISIBLE_EXCERPT_CHARS)
            if result_excerpt and len(result_excerpts) < 3:
                result_excerpts.append(result_excerpt)
    return {
        "visible_assistant_events": analysis["visible_assistant_events"],
        "thinking_event_count": analysis["thinking_events"],
        "tool_call_count": analysis["tool_calls"],
        "workspace_changing_call_count": analysis["workspace_changing_calls"],
        "trajectory_step_count": analysis["trajectory_steps"],
        "substantive_trajectory_step_count": analysis["substantive_trajectory_steps"],
        "synthetic_retry_count": analysis["synthetic_retry_count"],
        "terminal_reason": analysis["terminal_reason"],
        "stop_reason": analysis["stop_reason"],
        "api_error_status": analysis["api_error_status"],
        "visible_assistant_excerpts": visible_excerpts,
        "visible_result_excerpts": result_excerpts,
        "tool_calls": tool_calls,
        "hidden_reasoning_retained": False,
    }


def ctrf_packet_tests(text: Any) -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    tests: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def walk(value: Any) -> None:
        if len(tests) >= MAX_PACKET_CTRF_TESTS:
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        name = value.get("name") or value.get("testName") or value.get("title")
        status = value.get("status") or value.get("state") or value.get("result")
        failure_value = value.get("failure") or value.get("failureMessage") or value.get("message") or value.get("trace")
        if isinstance(failure_value, dict):
            failure_value = failure_value.get("message") or failure_value.get("trace") or failure_value.get("type")
        if name is not None and (status is not None or failure_value is not None):
            safe_name = bounded_excerpt(str(name), 300) or "unnamed test"
            safe_status = bounded_excerpt(str(status), 80) if status is not None else None
            safe_failure = bounded_excerpt(str(failure_value), 600) if failure_value is not None else None
            signature = (safe_name, safe_status or "", safe_failure or "")
            if signature not in seen:
                seen.add(signature)
                tests.append({"name": safe_name, "status": safe_status, "failure_message": safe_failure})
        for item in value.values():
            if isinstance(item, (dict, list)):
                walk(item)

    walk(parsed)
    return tests


def legacy_v111_reclassification_labels(analysis: dict[str, Any], request: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    if analysis["activity_subtype"] == "activity_unknown" and analysis["termination_subtype"] == "timeout":
        labels.append("reclassified_setup_transport_v1_1_1")
    verifier = request_artifact(request, "verifier_stdout")
    verifier_text = str(verifier.get("text") or "") if verifier else ""
    old_environment_signature = re.search(
        # Reproduce the v1.1.1 failure-detail rule exactly for provenance-only
        # packet selection. The current classifier deliberately does not use
        # this broad `environment` match because package-install output can
        # contain the word while a structured assertion actually failed.
        r"no tests ran|collection error|failed to (?:start|create)|environment|docker daemon|verifier (?:error|failed)",
        verifier_text,
        re.I,
    )
    if analysis["failure_subtype"] == "test_assertion_failure" and old_environment_signature:
        labels.append("reclassified_verifier_environment_v1_1_1")
    return labels


def manual_packet_evidence(
    request: dict[str, Any], analysis: dict[str, Any], metadata: dict[str, Any],
) -> dict[str, Any]:
    verifier = request_artifact(request, "verifier_stdout")
    ctrf = request_artifact(request, "verifier_ctrf")
    exception = request_artifact(request, "exception")
    return sanitize_evidence_output({
        "transcript_activity": transcript_packet_facts(request, analysis),
        "verifier_stdout_excerpt": bounded_excerpt(verifier.get("text"), VERIFIER_EXCERPT_CHARS) if verifier else None,
        "ctrf_tests": ctrf_packet_tests(ctrf.get("text") if ctrf else None),
        "exception_evidence": {
            "database_exception_summary": request.get("databaseExceptionSummary"),
            "exception_artifact_excerpt": bounded_excerpt(exception.get("text"), EXCEPTION_EXCERPT_CHARS) if exception else None,
            "trusted_markers": analysis["exception_trusted_markers"],
            "database_summary_trusted_markers": analysis["database_exception_summary_trusted_markers"],
            "unclassified_exception": analysis["unclassified_exception"],
            "exception_after_substantive_activity": analysis["exception_after_substantive_activity"],
        },
        "harbor_result": {
            "reward_present": analysis["result_reward_present"],
            "reward_value": analysis["result_reward_value"],
            "exception_present": analysis["result_exception_present"],
            "exception_type": analysis["result_exception_type"],
            "termination_reason": analysis["result_termination_reason"],
            "status": analysis["result_status"],
            "database_result_consistency": analysis["database_result_consistency"],
        },
        "artifacts": sorted(metadata["artifact_read_status"].values(), key=lambda item: (item["artifact_type"], item["artifact_id"])),
    })


def load_checkpoint(path: Path, source_hashes: dict[str, str]) -> dict[str, dict[str, Any]]:
    cached: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return cached
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            if (
                row.get("analyzer_version") == ANALYZER_VERSION
                and row.get("generator_version") == GENERATOR_VERSION
                and row.get("source_hashes") == source_hashes
            ):
                cached[str(row["trial_id"])] = row
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return cached


def append_checkpoint(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitize_evidence_output(row), sort_keys=True, separators=(",", ":"), default=json_default) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def evidence_reasons(analysis: dict[str, Any]) -> list[str]:
    return [f"{item.get('label')}: {item.get('value')}" for item in analysis.get("evidence", [])]


def make_trial_row(trial: dict[str, Any], analysis: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    reward_present = trial.get("reward") is not None
    return {
        "trial_id": str(trial["trial_id"]),
        "run_label": str(trial["run_label"]),
        "suite_id": str(trial["suite_id"]),
        "arm_id": str(trial["arm_id"]),
        "task_id": str(trial["task_id"]),
        "task_attempt": int(trial["task_attempt"]),
        "run_trial_ordinal": int(trial["run_trial_ordinal"]),
        "raw_reward_present": reward_present,
        "raw_reward": numeric(trial.get("reward")),
        "raw_outcome": analysis["raw_outcome"],
        "execution_validity": analysis["execution_validity"],
        "activity_subtype": analysis["activity_subtype"],
        "policy_disposition": analysis["policy_disposition"],
        "failure_subtype": analysis["failure_subtype"],
        "termination_subtype": analysis["termination_subtype"],
        "exception_trusted_markers": json.dumps(analysis["exception_trusted_markers"], separators=(",", ":")),
        "unclassified_exception": analysis["unclassified_exception"],
        "exception_after_substantive_activity": analysis["exception_after_substantive_activity"],
        "result_reward_present": analysis["result_reward_present"],
        "result_reward_value": analysis["result_reward_value"],
        "result_exception_present": analysis["result_exception_present"],
        "result_exception_type": analysis["result_exception_type"],
        "result_termination_reason": analysis["result_termination_reason"],
        "result_status": analysis["result_status"],
        "database_result_consistency": analysis["database_result_consistency"],
        "telemetry_status": analysis["telemetry_status"],
        "canonical_completeness": f"{metadata['canonical_present']}/{metadata['canonical_expected']}",
        "r2_indexed_completeness": f"{metadata['r2_present']}/{metadata['r2_expected']}",
        "r2_read_availability": metadata["r2_read_availability"],
        "analyzed_artifact_integrity_status": metadata["analyzed_artifact_integrity_status"],
        "size_metadata_status": metadata["size_metadata_status"],
        "router_observability": analysis["router_observability"],
        "classification_confidence": analysis["confidence"],
        "evidence_complete": bool(analysis["evidence_complete"]),
        "manual_review_required": bool(analysis["manual_review_required"]),
        "manual_review_priority": analysis["manual_review_priority"],
        "analyzer_manual_review_priority": analysis["manual_review_priority"],
        "evidence_reasons": json.dumps(evidence_reasons(analysis), separators=(",", ":")),
        "supporting_artifact_ids": json.dumps(metadata["supporting_artifact_ids"], separators=(",", ":")),
        "analyzer_version": analysis["analyzer_version"],
        "cost_usd": numeric(trial.get("cost_usd")),
        "runtime_seconds": numeric(trial.get("runtime_seconds")),
        "exception_type": redact_text(str(trial["exception_type"])) if trial.get("exception_type") else None,
        "database_exception_summary": redact_text(str(trial["exception_summary"])) if trial.get("exception_summary") else None,
        "database_exception_summary_present": analysis["database_exception_summary_present"],
        "database_exception_summary_trusted_markers": json.dumps(
            analysis["database_exception_summary_trusted_markers"], separators=(",", ":")
        ),
        "bytes_read": metadata["bytes_read"],
        "oversized_artifacts": metadata["oversized"],
        "unavailable_artifacts": metadata["unavailable"],
    }


def deterministic_key(row: dict[str, Any]) -> tuple[str, str]:
    digest = hashlib.sha256(str(row["trial_id"]).encode()).hexdigest()
    return digest, str(row["trial_id"])


def task_disagreements(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    by_task_arm: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task_arm[(str(row["task_id"]), str(row["arm_id"]))].append(row)
    tasks = sorted({task for task, _ in by_task_arm})
    result: list[dict[str, Any]] = []
    headline_trials: set[str] = set()
    for task in tasks:
        arms = sorted(arm for candidate_task, arm in by_task_arm if candidate_task == task)
        for arm_a, arm_b in itertools.combinations(arms, 2):
            left = by_task_arm[(task, arm_a)]
            right = by_task_arm[(task, arm_b)]
            left_success = sum(row["raw_outcome"] == "success" for row in left)
            right_success = sum(row["raw_outcome"] == "success" for row in right)
            if left_success == right_success:
                continue
            headline = (left_success == len(left) and right_success == 0) or (right_success == len(right) and left_success == 0)
            supporting = sorted({str(row["trial_id"]) for row in left + right})
            if headline:
                headline_trials.update(supporting)
            def summary(items: list[dict[str, Any]], field: str) -> str:
                return json.dumps(Counter(str(row[field]) for row in items), sort_keys=True, separators=(",", ":"))

            signals: list[str] = []
            left_policy = sum(row["policy_disposition"] == "provider_policy_refusal" for row in left)
            right_policy = sum(row["policy_disposition"] == "provider_policy_refusal" for row in right)
            left_timeout = sum(row["termination_subtype"] == "timeout" for row in left)
            right_timeout = sum(row["termination_subtype"] == "timeout" for row in right)
            left_setup = sum(row["termination_subtype"] == "setup_or_transport_exception" for row in left)
            right_setup = sum(row["termination_subtype"] == "setup_or_transport_exception" for row in right)
            left_verifier = sum(row["failure_subtype"] == "verifier_or_environment_failure" for row in left)
            right_verifier = sum(row["failure_subtype"] == "verifier_or_environment_failure" for row in right)
            left_substantive_success = sum(row["raw_outcome"] == "success" and row["execution_validity"] == "substantive" for row in left)
            right_substantive_success = sum(row["raw_outcome"] == "success" and row["execution_validity"] == "substantive" for row in right)
            if left_policy != right_policy: signals.append("policy_access_difference")
            if left_timeout != right_timeout: signals.append("timeout_reliability_difference")
            if left_setup != right_setup: signals.append("setup_or_transport_difference")
            if left_verifier != right_verifier: signals.append("verifier_environment_difference")
            if not signals and left_substantive_success != right_substantive_success: signals.append("capability_difference")
            category = signals[0] if len(signals) == 1 else "mixed" if len(signals) > 1 else "unresolved"
            result.append({
                "task_id": task,
                "arm_a": arm_a,
                "arm_b": arm_b,
                "arm_a_raw_outcome": f"{left_success}/{len(left)} success",
                "arm_b_raw_outcome": f"{right_success}/{len(right)} success",
                "arm_a_execution_classes": json.dumps(Counter(row["execution_validity"] for row in left), sort_keys=True),
                "arm_b_execution_classes": json.dumps(Counter(row["execution_validity"] for row in right), sort_keys=True),
                "arm_a_activity_summary": summary(left, "activity_subtype"),
                "arm_b_activity_summary": summary(right, "activity_subtype"),
                "arm_a_policy_summary": summary(left, "policy_disposition"),
                "arm_b_policy_summary": summary(right, "policy_disposition"),
                "arm_a_timeout_summary": f"{left_timeout}/{len(left)}",
                "arm_b_timeout_summary": f"{right_timeout}/{len(right)}",
                "arm_a_setup_transport_summary": f"{left_setup}/{len(left)}",
                "arm_b_setup_transport_summary": f"{right_setup}/{len(right)}",
                "arm_a_verifier_summary": summary(left, "failure_subtype"),
                "arm_b_verifier_summary": summary(right, "failure_subtype"),
                "disagreement_category": category,
                "headline_relevant": headline,
                "supporting_trial_links": json.dumps([f"/trials/{trial_id}" for trial_id in supporting], separators=(",", ":")),
            })
    return result, headline_trials


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def review_reasons(row: dict[str, Any], *, high_cost_threshold: float | None, headline_trials: set[str]) -> list[str]:
    reasons: list[str] = []
    if row["policy_disposition"] == "provider_policy_refusal": reasons.append("policy_refusal")
    if row["activity_subtype"] in {"empty_completion_zero_usage", "empty_completion_after_long_api_path_wait", "thinking_only_empty_completion"}: reasons.append("empty_or_thinking_only_completion")
    if row["activity_subtype"] == "synthetic_retry_empty_completion": reasons.append("synthetic_retry")
    if row["termination_subtype"] == "setup_or_transport_exception": reasons.append("setup_or_transport_exception")
    if row["termination_subtype"] == "timeout": reasons.append("timeout")
    if row["termination_subtype"] != "none" and row["raw_outcome"] == "success": reasons.append("exception_with_positive_reward")
    if row["activity_subtype"] == "questionable_success_no_activity": reasons.append("questionable_success")
    if row["activity_subtype"] == "activity_unknown": reasons.append("activity_unknown")
    if row["unclassified_exception"]: reasons.append("unclassified_exception")
    if row["telemetry_status"] not in {"consistent", "zero_usage_empty_completion"}: reasons.append("telemetry_mismatch_or_incomplete")
    if not row["evidence_complete"] or row["canonical_completeness"].split("/")[0] != row["canonical_completeness"].split("/")[1]: reasons.append("missing_or_incomplete_evidence")
    if row["database_result_consistency"] not in {"consistent", "not_recorded"}: reasons.append("database_result_inconsistency")
    if row["analyzed_artifact_integrity_status"] in {"mismatch", "partial", "unavailable"}: reasons.append("analyzed_artifact_integrity_issue")
    if row["size_metadata_status"] == "conflict": reasons.append("r2_size_metadata_conflict")
    if row["failure_subtype"] == "verifier_or_environment_failure": reasons.append("verifier_or_environment_failure")
    if high_cost_threshold is not None and row["raw_outcome"] == "failure" and (row["cost_usd"] or 0) >= high_cost_threshold: reasons.append("high_cost_failure")
    if row["classification_confidence"] in {"low", "unknown"}: reasons.append("low_confidence")
    if str(row["trial_id"]) in headline_trials: reasons.append("headline_task_disagreement")
    return sorted(set(reasons))


PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2}
REASON_PRIORITY = {
    "policy_refusal": "high", "empty_or_thinking_only_completion": "high", "synthetic_retry": "high",
    "setup_or_transport_exception": "high", "timeout": "medium", "exception_with_positive_reward": "high",
    "questionable_success": "high", "activity_unknown": "high", "unclassified_exception": "high",
    "telemetry_mismatch_or_incomplete": "medium", "missing_or_incomplete_evidence": "medium",
    "database_result_inconsistency": "medium", "analyzed_artifact_integrity_issue": "medium",
    "r2_size_metadata_conflict": "high", "verifier_or_environment_failure": "high",
    "high_cost_failure": "medium", "low_confidence": "high", "headline_task_disagreement": "medium",
}


def combine_priority(analyzer_priority: str, reasons: list[str]) -> str:
    candidates = [analyzer_priority] + [REASON_PRIORITY.get(reason, "low") for reason in reasons]
    return max(candidates, key=lambda item: PRIORITY_RANK[item])


def queue_strata(reasons: list[str]) -> list[str]:
    correctness = {
        "policy_refusal", "empty_or_thinking_only_completion", "synthetic_retry",
        "setup_or_transport_exception", "timeout", "exception_with_positive_reward",
        "questionable_success", "activity_unknown", "unclassified_exception",
        "verifier_or_environment_failure", "database_result_inconsistency",
        "analyzed_artifact_integrity_issue", "r2_size_metadata_conflict",
    }
    strata: list[str] = []
    if correctness.intersection(reasons): strata.append("correctness_anomaly")
    if {"telemetry_mismatch_or_incomplete", "missing_or_incomplete_evidence", "database_result_inconsistency", "analyzed_artifact_integrity_issue", "r2_size_metadata_conflict"}.intersection(reasons):
        strata.append("telemetry_or_integrity")
    if "headline_task_disagreement" in reasons: strata.append("task_disagreement")
    if "high_cost_failure" in reasons: strata.append("high_cost_failure")
    return strata


def arm_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for arm, items_iter in itertools.groupby(sorted(rows, key=lambda row: (row["arm_id"], row["trial_id"])), key=lambda row: row["arm_id"]):
        items = list(items_iter)
        telemetry_mismatch = {"database_missing_transcript_present", "database_zero_transcript_nonzero", "nonzero_mismatch", "partial", "incomplete_evidence", "unknown"}
        output.append({
            "arm_id": arm,
            "trials_reviewed": len(items),
            "substantive_successes": sum(row["raw_outcome"] == "success" and row["execution_validity"] == "substantive" for row in items),
            "substantive_failures": sum(row["raw_outcome"] == "failure" and row["execution_validity"] == "substantive" for row in items),
            "policy_refusals": sum(row["policy_disposition"] == "provider_policy_refusal" for row in items),
            "empty_completions": sum(row["activity_subtype"] in {"empty_completion_zero_usage", "empty_completion_after_long_api_path_wait", "thinking_only_empty_completion", "synthetic_retry_empty_completion"} for row in items),
            "timeouts": sum(row["termination_subtype"] == "timeout" for row in items),
            "setup_transport_failures": sum(row["termination_subtype"] == "setup_or_transport_exception" for row in items),
            "telemetry_mismatches": sum(row["telemetry_status"] in telemetry_mismatch for row in items),
            "unknown_classifications": sum(row["activity_subtype"] == "activity_unknown" for row in items),
            "high_confidence": sum(row["classification_confidence"] == "high" for row in items),
            "medium_confidence": sum(row["classification_confidence"] == "medium" for row in items),
            "low_or_unknown_confidence": sum(row["classification_confidence"] in {"low", "unknown"} for row in items),
            "manual_review_queue": sum(row["manual_review_required"] for row in items),
        })
    return output


def manual_sample(rows: list[dict[str, Any]], per_class: int) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    for arm in sorted({str(row["arm_id"]) for row in rows}):
        arm_rows = [row for row in rows if row["arm_id"] == arm]
        ordinary = [
            row for row in arm_rows
            if row["activity_subtype"] == "substantive_agent_activity"
            and not row["exception_type"] and not row.get("database_exception_summary_present")
            and row["termination_subtype"] == "none"
            and row["policy_disposition"] == "none_detected"
            and row["evidence_complete"] and row["classification_confidence"] == "high"
            and row["telemetry_status"] == "consistent"
        ]
        strata = (
            ("ordinary_success", [row for row in ordinary if row["raw_outcome"] == "success"]),
            ("ordinary_failure", [row for row in ordinary if row["raw_outcome"] == "failure"]),
            ("timeout_control", [row for row in arm_rows if row["termination_subtype"] == "timeout"]),
            ("telemetry_mismatch_control", [
                row for row in arm_rows
                if row["telemetry_status"] not in {"consistent", "zero_usage_empty_completion"}
                and row["activity_subtype"] == "substantive_agent_activity"
                and row["termination_subtype"] == "none" and row["policy_disposition"] == "none_detected"
                and row["evidence_complete"] and row["classification_confidence"] == "high"
            ]),
            ("exception_success_control", [
                row for row in arm_rows
                if row["raw_outcome"] == "success" and row["termination_subtype"] != "none"
            ]),
            ("incomplete_evidence_control", [row for row in arm_rows if not row["evidence_complete"]]),
        )
        for label, candidates in strata:
            for row in sorted(candidates, key=deterministic_key)[:per_class]:
                sample.append({
                    "sample_stratum": label,
                    "arm_id": arm,
                    "trial_id": row["trial_id"],
                    "task_id": row["task_id"],
                    "raw_outcome": row["raw_outcome"],
                    "execution_validity": row["execution_validity"],
                    "activity_subtype": row["activity_subtype"],
                    "failure_subtype": row["failure_subtype"],
                    "termination_subtype": row["termination_subtype"],
                    "telemetry_status": row["telemetry_status"],
                    "evidence_complete": row["evidence_complete"],
                    "trial_link": f"/trials/{row['trial_id']}",
                })
    return sample


def targeted_evidence_packet(
    rows: list[dict[str, Any]], controls: list[dict[str, Any]], evidence_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strata_by_trial: dict[str, set[str]] = defaultdict(set)
    evidence_by_trial = {str(row["trial_id"]): row for row in evidence_rows}
    for row in rows:
        trial_id = str(row["trial_id"])
        if row["policy_disposition"] == "provider_policy_refusal": strata_by_trial[trial_id].add("all_policy_refusals")
        if row["activity_subtype"] in {
            "empty_completion_zero_usage", "empty_completion_after_long_api_path_wait",
            "thinking_only_empty_completion", "synthetic_retry_empty_completion",
        }: strata_by_trial[trial_id].add("all_empty_or_synthetic")
        if row["raw_outcome"] == "success" and row["termination_subtype"] != "none":
            strata_by_trial[trial_id].add("all_positive_reward_exceptions")
        if row["canonical_completeness"] == "7/9": strata_by_trial[trial_id].add("all_7_of_9_evidence")
        if row["failure_subtype"] == "extraneous_output_artifacts":
            strata_by_trial[trial_id].add("all_extraneous_output_artifacts")
        legacy_labels = set(evidence_by_trial.get(trial_id, {}).get("legacy_v1_1_1_reclassifications") or [])
        if "reclassified_setup_transport_v1_1_1" in legacy_labels:
            strata_by_trial[trial_id].add("all_reclassified_setup_transport_v1_1_1")
        if "reclassified_verifier_environment_v1_1_1" in legacy_labels:
            strata_by_trial[trial_id].add("all_reclassified_verifier_environment_v1_1_1")
    for control in controls:
        if str(control["sample_stratum"]).startswith("ordinary_"):
            strata_by_trial[str(control["trial_id"])].add("revised_ordinary_controls")

    by_id = {str(row["trial_id"]): row for row in rows}
    packet: list[dict[str, Any]] = []
    for trial_id in sorted(strata_by_trial):
        row = by_id[trial_id]
        packet.append({
            "packet_strata": ";".join(sorted(strata_by_trial[trial_id])),
            "trial_id": trial_id,
            "trial_link": f"/trials/{trial_id}",
            "run_label": row["run_label"], "arm_id": row["arm_id"], "task_id": row["task_id"],
            "raw_outcome": row["raw_outcome"], "execution_validity": row["execution_validity"],
            "activity_subtype": row["activity_subtype"], "policy_disposition": row["policy_disposition"],
            "failure_subtype": row["failure_subtype"], "termination_subtype": row["termination_subtype"],
            "telemetry_status": row["telemetry_status"], "canonical_completeness": row["canonical_completeness"],
            "r2_read_availability": row["r2_read_availability"], "analyzed_artifact_integrity_status": row["analyzed_artifact_integrity_status"],
            "classification_confidence": row["classification_confidence"],
            "evidence_reasons": row["evidence_reasons"],
            "supporting_artifact_ids": row["supporting_artifact_ids"],
            "analyzer_version": row["analyzer_version"],
        })
    bundle: list[dict[str, Any]] = []
    for index_row in packet:
        trial_id = str(index_row["trial_id"])
        evidence = evidence_by_trial[trial_id]
        row = by_id[trial_id]
        bundle.append({
            "packet_strata": str(index_row["packet_strata"]).split(";"),
            "identity": {
                "trial_id": trial_id, "run_label": row["run_label"], "suite_id": row["suite_id"],
                "arm_id": row["arm_id"], "task_id": row["task_id"], "task_attempt": row["task_attempt"],
                "run_trial_ordinal": row["run_trial_ordinal"], "trial_link": index_row["trial_link"],
            },
            "classification": evidence["classification"],
            "analyzer_version": row["analyzer_version"],
            "classification_confidence": row["classification_confidence"],
            "evidence_complete": row["evidence_complete"],
            "evidence_reasons": evidence["evidence"],
            "manual_evidence": evidence["manual_evidence"],
            "supporting_artifact_ids": evidence["supporting_artifact_ids"],
            "hidden_reasoning_retained": False,
        })
    return sanitize_evidence_output(packet), sanitize_evidence_output(bundle)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip(" \t") for line in text.split("\n"))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    rows = sanitize_evidence_output(rows)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    temporary.replace(path)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Serialize derived rows only after recursive final-sink sanitization."""
    atomic_text(
        path,
        "".join(
            json.dumps(sanitize_evidence_output(row), sort_keys=True, separators=(",", ":"), default=json_default) + "\n"
            for row in rows
        ),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_review_rows(scope: Scope) -> list[dict[str, Any]]:
    return [{
        "run_id": row["run_id"], "run_label": row["run_label"], "suite_id": row["suite_id"],
        "arm_id": row["arm_id"], "status": row["status"], "trial_count": row["trial_count"],
        "task_count": row["task_count"], "required_task_count": row["required_task_count"],
        "full_suite_complete": row["full_suite_complete"], "valid": row["valid"], "selected": row["selected"],
        "invalid_reason": redact_text(str(row["invalid_reason"])) if row.get("invalid_reason") else None,
        "invalidated_at": iso(row.get("invalidated_at")),
        "started_at": iso(row.get("started_at")), "finished_at": iso(row.get("finished_at")),
    } for row in sorted(scope.runs, key=lambda item: (str(item["arm_id"]), str(item["run_label"])))]


def generate_outputs(
    output_dir: Path,
    scope: Scope,
    trial_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    generated_at: str,
    stats: dict[str, int],
    sample_per_class: int,
    options: dict[str, Any],
) -> dict[str, str]:
    # Work on recursively sanitized copies so every downstream derived output,
    # including CSV cells and nested manual-evidence JSON, shares one final sink.
    trial_rows = sanitize_evidence_output(trial_rows)
    evidence_rows = sanitize_evidence_output(evidence_rows)
    suite_id = str(scope.eligible_runs[0]["suite_id"]) if scope.eligible_runs else DEFAULT_SUITE
    disagreement_rows, headline_trials = task_disagreements(trial_rows)
    failure_costs = [float(row["cost_usd"]) for row in trial_rows if row["raw_outcome"] == "failure" and row.get("cost_usd") is not None]
    high_cost_threshold = percentile(failure_costs, 0.9)
    queue_rows: list[dict[str, Any]] = []
    for row in trial_rows:
        reasons = review_reasons(row, high_cost_threshold=high_cost_threshold, headline_trials=headline_trials)
        if reasons:
            row["manual_review_required"] = True
            row["manual_review_priority"] = combine_priority(str(row["analyzer_manual_review_priority"]), reasons)
            queue_rows.append({
                **row,
                "review_reasons": ";".join(reasons),
                "review_strata": ";".join(queue_strata(reasons)),
                "trial_link": f"/trials/{row['trial_id']}",
            })
    summaries = arm_summaries(trial_rows)
    sample = manual_sample(trial_rows, sample_per_class)
    targeted_packet, targeted_bundle = targeted_evidence_packet(trial_rows, sample, evidence_rows)

    trial_fields = [
        "trial_id", "run_label", "suite_id", "arm_id", "task_id", "task_attempt", "run_trial_ordinal",
        "raw_reward_present", "raw_reward", "raw_outcome", "execution_validity", "activity_subtype",
        "policy_disposition", "failure_subtype", "termination_subtype", "exception_trusted_markers",
        "unclassified_exception",
        "exception_after_substantive_activity", "result_reward_present", "result_reward_value",
        "result_exception_present", "result_exception_type", "result_termination_reason", "result_status",
        "database_result_consistency", "telemetry_status", "canonical_completeness",
        "r2_indexed_completeness", "r2_read_availability", "analyzed_artifact_integrity_status", "size_metadata_status",
        "router_observability", "classification_confidence", "evidence_complete",
        "manual_review_required", "manual_review_priority", "analyzer_manual_review_priority",
        "evidence_reasons", "supporting_artifact_ids",
        "analyzer_version", "cost_usd", "runtime_seconds", "exception_type",
        "database_exception_summary", "database_exception_summary_present",
        "database_exception_summary_trusted_markers", "bytes_read",
        "oversized_artifacts", "unavailable_artifacts",
    ]
    write_csv(output_dir / "run_review.csv", run_review_rows(scope))
    write_csv(output_dir / "trial_review.csv", trial_rows, trial_fields)
    write_jsonl(output_dir / "trial_evidence.jsonl", evidence_rows)
    write_csv(output_dir / "review_queue.csv", queue_rows, trial_fields + ["review_reasons", "review_strata", "trial_link"])
    write_csv(output_dir / "manual_control_sample.csv", sample)
    write_csv(output_dir / "task_disagreement_review.csv", disagreement_rows)
    write_csv(output_dir / "arm_review_summary.csv", summaries)
    write_csv(output_dir / "targeted_evidence_packet.csv", targeted_packet)
    write_jsonl(output_dir / "targeted_evidence_bundle.jsonl", targeted_bundle)
    packet_strata_counts = Counter(
        stratum
        for row in targeted_packet
        for stratum in str(row["packet_strata"]).split(";")
        if stratum
    )
    packet_files = ("targeted_evidence_packet.csv", "targeted_evidence_bundle.jsonl")
    packet_manifest = {
        "schema_version": "targeted-manual-evidence-bundle-v1",
        "analyzer_version": ANALYZER_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_at": generated_at,
        "trial_count": len(targeted_bundle),
        "file_count": len(packet_files),
        "strata": dict(sorted(packet_strata_counts.items())),
        "files": {
            name: {"bytes": (output_dir / name).stat().st_size, "sha256": sha256(output_dir / name)}
            for name in packet_files
        },
    }
    atomic_text(output_dir / "targeted_evidence_bundle_manifest.json", json.dumps(packet_manifest, indent=2, sort_keys=True) + "\n")

    confidence = Counter(row["classification_confidence"] for row in trial_rows)
    expected_packet_strata = (
        "all_policy_refusals", "all_empty_or_synthetic", "all_positive_reward_exceptions",
        "all_7_of_9_evidence", "all_reclassified_setup_transport_v1_1_1",
        "all_reclassified_verifier_environment_v1_1_1", "all_extraneous_output_artifacts",
        "revised_ordinary_controls",
    )
    coverage = {
        "analyzer_version": ANALYZER_VERSION,
        "generated_at": generated_at,
        "suite_id": suite_id,
        "runs_discovered": len(scope.runs),
        "valid_runs_reviewed": len(scope.eligible_runs),
        "invalid_or_unselected_runs": len(scope.runs) - len(scope.eligible_runs),
        "trials_reviewed": len(trial_rows),
        "artifact_rows_discovered": len(scope.artifacts),
        "complete_evidence_trials": sum(row["evidence_complete"] for row in trial_rows),
        "incomplete_evidence_trials": sum(not row["evidence_complete"] for row in trial_rows),
        "confidence": dict(sorted(confidence.items())),
        "manual_review_queue": len(queue_rows),
        "manual_control_sample": len(sample),
        "manual_control_strata": dict(sorted(Counter(row["sample_stratum"] for row in sample).items())),
        "review_queue_priorities": dict(sorted(Counter(row["manual_review_priority"] for row in queue_rows).items())),
        "review_queue_strata": dict(sorted(Counter(stratum for row in queue_rows for stratum in row["review_strata"].split(";") if stratum).items())),
        "task_disagreement_rows": len(disagreement_rows),
        "task_disagreement_categories": dict(sorted(Counter(row["disagreement_category"] for row in disagreement_rows).items())),
        "headline_disagreement_trials": len(headline_trials),
        "targeted_evidence_packet": len(targeted_packet),
        "targeted_evidence_packet_strata": {
            stratum: packet_strata_counts.get(stratum, 0) for stratum in expected_packet_strata
        },
        "r2_read_availability": dict(sorted(Counter(row["r2_read_availability"] for row in trial_rows).items())),
        "analyzed_artifact_integrity_status": dict(sorted(Counter(row["analyzed_artifact_integrity_status"] for row in trial_rows).items())),
        "size_metadata_status": dict(sorted(Counter(row["size_metadata_status"] for row in trial_rows).items())),
        "high_cost_failure_threshold_usd": high_cost_threshold,
        "read_statistics": stats,
        "source_of_truth": "Raw benchmark rewards, quality flags, and denominators remain unchanged in Supabase and historical result files.",
    }
    atomic_text(output_dir / "review_coverage.json", json.dumps(coverage, indent=2, sort_keys=True) + "\n")
    readme = f"""# Comprehensive evidence review

Generated: `{generated_at}`

Analyzer: `{ANALYZER_VERSION}`

Generator: `{GENERATOR_VERSION}`

Suite: `{suite_id}`

This directory is a local derived review layer. It reads Supabase and immutable R2 objects but does not write to either service. Raw rewards, stored quality flags, pass-rate denominators, historical results, and artifact bytes remain unchanged.

Coverage: {len(scope.eligible_runs)} selected valid full-suite runs, {len(trial_rows)} trials, and {len(scope.artifacts)} artifact metadata rows. The manual-review queue contains {len(queue_rows)} trials. The control sample contains strict ordinary controls plus explicit timeout, telemetry-mismatch, exception-success, and incomplete-evidence strata.

`trial_review.csv` is the row-level validated snapshot. `trial_evidence.jsonl` contains transparent evidence facts and direct artifact identifiers, never hidden reasoning or raw configuration secrets. `targeted_evidence_packet.csv` indexes the sanitized `targeted_evidence_bundle.jsonl`; its independent packet manifest binds row counts and hashes. `review_manifest.json` binds source versions, scope, row counts, and output hashes. `run_review.csv` retains invalid and unselected candidates for provenance. See `docs/COMPREHENSIVE_EVIDENCE_REVIEW_METHOD.md` for bounds, precedence, sampling, and limitations.
"""
    atomic_text(output_dir / "README.md", readme)

    files = [
        "run_review.csv", "trial_review.csv", "trial_evidence.jsonl", "review_queue.csv",
        "manual_control_sample.csv", "task_disagreement_review.csv", "arm_review_summary.csv",
        "targeted_evidence_packet.csv", "targeted_evidence_bundle.jsonl",
        "targeted_evidence_bundle_manifest.json", "review_coverage.json", "README.md",
    ]
    output_hashes = {name: sha256(output_dir / name) for name in files}
    source_hashes = implementation_source_hashes(Path(__file__).resolve().parents[1])
    selected_run_ids = sorted(str(run["run_id"]) for run in scope.eligible_runs)
    scope_digest, scope_descriptor = scope_fingerprint(scope, source_hashes, options, suite_id)
    row_counts = {
        "run_review.csv": len(scope.runs), "trial_review.csv": len(trial_rows),
        "trial_evidence.jsonl": len(evidence_rows), "review_queue.csv": len(queue_rows),
        "manual_control_sample.csv": len(sample), "task_disagreement_review.csv": len(disagreement_rows),
        "arm_review_summary.csv": len(summaries), "targeted_evidence_packet.csv": len(targeted_packet),
        "targeted_evidence_bundle.jsonl": len(targeted_bundle),
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "analyzer_version": ANALYZER_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source_hashes": source_hashes,
        "generated_at": generated_at,
        "suite_id": suite_id,
        "selected_run_ids": selected_run_ids,
        "scope_fingerprint": scope_digest,
        "scope_fingerprint_inputs": scope_descriptor,
        "row_counts": row_counts,
        "outputs": {
            name: {
                "sha256": digest,
                "bytes": (output_dir / name).stat().st_size,
                "rows": row_counts.get(name),
            }
            for name, digest in sorted(output_hashes.items())
        },
    }
    atomic_text(output_dir / "review_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    output_hashes["review_manifest.json"] = sha256(output_dir / "review_manifest.json")
    return output_hashes


def analyze_scope(args: argparse.Namespace, scope: Scope, boto3: Any, repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    artifacts_by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in scope.artifacts:
        artifacts_by_trial[str(artifact["trial_id"])].append(artifact)
    run_by_id = {str(run["run_id"]): run for run in scope.eligible_runs}
    checkpoint_path = args.checkpoint_path
    source_hashes = implementation_source_hashes(repo_root)
    options = generator_options(args)
    cache = load_checkpoint(checkpoint_path, source_hashes) if args.resume else {}
    client = r2_client(args, boto3)
    bridge = AnalyzerBridge(repo_root)
    trial_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    stats = {
        "bytes_read": 0,
        "evidence_bytes_represented": 0,
        "cache_hits": 0,
        "oversized_artifacts": 0,
        "unavailable_artifacts": 0,
        "analyzed_trials": 0,
    }

    def work(trial: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
        trial_artifacts = artifacts_by_trial[str(trial["trial_id"])]
        run = run_by_id[str(trial["run_id"])]
        request, metadata = prepare_trial(client, trial, trial_artifacts, run, args.stream_cap)
        return request, metadata, fingerprint(trial, trial_artifacts, args.stream_cap, source_hashes, options, run)

    pending: dict[Any, dict[str, Any]] = {}
    trials = sorted(scope.trials, key=lambda row: (str(row["run_label"]), int(row["run_trial_ordinal"] or 0), str(row["trial_id"])))
    try:
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="evidence-read") as executor:
            iterator = iter(trials)
            while True:
                while len(pending) < args.workers * 2:
                    try:
                        trial = next(iterator)
                    except StopIteration:
                        break
                    trial_id = str(trial["trial_id"])
                    trial_artifacts = artifacts_by_trial[trial_id]
                    run = run_by_id[str(trial["run_id"])]
                    expected_fingerprint = fingerprint(trial, trial_artifacts, args.stream_cap, source_hashes, options, run)
                    cached = cache.get(trial_id)
                    if cached and cached.get("fingerprint") == expected_fingerprint:
                        trial_rows.append(cached["trial_row"])
                        evidence_rows.append(cached["evidence_row"])
                        checkpoint_rows.append(cached)
                        stats["cache_hits"] += 1
                        stats["evidence_bytes_represented"] += int(cached["trial_row"].get("bytes_read") or 0)
                        stats["oversized_artifacts"] += int(cached["trial_row"].get("oversized_artifacts") or 0)
                        stats["unavailable_artifacts"] += int(cached["trial_row"].get("unavailable_artifacts") or 0)
                    else:
                        pending[executor.submit(work, trial)] = trial
                if not pending:
                    try:
                        next(iterator)
                    except StopIteration:
                        break
                    raise AssertionError("unreachable")
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    trial = pending.pop(future)
                    request, metadata, row_fingerprint = future.result()
                    analysis = bridge.classify(request)
                    trial_row = make_trial_row(trial, analysis, metadata)
                    legacy_reclassifications = legacy_v111_reclassification_labels(analysis, request)
                    evidence_row = sanitize_evidence_output({
                        "trial_id": str(trial["trial_id"]),
                        "analyzer_version": ANALYZER_VERSION,
                        "summary": analysis["summary"],
                        "classification": {
                            key: analysis[key] for key in (
                                "raw_outcome", "execution_validity", "activity_subtype", "policy_disposition",
                                "failure_subtype", "termination_subtype", "telemetry_status", "confidence",
                                "manual_review_required", "manual_review_priority", "database_result_consistency",
                                "result_reward_present", "result_reward_value", "result_exception_present",
                                "result_exception_type", "result_termination_reason", "result_status",
                                "exception_trusted_markers", "unclassified_exception",
                                "exception_after_substantive_activity",
                                "database_exception_summary_present",
                                "database_exception_summary_trusted_markers",
                            )
                        },
                        "evidence": analysis["evidence"],
                        "configuration": analysis["configuration"],
                        "supporting_artifact_ids": metadata["supporting_artifact_ids"],
                        "read_completeness": {item["artifactType"]: item["completeness"] for item in request["artifacts"]},
                        "r2_read_status": metadata["artifact_read_status"],
                        "manual_evidence": manual_packet_evidence(request, analysis, metadata),
                        "legacy_v1_1_1_reclassifications": legacy_reclassifications,
                        "thinking_event_count": analysis["thinking_events"],
                        "hidden_reasoning_retained": False,
                    })
                    checkpoint_row = sanitize_evidence_output({
                        "trial_id": str(trial["trial_id"]), "analyzer_version": ANALYZER_VERSION,
                        "generator_version": GENERATOR_VERSION, "source_hashes": source_hashes,
                        "fingerprint": row_fingerprint, "trial_row": trial_row, "evidence_row": evidence_row,
                    })
                    append_checkpoint(checkpoint_path, checkpoint_row)
                    checkpoint_rows.append(checkpoint_row)
                    trial_rows.append(trial_row)
                    evidence_rows.append(evidence_row)
                    stats["bytes_read"] += int(metadata["bytes_read"])
                    stats["evidence_bytes_represented"] += int(metadata["bytes_read"])
                    stats["oversized_artifacts"] += int(metadata["oversized"])
                    stats["unavailable_artifacts"] += int(metadata["unavailable"])
                    stats["analyzed_trials"] += 1
    finally:
        bridge.close()

    trial_rows.sort(key=lambda row: (row["run_label"], row["run_trial_ordinal"], row["trial_id"]))
    evidence_rows.sort(key=lambda row: row["trial_id"])
    checkpoint_rows.sort(key=lambda row: str(row["trial_id"]))
    write_jsonl(checkpoint_path, checkpoint_rows)
    return trial_rows, evidence_rows, stats


def print_scope(scope: Scope) -> None:
    print(f"discovered_runs\t{len(scope.runs)}")
    for run in sorted(scope.runs, key=lambda row: (str(row["arm_id"]), str(row["run_label"]))):
        disposition = "selected" if run["selected"] else "invalid" if not run["valid"] else "unselected"
        print(f"run\t{disposition}\t{run['arm_id']}\t{run['run_label']}\ttrials={run['trial_count']}\ttasks={run['task_count']}")
    print(f"selected_runs\t{len(scope.eligible_runs)}")
    print(f"discovered_trials\t{len(scope.trials)}")
    print(f"artifact_rows\t{len(scope.artifacts)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true", help="Discover and print exact scope without R2 reads or output writes.")
    parser.add_argument("--suite-id", default=DEFAULT_SUITE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stream-cap", type=int, default=int(os.getenv("DASHBOARD_ANALYSIS_MAX_BYTES", DEFAULT_STREAM_CAP)))
    parser.add_argument("--read-timeout", type=int, default=15)
    parser.add_argument("--sample-per-class", type=int, default=2)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"))
    parser.add_argument("--r2-endpoint-url", default=os.getenv("R2_ENDPOINT_URL"))
    parser.add_argument("--r2-access-key-id", default=os.getenv("R2_ACCESS_KEY_ID"))
    parser.add_argument("--r2-secret-access-key", default=os.getenv("R2_SECRET_ACCESS_KEY"))
    parser.add_argument("--r2-region", default=os.getenv("R2_REGION", "auto"))
    args = parser.parse_args(argv)
    args.workers = min(max(args.workers, 1), 16)
    args.stream_cap = min(max(args.stream_cap, 1024), ABSOLUTE_STREAM_CAP)
    args.output_dir = args.output_dir.resolve()
    args.checkpoint_path = args.checkpoint_path.resolve()
    if not args.db_url:
        parser.error("SUPABASE_DB_URL or --db-url is required")
    if not args.metadata_only and not all((args.r2_endpoint_url, args.r2_access_key_id, args.r2_secret_access_key)):
        parser.error("R2 endpoint, access key, and secret access key are required for full review")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    boto3, psycopg, dict_row = require_runtime_dependencies()
    connection = connect_read_only(args.db_url, psycopg, dict_row)
    try:
        scope = discover_scope(connection, args.suite_id)
    finally:
        connection.rollback()
        connection.close()
    print_scope(scope)
    if args.metadata_only:
        print("metadata_only\ttrue")
        print("writes\t0")
        return 0
    if not scope.eligible_runs:
        raise SystemExit("No eligible valid full-suite runs were discovered.")

    repo_root = Path(__file__).resolve().parents[1]
    generated_at = datetime.now(timezone.utc).isoformat()
    trial_rows, evidence_rows, stats = analyze_scope(args, scope, boto3, repo_root)
    checksums = generate_outputs(
        args.output_dir, scope, trial_rows, evidence_rows, generated_at, stats,
        args.sample_per_class, generator_options(args),
    )

    subtype_counts = Counter((row["arm_id"], row["activity_subtype"]) for row in trial_rows)
    print(f"bytes_read\t{stats['bytes_read']}")
    print(f"evidence_bytes_represented\t{stats['evidence_bytes_represented']}")
    print(f"oversized_artifacts\t{stats['oversized_artifacts']}")
    print(f"unavailable_artifacts\t{stats['unavailable_artifacts']}")
    print(f"cache_hits\t{stats['cache_hits']}")
    coverage = json.loads((args.output_dir / "review_coverage.json").read_text(encoding="utf-8"))
    print(f"review_queue\t{coverage['manual_review_queue']}")
    for (arm, subtype), count in sorted(subtype_counts.items()):
        print(f"classification\t{arm}\t{subtype}\t{count}")
    for name, digest in sorted(checksums.items()):
        print(f"sha256\t{digest}\t{args.output_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
