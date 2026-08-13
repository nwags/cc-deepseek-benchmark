import { AppShell } from "../../components/AppShell";
import { DataFreshnessNotice } from "../../components/DataFreshnessNotice";
import { getAllImportedTaskLatestIncludedExecutionAt, getTaskRows } from "../../lib/dashboard-data";
import { INDEX_ROUTE_FRESHNESS_SOURCES } from "../../lib/data-freshness-sources";
import { buildRegisteredOperationalFreshness, readFreshnessMetadata } from "../../lib/data-freshness-server";
import { formatRecordedCost, formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const [tasks, freshnessRead] = await Promise.all([
    getTaskRows(),
    readFreshnessMetadata(() => getAllImportedTaskLatestIncludedExecutionAt()),
  ]);
  const freshness = buildRegisteredOperationalFreshness(
    INDEX_ROUTE_FRESHNESS_SOURCES.tasks,
    freshnessRead,
    new Date().toISOString(),
  );

  return (
    <AppShell title="Tasks — All imported" description="Task-level summary across all imported run classes with registered task rows.">
      <DataFreshnessNotice freshness={freshness} />
      <section className="panel">
        <div className="panel-heading">
          <h2>Task summary</h2>
          <p>All-imported pass rate, runtime, and recorded cost by Terminal-Bench task; full-suite, smoke, canary, diagnostic, legacy, and other imported run classes may contribute.</p>
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
