export type ReviewedComparisonScopeId = "phase3-core" | "phase3-extended";
export type EvidenceSourceScopeId =
  | ReviewedComparisonScopeId
  | "valid-imported"
  | "all-imported";

export type EvidenceSourceScopeSelection = Readonly<{
  sourceScope: EvidenceSourceScopeId | null;
  warning: "invalid_source_scope" | "repeated_source_scope" | null;
  warningMessage: string | null;
}>;

export type CostProvenanceFocus = Readonly<{
  armId: string | null;
  runLabel: string | null;
  trialId: string | null;
}>;

export type CostProvenanceFocusSelection = Readonly<{
  focus: CostProvenanceFocus | null;
  warning: "invalid_trial_id" | "repeated_focus" | null;
  warningMessage: string | null;
}>;

export type ReviewedTrialEvidenceFilters = Readonly<{
  trialId?: string | null;
  armId?: string | null;
  runLabel?: string | null;
  taskId?: string | null;
  rawOutcome?: string | null;
  failureSubtype?: string | null;
  executionValidity?: string | null;
  terminationSubtype?: string | null;
  policyDisposition?: string | null;
}>;

export type FailureEvidenceLinkRequest =
  | Readonly<{
      source: "frozen_comprehensive_review";
      armId?: string | null;
      runLabel?: string | null;
      failureSubtype?: string | null;
      sourceScope?: EvidenceSourceScopeId | null;
    }>
  | Readonly<{
      source: "operational_or_unsupported";
    }>;

export const EVIDENCE_SOURCE_SCOPE_NOTE =
  "source_scope is navigation context only; it never changes a destination evidence population or exact run/trial identity.";

const SOURCE_SCOPE_LABELS: Readonly<Record<EvidenceSourceScopeId, string>> = Object.freeze({
  "phase3-core": "Phase 3 reviewed core",
  "phase3-extended": "Phase 3 reviewed extended",
  "valid-imported": "Valid imported inventory",
  "all-imported": "All imported inventory",
});

const REVIEWED_SCOPES = new Set<ReviewedComparisonScopeId>([
  "phase3-core",
  "phase3-extended",
]);
const SOURCE_SCOPES = new Set<EvidenceSourceScopeId>([
  "phase3-core",
  "phase3-extended",
  "valid-imported",
  "all-imported",
]);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function appendSourceScope(pathname: string, sourceScope?: EvidenceSourceScopeId | null): string {
  if (!sourceScope) return pathname;
  if (!SOURCE_SCOPES.has(sourceScope)) throw new Error("Unsupported evidence source scope");
  const params = new URLSearchParams({ source_scope: sourceScope });
  return `${pathname}?${params.toString()}`;
}

function appendSourceScopeParam(
  params: URLSearchParams,
  sourceScope?: EvidenceSourceScopeId | null,
): void {
  if (!sourceScope) return;
  if (!SOURCE_SCOPES.has(sourceScope)) throw new Error("Unsupported evidence source scope");
  params.set("source_scope", sourceScope);
}

export function buildExactRunHref(
  runLabel: string,
  sourceScope?: EvidenceSourceScopeId | null,
): string {
  return appendSourceScope(`/runs/${encodeURIComponent(runLabel)}`, sourceScope);
}

export function buildExactTrialHref(
  trialId: string,
  sourceScope?: EvidenceSourceScopeId | null,
): string {
  return appendSourceScope(`/trials/${encodeURIComponent(trialId)}`, sourceScope);
}

export function buildReviewedTrialEvidenceHref(
  filters: ReviewedTrialEvidenceFilters = {},
  sourceScope?: EvidenceSourceScopeId | null,
): string {
  const params = new URLSearchParams();
  const entries = [
    ["trial_id", filters.trialId],
    ["trial_arm", filters.armId],
    ["trial_run", filters.runLabel],
    ["trial_task", filters.taskId],
    ["trial_outcome", filters.rawOutcome],
    ["trial_failure", filters.failureSubtype],
    ["trial_execution", filters.executionValidity],
    ["trial_termination", filters.terminationSubtype],
    ["trial_policy", filters.policyDisposition],
  ] as const;
  for (const [key, value] of entries) {
    if (value) params.set(key, value);
  }
  appendSourceScopeParam(params, sourceScope);
  const query = params.toString();
  return `${query ? `/comprehensive-review?${query}` : "/comprehensive-review"}#reviewed-trials`;
}

export function buildReviewedAggregateArmEvidenceHref(
  armId: string,
  sourceScope?: EvidenceSourceScopeId | null,
): string {
  return buildReviewedTrialEvidenceHref({ armId }, sourceScope);
}

export function buildReviewedFailureEvidenceHref(
  request: FailureEvidenceLinkRequest,
): string | null {
  if (request.source !== "frozen_comprehensive_review") return null;
  return buildReviewedTrialEvidenceHref({
    armId: request.armId,
    runLabel: request.runLabel,
    rawOutcome: "failure",
    failureSubtype: request.failureSubtype,
  }, request.sourceScope);
}

export function buildCostCoverageHref(
  scope: ReviewedComparisonScopeId,
  focus: Partial<CostProvenanceFocus> = {},
  sourceScope?: EvidenceSourceScopeId | null,
): string {
  if (!REVIEWED_SCOPES.has(scope)) throw new Error("Cost Coverage requires a reviewed Phase 3 scope");
  const params = new URLSearchParams({ scope });
  if (focus.armId) params.set("arm_id", focus.armId);
  if (focus.runLabel) params.set("run_label", focus.runLabel);
  if (focus.trialId) params.set("trial_id", focus.trialId);
  appendSourceScopeParam(params, sourceScope);
  const hasFocus = Boolean(focus.armId || focus.runLabel || focus.trialId);
  return `/cost-coverage?${params.toString()}${hasFocus ? "#cost-provenance-focus" : ""}`;
}

export function selectEvidenceSourceScope(
  value: string | readonly string[] | null | undefined,
): EvidenceSourceScopeSelection {
  if (value === null || value === undefined) {
    return { sourceScope: null, warning: null, warningMessage: null };
  }
  if (Array.isArray(value)) {
    return {
      sourceScope: null,
      warning: "repeated_source_scope",
      warningMessage: "Repeated source_scope values were ignored; exact destination identity is unchanged.",
    };
  }
  if (SOURCE_SCOPES.has(value as EvidenceSourceScopeId)) {
    return { sourceScope: value as EvidenceSourceScopeId, warning: null, warningMessage: null };
  }
  return {
    sourceScope: null,
    warning: "invalid_source_scope",
    warningMessage: "Unknown source_scope was ignored; exact destination identity is unchanged.",
  };
}

export function evidenceSourceScopeLabel(scope: EvidenceSourceScopeId): string {
  return SOURCE_SCOPE_LABELS[scope];
}

export function selectCostProvenanceFocus(input: Readonly<{
  armId?: string | readonly string[] | null;
  runLabel?: string | readonly string[] | null;
  trialId?: string | readonly string[] | null;
}>): CostProvenanceFocusSelection {
  if ([input.armId, input.runLabel, input.trialId].some(Array.isArray)) {
    return {
      focus: null,
      warning: "repeated_focus",
      warningMessage: "Repeated cost-focus values were ignored; no stored evidence query was run.",
    };
  }
  const armId = typeof input.armId === "string" && input.armId !== "" ? input.armId : null;
  const runLabel = typeof input.runLabel === "string" && input.runLabel !== "" ? input.runLabel : null;
  const trialId = typeof input.trialId === "string" && input.trialId !== "" ? input.trialId : null;
  if (trialId !== null && !UUID_PATTERN.test(trialId)) {
    return {
      focus: null,
      warning: "invalid_trial_id",
      warningMessage: "The cost-focus trial_id is not a canonical UUID; no stored evidence query was run.",
    };
  }
  if (armId === null && runLabel === null && trialId === null) {
    return { focus: null, warning: null, warningMessage: null };
  }
  return {
    focus: Object.freeze({ armId, runLabel, trialId }),
    warning: null,
    warningMessage: null,
  };
}
