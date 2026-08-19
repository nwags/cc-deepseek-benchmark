import { friendlyArmLabel } from "../lib/presentation-labels";
import {
  FAILURE_COMPOSITION_CATEGORIES,
  type FailureCompositionModel,
} from "../lib/failure-composition";

export type FailureCompositionPresentationState =
  | Readonly<{
      available: true;
      model: FailureCompositionModel;
    }>
  | Readonly<{
      available: false;
      message: string;
    }>;

type FailureCompositionProvenance = Readonly<{
  snapshotId: string;
  sourceGeneratedAt: string;
  scopeFingerprint: string;
}>;

function share(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function categoryClassName(id: string): string {
  return [
    "failure-composition-segment",
    `failure-composition-segment-${id.replaceAll("_", "-")}`,
  ].join(" ");
}

export function FailureCompositionPanel({
  state,
  provenance,
}: {
  state: FailureCompositionPresentationState;
  provenance: FailureCompositionProvenance | null;
}) {
  if (!state.available) {
    return (
      <section
        className="panel failure-composition-panel"
        id="failure-composition"
        aria-labelledby="failure-composition-heading"
      >
        <div className="panel-heading">
          <div>
            <h2 id="failure-composition-heading">
              Failure composition by arm{" "}
              <span className="derived-label">derived</span>
            </h2>
            <p>
              Frozen Phase 3 extended raw-failure composition.
            </p>
          </div>
          <span className="quality-badge quality-badge-warn">
            unavailable
          </span>
        </div>
        <div className="evidence-warning">
          <strong>Failure composition unavailable.</strong>{" "}
          {state.message} No operational source is substituted.
        </div>
      </section>
    );
  }

  const { model } = state;
  const maxRawFailures = Math.max(
    1,
    ...model.arms.map((arm) => arm.rawFailureCount),
  );

  return (
    <section
      className="panel failure-composition-panel"
      id="failure-composition"
      aria-labelledby="failure-composition-heading"
    >
      <div className="panel-heading">
        <div>
          <h2 id="failure-composition-heading">
            Failure composition by arm{" "}
            <span className="derived-label">derived</span>
          </h2>
          <p>
            One display-only DR-302 bucket per raw benchmark failure
            in the frozen Phase 3 extended reviewed corpus.
          </p>
        </div>
        <span className="quality-badge">manifest verified</span>
      </div>

      <div
        className="failure-composition-provenance"
        aria-label="Failure composition provenance"
      >
        <strong>{model.scopeId}</strong>
        <span>{model.trialCount} exact reviewed trials</span>
        <span>{model.armCount} arms</span>
        <span>{model.rawFailureCount} raw failures</span>
        {provenance ? (
          <>
            <span>{provenance.snapshotId}</span>
            <span>
              source review {provenance.sourceGeneratedAt}
            </span>
            <span>
              scope fingerprint{" "}
              <code>{provenance.scopeFingerprint}</code>
            </span>
          </>
        ) : null}
      </div>

      <div className="failure-composition-summary-grid">
        <article>
          <span className="metric-label">Stack denominator</span>
          <strong>{model.rawFailureCount}</strong>
          <span>raw_outcome = failure</span>
        </article>
        <article>
          <span className="metric-label">Excluded successes</span>
          <strong>{model.successCount}</strong>
          <span>remain successful raw outcomes</span>
        </article>
        <article>
          <span className="metric-label">Excluded not recorded</span>
          <strong>{model.notRecordedCount}</strong>
          <span>not converted into failures</span>
        </article>
        <article>
          <span className="metric-label">
            Successful timeout anomaly
          </span>
          <strong>
            {model.successfulTimeoutAfterMeaningfulActivityCount}
          </strong>
          <span>successful outcomes excluded from this stack</span>
        </article>
      </div>

      <p className="failure-composition-note">
        The seven segments are a presentation partition only. They do
        not change J2 classifier precedence or any raw benchmark field.
        Counts use one shared failure-count scale across all arms, so an
        arm with fewer failures has a shorter total bar.
      </p>

      <ul
        className="failure-composition-legend"
        aria-label="Failure composition categories"
      >
        {FAILURE_COMPOSITION_CATEGORIES.map((category) => (
          <li key={category.id}>
            <i
              className={categoryClassName(category.id)}
              aria-hidden="true"
            />
            <span>
              <strong>{category.label}</strong>
              <small>{category.description}</small>
            </span>
          </li>
        ))}
      </ul>

      <div
        className="failure-composition-chart"
        aria-hidden="true"
      >
        {model.arms.map((arm) => (
          <div
            className="failure-composition-chart-row"
            key={arm.armId}
          >
            <div className="failure-composition-arm">
              <strong>{friendlyArmLabel(arm.armId)}</strong>
              <code>{arm.armId}</code>
              <span>{arm.rawFailureCount} raw failures</span>
            </div>

            <div className="failure-composition-track">
              {arm.categories.map((category) => {
                if (category.count === 0) return null;
                const width =
                  (category.count / maxRawFailures) * 100;
                return (
                  <span
                    key={category.id}
                    className={categoryClassName(category.id)}
                    style={{ width: `${width}%` }}
                    title={`${category.label}: ${category.count}`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="failure-composition-note">
        Exact values are provided in the table below rather than only
        through color or hover.
      </p>

      <div className="table-wrap">
        <table className="failure-composition-table">
          <caption className="sr-only">
            DR-302 failure composition counts and shares by arm.
            Shares use each arm&apos;s raw-failure count as the
            denominator.
          </caption>
          <thead>
            <tr>
              <th className="sticky-id-column">Arm</th>
              <th>Raw failures</th>
              {FAILURE_COMPOSITION_CATEGORIES.map((category) => (
                <th key={category.id}>{category.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {model.arms.map((arm) => (
              <tr key={arm.armId}>
                <td className="sticky-id-column">
                  <strong>{friendlyArmLabel(arm.armId)}</strong>
                  <div className="muted mono">{arm.armId}</div>
                </td>
                <td>
                  <strong>{arm.rawFailureCount}</strong>
                  <div className="muted">
                    of {arm.trialCount} reviewed trials
                  </div>
                </td>
                {arm.categories.map((category) => (
                  <td key={category.id}>
                    <span className="failure-composition-table-value">
                      <strong>{category.count}</strong>
                      <span className="muted">
                        {share(category.shareOfRawFailures)}
                      </span>
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="failure-composition-boundary">
        <p>
          <strong>Unknown / incomplete evidence</strong> is a
          conservative residual, not an alias for missing evidence.
          Of the {model.residualBreakdown.count} residual raw failures,{" "}
          {model.residualBreakdown.evidenceCompleteCount} are
          evidence-complete and{" "}
          {model.residualBreakdown.evidenceIncompleteCount} are
          evidence-incomplete. Confidence is{" "}
          {model.residualBreakdown.highConfidenceCount} high and{" "}
          {model.residualBreakdown.mediumConfidenceCount} medium.
          Trajectory disposition is{" "}
          {model.residualBreakdown.noSubstantiveAttemptCount}{" "}
          <code>no_substantive_attempt</code> and{" "}
          {model.residualBreakdown.indeterminateCount}{" "}
          <code>indeterminate</code>.
        </p>
        <p>
          No category count links to an operational or similarly named
          filter because those destinations do not reproduce the exact
          DR-302 display-partition predicate.
        </p>
      </div>
    </section>
  );
}
