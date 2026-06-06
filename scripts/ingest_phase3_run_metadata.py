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
import subprocess
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
    parts = run_dir.parts
    if "results" in parts:
        i = parts.index("results")
        phase = parts[i + 1] if len(parts) > i + 1 else "unknown"
        mode = parts[i + 2] if len(parts) > i + 2 else "unknown"
        return phase, mode
    return "unknown", "unknown"


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
    return f"{prefix}/{phase}/{mode}/{safe_arm}/{run_timestamp}/{rel}"


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


def extract_trials(run_dir: Path) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*/result.json")):
        data = read_json(path)
        trial_name = path.parent.name
        task_name = trial_name.split("__", 1)[0]
        result = data.get("result", {})
        agent = data.get("agent", {})
        trials.append(
            {
                "trial_dir": path.parent.as_posix(),
                "trial_name": trial_name,
                "task_name": task_name,
                "reward": data.get("reward"),
                "status": data.get("status") or result.get("status"),
                "exception_type": data.get("exception_type") or result.get("exception_type"),
                "runtime_seconds": data.get("runtime_seconds") or data.get("duration_seconds"),
                "model_name": agent.get("model_name") or data.get("model_name"),
                "raw_result_path": path.as_posix(),
            }
        )
    return trials


def build_manifest(run_dir: Path, r2_prefix: str) -> dict[str, Any]:
    run_result = read_json(run_dir / "result.json")
    run_config = read_json(run_dir / "config.json")
    phase, mode = detect_phase_mode(run_dir)
    arm_id = detect_arm(run_dir)

    git_commit = git_value(["git", "rev-parse", "HEAD"])
    branch = git_value(["git", "branch", "--show-current"])

    stats = run_result.get("stats", {})
    manifest = {
        "schema_version": 1,
        "run": {
            "phase": phase,
            "mode": mode,
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
        "artifacts": [asdict(a) for a in collect_artifacts(run_dir, r2_prefix, phase, mode, arm_id)],
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to one timestamped Harbor result directory.")
    parser.add_argument("--manifest-out", default=None, help="Output manifest JSON path.")
    parser.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX", "phase3"))
    parser.add_argument("--dry-run", action="store_true", help="Reserved for future network-enabled ingestion.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        raise SystemExit(f"run directory does not exist: {run_dir}")
    if not (run_dir / "result.json").exists():
        raise SystemExit(f"run directory is missing result.json: {run_dir}")

    manifest = build_manifest(run_dir, args.r2_prefix)

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
