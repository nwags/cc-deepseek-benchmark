# Phase 3 Full-Sweep First Three Arms Ingest Checkpoint

Date: 2026-06-20

## Status

The first three completed Phase 3 full-sweep arm runs have been downloaded from GitHub Actions artifacts, uploaded to Cloudflare R2, and inserted into Supabase.

## Ingested arm runs

| Arm | GitHub run ID | Run timestamp | Trials | R2 artifacts | Cost | Current DB mode |
|---|---:|---|---:|---:|---:|---|
| router-deepseek-pro | 27829497887 | 2026-06-19__13-47-59 | 60 | 491 | $50.203188 | raw |
| router-gpt-5.4 | 27829499173 | 2026-06-19__13-47-51 | 60 | 489 | $173.094830 | raw |
| router-glm-5.2 | 27829500567 | 2026-06-19__13-47-51 | 60 | 503 | $20.549075 | raw |

## Important data-model caveat

These were logical full-sweep runs, but the current ingestion script records `mode` from the physical results path. Phase 3 stores full-sweep Harbor output under `results/phase3/raw`, so these rows currently appear as `mode = raw`.

This should not be manually patched as a one-off. It should be fixed as part of the Phase 3 data-model interruption by separating:

- logical run mode: canary, smoke, full, ad-hoc;
- storage/results subdir: canary, smoke, raw, ad-hoc;
- eval suite: phase3-smoke-5, phase3-full-20, future expanded suites;
- arm run: one arm execution within a larger sweep or run batch.

## Decision

Pause further Phase 3 full-sweep dispatches after this checkpoint and implement the data-model/dashboard changes identified in `docs/reports/phase3/supabase/PHASE3_SUPABASE_DATA_MODEL_REVIEW.md`.

## Next implementation unit

1. Add `benchmark_eval_suites`, `benchmark_eval_suite_items`, `benchmark_arm_runs`, and `benchmark_trials.arm_run_id`.
2. Add checked-in eval suite definitions.
3. Update ingestion to resolve logical mode and suite ID instead of using only the results subdir.
4. Backfill existing canary, smoke, and the first three full-sweep arms into arm-run and suite records.
5. Redesign dashboard navigation around arms, arm runs, evals, eval suites, and artifact drilldown.
