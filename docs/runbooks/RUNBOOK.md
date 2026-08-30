# Runbook

Command-focused operating guide for the Claude Code backend benchmark repository.

Accepted baseline branch:

```text
main
```

Phase 1 and Phase 2 are frozen. Phase 3 is complete and closed. Phase 4 is
planned future work and Phase 5 remains after Phase 4.

Use short-lived feature branches for new work.

Current successor-team guidance begins in:

```text
docs/guides/README.md
```

Page-specific dashboard interpretation:

```text
docs/guides/dashboard/README.md
```

Current durable evidence-promotion review procedure:

```text
docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md
```

Current provider usage/cost automation reference:

```text
docs/reference/PROVIDER_USAGE_COST_AUTOMATION.md
```

## 0. Quick status

```bash
git branch --show-current
git status --short
```

When beginning new work from the accepted baseline, start from:

```text
main
```

If already on a reviewed feature branch, confirm that the branch and HEAD match
the intended work before making changes.

## 1. Install / setup

This repo uses Python/uv, Node/Claude Code, Docker, Harbor, and Terminal-Bench.

Basic setup:

```bash
uv sync
npm install -g @anthropic-ai/claude-code
docker --version
claude --version
uv run harbor --help
```

Check Python package state:

```bash
uv run python --version
uv run python -c "import pandas; print('pandas ok')"
```

## 2. Secrets

Create local ignored secret files.

```bash
mkdir -p .secrets
```

Anthropic:

```bash
cat > .secrets/anthropic.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
EOF
```

DeepSeek:

```bash
cat > .secrets/deepseek.env <<'EOF'
DEEPSEEK_API_KEY=sk-...
EOF
```

Additional provider-specific local secret files may include:

```bash
cat > .secrets/gemini.env <<'EOF'
GEMINI_API_KEY=...
EOF

cat > .secrets/openai.env <<'EOF'
OPENAI_API_KEY=...
EOF

cat > .secrets/xai.env <<'EOF'
XAI_API_KEY=...
EOF
```

Confirm secrets are ignored:

```bash
git check-ignore -v .secrets/anthropic.env .secrets/deepseek.env .env
```

## 3. Checks before committing

Preferred:

```bash
make check
make secret-scan
git status --short
```

Direct:

```bash
bash scripts/check.sh
bash scripts/secret_scan.sh
git status --short
```

Inspect staged files:

```bash
git diff --cached --stat
git diff --cached --name-only
```

## 4. Repository map

Important locations:

```text
configs/arms/             model/provider arm configs
configs/phases/           phase configs
configs/tasks/            task lists

docs/plans/               phase plans
docs/reference/           glossary, model/task, evidence/automation references
docs/reports/             phase reports and analysis
docs/runbooks/            repo operation docs
docs/guides/              successor guides and dashboard page manual

results/phase1/           frozen Phase 1 outputs
results/phase2/           frozen Phase 2 outputs
results/phase3/           closed Phase 3 evidence/reporting

figures/phase1/           Phase 1 figures
figures/phase2/           Phase 2 figures
figures/phase3/           Phase 3 figures

scripts/                  current scripts
scripts/lib/              shared Python helpers
scripts/old-scripts/      temporary migration backup
```

## 5. Current benchmark execution policy

Phase 3 is closed. Do not use the retained Phase 3 canary, smoke, full-sweep,
aggregation, publication, or branch commands below as current authorization for
new benchmark work.

Before any future benchmark execution:

1. start from the accepted `main` baseline using a reviewed feature branch;
2. define a new phase/suite identity;
3. follow the research and activation criteria in
   `docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md`;
4. use cheap/local integration checks where practical;
5. use canary and smoke gates before any approved paid full sweep;
6. preserve frozen Phase 1/2/3 evidence.

For a reviewed Canary -> Smoke or Smoke -> Full advancement decision, use:

    docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md

The current durable sequence is:

    Plan -> Check -> Rollback-only verification -> Apply

The Planner remains read-only. It consumes current fail-closed promotion
evidence but does not durably record the review or dispatch benchmark work.

For implementation details, use:

    docs/guides/CODEBASE_GUIDE.md

For provider usage/cost collection capabilities, credential/granularity
boundaries, current repository automation, and the prospective collector
expansion order, use:

    docs/reference/PROVIDER_USAGE_COST_AUTOMATION.md

That reference is the current navigation point for provider telemetry work. It
does not itself authorize a provider probe or paid benchmark execution.

## Historical pre-closeout operating record

> **Historical boundary — 2026-08-23:** Everything below this heading is
> retained as pre-closeout operating provenance. It records commands, branch
> practices, migration-era procedures, and Phase 3 execution guidance that were
> useful while the benchmark phases were being built and run. It is not the
> current operating contract. Do not execute a historical paid-run, publication,
> migration, or branch command merely because it appears below. Check the
> current guides and current implementation first.

## 5. Task lists

Canonical task-list directory:

```text
configs/tasks/
```

Main selected 20-task list:

```text
configs/tasks/tasks.txt
```

Equivalent selected 20-task list, if populated:

```text
configs/tasks/terminal-bench-20.txt
```

Full Terminal-Bench 2.0 task listing:

```text
configs/tasks/terminal_bench_2_all_tasks.txt
```

Phase 2 smoke/canary lists:

```text
configs/tasks/phase2-smoke.txt
configs/tasks/phase2-canary.txt
```

During migration, confirm these files are populated:

```bash
wc -l configs/tasks/tasks.txt
wc -l configs/tasks/terminal-bench-20.txt
wc -l configs/tasks/phase2-smoke.txt
wc -l configs/tasks/phase2-canary.txt
```

If the `configs/tasks/` copies are empty, copy from the legacy/artifact copies before using them:

```bash
cp artifacts/phase2/tasks.phase2-smoke.txt configs/tasks/phase2-smoke.txt
cp artifacts/phase2/tasks.phase2-canary.txt configs/tasks/phase2-canary.txt
cp configs/tasks/tasks.txt configs/tasks/terminal-bench-20.txt
```

## 6. Aggregation without rerunning paid benchmarks

Do not rerun paid full sweeps just to regenerate analysis.

### Phase 1

Preferred new command:

```bash
uv run python scripts/aggregate_phase.py phase1
```

Expected output:

```text
results/phase1/combined.csv
```

### Phase 2

Preferred new command:

```bash
uv run python scripts/aggregate_phase.py phase2
```

Expected output:

```text
results/phase2/combined.csv
```

### Phase 3

Preferred new command:

```bash
uv run python scripts/aggregate_phase.py phase3
```

Expected output:

```text
results/phase3/combined.csv
```

If the new aggregate interface changes, inspect:

```bash
uv run python scripts/aggregate_phase.py --help
```

## 7. Inspect aggregate summaries

Phase 1:

```bash
python - <<'PY'
import pandas as pd

df = pd.read_csv("results/phase1/combined.csv")
print(df.groupby("arm_dir").agg(
    trials=("success", "count"),
    successes=("success", "sum"),
    success_rate=("success", "mean"),
    total_cost=("effective_cost_usd", "sum"),
    median_wall=("wall_clock_seconds", "median"),
))
PY
```

Phase 2:

```bash
python - <<'PY'
import pandas as pd

df = pd.read_csv("results/phase2/combined.csv")
print(df.groupby("arm_dir").agg(
    trials=("success", "count"),
    successes=("success", "sum"),
    success_rate=("success", "mean"),
    total_cost=("effective_cost_usd", "sum"),
    median_wall=("wall_clock_seconds", "median"),
    median_turns=("agent_turns", "median"),
    median_tools=("tool_calls", "median"),
    median_bash=("bash_calls", "median"),
))
PY
```

Failure modes:

```bash
python - <<'PY'
import pandas as pd

df = pd.read_csv("results/phase2/combined.csv")
print(pd.crosstab(df["arm_dir"], df["failure_mode"]))
PY
```

Observed models:

```bash
python - <<'PY'
import pandas as pd

df = pd.read_csv("results/phase2/combined.csv")
print(df.groupby(["arm_dir", "observed_model_primary"], dropna=False).size())
PY
```

## 8. Running arms

The intended Phase 3 command shape is:

```bash
./scripts/run_arm.sh <phase> <arm>
```

Examples:

```bash
./scripts/run_arm.sh phase1 anthropic-sonnet
./scripts/run_arm.sh phase2 anthropic-opus
./scripts/run_arm.sh phase2 deepseek-pro
./scripts/run_arm.sh phase3-router router-gemini-flash
```

If the script supports modes, use:

```bash
./scripts/run_arm.sh <phase> <arm> --mode canary
./scripts/run_arm.sh <phase> <arm> --mode smoke
./scripts/run_arm.sh <phase> <arm> --mode full
```

If the mode interface is not implemented yet, use phase configs or environment variables as documented by:

```bash
./scripts/run_arm.sh --help
```

or inspect the script before running:

```bash
sed -n '1,220p' scripts/run_arm.sh
```

## 9. Canary runs

A canary is a tiny routing test, usually one task.

Purpose:

* confirm credentials
* confirm provider routing
* confirm observed model
* confirm Harbor/Claude Code can start
* avoid wasting money on broken full sweeps

Expected output path:

```text
results/<phase>/canary/<arm>/
```

Example intended command:

```bash
./scripts/run_arm.sh phase3-router router-gemini-flash --mode canary
```

After canary, inspect:

```bash
find results/phase3/canary -name result.json | head
grep -R "model" results/phase3/canary/router-gemini-flash -n | head -20
```

## 10. Smoke runs

A smoke run is a small multi-task run.

Purpose:

* confirm the arm can handle more than one task
* validate costs
* validate aggregation
* catch early systematic failures

Expected output path:

```text
results/<phase>/smoke/<arm>/
```

Example intended command:

```bash
./scripts/run_arm.sh phase3-router router-gemini-flash --mode smoke
```

Do not mix smoke outputs into the full scored aggregate.

## 11. Full scored sweeps

Full sweeps incur API cost.

Before running a full sweep:

```bash
make check
make secret-scan
git status --short
```

Confirm:

* correct branch
* correct phase
* correct arm
* correct task list
* correct output directory
* correct secret file
* canary completed
* smoke completed
* budget is approved

Expected output path:

```text
results/<phase>/raw/<arm>/
```

Example intended command:

```bash
./scripts/run_arm.sh phase3-router router-gemini-flash --mode full
```

After the full sweep:

```bash
uv run python scripts/aggregate_phase.py phase3
```

## 12. Oracle sanity

Oracle sanity checks are useful when changing task lists or validating selected tasks.

Expected output:

```text
results/<phase>/canary/oracle/
```

or phase-specific equivalent.

Example intended command:

```bash
./scripts/run_arm.sh phase3-router oracle --mode canary
```

If the config-driven oracle path is not implemented, use a direct Harbor command and write to an explicitly phase-scoped output directory.

## 13. Figure generation

Preferred:

```bash
uv run python scripts/generate_figures.py phase1
uv run python scripts/generate_figures.py phase2
uv run python scripts/generate_figures.py phase3
```

Expected outputs:

```text
figures/phase1/
figures/phase2/
figures/phase3/
```

If the script interface differs, inspect:

```bash
uv run python scripts/generate_figures.py --help
```

## 14. Trial summaries

Preferred:

```bash
uv run python scripts/summarize_trials.py phase2
uv run python scripts/summarize_trials.py phase3
```

Expected outputs:

```text
results/<phase>/supplemental/trial_summaries.jsonl
```

If the script interface differs, inspect:

```bash
uv run python scripts/summarize_trials.py --help
```

## 15. Secret scan

Run:

```bash
bash scripts/secret_scan.sh
```

Manual strict scan pattern:

```bash
grep -R --line-number --binary-files=without-match \
  -E 'sk-ant-api[0-9]+-[A-Za-z0-9_-]{40,}|sk-[A-Za-z0-9_-]{32,}|DEEPSEEK_API_KEY=[^.$<][^[:space:]]+|ANTHROPIC_AUTH_TOKEN=[^$<][^[:space:]]+' \
  scripts docs configs results \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=.secrets \
  --exclude='*.lock' \
  --exclude='.env' || true

git check-ignore -v .secrets/anthropic.env .secrets/deepseek.env .env
```

Expected false positives may include placeholder examples such as:

```text
sk-ant-...
sk-...
```

Investigate every match before committing.

## 16. Commit checklist

Before commit:

```bash
make check
make secret-scan
git status --short
git diff --stat
```

Stage intentionally:

```bash
git add AGENTS.md README.md docs/runbooks scripts configs
```

Inspect staged files:

```bash
git diff --cached --stat
git diff --cached --name-only
```

Commit:

```bash
git commit -m "docs: add phase3 collaboration runbooks"
```

Push current branch:

```bash
git push -u origin phase3
```

## 17. Common gotchas

### Empty config files

Some configs may exist as stubs during migration.

Check before using:

```bash
find configs -type f -size 0 -print
```

### Report image paths

After moving reports into `docs/reports/<phase>/`, figure paths may need to be adjusted.

From `docs/reports/phase1/REPORT.md`, Phase 1 figures should usually be referenced as:

```md
../../../figures/phase1/success_rate.png
```

From `docs/reports/phase2/PHASE2_REPORT.md`, Phase 2 figures should usually be referenced as:

```md
../../../figures/phase2/phase2_success_rate.png
```

### Old scripts

`scripts/old-scripts/` is a migration backup.

Do not add new functionality there.

Once the new scripts reproduce Phase 1 and Phase 2, delete `scripts/old-scripts/`.

### Paid reruns

Do not rerun full sweeps unless the task explicitly requires it and budget is approved.

Prefer:

```bash
uv run python scripts/aggregate_phase.py <phase>
```

over rerunning benchmark arms.

## 18. Phase freeze checklist

Before freezing a phase:

* [ ] raw scored outputs are under `results/<phase>/raw/`
* [ ] smoke/canary outputs are separate
* [ ] aggregate exists at `results/<phase>/combined.csv`
* [ ] figures exist under `figures/<phase>/`
* [ ] report exists under `docs/reports/<phase>/`
* [ ] plan exists under `docs/plans/<phase>/`
* [ ] README points to the phase outputs
* [ ] runbook commands are current
* [ ] checks pass
* [ ] secret scan passes
* [ ] no snapshot files are committed
* [ ] branch is committed and pushed

## Phase 3 runner firewall requirement

Phase 3 router arms run Claude Code inside Harbor/Docker containers and send Anthropic-compatible API traffic to the host LiteLLM proxy on TCP port 4000.

On VPS runners with UFW enabled, Docker bridge traffic to the host may be blocked even when the host itself can reach LiteLLM. This causes Claude Code inside Harbor to retry API calls until Harbor raises `AgentTimeoutError` with zero model tokens.

Required persistent UFW rules on the VPS runner:

    -A ufw-before-input -i docker0 -s 172.17.0.0/16 -p tcp --dport 4000 -j ACCEPT
    -A ufw-before-input -i br+ -s 172.16.0.0/12 -p tcp --dport 4000 -j ACCEPT

These rules belong in `/etc/ufw/before.rules` before the first `COMMIT`, followed by:

    sudo ufw reload

Validation:

    ./scripts/check_phase3_docker_host_firewall.sh

The runner doctor workflow includes this check so Phase 3 paid benchmark dispatches do not silently fail because containers cannot reach the host LiteLLM proxy.

<!-- phase3-2026-06-12-alignment:start -->
## 2026-06-12 Phase 3 dashboard and planner operating guidance

The dashboard is a read-only operating console unless a planner-generated dispatch is explicitly reviewed and launched through GitHub Actions.

Planner run types:

- `canary`: one known canary task; route/infrastructure gate.
- `smoke`: small multi-task gate; next benchmark milestone.
- `full-sweep`: large benchmark battery; final scored Phase 3 comparison when approved.
- `ad-hoc`: one-off diagnostic run; not scored unless explicitly promoted.

Implementation note: GitHub Actions currently uses `mode=full`; dashboard language may call this `full-sweep`, but dispatch payloads should use `mode=full` unless the workflow is changed.

Before dispatching paid runs, check:

1. runner doctor passed,
2. Docker-to-host LiteLLM firewall path passed,
3. required provider secrets exist,
4. LiteLLM route probe passed for any new provider,
5. direct provider probe passed for gated/unknown models,
6. cost and runtime estimates were reviewed.

Hosted NVIDIA NIM has been retired from the active Phase 3 plan. Self-hosted NIM and local open-weight model serving remain tabled.
<!-- phase3-2026-06-12-alignment:end -->

## Historical branch lifecycle context

During Phase 3 development, the `phase3` branch and `main` had roles that differ
from the current repository state.

That historical branch model is superseded. The current accepted baseline and
feature-branch policy are documented above this historical boundary and in:

    docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md

## Phase 3 smoke run guardrails

Use `docs/plans/phase3/PHASE3_SMOKE_PLAN.md` as the source of truth for smoke sequencing.

Initial smoke dispatches should be serial:

- one active benchmark workflow at a time,
- `mode=smoke`,
- `n_attempts=1`,
- `n_concurrent=1`,
- dry-run first,
- paid dispatch only with `confirm_paid_run=true` after review.

Do not start full-sweep work until the smoke plan review criteria and parallel runner blockers are satisfied.

## Phase 3 parallel runner guardrails

Current safe runner mode is serial: one active benchmark dispatch, `n_attempts=1`, and `n_concurrent=1` for initial smoke work.

Parallelism is intentionally blocked until runner-slot isolation exists. The planning rule is:

    effective_task_parallelism = active_runner_jobs * harbor_n_concurrent

Do not increase both workflow-level runner jobs and Harbor `--n-concurrent` at the same time. Full sweep requires tested runner slots, Docker cleanup, artifact upload, provider-family concurrency caps, and cost guardrails.

See `docs/reference/PHASE3_PARALLELISM_ARCHITECTURE.md`.

## Phase 3 ad-hoc diagnostics

Script-level ad-hoc task overrides are supported for diagnostics only:

```bash
./scripts/run_arm.sh phase3-router <arm-id> \
  --mode canary \
  --task-id modernize-scientific-stack \
  --ad-hoc-label <short-label> \
  --dry-run
```

Rules:

- `--task-id` runs one explicit Terminal-Bench task.
- `--task-file` runs an explicit task list.
- `--task-id` and `--task-file` are mutually exclusive.
- Any use of `--task-id`, `--task-file`, or `--ad-hoc-label` marks the run as ad-hoc and non-scored.
- Ad-hoc outputs are written under `results/phase3/ad-hoc/<label>/...`.
- Ad-hoc runs must not be included in scored canary, smoke, or full-sweep summaries unless explicitly promoted in a later reviewed commit.
- The Phase 3 dispatch workflow accepts `task_id`, `task_file`, and `ad_hoc_label` inputs on the `phase3` branch; the default-branch wrapper must be mirrored separately for manual dispatch.
