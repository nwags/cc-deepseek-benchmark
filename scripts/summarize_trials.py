from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_COLUMNS = [
    "arm_dir",
    "task_name",
    "trial_name",
    "success",
    "failure_mode",
    "exception_type",
    "observed_model_primary",
    "effective_cost_usd",
    "wall_clock_seconds",
    "agent_execution_seconds",
    "agent_turns",
    "tool_calls",
    "bash_calls",
]


def normalize_phase(phase: str) -> str:
    return "phase3" if phase == "phase3-router" else phase


def main() -> int:
    parser = argparse.ArgumentParser(description="Write compact JSONL trial summaries from a phase aggregate CSV.")
    parser.add_argument("phase")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    phase = normalize_phase(args.phase)
    csv_path = Path(args.input) if args.input else Path("results") / phase / "combined.csv"
    out_path = Path(args.output) if args.output else Path("results") / phase / "supplemental" / "trial_summaries.jsonl"

    if not csv_path.exists():
        raise SystemExit(f"Missing aggregate CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    columns = [col for col in DEFAULT_COLUMNS if col in df.columns]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in df[columns].to_dict(orient="records"):
            f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")

    print(f"Wrote {len(df)} trial summaries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
