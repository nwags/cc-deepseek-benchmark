from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ARM_DIRS = {
    "arm-a-anthropic": {
        "backend": "anthropic",
        "model_backend": "claude-sonnet-4-6",
        "input_cache_miss_usd_per_million": 3.00,
        "input_cache_hit_usd_per_million": 0.30,
        "output_usd_per_million": 15.00,
    },
    "arm-b-deepseek-pro": {
        "backend": "deepseek",
        "model_backend": "deepseek-v4-pro",
        "input_cache_miss_usd_per_million": 0.435,
        "input_cache_hit_usd_per_million": 0.003625,
        "output_usd_per_million": 0.87,
    },
    "arm-c-deepseek-flash": {
        "backend": "deepseek",
        "model_backend": "deepseek-v4-flash",
        "input_cache_miss_usd_per_million": 0.14,
        "input_cache_hit_usd_per_million": 0.0028,
        "output_usd_per_million": 0.28,
    },
}

WRITE_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}


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


def token_cost_usd(
    *,
    input_tokens: int | float | None,
    cache_tokens: int | float | None,
    output_tokens: int | float | None,
    input_cache_miss_usd_per_million: float,
    input_cache_hit_usd_per_million: float,
    output_usd_per_million: float,
) -> float | None:
    if input_tokens is None and output_tokens is None and cache_tokens is None:
        return None
    input_tokens = float(input_tokens or 0)
    cache_tokens = float(cache_tokens or 0)
    output_tokens = float(output_tokens or 0)
    cache_miss_tokens = max(input_tokens - cache_tokens, 0)
    return (
        cache_miss_tokens / 1_000_000 * input_cache_miss_usd_per_million
        + cache_tokens / 1_000_000 * input_cache_hit_usd_per_million
        + output_tokens / 1_000_000 * output_usd_per_million
    )


def is_trial_result(path: Path) -> bool:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return False
    return "task_name" in data and "trial_name" in data and "verifier_result" in data


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def iter_nested(obj: Any):
    """Yield every nested dict/list node in obj."""
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from iter_nested(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from iter_nested(value)


def trajectory_stats(trial_dir: Path) -> dict[str, Any]:
    """Best-effort extraction of turns/tool calls from Harbor's Claude Code trajectory.

    The trajectory schema can drift across Claude Code/Harbor versions, so this parser is
    intentionally permissive. It counts common Claude Code stream events and tool-use
    nodes found in nested JSON.
    """
    path = trial_dir / "agent" / "trajectory.json"
    traj = load_json(path)
    if traj is None:
        return {
            "agent_turns": None,
            "tool_calls": None,
            "bash_calls": None,
            "edit_write_calls": None,
            "read_search_calls": None,
            "unique_tool_count": None,
            "repeated_bash_commands": None,
            "tool_counts_json": None,
        }

    agent_turns = 0
    tool_names: list[str] = []
    bash_commands: list[str] = []

    for node in iter_nested(traj):
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")
        role = node.get("role")
        source = node.get("source")

        if role == "assistant" or source == "agent" or node_type == "assistant":
            # Avoid counting every nested assistant content block as a separate turn if it
            # is clearly just a content item.
            if "message" in node or "content" in node or source == "agent":
                agent_turns += 1

        # Anthropic tool-use format commonly appears as {"type":"tool_use", "name":"Bash", ...}
        if node_type == "tool_use" and node.get("name"):
            tool_name = str(node.get("name"))
            tool_names.append(tool_name)
            tool_input = node.get("input") or {}
            if tool_name == "Bash" and isinstance(tool_input, dict):
                cmd = tool_input.get("command") or tool_input.get("cmd")
                if cmd:
                    bash_commands.append(str(cmd))

        # Harbor/Claude Code trajectory sometimes stores tool name differently.
        for key in ("tool", "tool_name", "name"):
            maybe = node.get(key)
            if isinstance(maybe, str) and maybe in {"Bash", "Read", "Grep", "Glob", "Edit", "MultiEdit", "Write", "NotebookEdit"}:
                # Avoid double counting the exact same tool_use node handled above.
                if not (node_type == "tool_use" and key == "name"):
                    tool_names.append(maybe)

        command = node.get("command")
        if isinstance(command, str) and command.strip():
            # Only treat explicit command fields as bash-like repeats, not every text field.
            bash_commands.append(command)

    # If the permissive traversal over-counts assistant turns, cap by stream-json assistant
    # messages when available in claude-code.txt as a sanity fallback.
    transcript = trial_dir / "agent" / "claude-code.txt"
    if transcript.exists():
        assistant_messages = 0
        transcript_tool_calls = 0
        transcript_tool_names: list[str] = []
        transcript_bash_cmds: list[str] = []
        for line in transcript.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("type") == "assistant":
                assistant_messages += 1
                msg = event.get("message") or {}
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        transcript_tool_calls += 1
                        name = c.get("name")
                        if name:
                            transcript_tool_names.append(str(name))
                        inp = c.get("input") or {}
                        if name == "Bash" and isinstance(inp, dict) and inp.get("command"):
                            transcript_bash_cmds.append(str(inp["command"]))
        if assistant_messages:
            agent_turns = assistant_messages
        if transcript_tool_calls:
            tool_names = transcript_tool_names
            bash_commands = transcript_bash_cmds

    tool_counter = Counter(tool_names)
    bash_counter = Counter(bash_commands)
    repeated_bash = sum(count - 1 for count in bash_counter.values() if count > 1)

    return {
        "agent_turns": agent_turns,
        "tool_calls": sum(tool_counter.values()),
        "bash_calls": tool_counter.get("Bash", 0),
        "edit_write_calls": sum(tool_counter.get(t, 0) for t in WRITE_TOOLS),
        "read_search_calls": sum(tool_counter.get(t, 0) for t in READ_TOOLS),
        "unique_tool_count": len(tool_counter),
        "repeated_bash_commands": repeated_bash,
        "tool_counts_json": json.dumps(dict(sorted(tool_counter.items())), sort_keys=True),
    }


def classify_failure_mode(
    *,
    success: bool | None,
    exception_type: str | None,
    exception_message: str | None,
    reward: Any,
    stats: dict[str, Any],
) -> str:
    """Map trial outcome into the assignment's requested failure-mode taxonomy.

    Assignment buckets: refused-to-try, looped, ran-out-of-budget,
    produced-wrong-output, timed-out. We retain a transparent distinction for
    non-timeout agent-process errors by mapping them to ran-out-of-budget when they
    look like agent process exits, because Harbor does not expose a richer category.
    """
    if success:
        return "success"

    et = exception_type or ""
    em = exception_message or ""
    et_lower = et.lower()
    em_lower = em.lower()

    if "timeout" in et_lower or "timeout" in em_lower:
        return "timed-out"
    if et == "AgentTimeoutError":
        return "timed-out"
    if et == "NonZeroAgentExitCodeError":
        return "ran-out-of-budget"

    tool_calls = stats.get("tool_calls")
    agent_turns = stats.get("agent_turns")
    repeated_bash = stats.get("repeated_bash_commands") or 0

    if (tool_calls == 0 or tool_calls is None) and (agent_turns is None or agent_turns <= 2):
        return "refused-to-try"
    if repeated_bash >= 5:
        return "looped"

    # Reward 0 with no infra exception usually means the agent produced an output
    # that did not satisfy the verifier.
    if reward is not None:
        return "produced-wrong-output"
    return "produced-wrong-output"


def flatten_trial(path: Path, *, arm_dir: str, arm_meta: dict[str, Any]) -> dict[str, Any]:
    data = json.loads(path.read_text())
    verifier_result = data.get("verifier_result") or {}
    rewards = verifier_result.get("rewards") or {}
    agent_info = data.get("agent_info") or {}
    agent_result = data.get("agent_result") or {}

    input_tokens = agent_result.get("n_input_tokens")
    cache_tokens = agent_result.get("n_cache_tokens")
    output_tokens = agent_result.get("n_output_tokens")

    computed_cost = token_cost_usd(
        input_tokens=input_tokens,
        cache_tokens=cache_tokens,
        output_tokens=output_tokens,
        input_cache_miss_usd_per_million=arm_meta["input_cache_miss_usd_per_million"],
        input_cache_hit_usd_per_million=arm_meta["input_cache_hit_usd_per_million"],
        output_usd_per_million=arm_meta["output_usd_per_million"],
    )

    provider_reported_cost = agent_result.get("cost_usd")
    if arm_meta["backend"] == "deepseek":
        effective_cost = computed_cost
    else:
        effective_cost = provider_reported_cost if provider_reported_cost is not None else computed_cost

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

    trial_dir = path.parent
    stats = trajectory_stats(trial_dir)
    failure_mode = classify_failure_mode(
        success=success,
        exception_type=exception_type,
        exception_message=exception_message,
        reward=reward,
        stats=stats,
    )

    row = {
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
        "failure_mode": failure_mode,
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
        "provider_reported_cost_usd": provider_reported_cost,
        "computed_cache_aware_cost_usd": computed_cost,
        "effective_cost_usd": effective_cost,
        "input_cache_miss_usd_per_million": arm_meta["input_cache_miss_usd_per_million"],
        "input_cache_hit_usd_per_million": arm_meta["input_cache_hit_usd_per_million"],
        "output_usd_per_million": arm_meta["output_usd_per_million"],
        "result_json": str(path),
        "trial_dir": str(trial_dir),
    }
    row.update(stats)
    return row


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
        if "failure_mode" in df.columns:
            print("\nFailure modes:")
            print(pd.crosstab(df["arm_dir"], df["failure_mode"]))
        if "agent_turns" in df.columns:
            print("\nAgent turns/tool calls:")
            print(df.groupby("arm_dir").agg(
                median_agent_turns=("agent_turns", "median"),
                median_tool_calls=("tool_calls", "median"),
                mean_agent_turns=("agent_turns", "mean"),
                mean_tool_calls=("tool_calls", "mean"),
            ))


if __name__ == "__main__":
    main()
