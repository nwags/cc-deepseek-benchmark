import {
  EVIDENCE_SOURCE_SCOPE_NOTE,
  evidenceSourceScopeLabel,
  selectEvidenceSourceScope,
} from "../lib/evidence-links";

export function EvidenceSourceContextNotice({
  value,
}: {
  value: string | readonly string[] | null | undefined;
}) {
  const selection = selectEvidenceSourceScope(value);

  if (selection.warningMessage) {
    return <p className="warning-text" role="alert">{selection.warningMessage}</p>;
  }
  if (!selection.sourceScope) return null;

  return (
    <section className="quality-context-panel" aria-label="Evidence navigation context">
      <strong>Opened from:</strong> {evidenceSourceScopeLabel(selection.sourceScope)}. {EVIDENCE_SOURCE_SCOPE_NOTE}
    </section>
  );
}
