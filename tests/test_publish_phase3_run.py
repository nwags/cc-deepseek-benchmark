from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.publish_phase3_run as publisher
from scripts.lib.live_verification import ExistingCanonicalPublication
from scripts.publish_phase3_run import main


def make_complete_run(workspace: Path) -> Path:
    run_dir = (
        workspace
        / "results"
        / "phase3"
        / "canary"
        / "arm-router-test"
        / "2026-07-28__12-00-00"
    )
    trial_dir = run_dir / "task-one__abc"
    trial_dir.mkdir(parents=True)
    (run_dir / "config.json").write_text(
        json.dumps({"agent": "claude-code", "model_name": "router-test"})
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "started_at": "2026-07-28T12:00:00Z",
                "finished_at": "2026-07-28T12:00:10Z",
                "n_total_trials": 1,
                "stats": {
                    "n_completed_trials": 1,
                    "n_errored_trials": 0,
                    "n_running_trials": 0,
                    "n_pending_trials": 0,
                    "n_cancelled_trials": 0,
                    "cost_usd": 0.0,
                    "n_input_tokens": 0,
                    "n_cache_tokens": 0,
                    "n_output_tokens": 0,
                },
            }
        )
    )
    (trial_dir / "result.json").write_text(
        json.dumps(
            {
                "trial_name": trial_dir.name,
                "task_name": "task-one",
                "started_at": "2026-07-28T12:00:00Z",
                "finished_at": "2026-07-28T12:00:10Z",
                "agent_result": {
                    "n_input_tokens": 0,
                    "n_cache_tokens": 0,
                    "n_output_tokens": 0,
                    "cost_usd": 0,
                },
                "verifier_result": {"rewards": {"reward": 1}},
                "exception_info": None,
            }
        )
    )
    return run_dir


def test_canonical_publish_dry_run_builds_manifest_without_network(tmp_path: Path) -> None:
    run_dir = make_complete_run(tmp_path)
    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--mode",
            "canary",
            "--workspace",
            str(tmp_path),
            "--run-dir",
            str(run_dir),
            "--live-run-id",
            "live-publish-test",
            "--dry-run",
        ]
    )
    assert returncode == 0
    manifest_path = tmp_path / ".run" / "publish" / "live-publish-test.manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["trials"]) == 1
    assert manifest["run"]["live_run_id"] == "live-publish-test"
    assert manifest["run"]["arm_id"] == "router-test"
    assert len(manifest["run"]["publication_fingerprint"]) == 64
    assert str(tmp_path) not in json.dumps(manifest)


def test_canonical_publish_without_supervision_uses_explicit_expected_count(
    tmp_path: Path,
) -> None:
    run_dir = make_complete_run(tmp_path)
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
                "--expected-trial-count",
                "1",
                "--dry-run",
            ]
        )
        == 0
    )
    manifests = list((tmp_path / ".run" / "publish").glob("*.manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["run"]["live_run_id"] is None
    assert len(manifest["trials"]) == 1


def test_unsupervised_discovery_uses_publication_context(tmp_path: Path) -> None:
    make_complete_run(tmp_path)
    publish_dir = tmp_path / ".run" / "publish"
    publish_dir.mkdir(parents=True)
    context = publish_dir / "execution.discovery-context.json"
    context.write_text(
        json.dumps(
            {
                "watch_roots": [
                    "results/phase3/canary/arm-router-test",
                ],
                "baseline_run_dirs": [],
                "started_after_epoch": 0,
                "expected_trial_count": 1,
            }
        )
    )

    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--discovery-context",
                ".run/publish/execution.discovery-context.json",
                "--dry-run",
            ]
        )
        == 0
    )
    manifests = list(publish_dir.glob("*.manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert manifest["run"]["live_run_id"] is None


def test_canonical_publish_dry_run_allows_no_run_directory(tmp_path: Path) -> None:
    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--mode",
            "canary",
            "--workspace",
            str(tmp_path),
            "--live-run-id",
            "live-no-run",
            "--dry-run",
        ]
    )
    assert returncode == 0
    state = json.loads(
        (tmp_path / ".run" / "publish" / "live-no-run.json").read_text()
    )
    assert state["status"] == "dry_run_no_run_directory"


def test_canonical_publish_without_run_directory_fails(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--live-run-id",
                "live-no-run-paid",
                "--no-upload-r2",
                "--no-insert-db",
                "--no-verify",
            ]
        )
        == 1
    )


def test_canonical_manifest_rejects_allowlisted_symlink(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_complete_run(workspace)
    trial_dir = next(path for path in run_dir.iterdir() if path.is_dir())
    outside = tmp_path / "outside.log"
    outside.write_text("not part of the run")
    (trial_dir / "trial.log").symlink_to(outside)

    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--mode",
            "canary",
            "--workspace",
            str(workspace),
            "--run-dir",
            str(run_dir),
            "--live-run-id",
            "live-symlink-test",
            "--dry-run",
        ]
    )
    assert returncode == 1
    state = json.loads(
        (workspace / ".run" / "publish" / "live-symlink-test.json").read_text()
    )
    assert state["status"] == "failed"
    assert not (
        workspace / ".run" / "publish" / "live-symlink-test.manifest.json"
    ).exists()


def test_ineligible_run_stops_before_canonical_r2_or_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = make_complete_run(tmp_path)
    root = json.loads((run_dir / "result.json").read_text())
    root["n_total_trials"] = 2
    root["stats"]["n_completed_trials"] = 2
    (run_dir / "result.json").write_text(json.dumps(root))
    for name in (
        "SUPABASE_DB_URL",
        "R2_BUCKET",
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_REGION",
    ):
        monkeypatch.setenv(name, "configured")

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("canonical I/O must not run for ineligible results")

    monkeypatch.setattr(publisher, "create_r2_client", unexpected)
    monkeypatch.setattr(publisher, "upload_artifacts_to_r2", unexpected)
    monkeypatch.setattr(publisher, "PsycopgCanonicalDatabaseAdapter", unexpected)
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
            ]
        )
        == 1
    )
    state_files = list((tmp_path / ".run" / "publish").glob("*.json"))
    assert len(state_files) == 1
    state = json.loads(state_files[0].read_text())
    assert state["status"] == "ineligible"
    assert state["eligibility"]["eligible"] is False
    assert not list((tmp_path / ".run" / "publish").glob("*.manifest.json"))


def test_completed_replay_performs_no_r2_upload_or_canonical_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = make_complete_run(tmp_path)
    for name in (
        "SUPABASE_DB_URL",
        "R2_BUCKET",
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_REGION",
    ):
        monkeypatch.setenv(name, "configured")
    monkeypatch.setattr(publisher, "create_r2_client", lambda **_kwargs: object())

    def completed(**kwargs: object) -> ExistingCanonicalPublication:
        manifest = kwargs["manifest"]  # type: ignore[index]
        artifacts = tuple(
            {**artifact, "r2_uri": f"r2://bucket/existing/{index}"}
            for index, artifact in enumerate(manifest["artifacts"])  # type: ignore[index]
        )
        return ExistingCanonicalPublication(
            run_id="run-uuid",
            arm_run_id="arm-run-uuid",
            publication_fingerprint=str(kwargs["publication_fingerprint"]),
            artifacts=artifacts,
            verification={"ok": True, "errors": []},
        )

    monkeypatch.setattr(publisher, "inspect_completed_publication", completed)
    monkeypatch.setattr(
        publisher,
        "verify_manifest_r2_objects",
        lambda *_args, **_kwargs: [],
    )

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("completed replay must not mutate canonical storage")

    monkeypatch.setattr(publisher, "upload_artifacts_to_r2", unexpected)
    monkeypatch.setattr(publisher, "publish_manifest_transactionally", unexpected)

    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
                "--live-run-id",
                "live-completed-replay",
                "--authorize-phase3-repair",
            ]
        )
        == 0
    )
    state = json.loads(
        (
            tmp_path
            / ".run"
            / "publish"
            / "live-completed-replay.json"
        ).read_text()
    )
    assert state["status"] == "already_completed"


def test_closed_phase3_suite_stops_before_r2_or_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = make_complete_run(tmp_path)

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("closed-suite guard must precede canonical I/O")

    monkeypatch.setattr(publisher, "create_r2_client", unexpected)
    monkeypatch.setattr(publisher, "upload_artifacts_to_r2", unexpected)
    monkeypatch.setattr(publisher, "PsycopgCanonicalDatabaseAdapter", unexpected)
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
                "--no-upload-r2",
                "--no-insert-db",
                "--no-verify",
            ]
        )
        == 1
    )
    state_files = [
        path
        for path in (tmp_path / ".run" / "publish").glob("*.json")
        if not path.name.endswith(".manifest.json")
    ]
    assert len(state_files) == 1
    state = json.loads(state_files[0].read_text())
    assert state["status"] == "failed"
    assert state["error_type"] == "ClosedPhase3SuiteError"


def test_explicit_phase3_repair_authorization_allows_publication_path(
    tmp_path: Path,
) -> None:
    run_dir = make_complete_run(tmp_path)
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
                "--authorize-phase3-repair",
                "--no-upload-r2",
                "--no-insert-db",
                "--no-verify",
            ]
        )
        == 0
    )


def test_workflow_publisher_rejects_manifest_outside_workspace(
    tmp_path: Path,
) -> None:
    run_dir = make_complete_run(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-publication-manifest.json"
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--run-dir",
                str(run_dir),
                "--manifest-out",
                str(outside),
                "--dry-run",
            ]
        )
        == 2
    )
    assert not outside.exists()


def test_workflow_publisher_rejects_discovery_context_outside_workspace(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-context.json"
    outside.write_text("{}")
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--discovery-context",
                str(outside),
                "--dry-run",
            ]
        )
        == 2
    )


def test_workflow_publisher_rejects_symlinked_discovery_context(
    tmp_path: Path,
) -> None:
    publish_dir = tmp_path / ".run" / "publish"
    publish_dir.mkdir(parents=True)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-context.json"
    outside.write_text("{}")
    context = publish_dir / "execution.discovery-context.json"
    context.symlink_to(outside)

    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--discovery-context",
                ".run/publish/execution.discovery-context.json",
                "--dry-run",
            ]
        )
        == 2
    )


@pytest.mark.parametrize("symlink_name", [".run", ".run/publish"])
def test_workflow_publisher_rejects_symlinked_run_parents(
    tmp_path: Path,
    symlink_name: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = workspace / symlink_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(outside, target_is_directory=True)

    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--mode",
                "canary",
                "--workspace",
                str(workspace),
                "--dry-run",
            ]
        )
        == 2
    )
