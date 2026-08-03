export const ANALYZER_VERSION = "artifact-evidence-v1.3.2";

export type ActivitySubtype =
  | "substantive_agent_activity"
  | "empty_completion_zero_usage"
  | "empty_completion_after_long_api_path_wait"
  | "thinking_only_empty_completion"
  | "synthetic_retry_empty_completion"
  | "provider_policy_refusal"
  | "setup_or_transport_exception"
  | "timeout_after_meaningful_activity"
  | "telemetry_missing_activity_present"
  | "questionable_success_no_activity"
  | "activity_unknown";

export type FailureSubtype =
  | "none"
  | "missing_required_output"
  | "compile_failure"
  | "test_assertion_failure"
  | "wrong_output"
  | "extraneous_output_artifacts"
  | "verifier_or_environment_failure"
  | "policy_refusal"
  | "timeout"
  | "unknown_failure";

export type TerminationSubtype =
  | "none"
  | "provider_policy_refusal"
  | "timeout"
  | "setup_or_transport_exception"
  | "unclassified_exception";

export type DatabaseResultConsistency =
  | "consistent"
  | "mismatch"
  | "database_missing_result_present"
  | "result_missing_database_present"
  | "not_recorded"
  | "incomplete_evidence";

export type RawOutcome = "success" | "failure" | "not_recorded";
export type ExecutionValidity =
  | "substantive"
  | "invalid_response_path"
  | "invalid_transport_or_setup"
  | "policy_blocked"
  | "questionable"
  | "unknown";
export type PolicyDisposition = "none_detected" | "provider_policy_refusal" | "unknown";
export type TelemetryStatus =
  | "consistent"
  | "database_missing_transcript_present"
  | "database_zero_transcript_nonzero"
  | "nonzero_mismatch"
  | "zero_usage_empty_completion"
  | "partial"
  | "incomplete_evidence"
  | "unknown";
export type RouterObservability = "retained" | "not_retained" | "unknown";
export type AnalysisConfidence = "high" | "medium" | "low" | "unknown";
export type ArtifactReadCompleteness = "complete" | "head_tail_only" | "truncated" | "unavailable" | "malformed";

export type ArtifactTextInput = {
  artifactType: string;
  artifactId?: string;
  text: string | null;
  available: boolean;
  truncated?: boolean;
  malformed?: boolean;
  completeness?: ArtifactReadCompleteness;
  bytesRead?: number;
  totalBytes?: number | null;
};

export type TrialAnalysisInput = {
  reward: number | string | null;
  runtimeSeconds: number | string | null;
  exceptionType: string | null;
  databaseExceptionSummary?: string | null;
  databaseInputTokens: number | string | null;
  databaseCacheTokens: number | string | null;
  databaseOutputTokens: number | string | null;
  databaseCostUsd?: number | string | null;
  artifacts: ArtifactTextInput[];
  routerObservability?: RouterObservability;
  canonicalEvidenceComplete?: boolean;
  artifactSelectionAmbiguous?: boolean;
};

export type AnalysisEvidence = {
  label: string;
  value: string;
  source: string;
  artifactType?: string;
  artifactId?: string;
};

export type ConfigurationSummary = {
  task_repository: string | null;
  task_commit: string | null;
  task_checksum: string | null;
  task_path: string | null;
  model_alias: string | null;
  resolved_model: string | null;
  claude_code_version: string | null;
  router_endpoint: string | null;
  timeout_multipliers: string | null;
  disallowed_tools: string | null;
  verifier_configuration: string | null;
};

type NumericFact = { present: boolean; value: number | null };

export type UsageRecord = {
  uncachedInput: NumericFact;
  cacheReadInput: NumericFact;
  cacheCreationInput: NumericFact;
  output: NumericFact;
  cost: NumericFact;
  identifier: string | null;
  mode: "final_aggregate" | "cumulative" | "per_message";
};

export type TrialFacts = {
  reward: NumericFact;
  resultReward: NumericFact;
  databaseResultConsistency: DatabaseResultConsistency;
  runtimeSeconds: NumericFact;
  exceptionPresent: boolean;
  databaseExceptionType: string | null;
  databaseExceptionSummaryPresent: boolean;
  databaseExceptionSummaryTrustedMarkers: string[];
  databaseExceptionSummaryRefusalMarker: boolean;
  databaseExceptionTypeTrustedMarkers: string[];
  databaseExceptionTypeRefusalMarker: boolean;
  exceptionType: string | null;
  exceptionArtifactPresent: boolean;
  exceptionArtifactTrustedMarkers: string[];
  exceptionArtifactRefusalMarker: boolean;
  resultArtifactPresent: boolean;
  resultExceptionPresent: boolean;
  resultExceptionType: string | null;
  resultTerminationReason: string | null;
  resultStatus: string | null;
  resultTrustedMarkers: string[];
  resultRefusalMarker: boolean;
  exceptionTrustedMarkers: string[];
  unclassifiedException: boolean;
  exceptionAfterSubstantiveActivity: boolean;
  visibleAssistantEvents: number;
  thinkingEvents: number;
  toolCalls: number;
  workspaceChangingCalls: number;
  trajectorySteps: number;
  substantiveTrajectorySteps: number;
  substantiveActivityObserved: boolean;
  finalResultPresent: boolean;
  finalResultEmpty: boolean | null;
  terminalReason: string | null;
  stopReason: string | null;
  apiErrorStatus: string | null;
  apiDurationMs: number | null;
  syntheticRetryCount: number;
  transcriptExplicitRefusal: boolean;
  explicitRefusal: boolean;
  refusalCategory: string | null;
  timeout: boolean;
  transportOrSetupException: boolean;
  verifierExecutionStatus: "passed" | "failed" | "error" | "unknown";
  verifierFailureHeadline: string | null;
  failureSubtype: FailureSubtype;
  usageRecords: UsageRecord[];
  transcriptUsage: UsageRecord | null;
  databaseInput: NumericFact;
  databaseCache: NumericFact;
  databaseOutput: NumericFact;
  databaseCost: NumericFact;
  transcriptCompleteness: ArtifactReadCompleteness;
  trajectoryCompleteness: ArtifactReadCompleteness;
  resultCompleteness: ArtifactReadCompleteness;
  verifierCompleteness: ArtifactReadCompleteness;
  absenceSensitiveEvidenceComplete: boolean;
  evidenceComplete: boolean;
  artifactSelectionAmbiguous: boolean;
  malformedTranscriptLines: number;
  configuration: ConfigurationSummary;
};

export type TrialAnalysis = {
  analyzer_version: string;
  raw_outcome: RawOutcome;
  execution_validity: ExecutionValidity;
  policy_disposition: PolicyDisposition;
  activity_subtype: ActivitySubtype;
  failure_subtype: FailureSubtype;
  termination_subtype: TerminationSubtype;
  unclassified_exception: boolean;
  exception_after_substantive_activity: boolean;
  result_reward_present: boolean;
  result_reward_value: number | null;
  result_exception_present: boolean;
  result_exception_type: string | null;
  result_termination_reason: string | null;
  result_status: string | null;
  database_result_consistency: DatabaseResultConsistency;
  exception_trusted_markers: string[];
  database_exception_summary_present: boolean;
  database_exception_summary_trusted_markers: string[];
  telemetry_status: TelemetryStatus;
  router_observability: RouterObservability;
  confidence: AnalysisConfidence;
  evidence_complete: boolean;
  manual_review_required: boolean;
  manual_review_priority: "high" | "medium" | "low";
  summary: string;
  visible_assistant_events: number;
  thinking_events: number;
  tool_calls: number;
  workspace_changing_calls: number;
  trajectory_steps: number;
  substantive_trajectory_steps: number;
  substantive_activity_observed: boolean;
  synthetic_retry_count: number;
  explicit_refusal: boolean;
  refusal_category: string | null;
  terminal_reason: string | null;
  stop_reason: string | null;
  api_error_status: string | null;
  api_duration_ms: number | null;
  transcript_input_tokens: number | null;
  transcript_uncached_input_tokens: number | null;
  transcript_cache_read_input_tokens: number | null;
  transcript_cache_creation_input_tokens: number | null;
  transcript_output_tokens: number | null;
  transcript_cost_usd: number | null;
  final_result_empty: boolean | null;
  verifier_failure_headline: string | null;
  evidence: AnalysisEvidence[];
  configuration: ConfigurationSummary;
};

type TranscriptFacts = {
  visibleAssistantEvents: number;
  thinkingEvents: number;
  toolCalls: number;
  workspaceChangingCalls: number;
  syntheticRetryCount: number;
  explicitRefusal: boolean;
  refusalCategory: string | null;
  terminalReason: string | null;
  stopReason: string | null;
  apiErrorStatus: string | null;
  finalResultPresent: boolean;
  finalResultEmpty: boolean | null;
  apiDurationMs: number | null;
  model: string | null;
  claudeCodeVersion: string | null;
  malformedLines: number;
  usageRecords: UsageRecord[];
};

type ResultFacts = {
  reward: NumericFact;
  exceptionPresent: boolean;
  exceptionType: string | null;
  terminationReason: string | null;
  status: string | null;
};

const syntheticRetryMarker = "Your previous response had no visible output";
const refusalMarkers = ["model_refusal_no_fallback", "api_refusal_category", "refusal_category", "provider_policy_refusal"];
const workspaceToolNames = new Set(["Write", "Edit", "NotebookEdit", "MultiEdit", "apply_patch"]);
const metadataOnlyTrajectoryKeys = new Set(["id", "step_id", "timestamp", "created_at", "updated_at", "uuid", "source", "index", "sequence", "type", "subtype"]);

function hasOwn(value: object, key: string) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function numericFact(value: unknown, present = value !== null && value !== undefined && value !== ""): NumericFact {
  if (!present) return { present: false, value: null };
  const parsed = Number(value);
  return { present: true, value: Number.isFinite(parsed) ? parsed : null };
}

function numberOrNull(value: unknown): number | null {
  return numericFact(value).value;
}

function nonEmptyText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function safeEndpoint(value: unknown): string | null {
  const text = nonEmptyText(value);
  if (!text) return null;
  try {
    const url = new URL(text);
    if (url.username) url.username = "";
    if (url.password) url.password = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/signature|token|auth|credential|secret|password|api.?key|x-amz-/i.test(key)) {
        url.searchParams.set(key, "[redacted]");
      }
    }
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return /token|key|secret|credential|password|@/i.test(text) ? "recorded endpoint (redacted)" : text;
  }
}

function isHiddenReasoningNode(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const node = value as Record<string, unknown>;
  const type = String(node.type ?? "").toLowerCase();
  const subtype = String(node.subtype ?? "").toLowerCase();
  return type.includes("thinking") || type.includes("reasoning") || subtype.includes("thinking") || subtype.includes("reasoning");
}

function isWorkspaceChangingTool(name: string, input: unknown): boolean {
  if (workspaceToolNames.has(name)) return true;
  if (input && typeof input === "object" && (input as Record<string, unknown>).workspace_changing === true) return true;
  if (name !== "Bash" || !input || typeof input !== "object") return false;
  const command = String((input as Record<string, unknown>).command ?? "");
  return /(^|[;&|]\s*)(touch|mkdir|cp|mv|rm|install|patch|git\s+apply)\b|(^|\s)(sed\s+-i|tee\b)|>{1,2}\s*[^&]/m.test(command);
}

function usageRecord(value: unknown, mode: UsageRecord["mode"], identifier: string | null): UsageRecord | null {
  if (!value || typeof value !== "object") return null;
  const usage = value as Record<string, unknown>;
  const uncached = hasOwn(usage, "input_tokens")
    ? numericFact(usage.input_tokens, true)
    : numericFact(usage.uncached_input_tokens, hasOwn(usage, "uncached_input_tokens"));
  const cacheRead = numericFact(usage.cache_read_input_tokens, hasOwn(usage, "cache_read_input_tokens"));
  const cacheCreation = numericFact(usage.cache_creation_input_tokens, hasOwn(usage, "cache_creation_input_tokens"));
  const output = numericFact(usage.output_tokens, hasOwn(usage, "output_tokens"));
  const cost = numericFact(usage.cost_usd ?? usage.total_cost_usd, hasOwn(usage, "cost_usd") || hasOwn(usage, "total_cost_usd"));
  if (![uncached, cacheRead, cacheCreation, output, cost].some((fact) => fact.present)) return null;
  return { uncachedInput: uncached, cacheReadInput: cacheRead, cacheCreationInput: cacheCreation, output, cost, identifier, mode };
}

function usageSignature(record: UsageRecord) {
  return JSON.stringify([
    record.identifier,
    record.mode,
    record.uncachedInput,
    record.cacheReadInput,
    record.cacheCreationInput,
    record.output,
    record.cost
  ]);
}

function transcriptRecords(text: string): { records: unknown[]; malformedLines: number } {
  const records: unknown[] = [];
  let malformedLines = 0;
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try {
      records.push(JSON.parse(line));
    } catch {
      malformedLines += 1;
    }
  }
  return { records, malformedLines };
}

function recordRefusal(record: Record<string, any>) {
  const raw = JSON.stringify({
    type: record.type,
    subtype: record.subtype,
    terminal_reason: record.terminal_reason,
    api_error_status: record.api_error_status,
    api_refusal_category: record.api_refusal_category,
    refusal_category: record.refusal_category,
    error: record.error
  });
  return refusalMarkers.some((marker) => raw.includes(marker));
}

export function parseTranscript(text: string | null): TranscriptFacts {
  const facts: TranscriptFacts = {
    visibleAssistantEvents: 0,
    thinkingEvents: 0,
    toolCalls: 0,
    workspaceChangingCalls: 0,
    syntheticRetryCount: 0,
    explicitRefusal: false,
    refusalCategory: null,
    terminalReason: null,
    stopReason: null,
    apiErrorStatus: null,
    finalResultPresent: false,
    finalResultEmpty: null,
    apiDurationMs: null,
    model: null,
    claudeCodeVersion: null,
    malformedLines: 0,
    usageRecords: []
  };
  if (!text) return facts;

  facts.syntheticRetryCount = text.split(syntheticRetryMarker).length - 1;
  const parsed = transcriptRecords(text);
  facts.malformedLines = parsed.malformedLines;
  const seenUsage = new Set<string>();

  const addUsage = (record: UsageRecord | null) => {
    if (!record) return;
    const signature = usageSignature(record);
    if (seenUsage.has(signature)) return;
    seenUsage.add(signature);
    facts.usageRecords.push(record);
  };

  for (const raw of parsed.records) {
    if (!raw || typeof raw !== "object") continue;
    const record = raw as Record<string, any>;
    if (recordRefusal(record)) facts.explicitRefusal = true;
    facts.refusalCategory = nonEmptyText(record.api_refusal_category ?? record.refusal_category) ?? facts.refusalCategory;

    if (record.type === "system" && record.subtype === "thinking_tokens") {
      facts.thinkingEvents += 1;
      continue;
    }
    if (record.type === "system" && record.subtype === "init") {
      facts.model = nonEmptyText(record.model) ?? facts.model;
      facts.claudeCodeVersion = nonEmptyText(record.claude_code_version ?? record.claudeCodeVersion) ?? facts.claudeCodeVersion;
    }

    if (record.type === "assistant") {
      const content = record.message?.content ?? record.content;
      if (Array.isArray(content)) {
        let hasVisibleText = false;
        for (const item of content) {
          if (!item || typeof item !== "object") continue;
          if (isHiddenReasoningNode(item)) {
            facts.thinkingEvents += 1;
            continue;
          }
          if (item.type === "text" && nonEmptyText(item.text) && !String(item.text).startsWith("API Error:")) hasVisibleText = true;
          if (item.type === "tool_use") {
            facts.toolCalls += 1;
            if (isWorkspaceChangingTool(String(item.name ?? ""), item.input)) facts.workspaceChangingCalls += 1;
          }
        }
        if (hasVisibleText) facts.visibleAssistantEvents += 1;
      } else if (nonEmptyText(content) && !String(content).startsWith("API Error:")) {
        facts.visibleAssistantEvents += 1;
      }
      facts.stopReason = nonEmptyText(record.message?.stop_reason ?? record.stop_reason) ?? facts.stopReason;
      const usageMode = record.usage_mode === "cumulative" || record.usage_is_cumulative === true
        ? "cumulative" : "per_message";
      addUsage(usageRecord(record.message?.usage ?? record.usage, usageMode, nonEmptyText(record.message?.id ?? record.id)));
    }

    if (record.type === "result") {
      facts.finalResultPresent = true;
      facts.terminalReason = nonEmptyText(record.terminal_reason) ?? facts.terminalReason;
      facts.stopReason = nonEmptyText(record.stop_reason) ?? facts.stopReason;
      facts.apiErrorStatus = nonEmptyText(record.api_error_status ?? record.status) ?? facts.apiErrorStatus;
      facts.apiDurationMs = numberOrNull(record.duration_api_ms) ?? facts.apiDurationMs;
      if (hasOwn(record, "result")) facts.finalResultEmpty = !nonEmptyText(record.result);
      addUsage(usageRecord(record.usage, "final_aggregate", nonEmptyText(record.id ?? record.request_id)));
      if (!record.usage && record.modelUsage && typeof record.modelUsage === "object") {
        const modelRecords: UsageRecord[] = [];
        for (const [modelId, modelUsage] of Object.entries(record.modelUsage as Record<string, unknown>)) {
          const modelRecord = usageRecord(modelUsage, "final_aggregate", modelId);
          if (modelRecord) modelRecords.push(modelRecord);
        }
        addUsage(mergeUsageRecords(modelRecords, nonEmptyText(record.id ?? record.request_id) ?? "modelUsage"));
      }
      const resultCost = numericFact(record.total_cost_usd, hasOwn(record, "total_cost_usd"));
      if (resultCost.present && facts.usageRecords.length > 0) {
        const last = facts.usageRecords.at(-1)!;
        if (!last.cost.present) last.cost = resultCost;
      }
    }
  }
  return facts;
}

function factSum(...facts: NumericFact[]): NumericFact {
  const present = facts.some((fact) => fact.present);
  if (!present) return { present: false, value: null };
  if (facts.some((fact) => fact.present && fact.value === null)) return { present: true, value: null };
  return { present: true, value: facts.reduce((sum, fact) => sum + (fact.value ?? 0), 0) };
}

function mergeUsageRecords(records: UsageRecord[], identifier: string): UsageRecord | null {
  if (records.length === 0) return null;
  return {
    uncachedInput: factSum(...records.map((record) => record.uncachedInput)),
    cacheReadInput: factSum(...records.map((record) => record.cacheReadInput)),
    cacheCreationInput: factSum(...records.map((record) => record.cacheCreationInput)),
    output: factSum(...records.map((record) => record.output)),
    cost: factSum(...records.map((record) => record.cost)),
    identifier,
    mode: "final_aggregate"
  };
}

function combineUsageRecords(records: UsageRecord[]): UsageRecord | null {
  if (records.length === 0) return null;
  const finalRecords = records.filter((record) => record.mode === "final_aggregate");
  if (finalRecords.length) return finalRecords.at(-1)!;
  const cumulative = records.filter((record) => record.mode === "cumulative");
  if (cumulative.length) {
    return cumulative.reduce((best, current) => {
      const bestTotal = usageTotal(best) ?? -1;
      const currentTotal = usageTotal(current) ?? -1;
      return currentTotal >= bestTotal ? current : best;
    });
  }
  return {
    uncachedInput: factSum(...records.map((record) => record.uncachedInput)),
    cacheReadInput: factSum(...records.map((record) => record.cacheReadInput)),
    cacheCreationInput: factSum(...records.map((record) => record.cacheCreationInput)),
    output: factSum(...records.map((record) => record.output)),
    cost: factSum(...records.map((record) => record.cost)),
    identifier: null,
    mode: "per_message"
  };
}

function usageInputTotal(record: UsageRecord | null): NumericFact {
  if (!record) return { present: false, value: null };
  return factSum(record.uncachedInput, record.cacheReadInput, record.cacheCreationInput);
}

function usageTotal(record: UsageRecord | null): number | null {
  if (!record) return null;
  const values = [usageInputTotal(record), record.output];
  if (!values.some((fact) => fact.present)) return null;
  if (values.some((fact) => fact.present && fact.value === null)) return null;
  return values.reduce((sum, fact) => sum + (fact.value ?? 0), 0);
}

function explicitTrajectoryActivity(step: unknown): boolean {
  if (!step || typeof step !== "object" || isHiddenReasoningNode(step)) return false;
  const node = step as Record<string, any>;
  const content = node.message?.content ?? node.content;
  if (Array.isArray(content)) {
    return content.some((item) => item && typeof item === "object" && !isHiddenReasoningNode(item)
      && ((item.type === "text" && Boolean(nonEmptyText(item.text))) || item.type === "tool_use"));
  }
  if (nonEmptyText(content)) return true;
  if (nonEmptyText(node.tool ?? node.tool_name ?? node.action ?? node.command)) return true;
  if (node.tool_use && typeof node.tool_use === "object") return true;
  return Object.entries(node).some(([key, value]) => {
    if (metadataOnlyTrajectoryKeys.has(key) || /thinking|reasoning/i.test(key)) return false;
    if (!/assistant|tool|action|command|observation|response/i.test(key)) return false;
    return typeof value === "string" ? Boolean(nonEmptyText(value)) : Array.isArray(value) ? value.length > 0 : Boolean(value && typeof value === "object");
  });
}

export function parseTrajectory(text: string | null) {
  if (!text) return { steps: 0, substantive: 0, malformed: false };
  try {
    const value = JSON.parse(text) as Record<string, unknown>;
    const candidates = Array.isArray(value) ? value
      : Array.isArray(value.trajectory) ? value.trajectory
        : Array.isArray(value.steps) ? value.steps
          : Array.isArray(value.messages) ? value.messages
            : [];
    return {
      steps: candidates.length,
      substantive: candidates.filter(explicitTrajectoryActivity).length,
      malformed: false
    };
  } catch {
    return { steps: 0, substantive: 0, malformed: true };
  }
}

function parseConfig(text: string | null): ConfigurationSummary {
  const empty: ConfigurationSummary = {
    task_repository: null, task_commit: null, task_checksum: null, task_path: null,
    model_alias: null, resolved_model: null, claude_code_version: null, router_endpoint: null,
    timeout_multipliers: null, disallowed_tools: null, verifier_configuration: null
  };
  if (!text) return empty;
  try {
    const config = JSON.parse(text) as Record<string, any>;
    const timeouts = ["timeout_multiplier", "agent_timeout_multiplier", "verifier_timeout_multiplier", "agent_setup_timeout_multiplier", "environment_build_timeout_multiplier"]
      .filter((key) => config[key] !== null && config[key] !== undefined)
      .map((key) => `${key}=${config[key]}`);
    const disallowed = config.agent?.kwargs?.disallowed_tools;
    return {
      task_repository: nonEmptyText(config.task?.git_url ?? config.task?.repository),
      task_commit: nonEmptyText(config.task?.git_commit_id ?? config.task?.commit),
      task_checksum: nonEmptyText(config.task?.checksum ?? config.task?.sha256),
      task_path: nonEmptyText(config.task?.path),
      model_alias: nonEmptyText(config.agent?.model_name ?? config.agent?.env?.ANTHROPIC_MODEL),
      resolved_model: nonEmptyText(config.agent?.resolved_model ?? config.resolved_model),
      claude_code_version: nonEmptyText(config.agent?.version ?? config.claude_code_version),
      router_endpoint: safeEndpoint(config.agent?.env?.ANTHROPIC_BASE_URL ?? config.router_endpoint),
      timeout_multipliers: timeouts.length ? timeouts.join(" · ") : null,
      disallowed_tools: Array.isArray(disallowed) ? disallowed.join(", ") : nonEmptyText(disallowed),
      verifier_configuration: config.verifier
        ? `${config.verifier.disable ? "disabled" : "enabled"}${config.verifier.override_timeout_sec ? ` · timeout=${config.verifier.override_timeout_sec}s` : ""}`
        : null
    };
  } catch {
    return empty;
  }
}

function objectAt(value: unknown, ...path: string[]): Record<string, unknown> | null {
  let current: unknown = value;
  for (const key of path) {
    if (!current || typeof current !== "object" || Array.isArray(current)) return null;
    current = (current as Record<string, unknown>)[key];
  }
  return current && typeof current === "object" && !Array.isArray(current)
    ? current as Record<string, unknown> : null;
}

function firstText(...values: unknown[]): string | null {
  for (const value of values) {
    const text = nonEmptyText(value);
    if (text) return text;
  }
  return null;
}

/** Parse only documented, diagnosis-safe Harbor result fields. */
export function parseResultArtifact(text: string | null): ResultFacts {
  const empty: ResultFacts = {
    reward: { present: false, value: null },
    exceptionPresent: false,
    exceptionType: null,
    terminationReason: null,
    status: null
  };
  if (!text) return empty;
  try {
    const value = JSON.parse(text) as unknown;
    if (!value || typeof value !== "object" || Array.isArray(value)) return empty;
    const root = value as Record<string, unknown>;
    const verifier = objectAt(root, "verifier_result") ?? objectAt(root, "verifierResult");
    const rewards = verifier ? objectAt(verifier, "rewards") : null;
    const agent = objectAt(root, "agent_result") ?? objectAt(root, "agentResult");
    const exception = objectAt(root, "exception_info") ?? objectAt(root, "exceptionInfo")
      ?? objectAt(root, "exception");
    const rewardCandidates: Array<[boolean, unknown]> = [
      [hasOwn(root, "reward"), root.reward],
      [Boolean(verifier && hasOwn(verifier, "reward")), verifier?.reward],
      [Boolean(verifier && hasOwn(verifier, "score")), verifier?.score],
      [Boolean(rewards && hasOwn(rewards, "reward")), rewards?.reward]
    ];
    const rewardCandidate = rewardCandidates.find(([present]) => present);
    const exceptionType = firstText(
      root.exception_type, root.exceptionType,
      exception?.exception_type, exception?.exceptionType, exception?.type,
      agent?.exception_type, agent?.exceptionType
    );
    const terminationReason = firstText(
      root.terminal_reason, root.termination_reason,
      agent?.terminal_reason, agent?.termination_reason,
      exception?.terminal_reason, exception?.termination_reason
    );
    const status = firstText(root.status, agent?.status, verifier?.status);
    return {
      reward: rewardCandidate ? numericFact(rewardCandidate[1], true) : { present: false, value: null },
      exceptionPresent: Boolean(exceptionType || exception || root.exception === true),
      exceptionType,
      terminationReason,
      status
    };
  } catch {
    return empty;
  }
}

function resultConsistency(database: NumericFact, result: NumericFact, completeness: ArtifactReadCompleteness): DatabaseResultConsistency {
  if (completeness !== "complete") return "incomplete_evidence";
  if (!database.present && !result.present) return "not_recorded";
  if (!database.present && result.present) return "database_missing_result_present";
  if (database.present && !result.present) return "result_missing_database_present";
  if (database.value === null || result.value === null) return "mismatch";
  return Math.abs(database.value - result.value) <= 1e-12 ? "consistent" : "mismatch";
}

function ctrfEvidence(text: string | null): { status: TrialFacts["verifierExecutionStatus"]; diagnostic: string | null } {
  if (!text) return { status: "unknown", diagnostic: null };
  try {
    const value = JSON.parse(text) as Record<string, any>;
    const results = value.results && typeof value.results === "object" ? value.results : value;
    const summary = results.summary && typeof results.summary === "object" ? results.summary : {};
    const tests = Array.isArray(results.tests) ? results.tests : Array.isArray(value.tests) ? value.tests : [];
    const failed = numberOrNull(summary.failed) ?? tests.filter((item: any) => /fail|error/i.test(String(item?.status ?? ""))).length;
    const passed = numberOrNull(summary.passed) ?? tests.filter((item: any) => /pass/i.test(String(item?.status ?? ""))).length;
    const status: TrialFacts["verifierExecutionStatus"] = failed > 0 ? "failed" : passed > 0 ? "passed" : "unknown";
    const failure = tests.find((item: any) => /fail|error/i.test(String(item?.status ?? "")));
    const diagnostic = failure && typeof failure === "object"
      ? firstText(failure.message, failure.trace, failure.failure?.message, failure.failure?.trace)?.slice(0, 2000) ?? null
      : null;
    return { status, diagnostic };
  } catch {
    return { status: "unknown", diagnostic: null };
  }
}

function verifierHeadline(text: string | null): string | null {
  if (!text) return null;
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return lines.find((line) => /FAILED|ERROR|AssertionError|expected|passed|failed|missing|not found/i.test(line))?.slice(0, 240) ?? null;
}

function classifyVerifier(text: string | null, ctrfText: string | null, rawOutcome: RawOutcome, refusal: boolean, timeout: boolean): FailureSubtype {
  if (rawOutcome === "success") return "none";
  if (refusal) return "policy_refusal";
  if (timeout) return "timeout";
  const ctrf = ctrfEvidence(ctrfText);
  const combined = [text, ctrf.diagnostic].filter(Boolean).join("\n");
  if (!combined) return "unknown_failure";
  if (/expected\s+only[\s\S]{0,240}(?:found|contained)|(?:found|contained)[\s\S]{0,240}expected\s+only|unexpected\s+(?:files?|artifacts?)|extra(?:neous)?\s+(?:files?|artifacts?)/i.test(combined)) return "extraneous_output_artifacts";
  if (/missing required|required .{0,80}(?:missing|not found|does not exist)|no such file|expected .{0,80} to exist/i.test(combined)) return "missing_required_output";
  if (/(?:^|\n)(?:error(?:\[[A-Z0-9]+\])?:|fatal error:).{0,240}|could not compile|compilation terminated|linker command failed/i.test(combined)) return "compile_failure";
  if (/no tests ran|collection error|failed to (?:start|create)|environment failure|docker daemon|verifier (?:error|failed)/i.test(combined)) return "verifier_or_environment_failure";
  if (/AssertionError|assert(?:ion)? failed|\bFAILED\b/i.test(combined) || ctrf.status === "failed") return "test_assertion_failure";
  return "unknown_failure";
}

function readCompleteness(artifact: ArtifactTextInput | undefined): ArtifactReadCompleteness {
  if (!artifact?.available) return artifact?.malformed ? "malformed" : "unavailable";
  if (artifact.completeness) return artifact.completeness;
  if (artifact.malformed) return "malformed";
  if (artifact.truncated) return "truncated";
  return "complete";
}

function findArtifact(input: TrialAnalysisInput, artifactType: string) {
  return input.artifacts.find((artifact) => artifact.artifactType === artifactType);
}

function extractTrustedExceptionMarkers(text: string) {
  const markers = [
    "model_refusal_no_fallback",
    "timeout",
    "connection_error",
    "connection_refused",
    "api_connection_error",
    "authentication_error",
    "rate_limit",
    "service_unavailable",
    "network_error",
    "dns_error",
    "tls_error",
    "transport_error",
    "setup_error"
  ];
  const normalized = text.toLowerCase();
  return markers.filter((marker) => new RegExp(`(?:^|[^a-z0-9_])${marker}(?:$|[^a-z0-9_])`).test(normalized));
}

function verifierStatus(text: string | null, ctrfText: string | null): TrialFacts["verifierExecutionStatus"] {
  const structured = ctrfEvidence(ctrfText).status;
  if (structured !== "unknown") return structured;
  if (!text) return "unknown";
  if (/collection error|verifier error|environment failure|no tests ran/i.test(text)) return "error";
  if (/\b0 failed\b|\b\d+ passed\b/i.test(text) && !/\b[1-9]\d* failed\b|\bFAILED\b/i.test(text)) return "passed";
  if (/\bFAILED\b|\b[1-9]\d* failed\b|AssertionError|ERROR/i.test(text)) return "failed";
  return "unknown";
}

export function extractTrialFacts(input: TrialAnalysisInput): TrialFacts {
  const transcriptArtifact = findArtifact(input, "agent_transcript");
  const trajectoryArtifact = findArtifact(input, "trajectory");
  const resultArtifact = findArtifact(input, "result");
  const verifierArtifact = findArtifact(input, "verifier_stdout");
  const ctrfArtifact = findArtifact(input, "verifier_ctrf");
  const exceptionArtifact = findArtifact(input, "exception");
  const configArtifact = findArtifact(input, "config");
  const transcript = parseTranscript(transcriptArtifact?.text ?? null);
  const trajectory = parseTrajectory(trajectoryArtifact?.text ?? null);
  const result = parseResultArtifact(resultArtifact?.text ?? null);
  const configuration = parseConfig(configArtifact?.text ?? null);
  configuration.model_alias = configuration.model_alias ?? transcript.model;
  configuration.claude_code_version = transcript.claudeCodeVersion ?? configuration.claude_code_version;

  const reward = numericFact(input.reward);
  const rawOutcome: RawOutcome = !reward.present || reward.value === null ? "not_recorded" : reward.value > 0 ? "success" : "failure";
  const databaseExceptionSummary = input.databaseExceptionSummary ?? "";
  const databaseExceptionTypeText = input.exceptionType ?? "";
  const resultExceptionText = `${result.exceptionType ?? ""}\n${result.terminationReason ?? ""}`;
  const exceptionArtifactText = exceptionArtifact?.text ?? "";
  const artifactExceptionText = `${databaseExceptionTypeText}\n${resultExceptionText}\n${exceptionArtifactText}`;
  const exceptionText = `${artifactExceptionText}\n${databaseExceptionSummary}`;
  const databaseExceptionTypeTrustedMarkers = extractTrustedExceptionMarkers(databaseExceptionTypeText);
  const resultTrustedMarkers = extractTrustedExceptionMarkers(resultExceptionText);
  const exceptionArtifactTrustedMarkers = extractTrustedExceptionMarkers(exceptionArtifactText);
  const databaseExceptionSummaryTrustedMarkers = extractTrustedExceptionMarkers(databaseExceptionSummary);
  const exceptionTrustedMarkers = [...new Set([
    ...databaseExceptionTypeTrustedMarkers,
    ...resultTrustedMarkers,
    ...exceptionArtifactTrustedMarkers,
    ...databaseExceptionSummaryTrustedMarkers
  ])];
  const hasRefusalMarker = (text: string) => /model_refusal_no_fallback|provider_policy_refusal|refusal_category/i.test(text);
  const databaseExceptionTypeRefusalMarker = hasRefusalMarker(databaseExceptionTypeText);
  const resultRefusalMarker = hasRefusalMarker(resultExceptionText);
  const exceptionArtifactRefusalMarker = hasRefusalMarker(exceptionArtifactText);
  const databaseExceptionSummaryRefusalMarker = hasRefusalMarker(databaseExceptionSummary);
  const explicitRefusal = transcript.explicitRefusal || /model_refusal_no_fallback|provider_policy_refusal|refusal_category/i.test(exceptionText);
  const timeout = /timeout/i.test(exceptionText) || /timeout/i.test(transcript.terminalReason ?? "");
  const substantiveActivityObserved = transcript.visibleAssistantEvents > 0 || transcript.toolCalls > 0 || trajectory.substantive > 0;
  const transcriptCompleteness = readCompleteness(transcriptArtifact);
  const trajectoryCompleteness = readCompleteness(trajectoryArtifact);
  const resultCompleteness = readCompleteness(resultArtifact);
  const verifierCompleteness = readCompleteness(verifierArtifact);
  const absenceSensitiveEvidenceComplete = transcriptCompleteness === "complete" && trajectoryCompleteness === "complete";
  const evidenceComplete = [transcriptCompleteness, trajectoryCompleteness, resultCompleteness, verifierCompleteness].every((status) => status === "complete")
    && (input.canonicalEvidenceComplete ?? true)
    && !input.artifactSelectionAmbiguous;
  const transcriptUsage = combineUsageRecords(transcript.usageRecords);
  const exceptionPresent = Boolean(input.exceptionType || databaseExceptionSummary || exceptionArtifact || result.exceptionPresent);
  const transportMarkers = new Set([
    "connection_error", "connection_refused", "api_connection_error", "authentication_error",
    "rate_limit", "service_unavailable", "network_error", "dns_error", "tls_error",
    "transport_error", "setup_error"
  ]);
  const transportOrSetupException = exceptionPresent
    && !explicitRefusal
    && !timeout
    && exceptionTrustedMarkers.some((marker) => transportMarkers.has(marker));
  const unclassifiedException = exceptionPresent && !explicitRefusal && !timeout && !transportOrSetupException;
  const provisionalFailure = classifyVerifier(verifierArtifact?.text ?? null, ctrfArtifact?.text ?? null, rawOutcome, explicitRefusal, timeout);

  return {
    reward,
    resultReward: result.reward,
    databaseResultConsistency: resultConsistency(reward, result.reward, resultCompleteness),
    runtimeSeconds: numericFact(input.runtimeSeconds),
    exceptionPresent,
    databaseExceptionType: input.exceptionType,
    databaseExceptionSummaryPresent: Boolean(databaseExceptionSummary),
    databaseExceptionSummaryTrustedMarkers,
    databaseExceptionSummaryRefusalMarker,
    databaseExceptionTypeTrustedMarkers,
    databaseExceptionTypeRefusalMarker,
    exceptionType: input.exceptionType ?? result.exceptionType,
    exceptionArtifactPresent: Boolean(exceptionArtifact),
    exceptionArtifactTrustedMarkers,
    exceptionArtifactRefusalMarker,
    resultArtifactPresent: Boolean(resultArtifact),
    resultExceptionPresent: result.exceptionPresent,
    resultExceptionType: result.exceptionType,
    resultTerminationReason: result.terminationReason,
    resultStatus: result.status,
    resultTrustedMarkers,
    resultRefusalMarker,
    exceptionTrustedMarkers,
    unclassifiedException,
    exceptionAfterSubstantiveActivity: exceptionPresent && substantiveActivityObserved,
    visibleAssistantEvents: transcript.visibleAssistantEvents,
    thinkingEvents: transcript.thinkingEvents,
    toolCalls: transcript.toolCalls,
    workspaceChangingCalls: transcript.workspaceChangingCalls,
    trajectorySteps: trajectory.steps,
    substantiveTrajectorySteps: trajectory.substantive,
    substantiveActivityObserved,
    finalResultPresent: transcript.finalResultPresent,
    finalResultEmpty: transcript.finalResultEmpty,
    terminalReason: transcript.terminalReason,
    stopReason: transcript.stopReason,
    apiErrorStatus: transcript.apiErrorStatus,
    apiDurationMs: transcript.apiDurationMs,
    syntheticRetryCount: transcript.syntheticRetryCount,
    transcriptExplicitRefusal: transcript.explicitRefusal,
    explicitRefusal,
    refusalCategory: transcript.refusalCategory ?? (exceptionText.match(/(?:api_)?refusal_category["'=:\s]+([a-z0-9_-]+)/i)?.[1] ?? null),
    timeout,
    transportOrSetupException,
    verifierExecutionStatus: verifierStatus(verifierArtifact?.text ?? null, ctrfArtifact?.text ?? null),
    verifierFailureHeadline: verifierHeadline(verifierArtifact?.text ?? null),
    failureSubtype: provisionalFailure,
    usageRecords: transcript.usageRecords,
    transcriptUsage,
    databaseInput: numericFact(input.databaseInputTokens),
    databaseCache: numericFact(input.databaseCacheTokens),
    databaseOutput: numericFact(input.databaseOutputTokens),
    databaseCost: numericFact(input.databaseCostUsd),
    transcriptCompleteness,
    trajectoryCompleteness,
    resultCompleteness,
    verifierCompleteness,
    absenceSensitiveEvidenceComplete,
    evidenceComplete,
    artifactSelectionAmbiguous: Boolean(input.artifactSelectionAmbiguous),
    malformedTranscriptLines: transcript.malformedLines,
    configuration
  };
}

function rawOutcome(facts: TrialFacts): RawOutcome {
  if (!facts.reward.present || facts.reward.value === null) return "not_recorded";
  return facts.reward.value > 0 ? "success" : "failure";
}

function componentsMatch(database: NumericFact, transcript: NumericFact) {
  return database.present && transcript.present && database.value !== null && transcript.value !== null && database.value === transcript.value;
}

function telemetryStatus(facts: TrialFacts, emptyCompletion: boolean): TelemetryStatus {
  if (facts.transcriptCompleteness !== "complete") return "incomplete_evidence";
  const transcript = facts.transcriptUsage;
  if (!transcript) return "unknown";
  const transcriptInput = usageInputTotal(transcript);
  const transcriptOutput = transcript.output;
  const transcriptCost = transcript.cost;
  const transcriptFacts = [transcriptInput, transcript.cacheReadInput, transcriptOutput];
  const databaseFacts = [facts.databaseInput, facts.databaseCache, facts.databaseOutput];
  const anyTranscriptPresent = transcriptFacts.some((fact) => fact.present) || transcriptCost.present;
  const anyDatabasePresent = databaseFacts.some((fact) => fact.present) || facts.databaseCost.present;
  const allDatabaseMissing = !anyDatabasePresent;
  const anyDatabaseMissing = databaseFacts.some((fact) => !fact.present);
  const transcriptTotal = usageTotal(transcript);
  const databaseTotal = databaseFacts.reduce((sum, fact) => sum + (fact.value ?? 0), 0);

  if (transcript.mode !== "final_aggregate" && !facts.finalResultPresent) return "partial";
  if (allDatabaseMissing && anyTranscriptPresent) return "database_missing_transcript_present";
  if (anyDatabaseMissing || transcriptFacts.some((fact) => !fact.present)) return "partial";
  if (databaseFacts.some((fact) => fact.value === null) || transcriptFacts.some((fact) => fact.value === null)) return "partial";
  if (databaseTotal === 0 && (transcriptTotal ?? 0) > 0) return "database_zero_transcript_nonzero";
  if (!componentsMatch(facts.databaseInput, transcriptInput)
    || !componentsMatch(facts.databaseCache, transcript.cacheReadInput)
    || !componentsMatch(facts.databaseOutput, transcriptOutput)) return "nonzero_mismatch";
  if (facts.databaseCost.present !== transcriptCost.present) return "partial";
  if (facts.databaseCost.present && transcriptCost.present
    && facts.databaseCost.value !== null && transcriptCost.value !== null
    && Math.abs(facts.databaseCost.value - transcriptCost.value) > 1e-9) return "nonzero_mismatch";
  if (emptyCompletion && databaseTotal === 0 && transcriptTotal === 0) return "zero_usage_empty_completion";
  return "consistent";
}

function confidenceFor(facts: TrialFacts): AnalysisConfidence {
  const statuses = [facts.transcriptCompleteness, facts.trajectoryCompleteness, facts.resultCompleteness, facts.verifierCompleteness];
  if (statuses.every((status) => status === "unavailable")) return "unknown";
  if (facts.evidenceComplete && facts.malformedTranscriptLines === 0) return "high";
  if (facts.substantiveActivityObserved || facts.explicitRefusal || facts.timeout) {
    return statuses.some((status) => status === "malformed" || status === "unavailable") ? "low" : "medium";
  }
  return "low";
}

type ReviewPriority = "high" | "medium" | "low";

function maxPriority(...priorities: ReviewPriority[]): ReviewPriority {
  const rank: Record<ReviewPriority, number> = { low: 0, medium: 1, high: 2 };
  return priorities.reduce((best, current) => rank[current] > rank[best] ? current : best, "low");
}

function manualReview(facts: TrialFacts, activity: ActivitySubtype, failure: FailureSubtype, telemetry: TelemetryStatus, confidence: AnalysisConfidence) {
  const activityPriority: Partial<Record<ActivitySubtype, ReviewPriority>> = {
    provider_policy_refusal: "high",
    empty_completion_zero_usage: "high",
    empty_completion_after_long_api_path_wait: "high",
    thinking_only_empty_completion: "high",
    synthetic_retry_empty_completion: "high",
    setup_or_transport_exception: "high",
    timeout_after_meaningful_activity: "medium",
    questionable_success_no_activity: "high",
    activity_unknown: "high"
  };
  const priorities: ReviewPriority[] = [activityPriority[activity] ?? "low"];
  if (!["consistent", "zero_usage_empty_completion"].includes(telemetry)) priorities.push("medium");
  if (!facts.evidenceComplete || !facts.absenceSensitiveEvidenceComplete) priorities.push("medium");
  if (failure === "verifier_or_environment_failure") priorities.push("high");
  if (facts.unclassifiedException) priorities.push("high");
  if (facts.exceptionPresent && rawOutcome(facts) === "success") priorities.push("high");
  if (facts.databaseResultConsistency === "mismatch") priorities.push("high");
  if (["database_missing_result_present", "result_missing_database_present", "incomplete_evidence"].includes(facts.databaseResultConsistency)) priorities.push("medium");
  if (confidence === "low" || confidence === "unknown") priorities.push("high");
  const priority = maxPriority(...priorities);
  return { required: priority !== "low", priority };
}

export function classifyTrialFacts(facts: TrialFacts, routerObservability: RouterObservability = "unknown"): TrialAnalysis {
  const outcome = rawOutcome(facts);
  const usage = facts.transcriptUsage;
  const transcriptTotal = usageTotal(usage);
  const explicitZeroUsage = usage !== null
    && transcriptTotal === 0
    && usageInputTotal(usage).present
    && usage.output.present;
  const noObservedActivity = !facts.substantiveActivityObserved;
  const decisiveEmptyCompletion = facts.absenceSensitiveEvidenceComplete
    && noObservedActivity
    && facts.finalResultPresent
    && facts.finalResultEmpty === true;
  const longApiPathWait = (facts.apiDurationMs ?? 0) >= 60_000;

  let activitySubtype: ActivitySubtype;
  let executionValidity: ExecutionValidity;
  let policyDisposition: PolicyDisposition = "none_detected";
  const terminationSubtype: TerminationSubtype = facts.explicitRefusal ? "provider_policy_refusal"
    : facts.timeout ? "timeout"
      : facts.transportOrSetupException ? "setup_or_transport_exception"
        : facts.unclassifiedException ? "unclassified_exception"
          : "none";

  if (facts.explicitRefusal) {
    policyDisposition = "provider_policy_refusal";
    executionValidity = "policy_blocked";
    activitySubtype = facts.substantiveActivityObserved ? "substantive_agent_activity" : "provider_policy_refusal";
  } else if (facts.timeout && facts.substantiveActivityObserved) {
    activitySubtype = "timeout_after_meaningful_activity";
    executionValidity = "substantive";
  } else if (facts.transportOrSetupException) {
    activitySubtype = "setup_or_transport_exception";
    executionValidity = "invalid_transport_or_setup";
  } else if (facts.timeout) {
    // A timeout proves termination, but without retained substantive activity or a
    // trusted setup/transport marker it does not prove where execution stalled.
    activitySubtype = "activity_unknown";
    executionValidity = "unknown";
  } else if (facts.substantiveActivityObserved) {
    const provisionalTelemetry = telemetryStatus(facts, false);
    activitySubtype = ["database_missing_transcript_present", "database_zero_transcript_nonzero"].includes(provisionalTelemetry)
      ? "telemetry_missing_activity_present"
      : "substantive_agent_activity";
    executionValidity = "substantive";
  } else if (facts.unclassifiedException) {
    activitySubtype = "activity_unknown";
    executionValidity = "unknown";
  } else if (outcome === "success" && facts.absenceSensitiveEvidenceComplete) {
    activitySubtype = "questionable_success_no_activity";
    executionValidity = "questionable";
  } else if (decisiveEmptyCompletion && facts.syntheticRetryCount > 0) {
    activitySubtype = "synthetic_retry_empty_completion";
    executionValidity = "invalid_response_path";
  } else if (decisiveEmptyCompletion && facts.thinkingEvents > 0) {
    activitySubtype = "thinking_only_empty_completion";
    executionValidity = "invalid_response_path";
  } else if (decisiveEmptyCompletion && longApiPathWait) {
    activitySubtype = "empty_completion_after_long_api_path_wait";
    executionValidity = "invalid_response_path";
  } else if (decisiveEmptyCompletion && explicitZeroUsage) {
    activitySubtype = "empty_completion_zero_usage";
    executionValidity = "invalid_response_path";
  } else {
    activitySubtype = "activity_unknown";
    executionValidity = "unknown";
    policyDisposition = facts.absenceSensitiveEvidenceComplete ? "none_detected" : "unknown";
  }

  const telemetry = telemetryStatus(facts, decisiveEmptyCompletion);
  const confidence = confidenceFor(facts);
  const failureSubtype = facts.failureSubtype;
  const review = manualReview(facts, activitySubtype, failureSubtype, telemetry, confidence);

  const evidence: AnalysisEvidence[] = [];
  const artifactEvidence = (artifactType: string) => ({
    source: `artifact:${artifactType}`,
    artifactType,
    artifactId: undefined as string | undefined
  });
  const databaseEvidence = (source: string) => ({ source });
  const derivedEvidence = (source: "artifact_inventory" | "derived_absence" | "result_and_artifact_inventory") => ({ source });
  const markersSupportTermination = (markers: string[]) => markers.some((marker) =>
    marker === "model_refusal_no_fallback" || marker === "timeout" || [
      "connection_error", "connection_refused", "api_connection_error", "authentication_error",
      "rate_limit", "service_unavailable", "network_error", "dns_error", "tls_error",
      "transport_error", "setup_error"
    ].includes(marker)
  );
  const refusalEvidence = facts.transcriptExplicitRefusal
    ? artifactEvidence("agent_transcript")
    : facts.exceptionArtifactRefusalMarker
      ? artifactEvidence("exception")
      : facts.resultRefusalMarker
        ? artifactEvidence("result")
        : facts.databaseExceptionSummaryRefusalMarker
          ? databaseEvidence("database_exception_summary")
          : facts.databaseExceptionTypeRefusalMarker
            ? databaseEvidence("database_exception_type")
            : derivedEvidence("derived_absence");
  const terminationEvidence = facts.explicitRefusal
    ? refusalEvidence
    : facts.timeout && /timeout/i.test(facts.terminalReason ?? "")
      ? artifactEvidence("agent_transcript")
      : markersSupportTermination(facts.exceptionArtifactTrustedMarkers)
        ? artifactEvidence("exception")
        : markersSupportTermination(facts.resultTrustedMarkers)
          ? artifactEvidence("result")
          : markersSupportTermination(facts.databaseExceptionSummaryTrustedMarkers)
            ? databaseEvidence("database_exception_summary")
            : markersSupportTermination(facts.databaseExceptionTypeTrustedMarkers)
              ? databaseEvidence("database_exception_type")
              : facts.exceptionArtifactPresent
                ? artifactEvidence("exception")
                : facts.resultExceptionPresent
                  ? artifactEvidence("result")
                  : facts.databaseExceptionSummaryPresent
                    ? databaseEvidence("database_exception_summary")
                    : facts.databaseExceptionType
                      ? databaseEvidence("database_exception_type")
                      : derivedEvidence("derived_absence");
  const exceptionArtifactOrResultEvidence = facts.exceptionArtifactPresent
    ? artifactEvidence("exception")
    : facts.resultExceptionPresent
      ? artifactEvidence("result")
      : derivedEvidence("result_and_artifact_inventory");
  const valueOrMissing = (fact: NumericFact) => !fact.present ? "not recorded" : fact.value === null ? "recorded but non-numeric" : String(fact.value);
  evidence.push(
    { label: "Database reward (raw source of truth)", value: valueOrMissing(facts.reward), ...databaseEvidence("database_reward") },
    { label: "Harbor result reward", value: valueOrMissing(facts.resultReward), ...artifactEvidence("result") },
    { label: "Database/result reward consistency", value: facts.databaseResultConsistency, ...artifactEvidence("result") },
    { label: "Database exception type", value: facts.databaseExceptionType ?? "not recorded", ...databaseEvidence("database_exception_type") },
    { label: "Database exception summary", value: facts.databaseExceptionSummaryPresent ? "recorded (sanitized before analysis)" : "not recorded", ...databaseEvidence("database_exception_summary") },
    { label: "Database exception summary trusted markers", value: facts.databaseExceptionSummaryTrustedMarkers.length ? facts.databaseExceptionSummaryTrustedMarkers.join(", ") : "none", ...databaseEvidence("database_exception_summary") },
    { label: "Exception artifact/result", value: facts.exceptionArtifactPresent || facts.resultExceptionPresent ? facts.exceptionType ?? "exception evidence present" : "none recorded", ...exceptionArtifactOrResultEvidence },
    { label: "All trusted exception markers", value: facts.exceptionTrustedMarkers.length ? facts.exceptionTrustedMarkers.join(", ") : "none", ...(facts.exceptionTrustedMarkers.length ? terminationEvidence : derivedEvidence("derived_absence")) },
    { label: "Termination / exception subtype", value: terminationSubtype, ...(terminationSubtype === "none" ? derivedEvidence("derived_absence") : terminationEvidence) },
    { label: "Visible assistant events", value: String(facts.visibleAssistantEvents), ...artifactEvidence("agent_transcript") },
    { label: "Tool calls", value: String(facts.toolCalls), ...artifactEvidence("agent_transcript") },
    { label: "Workspace-changing calls", value: String(facts.workspaceChangingCalls), ...artifactEvidence("agent_transcript") },
    { label: "Thinking event metadata", value: `${facts.thinkingEvents} (content neither retained nor displayed)`, ...artifactEvidence("agent_transcript") },
    { label: "Final result", value: !facts.finalResultPresent ? "not observed" : facts.finalResultEmpty ? "empty" : "non-empty", ...artifactEvidence("agent_transcript") },
    { label: "Transcript evidence", value: facts.transcriptCompleteness, ...artifactEvidence("agent_transcript") },
    { label: "Trajectory evidence", value: facts.trajectoryCompleteness, ...artifactEvidence("trajectory") },
    { label: "Database input tokens", value: valueOrMissing(facts.databaseInput), ...databaseEvidence("database_telemetry") },
    { label: "Transcript total input tokens", value: valueOrMissing(usageInputTotal(usage)), ...artifactEvidence("agent_transcript") },
    { label: "Transcript output tokens", value: usage ? valueOrMissing(usage.output) : "not recorded", ...artifactEvidence("agent_transcript") },
    { label: "Transcript usage basis", value: usage ? usage.mode : "not recorded", ...artifactEvidence("agent_transcript") },
    { label: "Synthetic retry", value: facts.syntheticRetryCount ? `yes (${facts.syntheticRetryCount})` : "no", ...artifactEvidence("agent_transcript") },
    { label: "Explicit refusal marker", value: facts.explicitRefusal ? `yes${facts.refusalCategory ? ` (${facts.refusalCategory})` : ""}` : "no", ...(facts.explicitRefusal ? refusalEvidence : derivedEvidence("derived_absence")) },
    { label: "Verifier failure subtype", value: failureSubtype, ...artifactEvidence("verifier_stdout") }
  );

  const label = activitySubtype.replaceAll("_", " ");
  const summary = facts.explicitRefusal
    ? `Raw benchmark ${outcome}. A provider-policy refusal was recorded${facts.substantiveActivityObserved ? " after prior substantive activity" : " before substantive activity"}; policy disposition is independent from transport validity.`
    : facts.unclassifiedException
      ? `Raw benchmark ${outcome}. An exception is recorded, but retained markers do not justify a setup/transport attribution; termination remains unclassified for manual review.`
    : activitySubtype === "questionable_success_no_activity"
      ? "Raw benchmark success, but complete activity evidence contains no visible assistant content or tool activity. Manual review is required."
      : activitySubtype === "activity_unknown"
        ? `Raw benchmark ${outcome}. Retained evidence is insufficient for an absence-sensitive activity classification.`
        : `Raw benchmark ${outcome}. Derived activity classification: ${label}. ${facts.substantiveActivityObserved ? "Substantive visible activity was recorded." : "Complete activity evidence established no substantive visible activity."}`;

  const inputTotal = usageInputTotal(usage);
  return {
    analyzer_version: ANALYZER_VERSION,
    raw_outcome: outcome,
    execution_validity: executionValidity,
    policy_disposition: policyDisposition,
    activity_subtype: activitySubtype,
    failure_subtype: failureSubtype,
    termination_subtype: terminationSubtype,
    unclassified_exception: facts.unclassifiedException,
    exception_after_substantive_activity: facts.exceptionAfterSubstantiveActivity,
    result_reward_present: facts.resultReward.present,
    result_reward_value: facts.resultReward.value,
    result_exception_present: facts.resultExceptionPresent,
    result_exception_type: facts.resultExceptionType,
    result_termination_reason: facts.resultTerminationReason,
    result_status: facts.resultStatus,
    database_result_consistency: facts.databaseResultConsistency,
    exception_trusted_markers: facts.exceptionTrustedMarkers,
    database_exception_summary_present: facts.databaseExceptionSummaryPresent,
    database_exception_summary_trusted_markers: facts.databaseExceptionSummaryTrustedMarkers,
    telemetry_status: telemetry,
    router_observability: routerObservability,
    confidence,
    evidence_complete: facts.evidenceComplete,
    manual_review_required: review.required,
    manual_review_priority: review.priority,
    summary,
    visible_assistant_events: facts.visibleAssistantEvents,
    thinking_events: facts.thinkingEvents,
    tool_calls: facts.toolCalls,
    workspace_changing_calls: facts.workspaceChangingCalls,
    trajectory_steps: facts.trajectorySteps,
    substantive_trajectory_steps: facts.substantiveTrajectorySteps,
    substantive_activity_observed: facts.substantiveActivityObserved,
    synthetic_retry_count: facts.syntheticRetryCount,
    explicit_refusal: facts.explicitRefusal,
    refusal_category: facts.refusalCategory,
    terminal_reason: facts.terminalReason,
    stop_reason: facts.stopReason,
    api_error_status: facts.apiErrorStatus,
    api_duration_ms: facts.apiDurationMs,
    transcript_input_tokens: inputTotal.value,
    transcript_uncached_input_tokens: usage?.uncachedInput.value ?? null,
    transcript_cache_read_input_tokens: usage?.cacheReadInput.value ?? null,
    transcript_cache_creation_input_tokens: usage?.cacheCreationInput.value ?? null,
    transcript_output_tokens: usage?.output.value ?? null,
    transcript_cost_usd: usage?.cost.value ?? null,
    final_result_empty: facts.finalResultEmpty,
    verifier_failure_headline: facts.verifierFailureHeadline,
    evidence,
    configuration: facts.configuration
  };
}

export function classifyTrialEvidence(input: TrialAnalysisInput): TrialAnalysis {
  const facts = extractTrialFacts(input);
  const analysis = classifyTrialFacts(facts, input.routerObservability ?? "unknown");
  const artifactByType = new Map(input.artifacts.map((artifact) => [artifact.artifactType, artifact.artifactId]));
  analysis.evidence = analysis.evidence.map((item) => ({
    ...item,
    artifactId: item.artifactType ? artifactByType.get(item.artifactType) : item.artifactId
  }));
  return analysis;
}
