import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { getEvalSuites } from "../../lib/dashboard-data";
import { formatCurrency, formatNumber, formatPercent } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalSuitesPage() {
  const suites = await getEvalSuites();

  return (
    <AppShell
      title="Eval Suites"
      description="Sponsor-facing Terminal-Bench suite groupings for canary, smoke, and full Phase 3 comparisons."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Suites</h2>
          <p>Each suite groups evals/tasks and compares all imported arms.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Suite</th>
                <th>Type</th>
                <th>Items</th>
                <th>Arms</th>
                <th>Trials</th>
                <th>Pass rate</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {suites.map((row) => (
                <tr key={row.suite_id}>
                  <td>
                    <Link href={`/eval-suites/${encodeURIComponent(row.suite_id)}`}>
                      {row.display_name}
                    </Link>
                    <div className="mono">{row.suite_id}</div>
                  </td>
                  <td>{row.suite_type}</td>
                  <td>{formatNumber(row.suite_items)}</td>
                  <td>{formatNumber(row.arm_run_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
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
