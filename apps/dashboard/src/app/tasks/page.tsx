import { AppShell } from "../../components/AppShell";
import { getTaskRows } from "../../lib/dashboard-data";
import { formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await getTaskRows();

  return (
    <AppShell title="Tasks" description="Task-level summary for imported canary and smoke trials.">
      <section className="panel">
        <div className="panel-heading">
          <h2>Task summary</h2>
          <p>Pass rate and runtime by Terminal-Bench task.</p>
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
                  <td>{formatCurrency(row.trial_cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
