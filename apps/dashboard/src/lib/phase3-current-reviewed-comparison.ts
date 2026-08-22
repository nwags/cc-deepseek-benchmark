import currentReviewedSnapshotJson from "../generated/phase3-current-reviewed-comparison-data";
import {
  PHASE3_REVIEWED_COMPARISON,
  type ReviewedCostEvidence,
  type ReviewedOutcomeCostCoverage,
  type ReviewedPhase3Arm,
  type ReviewedPhase3ScopeId,
} from "./phase3-reviewed-comparison";

export const PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION =
  "phase3-current-reviewed-comparison-v2" as const;

export type CurrentReviewedPhase3ScopeId = ReviewedPhase3ScopeId;

export type CurrentSelectedCostBasis =
  | "adjusted_known_cost"
  | "qualified_retained_rate_estimate"
  | "provider_billed";

export type CurrentProviderBillingReconciliationStatus =
  | "exact_arm_total"
  | "not_available_in_current_provider_layer";

export type CurrentSelectedTrialCostAllocationStatus =
  | "available_for_reviewed_layer"
  | "unresolved"
  | "unavailable_provider_aggregate";

export type CurrentSelectedOutcomeCostAllocationStatus =
  | "available"
  | "unavailable"
  | "unavailable_provider_aggregate";

export type CurrentReviewedPhase3Arm = Readonly<
  ReviewedPhase3Arm & {
    historicalHarnessRecordedCostUsd: string;
    historicalReviewedCostBasis: ReviewedPhase3Arm["costBasis"];
    historicalReviewedCostUsd: string;
    providerBilledCostUsd: string | null;
    providerBillingReconciliationStatus:
      CurrentProviderBillingReconciliationStatus;
    providerSelectedRunLabel: string | null;
    selectedCostBasis: CurrentSelectedCostBasis;
    selectedCostConfidence: string;
    selectedCostPerAnySuccessUsd: string;
    selectedCostPerAttemptUsd: string;
    selectedCostPerCleanSuccessUsd: string;
    selectedCostUsd: string;
    selectedOutcomeCostAllocationStatus:
      CurrentSelectedOutcomeCostAllocationStatus;
    selectedTrialCostAllocationStatus:
      CurrentSelectedTrialCostAllocationStatus;
  }
>;

export type CurrentSelectedCostEvidence = Readonly<{
  historicalReviewedArmSumCostUsd: string;
  historicalSourceScopeCostUsd: string;
  note: string;
  outcomeAllocationStatus: "mixed_by_arm";
  providerBillingCoverageStatus: "partial_by_arm";
  providerReconciledArmCount: number;
  providerReconciledArmIds: readonly string[];
  providerReconciledCostUsd: string;
  selectedCostBasis: "mixed_best_available_arm_evidence";
  selectedCostUsd: string;
  sourceScopeReconciliationAdjustmentUsd: string;
  sourceScopeTransformedSelectedCostUsd: string;
  trialAllocationStatus: "mixed_by_arm";
}>;

export type CurrentReviewedPhase3Scope = Readonly<{
  scopeId: CurrentReviewedPhase3ScopeId;
  displayName: string;
  presentationKind:
    | "historical_reviewed_snapshot"
    | "current_reviewed_corpus";
  snapshotDate: string;
  armCount: number;
  trialCount: number;
  successCount: number;
  passRate: number;
  arms: readonly CurrentReviewedPhase3Arm[];
  historicalCostEvidence: ReviewedCostEvidence;
  historicalOutcomeCostCoverage: ReviewedOutcomeCostCoverage;
  selectedCostEvidence: CurrentSelectedCostEvidence;
}>;

export type Phase3CurrentReviewedComparison = Readonly<{
  schemaVersion:
    typeof PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION;
  reviewedAt: "2026-08-21";
  historicalReviewedAt: "2026-08-05";
  generator: Readonly<{
    name: "scripts/generate_phase3_current_reviewed_comparison.py";
    version: "1.0.0";
  }>;
  inputs: readonly Readonly<{
    path: string;
    role: string;
    sha256: string;
  }>[];
  scopes: Readonly<
    Record<CurrentReviewedPhase3ScopeId, CurrentReviewedPhase3Scope>
  >;
}>;

export type CurrentReviewedScopeSelection = Readonly<{
  scopeId: CurrentReviewedPhase3ScopeId;
  scope: CurrentReviewedPhase3Scope;
  warning: "invalid_scope" | "repeated_scope" | null;
  warningMessage: string | null;
  usedDefault: boolean;
}>;

const DECIMAL_PATTERN = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

const EXPECTED_INPUTS = new Map<string, Readonly<{
  role: string;
  sha256: string;
}>>([
  [
    "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
    {
      role: "frozen_historical_reviewed_comparison",
      sha256:
        "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d",
    },
  ],
  [
    "results/phase3/provider_usage/normalized/openai_provider_reconciliation_20260821.csv",
    {
      role: "sanitized_provider_billing_reconciliation",
      sha256:
        "5da12494743dc7265c3c08ffc08aa988451fbc308940453cf9b3bc6cdf71e452",
    },
  ],
]);

const SCOPE_EXPECTATIONS = Object.freeze({
  "phase3-core": Object.freeze({
    selectedCostUsd: "682.961171493867",
    historicalReviewedArmSumCostUsd: "972.169845489198",
    historicalSourceScopeCostUsd: "972.169845489198",
    sourceScopeReconciliationAdjustmentUsd: "0",
    sourceScopeTransformedSelectedCostUsd: "682.961171493867",
  }),
  "phase3-extended": Object.freeze({
    selectedCostUsd: "713.775490893867",
    historicalReviewedArmSumCostUsd: "1002.984164889198",
    historicalSourceScopeCostUsd: "1002.9841648891979",
    sourceScopeReconciliationAdjustmentUsd: "-0.0000000000001",
    sourceScopeTransformedSelectedCostUsd: "713.7754908938669",
  }),
});

const OPENAI_EXPECTATIONS = Object.freeze({
  "router-gpt-5.4": Object.freeze({
    providerBilledCostUsd: "29.7919335",
    selectedCostPerAttemptUsd: "0.496532225",
    selectedCostPerCleanSuccessUsd: "0.78399825",
    selectedCostPerAnySuccessUsd:
      "0.7638957307692307692307692308",
    providerSelectedRunLabel:
      "router-gpt-5.4/2026-06-19__13-47-51",
  }),
  "router-gpt-5.5": Object.freeze({
    providerBilledCostUsd: "48.604914",
    selectedCostPerAttemptUsd: "0.8100819",
    selectedCostPerCleanSuccessUsd:
      "1.157259857142857142857142857",
    selectedCostPerAnySuccessUsd:
      "1.104657136363636363636363636",
    providerSelectedRunLabel:
      "router-gpt-5.5/2026-06-27__01-30-18",
  }),
});

type UnknownRecord = Record<string, unknown>;
type DecimalParts = Readonly<{ units: bigint; scale: number }>;

function record(value: unknown, label: string): UnknownRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as UnknownRecord;
}

function text(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.length) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function nullableText(value: unknown, label: string): string | null {
  return value === null ? null : text(value, label);
}

function decimal(value: unknown, label: string): string {
  const parsed = text(value, label);
  if (!DECIMAL_PATTERN.test(parsed)) {
    throw new Error(`${label} must be a decimal string`);
  }
  return parsed;
}

function nullableDecimal(value: unknown, label: string): string | null {
  return value === null ? null : decimal(value, label);
}

function nonnegativeInteger(value: unknown, label: string): number {
  if (
    typeof value !== "number"
    || !Number.isInteger(value)
    || value < 0
  ) {
    throw new Error(`${label} must be a nonnegative integer`);
  }
  return value;
}

function finiteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label} must be finite`);
  }
  return value;
}

function exact<T extends string>(
  value: unknown,
  allowed: readonly T[],
  label: string,
): T {
  if (
    typeof value !== "string"
    || !allowed.includes(value as T)
  ) {
    throw new Error(`${label} has an unsupported value`);
  }
  return value as T;
}

function decimalParts(value: string, label: string): DecimalParts {
  if (!DECIMAL_PATTERN.test(value)) {
    throw new Error(`${label} is not a reviewed decimal`);
  }
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = unsigned.split(".");
  return {
    units: BigInt(
      `${negative ? "-" : ""}${whole}${fraction}`,
    ),
    scale: fraction.length,
  };
}

function scaleUnits(value: DecimalParts, scale: number): bigint {
  return value.units * (10n ** BigInt(scale - value.scale));
}

function decimalSumEquals(
  values: readonly string[],
  expected: string,
): boolean {
  const parts = values.map((value) =>
    decimalParts(value, "summed decimal")
  );
  const expectedParts = decimalParts(expected, "expected decimal");
  const scale = Math.max(
    expectedParts.scale,
    ...parts.map((value) => value.scale),
  );
  const total = parts.reduce(
    (sum, value) => sum + scaleUnits(value, scale),
    0n,
  );
  return total === scaleUnits(expectedParts, scale);
}

function significantDecimalDigits(value: string): number {
  const unsigned = value.startsWith("-") ? value.slice(1) : value;
  const digits = unsigned.replace(".", "").replace(/^0+/, "");
  return digits.length || 1;
}

function decimalRatioMatches(
  total: string,
  divisor: number,
  quotient: string,
): boolean {
  if (!Number.isInteger(divisor) || divisor <= 0) {
    return false;
  }

  const totalParts = decimalParts(total, "ratio total");
  const quotientParts = decimalParts(
    quotient,
    "ratio quotient",
  );
  const scale = Math.max(
    totalParts.scale,
    quotientParts.scale,
  );
  const totalUnits = scaleUnits(totalParts, scale);
  const quotientUnits = scaleUnits(quotientParts, scale);
  const divisorUnits = BigInt(divisor);
  const product = quotientUnits * divisorUnits;
  const difference =
    product >= totalUnits
      ? product - totalUnits
      : totalUnits - product;

  if (difference === 0n) {
    return true;
  }

  if (significantDecimalDigits(quotient) !== 28) {
    return false;
  }

  const quotientUlp = 10n ** BigInt(
    scale - quotientParts.scale,
  );

  return (
    2n * difference
    <= divisorUnits * quotientUlp
  );
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(value, (_key, item) => {
    if (
      item !== null
      && typeof item === "object"
      && !Array.isArray(item)
    ) {
      return Object.fromEntries(
        Object.entries(
          item as Record<string, unknown>,
        ).sort(([left], [right]) =>
          left.localeCompare(right)
        ),
      );
    }

    return item;
  });
}

function sameJson(left: unknown, right: unknown): boolean {
  return canonicalJson(left) === canonicalJson(right);
}

function assertExactKeys(
  value: UnknownRecord,
  expectedKeys: readonly string[],
  label: string,
): void {
  const actual = Object.keys(value).sort();
  const expected = [...expectedKeys].sort();
  if (!sameJson(actual, expected)) {
    throw new Error(`${label} has unsupported or missing fields`);
  }
}

function validateInputs(value: unknown): Phase3CurrentReviewedComparison["inputs"] {
  if (!Array.isArray(value) || value.length !== EXPECTED_INPUTS.size) {
    throw new Error("inputs must contain exactly the reviewed v2 sources");
  }

  const seen = new Set<string>();

  const inputs = value.map((raw, index) => {
    const item = record(raw, `inputs[${index}]`);
    assertExactKeys(item, ["path", "role", "sha256"], `inputs[${index}]`);

    const path = text(item.path, `inputs[${index}].path`);
    const role = text(item.role, `inputs[${index}].role`);
    const sha256 = text(item.sha256, `inputs[${index}].sha256`);

    if (!SHA256_PATTERN.test(sha256)) {
      throw new Error(`inputs[${index}].sha256 is invalid`);
    }

    const expected = EXPECTED_INPUTS.get(path);
    if (
      !expected
      || expected.role !== role
      || expected.sha256 !== sha256
      || seen.has(path)
    ) {
      throw new Error("current reviewed input provenance is invalid");
    }

    seen.add(path);
    return Object.freeze({ path, role, sha256 });
  });

  return Object.freeze(inputs);
}

function historicalReviewedCost(
  arm: ReviewedPhase3Arm,
): string {
  const value =
    arm.adjustedKnownCostUsd
    ?? arm.qualifiedRetainedRateCostUsd;

  if (value === null) {
    throw new Error(
      `historical reviewed cost is unavailable for ${arm.armId}`,
    );
  }

  return value;
}

function validateCurrentArm(
  value: unknown,
  historical: ReviewedPhase3Arm,
  label: string,
): CurrentReviewedPhase3Arm {
  const item = record(value, label);

  const extraKeys = [
    "historicalHarnessRecordedCostUsd",
    "historicalReviewedCostBasis",
    "historicalReviewedCostUsd",
    "providerBilledCostUsd",
    "providerBillingReconciliationStatus",
    "providerSelectedRunLabel",
    "selectedCostBasis",
    "selectedCostConfidence",
    "selectedCostPerAnySuccessUsd",
    "selectedCostPerAttemptUsd",
    "selectedCostPerCleanSuccessUsd",
    "selectedCostUsd",
    "selectedOutcomeCostAllocationStatus",
    "selectedTrialCostAllocationStatus",
  ];

  assertExactKeys(
    item,
    [...Object.keys(historical), ...extraKeys],
    label,
  );

  for (const [key, historicalValue] of Object.entries(historical)) {
    if (!sameJson(item[key], historicalValue)) {
      throw new Error(
        `${label}.${key} does not preserve the frozen historical arm`,
      );
    }
  }

  const historicalHarnessRecordedCostUsd = decimal(
    item.historicalHarnessRecordedCostUsd,
    `${label}.historicalHarnessRecordedCostUsd`,
  );
  const historicalReviewedCostBasis = exact(
    item.historicalReviewedCostBasis,
    ["adjusted_known_cost", "qualified_retained_rate_estimate"] as const,
    `${label}.historicalReviewedCostBasis`,
  );
  const historicalReviewedCostUsd = decimal(
    item.historicalReviewedCostUsd,
    `${label}.historicalReviewedCostUsd`,
  );
  const providerBilledCostUsd = nullableDecimal(
    item.providerBilledCostUsd,
    `${label}.providerBilledCostUsd`,
  );
  const providerBillingReconciliationStatus = exact(
    item.providerBillingReconciliationStatus,
    [
      "exact_arm_total",
      "not_available_in_current_provider_layer",
    ] as const,
    `${label}.providerBillingReconciliationStatus`,
  );
  const providerSelectedRunLabel = nullableText(
    item.providerSelectedRunLabel,
    `${label}.providerSelectedRunLabel`,
  );
  const selectedCostBasis = exact(
    item.selectedCostBasis,
    [
      "adjusted_known_cost",
      "qualified_retained_rate_estimate",
      "provider_billed",
    ] as const,
    `${label}.selectedCostBasis`,
  );
  const selectedCostConfidence = text(
    item.selectedCostConfidence,
    `${label}.selectedCostConfidence`,
  );
  const selectedCostPerAnySuccessUsd = decimal(
    item.selectedCostPerAnySuccessUsd,
    `${label}.selectedCostPerAnySuccessUsd`,
  );
  const selectedCostPerAttemptUsd = decimal(
    item.selectedCostPerAttemptUsd,
    `${label}.selectedCostPerAttemptUsd`,
  );
  const selectedCostPerCleanSuccessUsd = decimal(
    item.selectedCostPerCleanSuccessUsd,
    `${label}.selectedCostPerCleanSuccessUsd`,
  );
  const selectedCostUsd = decimal(
    item.selectedCostUsd,
    `${label}.selectedCostUsd`,
  );
  const selectedOutcomeCostAllocationStatus = exact(
    item.selectedOutcomeCostAllocationStatus,
    [
      "available",
      "unavailable",
      "unavailable_provider_aggregate",
    ] as const,
    `${label}.selectedOutcomeCostAllocationStatus`,
  );
  const selectedTrialCostAllocationStatus = exact(
    item.selectedTrialCostAllocationStatus,
    [
      "available_for_reviewed_layer",
      "unresolved",
      "unavailable_provider_aggregate",
    ] as const,
    `${label}.selectedTrialCostAllocationStatus`,
  );

  if (
    historicalHarnessRecordedCostUsd !== historical.recordedCostUsd
    || historicalReviewedCostBasis !== historical.costBasis
    || historicalReviewedCostUsd !== historicalReviewedCost(historical)
  ) {
    throw new Error(
      `${label} historical cost bridge does not match the frozen arm`,
    );
  }

  const openaiExpected =
    OPENAI_EXPECTATIONS[
      historical.armId as keyof typeof OPENAI_EXPECTATIONS
    ];

  if (openaiExpected) {
    if (
      historical.provider !== "openai"
      || providerBilledCostUsd !== openaiExpected.providerBilledCostUsd
      || providerBillingReconciliationStatus !== "exact_arm_total"
      || providerSelectedRunLabel
        !== openaiExpected.providerSelectedRunLabel
      || selectedCostBasis !== "provider_billed"
      || selectedCostConfidence !== "exact_provider_arm_total"
      || selectedCostUsd !== openaiExpected.providerBilledCostUsd
      || selectedCostPerAttemptUsd
        !== openaiExpected.selectedCostPerAttemptUsd
      || selectedCostPerCleanSuccessUsd
        !== openaiExpected.selectedCostPerCleanSuccessUsd
      || selectedCostPerAnySuccessUsd
        !== openaiExpected.selectedCostPerAnySuccessUsd
      || selectedTrialCostAllocationStatus
        !== "unavailable_provider_aggregate"
      || selectedOutcomeCostAllocationStatus
        !== "unavailable_provider_aggregate"
    ) {
      throw new Error(
        `${label} OpenAI provider-billed selection is invalid`,
      );
    }
  } else {
    if (
      providerBilledCostUsd !== null
      || providerBillingReconciliationStatus
        !== "not_available_in_current_provider_layer"
      || providerSelectedRunLabel !== null
      || selectedCostBasis !== historical.costBasis
      || selectedCostConfidence !== historical.costConfidence
      || selectedCostUsd !== historicalReviewedCost(historical)
      || selectedTrialCostAllocationStatus
        !== historical.trialAllocationStatus
      || selectedOutcomeCostAllocationStatus
        !== historical.outcomeCostAllocationStatus
    ) {
      throw new Error(
        `${label} non-provider selected-cost bridge is invalid`,
      );
    }
  }

  if (
    !decimalRatioMatches(
      selectedCostUsd,
      historical.trialCount,
      selectedCostPerAttemptUsd,
    )
    || !decimalRatioMatches(
      selectedCostUsd,
      historical.cleanSuccessCount,
      selectedCostPerCleanSuccessUsd,
    )
    || !decimalRatioMatches(
      selectedCostUsd,
      historical.successCount,
      selectedCostPerAnySuccessUsd,
    )
  ) {
    throw new Error(
      `${label} selected-cost efficiency metrics are invalid`,
    );
  }

  return Object.freeze({
    ...historical,
    historicalHarnessRecordedCostUsd,
    historicalReviewedCostBasis,
    historicalReviewedCostUsd,
    providerBilledCostUsd,
    providerBillingReconciliationStatus,
    providerSelectedRunLabel,
    selectedCostBasis,
    selectedCostConfidence,
    selectedCostPerAnySuccessUsd,
    selectedCostPerAttemptUsd,
    selectedCostPerCleanSuccessUsd,
    selectedCostUsd,
    selectedOutcomeCostAllocationStatus,
    selectedTrialCostAllocationStatus,
  });
}

function validateSelectedCostEvidence(
  value: unknown,
  scopeId: CurrentReviewedPhase3ScopeId,
  arms: readonly CurrentReviewedPhase3Arm[],
): CurrentSelectedCostEvidence {
  const label = `${scopeId}.selectedCostEvidence`;
  const item = record(value, label);

  const expectedKeys = [
    "historicalReviewedArmSumCostUsd",
    "historicalSourceScopeCostUsd",
    "note",
    "outcomeAllocationStatus",
    "providerBillingCoverageStatus",
    "providerReconciledArmCount",
    "providerReconciledArmIds",
    "providerReconciledCostUsd",
    "selectedCostBasis",
    "selectedCostUsd",
    "sourceScopeReconciliationAdjustmentUsd",
    "sourceScopeTransformedSelectedCostUsd",
    "trialAllocationStatus",
  ];

  assertExactKeys(item, expectedKeys, label);

  const historicalReviewedArmSumCostUsd = decimal(
    item.historicalReviewedArmSumCostUsd,
    `${label}.historicalReviewedArmSumCostUsd`,
  );
  const historicalSourceScopeCostUsd = decimal(
    item.historicalSourceScopeCostUsd,
    `${label}.historicalSourceScopeCostUsd`,
  );
  const note = text(item.note, `${label}.note`);
  const outcomeAllocationStatus = exact(
    item.outcomeAllocationStatus,
    ["mixed_by_arm"] as const,
    `${label}.outcomeAllocationStatus`,
  );
  const providerBillingCoverageStatus = exact(
    item.providerBillingCoverageStatus,
    ["partial_by_arm"] as const,
    `${label}.providerBillingCoverageStatus`,
  );
  const providerReconciledArmCount = nonnegativeInteger(
    item.providerReconciledArmCount,
    `${label}.providerReconciledArmCount`,
  );

  if (
    !Array.isArray(item.providerReconciledArmIds)
    || item.providerReconciledArmIds.some(
      (armId) => typeof armId !== "string",
    )
  ) {
    throw new Error(
      `${label}.providerReconciledArmIds must be a string array`,
    );
  }

  const providerReconciledArmIds = Object.freeze([
    ...item.providerReconciledArmIds,
  ] as string[]);

  const providerReconciledCostUsd = decimal(
    item.providerReconciledCostUsd,
    `${label}.providerReconciledCostUsd`,
  );
  const selectedCostBasis = exact(
    item.selectedCostBasis,
    ["mixed_best_available_arm_evidence"] as const,
    `${label}.selectedCostBasis`,
  );
  const selectedCostUsd = decimal(
    item.selectedCostUsd,
    `${label}.selectedCostUsd`,
  );
  const sourceScopeReconciliationAdjustmentUsd = decimal(
    item.sourceScopeReconciliationAdjustmentUsd,
    `${label}.sourceScopeReconciliationAdjustmentUsd`,
  );
  const sourceScopeTransformedSelectedCostUsd = decimal(
    item.sourceScopeTransformedSelectedCostUsd,
    `${label}.sourceScopeTransformedSelectedCostUsd`,
  );
  const trialAllocationStatus = exact(
    item.trialAllocationStatus,
    ["mixed_by_arm"] as const,
    `${label}.trialAllocationStatus`,
  );

  const expected = SCOPE_EXPECTATIONS[scopeId];

  if (
    historicalReviewedArmSumCostUsd
      !== expected.historicalReviewedArmSumCostUsd
    || historicalSourceScopeCostUsd
      !== expected.historicalSourceScopeCostUsd
    || selectedCostUsd !== expected.selectedCostUsd
    || sourceScopeReconciliationAdjustmentUsd
      !== expected.sourceScopeReconciliationAdjustmentUsd
    || sourceScopeTransformedSelectedCostUsd
      !== expected.sourceScopeTransformedSelectedCostUsd
    || providerReconciledArmCount !== 2
    || !sameJson(
      providerReconciledArmIds,
      ["router-gpt-5.4", "router-gpt-5.5"],
    )
    || providerReconciledCostUsd !== "78.3968475"
  ) {
    throw new Error(
      `${label} does not match the reviewed selected-cost contract`,
    );
  }

  if (
    !decimalSumEquals(
      arms.map((arm) => arm.selectedCostUsd),
      selectedCostUsd,
    )
  ) {
    throw new Error(
      `${label}.selectedCostUsd does not equal the exact arm sum`,
    );
  }

  const providerArmCosts = arms
    .filter((arm) => arm.selectedCostBasis === "provider_billed")
    .map((arm) => arm.selectedCostUsd);

  if (
    providerArmCosts.length !== 2
    || !decimalSumEquals(providerArmCosts, providerReconciledCostUsd)
  ) {
    throw new Error(
      `${label} provider-reconciled cost does not reconcile`,
    );
  }

  return Object.freeze({
    historicalReviewedArmSumCostUsd,
    historicalSourceScopeCostUsd,
    note,
    outcomeAllocationStatus,
    providerBillingCoverageStatus,
    providerReconciledArmCount,
    providerReconciledArmIds,
    providerReconciledCostUsd,
    selectedCostBasis,
    selectedCostUsd,
    sourceScopeReconciliationAdjustmentUsd,
    sourceScopeTransformedSelectedCostUsd,
    trialAllocationStatus,
  });
}

function validateScope(
  value: unknown,
  scopeId: CurrentReviewedPhase3ScopeId,
): CurrentReviewedPhase3Scope {
  const item = record(value, scopeId);
  const historical = PHASE3_REVIEWED_COMPARISON.scopes[scopeId];

  const expectedKeys = [
    "scopeId",
    "displayName",
    "presentationKind",
    "snapshotDate",
    "armCount",
    "trialCount",
    "successCount",
    "passRate",
    "arms",
    "historicalCostEvidence",
    "historicalOutcomeCostCoverage",
    "selectedCostEvidence",
  ];

  assertExactKeys(item, expectedKeys, scopeId);

  if (
    item.scopeId !== historical.scopeId
    || item.displayName !== historical.displayName
    || item.presentationKind !== historical.presentationKind
    || item.snapshotDate !== historical.snapshotDate
    || item.armCount !== historical.armCount
    || item.trialCount !== historical.trialCount
    || item.successCount !== historical.successCount
    || item.passRate !== historical.passRate
  ) {
    throw new Error(
      `${scopeId} does not preserve frozen reviewed scope identity`,
    );
  }

  if (
    !sameJson(item.historicalCostEvidence, historical.costEvidence)
    || !sameJson(
      item.historicalOutcomeCostCoverage,
      historical.outcomeCostCoverage,
    )
  ) {
    throw new Error(
      `${scopeId} historical evidence does not match frozen v1`,
    );
  }

  if (!Array.isArray(item.arms)) {
    throw new Error(`${scopeId}.arms must be an array`);
  }

  if (item.arms.length !== historical.arms.length) {
    throw new Error(`${scopeId} arm membership changed`);
  }

  const arms = item.arms.map((raw, index) => {
    const historicalArm = historical.arms[index];
    const rawArm = record(raw, `${scopeId}.arms[${index}]`);

    if (rawArm.armId !== historicalArm.armId) {
      throw new Error(
        `${scopeId} arm order or membership changed`,
      );
    }

    return validateCurrentArm(
      raw,
      historicalArm,
      `${scopeId}.arms[${index}]`,
    );
  });

  const selectedCostEvidence = validateSelectedCostEvidence(
    item.selectedCostEvidence,
    scopeId,
    arms,
  );

  return Object.freeze({
    scopeId,
    displayName: historical.displayName,
    presentationKind: historical.presentationKind,
    snapshotDate: historical.snapshotDate,
    armCount: historical.armCount,
    trialCount: historical.trialCount,
    successCount: historical.successCount,
    passRate: historical.passRate,
    arms: Object.freeze(arms),
    historicalCostEvidence: historical.costEvidence,
    historicalOutcomeCostCoverage: historical.outcomeCostCoverage,
    selectedCostEvidence,
  });
}

export type CurrentSelectedOutcomeCostEvidence =
  | Readonly<{
      status: "available";
      evidenceBasis: "historical_reviewed_selected_cost";
      adjustedCleanSuccessCostUsd: string;
      adjustedFailureOrIncompleteCostUsd: string;
      adjustedExceptionSuccessSignalCostUsd: string;
      failureOrIncompleteSpendShare: number;
      nonproductiveOrUncleanSpendShare: number;
    }>
  | Readonly<{
      status: Exclude<
        CurrentSelectedOutcomeCostAllocationStatus,
        "available"
      >;
      evidenceBasis: null;
      adjustedCleanSuccessCostUsd: null;
      adjustedFailureOrIncompleteCostUsd: null;
      adjustedExceptionSuccessSignalCostUsd: null;
      failureOrIncompleteSpendShare: null;
      nonproductiveOrUncleanSpendShare: null;
    }>;

/**
 * Return outcome-cost evidence only when it belongs to the selected cost.
 *
 * Current provider aggregates are never redistributed across historical
 * trials or outcomes. Historical outcome-cost fields can coexist on the
 * reviewed arm for provenance, but they are not selected-cost allocation
 * evidence unless the selected cost is the same historical reviewed basis.
 */
export function getCurrentSelectedOutcomeCostEvidence(
  arm: CurrentReviewedPhase3Arm,
): CurrentSelectedOutcomeCostEvidence {
  const status = arm.selectedOutcomeCostAllocationStatus;

  if (status !== "available") {
    return Object.freeze({
      status,
      evidenceBasis: null,
      adjustedCleanSuccessCostUsd: null,
      adjustedFailureOrIncompleteCostUsd: null,
      adjustedExceptionSuccessSignalCostUsd: null,
      failureOrIncompleteSpendShare: null,
      nonproductiveOrUncleanSpendShare: null,
    });
  }

  if (
    arm.selectedTrialCostAllocationStatus
      !== "available_for_reviewed_layer"
    || arm.selectedCostBasis
      !== arm.historicalReviewedCostBasis
    || arm.selectedCostUsd
      !== arm.historicalReviewedCostUsd
  ) {
    throw new Error(
      `${arm.armId} selected outcome allocation is not owned by the selected cost`,
    );
  }

  if (
    arm.adjustedCleanSuccessCostUsd === null
    || arm.adjustedFailureOrIncompleteCostUsd === null
    || arm.adjustedExceptionSuccessSignalCostUsd === null
    || arm.failureOrIncompleteSpendShare === null
    || arm.nonproductiveOrUncleanSpendShare === null
  ) {
    throw new Error(
      `${arm.armId} selected outcome allocation is incomplete`,
    );
  }

  return Object.freeze({
    status: "available",
    evidenceBasis: "historical_reviewed_selected_cost",
    adjustedCleanSuccessCostUsd:
      arm.adjustedCleanSuccessCostUsd,
    adjustedFailureOrIncompleteCostUsd:
      arm.adjustedFailureOrIncompleteCostUsd,
    adjustedExceptionSuccessSignalCostUsd:
      arm.adjustedExceptionSuccessSignalCostUsd,
    failureOrIncompleteSpendShare:
      arm.failureOrIncompleteSpendShare,
    nonproductiveOrUncleanSpendShare:
      arm.nonproductiveOrUncleanSpendShare,
  });
}

export function validatePhase3CurrentReviewedComparison(
  value: unknown,
): Phase3CurrentReviewedComparison {
  const item = record(value, "current reviewed comparison");

  assertExactKeys(
    item,
    [
      "schemaVersion",
      "reviewedAt",
      "historicalReviewedAt",
      "generator",
      "inputs",
      "scopes",
    ],
    "current reviewed comparison",
  );

  if (
    item.schemaVersion
      !== PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION
  ) {
    throw new Error(
      "unsupported current reviewed comparison schema version",
    );
  }

  if (item.reviewedAt !== "2026-08-21") {
    throw new Error("current reviewed comparison reviewedAt is invalid");
  }

  if (item.historicalReviewedAt !== "2026-08-05") {
    throw new Error(
      "current reviewed comparison historicalReviewedAt is invalid",
    );
  }

  const generator = record(item.generator, "generator");
  assertExactKeys(generator, ["name", "version"], "generator");

  if (
    generator.name
      !== "scripts/generate_phase3_current_reviewed_comparison.py"
    || generator.version !== "1.0.0"
  ) {
    throw new Error(
      "current reviewed comparison generator identity is invalid",
    );
  }

  const inputs = validateInputs(item.inputs);
  const scopesRaw = record(item.scopes, "scopes");

  assertExactKeys(
    scopesRaw,
    ["phase3-core", "phase3-extended"],
    "scopes",
  );

  const core = validateScope(
    scopesRaw["phase3-core"],
    "phase3-core",
  );
  const extended = validateScope(
    scopesRaw["phase3-extended"],
    "phase3-extended",
  );

  if (
    core.arms.some((arm) => arm.armId === "router-kimi-k3")
    || !extended.arms.some((arm) => arm.armId === "router-kimi-k3")
  ) {
    throw new Error(
      "current reviewed Kimi K3 scope membership is invalid",
    );
  }

  return Object.freeze({
    schemaVersion:
      PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION,
    reviewedAt: "2026-08-21",
    historicalReviewedAt: "2026-08-05",
    generator: Object.freeze({
      name:
        "scripts/generate_phase3_current_reviewed_comparison.py",
      version: "1.0.0",
    }),
    inputs,
    scopes: Object.freeze({
      "phase3-core": core,
      "phase3-extended": extended,
    }),
  });
}

export const PHASE3_CURRENT_REVIEWED_COMPARISON =
  validatePhase3CurrentReviewedComparison(
    currentReviewedSnapshotJson,
  );

export function getCurrentReviewedPhase3Scope(
  scopeId: CurrentReviewedPhase3ScopeId,
): CurrentReviewedPhase3Scope {
  return PHASE3_CURRENT_REVIEWED_COMPARISON.scopes[scopeId];
}

export function selectCurrentReviewedPhase3Scope(
  value: string | readonly string[] | null | undefined,
): CurrentReviewedScopeSelection {
  const defaultScopeId: CurrentReviewedPhase3ScopeId =
    "phase3-extended";

  if (value === null || value === undefined || value === "") {
    return Object.freeze({
      scopeId: defaultScopeId,
      scope: getCurrentReviewedPhase3Scope(defaultScopeId),
      warning: null,
      warningMessage: null,
      usedDefault: true,
    });
  }

  if (Array.isArray(value)) {
    return Object.freeze({
      scopeId: defaultScopeId,
      scope: getCurrentReviewedPhase3Scope(defaultScopeId),
      warning: "repeated_scope",
      warningMessage:
        "Repeated scope values are not supported; Phase 3 extended was selected.",
      usedDefault: true,
    });
  }

  if (value === "phase3-core" || value === "phase3-extended") {
    return Object.freeze({
      scopeId: value,
      scope: getCurrentReviewedPhase3Scope(value),
      warning: null,
      warningMessage: null,
      usedDefault: false,
    });
  }

  return Object.freeze({
    scopeId: defaultScopeId,
    scope: getCurrentReviewedPhase3Scope(defaultScopeId),
    warning: "invalid_scope",
    warningMessage:
      "Unknown scope; Phase 3 extended was selected.",
    usedDefault: true,
  });
}
