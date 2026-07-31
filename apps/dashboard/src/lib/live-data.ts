import { queryRows } from "./db";

export const LIVE_STALE_AFTER_SECONDS = 90;
export const LIVE_RUN_LIMIT = 20;
export const LIVE_EVENT_LIMIT = 200;
export const LIVE_OUTPUT_EVENT_LIMIT = 300;
export const LIVE_WARNING_EVENT_LIMIT = 100;
export const LIVE_TRIAL_LIMIT = 200;
export const LIVE_ARTIFACT_LIMIT = 300;

export type LiveRunRow = {
  live_run_id: string;
  arm_id: string;
  phase: string;
  mode: string;
  run_kind: string;
  scored: boolean;
  runner_name: string | null;
  github_run_id: string | null;
  github_run_attempt: number | null;
  github_job: string | null;
  status: string;
  display_status: string;
  is_active: boolean;
  is_stale: boolean;
  benchmark_status: string | null;
  live_publication_status: string | null;
  progressive_artifact_status: string | null;
  canonical_publication_status: string | null;
  started_at: string;
  finished_at: string | null;
  last_heartbeat_at: string | null;
  elapsed_seconds: number | null;
  expected_trial_count: number | null;
  completed_trial_count: number;
  success_count: number;
  failure_count: number;
  exception_count: number;
  observed_cost_usd: number | null;
  input_tokens: number | null;
  cache_tokens: number | null;
  output_tokens: number | null;
  event_count: number;
  returncode: number | null;
  latest_message: string | null;
  canonical_arm_run_id: string | null;
  provider_family: string | null;
  backend_model: string | null;
  router_model: string | null;
};

export type LiveEventRow = {
  sequence: number;
  event_type: string;
  occurred_at: string;
  elapsed_seconds: number | null;
  stream: string | null;
  message: string | null;
  payload: Record<string, unknown>;
};

export type LiveTrialRow = {
  trial_key: string;
  task_id: string | null;
  attempt_index: number | null;
  status: string;
  reward: number | null;
  exception_type: string | null;
  exception_summary: string | null;
  runtime_seconds: number | null;
  input_tokens: number | null;
  cache_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  started_at: string | null;
  finished_at: string | null;
  stability_state: string;
  relative_local_path: string | null;
};

export type LiveArtifactRow = {
  trial_key: string | null;
  artifact_type: string;
  relative_local_path: string;
  r2_uri: string | null;
  sha256: string;
  size_bytes: number;
  stability_state: string;
  uploaded_at: string | null;
};

const LIVE_RUN_COLUMNS = `
  live.live_run_id,
  live.arm_id,
  live.phase,
  live.mode,
  live.run_kind,
  live.scored,
  live.runner_name,
  live.github_run_id,
  live.github_run_attempt,
  live.github_job,
  live.status,
  case
    when live.status in ('starting', 'running', 'finalizing')
      and coalesce(live.last_heartbeat_at, live.started_at)
        < now() - interval '${LIVE_STALE_AFTER_SECONDS} seconds'
      then 'stale'
    else live.status
  end as display_status,
  live.status in ('starting', 'running', 'finalizing') as is_active,
  live.status in ('starting', 'running', 'finalizing')
    and coalesce(live.last_heartbeat_at, live.started_at)
      < now() - interval '${LIVE_STALE_AFTER_SECONDS} seconds' as is_stale,
  live.benchmark_status,
  live.live_publication_status,
  live.progressive_artifact_status,
  live.canonical_publication_status,
  live.started_at,
  live.finished_at,
  live.last_heartbeat_at,
  coalesce(
    live.elapsed_seconds,
    extract(epoch from (coalesce(live.finished_at, now()) - live.started_at))
  )::float8 as elapsed_seconds,
  live.expected_trial_count,
  live.completed_trial_count,
  live.success_count,
  live.failure_count,
  live.exception_count,
  live.observed_cost_usd::float8,
  live.input_tokens::float8 as input_tokens,
  live.cache_tokens::float8 as cache_tokens,
  live.output_tokens::float8 as output_tokens,
  live.event_count,
  live.returncode,
  live.latest_message,
  live.canonical_arm_run_id,
  arm.provider_family,
  arm.backend_model,
  arm.router_model
`;

export async function getRecentLiveRuns(limit = LIVE_RUN_LIMIT): Promise<LiveRunRow[]> {
  return queryRows<LiveRunRow>(
    `
      select ${LIVE_RUN_COLUMNS}
      from benchmark.live_runs live
      left join benchmark.benchmark_arms arm on arm.arm_id = live.arm_id
      order by live.started_at desc, live.live_run_id
      limit $1
    `,
    [Math.min(Math.max(limit, 1), LIVE_RUN_LIMIT)]
  );
}

export async function getActiveLiveRuns(limit = LIVE_RUN_LIMIT): Promise<LiveRunRow[]> {
  return queryRows<LiveRunRow>(
    `
      select ${LIVE_RUN_COLUMNS}
      from benchmark.live_runs live
      left join benchmark.benchmark_arms arm on arm.arm_id = live.arm_id
      where live.status in ('starting', 'running', 'finalizing')
      order by live.started_at desc
      limit $1
    `,
    [Math.min(Math.max(limit, 1), LIVE_RUN_LIMIT)]
  );
}

export async function getStaleLiveRuns(limit = LIVE_RUN_LIMIT): Promise<LiveRunRow[]> {
  return queryRows<LiveRunRow>(
    `
      select ${LIVE_RUN_COLUMNS}
      from benchmark.live_runs live
      left join benchmark.benchmark_arms arm on arm.arm_id = live.arm_id
      where live.status in ('starting', 'running', 'finalizing')
        and coalesce(live.last_heartbeat_at, live.started_at)
          < now() - interval '${LIVE_STALE_AFTER_SECONDS} seconds'
      order by coalesce(live.last_heartbeat_at, live.started_at)
      limit $1
    `,
    [Math.min(Math.max(limit, 1), LIVE_RUN_LIMIT)]
  );
}

export async function getLiveRun(liveRunId: string): Promise<LiveRunRow | null> {
  const rows = await queryRows<LiveRunRow>(
    `
      select ${LIVE_RUN_COLUMNS}
      from benchmark.live_runs live
      left join benchmark.benchmark_arms arm on arm.arm_id = live.arm_id
      where live.live_run_id = $1
      limit 1
    `,
    [liveRunId]
  );
  return rows[0] ?? null;
}

export async function getLiveRunEvents(
  liveRunId: string,
  limit = LIVE_EVENT_LIMIT
): Promise<LiveEventRow[]> {
  return queryRows<LiveEventRow>(
    `
      select *
      from (
        select
          sequence,
          event_type,
          occurred_at,
          elapsed_seconds::float8,
          stream,
          left(message, 2000) as message,
          payload
        from benchmark.live_run_events
        where live_run_id = $1
          and event_type not in ('process_output_chunk', 'agent_output_chunk')
        order by sequence desc
        limit $2
      ) recent
      order by sequence
    `,
    [liveRunId, Math.min(Math.max(limit, 1), LIVE_EVENT_LIMIT)]
  );
}

export async function getLiveOutputEvents(
  liveRunId: string,
  limit = LIVE_OUTPUT_EVENT_LIMIT
): Promise<LiveEventRow[]> {
  return queryRows<LiveEventRow>(
    `
      select *
      from (
        select
          sequence,
          event_type,
          occurred_at,
          elapsed_seconds::float8,
          stream,
          left(message, 2000) as message,
          payload
        from benchmark.live_run_events
        where live_run_id = $1
          and event_type in ('process_output_chunk', 'agent_output_chunk')
        order by sequence desc
        limit $2
      ) recent
      order by sequence
    `,
    [liveRunId, Math.min(Math.max(limit, 1), LIVE_OUTPUT_EVENT_LIMIT)]
  );
}

export async function getLiveRunWarnings(
  liveRunId: string,
  limit = LIVE_WARNING_EVENT_LIMIT
): Promise<LiveEventRow[]> {
  return queryRows<LiveEventRow>(
    `
      select *
      from (
        select
          sequence,
          event_type,
          occurred_at,
          elapsed_seconds::float8,
          stream,
          left(message, 2000) as message,
          payload
        from benchmark.live_run_events
        where live_run_id = $1
          and (
            event_type in ('publication_warning', 'runtime_warning')
            or (
              event_type in ('process_output_chunk', 'agent_output_chunk')
              and coalesce(message, '') ~*
                '(^|[^[:alpha:]])(warning|warn|error|exception|fatal)([^[:alpha:]]|$)'
            )
          )
        order by sequence desc
        limit $2
      ) recent
      order by sequence
    `,
    [liveRunId, Math.min(Math.max(limit, 1), LIVE_WARNING_EVENT_LIMIT)]
  );
}

export async function getLiveTrials(
  liveRunId: string,
  limit = LIVE_TRIAL_LIMIT
): Promise<LiveTrialRow[]> {
  return queryRows<LiveTrialRow>(
    `
      select
        trial_key,
        task_id,
        attempt_index,
        status,
        reward::float8,
        exception_type,
        left(exception_summary, 500) as exception_summary,
        runtime_seconds::float8,
        input_tokens::float8 as input_tokens,
        cache_tokens::float8 as cache_tokens,
        output_tokens::float8 as output_tokens,
        cost_usd::float8,
        started_at,
        finished_at,
        stability_state,
        relative_local_path
      from benchmark.live_trials
      where live_run_id = $1
      order by coalesce(finished_at, started_at) desc nulls last, trial_key
      limit $2
    `,
    [liveRunId, Math.min(Math.max(limit, 1), LIVE_TRIAL_LIMIT)]
  );
}

export async function getLiveArtifacts(
  liveRunId: string,
  limit = LIVE_ARTIFACT_LIMIT
): Promise<LiveArtifactRow[]> {
  return queryRows<LiveArtifactRow>(
    `
      select
        trial_key,
        artifact_type,
        relative_local_path,
        r2_uri,
        sha256,
        size_bytes::float8 as size_bytes,
        stability_state,
        uploaded_at
      from benchmark.live_artifacts
      where live_run_id = $1
      order by uploaded_at desc nulls last, relative_local_path
      limit $2
    `,
    [liveRunId, Math.min(Math.max(limit, 1), LIVE_ARTIFACT_LIMIT)]
  );
}
