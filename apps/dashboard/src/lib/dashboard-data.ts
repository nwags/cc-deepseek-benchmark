import { queryRows } from "./db";

export type OverviewRow = {
  run_count: number;
  trial_count: number;
  artifact_count: number;
  cost_usd: number;
  completed_runs: number;
  noncompleted_runs: number;
};

export type ModeStatusRow = {
  phase: string;
  mode: string;
  status: string;
  run_count: number;
  trial_count: number;
  artifact_count: number;
  cost_usd: number;
};

export type ArmRow = {
  arm_id: string;
  provider_family: string | null;
  backend_model: string | null;
  router_model: string | null;
  run_count: number;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  trial_cost_usd: number | null;
  median_runtime_seconds: number | null;
};

export type TaskRow = {
  task_id: string;
  task_name: string;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number | null;
};

export type RecentRunRow = {
  run_label: string;
  mode: string;
  status: string;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  trial_cost_usd: number;
  artifact_count: number;
  r2_artifact_count: number;
};

export async function getOverview(): Promise<OverviewRow> {
  const rows = await queryRows<OverviewRow>(`
    select
      count(*)::int as run_count,
      coalesce(sum(trial_count), 0)::int as trial_count,
      coalesce(sum(artifact_count), 0)::int as artifact_count,
      coalesce(sum(trial_cost_usd), 0)::float8 as cost_usd,
      count(*) filter (where status = 'completed')::int as completed_runs,
      count(*) filter (where status <> 'completed')::int as noncompleted_runs
    from benchmark.v_dashboard_runs
    where phase = 'phase3'
  `);

  return rows[0];
}

export async function getModeStatusRows(): Promise<ModeStatusRow[]> {
  return queryRows<ModeStatusRow>(`
    select
      phase,
      mode,
      status,
      count(*)::int as run_count,
      coalesce(sum(trial_count), 0)::int as trial_count,
      coalesce(sum(artifact_count), 0)::int as artifact_count,
      coalesce(sum(trial_cost_usd), 0)::float8 as cost_usd
    from benchmark.v_dashboard_runs
    where phase = 'phase3'
    group by phase, mode, status
    order by mode, status
  `);
}

export async function getArmRows(): Promise<ArmRow[]> {
  return queryRows<ArmRow>(`
    select
      arm_id,
      provider_family,
      backend_model,
      router_model,
      run_count::int,
      trial_count::int,
      success_count::int,
      pass_rate::float8,
      trial_cost_usd::float8,
      median_runtime_seconds::float8
    from benchmark.v_dashboard_arms
    where run_count > 0
    order by arm_id
  `);
}

export async function getTaskRows(): Promise<TaskRow[]> {
  return queryRows<TaskRow>(`
    select
      task_id,
      task_name,
      trial_count::int,
      success_count::int,
      pass_rate::float8,
      median_runtime_seconds::float8,
      trial_cost_usd::float8
    from benchmark.v_dashboard_tasks
    where trial_count > 0
    order by task_name
  `);
}

export async function getRecentRuns(): Promise<RecentRunRow[]> {
  return queryRows<RecentRunRow>(`
    select
      run_label,
      mode,
      status,
      trial_count::int,
      success_count::int,
      pass_rate::float8,
      trial_cost_usd::float8,
      artifact_count::int,
      r2_artifact_count::int
    from benchmark.v_dashboard_runs
    where phase = 'phase3'
    order by created_at desc, run_label
    limit 12
  `);
}
