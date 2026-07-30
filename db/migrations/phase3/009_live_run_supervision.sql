-- Shared live-run supervision state.
-- Incomplete executions remain separate from canonical benchmark tables until
-- final publication succeeds.

create table if not exists benchmark.live_runs (
    id uuid primary key default gen_random_uuid(),
    live_run_id text unique not null,
    github_run_id text,
    github_run_attempt integer,
    github_job text,
    runner_name text,
    workspace_name text,
    workspace_fingerprint text,
    arm_id text not null,
    phase text not null,
    mode text not null,
    run_kind text not null,
    scored boolean not null default false,
    status text not null default 'starting',
    benchmark_status text,
    live_publication_status text,
    progressive_artifact_status text,
    canonical_publication_status text,
    command_summary jsonb not null default '{}'::jsonb,
    expected_trial_count integer,
    completed_trial_count integer not null default 0,
    success_count integer not null default 0,
    failure_count integer not null default 0,
    exception_count integer not null default 0,
    observed_cost_usd numeric,
    input_tokens bigint,
    cache_tokens bigint,
    output_tokens bigint,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    last_heartbeat_at timestamptz,
    elapsed_seconds numeric,
    returncode integer,
    event_count integer not null default 0,
    latest_message text,
    canonical_arm_run_id uuid references benchmark.benchmark_arm_runs(id) on delete set null,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (github_run_attempt is null or github_run_attempt > 0),
    check (expected_trial_count is null or expected_trial_count >= 0),
    check (completed_trial_count >= 0),
    check (success_count >= 0),
    check (failure_count >= 0),
    check (exception_count >= 0),
    check (event_count >= 0)
);

create table if not exists benchmark.live_run_events (
    id bigserial primary key,
    live_run_id text not null references benchmark.live_runs(live_run_id) on delete cascade,
    sequence integer not null,
    event_type text not null,
    occurred_at timestamptz not null default now(),
    elapsed_seconds numeric,
    stream text,
    message text,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (live_run_id, sequence),
    check (sequence > 0)
);

create table if not exists benchmark.live_trials (
    id uuid primary key default gen_random_uuid(),
    live_run_id text not null references benchmark.live_runs(live_run_id) on delete cascade,
    trial_key text not null,
    task_id text,
    attempt_index integer,
    status text not null default 'detected',
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
    relative_local_path text,
    stability_state text not null default 'observed',
    completion_evidence jsonb not null default '{}'::jsonb,
    raw_result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (live_run_id, trial_key),
    check (attempt_index is null or attempt_index >= 0),
    check (runtime_seconds is null or runtime_seconds >= 0)
);

create table if not exists benchmark.live_artifacts (
    id uuid primary key default gen_random_uuid(),
    live_run_id text not null references benchmark.live_runs(live_run_id) on delete cascade,
    trial_key text,
    artifact_type text not null,
    relative_local_path text not null,
    r2_uri text,
    sha256 text not null,
    size_bytes bigint not null,
    stability_state text not null default 'stable',
    uploaded_at timestamptz,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (size_bytes >= 0)
);

create unique index if not exists idx_live_artifacts_idempotent
    on benchmark.live_artifacts (
        live_run_id,
        coalesce(trial_key, ''),
        relative_local_path,
        sha256
    );

create index if not exists idx_live_runs_newest
    on benchmark.live_runs (started_at desc, created_at desc);

create index if not exists idx_live_runs_active
    on benchmark.live_runs (status, last_heartbeat_at desc)
    where status in ('starting', 'running', 'finalizing');

create index if not exists idx_live_runs_stale_heartbeat
    on benchmark.live_runs (last_heartbeat_at)
    where status in ('starting', 'running', 'finalizing');

create index if not exists idx_live_runs_github_execution
    on benchmark.live_runs (github_run_id, github_run_attempt);

create index if not exists idx_live_runs_runner
    on benchmark.live_runs (runner_name, started_at desc);

create index if not exists idx_live_run_events_ordered
    on benchmark.live_run_events (live_run_id, sequence desc);

create index if not exists idx_live_trials_run_status
    on benchmark.live_trials (live_run_id, status, trial_key);

create index if not exists idx_live_artifacts_run_trial
    on benchmark.live_artifacts (live_run_id, trial_key, artifact_type);

comment on table benchmark.live_runs is
    'Non-canonical live execution state. Rows become linked to canonical arm runs only after final publication.';

comment on column benchmark.live_runs.workspace_fingerprint is
    'SHA-256 fingerprint of the resolved workspace path; the shared table intentionally does not store the full path.';

comment on table benchmark.live_run_events is
    'Bounded live event tail. Publishers sample high-volume process output and retain only its newest rows per run.';
