import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { ArtifactTypeLabel } from "../../../components/ArtifactTypeInfo";
import { InvalidReason, ValidityBadge } from "../../../components/ValidityContext";
import { buildSuspectNoopHref } from "../../../components/QualityContext";
import {
  InvalidArmRunRow,
  TrialEvidenceRow,
  getArtifactsForTrial,
  getTrialEvidence
} from "../../../lib/dashboard-data";
import { getTaskInstructionPreview } from "../../../lib/artifact-content";
import { buildArtifactHref } from "../../../lib/links";
import { formatBytes, formatCurrency, formatNumber, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

function compactPath(value: string | null | undefined) {
  if (!value) return "—";
  const parts = value.split("/");
  if (parts.length <= 7) return value;
  return `…/${parts.slice(-5).join("/")}`;
}

function invalidRowFromTrial(row: TrialEvidenceRow): InvalidArmRunRow | null {
  if (!row.invalid_reason || !row.suite_id || !row.arm_id) return null;
  return {
    suite_id: row.suite_id,
    arm_id: row.arm_id,
    run_label: row.run_label,
    provider_run_id: row.invalid_provider_run_id,
    reason: row.invalid_reason,
    invalidated_at: row.invalidated_at,
    invalidated_by: row.invalidated_by,
    raw_metadata: row.invalid_raw_metadata
  };
}

function trialQualityHref(row: TrialEvidenceRow) {
  if (row.quality_flag === "suspect_noop_zero_token") {
    return buildSuspectNoopHref({
      suite_id: row.suite_id,
      arm_id: row.arm_id,
      run_label: row.run_label,
      task_id: row.task_id
    });
  }

  return "/trial-quality";
}

export default async function TrialEvidencePage({
  params
}: {
  params: Promise<{ trialId: string }>;
}) {
  const { trialId } = await params;
  const decodedTrialId = decodeURIComponent(trialId);
  const trial = await getTrialEvidence(decodedTrialId);

  if (!trial) {
    notFound();
  }

  const [artifacts, taskInstruction] = await Promise.all([
    getArtifactsForTrial(decodedTrialId),
    getTaskInstructionPreview(trial.task_id)
  ]);
  const invalidRow = invalidRowFromTrial(trial);

  return (
    <AppShell
      title="Trial evidence"
      description="Task attempt evidence, quality status, and related artifacts for one imported benchmark trial."
    >
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{trial.trial_id}</h2>
            <p><Link href={buildArtifactHref({ run_label: trial.run_label, task_id: trial.task_id })}>Back to artifacts</Link></p>
          </div>
          <ValidityBadge row={invalidRow} />
        </div>

        <div className="detail-grid">
          <div><span>Run</span><strong><Link href={`/runs/${encodeURIComponent(trial.run_label)}`}>{trial.run_label}</Link></strong></div>
          <div><span>Suite</span><strong className="mono">{trial.suite_id ?? "—"}</strong></div>
          <div><span>Arm</span><strong className="mono">{trial.arm_id ?? "—"}</strong></div>
          <div><span>Task</span><strong className="mono">{trial.task_id ?? "—"}</strong></div>
          <div><span>Attempt</span><strong>{trial.attempt_index ?? "—"}</strong></div>
          <div><span>Quality</span><strong>{trial.quality_flag ?? "—"}</strong></div>
          <div><span>Reward</span><strong>{trial.reward ?? "—"}</strong></div>
          <div><span>Runtime</span><strong>{formatSeconds(trial.runtime_seconds)}</strong></div>
          <div><span>Cost</span><strong>{formatCurrency(trial.cost_usd)}</strong></div>
          <div><span>Input tokens</span><strong>{formatNumber(trial.input_tokens ?? 0)}</strong></div>
          <div><span>Cache tokens</span><strong>{formatNumber(trial.cache_tokens ?? 0)}</strong></div>
          <div><span>Output tokens</span><strong>{formatNumber(trial.output_tokens ?? 0)}</strong></div>
          <div><span>Result path</span><strong className="mono">{compactPath(trial.result_local_path)}</strong></div>
          <div><span>Result artifact URI</span><strong className="mono">{compactPath(trial.result_artifact_uri)}</strong></div>
          <div><span>Artifacts</span><strong>{formatNumber(artifacts.length)}</strong></div>
        </div>
      </section>

      {invalidRow ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Invalid / quarantined context</h2>
              <p><InvalidReason row={invalidRow} /></p>
            </div>
            <ValidityBadge row={invalidRow} />
          </div>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Evidence links</h2>
            <p>Move between the run, task, quality audit, and artifact rows for this trial.</p>
          </div>
        </div>
        <div className="artifact-link-bar">
          <Link href={`/runs/${encodeURIComponent(trial.run_label)}`}>Run detail</Link>
          <Link href={trialQualityHref(trial)}>Trial Quality</Link>
          {trial.task_id ? <Link href={`/evals/${encodeURIComponent(trial.task_id)}`}>Eval task</Link> : null}
          <Link href={buildArtifactHref({ run_label: trial.run_label, task_id: trial.task_id, quality_flag: trial.quality_flag })}>
            Artifact browser
          </Link>
        </div>
      </section>

      {trial.exception_type || trial.exception_summary ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Exception context</h2>
              <p>{trial.exception_type ?? "exception"}</p>
            </div>
          </div>
          <div className="placeholder-body">{trial.exception_summary ?? "No exception summary recorded."}</div>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Related artifacts</h2>
            <p>Artifact rows attached to this trial.</p>
          </div>
        </div>
        {artifacts.length === 0 ? (
          <div className="placeholder-body">No artifact rows are attached to this trial.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Artifact</th>
                  <th>Storage</th>
                  <th>Size</th>
                  <th>Preview</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((artifact) => (
                  <tr key={artifact.artifact_id}>
                    <td>
                      <div><ArtifactTypeLabel artifactType={artifact.artifact_type} /></div>
                      <div className="mono" title={artifact.local_path ?? artifact.r2_uri ?? artifact.artifact_id}>
                        {compactPath(artifact.local_path ?? artifact.r2_uri ?? artifact.artifact_id)}
                      </div>
                    </td>
                    <td>{artifact.r2_uri ? "R2 indexed" : "local only"}</td>
                    <td>{formatBytes(artifact.size_bytes)}</td>
                    <td><Link href={`/artifacts/${artifact.artifact_id}`}>View artifact</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Task text</h2>
            <p>{taskInstruction.message}</p>
          </div>
          {taskInstruction.path ? <span className="mono">{taskInstruction.path}</span> : null}
        </div>
        {taskInstruction.text ? (
          <pre className="content-preview content-preview-compact">{taskInstruction.text}</pre>
        ) : (
          <div className="placeholder-body">No task instruction text is available in this dashboard context.</div>
        )}
      </section>
    </AppShell>
  );
}
