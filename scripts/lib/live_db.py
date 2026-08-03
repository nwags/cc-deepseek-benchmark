from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from scripts.lib.live_events import BoundedQueue, Redactor, bounded_backoff_delays, utc_now
from scripts.lib.path_safety import ensure_workspace_output_path


@dataclass(frozen=True)
class PublicationItem:
    kind: str
    payload: dict[str, Any]


class LiveStore(Protocol):
    def publish_batch(self, items: Sequence[PublicationItem]) -> None: ...


TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "interrupted", "finalized"})
TERMINAL_PUBLICATION_STATUSES = frozenset(
    {"completed", "failed", "ineligible"}
)
TRIAL_STABILITY_RANK = {"observed": 0, "complete": 1}
ARTIFACT_STABILITY_RANK = {"observed": 0, "stable": 1, "uploaded": 2}
ARTIFACT_IMMUTABLE_METADATA_KEYS = frozenset(
    {
        "live_run_id",
        "trial_key",
        "artifact_type",
        "relative_local_path",
        "r2_uri",
        "sha256",
        "size_bytes",
        "stability_state",
        "uploaded_at",
    }
)


class LiveArtifactConflict(RuntimeError):
    pass


def _monotonic_nullable_number(current: Any, incoming: Any) -> Any:
    if current is None:
        return incoming
    if incoming is None:
        return current
    return max(current, incoming)


def _earliest_non_null(current: Any, incoming: Any) -> Any:
    if current is None:
        return incoming
    if incoming is None:
        return current
    return min(current, incoming)


def _latest_non_null(current: Any, incoming: Any) -> Any:
    if current is None:
        return incoming
    if incoming is None:
        return current
    return max(current, incoming)


def _higher_ranked_state(
    current: Any,
    incoming: Any,
    *,
    ranks: Mapping[str, int],
) -> Any:
    if current is None:
        return incoming
    if incoming is None:
        return current
    return (
        incoming
        if ranks.get(str(incoming), -1) > ranks.get(str(current), -1)
        else current
    )


def merge_live_trial_state(
    current: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    """Model final-evidence and monotonic fields in the trial SQL upsert."""
    merged = {**current, **incoming}
    current_finished = current.get("finished_at")
    incoming_finished = incoming.get("finished_at")
    incoming_is_later = (
        incoming_finished is not None
        and (
            current_finished is None
            or incoming_finished > current_finished
        )
    )
    preserve_current_terminal = (
        current_finished is not None and not incoming_is_later
    )

    for field in (
        "live_run_id",
        "trial_key",
        "task_id",
        "attempt_index",
        "relative_local_path",
    ):
        merged[field] = (
            current.get(field)
            if current.get(field) is not None
            else incoming.get(field)
        )

    for field in (
        "status",
        "reward",
        "exception_type",
        "exception_summary",
        "completion_evidence",
        "raw_result",
    ):
        if preserve_current_terminal:
            merged[field] = current.get(field)
        else:
            merged[field] = (
                incoming.get(field)
                if incoming.get(field) is not None
                else current.get(field)
            )

    for field in (
        "runtime_seconds",
        "input_tokens",
        "cache_tokens",
        "output_tokens",
        "cost_usd",
    ):
        merged[field] = _monotonic_nullable_number(
            current.get(field),
            incoming.get(field),
        )

    merged["started_at"] = _earliest_non_null(
        current.get("started_at"),
        incoming.get("started_at"),
    )
    merged["finished_at"] = _latest_non_null(
        current_finished,
        incoming_finished,
    )
    merged["stability_state"] = _higher_ranked_state(
        current.get("stability_state"),
        incoming.get("stability_state"),
        ranks=TRIAL_STABILITY_RANK,
    )
    return merged


def merge_live_artifact_state(
    current: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    """Model immutable identity and upload state in the artifact SQL upsert."""
    current_uri = current.get("r2_uri")
    incoming_uri = incoming.get("r2_uri")
    if (
        current_uri is not None
        and incoming_uri is not None
        and current_uri != incoming_uri
    ):
        raise LiveArtifactConflict(
            "conflicting R2 URI for immutable live artifact identity"
        )

    merged = {**current, **incoming}
    for field in (
        "live_run_id",
        "trial_key",
        "artifact_type",
        "relative_local_path",
        "sha256",
        "size_bytes",
    ):
        merged[field] = (
            current.get(field)
            if current.get(field) is not None
            else incoming.get(field)
        )
    merged["r2_uri"] = (
        current_uri if current_uri is not None else incoming_uri
    )
    merged["stability_state"] = _higher_ranked_state(
        current.get("stability_state"),
        incoming.get("stability_state"),
        ranks=ARTIFACT_STABILITY_RANK,
    )
    merged["uploaded_at"] = _latest_non_null(
        current.get("uploaded_at"),
        incoming.get("uploaded_at"),
    )
    current_metadata = dict(current.get("raw_metadata") or {})
    incoming_metadata = {
        key: value
        for key, value in dict(incoming.get("raw_metadata") or {}).items()
        if key not in ARTIFACT_IMMUTABLE_METADATA_KEYS
    }
    merged["raw_metadata"] = {**current_metadata, **incoming_metadata}
    return merged


def merge_live_run_state(
    current: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> dict[str, Any]:
    """Model the lifecycle-sensitive fields in the live-run SQL upsert."""
    merged = {**current, **incoming}
    current_terminal = current.get("status") in TERMINAL_RUN_STATUSES
    publication_terminal = (
        current.get("canonical_publication_status")
        in TERMINAL_PUBLICATION_STATUSES
    )
    if current_terminal and incoming.get("status") != "finalized":
        merged["status"] = current.get("status")
    if current.get("status") == "finalized":
        merged["status"] = "finalized"
    if current_terminal:
        for field in ("finished_at", "benchmark_status", "returncode"):
            merged[field] = (
                current.get(field)
                if current.get(field) is not None
                else incoming.get(field)
            )
    if publication_terminal:
        for field in (
            "canonical_publication_status",
            "canonical_arm_run_id",
            "latest_message",
        ):
            merged[field] = current.get(field)
        current_metadata = dict(current.get("raw_metadata") or {})
        incoming_metadata = dict(incoming.get("raw_metadata") or {})
        if "publication_fingerprint" in current_metadata:
            incoming_metadata.pop("publication_fingerprint", None)
        merged["raw_metadata"] = {
            **current_metadata,
            **incoming_metadata,
        }
    for field in (
        "observed_cost_usd",
        "input_tokens",
        "cache_tokens",
        "output_tokens",
    ):
        merged[field] = _monotonic_nullable_number(
            current.get(field),
            incoming.get(field),
        )
    return merged


def merge_event_parent_state(
    current: Mapping[str, Any],
    event: Mapping[str, Any],
    *,
    inserted: bool,
) -> dict[str, Any]:
    """Model the monotonic parent-row effects of a newly inserted event."""
    merged = dict(current)
    if not inserted:
        return merged
    merged["event_count"] = max(
        int(current.get("event_count") or 0),
        int(event.get("sequence") or 0),
    )
    elapsed = event.get("elapsed_seconds")
    if elapsed is not None:
        merged["elapsed_seconds"] = max(
            float(current.get("elapsed_seconds") or 0),
            float(elapsed),
        )
    if event.get("event_type") == "heartbeat" and event.get("occurred_at"):
        merged["last_heartbeat_at"] = max(
            str(current.get("last_heartbeat_at") or ""),
            str(event["occurred_at"]),
        )
    terminal = (
        current.get("status") in TERMINAL_RUN_STATUSES
        or current.get("canonical_publication_status")
        in TERMINAL_PUBLICATION_STATUSES
    )
    if not terminal and event.get("message") is not None:
        merged["latest_message"] = event["message"]
    return merged


def insert_event_and_update_parent(
    cursor: Any,
    row: Mapping[str, Any],
    *,
    json_payload: Any,
) -> bool:
    cursor.execute(
        """
        insert into benchmark.live_run_events (
            live_run_id, sequence, event_type, occurred_at,
            elapsed_seconds, stream, message, payload
        ) values (
            %(live_run_id)s, %(sequence)s, %(event_type)s,
            %(occurred_at)s, %(elapsed_seconds)s, %(stream)s,
            %(message)s, %(payload)s
        )
        on conflict (live_run_id, sequence) do nothing
        """,
        {**row, "payload": json_payload},
    )
    if cursor.rowcount != 1:
        return False
    cursor.execute(
        """
        update benchmark.live_runs
        set event_count = greatest(event_count, %(sequence)s),
            last_heartbeat_at = case
                when %(event_type)s = 'heartbeat'
                    then greatest(last_heartbeat_at, %(occurred_at)s)
                else last_heartbeat_at
            end,
            latest_message = case
                when status in ('completed', 'failed', 'interrupted', 'finalized')
                  or canonical_publication_status in (
                      'completed', 'failed', 'ineligible'
                  )
                    then latest_message
                else coalesce(%(message)s, latest_message)
            end,
            elapsed_seconds = greatest(elapsed_seconds, %(elapsed_seconds)s),
            updated_at = now()
        where live_run_id = %(live_run_id)s
        """,
        row,
    )
    return True


class PostgresLiveStore:
    """Publish a mixed live batch in one transaction."""

    def __init__(self, db_url: str, *, process_output_retention: int = 500) -> None:
        if not db_url:
            raise ValueError("SUPABASE_DB_URL is required")
        if process_output_retention <= 0:
            raise ValueError("process_output_retention must be positive")
        self.db_url = db_url
        self.process_output_retention = process_output_retention

    def publish_batch(self, items: Sequence[PublicationItem]) -> None:
        if not items:
            return
        try:
            import psycopg
            from psycopg.types.json import Jsonb
        except ImportError as exc:  # pragma: no cover - exercised by CLI dependency setup
            raise RuntimeError("psycopg is required for live database publication") from exc

        grouped: dict[str, list[dict[str, Any]]] = {
            "run": [],
            "event": [],
            "trial": [],
            "artifact": [],
        }
        for item in items:
            if item.kind not in grouped:
                raise ValueError(f"unsupported live publication kind: {item.kind}")
            grouped[item.kind].append(item.payload)

        with psycopg.connect(self.db_url) as connection:
            with connection.cursor() as cursor:
                for row in grouped["run"]:
                    cursor.execute(
                        """
                        insert into benchmark.live_runs (
                            live_run_id, github_run_id, github_run_attempt, github_job,
                            runner_name, workspace_name, workspace_fingerprint, arm_id,
                            phase, mode, run_kind, scored, status, benchmark_status,
                            live_publication_status, progressive_artifact_status,
                            canonical_publication_status, command_summary,
                            expected_trial_count, completed_trial_count, success_count,
                            failure_count, exception_count, observed_cost_usd,
                            input_tokens, cache_tokens, output_tokens, started_at,
                            finished_at, last_heartbeat_at, elapsed_seconds, returncode,
                            event_count, latest_message, canonical_arm_run_id,
                            raw_metadata, updated_at
                        ) values (
                            %(live_run_id)s, %(github_run_id)s, %(github_run_attempt)s,
                            %(github_job)s, %(runner_name)s, %(workspace_name)s,
                            %(workspace_fingerprint)s, %(arm_id)s, %(phase)s, %(mode)s,
                            %(run_kind)s, %(scored)s, %(status)s, %(benchmark_status)s,
                            %(live_publication_status)s, %(progressive_artifact_status)s,
                            %(canonical_publication_status)s, %(command_summary)s,
                            %(expected_trial_count)s, %(completed_trial_count)s,
                            %(success_count)s, %(failure_count)s, %(exception_count)s,
                            %(observed_cost_usd)s, %(input_tokens)s, %(cache_tokens)s,
                            %(output_tokens)s, %(started_at)s, %(finished_at)s,
                            %(last_heartbeat_at)s, %(elapsed_seconds)s, %(returncode)s,
                            %(event_count)s, %(latest_message)s, %(canonical_arm_run_id)s,
                            %(raw_metadata)s, now()
                        )
                        on conflict (live_run_id) do update set
                            github_run_id = coalesce(excluded.github_run_id, benchmark.live_runs.github_run_id),
                            github_run_attempt = coalesce(excluded.github_run_attempt, benchmark.live_runs.github_run_attempt),
                            github_job = coalesce(excluded.github_job, benchmark.live_runs.github_job),
                            runner_name = coalesce(excluded.runner_name, benchmark.live_runs.runner_name),
                            workspace_name = coalesce(excluded.workspace_name, benchmark.live_runs.workspace_name),
                            workspace_fingerprint = coalesce(excluded.workspace_fingerprint, benchmark.live_runs.workspace_fingerprint),
                            status = case
                                when benchmark.live_runs.status = 'finalized'
                                    then benchmark.live_runs.status
                                when benchmark.live_runs.status in (
                                    'completed', 'failed', 'interrupted'
                                ) and excluded.status <> 'finalized'
                                    then benchmark.live_runs.status
                                else excluded.status
                            end,
                            benchmark_status = case
                                when benchmark.live_runs.status in (
                                    'completed', 'failed', 'interrupted', 'finalized'
                                ) and benchmark.live_runs.benchmark_status is not null
                                    then benchmark.live_runs.benchmark_status
                                else coalesce(
                                    excluded.benchmark_status,
                                    benchmark.live_runs.benchmark_status
                                )
                            end,
                            live_publication_status = case
                                when benchmark.live_runs.live_publication_status in (
                                    'completed', 'failed', 'degraded'
                                ) then benchmark.live_runs.live_publication_status
                                else coalesce(
                                    excluded.live_publication_status,
                                    benchmark.live_runs.live_publication_status
                                )
                            end,
                            progressive_artifact_status = case
                                when benchmark.live_runs.progressive_artifact_status in (
                                    'completed', 'failed', 'degraded'
                                ) then benchmark.live_runs.progressive_artifact_status
                                else coalesce(
                                    excluded.progressive_artifact_status,
                                    benchmark.live_runs.progressive_artifact_status
                                )
                            end,
                            canonical_publication_status = case
                                when benchmark.live_runs.canonical_publication_status in (
                                    'completed', 'failed', 'ineligible'
                                ) then benchmark.live_runs.canonical_publication_status
                                else coalesce(
                                    excluded.canonical_publication_status,
                                    benchmark.live_runs.canonical_publication_status
                                )
                            end,
                            command_summary = case
                                when excluded.command_summary = '{}'::jsonb then benchmark.live_runs.command_summary
                                else excluded.command_summary
                            end,
                            expected_trial_count = coalesce(excluded.expected_trial_count, benchmark.live_runs.expected_trial_count),
                            completed_trial_count = greatest(excluded.completed_trial_count, benchmark.live_runs.completed_trial_count),
                            success_count = greatest(excluded.success_count, benchmark.live_runs.success_count),
                            failure_count = greatest(excluded.failure_count, benchmark.live_runs.failure_count),
                            exception_count = greatest(excluded.exception_count, benchmark.live_runs.exception_count),
                            observed_cost_usd = case
                                when benchmark.live_runs.observed_cost_usd is null
                                    then excluded.observed_cost_usd
                                when excluded.observed_cost_usd is null
                                    then benchmark.live_runs.observed_cost_usd
                                else greatest(
                                    excluded.observed_cost_usd,
                                    benchmark.live_runs.observed_cost_usd
                                )
                            end,
                            input_tokens = case
                                when benchmark.live_runs.input_tokens is null
                                    then excluded.input_tokens
                                when excluded.input_tokens is null
                                    then benchmark.live_runs.input_tokens
                                else greatest(
                                    excluded.input_tokens,
                                    benchmark.live_runs.input_tokens
                                )
                            end,
                            cache_tokens = case
                                when benchmark.live_runs.cache_tokens is null
                                    then excluded.cache_tokens
                                when excluded.cache_tokens is null
                                    then benchmark.live_runs.cache_tokens
                                else greatest(
                                    excluded.cache_tokens,
                                    benchmark.live_runs.cache_tokens
                                )
                            end,
                            output_tokens = case
                                when benchmark.live_runs.output_tokens is null
                                    then excluded.output_tokens
                                when excluded.output_tokens is null
                                    then benchmark.live_runs.output_tokens
                                else greatest(
                                    excluded.output_tokens,
                                    benchmark.live_runs.output_tokens
                                )
                            end,
                            finished_at = case
                                when benchmark.live_runs.status in (
                                    'completed', 'failed', 'interrupted', 'finalized'
                                ) and benchmark.live_runs.finished_at is not null
                                    then benchmark.live_runs.finished_at
                                else coalesce(
                                    excluded.finished_at,
                                    benchmark.live_runs.finished_at
                                )
                            end,
                            last_heartbeat_at = greatest(excluded.last_heartbeat_at, benchmark.live_runs.last_heartbeat_at),
                            elapsed_seconds = greatest(excluded.elapsed_seconds, benchmark.live_runs.elapsed_seconds),
                            returncode = case
                                when benchmark.live_runs.status in (
                                    'completed', 'failed', 'interrupted', 'finalized'
                                ) and benchmark.live_runs.returncode is not null
                                    then benchmark.live_runs.returncode
                                else coalesce(
                                    excluded.returncode,
                                    benchmark.live_runs.returncode
                                )
                            end,
                            event_count = greatest(excluded.event_count, benchmark.live_runs.event_count),
                            latest_message = case
                                when benchmark.live_runs.status in (
                                    'completed', 'failed', 'interrupted', 'finalized'
                                )
                                  or benchmark.live_runs.canonical_publication_status in (
                                      'completed', 'failed', 'ineligible'
                                  )
                                    then benchmark.live_runs.latest_message
                                else coalesce(
                                    excluded.latest_message,
                                    benchmark.live_runs.latest_message
                                )
                            end,
                            canonical_arm_run_id = case
                                when benchmark.live_runs.canonical_publication_status in (
                                    'completed', 'failed', 'ineligible'
                                ) then benchmark.live_runs.canonical_arm_run_id
                                else coalesce(
                                    excluded.canonical_arm_run_id,
                                    benchmark.live_runs.canonical_arm_run_id
                                )
                            end,
                            raw_metadata = case
                                when benchmark.live_runs.canonical_publication_status in (
                                    'completed', 'failed', 'ineligible'
                                ) then benchmark.live_runs.raw_metadata
                                    || (excluded.raw_metadata - 'publication_fingerprint')
                                else benchmark.live_runs.raw_metadata
                                    || excluded.raw_metadata
                            end,
                            updated_at = now()
                        """,
                        {
                            **_run_defaults(row),
                            "command_summary": Jsonb(row.get("command_summary") or {}),
                            "raw_metadata": Jsonb(row.get("raw_metadata") or {}),
                        },
                    )

                event_run_ids: set[str] = set()
                for row in grouped["event"]:
                    inserted = insert_event_and_update_parent(
                        cursor,
                        row,
                        json_payload=Jsonb(row.get("payload") or {}),
                    )
                    if inserted:
                        event_run_ids.add(str(row["live_run_id"]))
                for live_run_id in event_run_ids:
                    cursor.execute(
                        """
                        delete from benchmark.live_run_events
                        where id in (
                            select id
                            from benchmark.live_run_events
                            where live_run_id = %s
                              and event_type = 'process_output_chunk'
                            order by sequence desc
                            offset %s
                        )
                        """,
                        (live_run_id, self.process_output_retention),
                    )

                for row in grouped["trial"]:
                    trial_values = _trial_defaults(row)
                    trial_values["status"] = (
                        trial_values.get("status") or "detected"
                    )
                    trial_values["stability_state"] = (
                        trial_values.get("stability_state") or "observed"
                    )
                    cursor.execute(
                        """
                        insert into benchmark.live_trials (
                            live_run_id, trial_key, task_id, attempt_index, status,
                            reward, exception_type, exception_summary, runtime_seconds,
                            input_tokens, cache_tokens, output_tokens, cost_usd,
                            started_at, finished_at, relative_local_path,
                            stability_state, completion_evidence, raw_result, updated_at
                        ) values (
                            %(live_run_id)s, %(trial_key)s, %(task_id)s,
                            %(attempt_index)s, %(status)s, %(reward)s,
                            %(exception_type)s, %(exception_summary)s,
                            %(runtime_seconds)s, %(input_tokens)s, %(cache_tokens)s,
                            %(output_tokens)s, %(cost_usd)s, %(started_at)s,
                            %(finished_at)s, %(relative_local_path)s,
                            %(stability_state)s, %(completion_evidence)s,
                            %(raw_result)s, now()
                        )
                        on conflict (live_run_id, trial_key) do update set
                            task_id = coalesce(
                                benchmark.live_trials.task_id,
                                excluded.task_id
                            ),
                            attempt_index = coalesce(
                                benchmark.live_trials.attempt_index,
                                excluded.attempt_index
                            ),
                            status = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.status
                                else coalesce(
                                    case
                                        when %(has_status)s::boolean
                                            then excluded.status
                                        else null
                                    end,
                                    benchmark.live_trials.status
                                )
                            end,
                            reward = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.reward
                                else coalesce(
                                    excluded.reward,
                                    benchmark.live_trials.reward
                                )
                            end,
                            exception_type = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.exception_type
                                else coalesce(
                                    excluded.exception_type,
                                    benchmark.live_trials.exception_type
                                )
                            end,
                            exception_summary = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.exception_summary
                                else coalesce(
                                    excluded.exception_summary,
                                    benchmark.live_trials.exception_summary
                                )
                            end,
                            runtime_seconds = case
                                when benchmark.live_trials.runtime_seconds is null
                                    then excluded.runtime_seconds
                                when excluded.runtime_seconds is null
                                    then benchmark.live_trials.runtime_seconds
                                else greatest(
                                    benchmark.live_trials.runtime_seconds,
                                    excluded.runtime_seconds
                                )
                            end,
                            input_tokens = case
                                when benchmark.live_trials.input_tokens is null
                                    then excluded.input_tokens
                                when excluded.input_tokens is null
                                    then benchmark.live_trials.input_tokens
                                else greatest(
                                    benchmark.live_trials.input_tokens,
                                    excluded.input_tokens
                                )
                            end,
                            cache_tokens = case
                                when benchmark.live_trials.cache_tokens is null
                                    then excluded.cache_tokens
                                when excluded.cache_tokens is null
                                    then benchmark.live_trials.cache_tokens
                                else greatest(
                                    benchmark.live_trials.cache_tokens,
                                    excluded.cache_tokens
                                )
                            end,
                            output_tokens = case
                                when benchmark.live_trials.output_tokens is null
                                    then excluded.output_tokens
                                when excluded.output_tokens is null
                                    then benchmark.live_trials.output_tokens
                                else greatest(
                                    benchmark.live_trials.output_tokens,
                                    excluded.output_tokens
                                )
                            end,
                            cost_usd = case
                                when benchmark.live_trials.cost_usd is null
                                    then excluded.cost_usd
                                when excluded.cost_usd is null
                                    then benchmark.live_trials.cost_usd
                                else greatest(
                                    benchmark.live_trials.cost_usd,
                                    excluded.cost_usd
                                )
                            end,
                            started_at = case
                                when benchmark.live_trials.started_at is null
                                    then excluded.started_at
                                when excluded.started_at is null
                                    then benchmark.live_trials.started_at
                                else least(
                                    benchmark.live_trials.started_at,
                                    excluded.started_at
                                )
                            end,
                            finished_at = case
                                when benchmark.live_trials.finished_at is null
                                    then excluded.finished_at
                                when excluded.finished_at is null
                                    then benchmark.live_trials.finished_at
                                else greatest(
                                    benchmark.live_trials.finished_at,
                                    excluded.finished_at
                                )
                            end,
                            relative_local_path = coalesce(
                                benchmark.live_trials.relative_local_path,
                                excluded.relative_local_path
                            ),
                            stability_state = case
                                when benchmark.live_trials.stability_state = 'complete'
                                  or excluded.stability_state = 'complete'
                                    then 'complete'
                                else benchmark.live_trials.stability_state
                            end,
                            completion_evidence = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.completion_evidence
                                when %(has_completion_evidence)s::boolean
                                    then excluded.completion_evidence
                                else benchmark.live_trials.completion_evidence
                            end,
                            raw_result = case
                                when benchmark.live_trials.finished_at is not null
                                  and (
                                      excluded.finished_at is null
                                      or excluded.finished_at
                                          <= benchmark.live_trials.finished_at
                                  )
                                    then benchmark.live_trials.raw_result
                                when %(has_raw_result)s::boolean
                                    then excluded.raw_result
                                else benchmark.live_trials.raw_result
                            end,
                            updated_at = now()
                        """,
                        {
                            **trial_values,
                            "has_status": row.get("status") is not None,
                            "has_completion_evidence": (
                                row.get("completion_evidence") is not None
                            ),
                            "has_raw_result": row.get("raw_result") is not None,
                            "completion_evidence": Jsonb(row.get("completion_evidence") or {}),
                            "raw_result": Jsonb(row.get("raw_result") or {}),
                        },
                    )

                for row in grouped["artifact"]:
                    artifact_values = _artifact_defaults(row)
                    artifact_values["stability_state"] = (
                        artifact_values.get("stability_state") or "stable"
                    )
                    cursor.execute(
                        """
                        insert into benchmark.live_artifacts (
                            live_run_id, trial_key, artifact_type,
                            relative_local_path, r2_uri, sha256, size_bytes,
                            stability_state, uploaded_at, raw_metadata, updated_at
                        ) values (
                            %(live_run_id)s, %(trial_key)s, %(artifact_type)s,
                            %(relative_local_path)s, %(r2_uri)s, %(sha256)s,
                            %(size_bytes)s, %(stability_state)s, %(uploaded_at)s,
                            %(raw_metadata)s, now()
                        )
                        on conflict (
                            live_run_id,
                            (coalesce(trial_key, '')),
                            relative_local_path,
                            sha256
                        ) do update set
                            r2_uri = coalesce(
                                benchmark.live_artifacts.r2_uri,
                                excluded.r2_uri
                            ),
                            stability_state = case
                                when benchmark.live_artifacts.stability_state = 'uploaded'
                                  or excluded.stability_state = 'uploaded'
                                    then 'uploaded'
                                when benchmark.live_artifacts.stability_state = 'stable'
                                  or excluded.stability_state = 'stable'
                                    then 'stable'
                                else 'observed'
                            end,
                            uploaded_at = case
                                when benchmark.live_artifacts.uploaded_at is null
                                    then excluded.uploaded_at
                                when excluded.uploaded_at is null
                                    then benchmark.live_artifacts.uploaded_at
                                else greatest(
                                    benchmark.live_artifacts.uploaded_at,
                                    excluded.uploaded_at
                                )
                            end,
                            raw_metadata = benchmark.live_artifacts.raw_metadata
                                || (
                                    excluded.raw_metadata
                                    - array[
                                        'live_run_id',
                                        'trial_key',
                                        'artifact_type',
                                        'relative_local_path',
                                        'r2_uri',
                                        'sha256',
                                        'size_bytes',
                                        'stability_state',
                                        'uploaded_at'
                                    ]::text[]
                                ),
                            updated_at = now()
                        where benchmark.live_artifacts.r2_uri is null
                           or excluded.r2_uri is null
                           or benchmark.live_artifacts.r2_uri = excluded.r2_uri
                        """,
                        {
                            **artifact_values,
                            "raw_metadata": Jsonb(row.get("raw_metadata") or {}),
                        },
                    )
                    if row.get("r2_uri") is not None and cursor.rowcount != 1:
                        raise LiveArtifactConflict(
                            "conflicting R2 URI for immutable live artifact identity"
                        )


def reconcile_database_spool(
    spool_path: Path,
    store: LiveStore,
    *,
    workspace: Path | None = None,
) -> dict[str, int]:
    """Replay bounded spooled batches, retaining any rows that still fail."""
    if workspace is not None:
        spool_path = ensure_workspace_output_path(
            spool_path,
            workspace=workspace,
            label="database spool",
        )
    if not spool_path.is_file():
        return {"reconciled_items": 0, "remaining_items": 0}
    reconciled_items = 0
    remaining_items = 0
    has_remaining = False
    temporary = spool_path.with_suffix(spool_path.suffix + ".tmp")
    if workspace is not None:
        temporary = ensure_workspace_output_path(
            temporary,
            workspace=workspace,
            label="temporary database spool",
        )
    with (
        spool_path.open("r", encoding="utf-8") as source,
        temporary.open("w", encoding="utf-8") as destination,
    ):
        for line in source:
            record: Any = None
            try:
                record = json.loads(line)
                items = [
                    PublicationItem(kind=str(item["kind"]), payload=dict(item["payload"]))
                    for item in record.get("items") or []
                ]
                store.publish_batch(items)
                reconciled_items += len(items)
            except Exception:
                has_remaining = True
                destination.write(line if line.endswith("\n") else line + "\n")
                remaining_items += (
                    len(record.get("items") or []) if isinstance(record, Mapping) else 1
                )
    if has_remaining:
        temporary.replace(spool_path)
    else:
        temporary.unlink(missing_ok=True)
        spool_path.unlink(missing_ok=True)
    return {
        "reconciled_items": reconciled_items,
        "remaining_items": remaining_items,
    }


def _run_defaults(row: Mapping[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "github_run_id": None,
        "github_run_attempt": None,
        "github_job": None,
        "runner_name": None,
        "workspace_name": None,
        "workspace_fingerprint": None,
        "run_kind": "unknown",
        "scored": False,
        "status": "running",
        "benchmark_status": None,
        "live_publication_status": None,
        "progressive_artifact_status": None,
        "canonical_publication_status": None,
        "command_summary": {},
        "expected_trial_count": None,
        "completed_trial_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "exception_count": 0,
        "observed_cost_usd": None,
        "input_tokens": None,
        "cache_tokens": None,
        "output_tokens": None,
        "started_at": utc_now(),
        "finished_at": None,
        "last_heartbeat_at": None,
        "elapsed_seconds": None,
        "returncode": None,
        "event_count": 0,
        "latest_message": None,
        "canonical_arm_run_id": None,
        "raw_metadata": {},
    }
    return {**defaults, **dict(row)}


def _trial_defaults(row: Mapping[str, Any]) -> dict[str, Any]:
    defaults = {
        "task_id": None,
        "attempt_index": None,
        "status": "detected",
        "reward": None,
        "exception_type": None,
        "exception_summary": None,
        "runtime_seconds": None,
        "input_tokens": None,
        "cache_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "started_at": None,
        "finished_at": None,
        "relative_local_path": None,
        "stability_state": "observed",
        "completion_evidence": {},
        "raw_result": {},
    }
    return {**defaults, **dict(row)}


def _artifact_defaults(row: Mapping[str, Any]) -> dict[str, Any]:
    defaults = {
        "trial_key": None,
        "r2_uri": None,
        "stability_state": "stable",
        "uploaded_at": None,
        "raw_metadata": {},
    }
    return {**defaults, **dict(row)}


class BatchedDatabasePublisher:
    """Best-effort background publisher with a durable local failure spool."""

    def __init__(
        self,
        *,
        store: LiveStore,
        spool_path: Path,
        batch_size: int = 75,
        flush_seconds: float = 7.5,
        queue_size: int = 1_000,
        warning_callback: Callable[[str], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        redactor: Redactor | None = None,
        workspace: Path | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if flush_seconds <= 0:
            raise ValueError("flush_seconds must be positive")
        self.store = store
        self.workspace = workspace
        if workspace is None:
            self.spool_path = spool_path
            self.spool_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.spool_path = ensure_workspace_output_path(
                spool_path,
                workspace=workspace,
                create_parent=True,
                label="database spool",
            )
        self.batch_size = batch_size
        self.flush_seconds = flush_seconds
        self.queue = BoundedQueue(queue_size)
        self.warning_callback = warning_callback
        self.sleep = sleep
        self.redactor = redactor or Redactor.from_environment()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.published_count = 0
        self.failed_count = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="live-db-publisher", daemon=True)
        self._thread.start()

    def submit(self, kind: str, payload: Mapping[str, Any]) -> bool:
        accepted = self.queue.offer(
            PublicationItem(kind=kind, payload=self.redactor.value(dict(payload)))
        )
        if not accepted:
            self._warn("live publication queue full; item preserved only in local evidence")
        return accepted

    def submit_run(self, payload: Mapping[str, Any]) -> bool:
        return self.submit("run", payload)

    def submit_event(self, event: Mapping[str, Any]) -> bool:
        payload = {
            key: event.get(key)
            for key in (
                "live_run_id",
                "sequence",
                "event_type",
                "occurred_at",
                "elapsed_seconds",
                "stream",
                "message",
                "payload",
            )
        }
        return self.submit("event", payload)

    def submit_trial(self, payload: Mapping[str, Any]) -> bool:
        return self.submit("trial", payload)

    def submit_artifact(self, payload: Mapping[str, Any]) -> bool:
        return self.submit("artifact", payload)

    def _run(self) -> None:
        batch: list[PublicationItem] = []
        deadline = time.monotonic() + self.flush_seconds
        while not self._stop.is_set() or self.queue.size or batch:
            timeout = max(min(deadline - time.monotonic(), 0.5), 0.0)
            try:
                batch.append(self.queue.get(timeout=timeout))
            except queue.Empty:
                pass
            batch.extend(self.queue.drain(max(self.batch_size - len(batch), 0)))
            if batch and (len(batch) >= self.batch_size or time.monotonic() >= deadline or self._stop.is_set()):
                self._publish(batch)
                batch = []
                deadline = time.monotonic() + self.flush_seconds

    def _publish(self, items: Sequence[PublicationItem]) -> None:
        last_error: Exception | None = None
        for retry_delay in (*bounded_backoff_delays(), None):
            try:
                self.store.publish_batch(items)
                self.published_count += len(items)
                return
            except Exception as exc:  # publication must never terminate Harbor
                last_error = exc
                if retry_delay is not None and not self._stop.is_set():
                    self.sleep(retry_delay)
        self.failed_count += len(items)
        self._spool(items, last_error)
        self._warn(f"live database batch failed; {len(items)} item(s) spooled for reconciliation")

    def _spool(self, items: Sequence[PublicationItem], error: Exception | None) -> None:
        record = {
            "spooled_at": utc_now(),
            "error_type": type(error).__name__ if error else "UnknownError",
            "items": [{"kind": item.kind, "payload": item.payload} for item in items],
        }
        spool_path = self.spool_path
        if self.workspace is not None:
            spool_path = ensure_workspace_output_path(
                spool_path,
                workspace=self.workspace,
                label="database spool",
            )
        with spool_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    def _warn(self, message: str) -> None:
        if self.warning_callback:
            self.warning_callback(message)

    def stop(self, *, timeout: float = 10.0) -> bool:
        self._stop.set()
        if self._thread is None:
            return True
        self._thread.join(timeout=max(timeout, 0.0))
        return not self._thread.is_alive()
