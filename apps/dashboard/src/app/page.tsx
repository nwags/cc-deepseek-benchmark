import { AppShell } from "../components/AppShell";
import { MetricCard } from "../components/MetricCard";
import {
  getArmRows,
  getModeStatusRows,
  getOverview,
  getRecentRuns,
  getTaskRows
} from "../lib/dashboard-data";
import { formatRecordedCost, formatCurrency, formatNumber, formatPercent, formatSeconds } from "../lib/format";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [overview, modes, arms, tasks, recentRuns] = await Promise.all([
    getOverview(),
    getModeStatusRows(),
    getArmRows(),
    getTaskRows(),
    getRecentRuns()
  ]);

  return (
    <AppShell
      title="Phase 3 Router Dashboard"
      description="Live metadata view over Supabase benchmark summaries and Cloudflare R2 artifact records."
    >

      <section className="metric-grid">
        <MetricCard label="Runs" value={formatNumber(overview.run_count)} detail="Phase 3 run roots" />
        <MetricCard label="Trials" value={formatNumber(overview.trial_count)} detail="Canary + smoke trials" />
        <MetricCard label="Artifacts" value={formatNumber(overview.artifact_count)} detail="Tracked metadata rows" />
        <MetricCard label="Cost" value={formatRecordedCost(overview.cost_usd, overview.cost_row_count, overview.missing_cost_count)} detail="Recorded trial cost" />
        <MetricCard label="Completed runs" value={formatNumber(overview.completed_runs)} />
        <MetricCard label="Errored runs" value={formatNumber(overview.noncompleted_runs)} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Run status by mode</h2>
          <p>High-level split across canary and smoke runs.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Mode</th>
                <th>Status</th>
                <th>Runs</th>
                <th>Trials</th>
                <th>Artifacts</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {modes.map((row) => (
                <tr key={`${row.mode}-${row.status}`}>
                  <td>{row.mode}</td>
                  <td><span className={`status status-${row.status}`}>{row.status}</span></td>
                  <td>{formatNumber(row.run_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.artifact_count)}</td>
                  <td>{formatRecordedCost(row.cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Arms</h2>
          <p>Current Phase 3 model arms with imported run metadata.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Runs</th>
                <th>Trials</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Median runtime</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((row) => (
                <tr key={row.arm_id}>
                  <td className="mono">{row.arm_id}</td>
                  <td>{formatNumber(row.run_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                  <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Tasks</h2>
          <p>Task-level summary for imported Phase 3 trials.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Trials</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Median runtime</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((row) => (
                <tr key={row.task_id}>
                  <td className="mono">{row.task_name}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                  <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Recent runs</h2>
          <p>Latest imported run roots and artifact coverage.</p>
        </div>
        <div className="run-list">
          {recentRuns.map((row) => (
            <article className="run-card" key={row.run_label}>
              <div>
                <h3>{row.run_label}</h3>
                <p>{row.mode} · {row.status}</p>
              </div>
              <dl>
                <div><dt>Trials</dt><dd>{formatNumber(row.trial_count)}</dd></div>
                <div><dt>Pass rate</dt><dd>{formatPercent(row.pass_rate)}</dd></div>
                <div><dt>Cost</dt><dd>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</dd></div>
                <div><dt>R2 artifacts</dt><dd>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
