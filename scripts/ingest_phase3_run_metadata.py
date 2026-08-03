#!/usr/bin/env python3
"""
Build a local ingestion manifest for a Phase 3 Harbor/Terminal-Bench result directory.

This is intentionally file-first and network-off by default. It prepares the metadata
we will later insert into Supabase Postgres and upload to Cloudflare R2.

Example:
  uv run python scripts/ingest_phase3_run_metadata.py \
    --run-dir results/phase3/canary/arm-router-glm-5.1/2026-06-04__12-40-42 \
    --manifest-out /tmp/phase3-ingest-manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import nullcontext
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.path_safety import (
    PathBoundaryError,
    iter_allowlisted_files,
    resolve_under,
)


ARTIFACT_NAMES = {
    "result.json",
    "config.json",
    "lock.json",
    "job.log",
    "trial.log",
    "exception.txt",
    "claude-code.txt",
    "trajectory.json",
    "ctrf.json",
    "reward.txt",
    "test-stdout.txt",
}


@dataclass
class Artifact:
    artifact_type: str
    local_path: str
    sha256: str
    size_bytes: int
    r2_key: str | None = None


class CanonicalIdentityCollision(RuntimeError):
    pass


class DependentTrialRowsError(RuntimeError):
    pass


class R2ObjectConflict(RuntimeError):
    pass


def read_json(
    path: Path,
    *,
    workspace: Path | None = None,
    parent: Path | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {}
    if workspace is not None and parent is not None:
        path = resolve_under(
            path,
            workspace=workspace,
            parent=parent,
            require_file=True,
            label="manifest JSON input",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Invalid JSON object in {path}")
    return value


def sha256_file(path: Path, *, workspace: Path, parent: Path) -> str:
    path = resolve_under(
        path,
        workspace=workspace,
        parent=parent,
        require_file=True,
        label="manifest artifact",
    )
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def detect_phase_mode(run_dir: Path) -> tuple[str, str]:
    """Return phase and physical storage mode from a result path."""
    parts = run_dir.parts
    if "results" in parts:
        i = parts.index("results")
        phase = parts[i + 1] if len(parts) > i + 1 else "unknown"
        storage_mode = parts[i + 2] if len(parts) > i + 2 else "unknown"
        return phase, storage_mode
    return "unknown", "unknown"


def resolve_logical_mode(storage_mode: str, explicit_mode: str | None = None) -> str:
    """Map physical result storage mode to sponsor-facing logical run mode."""
    if explicit_mode:
        return explicit_mode
    if storage_mode == "raw":
        return "full"
    return storage_mode


def default_suite_id(phase: str, logical_mode: str) -> str | None:
    if phase != "phase3":
        return None
    return {
        "canary": "phase3-canary-1",
        "smoke": "phase3-smoke-5",
        "full": "phase3-full-20",
    }.get(logical_mode)


def detect_arm(run_dir: Path) -> str | None:
    for part in run_dir.parts:
        if part.startswith("arm-"):
            return part.removeprefix("arm-")
    return None


def artifact_type(path: Path) -> str:
    name = path.name
    if name == "result.json":
        return "result"
    if name == "trajectory.json":
        return "trajectory"
    if name.endswith(".log"):
        return "log"
    if name == "claude-code.txt":
        return "agent_transcript"
    if name == "config.json":
        return "config"
    if name == "lock.json":
        return "lock"
    if name == "ctrf.json":
        return "verifier_ctrf"
    if name == "test-stdout.txt":
        return "verifier_stdout"
    if name == "reward.txt":
        return "verifier_reward"
    if name == "exception.txt":
        return "exception"
    return "artifact"


def _safe_identity_component(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._") or "unknown"


def canonical_run_label(run: dict[str, Any]) -> str:
    explicit = run.get("run_label")
    if explicit:
        return str(explicit)
    base = f"{run.get('arm_id') or 'unknown-arm'}/{run.get('run_timestamp')}"
    if run.get("execution_scoped") and run.get("execution_identity"):
        return (
            f"{base}/execution-"
            f"{_safe_identity_component(run['execution_identity'])}"
        )
    if run.get("execution_scoped") and run.get("github_run_id"):
        return (
            f"{base}/github-{_safe_identity_component(run['github_run_id'])}"
            f"/attempt-{_safe_identity_component(run.get('github_run_attempt') or 1)}"
        )
    return base


def assert_canonical_identity_compatible(
    *,
    incoming_github_run_id: Any,
    incoming_github_run_attempt: Any,
    existing_github_run_id: Any,
    existing_github_run_attempt: Any,
) -> None:
    if incoming_github_run_id is None:
        return
    if existing_github_run_id is None:
        raise CanonicalIdentityCollision(
            "canonical identity is already occupied by an execution without GitHub identity"
        )
    if str(existing_github_run_id) != str(incoming_github_run_id):
        raise CanonicalIdentityCollision(
            "canonical identity is already occupied by a different GitHub run"
        )
    if (
        existing_github_run_attempt is not None
        and incoming_github_run_attempt is not None
        and int(existing_github_run_attempt) != int(incoming_github_run_attempt)
    ):
        raise CanonicalIdentityCollision(
            "canonical identity is already occupied by a different GitHub run attempt"
        )


def normalize_run_relative_artifact_path(
    local_path: Any,
    *,
    run_dir: Any,
    run_timestamp: Any,
) -> str | None:
    if not local_path:
        return None
    path = PurePosixPath(str(local_path).replace("\\", "/"))
    parts = path.parts
    if ".." in parts:
        return None
    run_parts = PurePosixPath(str(run_dir).replace("\\", "/")).parts
    for index in range(len(parts) - len(run_parts), -1, -1):
        if tuple(parts[index : index + len(run_parts)]) == tuple(run_parts):
            relative = parts[index + len(run_parts) :]
            return PurePosixPath(*relative).as_posix() if relative else None
    timestamp = str(run_timestamp or "")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == timestamp:
            relative = parts[index + 1 :]
            return PurePosixPath(*relative).as_posix() if relative else None
    if not path.is_absolute():
        return path.as_posix().lstrip("./") or None
    return None


def reusable_r2_uri_map(
    rows: list[tuple[Any, Any, Any, Any]],
    *,
    run: dict[str, Any],
) -> dict[tuple[str, str, int], str]:
    reusable: dict[tuple[str, str, int], str] = {}
    for local_path, r2_uri, sha256, size_bytes in rows:
        relative = normalize_run_relative_artifact_path(
            local_path,
            run_dir=run.get("run_dir"),
            run_timestamp=run.get("run_timestamp"),
        )
        if relative and r2_uri and sha256 is not None and size_bytes is not None:
            reusable[(relative, str(sha256), int(size_bytes))] = str(r2_uri)
    return reusable


def resolve_reusable_r2_uri(
    artifact: dict[str, Any],
    *,
    run: dict[str, Any],
    reusable: dict[tuple[str, str, int], str],
) -> str | None:
    relative = normalize_run_relative_artifact_path(
        artifact.get("local_path"),
        run_dir=run.get("run_dir"),
        run_timestamp=run.get("run_timestamp"),
    )
    if not relative:
        return None
    return reusable.get(
        (
            relative,
            str(artifact.get("sha256") or ""),
            int(artifact.get("size_bytes") or 0),
        )
    )


def build_r2_key(
    root: Path,
    path: Path,
    prefix: str,
    phase: str,
    mode: str,
    arm_id: str | None,
    execution_scope: str | None = None,
    sha256: str | None = None,
) -> str:
    rel = path.relative_to(root).as_posix()
    safe_arm = arm_id or "unknown-arm"
    run_timestamp = root.name

    # If R2_PREFIX is the same as the phase, avoid keys like
    # phase3/phase3/canary/...
    parts = [
        p.strip("/")
        for p in [
            prefix,
            phase,
            mode,
            safe_arm,
            execution_scope,
            run_timestamp,
            f"sha256-{sha256}" if sha256 else None,
            rel,
        ]
        if p
    ]
    if parts and len(parts) > 1 and parts[0] == parts[1]:
        parts.pop(1)
    return "/".join(parts)


def collect_artifacts(
    run_dir: Path,
    r2_prefix: str,
    phase: str,
    mode: str,
    arm_id: str | None,
    *,
    workspace: Path,
    execution_scope: str | None = None,
) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in sorted(
        iter_allowlisted_files(
            run_dir,
            workspace=workspace,
            names=ARTIFACT_NAMES,
        )
    ):
        artifact_sha256 = sha256_file(path, workspace=workspace, parent=run_dir)
        artifacts.append(
            Artifact(
                artifact_type=artifact_type(path),
                local_path=path.relative_to(workspace).as_posix(),
                sha256=artifact_sha256,
                size_bytes=path.stat().st_size,
                r2_key=build_r2_key(
                    run_dir,
                    path,
                    r2_prefix,
                    phase,
                    mode,
                    arm_id,
                    execution_scope,
                    artifact_sha256,
                ),
            )
        )
    return artifacts



def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def is_zeroish(value: Any) -> bool:
    if value is None:
        return False
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def elapsed_seconds(started_at: Any, finished_at: Any) -> float | None:
    start = parse_iso_datetime(started_at)
    finish = parse_iso_datetime(finished_at)
    if start is None or finish is None:
        return None
    return max((finish - start).total_seconds(), 0.0)


def extract_reward(data: dict[str, Any]) -> Any:
    verifier = data.get("verifier_result") or {}
    rewards = verifier.get("rewards") or {}
    return first_present(
        rewards.get("reward"),
        data.get("reward"),
    )


def extract_exception_type(data: dict[str, Any], result: dict[str, Any]) -> str | None:
    value = first_present(
        data.get("exception_type"),
        result.get("exception_type"),
        data.get("exception_info"),
    )
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(first_present(value.get("type"), value.get("class"), value.get("name"), value.get("message"), "exception_info"))
    return str(value)


def extract_trial_runtime_seconds(data: dict[str, Any]) -> Any:
    return first_present(
        data.get("runtime_seconds"),
        data.get("duration_seconds"),
        elapsed_seconds(data.get("started_at"), data.get("finished_at")),
    )


def extract_trials(run_dir: Path, *, workspace: Path) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    trial_dirs: list[Path] = []
    for child in sorted(run_dir.iterdir()):
        if "__" not in child.name:
            continue
        if child.is_symlink():
            raise PathBoundaryError("trial directory must not be a symbolic link")
        if child.is_dir():
            trial_dirs.append(
                resolve_under(
                    child,
                    workspace=workspace,
                    parent=run_dir,
                    require_directory=True,
                    label="trial directory",
                )
            )
    for trial_dir in trial_dirs:
        path = resolve_under(
            trial_dir / "result.json",
            workspace=workspace,
            parent=trial_dir,
            require_file=True,
            label="trial result",
        )
        data = read_json(path, workspace=workspace, parent=trial_dir)
        trial_name = trial_dir.name
        task_name = trial_name.split("__", 1)[0]

        result = data.get("result") or {}
        agent = data.get("agent") or {}
        agent_result = data.get("agent_result") or {}
        agent_info = data.get("agent_info") or {}
        model_info = agent_info.get("model_info") or {}

        exception_type = extract_exception_type(data, result)
        cost_usd = first_present(agent_result.get("cost_usd"), data.get("cost_usd"))
        input_tokens = first_present(agent_result.get("n_input_tokens"), data.get("n_input_tokens"))
        cache_tokens = first_present(agent_result.get("n_cache_tokens"), data.get("n_cache_tokens"))
        output_tokens = first_present(agent_result.get("n_output_tokens"), data.get("n_output_tokens"))

        if (
            is_zeroish(cost_usd)
            and is_zeroish(input_tokens)
            and is_zeroish(cache_tokens)
            and is_zeroish(output_tokens)
        ):
            cost_usd = None
            input_tokens = None
            cache_tokens = None
            output_tokens = None

        trials.append(
            {
                "trial_dir": trial_dir.relative_to(workspace).as_posix(),
                "trial_name": trial_name,
                "task_name": task_name,
                "reward": extract_reward(data),
                "status": first_present(
                    data.get("status"),
                    result.get("status"),
                    "errors" if exception_type else "completed",
                ),
                "exception_type": exception_type,
                "runtime_seconds": extract_trial_runtime_seconds(data),
                "cost_usd": cost_usd,
                "input_tokens": input_tokens,
                "cache_tokens": cache_tokens,
                "output_tokens": output_tokens,
                "model_name": first_present(
                    agent.get("model_name"),
                    model_info.get("name"),
                    data.get("model_name"),
                ),
                "raw_result_path": path.relative_to(workspace).as_posix(),
            }
        )
    return trials


def build_manifest(
    run_dir: Path,
    r2_prefix: str,
    *,
    logical_mode_override: str | None = None,
    suite_id_override: str | None = None,
    github_run_id: str | None = None,
    github_run_attempt: int | None = None,
    execution_scoped: bool = False,
    execution_identity: str | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    workspace = (workspace or Path.cwd()).resolve(strict=True)
    run_dir = resolve_under(
        run_dir,
        workspace=workspace,
        require_directory=True,
        label="canonical run directory",
    )
    run_result = read_json(run_dir / "result.json", workspace=workspace, parent=run_dir)
    run_config = read_json(run_dir / "config.json", workspace=workspace, parent=run_dir)
    phase, storage_mode = detect_phase_mode(run_dir)
    logical_mode = resolve_logical_mode(storage_mode, logical_mode_override)
    suite_id = suite_id_override or default_suite_id(phase, logical_mode)
    arm_id = detect_arm(run_dir)
    execution_scope = (
        f"execution-{_safe_identity_component(execution_identity)}"
        if execution_scoped and execution_identity
        else (
            f"github-{_safe_identity_component(github_run_id)}"
            f"/attempt-{_safe_identity_component(github_run_attempt or 1)}"
            if execution_scoped and github_run_id
            else None
        )
    )

    git_commit = git_value(["git", "rev-parse", "HEAD"])
    branch = git_value(["git", "branch", "--show-current"])

    stats = run_result.get("stats", {})
    jobs_dir = run_config.get("jobs_dir")
    if isinstance(jobs_dir, str) and Path(jobs_dir).is_absolute():
        try:
            jobs_dir = Path(jobs_dir).resolve().relative_to(workspace).as_posix()
        except ValueError:
            jobs_dir = None
    manifest = {
        "schema_version": 1,
        "run": {
            "phase": phase,
            "mode": logical_mode,
            "logical_mode": logical_mode,
            "storage_mode": storage_mode,
            "suite_id": suite_id,
            "github_run_id": github_run_id,
            "github_run_attempt": github_run_attempt,
            "execution_scoped": bool(execution_scope),
            "execution_identity": execution_identity,
            "arm_id": arm_id,
            "run_dir": run_dir.relative_to(workspace).as_posix(),
            "run_timestamp": run_dir.name,
            "git_commit": git_commit,
            "branch": branch,
            "started_at": run_result.get("started_at"),
            "finished_at": run_result.get("finished_at"),
            "status": "completed" if stats.get("n_errored_trials", 0) == 0 else "errors",
            "n_total_trials": run_result.get("n_total_trials"),
            "n_completed_trials": stats.get("n_completed_trials"),
            "n_errored_trials": stats.get("n_errored_trials"),
            "cost_usd": stats.get("cost_usd"),
            "input_tokens": stats.get("n_input_tokens"),
            "cache_tokens": stats.get("n_cache_tokens"),
            "output_tokens": stats.get("n_output_tokens"),
        },
        "config_summary": {
            "agent": run_config.get("agent"),
            "model_name": run_config.get("model_name"),
            "dataset": run_config.get("dataset"),
            "jobs_dir": jobs_dir,
        },
        "trials": extract_trials(run_dir, workspace=workspace),
        "artifacts": [
            asdict(a)
            for a in collect_artifacts(
                run_dir,
                r2_prefix,
                phase,
                storage_mode,
                arm_id,
                workspace=workspace,
                execution_scope=execution_scope,
            )
        ],
    }
    manifest["run"]["run_label"] = canonical_run_label(manifest["run"])
    return manifest



def is_timestamped_run_dir(path: Path) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}", path.name) is not None


def ensure_timestamped_run_dir(run_dir: Path) -> None:
    if not is_timestamped_run_dir(run_dir):
        raise SystemExit(
            "run directory must be a timestamped Harbor result directory like "
            "results/phase3/canary/arm-router-x/2026-06-04__12-40-42; "
            f"got: {run_dir}"
        )

def require_env(name: str, value: str | None) -> str:
    if not value:
        raise SystemExit(f"Missing required environment variable or argument: {name}")
    return value


def create_r2_client(
    *,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    region_name: str = "auto",
) -> Any:
    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("boto3 is required for R2 publication") from exc
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
    )


def upload_artifacts_to_r2(
    manifest: dict[str, Any],
    *,
    bucket: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    region_name: str = "auto",
    workspace: Path | None = None,
    run_dir: Path | None = None,
    client: Any = None,
) -> Any:
    client = client or create_r2_client(
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        region_name=region_name,
    )
    workspace = (workspace or Path.cwd()).resolve(strict=True)
    run_dir = resolve_under(
        run_dir or workspace / str(manifest.get("run", {}).get("run_dir") or ""),
        workspace=workspace,
        require_directory=True,
        label="canonical run directory",
    )

    uploaded = 0
    reused = 0
    for artifact in manifest.get("artifacts", []):
        if artifact.get("r2_uri"):
            continue
        local_path = artifact.get("local_path")
        r2_key = artifact.get("r2_key")
        if not local_path or not r2_key:
            continue
        resolved = resolve_under(
            workspace / str(local_path),
            workspace=workspace,
            parent=run_dir,
            require_file=True,
            label="canonical artifact",
        )
        expected_size = int(artifact.get("size_bytes") or -1)
        expected_sha = str(artifact.get("sha256") or "")
        if resolved.stat().st_size != expected_size:
            raise PathBoundaryError("canonical artifact size changed before upload")
        if sha256_file(resolved, workspace=workspace, parent=run_dir) != expected_sha:
            raise PathBoundaryError("canonical artifact checksum changed before upload")
        try:
            response = client.head_object(Bucket=bucket, Key=str(r2_key))
        except Exception as exc:
            if not _is_r2_not_found(exc):
                raise
        else:
            metadata = {
                str(key).lower(): str(value)
                for key, value in (response.get("Metadata") or {}).items()
            }
            exact = (
                metadata.get("sha256") == expected_sha
                and metadata.get("size_bytes") == str(expected_size)
                and int(response.get("ContentLength", -1)) == expected_size
            )
            if not exact:
                raise R2ObjectConflict(
                    "existing canonical R2 object has conflicting integrity metadata"
                )
            artifact["r2_uri"] = f"r2://{bucket}/{r2_key}"
            reused += 1
            continue
        client.upload_file(
            resolved.as_posix(),
            bucket,
            r2_key,
            ExtraArgs={
                "Metadata": {
                    "sha256": expected_sha,
                    "size_bytes": str(expected_size),
                }
            },
        )
        artifact["r2_uri"] = f"r2://{bucket}/{r2_key}"
        uploaded += 1

    print(f"uploaded {uploaded} artifacts to R2; reused {reused} exact objects")
    return client


def _is_r2_not_found(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    code = str((response.get("Error") or {}).get("Code") or "")
    return code in {"404", "NoSuchKey", "NotFound"}


def dependent_trial_row_counts(cursor: Any, run_id: Any) -> dict[str, int]:
    queries = {
        "benchmark_trial_cost_coverage": """
            select count(*)
            from benchmark.benchmark_trial_cost_coverage coverage
            join benchmark.benchmark_trials trial on trial.id = coverage.trial_id
            where trial.run_id = %s
        """,
        "contamination_audits": """
            select count(*)
            from benchmark.contamination_audits audit
            join benchmark.benchmark_trials trial on trial.id = audit.trial_id
            where trial.run_id = %s
        """,
    }
    counts: dict[str, int] = {}
    for relation, query in queries.items():
        cursor.execute("select to_regclass(%s)", (f"benchmark.{relation}",))
        if cursor.fetchone()[0] is None:
            counts[relation] = 0
            continue
        cursor.execute(query, (run_id,))
        counts[relation] = int(cursor.fetchone()[0] or 0)
    return counts


def assert_trial_replacement_allowed(
    cursor: Any,
    *,
    run_id: Any,
    allow_dependent_trial_replacement: bool,
) -> dict[str, int]:
    counts = dependent_trial_row_counts(cursor, run_id)
    if (
        not allow_dependent_trial_replacement
        and any(count > 0 for count in counts.values())
    ):
        occupied = ", ".join(
            f"{name}={count}" for name, count in counts.items() if count > 0
        )
        raise DependentTrialRowsError(
            f"canonical trial replacement would delete dependent rows: {occupied}"
        )
    return counts


def insert_manifest_into_postgres(
    manifest: dict[str, Any],
    *,
    db_url: str | None = None,
    connection: Any = None,
    allow_dependent_trial_replacement: bool = False,
) -> dict[str, str]:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("psycopg[binary] is required for --insert-db. Run with: uv run --with 'psycopg[binary]' ...") from exc

    run = manifest["run"]
    arm_id = run.get("arm_id") or "unknown-arm"
    config = manifest.get("config_summary", {})
    phase = run.get("phase") or "unknown"
    logical_mode = run.get("logical_mode") or run.get("mode") or "unknown"
    storage_mode = run.get("storage_mode") or logical_mode
    # benchmark_runs.mode is a legacy/physical storage-mode key used by the
    # existing idempotency constraint. Sponsor-facing mode lives on arm runs.
    run_mode = storage_mode
    suite_id = run.get("suite_id")
    run_label = canonical_run_label(run)
    owns_connection = connection is None
    if owns_connection and not db_url:
        raise ValueError("db_url is required when no connection is supplied")

    connection_context = (
        psycopg.connect(db_url) if owns_connection else nullcontext(connection)
    )
    with connection_context as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    arm_run.github_run_id,
                    arm_run.raw_metadata ->> 'github_run_attempt'
                from benchmark.benchmark_arm_runs arm_run
                join benchmark.benchmark_runs benchmark_run
                  on benchmark_run.id = arm_run.run_id
                where benchmark_run.phase = %s
                  and benchmark_run.mode = %s
                  and benchmark_run.run_label = %s
                  and arm_run.arm_id = %s
                """,
                (phase, run_mode, run_label, arm_id),
            )
            for existing_github_run_id, existing_attempt in cur.fetchall():
                assert_canonical_identity_compatible(
                    incoming_github_run_id=run.get("github_run_id"),
                    incoming_github_run_attempt=run.get("github_run_attempt"),
                    existing_github_run_id=existing_github_run_id,
                    existing_github_run_attempt=existing_attempt,
                )

            cur.execute(
                """
                insert into benchmark.benchmark_arms (
                    arm_id, display_name, provider_family, backend_model,
                    router_model, agent_harness, config_path, active, raw_config
                )
                values (%s, %s, %s, %s, %s, %s, %s, true, %s)
                on conflict (arm_id) do update set
                    display_name = excluded.display_name,
                    provider_family = coalesce(excluded.provider_family, benchmark.benchmark_arms.provider_family),
                    backend_model = coalesce(excluded.backend_model, benchmark.benchmark_arms.backend_model),
                    router_model = excluded.router_model,
                    agent_harness = excluded.agent_harness,
                    config_path = coalesce(excluded.config_path, benchmark.benchmark_arms.config_path),
                    raw_config = excluded.raw_config,
                    updated_at = now()
                """,
                (
                    arm_id,
                    arm_id,
                    None,
                    None,
                    config.get("model_name"),
                    config.get("agent"),
                    None,
                    Jsonb(config),
                ),
            )

            cur.execute(
                """
                insert into benchmark.benchmark_runs (
                    phase, mode, run_label, git_commit, branch, runner_name,
                    runner_provider, runner_region, started_at, finished_at,
                    status, notes, raw_metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (phase, mode, run_label) do update set
                    git_commit = excluded.git_commit,
                    branch = excluded.branch,
                    runner_name = coalesce(excluded.runner_name, benchmark.benchmark_runs.runner_name),
                    runner_provider = coalesce(excluded.runner_provider, benchmark.benchmark_runs.runner_provider),
                    runner_region = coalesce(excluded.runner_region, benchmark.benchmark_runs.runner_region),
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    status = excluded.status,
                    notes = excluded.notes,
                    raw_metadata = excluded.raw_metadata
                returning id
                """,
                (
                    phase,
                    run_mode,
                    run_label,
                    run.get("git_commit"),
                    run.get("branch"),
                    run.get("runner_name"),
                    run.get("runner_provider"),
                    run.get("runner_region"),
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("status") or "unknown",
                    f"Imported from {run.get('run_dir')}",
                    Jsonb(run),
                ),
            )
            run_id = cur.fetchone()[0]

            if suite_id:
                cur.execute(
                    """
                    insert into benchmark.benchmark_eval_suites (
                        suite_id, display_name, benchmark, benchmark_version,
                        phase, suite_type, active, raw_metadata
                    )
                    values (%s, %s, 'terminal-bench', '2.0', %s, %s, true, %s)
                    on conflict (suite_id) do nothing
                    """,
                    (
                        suite_id,
                        suite_id,
                        phase,
                        logical_mode,
                        Jsonb({"source": "ingest_phase3_run_metadata.py"}),
                    ),
                )

            cur.execute(
                """
                insert into benchmark.benchmark_arm_runs (
                    run_id, arm_id, suite_id, logical_mode, storage_mode,
                    status, started_at, finished_at, n_trials, n_completed_trials,
                    n_errored_trials, total_cost_usd, input_tokens, cache_tokens,
                    output_tokens, github_run_id, raw_metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (run_id, arm_id) do update set
                    suite_id = excluded.suite_id,
                    logical_mode = excluded.logical_mode,
                    storage_mode = excluded.storage_mode,
                    status = excluded.status,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    n_trials = excluded.n_trials,
                    n_completed_trials = excluded.n_completed_trials,
                    n_errored_trials = excluded.n_errored_trials,
                    total_cost_usd = excluded.total_cost_usd,
                    input_tokens = excluded.input_tokens,
                    cache_tokens = excluded.cache_tokens,
                    output_tokens = excluded.output_tokens,
                    github_run_id = excluded.github_run_id,
                    raw_metadata = excluded.raw_metadata,
                    updated_at = now()
                returning id
                """,
                (
                    run_id,
                    arm_id,
                    suite_id,
                    logical_mode,
                    storage_mode,
                    run.get("status") or "unknown",
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("n_total_trials"),
                    run.get("n_completed_trials"),
                    run.get("n_errored_trials"),
                    run.get("cost_usd"),
                    run.get("input_tokens"),
                    run.get("cache_tokens"),
                    run.get("output_tokens"),
                    run.get("github_run_id"),
                    Jsonb(run),
                ),
            )
            arm_run_id = cur.fetchone()[0]

            # Replace imported child rows for this run. This makes repeated
            # ingestion deterministic instead of accumulating duplicate trials
            # and artifacts.
            #
            # Preserve existing R2 URIs when doing a metadata-only re-ingest
            # without --upload-r2. Otherwise a normalization/idempotency pass can
            # accidentally erase R2 artifact coverage for an already-uploaded run.
            cur.execute(
                """
                select local_path, r2_uri, sha256, size_bytes
                from benchmark.benchmark_artifacts
                where run_id = %s
                  and r2_uri is not null
                """,
                (run_id,),
            )
            existing_r2_uri_by_identity = reusable_r2_uri_map(
                cur.fetchall(),
                run=run,
            )

            assert_trial_replacement_allowed(
                cur,
                run_id=run_id,
                allow_dependent_trial_replacement=(
                    allow_dependent_trial_replacement
                ),
            )
            cur.execute("delete from benchmark.benchmark_artifacts where run_id = %s", (run_id,))
            cur.execute("delete from benchmark.benchmark_trials where run_id = %s", (run_id,))

            trial_id_by_dir: dict[str, Any] = {}
            for idx, trial in enumerate(manifest.get("trials", []), start=1):
                task_name = trial.get("task_name") or "unknown-task"
                task_id = f"terminal-bench-2.0:{task_name}"

                cur.execute(
                    """
                    insert into benchmark.benchmark_tasks (
                        task_id, benchmark, benchmark_version, task_name, active, raw_metadata
                    )
                    values (%s, 'terminal-bench', '2.0', %s, true, %s)
                    on conflict (task_id) do update set
                        task_name = excluded.task_name,
                        raw_metadata = excluded.raw_metadata
                    """,
                    (task_id, task_name, Jsonb({"source": "ingest_phase3_run_metadata.py"})),
                )

                cur.execute(
                    """
                    insert into benchmark.benchmark_trials (
                        run_id, arm_run_id, arm_id, task_id, attempt_index, reward,
                        exception_type, runtime_seconds, cost_usd,
                        input_tokens, cache_tokens, output_tokens,
                        result_local_path, notes, raw_result
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        run_id,
                        arm_run_id,
                        arm_id,
                        task_id,
                        idx,
                        trial.get("reward"),
                        trial.get("exception_type"),
                        trial.get("runtime_seconds"),
                        trial.get("cost_usd"),
                        trial.get("input_tokens"),
                        trial.get("cache_tokens"),
                        trial.get("output_tokens"),
                        trial.get("raw_result_path"),
                        trial.get("status"),
                        Jsonb(trial),
                    ),
                )
                trial_db_id = cur.fetchone()[0]
                if trial.get("trial_dir"):
                    trial_id_by_dir[trial["trial_dir"]] = trial_db_id

            for artifact in manifest.get("artifacts", []):
                local_path = artifact.get("local_path") or ""
                trial_db_id = None
                for trial_dir, candidate_id in trial_id_by_dir.items():
                    if local_path.startswith(trial_dir + "/"):
                        trial_db_id = candidate_id
                        break

                cur.execute(
                    """
                    insert into benchmark.benchmark_artifacts (
                        run_id, trial_id, artifact_type, local_path, r2_uri,
                        github_uri, sha256, size_bytes, retention_class, notes
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, 'pilot', %s)
                    """,
                    (
                        run_id,
                        trial_db_id,
                        artifact.get("artifact_type"),
                        local_path,
                        artifact.get("r2_uri")
                        or resolve_reusable_r2_uri(
                            artifact,
                            run=run,
                            reusable=existing_r2_uri_by_identity,
                        ),
                        None,
                        artifact.get("sha256"),
                        artifact.get("size_bytes"),
                        artifact.get("r2_key"),
                    ),
                )

        if owns_connection:
            conn.commit()

    if owns_connection:
        print(f"upserted manifest into Postgres run_id={run_id} run_label={run_label}")
    return {"run_id": str(run_id), "arm_run_id": str(arm_run_id)}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to one timestamped Harbor result directory.")
    parser.add_argument("--workspace", default=os.getenv("GITHUB_WORKSPACE") or os.getcwd())
    parser.add_argument("--manifest-out", default=None, help="Output manifest JSON path.")
    parser.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX", "phase3"))
    parser.add_argument("--logical-mode", choices=["canary", "smoke", "full", "ad-hoc"], default=None)
    parser.add_argument("--suite-id", default=None)
    parser.add_argument("--github-run-id", default=os.getenv("GITHUB_RUN_ID"))
    parser.add_argument("--dry-run", action="store_true", help="Build manifest only; do not upload or insert.")
    parser.add_argument("--upload-r2", action="store_true", help="Upload selected artifacts to Cloudflare R2.")
    parser.add_argument("--insert-db", action="store_true", help="Insert manifest metadata into Supabase/Postgres.")
    parser.add_argument(
        "--allow-dependent-trial-replacement",
        action="store_true",
        help=(
            "Maintenance only: permit replacement that can cascade-delete "
            "trial-linked derived rows."
        ),
    )
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"), help="Postgres connection URL. Defaults to SUPABASE_DB_URL.")
    parser.add_argument("--r2-bucket", default=os.getenv("R2_BUCKET"))
    parser.add_argument("--r2-endpoint-url", default=os.getenv("R2_ENDPOINT_URL"))
    parser.add_argument("--r2-access-key-id", default=os.getenv("R2_ACCESS_KEY_ID"))
    parser.add_argument("--r2-secret-access-key", default=os.getenv("R2_SECRET_ACCESS_KEY"))
    parser.add_argument("--r2-region", default=os.getenv("R2_REGION", "auto"))
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = workspace / run_dir
    if not run_dir.exists():
        raise SystemExit(f"run directory does not exist: {run_dir}")
    if not (run_dir / "result.json").exists():
        raise SystemExit(f"run directory is missing result.json: {run_dir}")
    ensure_timestamped_run_dir(run_dir)

    manifest = build_manifest(
        run_dir,
        args.r2_prefix,
        logical_mode_override=args.logical_mode,
        suite_id_override=args.suite_id,
        github_run_id=args.github_run_id,
        workspace=workspace,
    )

    if args.dry_run and (args.upload_r2 or args.insert_db):
        raise SystemExit("--dry-run cannot be combined with --upload-r2 or --insert-db")

    if args.upload_r2:
        upload_artifacts_to_r2(
            manifest,
            bucket=require_env("R2_BUCKET", args.r2_bucket),
            endpoint_url=require_env("R2_ENDPOINT_URL", args.r2_endpoint_url),
            access_key_id=require_env("R2_ACCESS_KEY_ID", args.r2_access_key_id),
            secret_access_key=require_env("R2_SECRET_ACCESS_KEY", args.r2_secret_access_key),
            region_name=args.r2_region or "auto",
            workspace=workspace,
            run_dir=run_dir,
        )

    if args.insert_db:
        insert_manifest_into_postgres(
            manifest,
            db_url=require_env("SUPABASE_DB_URL", args.db_url),
            allow_dependent_trial_replacement=(
                args.allow_dependent_trial_replacement
            ),
        )

    out = Path(args.manifest_out) if args.manifest_out else run_dir / "ingest_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"wrote {out}")
    print(
        "summary:",
        json.dumps(
            {
                "arm_id": manifest["run"]["arm_id"],
                "phase": manifest["run"]["phase"],
                "mode": manifest["run"]["mode"],
                "trials": len(manifest["trials"]),
                "artifacts": len(manifest["artifacts"]),
                "cost_usd": manifest["run"]["cost_usd"],
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
