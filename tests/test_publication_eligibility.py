from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.publication_eligibility import evaluate_canonical_eligibility


def make_run(
    workspace: Path,
    *,
    total: int = 1,
    completed: int = 1,
    errors: int = 0,
    trial_count: int = 1,
    exception_trials: int = 0,
    incomplete_trial: bool = False,
) -> Path:
    run_dir = (
        workspace
        / "results"
        / "phase3"
        / "canary"
        / "arm-router-test"
        / "2026-07-28__12-00-00"
    )
    run_dir.mkdir(parents=True)
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-07-28T12:00:00Z",
                "finished_at": "2026-07-28T12:01:00Z",
                "n_total_trials": total,
                "stats": {
                    "n_completed_trials": completed,
                    "n_errored_trials": errors,
                    "n_running_trials": 0,
                    "n_pending_trials": 0,
                    "n_cancelled_trials": 0,
                },
            }
        )
    )
    for index in range(trial_count):
        trial = run_dir / f"task-{index}__abc"
        trial.mkdir()
        data = {
            "started_at": "2026-07-28T12:00:00Z",
            "finished_at": None if incomplete_trial and index == 0 else "2026-07-28T12:00:30Z",
            "verifier_result": {"rewards": {"reward": 0}},
            "exception_info": (
                {"exception_type": "AgentTimeoutError"}
                if index < exception_trials
                else None
            ),
        }
        (trial / "result.json").write_text(json.dumps(data))
    return run_dir


def test_complete_success_is_canonically_eligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=1,
        benchmark_status="completed",
    )
    assert result.eligible
    assert result.reasons == ()


def test_complete_error_bearing_execution_is_eligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, errors=1, exception_trials=1)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=1,
        benchmark_status="failed",
    )
    assert result.eligible
    assert result.discovered_error_count == 1


def test_missing_trials_are_ineligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, total=2, completed=2, trial_count=1)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=2,
    )
    assert not result.eligible
    assert any("expected trial count" in reason for reason in result.reasons)
    assert any("root total" in reason for reason in result.reasons)


def test_mismatched_root_totals_are_ineligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, completed=0)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=1,
    )
    assert not result.eligible
    assert any("completed count" in reason for reason in result.reasons)


def test_incomplete_trial_result_is_ineligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, incomplete_trial=True)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=1,
    )
    assert not result.eligible
    assert any("is incomplete" in reason for reason in result.reasons)


def test_interrupted_partial_execution_is_ineligible(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path)
    result = evaluate_canonical_eligibility(
        run_dir,
        workspace=tmp_path,
        expected_trial_count=1,
        benchmark_status="interrupted",
    )
    assert not result.eligible
    assert any("lifecycle is interrupted" in reason for reason in result.reasons)
