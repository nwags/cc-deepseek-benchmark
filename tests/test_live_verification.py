from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.lib.live_verification import (
    CompletedPublicationMismatch,
    apply_verified_progressive_artifacts,
    inspect_completed_publication_with_cursor,
    observed_suite_classification,
    update_live_run_publication_with_cursor,
    validate_publication_counts,
)
from scripts.lib.publication_fingerprint import publication_fingerprint


def exact_observed(**updates: object) -> dict[str, object]:
    return {
        "arm_run_count": 1,
        "trial_count": 2,
        "artifact_count": 1,
        "r2_artifact_count": 1,
        "r2_integrity_verified": True,
        "dashboard_arm_count": 1,
        "valid_view_count": 1,
        "invalid_row_count": 0,
        "live_link_expected": True,
        "live_link_count": 1,
        **updates,
    }


@pytest.mark.parametrize(
    ("valid_count", "invalid_count", "classification"),
    [
        (1, 0, "valid"),
        (0, 1, "invalid"),
        (0, 0, "unclassified"),
        (1, 1, "contradictory"),
    ],
)
def test_suite_classification_is_explicitly_observed(
    valid_count: int,
    invalid_count: int,
    classification: str,
) -> None:
    assert (
        observed_suite_classification(
            {"valid_view_count": valid_count, "invalid_row_count": invalid_count}
        )
        == classification
    )


@pytest.mark.parametrize(
    "classification",
    [
        {"valid_view_count": 1, "invalid_row_count": 0},
        {"valid_view_count": 0, "invalid_row_count": 1},
        {"valid_view_count": 0, "invalid_row_count": 0},
    ],
)
def test_valid_invalid_and_unclassified_runs_can_pass_integrity(
    classification: dict[str, int],
) -> None:
    manifest = {"trials": [{}, {}], "artifacts": [{}]}
    assert (
        validate_publication_counts(
            manifest,
            exact_observed(**classification),
            require_r2=True,
        )
        == []
    )


def test_contradictory_classification_is_rejected() -> None:
    errors = validate_publication_counts(
        {"trials": [{}, {}], "artifacts": [{}]},
        exact_observed(valid_view_count=1, invalid_row_count=1),
        require_r2=True,
    )
    assert "classified as both valid and invalid" in errors[0]


def test_non_null_r2_uri_count_is_not_integrity_proof() -> None:
    errors = validate_publication_counts(
        {"trials": [{}, {}], "artifacts": [{}]},
        exact_observed(r2_integrity_verified=False),
        require_r2=True,
    )
    assert errors == ["canonical R2 objects were not integrity-verified"]


class FakeS3:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def head_object(self, **_kwargs: object) -> dict[str, object]:
        return self.response


class FakePublicationCursor:
    def __init__(self, current: str | None) -> None:
        self.current = current
        self.calls: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object) -> None:
        self.calls.append((sql, params))

    def fetchone(self) -> tuple[str | None]:
        return (self.current,)


def test_failed_publication_requires_explicit_retry_to_reopen() -> None:
    stale = FakePublicationCursor("failed")
    assert (
        update_live_run_publication_with_cursor(
            stale,
            live_run_id="live-test",
            status="publishing",
            latest_message="stale replay",
        )
        == "failed"
    )
    assert len(stale.calls) == 1

    retry = FakePublicationCursor("failed")
    assert (
        update_live_run_publication_with_cursor(
            retry,
            live_run_id="live-test",
            status="publishing",
            latest_message="intentional retry",
            explicit_retry=True,
        )
        == "publishing"
    )
    update_sql, update_params = retry.calls[1]
    assert "updated_at = now()" in update_sql
    assert update_params["status"] == "publishing"  # type: ignore[index]
    assert update_params["latest_message"] == "intentional retry"  # type: ignore[index]


def test_completed_publication_state_is_immutable() -> None:
    cursor = FakePublicationCursor("completed")
    assert (
        update_live_run_publication_with_cursor(
            cursor,
            live_run_id="live-test",
            status="publishing",
            latest_message="must not replace completed",
            explicit_retry=True,
        )
        == "completed"
    )
    assert len(cursor.calls) == 1


def test_first_completion_persists_publication_fingerprint() -> None:
    cursor = FakePublicationCursor("verifying")
    assert (
        update_live_run_publication_with_cursor(
            cursor,
            live_run_id="live-test",
            status="completed",
            canonical_arm_run_id="arm-run-uuid",
            latest_message="verified",
            publication_fingerprint="a" * 64,
        )
        == "completed"
    )
    update_sql, params = cursor.calls[1]
    assert "jsonb_build_object" in update_sql
    assert "%(publication_fingerprint)s::text is null" in update_sql
    assert (
        "'publication_fingerprint',\n"
        "                    %(publication_fingerprint)s::text"
    ) in update_sql
    assert params["publication_fingerprint"] == "a" * 64  # type: ignore[index]


def test_pending_to_publishing_explicitly_types_null_fingerprint() -> None:
    cursor = FakePublicationCursor("pending")
    assert (
        update_live_run_publication_with_cursor(
            cursor,
            live_run_id="live-test",
            status="publishing",
            canonical_arm_run_id=None,
            latest_message="Canonical publication is running",
            publication_fingerprint=None,
        )
        == "publishing"
    )
    update_sql, params = cursor.calls[1]
    assert "%(publication_fingerprint)s::text is null" in update_sql
    assert "%(publication_fingerprint)s::text" in update_sql
    assert "%(canonical_arm_run_id)s::uuid" in update_sql
    assert params["publication_fingerprint"] is None  # type: ignore[index]
    assert params["status"] == "publishing"  # type: ignore[index]


def test_ineligible_publication_cannot_be_reopened() -> None:
    cursor = FakePublicationCursor("ineligible")
    assert (
        update_live_run_publication_with_cursor(
            cursor,
            live_run_id="live-test",
            status="publishing",
            latest_message="maintenance retry is not authorized",
            explicit_retry=True,
        )
        == "ineligible"
    )
    assert len(cursor.calls) == 1


def test_progressive_uri_reuse_requires_exact_remote_integrity(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    trial = run_dir / "task__abc"
    trial.mkdir(parents=True)
    artifact = trial / "result.json"
    artifact.write_text("{}")
    checksum = hashlib.sha256(b"{}").hexdigest()
    manifest = {
        "artifacts": [
            {
                "local_path": artifact.relative_to(tmp_path).as_posix(),
                "sha256": checksum,
                "size_bytes": 2,
            }
        ]
    }
    row = {
        "relative_local_path": "task__abc/result.json",
        "sha256": checksum,
        "size_bytes": 2,
        "r2_uri": "r2://bucket/key",
    }
    mismatch = FakeS3(
        {
            "ContentLength": 2,
            "Metadata": {"sha256": "wrong", "size_bytes": "2"},
        }
    )
    assert (
        apply_verified_progressive_artifacts(
            manifest,
            progressive_rows=[row],
            run_dir=run_dir,
            workspace=tmp_path,
            r2_client=mismatch,
        )
        == 0
    )
    assert "r2_uri" not in manifest["artifacts"][0]

    exact = FakeS3(
        {
            "ContentLength": 2,
            "Metadata": {"sha256": checksum, "size_bytes": "2"},
        }
    )
    assert (
        apply_verified_progressive_artifacts(
            manifest,
            progressive_rows=[row],
            run_dir=run_dir,
            workspace=tmp_path,
            r2_client=exact,
        )
        == 1
    )
    assert manifest["artifacts"][0]["r2_uri"] == "r2://bucket/key"


def completed_manifest() -> dict[str, object]:
    manifest: dict[str, object] = {
        "run": {
            "phase": "phase3",
            "storage_mode": "raw",
            "logical_mode": "full",
            "suite_id": None,
            "arm_id": "router-test",
            "run_label": "router-test/timestamp/github-123/attempt-1",
            "run_timestamp": "timestamp",
            "run_dir": "results/phase3/raw/arm-router-test/timestamp",
            "github_run_id": "123",
            "github_run_attempt": 1,
            "execution_scoped": True,
            "status": "completed",
            "n_total_trials": 1,
            "n_completed_trials": 1,
            "n_errored_trials": 0,
        },
        "trials": [
            {
                "trial_name": "task__one",
                "task_name": "task",
                "attempt_index": 1,
                "trial_dir": (
                    "results/phase3/raw/arm-router-test/timestamp/task__one"
                ),
                "raw_result_path": (
                    "results/phase3/raw/arm-router-test/timestamp/"
                    "task__one/result.json"
                ),
                "reward": 1,
                "status": "completed",
            }
        ],
        "artifacts": [
            {
                "artifact_type": "trial_result",
                "local_path": (
                    "results/phase3/raw/arm-router-test/timestamp/"
                    "task__one/result.json"
                ),
                "sha256": "a" * 64,
                "size_bytes": 42,
            }
        ],
    }
    return manifest


class CompletedPublicationCursor:
    def __init__(self, manifest: dict[str, object], fingerprint: str) -> None:
        self.manifest = manifest
        self.fingerprint = fingerprint
        self.sql = ""

    def execute(self, sql: str, _params: object) -> None:
        self.sql = " ".join(sql.split())

    def fetchone(self) -> tuple[object, ...]:
        if (
            "select canonical_publication_status, canonical_arm_run_id"
            in self.sql
        ):
            return ("completed", "arm-run-uuid", self.fingerprint)
        if "count(*) from benchmark.benchmark_arm_runs" in self.sql:
            return (1,)
        if "count(*) from benchmark.benchmark_trials" in self.sql:
            return (1,)
        if "count(*), count(*) filter" in self.sql:
            return (1, 1)
        if "count(*) from benchmark.v_dashboard_arms" in self.sql:
            return (1,)
        if "count(*) from benchmark.live_runs" in self.sql:
            return (1,)
        raise AssertionError(f"unexpected fetchone query: {self.sql}")

    def fetchall(self) -> list[tuple[object, ...]]:
        if "benchmark_run.raw_metadata ->> 'publication_fingerprint'" in self.sql:
            return [
                (
                    "run-uuid",
                    "arm-run-uuid",
                    self.fingerprint,
                    self.fingerprint,
                    "123",
                    "1",
                )
            ]
        if "select raw_result from benchmark.benchmark_trials" in self.sql:
            return [(self.manifest["trials"][0],)]  # type: ignore[index]
        if "select artifact_type, local_path, sha256" in self.sql:
            artifact = self.manifest["artifacts"][0]  # type: ignore[index]
            return [
                (
                    artifact["artifact_type"],
                    artifact["local_path"],
                    artifact["sha256"],
                    artifact["size_bytes"],
                    "r2://bucket/existing",
                )
            ]
        raise AssertionError(f"unexpected fetchall query: {self.sql}")


def test_exact_completed_supervised_evidence_is_accepted() -> None:
    manifest = completed_manifest()
    fingerprint = publication_fingerprint(manifest)
    existing = inspect_completed_publication_with_cursor(
        CompletedPublicationCursor(manifest, fingerprint),
        manifest=manifest,
        live_run_id="live-test",
        publication_fingerprint=fingerprint,
    )
    assert existing is not None
    assert existing.run_id == "run-uuid"
    assert existing.arm_run_id == "arm-run-uuid"


def test_exact_completed_unsupervised_evidence_is_accepted() -> None:
    manifest = completed_manifest()
    fingerprint = publication_fingerprint(manifest)
    existing = inspect_completed_publication_with_cursor(
        CompletedPublicationCursor(manifest, fingerprint),
        manifest=manifest,
        live_run_id=None,
        publication_fingerprint=fingerprint,
    )
    assert existing is not None
    assert existing.run_id == "run-uuid"


@pytest.mark.parametrize("changed_field", ["trial", "artifact"])
def test_completed_replay_with_changed_evidence_is_hard_mismatch(
    changed_field: str,
) -> None:
    stored = completed_manifest()
    fingerprint = publication_fingerprint(stored)
    incoming = completed_manifest()
    if changed_field == "trial":
        incoming["trials"][0]["reward"] = 0  # type: ignore[index]
    else:
        incoming["artifacts"][0]["sha256"] = "b" * 64  # type: ignore[index]

    with pytest.raises(
        CompletedPublicationMismatch,
        match="fingerprint differs",
    ):
        inspect_completed_publication_with_cursor(
            CompletedPublicationCursor(stored, fingerprint),
            manifest=incoming,
            live_run_id="live-test",
            publication_fingerprint=publication_fingerprint(incoming),
        )
