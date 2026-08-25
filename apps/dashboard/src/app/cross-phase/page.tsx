import {
  formatCurrentCostRelation,
} from "../../lib/current-cost-presentation";
import Link from "next/link";

import { AppShell } from "../../components/AppShell";
import { TermInfo } from "../../components/TermInfo";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { CorpusScopeSelector } from "../../components/CorpusScopeSelector";
import { getCorpusScope, getCorpusScopePresentationLabel } from "../../lib/corpus-scopes";
import {
  getBehaviorRows,
  getCrossPhaseRows,
  getPhaseSummaries,
  getRouterComparisonRows,
} from "../../lib/cross-phase-reporting";
import {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  selectCurrentReviewedPhase3Scope,
} from "../../lib/phase3-current-reviewed-comparison";
import { getCostPerformanceChartArms } from "../../lib/cost-performance-chart";
import {
  friendlyModelLabel,
  friendlyProviderLabel,
  friendlyRoutingLabel,
} from "../../lib/presentation-labels";

export const dynamic = "force-dynamic";

function formatPercent(value: number | null): string {
  if (value === null) return "Unavailable";
  return `${(value * 100).toFixed(1)}%`;
}

function formatMoney(value: number | null, maximumFractionDigits = 2): string {
  if (value === null) return "Unavailable";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits,
  }).format(value);
}

function linkedMoney(value: number | null, href: string, maximumFractionDigits = 2) {
  const formatted = formatMoney(value, maximumFractionDigits);
  return value === null ? formatted : <Link href={href}>{formatted}</Link>;
}

function formatRatio(value: number | null): string {
  if (value === null) return "n/a";
  return value.toFixed(2);
}

function phaseDisplayLabel(phase: string, scopeId: "phase3-core" | "phase3-extended"): string {
  const scope = getCorpusScope(scopeId);
  return phase === "phase3"
    ? `${scope.displayLabel} — ${getCorpusScopePresentationLabel(scope)}`
    : phase;
}

type CrossPhasePageProps = {
  searchParams?: Promise<{ scope?: string | string[] }>;
};

function evidenceLabel(
  value: string | null | undefined,
): string {
  if (!value) return "Not recorded";
  return value.split("_").join(" ");
}

export default async function CrossPhasePage({ searchParams }: CrossPhasePageProps) {
  const params = searchParams ? await searchParams : {};
  const selection =
    selectCurrentReviewedPhase3Scope(params.scope);
  const selectedScope = selection.scope;
  const rows = getCrossPhaseRows(selectedScope);
  const summaries = getPhaseSummaries(rows, selectedScope);
  const routerRows = getRouterComparisonRows();
  const behaviorRows = getBehaviorRows();

  const phase3Rows = rows
    .filter((row) => row.phase === "phase3")
    .sort((a, b) => b.pass_rate - a.pass_rate);

  const efficientPhase3Rows = [...phase3Rows]
    .filter(
      (row) =>
        row.comparison_cost_per_clean_success_usd
          !== null,
    )
    .sort(
      (left, right) =>
        (
          left.comparison_cost_per_clean_success_usd
            ?? Infinity
        )
        - (
          right.comparison_cost_per_clean_success_usd
            ?? Infinity
        ),
    )
    .slice(0, 8);

  const behaviorByArm = new Map(behaviorRows.map((row) => [row.arm_id, row]));
  const phase3Summary = summaries.find((summary) => summary.phase === "phase3");
  const chartArms = getCostPerformanceChartArms(selection.scopeId);
  const chartArmById = new Map(chartArms.map((arm) => [arm.armId, arm]));
  if (
    phase3Rows.some((row) => {
      const chartArm =
        chartArmById.get(row.arm_id);
      if (!chartArm) return true;
      return (
        row.current_selected_run_label !== null
        && row.current_selected_run_label
          !== chartArm.selectedRunLabel
      );
    })
  ) {
    throw new Error(
      "Cross-phase current-reviewed rows and frozen selected-run membership disagree",
    );
  }

  return (
    <AppShell
      title={`Cross-phase: ${phaseDisplayLabel("phase3", selection.scopeId)}`}
      description={`File-backed reporting view for frozen Phase 1/2 baselines and the ${selectedScope.displayName.toLowerCase()} using the current-reviewed 2026-08-25 selected-cost layer with historical Phase 3 evidence retained separately.`}
    >
      <CorpusScopeSelector pathname="/cross-phase" selectedScopeId={selection.scopeId} />
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <CorpusScopeNotice
        scopeId={selection.scopeId}
        costPresentation="current_and_historical"
        observedCounts={{
          armCount: phase3Summary?.arm_count ?? 0,
          trialCount: phase3Summary?.trial_count ?? 0,
          successCount: phase3Summary?.success_count ?? 0,
        }}
      />
      <section className="quality-context-panel">
        <strong>Current comparison provenance:</strong> Phase 3 decision-facing cost values come from the
        {" "}{PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt} current-reviewed selected-cost layer.
        Frozen Phase 1/2 baselines remain unchanged. Historical Phase 3 reviewed costs, outcome-cost shares,
        router-associated comparisons, and behavior tags remain separate historical evidence from the
        {" "}{PHASE3_CURRENT_REVIEWED_COMPARISON.historicalReviewedAt} layer. Provider-billed aggregate totals
        are not redistributed across trials or outcomes.
        {" "}<Link href={`/cost-coverage?scope=${selection.scopeId}`}>Open Cost Coverage with this scope</Link>.
        <details>
          <summary>Traceable current and historical sources</summary>
          <p className="mono">results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json</p>
          <p className="mono">results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json</p>
        </details>
      </section>

      <section className="phase-summary-grid" aria-label="Cross-phase summary cards">
        {summaries.map((summary) => (
          <article className="metric-card phase-summary-card" key={summary.phase}>
            <header className="phase-summary-header">
              <span className="metric-label">{phaseDisplayLabel(summary.phase, selection.scopeId)}</span>
              <strong className="phase-summary-rate">{formatPercent(summary.pass_rate)}</strong>
              <span className="phase-summary-rate-label">Pass rate</span>
            </header>
            <dl className="phase-summary-details">
              <div>
                <dt>Population</dt>
                <dd>{summary.arm_count} arms</dd>
              </div>
              <div>
                <dt>Results</dt>
                <dd>{summary.success_count}/{summary.trial_count} successes</dd>
              </div>
              <div>
                <dt>Comparison cost</dt>
                <dd>{formatMoney(summary.comparison_cost_usd, 6)}</dd>
              </div>
              <div>
                <dt>Cost basis</dt>
                <dd>{summary.comparison_cost_label}</dd>
              </div>
            </dl>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Phase summaries</h2>
            <p>Frozen Phase 1/2 totals plus the selected reviewed Phase 3 comparison.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Phase</th>
                <th>Arms</th>
                <th>Trials</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Comparison cost</th>
                <th>Cost basis</th>
                <th>Comparison cost / clean success</th>
                <th>Historical Phase 3 reviewed cost</th>
                <th>Historical unclean spend share</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((summary) => (
                <tr key={summary.phase}>
                  <td className="sticky-id-column"><span className="quality-badge">{phaseDisplayLabel(summary.phase, selection.scopeId)}</span></td>
                  <td>{summary.arm_count}</td>
                  <td>{summary.trial_count}</td>
                  <td>{summary.success_count}</td>
                  <td>{formatPercent(summary.pass_rate)}</td>
                  <td>{formatMoney(summary.comparison_cost_usd, 6)}</td>
                  <td>{summary.comparison_cost_label}</td>
                  <td>{formatMoney(summary.comparison_cost_per_clean_success_usd)}</td>
                  <td>{formatMoney(summary.historical_reviewed_cost_usd, 6)}</td>
                  <td>{formatPercent(summary.historical_unclean_spend_share)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>All arms across phases</h2>
            <p>Phase 1/2 direct baselines and Phase 3 router-mediated arms in one table.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Phase</th>
                <th>Provider</th>
                <th>Model</th>
                <th><span className="term-label">Routing path <TermInfo term="Routing path" /></span></th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Recorded cost</th>
                <th>Comparison cost</th>
                <th>Cost basis</th>
                <th>Comparison cost / clean success</th>
                <th>Historical Phase 3 reviewed cost</th>
                <th>Historical unclean spend share</th>
                <th>Evidence status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const isPhase3 = row.phase === "phase3";
                const chartArm = row.phase === "phase3" ? chartArmById.get(row.arm_id) : null;
                const providerLabel = isPhase3 ? friendlyProviderLabel(row.provider) : row.provider;
                const modelLabel = isPhase3 ? friendlyModelLabel(row.backend_model) : row.backend_model;
                const routingLabel = isPhase3 ? friendlyRoutingLabel(row.routing_path) : row.routing_path;
                return <tr key={`${row.phase}:${row.arm_id}`}>
                  <td className="sticky-id-column">
                    <div className="mono">{chartArm ? <Link href={chartArm.armHref}>{row.arm_id}</Link> : row.arm_id}</div>
                    {chartArm ? (
                      <div className="row-action-links">
                        <Link href={chartArm.selectedRunHref}>Selected run</Link>
                        <Link href={`/artifacts?arm_id=${encodeURIComponent(row.arm_id)}`}>Artifacts</Link>
                      </div>
                    ) : (
                      <div className="muted">Frozen aggregate row</div>
                    )}
                  </td>
                  <td>{phaseDisplayLabel(row.phase, selection.scopeId)}</td>
                  <td>
                    {isPhase3 ? (
                      <>
                        <strong>{providerLabel}</strong>
                        {providerLabel !== row.provider ? <div className="muted mono">{row.provider}</div> : null}
                      </>
                    ) : row.provider}
                  </td>
                  <td>
                    {isPhase3 ? (
                      <>
                        <strong>{modelLabel}</strong>
                        {modelLabel !== row.backend_model ? <div className="muted mono">{row.backend_model}</div> : null}
                      </>
                    ) : row.backend_model}
                  </td>
                  <td>
                    {isPhase3 ? (
                      <>
                        <strong>{routingLabel}</strong>
                        {routingLabel !== row.routing_path ? <div className="muted mono">{row.routing_path}</div> : null}
                      </>
                    ) : row.routing_path}
                  </td>
                  <td>{row.success_count}/{row.trial_count}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{chartArm ? linkedMoney(row.recorded_cost_usd, chartArm.costProvenanceHref, 6) : formatMoney(row.recorded_cost_usd, 6)}</td>
                  <td>
                    {formatCurrentCostRelation(
                      formatMoney(row.comparison_cost_usd, 7),
                      row.comparison_cost_relation,
                    )}
                  </td>
                  <td>{row.comparison_cost_label}</td>
                  <td>
                    {formatCurrentCostRelation(
                      formatMoney(row.comparison_cost_per_clean_success_usd),
                      row.comparison_efficiency_relation,
                    )}
                  </td>
                  <td>{chartArm ? linkedMoney(row.historical_reviewed_cost_usd, chartArm.costProvenanceHref, 7) : formatMoney(row.historical_reviewed_cost_usd, 7)}</td>
                  <td>{formatPercent(row.historical_unclean_spend_share)}</td>
                  <td className="table-cell-wrap">
                    <div>{row.comparison_cost_confidence} comparison-cost confidence</div>
                    {row.phase === "phase3" ? (
                      <>
                        <div className="muted">
                          Selected trial allocation: {evidenceLabel(row.selected_trial_allocation_status)} · selected outcome allocation: {evidenceLabel(row.selected_outcome_allocation_status)} · provider billing: {evidenceLabel(row.provider_billing_reconciliation_status)}
                        </div>
                        <div className="muted">
                          Historical pricing provenance: {evidenceLabel(row.pricing_provenance_status)} · historical arm-run allocation: {evidenceLabel(row.arm_run_allocation_confidence)}
                        </div>
                        {row.current_selected_run_label ? (
                          <div className="muted mono">
                            Current reconciliation run: {row.current_selected_run_label}
                          </div>
                        ) : null}
                      </>
                    ) : null}
                  </td>
                </tr>;
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{selectedScope.displayName} cost-efficient clean successes</h2>
            <p>Lowest current selected cost per clean success. These are aggregate selected-cost efficiency ratios and do not require trial-level or outcome-level cost allocation. Historical unclean-spend shares are shown separately and are never applied to provider-billed selected totals. Behavior tags remain tied to the retained historical Phase 3 core source and may reflect the older historical cost layer.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Model</th>
                <th>Pass rate</th>
                <th>Current selected cost</th>
                <th>Selected cost / clean success</th>
                <th>Historical unclean spend share</th>
                <th>Historical behavior tags</th>
              </tr>
            </thead>
            <tbody>
              {efficientPhase3Rows.map((row) => {
                const behavior = behaviorByArm.get(row.arm_id);
                const chartArm = chartArmById.get(row.arm_id);
                if (!chartArm) throw new Error(`No exact frozen selected run exists for ${row.arm_id}`);
                return (
                  <tr key={row.arm_id}>
                    <td className="sticky-id-column">
                      <div className="mono"><Link href={chartArm.armHref}>{row.arm_id}</Link></div>
                      <div className="row-action-links">
                        <Link href={chartArm.selectedRunHref}>Selected run</Link>
                        <Link href={`/artifacts?arm_id=${encodeURIComponent(row.arm_id)}`}>Artifacts</Link>
                      </div>
                    </td>
                    <td>
                      <strong>{friendlyModelLabel(row.backend_model)}</strong>
                      {friendlyModelLabel(row.backend_model) !== row.backend_model
                        ? <div className="muted mono">{row.backend_model}</div>
                        : null}
                    </td>
                    <td>{formatPercent(row.pass_rate)}</td>
                    <td>
                      {formatCurrentCostRelation(
                        formatMoney(row.comparison_cost_usd, 7),
                        row.comparison_cost_relation,
                      )}
                    </td>
                    <td>
                      {formatCurrentCostRelation(
                        formatMoney(row.comparison_cost_per_clean_success_usd),
                        row.comparison_efficiency_relation,
                      )}
                    </td>
                    <td>{formatPercent(row.historical_unclean_spend_share)}</td>
                    <td>{behavior?.behavior_tags ?? ""}</td>
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
            <h2>Router-associated comparisons</h2>
            <p>Historical source population: the retained 15-arm Phase 3 core comparison. This section does not include Kimi K3 or inherit the selected extended denominator.</p>
            <p>Observational comparison only: routing path changed along with date, provider-side model revisions, runner setup, invalid-run handling, and accounting policy.</p>
            <p>Cost and clean-success ratios in this section are frozen historical adjusted-cost ratios. They are not recomputed from the current provider-billed corrections.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Model family</th>
                <th>Direct phase</th>
                <th>Direct arm</th>
                <th>Router arm</th>
                <th>Pass delta</th>
                <th>Cost ratio</th>
                <th>Clean-success cost ratio</th>
                <th>Runtime ratio</th>
                <th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {routerRows.map((row) => (
                <tr key={`${row.direct_phase}:${row.direct_arm_id}:${row.router_arm_id}`}>
                  <td className="sticky-id-column">{row.model_family}</td>
                  <td>{row.direct_phase}</td>
                  <td>{row.direct_arm_id}</td>
                  <td>{row.router_arm_id}</td>
                  <td>{row.delta_pass_rate_pct_points.toFixed(1)} pp</td>
                  <td>{formatRatio(row.router_vs_direct_cost_ratio)}</td>
                  <td>{formatRatio(row.router_vs_direct_cost_per_clean_success_ratio)}</td>
                  <td>{formatRatio(row.router_vs_direct_wall_clock_ratio)}</td>
                  <td className="table-cell-wrap">{row.interpretation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
