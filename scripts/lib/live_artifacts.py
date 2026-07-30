from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts.ingest_phase3_run_metadata import ARTIFACT_NAMES, artifact_type
from scripts.lib.live_events import bounded_backoff_delays, safe_component, utc_now
from scripts.lib.path_safety import (
    PathBoundaryError,
    is_relative_to,
    iter_allowlisted_files,
    resolve_under,
)


TIMESTAMPED_RUN_DIR = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")
FINAL_TRIAL_STATUSES = {"completed", "failed", "error", "errors", "cancelled"}


def ensure_workspace_path(path: Path, workspace: Path) -> Path:
    workspace_resolved = workspace.resolve()
    candidate_path = path if path.is_absolute() else workspace_resolved / path
    if candidate_path.is_symlink():
        raise PathBoundaryError("approved path must not be a symbolic link")
    candidate = candidate_path.resolve()
    if not is_relative_to(candidate, workspace_resolved):
        raise ValueError(f"path is outside the supplied workspace: {path}")
    return candidate


def normalize_watch_roots(paths: Iterable[Path], workspace: Path) -> tuple[Path, ...]:
    roots: list[Path] = []
    for path in paths:
        candidate = ensure_workspace_path(path if path.is_absolute() else workspace / path, workspace)
        if candidate not in roots:
            roots.append(candidate)
    return tuple(roots)


def is_timestamped_run_dir(path: Path) -> bool:
    return bool(TIMESTAMPED_RUN_DIR.fullmatch(path.name))


def candidate_run_dirs(watch_roots: Iterable[Path]) -> list[Path]:
    candidates: list[Path] = []
    for root in watch_roots:
        if root.is_symlink():
            raise PathBoundaryError("watch root must not be a symbolic link")
        root_resolved = root.resolve()
        if is_timestamped_run_dir(root) and root.is_dir():
            candidates.append(root)
            continue
        if not root.is_dir():
            continue
        for directory, child_names, _files in os.walk(root):
            current = Path(directory)
            if not is_relative_to(current.resolve(), root_resolved):
                raise PathBoundaryError("run discovery escaped an approved watch root")
            depth = len(current.resolve().relative_to(root_resolved).parts)
            if depth >= 4:
                child_names[:] = []
                continue
            timestamped: list[str] = []
            retained: list[str] = []
            for name in child_names:
                child = current / name
                if child.is_symlink():
                    if is_timestamped_run_dir(child):
                        raise PathBoundaryError(
                            "timestamped run directory must not be a symbolic link"
                        )
                    continue
                if is_timestamped_run_dir(child):
                    timestamped.append(name)
                else:
                    retained.append(name)
            candidates.extend(current / name for name in timestamped)
            child_names[:] = retained
    return sorted(set(candidates))


def snapshot_run_dirs(
    watch_roots: Iterable[Path],
    *,
    workspace: Path | None = None,
) -> tuple[str, ...]:
    candidates = candidate_run_dirs(watch_roots)
    if workspace is None:
        return tuple(path.as_posix() for path in candidates)
    root = workspace.resolve()
    return tuple(path.resolve().relative_to(root).as_posix() for path in candidates)


def discover_run_dir(
    *,
    workspace: Path,
    watch_roots: Iterable[Path],
    explicit_run_dir: Path | None = None,
    baseline_run_dirs: Iterable[str] = (),
    started_after_epoch: float | None = None,
    require_final_result: bool = False,
) -> Path | None:
    """Discover exactly one current-workspace Harbor run or reject ambiguity."""
    roots = normalize_watch_roots(watch_roots, workspace)
    if explicit_run_dir is not None:
        candidate_path = (
            explicit_run_dir
            if explicit_run_dir.is_absolute()
            else workspace / explicit_run_dir
        )
        candidate = resolve_under(
            candidate_path,
            workspace=workspace,
            approved_roots=[root for root in roots if root.exists()],
            require_directory=True,
            label="run directory",
        )
        if not is_timestamped_run_dir(candidate):
            raise ValueError(f"run directory is not timestamped: {candidate}")
        if require_final_result:
            resolve_under(
                candidate / "result.json",
                workspace=workspace,
                parent=candidate,
                require_file=True,
                label="final run result",
            )
        return candidate

    baseline = {
        (Path(value) if Path(value).is_absolute() else workspace / value).resolve()
        for value in baseline_run_dirs
    }
    candidates = []
    for path in candidate_run_dirs(roots):
        candidate = resolve_under(
            path,
            workspace=workspace,
            approved_roots=[root for root in roots if root.exists()],
            require_directory=True,
            label="discovered run directory",
        )
        if candidate not in baseline:
            candidates.append(candidate)
    if started_after_epoch is not None:
        candidates = [
            path
            for path in candidates
            if path.stat().st_mtime >= started_after_epoch - 2.0
        ]
    if require_final_result:
        finalized: list[Path] = []
        for path in candidates:
            result_path = path / "result.json"
            if result_path.is_symlink():
                raise PathBoundaryError("final run result must not be a symbolic link")
            if not result_path.is_file():
                continue
            resolve_under(
                result_path,
                workspace=workspace,
                parent=path,
                require_file=True,
                label="final run result",
            )
            finalized.append(path)
        candidates = finalized
    if not candidates:
        return None
    if len(candidates) > 1:
        listed = ", ".join(path.as_posix() for path in candidates)
        raise ValueError(f"ambiguous current-job run directory discovery: {listed}")
    return candidates[0]


def read_json_if_complete(
    path: Path,
    *,
    workspace: Path,
    parent: Path,
) -> dict[str, Any] | None:
    try:
        resolved = resolve_under(
            path,
            workspace=workspace,
            parent=parent,
            require_file=True,
            label="result file",
        )
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _first(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _exception_details(value: Any) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if isinstance(value, str):
        return value.split(":", 1)[0][:200], value[:1_000]
    if isinstance(value, Mapping):
        exception_type = _first(value.get("type"), value.get("class"), value.get("name"))
        summary = _first(value.get("message"), value.get("traceback"), exception_type)
        return (
            str(exception_type)[:200] if exception_type is not None else "exception_info",
            str(summary)[:1_000] if summary is not None else None,
        )
    return type(value).__name__, str(value)[:1_000]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _runtime_seconds(started_at: Any, finished_at: Any) -> float | None:
    started = _parse_datetime(started_at)
    finished = _parse_datetime(finished_at)
    if started is None or finished is None:
        return None
    return max((finished - started).total_seconds(), 0.0)


def parse_trial_result(
    result_path: Path,
    *,
    live_run_id: str,
    run_dir: Path,
    workspace: Path | None = None,
) -> dict[str, Any] | None:
    workspace = workspace or run_dir
    trial_dir = resolve_under(
        result_path.parent,
        workspace=workspace,
        parent=run_dir,
        require_directory=True,
        label="trial directory",
    )
    data = read_json_if_complete(
        result_path,
        workspace=workspace,
        parent=trial_dir,
    )
    if data is None:
        return None

    finished_at = data.get("finished_at")
    status_value = str(data.get("status") or "").lower()
    exception_type, exception_summary = _exception_details(data.get("exception_info"))
    has_final_evidence = bool(
        finished_at
        and (
            isinstance(data.get("verifier_result"), Mapping)
            or exception_type
            or status_value in FINAL_TRIAL_STATUSES
        )
    )
    if not has_final_evidence:
        return None

    trial_key = str(data.get("trial_name") or result_path.parent.name)
    task_id = str(data.get("task_name") or trial_key.split("__", 1)[0])
    verifier_result = data.get("verifier_result") or {}
    rewards = verifier_result.get("rewards") or {}
    reward = _first(rewards.get("reward"), data.get("reward"))
    agent_result = data.get("agent_result") or {}
    try:
        successful_reward = reward is not None and float(reward) >= 1.0
    except (TypeError, ValueError):
        successful_reward = False
    if exception_type:
        status = "exception"
    elif successful_reward:
        status = "succeeded"
    else:
        status = "failed"

    relative_dir = trial_dir.relative_to(run_dir.resolve(strict=True)).as_posix()
    return {
        "live_run_id": live_run_id,
        "trial_key": trial_key,
        "task_id": task_id,
        "attempt_index": None,
        "status": status,
        "reward": reward,
        "exception_type": exception_type,
        "exception_summary": exception_summary,
        "runtime_seconds": _runtime_seconds(data.get("started_at"), finished_at),
        "input_tokens": agent_result.get("n_input_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cost_usd": agent_result.get("cost_usd"),
        "started_at": data.get("started_at"),
        "finished_at": finished_at,
        "relative_local_path": relative_dir,
        "stability_state": "complete",
        "completion_evidence": {
            "parseable_result": True,
            "finished_at": bool(finished_at),
            "verifier_result": isinstance(data.get("verifier_result"), Mapping),
            "exception_state": bool(exception_type),
        },
        "raw_result": {
            "trial_name": trial_key,
            "task_name": task_id,
            "status": status,
            "reward": reward,
            "exception_type": exception_type,
            "model_name": ((data.get("agent_info") or {}).get("model_info") or {}).get("name"),
        },
    }


@dataclass
class FileObservation:
    size_bytes: int
    modified_ns: int
    unchanged_since: float


class FileStabilityTracker:
    def __init__(self) -> None:
        self._observations: dict[Path, FileObservation] = {}

    def stable(
        self,
        path: Path,
        *,
        stability_seconds: float,
        now: float | None = None,
        workspace: Path | None = None,
        parent: Path | None = None,
    ) -> bool:
        current_time = time.monotonic() if now is None else now
        try:
            candidate = (
                resolve_under(
                    path,
                    workspace=workspace,
                    parent=parent,
                    require_file=True,
                    label="stability candidate",
                )
                if workspace is not None and parent is not None
                else path
            )
            if candidate.is_symlink():
                raise PathBoundaryError("stability candidate must not be a symbolic link")
            stat = candidate.stat()
        except OSError:
            self._observations.pop(path, None)
            return False
        previous = self._observations.get(path)
        signature = (stat.st_size, stat.st_mtime_ns)
        if previous is None or signature != (previous.size_bytes, previous.modified_ns):
            self._observations[path] = FileObservation(
                size_bytes=stat.st_size,
                modified_ns=stat.st_mtime_ns,
                unchanged_since=current_time,
            )
            return stability_seconds <= 0
        return current_time - previous.unchanged_since >= max(stability_seconds, 0.0)


def sha256_file(
    path: Path,
    *,
    workspace: Path,
    parent: Path,
) -> str:
    resolved = resolve_under(
        path,
        workspace=workspace,
        parent=parent,
        require_file=True,
        label="artifact",
    )
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_trial_artifacts(
    trial_dir: Path,
    tracker: FileStabilityTracker,
    *,
    stability_seconds: float,
    now: float | None = None,
    workspace: Path | None = None,
    run_dir: Path | None = None,
) -> list[Path]:
    workspace = workspace or trial_dir
    run_dir = run_dir or trial_dir
    resolved_trial = resolve_under(
        trial_dir,
        workspace=workspace,
        parent=run_dir,
        require_directory=True,
        label="trial directory",
    )
    artifacts: list[Path] = []
    for path in sorted(
        iter_allowlisted_files(
            resolved_trial,
            workspace=workspace,
            names=ARTIFACT_NAMES,
        )
    ):
        if tracker.stable(
            path,
            stability_seconds=stability_seconds,
            now=now,
            workspace=workspace,
            parent=resolved_trial,
        ):
            artifacts.append(path)
    return artifacts


def progressive_r2_key(
    *,
    prefix: str,
    github_run_id: str | None,
    github_run_attempt: int | str | None,
    runner_name: str | None,
    live_run_id: str,
    arm_id: str,
    mode: str,
    trial_key: str | None,
    relative_path: str,
    sha256: str,
) -> str:
    components = [
        prefix.strip("/") or "phase3",
        "live",
        f"github-{safe_component(github_run_id, fallback='local')}",
        f"attempt-{safe_component(str(github_run_attempt or 1))}",
        f"runner-{safe_component(runner_name, fallback='local-runner')}",
        safe_component(live_run_id, limit=120),
        safe_component(arm_id),
        safe_component(mode),
        safe_component(trial_key, fallback="run-root", limit=100),
        f"sha256-{safe_component(sha256, limit=64)}",
    ]
    safe_relative = "/".join(safe_component(part, limit=120) for part in Path(relative_path).parts)
    return "/".join((*components, safe_relative))


class ProgressiveR2Uploader:
    """Idempotently upload stable files; client creation remains lazy."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
        client: Any = None,
        sleep: Any = time.sleep,
    ) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self._client = client
        self.sleep = sleep
        self._uploaded: set[tuple[str, str]] = set()

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - CLI installs dependency
                raise RuntimeError("boto3 is required for progressive R2 upload") from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )
        return self._client

    def upload(
        self,
        path: Path,
        key: str,
        sha256: str,
        size_bytes: int,
        *,
        workspace: Path,
        parent: Path,
    ) -> bool:
        identity = (key, sha256)
        if identity in self._uploaded:
            return False
        resolved = resolve_under(
            path,
            workspace=workspace,
            parent=parent,
            require_file=True,
            label="progressive artifact",
        )
        if resolved.stat().st_size != size_bytes:
            raise PathBoundaryError("progressive artifact changed before upload")
        if sha256_file(resolved, workspace=workspace, parent=parent) != sha256:
            raise PathBoundaryError("progressive artifact checksum changed before upload")
        last_error: Exception | None = None
        for retry_delay in (*bounded_backoff_delays(attempts=3), None):
            try:
                self._get_client().upload_file(
                    resolved.as_posix(),
                    self.bucket,
                    key,
                    ExtraArgs={
                        "Metadata": {
                            "sha256": sha256,
                            "size_bytes": str(size_bytes),
                        }
                    },
                )
                self._uploaded.add(identity)
                return True
            except Exception as exc:
                last_error = exc
                if retry_delay is not None:
                    self.sleep(retry_delay)
        assert last_error is not None
        raise last_error

    def uri(self, key: str) -> str:
        return f"r2://{self.bucket}/{key}"


def artifact_row(
    *,
    live_run_id: str,
    run_dir: Path,
    path: Path,
    trial_key: str | None,
    r2_uri: str | None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    workspace = workspace or run_dir
    parent = path.parent
    resolve_under(
        parent,
        workspace=workspace,
        parent=run_dir,
        require_directory=True,
        label="trial directory",
    )
    resolved = resolve_under(
        path,
        workspace=workspace,
        parent=parent,
        require_file=True,
        label="artifact",
    )
    return {
        "live_run_id": live_run_id,
        "trial_key": trial_key,
        "artifact_type": artifact_type(path),
        "relative_local_path": resolved.relative_to(run_dir.resolve()).as_posix(),
        "r2_uri": r2_uri,
        "sha256": sha256_file(resolved, workspace=workspace, parent=parent),
        "size_bytes": resolved.stat().st_size,
        "stability_state": "uploaded" if r2_uri else "stable",
        "uploaded_at": utc_now() if r2_uri else None,
        "raw_metadata": {},
    }


def parse_r2_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("r2://"):
        raise ValueError("R2 URI must use r2://")
    bucket, separator, key = uri[5:].partition("/")
    if not bucket or not separator or not key:
        raise ValueError("R2 URI is incomplete")
    return bucket, key


def verify_r2_object(
    client: Any,
    *,
    uri: str,
    sha256: str,
    size_bytes: int,
) -> tuple[bool, str | None]:
    try:
        bucket, key = parse_r2_uri(uri)
        response = client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        return False, f"object lookup failed ({type(exc).__name__})"
    metadata = {
        str(key).lower(): str(value)
        for key, value in (response.get("Metadata") or {}).items()
    }
    if metadata.get("sha256") != sha256:
        return False, "object checksum metadata mismatch"
    if metadata.get("size_bytes") != str(size_bytes):
        return False, "object size metadata mismatch"
    if int(response.get("ContentLength", -1)) != size_bytes:
        return False, "object content length mismatch"
    return True, None


def verify_manifest_r2_objects(
    manifest: Mapping[str, Any],
    *,
    client: Any,
) -> list[str]:
    errors: list[str] = []
    for artifact in manifest.get("artifacts") or []:
        uri = artifact.get("r2_uri")
        if not uri:
            errors.append("artifact is missing an R2 URI")
            continue
        ok, reason = verify_r2_object(
            client,
            uri=str(uri),
            sha256=str(artifact.get("sha256") or ""),
            size_bytes=int(artifact.get("size_bytes") or 0),
        )
        if not ok:
            errors.append(
                f"R2 integrity failed for {artifact.get('r2_key') or 'artifact'}: {reason}"
            )
    return errors


def verify_manifest_local_artifacts(
    manifest: Mapping[str, Any],
    *,
    workspace: Path,
    run_dir: Path,
) -> list[str]:
    errors: list[str] = []
    for artifact in manifest.get("artifacts") or []:
        try:
            path = resolve_under(
                workspace / str(artifact.get("local_path") or ""),
                workspace=workspace,
                parent=run_dir,
                require_file=True,
                label="canonical artifact",
            )
            expected_size = int(artifact.get("size_bytes") or -1)
            expected_sha = str(artifact.get("sha256") or "")
            if path.stat().st_size != expected_size:
                errors.append("canonical artifact size changed after manifest collection")
                continue
            if sha256_file(path, workspace=workspace, parent=run_dir) != expected_sha:
                errors.append("canonical artifact checksum changed after manifest collection")
        except (OSError, PathBoundaryError, TypeError, ValueError):
            errors.append("canonical artifact path became unsafe after manifest collection")
    return errors


def required_r2_environment(env: Mapping[str, str] | None = None) -> tuple[list[str], dict[str, str]]:
    source = os.environ if env is None else env
    required = (
        "R2_BUCKET",
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_REGION",
    )
    missing = [name for name in required if not source.get(name)]
    return missing, {name: source[name] for name in required if source.get(name)}
