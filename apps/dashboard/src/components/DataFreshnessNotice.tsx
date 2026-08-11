import {
  canonicalPublicationText,
  type DataFreshnessContract,
} from "../lib/data-freshness";

type DataFreshnessNoticeProps = {
  freshness: DataFreshnessContract;
};

function tokenLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function timestampLabel(value: string | null): string {
  if (value === null) return "Unavailable";
  const timestamp = new Date(value);
  if (!Number.isFinite(timestamp.getTime())) return "Unavailable";
  return timestamp.toISOString();
}

function ageLabel(seconds: number | null): string {
  if (seconds === null) return "Unavailable";
  if (seconds < 60) return `${Math.round(seconds)} seconds`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} minutes`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} hours`;
  return `${(seconds / 86400).toFixed(1)} days`;
}

export function DataFreshnessNotice({ freshness }: DataFreshnessNoticeProps) {
  const reviewed = freshness.sourceKind === "reviewed";
  const alert = freshness.queryStatus === "unavailable" || freshness.warningMessage !== null;

  return (
    <section
      className="quality-context-panel"
      data-freshness-status={freshness.freshnessStatus}
      data-query-status={freshness.queryStatus}
      aria-label={`Data provenance: ${freshness.sourceLabel}`}
    >
      <p>
        <strong>{freshness.sourceLabel}</strong>{" "}
        <span className="quality-badge">{tokenLabel(freshness.freshnessStatus)}</span>
      </p>
      <p><strong>Population:</strong> {freshness.populationLabel}</p>
      {reviewed ? (
        <>
          <p><strong>Source kind:</strong> Reviewed snapshot, not live inventory</p>
          <p>
            <strong>Reviewed:</strong> {freshness.reviewedAt ?? "Unavailable"}
            {freshness.schemaVersion ? <> · <strong>Schema:</strong> <code>{freshness.schemaVersion}</code></> : null}
          </p>
          {freshness.provenanceIdentifier ? (
            <p className="muted"><strong>Provenance:</strong> <code>{freshness.provenanceIdentifier}</code></p>
          ) : null}
        </>
      ) : (
        <>
          <p><strong>Source kind:</strong> Operational database</p>
          <p>
            <strong>Relations:</strong>{" "}
            {freshness.sourceRelations.map((relation, index) => (
              <span key={relation}>
                {index ? ", " : ""}<code>{relation}</code>
              </span>
            ))}
          </p>
          <p><strong>Query status:</strong> {tokenLabel(freshness.queryStatus)}</p>
          <p><strong>Latest included execution completion:</strong> {timestampLabel(freshness.latestIncludedExecutionAt)}</p>
          <p><strong>Canonical publication:</strong> {canonicalPublicationText(freshness)}</p>
          <p><strong>Queried/rendered at:</strong> {timestampLabel(freshness.queriedAt)}</p>
          <p><strong>Data age:</strong> {ageLabel(freshness.dataAgeSeconds)}</p>
          <p>
            <strong>Freshness:</strong> {tokenLabel(freshness.freshnessStatus)} ·{" "}
            {tokenLabel(freshness.freshnessReason)}
          </p>
        </>
      )}
      {alert ? (
        <p className="warning-text" role="alert">
          {freshness.warningMessage ?? "Operational data is unavailable."}
        </p>
      ) : null}
    </section>
  );
}
