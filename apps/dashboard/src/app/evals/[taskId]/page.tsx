import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { CorpusScopeNotice } from "../../../components/CorpusScopeNotice";
import { DataFreshnessNotice } from "../../../components/DataFreshnessNotice";
import {
  getAllImportedEvalArmComparison,
  getAllImportedEvalTaskLatestIncludedExecutionAt,
  getEvalArmComparison,
  getValidEvalTaskLatestIncludedExecutionAt,
} from "../../../lib/dashboard-data";
import { buildRegisteredOperationalFreshness, readFreshnessMetadata } from "../../../lib/data-freshness-server";
import { DETAIL_ROUTE_FRESHNESS_SOURCES } from "../../../lib/data-freshness-sources";
import { selectEvalInventoryScope } from "../../../lib/eval-scopes";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

type EvalDetailPageProps = {
  params: Promise<{ taskId: string }>;
  searchParams?: Promise<{ scope?: string | string[] }>;
};

function validityLabel(value: "valid" | "invalid_or_quarantined" | "unlinked"): string {
  if (value === "invalid_or_quarantined") return "Invalid / quarantined";
  if (value === "unlinked") return "Imported / unlinked";
  return "Linked / unflagged";
}

export default async function EvalDetailPage({ params, searchParams }: EvalDetailPageProps) {
  const [{ taskId }, query] = await Promise.all([
    params,
    searchParams ?? Promise.resolve<{ scope?: string | string[] }>({}),
  ]);
  const decodedTaskId = decodeURIComponent(taskId);
  const selection = selectEvalInventoryScope(query.scope);
  const allImported = selection.scopeId === "all-imported";
  const [rows, executionRead] = await Promise.all([
    allImported ? getAllImportedEvalArmComparison(decodedTaskId) : getEvalArmComparison(decodedTaskId),
    readFreshnessMetadata(() => allImported
      ? getAllImportedEvalTaskLatestIncludedExecutionAt(decodedTaskId)
      : getValidEvalTaskLatestIncludedExecutionAt(decodedTaskId)),
  ]);

  if (rows.length === 0) {
    notFound();
  }

  const taskName = rows[0].task_name ?? decodedTaskId;
  const queriedAt = new Date().toISOString();
  const freshness = buildRegisteredOperationalFreshness(
    DETAIL_ROUTE_FRESHNESS_SOURCES.evalTaskDetail[selection.scopeId],
    executionRead,
    queriedAt,
    executionRead.queryStatus === "unavailable"
      ? "Task comparison rows remain visible, but the scope-aligned execution-completion lookup is unavailable."
      : null,
  );

  return (
    <AppShell
      title={taskName}
      description={`Cross-arm comparison for one Terminal-Bench eval/task in the ${allImported ? "all-imported" : "valid-imported"} inventory.`}
    >
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <CorpusScopeNotice scopeId={selection.scopeId} />
      <DataFreshnessNotice freshness={freshness} />
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{decodedTaskId}</h2>
            <p><Link href={`/evals?scope=${selection.scopeId}`}>← Back to evals</Link></p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Suite</th>
                <th>Mode</th>
                {allImported ? <th>Validity</th> : null}
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
                <tr key={`${row.arm_id ?? "unregistered"}-${row.suite_id}-${row.logical_mode}-${row.validity_status}`}>
                  <td className="mono">{row.arm_id ?? "Unregistered arm"}</td>
                  <td className="mono">{row.suite_id ?? "—"}</td>
                  <td>{row.logical_mode ?? "—"}</td>
                  {allImported ? <td>{validityLabel(row.validity_status)}</td> : null}
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
