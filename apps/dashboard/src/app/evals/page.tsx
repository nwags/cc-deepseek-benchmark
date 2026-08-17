import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { CorpusScopeNotice } from "../../components/CorpusScopeNotice";
import { DataFreshnessNotice } from "../../components/DataFreshnessNotice";
import { EvalScopeSelector } from "../../components/EvalScopeSelector";
import {
  getAllImportedEvalRows,
  getAllImportedTaskLatestIncludedExecutionAt,
  getEvalRows,
  getValidImportedEvalLatestIncludedExecutionAt,
} from "../../lib/dashboard-data";
import { INDEX_ROUTE_FRESHNESS_SOURCES } from "../../lib/data-freshness-sources";
import { buildRegisteredOperationalFreshness, readFreshnessMetadata } from "../../lib/data-freshness-server";
import { selectEvalInventoryScope } from "../../lib/eval-scopes";
import { formatNumber, formatPercent, formatRecordedCost, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

type EvalsPageProps = {
  searchParams?: Promise<{ scope?: string | string[] }>;
};

export default async function EvalsPage({ searchParams }: EvalsPageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = selectEvalInventoryScope(params.scope);
  const allImported = selection.scopeId === "all-imported";
  const [rows, freshnessRead] = await Promise.all([
    allImported ? getAllImportedEvalRows() : getEvalRows(),
    readFreshnessMetadata(() => allImported
      ? getAllImportedTaskLatestIncludedExecutionAt()
      : getValidImportedEvalLatestIncludedExecutionAt()),
  ]);
  const freshness = buildRegisteredOperationalFreshness(
    INDEX_ROUTE_FRESHNESS_SOURCES.evals[selection.scopeId],
    freshnessRead,
    new Date().toISOString(),
  );
  const observedCounts = rows.reduce(
    (counts, row) => ({
      trialCount: counts.trialCount + row.trial_count,
      successCount: counts.successCount + row.success_count,
    }),
    { trialCount: 0, successCount: 0 },
  );
  const scopeLabel = allImported ? "All imported" : "Valid imported";

  return (
    <AppShell
      title={`Evals — ${scopeLabel} inventory`}
      description={allImported
        ? "Task-level inventory across all imported trial-bearing runs, including evidence outside the valid-only comparison population."
        : "Task-level inventory across valid imported run classes; it is not a fixed full-suite leaderboard denominator."}
    >
      <EvalScopeSelector selectedScopeId={selection.scopeId} />
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Scope selection warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <CorpusScopeNotice scopeId={selection.scopeId} observedCounts={observedCounts} />
      <DataFreshnessNotice freshness={freshness} />
      <section className="panel">
        <div className="panel-heading">
          <h2>Eval comparison index</h2>
          {allImported ? (
            <p>
              Rows retain the broader all-imported task evidence formerly shown on Tasks. Full-suite, smoke, canary, diagnostic,
              legacy, invalid/quarantined, and other imported evidence may contribute. This inventory is not a fixed full-suite
              leaderboard denominator; counts can exceed Valid imported because no validity exclusion is applied.
            </p>
          ) : (
            <p>
              Task rows come from valid imported run classes, which may include full-suite, smoke, canary, diagnostic, legacy, or other valid imports.
              Invalid and quarantined arm runs are excluded. This is not a fixed full-suite leaderboard denominator;
              counts may differ from All imported and from the reviewed fixed Phase 3 comparisons.
            </p>
          )}
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
                    <Link href={`/evals/${encodeURIComponent(row.task_id)}?scope=${selection.scopeId}`}>
                      {row.task_name ?? row.task_id}
                    </Link>
                    <div className="mono">{row.task_id}</div>
                  </td>
                  <td>{formatNumber(row.arm_count)}</td>
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
