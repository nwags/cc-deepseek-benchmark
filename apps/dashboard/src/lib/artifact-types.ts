export type ArtifactScope = "run" | "trial" | "observability";

export type ArtifactReviewPriority = "start_here" | "high" | "supporting" | "confirmation";

export type ArtifactTypeDefinition = {
  artifactType: string;
  displayName: string;
  scope: ArtifactScope | "contextual";
  lifecycleOrder: number;
  generationDescription: string;
  shortDefinition: string;
  definition: string;
  bestFor: readonly string[];
  cautions: readonly string[];
  reviewPriority: ArtifactReviewPriority;
  commonFilenames: readonly string[];
};

export const artifactTypeDefinitions = [
  {
    artifactType: "config",
    displayName: "Captured configuration",
    scope: "contextual",
    lifecycleOrder: 1,
    generationDescription: "Harbor captures configuration before execution at both run and trial scope.",
    shortDefinition: "Run or trial configuration snapshot.",
    definition: "At run scope this records the job configuration; at trial scope it records the task, model alias, environment, timeouts, and verifier settings used for one attempt.",
    bestFor: ["Was the intended task and route requested?", "Were timeouts and tool restrictions comparable?"],
    cautions: ["A requested alias is not proof of the provider-resolved backend.", "Secret-valued fields must remain masked."],
    reviewPriority: "high",
    commonFilenames: ["config.json"]
  },
  {
    artifactType: "lock",
    displayName: "Run lock",
    scope: "run",
    lifecycleOrder: 2,
    generationDescription: "The runner creates a lock while coordinating a run.",
    shortDefinition: "Run coordination state.",
    definition: "Run-root lock evidence helps establish runner coordination and whether a job was active or interrupted.",
    bestFor: ["Was a run coordinated normally?", "Was stale runner state involved?"],
    cautions: ["A lock says little about model behavior within an individual trial."],
    reviewPriority: "supporting",
    commonFilenames: ["run.lock", ".lock"]
  },
  {
    artifactType: "log",
    displayName: "Harness log",
    scope: "contextual",
    lifecycleOrder: 3,
    generationDescription: "The runner and Harbor emit setup and execution logs throughout the run or trial.",
    shortDefinition: "Run job log or trial execution log.",
    definition: "At run scope this is commonly job.log; at trial scope trial.log records environment creation, agent setup, execution timing, and verifier launch.",
    bestFor: ["Did environment or agent setup fail?", "Where was time spent?"],
    cautions: ["A clean trial.log does not prove the model produced useful work."],
    reviewPriority: "supporting",
    commonFilenames: ["job.log", "trial.log"]
  },
  {
    artifactType: "agent_transcript",
    displayName: "Claude Code transcript",
    scope: "trial",
    lifecycleOrder: 4,
    generationDescription: "Claude Code emits a stream record of visible messages, tool requests, lifecycle signals, and terminal status.",
    shortDefinition: "Human-reviewable agent execution stream.",
    definition: "The transcript is the primary record of visible assistant output, tool calls, retries, refusals, usage, and CLI termination state.",
    bestFor: ["Did the agent visibly respond?", "Which tools did it call?", "Was there a refusal or synthetic retry?"],
    cautions: ["CLI subtype success only means no surfaced process/API exception; it is not benchmark success.", "Hidden reasoning content must not be displayed."],
    reviewPriority: "start_here",
    commonFilenames: ["claude-code.txt"]
  },
  {
    artifactType: "trajectory",
    displayName: "Structured trajectory",
    scope: "trial",
    lifecycleOrder: 5,
    generationDescription: "The agent adapter serializes structured messages, actions, and steps after or during execution.",
    shortDefinition: "Structured agent behavior record.",
    definition: "Trajectory JSON supports conservative counts of visible steps and tool activity without exposing hidden reasoning.",
    bestFor: ["Does structured behavior agree with the transcript?", "Was an apparently empty completion truly action-free?"],
    cautions: ["An empty step is evidence of no recorded action, not proof that the provider performed no internal computation."],
    reviewPriority: "high",
    commonFilenames: ["trajectory.json"]
  },
  {
    artifactType: "exception",
    displayName: "Exception evidence",
    scope: "trial",
    lifecycleOrder: 6,
    generationDescription: "Harbor writes exception.txt when execution surfaces an exception artifact.",
    shortDefinition: "Explicit exception or traceback evidence.",
    definition: "Exception evidence distinguishes setup/transport failures, timeouts, provider-policy refusals, and other abnormal termination from ordinary verifier failures.",
    bestFor: ["What interrupted execution?", "Was the failure caused before substantive agent activity?"],
    cautions: ["An exception_type field can exist even when no exception artifact was retained.", "Policy refusal is not the same as transport invalidity."],
    reviewPriority: "high",
    commonFilenames: ["exception.txt"]
  },
  {
    artifactType: "verifier_stdout",
    displayName: "Verifier stdout",
    scope: "trial",
    lifecycleOrder: 7,
    generationDescription: "The task verifier emits raw test output after agent execution.",
    shortDefinition: "Raw verifier and test output.",
    definition: "Verifier stdout is usually the clearest explanation of what final workspace condition passed or failed.",
    bestFor: ["Why did the final workspace fail?", "Which assertions passed?"],
    cautions: ["A verifier failure does not by itself identify whether the agent, environment, or test caused it."],
    reviewPriority: "start_here",
    commonFilenames: ["verifier/test-stdout.txt", "test-stdout.txt"]
  },
  {
    artifactType: "verifier_ctrf",
    displayName: "Structured verifier results",
    scope: "trial",
    lifecycleOrder: 8,
    generationDescription: "The verifier serializes test cases in CTRF JSON after test execution.",
    shortDefinition: "Machine-readable verifier results.",
    definition: "CTRF confirms structured test-case names, pass/fail state, timing, and failure details.",
    bestFor: ["Which exact test cases passed or failed?", "Does structured output agree with stdout?"],
    cautions: ["Use alongside verifier stdout for human context."],
    reviewPriority: "confirmation",
    commonFilenames: ["verifier/ctrf.json", "ctrf.json"]
  },
  {
    artifactType: "verifier_reward",
    displayName: "Verifier reward",
    scope: "trial",
    lifecycleOrder: 9,
    generationDescription: "The verifier writes the scored reward after evaluating the workspace.",
    shortDefinition: "Minimal scored outcome, commonly 0 or 1.",
    definition: "The reward file confirms the raw benchmark outcome without explaining why it occurred.",
    bestFor: ["What raw score was recorded?", "Does the reward agree with result.json?"],
    cautions: ["Reward alone cannot establish execution validity or substantive activity."],
    reviewPriority: "confirmation",
    commonFilenames: ["verifier/reward.txt", "reward.txt"]
  },
  {
    artifactType: "result",
    displayName: "Harbor result",
    scope: "contextual",
    lifecycleOrder: 10,
    generationDescription: "Harbor writes a structured result after a run or individual trial finishes.",
    shortDefinition: "Run summary or complete trial result JSON.",
    definition: "At run scope result.json summarizes the job; at trial scope it combines reward, exception metadata, timing, telemetry, and nested agent/verifier results.",
    bestFor: ["What was the recorded outcome?", "How did Harbor classify termination and telemetry?"],
    cautions: ["Null and zero telemetry are different.", "Raw success does not prove substantive agent activity."],
    reviewPriority: "start_here",
    commonFilenames: ["result.json"]
  },
  {
    artifactType: "router_log",
    displayName: "Router log",
    scope: "observability",
    lifecycleOrder: 40,
    generationDescription: "The router may retain request/response metadata while forwarding Claude Code traffic to a provider.",
    shortDefinition: "Router-side request observability.",
    definition: "Router logs can confirm request timing, routing, retries, and provider responses when retention was enabled.",
    bestFor: ["Which backend handled the request?", "Was latency inside the router/provider lane?"],
    cautions: ["Historical router logs were not always retained.", "Router logs are not part of the canonical 8-artifact trial contract."],
    reviewPriority: "supporting",
    commonFilenames: ["router.log", "litellm.log"]
  },
  {
    artifactType: "router_log_slice",
    displayName: "Router log slice",
    scope: "observability",
    lifecycleOrder: 41,
    generationDescription: "A bounded request-window slice may be extracted from a retained router log.",
    shortDefinition: "Trial-local router evidence slice.",
    definition: "A router log slice narrows shared router telemetry to the request window relevant to one trial.",
    bestFor: ["What happened at the router for this request window?", "Were provider responses or retries observed?"],
    cautions: ["Absence can mean not retained rather than no request.", "It remains separate from canonical Harbor evidence."],
    reviewPriority: "supporting",
    commonFilenames: ["router-log-slice.jsonl", "router.log.slice"]
  }
] as const satisfies readonly ArtifactTypeDefinition[];

export const canonicalTrialArtifactTypes = [
  "agent_transcript",
  "config",
  "log",
  "result",
  "trajectory",
  "verifier_ctrf",
  "verifier_reward",
  "verifier_stdout"
] as const;

export const canonicalRunArtifactTypes = ["config", "lock", "log", "result"] as const;
export const routerArtifactTypes = ["router_log", "router_log_slice"] as const;

export function getArtifactTypeDefinition(artifactType: string | null | undefined) {
  if (!artifactType) return undefined;
  return artifactTypeDefinitions.find((item) => item.artifactType === artifactType);
}

export function artifactTypeTitle(artifactType: string | null | undefined) {
  const label = artifactType || "unknown artifact";
  const definition = getArtifactTypeDefinition(artifactType);

  if (!definition) {
    return `${label}: artifact type metadata imported from the benchmark run. No dashboard glossary entry exists yet.`;
  }

  return `${definition.displayName}: ${definition.definition}`;
}

export function artifactScopeForContext(
  artifactType: string | null | undefined,
  trialId: string | null | undefined
): ArtifactScope {
  const definition = getArtifactTypeDefinition(artifactType);
  if (definition?.scope === "observability") return "observability";
  return trialId ? "trial" : "run";
}

export type EvidenceArtifact = {
  artifact_type: string | null;
  r2_uri?: string | null;
};

export type EvidenceCompleteness = {
  scope: "run" | "trial";
  expected_types: string[];
  present_types: string[];
  missing_types: string[];
  canonical_present_count: number;
  canonical_expected_count: number;
  r2_indexed_count: number;
  router_observability: "retained" | "not_retained" | "unknown";
  exception_metadata_without_artifact: boolean;
};

export function deriveEvidenceCompleteness(
  artifacts: readonly EvidenceArtifact[],
  scope: "run" | "trial",
  hasExceptionMetadata = false,
  routerRetentionContract: "retained" | "not_retained" | null = null
): EvidenceCompleteness {
  const present = new Set(artifacts.map((artifact) => artifact.artifact_type).filter((value): value is string => Boolean(value)));
  const hasExceptionArtifact = present.has("exception");
  const expected = scope === "trial"
    ? [...canonicalTrialArtifactTypes, ...(hasExceptionMetadata || hasExceptionArtifact ? ["exception"] : [])]
    : [...canonicalRunArtifactTypes];
  const missing = expected.filter((artifactType) => !present.has(artifactType));
  const r2IndexedCount = expected.filter((artifactType) =>
    artifacts.some((artifact) => artifact.artifact_type === artifactType && Boolean(artifact.r2_uri))
  ).length;
  const routerPresent = routerArtifactTypes.some((artifactType) => present.has(artifactType));

  return {
    scope,
    expected_types: expected,
    present_types: Array.from(present).sort(),
    missing_types: missing,
    canonical_present_count: expected.length - missing.length,
    canonical_expected_count: expected.length,
    r2_indexed_count: r2IndexedCount,
    router_observability: routerPresent ? "retained" : routerRetentionContract === "not_retained" ? "not_retained" : "unknown",
    exception_metadata_without_artifact: hasExceptionMetadata && !hasExceptionArtifact
  };
}
