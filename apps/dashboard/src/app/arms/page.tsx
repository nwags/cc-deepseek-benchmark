import { AppShell } from "../../components/AppShell";
import { getArmRows } from "../../lib/dashboard-data";
import { formatRecordedCost, formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function ArmsPage() {
  const arms = await getArmRows();

  return (
    <AppShell title="Arms" description="Model/backend arm comparison across imported benchmark runs.">
      <section className="panel">
        <div className="panel-heading">
          <h2>Arm comparison</h2>
          <p>Run count, trial count, pass rate, runtime, and cost.</p>
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
    </AppShell>
  );
}
