from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PHASE2_ARM_DIRS: dict[str, dict[str, Any]] = {
    "arm-anthropic-default": {
        "phase": "phase2",
        "backend": "anthropic",
        "model_backend": "claude-code-default-observed-opus-4-7-1m",
        "requested_model": "no-explicit-model",
        "cost_rule": "provider_reported",
        "input_cache_miss_usd_per_million": None,
        "input_cache_hit_usd_per_million": None,
        "output_usd_per_million": None,
    },
    "arm-anthropic-sonnet": {
        "phase": "phase2",
        "backend": "anthropic",
        "model_backend": "claude-sonnet-4-6",
        "requested_model": "anthropic/claude-sonnet-4-6",
        "cost_rule": "provider_reported",
        "input_cache_miss_usd_per_million": None,
        "input_cache_hit_usd_per_million": None,
        "output_usd_per_million": None,
    },
    "arm-anthropic-haiku": {
        "phase": "phase2",
        "backend": "anthropic",
        "model_backend": "claude-haiku-4-5-20251001",
        "requested_model": "anthropic/claude-haiku-4-5-20251001",
        "cost_rule": "provider_reported",
        "input_cache_miss_usd_per_million": None,
        "input_cache_hit_usd_per_million": None,
        "output_usd_per_million": None,
    },
    "arm-anthropic-opusplan": {
        "phase": "phase2",
        "backend": "anthropic",
        "model_backend": "opusplan-experimental-observed-sonnet-only",
        "requested_model": "opusplan",
        "cost_rule": "provider_reported",
        "input_cache_miss_usd_per_million": None,
        "input_cache_hit_usd_per_million": None,
        "output_usd_per_million": None,
    },
    "arm-deepseek-pro": {
        "phase": "phase2",
        "backend": "deepseek",
        "model_backend": "deepseek-v4-pro[1m]",
        "requested_model": "anthropic/claude-sonnet-4-6 + DeepSeek env override",
        "cost_rule": "computed_cache_aware",
        "input_cache_miss_usd_per_million": 0.435,
        "input_cache_hit_usd_per_million": 0.003625,
        "output_usd_per_million": 0.87,
    },
    "arm-deepseek-flash": {
        "phase": "phase2",
        "backend": "deepseek",
        "model_backend": "deepseek-v4-flash",
        "requested_model": "anthropic/claude-sonnet-4-6 + DeepSeek env override",
        "cost_rule": "computed_cache_aware",
        "input_cache_miss_usd_per_million": 0.14,
        "input_cache_hit_usd_per_million": 0.0028,
        "output_usd_per_million": 0.28,
    },
}


WRITE_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}
MODEL_RE = re.compile(r'"model"\s*:\s*"([^"]+)"')
MODEL_USAGE_RE = re.compile(r'"modelUsage"\s*:\s*\{([^{}]+)\}')


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def duration_seconds(start: str | None, finish: str | None) -> float | None:
    started = parse_dt(start)
    finished = parse_dt(finish)
    if not started or not finished:
        return None
    return (finished - started).total_seconds()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_trial_result(path: Path) -> bool:
    try:
        data = read_json(path)
    except Exception:
        return False
    return "task_name" in data and "trial_name" in data


def token_cost_usd(
    *,
    n_input_tokens: int | float | None,
    n_cache_tokens: int | float | None,
    n_output_tokens: int | float | None,
    input_cache_miss_usd_per_million: float | None,
    input_cache_hit_usd_per_million: float | None,
    output_usd_per_million: float | None,
) -> float | None:
    if (
        input_cache_miss_usd_per_million is None
        or input_cache_hit_usd_per_million is None
        or output_usd_per_million is None
    ):
        return None

    total_input = n_input_tokens or 0
    cached_input = n_cache_tokens or 0
    uncached_input = max(total_input - cached_input, 0)
    output = n_output_tokens or 0

    return (
        uncached_input / 1_000_000 * input_cache_miss_usd_per_million
        + cached_input / 1_000_000 * input_cache_hit_usd_per_million
        + output / 1_000_000 * output_usd_per_million
    )


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def observed_models_from_trial_dir(trial_dir: Path) -> tuple[list[str], str | None]:
    texts: list[str] = []

    for rel in [
        "agent/claude-code.txt",
        "agent/trajectory.json",
    ]:
        text = read_text_if_exists(trial_dir / rel)
        if text:
            texts.append(text)

    combined = "\n".join(texts)

    models: list[str] = []
    for model in MODEL_RE.findall(combined):
        if model and model != "<synthetic>" and model not in models:
            models.append(model)

    # Also try to capture modelUsage keys, which are often the best actual-model signal.
    for usage_match in MODEL_USAGE_RE.findall(combined):
        for model in re.findall(r'"([^"]+)"\s*:', usage_match):
            if model and model != "<synthetic>" and model not in models:
                models.append(model)

    primary = None
    if models:
        # Prefer concrete Claude/DeepSeek model names over aliases.
        concrete = [
            m
            for m in models
            if m.startswith("claude-") or m.startswith("deepseek-")
        ]
        primary = concrete[0] if concrete else models[0]

    return models, primary


def load_trajectory(trial_dir: Path) -> list[Any]:
    path = trial_dir / "agent" / "trajectory.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("steps", "trajectory", "events", "messages"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def extract_tool_name(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None

    for key in ("tool_name", "name", "tool", "type"):
        value = obj.get(key)
        if isinstance(value, str):
            # Avoid counting generic message types as tool names.
            if value in {
                "Bash",
                "Read",
                "Write",
                "Edit",
                "MultiEdit",
                "Grep",
                "Glob",
                "NotebookEdit",
                "WebFetch",
                "WebSearch",
            }:
                return value

    # Claude-style tool-use blocks can be nested in content.
    content = obj.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                name = item.get("name")
                if isinstance(name, str):
                    return name

    return None


def extract_bash_command(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None

    for key in ("command", "cmd"):
        value = obj.get(key)
        if isinstance(value, str):
            return value

    content = obj.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use" and item.get("name") == "Bash":
                tool_input = item.get("input")
                if isinstance(tool_input, dict):
                    value = tool_input.get("command")
                    if isinstance(value, str):
                        return value

    return None


def trajectory_metrics(trial_dir: Path) -> dict[str, Any]:
    trajectory = load_trajectory(trial_dir)

    tool_counts: Counter[str] = Counter()
    bash_commands: list[str] = []
    agent_turns = 0

    for step in trajectory:
        if isinstance(step, dict):
            source = step.get("source") or step.get("role")
            if source == "agent" or source == "assistant":
                agent_turns += 1

            tool_name = extract_tool_name(step)
            if tool_name:
                tool_counts[tool_name] += 1
                if tool_name == "Bash":
                    cmd = extract_bash_command(step)
                    if cmd:
                        bash_commands.append(cmd)

            # Some trajectory formats store nested messages/events.
            for key in ("content", "messages", "events", "steps"):
                nested = step.get(key)
                if isinstance(nested, list):
                    for item in nested:
                        tool_name = extract_tool_name(item)
                        if tool_name:
                            tool_counts[tool_name] += 1
                            if tool_name == "Bash":
                                cmd = extract_bash_command(item)
                                if cmd:
                                    bash_commands.append(cmd)

    repeated_bash_commands = sum(
        count - 1 for count in Counter(bash_commands).values() if count > 1
    )

    return {
        "agent_turns": agent_turns if agent_turns else None,
        "tool_calls": sum(tool_counts.values()),
        "bash_calls": tool_counts.get("Bash", 0),
        "edit_write_calls": sum(tool_counts.get(t, 0) for t in WRITE_TOOLS),
        "read_search_calls": sum(tool_counts.get(t, 0) for t in READ_TOOLS),
        "unique_tool_count": len(tool_counts),
        "repeated_bash_commands": repeated_bash_commands,
        "tool_counts_json": json.dumps(dict(sorted(tool_counts.items())), sort_keys=True),
    }


def classify_failure_mode(data: dict[str, Any], trial_dir: Path) -> str:
    reward = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    if reward == 1 or reward == 1.0:
        return "success"

    exception_info = data.get("exception_info") or {}
    exception_text = json.dumps(exception_info, sort_keys=True).lower()

    if "timeout" in exception_text or "agenttimeouterror" in exception_text:
        return "timed-out"

    if "output" in exception_text and ("limit" in exception_text or "budget" in exception_text):
        return "ran-out-of-budget"

    if "nonzeroagentexitcodeerror" in exception_text:
        return "ran-out-of-budget"

    traj = read_text_if_exists(trial_dir / "agent" / "trajectory.json").lower()
    log = read_text_if_exists(trial_dir / "agent" / "claude-code.txt").lower()
    combined = traj + "\n" + log

    if "refuse" in combined or "can't help" in combined or "cannot help" in combined:
        return "refused-to-try"

    metrics = trajectory_metrics(trial_dir)
    if (metrics.get("repeated_bash_commands") or 0) >= 3:
        return "looped"

    return "produced-wrong-output"


def flatten_trial(path: Path, arm_dir: str, arm_meta: dict[str, Any]) -> dict[str, Any]:
    data = read_json(path)
    trial_dir = path.parent

    agent_result = data.get("agent_result") or {}
    verifier_result = data.get("verifier_result") or {}
    rewards = verifier_result.get("rewards") or {}
    agent_info = data.get("agent_info") or {}

    reward = rewards.get("reward")
    success = reward == 1 or reward == 1.0

    exception_info = data.get("exception_info") or {}
    exception_type = None
    exception_message = None
    if isinstance(exception_info, dict):
        exception_type = (
            exception_info.get("exception_type")
            or exception_info.get("type")
            or exception_info.get("name")
        )
        exception_message = (
            exception_info.get("exception_message")
            or exception_info.get("message")
        )
    elif exception_info:
        exception_message = str(exception_info)

    n_input_tokens = agent_result.get("n_input_tokens")
    n_cache_tokens = agent_result.get("n_cache_tokens")
    n_output_tokens = agent_result.get("n_output_tokens")
    provider_reported_cost_usd = agent_result.get("cost_usd")

    computed_cache_aware_cost_usd = token_cost_usd(
        n_input_tokens=n_input_tokens,
        n_cache_tokens=n_cache_tokens,
        n_output_tokens=n_output_tokens,
        input_cache_miss_usd_per_million=arm_meta.get("input_cache_miss_usd_per_million"),
        input_cache_hit_usd_per_million=arm_meta.get("input_cache_hit_usd_per_million"),
        output_usd_per_million=arm_meta.get("output_usd_per_million"),
    )

    if arm_meta.get("cost_rule") == "computed_cache_aware":
        effective_cost_usd = computed_cache_aware_cost_usd
    else:
        effective_cost_usd = provider_reported_cost_usd

    if effective_cost_usd is None:
        effective_cost_usd = provider_reported_cost_usd or computed_cache_aware_cost_usd

    observed_models, observed_model_primary = observed_models_from_trial_dir(trial_dir)

    row = {
        "phase": arm_meta.get("phase"),
        "arm_dir": arm_dir,
        "backend": arm_meta.get("backend"),
        "model_backend": arm_meta.get("model_backend"),
        "requested_model": arm_meta.get("requested_model"),
        "observed_model_primary": observed_model_primary,
        "observed_models_json": json.dumps(observed_models, sort_keys=True),
        "cost_rule": arm_meta.get("cost_rule"),
        "agent_name": agent_info.get("name"),
        "agent_version": agent_info.get("version"),
        "agent_model_info": json.dumps(agent_info.get("model_info"), sort_keys=True),
        "task_name": data.get("task_name"),
        "trial_name": data.get("trial_name"),
        "trial_uri": data.get("trial_uri"),
        "source": data.get("source"),
        "task_checksum": data.get("task_checksum"),
        "task_git_url": (data.get("task_id") or {}).get("git_url"),
        "task_git_commit_id": (data.get("task_id") or {}).get("git_commit_id"),
        "task_path": (data.get("task_id") or {}).get("path"),
        "reward": reward,
        "success": success,
        "failure_mode": classify_failure_mode(data, trial_dir),
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
        "n_input_tokens": n_input_tokens,
        "n_cache_tokens": n_cache_tokens,
        "n_output_tokens": n_output_tokens,
        "provider_reported_cost_usd": provider_reported_cost_usd,
        "computed_cache_aware_cost_usd": computed_cache_aware_cost_usd,
        "effective_cost_usd": effective_cost_usd,
        "input_cache_miss_usd_per_million": arm_meta.get("input_cache_miss_usd_per_million"),
        "input_cache_hit_usd_per_million": arm_meta.get("input_cache_hit_usd_per_million"),
        "output_usd_per_million": arm_meta.get("output_usd_per_million"),
        "result_json": str(path),
        "trial_dir": str(trial_dir),
    }

    row.update(trajectory_metrics(trial_dir))
    return row


def collect_rows(results_root: Path, arms: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for arm_dir, arm_meta in arms.items():
        arm_path = results_root / arm_dir
        if not arm_path.exists():
            print(f"Skipping missing arm dir: {arm_path}")
            continue

        for path in sorted(arm_path.rglob("result.json")):
            if not is_trial_result(path):
                continue
            rows.append(flatten_trial(path, arm_dir, arm_meta))

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", default="results/phase2")
    parser.add_argument("--output", default="results/phase2/combined.csv")
    args = parser.parse_args()

    results_root = Path(args.results_root)
    output = Path(args.output)

    rows = collect_rows(results_root, PHASE2_ARM_DIRS)
    df = pd.DataFrame(rows)

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    print(f"Wrote {output} with {len(df)} rows")
    if not df.empty:
        print(df.groupby(["arm_dir", "model_backend"])["success"].agg(["count", "mean"]))
        print()
        print("Observed models:")
        print(df.groupby(["arm_dir", "observed_model_primary"]).size())


if __name__ == "__main__":
    main()
