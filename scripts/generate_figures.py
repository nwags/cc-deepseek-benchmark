from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def normalize_phase(phase: str) -> str:
    return "phase3" if phase == "phase3-router" else phase


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate basic phase figures from results/<phase>/combined.csv.")
    parser.add_argument("phase")
    args = parser.parse_args()

    phase = normalize_phase(args.phase)
    csv_path = Path("results") / phase / "combined.csv"
    out_dir = Path("figures") / phase
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        raise SystemExit(f"Missing aggregate CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    if "arm_dir" not in df.columns or "success" not in df.columns:
        raise SystemExit("Aggregate must contain arm_dir and success columns")

    success = df.groupby("arm_dir")["success"].mean().sort_values(ascending=False)
    ax = success.plot(kind="bar")
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1)
    ax.set_title(f"{phase} success rate")
    plt.tight_layout()
    plt.savefig(out_dir / f"{phase}_success_rate.png", dpi=160)
    plt.close()

    if "wall_clock_seconds" in df.columns:
        wall = df.groupby("arm_dir")["wall_clock_seconds"].median().sort_values()
        ax = wall.plot(kind="bar")
        ax.set_ylabel("Median wall-clock seconds")
        ax.set_title(f"{phase} median wall-clock")
        plt.tight_layout()
        plt.savefig(out_dir / f"{phase}_median_wall_clock.png", dpi=160)
        plt.close()

    if "failure_mode" in df.columns:
        table = pd.crosstab(df["arm_dir"], df["failure_mode"])
        ax = table.plot(kind="bar", stacked=True)
        ax.set_ylabel("Trials")
        ax.set_title(f"{phase} failure modes")
        plt.tight_layout()
        plt.savefig(out_dir / f"{phase}_failure_modes.png", dpi=160)
        plt.close()

    print(f"Wrote figures to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
