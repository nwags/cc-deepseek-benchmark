# Claude Code Backend Benchmark

Benchmarking Claude Code model/provider backends on Terminal-Bench 2.0 using Harbor.

Current active branch:

```text
main
```

`main` is active again after the Phase 3 closeout and hand-off merges. Phase 1 and Phase 2 remain frozen benchmark baselines. Phase 3 and post-Phase-3 addendum outputs are preserved under phase-specific result and report paths.

## New team members: REQUIRED hand-off onboarding

> **If you are joining, taking over, supervising, or contributing to this
> project for the first time, complete the hand-off onboarding before beginning
> substantive project work.**

**Reading this root README alone is not sufficient onboarding.**

The required starting point is:

**[`docs/guides/README.md`](docs/guides/README.md) - required hand-off and onboarding index**

That index contains the required reading order, dashboard access instructions,
complete dashboard walkthrough, evidence-tracing exercises, project-state
boundaries, and completion criteria.

Every incoming team member is expected to review the three primary guides in
this order:

1. **[Dashboard Research Guide](docs/guides/DASHBOARD_RESEARCH_GUIDE.md)**
   Learn what evidence already exists, what every dashboard surface means, how
   scopes differ, and how to investigate results before proposing new runs.

2. **[Codebase Guide](docs/guides/CODEBASE_GUIDE.md)**
   Learn how execution, publication, live supervision, reviewed snapshots,
   Supabase/R2, dashboard loaders, validation, and provenance boundaries fit
   together.

3. **[Project Handoff and Future Roadmap](docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md)**
   Learn the current project state, successor-team priorities, infrastructure
   horizon, deferred work, and the conditions for eventually activating
   Phase 4 and Phase 5.

PDF convenience snapshots are stored beside the authoritative Markdown:

- [Dashboard Research Guide PDF](docs/guides/DASHBOARD_RESEARCH_GUIDE.pdf)
- [Codebase Guide PDF](docs/guides/CODEBASE_GUIDE.pdf)
- [Project Handoff and Future Roadmap PDF](docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.pdf)

**The Markdown files are authoritative.** The PDFs are generated convenience
snapshots for reading, sharing, or offline review. If a PDF and Markdown file
ever disagree, use the Markdown file.

### Dashboard review is REQUIRED

A request to **"review the dashboard" means review the whole dashboard**, not
only the Overview page or only the pages that initially appear relevant.

Incoming team members are expected to open and inspect all 15 principal
dashboard surfaces:

`Overview`, `Architecture`, `Data Model`, `Glossary`, `Trial Quality`,
`Cross-phase`, `Eval Suites`, `Evals`, `Runs`, `Live Runs`, `Arms`,
`Artifacts`, `Evidence Review`, `Planner`, and `Cost Coverage`.

The detailed required walkthrough and the minimum question each page should
answer are in `docs/guides/README.md` and the Dashboard Research Guide.

Dashboard access/setup instructions are in:

- [`apps/dashboard/README.md`](apps/dashboard/README.md)
- `docs/guides/README.md`

If a shared dashboard URL has been provided to the team, use it. Otherwise,
follow the documented local setup. If required dashboard access or
`SUPABASE_DB_URL` is unavailable, request access rather than silently skipping
the dashboard review.

If a dashboard surface cannot be accessed, is unclear, or appears inconsistent
with the guides, **record the problem and ask about it; do not silently skip
the page and treat onboarding as complete.**

### What onboarding does not authorize

Completing onboarding does **not** authorize a new paid sweep, Phase 4,
provider probes, protected dashboard dispatch, migration reapplication,
Supabase/R2 benchmark writes, runner-topology redesign, or modification of
frozen/reviewed benchmark evidence.

The intended order is:

    read the hand-off guides
      -> obtain dashboard access
      -> review the complete dashboard
      -> inspect existing evidence
      -> reproduce evidence traces
      -> identify research questions
      -> propose targeted work
      -> activate new experiments only when justified

Do not begin with a broad refactor or a new paid benchmark run.

## Project question

Claude Code is an agent harness: it decides when to read files, run shell commands, edit code, use tools, and re-plan. The model backend is the language model called inside that loop.

This project asks:

```text
What happens when the Claude Code agent harness is held fixed but the model/provider backend changes?
```

The benchmark uses:

* Claude Code as the fixed terminal-agent harness
* Harbor as the benchmark runner
* Terminal-Bench 2.0 as the task substrate
* phase-specific model/backend arms
* trial-level raw outputs and aggregate CSVs for analysis

## Harbor CLI version note

The assignment PDF references older Harbor commands such as:

```bash
harbor list-datasets
harbor run --dataset terminal-bench@2.0
```

## Environment used

- Node.js: v24.14.0
- npm: 11.14.1
- Claude Code: 2.1.140
- Docker: 29.4.3
- Docker Compose: v5.1.3
- uv: 0.10.11
- Python via uv/Conda: 3.13.12
- Harbor: 0.6.6
- Dataset: terminal-bench@2.0

## Current branch: main after Phase 3 closeout

The active development branch is `main`. Use short-lived feature branches for dashboard cleanup, manual verification, addendum ingestion, and follow-on benchmark work.

Phase 3 introduced:

* repo housekeeping and collaboration-oriented refactoring
* config-driven phase/arm execution
* router-mediated Claude Code provider expansion
* Gemini, OpenAI, xAI/Grok, Kimi, Qwen, GLM, and Anthropic router arms
* dashboard, Supabase, R2, cost coverage, and qualitative audit scaffolding

Phase 3 results remain under:

```text
results/phase3/
```

Phase 3 reports remain under:

```text
docs/reports/phase3/
```

Phase 3 plans remain under:

```text
docs/plans/phase3/
```

Post-Phase-3 addendum arms, such as Kimi K3, may also use the Phase-3-compatible router harness and reporting structure. Dashboard visibility depends on whether the run artifacts have been ingested into the dashboard database/R2 layer.

## Phase 1: frozen baseline

Phase 1 compared three Claude Code backend configurations:

| Arm               | Backend                                | Model/routing                             |
| ----------------- | -------------------------------------- | ----------------------------------------- |
| Anthropic Sonnet  | Anthropic native                       | `claude-sonnet-4-6`                       |
| DeepSeek V4-Pro   | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-pro` / `deepseek-v4-pro[1m]` |
| DeepSeek V4-Flash | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-flash`                       |

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 3 arms = 180 trials
```

Source-of-truth aggregate:

```text
results/phase1/combined.csv
```

Phase 1 raw outputs:

```text
results/phase1/raw/
```

Phase 1 reports:

```text
docs/reports/phase1/
```

Phase 1 figures:

```text
figures/phase1/
```

Headline result:

* Anthropic Sonnet: 39/60 = 65.0%
* DeepSeek V4-Pro: 42/60 = 70.0%
* DeepSeek V4-Flash: 37/60 = 61.7%

DeepSeek V4-Pro matched Anthropic quality at dramatically lower cost, but was much slower. DeepSeek V4-Flash was cheapest and near Anthropic speed but slightly lower quality.

## Phase 2: frozen expanded Claude Code backend matrix

Phase 2 expanded the model/backend matrix while keeping Claude Code and the selected 20 Terminal-Bench tasks fixed.

Scored Phase 2 arms:

| Arm               | Backend                                | Model/routing               |
| ----------------- | -------------------------------------- | --------------------------- |
| Anthropic Haiku   | Anthropic native                       | `claude-haiku-4-5-20251001` |
| Anthropic Sonnet  | Anthropic native                       | `claude-sonnet-4-6`         |
| Anthropic Opus    | Anthropic native                       | `claude-opus-4-7`           |
| DeepSeek V4-Pro   | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-pro[1m]`       |
| DeepSeek V4-Flash | DeepSeek Anthropic-compatible endpoint | `deepseek-v4-flash`         |

Design:

```text
20 Terminal-Bench 2.0 tasks x 3 attempts x 5 arms = 300 scored trials
```

Source-of-truth aggregate:

```text
results/phase2/combined.csv
```

Phase 2 raw outputs:

```text
results/phase2/raw/
```

Phase 2 smoke and canary outputs:

```text
results/phase2/smoke/
results/phase2/canary/
```

Phase 2 reports:

```text
docs/reports/phase2/
```

Phase 2 figures:

```text
figures/phase2/
```

Headline result:

* Anthropic Opus: 45/60 = 75.0%
* Anthropic Sonnet: 40/60 = 66.7%
* DeepSeek V4-Pro: 39/60 = 65.0%
* DeepSeek V4-Flash: 35/60 = 58.3%
* Anthropic Haiku: 26/60 = 43.3%

Opus achieved the highest Phase 2 success rate. DeepSeek Pro remained close to Sonnet quality at much lower cost but with slower runtime. Flash was extremely cheap and moderately competitive. Haiku was fast but substantially weaker on this task mix.

## Reports

Phase-specific reports live under:

```text
docs/reports/
```

Important report locations:

```text
docs/reports/phase1/REPORT.md
docs/reports/phase1/analysis.md
docs/reports/phase1/FINDINGS.md
docs/reports/phase1/QUALITATIVE_TRANSCRIPT_REVIEW.md

docs/reports/phase2/PHASE2_REPORT.md
docs/reports/phase2/analysis.md
```

Plans live under:

```text
docs/plans/
```

Reference docs live under:

```text
docs/reference/
```

Runbooks live under:

```text
docs/runbooks/
```

## Results

Results are phase-specific.

```text
results/
  phase1/
    raw/
    supplemental/
    combined.csv

  phase2/
    raw/
    smoke/
    canary/
    supplemental/
    combined.csv
    smoke-combined.csv

  phase3/
    raw/
    smoke/
    canary/
    supplemental/
```

Source-of-truth aggregates:

```text
results/phase1/combined.csv
results/phase2/combined.csv
results/phase3/combined.csv
```

Do not use smoke/canary outputs as if they were scored full-sweep results.

## Figures

Figures are phase-specific.

```text
figures/
  phase1/
  phase2/
  phase3/
  phase4/
  phase5/
```

Reports should use relative paths that match their final locations.

For example, a report under `docs/reports/phase2/` should reference a Phase 2 figure with a path such as:

```md
../../../figures/phase2/phase2_success_rate.png
```

## Configuration

The repo uses config-driven run definitions introduced during Phase 3.

Configuration directories:

```text
configs/
  arms/     # model/provider/route configs
  phases/   # phase-level benchmark settings
  tasks/    # task lists
```

Task lists:

```text
configs/tasks/tasks.txt
configs/tasks/tasks.full.txt
configs/tasks/terminal-bench-20.txt
configs/tasks/phase2-smoke.txt
configs/tasks/phase2-canary.txt
configs/tasks/terminal_bench_2_all_tasks.txt
```

During migration, confirm that task-list files under `configs/tasks/` are populated before using them as canonical inputs.

## Secrets

Do not commit secrets.

Expected local-only secret files:

```text
.secrets/anthropic.env
.secrets/deepseek.env
.secrets/gemini.env
.secrets/openai.env
.secrets/xai.env
```

Example `.secrets/anthropic.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Example `.secrets/deepseek.env`:

```bash
DEEPSEEK_API_KEY=sk-...
```

`.secrets/` and `.env` must remain ignored.

## Reproduce aggregation without rerunning paid benchmarks

The raw results and aggregate CSVs are committed so analysis can be reproduced without rerunning paid model sweeps.

### Phase 1 aggregation

```bash
uv run python scripts/aggregate_phase.py phase1
```

Expected output:

```text
results/phase1/combined.csv
```

### Phase 2 aggregation

```bash
uv run python scripts/aggregate_phase.py phase2
```

Expected output:

```text
results/phase2/combined.csv
```

If the new config-driven aggregation is still being migrated, use the compatibility command documented in `docs/runbooks/RUNBOOK.md` or inspect:

```bash
python scripts/aggregate_phase.py --help
```

Do not rerun a full benchmark sweep just to regenerate tables.

## Run a benchmark arm

The config-driven benchmark command shape is:

```bash
./scripts/run_arm.sh <phase> <arm>
```

Examples:

```bash
./scripts/run_arm.sh phase1 anthropic-sonnet
./scripts/run_arm.sh phase2 deepseek-pro
./scripts/run_arm.sh phase3-router router-gemini-flash
```

For smoke/canary work, use the relevant phase config or environment variables documented in the runbook.

Full sweeps incur real API cost. Always run canary/smoke checks before a full paid sweep.

## Checks before committing

Run:

```bash
make check
make secret-scan
git status --short
```

Equivalent direct commands:

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

## Repository map

```text
cc-deepseek-bench/
  AGENTS.md
  README.md
  Makefile
  pyproject.toml
  uv.lock

  configs/
    arms/
    phases/
    tasks/

  docs/
    guides/      # required hand-off and successor-team onboarding
    plans/
    reference/
    reports/
    runbooks/

  scripts/
    lib/
    old-scripts/
    aggregate_phase.py
    check.sh
    generate_figures.py
    run_arm.sh
    secret_scan.sh
    summarize_trials.py

  results/
    phase1/
    phase2/
    phase3/
    phase4/
    phase5/

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
```

## Collaboration and hand-off docs

**New team members must start with the hand-off guide index before using the
operational runbooks as their primary orientation:**

    docs/guides/README.md

Required hand-off reading:

    docs/guides/DASHBOARD_RESEARCH_GUIDE.md
    docs/guides/CODEBASE_GUIDE.md
    docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md

Then use the collaboration and operational references appropriate to the work:

    AGENTS.md
    apps/dashboard/README.md
    docs/runbooks/RUNBOOK.md
    docs/runbooks/COLLABORATION.md
    docs/runbooks/ARTIFACT_POLICY.md
    docs/runbooks/EVAL_OPERATIONS.md
    docs/runbooks/LIVE_RUN_SUPERVISION.md
    docs/runbooks/BENCHMARK_CONTAMINATION.md
    docs/runbooks/REPO_MAP.md

Do not substitute one old plan, one runbook, or one dashboard page for the
required hand-off sequence. Historical documents are intentionally retained in
the repository and may describe project state that has since changed.

## Notes for contributors

* Phase 1 and Phase 2 are frozen.
* `main` is active again after the Phase 3 closeout merge.
* Keep outputs phase-specific.
* Treat Kimi K3 as a post-Phase-3 addendum unless a later phase explicitly supersedes it.
* Keep secrets out of Git.
* Do not conflate smoke/canary runs with scored sweeps.
* Prefer config-driven additions over one-off scripts.
* Update runbooks when commands or paths change.
