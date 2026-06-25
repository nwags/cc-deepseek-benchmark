import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { MetricCard } from "../../../components/MetricCard";
import { getArmRunArtifacts, getArmRunDetail, getArmRunTrials } from "../../../lib/dashboard-data";
import { formatBytes, formatCurrency, formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

function compactArtifactPath(value: string): string {
  const parts = value.split("/");
  return parts.length <= 7 ? value : `…/${parts.slice(-5).join("/")}`;
}

export default async function ArmRunDetailPage({
  params
}: {
  params: Promise<{ armRunId: string }>;
}) {
  const { armRunId } = await params;
  const [run, trials, artifacts] = await Promise.all([
    getArmRunDetail(armRunId),
    getArmRunTrials(armRunId),
    getArmRunArtifacts(armRunId)
  ]);

  if (!run) {
    notFound();
  }

  return (
    <AppShell
      title="Arm run detail"
      description="Task attempts and artifacts for one model arm execution."
    >
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{run.arm_id}</h2>
            <p>
              <Link href="/arm-runs">← Back to arm runs</Link>
            </p>
          </div>
          <span className={`status status-${run.status}`}>{run.status}</span>
        </div>
        <div className="metric-grid">
          <MetricCard label="Trials" value={formatNumber(run.trial_count)} />
          <MetricCard label="Pass rate" value={formatPercent(run.pass_rate)} />
          <MetricCard label="Cost" value={formatRecordedCost(run.trial_cost_usd, run.cost_row_count, run.missing_cost_count)} />
          <MetricCard label="Median runtime" value={formatSeconds(run.median_runtime_seconds)} />
          <MetricCard label="R2 artifacts" value={`${formatNumber(run.r2_artifact_count)} / ${formatNumber(run.artifact_count)}`} />
          <MetricCard label="Suite" value={run.suite_id ?? "—"} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Run metadata</h2>
          <p>Logical mode separates sponsor-facing run type from physical result storage path.</p>
        </div>
        <div className="detail-grid">
          <div><span>Run label</span><strong className="mono">{run.run_label}</strong></div>
          <div><span>Logical mode</span><strong>{run.logical_mode}</strong></div>
          <div><span>Storage mode</span><strong>{run.storage_mode ?? "—"}</strong></div>
          <div><span>Suite</span><strong className="mono">{run.suite_id ?? "—"}</strong></div>
          <div><span>Started</span><strong>{run.started_at ?? "—"}</strong></div>
          <div><span>Finished</span><strong>{run.finished_at ?? "—"}</strong></div>
          <div><span>Input tokens</span><strong>{formatNumber(run.input_tokens)}</strong></div>
          <div><span>Cache tokens</span><strong>{formatNumber(run.cache_tokens)}</strong></div>
          <div><span>Output tokens</span><strong>{formatNumber(run.output_tokens)}</strong></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Task attempts</h2>
          <p>Trial rows for this arm run.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Attempt</th>
                <th>Reward</th>
                <th>Exception</th>
                <th>Runtime</th>
                <th>Cost</th>
                <th>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {trials.map((trial) => (
                <tr key={trial.trial_id}>
                  <td className="mono">{trial.task_name ?? trial.task_id}</td>
                  <td>{trial.attempt_index ?? "—"}</td>
                  <td>{trial.reward ?? "—"}</td>
                  <td>{trial.exception_type ?? "—"}</td>
                  <td>{formatSeconds(trial.runtime_seconds)}</td>
                  <td>{formatCurrency(trial.cost_usd)}</td>
                  <td>{formatNumber(trial.input_tokens ?? 0)} in / {formatNumber(trial.output_tokens ?? 0)} out</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Artifacts</h2>
          <p>Artifact metadata linked to this arm run.</p>
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
