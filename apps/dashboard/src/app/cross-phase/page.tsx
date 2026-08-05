import { AppShell } from "../../components/AppShell";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { getCorpusScope, getCorpusScopePresentationLabel } from "../../lib/corpus-scopes";
import {
  getBehaviorRows,
  getCrossPhaseRows,
  getPhaseSummaries,
  getRouterComparisonRows,
} from "../../lib/cross-phase-reporting";

export const dynamic = "force-static";

const PHASE3_CORE_SCOPE = getCorpusScope("phase3-core");

function formatPercent(value: number | null): string {
  if (value === null) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

function formatMoney(value: number | null): string {
  if (value === null) return "n/a";
  return `$${value.toFixed(2)}`;
}

function formatRatio(value: number | null): string {
  if (value === null) return "n/a";
  return value.toFixed(2);
}

function phaseDisplayLabel(phase: string): string {
  return phase === "phase3"
    ? `${PHASE3_CORE_SCOPE.displayLabel} — ${getCorpusScopePresentationLabel(PHASE3_CORE_SCOPE)}`
    : phase;
}

export default function CrossPhasePage() {
  const rows = getCrossPhaseRows();
  const summaries = getPhaseSummaries(rows);
  const routerRows = getRouterComparisonRows();
  const behaviorRows = getBehaviorRows();

  const phase3Rows = rows
    .filter((row) => row.phase === "phase3")
    .sort((a, b) => b.pass_rate - a.pass_rate);

  const efficientPhase3Rows = [...phase3Rows]
    .sort((a, b) => a.cost_per_clean_success_usd - b.cost_per_clean_success_usd)
    .slice(0, 8);

  const behaviorByArm = new Map(behaviorRows.map((row) => [row.arm_id, row]));
  const phase3Summary = summaries.find((summary) => summary.phase === "phase3");

  return (
    <AppShell
      title={`Cross-phase: ${phaseDisplayLabel("phase3")}`}
      description={`File-backed reporting view for Phase 1 direct, Phase 2 direct, and ${PHASE3_CORE_SCOPE.displayLabel} router-mediated benchmark results.`}
    >
      <CorpusScopeNotice
        scopeId="phase3-core"
        observedCounts={{
          armCount: phase3Summary?.arm_count ?? 0,
          trialCount: phase3Summary?.trial_count ?? 0,
          successCount: phase3Summary?.success_count ?? 0,
        }}
      />
      <section className="quality-context-panel">
        <strong>Historical comparison provenance:</strong> This file-backed page represents the July 13 adjusted-cost comparison.
        Supabase-backed current views declare their corpus separately, and the frozen Phase 1/2 aggregates remain unchanged.
      </section>

      <section className="metric-grid">
        {summaries.map((summary) => (
          <article className="metric-card" key={summary.phase}>
            <span className="metric-label">{phaseDisplayLabel(summary.phase)}</span>
            <strong>{formatPercent(summary.pass_rate)}</strong>
            <span className="metric-subtitle">
              {summary.success_count}/{summary.trial_count} successes · {summary.arm_count} arms · {formatMoney(summary.adjusted_cost_usd)}
            </span>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Phase summaries</h2>
            <p>Cross-phase totals using the adjusted-cost reporting layer.</p>
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
                <th>Adjusted cost</th>
                <th>Cost / clean success</th>
                <th>Unclean spend share</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((summary) => (
                <tr key={summary.phase}>
                  <td className="sticky-id-column"><span className="quality-badge">{phaseDisplayLabel(summary.phase)}</span></td>
                  <td>{summary.arm_count}</td>
                  <td>{summary.trial_count}</td>
                  <td>{summary.success_count}</td>
                  <td>{formatPercent(summary.pass_rate)}</td>
                  <td>{formatMoney(summary.adjusted_cost_usd)}</td>
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
                <th>Routing path</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Adjusted cost</th>
                <th>Cost / clean success</th>
                <th>Unclean spend</th>
                <th>Cost confidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.phase}:${row.arm_id}`}>
                  <td className="sticky-id-column">
                    <div className="mono">{row.arm_id}</div>
                    {row.phase === "phase3" ? (
                      <div className="row-action-links">
                        <a href={`/trial-quality?arm_id=${encodeURIComponent(row.arm_id)}`}>Trial quality</a>
                        <a href={`/artifacts?arm_id=${encodeURIComponent(row.arm_id)}`}>Artifacts</a>
                      </div>
                    ) : (
                      <div className="muted">Frozen aggregate row</div>
                    )}
                  </td>
                  <td>{phaseDisplayLabel(row.phase)}</td>
                  <td>{row.provider}</td>
                  <td>{row.backend_model}</td>
                  <td>{row.routing_path}</td>
                  <td>{row.success_count}/{row.trial_count}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatMoney(row.adjusted_cost_usd)}</td>
                  <td>{formatMoney(row.cost_per_clean_success_usd)}</td>
                  <td>{formatPercent(row.unclean_spend_share)}</td>
                  <td>{row.cost_confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{PHASE3_CORE_SCOPE.displayLabel} cost-efficient clean successes</h2>
            <p>Lowest adjusted cost per clean success among rows in the file-backed reviewed comparison.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Model</th>
                <th>Pass rate</th>
                <th>Adjusted cost</th>
                <th>Cost / clean success</th>
                <th>Unclean spend</th>
                <th>Behavior tags</th>
              </tr>
            </thead>
            <tbody>
              {efficientPhase3Rows.map((row) => {
                const behavior = behaviorByArm.get(row.arm_id);
                return (
                  <tr key={row.arm_id}>
                    <td className="sticky-id-column">
                      <div className="mono">{row.arm_id}</div>
                      <div className="row-action-links">
                        <a href={`/trial-quality?arm_id=${encodeURIComponent(row.arm_id)}`}>Trial quality</a>
                        <a href={`/artifacts?arm_id=${encodeURIComponent(row.arm_id)}`}>Artifacts</a>
                      </div>
                    </td>
                    <td>{row.backend_model}</td>
                    <td>{formatPercent(row.pass_rate)}</td>
                    <td>{formatMoney(row.adjusted_cost_usd)}</td>
                    <td>{formatMoney(row.cost_per_clean_success_usd)}</td>
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
                  <td>{row.interpretation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
