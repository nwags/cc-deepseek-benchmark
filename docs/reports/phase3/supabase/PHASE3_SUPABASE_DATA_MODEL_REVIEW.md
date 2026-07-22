# Phase 3 Supabase Data Model Review

Date: 2026-06-19
Schema: `benchmark`
Branch context: Phase 3 dashboard / remote-runner architecture

## Executive summary

The current Supabase `benchmark` schema is a solid pilot model for ingesting Phase 3 benchmark results into the dashboard. It already has first-class tables for arms, models, runs, tasks, trials, artifacts, contamination audits, and cost forecasts, plus dashboard summary views for arms, runs, and tasks.

However, the sponsor’s requested navigation model needs two additional first-class concepts before the dashboard becomes a true evaluation console rather than a run-file browser:

1. **Eval suites / task suites** — named, versioned groupings of evals/tasks such as smoke-5, full-sweep-20, expanded-25, and future contamination-hardened suites.
2. **Arm runs** — one row per arm execution within a run/sweep, so the dashboard can navigate cleanly from an arm to that arm’s run, then to per-eval attempts and artifacts.

Without those two layers, the dashboard can still show runs and trials, but cross-linking from `arm -> arm run -> evals`, and from `eval suite -> eval -> compare all arms`, will require fragile inference from paths and run labels.

## Sponsor navigation requirement

The sponsor wants the dashboard to support the following paths:

- **Arms -> arm detail -> arm runs.**
- **Arm run -> eval/task attempts.**
- **Evals/tasks -> eval/task detail.**
- **Eval/task detail -> compare all arms on that eval.**
- **Eval suite -> grouped evals/tasks.**
- **Eval suite -> compare arms across that suite.**
- **Full-sweep run -> all arms, all evals, all attempts.**
- **Trial/artifact drilldown -> result JSON, trajectory, logs, verifier output, R2 object, GitHub artifact.**

## Exported schema sources

- Benchmark schema SQL: `docs/reports/phase3/supabase/phase3_benchmark_schema_20260619T154440Z.sql`
- Tables catalog: `results/phase3/supabase/phase3_benchmark_tables_20260619T154449Z.csv`
- Columns catalog: `results/phase3/supabase/phase3_benchmark_columns_20260619T154449Z.csv`
- Constraints catalog: `results/phase3/supabase/phase3_benchmark_constraints_20260619T154449Z.csv`
- Indexes catalog: `results/phase3/supabase/phase3_benchmark_indexes_20260619T154449Z.csv`
- Views catalog: `results/phase3/supabase/phase3_benchmark_views_20260619T154449Z.csv`
- Policies catalog: `results/phase3/supabase/phase3_benchmark_policies_20260619T154449Z.csv`

## Current schema inventory

- Base tables: `8`
- Views: `6`
- Primary-key entries: `8`
- Foreign-key entries: `8`
- Unique-constraint entries: `4`

### Current base tables

- `benchmark.benchmark_arms`
- `benchmark.benchmark_artifacts`
- `benchmark.benchmark_models`
- `benchmark.benchmark_runs`
- `benchmark.benchmark_tasks`
- `benchmark.benchmark_trials`
- `benchmark.contamination_audits`
- `benchmark.cost_forecasts`

### Current dashboard/read views

- `benchmark.v_dashboard_arms`
- `benchmark.v_dashboard_runs`
- `benchmark.v_dashboard_tasks`
- `benchmark.v_run_artifact_summary`
- `benchmark.v_run_audit_summary`
- `benchmark.v_run_trial_summary`

## Current entity coverage

- **Arms:** `benchmark_arms`, `v_dashboard_arms`
- **Backend models:** `benchmark_models`
- **Runs:** `benchmark_runs`, `v_dashboard_runs`, `v_run_artifact_summary`, `v_run_audit_summary`, `v_run_trial_summary`
- **Arm runs:** **MISSING / not obvious**
- **Evals/tasks:** `benchmark_tasks`, `v_dashboard_tasks`
- **Eval suites / task suites:** **MISSING / not obvious**
- **Suite membership:** **MISSING / not obvious**
- **Trials/attempts:** `benchmark_trials`, `v_run_trial_summary`
- **Artifacts/R2:** `benchmark_artifacts`, `v_run_artifact_summary`
- **Contamination/tool audits:** `contamination_audits`, `v_run_audit_summary`
- **Cost/usage:** `cost_forecasts`

## Current table details

### `benchmark.benchmark_arms` — BASE TABLE

- `arm_id`: text / `text` / not null
- `display_name`: text / `text` / nullable
- `provider_family`: text / `text` / nullable
- `backend_model`: text / `text` / nullable
- `router_model`: text / `text` / nullable
- `agent_harness`: text / `text` / nullable
- `config_path`: text / `text` / nullable
- `config_sha256`: text / `text` / nullable
- `active`: boolean / `bool` / not null; default `true`
- `notes`: text / `text` / nullable
- `raw_config`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`
- `updated_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17571_11_not_null`: CHECK
- `17559_17571_12_not_null`: CHECK
- `17559_17571_13_not_null`: CHECK
- `17559_17571_1_not_null`: CHECK
- `17559_17571_9_not_null`: CHECK
- `benchmark_arms_pkey`: PRIMARY KEY `arm_id`

Indexes:
- `benchmark_arms_pkey`

### `benchmark.benchmark_artifacts` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `run_id`: uuid / `uuid` / nullable
- `trial_id`: uuid / `uuid` / nullable
- `artifact_type`: text / `text` / not null
- `local_path`: text / `text` / nullable
- `r2_uri`: text / `text` / nullable
- `github_uri`: text / `text` / nullable
- `sha256`: text / `text` / nullable
- `size_bytes`: bigint / `int8` / nullable
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`
- `retention_class`: text / `text` / not null; default `'pilot'::text`
- `notes`: text / `text` / nullable

Constraints:
- `17559_17618_10_not_null`: CHECK
- `17559_17618_11_not_null`: CHECK
- `17559_17618_1_not_null`: CHECK
- `17559_17618_4_not_null`: CHECK
- `benchmark_artifacts_pkey`: PRIMARY KEY `id`
- `benchmark_artifacts_run_id_fkey`: FOREIGN KEY `run_id` -> `benchmark.benchmark_runs.id`
- `benchmark_artifacts_trial_id_fkey`: FOREIGN KEY `trial_id` -> `benchmark.benchmark_trials.id`

Indexes:
- `benchmark_artifacts_pkey`
- `idx_benchmark_artifacts_run`

### `benchmark.benchmark_models` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `provider_family`: text / `text` / not null
- `model_slug`: text / `text` / not null
- `endpoint_base`: text / `text` / nullable
- `endpoint_region`: text / `text` / nullable
- `context_window`: integer / `int4` / nullable
- `pricing_input_per_million`: numeric / `numeric` / nullable
- `pricing_output_per_million`: numeric / `numeric` / nullable
- `pricing_source_uri`: text / `text` / nullable
- `active`: boolean / `bool` / not null; default `true`
- `notes`: text / `text` / nullable
- `raw_metadata`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17638_10_not_null`: CHECK
- `17559_17638_12_not_null`: CHECK
- `17559_17638_13_not_null`: CHECK
- `17559_17638_1_not_null`: CHECK
- `17559_17638_2_not_null`: CHECK
- `17559_17638_3_not_null`: CHECK
- `benchmark_models_pkey`: PRIMARY KEY `id`
- `benchmark_models_provider_family_model_slug_key`: UNIQUE `provider_family`
- `benchmark_models_provider_family_model_slug_key`: UNIQUE `provider_family`
- `benchmark_models_provider_family_model_slug_key`: UNIQUE `model_slug`
- `benchmark_models_provider_family_model_slug_key`: UNIQUE `model_slug`

Indexes:
- `benchmark_models_pkey`
- `benchmark_models_provider_family_model_slug_key`

### `benchmark.benchmark_runs` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `phase`: text / `text` / not null
- `mode`: text / `text` / not null
- `run_label`: text / `text` / nullable
- `git_commit`: text / `text` / nullable
- `branch`: text / `text` / nullable
- `runner_name`: text / `text` / nullable
- `runner_provider`: text / `text` / nullable
- `runner_region`: text / `text` / nullable
- `started_at`: timestamp with time zone / `timestamptz` / nullable
- `finished_at`: timestamp with time zone / `timestamptz` / nullable
- `status`: text / `text` / not null; default `'unknown'::text`
- `notes`: text / `text` / nullable
- `raw_metadata`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17560_12_not_null`: CHECK
- `17559_17560_14_not_null`: CHECK
- `17559_17560_15_not_null`: CHECK
- `17559_17560_1_not_null`: CHECK
- `17559_17560_2_not_null`: CHECK
- `17559_17560_3_not_null`: CHECK
- `benchmark_runs_pkey`: PRIMARY KEY `id`

Indexes:
- `benchmark_runs_pkey`
- `idx_benchmark_runs_phase_mode`
- `idx_benchmark_runs_phase_mode_run_label_unique`

### `benchmark.benchmark_tasks` — BASE TABLE

- `task_id`: text / `text` / not null
- `benchmark`: text / `text` / not null; default `'terminal-bench'::text`
- `benchmark_version`: text / `text` / nullable
- `task_name`: text / `text` / not null
- `task_source_uri`: text / `text` / nullable
- `contamination_notes`: text / `text` / nullable
- `active`: boolean / `bool` / not null; default `true`
- `raw_metadata`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17582_1_not_null`: CHECK
- `17559_17582_2_not_null`: CHECK
- `17559_17582_4_not_null`: CHECK
- `17559_17582_7_not_null`: CHECK
- `17559_17582_8_not_null`: CHECK
- `17559_17582_9_not_null`: CHECK
- `benchmark_tasks_pkey`: PRIMARY KEY `task_id`

Indexes:
- `benchmark_tasks_pkey`

### `benchmark.benchmark_trials` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `run_id`: uuid / `uuid` / nullable
- `arm_id`: text / `text` / nullable
- `task_id`: text / `text` / nullable
- `attempt_index`: integer / `int4` / nullable
- `reward`: numeric / `numeric` / nullable
- `exception_type`: text / `text` / nullable
- `exception_summary`: text / `text` / nullable
- `runtime_seconds`: numeric / `numeric` / nullable
- `input_tokens`: bigint / `int8` / nullable
- `cache_tokens`: bigint / `int8` / nullable
- `output_tokens`: bigint / `int8` / nullable
- `cost_usd`: numeric / `numeric` / nullable
- `started_at`: timestamp with time zone / `timestamptz` / nullable
- `finished_at`: timestamp with time zone / `timestamptz` / nullable
- `result_local_path`: text / `text` / nullable
- `result_artifact_uri`: text / `text` / nullable
- `notes`: text / `text` / nullable
- `raw_result`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17593_19_not_null`: CHECK
- `17559_17593_1_not_null`: CHECK
- `17559_17593_20_not_null`: CHECK
- `benchmark_trials_arm_id_fkey`: FOREIGN KEY `arm_id` -> `benchmark.benchmark_arms.arm_id`
- `benchmark_trials_pkey`: PRIMARY KEY `id`
- `benchmark_trials_run_id_fkey`: FOREIGN KEY `run_id` -> `benchmark.benchmark_runs.id`
- `benchmark_trials_task_id_fkey`: FOREIGN KEY `task_id` -> `benchmark.benchmark_tasks.task_id`

Indexes:
- `benchmark_trials_pkey`
- `idx_benchmark_trials_run_arm`
- `idx_benchmark_trials_task`

### `benchmark.contamination_audits` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `run_id`: uuid / `uuid` / nullable
- `trial_id`: uuid / `uuid` / nullable
- `audit_status`: text / `text` / not null
- `websearch_events`: integer / `int4` / not null; default `0`
- `webfetch_events`: integer / `int4` / not null; default `0`
- `forbidden_tools_available`: integer / `int4` / not null; default `0`
- `disallowed_tools`: text / `text` / nullable
- `audit_local_path`: text / `text` / nullable
- `audit_artifact_uri`: text / `text` / nullable
- `notes`: text / `text` / nullable
- `raw_audit`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17651_12_not_null`: CHECK
- `17559_17651_13_not_null`: CHECK
- `17559_17651_1_not_null`: CHECK
- `17559_17651_4_not_null`: CHECK
- `17559_17651_5_not_null`: CHECK
- `17559_17651_6_not_null`: CHECK
- `17559_17651_7_not_null`: CHECK
- `contamination_audits_pkey`: PRIMARY KEY `id`
- `contamination_audits_run_id_fkey`: FOREIGN KEY `run_id` -> `benchmark.benchmark_runs.id`
- `contamination_audits_trial_id_fkey`: FOREIGN KEY `trial_id` -> `benchmark.benchmark_trials.id`

Indexes:
- `contamination_audits_pkey`
- `idx_contamination_audits_run`

### `benchmark.cost_forecasts` — BASE TABLE

- `id`: uuid / `uuid` / not null; default `gen_random_uuid()`
- `forecast_name`: text / `text` / not null
- `source_run_id`: uuid / `uuid` / nullable
- `method`: text / `text` / not null
- `arms_included`: integer / `int4` / nullable
- `task_count`: integer / `int4` / nullable
- `attempts_per_task`: integer / `int4` / nullable
- `estimated_cost_usd`: numeric / `numeric` / nullable
- `reserve_multiplier`: numeric / `numeric` / nullable
- `reserve_cost_usd`: numeric / `numeric` / nullable
- `notes`: text / `text` / nullable
- `raw_forecast`: jsonb / `jsonb` / not null; default `'{}'::jsonb`
- `created_at`: timestamp with time zone / `timestamptz` / not null; default `now()`

Constraints:
- `17559_17674_12_not_null`: CHECK
- `17559_17674_13_not_null`: CHECK
- `17559_17674_1_not_null`: CHECK
- `17559_17674_2_not_null`: CHECK
- `17559_17674_4_not_null`: CHECK
- `cost_forecasts_pkey`: PRIMARY KEY `id`
- `cost_forecasts_source_run_id_fkey`: FOREIGN KEY `source_run_id` -> `benchmark.benchmark_runs.id`

Indexes:
- `cost_forecasts_pkey`

### `benchmark.v_dashboard_arms` — VIEW

- `arm_id`: text / `text` / nullable
- `display_name`: text / `text` / nullable
- `provider_family`: text / `text` / nullable
- `backend_model`: text / `text` / nullable
- `router_model`: text / `text` / nullable
- `agent_harness`: text / `text` / nullable
- `config_path`: text / `text` / nullable
- `active`: boolean / `bool` / nullable
- `run_count`: bigint / `int8` / nullable
- `trial_count`: bigint / `int8` / nullable
- `success_count`: bigint / `int8` / nullable
- `pass_rate`: numeric / `numeric` / nullable
- `trial_cost_usd`: numeric / `numeric` / nullable
- `cost_row_count`: bigint / `int8` / nullable
- `missing_cost_count`: bigint / `int8` / nullable
- `avg_runtime_seconds`: numeric / `numeric` / nullable
- `median_runtime_seconds`: double precision / `float8` / nullable

### `benchmark.v_dashboard_runs` — VIEW

- `run_id`: uuid / `uuid` / nullable
- `phase`: text / `text` / nullable
- `mode`: text / `text` / nullable
- `run_label`: text / `text` / nullable
- `git_commit`: text / `text` / nullable
- `branch`: text / `text` / nullable
- `runner_name`: text / `text` / nullable
- `runner_provider`: text / `text` / nullable
- `runner_region`: text / `text` / nullable
- `started_at`: timestamp with time zone / `timestamptz` / nullable
- `finished_at`: timestamp with time zone / `timestamptz` / nullable
- `status`: text / `text` / nullable
- `created_at`: timestamp with time zone / `timestamptz` / nullable
- `raw_metadata`: jsonb / `jsonb` / nullable
- `trial_count`: bigint / `int8` / nullable
- `success_count`: bigint / `int8` / nullable
- `failure_count`: bigint / `int8` / nullable
- `pass_rate`: numeric / `numeric` / nullable
- `avg_runtime_seconds`: numeric / `numeric` / nullable
- `median_runtime_seconds`: double precision / `float8` / nullable
- `trial_cost_usd`: numeric / `numeric` / nullable
- `cost_row_count`: bigint / `int8` / nullable
- `missing_cost_count`: bigint / `int8` / nullable
- `input_tokens`: numeric / `numeric` / nullable
- `cache_tokens`: numeric / `numeric` / nullable
- `output_tokens`: numeric / `numeric` / nullable
- `artifact_count`: bigint / `int8` / nullable
- `artifact_size_bytes`: numeric / `numeric` / nullable
- `r2_artifact_count`: bigint / `int8` / nullable
- `audit_count`: bigint / `int8` / nullable
- `audit_pass_count`: bigint / `int8` / nullable
- `audit_nonpass_count`: bigint / `int8` / nullable
- `websearch_events`: bigint / `int8` / nullable
- `webfetch_events`: bigint / `int8` / nullable
- `forbidden_tools_available`: bigint / `int8` / nullable

### `benchmark.v_dashboard_tasks` — VIEW

- `task_id`: text / `text` / nullable
- `benchmark`: text / `text` / nullable
- `benchmark_version`: text / `text` / nullable
- `task_name`: text / `text` / nullable
- `active`: boolean / `bool` / nullable
- `trial_count`: bigint / `int8` / nullable
- `success_count`: bigint / `int8` / nullable
- `pass_rate`: numeric / `numeric` / nullable
- `avg_runtime_seconds`: numeric / `numeric` / nullable
- `median_runtime_seconds`: double precision / `float8` / nullable
- `trial_cost_usd`: numeric / `numeric` / nullable
- `cost_row_count`: bigint / `int8` / nullable
- `missing_cost_count`: bigint / `int8` / nullable

### `benchmark.v_run_artifact_summary` — VIEW

- `run_id`: uuid / `uuid` / nullable
- `artifact_count`: bigint / `int8` / nullable
- `artifact_size_bytes`: numeric / `numeric` / nullable
- `r2_artifact_count`: bigint / `int8` / nullable

### `benchmark.v_run_audit_summary` — VIEW

- `run_id`: uuid / `uuid` / nullable
- `audit_count`: bigint / `int8` / nullable
- `audit_pass_count`: bigint / `int8` / nullable
- `audit_nonpass_count`: bigint / `int8` / nullable
- `websearch_events`: bigint / `int8` / nullable
- `webfetch_events`: bigint / `int8` / nullable
- `forbidden_tools_available`: bigint / `int8` / nullable

### `benchmark.v_run_trial_summary` — VIEW

- `run_id`: uuid / `uuid` / nullable
- `trial_count`: bigint / `int8` / nullable
- `success_count`: bigint / `int8` / nullable
- `failure_count`: bigint / `int8` / nullable
- `avg_runtime_seconds`: numeric / `numeric` / nullable
- `median_runtime_seconds`: double precision / `float8` / nullable
- `trial_cost_usd`: numeric / `numeric` / nullable
- `cost_row_count`: bigint / `int8` / nullable
- `missing_cost_count`: bigint / `int8` / nullable
- `input_tokens`: numeric / `numeric` / nullable
- `cache_tokens`: numeric / `numeric` / nullable
- `output_tokens`: numeric / `numeric` / nullable

## Relationship model currently present

- `benchmark.benchmark_artifacts.run_id` -> `benchmark.benchmark_runs.id`
- `benchmark.benchmark_artifacts.trial_id` -> `benchmark.benchmark_trials.id`
- `benchmark.benchmark_trials.arm_id` -> `benchmark.benchmark_arms.arm_id`
- `benchmark.benchmark_trials.run_id` -> `benchmark.benchmark_runs.id`
- `benchmark.benchmark_trials.task_id` -> `benchmark.benchmark_tasks.task_id`
- `benchmark.contamination_audits.run_id` -> `benchmark.benchmark_runs.id`
- `benchmark.contamination_audits.trial_id` -> `benchmark.benchmark_trials.id`
- `benchmark.cost_forecasts.source_run_id` -> `benchmark.benchmark_runs.id`

## Assessment against sponsor request

- **PASS: Arm list and arm detail.** `benchmark_arms` exists.
- **PASS: Run list and run detail.** `benchmark_runs` exists.
- **PASS: Eval/task list and task detail.** `benchmark_tasks` exists.
- **PASS: Trial-level attempts.** `benchmark_trials` exists.
- **PASS: Artifact drilldown.** `benchmark_artifacts` exists.
- **PASS: Contamination audit drilldown.** `contamination_audits` exists.
- **GAP: Eval/task suites.** No first-class suite table found.
- **GAP: Suite membership.** No many-to-many suite membership table found.
- **GAP: Arm-run page.** No first-class arm-run table found.
- **GAP: Eval-by-arm comparison view.** `v_eval_arm_comparison` not found.
- **GAP: Suite-by-arm comparison view.** `v_suite_arm_comparison` not found.

## Recommended schema additions

### 1. `benchmark.benchmark_eval_suites`

Purpose: model sponsor-facing suites such as smoke-5, full-sweep-20, expanded-25, ad-hoc diagnostics, and future contamination-hardened suites.

Recommended columns:

- `id uuid primary key default gen_random_uuid()`
- `suite_id text unique not null`
- `display_name text not null`
- `description text`
- `benchmark text not null default 'terminal-bench'`
- `benchmark_version text`
- `phase text not null`
- `suite_type text not null` — `canary`, `smoke`, `full`, `expanded`, `ad_hoc`
- `version text`
- `active boolean not null default true`
- `created_at timestamptz not null default now()`
- `notes text`
- `raw_metadata jsonb not null default '{}'::jsonb`

### 2. `benchmark.benchmark_eval_suite_items`

Purpose: many-to-many relationship between suites and evals/tasks.

Recommended columns:

- `id uuid primary key default gen_random_uuid()`
- `suite_id text not null references benchmark.benchmark_eval_suites(suite_id)`
- `task_id text not null references benchmark.benchmark_tasks(task_id)`
- `display_order integer`
- `required boolean not null default true`
- `rationale text`
- `created_at timestamptz not null default now()`
- unique constraint on `(suite_id, task_id)`

### 3. `benchmark.benchmark_arm_runs`

Purpose: sponsor-facing “arm run” page, separating a whole sweep/run batch from one arm’s execution within that batch.

Recommended columns:

- `id uuid primary key default gen_random_uuid()`
- `run_id uuid references benchmark.benchmark_runs(id)`
- `arm_id text references benchmark.benchmark_arms(arm_id)`
- `suite_id text references benchmark.benchmark_eval_suites(suite_id)`
- `mode text not null`
- `status text not null default 'unknown'`
- `started_at timestamptz`
- `finished_at timestamptz`
- `n_trials integer`
- `n_completed_trials integer`
- `n_errored_trials integer`
- `mean_reward numeric`
- `total_cost_usd numeric`
- `total_runtime_seconds numeric`
- `github_run_id text`
- `artifact_root_uri text`
- `notes text`
- `raw_metadata jsonb not null default '{}'::jsonb`
- unique constraint on `(run_id, arm_id)` where practical

### 4. Add nullable `arm_run_id` to `benchmark_trials`

Purpose: let every trial belong directly to an arm-run page.

Recommended change:

- `alter table benchmark.benchmark_trials add column arm_run_id uuid references benchmark.benchmark_arm_runs(id);`

Backfill rule:

- for existing trials, group by `(run_id, arm_id)` and create one `benchmark_arm_runs` row per group, then set `benchmark_trials.arm_run_id` accordingly.

## Recommended dashboard views

### `benchmark.v_arm_run_summary`

One row per arm run with trial count, pass rate, runtime, cost, status, suite, and artifact counts.

### `benchmark.v_eval_arm_comparison`

One row per task/eval × arm, supporting task detail pages and cross-arm eval comparison.

### `benchmark.v_suite_arm_comparison`

One row per eval suite × arm, supporting smoke/full-sweep scorecards and sponsor-level model comparisons.

### `benchmark.v_arm_run_trials`

One row per arm run × task/eval × attempt, supporting drilldown into artifacts and trajectories.

## Dashboard implementation impact

### Routes/pages to add or adjust

- `/arms` -> existing arm list.
- `/arms/[arm_id]` -> arm detail, linking to arm runs.
- `/arm-runs/[arm_run_id]` -> one arm execution, listing eval/task attempts.
- `/evals` -> canonical eval/task list.
- `/evals/[task_id]` -> eval detail with all arms compared.
- `/eval-suites` -> suite list.
- `/eval-suites/[suite_id]` -> suite detail and arm comparison.
- `/runs/[run_id]` -> full run/sweep detail.
- `/artifacts/[artifact_id]` or linked artifact panel -> R2/GitHub/local artifact drilldown.

### Ingestion changes

- Continue ingesting `benchmark_runs`, `benchmark_trials`, `benchmark_artifacts`, and `contamination_audits`.
- Add suite resolution: infer or pass `suite_id` from workflow mode/task list.
- Create/upsert `benchmark_arm_runs` for each `(run_id, arm_id)` group.
- Set `benchmark_trials.arm_run_id` during ingestion.
- Upsert `benchmark_eval_suites` and `benchmark_eval_suite_items` from checked-in suite definitions, not from artifact paths alone.

### Repo/config changes

- Add a checked-in suite definition file, e.g. `configs/eval_suites/phase3-full-20.yaml`.
- Add `configs/eval_suites/phase3-smoke-5.yaml` if smoke remains a named suite.
- Add a migration SQL file for the new tables/views.
- Update ingestion tests to verify suite and arm-run backfill.
- Update dashboard queries to use views rather than local path parsing.

## Migration sequencing recommendation

1. Add schema migration for `benchmark_eval_suites`, `benchmark_eval_suite_items`, `benchmark_arm_runs`, and `benchmark_trials.arm_run_id`.
2. Add views: `v_arm_run_summary`, `v_eval_arm_comparison`, `v_suite_arm_comparison`, `v_arm_run_trials`.
3. Add eval suite YAML configs in the repo.
4. Backfill existing canary/smoke/full artifacts into the new model.
5. Update dashboard navigation to use arm-run and suite views.
6. Update GitHub Actions ingestion to populate arm runs and suite metadata automatically after completed runs.
7. Only then promote the dashboard as the sponsor-facing full-sweep operating console.

## Key risk

The current model is sufficient for a pilot dashboard, but if the dashboard grows around the current run/trial/path model without suites and arm-runs, the sponsor-requested navigation will become harder to retrofit. Add the two missing entities now while the model is still small.

