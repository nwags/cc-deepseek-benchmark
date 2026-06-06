# Phase 3 Remote Runner Database and Artifacts

This document defines the initial database and artifact-storage design for remote Phase 3 benchmark execution.

The selected starting stack is:

- Metadata database: Supabase Postgres
- Artifact storage: Cloudflare R2
- Compute: OVHcloud x86 VPS with self-hosted GitHub runner
- Source of truth for code/config/docs: GitHub repository

The initial goal is to keep Supabase and Cloudflare R2 within their free tiers while enabling a future dashboard.

## Design principle

Do not store large benchmark artifacts directly in the database.

Store structured metadata in Postgres. Store bulky files in Cloudflare R2. Store canonical scripts, configs, docs, and selected compact summaries in Git.

## What goes in Postgres

Postgres should store structured metadata and searchable summaries:

- Runs
- Trials
- Arms
- Models
- Task sets
- Trial outcomes
- Runtime and token counts
- Cost summaries
- Error classifications
- Contamination audit summaries
- Artifact URIs and hashes
- Git commit and config fingerprints
- Runner metadata
- Pricing assumptions
- Dashboard-ready aggregate views

## What goes in Cloudflare R2

R2 should store larger artifacts:

- `result.json`
- `trajectory.json`
- `claude-code.txt`
- `trial.log`
- `job.log`
- verifier outputs
- generated figures
- exported decks and PDF review copies
- full run bundles
- snapshots that are too large or too bulky for Git

## What stays in Git

Git should continue to store:

- Source scripts
- Arm configs
- Router configs
- Documentation
- Small generated CSV/JSON summaries
- Slide/deck source docs
- Selected figures that are useful for review
- Reproducibility scripts

Do not let Git become the primary store for every trajectory and log from every smoke/full-sweep run.

## Why Postgres

Postgres is a good default because benchmark data is partly relational and partly semi-structured.

Relational examples:

- one run has many trials
- one trial belongs to one arm and one task
- one arm has one provider family and backend model
- one artifact belongs to a run or trial

Semi-structured examples:

- raw arm config snapshots
- provider-specific response metadata
- pricing assumptions
- environment policy
- tool policy
- Harbor/LiteLLM config fragments

Postgres supports both normalized tables and JSON/JSONB columns. It also works well with many future dashboard options, including Supabase dashboards, Metabase, Grafana, Retool, Evidence.dev, Streamlit, and custom web apps.

## Why Supabase first

Supabase is attractive for the pilot because it is Postgres-based and dashboard-friendly. It can start on the free tier, then move to a paid tier if the database becomes important enough to need more storage, uptime, or collaboration features.

Starting constraints:

- Keep metadata compact.
- Store only artifact pointers and summaries in Postgres.
- Avoid storing full trajectories/logs in database rows.
- Add retention or archival policy before full sweeps.

Reference:
- Supabase pricing: https://supabase.com/pricing
- Supabase billing/quotas: https://supabase.com/docs/guides/platform/billing-on-supabase

## Why Cloudflare R2 first

Cloudflare R2 is attractive for artifacts because it is S3-compatible, has a useful free tier, and does not charge internet egress for standard storage. It keeps artifacts independent from the VPS provider and avoids tying this design to AWS.

Starting constraints:

- Keep bucket private by default.
- Use one bucket for Phase 3 benchmark artifacts.
- Store object paths in Postgres.
- Store SHA256 hashes for reproducibility.
- Upload only useful artifacts during the pilot.
- Avoid uploading duplicate bulky artifacts until retention rules are defined.

Reference:
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/

## Initial object path convention

Recommended R2 object key format:

phase3/{mode}/{arm_id}/{run_timestamp}/{task_name}/{trial_id}/{artifact_name}

Examples:

- phase3/canary/router-glm-5.1/2026-06-04__12-40-42/modernize-scientific-stack/jVyumUA/result.json
- phase3/smoke/router-deepseek-pro/2026-06-10__15-00-00/build-cython-ext/attempt-1/trajectory.json
- phase3/reports/2026-06-10/PHASE3_SPONSOR_DECK.pdf

## Minimal schema, first cut

### benchmark_runs

- id
- phase
- mode
- run_label
- git_commit
- branch
- runner_name
- runner_provider
- runner_region
- started_at
- finished_at
- status
- notes

### benchmark_arms

- arm_id
- display_name
- provider_family
- backend_model
- router_model
- agent_harness
- config_path
- config_sha256
- active
- notes

### benchmark_tasks

- task_id
- benchmark
- benchmark_version
- task_name
- task_source_uri
- contamination_notes
- active

### benchmark_trials

- id
- run_id
- arm_id
- task_id
- attempt_index
- reward
- exception_type
- exception_summary
- runtime_seconds
- input_tokens
- cache_tokens
- output_tokens
- cost_usd
- started_at
- finished_at
- result_local_path
- result_artifact_uri
- notes

### benchmark_artifacts

- id
- run_id
- trial_id
- artifact_type
- local_path
- r2_uri
- github_uri
- sha256
- size_bytes
- created_at
- retention_class
- notes

### benchmark_models

- id
- provider_family
- model_slug
- endpoint_base
- endpoint_region
- context_window
- pricing_input_per_million
- pricing_output_per_million
- pricing_source_uri
- active
- notes

### contamination_audits

- id
- run_id
- trial_id
- audit_status
- websearch_events
- webfetch_events
- forbidden_tools_available
- disallowed_tools
- audit_local_path
- audit_artifact_uri
- notes

### cost_forecasts

- id
- forecast_name
- source_run_id
- method
- arms_included
- task_count
- attempts_per_task
- estimated_cost_usd
- reserve_multiplier
- reserve_cost_usd
- created_at
- notes

## Dashboard readiness

The schema should support questions like:

- Which arms are active and canary-green?
- Which providers are most expensive per task?
- Which providers are slowest?
- Which tasks generate the most tokens?
- Which arms fail due to auth/config/schema/rate limits?
- Which arms fail benchmark tests after successful execution?
- How much would the next smoke/full sweep cost?
- Which artifacts support each claim?
- Which run was produced by which git commit and config hash?

## Supabase free-tier strategy

To stay inside the free tier during the pilot:

- Store only structured metadata and summaries.
- Store large artifacts in R2, not Postgres.
- Keep full logs out of database rows.
- Prefer compact JSON summaries over raw text blobs.
- Use a small number of indexes at first.
- Keep only current pilot tables and views.
- Export old DB snapshots if storage approaches the limit.
- Avoid using Supabase Storage for bulky benchmark artifacts while R2 is available.

## R2 free-tier strategy

To stay inside the R2 free tier during the pilot:

- Keep total artifact storage under 10 GB-month.
- Upload only selected artifacts from canary and smoke.
- Compress run bundles before upload if needed.
- Avoid duplicate uploads from reruns unless they are intentionally retained.
- Track object size in Postgres.
- Delete failed experimental uploads after validation.
- Use Standard storage for free-tier eligibility.

## Ingestion strategy

Initial ingestion should be file-first and append-safe:

1. Harbor writes local result directories.
2. Existing extraction scripts produce CSV/JSON summaries.
3. New ingestion script reads summaries and result files.
4. Ingestion computes SHA256 hashes.
5. Ingestion uploads selected artifacts to R2.
6. Ingestion inserts metadata rows into Supabase Postgres.
7. Ingestion prints a compact run summary.
8. Ingestion can be rerun without duplicating rows.

Recommended script path:

- `scripts/ingest_phase3_run_metadata.py`

Recommended environment variables:

- `SUPABASE_DB_URL`
- `SUPABASE_SERVICE_ROLE_KEY` or a narrower database credential
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_ENDPOINT_URL`

All of these must stay in ignored secret files or GitHub Actions secrets.

## Open design questions

- Should the first dashboard read directly from Supabase, or should it read from exported CSV/JSON?
- Should R2 artifacts be private-only, signed URL only, or selectively public?
- Should each run upload a compressed bundle in addition to individual artifacts?
- Should canary artifacts be retained indefinitely but smoke/full-sweep artifacts follow retention rules?
- Should the database store model pricing snapshots or only link to pricing assumptions?
- Should benchmark task metadata include contamination-risk labels?

## Recommended next implementation steps

1. Create Supabase project for benchmark metadata.
2. Create Cloudflare R2 bucket for benchmark artifacts.
3. Add ignored env examples for Supabase and R2.
4. Add SQL migration file for the minimal schema.
5. Add ingestion script that can run locally first.
6. Test ingestion on one existing canary result directory.
7. Confirm DB rows and R2 uploads.
8. Add GitHub Actions remote-runner workflow.
9. Run one remote canary on OVHcloud VPS.
10. Run funded 5-task smoke after remote canary passes.
