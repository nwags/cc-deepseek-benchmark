from pathlib import Path

import pytest

from scripts.lib.arms import ConfigError
from scripts.lib.harbor import build_harbor_command, write_ad_hoc_metadata


def value_after(cmd: list[str], flag: str) -> str:
    return cmd[cmd.index(flag) + 1]


def phase(tmp_path: Path) -> dict[str, object]:
    return {
        "phase_id": "phase3-router",
        "dataset": "terminal-bench@2.0",
        "agent": "claude-code",
        "results_root": str(tmp_path / "results" / "phase3"),
        "task_file": str(tmp_path / "full.txt"),
        "canary_task_file": str(tmp_path / "canary.txt"),
        "smoke_task_file": str(tmp_path / "smoke.txt"),
        "n_attempts": 3,
        "n_concurrent": 4,
        "mode_results_subdirs": {
            "canary": "canary",
            "smoke": "smoke",
            "full": "raw",
        },
    }


def arm() -> dict[str, object]:
    return {
        "arm_id": "router-test",
        "job_dir_name": "arm-router-test",
        "agent": "claude-code",
        "model": "router-test",
    }


def test_task_id_ad_hoc_uses_single_task_and_non_scored(tmp_path: Path) -> None:
    cmd, jobs_dir, metadata = build_harbor_command(
        phase=phase(tmp_path),
        arm=arm(),
        env={},
        mode="full",
        n_attempts=None,
        n_concurrent=None,
        task_id="modernize-scientific-stack",
        task_file_override=None,
        ad_hoc_label="debug-one",
    )

    assert jobs_dir == tmp_path / "results" / "phase3" / "ad-hoc" / "debug-one" / "arm-router-test"
    assert metadata["ad_hoc"] is True
    assert metadata["scored"] is False
    assert metadata["task_source"] == "task-id:modernize-scientific-stack"
    assert metadata["tasks"] == ["modernize-scientific-stack"]
    assert value_after(cmd, "--include-task-name") == "modernize-scientific-stack"
    assert value_after(cmd, "--n-attempts") == "1"
    assert value_after(cmd, "--n-concurrent") == "1"


def test_task_file_override_ad_hoc_reads_explicit_task_file(tmp_path: Path) -> None:
    task_file = tmp_path / "adhoc-tasks.txt"
    task_file.write_text("alpha\n# ignored\nbeta\n", encoding="utf-8")

    cmd, jobs_dir, metadata = build_harbor_command(
        phase=phase(tmp_path),
        arm=arm(),
        env={},
        mode="smoke",
        n_attempts=2,
        n_concurrent=1,
        task_id=None,
        task_file_override=str(task_file),
        ad_hoc_label="file-check",
    )

    assert jobs_dir == tmp_path / "results" / "phase3" / "ad-hoc" / "file-check" / "arm-router-test"
    assert metadata["tasks"] == ["alpha", "beta"]
    assert metadata["task_count"] == 2
    assert cmd.count("--include-task-name") == 2
    assert value_after(cmd, "--n-attempts") == "2"
    assert value_after(cmd, "--n-concurrent") == "1"


def test_task_id_and_task_file_are_mutually_exclusive(tmp_path: Path) -> None:
    task_file = tmp_path / "adhoc-tasks.txt"
    task_file.write_text("alpha\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="mutually exclusive"):
        build_harbor_command(
            phase=phase(tmp_path),
            arm=arm(),
            env={},
            mode="canary",
            n_attempts=None,
            n_concurrent=None,
            task_id="alpha",
            task_file_override=str(task_file),
            ad_hoc_label=None,
        )


def test_write_ad_hoc_metadata(tmp_path: Path) -> None:
    metadata_path = write_ad_hoc_metadata(tmp_path / "jobs", {"ad_hoc": True, "scored": False})

    assert metadata_path.exists()
    assert '"ad_hoc": true' in metadata_path.read_text(encoding="utf-8")
    assert '"scored": false' in metadata_path.read_text(encoding="utf-8")
