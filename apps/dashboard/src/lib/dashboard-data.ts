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
  latest_included_execution_at: string | null;
};

export type LatestIncludedExecutionRow = {
  latest_included_execution_at: string | null;
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
      count(*) filter (where status <> 'completed')::int as noncompleted_runs,
      max(runs.finished_at)::text as latest_included_execution_at
    from benchmark.v_dashboard_runs runs
    join valid_runs
      on valid_runs.run_id = runs.run_id
    where runs.phase = 'phase3'
  `);

  return rows[0];
}

export async function getValidSuiteLatestIncludedExecutionAt(
  suiteId: string,
): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(
    `
      select max(finished_at)::text as latest_included_execution_at
      from benchmark.v_valid_arm_run_summary
      where suite_id = $1
    `,
    [suiteId],
  );
  return rows[0]?.latest_included_execution_at ?? null;
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

export async function getAllImportedArmLatestIncludedExecutionAt(): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(`
    select max(r.finished_at)::text as latest_included_execution_at
    from benchmark.benchmark_trials t
    join benchmark.benchmark_arms a
      on a.arm_id = t.arm_id
    join benchmark.benchmark_runs r
      on r.id = t.run_id
  `);
  return rows[0]?.latest_included_execution_at ?? null;
}

export async function getAllImportedTaskLatestIncludedExecutionAt(): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(`
    select max(r.finished_at)::text as latest_included_execution_at
    from benchmark.benchmark_trials t
    join benchmark.benchmark_tasks task
      on task.task_id = t.task_id
    join benchmark.benchmark_runs r
      on r.id = t.run_id
  `);
  return rows[0]?.latest_included_execution_at ?? null;
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
  trial_id: string;
  task_id: string;
  arm_id: string;
  task_attempt: number;
  run_trial_ordinal: number | null;
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
  group_key: string;
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
  run_trial_number: number | null;
  task_attempt_number: number | null;
  task_attempt_count: number | null;
  task_ordinal: number | null;
  run_task_count: number | null;
  reward: number | string | null;
  quality_flag: string | null;
  exception_type: string | null;
  exception_summary: string | null;
  artifact_path: string;
  artifact_type: string | null;
  r2_uri: string | null;
  size_bytes: number | null;
  created_at: string | null;
  matching_artifact: boolean;
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
  page?: number;
  page_size?: number;
};

export type ArtifactBrowserGroup = {
  group_key: string;
  trial_id: string | null;
  run_id: string;
  run_label: string;
  suite_id: string | null;
  logical_mode: string | null;
  storage_mode: string | null;
  arm_id: string | null;
  task_id: string | null;
  attempt_index: number | null;
  run_trial_number: number | null;
  task_attempt_number: number | null;
  task_attempt_count: number | null;
  task_ordinal: number | null;
  run_task_count: number | null;
  reward: number | string | null;
  quality_flag: string | null;
  exception_type: string | null;
  exception_summary: string | null;
  artifacts: ArtifactBrowserRow[];
};

export type ArtifactBrowserPage = {
  groups: ArtifactBrowserGroup[];
  page: number;
  page_size: number;
  total_group_count: number;
  matching_artifact_count: number;
  expanded_artifact_count: number;
  total_pages: number;
};

export type ArtifactBrowserFilterOptions = {
  run_labels: string[];
  suite_ids: string[];
  arm_ids: string[];
  task_ids: string[];
  quality_flags: string[];
  exception_types: string[];
  artifact_types: string[];
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
  run_finished_at: string | null;
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
  run_trial_number: number | null;
  task_attempt_number: number | null;
  task_attempt_count: number | null;
  task_ordinal: number | null;
  run_task_count: number | null;
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
  run_started_at: string | null;
  run_finished_at: string | null;
  provider_family: string | null;
  backend_model: string | null;
  router_model: string | null;
};

export type RunDetailResolution =
  | Readonly<{ status: "not_found"; matches: readonly RunDetailRow[] }>
  | Readonly<{ status: "found"; run: RunDetailRow; matches: readonly RunDetailRow[] }>
  | Readonly<{ status: "ambiguous"; matches: readonly RunDetailRow[] }>;

export async function getRunDetailResolution(runLabel: string): Promise<RunDetailResolution> {
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
      order by mode, run_id
    `,
    [runLabel]
  );

  if (rows.length === 0) return Object.freeze({ status: "not_found", matches: Object.freeze([]) });
  if (rows.length > 1) return Object.freeze({ status: "ambiguous", matches: Object.freeze(rows) });
  return Object.freeze({ status: "found", run: rows[0], matches: Object.freeze([rows[0]]) });
}

export async function getRunTrials(runId: string): Promise<RunTrialRow[]> {
  return queryRows<RunTrialRow>(
    `
      select
        id::text as trial_id,
        task_id,
        arm_id,
        row_number() over (
          partition by run_id, task_id
          order by attempt_index nulls last, id
        )::int as task_attempt,
        attempt_index::int as run_trial_ordinal,
        reward::float8,
        runtime_seconds::float8,
        cost_usd::float8,
        input_tokens::int,
        cache_tokens::int,
        output_tokens::int
      from benchmark.benchmark_trials
      where run_id = $1::uuid
      order by task_id, task_attempt, id
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

function artifactBrowserQueryParts(filters: ArtifactBrowserFilters = {}) {
  const conditions = ["true"];
  const params: unknown[] = [];

  function addCondition(sql: string, value: string | undefined) {
    if (!value) return;
    params.push(value);
    conditions.push(sql.replace("$param", `$${params.length}`));
  }

  addCondition("suite_id = $param", filters.suite_id);
  addCondition("arm_id = $param", filters.arm_id);
  addCondition("run_label = $param", filters.run_label);
  addCondition("task_id = $param", filters.task_id);
  addCondition("quality_flag = $param", filters.quality_flag);
  addCondition("exception_type = $param", filters.exception_type);
  addCondition("artifact_type = $param", filters.artifact_type ?? filters.artifact_kind);

  if (filters.q) {
    params.push(`%${filters.q}%`);
    const placeholder = `$${params.length}`;
    conditions.push(`(
      artifact_path ilike ${placeholder}
      or notes ilike ${placeholder}
      or run_label ilike ${placeholder}
      or task_id ilike ${placeholder}
      or exception_summary ilike ${placeholder}
    )`);
  }

  const ctes = `
    with quality_rows as (
      select distinct on (trial_id) *
      from benchmark.v_trial_quality_flags
      order by trial_id, quality_flag, suite_id, arm_id
    ),
    trial_attempts as (
      select
        t.*,
        row_number() over (
          partition by t.run_id, t.task_id
          order by t.attempt_index nulls last, t.id
        )::int as task_attempt_number,
        count(*) over (partition by t.run_id, t.task_id)::int as task_attempt_count
      from benchmark.benchmark_trials t
    ),
    run_task_first_positions as (
      select run_id, task_id, min(attempt_index) as first_trial_position
      from benchmark.benchmark_trials
      where task_id is not null
      group by run_id, task_id
    ),
    run_tasks as (
      select
        run_id,
        task_id,
        row_number() over (
          partition by run_id
          order by first_trial_position nulls last, task_id
        )::int as task_ordinal,
        count(*) over (partition by run_id)::int as run_task_count
      from run_task_first_positions
    ),
    artifact_context as (
      select
        coalesce(t.id::text, 'run:' || r.id::text) as group_key,
        art.id::text as artifact_id,
        r.id::text as run_id,
        r.run_label,
        r.started_at,
        r.finished_at,
        coalesce(t.arm_run_id, ar.id)::text as arm_run_id,
        coalesce(q.suite_id, ar.suite_id) as suite_id,
        coalesce(q.logical_mode, ar.logical_mode) as logical_mode,
        coalesce(q.storage_mode, ar.storage_mode, r.mode) as storage_mode,
        coalesce(q.arm_id, t.arm_id, ar.arm_id) as arm_id,
        t.id::text as trial_id,
        coalesce(q.task_id, t.task_id) as task_id,
        coalesce(q.attempt_index, t.attempt_index)::int as attempt_index,
        t.attempt_index::int as run_trial_number,
        t.task_attempt_number,
        t.task_attempt_count,
        rt.task_ordinal,
        rt.run_task_count,
        coalesce(q.reward, t.reward) as reward,
        q.quality_flag,
        coalesce(q.exception_type, t.exception_type) as exception_type,
        coalesce(q.exception_summary, t.exception_summary) as exception_summary,
        coalesce(art.local_path, art.r2_uri, art.github_uri, art.id::text) as artifact_path,
        art.artifact_type,
        art.r2_uri,
        art.size_bytes::int,
        art.created_at,
        art.notes
      from benchmark.benchmark_artifacts art
      join benchmark.benchmark_runs r on r.id = art.run_id
      left join trial_attempts t on t.id = art.trial_id
      left join run_tasks rt on rt.run_id = t.run_id and rt.task_id = t.task_id
      left join lateral (
        select ar1.*
        from benchmark.benchmark_arm_runs ar1
        where ar1.id = t.arm_run_id
          or (t.id is not null and t.arm_run_id is null and ar1.run_id = art.run_id)
        order by case when ar1.id = t.arm_run_id then 0 else 1 end, ar1.created_at desc
        limit 1
      ) ar on true
      left join quality_rows q on q.trial_id = t.id
      where r.phase = 'phase3'
    ),
    matching_artifacts as (
      select * from artifact_context
      where ${conditions.join("\n        and ")}
    ),
    matching_groups as (
      select
        group_key,
        max(started_at) as group_started_at,
        min(run_trial_number) as group_trial_position
      from matching_artifacts
      group by group_key
    )`;

  return { ctes, params };
}

export async function getArtifactBrowserPage(
  filters: ArtifactBrowserFilters = {}
): Promise<ArtifactBrowserPage> {
  const pageSize = [10, 25, 50, 100].includes(filters.page_size ?? 25)
    ? filters.page_size ?? 25
    : 25;
  const requestedPage = Math.max(filters.page ?? 1, 1);
  const { ctes, params } = artifactBrowserQueryParts(filters);

  const countRows = await queryRows<{ total_group_count: number; matching_artifact_count: number }>(
    `${ctes}
      select
        (select count(*)::int from matching_groups) as total_group_count,
        (select count(distinct artifact_id)::int from matching_artifacts) as matching_artifact_count
    `,
    params
  );
  const totalGroupCount = countRows[0]?.total_group_count ?? 0;
  const matchingArtifactCount = countRows[0]?.matching_artifact_count ?? 0;
  const totalPages = Math.max(Math.ceil(totalGroupCount / pageSize), 1);
  const page = Math.min(requestedPage, totalPages);
  const offset = (page - 1) * pageSize;

  if (totalGroupCount === 0) {
    return {
      groups: [], page: 1, page_size: pageSize, total_group_count: 0,
      matching_artifact_count: 0, expanded_artifact_count: 0, total_pages: 1
    };
  }

  const rowParams = [...params, pageSize, offset];
  const rows = await queryRows<ArtifactBrowserRow>(
    `${ctes},
      paged_groups as (
        select * from matching_groups
        order by group_started_at desc nulls last, group_trial_position nulls first, group_key
        limit $${params.length + 1} offset $${params.length + 2}
      )
      select
        ac.group_key,
        ac.artifact_id,
        ac.run_id,
        ac.run_label,
        ac.arm_run_id,
        ac.suite_id,
        ac.logical_mode,
        ac.storage_mode,
        ac.arm_id,
        ac.trial_id,
        ac.task_id,
        ac.attempt_index,
        ac.run_trial_number,
        ac.task_attempt_number,
        ac.task_attempt_count,
        ac.task_ordinal,
        ac.run_task_count,
        ac.reward,
        ac.quality_flag,
        ac.exception_type,
        ac.exception_summary,
        ac.artifact_path,
        ac.artifact_type,
        ac.r2_uri,
        ac.size_bytes,
        ac.created_at::text,
        exists(select 1 from matching_artifacts ma where ma.artifact_id = ac.artifact_id) as matching_artifact
      from paged_groups pg
      join artifact_context ac on ac.group_key = pg.group_key
      order by pg.group_started_at desc nulls last, pg.group_trial_position nulls first,
        pg.group_key, ac.artifact_type, ac.artifact_path
    `,
    rowParams
  );

  const groupsByKey = new Map<string, ArtifactBrowserGroup>();
  for (const row of rows) {
    let group = groupsByKey.get(row.group_key);
    if (!group) {
      group = {
        group_key: row.group_key,
        trial_id: row.trial_id,
        run_id: row.run_id,
        run_label: row.run_label,
        suite_id: row.suite_id,
        logical_mode: row.logical_mode,
        storage_mode: row.storage_mode,
        arm_id: row.arm_id,
        task_id: row.task_id,
        attempt_index: row.attempt_index,
        run_trial_number: row.run_trial_number,
        task_attempt_number: row.task_attempt_number,
        task_attempt_count: row.task_attempt_count,
        task_ordinal: row.task_ordinal,
        run_task_count: row.run_task_count,
        reward: row.reward,
        quality_flag: row.quality_flag,
        exception_type: row.exception_type,
        exception_summary: row.exception_summary,
        artifacts: []
      };
      groupsByKey.set(row.group_key, group);
    }
    group.artifacts.push(row);
  }

  return {
    groups: Array.from(groupsByKey.values()),
    page,
    page_size: pageSize,
    total_group_count: totalGroupCount,
    matching_artifact_count: matchingArtifactCount,
    expanded_artifact_count: rows.length,
    total_pages: totalPages
  };
}

export async function getArtifactBrowserLatestIncludedExecutionAt(
  filters: ArtifactBrowserFilters = {},
): Promise<string | null> {
  const { ctes, params } = artifactBrowserQueryParts(filters);
  const rows = await queryRows<LatestIncludedExecutionRow>(
    `${ctes}
      select max(finished_at)::text as latest_included_execution_at
      from matching_artifacts
    `,
    params,
  );
  return rows[0]?.latest_included_execution_at ?? null;
}

export async function getArtifactBrowserFilterOptions(): Promise<ArtifactBrowserFilterOptions> {
  const rows = await queryRows<ArtifactBrowserFilterOptions>(`
    with quality_rows as (
      select distinct on (trial_id) *
      from benchmark.v_trial_quality_flags
      order by trial_id, quality_flag, suite_id, arm_id
    ),
    option_context as (
      select
        r.run_label,
        coalesce(q.suite_id, ar.suite_id) as suite_id,
        coalesce(q.arm_id, t.arm_id, ar.arm_id) as arm_id,
        coalesce(q.task_id, t.task_id) as task_id,
        q.quality_flag,
        coalesce(q.exception_type, t.exception_type) as exception_type,
        art.artifact_type
      from benchmark.benchmark_artifacts art
      join benchmark.benchmark_runs r on r.id = art.run_id
      left join benchmark.benchmark_trials t on t.id = art.trial_id
      left join lateral (
        select ar1.* from benchmark.benchmark_arm_runs ar1
        where ar1.id = t.arm_run_id
           or (t.id is not null and t.arm_run_id is null and ar1.run_id = art.run_id)
        order by case when ar1.id = t.arm_run_id then 0 else 1 end, ar1.created_at desc
        limit 1
      ) ar on true
      left join quality_rows q on q.trial_id = t.id
      where r.phase = 'phase3'
    )
    select
      coalesce(array(select distinct run_label from option_context where run_label is not null order by run_label limit 500), '{}') as run_labels,
      coalesce(array(select distinct suite_id from option_context where suite_id is not null order by suite_id limit 500), '{}') as suite_ids,
      coalesce(array(select distinct arm_id from option_context where arm_id is not null order by arm_id limit 500), '{}') as arm_ids,
      coalesce(array(select distinct task_id from option_context where task_id is not null order by task_id limit 500), '{}') as task_ids,
      coalesce(array(select distinct quality_flag from option_context where quality_flag is not null order by quality_flag limit 500), '{}') as quality_flags,
      coalesce(array(select distinct exception_type from option_context where exception_type is not null order by exception_type limit 500), '{}') as exception_types,
      coalesce(array(select distinct artifact_type from option_context where artifact_type is not null order by artifact_type limit 500), '{}') as artifact_types
  `);
  return rows[0] ?? {
    run_labels: [], suite_ids: [], arm_ids: [], task_ids: [], quality_flags: [],
    exception_types: [], artifact_types: []
  };
}

/** Compatibility helper for callers that still need a flat, bounded list. */
export async function getArtifactBrowserRows(
  filters: ArtifactBrowserFilters = {}
): Promise<ArtifactBrowserRow[]> {
  const page = await getArtifactBrowserPage({ ...filters, page: 1, page_size: 100 });
  return page.groups.flatMap((group) => group.artifacts);
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
    r.finished_at::text as run_finished_at,
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
       or (t.id is not null and t.arm_run_id is null and ar1.run_id = art.run_id)
    order by
      case when ar1.id = t.arm_run_id then 0 else 1 end,
      ar1.created_at desc
    limit 1
  ) ar on true
  left join lateral (
    select q1.*
    from benchmark.v_trial_quality_flags q1
    where q1.trial_id = t.id
    order by q1.quality_flag, q1.suite_id, q1.arm_id
    limit 1
  ) q on true
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
      with trial_positions as (
        select
          t.*,
          row_number() over (
            partition by t.run_id, t.task_id
            order by t.attempt_index nulls last, t.id
          )::int as task_attempt_number,
          count(*) over (partition by t.run_id, t.task_id)::int as task_attempt_count
        from benchmark.benchmark_trials t
      ),
      run_task_first_positions as (
        select run_id, task_id, min(attempt_index) as first_trial_position
        from benchmark.benchmark_trials
        where task_id is not null
        group by run_id, task_id
      ),
      run_tasks as (
        select
          run_id,
          task_id,
          row_number() over (
            partition by run_id
            order by first_trial_position nulls last, task_id
          )::int as task_ordinal,
          count(*) over (partition by run_id)::int as run_task_count
        from run_task_first_positions
      )
      select
        t.id::text as trial_id,
        r.id::text as run_id,
        r.run_label,
        t.arm_run_id::text,
        coalesce(q.suite_id, ar.suite_id) as suite_id,
        coalesce(q.logical_mode, ar.logical_mode) as logical_mode,
        coalesce(q.storage_mode, ar.storage_mode, r.mode) as storage_mode,
        coalesce(q.arm_id, t.arm_id, ar.arm_id) as arm_id,
        coalesce(q.task_id, t.task_id) as task_id,
        task.task_name,
        coalesce(q.attempt_index, t.attempt_index)::int as attempt_index,
        t.attempt_index::int as run_trial_number,
        t.task_attempt_number,
        t.task_attempt_count,
        rt.task_ordinal,
        rt.run_task_count,
        coalesce(q.reward, t.reward) as reward,
        coalesce(q.runtime_seconds, t.runtime_seconds) as runtime_seconds,
        coalesce(q.cost_usd, t.cost_usd) as cost_usd,
        coalesce(q.input_tokens, t.input_tokens) as input_tokens,
        coalesce(q.cache_tokens, t.cache_tokens) as cache_tokens,
        coalesce(q.output_tokens, t.output_tokens) as output_tokens,
        t.result_local_path,
        t.result_artifact_uri,
        q.quality_flag,
        coalesce(q.exception_type, t.exception_type) as exception_type,
        coalesce(q.exception_summary, t.exception_summary) as exception_summary,
        invalid.reason as invalid_reason,
        invalid.provider_run_id as invalid_provider_run_id,
        invalid.invalidated_at::text,
        invalid.invalidated_by,
        invalid.raw_metadata as invalid_raw_metadata,
        r.started_at::text as run_started_at,
        r.finished_at::text as run_finished_at,
        ar.provider_family,
        ar.backend_model,
        ar.router_model
      from trial_positions t
      join benchmark.benchmark_runs r
        on r.id = t.run_id
      left join benchmark.v_arm_run_summary ar
        on ar.arm_run_id = t.arm_run_id
      left join run_tasks rt
        on rt.run_id = t.run_id and rt.task_id = t.task_id
      left join lateral (
        select q1.*
        from benchmark.v_trial_quality_flags q1
        where q1.trial_id = t.id
        order by q1.quality_flag, q1.suite_id, q1.arm_id
        limit 1
      ) q on true
      left join benchmark.benchmark_tasks task
        on task.task_id = coalesce(q.task_id, t.task_id)
      left join benchmark.benchmark_invalid_arm_runs invalid
        on invalid.suite_id = coalesce(q.suite_id, ar.suite_id)
       and invalid.arm_id = coalesce(q.arm_id, t.arm_id, ar.arm_id)
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

export type ReviewedSelectedArmRunDbRow = {
  arm_run_id: string;
  run_id: string;
  run_label: string;
  arm_id: string;
  provider_family: string | null;
  backend_model: string | null;
  router_model: string | null;
  suite_id: string | null;
  suite_type: string | null;
  logical_mode: string;
  storage_mode: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  task_count: number;
  trial_count: number;
  success_count: number;
  failure_count: number;
  median_runtime_seconds: number | null;
  trial_cost_usd: string | null;
  cost_row_count: number;
  missing_cost_count: number;
  artifact_count: number;
  r2_artifact_count: number;
};

export type ReviewedSelectedRunAdjustedCostDbRow = {
  run_label: string;
  arm_id: string;
  suite_id: string | null;
  trial_count: number;
  recorded_cost_usd: string | null;
  adjusted_known_cost_usd: string | null;
  accounting_gap_usd: string | null;
  missing_recorded_cost_count: number;
  unresolved_adjusted_cost_count: number;
  adjusted_cost_sources: string[];
  adjusted_cost_confidences: string[];
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
  cost_row_count: number;
  missing_cost_count: number;
};

export type EvalArmComparisonRow = {
  task_id: string;
  task_name: string | null;
  arm_id: string | null;
  suite_id: string | null;
  logical_mode: string | null;
  validity_status: "valid" | "invalid_or_quarantined" | "unlinked";
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

export async function getPhase3EvalSuiteLatestIncludedExecutionAt(): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(`
    select max(arm_run.finished_at)::text as latest_included_execution_at
    from benchmark.v_valid_arm_run_summary arm_run
    join benchmark.benchmark_eval_suites suite
      on suite.suite_id = arm_run.suite_id
    where suite.phase = 'phase3'
  `);
  return rows[0]?.latest_included_execution_at ?? null;
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

export async function getReviewedSelectedArmRunRows(
  runLabels: readonly string[]
): Promise<ReviewedSelectedArmRunDbRow[]> {
  if (runLabels.length === 0) return [];
  if (new Set(runLabels).size !== runLabels.length) {
    throw new Error("Reviewed selected run labels must be unique");
  }

  return queryRows<ReviewedSelectedArmRunDbRow>(
    `
      with selected_runs as (
        select *
        from benchmark.v_valid_arm_run_summary
        where run_label = any($1::text[])
      ),
      task_counts as (
        select
          t.arm_run_id,
          count(distinct t.task_id)::int as task_count
        from benchmark.benchmark_trials t
        join selected_runs selected
          on selected.arm_run_id = t.arm_run_id
        group by t.arm_run_id
      )
      select
        selected.arm_run_id::text,
        selected.run_id::text,
        selected.run_label,
        selected.arm_id,
        selected.provider_family,
        selected.backend_model,
        selected.router_model,
        selected.suite_id,
        selected.suite_type,
        selected.logical_mode,
        selected.storage_mode,
        selected.status,
        selected.started_at::text,
        selected.finished_at::text,
        coalesce(tasks.task_count, 0)::int as task_count,
        selected.trial_count::int,
        selected.success_count::int,
        selected.failure_count::int,
        selected.median_runtime_seconds::float8,
        case
          when selected.cost_row_count = 0 then null
          else selected.trial_cost_usd::text
        end as trial_cost_usd,
        selected.cost_row_count::int,
        selected.missing_cost_count::int,
        selected.artifact_count::int,
        selected.r2_artifact_count::int
      from selected_runs selected
      left join task_counts tasks
        on tasks.arm_run_id = selected.arm_run_id
      order by selected.run_label, selected.arm_id
    `,
    [runLabels]
  );
}

export async function getReviewedSelectedRunAdjustedCostRows(
  runLabels: readonly string[]
): Promise<ReviewedSelectedRunAdjustedCostDbRow[]> {
  if (runLabels.length === 0) return [];
  if (new Set(runLabels).size !== runLabels.length) {
    throw new Error("Reviewed selected run labels must be unique");
  }

  return queryRows<ReviewedSelectedRunAdjustedCostDbRow>(
    `
      select
        run_label,
        arm_id,
        suite_id,
        count(*)::int as trial_count,
        case
          when count(recorded_cost_usd) = 0 then null
          else sum(recorded_cost_usd)::text
        end as recorded_cost_usd,
        case
          when count(adjusted_cost_usd) = 0 then null
          else sum(adjusted_cost_usd)::text
        end as adjusted_known_cost_usd,
        case
          when count(recorded_cost_usd) = 0 or count(adjusted_cost_usd) = 0 then null
          else (sum(adjusted_cost_usd) - sum(recorded_cost_usd))::text
        end as accounting_gap_usd,
        count(*) filter (where recorded_cost_usd is null)::int as missing_recorded_cost_count,
        count(*) filter (where adjusted_cost_usd is null)::int as unresolved_adjusted_cost_count,
        coalesce(
          array_agg(distinct cost_source order by cost_source)
            filter (where cost_source is not null),
          array[]::text[]
        ) as adjusted_cost_sources,
        coalesce(
          array_agg(distinct cost_confidence order by cost_confidence)
            filter (where cost_confidence is not null),
          array[]::text[]
        ) as adjusted_cost_confidences
      from benchmark.v_trial_adjusted_cost_coverage
      where run_label = any($1::text[])
      group by run_label, arm_id, suite_id
      order by run_label, arm_id, suite_id
    `,
    [runLabels]
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
      sum(trial_cost_usd)::float8 as trial_cost_usd,
      coalesce(sum(cost_row_count), 0)::int as cost_row_count,
      coalesce(sum(missing_cost_count), 0)::int as missing_cost_count
    from benchmark.v_valid_eval_arm_comparison
    group by task_id
    order by task_name
  `);
}

export async function getAllImportedEvalRows(): Promise<EvalSummaryRow[]> {
  return queryRows<EvalSummaryRow>(`
    with arm_summary as (
      select
        task_id,
        count(distinct arm_id)::int as arm_count
      from benchmark.benchmark_trials
      group by task_id
    )
    select
      task.task_id,
      task.task_name,
      coalesce(arm_summary.arm_count, 0)::int as arm_count,
      task.trial_count::int,
      task.success_count::int,
      task.pass_rate::float8,
      task.median_runtime_seconds::float8,
      task.trial_cost_usd::float8,
      task.cost_row_count::int,
      task.missing_cost_count::int
    from benchmark.v_dashboard_tasks task
    left join arm_summary
      on arm_summary.task_id = task.task_id
    where task.trial_count > 0
    order by task.task_name
  `);
}

export async function getValidImportedEvalLatestIncludedExecutionAt(): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(`
    select max(finished_at)::text as latest_included_execution_at
    from benchmark.v_valid_arm_run_summary
    where trial_count > 0
  `);
  return rows[0]?.latest_included_execution_at ?? null;
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
        'valid'::text as validity_status,
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

export async function getAllImportedEvalArmComparison(
  taskId: string,
): Promise<EvalArmComparisonRow[]> {
  return queryRows<EvalArmComparisonRow>(
    `
      select
        trial.task_id,
        task.task_name,
        trial.arm_id,
        arm_run.suite_id,
        coalesce(arm_run.logical_mode, run.mode) as logical_mode,
        case
          when trial.arm_run_id is null then 'unlinked'
          when invalid_lookup.is_invalid is true then 'invalid_or_quarantined'
          else 'valid'
        end::text as validity_status,
        count(trial.id)::int as trial_count,
        count(trial.id) filter (where coalesce(trial.reward, 0) >= 1)::int as success_count,
        case
          when count(trial.id) = 0 then null
          else count(trial.id) filter (where coalesce(trial.reward, 0) >= 1)::numeric
            / count(trial.id)::numeric
        end::float8 as pass_rate,
        avg(trial.reward)::float8 as mean_reward,
        percentile_cont(0.5) within group (order by trial.runtime_seconds)::float8 as median_runtime_seconds,
        sum(trial.cost_usd)::float8 as trial_cost_usd,
        count(trial.cost_usd)::int as cost_row_count,
        count(trial.id) filter (where trial.cost_usd is null)::int as missing_cost_count
      from benchmark.benchmark_trials trial
      left join benchmark.benchmark_runs run
        on run.id = trial.run_id
      left join benchmark.benchmark_tasks task
        on task.task_id = trial.task_id
      left join benchmark.benchmark_arm_runs arm_run
        on arm_run.id = trial.arm_run_id
      left join lateral (
        select true as is_invalid
        from benchmark.benchmark_invalid_arm_runs invalid_record
        where invalid_record.suite_id = arm_run.suite_id
          and invalid_record.arm_id = arm_run.arm_id
          and invalid_record.run_label = run.run_label
        limit 1
      ) invalid_lookup on true
      where trial.task_id = $1
      group by
        trial.task_id,
        task.task_name,
        trial.arm_id,
        arm_run.suite_id,
        coalesce(arm_run.logical_mode, run.mode),
        case
          when trial.arm_run_id is null then 'unlinked'
          when invalid_lookup.is_invalid is true then 'invalid_or_quarantined'
          else 'valid'
        end
      order by pass_rate desc nulls last, trial.arm_id, arm_run.suite_id, validity_status
    `,
    [taskId],
  );
}

export async function getValidEvalTaskLatestIncludedExecutionAt(
  taskId: string,
): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(
    `
      select max(arm_run.finished_at)::text as latest_included_execution_at
      from benchmark.v_valid_arm_run_summary arm_run
      join benchmark.benchmark_trials trial
        on trial.arm_run_id = arm_run.arm_run_id
      where trial.task_id = $1
    `,
    [taskId],
  );
  return rows[0]?.latest_included_execution_at ?? null;
}

export async function getAllImportedEvalTaskLatestIncludedExecutionAt(
  taskId: string,
): Promise<string | null> {
  const rows = await queryRows<LatestIncludedExecutionRow>(
    `
      select max(run.finished_at)::text as latest_included_execution_at
      from benchmark.benchmark_trials trial
      join benchmark.benchmark_runs run
        on run.id = trial.run_id
      where trial.task_id = $1
    `,
    [taskId],
  );
  return rows[0]?.latest_included_execution_at ?? null;
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

export type DisplayedArmRunFreshnessIdentity = Readonly<{
  suite_id: string | null;
  arm_id: string;
  run_label: string;
}>;

type DisplayedArmRunFreshnessMatchRow = DisplayedArmRunFreshnessIdentity & {
  match_count: number;
  finished_at: string | null;
};

export type DisplayedArmRunFreshnessResolution = Readonly<{
  latestIncludedExecutionAt: string | null;
  expectedIdentityCount: number;
  resolvedIdentityCount: number;
  unresolvedIdentities: readonly DisplayedArmRunFreshnessIdentity[];
  duplicateIdentities: readonly DisplayedArmRunFreshnessIdentity[];
  missingFinishedAtIdentities: readonly DisplayedArmRunFreshnessIdentity[];
}>;

function displayedArmRunFreshnessIdentityKey(identity: DisplayedArmRunFreshnessIdentity) {
  return JSON.stringify([identity.suite_id, identity.arm_id, identity.run_label]);
}

export function deduplicateDisplayedArmRunFreshnessIdentities(
  identities: readonly DisplayedArmRunFreshnessIdentity[],
): DisplayedArmRunFreshnessIdentity[] {
  const byKey = new Map<string, DisplayedArmRunFreshnessIdentity>();
  for (const identity of identities) {
    if (!identity.arm_id || !identity.run_label) {
      throw new Error("Displayed arm-run freshness identities require arm_id and run_label");
    }
    const retained = Object.freeze({
      suite_id: identity.suite_id,
      arm_id: identity.arm_id,
      run_label: identity.run_label,
    });
    byKey.set(displayedArmRunFreshnessIdentityKey(retained), retained);
  }
  return [...byKey.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([, identity]) => identity);
}

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

export async function getDisplayedArmRunFreshnessResolution(
  identities: readonly DisplayedArmRunFreshnessIdentity[],
): Promise<DisplayedArmRunFreshnessResolution> {
  const expected = deduplicateDisplayedArmRunFreshnessIdentities(identities);
  if (expected.length === 0) {
    return Object.freeze({
      latestIncludedExecutionAt: null,
      expectedIdentityCount: 0,
      resolvedIdentityCount: 0,
      unresolvedIdentities: Object.freeze([]),
      duplicateIdentities: Object.freeze([]),
      missingFinishedAtIdentities: Object.freeze([]),
    });
  }

  const rows = await queryRows<DisplayedArmRunFreshnessMatchRow>(
    `
      with requested as (
        select suite_id, arm_id, run_label
        from jsonb_to_recordset($1::jsonb)
          as identity(suite_id text, arm_id text, run_label text)
      )
      select
        requested.suite_id,
        requested.arm_id,
        requested.run_label,
        matched.match_count::int,
        matched.finished_at
      from requested
      cross join lateral (
        select
          count(*)::int as match_count,
          case
            when count(*) = 1 then max(summary.finished_at)::text
            else null
          end as finished_at
        from benchmark.v_arm_run_summary summary
        where summary.phase = 'phase3'
          and summary.suite_id is not distinct from requested.suite_id
          and summary.arm_id = requested.arm_id
          and summary.run_label = requested.run_label
      ) matched
      order by requested.suite_id nulls first, requested.arm_id, requested.run_label
    `,
    [JSON.stringify(expected)],
  );

  const rowsByIdentity = new Map(
    rows.map((row) => [displayedArmRunFreshnessIdentityKey(row), row]),
  );
  const unresolvedIdentities: DisplayedArmRunFreshnessIdentity[] = [];
  const duplicateIdentities: DisplayedArmRunFreshnessIdentity[] = [];
  const missingFinishedAtIdentities: DisplayedArmRunFreshnessIdentity[] = [];
  let resolvedIdentityCount = 0;
  let latestIncludedExecutionAt: string | null = null;
  let latestMilliseconds = Number.NEGATIVE_INFINITY;

  for (const identity of expected) {
    const row = rowsByIdentity.get(displayedArmRunFreshnessIdentityKey(identity));
    if (!row || row.match_count === 0) {
      unresolvedIdentities.push(identity);
      continue;
    }
    if (row.match_count !== 1) {
      duplicateIdentities.push(identity);
      continue;
    }

    resolvedIdentityCount += 1;
    if (row.finished_at === null) {
      missingFinishedAtIdentities.push(identity);
      continue;
    }
    const milliseconds = Date.parse(row.finished_at);
    if (!Number.isFinite(milliseconds)) {
      missingFinishedAtIdentities.push(identity);
      continue;
    }
    if (milliseconds > latestMilliseconds) {
      latestMilliseconds = milliseconds;
      latestIncludedExecutionAt = row.finished_at;
    }
  }

  return Object.freeze({
    latestIncludedExecutionAt,
    expectedIdentityCount: expected.length,
    resolvedIdentityCount,
    unresolvedIdentities: Object.freeze(unresolvedIdentities),
    duplicateIdentities: Object.freeze(duplicateIdentities),
    missingFinishedAtIdentities: Object.freeze(missingFinishedAtIdentities),
  });
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
