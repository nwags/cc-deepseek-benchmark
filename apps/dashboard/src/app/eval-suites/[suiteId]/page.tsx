import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { getEvalSuites, getSuiteArmComparison, getSuiteTaskDifficulty } from "../../../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalSuiteDetailPage({
  params
}: {
  params: Promise<{ suiteId: string }>;
}) {
  const { suiteId } = await params;
  const decodedSuiteId = decodeURIComponent(suiteId);
  const [suites, rows, difficultyRows] = await Promise.all([
    getEvalSuites(),
    getSuiteArmComparison(decodedSuiteId),
    getSuiteTaskDifficulty(decodedSuiteId, 25)
  ]);
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
          <div><span>Pass rate</span><strong>{formatPercent(suite.pass_rate)}</strong></div>
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
                <th>Pass rate</th>
                <th>Median runtime</th>
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
                <th>Pass rate</th>
                <th>Median runtime</th>
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
