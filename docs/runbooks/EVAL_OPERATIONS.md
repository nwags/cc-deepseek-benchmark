# Eval Operations

This runbook covers reusable helper commands for benchmark eval suites, arm-run artifact waves, ingestion manifests, R2/Supabase ingestion, and quality audits. The tools are suite-oriented rather than phase-specific. Phase 3 examples are shown because that is the active branch and current operating context.

## Concepts

- `SUITE_ID` identifies a benchmark eval suite, such as `phase3-full-20`.
- `ARMS` optionally limits commands to specific arm ids.
- `RUNS` maps GitHub Actions run ids to arm ids as `<github_run_id>:<arm_id>`.
- `DEST` is the local artifact download root, normally under `tmp/`.
- `RUN_DIRS_FILE` is a TSV file containing discovered top-level run directories.

When `configs/eval_suites/<suite_id>.yaml` exists, `scripts/eval_wave.py` uses it to infer the suite phase, suite type, task count, logical mode, and expected trial count. When a matching phase config exists under `configs/phases/`, mode-to-storage mapping such as `full -> raw` is read from that config.

## Artifact Wave

Example Phase 3 full-sweep wave:

```bash
export SUITE_ID=phase3-full-20
export PHASE=phase3
export RUNS="28274456798:router-anthropic-sonnet 28274460577:router-gemini-flash 28274462238:router-gpt-5.5"
export DEST=tmp/phase3-full-artifacts/wave-20260627
export RUN_DIRS_FILE=tmp/phase3_wave_20260627_run_dirs.tsv
export ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

List available GitHub Actions artifacts:

```bash
make eval-list-artifacts SUITE_ID=phase3-full-20 RUNS="$RUNS"
```

Download the wave:

```bash
make eval-download-wave RUNS="$RUNS" DEST="$DEST"
```

If the destination already exists and should be replaced:

```bash
make eval-download-wave RUNS="$RUNS" DEST="$DEST" OVERWRITE=1
```

Discover top-level Harbor run directories:

```bash
make eval-discover-wave SUITE_ID=phase3-full-20 RUNS="$RUNS" DEST="$DEST" RUN_DIRS_FILE="$RUN_DIRS_FILE"
```

For the Phase 3 full suite, the helper infers 60 expected trials from 20 suite tasks and 3 configured attempts, and it resolves physical storage mode `results/phase3/raw/...` from the Phase 3 phase config.

Build and validate local ingestion manifests without touching R2 or Supabase:

```bash
make eval-manifest-wave SUITE_ID=phase3-full-20 RUN_DIRS_FILE="$RUN_DIRS_FILE"
```

Ingest the wave to R2 and Supabase:

```bash
make eval-ingest-wave SUITE_ID=phase3-full-20 RUN_DIRS_FILE="$RUN_DIRS_FILE"
```

The ingest target sources ignored local secret files when present:

```text
.secrets/supabase.env
.secrets/r2.env
```

Required values are the same ones used by `scripts/ingest_phase3_run_metadata.py`, including `SUPABASE_DB_URL`, `R2_BUCKET`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`.

## Quality Audit

Summarize suite quality by arm:

```bash
make eval-suite-summary SUITE_ID=phase3-full-20 ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

Summarize individual arm runs:

```bash
make eval-arm-run-summary SUITE_ID=phase3-full-20 ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

Audit exception and suspect trials:

```bash
make eval-exception-audit SUITE_ID=phase3-full-20 ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

When `benchmark_trials.exception_summary` is blank, inspect local raw artifacts for `exception.txt` or `result.json` details:

```bash
make eval-exception-audit SUITE_ID=phase3-full-20 INSPECT_LOCAL=1 LOCAL_ROOTS="$DEST"
```

The audit script introspects the Supabase schema at runtime. It prefers `benchmark.v_suite_arm_quality_summary`, `benchmark.v_arm_run_quality_summary`, and `benchmark.v_trial_quality_flags` when present, and otherwise falls back to base-table joins. Fallback joins use `benchmark.benchmark_arm_runs.arm_id` for arm identity.

## Phase Aliases

The Phase 3 Make targets remain as convenience aliases:

```bash
make phase3-suite-summary SUITE_ID=phase3-full-20
make phase3-download-wave RUNS="$RUNS" DEST="$DEST"
make phase3-ingest-wave SUITE_ID=phase3-full-20 RUN_DIRS_FILE="$RUN_DIRS_FILE"
```

These call the corresponding `eval-*` targets.

## Guardrails

- Keep downloaded GitHub artifacts, generated manifests, and run-dir TSVs under `tmp/` unless a report explicitly needs a small derived summary.
- Do not copy raw provider exports, `.env` files, or `.secrets/` contents into Git.
- Preserve frozen Phase 1 and Phase 2 directories. Do not point these helpers at `results/phase1/` or `results/phase2/` unless explicitly instructed.
- Run `make check`, `make secret-scan`, and `git diff --check` before committing helper or documentation changes.
