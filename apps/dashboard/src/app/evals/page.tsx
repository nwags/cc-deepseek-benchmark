import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { getEvalRows } from "../../lib/dashboard-data";
import { formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalsPage() {
  const rows = await getEvalRows();

  return (
    <AppShell
      title="Evals"
      description="Task-level comparison entry point. Drill into one eval to compare all imported arms."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Eval comparison index</h2>
          <p>Terminal-Bench tasks with imported benchmark trial rows.</p>
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
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.task_id}>
                  <td>
                    <Link href={`/evals/${encodeURIComponent(row.task_id)}`}>
                      {row.task_name ?? row.task_id}
                    </Link>
                    <div className="mono">{row.task_id}</div>
                  </td>
                  <td>{formatNumber(row.arm_count)}</td>
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
