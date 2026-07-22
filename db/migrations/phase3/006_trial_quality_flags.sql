create or replace view benchmark.v_trial_quality_flags as
select
  t.id as trial_id,
  t.run_id,
  t.arm_run_id,
  t.arm_id,
  r.phase,
  r.mode as storage_mode,
  coalesce(ar.logical_mode, r.mode) as logical_mode,
  ar.suite_id,
  r.run_label,
  t.task_id,
  t.attempt_index,
  t.reward,
  t.runtime_seconds,
  t.cost_usd,
  t.input_tokens,
  t.cache_tokens,
  t.output_tokens,
  t.exception_type,
  t.exception_summary,
  case
    when coalesce(t.reward, 0) > 0 then 'success'
    when t.exception_type is not null then 'exception'
    else 'failed'
  end as raw_status,
  case
    when t.exception_type is not null and coalesce(t.reward, 0) > 0 then 'exception_with_success'
    when t.exception_type is not null then 'exception'
    when coalesce(t.reward, 0) > 0 then 'success'
    when coalesce(t.input_tokens, 0) = 0
     and coalesce(t.output_tokens, 0) = 0
     and coalesce(t.cost_usd, 0) = 0
     and t.exception_type is null
      then 'suspect_noop_zero_token'
    else 'normal_failed_trial'
  end as quality_flag,
  (
    coalesce(t.input_tokens, 0) = 0
    and coalesce(t.output_tokens, 0) = 0
    and coalesce(t.cost_usd, 0) = 0
    and t.exception_type is null
    and coalesce(t.reward, 0) = 0
  ) as is_suspect_noop,
  (coalesce(t.reward, 0) > 0) as is_success,
  not (
    coalesce(t.input_tokens, 0) = 0
    and coalesce(t.output_tokens, 0) = 0
    and coalesce(t.cost_usd, 0) = 0
    and t.exception_type is null
    and coalesce(t.reward, 0) = 0
  ) as is_qualified_attempt
from benchmark.benchmark_trials t
join benchmark.benchmark_runs r
  on r.id = t.run_id
left join benchmark.benchmark_arm_runs ar
  on ar.id = t.arm_run_id;

create or replace view benchmark.v_arm_run_quality_summary as
select
  run_id,
  arm_run_id,
  phase,
  logical_mode,
  storage_mode,
  suite_id,
  arm_id,
  run_label,
  count(*)::int as trial_count,
  count(*) filter (where is_success)::int as success_count,
  round(
    (count(*) filter (where is_success))::numeric / nullif(count(*), 0),
    4
  ) as raw_pass_rate,
  count(*) filter (where quality_flag = 'suspect_noop_zero_token')::int as suspect_noop_count,
  count(*) filter (where quality_flag in ('exception', 'exception_with_success'))::int as exception_count,
  count(*) filter (where quality_flag = 'normal_failed_trial')::int as normal_failed_count,
  count(*) filter (where is_qualified_attempt)::int as qualified_trial_count,
  count(*) filter (where is_qualified_attempt and is_success)::int as qualified_success_count,
  round(
    (count(*) filter (where is_qualified_attempt and is_success))::numeric
    / nullif(count(*) filter (where is_qualified_attempt), 0),
    4
  ) as qualified_pass_rate,
  coalesce(sum(cost_usd), 0) as recorded_cost_usd,
  count(*) filter (where cost_usd is null)::int as missing_cost_count
from benchmark.v_trial_quality_flags
group by
  run_id,
  arm_run_id,
  phase,
  logical_mode,
  storage_mode,
  suite_id,
  arm_id,
  run_label;

create or replace view benchmark.v_suite_arm_quality_summary as
select
  phase,
  logical_mode,
  storage_mode,
  suite_id,
  arm_id,
  count(distinct run_label)::int as arm_run_count,
  count(*)::int as trial_count,
  count(*) filter (where is_success)::int as success_count,
  round(
    (count(*) filter (where is_success))::numeric / nullif(count(*), 0),
    4
  ) as raw_pass_rate,
  count(*) filter (where quality_flag = 'suspect_noop_zero_token')::int as suspect_noop_count,
  count(*) filter (where quality_flag in ('exception', 'exception_with_success'))::int as exception_count,
  count(*) filter (where quality_flag = 'normal_failed_trial')::int as normal_failed_count,
  count(*) filter (where is_qualified_attempt)::int as qualified_trial_count,
  count(*) filter (where is_qualified_attempt and is_success)::int as qualified_success_count,
  round(
    (count(*) filter (where is_qualified_attempt and is_success))::numeric
    / nullif(count(*) filter (where is_qualified_attempt), 0),
    4
  ) as qualified_pass_rate,
  coalesce(sum(cost_usd), 0) as recorded_cost_usd,
  count(*) filter (where cost_usd is null)::int as missing_cost_count
from benchmark.v_trial_quality_flags
group by
  phase,
  logical_mode,
  storage_mode,
  suite_id,
  arm_id;
