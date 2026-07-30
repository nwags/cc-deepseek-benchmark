from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts.ingest_phase3_run_metadata import (
    R2ObjectConflict,
    upload_artifacts_to_r2,
)
from scripts.lib.live_artifacts import (
    FileStabilityTracker,
    ProgressiveR2Uploader,
    artifact_row,
    discover_run_dir,
    parse_trial_result,
    progressive_r2_key,
    stable_trial_artifacts,
    verify_manifest_r2_objects,
    verify_r2_object,
)
from scripts.lib.path_safety import PathBoundaryError


def make_run(workspace: Path, timestamp: str) -> Path:
    run_dir = workspace / "results" / "phase3" / "canary" / "arm-router-test" / timestamp
    run_dir.mkdir(parents=True)
    return run_dir


def test_discovery_is_workspace_scoped_and_rejects_ambiguity(tmp_path: Path) -> None:
    root = tmp_path / "results" / "phase3" / "canary" / "arm-router-test"
    make_run(tmp_path, "2026-07-28__10-00-00")
    make_run(tmp_path, "2026-07-28__10-01-00")
    with pytest.raises(ValueError, match="ambiguous"):
        discover_run_dir(workspace=tmp_path, watch_roots=[root])

    outside = tmp_path.parent / "2026-07-28__10-02-00"
    outside.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="outside"):
        discover_run_dir(
            workspace=tmp_path,
            watch_roots=[root],
            explicit_run_dir=outside,
        )


def test_discovery_honors_baseline_and_explicit_override(tmp_path: Path) -> None:
    old = make_run(tmp_path, "2026-07-28__10-00-00")
    new = make_run(tmp_path, "2026-07-28__10-01-00")
    root = old.parent
    assert discover_run_dir(
        workspace=tmp_path,
        watch_roots=[root],
        baseline_run_dirs=[old.as_posix()],
    ) == new
    assert discover_run_dir(
        workspace=tmp_path,
        watch_roots=[root],
        explicit_run_dir=old,
    ) == old


def complete_trial(run_dir: Path) -> Path:
    trial = run_dir / "task-one__abc"
    trial.mkdir()
    result = {
        "trial_name": trial.name,
        "task_name": "task-one",
        "started_at": "2026-07-28T10:00:00Z",
        "finished_at": "2026-07-28T10:00:05Z",
        "agent_result": {
            "n_input_tokens": 10,
            "n_cache_tokens": 5,
            "n_output_tokens": 2,
            "cost_usd": 0.01,
        },
        "verifier_result": {"rewards": {"reward": 1.0}},
        "exception_info": None,
    }
    (trial / "result.json").write_text(json.dumps(result))
    return trial


def test_progressive_trial_parsing_requires_final_evidence(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, "2026-07-28__10-00-00")
    trial = complete_trial(run_dir)
    parsed = parse_trial_result(
        trial / "result.json",
        live_run_id="live-test",
        run_dir=run_dir,
    )
    assert parsed is not None
    assert parsed["status"] == "succeeded"
    assert parsed["runtime_seconds"] == 5
    assert parsed["input_tokens"] == 10

    (trial / "result.json").write_text(json.dumps({"trial_name": trial.name}))
    assert parse_trial_result(
        trial / "result.json",
        live_run_id="live-test",
        run_dir=run_dir,
    ) is None


def test_growing_files_are_not_stable_or_uploaded(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, "2026-07-28__10-00-00")
    trial = complete_trial(run_dir)
    transcript = trial / "claude-code.txt"
    transcript.write_text("first")
    tracker = FileStabilityTracker()

    assert stable_trial_artifacts(
        trial,
        tracker,
        stability_seconds=5,
        now=0,
        workspace=tmp_path,
        run_dir=run_dir,
    ) == []
    transcript.write_text("first growing")
    assert stable_trial_artifacts(
        trial,
        tracker,
        stability_seconds=5,
        now=3,
        workspace=tmp_path,
        run_dir=run_dir,
    ) == []
    stable = stable_trial_artifacts(
        trial,
        tracker,
        stability_seconds=5,
        now=9,
        workspace=tmp_path,
        run_dir=run_dir,
    )
    assert transcript in stable


class FakeS3:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, dict[str, object]]] = []
        self.head: dict[tuple[str, str], dict[str, object]] = {}

    def upload_file(self, local_path: str, bucket: str, key: str, **kwargs: object) -> None:
        self.calls.append((local_path, bucket, key, kwargs))

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        if (Bucket, Key) not in self.head:
            raise FileNotFoundError(Key)
        return self.head[(Bucket, Key)]


def test_checksum_and_idempotent_progressive_upload(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path, "2026-07-28__10-00-00")
    trial = complete_trial(run_dir)
    row = artifact_row(
        live_run_id="live-test",
        run_dir=run_dir,
        path=trial / "result.json",
        trial_key=trial.name,
        r2_uri=None,
        workspace=tmp_path,
    )
    fake = FakeS3()
    uploader = ProgressiveR2Uploader(
        bucket="bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        client=fake,
        sleep=lambda _seconds: None,
    )
    key = "phase3/live/result.json"
    assert uploader.upload(
        trial / "result.json",
        key,
        row["sha256"],
        row["size_bytes"],
        workspace=tmp_path,
        parent=trial,
    )
    assert not uploader.upload(
        trial / "result.json",
        key,
        row["sha256"],
        row["size_bytes"],
        workspace=tmp_path,
        parent=trial,
    )
    assert len(fake.calls) == 1
    assert len(row["sha256"]) == 64
    metadata = fake.calls[0][3]["ExtraArgs"]["Metadata"]  # type: ignore[index]
    assert metadata == {
        "sha256": row["sha256"],
        "size_bytes": str(row["size_bytes"]),
    }


def test_r2_key_isolated_by_opaque_runner_and_attempt() -> None:
    common = {
        "prefix": "phase3",
        "github_run_id": "100",
        "runner_name": "vps-phase3-vps2-slot4",
        "live_run_id": "live-100",
        "arm_id": "router-test",
        "mode": "full",
        "trial_key": "task__abc",
        "relative_path": "task__abc/result.json",
        "sha256": "a" * 64,
    }
    first = progressive_r2_key(github_run_attempt=1, **common)
    second = progressive_r2_key(github_run_attempt=2, **common)
    assert first != second
    assert "vps-phase3-vps2-slot4" in first


def test_timestamped_symlink_outside_workspace_is_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "results" / "phase3" / "canary" / "arm-router-test"
    root.mkdir(parents=True)
    outside = tmp_path / "outside" / "2026-07-28__10-00-00"
    outside.mkdir(parents=True)
    (root / outside.name).symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathBoundaryError, match="symbolic link"):
        discover_run_dir(workspace=workspace, watch_roots=[root])


def test_allowlisted_artifact_symlink_is_rejected_and_never_uploaded(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_run(workspace, "2026-07-28__10-00-00")
    trial = complete_trial(run_dir)
    outside = tmp_path / "outside.txt"
    outside.write_text("must not upload")
    (trial / "claude-code.txt").symlink_to(outside)
    tracker = FileStabilityTracker()

    with pytest.raises(PathBoundaryError, match="symbolic link"):
        stable_trial_artifacts(
            trial,
            tracker,
            stability_seconds=0,
            workspace=workspace,
            run_dir=run_dir,
        )

    fake = FakeS3()
    assert fake.calls == []


def test_symlinked_trial_directory_is_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_run(workspace, "2026-07-28__10-00-00")
    outside_trial = tmp_path / "task-one__outside"
    outside_trial.mkdir()
    (outside_trial / "result.json").write_text("{}")
    linked_trial = run_dir / "task-one__linked"
    linked_trial.symlink_to(outside_trial, target_is_directory=True)

    with pytest.raises(PathBoundaryError, match="symbolic link"):
        parse_trial_result(
            linked_trial / "result.json",
            live_run_id="live-test",
            run_dir=run_dir,
            workspace=workspace,
        )


def test_progressive_object_identity_includes_artifact_hash() -> None:
    common = {
        "prefix": "phase3",
        "github_run_id": "100",
        "github_run_attempt": 1,
        "runner_name": "opaque-runner",
        "live_run_id": "live-100",
        "arm_id": "router-test",
        "mode": "full",
        "trial_key": "task__abc",
        "relative_path": "task__abc/result.json",
    }
    first = progressive_r2_key(sha256="a" * 64, **common)
    changed = progressive_r2_key(sha256="b" * 64, **common)
    assert first != changed
    assert "sha256-" + "a" * 64 in first


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (None, False),
        ({"ContentLength": 3, "Metadata": {"sha256": "wrong", "size_bytes": "3"}}, False),
        ({"ContentLength": 4, "Metadata": {"sha256": "abc", "size_bytes": "3"}}, False),
        ({"ContentLength": 3, "Metadata": {"sha256": "abc", "size_bytes": "3"}}, True),
    ],
)
def test_r2_object_integrity_checks_missing_checksum_and_size(
    response: dict[str, object] | None,
    expected: bool,
) -> None:
    fake = FakeS3()
    if response is not None:
        fake.head[("bucket", "key")] = response
    verified, _reason = verify_r2_object(
        fake,
        uri="r2://bucket/key",
        sha256="abc",
        size_bytes=3,
    )
    assert verified is expected

    manifest = {
        "artifacts": [
            {
                "r2_uri": "r2://bucket/key",
                "r2_key": "key",
                "sha256": "abc",
                "size_bytes": 3,
            }
        ]
    }
    assert (verify_manifest_r2_objects(manifest, client=fake) == []) is expected


def test_final_upload_attaches_integrity_metadata_and_rejects_symlink(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_run(workspace, "2026-07-28__10-00-00")
    trial = complete_trial(run_dir)
    artifact = trial / "result.json"
    data = artifact.read_bytes()
    manifest = {
        "run": {"run_dir": run_dir.relative_to(workspace).as_posix()},
        "artifacts": [
            {
                "local_path": artifact.relative_to(workspace).as_posix(),
                "r2_key": "phase3/final/result.json",
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        ],
    }
    fake = FakeS3()
    upload_artifacts_to_r2(
        manifest,
        bucket="bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        workspace=workspace,
        run_dir=run_dir,
        client=fake,
    )
    assert fake.calls[0][3]["ExtraArgs"]["Metadata"]["size_bytes"] == str(len(data))  # type: ignore[index]

    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    artifact.unlink()
    artifact.symlink_to(outside)
    manifest["artifacts"][0].pop("r2_uri", None)
    second_fake = FakeS3()
    with pytest.raises(PathBoundaryError):
        upload_artifacts_to_r2(
            manifest,
            bucket="bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            workspace=workspace,
            run_dir=run_dir,
            client=second_fake,
        )
    assert second_fake.calls == []


@pytest.mark.parametrize(
    "metadata_updates",
    [
        {"sha256": "wrong"},
        {"size_bytes": "999"},
    ],
)
def test_final_upload_rejects_conflicting_immutable_object(
    tmp_path: Path,
    metadata_updates: dict[str, str],
) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_run(workspace, "2026-07-28__10-00-00")
    artifact = complete_trial(run_dir) / "result.json"
    data = artifact.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    key = f"phase3/final/sha256-{checksum}/result.json"
    manifest = {
        "run": {"run_dir": run_dir.relative_to(workspace).as_posix()},
        "artifacts": [
            {
                "local_path": artifact.relative_to(workspace).as_posix(),
                "r2_key": key,
                "sha256": checksum,
                "size_bytes": len(data),
            }
        ],
    }
    metadata = {"sha256": checksum, "size_bytes": str(len(data))}
    metadata.update(metadata_updates)
    fake = FakeS3()
    fake.head[("bucket", key)] = {
        "ContentLength": len(data),
        "Metadata": metadata,
    }

    with pytest.raises(R2ObjectConflict):
        upload_artifacts_to_r2(
            manifest,
            bucket="bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            workspace=workspace,
            run_dir=run_dir,
            client=fake,
        )
    assert fake.calls == []


def test_same_execution_final_upload_reuses_exact_immutable_object(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    run_dir = make_run(workspace, "2026-07-28__10-00-00")
    artifact = complete_trial(run_dir) / "result.json"
    data = artifact.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    key = f"phase3/final/sha256-{checksum}/result.json"
    manifest = {
        "run": {"run_dir": run_dir.relative_to(workspace).as_posix()},
        "artifacts": [
            {
                "local_path": artifact.relative_to(workspace).as_posix(),
                "r2_key": key,
                "sha256": checksum,
                "size_bytes": len(data),
            }
        ],
    }
    fake = FakeS3()
    fake.head[("bucket", key)] = {
        "ContentLength": len(data),
        "Metadata": {
            "sha256": checksum,
            "size_bytes": str(len(data)),
        },
    }

    upload_artifacts_to_r2(
        manifest,
        bucket="bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        workspace=workspace,
        run_dir=run_dir,
        client=fake,
    )

    assert fake.calls == []
    assert manifest["artifacts"][0]["r2_uri"] == f"r2://bucket/{key}"
