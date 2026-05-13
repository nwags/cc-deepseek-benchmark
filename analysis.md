# Analysis

This analysis uses `results/combined.csv`, produced by:

    uv run python scripts/aggregate.py

## Required questions

1. Quality: success rates, Wilson confidence intervals, per-task success, divergent tasks.
2. Speed: mean/median wall-clock seconds, distributions, speedup ratios.
3. Cost: total spend, token-derived spend, cost per resolved task.
4. Qualitative divergence: transcript review for 3-5 interesting tasks.

## Data source

The analysis should use the long-format CSV at:

    results/combined.csv

Each row should represent one `(arm, task, trial)` result.

## Notes

This file is a placeholder until the full benchmark sweep is complete.
