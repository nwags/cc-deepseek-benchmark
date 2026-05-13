from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ARM_DIRS = {
    "arm-a-anthropic": {
        "backend": "anthropic",
        "model_backend": "claude-sonnet-4-6",
        "input_usd_per_million": 3.00,
        "output_usd_per_million": 15.00,
    },
    "arm-b-deepseek-pro": {
        "backend": "deepseek",
        "model_backend": "deepseek-v4-pro",
        "input_usd_per_million": 0.435,
        "output_usd_per_million": 0.87,
    },
    "arm-c-deepseek-flash": {
        "backend": "deepseek",
        "model_backend": "deepseek-v4-flash",
        "input_usd_per_million": 0.14,
        "output_usd_per_million": 0.28,
    },
}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def duration_seconds(start: str | None, finish: str | None) -> float | None:
    started = parse_dt(start)
    finished = parse_dt(finish)
    if started is None or finished is None:
        return None
    return (finished - started).total_seconds()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def token_cost_usd(
    input_tokens: int | float | None,
    output_tokens: int | float | None,
    input_usd_per_million: float,
    output_usd_per_million: float,
) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None

    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0

    return (
        input_tokens / 1_000_000 * input_usd_per_million
        + output_tokens / 1_000_000 * output_usd_per_million
    )


def is_trial_result(path: Path) -> bool:
    # Exclude top-level job result.json files. Trial result.json files live one
    # directory below the timestamp directory and include task_name/trial_name.
    try:
        data = read_json(path)
    except Exception:
        return False
    return "task_name" in data and "trial_name" in data


def flatten_trial(path: Path, arm_dir: str, arm_meta: dict[str, Any]) -> dict[str, Any]:
    data = read_json(path)

    agent_result = data.get("agent_result") or {}
    verifier_result = data.get("verifier_result") or {}
    rewards = verifier_result.get("rewards") or {}
    agent_info = data.get("agent_info") or {}

    input_tokens = agent_result.get("n_input_tokens")
    cache_tokens = agent_result.get("n_cache_tokens")
    output_tokens = agent_result.get("n_output_tokens")

    computed_cost = token_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_usd_per_million=arm_meta["input_usd_per_million"],
        output_usd_per_million=arm_meta["output_usd_per_million"],
    )

    reward = rewards.get("reward")
    success = None if reward is None else float(reward) >= 1.0

    exception_info = data.get("exception_info")
    exception_type = None
    exception_message = None
    if isinstance(exception_info, dict):
        exception_type = exception_info.get("type") or exception_info.get("exception_type")
        exception_message = exception_info.get("message") or exception_info.get("exception_message")
    elif exception_info is not None:
        exception_message = str(exception_info)

    return {
        "arm_dir": arm_dir,
        "backend": arm_meta["backend"],
        "model_backend": arm_meta["model_backend"],
        "agent_name": agent_info.get("name"),
        "agent_version": agent_info.get("version"),
        "agent_model_info": json.dumps(agent_info.get("model_info"), sort_keys=True),
        "task_name": data.get("task_name"),
        "trial_name": data.get("trial_name"),
        "trial_uri": data.get("trial_uri"),
        "source": data.get("source"),
        "task_checksum": data.get("task_checksum"),
        "task_git_url": ((data.get("task_id") or {}).get("git_url")),
        "task_git_commit_id": ((data.get("task_id") or {}).get("git_commit_id")),
        "task_path": ((data.get("task_id") or {}).get("path")),
        "reward": reward,
        "success": success,
        "exception_type": exception_type,
        "exception_message": exception_message,
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "wall_clock_seconds": duration_seconds(data.get("started_at"), data.get("finished_at")),
        "environment_setup_seconds": duration_seconds(
            (data.get("environment_setup") or {}).get("started_at"),
            (data.get("environment_setup") or {}).get("finished_at"),
        ),
        "agent_setup_seconds": duration_seconds(
            (data.get("agent_setup") or {}).get("started_at"),
            (data.get("agent_setup") or {}).get("finished_at"),
        ),
        "agent_execution_seconds": duration_seconds(
            (data.get("agent_execution") or {}).get("started_at"),
            (data.get("agent_execution") or {}).get("finished_at"),
        ),
        "verifier_seconds": duration_seconds(
            (data.get("verifier") or {}).get("started_at"),
            (data.get("verifier") or {}).get("finished_at"),
        ),
        "n_input_tokens": input_tokens,
        "n_cache_tokens": cache_tokens,
        "n_output_tokens": output_tokens,
        "provider_reported_cost_usd": agent_result.get("cost_usd"),
        "computed_cost_usd": computed_cost,
        "input_usd_per_million": arm_meta["input_usd_per_million"],
        "output_usd_per_million": arm_meta["output_usd_per_million"],
        "result_json": str(path),
        "trial_dir": str(path.parent),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--out", default="results/combined.csv")
    args = parser.parse_args()

    results_root = Path(args.results_dir)
    rows: list[dict[str, Any]] = []

    for arm_dir, arm_meta in ARM_DIRS.items():
        arm_path = results_root / arm_dir
        if not arm_path.exists():
            print(f"Skipping missing arm dir: {arm_path}")
            continue

        for result_path in arm_path.rglob("result.json"):
            if is_trial_result(result_path):
                rows.append(flatten_trial(result_path, arm_dir=arm_dir, arm_meta=arm_meta))

    df = pd.DataFrame(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"Wrote {out} with {len(df)} rows")
    if len(df):
        print(df.groupby(["arm_dir", "model_backend"])["success"].agg(["count", "mean"]))


if __name__ == "__main__":
    main()
