# Collaboration Guide

This repository is organized for phase-based and patch-based collaboration on Claude Code / Terminal-Bench / Harbor benchmarking.

The goal is to make it easy for multiple contributors to work on separate phases, providers, scripts, reports, or upstream patches without corrupting frozen results.

## Collaboration model

Work should usually be delegated in one of three ways:

1. **By phase**
   - Example: Phase 3 router-mediated provider expansion.
   - Example: Phase 4 agent harness comparison.
   - Example: Phase 5 plan-execute study.

2. **By patch**
   - Example: add a trial summarizer.
   - Example: improve failure-mode taxonomy.
   - Example: add cost-aware aggregation.
   - Example: fix report figure paths.

3. **By library/tool integration**
   - Example: integrate Claude Code Router.
   - Example: integrate Bifrost.
   - Example: add Gemini router arm.
   - Example: add OpenAI router arm.
   - Example: add xAI/Grok router arm.
   - Example: prototype a Harbor plan-execute agent.

## Branch naming

Use descriptive branch names.

Recommended patterns:

```text
phase3/router-gemini-smoke
phase3/router-openai-smoke
phase3/router-xai-grok-smoke
phase3/router-anthropic-comparability
phase3/router-deepseek-comparability
phase3/aggregate-router-metrics
phase3/report-router-findings

phase4/agent-harness-plan
phase4/codex-harness-canary
phase4/gemini-cli-harness-canary

phase5/plan-execute-agent-prototype
phase5/planner-executor-configs

docs/runbook-refresh
docs/report-path-fixes
scripts/config-driven-runner
analysis/trial-summary-extractor
analysis/failure-taxonomy-v2
```

Avoid vague branch names such as:

```text
updates
fixes
misc
newstuff
```

## Phase ownership

Each phase should have:

* a phase plan under `docs/plans/<phase>/`
* phase config under `configs/phases/`
* raw outputs under `results/<phase>/raw/`
* smoke outputs under `results/<phase>/smoke/`
* canary outputs under `results/<phase>/canary/`
* aggregate output under `results/<phase>/combined.csv`
* report output under `docs/reports/<phase>/`
* figures under `figures/<phase>/`

## Patch ownership

Each patch should have a clear acceptance target.

Examples:

### Trial summarizer patch

Owner task:

```text
Add scripts/summarize_trials.py to generate compact per-trial summaries from raw Harbor outputs.
```

Acceptance criteria:

* reads `results/<phase>/raw/`
* writes `results/<phase>/supplemental/trial_summaries.jsonl`
* includes task, arm, trial, success, failure mode, observed model, cost, timing, tool counts, first verifier error, and last meaningful action
* does not modify raw outputs
* passes `make check`

### Router Gemini smoke patch

Owner task:

```text
Add a router-mediated Gemini Flash canary/smoke arm.
```

Acceptance criteria:

* adds or updates `configs/arms/router-gemini-flash.yaml`
* documents required local secret file
* runs one canary task into `results/phase3/canary/`
* extracts observed model metadata where possible
* does not mix canary output into full scored aggregate
* updates `docs/plans/phase3/PHASE3_ROUTER_PLAN.md`

### Report path-fix patch

Owner task:

```text
Fix report Markdown image paths after moving figures into phase-specific folders.
```

Acceptance criteria:

* Phase 1 report image paths point to `../../../figures/phase1/...`
* Phase 2 report image paths point to `../../../figures/phase2/...`
* reports render from their current locations
* no quantitative content is changed

## Pull request / review checklist

Before submitting a pull request or asking for review:

* [ ] The branch name describes the work.
* [ ] The change is scoped to one phase or one patch.
* [ ] Frozen Phase 1 and Phase 2 results are not modified unless explicitly requested.
* [ ] New outputs are written to the correct phase directory.
* [ ] Smoke/canary outputs are separated from full scored outputs.
* [ ] `make check` passes.
* [ ] `make secret-scan` passes.
* [ ] No `.env`, `.secrets/`, or real API keys are included.
* [ ] README or runbooks are updated if commands changed.
* [ ] Reports distinguish scored sweeps from exploratory findings.
* [ ] The commit does not include snapshot files unless explicitly requested.

## Result artifact rules

### Full scored sweeps

Full scored sweeps should write to:

```text
results/<phase>/raw/<arm>/
```

The aggregate should write to:

```text
results/<phase>/combined.csv
```

### Smoke runs

Smoke runs should write to:

```text
results/<phase>/smoke/<arm>/
```

Smoke runs may have a smoke aggregate such as:

```text
results/<phase>/smoke-combined.csv
```

Smoke runs are not scored full-sweep results.

### Canary runs

Canary runs should write to:

```text
results/<phase>/canary/<arm>/
```

Canaries are used to confirm routing, credentials, output format, and observed model behavior.

Canaries are not scored full-sweep results.

### Supplemental outputs

Generated tables, compact summaries, or analysis artifacts should write to:

```text
results/<phase>/supplemental/
```

Examples:

```text
results/phase2/supplemental/summary_metrics.csv
results/phase2/supplemental/failure_modes.csv
results/phase3/supplemental/router_observed_models.csv
```

## How to add a new model/provider arm

1. Create or update an arm config:

```text
configs/arms/<arm-id>.yaml
```

2. Confirm the phase config references the intended task list, attempts, concurrency, and output root.

3. Confirm the required local secret file exists under `.secrets/`.

4. Run a canary:

```bash
./scripts/run_arm.sh <phase> <arm-id> --mode canary
```

5. Inspect observed model metadata in the raw logs.

6. Run a smoke test:

```bash
./scripts/run_arm.sh <phase> <arm-id> --mode smoke
```

7. Aggregate smoke results if needed.

8. Only after the canary and smoke pass, run a full sweep:

```bash
./scripts/run_arm.sh <phase> <arm-id> --mode full
```

9. Regenerate the phase aggregate:

```bash
uv run python scripts/aggregate_phase.py <phase>
```

10. Update the relevant plan/report.

If the `--mode` interface is not yet implemented, use the current script interface and document the exact command in `docs/runbooks/RUNBOOK.md`.

## How to add a new phase

1. Create phase config:

```text
configs/phases/<phase>.yaml
```

2. Create directories:

```bash
mkdir -p results/<phase>/{raw,smoke,canary,supplemental}
mkdir -p figures/<phase>
mkdir -p docs/plans/<phase>
mkdir -p docs/reports/<phase>
mkdir -p artifacts/<phase>
```

3. Add or update phase plan:

```text
docs/plans/<phase>/<PHASE_PLAN>.md
```

4. Add relevant arm configs under:

```text
configs/arms/
```

5. Add or confirm task lists under:

```text
configs/tasks/
```

6. Update:

```text
README.md
docs/runbooks/REPO_MAP.md
docs/runbooks/RUNBOOK.md
```

7. Run checks:

```bash
make check
make secret-scan
```

## Acceptance criteria template

Use this template for delegated patches:

````md
## Goal

One-sentence goal.

## Scope

- Included:
- Included:
- Excluded:

## Files expected to change

- `path/to/file`
- `path/to/file`

## Commands to run

```bash
make check
make secret-scan
```

## Acceptance criteria

* [ ] Criterion 1
* [ ] Criterion 2
* [ ] Criterion 3

## Notes

Any risk, cost, or migration concerns.

```

## Review priorities

When reviewing collaboration work, prioritize:

1. Reproducibility
2. Correct phase separation
3. Secret safety
4. Avoiding accidental paid benchmark reruns
5. Clear observed-model provenance
6. Clear distinction between canary, smoke, and full scored results
7. Minimal, reviewable diffs