-- Phase 3 benchmark metadata schema.
-- Target: Supabase Postgres.
-- Large artifacts should live in Cloudflare R2; this schema stores metadata,
-- hashes, local paths, and artifact URIs.

create extension if not exists pgcrypto;

create schema if not exists benchmark;

create table if not exists benchmark.benchmark_runs (
    id uuid primary key default gen_random_uuid(),
    phase text not null,
    mode text not null,
    run_label text,
    git_commit text,
    branch text,
    runner_name text,
    runner_provider text,
    runner_region text,
    started_at timestamptz,
    finished_at timestamptz,
    status text not null default 'unknown',
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists benchmark.benchmark_arms (
    arm_id text primary key,
    display_name text,
    provider_family text,
    backend_model text,
    router_model text,
    agent_harness text,
    config_path text,
    config_sha256 text,
    active boolean not null default true,
    notes text,
    raw_config jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists benchmark.benchmark_tasks (
    task_id text primary key,
    benchmark text not null default 'terminal-bench',
    benchmark_version text,
    task_name text not null,
    task_source_uri text,
    contamination_notes text,
    active boolean not null default true,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists benchmark.benchmark_trials (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references benchmark.benchmark_runs(id) on delete cascade,
    arm_id text references benchmark.benchmark_arms(arm_id),
    task_id text references benchmark.benchmark_tasks(task_id),
    attempt_index integer,
    reward numeric,
    exception_type text,
    exception_summary text,
    runtime_seconds numeric,
    input_tokens bigint,
    cache_tokens bigint,
    output_tokens bigint,
    cost_usd numeric,
    started_at timestamptz,
    finished_at timestamptz,
    result_local_path text,
    result_artifact_uri text,
    notes text,
    raw_result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists benchmark.benchmark_artifacts (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references benchmark.benchmark_runs(id) on delete cascade,
    trial_id uuid references benchmark.benchmark_trials(id) on delete cascade,
    artifact_type text not null,
    local_path text,
    r2_uri text,
    github_uri text,
    sha256 text,
    size_bytes bigint,
    created_at timestamptz not null default now(),
    retention_class text not null default 'pilot',
    notes text
);

create table if not exists benchmark.benchmark_models (
    id uuid primary key default gen_random_uuid(),
    provider_family text not null,
    model_slug text not null,
    endpoint_base text,
    endpoint_region text,
    context_window integer,
    pricing_input_per_million numeric,
    pricing_output_per_million numeric,
    pricing_source_uri text,
    active boolean not null default true,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique(provider_family, model_slug)
);

create table if not exists benchmark.contamination_audits (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references benchmark.benchmark_runs(id) on delete cascade,
    trial_id uuid references benchmark.benchmark_trials(id) on delete cascade,
    audit_status text not null,
    websearch_events integer not null default 0,
    webfetch_events integer not null default 0,
    forbidden_tools_available integer not null default 0,
    disallowed_tools text,
    audit_local_path text,
    audit_artifact_uri text,
    notes text,
    raw_audit jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists benchmark.cost_forecasts (
    id uuid primary key default gen_random_uuid(),
    forecast_name text not null,
    source_run_id uuid references benchmark.benchmark_runs(id) on delete set null,
    method text not null,
    arms_included integer,
    task_count integer,
    attempts_per_task integer,
    estimated_cost_usd numeric,
    reserve_multiplier numeric,
    reserve_cost_usd numeric,
    notes text,
    raw_forecast jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_benchmark_runs_phase_mode
    on benchmark.benchmark_runs(phase, mode);

create index if not exists idx_benchmark_trials_run_arm
    on benchmark.benchmark_trials(run_id, arm_id);

create index if not exists idx_benchmark_trials_task
    on benchmark.benchmark_trials(task_id);

create index if not exists idx_benchmark_artifacts_run
    on benchmark.benchmark_artifacts(run_id);

create index if not exists idx_contamination_audits_run
    on benchmark.contamination_audits(run_id);
