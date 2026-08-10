import reviewedRunSelectionJson from "../generated/phase3-reviewed-run-selection-data";
import {
  PHASE3_REVIEWED_COMPARISON,
  type ReviewedPhase3ScopeId,
} from "./phase3-reviewed-comparison";

export const PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION =
  "phase3-reviewed-run-selection-v1" as const;

export type ReviewedRunSelectionInput = Readonly<{
  path: string;
  role: string;
  sha256: string;
}>;

export type ProviderLogAllocationQualification = Readonly<{
  armRunAllocationConfidence: "low";
  providerLogExclusivityStatus: "not_proven";
  requestToTrialAllocationStatus: "unresolved";
}>;

export type ReviewedSelectedRun = Readonly<{
  armId: string;
  selectedRunLabel: string;
  selectionKind: "reviewed_full_suite_run";
  runIdentityEvidenceStatus: "reviewed";
  trialCount: number;
  taskCount: number;
  attemptsPerTask: number;
  providerLogAllocationQualification: ProviderLogAllocationQualification | null;
  sourcePaths: readonly string[];
}>;

export type ReviewedRunSelectionScope = Readonly<{
  scopeId: ReviewedPhase3ScopeId;
  armCount: number;
  selectedRunCount: number;
  trialCount: number;
  selections: readonly ReviewedSelectedRun[];
}>;

export type ReviewedRunSelectionPolicy = Readonly<{
  suiteId: "phase3-full-20";
  selectionKind: "reviewed_full_suite_run";
  fullSuiteRequired: true;
  completeTaskSetRequired: true;
  requiredTaskCount: 20;
  attemptsPerTask: 3;
  invalidRunExcluded: true;
  historicalOrderingRule: "finished_at_desc_nulls_last_then_run_label";
  selectionStability: "frozen_by_reviewed_artifact";
}>;

export type Phase3ReviewedRunSelection = Readonly<{
  schemaVersion: typeof PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION;
  reviewedAt: "2026-08-09";
  generator: Readonly<{
    name: "scripts/generate_phase3_reviewed_run_selection.py";
    version: "1.0.0";
  }>;
  inputs: readonly ReviewedRunSelectionInput[];
  selectionPolicy: ReviewedRunSelectionPolicy;
  scopes: Readonly<Record<ReviewedPhase3ScopeId, ReviewedRunSelectionScope>>;
}>;

const SCOPE_IDS: readonly ReviewedPhase3ScopeId[] = ["phase3-core", "phase3-extended"];
const SHA256_PATTERN = /^[a-f0-9]{64}$/;
const EXPECTED_INPUT_ROLES = new Map<string, string>([
  [
    "docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md",
    "kimi_full_run_identity_source",
  ],
  [
    "docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md",
    "kimi_run_identity_qualification_source",
  ],
  [
    "results/manual_verification/comprehensive_review_20260731/review_manifest.json",
    "independent_selection_integrity_manifest",
  ],
  [
    "results/manual_verification/comprehensive_review_20260731/run_review.csv",
    "independent_reviewed_selection_cross_check",
  ],
  [
    "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
    "reviewed_scope_membership_cross_check",
  ],
  [
    "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
    "phase3_core_reviewed_run_identity_source",
  ],
]);

function record(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function integer(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative safe integer`);
  }
  return value;
}

function exact<T extends string>(value: unknown, expected: readonly T[], label: string): T {
  if (typeof value !== "string" || !expected.includes(value as T)) {
    throw new Error(`${label} has an unexpected value`);
  }
  return value as T;
}

function strings(value: unknown, label: string): readonly string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.length === 0)) {
    throw new Error(`${label} must be an array of non-empty strings`);
  }
  return value;
}

function validateQualification(
  value: unknown,
  label: string,
): ProviderLogAllocationQualification | null {
  if (value === null) return null;
  const item = record(value, label);
  return {
    armRunAllocationConfidence: exact(
      item.armRunAllocationConfidence,
      ["low"],
      `${label}.armRunAllocationConfidence`,
    ),
    providerLogExclusivityStatus: exact(
      item.providerLogExclusivityStatus,
      ["not_proven"],
      `${label}.providerLogExclusivityStatus`,
    ),
    requestToTrialAllocationStatus: exact(
      item.requestToTrialAllocationStatus,
      ["unresolved"],
      `${label}.requestToTrialAllocationStatus`,
    ),
  };
}

function validateSelection(value: unknown, label: string): ReviewedSelectedRun {
  const item = record(value, label);
  const armId = text(item.armId, `${label}.armId`);
  const selectedRunLabel = text(item.selectedRunLabel, `${label}.selectedRunLabel`);
  if (!selectedRunLabel.startsWith(`${armId}/`)) {
    throw new Error(`${label}.selectedRunLabel does not match its arm ID`);
  }
  const sourcePaths = strings(item.sourcePaths, `${label}.sourcePaths`);
  if (new Set(sourcePaths).size !== sourcePaths.length) {
    throw new Error(`${label}.sourcePaths contains duplicates`);
  }
  if (sourcePaths.some((path) => !EXPECTED_INPUT_ROLES.has(path))) {
    throw new Error(`${label}.sourcePaths contains an unreviewed path`);
  }
  return {
    armId,
    selectedRunLabel,
    selectionKind: exact(
      item.selectionKind,
      ["reviewed_full_suite_run"],
      `${label}.selectionKind`,
    ),
    runIdentityEvidenceStatus: exact(
      item.runIdentityEvidenceStatus,
      ["reviewed"],
      `${label}.runIdentityEvidenceStatus`,
    ),
    trialCount: integer(item.trialCount, `${label}.trialCount`),
    taskCount: integer(item.taskCount, `${label}.taskCount`),
    attemptsPerTask: integer(item.attemptsPerTask, `${label}.attemptsPerTask`),
    providerLogAllocationQualification: validateQualification(
      item.providerLogAllocationQualification,
      `${label}.providerLogAllocationQualification`,
    ),
    sourcePaths,
  };
}

function validateScope(
  value: unknown,
  scopeId: ReviewedPhase3ScopeId,
): ReviewedRunSelectionScope {
  const label = `scopes.${scopeId}`;
  const item = record(value, label);
  if (!Array.isArray(item.selections)) throw new Error(`${label}.selections must be an array`);
  const selections = item.selections.map((selection, index) =>
    validateSelection(selection, `${label}.selections[${index}]`));
  const armIds = selections.map((selection) => selection.armId);
  const runLabels = selections.map((selection) => selection.selectedRunLabel);
  if (new Set(armIds).size !== selections.length) {
    throw new Error(`${label} contains duplicate arm IDs`);
  }
  if (new Set(runLabels).size !== selections.length) {
    throw new Error(`${label} contains duplicate selected run labels`);
  }
  if (JSON.stringify(armIds) !== JSON.stringify([...armIds].sort())) {
    throw new Error(`${label} selections are not in stable arm-ID order`);
  }
  const parsed: ReviewedRunSelectionScope = {
    scopeId: exact(item.scopeId, SCOPE_IDS, `${label}.scopeId`),
    armCount: integer(item.armCount, `${label}.armCount`),
    selectedRunCount: integer(item.selectedRunCount, `${label}.selectedRunCount`),
    trialCount: integer(item.trialCount, `${label}.trialCount`),
    selections,
  };
  if (parsed.scopeId !== scopeId) throw new Error(`${label}.scopeId does not match its key`);
  if (parsed.armCount !== selections.length || parsed.selectedRunCount !== selections.length) {
    throw new Error(`${label} arm/run counts do not match its selections`);
  }
  if (parsed.trialCount !== selections.reduce((total, selection) => total + selection.trialCount, 0)) {
    throw new Error(`${label}.trialCount does not match its selections`);
  }
  for (const selection of selections) {
    if (selection.trialCount !== 60 || selection.taskCount !== 20 || selection.attemptsPerTask !== 3) {
      throw new Error(`${label}.${selection.armId} is not a complete reviewed 60-trial run`);
    }
  }
  return parsed;
}

function validatePolicy(value: unknown): ReviewedRunSelectionPolicy {
  const item = record(value, "selectionPolicy");
  if (item.fullSuiteRequired !== true
    || item.completeTaskSetRequired !== true
    || item.invalidRunExcluded !== true) {
    throw new Error("selectionPolicy must retain the reviewed full-suite validity requirements");
  }
  const requiredTaskCount = integer(item.requiredTaskCount, "selectionPolicy.requiredTaskCount");
  const attemptsPerTask = integer(item.attemptsPerTask, "selectionPolicy.attemptsPerTask");
  if (requiredTaskCount !== 20 || attemptsPerTask !== 3) {
    throw new Error("selectionPolicy task/attempt requirements are unexpected");
  }
  return {
    suiteId: exact(item.suiteId, ["phase3-full-20"], "selectionPolicy.suiteId"),
    selectionKind: exact(
      item.selectionKind,
      ["reviewed_full_suite_run"],
      "selectionPolicy.selectionKind",
    ),
    fullSuiteRequired: true,
    completeTaskSetRequired: true,
    requiredTaskCount: 20,
    attemptsPerTask: 3,
    invalidRunExcluded: true,
    historicalOrderingRule: exact(
      item.historicalOrderingRule,
      ["finished_at_desc_nulls_last_then_run_label"],
      "selectionPolicy.historicalOrderingRule",
    ),
    selectionStability: exact(
      item.selectionStability,
      ["frozen_by_reviewed_artifact"],
      "selectionPolicy.selectionStability",
    ),
  };
}

function deepFreeze<T>(value: T): Readonly<T> {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

export function validatePhase3ReviewedRunSelection(value: unknown): Phase3ReviewedRunSelection {
  const root = record(value, "snapshot");
  if (root.schemaVersion !== PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION) {
    throw new Error("unsupported Phase 3 reviewed run-selection schema version");
  }
  if (root.reviewedAt !== "2026-08-09") {
    throw new Error("snapshot.reviewedAt is not the reviewed run-selection date");
  }
  const generator = record(root.generator, "snapshot.generator");
  if (generator.name !== "scripts/generate_phase3_reviewed_run_selection.py"
    || generator.version !== "1.0.0") {
    throw new Error("snapshot.generator identity is unexpected");
  }
  if (!Array.isArray(root.inputs) || root.inputs.length !== EXPECTED_INPUT_ROLES.size) {
    throw new Error("snapshot.inputs does not contain the exact reviewed input set");
  }
  const inputs = root.inputs.map((value, index): ReviewedRunSelectionInput => {
    const item = record(value, `inputs[${index}]`);
    const path = text(item.path, `inputs[${index}].path`);
    const role = text(item.role, `inputs[${index}].role`);
    const sha256 = text(item.sha256, `inputs[${index}].sha256`);
    if (EXPECTED_INPUT_ROLES.get(path) !== role) {
      throw new Error(`snapshot input path or role is not reviewed: ${path}`);
    }
    if (!SHA256_PATTERN.test(sha256)) throw new Error(`inputs[${index}].sha256 is invalid`);
    return { path, role, sha256 };
  });
  if (new Set(inputs.map((input) => input.path)).size !== EXPECTED_INPUT_ROLES.size
    || [...EXPECTED_INPUT_ROLES].some(([path, role]) => !inputs.some(
      (input) => input.path === path && input.role === role,
    ))) {
    throw new Error("snapshot.inputs does not exactly match the reviewed input path/role set");
  }

  const scopesRecord = record(root.scopes, "snapshot.scopes");
  const scopeKeys = Object.keys(scopesRecord).sort();
  if (JSON.stringify(scopeKeys) !== JSON.stringify([...SCOPE_IDS].sort())) {
    throw new Error("snapshot.scopes must contain exactly phase3-core and phase3-extended");
  }
  const core = validateScope(scopesRecord["phase3-core"], "phase3-core");
  const extended = validateScope(scopesRecord["phase3-extended"], "phase3-extended");
  if (core.armCount !== 15 || core.selectedRunCount !== 15 || core.trialCount !== 900
    || extended.armCount !== 16 || extended.selectedRunCount !== 16 || extended.trialCount !== 960) {
    throw new Error("reviewed run-selection scope counts do not match 15/900 and 16/960");
  }
  if (core.selections.some((selection) => selection.armId === "router-kimi-k3")) {
    throw new Error("router-kimi-k3 must not appear in phase3-core run selection");
  }
  const extendedKimi = extended.selections.filter((selection) => selection.armId === "router-kimi-k3");
  if (extendedKimi.length !== 1) {
    throw new Error("phase3-extended must contain router-kimi-k3 exactly once");
  }
  const kimi = extendedKimi[0];
  if (kimi.selectedRunLabel !== "router-kimi-k3/2026-07-22__17-51-05") {
    throw new Error("router-kimi-k3 selected run label is unexpected");
  }
  if (kimi.providerLogAllocationQualification === null
    || kimi.providerLogAllocationQualification.armRunAllocationConfidence !== "low"
    || kimi.providerLogAllocationQualification.providerLogExclusivityStatus !== "not_proven"
    || kimi.providerLogAllocationQualification.requestToTrialAllocationStatus !== "unresolved") {
    throw new Error("router-kimi-k3 provider-log allocation qualifications are incomplete");
  }
  if (core.selections.some((selection) => selection.providerLogAllocationQualification !== null)
    || extended.selections.some((selection) =>
      selection.armId !== "router-kimi-k3" && selection.providerLogAllocationQualification !== null)) {
    throw new Error("provider-log allocation qualifications must be limited to router-kimi-k3");
  }

  const extendedCore = extended.selections.filter((selection) => selection.armId !== "router-kimi-k3");
  if (JSON.stringify(core.selections) !== JSON.stringify(extendedCore)) {
    throw new Error("shared core run selections must be identical across scopes");
  }

  for (const scopeId of SCOPE_IDS) {
    const runScope = scopeId === "phase3-core" ? core : extended;
    const comparisonScope = PHASE3_REVIEWED_COMPARISON.scopes[scopeId];
    const selectedArmIds = runScope.selections.map((selection) => selection.armId);
    const comparisonArmIds = comparisonScope.arms.map((arm) => arm.armId);
    if (runScope.armCount !== comparisonScope.armCount
      || runScope.trialCount !== comparisonScope.trialCount
      || JSON.stringify(selectedArmIds) !== JSON.stringify(comparisonArmIds)) {
      throw new Error(`${scopeId} run selection does not match reviewed comparison membership`);
    }
    for (const selection of runScope.selections) {
      const comparisonArm = comparisonScope.arms.find((arm) => arm.armId === selection.armId);
      if (!comparisonArm || comparisonArm.trialCount !== selection.trialCount) {
        throw new Error(`${scopeId}.${selection.armId} does not match reviewed comparison trials`);
      }
    }
  }

  return deepFreeze({
    schemaVersion: PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION,
    reviewedAt: "2026-08-09",
    generator: {
      name: "scripts/generate_phase3_reviewed_run_selection.py",
      version: "1.0.0",
    },
    inputs,
    selectionPolicy: validatePolicy(root.selectionPolicy),
    scopes: {
      "phase3-core": core,
      "phase3-extended": extended,
    },
  });
}

export const PHASE3_REVIEWED_RUN_SELECTION = validatePhase3ReviewedRunSelection(
  reviewedRunSelectionJson,
);

export function getReviewedRunSelectionScope(
  scopeId: ReviewedPhase3ScopeId,
): ReviewedRunSelectionScope {
  return PHASE3_REVIEWED_RUN_SELECTION.scopes[scopeId];
}

export function getReviewedSelectedRun(
  scopeId: ReviewedPhase3ScopeId,
  armId: string,
): ReviewedSelectedRun | null {
  return getReviewedRunSelectionScope(scopeId).selections.find(
    (selection) => selection.armId === armId,
  ) ?? null;
}

export function getReviewedSelectedRunLabels(
  scopeId: ReviewedPhase3ScopeId,
): readonly string[] {
  return Object.freeze(
    getReviewedRunSelectionScope(scopeId).selections.map(
      (selection) => selection.selectedRunLabel,
    ),
  );
}
