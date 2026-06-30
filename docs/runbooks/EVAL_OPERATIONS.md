# Eval Operations

This runbook covers reusable helper commands for benchmark eval suites, arm-run artifact waves, ingestion manifests, R2/Supabase ingestion, and quality audits. The tools are suite-oriented rather than phase-specific. Phase 3 examples are shown because that is the active branch and current operating context.

## Concepts

- `SUITE_ID` identifies a benchmark eval suite, such as `phase3-full-20`.
- `ARMS` optionally limits commands to specific arm ids.
- `RUNS` maps GitHub Actions run ids to arm ids as `<github_run_id>:<arm_id>`.
- `DEST` is the local artifact download root, normally under `tmp/`.
- `RUN_DIRS_FILE` is a TSV file containing discovered top-level run directories.
- `INVALID_RUNS_FILE` is an ignored local TSV used to exclude known-invalid provider runs from valid-only summaries.

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

For partial wave recovery, keep strict discovery as the default, then opt into skipping empty or missing artifact directories:

```bash
make eval-discover-wave \
  SUITE_ID=phase3-full-20 \
  RUNS="$RUNS" \
  DEST="$DEST" \
  RUN_DIRS_FILE="$RUN_DIRS_FILE" \
  SKIP_MISSING_RUN_DIRS=1
```

With `SKIP_MISSING_RUN_DIRS=1`, `discover-wave` writes valid run directories to `RUN_DIRS_FILE` and prints skipped rows to stderr as:

```text
skipped_run_dir	<github_run_id>	<arm_id>	<reason>	<artifact_root>
```

Use this only when the missing/empty run is intentionally being retried or excluded. Ambiguous discoveries, such as multiple matching top-level run dirs for the same arm/run pair, still fail.

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

## Remote Runner Recovery

The current Phase 3 runner fleet is six GitHub self-hosted runner slots across two VPS hosts:

| Host | SSH target | User mode | Runner directories |
| --- | --- | --- | --- |
| VPS-1 | `bench@51.81.81.176` | direct `bench` login | `/home/bench/actions-runner`, `/home/bench/actions-runner-slot2`, `/home/bench/actions-runner-slot3` |
| VPS-2 | `ubuntu@135.148.42.89` | `sudo -iu bench` | `/home/bench/actions-runner-slot4`, `/home/bench/actions-runner-slot5`, `/home/bench/actions-runner-slot6` |

The defaults live in `Makefile` and `scripts/eval_remote_ops.sh`. Override the inventory with Make/environment variables such as:

```bash
make eval-remote-runner-status \
  EVAL_REMOTE_HOSTS="vps1 vps2" \
  EVAL_REMOTE_VPS1_HOST=bench@51.81.81.176 \
  EVAL_REMOTE_VPS2_HOST=ubuntu@135.148.42.89
```

Check runner services, recent diagnostics, workspaces, relevant processes, and disk pressure:

```bash
make eval-remote-runner-status
```

Find Phase 3 result files still on remote runner workspaces:

```bash
make eval-remote-find-results EVAL_REMOTE_FIND_LIMIT=120
```

Rescue remote `results/phase3` and `artifacts/phase3` directories into a local ignored destination:

```bash
make eval-remote-rescue-results EVAL_REMOTE_RESCUE_DEST=tmp/eval-remote-rescue
```

### Cache Cleanup Workflow

Use cache cleanup after a runner produces empty artifacts or Harbor/Terminal-Bench cache errors and before retrying the affected arm. The cleanup target is dry-run by default:

```bash
make eval-harbor-cache-clean
```

Review the printed cache and Docker usage, then explicitly confirm cleanup:

```bash
make eval-harbor-cache-clean EVAL_REMOTE_CLEAN_CONFIRM=1
```

After cleanup:

1. Retry only the affected arm/run.
2. Download the retry artifact.
3. Run `eval-discover-wave` again with the retry run id.
4. Use `SKIP_MISSING_RUN_DIRS=1` only if the failed original is still present in the wave input.
5. Ingest the valid retry run and leave the empty/cache-failed run out of scored summaries.

### Recovery Examples

- Qwen GitHub Actions run `28323749421` is the empty-artifact/cache-failure example. Treat it as a failed artifact source, clean caches, and do not ingest it as a scored run.
- Qwen GitHub Actions run `28346284705` is the successful retry example. Use its artifact as the valid `router-qwen-3.7-plus` source after discovery and manifest validation pass.
- Opus GitHub Actions run `28323747982` produced `router-anthropic-opus/2026-06-28__13-28-56`, but the provider hit the Anthropic workspace API usage limit until `2026-07-01 00:00 UTC`. Exclude it from valid-only summaries rather than treating its failures as model quality.

## Quality Audit

Summarize suite quality by arm:

```bash
make eval-suite-summary SUITE_ID=phase3-full-20 ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

Summarize individual arm runs:

```bash
make eval-arm-run-summary SUITE_ID=phase3-full-20 ARMS="router-gemini-flash router-gpt-5.5 router-anthropic-sonnet"
```

### Valid-Only Summaries

Keep invalid-run exclusions in an ignored local TSV. The default Make path is:

```text
configs/eval_invalid_runs.local.tsv
```

The alternate ignored scratch path is:

```text
tmp/eval-invalid-runs.tsv
```

TSV format:

```text
suite_id	arm_id	run_label	provider_run_id	reason
```

Current known invalid run:

```text
suite_id	arm_id	run_label	provider_run_id	reason
phase3-full-20	router-anthropic-opus	router-anthropic-opus/2026-06-28__13-28-56		Anthropic workspace API usage limit until 2026-07-01 00:00 UTC
```

Generate a valid-only arm summary:

```bash
make eval-suite-summary-valid SUITE_ID=phase3-full-20
```

Generate valid-only per-run rows:

```bash
make eval-arm-run-summary-valid SUITE_ID=phase3-full-20
```

Use a different local exclusion file when needed:

```bash
make eval-suite-summary-valid \
  SUITE_ID=phase3-full-20 \
  INVALID_RUNS_FILE=tmp/eval-invalid-runs.tsv
```

When invalid-run exclusions are active, `scripts/eval_quality_audit.py` uses base-table joins instead of pre-aggregated summary views so a single bad arm run can be subtracted correctly.

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
