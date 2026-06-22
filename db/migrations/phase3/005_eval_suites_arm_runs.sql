-- Phase 3 sponsor-facing evaluation model.
-- Adds first-class eval suites and arm runs without removing the pilot run/trial model.

create table if not exists benchmark.benchmark_eval_suites (
    id uuid primary key default gen_random_uuid(),
    suite_id text unique not null,
    display_name text not null,
    description text,
    benchmark text not null default 'terminal-bench',
    benchmark_version text,
    phase text not null default 'phase3',
    suite_type text not null,
    version text,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb
);

create table if not exists benchmark.benchmark_eval_suite_items (
    id uuid primary key default gen_random_uuid(),
    suite_id text not null references benchmark.benchmark_eval_suites(suite_id) on delete cascade,
    task_id text not null references benchmark.benchmark_tasks(task_id) on delete cascade,
    display_order integer,
    required boolean not null default true,
    rationale text,
    created_at timestamptz not null default now(),
    unique(suite_id, task_id)
);

create table if not exists benchmark.benchmark_arm_runs (
    id uuid primary key default gen_random_uuid(),
    run_id uuid references benchmark.benchmark_runs(id) on delete cascade,
    arm_id text references benchmark.benchmark_arms(arm_id),
    suite_id text references benchmark.benchmark_eval_suites(suite_id),
    logical_mode text not null,
    storage_mode text,
    status text not null default 'unknown',
    started_at timestamptz,
    finished_at timestamptz,
    n_trials integer,
    n_completed_trials integer,
    n_errored_trials integer,
    mean_reward numeric,
    total_cost_usd numeric,
    total_runtime_seconds numeric,
    input_tokens bigint,
    cache_tokens bigint,
    output_tokens bigint,
    github_run_id text,
    artifact_root_uri text,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(run_id, arm_id)
);

alter table benchmark.benchmark_trials
    add column if not exists arm_run_id uuid references benchmark.benchmark_arm_runs(id) on delete set null;

create index if not exists idx_benchmark_arm_runs_run
    on benchmark.benchmark_arm_runs(run_id);

create index if not exists idx_benchmark_arm_runs_arm
    on benchmark.benchmark_arm_runs(arm_id);

create index if not exists idx_benchmark_arm_runs_suite
    on benchmark.benchmark_arm_runs(suite_id);

create index if not exists idx_benchmark_trials_arm_run
    on benchmark.benchmark_trials(arm_run_id);

insert into benchmark.benchmark_eval_suites (
    suite_id, display_name, description, benchmark, benchmark_version,
    phase, suite_type, version, active, notes, raw_metadata
)
values
    (
      'phase3-canary-1',
      'Phase 3 canary',
      'Single-task canary gate used before smoke/full-sweep eligibility.',
      'terminal-bench',
      '2.0',
      'phase3',
      'canary',
      '2026-06',
      true,
      'Seeded by migration 005.',
      '{"source":"db/migrations/phase3/005_eval_suites_arm_runs.sql"}'::jsonb
    ),
    (
      'phase3-smoke-5',
      'Phase 3 smoke suite',
      'Small smoke suite used to validate provider/router behavior before full sweep.',
      'terminal-bench',
      '2.0',
      'phase3',
      'smoke',
      '2026-06',
      true,
      'Seeded by migration 005.',
      '{"source":"db/migrations/phase3/005_eval_suites_arm_runs.sql"}'::jsonb
    ),
    (
      'phase3-full-20',
      'Phase 3 full sweep',
      'Twenty Terminal-Bench 2.0 tasks used for Phase 3 full-sweep comparisons.',
      'terminal-bench',
      '2.0',
      'phase3',
      'full',
      '2026-06',
      true,
      'Seeded by migration 005.',
      '{"source":"db/migrations/phase3/005_eval_suites_arm_runs.sql"}'::jsonb
    )
on conflict (suite_id) do update set
    display_name = excluded.display_name,
    description = excluded.description,
    benchmark = excluded.benchmark,
    benchmark_version = excluded.benchmark_version,
    phase = excluded.phase,
    suite_type = excluded.suite_type,
    version = excluded.version,
    active = excluded.active,
    raw_metadata = excluded.raw_metadata;

-- Seed eval suite membership rows from checked-in suite definitions.
-- The join to benchmark_tasks keeps this migration safe on partially populated DBs.
insert into benchmark.benchmark_eval_suite_items (
    suite_id,
    task_id,
    display_order,
    required,
    rationale
)
select
    v.suite_id,
    v.task_id,
    v.display_order,
    v.required,
    v.rationale
from (
values
    ('phase3-canary-1', 'terminal-bench-2.0:modernize-scientific-stack', 1, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:build-cython-ext', 1, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:cancel-async-tasks', 2, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:custom-memory-heap-crash', 3, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:fix-code-vulnerability', 4, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:git-leak-recovery', 5, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:multi-source-data-merger', 6, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:modernize-scientific-stack', 7, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:query-optimize', 8, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:portfolio-optimization', 9, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:model-extraction-relu-logits', 10, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:mteb-retrieve', 11, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:llm-inference-batching-scheduler', 12, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:torch-pipeline-parallelism', 13, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:configure-git-webserver', 14, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:nginx-request-logging', 15, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:openssl-selfsigned-cert', 16, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:sqlite-db-truncate', 17, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:password-recovery', 18, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:polyglot-rust-c', 19, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-full-20', 'terminal-bench-2.0:schemelike-metacircular-eval', 20, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-smoke-5', 'terminal-bench-2.0:modernize-scientific-stack', 1, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-smoke-5', 'terminal-bench-2.0:query-optimize', 2, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-smoke-5', 'terminal-bench-2.0:cancel-async-tasks', 3, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-smoke-5', 'terminal-bench-2.0:build-cython-ext', 4, true, 'Seeded from configs/eval_suites/*.yaml'),
    ('phase3-smoke-5', 'terminal-bench-2.0:schemelike-metacircular-eval', 5, true, 'Seeded from configs/eval_suites/*.yaml')
) as v(suite_id, task_id, display_order, required, rationale)
join benchmark.benchmark_tasks task
    on task.task_id = v.task_id
on conflict (suite_id, task_id) do update set
    display_order = excluded.display_order,
    required = excluded.required,
    rationale = excluded.rationale;


-- Backfill arm-run rows from existing pilot runs/trials.
with run_trial_stats as (
    select
        r.id as run_id,
        t.arm_id,
        r.phase,
        r.mode as storage_mode,
        case
            when r.phase = 'phase3' and r.mode = 'raw' then 'full'
            else r.mode
        end as logical_mode,
        case
            when r.phase = 'phase3' and r.mode = 'raw' then 'phase3-full-20'
            when r.phase = 'phase3' and r.mode = 'smoke' then 'phase3-smoke-5'
            when r.phase = 'phase3' and r.mode = 'canary' then 'phase3-canary-1'
            else null
        end as suite_id,
        r.status,
        r.started_at,
        r.finished_at,
        count(t.id)::integer as n_trials,
        count(t.id) filter (where t.exception_type is null)::integer as n_completed_trials,
        count(t.id) filter (where t.exception_type is not null)::integer as n_errored_trials,
        avg(t.reward) as mean_reward,
        sum(t.cost_usd) as total_cost_usd,
        sum(t.runtime_seconds) as total_runtime_seconds,
        sum(t.input_tokens)::bigint as input_tokens,
        sum(t.cache_tokens)::bigint as cache_tokens,
        sum(t.output_tokens)::bigint as output_tokens
    from benchmark.benchmark_runs r
    join benchmark.benchmark_trials t on t.run_id = r.id
    where t.arm_id is not null
    group by r.id, t.arm_id
)
insert into benchmark.benchmark_arm_runs (
    run_id,
    arm_id,
    suite_id,
    logical_mode,
    storage_mode,
    status,
    started_at,
    finished_at,
    n_trials,
    n_completed_trials,
    n_errored_trials,
    mean_reward,
    total_cost_usd,
    total_runtime_seconds,
    input_tokens,
    cache_tokens,
    output_tokens,
    raw_metadata
)
select
    run_id,
    arm_id,
    suite_id,
    logical_mode,
    storage_mode,
    status,
    started_at,
    finished_at,
    n_trials,
    n_completed_trials,
    n_errored_trials,
    mean_reward,
    total_cost_usd,
    total_runtime_seconds,
    input_tokens,
    cache_tokens,
    output_tokens,
    jsonb_build_object(
      'source', 'db/migrations/phase3/005_eval_suites_arm_runs.sql',
      'backfilled_from_run_mode', storage_mode
    )
from run_trial_stats
on conflict (run_id, arm_id) do update set
    suite_id = excluded.suite_id,
    logical_mode = excluded.logical_mode,
    storage_mode = excluded.storage_mode,
    status = excluded.status,
    started_at = excluded.started_at,
    finished_at = excluded.finished_at,
    n_trials = excluded.n_trials,
    n_completed_trials = excluded.n_completed_trials,
    n_errored_trials = excluded.n_errored_trials,
    mean_reward = excluded.mean_reward,
    total_cost_usd = excluded.total_cost_usd,
    total_runtime_seconds = excluded.total_runtime_seconds,
    input_tokens = excluded.input_tokens,
    cache_tokens = excluded.cache_tokens,
    output_tokens = excluded.output_tokens,
    raw_metadata = excluded.raw_metadata,
    updated_at = now();

update benchmark.benchmark_trials t
set arm_run_id = ar.id
from benchmark.benchmark_arm_runs ar
where ar.run_id = t.run_id
  and ar.arm_id = t.arm_id
  and t.arm_run_id is distinct from ar.id;

create or replace view benchmark.v_arm_run_trials as
select
    ar.id as arm_run_id,
    ar.run_id,
    ar.arm_id,
    ar.suite_id,
    ar.logical_mode,
    ar.storage_mode,
    t.id as trial_id,
    t.task_id,
    task.task_name,
    t.attempt_index,
    t.reward,
    t.exception_type,
    t.runtime_seconds,
    t.cost_usd,
    t.input_tokens,
    t.cache_tokens,
    t.output_tokens,
    t.result_local_path,
    t.result_artifact_uri,
    t.notes,
    t.raw_result,
    t.created_at
from benchmark.benchmark_arm_runs ar
join benchmark.benchmark_trials t
    on t.arm_run_id = ar.id
left join benchmark.benchmark_tasks task
    on task.task_id = t.task_id;

create or replace view benchmark.v_arm_run_summary as
with trial_summary as (
    select
        arm_run_id,
        count(*) as trial_count,
        count(*) filter (where coalesce(reward, 0) >= 1) as success_count,
        count(*) filter (where coalesce(reward, 0) < 1) as failure_count,
        case
            when count(*) = 0 then null
            else count(*) filter (where coalesce(reward, 0) >= 1)::numeric / count(*)::numeric
        end as pass_rate,
        avg(runtime_seconds) as avg_runtime_seconds,
        percentile_cont(0.5) within group (order by runtime_seconds) as median_runtime_seconds,
        sum(cost_usd) as trial_cost_usd,
        count(cost_usd) as cost_row_count,
        count(*) filter (where cost_usd is null) as missing_cost_count,
        sum(input_tokens) as input_tokens,
        sum(cache_tokens) as cache_tokens,
        sum(output_tokens) as output_tokens
    from benchmark.benchmark_trials
    group by arm_run_id
),
artifact_summary as (
    select
        t.arm_run_id,
        count(distinct art.id) as artifact_count,
        count(distinct art.id) filter (where art.r2_uri is not null) as r2_artifact_count
    from benchmark.benchmark_trials t
    left join benchmark.benchmark_artifacts art
        on art.trial_id = t.id
    group by t.arm_run_id
),
run_root_artifact_summary as (
    select
        ar.id as arm_run_id,
        count(distinct art.id) as run_root_artifact_count,
        count(distinct art.id) filter (where art.r2_uri is not null) as run_root_r2_artifact_count
    from benchmark.benchmark_arm_runs ar
    left join benchmark.benchmark_artifacts art
        on art.run_id = ar.run_id
       and art.trial_id is null
    group by ar.id
)
select
    ar.id as arm_run_id,
    ar.run_id,
    r.run_label,
    ar.arm_id,
    a.display_name as arm_display_name,
    a.provider_family,
    a.backend_model,
    a.router_model,
    ar.suite_id,
    suite.display_name as suite_display_name,
    suite.suite_type,
    ar.logical_mode,
    ar.storage_mode,
    ar.status,
    ar.started_at,
    ar.finished_at,
    ar.n_trials,
    ar.n_completed_trials,
    ar.n_errored_trials,
    coalesce(ts.trial_count, 0) as trial_count,
    coalesce(ts.success_count, 0) as success_count,
    coalesce(ts.failure_count, 0) as failure_count,
    ts.pass_rate,
    ts.avg_runtime_seconds,
    ts.median_runtime_seconds,
    coalesce(ts.trial_cost_usd, 0) as trial_cost_usd,
    coalesce(ts.cost_row_count, 0) as cost_row_count,
    coalesce(ts.missing_cost_count, 0) as missing_cost_count,
    coalesce(ts.input_tokens, 0) as input_tokens,
    coalesce(ts.cache_tokens, 0) as cache_tokens,
    coalesce(ts.output_tokens, 0) as output_tokens,
    coalesce(art.artifact_count, 0) + coalesce(root_art.run_root_artifact_count, 0) as artifact_count,
    coalesce(art.r2_artifact_count, 0) + coalesce(root_art.run_root_r2_artifact_count, 0) as r2_artifact_count
from benchmark.benchmark_arm_runs ar
join benchmark.benchmark_runs r
    on r.id = ar.run_id
left join benchmark.benchmark_arms a
    on a.arm_id = ar.arm_id
left join benchmark.benchmark_eval_suites suite
    on suite.suite_id = ar.suite_id
left join trial_summary ts
    on ts.arm_run_id = ar.id
left join artifact_summary art
    on art.arm_run_id = ar.id
left join run_root_artifact_summary root_art
    on root_art.arm_run_id = ar.id;

create or replace view benchmark.v_eval_arm_comparison as
select
    t.task_id,
    task.task_name,
    ar.arm_id,
    ar.suite_id,
    ar.logical_mode,
    count(t.id) as trial_count,
    count(t.id) filter (where coalesce(t.reward, 0) >= 1) as success_count,
    case
        when count(t.id) = 0 then null
        else count(t.id) filter (where coalesce(t.reward, 0) >= 1)::numeric / count(t.id)::numeric
    end as pass_rate,
    avg(t.reward) as mean_reward,
    avg(t.runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by t.runtime_seconds) as median_runtime_seconds,
    sum(t.cost_usd) as trial_cost_usd,
    count(t.cost_usd) as cost_row_count,
    count(t.id) filter (where t.cost_usd is null) as missing_cost_count
from benchmark.benchmark_arm_runs ar
join benchmark.benchmark_trials t
    on t.arm_run_id = ar.id
left join benchmark.benchmark_tasks task
    on task.task_id = t.task_id
group by
    t.task_id,
    task.task_name,
    ar.arm_id,
    ar.suite_id,
    ar.logical_mode;

create or replace view benchmark.v_suite_arm_comparison as
select
    ar.suite_id,
    suite.display_name as suite_display_name,
    suite.suite_type,
    ar.arm_id,
    count(t.id) as trial_count,
    count(distinct t.task_id) as task_count,
    count(t.id) filter (where coalesce(t.reward, 0) >= 1) as success_count,
    case
        when count(t.id) = 0 then null
        else count(t.id) filter (where coalesce(t.reward, 0) >= 1)::numeric / count(t.id)::numeric
    end as pass_rate,
    avg(t.reward) as mean_reward,
    avg(t.runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by t.runtime_seconds) as median_runtime_seconds,
    sum(t.cost_usd) as trial_cost_usd,
    count(t.cost_usd) as cost_row_count,
    count(t.id) filter (where t.cost_usd is null) as missing_cost_count
from benchmark.benchmark_arm_runs ar
left join benchmark.benchmark_eval_suites suite
    on suite.suite_id = ar.suite_id
left join benchmark.benchmark_trials t
    on t.arm_run_id = ar.id
group by
    ar.suite_id,
    suite.display_name,
    suite.suite_type,
    ar.arm_id;
