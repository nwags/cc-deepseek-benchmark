# Phase 3 Completion and Operationalization Plan

## Purpose

This plan defines the remaining work needed to complete Phase 3 as an auditable, reproducible router-mediated benchmark phase. The goal is to finish the validity/provenance layer, add enough drilldown to investigate anomalous trials from the dashboard, automate ingestion from completed workflow runs through artifact storage and reporting, and only then run the remaining Haiku and Fable arms as end-to-end proof of the operational path.

Primary scored comparisons should remain valid-only. Trial Quality, Runs, Run Detail, and future Artifact/Trial drilldowns are audit and provenance views, so they may include invalid/quarantined runs with explicit labels and reasons.

Do not run Haiku or Fable before drilldown and ingestion automation are ready.

## Current State

- Phase 3 is the active branch and active benchmark phase.
- `db/migrations/phase3/007_valid_only_dashboard_views.sql` exists and has been applied.
- Valid-only dashboard views report 13 arms, 780 trials, and 451 successes for `phase3-full-20`.
- Invalid/quarantined runs are preserved in `benchmark.benchmark_invalid_arm_runs`.
- Invalid/quarantined runs are excluded from scored comparison views and retained for audit.
- Dashboard comparison surfaces now align with valid-only views for the primary comparison path.
- The immediate dashboard work in progress is the validity/provenance UI, invalid reason surfacing, and suspect no-op drilldown.

## Stage A: Dashboard Validity/Provenance

Finish and commit the dashboard layer that distinguishes valid scored comparisons from audit/provenance rows.

Required work:

- Keep primary overview and suite comparisons on valid-only views.
- Surface invalid/quarantined run labels, categories, and reasons in Trial Quality.
- Show validity badge and reason context on Runs and Run Detail.
- Keep invalid/quarantined runs available for audit, not silently hidden from provenance views.
- Make overview copy explicit that the leaderboard and suite comparison are valid-only.

Acceptance criteria:

- `phase3-full-20` leaderboard and suite pages use valid-only comparison views.
- Dashboard overview shows a compact data provenance and validity panel.
- Trial Quality includes an invalid/quarantined runs table with reason text.
- Runs and Run Detail show valid, invalid, or quarantined status clearly.
- No scoring semantics are changed by the UI layer.

## Stage B: Artifact and Trial Drilldown

Status: actively underway after the validity/provenance layer and suspect no-op drilldown.

Artifact content preview is the gate before qualitative artifact review. Current `local_path` values may point at stale or missing extraction directories, so Cloudflare R2 is the durable artifact source for dashboard inspection. Local previews are useful only as a safe fallback or after explicit rehydration.

Build enough drilldown to move from aggregate anomaly flags to specific trial evidence without leaving the dashboard context.

Desired drilldown path:

```text
overview / suite / run / trial-quality
  -> filtered trial list
  -> trial detail
  -> artifacts, logs, R2 URI, local path, workflow/provider metadata
```

Initial scope:

- Add Trial Quality filters for suspect no-op rows by `quality`, `suite_id`, `arm_id`, `run_label`, and `task_id`.
- Link nonzero suspect no-op badges from overview, runs, and run detail to the filtered Trial Quality table.
- Add a stable `suspect-noop-trials` anchor for deep links.
- Replace the Artifacts placeholder with a filterable audit/provenance browser over imported artifact metadata.
- Add a server-side, bounded artifact content preview backed by R2 credentials when configured.
- Keep Artifacts inclusive of invalid/quarantined runs because it is not a scored comparison view.
- Do not expose signed download links until a safe server-side route exists.

Acceptance criteria:

- A user can click from a nonzero suspect no-op badge to the relevant filtered trial list.
- Active filters are visible and can be cleared.
- Filtered trial rows include run label, suite, arm, task, attempt, token/cost signature, and exception fields.
- The artifact browser can filter by run label, suite, arm, task, quality flag, exception type, artifact kind, and text search.
- Artifact rows show run/suite/arm/task context, quality/exception state, invalid/quarantined status, size, R2/local storage state, and links back to Run Detail, Trial Quality, and task detail where applicable.
- Run-root artifacts remain visible even when no `trial_id` is attached.
- Artifact detail pages can preview text-like R2 artifacts without exposing public signed URLs or browser-side credentials.
- Trial evidence pages show quality, exception, token/cost/runtime, validity, task text when available, and related artifacts.
- If dashboard R2 credentials or task text are unavailable, the UI shows explicit readiness messages rather than inventing content.
- No trial scoring or qualified pass-rate calculation changes in this stage.

## Stage C: Qualitative Artifact Review

Use the drilldown to perform targeted qualitative review of anomalous and high-risk evidence.

Required review tracks:

- Sonnet exception review.
- Suspect no-op zero-token review.
- Invalid/quarantined run reason review.
- Spot checks of artifacts and logs for representative pass, normal failure, exception, and suspect no-op trials.
- Confirm task text availability for reviewed trials; if task text is not locally available or ingested, record that as a qualitative-review readiness gap.

Acceptance criteria:

- Review notes identify whether each inspected anomaly is model behavior, provider behavior, harness behavior, or ingestion/reporting behavior.
- Sonnet exception findings are documented with trial/task references.
- Suspect no-op findings are documented with trial/task references and artifact/log pointers where available.
- Any required invalid labels or reason refinements are recorded before final reporting.

## Stage D: Full Ingestion Automation

Implement the operational path from completed workflow run to refreshed dashboard and reports.

Required automation:

- Detect or select completed GitHub Actions workflow runs.
- Upload required artifacts to Cloudflare R2 using stable object keys.
- Ingest run, arm-run, trial, artifact, audit, and cost metadata into Supabase.
- Refresh dashboard-ready views and report inputs.
- Produce or update Phase 3 report artifacts from the ingested source of truth.
- Record observed model/provider metadata from raw logs.

Acceptance criteria:

- One command or documented workflow can process a completed run from workflow output into R2, Supabase, dashboard, and refreshed report inputs.
- The ingestion path is idempotent for already-seen runs.
- Missing artifacts, missing costs, and missing observed model metadata are reported explicitly.
- Automation writes only Phase 3 outputs unless explicitly instructed otherwise.
- `make check`, `make secret-scan`, dashboard checks, and tests pass before paid full runs resume.

## Stage E: Haiku and Fable Automated Runs

Run Haiku and Fable only after Stages A-D are complete.

Purpose:

- Use Haiku and Fable as proof that run, upload, ingest, dashboard refresh, and report refresh work automatically end to end.
- Treat these as operational validation runs as well as benchmark arms.

Acceptance criteria:

- Pre-run checks, canary/smoke validation, observed routing, output directory, budget, and concurrency are confirmed before full execution.
- Haiku and Fable runs are launched through the documented operational path.
- Artifacts land in R2 and metadata lands in Supabase without manual backfill.
- Dashboard and report inputs refresh from the ingested records.
- Any provider/harness exceptions are visible through the drilldown and documented in the Phase 3 report.

## Stage F: Merge `phase3` Into `main`

After Phase 3 is stable and complete, merge `phase3` into `main` and make it the baseline for future phases.

Acceptance criteria:

- Phase 3 source-of-truth data, reports, figures, configs, scripts, and docs are complete.
- Frozen Phase 1 and Phase 2 results remain untouched.
- Phase 3 scored comparisons are valid-only and reproducible.
- Audit/provenance views preserve invalid/quarantined evidence with labels and reasons.
- The operational ingestion path is documented and demonstrated by Haiku and Fable.
- `main` can serve as the baseline for future Phase 4+ work.
