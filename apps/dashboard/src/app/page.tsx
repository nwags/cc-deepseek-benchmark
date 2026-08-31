import {
  formatCurrentCostRelation,
} from "../lib/current-cost-presentation";
import Link from "next/link";
import { TermInfo } from "../components/TermInfo";
import { AppShell } from "../components/AppShell";
import { CorpusScopeNotice } from "../components/CorpusScopeNotice";
import { CostPerformanceChart } from "../components/CostPerformanceChart";
import { DataFreshnessNotice } from "../components/DataFreshnessNotice";
import { MetricCard } from "../components/MetricCard";
import { SuiteHeatmap } from "../components/SuiteHeatmap";
import { QualityPassRate, QualityBadge, buildSuspectNoopHref } from "../components/QualityContext";
import {
  getReviewedSelectedArmRunRows,
  getReviewedSelectedRunAdjustedCostRows,
  getOverview,
  getSuiteTaskDifficulty,
  getSuiteHeatmapCells,
  getArmRunQualityByRunLabels,
  getInvalidArmRunRows,
  getValidSuiteLatestIncludedExecutionAt,
} from "../lib/dashboard-data";
import {
  buildOperationalFreshness,
  buildReviewedSnapshotFreshness,
  expectedLabelCoverageWarning,
  findLatestIncludedExecutionAt,
  summarizeExpectedLabelCoverage,
} from "../lib/data-freshness";
import { OVERVIEW_FRESHNESS_SOURCES } from "../lib/data-freshness-sources";
import {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  getCurrentReviewedPhase3Scope,
} from "../lib/phase3-current-reviewed-comparison";
import {
  PHASE3_REVIEWED_RUN_SELECTION,
  getReviewedRunSelectionScope,
  getReviewedSelectedRunLabels,
} from "../lib/phase3-reviewed-run-selection";
import {
  buildOverviewReviewedComparison,
  type DatabaseReadStatus,
} from "../lib/overview-reviewed-comparison";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds, formatTruncatedCurrency } from "../lib/format";
import {
  deriveProviderFilterOptions,
  getCostPerformanceChartArms,
  selectCostPerformanceChartScope,
} from "../lib/cost-performance-chart";
import {
  friendlyModelLabel,
  friendlyProviderLabel,
  friendlyRoutingLabel,
} from "../lib/presentation-labels";

export const dynamic = "force-dynamic";

async function readDatabaseEvidence<T>(promise: Promise<T>): Promise<{
  status: DatabaseReadStatus;
  value: T | null;
}> {
  try {
    return { status: "available", value: await promise };
  } catch {
    return { status: "unavailable", value: null };
  }
}

function formatReviewedUsd(value: string | null): string {
  if (value === null) return "Unavailable";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "Unavailable";
  return formatTruncatedCurrency(value);
}

function linkedReviewedUsd(value: string | null, href: string) {
  const formatted = formatReviewedUsd(value);
  return value === null ? formatted : <Link href={href}>{formatted}</Link>;
}

function evidenceLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function readGroupStatus(...statuses: DatabaseReadStatus[]): "available" | "unavailable" {
  return statuses.every((status) => status === "available") ? "available" : "unavailable";
}

function warningText(messages: Array<string | null>): string | null {
  const retained = messages.filter((message): message is string => Boolean(message));
  return retained.length ? retained.join(" ") : null;
}

type DashboardPageSearchParams = Promise<{ chart_scope?: string | string[] }>;

export default async function DashboardPage({
  searchParams,
}: Readonly<{ searchParams?: DashboardPageSearchParams }>) {
  const query = searchParams ? await searchParams : {};
  const chartScopeSelection = selectCostPerformanceChartScope(query.chart_scope);
  const chartArms = getCostPerformanceChartArms(chartScopeSelection.scopeId);
  const chartProviderOptions = deriveProviderFilterOptions(chartArms);
  const reviewedScope =
    getCurrentReviewedPhase3Scope("phase3-extended");
  const reviewedArmById = new Map(
    reviewedScope.arms.map((arm) => [arm.armId, arm]),
  );
  const runSelectionScope = getReviewedRunSelectionScope("phase3-extended");
  const selectedRunLabels = getReviewedSelectedRunLabels("phase3-extended");
  const [
    overviewRead,
    selectedRunRead,
    selectedCostRead,
    hardestFullEvalsRead,
    heatmapCellsRead,
    selectedQualityRead,
    invalidRowsRead,
    suiteLatestExecutionRead,
  ] = await Promise.all([
    readDatabaseEvidence(getOverview()),
    readDatabaseEvidence(getReviewedSelectedArmRunRows(selectedRunLabels)),
    readDatabaseEvidence(getReviewedSelectedRunAdjustedCostRows(selectedRunLabels)),
    readDatabaseEvidence(getSuiteTaskDifficulty("phase3-full-20", 8)),
    readDatabaseEvidence(getSuiteHeatmapCells("phase3-full-20")),
    readDatabaseEvidence(getArmRunQualityByRunLabels([...selectedRunLabels])),
    readDatabaseEvidence(getInvalidArmRunRows()),
    readDatabaseEvidence(getValidSuiteLatestIncludedExecutionAt("phase3-full-20")),
  ]);

  const renderedAt = new Date().toISOString();

  const reviewedComparison = buildOverviewReviewedComparison({
    scope: reviewedScope,
    runSelectionScope,
    comparisonReviewedAt:
      PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
    runSelectionReviewedAt: PHASE3_REVIEWED_RUN_SELECTION.reviewedAt,
    databaseRunReadStatus: selectedRunRead.status,
    databaseRunRows: selectedRunRead.value ?? [],
    databaseCostReadStatus: selectedCostRead.status,
    databaseAdjustedCostRows: selectedCostRead.value ?? [],
  });
  const overview = overviewRead.value;
  const hardestFullEvals = hardestFullEvalsRead.value ?? [];
  const heatmapCells = heatmapCellsRead.value ?? [];
  const invalidFullSuiteCount = invalidRowsRead.value
    ?.filter((row) => row.suite_id === "phase3-full-20").length ?? null;
  const selectedQualityByRun = new Map(
    (selectedQualityRead.value ?? []).map((row) => [row.run_label, row]),
  );
  const selectedExecution = findLatestIncludedExecutionAt(
    (selectedRunRead.value ?? []).map((row) => row.finished_at),
  );
  const selectedRunCoverage = summarizeExpectedLabelCoverage(
    selectedRunLabels,
    (selectedRunRead.value ?? []).map((row) => row.run_label),
  );
  const selectedCostCoverage = summarizeExpectedLabelCoverage(
    selectedRunLabels,
    (selectedCostRead.value ?? []).map((row) => row.run_label),
  );
  const selectedQualityCoverage = summarizeExpectedLabelCoverage(
    selectedRunLabels,
    (selectedQualityRead.value ?? []).map((row) => row.run_label),
  );
  const selectedEvidenceWarning = warningText([
    selectedRunRead.status === "available"
      ? expectedLabelCoverageWarning("Stored run-summary evidence", selectedRunCoverage)
      : null,
    selectedCostRead.status === "available"
      ? expectedLabelCoverageWarning("Stored adjusted-cost evidence", selectedCostCoverage)
      : null,
    selectedQualityRead.status === "available"
      ? expectedLabelCoverageWarning("Stored quality context", selectedQualityCoverage)
      : null,
    selectedExecution.invalidTimestampCount
      ? `${selectedExecution.invalidTimestampCount} stored run completion timestamp(s) were invalid and excluded from the latest-execution calculation.`
      : null,
  ]);

  const reviewedComparisonFreshness = buildReviewedSnapshotFreshness({
    sourceLabel: OVERVIEW_FRESHNESS_SOURCES.reviewedComparison.sourceLabel,
    populationLabel: OVERVIEW_FRESHNESS_SOURCES.reviewedComparison.populationLabel,
    reviewedAt: OVERVIEW_FRESHNESS_SOURCES.reviewedComparison.reviewedAt,
    schemaVersion: OVERVIEW_FRESHNESS_SOURCES.reviewedComparison.schemaVersion,
    provenanceIdentifier: OVERVIEW_FRESHNESS_SOURCES.reviewedComparison.provenanceIdentifier,
  });
  const reviewedRunSelectionFreshness = buildReviewedSnapshotFreshness({
    sourceLabel: OVERVIEW_FRESHNESS_SOURCES.reviewedRunSelection.sourceLabel,
    populationLabel: OVERVIEW_FRESHNESS_SOURCES.reviewedRunSelection.populationLabel,
    reviewedAt: OVERVIEW_FRESHNESS_SOURCES.reviewedRunSelection.reviewedAt,
    schemaVersion: OVERVIEW_FRESHNESS_SOURCES.reviewedRunSelection.schemaVersion,
    provenanceIdentifier: OVERVIEW_FRESHNESS_SOURCES.reviewedRunSelection.provenanceIdentifier,
  });
  const selectedRunEvidenceFreshness = buildOperationalFreshness({
    sourceLabel: OVERVIEW_FRESHNESS_SOURCES.selectedRunEvidence.sourceLabel,
    sourceRelations: OVERVIEW_FRESHNESS_SOURCES.selectedRunEvidence.sourceRelations,
    populationLabel: OVERVIEW_FRESHNESS_SOURCES.selectedRunEvidence.populationLabel,
    queryStatus: readGroupStatus(
      selectedRunRead.status,
      selectedCostRead.status,
      selectedQualityRead.status,
    ),
    queriedAt: renderedAt,
    latestIncludedExecutionAt: selectedExecution.latestTimestamp,
    latestCanonicalPublishedAt: null,
    staleAfterSeconds: null,
    warningMessage: selectedEvidenceWarning,
  });
  const validImportedFreshness = buildOperationalFreshness({
    sourceLabel: OVERVIEW_FRESHNESS_SOURCES.validImportedInventory.sourceLabel,
    sourceRelations: OVERVIEW_FRESHNESS_SOURCES.validImportedInventory.sourceRelations,
    populationLabel: OVERVIEW_FRESHNESS_SOURCES.validImportedInventory.populationLabel,
    queryStatus: overviewRead.status,
    queriedAt: renderedAt,
    latestIncludedExecutionAt: overview?.latest_included_execution_at ?? null,
    latestCanonicalPublishedAt: null,
    staleAfterSeconds: null,
    warningMessage: null,
  });
  const dynamicSuiteFreshness = buildOperationalFreshness({
    sourceLabel: OVERVIEW_FRESHNESS_SOURCES.dynamicSuiteAggregates.sourceLabel,
    sourceRelations: OVERVIEW_FRESHNESS_SOURCES.dynamicSuiteAggregates.sourceRelations,
    populationLabel: OVERVIEW_FRESHNESS_SOURCES.dynamicSuiteAggregates.populationLabel,
    queryStatus: readGroupStatus(
      hardestFullEvalsRead.status,
      heatmapCellsRead.status,
      suiteLatestExecutionRead.status,
    ),
    queriedAt: renderedAt,
    latestIncludedExecutionAt: suiteLatestExecutionRead.value,
    latestCanonicalPublishedAt: null,
    staleAfterSeconds: null,
    warningMessage: null,
  });

  return (
    <AppShell title="Coding Agent Benchmark Dashboard">
      <h2>Phase 3 extended full-suite comparison</h2>
      <CorpusScopeNotice
        scopeId="phase3-extended"
        costPresentation="current_and_historical"
        observedCounts={{
          armCount: reviewedComparison.armCount,
          trialCount: reviewedComparison.trialCount,
          successCount: reviewedComparison.successCount,
        }}
      />
      <DataFreshnessNotice freshness={reviewedComparisonFreshness} />
      <DataFreshnessNotice freshness={reviewedRunSelectionFreshness} />
      <section className="metric-grid">
        <MetricCard label="Reviewed arms" value={formatNumber(reviewedComparison.armCount)} detail="Frozen reviewed comparison membership" />
        <MetricCard label="Reviewed trials" value={formatNumber(reviewedComparison.trialCount)} detail="20 tasks × 3 attempts × 16 selected runs" />
        <MetricCard label="Reviewed pass rate" value={formatPercent(reviewedScope.passRate)} detail={`${formatNumber(reviewedComparison.successCount)} reviewed successes`} />
        <MetricCard
          label="Mixed best-supported arm sum"
          value={formatReviewedUsd(reviewedComparison.selectedCostUsd)}
          detail="Arithmetic sum of mixed arm-level evidence; neither an exact scope bill nor a global lower bound"
        />
        <MetricCard
          label="Historical reviewed cost"
          value={formatReviewedUsd(reviewedComparison.historicalReviewedCostUsd)}
          detail="Frozen August 5 reviewed arm-sum cost retained for historical evidence"
        />
      </section>

      <section className="quality-context-panel">
        <strong>Current reviewed comparison provenance:</strong> Decision-facing selected costs come from the{" "}
        {PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt} current-reviewed V4 layer. It preserves the 2026-08-05 historical benchmark/reviewed cost evidence
        as a separate layer. Exact run labels remain frozen by the 2026-08-09 reviewed run-selection contract.
        Database evidence is resolved only for those labels; the database does not select a newer run. Stored cost
        reconciliation compares against the historical benchmark-side recorded/adjusted evidence, not against
        provider-billed aggregate totals, and provider aggregates are never reallocated to trials or outcomes.
        Current invalid/quarantined full-suite records remain visible in the audit layer:{" "}
        {invalidFullSuiteCount === null ? "Unavailable" : formatNumber(invalidFullSuiteCount)}.{" "}
        <Link href="/trial-quality">Open trial quality audit</Link>.
      </section>
      <DataFreshnessNotice freshness={selectedRunEvidenceFreshness} />

      {(reviewedComparison.databaseEvidenceWarnings.length > 0
        || selectedRunRead.status === "unavailable"
        || selectedCostRead.status === "unavailable"
        || selectedQualityRead.status === "unavailable") && (
        <section className="quality-context-panel" role="alert">
          <strong>Stored-evidence reconciliation is incomplete.</strong>{" "}
          The checked-in reviewed facts and exact selected run identities remain available; no alternate database
          run was substituted.
          {reviewedComparison.databaseEvidenceWarnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Current reviewed full-suite comparison</h2>
            <p>
              The current-reviewed comparison keeps one complete valid full-suite run per arm while selecting the
              best available reviewed arm-level cost basis. Exact provider-billed arm totals are used where provider
              reconciliation exists; historical reviewed cost evidence remains separately visible.
            </p>
            <p>
              The 2026-08-09 reviewed run-selection contract freezes the exact run labels and they do not
              automatically change when newer runs are imported. Current stored evidence is resolved only for those
              labels, and no mutable suite/arm aggregate is used as a fallback.
            </p>
            <p>
              Stored reconciliation reads <code>benchmark.v_valid_arm_run_summary</code> and{" "}
              <code>benchmark.v_trial_adjusted_cost_coverage</code> for the exact labels. Those database cost rows
              are historical benchmark-side evidence; they are not expected to equal a provider-billed aggregate
              selected cost.
            </p>
          </div>
          <Link href="/eval-suites/phase3-full-20">Open suite →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Arm and selected reviewed run</th>
                <th>Reviewed result</th>
                <th>Current selected cost</th>
                <th>Selected-cost status</th>
                <th>Historical benchmark cost evidence</th>
                <th>Historical cost coverage</th>
                <th>Stored historical-evidence reconciliation</th>
              </tr>
            </thead>
            <tbody>
              {reviewedComparison.rows.map((row) => {
                const reviewedArm = reviewedArmById.get(row.armId);
                if (!reviewedArm) {
                  throw new Error(`No reviewed arm presentation exists for ${row.armId}`);
                }
                const quality = selectedQualityByRun.get(row.selectedRunLabel);
                const suspectNoopCount = quality?.suspect_noop_count ?? 0;
                const isKimi = row.armId === "router-kimi-k3";
                return (
                  <tr key={row.selectedRunLabel}>
                    <td>{row.rank}</td>
                    <td>
                      <strong>
                        <Link href={row.armEvidenceHref}>
                          {friendlyModelLabel(reviewedArm.backendModel)}
                        </Link>
                      </strong>
                      <div className="muted mono">{row.armId}</div>
                      <div className="muted">
                        {friendlyProviderLabel(reviewedArm.provider)} · {friendlyRoutingLabel(reviewedArm.routingPath)}
                      </div>
                      <Link className="mono" href={row.selectedRunHref}>{row.selectedRunLabel}</Link>
                      <div>Selected reviewed run · reviewed full-suite run</div>
                    </td>
                    <td>
                      <div>Reviewed pass rate: {formatPercent(row.reviewedPassRate)}</div>
                      <div>{formatNumber(row.reviewedSuccessCount)} / {formatNumber(row.reviewedTrialCount)} successes</div>
                      {quality ? <QualityPassRate row={quality} /> : <div>Stored quality context: Unavailable</div>}
                      {quality && suspectNoopCount > 0 ? (
                        <Link href={buildSuspectNoopHref({ run_label: row.selectedRunLabel })}>
                          <QualityBadge count={suspectNoopCount} />
                        </Link>
                      ) : quality ? (
                        <QualityBadge count={suspectNoopCount} />
                      ) : <div>Suspect no-op: Unavailable</div>}
                    </td>
                    <td>
                      <strong>
                        {formatCurrentCostRelation(
                          formatReviewedUsd(row.selectedCostUsd),
                          row.selectedCostRelation,
                        )}
                      </strong>
                      <div>
                        Per attempt:{" "}
                        {formatCurrentCostRelation(
                          formatReviewedUsd(row.selectedCostPerAttemptUsd),
                          row.selectedEfficiencyRelation,
                        )}
                      </div>
                      <div>
                        Per clean success:{" "}
                        {formatCurrentCostRelation(
                          formatReviewedUsd(row.selectedCostPerCleanSuccessUsd),
                          row.selectedEfficiencyRelation,
                        )}
                      </div>
                    </td>
                    <td>
                      <div>Selected basis: {evidenceLabel(row.selectedCostBasis)}</div>
                      <div>Cost relation: {evidenceLabel(row.selectedCostRelation)}</div>
                      <div>Efficiency relation: {evidenceLabel(row.selectedEfficiencyRelation)}</div>
                      <div>Selected confidence: {row.selectedCostConfidence}</div>
                      <div>
                        Provider billing reconciliation:{" "}
                        {evidenceLabel(row.providerBillingReconciliationStatus)}
                      </div>
                      <div>
                        Selected trial allocation:{" "}
                        {evidenceLabel(row.selectedTrialCostAllocationStatus)}
                      </div>
                      <div>
                        Selected outcome allocation:{" "}
                        {evidenceLabel(row.selectedOutcomeCostAllocationStatus)}
                      </div>
                      {row.providerBilledCostUsd !== null && (
                        <div>
                          Provider-billed arm total:{" "}
                          {formatReviewedUsd(row.providerBilledCostUsd)}
                        </div>
                      )}
                      {row.currentSelectedRunLabel && (
                        <div>
                          Current reconciliation run:{" "}
                          <span className="mono">{row.currentSelectedRunLabel}</span>
                        </div>
                      )}
                      {isKimi && (
                        <>
                          <div>
                            Qualified retained-rate estimate; aggregate efficiency ratios do not imply trial or
                            outcome allocation.
                          </div>
                          <div>Provider-log exclusivity not proven</div>
                        </>
                      )}
                    </td>
                    <td>
                      <div>
                        Historical harness recorded:{" "}
                        {linkedReviewedUsd(
                          row.historicalHarnessRecordedCostUsd,
                          row.costProvenanceHref,
                        )}
                      </div>
                      <div>
                        Historical reviewed cost:{" "}
                        {linkedReviewedUsd(
                          row.historicalReviewedCostUsd,
                          row.costProvenanceHref,
                        )}
                      </div>
                      <div>
                        Historical reviewed basis:{" "}
                        {evidenceLabel(row.historicalReviewedCostBasis)}
                      </div>
                      <div>
                        Historical reviewed accounting gap:{" "}
                        {linkedReviewedUsd(
                          row.reviewedAccountingGapUsd,
                          row.costProvenanceHref,
                        )}
                      </div>
                      <div>Historical sources: {row.costSources.join(", ")}</div>
                      <div>Historical confidence: {row.costConfidence}</div>
                      <div>
                        Historical pricing provenance:{" "}
                        {evidenceLabel(row.pricingProvenanceStatus)}
                      </div>
                      <div>
                        Historical arm/run allocation:{" "}
                        {evidenceLabel(row.armRunAllocationConfidence)}
                      </div>
                      <div>
                        Historical trial allocation:{" "}
                        {evidenceLabel(row.trialAllocationStatus)}
                      </div>
                      <div>
                        Historical billing reconciliation:{" "}
                        {evidenceLabel(row.billingReconciliationStatus)}
                      </div>
                      {isKimi && (
                        <div>Historical adjusted known cost: Unavailable</div>
                      )}
                    </td>
                    <td>
                      <div>
                        Historical missing recorded:{" "}
                        {formatNumber(row.missingRecordedCostCount)}
                      </div>
                      <div>
                        Historical unresolved adjusted:{" "}
                        {formatNumber(row.unresolvedAdjustedCostCount)}
                      </div>
                    </td>
                    <td className="table-cell-wrap">
                      <div>
                        Compared only with historical benchmark-side recorded/adjusted cost evidence.
                      </div>
                      <strong>{evidenceLabel(row.reconciliationStatus)}</strong>
                      <div>Run evidence: {evidenceLabel(row.databaseRunEvidenceStatus)}</div>
                      <div>Cost evidence: {evidenceLabel(row.databaseCostEvidenceStatus)}</div>
                      {row.databaseRunEvidence && (
                        <div>
                          Stored result: {formatNumber(row.databaseRunEvidence.success_count)} /{" "}
                          {formatNumber(row.databaseRunEvidence.trial_count)} successes ·{" "}
                          {row.databaseRunEvidence.suite_id ?? "suite unavailable"}
                        </div>
                      )}
                      {!isKimi && row.databaseAdjustedCostEvidence && (
                        <>
                          <div>Stored recorded evidence: {linkedReviewedUsd(row.databaseAdjustedCostEvidence.recorded_cost_usd, row.costProvenanceHref)}</div>
                          <div>Stored adjusted evidence: {linkedReviewedUsd(row.databaseAdjustedCostEvidence.adjusted_known_cost_usd, row.costProvenanceHref)}</div>
                          <div>
                            Stored sources/confidence:{" "}
                            {row.databaseAdjustedCostEvidence.adjusted_cost_sources.join(", ") || "Unavailable"} /{" "}
                            {row.databaseAdjustedCostEvidence.adjusted_cost_confidences.join(", ") || "Unavailable"}
                          </div>
                        </>
                      )}
                      {row.reconciliationMessages.map((message) => (
                        <div key={message}>{message}</div>
                      ))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <CostPerformanceChart
        key={chartScopeSelection.scopeId}
        arms={chartArms}
        providerOptions={chartProviderOptions}
        scopeId={chartScopeSelection.scopeId}
        scopeWarningMessage={chartScopeSelection.warningMessage}
      />

      <section className="quality-context-panel">
        <strong>Different population below:</strong> the heatmap and hardest-task sections use current dynamic
        valid-imported <code>phase3-full-20</code> suite/arm aggregates. They are not restricted to the frozen
        16 selected reviewed run labels and can combine multiple valid imports for an arm.
        {(heatmapCellsRead.status === "unavailable" || hardestFullEvalsRead.status === "unavailable") && (
          <p role="alert">The current dynamic suite aggregates are unavailable; no reviewed-run values were substituted.</p>
        )}
      </section>
      <DataFreshnessNotice freshness={dynamicSuiteFreshness} />

      <SuiteHeatmap
        rows={heatmapCells}
        title="Dynamic valid-imported full-suite heatmap"
        description="Rows are evals and columns are current valid-imported suite/arm aggregates, not the frozen reviewed-run cohort. Heatmap cells show successes/trials."
      />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Dynamic valid-imported hardest full-suite evals</h2>
            <p>
              Tasks where the current valid-imported suite aggregates struggle most. This population can include
              more than one valid run per arm and is not the frozen reviewed-run cohort.
            </p>
          </div>
          <Link href="/evals">All evals →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Eval</th>
                <th>Arms</th>
                <th>Trials</th>
                <th>Successes</th>
                <th><span className="term-label">Pass rate <TermInfo term="Pass rate" /></span></th>
                <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
              </tr>
            </thead>
            <tbody>
              {hardestFullEvals.map((row) => (
                <tr key={row.task_id}>
                  <td>
                    <Link href={`/evals/${encodeURIComponent(row.task_id)}`}>{row.task_name ?? row.task_id}</Link>
                    <div className="mono">{row.task_id}</div>
                  </td>
                  <td>{formatNumber(row.arm_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Selected reviewed run evidence</h2>
            <p>
              Current stored evidence for the same 16 frozen reviewed run labels used in the comparison above.
              Missing database evidence stays unavailable; a newer run is never substituted.
            </p>
          </div>
          <Link href="/arm-runs">All arm runs →</Link>
        </div>
        <div className="run-list">
          {reviewedComparison.rows.map((row) => {
            const reviewedArm = reviewedArmById.get(row.armId);
            if (!reviewedArm) {
              throw new Error(`No reviewed arm presentation exists for ${row.armId}`);
            }
            const databaseRun = row.databaseRunEvidence;
            const quality = selectedQualityByRun.get(row.selectedRunLabel);
            return (
              <article className="run-card" key={row.selectedRunLabel}>
                <div>
                  <h3>
                    <Link href={row.selectedRunHref}>
                      {friendlyModelLabel(reviewedArm.backendModel)}
                    </Link>
                  </h3>
                  <p className="mono">{row.armId}</p>
                  <p className="muted">
                    {friendlyProviderLabel(reviewedArm.provider)} · {friendlyRoutingLabel(reviewedArm.routingPath)}
                  </p>
                  <p>Reviewed full-suite run · stored evidence {evidenceLabel(row.databaseRunEvidenceStatus)}</p>
                  <p className="mono">{row.selectedRunLabel}</p>
                  {databaseRun?.arm_run_id && (
                    <Link href={`/arm-runs/${databaseRun.arm_run_id}`}>Open stored arm-run evidence →</Link>
                  )}
                </div>
                <dl>
                  <div><dt>Reviewed trials</dt><dd>{formatNumber(row.reviewedTrialCount)}</dd></div>
                  <div><dt>Reviewed pass rate</dt><dd>{formatPercent(row.reviewedPassRate)}</dd></div>
                  <div><dt>Stored raw / qualified pass</dt><dd>{quality
                    ? <QualityPassRate compact row={quality} />
                    : "Unavailable"}</dd></div>
                  <div>
                    <dt>Suspect no-op</dt>
                    <dd>
                      {quality && quality.suspect_noop_count > 0 ? (
                        <Link href={buildSuspectNoopHref({ run_label: row.selectedRunLabel })}>
                          <QualityBadge count={quality.suspect_noop_count} />
                        </Link>
                      ) : quality ? (
                        <QualityBadge count={quality.suspect_noop_count} />
                      ) : "Unavailable"}
                    </dd>
                  </div>
                  <div>
                    <dt>Stored completion</dt>
                    <dd>{databaseRun?.finished_at ?? "Unavailable"}</dd>
                  </div>
                  <div>
                    <dt>Stored median runtime</dt>
                    <dd>{databaseRun ? formatSeconds(databaseRun.median_runtime_seconds) : "Unavailable"}</dd>
                  </div>
                  <div>
                    <dt>R2 artifacts</dt>
                    <dd>{databaseRun
                      ? `${formatNumber(databaseRun.r2_artifact_count)} / ${formatNumber(databaseRun.artifact_count)}`
                      : "Unavailable"}</dd>
                  </div>
                </dl>
              </article>
            );
          })}
        </div>
      </section>

      <h2>Valid imported evidence inventory</h2>
      <CorpusScopeNotice
        scopeId="valid-imported"
        observedCounts={overview ? { trialCount: overview.trial_count } : {}}
      />
      <DataFreshnessNotice freshness={validImportedFreshness} />
      <section className="metric-grid">
        <MetricCard label="Valid imported trials" value={overview ? formatNumber(overview.trial_count) : "Unavailable"} detail="Canary + smoke + full valid arm runs" />
        <MetricCard label="Valid-run R2 artifacts" value={overview ? formatNumber(overview.artifact_count) : "Unavailable"} detail="Tracked evidence rows" />
        <MetricCard label="Recorded cost" value={overview
          ? formatRecordedCost(overview.cost_usd, overview.cost_row_count, overview.missing_cost_count)
          : "Unavailable"} detail="Known cost rows only; not the reviewed adjusted-cost total" />
      </section>
    </AppShell>
  );
}
