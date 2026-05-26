# Phase 1 Plan: Frozen Claude Code Backend Baseline

## Status

Phase 1 is complete and frozen.

This document records the original benchmark design so collaborators can understand the baseline without reading the entire Phase 1 report or assignment document. Phase 1 should not be modified or rerun into the same output paths unless explicitly requested.

## Research question

```text
What happens when Claude Code's agent harness is held fixed and the model backend is swapped from Anthropic Sonnet to DeepSeek V4-Pro or DeepSeek V4-Flash through an Anthropic-compatible endpoint?
```

## Purpose

Phase 1 established the baseline methodology for the project:

- use Harbor as the benchmark runner
- use Terminal-Bench 2.0 as the task substrate
- use Claude Code as the fixed agent harness
- vary only the model/backend
- collect raw Harbor artifacts and aggregate them into a trial-level CSV
- report quality, speed, cost, and qualitative failure patterns

## Experimental design

Phase 1 compared three arms:

| Arm | Backend | Model/routing | Role |
|---|---|---|---|
| `arm-a-anthropic` | Anthropic | `claude-sonnet-4-6` | Anthropic control |
| `arm-b-deepseek-pro` | DeepSeek | `deepseek-v4-pro` / `deepseek-v4-pro[1m]` through `https://api.deepseek.com/anthropic` | quality/cost challenger |
| `arm-c-deepseek-flash` | DeepSeek | `deepseek-v4-flash` through `https://api.deepseek.com/anthropic` | low-cost/fast challenger |

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 3 arms = 180 trials
```

The selected task list is preserved in:

```text
configs/tasks/terminal-bench-20.txt
configs/tasks/tasks.txt
```

## Oracle sanity check

Before paid runs, the task subset was sanity-checked with the oracle/reference path. The original candidate `rstan-to-pystan` was replaced with `model-extraction-relu-logits` after oracle sanity issues. The final 20-task subset passed oracle sanity.

## Source-of-truth paths

Raw Phase 1 results:

```text
results/phase1/raw/
```

Canonical aggregate:

```text
results/phase1/combined.csv
```

Supplemental analysis outputs:

```text
results/phase1/supplemental/
```

Reports:

```text
docs/reports/phase1/REPORT.md
docs/reports/phase1/REPORT.pdf
docs/reports/phase1/analysis.md
docs/reports/phase1/FINDINGS.md
docs/reports/phase1/QUALITATIVE_TRANSCRIPT_REVIEW.md
```

Figures:

```text
figures/phase1/
```

Legacy scripts were moved under:

```text
scripts/old-scripts/
```

They remain as migration reference but should not be extended for new work unless necessary.

## Headline results

Final Phase 1 results:

| Arm | Successes | Trials | Success rate | Total cost | Median wall-clock |
|---|---:|---:|---:|---:|---:|
| Anthropic Sonnet | 39 | 60 | 65.0% | about $37.30 | about 255.7s |
| DeepSeek V4-Pro | 42 | 60 | 70.0% | about $2.01 | about 617.5s |
| DeepSeek V4-Flash | 37 | 60 | 61.7% | about $1.10 | about 262.7s |

Interpretation:

- DeepSeek V4-Pro matched Anthropic Sonnet quality on the selected task set and was dramatically cheaper.
- DeepSeek V4-Pro was much slower than Anthropic Sonnet.
- DeepSeek V4-Flash was cheapest and near Anthropic speed, but slightly lower quality.
- The correct conclusion is not that DeepSeek universally beats Anthropic; it is that DeepSeek Pro was highly competitive in this fixed Claude Code harness setup at far lower cost.

## Cost-accounting rule

The Phase 1 cost lesson is important and must be preserved in future scripts:

- Anthropic costs may use provider-reported costs where available.
- DeepSeek costs should use computed cache-aware costs, because compatibility-layer provider-reported costs can be misleading.
- `effective_cost_usd` is the report-level cost field.

DeepSeek cache-aware calculation should treat total input tokens and cached tokens carefully:

```text
uncached_input = max(n_input_tokens - n_cache_tokens, 0)
cost = uncached_input * uncached_input_rate
     + n_cache_tokens * cached_input_rate
     + n_output_tokens * output_rate
```

## Reproducibility expectations

Phase 1 should be reproducible without rerunning paid benchmarks by using:

```bash
uv run python scripts/aggregate_phase.py phase1
```

The new Phase 3 scaffolding summarizes existing Phase 1 aggregates rather than regenerating all raw rows. If raw-regeneration support is added later, it must be regression-tested against `results/phase1/combined.csv`.

## Threats to validity

- The task subset has 20 tasks, not the full Terminal-Bench 2.0 set.
- There are only 3 attempts per task per arm.
- Claude Code version drift must be disclosed where present.
- Results are specific to Claude Code + Harbor + Terminal-Bench 2.0.
- DeepSeek results are from the Anthropic-compatible endpoint, not a native DeepSeek agent harness.
- Wall-clock speed depends on local hardware, Docker behavior, provider latency, timeouts, and the model/harness interaction.

## Freeze policy

Do not overwrite:

```text
results/phase1/combined.csv
results/phase1/raw/
docs/reports/phase1/
figures/phase1/
```

unless the user explicitly requests a Phase 1 rerun or correction.

New work should go into later phase paths:

```text
results/phase2/
results/phase3/
results/phase4/
results/phase5/
```

## Relationship to later phases

- Phase 2 expands the native Claude Code backend matrix.
- Phase 3 tests router-mediated provider expansion while keeping Claude Code fixed.
- Phase 4 compares agent harnesses.
- Phase 5 incorporates true plan mode / plan-execute workflows.

Phase 1 remains the baseline comparator for all later phases.
