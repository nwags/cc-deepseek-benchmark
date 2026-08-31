import Link from "next/link";

import { friendlyArmLabel } from "../lib/presentation-labels";
import { formatTruncatedCurrency } from "../lib/format";
import {
  SPEND_DECOMPOSITION_KIMI_ARM_ID,
  SPEND_DECOMPOSITION_SEGMENTS,
  getSpendDecompositionSegment,
  type SpendDecompositionModel,
  type SpendDecompositionSegmentId,
} from "../lib/spend-decomposition";

export type SpendDecompositionPresentationState =
  | Readonly<{
      available: true;
      model: SpendDecompositionModel;
    }>
  | Readonly<{
      available: false;
      message: string;
    }>;

export type SpendDecompositionPanelProvenance = Readonly<{
  coreCostPath: string;
  coreCostSha256: string;
  reviewPath: string;
  reviewSha256: string;
  coreTrialCount: number;
  reviewTrialCount: number;
}>;

export type SpendDecompositionArmLinks = Readonly<
  Record<
    string,
    Readonly<{
      armEvidenceHref: string;
      costProvenanceHref: string;
    }>
  >
>;

const SEGMENT_DESCRIPTIONS: Readonly<
  Record<SpendDecompositionSegmentId, string>
> = Object.freeze({
  clean_success:
    "Recorded trial-cost dollars for clean successful outcomes.",
  normal_failure:
    "Recorded trial-cost dollars for failures without a retained exception.",
  exception_failure:
    "Recorded trial-cost dollars for non-success outcomes with a retained exception.",
  exception_with_success_signal:
    "Recorded trial-cost dollars for successful outcomes that also retained an exception signal.",
});

function displayedUsd(value: string): string {
  return formatTruncatedCurrency(value);
}

function evidenceLabel(value: string): string {
  return value.split("_").join(" ");
}

function selectedCostBasisLabel(
  value:
    | "adjusted_known_cost"
    | "qualified_retained_rate_estimate",
): string {
  return value === "qualified_retained_rate_estimate"
    ? "Qualified retained-rate estimate"
    : "Adjusted known cost";
}

function scopeCostBasisLabel(
  value:
    | "adjusted_known_cost"
    | "qualified_adjusted_cost_estimate",
): string {
  return value === "qualified_adjusted_cost_estimate"
    ? "Qualified adjusted-cost estimate"
    : "Adjusted known cost";
}

function segmentClassName(id: string): string {
  return [
    "spend-decomposition-segment",
    `spend-decomposition-segment-${id.replaceAll("_", "-")}`,
  ].join(" ");
}

function geometryUsd(value: string): number {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error("invalid_spend_decomposition_geometry_value");
  }
  return amount;
}

function displayedArmValue(
  value: string,
  href: string | undefined,
) {
  const formatted = displayedUsd(value);
  return href ? <Link href={href}>{formatted}</Link> : formatted;
}

export function SpendDecompositionPanel({
  state,
  provenance,
  armLinks,
}: {
  state: SpendDecompositionPresentationState;
  provenance: SpendDecompositionPanelProvenance | null;
  armLinks: SpendDecompositionArmLinks;
}) {
  if (!state.available) {
    return (
      <section
        className="panel spend-decomposition-panel"
        id="spend-decomposition"
        aria-labelledby="spend-decomposition-heading"
      >
        <div className="panel-heading">
          <div>
            <h2 id="spend-decomposition-heading">
              Historical DR-303 outcome-cost reconstruction{" "}
              <span className="derived-label">derived</span>
            </h2>
            <p>
              Frozen reviewed cost decomposition for the selected
              Phase 3 scope.
            </p>
          </div>
          <span className="quality-badge quality-badge-warn">
            unavailable
          </span>
        </div>
        <div className="evidence-warning">
          <strong>Spend decomposition unavailable.</strong>{" "}
          {state.message} No operational source is substituted.
        </div>
      </section>
    );
  }

  const { model } = state;

  const maxSelectedCost = Math.max(
    1,
    ...model.arms.map((arm) =>
      geometryUsd(arm.selectedReviewedCostUsd),
    ),
  );

  const exceptionSuccess =
    getSpendDecompositionSegment(
      model,
      "exception_with_success_signal",
    );

  const kimi =
    model.arms.find(
      (arm) =>
        arm.armId
        === SPEND_DECOMPOSITION_KIMI_ARM_ID,
    ) ?? null;

  return (
    <section
      className="panel spend-decomposition-panel"
      id="spend-decomposition"
      aria-labelledby="spend-decomposition-heading"
    >
      <div className="panel-heading">
        <div>
          <h2 id="spend-decomposition-heading">
            Historical DR-303 outcome-cost reconstruction{" "}
            <span className="derived-label">derived</span>
          </h2>
          <p>
            Four mutually exclusive recorded-outcome dollar buckets
            plus one known accounting gap, using one shared absolute
            dollar scale across arms.
          </p>
        </div>
        <span className="quality-badge">
          frozen sources verified
        </span>
      </div>

      <div
        className="spend-decomposition-provenance"
        aria-label="Spend decomposition provenance"
      >
        <strong>{model.scopeId}</strong>
        <span>{model.trialCount} exact reviewed trials</span>
        <span>{model.armCount} arms</span>
        <span>
          scope basis:{" "}
          {scopeCostBasisLabel(model.scopeSelectedCostBasis)}
        </span>
      </div>

      <div className="spend-decomposition-summary-grid">
        <article>
          <span className="metric-label">
            Historical DR-303 reviewed scope estimate
          </span>
          <strong>
            {displayedUsd(model.scopeSelectedReviewedCostUsd)}
          </strong>
          <span>
            {scopeCostBasisLabel(model.scopeSelectedCostBasis)}
          </span>
        </article>

        <article>
          <span className="metric-label">
            Recorded outcome spend
          </span>
          <strong>{displayedUsd(model.recordedCostUsd)}</strong>
          <span>sum of the four recorded outcome buckets</span>
        </article>

        <article>
          <span className="metric-label">
            Summed arm-level known gap
          </span>
          <strong>
            {displayedUsd(model.summedArmAccountingGapUsd)}
          </strong>
          <span>fifth segment; not an outcome bucket</span>
        </article>

        <article>
          <span className="metric-label">
            Missing / unresolved rows
          </span>
          <strong>
            {model.missingRecordedCostCount} /{" "}
            {model.unresolvedCostCount}
          </strong>
          <span>evidence counts, not dollar segments</span>
        </article>
      </div>

      <p className="spend-decomposition-note">
        Bar lengths are not normalized per arm. Every segment uses the
        same dollar denominator: the largest selected reviewed arm cost
        in this scope. Displayed values are capped at four decimal places in the visible table
        below.
      </p>

      <ul
        className="spend-decomposition-legend"
        aria-label="Spend decomposition categories"
      >
        {SPEND_DECOMPOSITION_SEGMENTS.map((segment) => (
          <li key={segment.id}>
            <i
              className={segmentClassName(segment.id)}
              aria-hidden="true"
            />
            <span>
              <strong>{segment.label}</strong>
              <small>{SEGMENT_DESCRIPTIONS[segment.id]}</small>
            </span>
          </li>
        ))}

        <li>
          <i
            className={segmentClassName("accounting_gap")}
            aria-hidden="true"
          />
          <span>
            <strong>Known accounting gap</strong>
            <small>
              Historical DR-303 reviewed arm estimate minus recorded arm cost.
              This is the fifth dollar segment, not an outcome
              classification.
            </small>
          </span>
        </li>
      </ul>

      <div
        className="spend-decomposition-chart"
        aria-hidden="true"
      >
        {model.arms.map((arm) => {
          const links = armLinks[arm.armId];

          return (
            <div
              className="spend-decomposition-chart-row"
              key={arm.armId}
            >
              <div className="spend-decomposition-arm">
                <strong>{friendlyArmLabel(arm.armId)}</strong>
                <code>{arm.armId}</code>
                <span>
                  {displayedUsd(arm.selectedReviewedCostUsd)} historical
                  DR-303 reviewed estimate
                </span>
              </div>

              <div className="spend-decomposition-track">
                {arm.segments.map((segment) => {
                  const width =
                    (
                      geometryUsd(segment.recordedCostUsd)
                      / maxSelectedCost
                    ) * 100;

                  if (width === 0) return null;

                  return (
                    <span
                      key={segment.id}
                      className={segmentClassName(segment.id)}
                      style={{ width: `${width}%` }}
                      title={`${segment.label}: ${displayedUsd(segment.recordedCostUsd)}`}
                    />
                  );
                })}

                {geometryUsd(arm.accountingGapUsd) > 0 ? (
                  <span
                    className={segmentClassName("accounting_gap")}
                    style={{
                      width:
                        `${(
                          geometryUsd(arm.accountingGapUsd)
                          / maxSelectedCost
                        ) * 100}%`,
                    }}
                    title={`Known accounting gap: ${displayedUsd(arm.accountingGapUsd)}`}
                  />
                ) : null}
              </div>

              <div className="spend-decomposition-chart-total">
                {displayedUsd(arm.selectedReviewedCostUsd)}
              </div>
            </div>
          );
        })}
      </div>

      <p className="spend-decomposition-note">
        Recorded exception-with-success-signal spend remains a fixed
        category even when its geometry is zero. In the selected scope,
        {` ${exceptionSuccess.trialCount} `}
        such trials contribute{" "}
        {displayedUsd(exceptionSuccess.recordedCostUsd)} recorded dollars
        and {` ${exceptionSuccess.missingRecordedCostCount} `}
        missing recorded-cost rows.
      </p>

      <div className="table-wrap">
        <table className="spend-decomposition-table">
          <caption className="sr-only">
            DR-303 five-part spend decomposition by arm. Dollar values are
            presentation-truncated to at most four decimal places; source
            precision remains retained in the underlying reviewed evidence.
            Missing and unresolved values are evidence-row counts.
          </caption>
          <thead>
            <tr>
              <th className="sticky-id-column">Arm</th>
              {SPEND_DECOMPOSITION_SEGMENTS.map((segment) => (
                <th key={segment.id}>{segment.label}</th>
              ))}
              <th>Recorded total</th>
              <th>Known accounting gap</th>
              <th>Historical DR-303 reviewed estimate</th>
              <th>Historical cost basis</th>
              <th>Missing / unresolved</th>
              <th>Evidence qualification</th>
            </tr>
          </thead>
          <tbody>
            {model.arms.map((arm) => {
              const links = armLinks[arm.armId];

              return (
                <tr key={arm.armId}>
                  <td className="sticky-id-column">
                    <strong>
                      {links ? (
                        <Link href={links.armEvidenceHref}>
                          {friendlyArmLabel(arm.armId)}
                        </Link>
                      ) : (
                        friendlyArmLabel(arm.armId)
                      )}
                    </strong>
                    <div className="muted mono">{arm.armId}</div>
                    <div className="muted">
                      {arm.successCount}/{arm.trialCount} successes
                    </div>
                  </td>

                  {arm.segments.map((segment) => (
                    <td key={segment.id}>
                      <span className="spend-decomposition-table-value">
                        <strong>
                          {displayedUsd(segment.recordedCostUsd)}
                        </strong>
                        <span className="muted">
                          {segment.trialCount} trials ·{" "}
                          {segment.missingRecordedCostCount} missing
                          recorded
                        </span>
                      </span>
                    </td>
                  ))}

                  <td>
                    {displayedArmValue(
                      arm.recordedCostUsd,
                      links?.costProvenanceHref,
                    )}
                  </td>

                  <td>
                    {displayedArmValue(
                      arm.accountingGapUsd,
                      links?.costProvenanceHref,
                    )}
                  </td>

                  <td>
                    <strong>
                      {displayedArmValue(
                        arm.selectedReviewedCostUsd,
                        links?.costProvenanceHref,
                      )}
                    </strong>
                  </td>

                  <td>
                    {selectedCostBasisLabel(arm.selectedCostBasis)}
                  </td>

                  <td>
                    <strong>
                      {arm.missingRecordedCostCount} /{" "}
                      {arm.unresolvedCostCount}
                    </strong>
                    <div className="muted">
                      missing recorded / unresolved
                    </div>
                  </td>

                  <td className="table-cell-wrap">
                    <div>{arm.costConfidence} confidence</div>
                    <div className="muted">
                      Pricing provenance:{" "}
                      {evidenceLabel(arm.pricingProvenanceStatus)}
                      {" · "}arm/run allocation:{" "}
                      {evidenceLabel(arm.armRunAllocationConfidence)}
                      {" · "}trial allocation:{" "}
                      {evidenceLabel(arm.trialAllocationStatus)}
                      {" · "}outcome allocation:{" "}
                      {evidenceLabel(arm.outcomeCostAllocationStatus)}
                      {" · "}billing:{" "}
                      {evidenceLabel(arm.billingReconciliationStatus)}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="spend-decomposition-boundary">
        <p>
          <strong>Accounting gap is not an outcome bucket.</strong>{" "}
          Missing recorded-cost rows and unresolved-cost rows remain
          evidence counts and are never converted into synthetic dollar
          segments.
        </p>

        {kimi ? (
          <p>
            <strong>Kimi K3 qualification:</strong>{" "}
            {displayedUsd(kimi.accountingGapUsd)} is the known difference
            between its recorded trial cost and qualified retained-rate
            estimate. Outcome allocation remains{" "}
            <code>{kimi.outcomeCostAllocationStatus}</code>, and trial
            allocation remains <code>{kimi.trialAllocationStatus}</code>.
            The provider-log remainder is not allocated to Kimi outcomes.
          </p>
        ) : null}

        <p>
          <strong>Scope reconciliation:</strong> summed selected arm
          costs are {displayedUsd(model.summedSelectedArmCostUsd)}; the
          authoritative reviewed scope headline is{" "}
          {displayedUsd(model.scopeSelectedReviewedCostUsd)}. The retained
          decimal difference is{" "}
          {displayedUsd(model.scopeReconciliationDeltaUsd)} with tolerance{" "}
          {displayedUsd(model.scopeReconciliationToleranceUsd)}. No
          reconciliation amount is assigned to an outcome segment.
        </p>

        {model.summedArmAccountingGapUsd
          !== model.scopeAccountingGapUsd ? (
          <p>
            The summed arm-level known gap is{" "}
            {displayedUsd(model.summedArmAccountingGapUsd)}, while the
            reviewed scope-level gap is{" "}
            {displayedUsd(model.scopeAccountingGapUsd)}. This retained
            scope/arm decimal difference is not redistributed.
          </p>
        ) : null}

        {provenance ? (
          <details>
            <summary>Frozen DR-303 source provenance</summary>
            <dl className="spend-decomposition-source-list">
              <div>
                <dt>Historical trial-cost source</dt>
                <dd>
                  <code>{provenance.coreCostPath}</code>
                  <br />
                  SHA-256 <code>{provenance.coreCostSha256}</code>
                  <br />
                  {provenance.coreTrialCount} rows
                </dd>
              </div>
              <div>
                <dt>Comprehensive Review source</dt>
                <dd>
                  <code>{provenance.reviewPath}</code>
                  <br />
                  SHA-256 <code>{provenance.reviewSha256}</code>
                  <br />
                  {provenance.reviewTrialCount} rows
                </dd>
              </div>
            </dl>
          </details>
        ) : null}
      </div>
    </section>
  );
}
