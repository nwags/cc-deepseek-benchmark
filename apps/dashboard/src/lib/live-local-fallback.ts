import fs from "node:fs";
import path from "node:path";
import {
  LIVE_EVENT_LIMIT,
  LIVE_RUN_LIMIT,
  LIVE_STALE_AFTER_SECONDS,
  LiveEventRow,
  LiveRunRow
} from "./live-data";

type LocalRecord = {
  sequence?: number;
  event_type?: string;
  occurred_at?: string;
  timestamp?: string;
  elapsed_seconds?: number;
  live_run_id?: string;
  run_id?: string;
  stream?: string;
  message?: string;
  text?: string;
  payload?: Record<string, unknown>;
  arm_id?: string;
  phase?: string;
  mode?: string;
  run_kind?: string;
  status?: string;
  returncode?: number | null;
};

export type LocalLiveFallback = {
  directory: string;
  runs: LiveRunRow[];
  eventsByRun: Map<string, LiveEventRow[]>;
};

function readTailRecords(filePath: string, limit: number): LocalRecord[] {
  const stat = fs.statSync(filePath);
  const byteLimit = 512 * 1024;
  const start = Math.max(stat.size - byteLimit, 0);
  const length = stat.size - start;
  const buffer = Buffer.alloc(length);
  const descriptor = fs.openSync(filePath, "r");
  try {
    fs.readSync(descriptor, buffer, 0, length, start);
  } finally {
    fs.closeSync(descriptor);
  }
  let text = buffer.toString("utf8");
  if (start > 0) text = text.slice(text.indexOf("\n") + 1);
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-limit)
    .flatMap((line) => {
      try {
        return [JSON.parse(line) as LocalRecord];
      } catch {
        return [];
      }
    });
}

function metadata(record: LocalRecord): Record<string, unknown> {
  return { ...record, ...(record.payload ?? {}) };
}

function asRun(records: LocalRecord[], fileName: string): LiveRunRow {
  const first = records[0] ?? {};
  const last = records[records.length - 1] ?? first;
  const finished = [...records].reverse().find((record) => record.event_type === "run_finished");
  const values = { ...metadata(last), ...(finished ? metadata(finished) : {}) };
  const liveRunId = String(last.live_run_id ?? last.run_id ?? fileName.replace(/\.ndjson$/, ""));
  const occurredAt = String(last.occurred_at ?? last.timestamp ?? new Date(0).toISOString());
  const startedAt = String(first.occurred_at ?? first.timestamp ?? occurredAt);
  const active = !finished;
  const stale = active && Date.now() - Date.parse(occurredAt) > LIVE_STALE_AFTER_SECONDS * 1000;
  const status = finished ? String(values.status ?? "completed") : "running";

  return {
    live_run_id: liveRunId,
    arm_id: String(values.arm_id ?? "unknown"),
    phase: String(values.phase ?? "unknown"),
    mode: String(values.mode ?? "unknown"),
    run_kind: String(values.run_kind ?? "local"),
    scored: Boolean(values.scored),
    runner_name: typeof values.runner_name === "string" ? values.runner_name : null,
    github_run_id: typeof values.github_run_id === "string" ? values.github_run_id : null,
    github_run_attempt: Number(values.github_run_attempt) || null,
    github_job: typeof values.github_job === "string" ? values.github_job : null,
    status,
    display_status: stale ? "stale" : status,
    is_active: active,
    is_stale: stale,
    benchmark_status: typeof values.benchmark_status === "string" ? values.benchmark_status : null,
    live_publication_status: "local-development-fallback",
    progressive_artifact_status: null,
    canonical_publication_status: null,
    started_at: startedAt,
    finished_at: finished
      ? String(finished.occurred_at ?? finished.timestamp ?? occurredAt)
      : null,
    last_heartbeat_at: occurredAt,
    elapsed_seconds: typeof (finished ?? last).elapsed_seconds === "number"
      ? (finished ?? last).elapsed_seconds ?? null
      : null,
    expected_trial_count: null,
    completed_trial_count: 0,
    success_count: 0,
    failure_count: 0,
    exception_count: 0,
    observed_cost_usd: null,
    input_tokens: null,
    cache_tokens: null,
    output_tokens: null,
    event_count: records.length,
    returncode: typeof values.returncode === "number" ? values.returncode : null,
    latest_message: last.message ?? last.text ?? null,
    canonical_arm_run_id: null,
    provider_family: null,
    backend_model: null,
    router_model: null
  };
}

export function getLocalLiveFallback(): LocalLiveFallback {
  const directory = path.join(process.cwd(), ".run", "live");
  if (!fs.existsSync(directory)) {
    return { directory, runs: [], eventsByRun: new Map() };
  }

  const recordsByRun = fs
    .readdirSync(directory)
    .filter((name) => name.endsWith(".ndjson"))
    .map((name) => ({ name, records: readTailRecords(path.join(directory, name), LIVE_EVENT_LIMIT) }))
    .filter((item) => item.records.length > 0);
  const runs = recordsByRun
    .map((item) => asRun(item.records, item.name))
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
    .slice(0, LIVE_RUN_LIMIT);
  const eventsByRun = new Map<string, LiveEventRow[]>(
    recordsByRun.map((item) => {
      const run = asRun(item.records, item.name);
      const events = item.records.map((record, index): LiveEventRow => ({
        sequence: record.sequence ?? index + 1,
        event_type: record.event_type ?? "unknown",
        occurred_at: record.occurred_at ?? record.timestamp ?? run.started_at,
        elapsed_seconds: record.elapsed_seconds ?? null,
        stream: record.stream ?? null,
        message: record.message ?? record.text ?? null,
        payload: record.payload ?? {}
      }));
      return [run.live_run_id, events] as const;
    })
  );
  return { directory, runs, eventsByRun };
}
