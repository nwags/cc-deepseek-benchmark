import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { getEvalArmComparison } from "../../../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalDetailPage({
  params
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;
  const decodedTaskId = decodeURIComponent(taskId);
  const rows = await getEvalArmComparison(decodedTaskId);

  if (rows.length === 0) {
    notFound();
  }

  const taskName = rows[0].task_name ?? decodedTaskId;

  return (
    <AppShell
      title={taskName}
      description="Cross-arm comparison for one Terminal-Bench eval/task."
    >
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{decodedTaskId}</h2>
            <p><Link href="/evals">← Back to evals</Link></p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Suite</th>
                <th>Mode</th>
                <th>Trials</th>
                <th>Successes</th>
                <th>Pass rate</th>
                <th>Mean reward</th>
                <th>Median runtime</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.arm_id}-${row.suite_id}-${row.logical_mode}`}>
                  <td className="mono">{row.arm_id}</td>
                  <td className="mono">{row.suite_id ?? "—"}</td>
                  <td>{row.logical_mode ?? "—"}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{row.mean_reward === null ? "—" : Number(row.mean_reward).toFixed(3)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                  <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
