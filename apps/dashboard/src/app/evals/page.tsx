import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { getEvalRows } from "../../lib/dashboard-data";
import { formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function EvalsPage() {
  const rows = await getEvalRows();
  const observedCounts = rows.reduce(
    (counts, row) => ({
      trialCount: counts.trialCount + row.trial_count,
      successCount: counts.successCount + row.success_count,
    }),
    { trialCount: 0, successCount: 0 },
  );

  return (
    <AppShell
      title="Evals — Valid imported inventory"
      description="Task-level inventory across valid imported run classes; it is not a fixed full-suite leaderboard denominator."
    >
      <CorpusScopeNotice scopeId="valid-imported" observedCounts={observedCounts} />
      <section className="panel">
        <div className="panel-heading">
          <h2>Eval comparison index</h2>
          <p>
            Task rows come from valid imported run classes, which may include full-suite, smoke, canary, diagnostic, legacy, or other valid imports.
            Invalid and quarantined arm runs are excluded. This is not a fixed full-suite leaderboard denominator;
            counts may differ from the Phase 3 extended Overview comparison and the historical Phase 3 core Cross-phase comparison.
          </p>
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
