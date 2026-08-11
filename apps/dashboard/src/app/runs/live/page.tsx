import Link from "next/link";
import { AppShell } from "../../../components/AppShell";
import { LiveAutoRefresh } from "../../../components/LiveAutoRefresh";
import { LiveLivenessNotice } from "../../../components/LiveLivenessNotice";
import {
  LIVE_STALE_AFTER_SECONDS,
  LiveArtifactRow,
  LiveEventRow,
  LiveRunRow,
  LiveTrialRow,
  getActiveLiveRuns,
  getLiveArtifacts,
  getLiveOutputEvents,
  getLiveRun,
  getLiveRunEvents,
  getLiveRunWarnings,
  getLiveToolEvents,
  getLiveTrials,
  getRecentLiveRuns,
  getStaleLiveRuns
} from "../../../lib/live-data";
import { buildLiveHeartbeatLiveness, findLatestObservedTimestamp } from "../../../lib/data-freshness";
import { LIVE_ROUTE_FRESHNESS_SOURCES } from "../../../lib/data-freshness-sources";
import { redactSecretsInText, sanitizeDisplayedUri } from "../../../lib/safe-display";

export const dynamic = "force-dynamic";

type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function fmtNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : Intl.NumberFormat("en-US").format(value);
}

function fmtMoney(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `$${value.toFixed(4)}`;
}

function fmtSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value < 120) return `${value.toFixed(1)}s`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function statusClass(status: string): string {
  if (status === "completed" || status === "finalized" || status === "succeeded") {
    return "status status-completed";
  }
  if (
    status === "failed"
    || status === "errors"
    || status === "exception"
    || status === "interrupted"
    || status === "stale"
  ) {
    return "status status-errors";
  }
  return "status";
}

function modelLabel(run: LiveRunRow | null | undefined): string {
  return redactSecretsInText(run?.backend_model ?? run?.router_model ?? run?.provider_family ?? "—");
}

function safeText(value: string | null | undefined, fallback = "—"): string {
  return value ? redactSecretsInText(value) : fallback;
}

const OUTPUT_EVENT_TYPES = new Set(["process_output_chunk", "agent_output_chunk"]);
const TOOL_EVENT_TYPES = new Set(["tool_call_started", "tool_result", "tool_call_finished"]);
const WARNING_TEXT = /(^|[^a-z])(warning|warn|error|exception|fatal)([^a-z]|$)/i;

function isOutputEvent(event: LiveEventRow): boolean {
  return OUTPUT_EVENT_TYPES.has(event.event_type);
}

function isToolEvent(event: LiveEventRow): boolean {
  return TOOL_EVENT_TYPES.has(event.event_type);
}

function payloadString(event: LiveEventRow, key: string): string | null {
  const value = event.payload?.[key];
  return typeof value === "string" ? value : null;
}

function isWarningEvent(event: LiveEventRow): boolean {
  return event.event_type === "publication_warning"
    || event.event_type === "runtime_warning"
    || (
      event.event_type === "tool_call_finished"
      && payloadString(event, "status") === "failed"
    )
    || (isOutputEvent(event) && WARNING_TEXT.test(event.message ?? ""));
}

function formatOutput(events: LiveEventRow[]): string {
  const lines = events.map(
    (event) => `[${safeText(event.stream, "out")}] ${safeText(event.message, "")}`
  );
  return lines.join("\n") || "No observable process output is available yet.";
}

async function loadLocalFallback(selectedId?: string) {
  const { getLocalLiveFallback } = await import("../../../lib/live-local-fallback");
  const local = getLocalLiveFallback();
  const selected = local.runs.find((run) => run.live_run_id === selectedId) ?? local.runs[0] ?? null;
  const events = selected ? local.eventsByRun.get(selected.live_run_id) ?? [] : [];
  return {
    runs: local.runs,
    active: local.runs.filter((run) => run.is_active),
    stale: local.runs.filter((run) => run.is_stale),
    selected,
    events,
    outputEvents: events.filter(isOutputEvent),
    warningEvents: events.filter(isWarningEvent),
    toolEvents: events.filter(isToolEvent),
    trials: [] as LiveTrialRow[],
    artifacts: [] as LiveArtifactRow[],
    localDirectory: local.directory
  };
}

export default async function LiveRunsPage({
  searchParams
}: {
  searchParams?: PageSearchParams;
}) {
  const params = searchParams ? await searchParams : {};
  const requestedId = firstParam(params.live_run_id)?.trim() || undefined;
  let runs: LiveRunRow[] = [];
  let active: LiveRunRow[] = [];
  let stale: LiveRunRow[] = [];
  let selected: LiveRunRow | null = null;
  let events: LiveEventRow[] = [];
  let outputEvents: LiveEventRow[] = [];
  let warningEvents: LiveEventRow[] = [];
  let toolEvents: LiveEventRow[] = [];
  let trials: LiveTrialRow[] = [];
  let artifacts: LiveArtifactRow[] = [];
  let errorState: "migration" | "database" | null = null;
  let usingLocalFallback = false;
  let localDirectory: string | null = null;
  let cloudActiveRuns: LiveRunRow[] = [];
  let cloudEvents: LiveEventRow[] = [];

  try {
    [runs, active, stale] = await Promise.all([
      getRecentLiveRuns(),
      getActiveLiveRuns(),
      getStaleLiveRuns()
    ]);
    cloudActiveRuns = active;
    const selectedId = requestedId ?? runs[0]?.live_run_id;
    if (selectedId) {
      [selected, events, outputEvents, warningEvents, toolEvents, trials, artifacts] = await Promise.all([
        getLiveRun(selectedId),
        getLiveRunEvents(selectedId),
        getLiveOutputEvents(selectedId),
        getLiveRunWarnings(selectedId),
        getLiveToolEvents(selectedId),
        getLiveTrials(selectedId),
        getLiveArtifacts(selectedId)
      ]);
      cloudEvents = [...events, ...outputEvents, ...toolEvents];
    }
  } catch (error) {
    const code = typeof error === "object" && error && "code" in error ? String(error.code) : "";
    errorState = code === "42P01" || code === "3F000" ? "migration" : "database";
    if (process.env.DASHBOARD_LIVE_LOCAL_FALLBACK === "true") {
      try {
        const fallback = await loadLocalFallback(requestedId);
        ({
          runs,
          active,
          stale,
          selected,
          events,
          outputEvents,
          warningEvents,
          toolEvents,
          trials,
          artifacts,
          localDirectory
        } = fallback);
        usingLocalFallback = true;
      } catch {
        localDirectory = null;
      }
    }
  }

  const refreshEnabled = active.some((run) => !run.is_stale);
  const outputHistory = formatOutput(outputEvents);
  const observedAt = new Date().toISOString();
  const cloudHeartbeatAt = findLatestObservedTimestamp(
    cloudActiveRuns.map((run) => run.last_heartbeat_at),
  ).latestTimestamp;
  const cloudEventAt = findLatestObservedTimestamp(
    cloudEvents.map((event) => event.occurred_at),
  ).latestTimestamp;
  const cloudLiveness = buildLiveHeartbeatLiveness({
    queryStatus: errorState ? "unavailable" : "available",
    observedAt,
    latestHeartbeatAt: errorState ? null : cloudHeartbeatAt,
    latestEventAt: errorState ? null : cloudEventAt,
    heartbeatThresholdSeconds: LIVE_STALE_AFTER_SECONDS,
  });
  const localLiveness = usingLocalFallback
    ? buildLiveHeartbeatLiveness({
        queryStatus: "available",
        observedAt,
        latestHeartbeatAt: findLatestObservedTimestamp(
          active.map((run) => run.last_heartbeat_at),
        ).latestTimestamp,
        latestEventAt: findLatestObservedTimestamp(
          events.map((event) => event.occurred_at),
        ).latestTimestamp,
        heartbeatThresholdSeconds: LIVE_STALE_AFTER_SECONDS,
      })
    : null;

  return (
    <AppShell
      title="Live Runs"
      description="Shared execution state published by remote benchmark runners to Supabase, with progressive artifact availability in R2."
    >
      <LiveAutoRefresh enabled={refreshEnabled} />

      <LiveLivenessNotice
        source={LIVE_ROUTE_FRESHNESS_SOURCES.liveRunsCloud}
        liveness={cloudLiveness}
      />
      {localLiveness ? (
        <LiveLivenessNotice
          source={LIVE_ROUTE_FRESHNESS_SOURCES.localFallback}
          liveness={localLiveness}
        />
      ) : null}

      <section className="quality-context-panel">
        <strong>Observable activity only.</strong> Process output, heartbeats, and artifact state shown here are not hidden or private model reasoning. Partial trial results can change until final canonical ingestion completes.
      </section>

      {errorState ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>{errorState === "migration" ? "Live schema is not available" : "Live database is unavailable"}</h2>
              <p>
                {usingLocalFallback
                  ? `Using the explicitly enabled local-development fallback${localDirectory ? ` at ${safeText(localDirectory)}` : ""}.`
                  : errorState === "migration"
                    ? "Apply the live supervision migration before using shared live state."
                    : "The canonical dashboard remains separate; live state will return when the database connection recovers."}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Recent runs</div>
          <div className="metric-value">{runs.length}</div>
          <div className="metric-detail">{usingLocalFallback ? "local development" : "shared Supabase"}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Active</div>
          <div className="metric-value">{active.length}</div>
          <div className="metric-detail">refreshes every 8 seconds</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Stale</div>
          <div className="metric-value">{stale.length}</div>
          <div className="metric-detail">&gt; {LIVE_STALE_AFTER_SECONDS}s since heartbeat</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Selected arm</div>
          <div className="metric-value">{selected?.arm_id ?? "—"}</div>
          <div className="metric-detail">{modelLabel(selected ?? runs[0])}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Trials</div>
          <div className="metric-value">{selected ? `${selected.completed_trial_count}/${selected.expected_trial_count ?? "?"}` : "—"}</div>
          <div className="metric-detail">stable completed evidence</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Observed cost</div>
          <div className="metric-value">{fmtMoney(selected?.observed_cost_usd)}</div>
          <div className="metric-detail">partial and subject to reconciliation</div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Recent shared executions</h2>
            <p>Runner display names are opaque infrastructure identities; labels control routing.</p>
          </div>
        </div>
        {runs.length === 0 ? (
          <div className="placeholder-body">
            {errorState
              ? "No shared live rows are available."
              : "No live runs have been published. Dry runs appear here only when supervision is enabled."}
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Execution</th>
                  <th>Arm / model</th>
                  <th>Mode</th>
                  <th>Runner</th>
                  <th>GitHub run</th>
                  <th>Status</th>
                  <th>Trials</th>
                  <th>Heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.live_run_id}>
                    <td><Link className="mono" href={`/runs/live?live_run_id=${encodeURIComponent(run.live_run_id)}`}>{run.live_run_id}</Link></td>
                    <td><div className="mono">{run.arm_id}</div><div className="muted">{modelLabel(run)}</div></td>
                    <td>{run.phase} / {run.mode}<div className="muted">{run.run_kind}{run.scored ? " · scored" : " · non-scored"}</div></td>
                    <td className="mono">{run.runner_name ?? "—"}</td>
                    <td>{run.github_run_id ?? "—"}<div className="muted">attempt {run.github_run_attempt ?? "—"}</div></td>
                    <td><span className={statusClass(run.display_status)}>{run.display_status}</span></td>
                    <td>{run.completed_trial_count}/{run.expected_trial_count ?? "?"}</td>
                    <td>{fmtDate(run.last_heartbeat_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected ? (
        <>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Selected execution</h2>
                <p className="mono">{selected.live_run_id}</p>
                <p>{safeText(selected.latest_message, "No publication message yet.")}</p>
              </div>
              <span className={statusClass(selected.display_status)}>{selected.display_status}</span>
            </div>
            <div className="detail-grid">
              <div><span>Benchmark</span><strong>{selected.benchmark_status ?? "pending"}</strong></div>
              <div><span>Live publication</span><strong>{selected.live_publication_status ?? "pending"}</strong></div>
              <div><span>Progressive artifacts</span><strong>{selected.progressive_artifact_status ?? "pending"}</strong></div>
              <div><span>Canonical publication</span><strong>{selected.canonical_publication_status ?? "pending"}</strong></div>
              <div><span>Started</span><strong>{fmtDate(selected.started_at)}</strong></div>
              <div><span>Finished</span><strong>{fmtDate(selected.finished_at)}</strong></div>
              <div><span>Last heartbeat</span><strong>{fmtDate(selected.last_heartbeat_at)}</strong></div>
              <div><span>Elapsed</span><strong>{fmtSeconds(selected.elapsed_seconds)}</strong></div>
              <div><span>Events</span><strong>{fmtNumber(selected.event_count)}</strong></div>
              <div><span>Completed / success</span><strong>{selected.completed_trial_count} / {selected.success_count}</strong></div>
              <div><span>Failure / exception</span><strong>{selected.failure_count} / {selected.exception_count}</strong></div>
              <div><span>Return code</span><strong>{selected.returncode ?? "—"}</strong></div>
              <div><span>Input tokens</span><strong>{fmtNumber(selected.input_tokens)}</strong></div>
              <div><span>Cache tokens</span><strong>{fmtNumber(selected.cache_tokens)}</strong></div>
              <div><span>Output tokens</span><strong>{fmtNumber(selected.output_tokens)}</strong></div>
            </div>
          </section>

          <section className="panel warning-panel">
            <div className="panel-heading">
              <div>
                <h2>Warnings and diagnostic signals</h2>
                <p>
                  {warningEvents.length} preserved warning events, queried independently from the rolling output history.
                </p>
              </div>
            </div>
            {warningEvents.length === 0 ? (
              <div className="placeholder-body">No warning signals have been observed for this execution.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Seq</th><th>Time</th><th>Event</th><th>Stream</th><th>Message</th></tr></thead>
                  <tbody>{warningEvents.map((event) => (
                    <tr key={`warning-${event.sequence}`}>
                      <td>{event.sequence}</td>
                      <td>{fmtDate(event.occurred_at)}</td>
                      <td>{safeText(event.event_type)}</td>
                      <td>{safeText(event.stream)}</td>
                      <td className="live-message">{safeText(event.message)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Tool activity</h2>
                <p>
                  {toolEvents.length} structured lifecycle events parsed incrementally from Claude Code tool-use and tool-result records. Thinking and reasoning content is not parsed or displayed.
                </p>
              </div>
            </div>
            {toolEvents.length === 0 ? (
              <div className="placeholder-body">No structured tool activity has been observed for this execution.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Seq</th><th>Time</th><th>Trial</th><th>Tool</th><th>Event</th><th>Status</th><th>Summary</th></tr></thead>
                  <tbody>{toolEvents.map((event) => (
                    <tr key={`tool-${event.sequence}`}>
                      <td>{event.sequence}</td>
                      <td>{fmtDate(payloadString(event, "source_timestamp") ?? event.occurred_at)}</td>
                      <td className="mono">{safeText(payloadString(event, "trial_key"))}</td>
                      <td>{safeText(payloadString(event, "tool_name"), "unknown")}</td>
                      <td>{safeText(event.event_type)}</td>
                      <td>{safeText(payloadString(event, "status"))}</td>
                      <td className="live-message">{safeText(event.message)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Observable output history</h2>
                <p>
                  Showing {outputEvents.length} latest process or agent output events from a dedicated output-only query.
                </p>
              </div>
            </div>
            <pre className="content-preview content-preview-compact">{outputHistory}</pre>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Partial trials</h2>
                <p>Only trials with stable parseable completion evidence are summarized.</p>
              </div>
            </div>
            {trials.length === 0 ? <div className="placeholder-body">No completed stable trials have been published yet.</div> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Trial</th><th>Task</th><th>Status</th><th>Reward</th><th>Runtime</th><th>Tokens</th><th>Cost</th><th>Exception</th></tr></thead>
                  <tbody>{trials.map((trial) => (
                    <tr key={trial.trial_key}>
                      <td className="mono">{trial.trial_key}</td>
                      <td>{trial.task_id ?? "—"}</td>
                      <td><span className={statusClass(trial.status)}>{trial.status}</span></td>
                      <td>{trial.reward ?? "—"}</td>
                      <td>{fmtSeconds(trial.runtime_seconds)}</td>
                      <td>{fmtNumber((trial.input_tokens ?? 0) + (trial.cache_tokens ?? 0) + (trial.output_tokens ?? 0))}</td>
                      <td>{fmtMoney(trial.cost_usd)}</td>
                      <td title={trial.exception_summary ? safeText(trial.exception_summary) : undefined}>{safeText(trial.exception_type)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Progressive artifacts</h2>
                <p>Stable completed-trial files only. Final publication reconciles anything not uploaded here.</p>
              </div>
            </div>
            {artifacts.length === 0 ? <div className="placeholder-body">No progressive artifacts are available.</div> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Trial</th><th>Type</th><th>Path</th><th>Size</th><th>State</th><th>R2</th><th>Content</th></tr></thead>
                  <tbody>{artifacts.map((artifact) => (
                    <tr key={artifact.artifact_id}>
                      <td className="mono">{artifact.trial_key ?? "run root"}</td>
                      <td>{artifact.artifact_type}</td>
                      <td className="mono">{sanitizeDisplayedUri(artifact.relative_local_path)}</td>
                      <td>{fmtNumber(artifact.size_bytes)} B</td>
                      <td>{artifact.stability_state}</td>
                      <td>{artifact.r2_uri ? "available" : "pending"}</td>
                      <td><Link href={`/live-artifacts/${encodeURIComponent(artifact.artifact_id)}`}>Preview</Link></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Event tail</h2>
                <p>{events.length} latest status, lifecycle, diagnostic, and publication events.</p>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Seq</th><th>Time</th><th>Event</th><th>Stream</th><th>Message</th></tr></thead>
                <tbody>{events.map((event) => (
                  <tr key={event.sequence}>
                    <td>{event.sequence}</td>
                    <td>{fmtDate(event.occurred_at)}</td>
                    <td>{safeText(event.event_type)}</td>
                    <td>{safeText(event.stream)}</td>
                    <td className="live-message">{safeText(event.message)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}
