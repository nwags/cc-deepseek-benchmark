import Link from "next/link";

import { AppShell } from "../../components/AppShell";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { CorpusScopeSelector } from "../../components/CorpusScopeSelector";
import { EvidenceSourceContextNotice } from "../../components/EvidenceSourceContextNotice";
import { MetricCard } from "../../components/MetricCard";
import {
  SpendDecompositionPanel,
  type SpendDecompositionArmLinks,
  type SpendDecompositionPresentationState,
} from "../../components/SpendDecompositionPanel";
import { TermInfo } from "../../components/TermInfo";
import { getCostProvenanceFocusRows, type CostProvenanceFocusRow } from "../../lib/dashboard-data";
import {
  buildCostCoverageHref,
  buildExactRunHref,
  buildExactTrialHref,
  buildReviewedAggregateArmEvidenceHref,
  selectCostProvenanceFocus,
  selectEvidenceSourceScope,
} from "../../lib/evidence-links";
import { getCostPerformanceChartArms } from "../../lib/cost-performance-chart";
import { getGlossaryEntry } from "../../lib/glossary";
import {
  friendlyArmLabel,
  friendlyProviderLabel,
  friendlyRoutingLabel,
} from "../../lib/presentation-labels";
import {
  selectReviewedPhase3Scope,
} from "../../lib/phase3-reviewed-comparison";
import {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  getCurrentReviewedPhase3Scope,
  type CurrentReviewedPhase3Arm,
} from "../../lib/phase3-current-reviewed-comparison";
import {
  buildSpendDecompositionModel,
} from "../../lib/spend-decomposition";
import {
  getSpendDecompositionSource,
} from "../../lib/spend-decomposition-source";
import { formatNumber, formatPercent } from "../../lib/format";

export const dynamic = "force-dynamic";

const costCategories = [
  {
    category: "Recorded cost",
    meaning: getGlossaryEntry("Recorded cost").definition,
    action: "Keep separate from reviewed reconstruction when recorded-cost rows are missing."
  },
  {
    category: "Adjusted known cost",
    meaning: getGlossaryEntry("Adjusted known cost").definition,
    action: "Use for the historical core only; it is not the label for Kimi K3."
  },
  {
    category: "Qualified retained-rate estimate",
    meaning: "Retained-rate arithmetic applied to provider-log token totals with explicit provenance and allocation limitations.",
    action: "Display with pricing, allocation, and billing qualifications; do not call it invoice-level spend."
  },
  {
    category: "Accounting gap",
    meaning: getGlossaryEntry("Accounting gap").definition,
    action: "Keep the gap, source, basis, and confidence visible rather than treating missing evidence as zero."
  },
  {
    category: "Exception with success signal",
    meaning: getGlossaryEntry("Exception with success signal").definition,
    action: "Keep separate from clean success; operationally unclean does not automatically mean an incorrect result."
  }
];

type CostCoveragePageProps = {
  searchParams?: Promise<{
    scope?: string | string[];
    arm_id?: string | string[];
    run_label?: string | string[];
    trial_id?: string | string[];
    source_scope?: string | string[];
  }>;
};

function formatCost(value: string | null, maximumFractionDigits = 6): string {
  if (value === null) return "Unavailable";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits,
  }).format(Number(value));
}

function linkedCost(value: string | null, href: string, maximumFractionDigits = 6) {
  const formatted = formatCost(value, maximumFractionDigits);
  return value === null ? formatted : <Link href={href}>{formatted}</Link>;
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

function historicalReviewedArmCostLabel(
  arm: CurrentReviewedPhase3Arm,
): string {
  return arm.historicalReviewedCostBasis
    === "qualified_retained_rate_estimate"
    ? "Qualified retained-rate reconstruction"
    : "Adjusted known cost";
}

function availablePercent(value: number | null): string {
  return value === null ? "Unavailable" : formatPercent(value);
}

export default async function CostCoveragePage({ searchParams }: CostCoveragePageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = selectReviewedPhase3Scope(params.scope);
  const sourceScopeSelection = selectEvidenceSourceScope(params.source_scope);
  const onwardSourceScope = sourceScopeSelection.sourceScope ?? selection.scopeId;
  const focusSelection = selectCostProvenanceFocus({
    armId: params.arm_id,
    runLabel: params.run_label,
    trialId: params.trial_id,
  });
  let focusRows: CostProvenanceFocusRow[] = [];
  let focusReadUnavailable = false;
  if (focusSelection.focus) {
    try {
      focusRows = await getCostProvenanceFocusRows(focusSelection.focus);
    } catch {
      focusReadUnavailable = true;
    }
  }
  const scope = selection.scope;
  const currentScope =
    getCurrentReviewedPhase3Scope(selection.scopeId);
  const cost = scope.costEvidence;
  const outcomes = scope.outcomeCostCoverage;
  const arms = [...currentScope.arms].sort(
    (left, right) => right.passRate - left.passRate,
  );
  const kimi =
    currentScope.arms.find(
      (arm) => arm.armId === "router-kimi-k3",
    ) ?? null;
  const chartArms = getCostPerformanceChartArms(selection.scopeId);
  const chartArmById = new Map(
    chartArms.map((arm) => [arm.armId, arm]),
  );
  if (
    currentScope.armCount !== scope.armCount
    || currentScope.trialCount !== scope.trialCount
    || currentScope.successCount !== scope.successCount
    || chartArms.length !== currentScope.armCount
    || arms.some((arm) => !chartArmById.has(arm.armId))
  ) {
    throw new Error(
      "Current Cost Coverage, historical DR-303 scope, and frozen selected-run membership disagree",
    );
  }
  const kimiChartArm = kimi ? chartArmById.get(kimi.armId) ?? null : null;

  const spendSource = await getSpendDecompositionSource();

  let spendState: SpendDecompositionPresentationState;

  if (!spendSource.available) {
    spendState = {
      available: false,
      message: spendSource.message,
    };
  } else {
    try {
      spendState = {
        available: true,
        model: buildSpendDecompositionModel(
          spendSource.coreRows,
          spendSource.reviewRows,
          selection.scope,
        ),
      };
    } catch {
      spendState = {
        available: false,
        message:
          "Frozen DR-303 source relationship failed closed because the validated reviewed inputs did not satisfy the spend-decomposition contract.",
      };
    }
  }

  const spendArmLinks: SpendDecompositionArmLinks =
    Object.fromEntries(
      arms.map((arm) => {
        const chartArm = chartArmById.get(arm.armId);
        if (!chartArm) {
          throw new Error(
            `No exact frozen selected run exists for ${arm.armId}`,
          );
        }

        return [
          arm.armId,
          {
            armEvidenceHref:
              buildReviewedAggregateArmEvidenceHref(
                arm.armId,
                onwardSourceScope,
              ),
            costProvenanceHref:
              buildCostCoverageHref(
                selection.scopeId,
                {
                  armId: arm.armId,
                  runLabel: chartArm.selectedRunLabel,
                },
                onwardSourceScope,
              ),
          },
        ];
      }),
    );

  return (
    <AppShell
      title={`Cost Coverage: ${scope.displayName}`}
      description={`Current selected cost plus preserved historical benchmark-side cost coverage, accounting gaps, and allocation limits for the ${scope.displayName.toLowerCase()}.`}
    >
      <CorpusScopeSelector
        pathname="/cost-coverage"
        selectedScopeId={selection.scopeId}
        sourceScope={sourceScopeSelection.sourceScope}
      />
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <EvidenceSourceContextNotice value={params.source_scope} />
      <CorpusScopeNotice
        scopeId={selection.scopeId}
        costPresentation="current_and_historical"
        observedCounts={{
          armCount: scope.armCount,
          trialCount: scope.trialCount,
          successCount: scope.successCount,
        }}
      />

      <section className="quality-context-panel">
        <strong>Current selected-cost source:</strong> Decision-facing selected costs come from the
        {" "}{PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt} current-reviewed layer. It preserves the
        {" "}{PHASE3_CURRENT_REVIEWED_COMPARISON.historicalReviewedAt} benchmark-side cost evidence used by
        DR-303 as a separate historical layer. Provider-billed arm totals are used only where exact provider
        reconciliation exists and are not redistributed across trials or outcomes.
        {" "}<Link href={`/cross-phase?scope=${selection.scopeId}`}>Open Cross-phase with this scope</Link>.
        <details>
          <summary>Traceable current and historical sources</summary>
          <p className="mono">results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json</p>
          <p className="mono">results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json</p>
        </details>
        <p className="muted">
          The corpus-scope notice identifies the retained corpus and separates current selected cost from
          preserved historical reviewed cost metadata. Detailed arm-level evidence remains below.
        </p>
      </section>

      {kimi ? (
        <section className="quality-context-panel" aria-label="Kimi K3 current selected and historical cost evidence">
          <p><strong>Kimi K3 current selected and historical cost evidence</strong></p>
          <p>
            Current selected cost: {formatCost(kimi.selectedCostUsd, 7)} · selected cost / attempt: {formatCost(kimi.selectedCostPerAttemptUsd, 7)} · selected cost / clean success: {formatCost(kimi.selectedCostPerCleanSuccessUsd, 7)}.
          </p>
          <p>
            Selected basis: {evidenceLabel(kimi.selectedCostBasis)} · selected confidence: {kimi.selectedCostConfidence} · selected trial allocation: {evidenceLabel(kimi.selectedTrialCostAllocationStatus)} · selected outcome allocation: {evidenceLabel(kimi.selectedOutcomeCostAllocationStatus)} · provider-billed total: {formatCost(kimi.providerBilledCostUsd, 7)}.
          </p>
          <p>
            Historical harness recorded: {kimiChartArm ? linkedCost(kimi.historicalHarnessRecordedCostUsd, buildCostCoverageHref(selection.scopeId, { armId: kimi.armId, runLabel: kimiChartArm.selectedRunLabel }, onwardSourceScope), 6) : formatCost(kimi.historicalHarnessRecordedCostUsd, 6)} · historical qualified retained-rate reconstruction: {kimiChartArm ? linkedCost(kimi.historicalReviewedCostUsd, buildCostCoverageHref(selection.scopeId, { armId: kimi.armId, runLabel: kimiChartArm.selectedRunLabel }, onwardSourceScope), 7) : formatCost(kimi.historicalReviewedCostUsd, 7)} · historical accounting gap: {kimiChartArm ? linkedCost(kimi.accountingGapUsd, buildCostCoverageHref(selection.scopeId, { armId: kimi.armId, runLabel: kimiChartArm.selectedRunLabel }, onwardSourceScope), 7) : formatCost(kimi.accountingGapUsd, 7)}.
          </p>
          <p>
            Pricing-source provenance incomplete · arm-run/provider-log allocation confidence low · trial-level allocation unresolved · not invoice-level or provider-billed spend. The selected aggregate efficiency ratios do not imply trial-level or outcome-level allocation.
          </p>
        </section>
      ) : null}

      <section className="metric-grid">
        <MetricCard
          label="Current selected cost"
          value={formatCost(
            currentScope.selectedCostEvidence.selectedCostUsd,
            13,
          )}
          detail={`Basis: ${evidenceLabel(currentScope.selectedCostEvidence.selectedCostBasis)}.`}
        />
        <MetricCard
          label="Historical reviewed arm-sum cost"
          value={formatCost(
            currentScope.selectedCostEvidence.historicalReviewedArmSumCostUsd,
            13,
          )}
          detail={`Preserved ${PHASE3_CURRENT_REVIEWED_COMPARISON.historicalReviewedAt} benchmark-side reviewed evidence.`}
        />
        <MetricCard
          label="Provider-reconciled selected cost"
          value={formatCost(
            currentScope.selectedCostEvidence.providerReconciledCostUsd,
            8,
          )}
          detail={`${formatNumber(currentScope.selectedCostEvidence.providerReconciledArmCount)}/${formatNumber(currentScope.armCount)} arms have exact provider-billed reconciliation.`}
        />
        <MetricCard
          label="Historical recorded cost"
          value={formatCost(cost.recordedCostUsd, 8)}
          detail={`${formatNumber(cost.missingRecordedCostCount)} trials have missing historical recorded cost.`}
        />
        <MetricCard
          label="Historical accounting gap"
          value={formatCost(cost.accountingGapUsd, 13)}
          detail="Historical reviewed cost measure minus historical recorded cost."
        />
        <MetricCard
          label="Selected allocation status"
          value={evidenceLabel(
            currentScope.selectedCostEvidence.trialAllocationStatus,
          )}
          detail={`Outcome allocation: ${evidenceLabel(currentScope.selectedCostEvidence.outcomeAllocationStatus)}.`}
        />
      </section>

      <section
        className="quality-context-panel"
        aria-label="Historical DR-303 spend decomposition boundary"
      >
        <strong>Historical DR-303 spend decomposition:</strong> The outcome buckets and accounting gaps below
        reproduce the frozen benchmark-side DR-303 evidence. Current provider-billed aggregate corrections are
        not redistributed into these trial or outcome buckets, so the historical bars are not components of the
        current selected total above.
      </section>

      <SpendDecompositionPanel
        state={spendState}
        provenance={
          spendSource.available
            ? spendSource.provenance
            : null
        }
        armLinks={spendArmLinks}
      />

      <section className="panel" id="cost-provenance-focus">
        <div className="panel-heading">
          <div>
            <h2>Cost provenance focus</h2>
            <p>Optional exact stored historical benchmark-side evidence is shown separately and never changes either the current selected totals or preserved historical reviewed totals above.</p>
          </div>
        </div>
        <div className="quality-context-panel">
          <p>
            <strong>Current selected aggregate:</strong> the current-selected totals come from the checked-in current-reviewed v2 layer.
            <br />
            <strong>Historical reviewed aggregate:</strong> DR-303 and historical benchmark-side totals remain the preserved {scope.displayName} evidence.
            <br />
            <strong>Stored historical focus:</strong> rows below, when requested, come from the valid-only <span className="mono">benchmark.v_trial_adjusted_cost_coverage</span> view and do not reconcile against provider-billed selected totals.
          </p>
          {focusSelection.focus?.armId && !focusSelection.focus.runLabel && !focusSelection.focus.trialId ? (
            <p>An arm-only focus may span multiple valid runs. It does not identify or select a latest run.</p>
          ) : null}
        </div>
        {focusSelection.warningMessage ? (
          <p className="warning-text" role="alert">{focusSelection.warningMessage}</p>
        ) : null}
        {!focusSelection.focus ? (
          <div className="placeholder-body">No cost provenance focus is selected. Reviewed scope totals remain available above.</div>
        ) : focusReadUnavailable ? (
          <div className="placeholder-body warning-text">Stored valid-only cost evidence is unavailable. No database or reviewed-total fallback was substituted.</div>
        ) : focusRows.length === 0 ? (
          <div className="placeholder-body">No valid stored cost-coverage row matched every supplied exact identity. No latest, prefix, or alternate-trial fallback was used.</div>
        ) : (
          <>
            <p className="muted">Showing {focusRows.length} matching row(s), bounded to 50. Focus parameters constrain only this evidence table.</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th className="sticky-id-column">Trial</th>
                    <th>Arm / run</th>
                    <th><span className="term-label">Task / attempt <TermInfo term="Attempt" /></span></th>
                    <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
                    <th><span className="term-label">Adjusted known cost <TermInfo term="Adjusted known cost" /></span></th>
                    <th><span className="term-label">Accounting gap <TermInfo term="Known accounting gap" /></span></th>
                    <th><span className="term-label">Source / confidence <TermInfo term="Confidence" /></span></th>
                    <th>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {focusRows.map((row) => (
                    <tr key={row.trial_id}>
                      <td className="sticky-id-column mono">
                        <Link href={buildExactTrialHref(row.trial_id, onwardSourceScope)}>{row.trial_id}</Link>
                      </td>
                      <td>
                        <div className="mono">{row.arm_id}</div>
                        <Link className="mono" href={buildExactRunHref(row.run_label, onwardSourceScope)}>{row.run_label}</Link>
                      </td>
                      <td><span className="mono">{row.task_id ?? "Unavailable"}</span><br />attempt {row.attempt_index ?? "Unavailable"}</td>
                      <td>{formatCost(row.recorded_cost_usd, 8)}</td>
                      <td>{formatCost(row.adjusted_cost_usd, 8)}</td>
                      <td>{formatCost(row.known_accounting_gap_usd, 8)}</td>
                      <td>{evidenceLabel(row.cost_source)} · {evidenceLabel(row.cost_confidence)}<div className="muted">{row.cost_gap_reason ? evidenceLabel(row.cost_gap_reason) : "No recorded gap reason"}</div></td>
                      <td>{outcomeLabel(row.outcome_bucket)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Current selected and historical arm cost evidence</h2>
            <p>Current selected cost is decision-facing. Historical benchmark-side recorded/reviewed costs and outcome allocations remain separate evidence and retain their provenance links.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Successes</th>
                <th>Current selected cost</th>
                <th>Selected basis / confidence</th>
                <th>Selected efficiency ratios</th>
                <th>Provider billing</th>
                <th>Selected allocation</th>
                <th><span className="term-label">Historical recorded cost <TermInfo term="Recorded cost" /></span></th>
                <th>Historical reviewed cost</th>
                <th><span className="term-label">Historical gap <TermInfo term="Accounting gap" /></span></th>
                <th>Historical failure spend</th>
                <th>Historical evidence status</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((arm) => {
                const modelLabel = friendlyArmLabel(arm.armId, arm.backendModel);
                const providerLabel = friendlyProviderLabel(arm.provider);
                const routingLabel = friendlyRoutingLabel(arm.routingPath);
                const chartArm = chartArmById.get(arm.armId);
                if (!chartArm) throw new Error(`No exact frozen selected run exists for ${arm.armId}`);
                const costHref = buildCostCoverageHref(
                  selection.scopeId,
                  { armId: arm.armId, runLabel: chartArm.selectedRunLabel },
                  onwardSourceScope,
                );
                return (
                  <tr key={arm.armId}>
                    <td className="sticky-id-column">
                      <strong>
                        <Link href={buildReviewedAggregateArmEvidenceHref(arm.armId, onwardSourceScope)}>
                          {modelLabel}
                        </Link>
                      </strong>
                      <div className="muted mono">{arm.armId}</div>
                      <div className="muted">{providerLabel} · {routingLabel}</div>
                      <div className="row-action-links">
                        <Link href={buildExactRunHref(chartArm.selectedRunLabel, onwardSourceScope)}>Selected run</Link>
                        <Link href={costHref}>Focus stored cost rows</Link>
                      </div>
                    </td>
                    <td>
                      {formatNumber(arm.successCount)}/{formatNumber(arm.trialCount)}
                      <div className="muted">{formatPercent(arm.passRate)}</div>
                    </td>
                    <td>
                      <strong>{formatCost(arm.selectedCostUsd, 7)}</strong>
                    </td>
                    <td>
                      <div>{evidenceLabel(arm.selectedCostBasis)}</div>
                      <div className="muted">{arm.selectedCostConfidence}</div>
                    </td>
                    <td>
                      <div>Per attempt: {formatCost(arm.selectedCostPerAttemptUsd, 7)}</div>
                      <div>Per clean success: {formatCost(arm.selectedCostPerCleanSuccessUsd, 7)}</div>
                    </td>
                    <td>
                      <div>Provider-billed total: {formatCost(arm.providerBilledCostUsd, 7)}</div>
                      <div className="muted">
                        Reconciliation: {evidenceLabel(arm.providerBillingReconciliationStatus)}
                      </div>
                      {arm.providerSelectedRunLabel ? (
                        <div className="muted mono">{arm.providerSelectedRunLabel}</div>
                      ) : null}
                    </td>
                    <td>
                      <div>Trial: {evidenceLabel(arm.selectedTrialCostAllocationStatus)}</div>
                      <div>Outcome: {evidenceLabel(arm.selectedOutcomeCostAllocationStatus)}</div>
                    </td>
                    <td>{linkedCost(arm.historicalHarnessRecordedCostUsd, costHref, 7)}</td>
                    <td>
                      {linkedCost(arm.historicalReviewedCostUsd, costHref, 7)}
                      <div className="muted">
                        {historicalReviewedArmCostLabel(arm)}
                      </div>
                    </td>
                    <td>{linkedCost(arm.accountingGapUsd, costHref, 7)}</td>
                    <td>
                      <div>{linkedCost(arm.adjustedFailureOrIncompleteCostUsd, costHref, 7)}</div>
                      <div className="muted">{availablePercent(arm.failureOrIncompleteSpendShare)}</div>
                    </td>
                    <td className="table-cell-wrap">
                      <div>
                        Missing / unresolved: {formatNumber(arm.missingRecordedCostCount)} / {formatNumber(arm.unresolvedCostCount)}
                      </div>
                      <div>{arm.costConfidence} historical confidence</div>
                      <div className="muted">
                        Pricing provenance: {evidenceLabel(arm.pricingProvenanceStatus)} · allocation: {evidenceLabel(arm.armRunAllocationConfidence)} · trial allocation: {evidenceLabel(arm.trialAllocationStatus)} · billing: {evidenceLabel(arm.billingReconciliationStatus)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Historical outcome-cost breakdown</h2>
            <p>Frozen source-derived benchmark-side outcome rows with explicit selected-population coverage. These rows are not allocations of current provider-billed aggregate totals.</p>
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
                <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
                <th><span className="term-label">Source adjusted known cost <TermInfo term="Adjusted known cost" /></span></th>
                <th><span className="term-label">Source accounting gap <TermInfo term="Known accounting gap" /></span></th>
                <th>Missing recorded</th>
                <th><span className="term-label">Unresolved adjusted <TermInfo term="Unresolved" /></span></th>
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
