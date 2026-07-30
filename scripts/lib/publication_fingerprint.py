from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Mapping


FINGERPRINT_VERSION = 1
RUN_FIELDS = (
    "phase",
    "logical_mode",
    "storage_mode",
    "suite_id",
    "arm_id",
    "run_label",
    "run_timestamp",
    "github_run_id",
    "github_run_attempt",
    "status",
    "started_at",
    "finished_at",
    "n_total_trials",
    "n_completed_trials",
    "n_errored_trials",
    "cost_usd",
    "input_tokens",
    "cache_tokens",
    "output_tokens",
)
TRIAL_FIELDS = (
    "trial_name",
    "task_name",
    "reward",
    "status",
    "exception_type",
    "started_at",
    "finished_at",
    "runtime_seconds",
    "cost_usd",
    "input_tokens",
    "cache_tokens",
    "output_tokens",
    "model_name",
)


def _run_relative_path(value: Any, run: Mapping[str, Any]) -> str | None:
    if not value:
        return None
    path = PurePosixPath(str(value).replace("\\", "/"))
    if ".." in path.parts:
        return None
    run_dir = PurePosixPath(str(run.get("run_dir") or "").replace("\\", "/"))
    run_parts = run_dir.parts
    if run_parts:
        for index in range(len(path.parts) - len(run_parts), -1, -1):
            if path.parts[index : index + len(run_parts)] == run_parts:
                relative = path.parts[index + len(run_parts) :]
                return PurePosixPath(*relative).as_posix() if relative else None
    timestamp = str(run.get("run_timestamp") or "")
    if timestamp in path.parts:
        index = len(path.parts) - 1 - tuple(reversed(path.parts)).index(timestamp)
        relative = path.parts[index + 1 :]
        return PurePosixPath(*relative).as_posix() if relative else None
    if not path.is_absolute():
        return path.as_posix().lstrip("./") or None
    return None


def trial_fingerprint_records(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    run = manifest.get("run") or {}
    records: list[dict[str, Any]] = []
    for index, trial in enumerate(manifest.get("trials") or [], start=1):
        record = {field: trial.get(field) for field in TRIAL_FIELDS}
        record.update(
            {
                "attempt_index": int(trial.get("attempt_index") or index),
                "trial_path": _run_relative_path(trial.get("trial_dir"), run),
                "result_path": _run_relative_path(
                    trial.get("raw_result_path"),
                    run,
                ),
            }
        )
        records.append(record)
    return sorted(
        records,
        key=lambda row: (
            str(row.get("task_name") or ""),
            int(row.get("attempt_index") or 0),
            str(row.get("trial_name") or ""),
            str(row.get("trial_path") or ""),
        ),
    )


def artifact_fingerprint_records(
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    run = manifest.get("run") or {}
    records = [
        {
            "artifact_type": artifact.get("artifact_type"),
            "path": _run_relative_path(artifact.get("local_path"), run),
            "sha256": str(artifact.get("sha256") or ""),
            "size_bytes": int(artifact.get("size_bytes") or 0),
        }
        for artifact in manifest.get("artifacts") or []
    ]
    return sorted(
        records,
        key=lambda row: (
            str(row.get("path") or ""),
            str(row.get("artifact_type") or ""),
            str(row.get("sha256") or ""),
            int(row.get("size_bytes") or 0),
        ),
    )


def publication_fingerprint_payload(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    run = manifest.get("run") or {}
    return {
        "version": FINGERPRINT_VERSION,
        "run": {field: run.get(field) for field in RUN_FIELDS},
        "trials": trial_fingerprint_records(manifest),
        "artifacts": artifact_fingerprint_records(manifest),
    }


def publication_fingerprint(manifest: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        publication_fingerprint_payload(manifest),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
