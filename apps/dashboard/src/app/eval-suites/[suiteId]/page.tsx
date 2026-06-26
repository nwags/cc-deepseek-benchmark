import Link from "next/link";
import { notFound } from "next/navigation";
import { TermInfo } from "../../../components/TermInfo";
import { AppShell } from "../../../components/AppShell";
import { SuiteHeatmap } from "../../../components/SuiteHeatmap";
import { QualityPassRate, QualityBadge } from "../../../components/QualityContext";
import { getEvalSuites, getSuiteArmComparison, getSuiteTaskDifficulty, getSuiteHeatmapCells, getSuiteArmQualityRows, getSuiteQualityTotals } from "../../../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalSuiteDetailPage({
  params
}: {
  params: Promise<{ suiteId: string }>;
}) {
  const { suiteId } = await params;
  const decodedSuiteId = decodeURIComponent(suiteId);
  const [suites, rows, difficultyRows, heatmapCells, qualityRows, qualityTotals] = await Promise.all([
    getEvalSuites(),
    getSuiteArmComparison(decodedSuiteId),
    getSuiteTaskDifficulty(decodedSuiteId, 25),
    getSuiteHeatmapCells(decodedSuiteId),
    getSuiteArmQualityRows(decodedSuiteId),
    getSuiteQualityTotals(decodedSuiteId)
  ]);
  const qualityByArm = new Map(qualityRows.map((row) => [row.arm_id, row]));
  const suite = suites.find((row) => row.suite_id === decodedSuiteId);

  if (!suite) {
    notFound();
  }

  return (
    <AppShell
      title={suite.display_name}
      description={suite.description ?? "Suite-level cross-arm comparison."}
    >
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{suite.suite_id}</h2>
            <p><Link href="/eval-suites">← Back to eval suites</Link></p>
          </div>
          <span className="status">{suite.suite_type}</span>
        </div>
        <div className="detail-grid">
          <div><span>Suite items</span><strong>{formatNumber(suite.suite_items)}</strong></div>
          <div><span>Arm runs</span><strong>{formatNumber(suite.arm_run_count)}</strong></div>
          <div><span>Trials</span><strong>{formatNumber(suite.trial_count)}</strong></div>
          <div><span>Raw pass rate</span><strong>{formatPercent(suite.pass_rate)}</strong></div>
          <div><span>Suspect no-op</span><strong>{formatNumber(qualityTotals?.suspect_noop_count ?? 0)}</strong></div>
          <div><span>Benchmark</span><strong>{suite.benchmark} {suite.benchmark_version ?? ""}</strong></div>
          <div><span>Version</span><strong>{suite.version ?? "—"}</strong></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Arm comparison</h2>
          <p>All imported arm runs attached to this suite.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Tasks</th>
                <th>Trials</th>
                <th>Successes</th>
                <th><span className="term-label">Raw / qualified pass <TermInfo term="Pass rate" /></span></th>
                <th>Suspect no-op</th>
                <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.suite_id}-${row.arm_id}`}>
                  <td className="mono">{row.arm_id}</td>
                  <td>{formatNumber(row.task_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td><QualityPassRate row={qualityByArm.get(row.arm_id) ?? {
                    raw_pass_rate: row.pass_rate,
                    trial_count: row.trial_count,
                    success_count: row.success_count,
                    qualified_pass_rate: row.pass_rate,
                    qualified_trial_count: row.trial_count,
                    qualified_success_count: row.success_count,
                    suspect_noop_count: 0
                  }} /></td>
                  <td><QualityBadge count={qualityByArm.get(row.arm_id)?.suspect_noop_count ?? 0} /></td>
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
        title="Eval × arm heatmap"
        description="Rows are evals, columns are arms attached to this suite, and each cell shows successes / trials."
      />

      <section className="panel">
        <div className="panel-heading">
          <h2>Task difficulty</h2>
          <p>Tasks ordered from lowest to highest pass rate within this suite.</p>
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
              {difficultyRows.map((row) => (
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

    </AppShell>
  );
}
