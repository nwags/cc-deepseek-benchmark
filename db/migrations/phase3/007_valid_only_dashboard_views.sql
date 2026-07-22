-- Phase 3 valid-only dashboard layer.
--
-- Raw ingested runs/trials stay preserved. This adds an explicit invalid-run
-- exclusion table plus valid-only views for dashboard comparison surfaces.

create table if not exists benchmark.benchmark_invalid_arm_runs (
    id bigserial primary key,
    suite_id text not null,
    arm_id text not null,
    run_label text not null,
    provider_run_id text,
    reason text not null,
    invalidated_at timestamptz not null default now(),
    invalidated_by text not null default 'manual-audit',
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (suite_id, arm_id, run_label)
);

create index if not exists idx_benchmark_invalid_arm_runs_lookup
    on benchmark.benchmark_invalid_arm_runs (suite_id, arm_id, run_label);

insert into benchmark.benchmark_invalid_arm_runs (
    suite_id,
    arm_id,
    run_label,
    provider_run_id,
    reason,
    invalidated_by,
    raw_metadata
)
values
    (
      'phase3-full-20',
      'router-anthropic-opus',
      'router-anthropic-opus/2026-06-28__13-28-56',
      '28323747982',
      'Anthropic workspace API usage limit until 2026-07-01 00:00 UTC',
      'phase3-validity-audit',
      '{"source":"configs/eval_invalid_runs.local.tsv","category":"provider_limit"}'::jsonb
    ),
    (
      'phase3-full-20',
      'router-gemini-3.1-pro',
      'router-gemini-3.1-pro/2026-06-30__01-23-54',
      '28413826034',
      'Gemini project monthly spending cap exceeded; 429 RESOURCE_EXHAUSTED provider-limit failures',
      'phase3-validity-audit',
      '{"source":"configs/eval_invalid_runs.local.tsv","category":"provider_limit"}'::jsonb
    ),
    (
      'phase3-full-20',
      'router-anthropic-haiku-sanitized',
      'router-anthropic-haiku-sanitized/2026-07-02__02-01-16',
      '28560121535',
      'Runtime service/API path failure; Claude Code reported ConnectionRefused via sanitizer/LiteLLM path; zero API tokens/cost across all trials',
      'phase3-validity-audit',
      '{"source":"configs/eval_invalid_runs.local.tsv","category":"infrastructure_failure"}'::jsonb
    )
on conflict (suite_id, arm_id, run_label) do update set
    provider_run_id = excluded.provider_run_id,
    reason = excluded.reason,
    invalidated_by = excluded.invalidated_by,
    raw_metadata = excluded.raw_metadata,
    updated_at = now();

create or replace view benchmark.v_valid_trial_quality_flags as
select tqf.*
from benchmark.v_trial_quality_flags tqf
where not exists (
    select 1
    from benchmark.benchmark_invalid_arm_runs invalid
    where invalid.suite_id = tqf.suite_id
      and invalid.arm_id = tqf.arm_id
      and invalid.run_label = tqf.run_label
);

create or replace view benchmark.v_valid_arm_run_summary as
select ars.*
from benchmark.v_arm_run_summary ars
where not exists (
    select 1
    from benchmark.benchmark_invalid_arm_runs invalid
    where invalid.suite_id = ars.suite_id
      and invalid.arm_id = ars.arm_id
      and invalid.run_label = ars.run_label
);

create or replace view benchmark.v_valid_suite_arm_quality_summary as
select
    phase,
    logical_mode,
    storage_mode,
    suite_id,
    arm_id,
    count(distinct run_label)::integer as arm_run_count,
    count(*)::integer as trial_count,
    count(*) filter (where is_success)::integer as success_count,
    round(count(*) filter (where is_success)::numeric / nullif(count(*), 0)::numeric, 4) as raw_pass_rate,
    count(*) filter (where quality_flag = 'suspect_noop_zero_token')::integer as suspect_noop_count,
    count(*) filter (where quality_flag = any(array['exception', 'exception_with_success']))::integer as exception_count,
    count(*) filter (where quality_flag = 'normal_failed_trial')::integer as normal_failed_count,
    count(*) filter (where is_qualified_attempt)::integer as qualified_trial_count,
    count(*) filter (where is_qualified_attempt and is_success)::integer as qualified_success_count,
    round(
      count(*) filter (where is_qualified_attempt and is_success)::numeric
      / nullif(count(*) filter (where is_qualified_attempt), 0)::numeric,
      4
    ) as qualified_pass_rate,
    coalesce(sum(cost_usd), 0::numeric) as recorded_cost_usd,
    count(*) filter (where cost_usd is null)::integer as missing_cost_count
from benchmark.v_valid_trial_quality_flags
group by phase, logical_mode, storage_mode, suite_id, arm_id;

create or replace view benchmark.v_valid_suite_arm_comparison as
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
    percentile_cont(0.5) within group (order by t.runtime_seconds::double precision) as median_runtime_seconds,
    sum(t.cost_usd) as trial_cost_usd,
    count(t.cost_usd) as cost_row_count,
    count(t.id) filter (where t.cost_usd is null) as missing_cost_count
from benchmark.benchmark_arm_runs ar
join benchmark.benchmark_runs r
    on r.id = ar.run_id
left join benchmark.benchmark_eval_suites suite
    on suite.suite_id = ar.suite_id
left join benchmark.benchmark_trials t
    on t.arm_run_id = ar.id
where not exists (
    select 1
    from benchmark.benchmark_invalid_arm_runs invalid
    where invalid.suite_id = ar.suite_id
      and invalid.arm_id = ar.arm_id
      and invalid.run_label = r.run_label
)
group by
    ar.suite_id,
    suite.display_name,
    suite.suite_type,
    ar.arm_id;

create or replace view benchmark.v_valid_eval_arm_comparison as
select
    ar.suite_id,
    ar.arm_id,
    ar.logical_mode,
    ar.storage_mode,
    t.task_id,
    task.task_name,
    count(t.id) as trial_count,
    count(t.id) filter (where coalesce(t.reward, 0) >= 1) as success_count,
    case
        when count(t.id) = 0 then null
        else count(t.id) filter (where coalesce(t.reward, 0) >= 1)::numeric / count(t.id)::numeric
    end as pass_rate,
    avg(t.reward) as mean_reward,
    avg(t.runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by t.runtime_seconds::double precision) as median_runtime_seconds,
    sum(t.cost_usd) as trial_cost_usd,
    count(t.cost_usd) as cost_row_count,
    count(t.id) filter (where t.cost_usd is null) as missing_cost_count
from benchmark.benchmark_arm_runs ar
join benchmark.benchmark_runs r
    on r.id = ar.run_id
join benchmark.benchmark_trials t
    on t.arm_run_id = ar.id
left join benchmark.benchmark_tasks task
    on task.task_id = t.task_id
where not exists (
    select 1
    from benchmark.benchmark_invalid_arm_runs invalid
    where invalid.suite_id = ar.suite_id
      and invalid.arm_id = ar.arm_id
      and invalid.run_label = r.run_label
)
group by
    ar.suite_id,
    ar.arm_id,
    ar.logical_mode,
    ar.storage_mode,
    t.task_id,
    task.task_name;
