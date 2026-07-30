from __future__ import annotations

from copy import deepcopy

from scripts.lib.publication_fingerprint import publication_fingerprint


def manifest() -> dict[str, object]:
    return {
        "run": {
            "phase": "phase3",
            "logical_mode": "full",
            "storage_mode": "raw",
            "suite_id": "phase3-full-20",
            "arm_id": "router-test",
            "run_label": "router-test/timestamp/github-123/attempt-1",
            "run_timestamp": "timestamp",
            "run_dir": "results/phase3/raw/arm-router-test/timestamp",
            "github_run_id": "123",
            "github_run_attempt": 1,
            "status": "completed",
            "started_at": "2026-07-28T00:00:00Z",
            "finished_at": "2026-07-28T00:00:10Z",
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
                "started_at": "2026-07-28T00:00:00Z",
                "finished_at": "2026-07-28T00:00:10Z",
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
                "r2_uri": "r2://bucket/transient-one",
            }
        ],
        "publication": {"created_at": "publisher-time-one"},
    }


def test_publication_fingerprint_excludes_transient_and_location_fields() -> None:
    first = manifest()
    second = deepcopy(first)
    second["publication"] = {"created_at": "publisher-time-two"}
    second["artifacts"][0]["r2_uri"] = "r2://bucket/transient-two"  # type: ignore[index]
    second["run"]["run_dir"] = (  # type: ignore[index]
        "/home/another-runner/work/results/phase3/raw/"
        "arm-router-test/timestamp"
    )
    second["trials"][0]["trial_dir"] = (  # type: ignore[index]
        "/home/another-runner/work/results/phase3/raw/"
        "arm-router-test/timestamp/task__one"
    )
    second["trials"][0]["raw_result_path"] = (  # type: ignore[index]
        "/home/another-runner/work/results/phase3/raw/"
        "arm-router-test/timestamp/task__one/result.json"
    )
    second["artifacts"][0]["local_path"] = (  # type: ignore[index]
        "/home/another-runner/work/results/phase3/raw/"
        "arm-router-test/timestamp/task__one/result.json"
    )

    assert publication_fingerprint(first) == publication_fingerprint(second)


def test_completed_replay_trial_change_changes_fingerprint() -> None:
    first = manifest()
    second = deepcopy(first)
    second["trials"][0]["reward"] = 0  # type: ignore[index]

    assert publication_fingerprint(first) != publication_fingerprint(second)


def test_completed_replay_artifact_change_changes_fingerprint() -> None:
    first = manifest()
    second = deepcopy(first)
    second["artifacts"][0]["sha256"] = "b" * 64  # type: ignore[index]

    assert publication_fingerprint(first) != publication_fingerprint(second)
