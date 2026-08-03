import { createHash, createHmac } from "crypto";
import {
  redactSecretsInText,
  redactStructuredValue
} from "./safe-display";

type PreviewArtifact = {
  artifact_id?: string | null;
  artifact_type?: string | null;
  local_path?: string | null;
  r2_uri?: string | null;
  sha256?: string | null;
  size_bytes?: number | string | null;
};

export type ArtifactReadCompleteness =
  | "complete"
  | "head_tail_only"
  | "truncated"
  | "unavailable"
  | "malformed";

export type SizeMetadataStatus =
  | "consistent"
  | "stored_underreported"
  | "stored_overreported"
  | "stored_missing"
  | "remote_unverified"
  | "remote_range_conflict"
  | "unknown";

export type AnalyzedArtifactIntegrityStatus =
  | "verified"
  | "mismatch"
  | "not_verifiable"
  | "not_checked_incomplete"
  | "unavailable";

export type ArtifactContentPreview = {
  available: boolean;
  source: "r2" | "local" | "metadata";
  text: string | null;
  content_type: string | null;
  is_text: boolean;
  is_json: boolean;
  truncated: boolean;
  completeness: ArtifactReadCompleteness;
  bytes_read: number;
  total_bytes: number | null;
  stored_total_bytes: number | null;
  remote_total_bytes: number | null;
  size_metadata_status: SizeMetadataStatus;
  analyzed_artifact_integrity_status: AnalyzedArtifactIntegrityStatus;
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
const DEFAULT_ANALYSIS_BYTES = 8 * 1024 * 1024;
const ABSOLUTE_ANALYSIS_BYTES = 32 * 1024 * 1024;
const DEFAULT_FETCH_TIMEOUT_MS = 15_000;
const ANALYSIS_LIMITS: Record<string, number> = {
  agent_transcript: DEFAULT_ANALYSIS_BYTES,
  trajectory: DEFAULT_ANALYSIS_BYTES,
  verifier_stdout: 2 * 1024 * 1024,
  verifier_ctrf: 2 * 1024 * 1024,
  exception: 1024 * 1024,
  result: 1024 * 1024,
  config: 1024 * 1024
};
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
  const configuredBucket = process.env.R2_BUCKET || null;
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
    region,
    configuredBucket
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
  range?: string;
}) {
  const now = new Date();
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, "");
  const dateStamp = amzDate.slice(0, 8);
  const service = "s3";
  const credentialScope = `${dateStamp}/${region}/${service}/aws4_request`;
  const headers: Record<string, string> = {
    host: url.host,
    "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    "x-amz-date": amzDate
  };
  if (range) headers.range = range;
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

export function parseContentRange(value: string | null) {
  if (!value) return null;
  const match = value.match(/^bytes\s+(\d+)-(\d+)\/(\d+)$/i);
  if (!match) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  const total = Number(match[3]);
  if (![start, end, total].every(Number.isSafeInteger) || start < 0 || end < start || total <= end) return null;
  return { start, end, total };
}

export function compareSizeMetadata(stored: number | null, remote: number | null): SizeMetadataStatus {
  if (stored === null && remote === null) return "unknown";
  if (stored === null) return "stored_missing";
  if (remote === null) return "remote_unverified";
  if (stored === remote) return "consistent";
  return stored < remote ? "stored_underreported" : "stored_overreported";
}

export async function readResponseWithByteLimit(
  response: Response,
  maxBytes: number
): Promise<{ buffer: Buffer; exceeded: boolean; bytesReceived: number }> {
  const limit = Math.max(1, Math.floor(maxBytes));
  if (!response.body) return { buffer: Buffer.alloc(0), exceeded: false, bytesReceived: 0 };

  const reader = response.body.getReader();
  const chunks: Buffer[] = [];
  let retained = 0;
  let received = 0;
  let exceeded = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = Buffer.from(value);
      received += chunk.length;
      const remaining = limit - retained;
      if (remaining > 0) {
        chunks.push(chunk.subarray(0, remaining));
        retained += Math.min(chunk.length, remaining);
      }
      if (chunk.length > remaining) {
        exceeded = true;
        await reader.cancel();
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }
  return { buffer: Buffer.concat(chunks, retained), exceeded, bytesReceived: received };
}

export function newlineAlignedHeadTail(head: Buffer, tail: Buffer): Buffer {
  const lastHeadNewline = head.lastIndexOf(0x0a);
  const firstTailNewline = tail.indexOf(0x0a);
  const alignedHead = lastHeadNewline >= 0 ? head.subarray(0, lastHeadNewline + 1) : Buffer.alloc(0);
  const alignedTail = firstTailNewline >= 0 ? tail.subarray(firstTailNewline + 1) : Buffer.alloc(0);
  return Buffer.concat([alignedHead, alignedTail]);
}

function numericArtifactSize(artifact: PreviewArtifact): number | null {
  const parsed = Number(artifact.size_bytes);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function isLineStreamArtifact(artifact: PreviewArtifact) {
  return artifact.artifact_type === "agent_transcript";
}

function analysisLimitForArtifact(artifact: PreviewArtifact, requested?: number) {
  const configuredRaw = process.env.DASHBOARD_ANALYSIS_MAX_BYTES;
  const configuredDefault = Number(configuredRaw ?? DEFAULT_ANALYSIS_BYTES);
  const typeDefault = ANALYSIS_LIMITS[artifact.artifact_type ?? ""] ?? DEFAULT_ANALYSIS_BYTES;
  const configurableType = artifact.artifact_type === "agent_transcript" || artifact.artifact_type === "trajectory";
  const validConfigured = Number.isFinite(configuredDefault) && configuredDefault > 0
    ? configuredDefault : DEFAULT_ANALYSIS_BYTES;
  const chosen = requested ?? (configuredRaw && configurableType ? validConfigured : Math.min(validConfigured, typeDefault));
  return Math.min(Math.max(Math.floor(chosen), 1), ABSOLUTE_ANALYSIS_BYTES);
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
  return { text: raw, isText: true, isJson: false };
}

function redactReasoningValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactReasoningValue);
  if (!value || typeof value !== "object") return value;
  const source = value as Record<string, unknown>;
  const type = String(source.type ?? "").toLowerCase();
  const subtype = String(source.subtype ?? "").toLowerCase();
  if (subtype === "thinking_tokens") {
    return {
      type: source.type,
      subtype: source.subtype,
      estimated_tokens: source.estimated_tokens,
      estimated_tokens_delta: source.estimated_tokens_delta,
      content: "[thinking event metadata only; hidden reasoning not displayed]"
    };
  }
  if (type.includes("thinking") || type.includes("reasoning") || subtype.includes("thinking") || subtype.includes("reasoning")) {
    return { type: source.type ?? "hidden_reasoning", subtype: source.subtype, content: "[hidden reasoning not displayed]" };
  }
  const safe: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(source)) {
    safe[key] = /thinking|reasoning/i.test(key) && key !== "thinking_tokens"
      ? "[hidden reasoning not displayed]"
      : redactReasoningValue(item);
  }
  return safe;
}

function definiteWorkspaceChange(name: string, input: unknown) {
  if (["Write", "Edit", "NotebookEdit", "MultiEdit", "apply_patch"].includes(name)) return true;
  if (name !== "Bash" || !input || typeof input !== "object") return false;
  const command = String((input as Record<string, unknown>).command ?? "");
  return /(^|[;&|]\s*)(touch|mkdir|cp|mv|rm|install|patch|git\s+apply)\b|(^|\s)(sed\s+-i|tee\b)|>{1,2}\s*[^&]/m.test(command);
}

function usageFields(value: unknown) {
  if (!value || typeof value !== "object") return undefined;
  const source = value as Record<string, unknown>;
  const allowed = [
    "input_tokens", "uncached_input_tokens", "cache_read_input_tokens",
    "cache_creation_input_tokens", "output_tokens", "cost_usd", "total_cost_usd"
  ];
  const output: Record<string, unknown> = {};
  for (const key of allowed) {
    if (Object.prototype.hasOwnProperty.call(source, key)) output[key] = source[key];
  }
  return Object.keys(output).length ? output : undefined;
}

function sanitizeTranscriptRecord(value: unknown): unknown {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, any>;
  const base: Record<string, unknown> = {
    type: record.type,
    subtype: record.subtype
  };

  for (const key of ["api_refusal_category", "refusal_category", "terminal_reason", "stop_reason", "api_error_status", "status", "duration_api_ms", "duration_ms", "total_cost_usd", "id", "request_id", "usage_mode", "usage_is_cumulative"]) {
    if (Object.prototype.hasOwnProperty.call(record, key)) base[key] = record[key];
  }

  if (record.type === "system") {
    if (record.subtype === "thinking_tokens") {
      base.estimated_tokens = record.estimated_tokens;
      base.estimated_tokens_delta = record.estimated_tokens_delta;
    }
    if (record.subtype === "init") {
      base.model = record.model;
      base.claude_code_version = record.claude_code_version ?? record.claudeCodeVersion;
    }
    return base;
  }

  if (record.type === "user") {
    const serialized = JSON.stringify(record.message ?? record.content ?? "");
    if (serialized.includes("Your previous response had no visible output")) {
      return { type: "user", message: { content: "[Your previous response had no visible output.]" } };
    }
    return { type: "user", visible_content_omitted: true };
  }

  if (record.type === "assistant") {
    const message = record.message && typeof record.message === "object" ? record.message : record;
    const content = Array.isArray(message.content) ? message.content : [];
    const safeContent: Record<string, unknown>[] = [];
    for (const item of content) {
      if (!item || typeof item !== "object") continue;
      if (String(item.type ?? "").match(/thinking|reasoning/i)) {
        safeContent.push({ type: item.type ?? "hidden_reasoning", hidden_content_omitted: true });
      } else if (item.type === "text") {
        const text = String(item.text ?? "");
        safeContent.push({ type: "text", text: text.startsWith("API Error:") ? "API Error:" : text.trim() ? "[visible assistant content]" : "" });
      } else if (item.type === "tool_use") {
        const name = String(item.name ?? "");
        safeContent.push({ type: "tool_use", name, input: { workspace_changing: definiteWorkspaceChange(name, item.input) } });
      }
    }
    return {
      ...base,
      message: {
        id: message.id,
        stop_reason: message.stop_reason,
        usage: usageFields(message.usage),
        content: safeContent
      },
      usage: usageFields(record.usage)
    };
  }

  if (record.type === "result") {
    const modelUsage: Record<string, unknown> = {};
    if (record.modelUsage && typeof record.modelUsage === "object") {
      for (const [model, usage] of Object.entries(record.modelUsage as Record<string, unknown>)) {
        modelUsage[model] = usageFields(usage);
      }
    }
    return {
      ...base,
      result: Object.prototype.hasOwnProperty.call(record, "result")
        ? (typeof record.result === "string" && record.result.trim() ? "[visible result]" : "")
        : undefined,
      usage: usageFields(record.usage),
      modelUsage: Object.keys(modelUsage).length ? modelUsage : undefined
    };
  }

  return base;
}

function safelyRenderStructuredArtifact(
  raw: string,
  artifactType: string | null | undefined,
  completeness: ArtifactReadCompleteness
): { text: string | null; isJson: boolean; malformed: boolean } {
  if (artifactType === "agent_transcript") {
    const safeLines: string[] = [];
    let malformed = false;
    for (const line of raw.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try {
        const safe = redactStructuredValue(sanitizeTranscriptRecord(JSON.parse(line)));
        safeLines.push(JSON.stringify(safe));
      } catch {
        malformed = true;
      }
    }
    return {
      text: safeLines.join("\n") || null,
      isJson: safeLines.length > 0,
      malformed: malformed && completeness === "complete"
    };
  }

  const trimmed = raw.trim();
  if (artifactType === "trajectory" || artifactType === "config" || artifactType === "result" || artifactType === "verifier_ctrf") {
    if (completeness !== "complete") {
      return { text: null, isJson: false, malformed: false };
    }
    try {
      const parsed = JSON.parse(trimmed);
      const reasoningSafe = artifactType === "trajectory" ? redactReasoningValue(parsed) : parsed;
      return {
        text: JSON.stringify(redactStructuredValue(reasoningSafe), null, 2),
        isJson: true,
        malformed: false
      };
    } catch {
      if (artifactType === "config") {
        return { text: redactSecretsInText(raw), isJson: false, malformed: false };
      }
      return { text: null, isJson: false, malformed: true };
    }
  }

  return { text: redactSecretsInText(raw), isJson: false, malformed: false };
}

export function redactHiddenReasoningPreview(
  text: string | null,
  artifactType: string | null | undefined
): string | null {
  if (!text || (artifactType !== "agent_transcript" && artifactType !== "trajectory")) return text;
  const rendered = safelyRenderStructuredArtifact(text, artifactType, "complete");
  return rendered.text ?? "Structured agent evidence could not be safely parsed. Hidden reasoning content is not displayed.";
}

function previewFromBuffer({
  buffer,
  source,
  artifact,
  contentType,
  totalBytes,
  storedTotalBytes,
  remoteTotalBytes,
  sizeMetadataStatus,
  analyzedArtifactIntegrityStatus,
  completeness,
  bytesRead,
  messages
}: {
  buffer: Buffer;
  source: "r2" | "local";
  artifact: PreviewArtifact;
  contentType: string | null;
  totalBytes: number | null;
  storedTotalBytes?: number | null;
  remoteTotalBytes?: number | null;
  sizeMetadataStatus?: SizeMetadataStatus;
  analyzedArtifactIntegrityStatus?: AnalyzedArtifactIntegrityStatus;
  completeness: ArtifactReadCompleteness;
  bytesRead?: number;
  messages: string[];
}): ArtifactContentPreview {
  const stored = storedTotalBytes ?? numericArtifactSize(artifact);
  const remote = remoteTotalBytes ?? null;
  const sizeStatus = sizeMetadataStatus ?? compareSizeMetadata(stored, remote);
  let integrity = analyzedArtifactIntegrityStatus ?? (completeness === "complete"
    ? artifact.sha256
      ? createHash("sha256").update(buffer).digest("hex") === artifact.sha256.trim().toLowerCase() ? "verified" : "mismatch"
      : "not_verifiable"
    : "not_checked_incomplete");
  const effectiveCompleteness = integrity === "mismatch" ? "malformed" : completeness;
  const rendered = textFromBuffer(buffer, artifact, contentType);
  const safeRendered = rendered.text === null
    ? { text: null, isJson: false, malformed: false }
    : safelyRenderStructuredArtifact(rendered.text, artifact.artifact_type, effectiveCompleteness);
  const finalMessages = [...messages];

  if (!rendered.isText) {
    finalMessages.push("Binary or unknown content type; metadata only.");
  }

  if (effectiveCompleteness === "head_tail_only") {
    finalMessages.push("Artifact exceeded the complete-read cap; only newline-aligned head and tail records were inspected.");
  } else if (effectiveCompleteness === "truncated") {
    finalMessages.push(`Preview is truncated to ${buffer.length.toLocaleString()} bytes.`);
  } else if (safeRendered.malformed) {
    finalMessages.push("Structured artifact content is malformed and was not rendered.");
  }

  return {
    available: rendered.isText && safeRendered.text !== null,
    source,
    text: safeRendered.text,
    content_type: contentType,
    is_text: rendered.isText,
    is_json: safeRendered.isJson,
    truncated: effectiveCompleteness !== "complete",
    completeness: safeRendered.malformed ? "malformed" : effectiveCompleteness,
    bytes_read: bytesRead ?? buffer.length,
    total_bytes: totalBytes,
    stored_total_bytes: stored,
    remote_total_bytes: remote,
    size_metadata_status: sizeStatus,
    analyzed_artifact_integrity_status: integrity,
    messages: finalMessages
  };
}

async function readLocalPreview(
  artifact: PreviewArtifact,
  maxBytes: number,
  messages: string[],
  headTail = false
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

    const handle = await open(safePath, "r");
    try {
      if (headTail && fileStat.size > maxBytes && isLineStreamArtifact(artifact)) {
        const headLength = Math.floor(maxBytes / 2);
        const tailLength = maxBytes - headLength;
        const head = Buffer.alloc(headLength);
        const tail = Buffer.alloc(tailLength);
        const [headRead, tailRead] = await Promise.all([
          handle.read(head, 0, headLength, 0),
          handle.read(tail, 0, tailLength, Math.max(fileStat.size - tailLength, 0))
        ]);
        const combined = newlineAlignedHeadTail(
          head.subarray(0, headRead.bytesRead),
          tail.subarray(0, tailRead.bytesRead)
        );
        return previewFromBuffer({
          buffer: combined,
          source: "local",
          artifact,
          contentType: null,
          totalBytes: fileStat.size,
          completeness: "head_tail_only",
          bytesRead: headRead.bytesRead + tailRead.bytesRead,
          messages
        });
      }

      const length = Math.min(fileStat.size, maxBytes);
      const buffer = Buffer.alloc(length);
      const result = await handle.read(buffer, 0, length, 0);
      return previewFromBuffer({
        buffer: buffer.subarray(0, result.bytesRead),
        source: "local",
        artifact,
        contentType: null,
        totalBytes: fileStat.size,
        completeness: fileStat.size > result.bytesRead ? "truncated" : "complete",
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
  messages: string[],
  headTail = false
): Promise<ArtifactContentPreview | null> {
  const parsed = parseR2Uri(artifact.r2_uri);
  if (!parsed) return null;

  const config = r2Config();
  if (!config.configured) {
    messages.push(`R2 preview unavailable: missing server configuration (${config.missing.join(", ")}).`);
    return null;
  }
  if (config.configuredBucket && parsed.bucket !== config.configuredBucket) {
    messages.push("R2 preview unavailable: artifact bucket does not match dashboard configuration.");
    return null;
  }

  const endpoint = new URL(config.endpointUrl);
  const keyPath = parsed.key.split("/").map(encodePathSegment).join("/");
  const basePath = endpoint.pathname.replace(/\/$/, "");
  endpoint.pathname = `${basePath}/${encodePathSegment(parsed.bucket)}/${keyPath}`;
  try {
    const requestRange = async (start: number, end: number, byteLimit: number) => {
      const range = `bytes=${start}-${end}`;
      const headers = signR2Request({
        accessKeyId: config.accessKeyId,
        secretAccessKey: config.secretAccessKey,
        region: config.region,
        method: "GET",
        url: endpoint,
        range
      });
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), DEFAULT_FETCH_TIMEOUT_MS);
      try {
        const response = await fetch(endpoint, {
          headers,
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok && response.status !== 206) {
          await response.body?.cancel();
          throw new Error(`HTTP ${response.status}`);
        }
        const body = await readResponseWithByteLimit(response, byteLimit);
        const parsedRange = parseContentRange(response.headers.get("content-range"));
        const contentLength = Number(response.headers.get("content-length"));
        const remoteTotal = parsedRange?.total
          ?? (response.status === 200 && Number.isSafeInteger(contentLength) && contentLength >= 0 ? contentLength : null);
        return {
          response,
          parsedRange,
          remoteTotal,
          rangeHonored: response.status === 206 && parsedRange?.start === start,
          ...body
        };
      } finally {
        clearTimeout(timeout);
      }
    };

    const recordedSize = numericArtifactSize(artifact);
    const lineStream = headTail && isLineStreamArtifact(artifact);
    const headLimit = lineStream ? Math.max(Math.floor(maxBytes / 2), 1) : maxBytes;
    const head = await requestRange(0, headLimit - 1, headLimit);
    const remoteTotal = head.remoteTotal;
    let sizeStatus = compareSizeMetadata(recordedSize, remoteTotal);
    let sizeConflict = sizeStatus === "stored_underreported" || sizeStatus === "stored_overreported";
    const contentType = head.response.headers.get("content-type");
    const integrityFor = (buffer: Buffer, fullyRead: boolean): AnalyzedArtifactIntegrityStatus => {
      if (!fullyRead) return "not_checked_incomplete";
      const expected = artifact.sha256?.trim().toLowerCase();
      if (!expected) return "not_verifiable";
      return createHash("sha256").update(buffer).digest("hex") === expected ? "verified" : "mismatch";
    };

    if (remoteTotal !== null && remoteTotal > maxBytes && lineStream) {
      const tailLimit = Math.max(maxBytes - head.buffer.length, 0);
      if (!head.rangeHonored || tailLimit === 0) {
        messages.push("R2 endpoint did not provide a verified prefix Range; only bounded prefix evidence was retained.");
        return previewFromBuffer({
          buffer: head.buffer, source: "r2", artifact, contentType,
          totalBytes: remoteTotal, storedTotalBytes: recordedSize, remoteTotalBytes: remoteTotal,
          sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: "not_checked_incomplete",
          completeness: "truncated", bytesRead: head.buffer.length, messages
        });
      }
      const tailStart = Math.max(remoteTotal - tailLimit, 0);
      const tail = await requestRange(tailStart, remoteTotal - 1, tailLimit);
      if (!tail.rangeHonored || tail.remoteTotal !== remoteTotal) {
        if (tail.remoteTotal !== null && tail.remoteTotal !== remoteTotal) {
          sizeStatus = "remote_range_conflict";
          sizeConflict = true;
        }
        messages.push("R2 endpoint did not provide a consistent verified tail Range; only bounded prefix evidence was retained.");
        return previewFromBuffer({
          buffer: head.buffer, source: "r2", artifact, contentType,
          totalBytes: remoteTotal, storedTotalBytes: recordedSize, remoteTotalBytes: remoteTotal,
          sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: "not_checked_incomplete",
          completeness: "truncated", bytesRead: head.buffer.length + tail.buffer.length, messages
        });
      }
      return previewFromBuffer({
        buffer: newlineAlignedHeadTail(head.buffer, tail.buffer), source: "r2", artifact, contentType,
        totalBytes: remoteTotal, storedTotalBytes: recordedSize, remoteTotalBytes: remoteTotal,
        sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: "not_checked_incomplete",
        completeness: "head_tail_only", bytesRead: head.buffer.length + tail.buffer.length, messages
      });
    }

    if (remoteTotal === null) {
      messages.push("R2 response did not provide a verified total object size; completeness cannot be established.");
      return previewFromBuffer({
        buffer: head.buffer, source: "r2", artifact, contentType,
        totalBytes: recordedSize, storedTotalBytes: recordedSize, remoteTotalBytes: null,
        sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: "not_checked_incomplete",
        completeness: "truncated", bytesRead: head.buffer.length, messages
      });
    }

    if (remoteTotal > maxBytes) {
      return previewFromBuffer({
        buffer: head.buffer, source: "r2", artifact, contentType,
        totalBytes: remoteTotal, storedTotalBytes: recordedSize, remoteTotalBytes: remoteTotal,
        sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: "not_checked_incomplete",
        completeness: "truncated", bytesRead: head.buffer.length, messages
      });
    }

    let raw = head.buffer.subarray(0, Math.min(head.buffer.length, remoteTotal));
    let bytesRead = head.buffer.length;
    let fullyRead = !head.exceeded && raw.length >= remoteTotal;
    if (!fullyRead && raw.length < remoteTotal) {
      const remainingLimit = Math.min(remoteTotal - raw.length, Math.max(maxBytes - bytesRead, 0));
      if (remainingLimit > 0) {
        const remainder = await requestRange(raw.length, remoteTotal - 1, remainingLimit);
        bytesRead += remainder.buffer.length;
        if (remainder.remoteTotal !== null && remainder.remoteTotal !== remoteTotal) {
          sizeStatus = "remote_range_conflict";
          sizeConflict = true;
        }
        if (remainder.rangeHonored && remainder.remoteTotal === remoteTotal) raw = Buffer.concat([raw, remainder.buffer]);
      }
      fullyRead = raw.length >= remoteTotal;
    }
    raw = raw.subarray(0, Math.min(raw.length, remoteTotal));
    const integrity = integrityFor(raw, fullyRead);
    return previewFromBuffer({
      buffer: raw, source: "r2", artifact, contentType,
      totalBytes: remoteTotal, storedTotalBytes: recordedSize, remoteTotalBytes: remoteTotal,
      sizeMetadataStatus: sizeStatus, analyzedArtifactIntegrityStatus: integrity,
      completeness: fullyRead && !sizeConflict ? "complete" : "truncated", bytesRead, messages
    });
  } catch (error) {
    const safeError = error instanceof Error ? redactSecretsInText(error.message) : null;
    messages.push(`R2 preview unavailable: ${safeError || "request failed"}.`);
    return null;
  }
}

export async function fetchArtifactDownload(
  artifact: PreviewArtifact
): Promise<Response | null> {
  const parsed = parseR2Uri(artifact.r2_uri);
  if (!parsed) return null;
  const config = r2Config();
  if (!config.configured) return null;
  if (config.configuredBucket && parsed.bucket !== config.configuredBucket) {
    return null;
  }

  const endpoint = new URL(config.endpointUrl);
  const keyPath = parsed.key.split("/").map(encodePathSegment).join("/");
  const basePath = endpoint.pathname.replace(/\/$/, "");
  endpoint.pathname = `${basePath}/${encodePathSegment(parsed.bucket)}/${keyPath}`;
  const headers = signR2Request({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region,
    method: "GET",
    url: endpoint
  });

  try {
    const response = await fetch(endpoint, { headers, cache: "no-store" });
    if (!response.ok) return null;

    const expectedSha = artifact.sha256?.trim().toLowerCase() || null;
    const remoteSha = response.headers
      .get("x-amz-meta-sha256")
      ?.trim()
      .toLowerCase() || null;
    const expectedSize =
      artifact.size_bytes === null || artifact.size_bytes === undefined
        ? null
        : Number(artifact.size_bytes);
    const remoteMetadataSizeHeader =
      response.headers.get("x-amz-meta-size_bytes");
    const remoteMetadataSize =
      remoteMetadataSizeHeader === null
        ? null
        : Number(remoteMetadataSizeHeader);
    const remoteContentLengthHeader =
      response.headers.get("content-length");
    const remoteContentLength =
      remoteContentLengthHeader === null
        ? null
        : Number(remoteContentLengthHeader);
    const integrityMismatch =
      (expectedSha !== null && remoteSha !== expectedSha)
      || (
        expectedSize !== null
        && remoteMetadataSize !== expectedSize
      )
      || (
        expectedSize !== null
        && remoteContentLength !== null
        && remoteContentLength !== expectedSize
      );

    if (integrityMismatch) {
      await response.body?.cancel();
      return null;
    }
    return response;
  } catch {
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
    completeness: "unavailable",
    bytes_read: 0,
    total_bytes: Number(artifact.size_bytes ?? 0) || null,
    stored_total_bytes: numericArtifactSize(artifact),
    remote_total_bytes: null,
    size_metadata_status: artifact.size_bytes === null || artifact.size_bytes === undefined ? "unknown" : "remote_unverified",
    analyzed_artifact_integrity_status: "unavailable",
    messages
  };
}

/**
 * Analysis reader with type-specific hard bounds. JSONL transcripts that exceed
 * the full-stream cap retain newline-aligned head and tail records; structured
 * JSON is analyzed only when the complete document fits within its cap.
 */
export async function readArtifactForAnalysis(
  artifact: PreviewArtifact,
  options: { maxBytes?: number } = {}
): Promise<ArtifactContentPreview> {
  const maxBytes = analysisLimitForArtifact(artifact, options.maxBytes);
  const messages: string[] = [];

  const r2Preview = await readR2Preview(artifact, maxBytes, messages, true);
  if (r2Preview) return r2Preview;

  const localPreview = await readLocalPreview(artifact, maxBytes, messages, true);
  if (localPreview) return localPreview;

  if (artifact.r2_uri && messages.every((message) => !message.startsWith("R2 preview unavailable"))) {
    messages.push("R2 URI present but unavailable for bounded analysis.");
  }
  if (!artifact.local_path) messages.push("Local file unavailable: no local path recorded.");

  return {
    available: false,
    source: "metadata",
    text: null,
    content_type: null,
    is_text: false,
    is_json: false,
    truncated: false,
    completeness: "unavailable",
    bytes_read: 0,
    total_bytes: numericArtifactSize(artifact),
    stored_total_bytes: numericArtifactSize(artifact),
    remote_total_bytes: null,
    size_metadata_status: artifact.size_bytes === null || artifact.size_bytes === undefined ? "unknown" : "remote_unverified",
    analyzed_artifact_integrity_status: "unavailable",
    messages
  };
}

export async function getTaskInstructionPreview(taskId: string | null | undefined): Promise<TaskInstructionPreview> {
  if (!taskId) {
    return { available: false, text: null, path: null, message: "No task id is attached, so task instructions cannot be resolved." };
  }

  if (!TASK_TEXT_PREVIEW_ENABLED) {
    return {
      available: false,
      text: null,
      path: null,
      message: "Task instructions are not stored in the dashboard database. Enable local preview with DASHBOARD_ENABLE_LOCAL_TASK_TEXT_PREVIEW=1 and DASHBOARD_TASK_TEXT_CACHE_DIR pointing at the Terminal-Bench task directory."
    };
  }

  const slug = taskId.includes(":") ? taskId.split(":").at(-1) : taskId;
  if (!slug || !/^[a-zA-Z0-9._-]+$/.test(slug)) {
    return { available: false, text: null, path: null, message: "Task id could not be mapped to a safe local task directory." };
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
    return { available: false, text: null, path: null, message: "No local instruction.md was found for this task. Set DASHBOARD_TASK_TEXT_CACHE_DIR to the Terminal-Bench task directory or ingest task instructions." };
  }
}
