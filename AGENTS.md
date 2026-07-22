# AGENTS.md

This repository benchmarks Claude Code model/provider backends on Terminal-Bench / Harbor.

The project is structured as a multi-phase benchmark repository. Contributors may be human or agentic. Treat this file as the top-level operating guide for automated coding agents and for contributors using tools such as Claude Code, Codex, or other agent harnesses.

## Current branch

Current active branch:

```text
phase3
```

The `phase3` branch begins the router-mediated provider expansion and repository refactor after Phase 1 and Phase 2 were frozen.

## Phase status

### Phase 1: frozen baseline

Phase 1 compared:

1. Anthropic Sonnet / `claude-sonnet-4-6`
2. DeepSeek V4-Pro through DeepSeek's Anthropic-compatible endpoint
3. DeepSeek V4-Flash through DeepSeek's Anthropic-compatible endpoint

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 3 arms = 180 trials
```

Source-of-truth aggregate:

```text
results/phase1/combined.csv
```

Do not overwrite Phase 1 raw results or aggregate outputs unless explicitly instructed.

### Phase 2: frozen expanded Claude Code backend matrix

Phase 2 expanded the fixed Claude Code harness matrix to:

1. Anthropic Haiku
2. Anthropic Sonnet
3. Anthropic Opus
4. DeepSeek V4-Pro
5. DeepSeek V4-Flash

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 5 arms = 300 scored trials
```

Source-of-truth aggregate:

```text
results/phase2/combined.csv
```

Smoke and canary results are preserved separately under:

```text
results/phase2/smoke/
results/phase2/canary/
```

Do not treat Phase 2 smoke/canary outputs as part of the scored 300-trial sweep.

### Phase 3: active work

Phase 3 is intended to test router-mediated Claude Code provider expansion.

Candidate work includes:

* Gemini through a router/gateway
* OpenAI through a router/gateway
* xAI/Grok through a router/gateway
* previously tested Anthropic/DeepSeek models through the same router/gateway for comparability
* common config-driven run scripts and aggregation paths

Phase 3 outputs should go under:

```text
results/phase3/
figures/phase3/
docs/reports/phase3/
docs/plans/phase3/
artifacts/phase3/
```

## Non-negotiable rules

### Protect frozen results

Do not overwrite or delete:

```text
results/phase1/
results/phase2/
docs/reports/phase1/
docs/reports/phase2/
figures/phase1/
figures/phase2/
```

unless the user explicitly asks.

When generating new Phase 3 outputs, use:

```text
results/phase3/
```

### Protect secrets

Never commit:

```text
.env
.secrets/
*.env
real API keys
real auth tokens
local credential files
```

Expected local secret files:

```text
.secrets/anthropic.env
.secrets/deepseek.env
.secrets/gemini.env
.secrets/openai.env
.secrets/xai.env
```

These files are local-only and must remain ignored.

### Do not commit local/generated junk

Do not commit:

```text
.venv/
__pycache__/
.pytest_cache/
.DS_Store
snapshot_*.md
phase*_snapshot_*.md
temporary scratch files
```

Snapshot files are for chat/review context only unless explicitly requested.

### Prefer config-driven execution

The Phase 3 direction is to migrate away from one-off run scripts and toward config-driven commands.

Preferred pattern:

```bash
./scripts/run_arm.sh <phase> <arm>
```

Examples:

```bash
./scripts/run_arm.sh phase1 anthropic-sonnet
./scripts/run_arm.sh phase2 deepseek-pro
./scripts/run_arm.sh phase3-router router-gemini-flash
```

If the implementation is incomplete, update scripts/configs incrementally and document the exact current behavior.

### Keep phase configs and arm configs separate

Phase-level config belongs in:

```text
configs/phases/
```

Arm/provider-level config belongs in:

```text
configs/arms/
```

Task lists belong in:

```text
configs/tasks/
```

An arm config should not duplicate the phase identity if the phase is already selected by the run command and phase config.

### Maintain reproducibility

Every scored run should be reproducible from:

```text
configs/phases/<phase>.yaml
configs/arms/<arm>.yaml
configs/tasks/<task-list>.txt
scripts/run_arm.sh
scripts/aggregate_phase.py
```

Every scored phase should produce:

```text
results/<phase>/combined.csv
```

### Do not rerun paid benchmarks casually

Full sweeps incur real API cost.

Before running a full paid sweep:

1. Run syntax checks.
2. Run a canary.
3. Run a small smoke test.
4. Confirm observed model routing.
5. Confirm output directory.
6. Confirm budget/concurrency.

## Canonical directories

```text
configs/
  arms/        # model/provider/route configs
  phases/      # phase-level benchmark configs
  tasks/       # task list files

docs/
  plans/       # phase plans
  reference/   # glossary, model matrix, task-selection notes
  reports/     # phase-specific reports and analysis
  runbooks/    # operator and collaboration docs

results/
  phase1/      # frozen Phase 1 results
  phase2/      # frozen Phase 2 results
  phase3/      # active Phase 3 results
  phase4/      # future
  phase5/      # future

figures/
  phase1/
  phase2/
  phase3/
  phase4/
  phase5/

artifacts/
  phase1/
  phase2/
  phase3/
  phase4/
  phase5/

scripts/
  lib/
  old-scripts/ # temporary migration backup only
```

## Source-of-truth aggregates

Use these files as source of truth:

```text
results/phase1/combined.csv
results/phase2/combined.csv
results/phase3/combined.csv
```

Do not use smoke/canary aggregates as scored benchmark results.

## Checks before committing

Run:

```bash
make check
make secret-scan
git status --short
```

or directly:

```bash
bash scripts/check.sh
bash scripts/secret_scan.sh
git status --short
```

Also inspect staged files:

```bash
git diff --cached --stat
git diff --cached --name-only
```

## Expected commit style

Use small, reviewable commits.

Good examples:

```text
docs: add phase3 runbooks
scripts: add config-driven arm runner
configs: add phase3 router arm stubs
analysis: add phase2 aggregate compatibility check
```

Avoid mixing unrelated changes such as docs, raw results, script refactors, and report rewrites in one large commit unless explicitly requested.

## When adding a new model arm

1. Add or update an arm config under `configs/arms/`.
2. Confirm required secret file and environment variables.
3. Run a canary.
4. Run a smoke test.
5. Confirm observed model metadata from raw logs.
6. Only then run a full sweep.
7. Aggregate results into the correct phase output.
8. Update the relevant plan/report notes.

## When adding a new phase

1. Add `configs/phases/<phase>.yaml`.
2. Add `results/<phase>/raw/`, `results/<phase>/smoke/`, `results/<phase>/canary/`, and `results/<phase>/supplemental/`.
3. Add `figures/<phase>/`.
4. Add `docs/plans/<phase>/`.
5. Add `docs/reports/<phase>/`.
6. Update `README.md`.
7. Update `docs/runbooks/REPO_MAP.md` if layout changes.
8. Do not modify frozen prior phases unless explicitly asked.

## Review priorities

When reviewing work in this repo, prioritize:

1. No secrets committed.
2. Frozen Phase 1/2 results preserved.
3. Phase-specific outputs kept separate.
4. Commands are reproducible.
5. Aggregates can be regenerated from committed raw outputs.
6. Reports distinguish full sweeps from smoke/canary findings.
7. New model/provider arms record observed model metadata.
8. Cost accounting is explicit and phase-specific.