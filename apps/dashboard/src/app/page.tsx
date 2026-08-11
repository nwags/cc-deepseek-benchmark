import Link from "next/link";
import { TermInfo } from "../components/TermInfo";
import { AppShell } from "../components/AppShell";
import { CorpusScopeNotice } from "../components/CorpusScopeNotice";
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
  getInvalidArmRunRows
} from "../lib/dashboard-data";
import {
  PHASE3_REVIEWED_COMPARISON,
  getReviewedPhase3Scope,
} from "../lib/phase3-reviewed-comparison";
import {
  PHASE3_REVIEWED_RUN_SELECTION,
  getReviewedRunSelectionScope,
  getReviewedSelectedRunLabels,
} from "../lib/phase3-reviewed-run-selection";
import {
  buildOverviewReviewedComparison,
  type DatabaseReadStatus,
} from "../lib/overview-reviewed-comparison";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../lib/format";

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
  return `$${numeric.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 9,
  })}`;
}

function evidenceLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export default async function DashboardPage() {
  const reviewedScope = getReviewedPhase3Scope("phase3-extended");
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
  ] = await Promise.all([
    readDatabaseEvidence(getOverview()),
    readDatabaseEvidence(getReviewedSelectedArmRunRows(selectedRunLabels)),
    readDatabaseEvidence(getReviewedSelectedRunAdjustedCostRows(selectedRunLabels)),
    readDatabaseEvidence(getSuiteTaskDifficulty("phase3-full-20", 8)),
    readDatabaseEvidence(getSuiteHeatmapCells("phase3-full-20")),
    readDatabaseEvidence(getArmRunQualityByRunLabels([...selectedRunLabels])),
    readDatabaseEvidence(getInvalidArmRunRows()),
  ]);

  const reviewedComparison = buildOverviewReviewedComparison({
    scope: reviewedScope,
    runSelectionScope,
    comparisonReviewedAt: PHASE3_REVIEWED_COMPARISON.reviewedAt,
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

  return (
    <AppShell title="Coding Agent Benchmark Dashboard">
      <h2>Phase 3 extended full-suite comparison</h2>
      <CorpusScopeNotice
        scopeId="phase3-extended"
        observedCounts={{
          armCount: reviewedComparison.armCount,
          trialCount: reviewedComparison.trialCount,
          successCount: reviewedComparison.successCount,
        }}
      />
      <section className="metric-grid">
        <MetricCard label="Reviewed arms" value={formatNumber(reviewedComparison.armCount)} detail="Frozen reviewed comparison membership" />
        <MetricCard label="Reviewed trials" value={formatNumber(reviewedComparison.trialCount)} detail="20 tasks × 3 attempts × 16 selected runs" />
        <MetricCard label="Reviewed pass rate" value={formatPercent(reviewedScope.passRate)} detail={`${formatNumber(reviewedComparison.successCount)} reviewed successes`} />
      </section>

      <section className="quality-context-panel">
        <strong>Reviewed comparison provenance:</strong> Arm-level facts and cost evidence come from the reviewed
        2026-08-05 comparison layer. Exact run labels come from the 2026-08-09 reviewed run-selection contract.
        Database evidence is resolved only for those labels; the database does not select a newer run.
        Current invalid/quarantined full-suite records remain visible in the audit layer:{" "}
        {invalidFullSuiteCount === null ? "Unavailable" : formatNumber(invalidFullSuiteCount)}.{" "}
        <Link href="/trial-quality">Open trial quality audit</Link>.
      </section>

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
            <h2>Reviewed full-suite comparison</h2>
            <p>
              The reviewed comparison freezes one complete valid full-suite run per arm. These run labels are
              recorded by the 2026-08-09 reviewed run-selection contract and do not automatically change when
              newer runs are imported.
            </p>
            <p>
              Database evidence shown here is resolved for those exact run labels. Reviewed facts remain visible
              when current stored evidence is missing, and no mutable suite/arm aggregate is used as a fallback.
              Stored reconciliation reads <code>benchmark.v_valid_arm_run_summary</code> and{" "}
              <code>benchmark.v_trial_adjusted_cost_coverage</code> for the exact labels.
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
                <th>Recorded cost</th>
                <th>Reviewed cost and basis</th>
                <th>Accounting gap</th>
                <th>Cost coverage</th>
                <th>Source and confidence</th>
                <th>Stored-evidence reconciliation</th>
              </tr>
            </thead>
            <tbody>
              {reviewedComparison.rows.map((row) => {
                const quality = selectedQualityByRun.get(row.selectedRunLabel);
                const suspectNoopCount = quality?.suspect_noop_count ?? 0;
                const isKimi = row.armId === "router-kimi-k3";
                return (
                  <tr key={row.selectedRunLabel}>
                    <td>{row.rank}</td>
                    <td>
                      <div className="mono">{row.armId}</div>
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
                    <td>{formatReviewedUsd(row.reviewedRecordedCostUsd)}</td>
                    <td>
                      {isKimi ? (
                        <>
                          <strong>Qualified retained-rate estimate:</strong>{" "}
                          {formatReviewedUsd(row.reviewedQualifiedRetainedRateCostUsd)}
                          <div>Adjusted known cost: Unavailable</div>
                        </>
                      ) : (
                        <>
                          <strong>Adjusted known cost:</strong>{" "}
                          {formatReviewedUsd(row.reviewedAdjustedKnownCostUsd)}
                        </>
                      )}
                    </td>
                    <td>{formatReviewedUsd(row.reviewedAccountingGapUsd)}</td>
                    <td>
                      <div>Missing recorded: {formatNumber(row.missingRecordedCostCount)}</div>
                      <div>Unresolved adjusted: {formatNumber(row.unresolvedAdjustedCostCount)}</div>
                    </td>
                    <td>
                      <div>{row.costSources.join(", ")}</div>
                      <div>Confidence: {row.costConfidence}</div>
                      {isKimi && (
                        <>
                          <div>Pricing-source provenance incomplete</div>
                          <div>Provider-log allocation confidence low</div>
                          <div>Provider-log exclusivity not proven</div>
                          <div>Trial allocation unresolved</div>
                          <div>Not invoice-level or provider-billed spend</div>
                        </>
                      )}
                    </td>
                    <td>
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
                          <div>Stored recorded evidence: {formatReviewedUsd(row.databaseAdjustedCostEvidence.recorded_cost_usd)}</div>
                          <div>Stored adjusted evidence: {formatReviewedUsd(row.databaseAdjustedCostEvidence.adjusted_known_cost_usd)}</div>
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

      <section className="quality-context-panel">
        <strong>Different population below:</strong> the heatmap and hardest-task sections use current dynamic
        valid-imported <code>phase3-full-20</code> suite/arm aggregates. They are not restricted to the frozen
        16 selected reviewed run labels and can combine multiple valid imports for an arm.
        {(heatmapCellsRead.status === "unavailable" || hardestFullEvalsRead.status === "unavailable") && (
          <p role="alert">The current dynamic suite aggregates are unavailable; no reviewed-run values were substituted.</p>
        )}
      </section>

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
            const databaseRun = row.databaseRunEvidence;
            const quality = selectedQualityByRun.get(row.selectedRunLabel);
            return (
              <article className="run-card" key={row.selectedRunLabel}>
                <div>
                  <h3>
                    <Link href={row.selectedRunHref}>{row.armId}</Link>
                  </h3>
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
