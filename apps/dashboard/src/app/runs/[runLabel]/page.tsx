import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { MetricCard } from "../../../components/MetricCard";
import { QualityBadge, QualityPassRate, buildSuspectNoopHref } from "../../../components/QualityContext";
import { InvalidReason, ValidityBadge, invalidCategory, validityLabel } from "../../../components/ValidityContext";
import { buildArtifactHref } from "../../../lib/links";
import {
  getArmRunQualityByRunLabels,
  getInvalidArmRunRowsByRunLabels,
  getRunArtifacts,
  getRunDetail,
  getRunTrials
} from "../../../lib/dashboard-data";
import {
  formatBytes,
  formatRecordedCost, formatCurrency,
  formatNumber,
  formatPercent,
  formatSeconds
} from "../../../lib/format";

export const dynamic = "force-dynamic";

function compactArtifactPath(value: string): string {
  const parts = value.split("/");
  if (parts.length <= 7) {
    return value;
  }

  return `…/${parts.slice(-5).join("/")}`;
}

export default async function RunDetailPage({
  params
}: {
  params: Promise<{ runLabel: string }>;
}) {
  const { runLabel } = await params;
  const decodedRunLabel = decodeURIComponent(runLabel);
  const run = await getRunDetail(decodedRunLabel);

  if (!run) {
    notFound();
  }

  const [trials, artifacts, qualityRows, invalidRows] = await Promise.all([
    getRunTrials(run.run_id),
    getRunArtifacts(run.run_id),
    getArmRunQualityByRunLabels([run.run_label]),
    getInvalidArmRunRowsByRunLabels([run.run_label])
  ]);
  const quality = qualityRows[0] ?? null;
  const invalidRow = invalidRows[0] ?? null;
  const suspectNoopCount = quality?.suspect_noop_count ?? 0;

  return (
    <AppShell title="Run detail">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{run.run_label}</h2>
            <p>
              <Link href="/runs">← Back to runs</Link>
            </p>
          </div>
          <span className={`status status-${run.status}`}>{run.status}</span>
        </div>

        <div className="metric-grid">
          <MetricCard label="Trials" value={formatNumber(run.trial_count)} />
          <MetricCard label="Raw pass rate" value={formatPercent(run.pass_rate)} />
          <MetricCard label="Qualified pass rate" value={formatPercent(quality?.qualified_pass_rate ?? run.pass_rate)} />
          <MetricCard
            label="Suspect no-op"
            value={suspectNoopCount > 0 ? (
              <Link href={buildSuspectNoopHref({ run_label: run.run_label })}>
                <QualityBadge count={suspectNoopCount} />
              </Link>
            ) : (
              <QualityBadge count={suspectNoopCount} />
            )}
          />
          <MetricCard label="Cost" value={formatRecordedCost(run.trial_cost_usd, run.cost_row_count, run.missing_cost_count)} />
          <MetricCard label="Median runtime" value={formatSeconds(run.median_runtime_seconds)} />
          <MetricCard label="Artifacts in R2" value={`${formatNumber(run.r2_artifact_count)} / ${formatNumber(run.artifact_count)}`} />
          <MetricCard label="Audit events" value={formatNumber(run.audit_count)} />
        </div>
        <div className="placeholder-body">
          Suspect no-op drilldown opens the affected zero-token trials in Trial Quality.
        </div>
      </section>

      {invalidRow ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Invalid / quarantined run</h2>
              <p>This run is retained for audit but excluded from valid-only scored comparisons.</p>
            </div>
            <ValidityBadge row={invalidRow} />
          </div>
          <div className="detail-grid">
            <div><span>Validity</span><strong>{validityLabel(invalidRow)}</strong></div>
            <div><span>Category</span><strong>{invalidCategory(invalidRow) ?? "—"}</strong></div>
            <div><span>Provider/workflow id</span><strong className="mono">{invalidRow.provider_run_id ?? "—"}</strong></div>
            <div><span>Reason</span><strong><InvalidReason row={invalidRow} includeProvider={false} /></strong></div>
            <div><span>Invalidated by</span><strong>{invalidRow.invalidated_by ?? "—"}</strong></div>
            <div><span>Invalidated at</span><strong>{invalidRow.invalidated_at ?? "—"}</strong></div>
          </div>
        </section>
      ) : (
        <section className="quality-context-panel">
          <strong>Validity:</strong> <ValidityBadge row={invalidRow} />
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <h2>Run metadata</h2>
          <p>Branch, commit, runner, timing, tokens, and contamination counters.</p>
        </div>

        <div className="detail-grid">
          <div><span>Phase</span><strong>{run.phase}</strong></div>
          <div><span>Arm</span><strong className="mono">{quality?.arm_id ?? "—"}</strong></div>
          <div><span>Logical mode</span><strong>{quality?.logical_mode ?? run.mode}</strong></div>
          <div><span>Storage mode</span><strong>{quality?.storage_mode ?? run.mode}</strong></div>
          <div><span>Suite</span><strong className="mono">{quality?.suite_id ?? "—"}</strong></div>
          <div><span>Branch</span><strong>{run.branch ?? "—"}</strong></div>
          <div><span>Git commit</span><strong className="mono">{run.git_commit ?? "—"}</strong></div>
          <div><span>Runner</span><strong>{run.runner_name ?? "—"}</strong></div>
          <div><span>Runner provider</span><strong>{run.runner_provider ?? "—"}</strong></div>
          <div><span>Started</span><strong>{run.started_at ?? "—"}</strong></div>
          <div><span>Finished</span><strong>{run.finished_at ?? "—"}</strong></div>
          <div><span>Input tokens</span><strong>{formatNumber(run.input_tokens)}</strong></div>
          <div><span>Cache tokens</span><strong>{formatNumber(run.cache_tokens)}</strong></div>
          <div><span>Output tokens</span><strong>{formatNumber(run.output_tokens)}</strong></div>
          <div><span>Qualified pass</span><strong><QualityPassRate row={quality ?? {
            raw_pass_rate: run.pass_rate,
            trial_count: run.trial_count,
            success_count: Math.round((run.pass_rate ?? 0) * (run.trial_count ?? 0)),
            qualified_pass_rate: run.pass_rate,
            qualified_trial_count: run.trial_count,
            qualified_success_count: Math.round((run.pass_rate ?? 0) * (run.trial_count ?? 0)),
            suspect_noop_count: 0
          }} /></strong></div>
          <div>
            <span>Suspect no-op</span>
            <strong>
              {suspectNoopCount > 0 ? (
                <Link href={buildSuspectNoopHref({ run_label: run.run_label })}>
                  <QualityBadge count={suspectNoopCount} />
                </Link>
              ) : (
                <QualityBadge count={suspectNoopCount} />
              )}
            </strong>
          </div>
          <div><span>Artifact bytes</span><strong>{formatBytes(run.artifact_size_bytes)}</strong></div>
          <div><span>WebSearch events</span><strong>{formatNumber(run.websearch_events)}</strong></div>
          <div><span>WebFetch events</span><strong>{formatNumber(run.webfetch_events)}</strong></div>
          <div><span>Forbidden tools available</span><strong>{formatNumber(run.forbidden_tools_available)}</strong></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Trials</h2>
          <p>Task-level trial rows imported for this run.</p>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Arm</th>
                <th>Reward</th>
                <th>Runtime</th>
                <th>Cost</th>
                <th>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {trials.map((trial) => (
                <tr key={`${trial.task_id}-${trial.arm_id}`}>
                  <td className="mono">{trial.task_id}</td>
                  <td className="mono">{trial.arm_id}</td>
                  <td>{trial.reward ?? "—"}</td>
                  <td>{formatSeconds(trial.runtime_seconds)}</td>
                  <td>{formatCurrency(trial.cost_usd)}</td>
                  <td>
                    {formatNumber(trial.input_tokens ?? 0)} in / {formatNumber(trial.output_tokens ?? 0)} out
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
            <h2>Artifacts</h2>
            <p>First 100 artifact records. Signed download links will come in a later pass.</p>
          </div>
          <div className="artifact-link-list">
            <Link href={buildArtifactHref({ run_label: run.run_label })}>Open in artifact browser</Link>
            {suspectNoopCount > 0 ? (
              <Link href={buildArtifactHref({ run_label: run.run_label, quality_flag: "suspect_noop_zero_token" })}>
                Suspect no-op artifacts
              </Link>
            ) : null}
          </div>
        </div>

        <div className="artifact-list">
          {artifacts.map((artifact) => (
            <article className="artifact-card" key={artifact.artifact_path}>
              <div className="artifact-path mono" title={artifact.artifact_path}>
                {compactArtifactPath(artifact.artifact_path)}
              </div>
              <div className="artifact-meta">
                <span>{artifact.artifact_kind ?? "unknown"}</span>
                <span>{formatBytes(artifact.size_bytes)}</span>
                <span>{artifact.r2_uri ? "R2 indexed" : "local only"}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
