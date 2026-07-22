-- Phase 3 dashboard read models.
-- These views aggregate trials/artifacts/audits separately first to avoid
-- join multiplication when a run has many trials and many artifacts.

create or replace view benchmark.v_run_trial_summary as
select
    run_id,
    count(*) as trial_count,
    count(*) filter (where coalesce(reward, 0) >= 1) as success_count,
    count(*) filter (where coalesce(reward, 0) < 1) as failure_count,
    avg(runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by runtime_seconds) as median_runtime_seconds,
    sum(cost_usd) as trial_cost_usd,
    sum(input_tokens) as input_tokens,
    sum(cache_tokens) as cache_tokens,
    sum(output_tokens) as output_tokens
from benchmark.benchmark_trials
group by run_id;

create or replace view benchmark.v_run_artifact_summary as
select
    run_id,
    count(*) as artifact_count,
    sum(size_bytes) as artifact_size_bytes,
    count(*) filter (where r2_uri is not null) as r2_artifact_count
from benchmark.benchmark_artifacts
group by run_id;

create or replace view benchmark.v_run_audit_summary as
select
    run_id,
    count(*) as audit_count,
    count(*) filter (where audit_status = 'pass') as audit_pass_count,
    count(*) filter (where audit_status <> 'pass') as audit_nonpass_count,
    sum(websearch_events) as websearch_events,
    sum(webfetch_events) as webfetch_events,
    sum(forbidden_tools_available) as forbidden_tools_available
from benchmark.contamination_audits
group by run_id;

create or replace view benchmark.v_dashboard_runs as
select
    r.id as run_id,
    r.phase,
    r.mode,
    r.run_label,
    r.git_commit,
    r.branch,
    r.runner_name,
    r.runner_provider,
    r.runner_region,
    r.started_at,
    r.finished_at,
    r.status,
    r.created_at,
    r.raw_metadata,
    coalesce(ts.trial_count, 0) as trial_count,
    coalesce(ts.success_count, 0) as success_count,
    coalesce(ts.failure_count, 0) as failure_count,
    case
        when coalesce(ts.trial_count, 0) = 0 then null
        else ts.success_count::numeric / ts.trial_count::numeric
    end as pass_rate,
    ts.avg_runtime_seconds,
    ts.median_runtime_seconds,
    coalesce(ts.trial_cost_usd, 0) as trial_cost_usd,
    coalesce(ts.input_tokens, 0) as input_tokens,
    coalesce(ts.cache_tokens, 0) as cache_tokens,
    coalesce(ts.output_tokens, 0) as output_tokens,
    coalesce(art.artifact_count, 0) as artifact_count,
    coalesce(art.artifact_size_bytes, 0) as artifact_size_bytes,
    coalesce(art.r2_artifact_count, 0) as r2_artifact_count,
    coalesce(aud.audit_count, 0) as audit_count,
    coalesce(aud.audit_pass_count, 0) as audit_pass_count,
    coalesce(aud.audit_nonpass_count, 0) as audit_nonpass_count,
    coalesce(aud.websearch_events, 0) as websearch_events,
    coalesce(aud.webfetch_events, 0) as webfetch_events,
    coalesce(aud.forbidden_tools_available, 0) as forbidden_tools_available
from benchmark.benchmark_runs r
left join benchmark.v_run_trial_summary ts
    on ts.run_id = r.id
left join benchmark.v_run_artifact_summary art
    on art.run_id = r.id
left join benchmark.v_run_audit_summary aud
    on aud.run_id = r.id;

create or replace view benchmark.v_dashboard_arms as
select
    a.arm_id,
    a.display_name,
    a.provider_family,
    a.backend_model,
    a.router_model,
    a.agent_harness,
    a.config_path,
    a.active,
    count(distinct r.id) as run_count,
    count(t.id) as trial_count,
    count(t.id) filter (where coalesce(t.reward, 0) >= 1) as success_count,
    case
        when count(t.id) = 0 then null
        else count(t.id) filter (where coalesce(t.reward, 0) >= 1)::numeric / count(t.id)::numeric
    end as pass_rate,
    sum(t.cost_usd) as trial_cost_usd,
    avg(t.runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by t.runtime_seconds) as median_runtime_seconds
from benchmark.benchmark_arms a
left join benchmark.benchmark_trials t
    on t.arm_id = a.arm_id
left join benchmark.benchmark_runs r
    on r.id = t.run_id
group by
    a.arm_id,
    a.display_name,
    a.provider_family,
    a.backend_model,
    a.router_model,
    a.agent_harness,
    a.config_path,
    a.active;

create or replace view benchmark.v_dashboard_tasks as
select
    task.task_id,
    task.benchmark,
    task.benchmark_version,
    task.task_name,
    task.active,
    count(t.id) as trial_count,
    count(t.id) filter (where coalesce(t.reward, 0) >= 1) as success_count,
    case
        when count(t.id) = 0 then null
        else count(t.id) filter (where coalesce(t.reward, 0) >= 1)::numeric / count(t.id)::numeric
    end as pass_rate,
    avg(t.runtime_seconds) as avg_runtime_seconds,
    percentile_cont(0.5) within group (order by t.runtime_seconds) as median_runtime_seconds,
    sum(t.cost_usd) as trial_cost_usd
from benchmark.benchmark_tasks task
left join benchmark.benchmark_trials t
    on t.task_id = task.task_id
group by
    task.task_id,
    task.benchmark,
    task.benchmark_version,
    task.task_name,
    task.active;
