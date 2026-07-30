from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Mapping

from scripts.lib.live_artifacts import (
    FileStabilityTracker,
    ProgressiveR2Uploader,
    artifact_row,
    discover_run_dir,
    parse_trial_result,
    progressive_r2_key,
    stable_trial_artifacts,
)
from scripts.lib.live_db import BatchedDatabasePublisher
from scripts.lib.live_events import LocalEventWriter, utc_now
from scripts.lib.path_safety import PathBoundaryError, resolve_under


class ProgressiveRunMonitor:
    """Low-priority scanner restricted to explicit current-workspace roots."""

    def __init__(
        self,
        *,
        live_run_id: str,
        workspace: Path,
        watch_roots: tuple[Path, ...],
        baseline_run_dirs: tuple[str, ...],
        started_after_epoch: float,
        arm_id: str,
        phase: str,
        mode: str,
        github_run_id: str | None,
        github_run_attempt: int | str | None,
        runner_name: str | None,
        writer: LocalEventWriter,
        publisher: BatchedDatabasePublisher | None,
        uploader: ProgressiveR2Uploader | None,
        r2_prefix: str,
        scan_seconds: float = 10.0,
        stability_seconds: float = 15.0,
    ) -> None:
        self.live_run_id = live_run_id
        self.workspace = workspace
        self.watch_roots = watch_roots
        self.baseline_run_dirs = baseline_run_dirs
        self.started_after_epoch = started_after_epoch
        self.arm_id = arm_id
        self.phase = phase
        self.mode = mode
        self.github_run_id = github_run_id
        self.github_run_attempt = github_run_attempt
        self.runner_name = runner_name
        self.writer = writer
        self.publisher = publisher
        self.uploader = uploader
        self.r2_prefix = r2_prefix
        self.scan_seconds = max(scan_seconds, 0.1)
        self.stability_seconds = max(stability_seconds, 0.0)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tracker = FileStabilityTracker()
        self._run_dir: Path | None = None
        self._detected: set[str] = set()
        self._verifier_started: set[str] = set()
        self._finished: dict[str, dict[str, Any]] = {}
        self._published_artifacts: set[tuple[str, str]] = set()
        self._last_cost_state: tuple[Any, ...] | None = None
        self.warning_count = 0

    @property
    def run_dir(self) -> Path | None:
        return self._run_dir

    @property
    def trials(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._finished.values())

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="live-artifact-monitor", daemon=True)
        self._thread.start()

    def stop(self, *, timeout: float = 15.0, final_scan: bool = True) -> bool:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(timeout, 0.0))
        if final_scan:
            try:
                self.scan_once(final=True)
            except Exception as exc:
                self._warning(f"final progressive scan failed ({type(exc).__name__})")
        return self._thread is None or not self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.wait(self.scan_seconds):
            try:
                self.scan_once()
            except Exception as exc:
                self._warning(f"progressive scan failed ({type(exc).__name__})")

    def scan_once(self, *, final: bool = False) -> None:
        if self._run_dir is None:
            self._run_dir = discover_run_dir(
                workspace=self.workspace,
                watch_roots=self.watch_roots,
                baseline_run_dirs=self.baseline_run_dirs,
                started_after_epoch=self.started_after_epoch,
            )
            if self._run_dir is None:
                return
            self.writer.emit(
                "task_or_trial_detected",
                message="Harbor run directory detected",
                relative_run_dir=self._run_dir.relative_to(self.workspace).as_posix(),
            )

        trial_dirs: list[Path] = []
        for path in sorted(self._run_dir.iterdir()):
            if "__" not in path.name:
                continue
            if path.is_symlink():
                raise PathBoundaryError("trial directory must not be a symbolic link")
            if path.is_dir():
                trial_dirs.append(
                    resolve_under(
                        path,
                        workspace=self.workspace,
                        parent=self._run_dir,
                        require_directory=True,
                        label="trial directory",
                    )
                )
        for trial_dir in trial_dirs:
            trial_key = trial_dir.name
            if trial_key not in self._detected:
                self._detected.add(trial_key)
                self.writer.emit(
                    "task_or_trial_detected",
                    trial_key=trial_key,
                    task_id=trial_key.split("__", 1)[0],
                )
                self.writer.emit(
                    "trial_started",
                    trial_key=trial_key,
                    task_id=trial_key.split("__", 1)[0],
                )

            verifier_path = trial_dir / "verifier"
            if verifier_path.exists() and trial_key not in self._verifier_started:
                self._verifier_started.add(trial_key)
                self.writer.emit("verifier_started", trial_key=trial_key)

            result_path = trial_dir / "result.json"
            result_stable = self._tracker.stable(
                result_path,
                stability_seconds=0.0 if final else self.stability_seconds,
                workspace=self.workspace,
                parent=trial_dir,
            )
            parsed = (
                parse_trial_result(
                    result_path,
                    live_run_id=self.live_run_id,
                    run_dir=self._run_dir,
                    workspace=self.workspace,
                )
                if result_stable
                else None
            )
            if parsed is None:
                continue

            first_completion = trial_key not in self._finished
            self._finished[trial_key] = parsed
            if self.publisher:
                self.publisher.submit_trial(parsed)
            if first_completion:
                if trial_key in self._verifier_started:
                    self.writer.emit(
                        "verifier_finished",
                        trial_key=trial_key,
                        status=parsed["status"],
                    )
                self.writer.emit(
                    "trial_finished",
                    trial_key=trial_key,
                    task_id=parsed["task_id"],
                    status=parsed["status"],
                    reward=parsed["reward"],
                    exception_type=parsed["exception_type"],
                    runtime_seconds=parsed["runtime_seconds"],
                )

            for path in stable_trial_artifacts(
                trial_dir,
                self._tracker,
                stability_seconds=0.0 if final else self.stability_seconds,
                workspace=self.workspace,
                run_dir=self._run_dir,
            ):
                self._publish_artifact(path, trial_key)

        self._publish_aggregates()

    def _publish_artifact(self, path: Path, trial_key: str) -> None:
        assert self._run_dir is not None
        base_row = artifact_row(
            live_run_id=self.live_run_id,
            run_dir=self._run_dir,
            path=path,
            trial_key=trial_key,
            r2_uri=None,
            workspace=self.workspace,
        )
        identity = (base_row["relative_local_path"], base_row["sha256"])
        if identity in self._published_artifacts:
            return

        self.writer.emit(
            "artifact_stable",
            trial_key=trial_key,
            artifact_type=base_row["artifact_type"],
            relative_local_path=base_row["relative_local_path"],
            sha256=base_row["sha256"],
            size_bytes=base_row["size_bytes"],
        )
        row = base_row
        if self.uploader is not None:
            key = progressive_r2_key(
                prefix=self.r2_prefix,
                github_run_id=self.github_run_id,
                github_run_attempt=self.github_run_attempt,
                runner_name=self.runner_name,
                live_run_id=self.live_run_id,
                arm_id=self.arm_id,
                mode=self.mode,
                trial_key=trial_key,
                relative_path=base_row["relative_local_path"],
                sha256=base_row["sha256"],
            )
            try:
                uploaded = self.uploader.upload(
                    path,
                    key,
                    base_row["sha256"],
                    base_row["size_bytes"],
                    workspace=self.workspace,
                    parent=path.parent,
                )
                row = {
                    **base_row,
                    "r2_uri": self.uploader.uri(key),
                    "stability_state": "uploaded",
                    "uploaded_at": utc_now(),
                }
                if uploaded:
                    self.writer.emit(
                        "artifact_uploaded",
                        trial_key=trial_key,
                        artifact_type=row["artifact_type"],
                        relative_local_path=row["relative_local_path"],
                        r2_uri=row["r2_uri"],
                        sha256=row["sha256"],
                        size_bytes=row["size_bytes"],
                    )
            except Exception as exc:
                self._warning(
                    f"progressive artifact upload failed for {base_row['relative_local_path']} "
                    f"({type(exc).__name__})"
                )
        if self.publisher:
            self.publisher.submit_artifact(row)
        if self.uploader is None or row.get("r2_uri"):
            self._published_artifacts.add(identity)

    def aggregate_row(self) -> dict[str, Any]:
        values = tuple(self._finished.values())
        return {
            "completed_trial_count": len(values),
            "success_count": sum(trial["status"] == "succeeded" for trial in values),
            "failure_count": sum(trial["status"] == "failed" for trial in values),
            "exception_count": sum(trial["status"] == "exception" for trial in values),
            "observed_cost_usd": _sum_optional(values, "cost_usd"),
            "input_tokens": _sum_optional(values, "input_tokens"),
            "cache_tokens": _sum_optional(values, "cache_tokens"),
            "output_tokens": _sum_optional(values, "output_tokens"),
        }

    def _publish_aggregates(self) -> None:
        aggregates = self.aggregate_row()
        state = tuple(aggregates.values())
        if state == self._last_cost_state:
            return
        self._last_cost_state = state
        if self.publisher:
            self.publisher.submit_run(
                {
                    "live_run_id": self.live_run_id,
                    "arm_id": self.arm_id,
                    "phase": self.phase,
                    "mode": self.mode,
                    **aggregates,
                }
            )
        self.writer.emit("cost_update", **aggregates)

    def _warning(self, message: str) -> None:
        self.warning_count += 1
        self.writer.emit("publication_warning", message=message)


def _sum_optional(rows: tuple[Mapping[str, Any], ...], key: str) -> Any:
    values = [row.get(key) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return sum(values)
