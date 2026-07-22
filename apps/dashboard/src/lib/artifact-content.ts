import { createHash, createHmac } from "crypto";

type PreviewArtifact = {
  artifact_id?: string | null;
  artifact_type?: string | null;
  local_path?: string | null;
  r2_uri?: string | null;
  size_bytes?: number | string | null;
};

export type ArtifactContentPreview = {
  available: boolean;
  source: "r2" | "local" | "metadata";
  text: string | null;
  content_type: string | null;
  is_text: boolean;
  is_json: boolean;
  truncated: boolean;
  bytes_read: number;
  total_bytes: number | null;
  messages: string[];
};

export type TaskInstructionPreview = {
  available: boolean;
  text: string | null;
  path: string | null;
  message: string;
};

const DEFAULT_PREVIEW_BYTES = 200 * 1024;
const ABSOLUTE_PREVIEW_BYTES = 1024 * 1024;
const TEXT_ARTIFACT_TYPES = new Set([
  "log",
  "config",
  "result",
  "agent_transcript",
  "verifier_stdout",
  "trajectory",
  "verifier_reward",
  "verifier_ctrf",
  "exception",
  "lock"
]);

async function importFs(): Promise<typeof import("fs/promises")> {
  const runtimeImport = new Function("specifier", "return import(specifier)") as (
    specifier: string
  ) => Promise<typeof import("fs/promises")>;

  return runtimeImport("fs/promises");
}

const LOCAL_PREVIEW_ENABLED = process.env.DASHBOARD_ENABLE_LOCAL_ARTIFACT_PREVIEW === "1";
const TASK_TEXT_PREVIEW_ENABLED = process.env.DASHBOARD_ENABLE_LOCAL_TASK_TEXT_PREVIEW === "1";

function defaultCacheRoot() {
  return ".dashboard-artifact-cache";
}

function artifactCacheRoot() {
  return normalizeCacheRoot(process.env.DASHBOARD_ARTIFACT_CACHE_DIR || defaultCacheRoot());
}

function taskTextCacheRoot() {
  return normalizeCacheRoot(process.env.DASHBOARD_TASK_TEXT_CACHE_DIR || `${defaultCacheRoot()}/task-text`);
}

function normalizeCacheRoot(value: string) {
  const cleaned = value.replace(/\\/g, "/").replace(/\/+$/, "");
  return cleaned || defaultCacheRoot();
}

function absoluteCachePath(root: string, relativePath: string) {
  if (root.startsWith("/")) {
    return `${root}/${relativePath}`;
  }

  return `${process.cwd()}/${root}/${relativePath}`;
}

function cacheRelativePath(value: string | null | undefined) {
  if (!value) return null;

  const parts = value
    .replace(/\\/g, "/")
    .replace(/^\/+/, "")
    .split("/")
    .filter((part) => part && part !== ".");

  if (parts.length === 0 || parts.some((part) => part === "..")) {
    return null;
  }

  if (parts.includes(".git") || parts.includes(".secrets") || parts.some((part) => part.endsWith(".env"))) {
    return null;
  }

  return parts.join("/");
}

function safeLocalPath(localPath: string | null | undefined): string | null {
  if (!LOCAL_PREVIEW_ENABLED) return null;
  if (!localPath) return null;

  const relativePath = cacheRelativePath(localPath);
  if (!relativePath) return null;

  return absoluteCachePath(artifactCacheRoot(), relativePath);
}

function parseR2Uri(value: string | null | undefined): { bucket: string; key: string } | null {
  if (!value) return null;
  const match = value.match(/^r2:\/\/([^/]+)\/(.+)$/);
  if (!match) return null;
  return { bucket: match[1], key: match[2] };
}

function r2Config() {
  const endpointUrl = process.env.R2_ENDPOINT_URL;
  const accessKeyId = process.env.R2_ACCESS_KEY_ID;
  const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
  const region = process.env.R2_REGION || "auto";
  const missing = [];

  if (!endpointUrl) missing.push("R2_ENDPOINT_URL");
  if (!accessKeyId) missing.push("R2_ACCESS_KEY_ID");
  if (!secretAccessKey) missing.push("R2_SECRET_ACCESS_KEY");

  if (missing.length > 0 || !endpointUrl || !accessKeyId || !secretAccessKey) {
    return { configured: false as const, missing };
  }

  return {
    configured: true as const,
    endpointUrl,
    accessKeyId,
    secretAccessKey,
    region
  };
}

function encodePathSegment(value: string) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (char) =>
    `%${char.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function sha256Hex(value: string) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function hmac(key: Buffer | string, value: string) {
  return createHmac("sha256", key).update(value, "utf8").digest();
}

function hmacHex(key: Buffer | string, value: string) {
  return createHmac("sha256", key).update(value, "utf8").digest("hex");
}

function signR2Request({
  accessKeyId,
  secretAccessKey,
  region,
  method,
  url,
  range
}: {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  method: string;
  url: URL;
  range: string;
}) {
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, "");
  const dateStamp = amzDate.slice(0, 8);
  const service = "s3";
  const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;
  const headers: Record<string, string> = {
    host: url.host,
    range,
    "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    "x-amz-date": amzDate
  };
  const signedHeaders = Object.keys(headers).sort().join(";");
  const canonicalHeaders = Object.keys(headers)
    .sort()
    .map((key) => `${key}:${headers[key]}\n`)
    .join("");
  const canonicalRequest = [
    method,
    url.pathname,
    "",
    canonicalHeaders,
    signedHeaders,
    "UNSIGNED-PAYLOAD"
  ].join("\n");
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    credentialScope,
    sha256Hex(canonicalRequest)
  ].join("\n");
  const dateKey = hmac(`AWS4${secretAccessKey}`, dateStamp);
  const dateRegionKey = hmac(dateKey, region);
  const dateRegionServiceKey = hmac(dateRegionKey, service);
  const signingKey = hmac(dateRegionServiceKey, "aws4_request");
  const signature = hmacHex(signingKey, stringToSign);

  return {
    ...headers,
    authorization: `AWS4-HMAC-SHA256 Credential=${accessKeyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`
  };
}

function contentRangeTotal(value: string | null) {
  if (!value) return null;
  const match = value.match(/\/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function textLooksBinary(buffer: Buffer) {
  const sample = buffer.subarray(0, Math.min(buffer.length, 4096));
  return sample.includes(0);
}

function isTextPreview(artifact: PreviewArtifact, contentType: string | null, buffer: Buffer) {
  const artifactType = artifact.artifact_type ?? "";
  const localPath = artifact.local_path ?? artifact.r2_uri ?? "";

  if (TEXT_ARTIFACT_TYPES.has(artifactType)) return true;
  if (contentType?.includes("text/") || contentType?.includes("json") || contentType?.includes("xml")) {
    return true;
  }
  if (/\.(json|jsonl|txt|log|md|toml|yaml|yml|xml|ctrf)$/i.test(localPath)) return true;

  return !textLooksBinary(buffer);
}

function textFromBuffer(buffer: Buffer, artifact: PreviewArtifact, contentType: string | null) {
  if (!isTextPreview(artifact, contentType, buffer)) {
    return { text: null, isText: false, isJson: false };
  }

  const raw = new TextDecoder("utf-8").decode(buffer);
  const trimmed = raw.trim();

  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      return {
        text: JSON.stringify(JSON.parse(trimmed), null, 2),
        isText: true,
        isJson: true
      };
    } catch {
      // Keep the raw text when an artifact looks JSON-ish but is partial.
    }
  }

  return { text: raw, isText: true, isJson: false };
}

function previewFromBuffer({
  buffer,
  source,
  artifact,
  contentType,
  totalBytes,
  truncated,
  messages
}: {
  buffer: Buffer;
  source: "r2" | "local";
  artifact: PreviewArtifact;
  contentType: string | null;
  totalBytes: number | null;
  truncated: boolean;
  messages: string[];
}): ArtifactContentPreview {
  const rendered = textFromBuffer(buffer, artifact, contentType);
  const finalMessages = [...messages];

  if (!rendered.isText) {
    finalMessages.push("Binary or unknown content type; metadata only.");
  }

  if (truncated) {
    finalMessages.push(`Preview is truncated to ${buffer.length.toLocaleString()} bytes.`);
  }

  return {
    available: rendered.isText,
    source,
    text: rendered.text,
    content_type: contentType,
    is_text: rendered.isText,
    is_json: rendered.isJson,
    truncated,
    bytes_read: buffer.length,
    total_bytes: totalBytes,
    messages: finalMessages
  };
}

async function readLocalPreview(
  artifact: PreviewArtifact,
  maxBytes: number,
  messages: string[]
): Promise<ArtifactContentPreview | null> {
  if (!LOCAL_PREVIEW_ENABLED) {
    if (artifact.local_path) {
      messages.push("Local file preview disabled. Set DASHBOARD_ENABLE_LOCAL_ARTIFACT_PREVIEW=1 to use the local artifact cache fallback.");
    }
    return null;
  }

  const safePath = safeLocalPath(artifact.local_path);

  if (!safePath) {
    if (artifact.local_path) messages.push("Local file unavailable: path is outside allowed preview roots.");
    return null;
  }

  try {
    const { open, stat } = await importFs();
    const fileStat = await stat(safePath);
    if (!fileStat.isFile()) {
      messages.push("Local file unavailable: path is not a regular file.");
      return null;
    }

    const length = Math.min(fileStat.size, maxBytes);
    const handle = await open(safePath, "r");
    try {
      const buffer = Buffer.alloc(length);
      const result = await handle.read(buffer, 0, length, 0);
      return previewFromBuffer({
        buffer: buffer.subarray(0, result.bytesRead),
        source: "local",
        artifact,
        contentType: null,
        totalBytes: fileStat.size,
        truncated: fileStat.size > result.bytesRead,
        messages
      });
    } finally {
      await handle.close();
    }
  } catch {
    messages.push("Local file unavailable: file does not exist in the dashboard workspace.");
    return null;
  }
}

async function readR2Preview(
  artifact: PreviewArtifact,
  maxBytes: number,
  messages: string[]
): Promise<ArtifactContentPreview | null> {
  const parsed = parseR2Uri(artifact.r2_uri);
  if (!parsed) return null;

  const config = r2Config();
  if (!config.configured) {
    messages.push(`R2 preview unavailable: missing server configuration (${config.missing.join(", ")}).`);
    return null;
  }

  const endpoint = new URL(config.endpointUrl);
  const keyPath = parsed.key.split("/").map(encodePathSegment).join("/");
  const basePath = endpoint.pathname.replace(/\/$/, "");
  endpoint.pathname = `${basePath}/${encodePathSegment(parsed.bucket)}/${keyPath}`;
  const range = `bytes=0-${maxBytes - 1}`;
  const headers = signR2Request({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region,
    method: "GET",
    url: endpoint,
    range
  });

  try {
    const response = await fetch(endpoint, {
      headers,
      cache: "no-store"
    });

    if (!response.ok && response.status !== 206) {
      messages.push(`R2 preview unavailable: object request returned HTTP ${response.status}.`);
      return null;
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    const totalFromRange = contentRangeTotal(response.headers.get("content-range"));
    const fallbackTotal = Number(response.headers.get("content-length") ?? artifact.size_bytes ?? 0);
    const totalBytes = totalFromRange ?? (fallbackTotal || null);

    return previewFromBuffer({
      buffer,
      source: "r2",
      artifact,
      contentType: response.headers.get("content-type"),
      totalBytes,
      truncated: response.status === 206 || (totalBytes !== null && totalBytes > buffer.length),
      messages
    });
  } catch (error) {
    messages.push(`R2 preview unavailable: ${error instanceof Error ? error.message : "request failed"}.`);
    return null;
  }
}

export async function previewArtifactContent(
  artifact: PreviewArtifact,
  options: { maxBytes?: number } = {}
): Promise<ArtifactContentPreview> {
  const maxBytes = Math.min(
    Math.max(options.maxBytes ?? DEFAULT_PREVIEW_BYTES, 1),
    ABSOLUTE_PREVIEW_BYTES
  );
  const messages: string[] = [];

  const r2Preview = await readR2Preview(artifact, maxBytes, messages);
  if (r2Preview) return r2Preview;

  const localPreview = await readLocalPreview(artifact, maxBytes, messages);
  if (localPreview) return localPreview;

  if (artifact.r2_uri && messages.every((message) => !message.startsWith("R2 preview unavailable"))) {
    messages.push("R2 URI present but unavailable for preview.");
  }
  if (!artifact.local_path) {
    messages.push("Local file unavailable: no local path recorded.");
  }
  messages.push("Artifact rehydration or dashboard R2 credentials are needed for content preview.");

  return {
    available: false,
    source: "metadata",
    text: null,
    content_type: null,
    is_text: false,
    is_json: false,
    truncated: false,
    bytes_read: 0,
    total_bytes: Number(artifact.size_bytes ?? 0) || null,
    messages
  };
}

export async function getTaskInstructionPreview(taskId: string | null | undefined): Promise<TaskInstructionPreview> {
  if (!taskId) {
    return { available: false, text: null, path: null, message: "Task text is not ingested yet." };
  }

  if (!TASK_TEXT_PREVIEW_ENABLED) {
    return {
      available: false,
      text: null,
      path: null,
      message: "Task text is not ingested yet. Optional local task text preview is disabled."
    };
  }

  const slug = taskId.includes(":") ? taskId.split(":").at(-1) : taskId;
  if (!slug || !/^[a-zA-Z0-9._-]+$/.test(slug)) {
    return { available: false, text: null, path: null, message: "Task text is not ingested yet." };
  }

  const root = taskTextCacheRoot();
  const instructionPath = absoluteCachePath(root, `${slug}/instruction.md`);

  try {
    const { readFile } = await importFs();
    const text = await readFile(instructionPath, "utf8");
    return {
      available: true,
      text,
      path: `${slug}/instruction.md`,
      message: "Loaded from local task text cache."
    };
  } catch {
    return { available: false, text: null, path: null, message: "Task text is not ingested yet." };
  }
}
