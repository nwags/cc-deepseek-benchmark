import { queryRows } from "./db";

export type OverviewRow = {
  run_count: number;
  trial_count: number;
  artifact_count: number;
  cost_usd: number;
  cost_row_count: number;
  missing_cost_count: number;
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
  cost_row_count: number;
  missing_cost_count: number;
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
  cost_row_count: number;
  missing_cost_count: number;
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
  cost_row_count: number;
  missing_cost_count: number;
};

export type RecentRunRow = {
  run_label: string;
  mode: string;
  status: string;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  trial_cost_usd: number;
  cost_row_count: number;
  missing_cost_count: number;
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
      coalesce(sum(cost_row_count), 0)::int as cost_row_count,
      coalesce(sum(missing_cost_count), 0)::int as missing_cost_count,
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
      coalesce(sum(trial_cost_usd), 0)::float8 as cost_usd,
      coalesce(sum(cost_row_count), 0)::int as cost_row_count,
      coalesce(sum(missing_cost_count), 0)::int as missing_cost_count
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
      cost_row_count::int,
      missing_cost_count::int,
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
      trial_cost_usd::float8,
      cost_row_count::int,
      missing_cost_count::int
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
      cost_row_count::int,
      missing_cost_count::int,
      artifact_count::int,
      r2_artifact_count::int
    from benchmark.v_dashboard_runs
    where phase = 'phase3'
    order by created_at desc, run_label
    limit 12
  `);
}

export type RunDetailRow = {
  run_id: string;
  phase: string;
  mode: string;
  run_label: string;
  git_commit: string | null;
  branch: string | null;
  runner_name: string | null;
  runner_provider: string | null;
  runner_region: string | null;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  trial_count: number;
  success_count: number;
  failure_count: number;
  pass_rate: number | null;
  avg_runtime_seconds: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number;
  cost_row_count: number;
  missing_cost_count: number;
  input_tokens: number;
  cache_tokens: number;
  output_tokens: number;
  artifact_count: number;
  artifact_size_bytes: number;
  r2_artifact_count: number;
  audit_count: number;
  audit_pass_count: number;
  audit_nonpass_count: number;
  websearch_events: number;
  webfetch_events: number;
  forbidden_tools_available: number;
};

export type RunTrialRow = {
  task_id: string;
  arm_id: string;
  reward: number | null;
  runtime_seconds: number | null;
  cost_usd: number | null;
  input_tokens: number | null;
  cache_tokens: number | null;
  output_tokens: number | null;
};

export type RunArtifactRow = {
  artifact_path: string;
  artifact_kind: string | null;
  size_bytes: number | null;
  r2_uri: string | null;
};

export async function getRunDetail(runLabel: string): Promise<RunDetailRow | null> {
  const rows = await queryRows<RunDetailRow>(
    `
      select
        run_id::text,
        phase,
        mode,
        run_label,
        git_commit,
        branch,
        runner_name,
        runner_provider,
        runner_region,
        started_at::text,
        finished_at::text,
        status,
        trial_count::int,
        success_count::int,
        failure_count::int,
        pass_rate::float8,
        avg_runtime_seconds::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int,
        input_tokens::int,
        cache_tokens::int,
        output_tokens::int,
        artifact_count::int,
        artifact_size_bytes::int,
        r2_artifact_count::int,
        audit_count::int,
        audit_pass_count::int,
        audit_nonpass_count::int,
        websearch_events::int,
        webfetch_events::int,
        forbidden_tools_available::int
      from benchmark.v_dashboard_runs
      where phase = 'phase3'
        and run_label = $1
      limit 1
    `,
    [runLabel]
  );

  return rows[0] ?? null;
}

export async function getRunTrials(runId: string): Promise<RunTrialRow[]> {
  return queryRows<RunTrialRow>(
    `
      select
        task_id,
        arm_id,
        reward::float8,
        runtime_seconds::float8,
        cost_usd::float8,
        input_tokens::int,
        cache_tokens::int,
        output_tokens::int
      from benchmark.benchmark_trials
      where run_id = $1::uuid
      order by task_id, arm_id
    `,
    [runId]
  );
}

export async function getRunArtifacts(runId: string): Promise<RunArtifactRow[]> {
  return queryRows<RunArtifactRow>(
    `
      select
        coalesce(local_path, r2_uri, github_uri, id::text) as artifact_path,
        artifact_type as artifact_kind,
        size_bytes::int,
        r2_uri
      from benchmark.benchmark_artifacts
      where run_id = $1::uuid
      order by artifact_path
      limit 100
    `,
    [runId]
  );
}
