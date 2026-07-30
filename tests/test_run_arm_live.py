from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.run_arm_live import main


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_local_dry_run_preserves_child_exit_and_structured_output(tmp_path: Path) -> None:
    live_dir = tmp_path / ".run" / "live"
    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--phase",
            "phase3",
            "--mode",
            "canary",
            "--live-run-id",
            "live-dry-test",
            "--workspace",
            str(tmp_path),
            "--live-dir",
            str(live_dir),
            "--dry-run-metadata",
            "--",
            sys.executable,
            "-c",
            "print('zero cost dry run')",
        ]
    )
    assert returncode == 0
    events = read_events(live_dir / "live-dry-test.ndjson")
    assert events[0]["event_type"] == "run_started"
    assert events[0]["payload"]["run_kind"] == "dry-run"
    assert events[0]["payload"]["scored"] is False
    assert any(event["event_type"] == "process_output_chunk" for event in events)
    assert events[-1]["event_type"] == "run_finished"
    assert events[-1]["payload"]["returncode"] == 0


def test_nonzero_child_exit_is_preserved(tmp_path: Path) -> None:
    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--phase",
            "phase3",
            "--mode",
            "canary",
            "--live-run-id",
            "live-failed-test",
            "--workspace",
            str(tmp_path),
            "--live-dir",
            str(tmp_path / "live"),
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        ]
    )
    assert returncode == 7


def test_wrapper_loads_runtime_env_file_values_into_redactor(tmp_path: Path) -> None:
    secret = "provider-secret-format::not-prefix-shaped"
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "provider.env").write_text(f"ODD_PROVIDER_LOGIN='{secret}'\n")
    live_dir = tmp_path / "live"
    returncode = main(
        [
            "--arm-id",
            "router-test",
            "--phase",
            "phase3",
            "--mode",
            "canary",
            "--live-run-id",
            "live-secret-test",
            "--workspace",
            str(tmp_path),
            "--live-dir",
            str(live_dir),
            "--",
            sys.executable,
            "-c",
            f"print({secret!r})",
        ]
    )
    assert returncode == 0
    assert secret not in (live_dir / "live-secret-test.ndjson").read_text()


def test_sigterm_is_forwarded_and_recorded_as_interrupted(tmp_path: Path) -> None:
    live_dir = tmp_path / "live"
    process = subprocess.Popen(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_arm_live.py"),
            "--arm-id",
            "router-test",
            "--phase",
            "phase3",
            "--mode",
            "canary",
            "--live-run-id",
            "live-signal-test",
            "--workspace",
            str(tmp_path),
            "--live-dir",
            str(live_dir),
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        ],
        cwd=REPO_ROOT,
    )
    event_path = live_dir / "live-signal-test.ndjson"
    deadline = time.time() + 5
    while time.time() < deadline and not event_path.exists():
        time.sleep(0.05)
    assert event_path.exists()

    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=8) == 143
    events = read_events(event_path)
    assert any(
        event["event_type"] == "exception"
        and event["payload"].get("status") == "interrupted"
        for event in events
    )
    assert events[-1]["payload"]["benchmark_status"] == "interrupted"


def test_wrapper_rejects_live_directory_outside_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-live-evidence"
    assert (
        main(
            [
                "--arm-id",
                "router-test",
                "--phase",
                "phase3",
                "--mode",
                "canary",
                "--workspace",
                str(tmp_path),
                "--live-dir",
                str(outside),
                "--",
                sys.executable,
                "-c",
                "raise AssertionError('child must not run')",
            ]
        )
        == 2
    )
    assert not outside.exists()


@pytest.mark.parametrize("symlink_name", [".run", ".run/live"])
def test_wrapper_rejects_symlinked_live_parents(
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
                "--phase",
                "phase3",
                "--mode",
                "canary",
                "--workspace",
                str(workspace),
                "--live-dir",
                ".run/live",
                "--",
                sys.executable,
                "-c",
                "raise AssertionError('child must not run')",
            ]
        )
        == 2
    )
