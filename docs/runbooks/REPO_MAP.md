# Repository Map

This repository is organized around benchmark phases.

## Root files

| Path | Purpose |
|---|---|
| `README.md` | Front door for the project. Explains current branch, phase status, reports, results, and basic commands. |
| `AGENTS.md` | Operating instructions for agentic contributors and humans using coding agents. |
| `Makefile` | Short aliases for checks, secret scans, and aggregation commands. |
| `.env.example` | Non-secret template for local credentials. |
| `.gitignore` | Prevents secrets, virtualenvs, snapshots, and generated junk from being committed. |
| `pyproject.toml`, `uv.lock` | Python/uv environment metadata. |

## Configs

```text
configs/
  arms/      model/provider arm configs
  phases/    phase-level benchmark configs
  tasks/     canonical task lists
```

Use `configs/tasks/tasks.txt` or `configs/tasks/terminal-bench-20.txt` for the selected 20-task benchmark set.

## Scripts

```text
scripts/
  lib/                 shared Python helpers
  old-scripts/          migration backup only
  aggregate_phase.py    intended phase-aware aggregate entry point
  check.sh              repository checks
  generate_figures.py   intended figure-generation entry point
  run_arm.sh            intended config-driven arm runner
  secret_scan.sh        secret scanner
  summarize_trials.py   intended compact trial summarizer
```

Do not add new functionality to `scripts/old-scripts/`.

## Docs

```text
docs/
  plans/       phase plans
  reference/   glossary, model matrix, task selection notes
  reports/     phase-specific reports and analysis
  runbooks/    operational/collaboration docs
```

## Results

```text
results/
  phase1/      frozen Phase 1 outputs
  phase2/      frozen Phase 2 outputs
  phase3/      active Phase 3 outputs
  phase4/      future
  phase5/      future
```

Canonical aggregates:

```text
results/phase1/combined.csv
results/phase2/combined.csv
results/phase3/combined.csv
```

Smoke and canary outputs must not be treated as full scored sweeps.

## Figures

```text
figures/
  phase1/
  phase2/
  phase3/
  phase4/
  phase5/
```

Reports under `docs/reports/<phase>/` should use relative paths to the appropriate `figures/<phase>/` directory.

## Artifact distinction

* Full scored raw outputs: `results/<phase>/raw/`
* Smoke outputs: `results/<phase>/smoke/`
* Canary outputs: `results/<phase>/canary/`
* Supplemental generated tables: `results/<phase>/supplemental/`
* Report figures: `figures/<phase>/`