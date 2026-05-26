from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.lib.arms import (
    ConfigError,
    load_arm,
    load_phase,
    read_task_list,
    results_dir_for_mode,
    task_file_for_mode,
)


def parse_env_file(path: str | Path) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Secret/env file not found: {p}")

    out: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def build_env(base: dict[str, str], arm: dict[str, Any]) -> dict[str, str]:
    env = dict(base)

    for key in arm.get("clear_env") or []:
        env.pop(str(key), None)

    secret_file = arm.get("secret_file")
    secrets = parse_env_file(secret_file) if secret_file else {}

    for dest, source in (arm.get("secret_env_map") or {}).items():
        if source not in secrets:
            raise ConfigError(f"{secret_file} does not define {source}, required for {dest}")
        env[str(dest)] = str(secrets[source])

    for key, value in (arm.get("env") or {}).items():
        env[str(key)] = str(value)

    return env


def build_harbor_command(
    phase: dict[str, Any],
    arm: dict[str, Any],
    mode: str,
    n_attempts: int | None,
    n_concurrent: int | None,
) -> tuple[list[str], Path]:
    task_file = task_file_for_mode(phase, mode)
    tasks = read_task_list(task_file)

    jobs_dir = results_dir_for_mode(phase, arm, mode)

    attempts = n_attempts
    if attempts is None:
        attempts = 1 if mode in {"canary", "smoke"} else int(phase.get("n_attempts", 3))

    concurrent = n_concurrent
    if concurrent is None:
        concurrent = 1 if mode in {"canary", "smoke"} else int(phase.get("n_concurrent", 4))

    cmd = [
        "uv",
        "run",
        "harbor",
        "run",
        "--dataset",
        str(phase.get("dataset", "terminal-bench@2.0")),
        "--agent",
        str(arm.get("agent") or phase.get("agent", "claude-code")),
    ]

    model = arm.get("model")
    if model:
        cmd.extend(["--model", str(model)])

    for task in tasks:
        cmd.extend(["--include-task-name", task])

    cmd.extend(
        [
            "--n-attempts",
            str(attempts),
            "--n-concurrent",
            str(concurrent),
            "--jobs-dir",
            str(jobs_dir),
            "--yes",
        ]
    )

    return cmd, jobs_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a configured Harbor benchmark arm.")
    parser.add_argument("phase", help="Phase config name, e.g. phase2 or phase3-router")
    parser.add_argument("arm", help="Arm config name, e.g. anthropic-sonnet")
    parser.add_argument(
        "--mode",
        choices=["canary", "smoke", "full"],
        default="canary",
        help="Run mode. Defaults to canary for safety.",
    )
    parser.add_argument("--n-attempts", type=int, default=None)
    parser.add_argument("--n-concurrent", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        phase = load_phase(args.phase)
        arm = load_arm(args.arm)
        env = build_env(os.environ, arm)
        cmd, jobs_dir = build_harbor_command(
            phase=phase,
            arm=arm,
            mode=args.mode,
            n_attempts=args.n_attempts,
            n_concurrent=args.n_concurrent,
        )
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    print("phase:", args.phase)
    print("arm:", args.arm)
    print("mode:", args.mode)
    print("jobs_dir:", jobs_dir)
    print("command:")
    print(" ".join(shlex.quote(x) for x in cmd))

    if args.dry_run:
        return 0

    jobs_dir.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(cmd, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
