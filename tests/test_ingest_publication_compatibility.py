from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ingest_phase3_run_metadata import (
    CanonicalIdentityCollision,
    DependentTrialRowsError,
    assert_canonical_identity_compatible,
    assert_trial_replacement_allowed,
    build_r2_key,
    canonical_run_label,
    resolve_reusable_r2_uri,
    reusable_r2_uri_map,
)


def run_metadata() -> dict[str, object]:
    return {
        "arm_id": "router-test",
        "run_dir": (
            "results/phase3/raw/arm-router-test/2026-07-28__12-00-00"
        ),
        "run_timestamp": "2026-07-28__12-00-00",
    }


def test_legacy_absolute_artifact_matches_new_relative_identity() -> None:
    run = run_metadata()
    legacy_path = (
        "/home/bench/actions-runner/_work/repo/repo/"
        "results/phase3/raw/arm-router-test/2026-07-28__12-00-00/"
        "task-one__abc/result.json"
    )
    reusable = reusable_r2_uri_map(
        [(legacy_path, "r2://bucket/original", "abc123", 42)],
        run=run,
    )
    artifact = {
        "local_path": (
            "results/phase3/raw/arm-router-test/2026-07-28__12-00-00/"
            "task-one__abc/result.json"
        ),
        "sha256": "abc123",
        "size_bytes": 42,
    }

    assert (
        resolve_reusable_r2_uri(artifact, run=run, reusable=reusable)
        == "r2://bucket/original"
    )


def test_metadata_only_reingestion_reuses_only_exact_hash_and_size() -> None:
    run = run_metadata()
    reusable = reusable_r2_uri_map(
        [
            (
                "results/phase3/raw/arm-router-test/2026-07-28__12-00-00/"
                "task-one__abc/result.json",
                "r2://bucket/original",
                "abc123",
                42,
            )
        ],
        run=run,
    )
    unchanged = {
        "local_path": (
            "results/phase3/raw/arm-router-test/2026-07-28__12-00-00/"
            "task-one__abc/result.json"
        ),
        "sha256": "abc123",
        "size_bytes": 42,
    }
    changed_checksum = {**unchanged, "sha256": "different"}
    changed_size = {**unchanged, "size_bytes": 43}

    assert resolve_reusable_r2_uri(unchanged, run=run, reusable=reusable)
    assert resolve_reusable_r2_uri(
        changed_checksum,
        run=run,
        reusable=reusable,
    ) is None
    assert resolve_reusable_r2_uri(
        changed_size,
        run=run,
        reusable=reusable,
    ) is None


def test_github_execution_scopes_same_second_labels_and_final_r2_keys(
    tmp_path: Path,
) -> None:
    root = tmp_path / "2026-07-28__12-00-00"
    artifact = root / "task__abc" / "result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}")
    first_run = {
        **run_metadata(),
        "execution_scoped": True,
        "github_run_id": "100",
        "github_run_attempt": 1,
    }
    second_run = {
        **run_metadata(),
        "execution_scoped": True,
        "github_run_id": "101",
        "github_run_attempt": 1,
    }

    assert canonical_run_label(first_run) != canonical_run_label(second_run)
    first_key = build_r2_key(
        root,
        artifact,
        "phase3",
        "phase3",
        "raw",
        "router-test",
        "github-100/attempt-1",
        "a" * 64,
    )
    second_key = build_r2_key(
        root,
        artifact,
        "phase3",
        "phase3",
        "raw",
        "router-test",
        "github-101/attempt-1",
        "a" * 64,
    )
    assert first_key != second_key
    assert f"sha256-{'a' * 64}" in first_key


def test_canonical_identity_replay_and_collision_guard() -> None:
    assert_canonical_identity_compatible(
        incoming_github_run_id="100",
        incoming_github_run_attempt=2,
        existing_github_run_id="100",
        existing_github_run_attempt="2",
    )
    with pytest.raises(CanonicalIdentityCollision, match="different GitHub run"):
        assert_canonical_identity_compatible(
            incoming_github_run_id="100",
            incoming_github_run_attempt=2,
            existing_github_run_id="101",
            existing_github_run_attempt=2,
        )
    with pytest.raises(CanonicalIdentityCollision, match="different GitHub run attempt"):
        assert_canonical_identity_compatible(
            incoming_github_run_id="100",
            incoming_github_run_attempt=2,
            existing_github_run_id="100",
            existing_github_run_attempt=1,
        )


def test_historical_canonical_identity_remains_compatible() -> None:
    run = run_metadata()
    assert canonical_run_label(run) == (
        "router-test/2026-07-28__12-00-00"
    )


class DependentRowCursor:
    def __init__(self, counts: dict[str, int]) -> None:
        self.counts = counts
        self.sql = ""
        self.params: tuple[object, ...] = ()

    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        self.sql = sql
        self.params = params

    def fetchone(self) -> tuple[object]:
        if "to_regclass" in self.sql:
            return (self.params[0],)
        for relation, count in self.counts.items():
            if relation in self.sql:
                return (count,)
        raise AssertionError("unexpected dependent-row query")


def test_trial_replacement_refuses_dependent_cost_coverage() -> None:
    cursor = DependentRowCursor(
        {
            "benchmark_trial_cost_coverage": 1,
            "contamination_audits": 0,
        }
    )
    with pytest.raises(DependentTrialRowsError, match="cost_coverage=1"):
        assert_trial_replacement_allowed(
            cursor,
            run_id="run-uuid",
            allow_dependent_trial_replacement=False,
        )


def test_maintenance_override_is_required_for_dependent_replacement() -> None:
    counts = assert_trial_replacement_allowed(
        DependentRowCursor(
            {
                "benchmark_trial_cost_coverage": 1,
                "contamination_audits": 2,
            }
        ),
        run_id="run-uuid",
        allow_dependent_trial_replacement=True,
    )
    assert counts == {
        "benchmark_trial_cost_coverage": 1,
        "contamination_audits": 2,
    }
