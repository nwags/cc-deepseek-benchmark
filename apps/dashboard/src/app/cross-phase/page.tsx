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
import { selectReviewedPhase3Scope } from "../../lib/phase3-reviewed-comparison";
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

function evidenceLabel(value: string | undefined): string {
  if (!value) return "Not recorded";
  return value.split("_").join(" ");
}

export default async function CrossPhasePage({ searchParams }: CrossPhasePageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = selectReviewedPhase3Scope(params.scope);
  const selectedScope = selection.scope;
  const rows = getCrossPhaseRows(selectedScope);
  const summaries = getPhaseSummaries(rows, selectedScope);
  const routerRows = getRouterComparisonRows();
  const behaviorRows = getBehaviorRows();

  const phase3Rows = rows
    .filter((row) => row.phase === "phase3")
    .sort((a, b) => b.pass_rate - a.pass_rate);

  const efficientPhase3Rows = [...phase3Rows]
    .filter((row) => row.cost_per_clean_success_usd !== null)
    .sort((a, b) => (a.cost_per_clean_success_usd ?? Infinity) - (b.cost_per_clean_success_usd ?? Infinity))
    .slice(0, 8);

  const behaviorByArm = new Map(behaviorRows.map((row) => [row.arm_id, row]));
  const phase3Summary = summaries.find((summary) => summary.phase === "phase3");
  const chartArms = getCostPerformanceChartArms(selection.scopeId);
  const chartArmById = new Map(chartArms.map((arm) => [arm.armId, arm]));
  if (phase3Rows.some((row) => !chartArmById.has(row.arm_id))) {
    throw new Error("Cross-phase Phase 3 rows and frozen selected-run membership disagree");
  }

  return (
    <AppShell
      title={`Cross-phase: ${phaseDisplayLabel("phase3", selection.scopeId)}`}
      description={`File-backed reporting view for frozen Phase 1/2 baselines and the ${selectedScope.displayName.toLowerCase()} from the reviewed 2026-08-05 comparison layer.`}
    >
      <CorpusScopeSelector pathname="/cross-phase" selectedScopeId={selection.scopeId} />
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <CorpusScopeNotice
        scopeId={selection.scopeId}
        observedCounts={{
          armCount: phase3Summary?.arm_count ?? 0,
          trialCount: phase3Summary?.trial_count ?? 0,
          successCount: phase3Summary?.success_count ?? 0,
        }}
      />
      <section className="quality-context-panel">
        <strong>Reviewed comparison provenance:</strong> The selected Phase 3 rows come from the reviewed 2026-08-05 layer.
        Phase 3 core remains the historical alternate; Phase 1/2 aggregates and earlier Phase 3 source artifacts remain unchanged.
        {" "}<Link href={`/cost-coverage?scope=${selection.scopeId}`}>Open Cost Coverage with this scope</Link>.
        <details>
          <summary>Traceable reviewed source</summary>
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
                <dt>Reviewed cost</dt>
                <dd>{formatMoney(summary.adjusted_cost_usd, 6)}</dd>
              </div>
              <div>
                <dt>Cost basis</dt>
                <dd>{summary.cost_label}</dd>
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
                <th>Reviewed cost</th>
                <th>Cost basis</th>
                <th>Cost / clean success</th>
                <th>Unclean spend share</th>
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
                  <td>{formatMoney(summary.adjusted_cost_usd, 6)}</td>
                  <td>{summary.cost_label}</td>
                  <td>{formatMoney(summary.cost_per_clean_success_usd)}</td>
                  <td>{formatPercent(summary.unclean_spend_share)}</td>
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
                <th>Reviewed cost</th>
                <th>Cost basis</th>
                <th>Cost / clean success</th>
                <th>Unclean spend</th>
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
                  <td>{chartArm ? linkedMoney(row.adjusted_cost_usd, chartArm.costProvenanceHref, 7) : formatMoney(row.adjusted_cost_usd, 7)}</td>
                  <td>{row.reviewed_cost_label ?? "Adjusted known cost"}</td>
                  <td>{chartArm ? linkedMoney(row.cost_per_clean_success_usd, chartArm.costProvenanceHref) : formatMoney(row.cost_per_clean_success_usd)}</td>
                  <td>{formatPercent(row.unclean_spend_share)}</td>
                  <td className="table-cell-wrap">
                    <div>{row.cost_confidence} confidence</div>
                    {row.phase === "phase3" ? (
                      <div className="muted">
                        Pricing provenance: {evidenceLabel(row.pricing_provenance_status)} · allocation: {evidenceLabel(row.arm_run_allocation_confidence)} · trial allocation: {evidenceLabel(row.trial_allocation_status)} · billing: {evidenceLabel(row.billing_reconciliation_status)}
                      </div>
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
            <p>Lowest available adjusted cost per clean success. Arms without outcome-level allocation, including Kimi K3, are not assigned a fabricated value. Behavior tags remain tied to the retained historical Phase 3 core source.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Model</th>
                <th>Pass rate</th>
                <th>Reviewed cost</th>
                <th>Cost / clean success</th>
                <th>Unclean spend</th>
                <th>Behavior tags</th>
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
                    <td>{linkedMoney(row.adjusted_cost_usd, chartArm.costProvenanceHref, 7)}</td>
                    <td>{linkedMoney(row.cost_per_clean_success_usd, chartArm.costProvenanceHref)}</td>
                    <td>{formatPercent(row.unclean_spend_share)}</td>
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
