import Link from "next/link";
import { TermInfo } from "../components/TermInfo";
import { AppShell } from "../components/AppShell";
import { MetricCard } from "../components/MetricCard";
import { SuiteHeatmap } from "../components/SuiteHeatmap";
import { QualityPassRate, QualityBadge } from "../components/QualityContext";
import {
  getArmRunRows,
  getEvalSuites,
  getOverview,
  getSuiteArmComparison,
  getSuiteTaskDifficulty,
  getSuiteHeatmapCells,
  getSuiteArmQualityRows,
  getArmRunQualityByRunLabels
} from "../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../lib/format";

export const dynamic = "force-dynamic";

function runHealthLabel(status: string, trialCount: number, logicalMode: string) {
  if (status === "completed") return "completed";
  if (status === "errors" && trialCount > 0) {
    return logicalMode === "full" ? "imported with trial errors" : "trial errors";
  }
  return status;
}

export default async function DashboardPage() {
  const [overview, suites, armRuns, fullSuiteRows, hardestFullEvals, heatmapCells, fullSuiteQualityRows] = await Promise.all([
    getOverview(),
    getEvalSuites(),
    getArmRunRows(12),
    getSuiteArmComparison("phase3-full-20"),
    getSuiteTaskDifficulty("phase3-full-20", 8),
    getSuiteHeatmapCells("phase3-full-20"),
    getSuiteArmQualityRows("phase3-full-20")
  ]);

  const fullSuite = suites.find((suite) => suite.suite_id === "phase3-full-20");
  const fullArmRuns = armRuns.filter((row) => row.logical_mode === "full");
  const fullQualityByArm = new Map(fullSuiteQualityRows.map((row) => [row.arm_id, row]));
  const fullRunQualityRows = await getArmRunQualityByRunLabels(fullArmRuns.map((row) => row.run_label));
  const fullQualityByRun = new Map(fullRunQualityRows.map((row) => [row.run_label, row]));

  return (
    <AppShell title="Phase 3 Router Dashboard">
      <section className="metric-grid">
        <MetricCard label="Full-suite arms" value={formatNumber(fullSuite?.arm_run_count ?? 0)} detail="Imported into phase3-full-20" />
        <MetricCard label="Full-suite trials" value={formatNumber(fullSuite?.trial_count ?? 0)} detail="20 evals × 3 attempts × imported arms" />
        <MetricCard label="Full-suite pass rate" value={formatPercent(fullSuite?.pass_rate ?? null)} detail="Across imported full arms" />
        <MetricCard label="All imported trials" value={formatNumber(overview.trial_count)} detail="Canary + smoke + full" />
        <MetricCard label="All R2 artifacts" value={formatNumber(overview.artifact_count)} detail="Tracked evidence rows" />
        <MetricCard label="Recorded cost" value={formatRecordedCost(overview.cost_usd, overview.cost_row_count, overview.missing_cost_count)} detail="Known cost rows only" />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Full-suite leaderboard</h2>
            <p>
              Current imported full-sweep arms in{" "}
              <Link href="/eval-suites/phase3-full-20">phase3-full-20</Link>.
              Costs are recorded costs; rows with missing cost coverage should be treated as lower bounds.
            </p>
          </div>
          <Link href="/eval-suites/phase3-full-20">Open suite →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Arm</th>
                <th>Tasks</th>
                <th>Trials</th>
                <th>Successes</th>
                <th><span className="term-label">Pass rate <TermInfo term="Pass rate" /></span></th>
                <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
                <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
              </tr>
            </thead>
            <tbody>
              {fullSuiteRows.map((row, index) => (
                <tr key={row.arm_id}>
                  <td>{index + 1}</td>
                  <td className="mono">{row.arm_id}</td>
                  <td>{formatNumber(row.task_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td><QualityPassRate row={fullQualityByArm.get(row.arm_id) ?? {
                    raw_pass_rate: row.pass_rate,
                    trial_count: row.trial_count,
                    success_count: row.success_count,
                    qualified_pass_rate: row.pass_rate,
                    qualified_trial_count: row.trial_count,
                    qualified_success_count: row.success_count,
                    suspect_noop_count: 0
                  }} /></td>
                  <td><QualityBadge count={fullQualityByArm.get(row.arm_id)?.suspect_noop_count ?? 0} /></td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                  <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <SuiteHeatmap
        rows={heatmapCells}
        title="Full-suite pass/fail heatmap"
        description="Rows are evals, columns are imported full-suite arms, and each cell shows successes / trials."
      />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Hardest full-suite evals</h2>
            <p>Tasks where the imported full-sweep arms struggle most. These are the best starting points for trajectory review.</p>
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
            <h2>Full arm-run health</h2>
            <p>These are complete imported arm executions. “Trial errors” means failures occurred inside the 60 attempts, not that ingestion failed.</p>
          </div>
          <Link href="/arm-runs">All arm runs →</Link>
        </div>
        <div className="run-list">
          {fullArmRuns.map((row) => (
            <article className="run-card" key={row.arm_run_id}>
              <div>
                <h3>
                  <Link href={`/arm-runs/${row.arm_run_id}`}>{row.arm_id}</Link>
                </h3>
                <p>{row.logical_mode} / {row.storage_mode ?? "—"} · {row.suite_id ?? "no suite"} · {runHealthLabel(row.status, row.trial_count, row.logical_mode)}</p>
                <p className="mono">{row.run_label}</p>
              </div>
              <dl>
                <div><dt>Trials</dt><dd>{formatNumber(row.trial_count)}</dd></div>
                <div><dt>Raw / qualified pass</dt><dd><QualityPassRate compact row={fullQualityByRun.get(row.run_label) ?? {
                  raw_pass_rate: row.pass_rate,
                  trial_count: row.trial_count,
                  success_count: row.success_count,
                  qualified_pass_rate: row.pass_rate,
                  qualified_trial_count: row.trial_count,
                  qualified_success_count: row.success_count,
                  suspect_noop_count: 0
                }} /></dd></div>
                <div><dt>Suspect no-op</dt><dd><QualityBadge count={fullQualityByRun.get(row.run_label)?.suspect_noop_count ?? 0} /></dd></div>
                <div><dt><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></dt><dd>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</dd></div>
                <div><dt>R2 artifacts</dt><dd>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
