import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const compile = (source) => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
}).outputText;

const safeSource = await readFile(join(here, "safe-display.ts"), "utf8");
const safeUrl = `data:text/javascript;base64,${Buffer.from(compile(safeSource)).toString("base64")}`;
const safeModule = await import(safeUrl);
const sharedRedactionVectors = JSON.parse(await readFile(join(here, "../../../../tests/fixtures/secret_redaction_vectors.json"), "utf8"));

const testCache = await mkdtemp(join(tmpdir(), "cc-artifact-reader-"));
process.env.DASHBOARD_ENABLE_LOCAL_ARTIFACT_PREVIEW = "1";
process.env.DASHBOARD_ARTIFACT_CACHE_DIR = testCache;
process.env.R2_ENDPOINT_URL = "https://r2.example.test";
process.env.R2_ACCESS_KEY_ID = "test-access";
process.env.R2_SECRET_ACCESS_KEY = "test-secret";
process.env.R2_BUCKET = "test-bucket";

const contentSource = await readFile(join(here, "artifact-content.ts"), "utf8");
const contentCompiled = compile(contentSource).replace('from "./safe-display"', `from "${safeUrl}"`);
const contentUrl = `data:text/javascript;base64,${Buffer.from(contentCompiled).toString("base64")}`;
const contentModule = await import(contentUrl);

test.after(async () => {
  await rm(testCache, { recursive: true, force: true });
});

test("recursive configuration redaction removes secrets while retaining safe endpoint context", () => {
  const source = {
    agent: {
      model_name: "router-kimi-k3",
      env: {
        ANTHROPIC_BASE_URL: "https://user:password@router.example.test:4000/v1/messages?deployment=kimi&api_key=top-secret",
        ANTHROPIC_AUTH_TOKEN: "sk-secret-value-1234567890",
        NORMAL_SETTING: "visible"
      }
    },
    database_url: "postgres://admin:password@db.example.test/bench",
    timeout_multiplier: 2
  };
  const before = JSON.stringify(source);
  const redacted = safeModule.redactStructuredValue(source);
  const rendered = JSON.stringify(redacted);
  assert.equal(JSON.stringify(source), before, "redaction must not mutate source objects");
  for (const secret of ["password", "top-secret", "sk-secret-value", "postgres://admin"]) {
    assert.equal(rendered.includes(secret), false);
  }
  assert.match(rendered, /router\.example\.test:4000/);
  assert.match(rendered, /deployment=kimi/);
  assert.match(rendered, /router-kimi-k3/);
  assert.match(rendered, /timeout_multiplier/);
});

test("displayed URL sanitization removes userinfo and signed query secrets for HTTP and R2", () => {
  const http = safeModule.sanitizeDisplayedUri("https://alice:secret@example.test:8443/api?deployment=blue&X-Amz-Signature=signed-secret&token=query-secret");
  const r2 = safeModule.sanitizeDisplayedUri("r2://user:password@bucket/path/object.json?X-Amz-Credential=credential-secret&version=7");
  for (const value of [http, r2]) {
    assert.equal(value.includes("alice"), false);
    assert.equal(value.includes("password"), false);
    assert.equal(value.includes("signed-secret"), false);
    assert.equal(value.includes("credential-secret"), false);
    assert.equal(value.includes("query-secret"), false);
    assert.equal(value.includes("@"), false);
  }
  assert.match(http, /example\.test:8443\/api/);
  assert.match(http, /deployment=blue/);
  assert.match(r2, /bucket\/path\/object\.json/);
  assert.match(r2, /version=7/);
});

test("structured redaction sanitizes secret-bearing primitive strings inside nested arrays", () => {
  const source = {
    arguments: [
      "Authorization: Bearer bearer-token-value-123456",
      [
        "ANTHROPIC_AUTH_TOKEN=sk-array-secret-value-123456",
        "provider=xai key=xai-provider-secret-123456",
        "https://alice:password@example.test/v1?deployment=green&X-Amz-Signature=signed-value",
        ["GOOGLE_API_KEY=AIzaNestedArraySecret123456789", "safe-option=visible"]
      ]
    ]
  };
  const original = JSON.stringify(source);
  const rendered = JSON.stringify(safeModule.redactStructuredValue(source));
  assert.equal(JSON.stringify(source), original, "structured redaction must remain immutable");
  for (const secret of ["bearer-token-value", "sk-array-secret", "xai-provider-secret", "password", "signed-value", "AIzaNestedArraySecret"]) {
    assert.equal(rendered.includes(secret), false, secret);
  }
  assert.match(rendered, /example\.test\/v1/);
  assert.match(rendered, /deployment=green/);
  assert.match(rendered, /safe-option=visible/);
});

test("free-text redaction covers bearer tokens, provider keys, assignments, signed URLs, and userinfo", () => {
  const text = [
    "Authorization: Bearer bearer-secret-123456",
    "OPENAI_API_KEY=sk-provider-secret-123456",
    "nested xai_api_key=xai-secret-value-123456; safe=value",
    "https://person:password@api.example.test/messages?route=blue&token=query-secret"
  ].join("\n");
  const rendered = safeModule.redactSecretsInText(text);
  for (const secret of ["bearer-secret", "sk-provider-secret", "xai-secret-value", "person", "password", "query-secret"]) {
    assert.equal(rendered.includes(secret), false, secret);
  }
  assert.match(rendered, /api\.example\.test\/messages/);
  assert.match(rendered, /route=blue/);
  assert.match(rendered, /safe=value/);
});

test("shared free-text and structured secret vectors match the TypeScript redactor", () => {
  for (const vector of sharedRedactionVectors.text_vectors) {
    const rendered = safeModule.redactSecretsInText(vector.input);
    for (const secret of vector.forbidden) assert.equal(rendered.includes(secret), false, `${vector.name}: ${secret}`);
    for (const safe of vector.required) assert.equal(rendered.includes(safe), true, `${vector.name}: ${safe}`);
  }
  for (const vector of sharedRedactionVectors.structured_vectors) {
    const before = JSON.stringify(vector.input);
    const rendered = JSON.stringify(safeModule.redactStructuredValue(vector.input));
    assert.equal(JSON.stringify(vector.input), before, `${vector.name}: immutable input`);
    for (const secret of vector.forbidden) assert.equal(rendered.includes(secret), false, `${vector.name}: ${secret}`);
    for (const safe of vector.required) assert.equal(rendered.includes(safe), true, `${vector.name}: ${safe}`);
  }
});

test("final evidence sink sanitizes every nested excerpt shape without changing ordinary password prose", () => {
  const source = {
    manual_evidence: {
      transcript_activity: {
        visible_assistant_excerpts: [
          "password=x",
          ['assistant emitted {"password":"abcdefghijklmnopqrst"}', "export PASSWD='abcdefghijklmnopqrstuvwx'"],
          "ordinary prose about a password-recovery benchmark"
        ],
        visible_result_excerpts: ["password = \"result value with spaces\";"]
      },
      verifier_stdout_excerpt: "PASSWORD=verifier-value, passwd:backup-value.",
      ctrf_tests: [{ name: "password=case-name", failure_message: "passwd='failure-value'" }]
    }
  };
  const before = JSON.stringify(source);
  const rendered = safeModule.sanitizeEvidenceOutput(source);
  const text = JSON.stringify(rendered);
  assert.equal(JSON.stringify(source), before, "final-sink redaction must be immutable");
  for (const secret of [
    "abcdefghijklmnopqrst", "abcdefghijklmnopqrstuvwx", "result value with spaces",
    "verifier-value", "backup-value", "case-name", "failure-value"
  ]) assert.equal(text.includes(secret), false, secret);
  assert.equal(text.includes("ordinary prose about a password-recovery benchmark"), true);
  assert.equal(text.includes("[REDACTED]"), true);
});

test("reasoning previews retain safe event metadata but never reasoning content", () => {
  const hidden = "private chain of thought";
  const transcript = JSON.stringify({ type: "system", subtype: "thinking_tokens", estimated_tokens: 12, content: hidden });
  const rendered = contentModule.redactHiddenReasoningPreview(transcript, "agent_transcript");
  assert.equal(rendered.includes(hidden), false);
  assert.match(rendered, /thinking_tokens/);
  assert.match(rendered, /estimated_tokens/);
});

test("streamed response cap is enforced when a server ignores Range", async () => {
  const response = new Response(Buffer.alloc(128 * 1024, 0x61), { status: 200 });
  const bounded = await contentModule.readResponseWithByteLimit(response, 4096);
  assert.equal(bounded.buffer.length, 4096);
  assert.equal(bounded.exceeded, true);
});

test("newline-aligned head and tail handling drops UTF-8 partial records", () => {
  const head = Buffer.from('{"head":"ok"}\n{"partial":"snowman ☃');
  const tail = Buffer.concat([
    Buffer.from([0x98, 0x83]),
    Buffer.from(' broken"}\n{"tail":"café"}\n')
  ]);
  const aligned = contentModule.newlineAlignedHeadTail(head, tail).toString("utf8");
  assert.equal(aligned, '{"head":"ok"}\n{"tail":"café"}\n');
  assert.equal(aligned.includes("�"), false);
});

function rangedFetch(data, options = {}) {
  const calls = [];
  const fetcher = async (_url, init = {}) => {
    const range = new Headers(init.headers).get("range") ?? "";
    calls.push(range);
    if (options.ignoreRange) {
      return new Response(data, {
        status: 200,
        headers: { "content-length": String(data.length), "content-type": "application/jsonl" }
      });
    }
    const match = /^bytes=(\d+)-(\d+)$/.exec(range);
    assert.ok(match, range);
    const start = Number(match[1]);
    const requestedEnd = Number(match[2]);
    const end = Math.min(requestedEnd, data.length - 1);
    const body = start < data.length ? data.subarray(start, end + 1) : Buffer.alloc(0);
    return new Response(body, {
      status: 206,
      headers: {
        "content-length": String(body.length),
        "content-type": "application/jsonl",
        "content-range": options.malformedContentRange ? `bytes ${start}-${end}/invalid` : `bytes ${start}-${end}/${data.length}`
      }
    });
  };
  return { fetcher, calls };
}

async function withMockFetch(fetcher, work) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = fetcher;
  try { return await work(); } finally { globalThis.fetch = originalFetch; }
}

test("live R2 reader prefers remote total for underreported size and tail offset", async () => {
  const data = Buffer.from(`${JSON.stringify({ type: "system", subtype: "init", model: "safe" })}\n${JSON.stringify({ type: "system", padding: "x".repeat(4096) })}\n${JSON.stringify({ type: "result", result: "done", usage: { input_tokens: 1, output_tokens: 1 } })}\n`);
  const mock = rangedFetch(data);
  const preview = await withMockFetch(mock.fetcher, () => contentModule.readArtifactForAnalysis({
    artifact_type: "agent_transcript", r2_uri: "r2://test-bucket/path/transcript.jsonl", size_bytes: 100
  }, { maxBytes: 1024 }));
  assert.equal(preview.remote_total_bytes, data.length);
  assert.equal(preview.stored_total_bytes, 100);
  assert.equal(preview.size_metadata_status, "stored_underreported");
  assert.equal(preview.completeness, "head_tail_only");
  assert.equal(mock.calls[1], `bytes=${data.length - 512}-${data.length - 1}`);
});

test("live R2 reader never calls overreported stored size complete", async () => {
  const data = Buffer.from(`${JSON.stringify({ type: "result", result: "done", usage: { input_tokens: 1, output_tokens: 1 } })}\n`);
  const sha = createHash("sha256").update(data).digest("hex");
  const mock = rangedFetch(data);
  const preview = await withMockFetch(mock.fetcher, () => contentModule.readArtifactForAnalysis({
    artifact_type: "agent_transcript", r2_uri: "r2://test-bucket/path/transcript.jsonl",
    size_bytes: data.length + 5000, sha256: sha
  }, { maxBytes: 1024 }));
  assert.equal(preview.remote_total_bytes, data.length);
  assert.equal(preview.size_metadata_status, "stored_overreported");
  assert.notEqual(preview.completeness, "complete");
  assert.equal(preview.analyzed_artifact_integrity_status, "verified");
});

test("live R2 reader treats malformed Content-Range as unverified and incomplete", async () => {
  const data = Buffer.from(`${JSON.stringify({ type: "result", result: "done" })}\n`);
  const mock = rangedFetch(data, { malformedContentRange: true });
  const preview = await withMockFetch(mock.fetcher, () => contentModule.readArtifactForAnalysis({
    artifact_type: "agent_transcript", r2_uri: "r2://test-bucket/path/transcript.jsonl", size_bytes: data.length
  }, { maxBytes: 1024 }));
  assert.equal(preview.remote_total_bytes, null);
  assert.equal(preview.size_metadata_status, "remote_unverified");
  assert.equal(preview.completeness, "truncated");
});

test("live R2 reader hard-caps an ignored Range response", async () => {
  const data = Buffer.from(`${JSON.stringify({ type: "system", subtype: "init" })}\n${"x".repeat(8192)}\n${JSON.stringify({ type: "result", result: "done" })}\n`);
  const mock = rangedFetch(data, { ignoreRange: true });
  const preview = await withMockFetch(mock.fetcher, () => contentModule.readArtifactForAnalysis({
    artifact_type: "agent_transcript", r2_uri: "r2://test-bucket/path/transcript.jsonl", size_bytes: data.length
  }, { maxBytes: 1024 }));
  assert.ok(preview.bytes_read <= 512);
  assert.equal(preview.completeness, "truncated");
  assert.equal(preview.remote_total_bytes, data.length);
});

test("live R2 head-tail reader drops UTF-8 and JSONL partial boundaries", async () => {
  const data = Buffer.from(`${JSON.stringify({ type: "system", subtype: "init", model: "café" })}\n${JSON.stringify({ type: "system", padding: `☃${"m".repeat(4096)}` })}\n${JSON.stringify({ type: "result", result: "done", usage: { input_tokens: 1, output_tokens: 1 } })}\n`);
  const mock = rangedFetch(data);
  const preview = await withMockFetch(mock.fetcher, () => contentModule.readArtifactForAnalysis({
    artifact_type: "agent_transcript", r2_uri: "r2://test-bucket/path/transcript.jsonl", size_bytes: data.length
  }, { maxBytes: 1025 }));
  assert.equal(preview.completeness, "head_tail_only");
  assert.equal(preview.text.includes("�"), false);
  assert.match(preview.text, /"type":"result"/);
});

test("complete 2 MiB transcript is retained under the default 8 MiB analysis cap", async () => {
  const relative = "full/claude-code.txt";
  await mkdir(join(testCache, "full"), { recursive: true });
  const padding = JSON.stringify({ type: "system", subtype: "metadata", padding: "x".repeat(2 * 1024 * 1024) });
  const result = JSON.stringify({ type: "result", result: "done", usage: { input_tokens: 1, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 1 } });
  const bytes = `${padding}\n${result}\n`;
  await writeFile(join(testCache, relative), bytes);
  const preview = await contentModule.readArtifactForAnalysis({ artifact_type: "agent_transcript", local_path: relative, size_bytes: Buffer.byteLength(bytes) });
  assert.equal(preview.completeness, "complete");
  assert.equal(preview.truncated, false);
  assert.match(preview.text, /"type":"result"/);
  assert.equal(preview.text.includes("x".repeat(1024)), false, "unapproved padding is not retained");
});

test("oversized JSONL uses newline-aligned head and tail and retains a tail result event", async () => {
  const relative = "oversized/claude-code.txt";
  await mkdir(join(testCache, "oversized"), { recursive: true });
  const head = JSON.stringify({ type: "system", subtype: "init", model: "test-model" });
  const middle = JSON.stringify({ type: "system", subtype: "metadata", marker: "middle-only", padding: "m".repeat(32 * 1024) });
  const tail = JSON.stringify({ type: "result", result: "", terminal_reason: "success", usage: { input_tokens: 0, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 0 } });
  const bytes = `${head}\n${middle}\n${tail}\n`;
  await writeFile(join(testCache, relative), bytes);
  const preview = await contentModule.readArtifactForAnalysis(
    { artifact_type: "agent_transcript", local_path: relative, size_bytes: Buffer.byteLength(bytes) },
    { maxBytes: 4096 }
  );
  assert.equal(preview.completeness, "head_tail_only");
  assert.ok(preview.bytes_read <= 4096);
  assert.match(preview.text, /"type":"result"/);
  assert.equal(preview.text.includes("middle-only"), false);
});

test("pretty trajectory parses whole, redacts reasoning recursively, and oversized structured JSON becomes incomplete", async () => {
  const relative = "trajectory/trajectory.json";
  await mkdir(join(testCache, "trajectory"), { recursive: true });
  const hidden = "never display this reasoning";
  const value = { steps: [{ id: "s1", action: "Bash", reasoning: hidden }], metadata: { token: "secret-token" } };
  const pretty = JSON.stringify(value, null, 2);
  await writeFile(join(testCache, relative), pretty);
  const complete = await contentModule.readArtifactForAnalysis({ artifact_type: "trajectory", local_path: relative, size_bytes: Buffer.byteLength(pretty) });
  assert.equal(complete.completeness, "complete");
  assert.equal(complete.text.includes(hidden), false);
  assert.equal(complete.text.includes("secret-token"), false);
  assert.equal(JSON.parse(complete.text).steps[0].action, "Bash");

  const oversized = await contentModule.readArtifactForAnalysis(
    { artifact_type: "trajectory", local_path: relative, size_bytes: Buffer.byteLength(pretty) },
    { maxBytes: 32 }
  );
  assert.equal(oversized.completeness, "truncated");
  assert.equal(oversized.available, false);
  assert.equal(oversized.text, null);
});

test("immutable raw download response bytes are not redacted or rewritten", async () => {
  const raw = Buffer.from('{"ANTHROPIC_AUTH_TOKEN":"raw-source-value","endpoint":"https://user:pass@example.test"}');
  const sha = createHash("sha256").update(raw).digest("hex");
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(raw, {
    status: 200,
    headers: {
      "content-length": String(raw.length),
      "x-amz-meta-size_bytes": String(raw.length),
      "x-amz-meta-sha256": sha
    }
  });
  try {
    const response = await contentModule.fetchArtifactDownload({
      artifact_type: "config",
      r2_uri: "r2://test-bucket/raw/config.json",
      size_bytes: raw.length,
      sha256: sha
    });
    assert.ok(response);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), raw);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("artifact provenance never treats an R2 URI alone as verified bytes", () => {
  const provenance = contentModule.buildArtifactProvenance(
    { r2_uri: "r2://test-bucket/path/result.json", size_bytes: 100, sha256: "a".repeat(64) },
    {
      available: false, source: "metadata", text: null, content_type: null,
      is_text: false, is_json: false, truncated: false, completeness: "unavailable",
      bytes_read: 0, total_bytes: 100, stored_total_bytes: 100,
      remote_total_bytes: null, size_metadata_status: "remote_unverified",
      analyzed_artifact_integrity_status: "unavailable", messages: [],
    },
    "2026-08-11T12:00:00Z",
  );
  assert.equal(provenance.retrievalStatus, "unavailable");
  assert.equal(provenance.integrityStatus, "unavailable");
  assert.equal(provenance.observedSizeBytes, null);
  assert.match(provenance.warningMessage, /not verified/);
});

test("artifact provenance distinguishes verified complete R2 bytes from bounded evidence", () => {
  const artifact = { r2_uri: "r2://test-bucket/path/result.json", size_bytes: 100, sha256: "b".repeat(64) };
  const base = {
    available: true, source: "r2", text: "{}", content_type: "application/json",
    is_text: true, is_json: true, truncated: false, bytes_read: 100,
    total_bytes: 100, stored_total_bytes: 100, remote_total_bytes: 100,
    size_metadata_status: "consistent", messages: [],
  };
  const verified = contentModule.buildArtifactProvenance(artifact, {
    ...base, completeness: "complete", analyzed_artifact_integrity_status: "verified",
  }, "2026-08-11T12:00:00Z");
  assert.equal(verified.retrievalStatus, "available");
  assert.equal(verified.completenessStatus, "complete");
  assert.equal(verified.integrityStatus, "verified");
  assert.equal(verified.warningMessage, null);

  const partial = contentModule.buildArtifactProvenance(artifact, {
    ...base, truncated: true, bytes_read: 50, completeness: "head_tail_only",
    analyzed_artifact_integrity_status: "not_checked_incomplete",
  }, "2026-08-11T12:00:00Z");
  assert.equal(partial.completenessStatus, "head_tail_only");
  assert.equal(partial.integrityStatus, "partial");
  assert.match(partial.warningMessage, /does not verify object bytes/);
});

test("local cache fallback is not represented as R2 integrity", () => {
  const provenance = contentModule.buildArtifactProvenance(
    { r2_uri: "r2://test-bucket/path/result.json", local_path: "path/result.json", size_bytes: 20 },
    {
      available: true, source: "local", text: "{}", content_type: "application/json",
      is_text: true, is_json: true, truncated: false, completeness: "complete",
      bytes_read: 20, total_bytes: 20, stored_total_bytes: 20,
      remote_total_bytes: null, size_metadata_status: "unknown",
      analyzed_artifact_integrity_status: "not_verifiable", messages: [],
    },
    "2026-08-11T12:00:00Z",
  );
  assert.equal(provenance.retrievalSource, "local_cache");
  assert.equal(provenance.retrievalStatus, "unavailable");
  assert.equal(provenance.integrityStatus, "unavailable");
  assert.equal(provenance.bytesRead, 20);
});
