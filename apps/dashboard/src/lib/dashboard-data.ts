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
    with valid_runs as (
      select distinct run_id
      from benchmark.v_valid_arm_run_summary
      where suite_id like 'phase3-%'
    )
    select
      count(*)::int as run_count,
      coalesce(sum(trial_count), 0)::int as trial_count,
      coalesce(sum(artifact_count), 0)::int as artifact_count,
      coalesce(sum(trial_cost_usd), 0)::float8 as cost_usd,
      coalesce(sum(cost_row_count), 0)::int as cost_row_count,
      coalesce(sum(missing_cost_count), 0)::int as missing_cost_count,
      count(*) filter (where status = 'completed')::int as completed_runs,
      count(*) filter (where status <> 'completed')::int as noncompleted_runs
    from benchmark.v_dashboard_runs runs
    join valid_runs
      on valid_runs.run_id = runs.run_id
    where runs.phase = 'phase3'
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

export type ArtifactBrowserRow = {
  artifact_id: string;
  run_id: string;
  run_label: string;
  arm_run_id: string | null;
  suite_id: string | null;
  logical_mode: string | null;
  storage_mode: string | null;
  arm_id: string | null;
  trial_id: string | null;
  task_id: string | null;
  attempt_index: number | null;
  reward: number | string | null;
  quality_flag: string | null;
  exception_type: string | null;
  exception_summary: string | null;
  artifact_path: string;
  artifact_type: string | null;
  r2_uri: string | null;
  size_bytes: number | null;
  created_at: string | null;
};

export type ArtifactBrowserFilters = {
  suite_id?: string;
  arm_id?: string;
  run_label?: string;
  task_id?: string;
  quality_flag?: string;
  exception_type?: string;
  artifact_type?: string;
  artifact_kind?: string;
  q?: string;
  limit?: number;
};

export type ArtifactDetailRow = {
  artifact_id: string;
  run_id: string;
  trial_id: string | null;
  artifact_type: string | null;
  local_path: string | null;
  r2_uri: string | null;
  github_uri: string | null;
  sha256: string | null;
  size_bytes: number | null;
  created_at: string | null;
  retention_class: string | null;
  notes: string | null;
  run_label: string;
  suite_id: string | null;
  logical_mode: string | null;
  storage_mode: string | null;
  arm_id: string | null;
  task_id: string | null;
  attempt_index: number | null;
  reward: number | string | null;
  runtime_seconds: number | string | null;
  cost_usd: number | string | null;
  input_tokens: number | string | null;
  cache_tokens: number | string | null;
  output_tokens: number | string | null;
  quality_flag: string | null;
  exception_type: string | null;
  exception_summary: string | null;
  invalid_reason: string | null;
  invalid_provider_run_id: string | null;
  invalidated_at: string | null;
  invalidated_by: string | null;
  invalid_raw_metadata: Record<string, unknown> | null;
};

export type TrialEvidenceRow = {
  trial_id: string;
  run_id: string;
  run_label: string;
  arm_run_id: string | null;
  suite_id: string | null;
  logical_mode: string | null;
  storage_mode: string | null;
  arm_id: string | null;
  task_id: string | null;
  task_name: string | null;
  attempt_index: number | null;
  reward: number | string | null;
  runtime_seconds: number | string | null;
  cost_usd: number | string | null;
  input_tokens: number | string | null;
  cache_tokens: number | string | null;
  output_tokens: number | string | null;
  result_local_path: string | null;
  result_artifact_uri: string | null;
  quality_flag: string | null;
  exception_type: string | null;
  exception_summary: string | null;
  invalid_reason: string | null;
  invalid_provider_run_id: string | null;
  invalidated_at: string | null;
  invalidated_by: string | null;
  invalid_raw_metadata: Record<string, unknown> | null;
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

export async function getArtifactBrowserRows(
  filters: ArtifactBrowserFilters = {}
): Promise<ArtifactBrowserRow[]> {
  const conditions = ["r.phase = 'phase3'"];
  const params: unknown[] = [];
  const limit = Math.min(Math.max(filters.limit ?? 250, 1), 1000);

  function addCondition(sql: string, value: string | undefined) {
    if (!value) return;
    params.push(value);
    conditions.push(sql.replace("$param", `$${params.length}`));
  }

  addCondition("coalesce(q.suite_id, ar.suite_id) = $param", filters.suite_id);
  addCondition("coalesce(q.arm_id, t.arm_id, ar.arm_id) = $param", filters.arm_id);
  addCondition("r.run_label = $param", filters.run_label);
  addCondition("coalesce(q.task_id, t.task_id) = $param", filters.task_id);
  addCondition("q.quality_flag = $param", filters.quality_flag);
  addCondition("coalesce(q.exception_type, t.exception_type) = $param", filters.exception_type);
  addCondition("art.artifact_type = $param", filters.artifact_type ?? filters.artifact_kind);

  if (filters.q) {
    params.push(`%${filters.q}%`);
    const placeholder = `$${params.length}`;
    conditions.push(`(
      art.local_path ilike ${placeholder}
      or art.r2_uri ilike ${placeholder}
      or art.github_uri ilike ${placeholder}
      or art.notes ilike ${placeholder}
      or r.run_label ilike ${placeholder}
      or t.task_id ilike ${placeholder}
      or t.exception_summary ilike ${placeholder}
    )`);
  }

  params.push(limit);

  return queryRows<ArtifactBrowserRow>(
    `
      select
        art.id::text as artifact_id,
        r.id::text as run_id,
        r.run_label,
        coalesce(t.arm_run_id, ar.id)::text as arm_run_id,
        coalesce(q.suite_id, ar.suite_id) as suite_id,
        coalesce(q.logical_mode, ar.logical_mode) as logical_mode,
        coalesce(q.storage_mode, ar.storage_mode, r.mode) as storage_mode,
        coalesce(q.arm_id, t.arm_id, ar.arm_id) as arm_id,
        t.id::text as trial_id,
        coalesce(q.task_id, t.task_id) as task_id,
        coalesce(q.attempt_index, t.attempt_index)::int as attempt_index,
        coalesce(q.reward, t.reward) as reward,
        q.quality_flag,
        coalesce(q.exception_type, t.exception_type) as exception_type,
        coalesce(q.exception_summary, t.exception_summary) as exception_summary,
        coalesce(art.local_path, art.r2_uri, art.github_uri, art.id::text) as artifact_path,
        art.artifact_type,
        art.r2_uri,
        art.size_bytes::int,
        art.created_at::text
      from benchmark.benchmark_artifacts art
      join benchmark.benchmark_runs r
        on r.id = art.run_id
      left join benchmark.benchmark_trials t
        on t.id = art.trial_id
      left join lateral (
        select ar1.*
        from benchmark.benchmark_arm_runs ar1
        where ar1.id = t.arm_run_id
           or (t.arm_run_id is null and ar1.run_id = art.run_id)
        order by
          case when ar1.id = t.arm_run_id then 0 else 1 end,
          ar1.created_at desc
        limit 1
      ) ar on true
      left join benchmark.v_trial_quality_flags q
        on q.trial_id = t.id
      where ${conditions.join("\n        and ")}
      order by
        r.started_at desc nulls last,
        r.run_label desc,
        coalesce(q.task_id, t.task_id) nulls last,
        coalesce(q.attempt_index, t.attempt_index) nulls last,
        art.artifact_type,
        artifact_path
      limit $${params.length}
    `,
    params
  );
}

const artifactDetailSelect = `
  select
    art.id::text as artifact_id,
    r.id::text as run_id,
    art.trial_id::text,
    art.artifact_type,
    art.local_path,
    art.r2_uri,
    art.github_uri,
    art.sha256,
    art.size_bytes::int,
    art.created_at::text,
    art.retention_class,
    art.notes,
    r.run_label,
    coalesce(q.suite_id, ar.suite_id) as suite_id,
    coalesce(q.logical_mode, ar.logical_mode) as logical_mode,
    coalesce(q.storage_mode, ar.storage_mode, r.mode) as storage_mode,
    coalesce(q.arm_id, t.arm_id, ar.arm_id) as arm_id,
    coalesce(q.task_id, t.task_id) as task_id,
    coalesce(q.attempt_index, t.attempt_index)::int as attempt_index,
    coalesce(q.reward, t.reward) as reward,
    t.runtime_seconds,
    t.cost_usd,
    t.input_tokens,
    t.cache_tokens,
    t.output_tokens,
    q.quality_flag,
    coalesce(q.exception_type, t.exception_type) as exception_type,
    coalesce(q.exception_summary, t.exception_summary) as exception_summary,
    invalid.reason as invalid_reason,
    invalid.provider_run_id as invalid_provider_run_id,
    invalid.invalidated_at::text,
    invalid.invalidated_by,
    invalid.raw_metadata as invalid_raw_metadata
  from benchmark.benchmark_artifacts art
  join benchmark.benchmark_runs r
    on r.id = art.run_id
  left join benchmark.benchmark_trials t
    on t.id = art.trial_id
  left join lateral (
    select ar1.*
    from benchmark.benchmark_arm_runs ar1
    where ar1.id = t.arm_run_id
       or (t.arm_run_id is null and ar1.run_id = art.run_id)
    order by
      case when ar1.id = t.arm_run_id then 0 else 1 end,
      ar1.created_at desc
    limit 1
  ) ar on true
  left join benchmark.v_trial_quality_flags q
    on q.trial_id = t.id
  left join benchmark.benchmark_invalid_arm_runs invalid
    on invalid.suite_id = coalesce(q.suite_id, ar.suite_id)
   and invalid.arm_id = coalesce(q.arm_id, t.arm_id, ar.arm_id)
   and invalid.run_label = r.run_label
`;

export async function getArtifactDetail(artifactId: string): Promise<ArtifactDetailRow | null> {
  const rows = await queryRows<ArtifactDetailRow>(
    `
      ${artifactDetailSelect}
      where art.id = $1::uuid
        and r.phase = 'phase3'
      limit 1
    `,
    [artifactId]
  );

  return rows[0] ?? null;
}

export async function getArtifactsForTrial(trialId: string): Promise<ArtifactDetailRow[]> {
  return queryRows<ArtifactDetailRow>(
    `
      ${artifactDetailSelect}
      where art.trial_id = $1::uuid
        and r.phase = 'phase3'
      order by art.artifact_type, coalesce(art.local_path, art.r2_uri, art.github_uri, art.id::text)
    `,
    [trialId]
  );
}

export async function getTrialEvidence(trialId: string): Promise<TrialEvidenceRow | null> {
  const rows = await queryRows<TrialEvidenceRow>(
    `
      select
        t.id::text as trial_id,
        r.id::text as run_id,
        r.run_label,
        t.arm_run_id::text,
        q.suite_id,
        q.logical_mode,
        q.storage_mode,
        q.arm_id,
        q.task_id,
        task.task_name,
        q.attempt_index::int,
        q.reward,
        q.runtime_seconds,
        q.cost_usd,
        q.input_tokens,
        q.cache_tokens,
        q.output_tokens,
        t.result_local_path,
        t.result_artifact_uri,
        q.quality_flag,
        q.exception_type,
        q.exception_summary,
        invalid.reason as invalid_reason,
        invalid.provider_run_id as invalid_provider_run_id,
        invalid.invalidated_at::text,
        invalid.invalidated_by,
        invalid.raw_metadata as invalid_raw_metadata
      from benchmark.benchmark_trials t
      join benchmark.benchmark_runs r
        on r.id = t.run_id
      left join benchmark.v_trial_quality_flags q
        on q.trial_id = t.id
      left join benchmark.benchmark_tasks task
        on task.task_id = coalesce(q.task_id, t.task_id)
      left join benchmark.benchmark_invalid_arm_runs invalid
        on invalid.suite_id = q.suite_id
       and invalid.arm_id = q.arm_id
       and invalid.run_label = r.run_label
      where t.id = $1::uuid
        and r.phase = 'phase3'
      limit 1
    `,
    [trialId]
  );

  return rows[0] ?? null;
}


export type EvalSuiteRow = {
  suite_id: string;
  display_name: string;
  description: string | null;
  suite_type: string;
  benchmark: string;
  benchmark_version: string | null;
  phase: string;
  version: string | null;
  active: boolean;
  suite_items: number;
  arm_run_count: number;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  trial_cost_usd: number | null;
};

export type SuiteArmComparisonRow = {
  suite_id: string;
  suite_display_name: string | null;
  suite_type: string | null;
  arm_id: string;
  trial_count: number;
  task_count: number;
  success_count: number;
  pass_rate: number | null;
  mean_reward: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number | null;
  cost_row_count: number;
  missing_cost_count: number;
};

export type ArmRunSummaryRow = {
  arm_run_id: string;
  run_id: string;
  run_label: string;
  arm_id: string;
  provider_family: string | null;
  backend_model: string | null;
  router_model: string | null;
  suite_id: string | null;
  suite_display_name: string | null;
  suite_type: string | null;
  logical_mode: string;
  storage_mode: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  trial_count: number;
  success_count: number;
  failure_count: number;
  pass_rate: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number;
  cost_row_count: number;
  missing_cost_count: number;
  input_tokens: number | string;
  cache_tokens: number | string;
  output_tokens: number | string;
  artifact_count: number;
  r2_artifact_count: number;
};

export type InvalidArmRunRow = {
  suite_id: string;
  arm_id: string;
  run_label: string;
  provider_run_id: string | null;
  reason: string;
  invalidated_at: string | null;
  invalidated_by: string | null;
  raw_metadata: Record<string, unknown> | null;
};

export type ArmRunTrialDetailRow = {
  trial_id: string;
  task_id: string;
  task_name: string | null;
  attempt_index: number | null;
  reward: number | null;
  exception_type: string | null;
  runtime_seconds: number | null;
  cost_usd: number | null;
  input_tokens: number | string | null;
  cache_tokens: number | string | null;
  output_tokens: number | string | null;
  result_local_path: string | null;
};

export type EvalSummaryRow = {
  task_id: string;
  task_name: string | null;
  arm_count: number;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number | null;
};

export type EvalArmComparisonRow = {
  task_id: string;
  task_name: string | null;
  arm_id: string;
  suite_id: string | null;
  logical_mode: string | null;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  mean_reward: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number | null;
  cost_row_count: number;
  missing_cost_count: number;
};

export async function getEvalSuites(): Promise<EvalSuiteRow[]> {
  return queryRows<EvalSuiteRow>(`
    with item_summary as (
      select suite_id, count(*)::int as suite_items
      from benchmark.benchmark_eval_suite_items
      group by suite_id
    ),
    arm_summary as (
      select
        suite_id,
        count(distinct arm_id)::int as arm_run_count,
        coalesce(sum(trial_count), 0)::int as trial_count,
        coalesce(sum(success_count), 0)::int as success_count,
        case
          when coalesce(sum(trial_count), 0) = 0 then null
          else sum(success_count)::numeric / sum(trial_count)::numeric
        end as pass_rate,
        sum(trial_cost_usd)::float8 as trial_cost_usd
      from benchmark.v_valid_suite_arm_comparison
      group by suite_id
    )
    select
      s.suite_id,
      s.display_name,
      s.description,
      s.suite_type,
      s.benchmark,
      s.benchmark_version,
      s.phase,
      s.version,
      s.active,
      coalesce(i.suite_items, 0)::int as suite_items,
      coalesce(a.arm_run_count, 0)::int as arm_run_count,
      coalesce(a.trial_count, 0)::int as trial_count,
      coalesce(a.success_count, 0)::int as success_count,
      a.pass_rate::float8,
      a.trial_cost_usd::float8
    from benchmark.benchmark_eval_suites s
    left join item_summary i on i.suite_id = s.suite_id
    left join arm_summary a on a.suite_id = s.suite_id
    where s.phase = 'phase3'
    order by
      case s.suite_type when 'canary' then 1 when 'smoke' then 2 when 'full' then 3 else 9 end,
      s.suite_id
  `);
}

export async function getSuiteArmComparison(suiteId: string): Promise<SuiteArmComparisonRow[]> {
  return queryRows<SuiteArmComparisonRow>(
    `
      select
        suite_id,
        suite_display_name,
        suite_type,
        arm_id,
        trial_count::int,
        task_count::int,
        success_count::int,
        pass_rate::float8,
        mean_reward::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int
      from benchmark.v_valid_suite_arm_comparison
      where suite_id = $1
      order by pass_rate desc nulls last, arm_id
    `,
    [suiteId]
  );
}

export async function getArmRunRows(limit = 100): Promise<ArmRunSummaryRow[]> {
  return queryRows<ArmRunSummaryRow>(
    `
      select
        arm_run_id::text,
        run_id::text,
        run_label,
        arm_id,
        provider_family,
        backend_model,
        router_model,
        suite_id,
        suite_display_name,
        suite_type,
        logical_mode,
        storage_mode,
        status,
        started_at::text,
        finished_at::text,
        trial_count::int,
        success_count::int,
        failure_count::int,
        pass_rate::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int,
        input_tokens::text,
        cache_tokens::text,
        output_tokens::text,
        artifact_count::int,
        r2_artifact_count::int
      from benchmark.v_arm_run_summary
      order by started_at desc nulls last, run_label desc, arm_id
      limit $1
    `,
    [limit]
  );
}


export async function getValidSuiteArmRunRows(suiteId: string, limit = 100): Promise<ArmRunSummaryRow[]> {
  return queryRows<ArmRunSummaryRow>(
    `
      select
        arm_run_id::text,
        run_id::text,
        run_label,
        arm_id,
        provider_family,
        backend_model,
        router_model,
        suite_id,
        suite_display_name,
        suite_type,
        logical_mode,
        storage_mode,
        status,
        started_at::text,
        finished_at::text,
        trial_count::int,
        success_count::int,
        failure_count::int,
        pass_rate::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int,
        input_tokens::text,
        cache_tokens::text,
        output_tokens::text,
        artifact_count::int,
        r2_artifact_count::int
      from benchmark.v_valid_arm_run_summary
      where suite_id = $1
      order by started_at desc nulls last, run_label desc, arm_id
      limit $2
    `,
    [suiteId, limit]
  );
}

export async function getInvalidArmRunRows(): Promise<InvalidArmRunRow[]> {
  return queryRows<InvalidArmRunRow>(`
    select
      suite_id,
      arm_id,
      run_label,
      provider_run_id,
      reason,
      invalidated_at::text,
      invalidated_by,
      raw_metadata
    from benchmark.benchmark_invalid_arm_runs
    order by suite_id, arm_id, run_label
  `);
}

export async function getInvalidArmRunRowsByRunLabels(runLabels: string[]): Promise<InvalidArmRunRow[]> {
  if (runLabels.length === 0) return [];

  return queryRows<InvalidArmRunRow>(
    `
      select
        suite_id,
        arm_id,
        run_label,
        provider_run_id,
        reason,
        invalidated_at::text,
        invalidated_by,
        raw_metadata
      from benchmark.benchmark_invalid_arm_runs
      where run_label = any($1::text[])
      order by suite_id, arm_id, run_label
    `,
    [runLabels]
  );
}

export async function getArmRunDetail(armRunId: string): Promise<ArmRunSummaryRow | null> {
  const rows = await queryRows<ArmRunSummaryRow>(
    `
      select
        arm_run_id::text,
        run_id::text,
        run_label,
        arm_id,
        provider_family,
        backend_model,
        router_model,
        suite_id,
        suite_display_name,
        suite_type,
        logical_mode,
        storage_mode,
        status,
        started_at::text,
        finished_at::text,
        trial_count::int,
        success_count::int,
        failure_count::int,
        pass_rate::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int,
        input_tokens::text,
        cache_tokens::text,
        output_tokens::text,
        artifact_count::int,
        r2_artifact_count::int
      from benchmark.v_arm_run_summary
      where arm_run_id = $1::uuid
      limit 1
    `,
    [armRunId]
  );

  return rows[0] ?? null;
}

export async function getArmRunTrials(armRunId: string): Promise<ArmRunTrialDetailRow[]> {
  return queryRows<ArmRunTrialDetailRow>(
    `
      select
        trial_id::text,
        task_id,
        task_name,
        attempt_index::int,
        reward::float8,
        exception_type,
        runtime_seconds::float8,
        cost_usd::float8,
        input_tokens::text,
        cache_tokens::text,
        output_tokens::text,
        result_local_path
      from benchmark.v_arm_run_trials
      where arm_run_id = $1::uuid
      order by task_name, attempt_index
    `,
    [armRunId]
  );
}

export async function getArmRunArtifacts(armRunId: string): Promise<RunArtifactRow[]> {
  return queryRows<RunArtifactRow>(
    `
      select
        coalesce(art.local_path, art.r2_uri, art.github_uri, art.id::text) as artifact_path,
        art.artifact_type as artifact_kind,
        art.size_bytes::int,
        art.r2_uri
      from benchmark.benchmark_arm_runs ar
      join benchmark.benchmark_artifacts art
        on art.run_id = ar.run_id
      left join benchmark.benchmark_trials t
        on t.id = art.trial_id
      where ar.id = $1::uuid
        and (
          art.trial_id is null
          or t.arm_run_id = ar.id
        )
      order by artifact_path
      limit 200
    `,
    [armRunId]
  );
}

export async function getEvalRows(): Promise<EvalSummaryRow[]> {
  return queryRows<EvalSummaryRow>(`
    select
      task_id,
      max(task_name) as task_name,
      count(distinct arm_id)::int as arm_count,
      coalesce(sum(trial_count), 0)::int as trial_count,
      coalesce(sum(success_count), 0)::int as success_count,
      case
        when coalesce(sum(trial_count), 0) = 0 then null
        else sum(success_count)::numeric / sum(trial_count)::numeric
      end::float8 as pass_rate,
      percentile_cont(0.5) within group (order by median_runtime_seconds)::float8 as median_runtime_seconds,
      sum(trial_cost_usd)::float8 as trial_cost_usd
    from benchmark.v_valid_eval_arm_comparison
    group by task_id
    order by task_name
  `);
}

export async function getEvalArmComparison(taskId: string): Promise<EvalArmComparisonRow[]> {
  return queryRows<EvalArmComparisonRow>(
    `
      select
        task_id,
        task_name,
        arm_id,
        suite_id,
        logical_mode,
        trial_count::int,
        success_count::int,
        pass_rate::float8,
        mean_reward::float8,
        median_runtime_seconds::float8,
        trial_cost_usd::float8,
        cost_row_count::int,
        missing_cost_count::int
      from benchmark.v_valid_eval_arm_comparison
      where task_id = $1
      order by pass_rate desc nulls last, arm_id, suite_id
    `,
    [taskId]
  );
}


export type SuiteTaskDifficultyRow = {
  suite_id: string;
  task_id: string;
  task_name: string | null;
  arm_count: number;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  median_runtime_seconds: number | null;
  trial_cost_usd: number | null;
};

export async function getSuiteTaskDifficulty(suiteId: string, limit = 20): Promise<SuiteTaskDifficultyRow[]> {
  return queryRows<SuiteTaskDifficultyRow>(
    `
      select
        suite_id,
        task_id,
        max(task_name) as task_name,
        count(distinct arm_id)::int as arm_count,
        coalesce(sum(trial_count), 0)::int as trial_count,
        coalesce(sum(success_count), 0)::int as success_count,
        case
          when coalesce(sum(trial_count), 0) = 0 then null
          else sum(success_count)::numeric / sum(trial_count)::numeric
        end::float8 as pass_rate,
        percentile_cont(0.5) within group (order by median_runtime_seconds)::float8 as median_runtime_seconds,
        sum(trial_cost_usd)::float8 as trial_cost_usd
      from benchmark.v_valid_eval_arm_comparison
      where suite_id = $1
      group by suite_id, task_id
      order by pass_rate asc nulls last, trial_count desc, task_id
      limit $2
    `,
    [suiteId, limit]
  );
}

export type SuiteHeatmapCellRow = {
  suite_id: string;
  task_id: string;
  task_name: string | null;
  arm_id: string;
  trial_count: number;
  success_count: number;
  pass_rate: number | null;
  task_trial_count: number;
  task_success_count: number;
  task_pass_rate: number | null;
};

export async function getSuiteHeatmapCells(suiteId: string): Promise<SuiteHeatmapCellRow[]> {
  return queryRows<SuiteHeatmapCellRow>(
    `
      with task_summary as (
        select
          suite_id,
          task_id,
          coalesce(sum(trial_count), 0)::int as task_trial_count,
          coalesce(sum(success_count), 0)::int as task_success_count,
          case
            when coalesce(sum(trial_count), 0) = 0 then null
            else sum(success_count)::numeric / sum(trial_count)::numeric
          end as task_pass_rate
        from benchmark.v_valid_eval_arm_comparison
        where suite_id = $1
        group by suite_id, task_id
      )
      select
        e.suite_id,
        e.task_id,
        e.task_name,
        e.arm_id,
        e.trial_count::int,
        e.success_count::int,
        e.pass_rate::float8,
        ts.task_trial_count::int,
        ts.task_success_count::int,
        ts.task_pass_rate::float8
      from benchmark.v_valid_eval_arm_comparison e
      join task_summary ts
        on ts.suite_id = e.suite_id
       and ts.task_id = e.task_id
      where e.suite_id = $1
      order by ts.task_pass_rate asc nulls last, e.task_id, e.arm_id
    `,
    [suiteId]
  );
}

export type ArmRunQualitySummaryRow = {
  phase: string;
  logical_mode: string | null;
  storage_mode: string | null;
  suite_id: string | null;
  arm_id: string;
  run_label: string;
  trial_count: number;
  success_count: number;
  raw_pass_rate: number | null;
  suspect_noop_count: number;
  exception_count: number;
  normal_failed_count: number;
  qualified_trial_count: number;
  qualified_success_count: number;
  qualified_pass_rate: number | null;
  recorded_cost_usd: number | string | null;
  missing_cost_count: number;
};

export type SuspectTrialRow = {
  arm_id: string;
  logical_mode: string | null;
  storage_mode: string | null;
  suite_id: string | null;
  run_label: string;
  task_id: string;
  attempt_index: number | null;
  reward: number | string | null;
  runtime_seconds: number | string | null;
  cost_usd: number | string | null;
  input_tokens: number | string | null;
  output_tokens: number | string | null;
  exception_type: string | null;
  exception_summary: string | null;
};

export type SuspectNoopTrialFilters = {
  suite_id?: string;
  arm_id?: string;
  run_label?: string;
  task_id?: string;
};

export async function getArmRunQualitySummaryRows(limit = 100): Promise<ArmRunQualitySummaryRow[]> {
  return queryRows<ArmRunQualitySummaryRow>(
    `
      select
        phase,
        logical_mode,
        storage_mode,
        suite_id,
        arm_id,
        run_label,
        trial_count::int,
        success_count::int,
        raw_pass_rate::float8,
        suspect_noop_count::int,
        exception_count::int,
        normal_failed_count::int,
        qualified_trial_count::int,
        qualified_success_count::int,
        qualified_pass_rate::float8,
        recorded_cost_usd,
        missing_cost_count::int
      from benchmark.v_arm_run_quality_summary
      where phase = 'phase3'
      order by
        case logical_mode
          when 'full' then 1
          when 'smoke' then 2
          when 'canary' then 3
          else 4
        end,
        suspect_noop_count desc,
        exception_count desc,
        run_label
      limit $1
    `,
    [limit]
  );
}

export async function getSuspectNoopTrialRows(limit = 100): Promise<SuspectTrialRow[]> {
  return getSuspectNoopTrialRowsFiltered({}, limit);
}

export async function getSuspectNoopTrialRowsFiltered(
  filters: SuspectNoopTrialFilters = {},
  limit = 100
): Promise<SuspectTrialRow[]> {
  const conditions = ["phase = 'phase3'", "quality_flag = 'suspect_noop_zero_token'"];
  const params: unknown[] = [];

  for (const key of ["suite_id", "arm_id", "run_label", "task_id"] as const) {
    const value = filters[key];
    if (value) {
      params.push(value);
      conditions.push(`${key} = $${params.length}`);
    }
  }

  params.push(limit);

  return queryRows<SuspectTrialRow>(
    `
      select
        arm_id,
        logical_mode,
        storage_mode,
        suite_id,
        run_label,
        task_id,
        attempt_index::int,
        reward,
        runtime_seconds,
        cost_usd,
        input_tokens,
        output_tokens,
        exception_type,
        exception_summary
      from benchmark.v_trial_quality_flags
      where ${conditions.join("\n        and ")}
      order by logical_mode, arm_id, run_label, task_id, attempt_index nulls last
      limit $${params.length}
    `,
    params
  );
}

export async function getSuiteArmQualityRows(suiteId: string): Promise<ArmRunQualitySummaryRow[]> {
  return queryRows<ArmRunQualitySummaryRow>(
    `
      select
        phase,
        logical_mode,
        storage_mode,
        suite_id,
        arm_id,
        '' as run_label,
        trial_count::int,
        success_count::int,
        raw_pass_rate::float8,
        suspect_noop_count::int,
        exception_count::int,
        normal_failed_count::int,
        qualified_trial_count::int,
        qualified_success_count::int,
        qualified_pass_rate::float8,
        recorded_cost_usd,
        missing_cost_count::int
      from benchmark.v_valid_suite_arm_quality_summary
      where phase = 'phase3'
        and suite_id = $1
      order by raw_pass_rate desc nulls last, arm_id
    `,
    [suiteId]
  );
}

export async function getArmRunQualityByRunLabels(runLabels: string[]): Promise<ArmRunQualitySummaryRow[]> {
  if (runLabels.length === 0) return [];
  return queryRows<ArmRunQualitySummaryRow>(
    `
      select
        phase,
        logical_mode,
        storage_mode,
        suite_id,
        arm_id,
        run_label,
        trial_count::int,
        success_count::int,
        raw_pass_rate::float8,
        suspect_noop_count::int,
        exception_count::int,
        normal_failed_count::int,
        qualified_trial_count::int,
        qualified_success_count::int,
        qualified_pass_rate::float8,
        recorded_cost_usd,
        missing_cost_count::int
      from benchmark.v_arm_run_quality_summary
      where phase = 'phase3'
        and run_label = any($1::text[])
      order by run_label
    `,
    [runLabels]
  );
}

export async function getSuiteQualityTotals(suiteId: string): Promise<{
  suite_id: string;
  suspect_noop_count: number;
  affected_arm_count: number;
  affected_full_arm_count: number;
} | null> {
  const rows = await queryRows<{
    suite_id: string;
    suspect_noop_count: number;
    affected_arm_count: number;
    affected_full_arm_count: number;
  }>(
    `
      select
        suite_id,
        coalesce(sum(suspect_noop_count), 0)::int as suspect_noop_count,
        count(*) filter (where suspect_noop_count > 0)::int as affected_arm_count,
        count(*) filter (where logical_mode = 'full' and suspect_noop_count > 0)::int as affected_full_arm_count
      from benchmark.v_valid_suite_arm_quality_summary
      where phase = 'phase3'
        and suite_id = $1
      group by suite_id
    `,
    [suiteId]
  );
  return rows[0] ?? null;
}

export async function getOverallQualityTotals(): Promise<{
  suspect_noop_count: number;
  affected_arm_run_count: number;
  affected_full_arm_run_count: number;
} | null> {
  const rows = await queryRows<{
    suspect_noop_count: number;
    affected_arm_run_count: number;
    affected_full_arm_run_count: number;
  }>(
    `
      select
        coalesce(sum(suspect_noop_count), 0)::int as suspect_noop_count,
        count(*) filter (where suspect_noop_count > 0)::int as affected_arm_run_count,
        count(*) filter (where logical_mode = 'full' and suspect_noop_count > 0)::int as affected_full_arm_run_count
      from benchmark.v_arm_run_quality_summary
      where phase = 'phase3'
    `
  );
  return rows[0] ?? null;
}

export async function getRunLabelForArmRunId(armRunId: string): Promise<string | null> {
  const rows = await queryRows<{ run_label: string }>(
    `
      select r.run_label
      from benchmark.benchmark_arm_runs ar
      join benchmark.benchmark_runs r
        on r.id = ar.run_id
      where ar.id = $1
      limit 1
    `,
    [armRunId]
  );

  return rows[0]?.run_label ?? null;
}


export type AdjustedCostOverviewRow = {
  suite_id: string;
  trial_count: number;
  success_count: number;
  clean_success_count: number;
  exception_success_signal_count: number;
  failure_or_incomplete_count: number;
  recorded_cost_usd: number;
  adjusted_known_cost_usd: number;
  known_accounting_gap_usd: number;
  unresolved_cost_count: number;
  adjusted_clean_success_cost_usd: number;
  adjusted_exception_success_signal_cost_usd: number;
  adjusted_failure_or_incomplete_cost_usd: number;
  nonproductive_or_unclean_spend_share: number | null;
  failure_or_incomplete_spend_share: number | null;
};

export type AdjustedCostArmRow = {
  suite_id: string;
  arm_id: string;
  provider_family: string | null;
  backend_model: string | null;
  trial_count: number;
  success_count: number;
  clean_success_count: number;
  raw_pass_rate: number | null;
  recorded_cost_usd: number;
  adjusted_known_cost_usd: number;
  known_accounting_gap_usd: number;
  unresolved_cost_count: number;
  adjusted_failure_or_incomplete_cost_usd: number;
  nonproductive_or_unclean_spend_share: number | null;
  failure_or_incomplete_spend_share: number | null;
  adjusted_cost_per_clean_success: number | null;
  adjusted_cost_per_any_success: number | null;
  cost_sources_present: string | null;
  cost_confidence_present: string | null;
};

export type AdjustedOutcomeCostRow = {
  suite_id: string;
  outcome_bucket: string;
  trial_count: number;
  recorded_cost_usd: number;
  adjusted_known_cost_usd: number;
  known_accounting_gap_usd: number;
};

export async function getAdjustedCostOverview(suiteId: string): Promise<AdjustedCostOverviewRow> {
  const rows = await queryRows<AdjustedCostOverviewRow>(
    `
      select
        $1::text as suite_id,
        count(*)::int as trial_count,
        (count(*) filter (where outcome_bucket in ('clean_success', 'exception_with_success_signal')))::int as success_count,
        (count(*) filter (where outcome_bucket = 'clean_success'))::int as clean_success_count,
        (count(*) filter (where outcome_bucket = 'exception_with_success_signal'))::int as exception_success_signal_count,
        (count(*) filter (where outcome_bucket not in ('clean_success', 'exception_with_success_signal')))::int as failure_or_incomplete_count,
        coalesce(sum(recorded_cost_usd), 0::numeric)::float8 as recorded_cost_usd,
        coalesce(sum(adjusted_cost_usd), 0::numeric)::float8 as adjusted_known_cost_usd,
        (
          coalesce(sum(adjusted_cost_usd), 0::numeric)
          - coalesce(sum(recorded_cost_usd), 0::numeric)
        )::float8 as known_accounting_gap_usd,
        (count(*) filter (where adjusted_cost_usd is null))::int as unresolved_cost_count,
        coalesce(sum(adjusted_cost_usd) filter (where outcome_bucket = 'clean_success'), 0::numeric)::float8
          as adjusted_clean_success_cost_usd,
        coalesce(sum(adjusted_cost_usd) filter (where outcome_bucket = 'exception_with_success_signal'), 0::numeric)::float8
          as adjusted_exception_success_signal_cost_usd,
        coalesce(sum(adjusted_cost_usd) filter (
          where outcome_bucket not in ('clean_success', 'exception_with_success_signal')
        ), 0::numeric)::float8 as adjusted_failure_or_incomplete_cost_usd,
        case
          when coalesce(sum(adjusted_cost_usd), 0::numeric) = 0 then null
          else (
            coalesce(sum(adjusted_cost_usd) filter (where outcome_bucket <> 'clean_success'), 0::numeric)
            / sum(adjusted_cost_usd)
          )::float8
        end as nonproductive_or_unclean_spend_share,
        case
          when coalesce(sum(adjusted_cost_usd), 0::numeric) = 0 then null
          else (
            coalesce(sum(adjusted_cost_usd) filter (
              where outcome_bucket not in ('clean_success', 'exception_with_success_signal')
            ), 0::numeric) / sum(adjusted_cost_usd)
          )::float8
        end as failure_or_incomplete_spend_share
      from benchmark.v_trial_adjusted_cost_coverage
      where suite_id = $1
    `,
    [suiteId]
  );

  return rows[0];
}

export async function getAdjustedCostArmRows(suiteId: string): Promise<AdjustedCostArmRow[]> {
  return queryRows<AdjustedCostArmRow>(
    `
      select
        f.suite_id,
        f.arm_id,
        a.provider_family,
        a.backend_model,
        f.trial_count::int,
        f.success_count::int,
        f.clean_success_count::int,
        f.raw_pass_rate::float8,
        f.recorded_cost_usd::float8,
        f.adjusted_known_cost_usd::float8,
        f.known_accounting_gap_usd::float8,
        f.unresolved_cost_count::int,
        f.adjusted_failure_or_incomplete_cost_usd::float8,
        f.nonproductive_or_unclean_spend_share::float8,
        f.failure_or_incomplete_spend_share::float8,
        f.adjusted_cost_per_clean_success::float8,
        f.adjusted_cost_per_any_success::float8,
        f.cost_sources_present,
        f.cost_confidence_present
      from benchmark.v_suite_adjusted_cost_frontier f
      left join benchmark.benchmark_arms a
        on a.arm_id = f.arm_id
      where f.suite_id = $1
      order by f.adjusted_known_cost_usd asc nulls last, f.arm_id
    `,
    [suiteId]
  );
}

export async function getAdjustedOutcomeCostRows(suiteId: string): Promise<AdjustedOutcomeCostRow[]> {
  return queryRows<AdjustedOutcomeCostRow>(
    `
      select
        suite_id,
        outcome_bucket,
        sum(trial_count)::int as trial_count,
        coalesce(sum(recorded_cost_usd), 0::numeric)::float8 as recorded_cost_usd,
        coalesce(sum(adjusted_known_cost_usd), 0::numeric)::float8 as adjusted_known_cost_usd,
        coalesce(sum(known_accounting_gap_usd), 0::numeric)::float8 as known_accounting_gap_usd
      from benchmark.v_arm_outcome_cost_breakdown
      where suite_id = $1
      group by suite_id, outcome_bucket
      order by
        case outcome_bucket
          when 'clean_success' then 1
          when 'exception_with_success_signal' then 2
          when 'normal_failure' then 3
          when 'exception_failure' then 4
          else 9
        end,
        outcome_bucket
    `,
    [suiteId]
  );
}
