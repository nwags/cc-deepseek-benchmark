import type { LiveHeartbeatLivenessContract } from "../lib/data-freshness";
import type { LiveRouteSourceDefinition } from "../lib/data-freshness-sources";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function timestamp(value: string | null): string {
  if (value === null) return "Unavailable";
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed.toISOString() : "Unavailable";
}

export function LiveLivenessNotice({
  source,
  liveness,
}: {
  source: LiveRouteSourceDefinition;
  liveness: LiveHeartbeatLivenessContract;
}) {
  const localFallback = source.sourceKind === "local_fallback";
  const alert = liveness.warningMessage !== null || liveness.queryStatus === "unavailable";
  return (
    <section
      className="quality-context-panel"
      data-live-liveness-status={liveness.livenessStatus}
      data-query-status={liveness.queryStatus}
      aria-label={`Live source provenance: ${source.sourceLabel}`}
    >
      <p><strong>{source.sourceLabel}</strong> <span className="quality-badge">{label(liveness.livenessStatus)}</span></p>
      <p><strong>Source kind:</strong> {localFallback ? "Local development fallback, not cloud state" : "Cloud operational database"}</p>
      <p><strong>Population:</strong> {source.populationLabel}</p>
      {source.sourceRelations.length ? (
        <p><strong>Relations:</strong> {source.sourceRelations.map((relation, index) => (
          <span key={relation}>{index ? ", " : ""}<code>{relation}</code></span>
        ))}</p>
      ) : null}
      {source.provenanceIdentifier ? <p><strong>Fallback path pattern:</strong> <code>{source.provenanceIdentifier}</code></p> : null}
      <p><strong>Source query status:</strong> {label(liveness.queryStatus)}</p>
      <p><strong>Latest heartbeat/observation:</strong> {timestamp(liveness.latestHeartbeatAt)}</p>
      <p><strong>Latest selected-run event:</strong> {timestamp(liveness.latestEventAt)}</p>
      <p><strong>Observed/rendered at:</strong> {timestamp(liveness.observedAt)}</p>
      <p><strong>Heartbeat age:</strong> {liveness.heartbeatAgeSeconds === null ? "Unavailable" : `${liveness.heartbeatAgeSeconds.toFixed(1)} seconds`}</p>
      <p><strong>Live heartbeat policy:</strong> {liveness.heartbeatThresholdSeconds} seconds; applies only to live reporting liveness.</p>
      <p><strong>Liveness:</strong> {label(liveness.livenessStatus)} · {label(liveness.livenessReason)}</p>
      <p><strong>Canonical publication time:</strong> {localFallback ? "Not applicable to local fallback" : "Not recorded"}</p>
      {alert ? <p className="warning-text" role="alert">{liveness.warningMessage ?? "Live source evidence is unavailable."}</p> : null}
    </section>
  );
}
