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
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
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


def build_r2_key(root: Path, path: Path, prefix: str, phase: str, mode: str, arm_id: str | None) -> str:
    rel = path.relative_to(root).as_posix()
    safe_arm = arm_id or "unknown-arm"
    run_timestamp = root.name

    # If R2_PREFIX is the same as the phase, avoid keys like
    # phase3/phase3/canary/...
    parts = [p.strip("/") for p in [prefix, phase, mode, safe_arm, run_timestamp, rel] if p]
    if parts and len(parts) > 1 and parts[0] == parts[1]:
        parts.pop(1)
    return "/".join(parts)


def collect_artifacts(run_dir: Path, r2_prefix: str, phase: str, mode: str, arm_id: str | None) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name not in ARTIFACT_NAMES:
            continue
        artifacts.append(
            Artifact(
                artifact_type=artifact_type(path),
                local_path=path.as_posix(),
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                r2_key=build_r2_key(run_dir, path, r2_prefix, phase, mode, arm_id),
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


def extract_trials(run_dir: Path) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*/result.json")):
        data = read_json(path)
        trial_name = path.parent.name
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
                "trial_dir": path.parent.as_posix(),
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
                "raw_result_path": path.as_posix(),
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
) -> dict[str, Any]:
    run_result = read_json(run_dir / "result.json")
    run_config = read_json(run_dir / "config.json")
    phase, storage_mode = detect_phase_mode(run_dir)
    logical_mode = resolve_logical_mode(storage_mode, logical_mode_override)
    suite_id = suite_id_override or default_suite_id(phase, logical_mode)
    arm_id = detect_arm(run_dir)

    git_commit = git_value(["git", "rev-parse", "HEAD"])
    branch = git_value(["git", "branch", "--show-current"])

    stats = run_result.get("stats", {})
    manifest = {
        "schema_version": 1,
        "run": {
            "phase": phase,
            "mode": logical_mode,
            "logical_mode": logical_mode,
            "storage_mode": storage_mode,
            "suite_id": suite_id,
            "github_run_id": github_run_id,
            "arm_id": arm_id,
            "run_dir": run_dir.as_posix(),
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
            "jobs_dir": run_config.get("jobs_dir"),
        },
        "trials": extract_trials(run_dir),
        "artifacts": [asdict(a) for a in collect_artifacts(run_dir, r2_prefix, phase, storage_mode, arm_id)],
    }
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


def upload_artifacts_to_r2(manifest: dict[str, Any], *, bucket: str, endpoint_url: str, access_key_id: str, secret_access_key: str, region_name: str = "auto") -> None:
    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("boto3 is required for --upload-r2. Run with: uv run --with boto3 ...") from exc

    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
    )

    uploaded = 0
    for artifact in manifest.get("artifacts", []):
        local_path = artifact.get("local_path")
        r2_key = artifact.get("r2_key")
        if not local_path or not r2_key:
            continue
        client.upload_file(local_path, bucket, r2_key)
        artifact["r2_uri"] = f"r2://{bucket}/{r2_key}"
        uploaded += 1

    print(f"uploaded {uploaded} artifacts to R2 bucket {bucket}")


def insert_manifest_into_postgres(manifest: dict[str, Any], *, db_url: str) -> None:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("psycopg[binary] is required for --insert-db. Run with: uv run --with 'psycopg[binary]' ...") from exc

    run = manifest["run"]
    arm_id = run.get("arm_id") or "unknown-arm"
    config = manifest.get("config_summary", {})
    phase = run.get("phase") or "unknown"
    mode = run.get("mode") or run.get("logical_mode") or "unknown"
    storage_mode = run.get("storage_mode")
    suite_id = run.get("suite_id")
    run_label = f"{arm_id}/{run.get('run_timestamp')}"

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
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
                    mode,
                    run_label,
                    run.get("git_commit"),
                    run.get("branch"),
                    None,
                    None,
                    None,
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
                        mode,
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
                    mode,
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
                        artifact.get("r2_uri"),
                        None,
                        artifact.get("sha256"),
                        artifact.get("size_bytes"),
                        artifact.get("r2_key"),
                    ),
                )

        conn.commit()

    print(f"upserted manifest into Postgres run_id={run_id} run_label={run_label}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to one timestamped Harbor result directory.")
    parser.add_argument("--manifest-out", default=None, help="Output manifest JSON path.")
    parser.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX", "phase3"))
    parser.add_argument("--logical-mode", choices=["canary", "smoke", "full", "ad-hoc"], default=None)
    parser.add_argument("--suite-id", default=None)
    parser.add_argument("--github-run-id", default=os.getenv("GITHUB_RUN_ID"))
    parser.add_argument("--dry-run", action="store_true", help="Build manifest only; do not upload or insert.")
    parser.add_argument("--upload-r2", action="store_true", help="Upload selected artifacts to Cloudflare R2.")
    parser.add_argument("--insert-db", action="store_true", help="Insert manifest metadata into Supabase/Postgres.")
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL"), help="Postgres connection URL. Defaults to SUPABASE_DB_URL.")
    parser.add_argument("--r2-bucket", default=os.getenv("R2_BUCKET"))
    parser.add_argument("--r2-endpoint-url", default=os.getenv("R2_ENDPOINT_URL"))
    parser.add_argument("--r2-access-key-id", default=os.getenv("R2_ACCESS_KEY_ID"))
    parser.add_argument("--r2-secret-access-key", default=os.getenv("R2_SECRET_ACCESS_KEY"))
    parser.add_argument("--r2-region", default=os.getenv("R2_REGION", "auto"))
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
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
        )

    if args.insert_db:
        insert_manifest_into_postgres(
            manifest,
            db_url=require_env("SUPABASE_DB_URL", args.db_url),
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
