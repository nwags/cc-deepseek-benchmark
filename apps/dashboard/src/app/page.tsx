import Link from "next/link";
import { AppShell } from "../components/AppShell";
import { MetricCard } from "../components/MetricCard";
import {
  getArmRunRows,
  getEvalSuites,
  getOverview,
  getSuiteArmComparison
} from "../lib/dashboard-data";
import { formatRecordedCost, formatCurrency, formatNumber, formatPercent, formatSeconds } from "../lib/format";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [overview, suites, armRuns, fullSuiteRows] = await Promise.all([
    getOverview(),
    getEvalSuites(),
    getArmRunRows(8),
    getSuiteArmComparison("phase3-full-20")
  ]);

  const fullSuite = suites.find((suite) => suite.suite_id === "phase3-full-20");

  return (
    <AppShell
      title="Phase 3 Router Dashboard"
      description="Sponsor-facing benchmark dashboard organized by eval suites, arm runs, evals, and artifacts."
    >
      <section className="metric-grid">
        <MetricCard label="Raw runs" value={formatNumber(overview.run_count)} detail="Imported run roots" />
        <MetricCard label="Trials" value={formatNumber(overview.trial_count)} detail="All imported Phase 3 trials" />
        <MetricCard label="Artifacts" value={formatNumber(overview.artifact_count)} detail="Tracked metadata rows" />
        <MetricCard label="Recorded cost" value={formatRecordedCost(overview.cost_usd, overview.cost_row_count, overview.missing_cost_count)} />
        <MetricCard label="Full-suite arms" value={formatNumber(fullSuite?.arm_run_count ?? 0)} detail="phase3-full-20" />
        <MetricCard label="Full-suite pass rate" value={formatPercent(fullSuite?.pass_rate ?? null)} detail="Imported full arms" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Phase 3 full-suite comparison</h2>
            <p>Current imported full-sweep arms in <Link href="/eval-suites/phase3-full-20">phase3-full-20</Link>.</p>
          </div>
          <Link href="/eval-suites">All eval suites →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Tasks</th>
                <th>Trials</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Median runtime</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {fullSuiteRows.map((row) => (
                <tr key={row.arm_id}>
                  <td className="mono">{row.arm_id}</td>
                  <td>{formatNumber(row.task_count)}</td>
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
          <div>
            <h2>Recent arm runs</h2>
            <p>Concrete model-arm executions with logical mode and storage mode separated.</p>
          </div>
          <Link href="/arm-runs">All arm runs →</Link>
        </div>
        <div className="run-list">
          {armRuns.map((row) => (
            <article className="run-card" key={row.arm_run_id}>
              <div>
                <h3>
                  <Link href={`/arm-runs/${row.arm_run_id}`}>{row.arm_id}</Link>
                </h3>
                <p>{row.logical_mode} / {row.storage_mode ?? "—"} · {row.suite_id ?? "no suite"} · {row.status}</p>
                <p className="mono">{row.run_label}</p>
              </div>
              <dl>
                <div><dt>Trials</dt><dd>{formatNumber(row.trial_count)}</dd></div>
                <div><dt>Pass rate</dt><dd>{formatPercent(row.pass_rate)}</dd></div>
                <div><dt>Cost</dt><dd>{formatCurrency(row.trial_cost_usd)}</dd></div>
                <div><dt>R2 artifacts</dt><dd>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
