import Link from "next/link";
import {
  getFailureTaxonomyAxis,
  type FailureTaxonomyAxisId,
} from "../lib/failure-taxonomy";
import {
  FAILURE_TAXONOMY_AXIS_IDS,
  type FailureTaxonomyDiagnosis,
  type FailureTaxonomyTrialJoin,
} from "../lib/failure-taxonomy-snapshot";

function filterHref(axisId: FailureTaxonomyAxisId, value: string) {
  const query = new URLSearchParams({ [axisId]: value });
  return `/trial-quality?${query.toString()}#failure-taxonomy`;
}

function ConfidenceBadge({ diagnosis }: { diagnosis: FailureTaxonomyDiagnosis }) {
  return (
    <span className={diagnosis.confidence === "high" ? "quality-badge" : "quality-badge quality-badge-warn"}>
      {diagnosis.confidence} confidence
    </span>
  );
}

export function FailureTaxonomyCompactDiagnosis({
  axisId,
  diagnosis,
}: {
  axisId: FailureTaxonomyAxisId;
  diagnosis: FailureTaxonomyDiagnosis;
}) {
  return (
    <div className="taxonomy-compact-diagnosis">
      <Link href={filterHref(axisId, diagnosis.value)}>{diagnosis.label}</Link>
      <span>{diagnosis.confidence}</span>
      {diagnosis.manual_review_required ? <strong>review</strong> : null}
    </div>
  );
}

export function FailureTaxonomyDetails({ result }: { result: FailureTaxonomyTrialJoin }) {
  if (result.status === "unavailable") {
    return (
      <section className="panel warning-panel" id="failure-taxonomy" aria-labelledby="failure-taxonomy-heading">
        <div className="panel-heading">
          <div>
            <h2 id="failure-taxonomy-heading">Frozen failure and trajectory taxonomy</h2>
            <p>{result.message}</p>
          </div>
          <span className="derived-label">unavailable</span>
        </div>
        <p className="taxonomy-boundary-note">
          No database, live artifact, or browser-side classification is used as a fallback for this frozen J2 diagnosis.
        </p>
      </section>
    );
  }

  const { trial, provenance } = result;
  return (
    <section className="panel taxonomy-detail-panel" id="failure-taxonomy" aria-labelledby="failure-taxonomy-heading">
      <div className="panel-heading">
        <div>
          <h2 id="failure-taxonomy-heading">Frozen failure and trajectory taxonomy <span className="derived-label">derived</span></h2>
          <p>
            Offline second-stage interpretation joined only by this trial&apos;s exact canonical ID. Raw outcome and the
            accepted review axes remain independent source facts.
          </p>
        </div>
        <span className="quality-badge">manifest verified</span>
      </div>
      <div className="taxonomy-axis-detail-grid">
        {FAILURE_TAXONOMY_AXIS_IDS.map((axisId) => {
          const axis = getFailureTaxonomyAxis(axisId);
          const diagnosis = trial[axisId];
          return (
            <article key={axisId}>
              <div className="taxonomy-axis-detail-heading">
                <div>
                  <span>{axis.label}</span>
                  <h3>{diagnosis.label}</h3>
                </div>
                <ConfidenceBadge diagnosis={diagnosis} />
              </div>
              <p>{diagnosis.definition}</p>
              <p className="muted">{axis.definition}</p>
              <div className="taxonomy-review-state">
                <strong>Manual review:</strong>{" "}
                {diagnosis.manual_review_required ? "required for this derived diagnosis" : "not required by the J2 rule"}
              </div>
              <details>
                <summary>Structured evidence basis</summary>
                <ul className="taxonomy-evidence-list">
                  {diagnosis.evidence_basis.map((fact) => <li key={fact}><code>{fact}</code></li>)}
                </ul>
              </details>
              <div className="taxonomy-artifact-links">
                <strong>Supporting artifacts</strong>
                {diagnosis.supporting_artifact_ids.length ? (
                  <ul>
                    {diagnosis.supporting_artifact_ids.map((artifactId) => (
                      <li key={artifactId}>
                        <Link href={`/artifacts/${encodeURIComponent(artifactId)}`}>Open artifact <span className="mono">{artifactId}</span></Link>
                      </li>
                    ))}
                  </ul>
                ) : <span className="muted">No artifact ID is required for this rule.</span>}
              </div>
              <p className="taxonomy-axis-actions">
                <Link href={filterHref(axisId, diagnosis.value)}>Filter Trial Quality to exact value</Link>
              </p>
            </article>
          );
        })}
      </div>
      <div className="taxonomy-provenance" aria-label="Failure taxonomy snapshot provenance">
        <strong>Frozen snapshot provenance</strong>
        <span>{provenance.snapshotId}</span>
        <span>{provenance.scope}</span>
        <span>{provenance.trialCount} exact trial IDs</span>
        <span>taxonomy {provenance.taxonomyVersion}</span>
        <span>classifier {provenance.classifierVersion}</span>
        <span>source review {provenance.sourceGeneratedAt}</span>
        <span>scope fingerprint <code>{provenance.scopeFingerprint}</code></span>
      </div>
      <p className="taxonomy-boundary-note">
        This snapshot retains structured evidence facts and artifact identifiers only. It does not retain or infer hidden/private reasoning and does not replace raw benchmark truth.
      </p>
    </section>
  );
}
