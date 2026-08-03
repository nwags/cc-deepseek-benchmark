import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { previewArtifactContent } from "../../../lib/artifact-content";
import { formatBytes } from "../../../lib/format";
import { getLiveArtifact, getLiveRun } from "../../../lib/live-data";

export const dynamic = "force-dynamic";

function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

export default async function LiveArtifactPage({
  params
}: {
  params: Promise<{ artifactId: string }>;
}) {
  const { artifactId } = await params;
  const artifact = await getLiveArtifact(decodeURIComponent(artifactId));
  if (!artifact) notFound();

  const [run, preview] = await Promise.all([
    getLiveRun(artifact.live_run_id),
    previewArtifactContent({
      artifact_id: artifact.artifact_id,
      artifact_type: artifact.artifact_type,
      local_path: artifact.relative_local_path,
      r2_uri: artifact.r2_uri,
      sha256: artifact.sha256,
      size_bytes: artifact.size_bytes
    })
  ]);

  return (
    <AppShell
      title="Live artifact"
      description="Read-only preview of an immutable progressive artifact version. R2 content is fetched server-side."
    >
      <section className="quality-context-panel">
        This row represents one stable uploaded version. Growing active files are observed separately for structured tool activity and are not exposed as mutable downloads.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{artifact.artifact_type}</h2>
            <p className="mono">{artifact.relative_local_path}</p>
          </div>
          <span className={artifact.r2_uri ? "quality-badge" : "quality-badge quality-badge-warn"}>
            {artifact.r2_uri ? "R2 available" : "metadata only"}
          </span>
        </div>
        <div className="detail-grid">
          <div><span>Live run</span><strong><Link href={`/runs/live?live_run_id=${encodeURIComponent(artifact.live_run_id)}`}>{artifact.live_run_id}</Link></strong></div>
          <div><span>Arm</span><strong className="mono">{run?.arm_id ?? "—"}</strong></div>
          <div><span>Trial</span><strong className="mono">{artifact.trial_key ?? "run root"}</strong></div>
          <div><span>Artifact id</span><strong className="mono">{artifact.artifact_id}</strong></div>
          <div><span>State</span><strong>{artifact.stability_state}</strong></div>
          <div><span>Uploaded</span><strong>{fmtDate(artifact.uploaded_at)}</strong></div>
          <div><span>Size</span><strong>{formatBytes(artifact.size_bytes)}</strong></div>
          <div><span>SHA256</span><strong className="mono">{artifact.sha256}</strong></div>
          <div><span>Preview source</span><strong>{preview.source}</strong></div>
        </div>
        <div className="artifact-link-bar">
          <Link href={`/runs/live?live_run_id=${encodeURIComponent(artifact.live_run_id)}`}>Back to Live Runs</Link>
          {artifact.r2_uri ? <a href={`/live-artifacts/${encodeURIComponent(artifact.artifact_id)}/download`}>Download immutable R2 object</a> : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Content preview</h2>
            <p>Bounded server-side preview; dashboard credentials and signed storage requests are never sent to the browser.</p>
          </div>
          <span className={preview.available ? "quality-badge" : "quality-badge quality-badge-warn"}>
            {preview.available ? "preview loaded" : "metadata only"}
          </span>
        </div>
        <div className="placeholder-body">
          {preview.messages.length > 0 ? (
            <ul>{preview.messages.map((message) => <li key={message}>{message}</li>)}</ul>
          ) : null}
          <p>
            Read {formatBytes(preview.bytes_read)}{preview.total_bytes ? ` of ${formatBytes(preview.total_bytes)}` : ""}.
            {preview.content_type ? ` Content type: ${preview.content_type}.` : ""}
          </p>
        </div>
        {preview.text ? <pre className="content-preview">{preview.text}</pre> : null}
      </section>
    </AppShell>
  );
}
