# Phase 3 Artifact Qualitative Review 20260706

## Purpose

Prepare a reproducible evidence inventory for the Phase 3 qualitative investigation pass. This scaffold is focused on Sonnet exceptions and suspect no-op zero-token trials first, while preserving dashboard links into the artifact browser and trial evidence pages.

Do not run Haiku or Fable from this scaffold. Those runs remain gated on drilldown readiness and ingestion automation.

## Source Files Generated

- `results/phase3/reporting/phase3_trial_evidence_audit_20260706.tsv`
- `results/phase3/reporting/phase3_exception_audit_20260706.tsv`
- `results/phase3/reporting/phase3_suspect_noop_audit_20260706.tsv`
- `results/phase3/reporting/phase3_arm_task_qualitative_matrix_20260706.tsv`
- `results/phase3/reporting/phase3_arm_qualitative_summary_20260706.tsv`
- `results/phase3/reporting/phase3_task_qualitative_summary_20260706.tsv`
- `results/phase3/reporting/phase3_exception_review_targets_20260706.tsv`
- `docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_20260706.md`

## Review Method

- Suite: `phase3-full-20`.
- Focus arms: `router-anthropic-sonnet`.
- Invalid/quarantined runs: excluded from generated trial rows.
- Generation command:

```bash
uv run --with 'psycopg[binary]' python scripts/generate_phase3_qualitative_audit.py --suite-id phase3-full-20 --focus-arm router-anthropic-sonnet
```

- Start with exception and suspect no-op rows, then compare against normal failures and representative successes only when needed.
- Use `/artifacts/<artifact_id>` for R2-backed content preview and `/trials/<trial_id>` for trial evidence context.
- Record whether each anomaly appears to be model behavior, provider behavior, harness behavior, or ingestion/reporting behavior.

## Initial Aggregate Observations

- Selected trial rows: 60.
- Evidence-audit rows emitted: 32.
- Successes in selected rows: 28.
- Exceptions in selected rows: 23.
- Suspect no-op rows in selected rows: 0.
- Normal failures in selected rows: 9.
- Missing-cost rows in selected rows: 22.
- Artifact references indexed: 503 artifacts across 60 selected trials.

## Sonnet Exception Review

### `router-anthropic-sonnet/2026-06-27__01-30-11`

Planned first focus counts:

- Trials: 60.
- Successes: 28.
- Exception failures: 23.
- Normal failures: 9.
- Missing-cost trials: 22.

Generated row check for this run in the current inventory:

- Rows: 60.
- Successes: 28.
- Exceptions: 23.
- Normal failures: 9.
- Missing-cost rows: 22.

Use `phase3_exception_review_targets_20260706.tsv` for direct exception.txt artifact links.

Dashboard starting links:

- [Sonnet exception artifacts](/artifacts?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11&quality_flag=exception).
- [Sonnet run detail](/runs/router-anthropic-sonnet%2F2026-06-27__01-30-11).
- [Sonnet trial quality](/trial-quality?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11).

Review notes:

- Pending: classify representative exception artifacts by root cause.
- Pending: compare exception summaries against R2 preview contents.
- Pending: check whether missing-cost rows line up with exception boundaries or ingestion gaps.

## Suspect No-op Review

- Start from `phase3_suspect_noop_audit_20260706.tsv`.
- For each row, open `trial_dashboard_path`, then `first_artifact_dashboard_path` when present.
- Confirm whether zero tokens/cost reflects provider non-start, harness no-op, ingestion omission, or legitimate empty accounting.

## Gemini Flash Review

- Pending after the Sonnet exception pass.
- Use the exception and suspect no-op inventories to select representative Gemini Flash rows.
- Keep invalid/quarantined evidence labeled if `--include-invalid` is used for a follow-up pass.

## Invalid/Quarantined Run Review

- No invalid/quarantined runs matched this suite and focus-arm selection.

## Cross-arm Exception Patterns

- `exception_info`: 23

## Task-level Observations

- `terminal-bench-2.0:model-extraction-relu-logits`: trials=3, successes=0, exceptions=3, suspect_noops=0, normal_failures=0, priority=medium
- `terminal-bench-2.0:schemelike-metacircular-eval`: trials=3, successes=0, exceptions=3, suspect_noops=0, normal_failures=0, priority=medium
- `terminal-bench-2.0:polyglot-rust-c`: trials=3, successes=0, exceptions=2, suspect_noops=0, normal_failures=1, priority=medium
- `terminal-bench-2.0:cancel-async-tasks`: trials=3, successes=0, exceptions=1, suspect_noops=0, normal_failures=2, priority=medium
- `terminal-bench-2.0:mteb-retrieve`: trials=3, successes=0, exceptions=0, suspect_noops=0, normal_failures=3, priority=medium
- `terminal-bench-2.0:custom-memory-heap-crash`: trials=3, successes=1, exceptions=2, suspect_noops=0, normal_failures=0, priority=medium
- `terminal-bench-2.0:torch-pipeline-parallelism`: trials=3, successes=1, exceptions=2, suspect_noops=0, normal_failures=0, priority=medium
- `terminal-bench-2.0:configure-git-webserver`: trials=3, successes=1, exceptions=1, suspect_noops=0, normal_failures=1, priority=medium
- `terminal-bench-2.0:query-optimize`: trials=3, successes=1, exceptions=1, suspect_noops=0, normal_failures=1, priority=medium
- `terminal-bench-2.0:build-cython-ext`: trials=3, successes=2, exceptions=1, suspect_noops=0, normal_failures=0, priority=medium

## Open Questions and Recommended Actions

- Confirm whether task text is available for each reviewed trial; if not, keep task text ingestion on the qualitative-review readiness checklist.
- Decide whether any invalid/quarantined labels or reasons need refinement before final Phase 3 reporting.
- Capture representative artifact links for each root-cause category before resuming paid full runs.
- Do not run Haiku or Fable until drilldown review and ingestion automation are ready.
