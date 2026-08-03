import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "trial-analysis-core.ts"), "utf8");
const transpiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
}).outputText;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`;
const { classifyTrialEvidence, extractTrialFacts, parseTrajectory } = await import(moduleUrl);

const jsonl = (...records) => records.map((record) => JSON.stringify(record)).join("\n");
const zeroUsage = { input_tokens: 0, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 0 };

function artifact(artifactType, text, overrides = {}) {
  return {
    artifactType,
    artifactId: `${artifactType}-id`,
    text,
    available: true,
    truncated: false,
    malformed: false,
    completeness: "complete",
    ...overrides
  };
}

function trial(overrides = {}) {
  return {
    reward: 0,
    runtimeSeconds: 30,
    exceptionType: null,
    databaseInputTokens: 0,
    databaseCacheTokens: 0,
    databaseOutputTokens: 0,
    databaseCostUsd: null,
    routerObservability: "unknown",
    canonicalEvidenceComplete: true,
    artifacts: [
      artifact("result", "{}"),
      artifact("agent_transcript", jsonl({ type: "result", result: "", usage: zeroUsage })),
      artifact("trajectory", JSON.stringify({ steps: [] })),
      artifact("verifier_stdout", "1 failed")
    ],
    ...overrides
  };
}

function withCoreArtifacts(transcript, trajectory = { steps: [] }, verifier = "1 failed", extras = []) {
  return [
    artifact("result", "{}"),
    artifact("agent_transcript", transcript),
    artifact("trajectory", JSON.stringify(trajectory)),
    artifact("verifier_stdout", verifier),
    ...extras
  ];
}

test("Kimi substantive failure after the former 512 KiB prefix boundary is a high-confidence near miss", () => {
  const prefixPadding = { type: "system", subtype: "metadata", padding: "x".repeat(530 * 1024) };
  const transcript = jsonl(
    prefixPadding,
    { type: "assistant", message: { content: [
      { type: "text", text: "Implementing the requested source." },
      { type: "tool_use", name: "Write", input: { file_path: "/workspace/main.rs" } },
      { type: "tool_use", name: "Bash", input: { command: "rustc main.rs -o main" } }
    ] } },
    { type: "result", result: "Done", terminal_reason: "success", stop_reason: "end_turn", duration_api_ms: 340867,
      total_cost_usd: 0.355991,
      usage: { input_tokens: "3735", cache_read_input_tokens: "101632", cache_creation_input_tokens: "0", output_tokens: "11460" } }
  );
  assert.ok(Buffer.byteLength(transcript) > 512 * 1024);
  const result = classifyTrialEvidence(trial({
    reward: 0,
    runtimeSeconds: 401.445745,
    databaseInputTokens: 105367,
    databaseCacheTokens: 101632,
    databaseOutputTokens: 11460,
    databaseCostUsd: 0.355991,
    artifacts: withCoreArtifacts(
      transcript,
      { steps: [{ tool_name: "Write" }, { action: "Bash" }] },
      "AssertionError: directory contained ['cmain', 'main.rs', 'main']; expected only ['main.rs']\n1 failed"
    )
  }));
  assert.equal(result.raw_outcome, "failure");
  assert.equal(result.execution_validity, "substantive");
  assert.equal(result.activity_subtype, "substantive_agent_activity");
  assert.equal(result.failure_subtype, "extraneous_output_artifacts");
  assert.equal(result.policy_disposition, "none_detected");
  assert.equal(result.telemetry_status, "consistent");
  assert.equal(result.transcript_input_tokens, 105367);
  assert.equal(result.confidence, "high");
});

test("Kimi substantive success reconciles cached input and remains substantive", () => {
  const transcript = jsonl(
    { type: "assistant", message: { content: [{ type: "tool_use", name: "Bash", input: { command: "openssl version" } }] } },
    { type: "result", result: "Done", usage: { input_tokens: 15183, cache_read_input_tokens: 146432, cache_creation_input_tokens: 0, output_tokens: 1832 } }
  );
  const result = classifyTrialEvidence(trial({
    reward: 1,
    databaseInputTokens: 161615,
    databaseCacheTokens: 146432,
    databaseOutputTokens: 1832,
    artifacts: withCoreArtifacts(transcript, { steps: [{ tool: "Bash" }] }, "6 passed")
  }));
  assert.equal(result.raw_outcome, "success");
  assert.equal(result.activity_subtype, "substantive_agent_activity");
  assert.equal(result.failure_subtype, "none");
  assert.equal(result.telemetry_status, "consistent");
});

test("GPT synthetic retry with missing database fields is not called database zero", () => {
  const transcript = jsonl(
    { type: "user", message: { content: "[Your previous response had no visible output. Please continue and produce a user-visible response.]" } },
    { type: "result", result: "", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({
    databaseInputTokens: null, databaseCacheTokens: null, databaseOutputTokens: null,
    artifacts: withCoreArtifacts(transcript)
  }));
  assert.equal(result.activity_subtype, "synthetic_retry_empty_completion");
  assert.equal(result.execution_validity, "invalid_response_path");
  assert.equal(result.telemetry_status, "database_missing_transcript_present");
  assert.equal(result.synthetic_retry_count, 1);
});

test("Gemini long API-path empty completion uses API duration, not total runtime attribution", () => {
  const transcript = jsonl({ type: "result", result: "", duration_api_ms: 89542, stop_reason: null, usage: zeroUsage });
  const result = classifyTrialEvidence(trial({
    runtimeSeconds: 475.8,
    databaseInputTokens: null, databaseCacheTokens: null, databaseOutputTokens: null,
    artifacts: withCoreArtifacts(transcript)
  }));
  assert.equal(result.activity_subtype, "empty_completion_after_long_api_path_wait");
  assert.equal(result.execution_validity, "invalid_response_path");
  assert.equal(result.api_duration_ms, 89542);
  assert.equal(result.summary.includes("provider wait"), false);
});

test("Gemini thinking-only completion counts metadata without exposing reasoning", () => {
  const secretReasoning = "hidden reasoning must never survive";
  const transcript = jsonl(
    { type: "system", subtype: "thinking_tokens", estimated_tokens: 5, content: secretReasoning },
    { type: "result", result: "", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({ artifacts: withCoreArtifacts(transcript) }));
  assert.equal(result.activity_subtype, "thinking_only_empty_completion");
  assert.equal(result.execution_validity, "invalid_response_path");
  assert.equal(result.thinking_events, 1);
  assert.equal(JSON.stringify(result).includes(secretReasoning), false);
});

test("Fable refusal outranks empty completion and reports database-zero/transcript-nonzero", () => {
  const transcript = jsonl(
    { type: "system", subtype: "model_refusal_no_fallback", api_refusal_category: "cyber" },
    { type: "result", result: "API Error", terminal_reason: "api_error", api_error_status: "refusal",
      usage: { input_tokens: 2606, cache_read_input_tokens: 25611, cache_creation_input_tokens: 385, output_tokens: 2 } }
  );
  const result = classifyTrialEvidence(trial({
    exceptionType: "exception_info",
    artifacts: withCoreArtifacts(transcript, { steps: [] }, "2 failed", [artifact("exception", "model_refusal_no_fallback refusal_category cyber api_error")])
  }));
  assert.equal(result.activity_subtype, "provider_policy_refusal");
  assert.equal(result.execution_validity, "policy_blocked");
  assert.equal(result.policy_disposition, "provider_policy_refusal");
  assert.equal(result.failure_subtype, "policy_refusal");
  assert.equal(result.telemetry_status, "database_zero_transcript_nonzero");
  assert.equal(result.refusal_category, "cyber");
});

test("policy refusal after prior activity preserves both axes", () => {
  const transcript = jsonl(
    { type: "assistant", message: { content: [{ type: "tool_use", name: "Bash", input: { command: "ls" } }] } },
    { type: "system", subtype: "model_refusal_no_fallback", refusal_category: "cyber" },
    { type: "result", result: "API Error", terminal_reason: "api_error", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({ artifacts: withCoreArtifacts(transcript) }));
  assert.equal(result.activity_subtype, "substantive_agent_activity");
  assert.equal(result.substantive_activity_observed, true);
  assert.equal(result.execution_validity, "policy_blocked");
  assert.equal(result.policy_disposition, "provider_policy_refusal");
});

test("transport exception after tool activity remains an invalid transport/setup trial", () => {
  const transcript = jsonl(
    { type: "assistant", message: { content: [{ type: "tool_use", name: "Bash", input: { command: "ls" } }] } },
    { type: "result", result: "", terminal_reason: "api_error", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({
    exceptionType: "connection_error",
    artifacts: withCoreArtifacts(transcript, { steps: [{ tool: "Bash" }] }, "not executed", [artifact("exception", "transport_error connection_error")])
  }));
  assert.equal(result.activity_subtype, "setup_or_transport_exception");
  assert.equal(result.substantive_activity_observed, true);
  assert.equal(result.execution_validity, "invalid_transport_or_setup");
});

test("timeout after meaningful activity is distinct from setup failure", () => {
  const transcript = jsonl(
    { type: "assistant", message: { content: [{ type: "tool_use", name: "Edit", input: {} }] } },
    { type: "result", result: "", terminal_reason: "timeout", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({ exceptionType: "timeout", artifacts: withCoreArtifacts(transcript, { steps: [{ action: "Edit" }] }, "timeout", [artifact("exception", "timeout")]) }));
  assert.equal(result.activity_subtype, "timeout_after_meaningful_activity");
  assert.equal(result.execution_validity, "substantive");
  assert.equal(result.failure_subtype, "timeout");
});

test("timeout before observed activity is unknown rather than invented as setup or transport", () => {
  const transcript = jsonl({
    type: "result", result: "", terminal_reason: "timeout", duration_ms: 900_000, usage: zeroUsage
  });
  const analysis = classifyTrialEvidence(trial({
    exceptionType: "AgentTimeoutError",
    artifacts: withCoreArtifacts(transcript, { steps: [] }, "timeout", [artifact("exception", "timeout")])
  }));
  assert.equal(analysis.termination_subtype, "timeout");
  assert.equal(analysis.activity_subtype, "activity_unknown");
  assert.equal(analysis.execution_validity, "unknown");
  assert.equal(analysis.exception_trusted_markers.includes("timeout"), true);
});

test("reward-positive with complete no-activity evidence is questionable", () => {
  const result = classifyTrialEvidence(trial({ reward: 0.5 }));
  assert.equal(result.raw_outcome, "success");
  assert.equal(result.activity_subtype, "questionable_success_no_activity");
  assert.equal(result.execution_validity, "questionable");
});

test("null reward remains not recorded rather than becoming failure zero", () => {
  const result = classifyTrialEvidence(trial({ reward: null }));
  assert.equal(result.raw_outcome, "not_recorded");
  assert.equal(result.evidence.find((item) => item.label === "Database reward (raw source of truth)").value, "not recorded");
});

test("explicit zero and missing database telemetry remain distinct", () => {
  const explicit = classifyTrialEvidence(trial());
  const missing = classifyTrialEvidence(trial({ databaseInputTokens: null, databaseCacheTokens: null, databaseOutputTokens: null }));
  assert.equal(explicit.execution_validity, "invalid_response_path");
  assert.equal(explicit.telemetry_status, "zero_usage_empty_completion");
  assert.equal(missing.telemetry_status, "database_missing_transcript_present");
});

test("tail-only final result is positive evidence but cannot establish absence", () => {
  const result = classifyTrialEvidence(trial({
    artifacts: withCoreArtifacts(
      jsonl({ type: "result", result: "", usage: zeroUsage }),
      { steps: [] },
      "1 failed"
    ).map((item) => item.artifactType === "agent_transcript" ? { ...item, completeness: "head_tail_only", truncated: true } : item)
  }));
  assert.equal(result.final_result_empty, true);
  assert.equal(result.activity_subtype, "activity_unknown");
  assert.equal(result.confidence, "low");
});

test("oversized transcript without complete middle evidence cannot support a no-op claim", () => {
  const result = classifyTrialEvidence(trial({
    artifacts: trial().artifacts.map((item) => item.artifactType === "agent_transcript"
      ? { ...item, completeness: "truncated", truncated: true }
      : item)
  }));
  assert.equal(result.activity_subtype, "activity_unknown");
  assert.equal(result.telemetry_status, "incomplete_evidence");
});

test("pretty-printed trajectory parses as one document; metadata-only steps are not substantive", () => {
  const pretty = JSON.stringify({ steps: [{ message: { content: [{ type: "tool_use", name: "Bash" }] } }] }, null, 2);
  assert.deepEqual(parseTrajectory(pretty), { steps: 1, substantive: 1, malformed: false });
  assert.deepEqual(parseTrajectory(JSON.stringify({ steps: [{ step_id: "s1", timestamp: "now", uuid: "u", source: "adapter" }] })), { steps: 1, substantive: 0, malformed: false });
});

test("verifier evidence maps supported failure-detail subtypes independently", () => {
  const cases = [
    ["missing_required_output", "AssertionError: required file output.json was not found"],
    ["compile_failure", "error: could not compile requested crate"],
    ["test_assertion_failure", "FAILED tests/test_behavior.py::test_case - AssertionError"],
    ["unknown_failure", "output mismatch: expected 4, got 5"],
    ["verifier_or_environment_failure", "collection error: no tests ran because environment failed"]
  ];
  for (const [expected, verifier] of cases) {
    const result = classifyTrialEvidence(trial({ artifacts: withCoreArtifacts(jsonl({ type: "result", result: "", usage: zeroUsage }), { steps: [] }, verifier) }));
    assert.equal(result.failure_subtype, expected);
  }
});

test("Harbor result reward is independent evidence and never replaces database truth", () => {
  const result = classifyTrialEvidence(trial({
    reward: 0,
    artifacts: withCoreArtifacts(jsonl({ type: "result", result: "done", usage: zeroUsage })).map((item) =>
      item.artifactType === "result" ? artifact("result", JSON.stringify({ reward: 1, status: "completed" })) : item
    )
  }));
  assert.equal(result.raw_outcome, "failure");
  assert.equal(result.result_reward_present, true);
  assert.equal(result.result_reward_value, 1);
  assert.equal(result.database_result_consistency, "mismatch");
  assert.equal(result.manual_review_priority, "high");
});

test("result exception and termination fields are allow-listed without changing verifier failure subtype", () => {
  const result = classifyTrialEvidence(trial({
    reward: 1,
    artifacts: withCoreArtifacts(
      jsonl({ type: "assistant", message: { content: [{ type: "text", text: "done" }] } }, { type: "result", result: "done", usage: zeroUsage }),
      { steps: [{ action: "work" }] },
      "2 passed"
    ).map((item) => item.artifactType === "result" ? artifact("result", JSON.stringify({
      reward: 1, status: "completed_with_exception",
      exception_info: { type: "PostVerificationCleanupError" },
      termination_reason: "cleanup_exception",
      ignored_secret_field: "must-not-drive-classification"
    })) : item)
  }));
  assert.equal(result.raw_outcome, "success");
  assert.equal(result.failure_subtype, "none");
  assert.equal(result.termination_subtype, "unclassified_exception");
  assert.equal(result.result_exception_type, "PostVerificationCleanupError");
  assert.equal(result.exception_after_substantive_activity, true);
  assert.equal(result.manual_review_priority, "high");
});

test("generic exceptions are unclassified instead of being invented as setup or transport", () => {
  const active = classifyTrialEvidence(trial({
    exceptionType: "PostProcessingError",
    artifacts: withCoreArtifacts(
      jsonl({ type: "assistant", message: { content: [{ type: "tool_use", name: "Bash", input: { command: "ls" } }] } }, { type: "result", result: "done", usage: zeroUsage }),
      { steps: [{ tool: "Bash" }] }, "1 failed", [artifact("exception", "PostProcessingError")]
    )
  }));
  assert.equal(active.termination_subtype, "unclassified_exception");
  assert.equal(active.unclassified_exception, true);
  assert.equal(active.execution_validity, "substantive");
  assert.notEqual(active.activity_subtype, "setup_or_transport_exception");

  const inactive = classifyTrialEvidence(trial({
    exceptionType: "PostProcessingError",
    artifacts: withCoreArtifacts(jsonl({ type: "result", result: "", usage: zeroUsage }), { steps: [] }, "not run", [artifact("exception", "PostProcessingError")])
  }));
  assert.equal(inactive.activity_subtype, "activity_unknown");
  assert.equal(inactive.execution_validity, "unknown");
});

test("database exception summary alone can prove an explicit provider-policy refusal", () => {
  const result = classifyTrialEvidence(trial({
    exceptionType: null,
    databaseExceptionSummary: "model_refusal_no_fallback refusal_category=cyber",
  }));
  assert.equal(result.policy_disposition, "provider_policy_refusal");
  assert.equal(result.activity_subtype, "provider_policy_refusal");
  assert.equal(result.termination_subtype, "provider_policy_refusal");
  assert.deepEqual(result.database_exception_summary_trusted_markers, ["model_refusal_no_fallback"]);
  assert.equal(result.evidence.some((item) => item.source === "database_exception_summary"), true);
});

test("database exception summary alone can prove timeout without inventing setup or transport", () => {
  const result = classifyTrialEvidence(trial({
    exceptionType: null,
    databaseExceptionSummary: "AgentTimeoutError: timeout waiting for agent",
  }));
  assert.equal(result.termination_subtype, "timeout");
  assert.equal(result.activity_subtype, "activity_unknown");
  assert.equal(result.execution_validity, "unknown");
});

test("database exception summary trusted transport marker can establish setup or transport", () => {
  const result = classifyTrialEvidence(trial({
    exceptionType: null,
    databaseExceptionSummary: "api_connection_error during environment setup",
  }));
  assert.equal(result.termination_subtype, "setup_or_transport_exception");
  assert.equal(result.activity_subtype, "setup_or_transport_exception");
  assert.equal(result.execution_validity, "invalid_transport_or_setup");
  assert.deepEqual(result.database_exception_summary_trusted_markers, ["api_connection_error"]);
});

test("generic database exception summary remains unclassified and secret text is never retained", () => {
  const secret = "summary-secret-value";
  const result = classifyTrialEvidence(trial({
    exceptionType: null,
    databaseExceptionSummary: `Unexpected provider response client_secret=${secret}`,
  }));
  assert.equal(result.termination_subtype, "unclassified_exception");
  assert.equal(result.activity_subtype, "activity_unknown");
  assert.equal(result.unclassified_exception, true);
  assert.equal(JSON.stringify(result).includes(secret), false);
  assert.equal(result.database_exception_summary_present, true);
});

test("positive reward timeout keeps verifier failure and termination separate", () => {
  const result = classifyTrialEvidence(trial({
    reward: 1,
    exceptionType: "AgentTimeoutError",
    artifacts: withCoreArtifacts(
      jsonl({ type: "assistant", message: { content: [{ type: "tool_use", name: "Edit", input: {} }] } }, { type: "result", result: "done", terminal_reason: "timeout", usage: zeroUsage }),
      { steps: [{ action: "Edit" }] }, "2 passed", [artifact("exception", "timeout")]
    )
  }));
  assert.equal(result.failure_subtype, "none");
  assert.equal(result.termination_subtype, "timeout");
  assert.equal(result.manual_review_priority, "high");
});

test("structured CTRF failures support conservative assertion classification", () => {
  const ctrf = JSON.stringify({ results: { summary: { failed: 1, passed: 0 }, tests: [{ status: "failed", message: "expected 4, received 5" }] } });
  const result = classifyTrialEvidence(trial({
    artifacts: withCoreArtifacts(jsonl({ type: "result", result: "done", usage: zeroUsage }), { steps: [] }, "", [artifact("verifier_ctrf", ctrf)])
  }));
  assert.equal(result.failure_subtype, "test_assertion_failure");
});

test("duplicate artifact selection lowers confidence and completeness", () => {
  const result = classifyTrialEvidence(trial({ artifactSelectionAmbiguous: true }));
  assert.equal(result.evidence_complete, false);
  assert.equal(result.confidence, "low");
});

test("final aggregate usage outranks duplicate per-message usage and numeric strings normalize", () => {
  const transcript = jsonl(
    { type: "assistant", id: "m1", usage: { input_tokens: "10", cache_read_input_tokens: "5", cache_creation_input_tokens: "1", output_tokens: "2" }, message: { content: [{ type: "text", text: "done" }] } },
    { type: "assistant", id: "m1", usage: { input_tokens: "10", cache_read_input_tokens: "5", cache_creation_input_tokens: "1", output_tokens: "2" }, message: { content: [] } },
    { type: "result", result: "done", usage: { input_tokens: "10", cache_read_input_tokens: "5", cache_creation_input_tokens: "1", output_tokens: "2" } }
  );
  const facts = extractTrialFacts(trial({ databaseInputTokens: 16, databaseCacheTokens: 5, databaseOutputTokens: 2, artifacts: withCoreArtifacts(transcript) }));
  assert.equal(facts.usageRecords.length, 2);
  assert.equal(facts.transcriptUsage.uncachedInput.value, 10);
  assert.equal(classifyTrialEvidence(trial({ databaseInputTokens: 16, databaseCacheTokens: 5, databaseOutputTokens: 2, artifacts: withCoreArtifacts(transcript) })).telemetry_status, "consistent");
});

test("missing terminal aggregate makes per-message telemetry partial, while the last terminal aggregate wins", () => {
  const partialTranscript = jsonl(
    { type: "assistant", id: "m1", usage: { input_tokens: 5, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 1 }, message: { content: [{ type: "text", text: "work" }] } }
  );
  const partial = classifyTrialEvidence(trial({
    databaseInputTokens: 5, databaseCacheTokens: 0, databaseOutputTokens: 1,
    artifacts: withCoreArtifacts(partialTranscript, { steps: [{ action: "work" }] })
  }));
  assert.equal(partial.telemetry_status, "partial");

  const retried = jsonl(
    { type: "result", id: "first", result: "first", usage: { input_tokens: 2, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 1 } },
    { type: "result", id: "final", result: "final", usage: { input_tokens: 7, cache_read_input_tokens: 3, cache_creation_input_tokens: 1, output_tokens: 2 } }
  );
  const final = classifyTrialEvidence(trial({
    databaseInputTokens: 11, databaseCacheTokens: 3, databaseOutputTokens: 2,
    artifacts: withCoreArtifacts(retried)
  }));
  assert.equal(final.transcript_input_tokens, 11);
  assert.equal(final.telemetry_status, "consistent");
});

test("multiple model-usage entries inside one final result are combined once", () => {
  const transcript = jsonl({
    type: "result", id: "final", result: "done", modelUsage: {
      modelA: { input_tokens: 4, cache_read_input_tokens: 2, cache_creation_input_tokens: 0, output_tokens: 1 },
      modelB: { input_tokens: 3, cache_read_input_tokens: 1, cache_creation_input_tokens: 1, output_tokens: 2 }
    }
  });
  const result = classifyTrialEvidence(trial({
    databaseInputTokens: 11, databaseCacheTokens: 3, databaseOutputTokens: 3,
    artifacts: withCoreArtifacts(transcript)
  }));
  assert.equal(result.transcript_input_tokens, 11);
  assert.equal(result.telemetry_status, "consistent");
});

test("unavailable evidence yields unknown confidence and never a decisive empty classification", () => {
  const unavailable = ["result", "agent_transcript", "trajectory", "verifier_stdout"].map((artifactType) => artifact(artifactType, null, { available: false, completeness: "unavailable" }));
  const result = classifyTrialEvidence(trial({ artifacts: unavailable, canonicalEvidenceComplete: false }));
  assert.equal(result.activity_subtype, "activity_unknown");
  assert.equal(result.confidence, "unknown");
});

test("every derived fact identifies its database source or supporting artifact ID and type", () => {
  const result = classifyTrialEvidence(trial({
    databaseExceptionSummary: "generic exception",
    artifacts: withCoreArtifacts(
      jsonl(
        { type: "assistant", message: { content: [{ type: "tool_use", name: "Write", input: {} }] } },
        { type: "result", result: "done", usage: zeroUsage }
      ),
      { steps: [{ action: "Write" }] },
      "1 failed",
      [artifact("exception", "generic exception")]
    )
  }));
  assert.ok(result.evidence.length > 0);
  for (const fact of result.evidence) {
    assert.equal(typeof fact.source, "string", fact.label);
    assert.ok(fact.source.length > 0, fact.label);
    if (fact.artifactType) {
      assert.equal(fact.artifactId, `${fact.artifactType}-id`, fact.label);
      assert.equal(fact.source, `artifact:${fact.artifactType}`, fact.label);
    }
  }
  assert.equal(result.evidence.some((fact) => fact.source === "database_exception_summary"), true);
});

test("absent exception facts use inventory or derived-absence provenance without a phantom artifact", () => {
  const result = classifyTrialEvidence(trial());
  const exception = result.evidence.find((item) => item.label === "Exception artifact/result");
  const markers = result.evidence.find((item) => item.label === "All trusted exception markers");
  const termination = result.evidence.find((item) => item.label === "Termination / exception subtype");
  const refusal = result.evidence.find((item) => item.label === "Explicit refusal marker");
  assert.deepEqual(
    [exception?.source, exception?.artifactType, exception?.artifactId],
    ["result_and_artifact_inventory", undefined, undefined]
  );
  for (const item of [markers, termination, refusal]) {
    assert.equal(item?.source, "derived_absence");
    assert.equal(item?.artifactType, undefined);
    assert.equal(item?.artifactId, undefined);
  }
});

test("present exception artifact retains its exact artifact provenance", () => {
  const result = classifyTrialEvidence(trial({
    artifacts: withCoreArtifacts(
      jsonl({ type: "result", result: "", usage: zeroUsage }),
      { steps: [] },
      "not run",
      [artifact("exception", "PostProcessingError")]
    )
  }));
  const exception = result.evidence.find((item) => item.label === "Exception artifact/result");
  const termination = result.evidence.find((item) => item.label === "Termination / exception subtype");
  for (const item of [exception, termination]) {
    assert.equal(item?.source, "artifact:exception");
    assert.equal(item?.artifactType, "exception");
    assert.equal(item?.artifactId, "exception-id");
  }
});

test("result-only exception retains the result artifact ID and type", () => {
  const artifacts = withCoreArtifacts(jsonl({ type: "result", result: "done", usage: zeroUsage }))
    .map((item) => item.artifactType === "result"
      ? artifact("result", JSON.stringify({ exception_info: { type: "PostVerificationCleanupError" } }))
      : item);
  const result = classifyTrialEvidence(trial({ artifacts }));
  const exception = result.evidence.find((item) => item.label === "Exception artifact/result");
  const termination = result.evidence.find((item) => item.label === "Termination / exception subtype");
  for (const item of [exception, termination]) {
    assert.equal(item?.source, "artifact:result");
    assert.equal(item?.artifactType, "result");
    assert.equal(item?.artifactId, "result-id");
  }
});

test("database-summary-only refusal marker retains database provenance without an artifact ID", () => {
  const result = classifyTrialEvidence(trial({
    databaseExceptionSummary: "model_refusal_no_fallback refusal_category=cyber"
  }));
  const exception = result.evidence.find((item) => item.label === "Exception artifact/result");
  const termination = result.evidence.find((item) => item.label === "Termination / exception subtype");
  const refusal = result.evidence.find((item) => item.label === "Explicit refusal marker");
  assert.equal(exception?.source, "result_and_artifact_inventory");
  for (const item of [termination, refusal]) {
    assert.equal(item?.source, "database_exception_summary");
    assert.equal(item?.artifactType, undefined);
    assert.equal(item?.artifactId, undefined);
  }
});

test("transcript refusal marker retains transcript artifact provenance", () => {
  const transcript = jsonl(
    { type: "system", subtype: "model_refusal_no_fallback", refusal_category: "cyber" },
    { type: "result", result: "API Error", terminal_reason: "api_error", usage: zeroUsage }
  );
  const result = classifyTrialEvidence(trial({ artifacts: withCoreArtifacts(transcript) }));
  const termination = result.evidence.find((item) => item.label === "Termination / exception subtype");
  const refusal = result.evidence.find((item) => item.label === "Explicit refusal marker");
  for (const item of [termination, refusal]) {
    assert.equal(item?.source, "artifact:agent_transcript");
    assert.equal(item?.artifactType, "agent_transcript");
    assert.equal(item?.artifactId, "agent_transcript-id");
  }
});
