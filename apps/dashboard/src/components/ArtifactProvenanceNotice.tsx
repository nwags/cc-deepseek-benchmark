import type { ArtifactProvenanceContract } from "../lib/artifact-content";
import { formatBytes } from "../lib/format";
import { sanitizeDisplayedUri } from "../lib/safe-display";

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export function ArtifactProvenanceNotice({ provenance }: {
  provenance: ArtifactProvenanceContract;
}) {
  const alert = provenance.warningMessage !== null
    || provenance.integrityStatus === "mismatch"
    || provenance.retrievalStatus === "unavailable";

  return (
    <section className="quality-context-panel" aria-label="Artifact byte provenance">
      <p><strong>{provenance.sourceLabel}</strong></p>
      <p><strong>Source kind:</strong> Artifact object storage</p>
      <p><strong>Object:</strong> <code>{sanitizeDisplayedUri(provenance.provenanceIdentifier) ?? "Not recorded"}</code></p>
      <p><strong>Retrieval status:</strong> {label(provenance.retrievalStatus)} · <strong>observed source:</strong> {label(provenance.retrievalSource)}</p>
      <p><strong>Preview completeness:</strong> {label(provenance.completenessStatus)}</p>
      <p>
        <strong>Stored expected size:</strong> {formatBytes(provenance.expectedSizeBytes)} ·{" "}
        <strong>remote observed size:</strong> {formatBytes(provenance.observedSizeBytes)} ·{" "}
        <strong>bytes read:</strong> {formatBytes(provenance.bytesRead)}
      </p>
      <p><strong>Expected SHA256:</strong> <code>{provenance.expectedSha256 ?? "Not recorded"}</code></p>
      <p><strong>Integrity:</strong> {label(provenance.integrityStatus)}</p>
      <p className="muted">Observed at {provenance.observedAt}. Retrieval time is not benchmark execution or canonical publication time.</p>
      {alert ? <p className="warning-text" role="alert">{provenance.warningMessage ?? "Artifact-byte evidence is unavailable or inconsistent."}</p> : null}
    </section>
  );
}
