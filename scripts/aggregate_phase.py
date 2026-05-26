from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def summarize(df: pd.DataFrame) -> None:
    if "arm_dir" not in df.columns or "success" not in df.columns:
        print(f"Loaded {len(df)} rows; no standard arm/success columns found.")
        return

    agg = df.groupby("arm_dir").agg(
        trials=("success", "count"),
        successes=("success", "sum"),
        success_rate=("success", "mean"),
    )

    if "effective_cost_usd" in df.columns:
        agg["total_cost"] = df.groupby("arm_dir")["effective_cost_usd"].sum()

    if "wall_clock_seconds" in df.columns:
        agg["median_wall"] = df.groupby("arm_dir")["wall_clock_seconds"].median()

    print(agg)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase-aware aggregate entry point. Current scaffold validates and "
            "summarizes existing combined.csv files; raw-output regeneration will "
            "be added in a later Phase 3 patch."
        )
    )
    parser.add_argument("phase", help="phase1, phase2, phase3, or phase3-router")
    parser.add_argument("--input", default=None, help="Optional aggregate CSV path")
    parser.add_argument("--output", default=None, help="Reserved for future raw regeneration")
    args = parser.parse_args()

    phase = args.phase
    normalized = "phase3" if phase == "phase3-router" else phase
    csv_path = Path(args.input) if args.input else Path("results") / normalized / "combined.csv"

    if not csv_path.exists():
        raise SystemExit(
            f"No aggregate CSV found at {csv_path}. "
            "This scaffold currently summarizes existing aggregates only."
        )

    df = pd.read_csv(csv_path)
    print(f"Loaded {csv_path} with {len(df)} rows x {len(df.columns)} columns")
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
