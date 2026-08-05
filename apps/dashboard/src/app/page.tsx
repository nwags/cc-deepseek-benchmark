import Link from "next/link";
import { TermInfo } from "../components/TermInfo";
import { AppShell } from "../components/AppShell";
import { CorpusScopeNotice } from "../components/CorpusScopeNotice";
import { MetricCard } from "../components/MetricCard";
import { SuiteHeatmap } from "../components/SuiteHeatmap";
import { QualityPassRate, QualityBadge, buildSuspectNoopHref } from "../components/QualityContext";
import {
  getValidSuiteArmRunRows,
  getEvalSuites,
  getOverview,
  getSuiteArmComparison,
  getSuiteTaskDifficulty,
  getSuiteHeatmapCells,
  getSuiteArmQualityRows,
  getArmRunQualityByRunLabels,
  getInvalidArmRunRows
} from "../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../lib/format";

export const dynamic = "force-dynamic";

function runHealthLabel(status: string, trialCount: number, logicalMode: string) {
  if (status === "completed") return "completed";
  if (status === "errors" && trialCount > 0) {
    return logicalMode === "full" ? "imported with trial errors" : "trial errors";
  }
  return status;
}

export default async function DashboardPage() {
  const [overview, suites, fullArmRuns, fullSuiteRows, hardestFullEvals, heatmapCells, fullSuiteQualityRows, invalidRows] = await Promise.all([
    getOverview(),
    getEvalSuites(),
    getValidSuiteArmRunRows("phase3-full-20", 20),
    getSuiteArmComparison("phase3-full-20"),
    getSuiteTaskDifficulty("phase3-full-20", 8),
    getSuiteHeatmapCells("phase3-full-20"),
    getSuiteArmQualityRows("phase3-full-20"),
    getInvalidArmRunRows()
  ]);

  const fullSuite = suites.find((suite) => suite.suite_id === "phase3-full-20");
  const invalidFullSuiteCount = invalidRows.filter((row) => row.suite_id === "phase3-full-20").length;
  const fullQualityByArm = new Map(fullSuiteQualityRows.map((row) => [row.arm_id, row]));
  const fullRunQualityRows = await getArmRunQualityByRunLabels(fullArmRuns.map((row) => row.run_label));
  const fullQualityByRun = new Map(fullRunQualityRows.map((row) => [row.run_label, row]));

  return (
    <AppShell title="Coding Agent Benchmark Dashboard">
      <h2>Phase 3 extended full-suite comparison</h2>
      <CorpusScopeNotice
        scopeId="phase3-extended"
        observedCounts={{
          armCount: fullSuite?.arm_run_count ?? 0,
          trialCount: fullSuite?.trial_count ?? 0,
          successCount: fullSuite?.success_count ?? 0,
        }}
      />
      <section className="metric-grid">
        <MetricCard label="Full-suite arms" value={formatNumber(fullSuite?.arm_run_count ?? 0)} detail="Imported into phase3-full-20" />
        <MetricCard label="Full-suite trials" value={formatNumber(fullSuite?.trial_count ?? 0)} detail="20 evals × 3 attempts × imported arms" />
        <MetricCard label="Full-suite pass rate" value={formatPercent(fullSuite?.pass_rate ?? null)} detail="Across imported full arms" />
      </section>

      <section className="quality-context-panel">
        <strong>Data provenance and validity:</strong> Primary comparison uses valid-only views.
        Invalid/quarantined runs are preserved in the audit layer.
        Current invalid/quarantined full-suite runs: {formatNumber(invalidFullSuiteCount)}.{" "}
        <Link href="/trial-quality">Open trial quality audit</Link>.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Full-suite leaderboard</h2>
            <p>
              Current imported full-sweep arms in{" "}
              <Link href="/eval-suites/phase3-full-20">phase3-full-20</Link>.
              Costs are recorded costs; rows with missing cost coverage should be treated as lower bounds.
            </p>
          </div>
          <Link href="/eval-suites/phase3-full-20">Open suite →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Arm</th>
                <th>Tasks</th>
                <th>Trials</th>
                <th>Successes</th>
                <th><span className="term-label">Pass rate <TermInfo term="Pass rate" /></span></th>
                <th>Suspect no-op</th>
                <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
                <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
              </tr>
            </thead>
            <tbody>
              {fullSuiteRows.map((row, index) => {
                const quality = fullQualityByArm.get(row.arm_id);
                const suspectNoopCount = quality?.suspect_noop_count ?? 0;
                return (
                  <tr key={row.arm_id}>
                    <td>{index + 1}</td>
                    <td className="mono">{row.arm_id}</td>
                    <td>{formatNumber(row.task_count)}</td>
                    <td>{formatNumber(row.trial_count)}</td>
                    <td>{formatNumber(row.success_count)}</td>
                    <td><QualityPassRate row={quality ?? {
                      raw_pass_rate: row.pass_rate,
                      trial_count: row.trial_count,
                      success_count: row.success_count,
                      qualified_pass_rate: row.pass_rate,
                      qualified_trial_count: row.trial_count,
                      qualified_success_count: row.success_count,
                      suspect_noop_count: 0
                    }} /></td>
                    <td>
                      {suspectNoopCount > 0 ? (
                        <Link href={buildSuspectNoopHref({ suite_id: "phase3-full-20", arm_id: row.arm_id })}>
                          <QualityBadge count={suspectNoopCount} />
                        </Link>
                      ) : (
                        <QualityBadge count={suspectNoopCount} />
                      )}
                    </td>
                    <td>{formatSeconds(row.median_runtime_seconds)}</td>
                    <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <SuiteHeatmap
        rows={heatmapCells}
        title="Full-suite pass/fail heatmap"
        description="Rows are evals, columns are imported full-suite arms. Heatmap cells show successes/trials. Suspect no-op detail is available through Trial Quality drilldowns."
      />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Hardest full-suite evals</h2>
            <p>Tasks where the imported full-sweep arms struggle most. These are the best starting points for trajectory review.</p>
          </div>
          <Link href="/evals">All evals →</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Eval</th>
                <th>Arms</th>
                <th>Trials</th>
                <th>Successes</th>
                <th><span className="term-label">Pass rate <TermInfo term="Pass rate" /></span></th>
                <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
              </tr>
            </thead>
            <tbody>
              {hardestFullEvals.map((row) => (
                <tr key={row.task_id}>
                  <td>
                    <Link href={`/evals/${encodeURIComponent(row.task_id)}`}>{row.task_name ?? row.task_id}</Link>
                    <div className="mono">{row.task_id}</div>
                  </td>
                  <td>{formatNumber(row.arm_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Full arm-run health</h2>
            <p>These are complete imported arm executions. “Trial errors” means failures occurred inside the 60 attempts, not that ingestion failed.</p>
          </div>
          <Link href="/arm-runs">All arm runs →</Link>
        </div>
        <div className="run-list">
          {fullArmRuns.map((row) => (
            <article className="run-card" key={row.arm_run_id}>
              <div>
                <h3>
                  <Link href={`/arm-runs/${row.arm_run_id}`}>{row.arm_id}</Link>
                </h3>
                <p>{row.logical_mode} / {row.storage_mode ?? "—"} · {row.suite_id ?? "no suite"} · {runHealthLabel(row.status, row.trial_count, row.logical_mode)}</p>
                <p className="mono">{row.run_label}</p>
              </div>
              <dl>
                <div><dt>Trials</dt><dd>{formatNumber(row.trial_count)}</dd></div>
                <div><dt>Raw / qualified pass</dt><dd><QualityPassRate compact row={fullQualityByRun.get(row.run_label) ?? {
                  raw_pass_rate: row.pass_rate,
                  trial_count: row.trial_count,
                  success_count: row.success_count,
                  qualified_pass_rate: row.pass_rate,
                  qualified_trial_count: row.trial_count,
                  qualified_success_count: row.success_count,
                  suspect_noop_count: 0
                }} /></dd></div>
                <div>
                  <dt>Suspect no-op</dt>
                  <dd>
                    {(fullQualityByRun.get(row.run_label)?.suspect_noop_count ?? 0) > 0 ? (
                      <Link href={buildSuspectNoopHref({ run_label: row.run_label })}>
                        <QualityBadge count={fullQualityByRun.get(row.run_label)?.suspect_noop_count ?? 0} />
                      </Link>
                    ) : (
                      <QualityBadge count={fullQualityByRun.get(row.run_label)?.suspect_noop_count ?? 0} />
                    )}
                  </dd>
                </div>
                <div><dt><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></dt><dd>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</dd></div>
                <div><dt>R2 artifacts</dt><dd>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <h2>Valid imported evidence inventory</h2>
      <CorpusScopeNotice
        scopeId="valid-imported"
        observedCounts={{ trialCount: overview.trial_count }}
      />
      <section className="metric-grid">
        <MetricCard label="Valid imported trials" value={formatNumber(overview.trial_count)} detail="Canary + smoke + full valid arm runs" />
        <MetricCard label="Valid-run R2 artifacts" value={formatNumber(overview.artifact_count)} detail="Tracked evidence rows" />
        <MetricCard label="Recorded cost" value={formatRecordedCost(overview.cost_usd, overview.cost_row_count, overview.missing_cost_count)} detail="Known cost rows only; not the reviewed adjusted-cost total" />
      </section>
    </AppShell>
  );
}
