import { fetchArtifactDownload } from "../../../../lib/artifact-content";
import { getLiveArtifact } from "../../../../lib/live-data";

export const dynamic = "force-dynamic";

function safeFilename(value: string): string {
  const basename = value.replace(/\\/g, "/").split("/").at(-1) || "artifact";
  return basename.replace(/[^A-Za-z0-9._-]+/g, "_").slice(0, 180) || "artifact";
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ artifactId: string }> }
) {
  const { artifactId } = await params;
  const artifact = await getLiveArtifact(decodeURIComponent(artifactId));
  if (!artifact || !artifact.r2_uri) {
    return new Response("Live artifact content is not available in R2.\n", { status: 404 });
  }

  const upstream = await fetchArtifactDownload({
    artifact_id: artifact.artifact_id,
    artifact_type: artifact.artifact_type,
    local_path: artifact.relative_local_path,
    r2_uri: artifact.r2_uri,
    sha256: artifact.sha256,
    size_bytes: artifact.size_bytes
  });
  if (!upstream || !upstream.body) {
    return new Response("R2 artifact download is unavailable.\n", { status: 503 });
  }

  const headers = new Headers({
    "cache-control": "private, no-store",
    "content-disposition": `attachment; filename="${safeFilename(artifact.relative_local_path)}"`,
    "content-security-policy": "default-src 'none'",
    "content-type": upstream.headers.get("content-type") || "application/octet-stream",
    "x-content-type-options": "nosniff"
  });
  const contentLength = upstream.headers.get("content-length");
  if (contentLength) headers.set("content-length", contentLength);

  return new Response(upstream.body, {
    status: upstream.status,
    headers
  });
}
