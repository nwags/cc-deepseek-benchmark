from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.lib.arms import (
    ConfigError,
    job_dir_name,
    load_arm,
    load_phase,
    read_task_list,
    results_dir_for_mode,
    task_file_for_mode,
)


SENSITIVE_KEY_FRAGMENTS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
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


def agent_env_keys_for_arm(arm: dict[str, Any]) -> list[str]:
    explicit = arm.get("agent_env_keys")
    if explicit is not None:
        return [str(key) for key in explicit]

    keys: list[str] = []

    for dest in (arm.get("secret_env_map") or {}).keys():
        keys.append(str(dest))

    for key in (arm.get("env") or {}).keys():
        keys.append(str(key))

    return sorted(dict.fromkeys(keys))


def is_sensitive_env_key(key: str) -> bool:
    upper = key.upper()
    return any(fragment in upper for fragment in SENSITIVE_KEY_FRAGMENTS)


def redact_agent_env_arg(arg: str) -> str:
    if "=" not in arg:
        return arg

    key, value = arg.split("=", 1)
    if is_sensitive_env_key(key):
        return f"{key}=<redacted>"

    return f"{key}={value}"


def redact_command(cmd: list[str]) -> list[str]:
    redacted: list[str] = []
    i = 0

    while i < len(cmd):
        part = cmd[i]
        redacted.append(part)

        if part == "--agent-env" and i + 1 < len(cmd):
            redacted.append(redact_agent_env_arg(cmd[i + 1]))
            i += 2
            continue

        i += 1

    return redacted


def slugify_label(value: str | None) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9._-]+", "-", raw)
    raw = re.sub(r"-+", "-", raw).strip("-._")
    return raw or "manual"


def resolve_task_selection(
    phase: dict[str, Any],
    mode: str,
    task_id: str | None,
    task_file_override: str | None,
) -> tuple[list[str], str]:
    if task_id and task_file_override:
        raise ConfigError("--task-id and --task-file are mutually exclusive")

    if task_id:
        task = task_id.strip()
        if not task:
            raise ConfigError("--task-id must not be blank")
        return [task], f"task-id:{task}"

    task_file = Path(task_file_override) if task_file_override else task_file_for_mode(phase, mode)
    tasks = read_task_list(task_file)
    return tasks, str(task_file)


def is_ad_hoc_run(
    task_id: str | None,
    task_file_override: str | None,
    ad_hoc_label: str | None,
) -> bool:
    return bool(task_id or task_file_override or ad_hoc_label)


def default_ad_hoc_label(
    mode: str,
    task_id: str | None,
    task_file_override: str | None,
    ad_hoc_label: str | None,
) -> str:
    if ad_hoc_label:
        return ad_hoc_label
    if task_id:
        return f"task-{task_id}"
    if task_file_override:
        return f"task-file-{Path(task_file_override).stem}"
    return f"{mode}-manual"


def ad_hoc_results_dir(
    phase: dict[str, Any],
    arm: dict[str, Any],
    label: str,
) -> Path:
    root = Path(str(phase.get("results_root", f"results/{phase.get('phase_id', 'phase')}")))
    return root / "ad-hoc" / slugify_label(label) / job_dir_name(phase, arm)


def build_harbor_command(
    phase: dict[str, Any],
    arm: dict[str, Any],
    env: dict[str, str],
    mode: str,
    n_attempts: int | None,
    n_concurrent: int | None,
    task_id: str | None = None,
    task_file_override: str | None = None,
    ad_hoc_label: str | None = None,
) -> tuple[list[str], Path, dict[str, Any]]:
    tasks, task_source = resolve_task_selection(
        phase=phase,
        mode=mode,
        task_id=task_id,
        task_file_override=task_file_override,
    )

    ad_hoc = is_ad_hoc_run(
        task_id=task_id,
        task_file_override=task_file_override,
        ad_hoc_label=ad_hoc_label,
    )
    label = default_ad_hoc_label(
        mode=mode,
        task_id=task_id,
        task_file_override=task_file_override,
        ad_hoc_label=ad_hoc_label,
    )

    jobs_dir = ad_hoc_results_dir(phase, arm, label) if ad_hoc else results_dir_for_mode(phase, arm, mode)

    attempts = n_attempts
    if attempts is None:
        attempts = 1 if mode in {"canary", "smoke"} or ad_hoc else int(phase.get("n_attempts", 3))

    concurrent = n_concurrent
    if concurrent is None:
        concurrent = 1 if mode in {"canary", "smoke"} or ad_hoc else int(phase.get("n_concurrent", 4))

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

    for key, value in (arm.get("agent_kwargs") or {}).items():
        cmd.extend(["--agent-kwarg", f"{key}={value}"])
    for key in agent_env_keys_for_arm(arm):
        if key not in env:
            raise ConfigError(f"Configured agent env key is missing after env build: {key}")
        cmd.extend(["--agent-env", f"{key}={env[key]}"])

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

    metadata = {
        "ad_hoc": ad_hoc,
        "ad_hoc_label": slugify_label(label) if ad_hoc else None,
        "scored": not ad_hoc,
        "phase_id": phase.get("phase_id"),
        "arm_id": arm.get("arm_id"),
        "mode": mode,
        "task_source": task_source,
        "task_count": len(tasks),
        "tasks": tasks,
        "n_attempts": attempts,
        "n_concurrent": concurrent,
        "jobs_dir": str(jobs_dir),
    }

    return cmd, jobs_dir, metadata


def write_ad_hoc_metadata(jobs_dir: Path, metadata: dict[str, Any]) -> Path:
    jobs_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = jobs_dir / "ad_hoc_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata_path


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
    parser.add_argument(
        "--task-id",
        default=None,
        help="Run one explicit Terminal-Bench task as an ad-hoc diagnostic.",
    )
    parser.add_argument(
        "--task-file",
        dest="task_file_override",
        default=None,
        help="Run tasks from an explicit task file as an ad-hoc diagnostic.",
    )
    parser.add_argument(
        "--ad-hoc-label",
        default=None,
        help="Label an ad-hoc diagnostic run. Ad-hoc runs are marked non-scored.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        phase = load_phase(args.phase)
        arm = load_arm(args.arm)
        env = build_env(os.environ, arm)
        cmd, jobs_dir, metadata = build_harbor_command(
            phase=phase,
            arm=arm,
            env=env,
            mode=args.mode,
            n_attempts=args.n_attempts,
            n_concurrent=args.n_concurrent,
            task_id=args.task_id,
            task_file_override=args.task_file_override,
            ad_hoc_label=args.ad_hoc_label,
        )
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    print("phase:", args.phase)
    print("arm:", args.arm)
    print("mode:", args.mode)
    print("jobs_dir:", jobs_dir)
    print("task_source:", metadata["task_source"])
    print("task_count:", metadata["task_count"])
    print("ad_hoc:", "true" if metadata["ad_hoc"] else "false")
    print("scored:", "true" if metadata["scored"] else "false")
    if metadata["ad_hoc"]:
        print("ad_hoc_label:", metadata["ad_hoc_label"])
        print("ad_hoc_metadata:", jobs_dir / "ad_hoc_metadata.json")
    print("command:")
    print(" ".join(shlex.quote(x) for x in redact_command(cmd)))

    if args.dry_run:
        return 0

    if metadata["ad_hoc"]:
        write_ad_hoc_metadata(jobs_dir, metadata)
    else:
        jobs_dir.parent.mkdir(parents=True, exist_ok=True)

    return subprocess.run(cmd, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
