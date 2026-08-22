import {
  compareCorpusScopeCounts,
  getCorpusScope,
  getCorpusScopePresentationLabel,
  type CorpusScopeId,
  type ObservedCorpusScopeCounts,
} from "../lib/corpus-scopes";
import { formatCurrency, formatNumber } from "../lib/format";

type CorpusScopeNoticeProps = {
  scopeId: CorpusScopeId;
  observedCounts?: ObservedCorpusScopeCounts;
  costPresentation?: "historical_only" | "current_and_historical";
};

function observedCountText(observed: ObservedCorpusScopeCounts): string | null {
  const values = [
    observed.armCount === null || observed.armCount === undefined ? null : `${formatNumber(observed.armCount)} arms`,
    observed.trialCount === null || observed.trialCount === undefined ? null : `${formatNumber(observed.trialCount)} trials`,
    observed.successCount === null || observed.successCount === undefined ? null : `${formatNumber(observed.successCount)} successes`,
  ].filter((value): value is string => Boolean(value));
  return values.length ? values.join(" · ") : null;
}

export function CorpusScopeNotice({
  scopeId,
  observedCounts = {},
  costPresentation = "historical_only",
}: CorpusScopeNoticeProps) {
  const scope = getCorpusScope(scopeId);
  const comparison = compareCorpusScopeCounts(scope, observedCounts);
  const observedText = observedCountText(observedCounts);
  const expected = scope.expectedCounts;
  const historicalReviewedCost =
    scope.adjustedKnownCostUsd
    ?? scope.qualifiedAdjustedCostEstimateUsd;
  const showCurrentSelectedCost =
    costPresentation === "current_and_historical"
    && scope.selectedCostUsd !== null
    && scope.historicalReviewedCostUsd !== null;

  return (
    <section className="quality-context-panel" data-corpus-scope={scope.id} aria-label={`Corpus scope: ${scope.displayLabel}`}>
      <p>
        <strong>Corpus scope: {scope.displayLabel}</strong>{" "}
        <span className="quality-badge">
          {getCorpusScopePresentationLabel(scope)}
        </span>
      </p>
      <p>{scope.shortDescription}</p>
      {expected ? (
        <p>
          <strong>Reviewed denominator:</strong>{" "}
          {formatNumber(expected.armCount)} arms · {formatNumber(expected.trialCount)} trials · {formatNumber(expected.successCount)} successes
          {showCurrentSelectedCost ? (
            <>
              {" "}· {formatCurrency(scope.selectedCostUsd)} current selected cost
              {" "}· {formatCurrency(scope.historicalReviewedCostUsd)} historical reviewed cost
            </>
          ) : historicalReviewedCost === null || scope.costDisplayLabel === null
            ? null
            : <> · {formatCurrency(historicalReviewedCost)} {scope.costDisplayLabel}</>}
        </p>
      ) : observedText ? (
        <p><strong>Current observed inventory:</strong> {observedText}. These totals are dynamic, not a fixed leaderboard denominator.</p>
      ) : (
        <p><strong>Denominator:</strong> Dynamic; no fixed arm, trial, or success total is asserted.</p>
      )}
      <p><strong>Includes:</strong> {scope.includedPopulation}</p>
      <p><strong>Excludes/limits:</strong> {scope.excludedPopulation}</p>
      {showCurrentSelectedCost ? (
        <>
          <p>
            <strong>Current selected-cost coverage:</strong>{" "}
            {scope.selectedCostDescription}
          </p>
          <p>
            <strong>Historical cost coverage:</strong>{" "}
            {scope.costCoverageDescription}
          </p>
          <p className="muted">
            Current cost reviewed {scope.currentCostReviewedAt}
            {" "}· historical provenance: {scope.provenanceLabel}
            {scope.snapshotDate
              ? ` · historical snapshot reviewed ${scope.snapshotDate}`
              : ""}
            {scope.comparisonValid
              ? " · valid for the stated comparison"
              : " · not a full-suite leaderboard denominator"}
          </p>
        </>
      ) : (
        <>
          <p><strong>Cost coverage:</strong> {scope.costCoverageDescription}</p>
          <p className="muted">
            Provenance: {scope.provenanceLabel}
            {scope.snapshotDate
              ? ` · reviewed ${scope.snapshotDate}`
              : " · live/dynamic query result"}
            {scope.comparisonValid
              ? " · valid for the stated comparison"
              : " · not a full-suite leaderboard denominator"}
          </p>
        </>
      )}
      {comparison.status === "mismatch" ? (
        <p className="warning-text" role="alert">
          <strong>Scope warning:</strong> Observed counts do not match the fixed reviewed denominator
          {comparison.mismatchedFields.length ? ` (${comparison.mismatchedFields.join(", ")})` : ""}. The page is showing retained data without changing or hiding it.
          {observedText ? ` Observed: ${observedText}.` : ""}
        </p>
      ) : null}
    </section>
  );
}
