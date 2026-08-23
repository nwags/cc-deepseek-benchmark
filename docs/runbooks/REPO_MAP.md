# Repository Map

This repository is organized around benchmark phases, retained evidence,
reviewed interpretation layers, operational publication, and the dashboard.

## Start here

For successor-team work:

```text
docs/guides/README.md
docs/guides/DASHBOARD_RESEARCH_GUIDE.md
docs/guides/CODEBASE_GUIDE.md
docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md
```

Use the Dashboard Research Guide first, then trace important findings into the
codebase.

## Root files

| Path | Purpose |
|---|---|
| `README.md` | Project front door and completed-phase overview. |
| `AGENTS.md` | Operating rules for contributors and coding agents. |
| `Makefile` | Repository checks and operational helpers. |
| `.env.example` | Non-secret local environment template. |
| `.gitignore` | Protects secrets and local/generated state. |
| `pyproject.toml`, `uv.lock` | Python/uv environment metadata. |

## Configs

```text
configs/
  arms/       model/provider/route configs
  phases/     benchmark phase configs
  tasks/      benchmark task lists
  router/     router configuration
  dashboard/  dashboard research/taxonomy contracts
```

The selected 20-task Terminal-Bench set is:

```text
configs/tasks/terminal-bench-20.txt
```

## Scripts

```text
scripts/
  lib/                          shared Python helpers
  run_arm.sh                    config-driven benchmark entry point
  run_arm_live.py               optional live-supervision wrapper
  publish_phase3_run.py         final Phase 3 canonical publisher
  ingest_phase3_run_metadata.py manifest/metadata ingestion support
  check.sh                      repository checks
  secret_scan.sh                secret scanner
```

Phase-3-named publication scripts remain part of the retained implementation.
Future phases should generalize them only where a real experiment requires it.

## Docs

```text
docs/
  guides/      current successor research/code/handoff guidance
  plans/       historical and future phase plans
  reference/   glossary and methodological references
  reports/     phase-specific reports and analysis
  reviews/     manual/acceptance review records
  runbooks/    operational procedures and historical operating records
```

Older Phase 3 plans and operating sections may describe Phase 3 as active.
Where explicitly marked historical/superseded, preserve those bodies as
provenance rather than rewriting them.

## Results

```text
results/
  phase1/                frozen Phase 1 evidence
  phase2/                frozen Phase 2 evidence
  phase3/                closed Phase 3 evidence and reporting
  manual_verification/   frozen reviewed evidence/taxonomy snapshots
  phase4/                future Phase 4 outputs when activated
  phase5/                future Phase 5 outputs when activated
```

Do not treat canary, smoke, diagnostic, or all-imported inventory as a scored
full-suite population unless the relevant reviewed methodology says so.

## Phase source-of-truth starting points

Phase 1:

```text
results/phase1/combined.csv
```

Phase 2:

```text
results/phase2/combined.csv
```

Phase 3 closeout/current review:

```text
docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md
results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json
results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json
results/phase3/reporting/phase3_reviewed_run_selection_20260809.json
```

Reviewed behavioral evidence:

```text
results/manual_verification/comprehensive_review_20260731/
results/manual_verification/failure_taxonomy_20260813/
```

## Dashboard

```text
apps/dashboard/
  src/app/         pages/routes
  src/components/  presentation components
  src/lib/         data loaders and research/presentation models
  src/generated/   generated mirrors of checked-in reviewed data
```

The dashboard mixes deliberately distinct source classes:

- frozen reviewed snapshots;
- current reviewed interpretation;
- canonical operational database state;
- dynamic imported inventory;
- mutable live observation.

Do not merge these merely because they can be represented in one table.

## Database and artifact storage

```text
db/migrations/phase3/
```

Supabase Postgres stores benchmark metadata and live/canonical relationships.

Cloudflare R2 stores large artifact bytes.

Migration `009_live_run_supervision.sql` was applied historically. Do not rerun
it. Future schema changes require a new migration.

## Figures

```text
figures/
  phase1/
  phase2/
  phase3/
  phase4/
  phase5/
```

Phase 1/2/3 figures are retained historical outputs. Phase 4/5 paths are for
future work when those phases are activated.

## Artifact distinction

Typical result classes:

- full scored raw output;
- canary;
- smoke;
- ad-hoc/diagnostic;
- supplemental reporting;
- reviewed/manual-verification output;
- live/progressive observation;
- canonical published evidence.

These classes are not automatically interchangeable.
