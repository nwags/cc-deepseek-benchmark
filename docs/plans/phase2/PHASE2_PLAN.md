# Phase 2 Plan: Expanded Claude Code Model Matrix and Behavioral Failure Analysis

## Status

Phase 2 is complete and frozen.

This document records the Phase 2 plan, final methodological boundaries, smoke/canary findings, and the behavioral-analysis goals that motivated the Phase 2 report. It is kept under `docs/plans/phase2/` for provenance.

The Phase 2 report and analysis live under:

```text
docs/reports/phase2/PHASE2_REPORT.md
docs/reports/phase2/PHASE2_REPORT.pdf
docs/reports/phase2/analysis.md
```

## Purpose

Phase 2 extended the frozen Phase 1 baseline in response to sponsor requests:

1. Add more model/backend arms.
2. Test Claude Code default/auto model selection.
3. Test Haiku.
4. Investigate why tasks pass or fail and what models do differently.
5. Use available raw trajectories and result artifacts for deeper behavioral analysis.

The key research question was:

```text
What happens when Claude Code's agent harness is held fixed, but the model/backend matrix is expanded?
```

## Relationship to Phase 1

Phase 1 is frozen on `main`.

Phase 1 compared:

- Anthropic Sonnet / `claude-sonnet-4-6`
- DeepSeek V4-Pro through DeepSeek's Anthropic-compatible endpoint
- DeepSeek V4-Flash through DeepSeek's Anthropic-compatible endpoint

Phase 1 used:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 3 arms = 180 trials
```

Phase 2 does not replace Phase 1. It extends the experiment by adding more Claude Code backend configurations while preserving the same benchmark task subset and the same fixed Claude Code harness.

## Initial Phase 2 model matrix

The initial Phase 2 planning matrix included both scored arms and smoke/canary discovery arms:

- `anthropic-default`
- `anthropic-sonnet`
- `anthropic-haiku`
- `anthropic-opus`
- `anthropic-opusplan`
- `deepseek-pro`
- `deepseek-flash`

This initial matrix was refined into:

1. a scored full-sweep matrix, and
2. separate smoke/canary-only findings.

## Scored Phase 2 design

Phase 2 scored arms:

| Arm | Backend | Model/routing |
|---|---|---|
| Anthropic Haiku | Anthropic native | `claude-haiku-4-5-20251001` |
| Anthropic Sonnet | Anthropic native | `claude-sonnet-4-6` |
| Anthropic Opus | Anthropic native | `claude-opus-4-7` |
| DeepSeek V4-Pro | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-pro[1m]` |
| DeepSeek V4-Flash | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-flash` |

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 5 arms = 300 scored trials
```

Fixed components:

- Benchmark substrate: `terminal-bench@2.0`
- Runner: Harbor
- Agent harness: Claude Code
- Task subset: the same selected 20 tasks used in Phase 1 after oracle sanity correction
- Attempts: 3 per task per arm

Main variable:

- Model/backend used by Claude Code

## Smoke and canary findings

Phase 2 included smoke/canary work that should not be mixed into the scored 300-trial matrix.

### Default / auto model selection

The default arm was tested by omitting the `--model` flag rather than passing `--model default`.

Observed behavior:

- The no-explicit-model smoke run resolved to `claude-opus-4-7[1m]` in this account environment.
- This result is account/default-policy dependent.
- It is useful discovery evidence, but it is not a full scored arm.

Conclusion:

- Default/auto model selection is important to understand, but it should not be treated as a stable model arm unless the account policy and observed model are recorded.

### OpusPlan

A canary run with `--model opusplan` succeeded, but the observed trajectory used `claude-sonnet-4-6` throughout and did not show a visible true `EnterPlanMode` / `ExitPlanMode` cycle.

Conclusion:

- `opusplan` was not included as a full scored Phase 2 arm.
- True plan-mode benchmarking should be implemented later as a custom two-pass Harbor agent that explicitly runs a planning pass and then an execution pass.
- That future benchmark should be reported separately because it changes the agent procedure rather than only changing the model/backend.

## Source-of-truth files

Phase 2 source of truth:

```text
results/phase2/combined.csv
```

Raw scored outputs:

```text
results/phase2/raw/
```

Smoke outputs:

```text
results/phase2/smoke/
```

Canary outputs:

```text
results/phase2/canary/
```

Reports and analysis:

```text
docs/reports/phase2/PHASE2_REPORT.md
docs/reports/phase2/PHASE2_REPORT.pdf
docs/reports/phase2/analysis.md
```

Figures:

```text
figures/phase2/
```

## Phase 2 headline results

Final scored results:

| Arm | Successes | Trials | Success rate | Total cost | Median wall-clock |
|---|---:|---:|---:|---:|---:|
| Anthropic Opus | 45 | 60 | 75.0% | about $50.93 | about 246.8s |
| Anthropic Sonnet | 40 | 60 | 66.7% | about $28.36 | about 259.3s |
| DeepSeek V4-Pro | 39 | 60 | 65.0% | about $1.71 | about 566.6s |
| DeepSeek V4-Flash | 35 | 60 | 58.3% | about $0.72 | about 283.4s |
| Anthropic Haiku | 26 | 60 | 43.3% | about $14.31 | about 154.7s |

Interpretation:

- Opus achieved the highest Phase 2 quality.
- Sonnet remained a strong balanced control.
- DeepSeek Pro was close to Sonnet on quality and dramatically cheaper, but slower.
- DeepSeek Flash was extremely cheap and moderately competitive.
- Haiku was fastest, but substantially weaker on this task mix.

## Behavioral and trajectory analysis goals

Phase 2 added deeper trajectory and behavioral analysis beyond reward/pass rate.

Trajectory features to extract or analyze included:

- agent turns
- tool calls
- Bash/Edit/Read/Write/Glob/Grep counts
- Bash calls
- edit/write calls
- read/search calls
- repeated commands
- files touched
- first test run
- last verifier error
- timeout phase
- whether visible tests were run
- whether the final answer was given before verification
- observed model metadata
- wall-clock and agent-execution time
- provider-reported versus computed cache-aware cost
- effective cost
- exception type
- rule-assisted failure mode
- per-task divergence
- qualitative transcript patterns

The purpose was to understand not only whether an arm passed, but what it did differently while attempting the task.

## Failure-mode taxonomy

Failure-mode labels were intended to support qualitative review and aggregate diagnostics.

Primary categories:

- `success`
- `produced-wrong-output`
- `timed-out`
- `looped`
- `refused-to-try`
- `ran-out-of-budget`

These labels are rule-assisted and should be interpreted as diagnostic labels rather than perfect human annotations.

## Methodological constraints

- Do not treat smoke/canary rows as scored full-sweep results.
- Do not overwrite Phase 1 outputs.
- Do not overwrite Phase 2 outputs after freeze unless explicitly requested.
- Use `results/phase2/combined.csv` as the source of truth for Phase 2.
- Use `results/phase1/combined.csv` as the source of truth for Phase 1.
- Keep `.secrets/` and `.env` ignored.
- Do not commit real API keys.
- Treat missing observed-model rows on exception trials as a telemetry limitation, not as evidence of a different model unless supported by logs.
- Treat DeepSeek cost using computed cache-aware cost rather than misleading Anthropic-compatible cost metadata.

## Lessons carried into Phase 3

1. Environment propagation must be explicit.
2. Observed model metadata must be extracted from raw artifacts, not inferred from Harbor display names.
3. DeepSeek cost must use computed cache-aware cost rather than misleading compatibility-layer cost.
4. Smoke/canary outputs must be physically separated from full scored sweeps.
5. Default/auto model behavior is useful but account-dependent.
6. True plan-mode evaluation requires a different benchmark procedure, not merely a model alias.
7. Router-mediated provider expansion should be reported separately from native Phase 2 backend substitution.
8. Future analysis should preserve both quantitative aggregate metrics and qualitative trajectory review.