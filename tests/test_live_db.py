from __future__ import annotations

import json
import inspect
from pathlib import Path

import pytest

from scripts.lib.live_db import (
    BatchedDatabasePublisher,
    LiveArtifactConflict,
    PostgresLiveStore,
    PublicationItem,
    insert_event_and_update_parent,
    merge_live_artifact_state,
    merge_event_parent_state,
    merge_live_run_state,
    merge_live_trial_state,
    reconcile_database_spool,
)
from scripts.lib.live_events import LocalEventWriter, Redactor
from scripts.lib.live_verification import publication_transition


class FakeStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.batches: list[list[PublicationItem]] = []

    def publish_batch(self, items: list[PublicationItem]) -> None:
        self.batches.append(list(items))
        if self.fail:
            raise ConnectionError("synthetic database outage")


def test_database_publisher_batches_items(tmp_path: Path) -> None:
    store = FakeStore()
    publisher = BatchedDatabasePublisher(
        store=store,
        spool_path=tmp_path / "spool.ndjson",
        batch_size=10,
        flush_seconds=60,
        sleep=lambda _seconds: None,
    )
    publisher.start()
    publisher.submit_run({"live_run_id": "live-test", "arm_id": "arm"})
    publisher.submit_event(
        {
            "live_run_id": "live-test",
            "sequence": 1,
            "event_type": "heartbeat",
            "occurred_at": "2026-07-28T00:00:00+00:00",
            "payload": {},
        }
    )
    assert publisher.stop(timeout=2)

    assert len(store.batches) == 1
    assert [item.kind for item in store.batches[0]] == ["run", "event"]
    assert publisher.published_count == 2


def test_database_failure_preserves_local_evidence_and_spools(tmp_path: Path) -> None:
    store = FakeStore(fail=True)
    redactor = Redactor(["database-secret-value"])
    writer = LocalEventWriter(
        live_run_id="live-outage",
        out_dir=tmp_path / "live",
        metadata={"arm_id": "router-test"},
        redactor=redactor,
    )
    publisher = BatchedDatabasePublisher(
        store=store,
        spool_path=tmp_path / "live" / "spool.ndjson",
        batch_size=10,
        flush_seconds=60,
        sleep=lambda _seconds: None,
        redactor=redactor,
    )
    writer.set_sink(publisher.submit_event)
    publisher.start()
    writer.emit("process_output_chunk", message="password=database-secret-value")
    assert publisher.stop(timeout=2)
    writer.close()

    assert writer.event_path.is_file()
    assert publisher.failed_count == 1
    spool = json.loads((tmp_path / "live" / "spool.ndjson").read_text().splitlines()[0])
    assert spool["error_type"] == "ConnectionError"
    serialized = json.dumps(spool)
    assert "database-secret-value" not in serialized


def test_database_spool_reconciles_in_bounded_batches(tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.ndjson"
    records = [
        {
            "items": [
                {"kind": "run", "payload": {"live_run_id": "live-test", "sequence": index}}
            ]
        }
        for index in range(2)
    ]
    spool_path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    store = FakeStore()

    result = reconcile_database_spool(spool_path, store)

    assert result == {"reconciled_items": 2, "remaining_items": 0}
    assert len(store.batches) == 2
    assert not spool_path.exists()


def test_runtime_file_secret_absent_from_database_payload_and_spool(
    tmp_path: Path,
) -> None:
    secret = "opaque-provider-format::%/with spaces"
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "provider.env").write_text(f"STRANGE_LOGIN={json.dumps(secret)}\n")
    redactor = Redactor.from_runtime_sources(tmp_path, env={})
    store = FakeStore(fail=True)
    writer = LocalEventWriter(
        live_run_id="live-file-secret",
        out_dir=tmp_path / ".run" / "live",
        metadata={},
        redactor=redactor,
    )
    publisher = BatchedDatabasePublisher(
        store=store,
        spool_path=tmp_path / ".run" / "live" / "spool.ndjson",
        batch_size=10,
        flush_seconds=60,
        sleep=lambda _seconds: None,
        redactor=redactor,
    )
    writer.set_sink(publisher.submit_event)
    publisher.start()
    writer.emit("process_output_chunk", message=f"provider said {secret}")
    assert publisher.stop(timeout=2)
    writer.close()

    assert secret not in writer.event_path.read_text()
    assert secret not in json.dumps(
        [
            {"kind": item.kind, "payload": item.payload}
            for batch in store.batches
            for item in batch
        ]
    )
    assert secret not in (tmp_path / ".run" / "live" / "spool.ndjson").read_text()


def test_live_run_upsert_preserves_terminal_lifecycle_and_publication_states() -> None:
    sql = inspect.getsource(PostgresLiveStore.publish_batch)
    assert "benchmark.live_runs.status = 'finalized'" in sql
    assert "'completed', 'failed', 'interrupted'" in sql
    assert "excluded.status <> 'finalized'" in sql
    assert "canonical_publication_status in (" in sql
    assert "'completed', 'failed'" in sql
    assert "greatest(\n                                    excluded.observed_cost_usd" in sql
    assert "greatest(\n                                    excluded.input_tokens" in sql
    assert "benchmark.live_runs.finished_at is not null" in sql
    assert "benchmark.live_runs.canonical_arm_run_id" in sql

    assert publication_transition("pending", "publishing") == "publishing"
    assert publication_transition("failed", "publishing") == "failed"
    assert (
        publication_transition("failed", "publishing", explicit_retry=True)
        == "publishing"
    )
    assert publication_transition("completed", "publishing", explicit_retry=True) == (
        "completed"
    )
    assert (
        publication_transition("ineligible", "publishing", explicit_retry=True)
        == "ineligible"
    )


def test_live_run_numeric_totals_are_monotonic_with_null_semantics() -> None:
    current = {
        "status": "running",
        "observed_cost_usd": 4.5,
        "input_tokens": 100,
        "cache_tokens": None,
        "output_tokens": 50,
    }
    stale = merge_live_run_state(
        current,
        {
            "status": "running",
            "observed_cost_usd": 3.0,
            "input_tokens": 90,
            "cache_tokens": None,
            "output_tokens": None,
        },
    )
    assert stale["observed_cost_usd"] == 4.5
    assert stale["input_tokens"] == 100
    assert stale["cache_tokens"] is None
    assert stale["output_tokens"] == 50

    newer = merge_live_run_state(
        current,
        {
            "status": "running",
            "observed_cost_usd": 5.0,
            "input_tokens": 110,
            "cache_tokens": 25,
            "output_tokens": 75,
        },
    )
    assert newer["observed_cost_usd"] == 5.0
    assert newer["input_tokens"] == 110
    assert newer["cache_tokens"] == 25
    assert newer["output_tokens"] == 75


def test_stale_live_upsert_preserves_terminal_and_failed_publication_fields() -> None:
    current = {
        "status": "failed",
        "finished_at": "2026-07-28T12:00:10Z",
        "benchmark_status": "failed",
        "returncode": 17,
        "canonical_publication_status": "failed",
        "canonical_arm_run_id": "original-arm-run",
        "latest_message": "Canonical publication failed",
    }
    merged = merge_live_run_state(
        current,
        {
            "status": "running",
            "finished_at": None,
            "benchmark_status": "running",
            "returncode": None,
            "canonical_publication_status": "pending",
            "canonical_arm_run_id": "stale-arm-run",
            "latest_message": "old process output",
        },
    )
    assert merged["status"] == "failed"
    assert merged["finished_at"] == current["finished_at"]
    assert merged["benchmark_status"] == "failed"
    assert merged["returncode"] == 17
    assert merged["canonical_publication_status"] == "failed"
    assert merged["canonical_arm_run_id"] == "original-arm-run"
    assert merged["latest_message"] == "Canonical publication failed"


def test_stale_live_upsert_preserves_ineligible_publication_diagnostics() -> None:
    current = {
        "status": "completed",
        "canonical_publication_status": "ineligible",
        "canonical_arm_run_id": "existing-arm-run",
        "latest_message": "Expected trial count did not match",
        "raw_metadata": {
            "publication_fingerprint": "original-fingerprint",
            "eligibility": "ineligible",
        },
    }
    merged = merge_live_run_state(
        current,
        {
            "status": "running",
            "canonical_publication_status": "pending",
            "canonical_arm_run_id": "stale-arm-run",
            "latest_message": "old process output",
            "raw_metadata": {
                "publication_fingerprint": "stale-fingerprint",
                "replayed": True,
            },
        },
    )
    assert merged["canonical_publication_status"] == "ineligible"
    assert merged["canonical_arm_run_id"] == "existing-arm-run"
    assert merged["latest_message"] == "Expected trial count did not match"
    assert (
        merged["raw_metadata"]["publication_fingerprint"]
        == "original-fingerprint"
    )
    assert merged["raw_metadata"]["replayed"] is True

    sql = inspect.getsource(PostgresLiveStore.publish_batch)
    assert "'completed', 'failed', 'ineligible'" in sql
    assert "excluded.raw_metadata - 'publication_fingerprint'" in sql


def terminal_trial(**updates: object) -> dict[str, object]:
    return {
        "live_run_id": "live-test",
        "trial_key": "task-one__abc",
        "task_id": "task-one",
        "attempt_index": 1,
        "relative_local_path": "task-one__abc",
        "status": "completed",
        "reward": 1,
        "exception_type": None,
        "exception_summary": None,
        "runtime_seconds": 20.0,
        "input_tokens": 100,
        "cache_tokens": 40,
        "output_tokens": 25,
        "cost_usd": 2.0,
        "started_at": "2026-07-28T12:00:00Z",
        "finished_at": "2026-07-28T12:00:20Z",
        "stability_state": "complete",
        "completion_evidence": {"final": True},
        "raw_result": {"reward": 1},
        **updates,
    }


@pytest.mark.parametrize(
    "incoming_finished_at",
    ["2026-07-28T12:00:19Z", "2026-07-28T12:00:20Z"],
)
def test_stale_or_equal_trial_replay_cannot_replace_terminal_evidence(
    incoming_finished_at: str,
) -> None:
    current = terminal_trial()
    merged = merge_live_trial_state(
        current,
        terminal_trial(
            task_id="different-task",
            attempt_index=2,
            relative_local_path="different",
            live_run_id="different-live",
            trial_key="different-trial",
            status="failed",
            reward=0,
            exception_type="OldError",
            exception_summary="stale",
            runtime_seconds=10.0,
            input_tokens=50,
            cache_tokens=20,
            output_tokens=10,
            cost_usd=1.0,
            started_at="2026-07-28T12:00:05Z",
            finished_at=incoming_finished_at,
            stability_state="observed",
            completion_evidence={"final": False},
            raw_result={"reward": 0},
        ),
    )
    assert merged["status"] == "completed"
    assert merged["reward"] == 1
    assert merged["exception_type"] is None
    assert merged["completion_evidence"] == {"final": True}
    assert merged["raw_result"] == {"reward": 1}
    assert merged["finished_at"] == current["finished_at"]
    assert merged["started_at"] == current["started_at"]
    assert merged["task_id"] == "task-one"
    assert merged["live_run_id"] == "live-test"
    assert merged["trial_key"] == "task-one__abc"
    assert merged["attempt_index"] == 1
    assert merged["relative_local_path"] == "task-one__abc"
    assert merged["stability_state"] == "complete"


def test_genuinely_newer_trial_evidence_replaces_terminal_observation() -> None:
    merged = merge_live_trial_state(
        terminal_trial(),
        terminal_trial(
            status="failed",
            reward=0,
            exception_type="NewError",
            exception_summary="newer",
            runtime_seconds=25.0,
            input_tokens=120,
            cache_tokens=45,
            output_tokens=30,
            cost_usd=2.5,
            finished_at="2026-07-28T12:00:25Z",
            completion_evidence={"final": True, "newer": True},
            raw_result={"exception": "NewError"},
        ),
    )
    assert merged["status"] == "failed"
    assert merged["reward"] == 0
    assert merged["exception_type"] == "NewError"
    assert merged["completion_evidence"]["newer"] is True
    assert merged["raw_result"] == {"exception": "NewError"}
    assert merged["finished_at"] == "2026-07-28T12:00:25Z"
    assert merged["runtime_seconds"] == 25.0
    assert merged["input_tokens"] == 120
    assert merged["cost_usd"] == 2.5


def test_trial_numeric_fields_are_monotonic_and_null_safe() -> None:
    current = terminal_trial()
    lower = merge_live_trial_state(
        current,
        terminal_trial(
            runtime_seconds=1.0,
            input_tokens=1,
            cache_tokens=1,
            output_tokens=1,
            cost_usd=0.1,
        ),
    )
    for field in (
        "runtime_seconds",
        "input_tokens",
        "cache_tokens",
        "output_tokens",
        "cost_usd",
    ):
        assert lower[field] == current[field]

    higher = merge_live_trial_state(
        current,
        terminal_trial(
            runtime_seconds=30.0,
            input_tokens=130,
            cache_tokens=50,
            output_tokens=35,
            cost_usd=3.0,
        ),
    )
    assert higher["runtime_seconds"] == 30.0
    assert higher["input_tokens"] == 130
    assert higher["cache_tokens"] == 50
    assert higher["output_tokens"] == 35
    assert higher["cost_usd"] == 3.0

    incoming_null = merge_live_trial_state(
        current,
        terminal_trial(
            runtime_seconds=None,
            input_tokens=None,
            cache_tokens=None,
            output_tokens=None,
            cost_usd=None,
        ),
    )
    for field in (
        "runtime_seconds",
        "input_tokens",
        "cache_tokens",
        "output_tokens",
        "cost_usd",
    ):
        assert incoming_null[field] == current[field]


def test_newer_trial_null_evidence_does_not_erase_existing_values() -> None:
    current = terminal_trial()
    merged = merge_live_trial_state(
        current,
        terminal_trial(
            status=None,
            reward=None,
            exception_type=None,
            exception_summary=None,
            completion_evidence=None,
            raw_result=None,
            finished_at="2026-07-28T12:00:30Z",
        ),
    )
    assert merged["status"] == current["status"]
    assert merged["reward"] == current["reward"]
    assert merged["completion_evidence"] == current["completion_evidence"]
    assert merged["raw_result"] == current["raw_result"]
    assert merged["finished_at"] == "2026-07-28T12:00:30Z"


def test_trial_sql_encodes_freshness_and_monotonic_rules() -> None:
    sql = inspect.getsource(PostgresLiveStore.publish_batch)
    assert "excluded.finished_at\n                                          <= benchmark.live_trials.finished_at" in sql
    assert "greatest(\n                                    benchmark.live_trials.runtime_seconds" in sql
    assert "least(\n                                    benchmark.live_trials.started_at" in sql
    assert "benchmark.live_trials.stability_state = 'complete'" in sql
    assert "coalesce(\n                                benchmark.live_trials.task_id" in sql
    assert "%(has_completion_evidence)s::boolean" in sql
    assert "%(has_raw_result)s::boolean" in sql


def uploaded_artifact(**updates: object) -> dict[str, object]:
    return {
        "live_run_id": "live-test",
        "trial_key": "task-one__abc",
        "artifact_type": "trial_result",
        "relative_local_path": "task-one__abc/result.json",
        "sha256": "a" * 64,
        "size_bytes": 42,
        "r2_uri": "r2://bucket/exact",
        "stability_state": "uploaded",
        "uploaded_at": "2026-07-28T12:00:20Z",
        "raw_metadata": {"source": "upload"},
        **updates,
    }


def test_uploaded_artifact_cannot_regress_to_stable_or_older_time() -> None:
    merged = merge_live_artifact_state(
        uploaded_artifact(),
        uploaded_artifact(
            r2_uri=None,
            stability_state="stable",
            uploaded_at="2026-07-28T12:00:10Z",
            raw_metadata={
                "replayed": True,
                "r2_uri": "r2://bucket/raw-conflict",
                "size_bytes": 1,
            },
        ),
    )
    assert merged["r2_uri"] == "r2://bucket/exact"
    assert merged["stability_state"] == "uploaded"
    assert merged["uploaded_at"] == "2026-07-28T12:00:20Z"
    assert merged["raw_metadata"] == {
        "source": "upload",
        "replayed": True,
    }


def test_stable_artifact_can_advance_to_uploaded() -> None:
    current = uploaded_artifact(
        r2_uri=None,
        stability_state="stable",
        uploaded_at=None,
    )
    merged = merge_live_artifact_state(current, uploaded_artifact())
    assert merged["r2_uri"] == "r2://bucket/exact"
    assert merged["stability_state"] == "uploaded"
    assert merged["uploaded_at"] == "2026-07-28T12:00:20Z"


def test_exact_uploaded_artifact_replay_is_idempotent() -> None:
    artifact = uploaded_artifact()
    assert merge_live_artifact_state(artifact, dict(artifact)) == artifact


def test_conflicting_live_artifact_uri_is_rejected() -> None:
    with pytest.raises(LiveArtifactConflict, match="conflicting R2 URI"):
        merge_live_artifact_state(
            uploaded_artifact(),
            uploaded_artifact(r2_uri="r2://bucket/conflict"),
        )


def test_artifact_sql_preserves_upload_state_and_rejects_uri_conflicts() -> None:
    sql = inspect.getsource(PostgresLiveStore.publish_batch)
    assert "coalesce(\n                                benchmark.live_artifacts.r2_uri" in sql
    assert "benchmark.live_artifacts.stability_state = 'uploaded'" in sql
    assert "greatest(\n                                    benchmark.live_artifacts.uploaded_at" in sql
    assert "benchmark.live_artifacts.r2_uri = excluded.r2_uri" in sql
    assert "cursor.rowcount != 1" in sql


def test_process_output_database_retention_is_bounded() -> None:
    sql = inspect.getsource(PostgresLiveStore.publish_batch)
    assert "event_type = 'process_output_chunk'" in sql
    assert "order by sequence desc" in sql
    assert "offset %s" in sql


class FakeEventCursor:
    def __init__(self, *, inserted: bool) -> None:
        self.inserted = inserted
        self.rowcount = -1
        self.calls: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object) -> None:
        self.calls.append((sql, params))
        self.rowcount = 1 if len(self.calls) == 1 and self.inserted else 0


def event_row(**updates: object) -> dict[str, object]:
    return {
        "live_run_id": "live-test",
        "sequence": 9,
        "event_type": "heartbeat",
        "occurred_at": "2026-07-28T12:00:09+00:00",
        "elapsed_seconds": 9.0,
        "stream": None,
        "message": "running",
        "payload": {},
        **updates,
    }


def test_duplicate_event_replay_does_not_update_parent_row() -> None:
    duplicate = FakeEventCursor(inserted=False)
    assert (
        insert_event_and_update_parent(
            duplicate,
            event_row(),
            json_payload={},
        )
        is False
    )
    assert len(duplicate.calls) == 1

    inserted = FakeEventCursor(inserted=True)
    assert (
        insert_event_and_update_parent(
            inserted,
            event_row(),
            json_payload={},
        )
        is True
    )
    assert len(inserted.calls) == 2


def test_event_parent_state_is_monotonic_and_terminal_messages_are_immutable() -> None:
    current = {
        "status": "completed",
        "canonical_publication_status": "failed",
        "event_count": 12,
        "last_heartbeat_at": "2026-07-28T12:00:12+00:00",
        "elapsed_seconds": 12.0,
        "latest_message": "Canonical publication failed",
    }
    replay = merge_event_parent_state(
        current,
        event_row(
            sequence=9,
            occurred_at="2026-07-28T12:00:09+00:00",
            elapsed_seconds=9.0,
            event_type="publication_warning",
            message="old warning",
        ),
        inserted=True,
    )
    assert replay["event_count"] == 12
    assert replay["last_heartbeat_at"] == current["last_heartbeat_at"]
    assert replay["elapsed_seconds"] == 12.0
    assert replay["latest_message"] == "Canonical publication failed"

    assert merge_event_parent_state(current, event_row(), inserted=False) == current

    ineligible = merge_event_parent_state(
        {
            "status": "running",
            "canonical_publication_status": "ineligible",
            "latest_message": "Canonical publication was ineligible",
        },
        event_row(message="stale process output"),
        inserted=True,
    )
    assert ineligible["latest_message"] == "Canonical publication was ineligible"


def test_spool_symlink_is_rejected_before_read_or_rewrite(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    live_dir = workspace / ".run" / "live"
    live_dir.mkdir(parents=True)
    outside = tmp_path / "outside.ndjson"
    outside.write_text("{}\n")
    spool = live_dir / "spool.ndjson"
    spool.symlink_to(outside)

    with pytest.raises(ValueError, match="symbolic link"):
        reconcile_database_spool(spool, FakeStore(), workspace=workspace)
