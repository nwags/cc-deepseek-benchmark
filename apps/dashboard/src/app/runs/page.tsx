import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { getRecentRuns } from "../../lib/dashboard-data";
import { formatRecordedCost, formatCurrency, formatNumber, formatPercent } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await getRecentRuns();

  return (
    <AppShell
      title="Runs"
      description="Imported Phase 3 run roots, current status, cost, pass rate, and artifact coverage."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Recent imported runs</h2>
          <p>Latest run roots from Supabase metadata views.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Trials</th>
                <th>Pass rate</th>
                <th>Cost</th>
                <th>R2 artifacts</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((row) => (
                <tr key={row.run_label}>
                  <td className="mono">
                    <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>
                      {row.run_label}
                    </Link>
                  </td>
                  <td>{row.mode}</td>
                  <td><span className={`status status-${row.status}`}>{row.status}</span></td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                  <td>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
