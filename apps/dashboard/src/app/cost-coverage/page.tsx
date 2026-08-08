import Link from "next/link";

import { AppShell } from "../../components/AppShell";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { CorpusScopeSelector } from "../../components/CorpusScopeSelector";
import { MetricCard } from "../../components/MetricCard";
import {
  selectReviewedPhase3Scope,
  type ReviewedPhase3Arm,
} from "../../lib/phase3-reviewed-comparison";
import { formatNumber, formatPercent } from "../../lib/format";

export const dynamic = "force-dynamic";

const costCategories = [
  {
    category: "Recorded cost",
    meaning: "Cost explicitly captured in retained benchmark trial metadata.",
    action: "Keep separate from reviewed reconstruction when recorded-cost rows are missing."
  },
  {
    category: "Adjusted known cost",
    meaning: "Reviewed core cost after supported reconstruction of missing-cost rows.",
    action: "Use for the historical core only; it is not the label for Kimi K3."
  },
  {
    category: "Qualified retained-rate estimate",
    meaning: "Retained-rate arithmetic applied to provider-log token totals with explicit provenance and allocation limitations.",
    action: "Display with pricing, allocation, and billing qualifications; do not call it invoice-level spend."
  },
  {
    category: "Accounting gap",
    meaning: "The selected reviewed cost measure minus recorded trial cost.",
    action: "Keep the gap, source, basis, and confidence visible rather than treating missing evidence as zero."
  },
  {
    category: "Exception with success signal",
    meaning: "A trial had reward=1 and an exception marker in the reviewed core outcome layer.",
    action: "Keep separate from clean success; operationally unclean does not automatically mean an incorrect result."
  }
];

type CostCoveragePageProps = {
  searchParams?: Promise<{ scope?: string | string[] }>;
};

function formatCost(value: string | null, maximumFractionDigits = 6): string {
  if (value === null) return "Unavailable";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits,
  }).format(Number(value));
}

function evidenceLabel(value: string): string {
  return value.split("_").join(" ");
}

function outcomeLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function reviewedArmCost(arm: ReviewedPhase3Arm): string | null {
  return arm.adjustedKnownCostUsd ?? arm.qualifiedRetainedRateCostUsd;
}

function reviewedArmCostLabel(arm: ReviewedPhase3Arm): string {
  return arm.costBasis === "qualified_retained_rate_estimate"
    ? "Qualified retained-rate reconstruction"
    : "Adjusted known cost";
}

function availablePercent(value: number | null): string {
  return value === null ? "Unavailable" : formatPercent(value);
}

export default async function CostCoveragePage({ searchParams }: CostCoveragePageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = selectReviewedPhase3Scope(params.scope);
  const scope = selection.scope;
  const cost = scope.costEvidence;
  const outcomes = scope.outcomeCostCoverage;
  const selectedReviewedCost = cost.adjustedKnownCostUsd ?? cost.qualifiedAdjustedCostEstimateUsd;
  const arms = [...scope.arms].sort((left, right) => right.passRate - left.passRate);
  const kimi = scope.arms.find((arm) => arm.armId === "router-kimi-k3") ?? null;

  return (
    <AppShell
      title={`Cost Coverage: ${scope.displayName}`}
      description={`Recorded cost, reviewed cost evidence, accounting gaps, and allocation limits for the ${scope.displayName.toLowerCase()} from the reviewed 2026-08-05 layer.`}
    >
      <CorpusScopeSelector pathname="/cost-coverage" selectedScopeId={selection.scopeId} />
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <CorpusScopeNotice
        scopeId={selection.scopeId}
        observedCounts={{
          armCount: scope.armCount,
          trialCount: scope.trialCount,
          successCount: scope.successCount,
        }}
      />

      <section className="quality-context-panel">
        <strong>Reviewed fixed-comparison source:</strong> Both this page and Cross-phase use the same validated 2026-08-05 reviewed layer.
        The historical core remains selectable without rewriting its source artifacts.
        {" "}<Link href={`/cross-phase?scope=${selection.scopeId}`}>Open Cross-phase with this scope</Link>.
        <details>
          <summary>Traceable reviewed source</summary>
          <p className="mono">results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json</p>
        </details>
      </section>

      {kimi ? (
        <section className="quality-context-panel" aria-label="Kimi K3 qualified cost evidence">
          <p><strong>Kimi K3 qualified cost evidence</strong></p>
          <p>
            Recorded trial cost: {formatCost(kimi.recordedCostUsd, 6)} · qualified retained-rate reconstruction: {formatCost(kimi.qualifiedRetainedRateCostUsd, 7)} · accounting gap: {formatCost(kimi.accountingGapUsd, 7)}.
          </p>
          <p>
            Pricing-source provenance incomplete · arm-run/provider-log allocation confidence low · trial-level allocation unresolved · not invoice-level or provider-billed spend.
          </p>
        </section>
      ) : null}

      <section className="metric-grid">
        <MetricCard
          label="Recorded cost"
          value={formatCost(cost.recordedCostUsd, 8)}
          detail={`${formatNumber(cost.missingRecordedCostCount)} trials have missing recorded cost.`}
        />
        <MetricCard
          label={cost.costLabel}
          value={formatCost(selectedReviewedCost, 13)}
          detail={`Basis: ${evidenceLabel(cost.costBasis)}.`}
        />
        <MetricCard
          label="Accounting gap"
          value={formatCost(cost.accountingGapUsd, 13)}
          detail="Selected reviewed cost measure minus recorded cost."
        />
        <MetricCard
          label="Unresolved cost rows"
          value={formatNumber(cost.unresolvedCostCount)}
          detail={`Trial allocation: ${evidenceLabel(cost.trialAllocationStatus)}.`}
        />
        <MetricCard
          label="Failure/incomplete spend"
          value={formatCost(cost.adjustedFailureOrIncompleteCostUsd, 6)}
          detail={cost.adjustedFailureOrIncompleteCostUsd === null
            ? "Unavailable because the selected scope lacks complete outcome allocation."
            : availablePercent(cost.failureOrIncompleteSpendShare)}
        />
        <MetricCard
          label="Cost / clean success"
          value={formatCost(cost.adjustedCostPerCleanSuccessUsd, 6)}
          detail={cost.adjustedCostPerCleanSuccessUsd === null
            ? "Unavailable; no Kimi outcome cost was fabricated."
            : `${formatNumber(scope.arms.reduce((sum, arm) => sum + arm.cleanSuccessCount, 0))} clean successes.`}
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Reviewed arm cost evidence</h2>
            <p>Recorded cost and the applicable reviewed cost measure remain separate. Unavailable outcome allocations are shown explicitly.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Successes</th>
                <th>Recorded cost</th>
                <th>Reviewed cost</th>
                <th>Cost basis</th>
                <th>Gap</th>
                <th>Failure spend</th>
                <th>Failure share</th>
                <th>Cost / clean success</th>
                <th>Missing / unresolved</th>
                <th>Evidence status</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((arm) => (
                <tr key={arm.armId}>
                  <td className="sticky-id-column">
                    <strong>{arm.armId}</strong>
                    <div className="muted">{arm.backendModel}</div>
                  </td>
                  <td>
                    {formatNumber(arm.successCount)}/{formatNumber(arm.trialCount)}
                    <div className="muted">{formatPercent(arm.passRate)}</div>
                  </td>
                  <td>{formatCost(arm.recordedCostUsd, 7)}</td>
                  <td>{formatCost(reviewedArmCost(arm), 7)}</td>
                  <td>{reviewedArmCostLabel(arm)}</td>
                  <td>{formatCost(arm.accountingGapUsd, 7)}</td>
                  <td>{formatCost(arm.adjustedFailureOrIncompleteCostUsd, 7)}</td>
                  <td>{availablePercent(arm.failureOrIncompleteSpendShare)}</td>
                  <td>{formatCost(arm.adjustedCostPerCleanSuccessUsd, 7)}</td>
                  <td>{formatNumber(arm.missingRecordedCostCount)} / {formatNumber(arm.unresolvedCostCount)}</td>
                  <td>
                    <div>{arm.costConfidence} confidence</div>
                    <div className="muted">
                      Pricing provenance: {evidenceLabel(arm.pricingProvenanceStatus)} · allocation: {evidenceLabel(arm.armRunAllocationConfidence)} · trial allocation: {evidenceLabel(arm.trialAllocationStatus)} · billing: {evidenceLabel(arm.billingReconciliationStatus)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Outcome-cost breakdown</h2>
            <p>Historical source-derived outcome rows with explicit selected-scope coverage.</p>
          </div>
        </div>
        <div className="quality-context-panel">
          {outcomes.status === "partial_core_only" ? (
            <p>
              <strong>Partial outcome coverage:</strong> These outcome-cost rows cover the 900-trial Phase 3 core only. Kimi K3&apos;s 60 trials are excluded because provider-log cost cannot be allocated reliably to individual trials or outcomes.
            </p>
          ) : (
            <p>
              <strong>Complete reviewed core coverage:</strong> These source rows cover all {formatNumber(outcomes.coveredTrialCount)}/{formatNumber(scope.trialCount)} trials in Phase 3 core.
            </p>
          )}
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Outcome bucket</th>
                <th>Trials</th>
                <th>Recorded cost</th>
                <th>Source adjusted known cost</th>
                <th>Source accounting gap</th>
                <th>Missing recorded</th>
                <th>Unresolved adjusted</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.rows.map((row) => (
                <tr key={row.outcomeBucket}>
                  <td>{outcomeLabel(row.outcomeBucket)}</td>
                  <td>{formatNumber(row.trialCount)}</td>
                  <td>{formatCost(row.recordedCostUsd, 7)}</td>
                  <td>{formatCost(row.sourceAdjustedKnownCostUsd, 12)}</td>
                  <td>{formatCost(row.sourceAccountingGapUsd, 12)}</td>
                  <td>{formatNumber(row.missingRecordedCostCount)}</td>
                  <td>{formatNumber(row.unresolvedAdjustedCostCount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details>
          <summary>Historical decimal reconciliation</summary>
          <p>
            The preserved source outcome rows total ${outcomes.sourceAdjustedKnownCostTotalUsd}; the reviewed scope headline is ${outcomes.reviewedAdjustedKnownCostTotalUsd}. The ${outcomes.reviewedScopeReconciliationAdjustmentUsd} serialization adjustment remains scope-level and is not assigned to any outcome bucket.
          </p>
        </details>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Cost evidence terminology</h2>
            <p>Interpretation rules for the reviewed core and qualified extended layers.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Meaning</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {costCategories.map((row) => (
                <tr key={row.category}>
                  <td>{row.category}</td>
                  <td>{row.meaning}</td>
                  <td>{row.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
