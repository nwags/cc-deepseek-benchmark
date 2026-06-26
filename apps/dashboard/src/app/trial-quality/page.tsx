import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { TermInfo } from "../../components/TermInfo";
import {
  getArmRunQualitySummaryRows,
  getSuspectNoopTrialRows
} from "../../lib/dashboard-data";

export const dynamic = "force-dynamic";

function pct(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function money(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return `$${Number(value).toFixed(2)}`;
}

function modeLabel(logicalMode: string | null, storageMode: string | null) {
  if (!logicalMode && !storageMode) return "—";
  if (logicalMode === storageMode || !storageMode) return logicalMode ?? storageMode;
  return `${logicalMode} / ${storageMode}`;
}

export default async function TrialQualityPage() {
  const [summaries, suspectTrials] = await Promise.all([
    getArmRunQualitySummaryRows(120),
    getSuspectNoopTrialRows(120)
  ]);

  const totalSuspect = summaries.reduce((acc, row) => acc + Number(row.suspect_noop_count ?? 0), 0);
  const affectedRuns = summaries.filter((row) => Number(row.suspect_noop_count ?? 0) > 0).length;
  const affectedFullRuns = summaries.filter(
    (row) => row.logical_mode === "full" && Number(row.suspect_noop_count ?? 0) > 0
  ).length;

  return (
    <AppShell
      eyebrow="Phase 3 interpretation layer"
      title="Trial quality"
      description="Raw benchmark outcomes remain the source of truth. This page adds diagnostic flags so no-op exits, exceptions, and normal failures are not interpreted as the same kind of model behavior."
    >

      <section className="panel warning-panel">
        <h2>Interpretation policy</h2>
        <p>
          Canary and smoke suites are diagnostic route/provider tests. They are useful for
          readiness and anomaly detection, but they should not be read as definitive model-quality
          comparisons. Full sweeps are the sponsor-facing comparison layer, but they still need
          anomaly flags when suspicious trial behavior appears.
        </p>
        <div className="concept-grid">
          <article>
            <h3>Raw pass rate <TermInfo term="Pass rate" /></h3>
            <p>Successes divided by all imported trials. This remains the auditable benchmark outcome.</p>
          </article>
          <article>
            <h3>Qualified pass rate</h3>
            <p>Successes divided by trials after excluding suspect no-op zero-token exits.</p>
          </article>
          <article>
            <h3>Suspect no-op exit</h3>
            <p>A failed trial with no exception, no recorded tokens, no recorded cost, and an empty completed agent result or DB-equivalent zero-token signature.</p>
          </article>
        </div>
      </section>

      <section className="metric-grid metric-grid-compact">
        <article className="metric-card">
          <span className="metric-label">Suspect no-op trials</span>
          <strong>{totalSuspect}</strong>
          <span className="metric-subtitle">Phase 3 imported rows</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Affected arm runs</span>
          <strong>{affectedRuns}</strong>
          <span className="metric-subtitle">Any mode</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Affected full runs</span>
          <strong>{affectedFullRuns}</strong>
          <span className="metric-subtitle">Should be zero or investigated</span>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Arm-run quality summary</h2>
            <p>Shows raw and qualified pass rates side by side. Qualified rate only removes suspect no-op zero-token exits.</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mode</th>
                <th>Arm run</th>
                <th>Raw pass</th>
                <th>Qualified pass</th>
                <th>Suspect no-op</th>
                <th>Exceptions</th>
                <th>Normal failures</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((row) => (
                <tr key={row.run_label}>
                  <td>{modeLabel(row.logical_mode, row.storage_mode)}</td>
                  <td>
                    <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                    {row.suite_id ? <div className="muted">{row.suite_id}</div> : null}
                  </td>
                  <td>{row.success_count}/{row.trial_count} · {pct(row.raw_pass_rate)}</td>
                  <td>
                    {row.qualified_success_count}/{row.qualified_trial_count} · {pct(row.qualified_pass_rate)}
                  </td>
                  <td>
                    <span className={row.suspect_noop_count > 0 ? "quality-badge quality-badge-warn" : "quality-badge"}>
                      {row.suspect_noop_count}
                    </span>
                  </td>
                  <td>{row.exception_count}</td>
                  <td>{row.normal_failed_count}</td>
                  <td>
                    {money(row.recorded_cost_usd)}
                    {row.missing_cost_count > 0 ? <div className="muted">{row.missing_cost_count} missing</div> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Suspect no-op zero-token trials</h2>
            <p>These should be interpreted as route, provider, or harness anomalies until reviewed.</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Mode</th>
                <th>Arm run</th>
                <th>Task</th>
                <th>Runtime</th>
                <th>Tokens</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {suspectTrials.length === 0 ? (
                <tr>
                  <td colSpan={6}>No suspect no-op zero-token trials found.</td>
                </tr>
              ) : (
                suspectTrials.map((row) => (
                  <tr key={`${row.run_label}-${row.task_id}`}>
                    <td>{modeLabel(row.logical_mode, row.storage_mode)}</td>
                    <td>
                      <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                      {row.suite_id ? <div className="muted">{row.suite_id}</div> : null}
                    </td>
                    <td>{row.task_id}</td>
                    <td>{row.runtime_seconds ? `${Number(row.runtime_seconds).toFixed(1)}s` : "—"}</td>
                    <td>{Number(row.input_tokens ?? 0).toLocaleString()} in / {Number(row.output_tokens ?? 0).toLocaleString()} out</td>
                    <td>{money(row.cost_usd)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
