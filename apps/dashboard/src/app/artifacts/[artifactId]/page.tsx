import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { ArtifactTypeLabel, ArtifactTypesReference } from "../../../components/ArtifactTypeInfo";
import { QualityBadge, buildSuspectNoopHref } from "../../../components/QualityContext";
import { InvalidReason, ValidityBadge } from "../../../components/ValidityContext";
import {
  ArtifactDetailRow,
  InvalidArmRunRow,
  getArtifactDetail,
  getArtifactsForTrial
} from "../../../lib/dashboard-data";
import { getTaskInstructionPreview, previewArtifactContent } from "../../../lib/artifact-content";
import { buildArtifactHref } from "../../../lib/links";
import { formatBytes, formatCurrency, formatNumber, formatSeconds } from "../../../lib/format";

export const dynamic = "force-dynamic";

function compactPath(value: string | null | undefined) {
  if (!value) return "—";
  const parts = value.split("/");
  if (parts.length <= 7) return value;
  return `…/${parts.slice(-5).join("/")}`;
}

function invalidRowFromArtifact(row: ArtifactDetailRow): InvalidArmRunRow | null {
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

function trialQualityHref(row: ArtifactDetailRow) {
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

export default async function ArtifactDetailPage({
  params
}: {
  params: Promise<{ artifactId: string }>;
}) {
  const { artifactId } = await params;
  const artifact = await getArtifactDetail(decodeURIComponent(artifactId));

  if (!artifact) {
    notFound();
  }

  const [relatedArtifacts, preview, taskInstruction] = await Promise.all([
    artifact.trial_id ? getArtifactsForTrial(artifact.trial_id) : Promise.resolve([]),
    previewArtifactContent(artifact),
    getTaskInstructionPreview(artifact.task_id)
  ]);
  const invalidRow = invalidRowFromArtifact(artifact);

  return (
    <AppShell
      title="Artifact detail"
      description="Read-only artifact evidence preview. Content is fetched server-side from R2 when configured."
    >
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2><ArtifactTypeLabel artifactType={artifact.artifact_type ?? "artifact"} /></h2>
            <p>
              <Link href={buildArtifactHref({ run_label: artifact.run_label, task_id: artifact.task_id })}>
                Back to filtered artifacts
              </Link>
            </p>
          </div>
          <ValidityBadge row={invalidRow} />
        </div>

        <div className="detail-grid">
          <div><span>Run</span><strong><Link href={`/runs/${encodeURIComponent(artifact.run_label)}`}>{artifact.run_label}</Link></strong></div>
          <div><span>Suite</span><strong className="mono">{artifact.suite_id ?? "—"}</strong></div>
          <div><span>Arm</span><strong className="mono">{artifact.arm_id ?? "—"}</strong></div>
          <div><span>Task</span><strong className="mono">{artifact.task_id ?? "run-root artifact"}</strong></div>
          <div><span>Attempt</span><strong>{artifact.attempt_index ?? "—"}</strong></div>
          <div><span>Quality</span><strong>{artifact.quality_flag ?? "run artifact"}</strong></div>
          <div><span>Reward</span><strong>{artifact.reward ?? "—"}</strong></div>
          <div><span>Runtime</span><strong>{formatSeconds(artifact.runtime_seconds)}</strong></div>
          <div><span>Cost</span><strong>{formatCurrency(artifact.cost_usd)}</strong></div>
          <div><span>Tokens</span><strong>{formatNumber(artifact.input_tokens ?? 0)} in / {formatNumber(artifact.output_tokens ?? 0)} out</strong></div>
          <div><span>Artifact id</span><strong className="mono">{artifact.artifact_id}</strong></div>
          <div><span>Trial id</span><strong className="mono">{artifact.trial_id ?? "—"}</strong></div>
          <div><span>Size</span><strong>{formatBytes(artifact.size_bytes)}</strong></div>
          <div><span>SHA256</span><strong className="mono">{artifact.sha256 ?? "—"}</strong></div>
          <div><span>Created</span><strong>{artifact.created_at ?? "—"}</strong></div>
          <div><span>Retention</span><strong>{artifact.retention_class ?? "—"}</strong></div>
          <div><span>R2</span><strong>{artifact.r2_uri ? "R2 indexed" : "not indexed"}</strong></div>
          <div><span>Preview source</span><strong>{preview.source}</strong></div>
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

      <ArtifactTypesReference />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Evidence links</h2>
            <p>Navigate from this artifact to the surrounding trial, run, and task context.</p>
          </div>
        </div>
        <div className="artifact-link-bar">
          <Link href={`/runs/${encodeURIComponent(artifact.run_label)}`}>Run detail</Link>
          <Link href={trialQualityHref(artifact)}>Trial Quality</Link>
          {artifact.task_id ? <Link href={`/evals/${encodeURIComponent(artifact.task_id)}`}>Eval task</Link> : null}
          {artifact.trial_id ? <Link href={`/trials/${artifact.trial_id}`}>Trial evidence</Link> : null}
          {artifact.r2_uri ? <span className="mono" title={artifact.r2_uri}>{compactPath(artifact.r2_uri)}</span> : null}
          {artifact.local_path ? <span className="mono" title={artifact.local_path}>{compactPath(artifact.local_path)}</span> : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Content preview</h2>
            <p>Server-side bounded preview. Public signed download links are not exposed.</p>
          </div>
          <span className={preview.available ? "quality-badge" : "quality-badge quality-badge-warn"}>
            {preview.available ? "preview loaded" : "metadata only"}
          </span>
        </div>
        <div className="placeholder-body">
          {preview.messages.length > 0 ? (
            <ul>
              {preview.messages.map((message) => <li key={message}>{message}</li>)}
            </ul>
          ) : null}
          <p>
            Read {formatBytes(preview.bytes_read)}{preview.total_bytes ? ` of ${formatBytes(preview.total_bytes)}` : ""}.
            {preview.content_type ? ` Content type: ${preview.content_type}.` : ""}
          </p>
        </div>
        {preview.text ? (
          <pre className="content-preview">{preview.text}</pre>
        ) : null}
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

      {artifact.exception_type || artifact.exception_summary ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Exception context</h2>
              <p>{artifact.exception_type ?? "exception"}</p>
            </div>
          </div>
          <div className="placeholder-body">{artifact.exception_summary ?? "No exception summary recorded."}</div>
        </section>
      ) : null}

      {relatedArtifacts.length > 0 ? (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Related trial artifacts</h2>
              <p>All artifact rows attached to this trial.</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Artifact</th>
                  <th>Storage</th>
                  <th>Size</th>
                  <th>Link</th>
                </tr>
              </thead>
              <tbody>
                {relatedArtifacts.map((row) => (
                  <tr key={row.artifact_id}>
                    <td>
                      <div><ArtifactTypeLabel artifactType={row.artifact_type} /></div>
                      <div className="mono" title={row.local_path ?? row.r2_uri ?? row.artifact_id}>
                        {compactPath(row.local_path ?? row.r2_uri ?? row.artifact_id)}
                      </div>
                    </td>
                    <td>{row.r2_uri ? "R2 indexed" : "local only"}</td>
                    <td>{formatBytes(row.size_bytes)}</td>
                    <td><Link href={`/artifacts/${row.artifact_id}`}>View artifact</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </AppShell>
  );
}
