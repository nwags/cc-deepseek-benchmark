import currentReviewedSnapshotJson from "../generated/phase3-current-reviewed-comparison-data-v4";
import {
  PHASE3_REVIEWED_COMPARISON,
  type ReviewedCostEvidence,
  type ReviewedOutcomeCostCoverage,
  type ReviewedPhase3Arm,
  type ReviewedPhase3ScopeId,
} from "./phase3-reviewed-comparison";

export const PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION =
  "phase3-current-reviewed-comparison-v4" as const;

export type CurrentReviewedPhase3ScopeId = ReviewedPhase3ScopeId;

import type {
  CurrentSelectedCostRelation,
} from "./current-cost-relation";

export type {
  CurrentSelectedCostRelation,
} from "./current-cost-relation";

export type CurrentSelectedEfficiencyRelation =
  CurrentSelectedCostRelation;

export type CurrentSelectedCostBasis =
  | "adjusted_known_cost"
  | "qualified_retained_rate_estimate"
  | "provider_billed"
  | "provider_rate_reconstructed_retained_usage"
  | "provider_rate_reconstructed_retained_usage_lower_bound"
  | "provider_rate_reconstructed_retained_usage_partial"
  | "provider_rate_reconstructed_selected_run"
  | "provider_rate_reconstructed_selected_run_request_tier";

export type CurrentReconciliationStatus =
  | "reconciled"
  | "historical_fallback";

export type CurrentEvidenceClass =
  | "exact_provider_arm_total"
  | "historical_reviewed_fallback"
  | "provider_rate_reconstruction_with_same_day_provider_crosscheck"
  | "verified_retained_artifacts_plus_official_provider_rates"
  | "verified_retained_trajectories_plus_official_provider_rates"
  | "verified_retained_trajectories_plus_provider_bill_validated_rates"
  | "retained_artifacts_plus_official_provider_rates_trajectory_archive_unavailable"
  | "complete_retained_usage_plus_provider_dashboard_validated_rates"
  | "complete_retained_usage_plus_retained_published_rates"
  | "partial_retained_usage_plus_retained_published_rates_cache_accounting_unverified"
  | "complete_retained_usage_plus_retained_rate_constants_qualified_provenance";

export type CurrentProviderBillingReconciliationStatus =
  | "exact_arm_total"
  | "not_available_in_current_reconciliation_layer"
  | "preselected_family_billing_context_not_selected_run"
  | "preselected_provider_context_not_selected_run"
  | "provider_invoice_unavailable"
  | "provider_log_not_invoice_level_allocation_low_confidence"
  | "same_day_model_aggregate_not_run_isolated"
  | "selected_run_provider_invoice_unavailable";

export type CurrentProviderContextScope =
  | "exact_arm_total"
  | "same_day_model_aggregate"
  | "preselected_family_dashboard_total_through_2026-06-19"
  | "preselected_glm5.1_provider_billing_table_through_2026-06-19"
  | "glm5.1_billing_evidence_is_same_family_but_different_model"
  | "shared_preselected_gemini_family_billing_export_through_2026-06-17_nonadditive"
  | "preselected_qwen_payg_bill_detail_through_2026-06-19"
  | "preselected_request_logs_and_dashboard_total_2026-06-04_to_2026-06-16"
  | "broader_provider_request_log_retained_rate_reconstruction";

export type CurrentSelectedTrialCostAllocationStatus =
  | "available_for_reviewed_layer"
  | "available_provider_rate_reconstruction"
  | "available_with_exception_path_lower_bounds"
  | "available_with_unresolved_usage_lower_bounds"
  | "partial_selected_usage_reconstruction_with_unresolved_trials"
  | "unavailable_provider_aggregate"
  | "unresolved";

export type CurrentSelectedOutcomeCostAllocationStatus =
  | "available"
  | "available_lower_bound"
  | "available_partial_estimate"
  | "available_provider_rate_reconstruction"
  | "unavailable"
  | "unavailable_no_reviewed_outcome_join"
  | "unavailable_provider_aggregate";

export type CurrentUnquantifiedAdditionalCostStatus =
  | "none"
  | "none_for_selected_retained_usage"
  | "not_evaluated_current_reconciliation"
  | "possible_additional_exception_path_spend"
  | "possible_additional_unresolved_trial_spend"
  | "unresolved_trial_spend_and_cache_classification_uncertainty";

export type CurrentProviderEvidenceAudit = Readonly<{
  provider: string;
  auditScope: string;
  pricingProvenanceStatus: string;
  trajectoryEvidenceStatus: string;
  providerContextTemporalRelation: string;
  providerContextAllocationConfidence: string;
  auditConclusion: string;

  providerContextAccountSpendUsd: string | null;
  providerContextOverheadUsd: string | null;
  providerContextRateReconstructionUsd: string | null;
  providerContextRateReconstructionExcessVsSelectedUsd:
    string | null;

  selectedInputTokens: string | null;
  selectedCacheTokens: string | null;
  selectedOutputTokens: string | null;
}>;

export type CurrentReviewedPhase3Arm = Readonly<
  ReviewedPhase3Arm & {
    historicalHarnessRecordedCostUsd: string;
    historicalReviewedCostBasis: ReviewedPhase3Arm["costBasis"];
    historicalReviewedCostUsd: string;

    currentReconciliationStatus: CurrentReconciliationStatus;
    currentSelectedRunLabel: string | null;
    currentRoutingAliases: readonly string[];
    currentProviderModels: readonly string[];
    currentEvidenceNote: string;

    selectedCostRelation: CurrentSelectedCostRelation;
    selectedEfficiencyRelation: CurrentSelectedEfficiencyRelation;
    selectedCostBasis: CurrentSelectedCostBasis;
    selectedCostConfidence: string;
    selectedCostUsd: string;
    selectedCostPerAnySuccessUsd: string;
    selectedCostPerAttemptUsd: string;
    selectedCostPerCleanSuccessUsd: string;

    evidenceClass: CurrentEvidenceClass;

    providerBilledCostUsd: string | null;
    providerContextBilledCostUsd: string | null;
    providerContextScope: CurrentProviderContextScope | null;
    providerContextExcessUsd: string | null;
    providerBillingReconciliationStatus:
      CurrentProviderBillingReconciliationStatus;

    completeTrialCostCount: number | null;
    lowerBoundTrialCount: number | null;
    confirmedZeroCostTrialCount: number | null;
    currentUnresolvedTrialCount: number | null;

    selectedTrialCostAllocationStatus:
      CurrentSelectedTrialCostAllocationStatus;
    selectedOutcomeCostAllocationStatus:
      CurrentSelectedOutcomeCostAllocationStatus;

    selectedCleanSuccessCostUsd: string | null;
    selectedNormalFailureCostUsd: string | null;
    selectedExceptionFailureCostUsd: string | null;
    selectedExceptionWithSuccessSignalCostUsd: string | null;
    knownAllocatedCostUsd: string | null;
    unallocatedKnownCostUsd: string | null;
    unquantifiedAdditionalCostStatus:
      CurrentUnquantifiedAdditionalCostStatus;

    providerEvidenceAudit: CurrentProviderEvidenceAudit;
  }
>;

export type CurrentSelectedCostRelationCounts = Readonly<{
  exact: number;
  estimate: number;
  lowerBound: number;
  historicalFallback: number;
}>;

export type CurrentSelectedCostEvidence = Readonly<{
  historicalReviewedArmSumCostUsd: string;
  historicalSourceScopeCostUsd: string;
  note: string;

  currentReconciledArmCount: number;
  currentReconciledArmIds: readonly string[];
  currentReconciledCostUsd: string;
  currentReconciliationCoverageStatus: "complete_by_arm";

  exactProviderBilledArmCount: number;
  exactProviderBilledArmIds: readonly string[];
  exactProviderBilledCostUsd: string;

  selectedCostBasis: "mixed_best_available_arm_evidence";
  selectedCostRelation: "mixed_by_arm";
  selectedCostRelationCounts: CurrentSelectedCostRelationCounts;
  selectedCostUsd: string;

  sourceScopeReconciliationAdjustmentUsd: string;
  sourceScopeTransformedSelectedCostUsd: string;

  trialAllocationStatus: "mixed_by_arm";
  outcomeAllocationStatus: "mixed_by_arm";

  unquantifiedAdditionalCostArmCount: number;
  unquantifiedAdditionalCostArmIds: readonly string[];
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
  reviewedAt: "2026-08-25";
  historicalReviewedAt: "2026-08-05";
  generator: Readonly<{
    name: "scripts/generate_phase3_current_reviewed_comparison_v4.py";
    version: "3.0.0";
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

type UnknownRecord = Record<string, unknown>;
type DecimalParts = Readonly<{ units: bigint; scale: number }>;

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
    "results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv",
    {
      role: "sanitized_current_arm_cost_reconciliation",
      sha256:
        "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256",
    },
  ],
  [
    "results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv",
    {
      role: "sanitized_provider_cost_evidence_matrix",
      sha256:
        "e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218",
    },
  ],
  [
    "results/phase3/reporting/phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv",
    {
      role: "supporting_anthropic_exception_lower_bound_evidence",
      sha256:
        "9223673f2dcdd55fa558f0336d72d721f0bf3c58f409e84fadeaeb277a7dfa88",
    },
  ],
]);

const EXPECTED_EXACT_PROVIDER_BILLED_ARM_IDS =
  Object.freeze([
    "router-gpt-5.4",
    "router-gpt-5.5",
  ]);

const EXPECTED_UNQUANTIFIED_ADDITIONAL_COST_ARM_IDS =
  Object.freeze([
    "router-anthropic-opus",
    "router-anthropic-sonnet",
    "router-gemini-flash",
    "router-glm-5.1",
    "router-grok-build-0.1",
    "router-qwen-3.7-plus",
  ]);

const SCOPE_EXPECTATIONS = Object.freeze({
  "phase3-core": Object.freeze({
    selectedCostUsd: "316.8790274572",
    historicalReviewedArmSumCostUsd: "972.169845489198",
    historicalSourceScopeCostUsd: "972.169845489198",
    sourceScopeReconciliationAdjustmentUsd: "0",
    sourceScopeTransformedSelectedCostUsd:
      "316.879027457200",
    relationCounts: Object.freeze({
      exact: 4,
      estimate: 6,
      lowerBound: 5,
      historicalFallback: 0,
    }),
  }),
  "phase3-extended": Object.freeze({
    selectedCostUsd: "343.4494304572",
    historicalReviewedArmSumCostUsd: "1002.984164889198",
    historicalSourceScopeCostUsd: "1002.9841648891979",
    sourceScopeReconciliationAdjustmentUsd:
      "-0.0000000000001",
    sourceScopeTransformedSelectedCostUsd:
      "343.4494304571999",
    relationCounts: Object.freeze({
      exact: 4,
      estimate: 7,
      lowerBound: 5,
      historicalFallback: 0,
    }),
  }),
});

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
  const expectedParts = decimalParts(
    expected,
    "expected decimal",
  );
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

function sumDecimalStrings(values: readonly string[]): string {
  if (!values.length) return "0";

  const parts = values.map((value) =>
    decimalParts(value, "decimal sum")
  );
  const scale = Math.max(...parts.map((value) => value.scale));
  const total = parts.reduce(
    (sum, value) => sum + scaleUnits(value, scale),
    0n,
  );

  const negative = total < 0n;
  const absolute = negative ? -total : total;

  if (scale === 0) {
    return `${negative ? "-" : ""}${absolute.toString()}`;
  }

  const padded = absolute
    .toString()
    .padStart(scale + 1, "0");

  const whole = padded.slice(0, -scale);
  const fraction = padded
    .slice(-scale)
    .replace(/0+$/, "");

  return (
    `${negative ? "-" : ""}${whole}`
    + `${fraction ? `.${fraction}` : ""}`
  );
}

function isNonnegativeDecimal(value: string): boolean {
  return decimalParts(value, "nonnegative decimal").units >= 0n;
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

  const quotientUlp =
    10n ** BigInt(scale - quotientParts.scale);

  return (
    2n * difference
    <= divisorUnits * quotientUlp
  );
}

function nonnegativeInteger(
  value: unknown,
  label: string,
): number {
  if (
    typeof value !== "number"
    || !Number.isInteger(value)
    || value < 0
  ) {
    throw new Error(`${label} must be a nonnegative integer`);
  }
  return value;
}

function nullableNonnegativeInteger(
  value: unknown,
  label: string,
): number | null {
  return value === null
    ? null
    : nonnegativeInteger(value, label);
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

function stringArray(
  value: unknown,
  label: string,
): readonly string[] {
  if (
    !Array.isArray(value)
    || value.some(
      (item) => typeof item !== "string" || !item.length,
    )
  ) {
    throw new Error(`${label} must be a string array`);
  }

  return Object.freeze([...value] as string[]);
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
    throw new Error(
      `${label} has unsupported or missing fields`,
    );
  }
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

function validateInputs(
  value: unknown,
): Phase3CurrentReviewedComparison["inputs"] {
  if (
    !Array.isArray(value)
    || value.length !== EXPECTED_INPUTS.size
  ) {
    throw new Error(
      "inputs must contain exactly the reviewed v4 sources",
    );
  }

  const seen = new Set<string>();

  const inputs = value.map((raw, index) => {
    const item = record(raw, `inputs[${index}]`);

    assertExactKeys(
      item,
      ["path", "role", "sha256"],
      `inputs[${index}]`,
    );

    const path = text(
      item.path,
      `inputs[${index}].path`,
    );
    const role = text(
      item.role,
      `inputs[${index}].role`,
    );
    const sha256 = text(
      item.sha256,
      `inputs[${index}].sha256`,
    );

    if (!SHA256_PATTERN.test(sha256)) {
      throw new Error(
        `inputs[${index}].sha256 is invalid`,
      );
    }

    const expected = EXPECTED_INPUTS.get(path);

    if (
      !expected
      || expected.role !== role
      || expected.sha256 !== sha256
      || seen.has(path)
    ) {
      throw new Error(
        "current reviewed input provenance is invalid",
      );
    }

    seen.add(path);

    return Object.freeze({
      path,
      role,
      sha256,
    });
  });

  return Object.freeze(inputs);
}

function validateProviderEvidenceAudit(
  value: unknown,
  label: string,
): CurrentProviderEvidenceAudit {
  const item = record(value, label);

  assertExactKeys(
    item,
    [
      "auditConclusion",
      "auditScope",
      "pricingProvenanceStatus",
      "provider",
      "providerContextAccountSpendUsd",
      "providerContextAllocationConfidence",
      "providerContextOverheadUsd",
      "providerContextRateReconstructionExcessVsSelectedUsd",
      "providerContextRateReconstructionUsd",
      "providerContextTemporalRelation",
      "selectedCacheTokens",
      "selectedInputTokens",
      "selectedOutputTokens",
      "trajectoryEvidenceStatus",
    ],
    label,
  );

  return Object.freeze({
    provider: text(item.provider, `${label}.provider`),
    auditScope: text(
      item.auditScope,
      `${label}.auditScope`,
    ),
    pricingProvenanceStatus: text(
      item.pricingProvenanceStatus,
      `${label}.pricingProvenanceStatus`,
    ),
    trajectoryEvidenceStatus: text(
      item.trajectoryEvidenceStatus,
      `${label}.trajectoryEvidenceStatus`,
    ),
    providerContextTemporalRelation: text(
      item.providerContextTemporalRelation,
      `${label}.providerContextTemporalRelation`,
    ),
    providerContextAllocationConfidence: text(
      item.providerContextAllocationConfidence,
      `${label}.providerContextAllocationConfidence`,
    ),
    auditConclusion: text(
      item.auditConclusion,
      `${label}.auditConclusion`,
    ),
    providerContextAccountSpendUsd: nullableDecimal(
      item.providerContextAccountSpendUsd,
      `${label}.providerContextAccountSpendUsd`,
    ),
    providerContextOverheadUsd: nullableDecimal(
      item.providerContextOverheadUsd,
      `${label}.providerContextOverheadUsd`,
    ),
    providerContextRateReconstructionUsd: nullableDecimal(
      item.providerContextRateReconstructionUsd,
      `${label}.providerContextRateReconstructionUsd`,
    ),
    providerContextRateReconstructionExcessVsSelectedUsd:
      nullableDecimal(
        item.providerContextRateReconstructionExcessVsSelectedUsd,
        `${label}.providerContextRateReconstructionExcessVsSelectedUsd`,
      ),
    selectedInputTokens: nullableDecimal(
      item.selectedInputTokens,
      `${label}.selectedInputTokens`,
    ),
    selectedCacheTokens: nullableDecimal(
      item.selectedCacheTokens,
      `${label}.selectedCacheTokens`,
    ),
    selectedOutputTokens: nullableDecimal(
      item.selectedOutputTokens,
      `${label}.selectedOutputTokens`,
    ),
  });
}

function validateHistoricalFallback(
  arm: CurrentReviewedPhase3Arm,
  historical: ReviewedPhase3Arm,
  label: string,
): void {
  const nullableCurrentFields = [
    arm.currentSelectedRunLabel,
    arm.providerBilledCostUsd,
    arm.providerContextBilledCostUsd,
    arm.providerContextScope,
    arm.providerContextExcessUsd,
    arm.completeTrialCostCount,
    arm.lowerBoundTrialCount,
    arm.confirmedZeroCostTrialCount,
    arm.selectedCleanSuccessCostUsd,
    arm.selectedNormalFailureCostUsd,
    arm.selectedExceptionFailureCostUsd,
    arm.selectedExceptionWithSuccessSignalCostUsd,
    arm.knownAllocatedCostUsd,
    arm.unallocatedKnownCostUsd,
  ];

  if (
    arm.currentReconciliationStatus !== "historical_fallback"
    || arm.currentRoutingAliases.length !== 0
    || arm.currentProviderModels.length !== 0
    || nullableCurrentFields.some((value) => value !== null)
    || arm.selectedCostRelation !== "historical_fallback"
    || arm.selectedEfficiencyRelation !== "historical_fallback"
    || arm.selectedCostBasis !== historical.costBasis
    || arm.selectedCostConfidence !== historical.costConfidence
    || arm.selectedCostUsd !== historicalReviewedCost(historical)
    || arm.providerBillingReconciliationStatus
      !== "not_available_in_current_reconciliation_layer"
    || arm.selectedTrialCostAllocationStatus
      !== historical.trialAllocationStatus
    || arm.selectedOutcomeCostAllocationStatus
      !== historical.outcomeCostAllocationStatus
    || arm.evidenceClass !== "historical_reviewed_fallback"
    || arm.unquantifiedAdditionalCostStatus
      !== "not_evaluated_current_reconciliation"
  ) {
    throw new Error(
      `${label} historical fallback contract is invalid`,
    );
  }
}

function validateAllocatedCurrentCost(
  arm: CurrentReviewedPhase3Arm,
  label: string,
): void {
  const buckets = [
    arm.selectedCleanSuccessCostUsd,
    arm.selectedNormalFailureCostUsd,
    arm.selectedExceptionFailureCostUsd,
    arm.selectedExceptionWithSuccessSignalCostUsd,
  ];

  if (
    buckets.some((value) => value === null)
    || arm.knownAllocatedCostUsd === null
    || arm.unallocatedKnownCostUsd === null
  ) {
    throw new Error(
      `${label} selected current allocation is incomplete`,
    );
  }

  const allocated = buckets as string[];

  if (
    !decimalSumEquals(
      allocated,
      arm.knownAllocatedCostUsd,
    )
    || !decimalSumEquals(
      [
        arm.knownAllocatedCostUsd,
        arm.unallocatedKnownCostUsd,
      ],
      arm.selectedCostUsd,
    )
  ) {
    throw new Error(
      `${label} selected current allocation does not reconcile`,
    );
  }
}

function validateReconciledArm(
  arm: CurrentReviewedPhase3Arm,
  label: string,
): void {
  if (
    arm.currentReconciliationStatus !== "reconciled"
    || arm.currentSelectedRunLabel === null
    || arm.currentRoutingAliases.length === 0
    || arm.currentProviderModels.length === 0
    || arm.selectedCostRelation
      !== arm.selectedEfficiencyRelation
  ) {
    throw new Error(
      `${label} reconciled current identity is invalid`,
    );
  }

  const complete = arm.completeTrialCostCount;
  const lower = arm.lowerBoundTrialCount;
  const zero = arm.confirmedZeroCostTrialCount;
  const unresolved = arm.currentUnresolvedTrialCount;

  if (
    complete === null
    || lower === null
    || zero === null
    || unresolved === null
    || complete > arm.trialCount
    || lower > arm.trialCount
    || zero > arm.trialCount
    || unresolved > arm.trialCount
  ) {
    throw new Error(
      `${label} reconciled trial-count coverage is invalid`,
    );
  }

  if (arm.providerContextExcessUsd !== null) {
    if (
      arm.providerContextBilledCostUsd === null
      || !decimalSumEquals(
        [
          arm.selectedCostUsd,
          arm.providerContextExcessUsd,
        ],
        arm.providerContextBilledCostUsd,
      )
    ) {
      throw new Error(
        `${label} provider-context excess does not reconcile`,
      );
    }
  }

  if (arm.selectedCostBasis === "provider_billed") {
    if (
      arm.selectedCostRelation !== "exact"
      || arm.evidenceClass !== "exact_provider_arm_total"
      || arm.providerBilledCostUsd !== arm.selectedCostUsd
      || arm.providerContextBilledCostUsd !== arm.selectedCostUsd
      || arm.providerContextScope !== "exact_arm_total"
      || arm.providerContextExcessUsd !== "0"
      || arm.providerBillingReconciliationStatus
        !== "exact_arm_total"
      || complete !== 0
      || lower !== 0
      || unresolved !== 0
      || zero !== 0
      || arm.selectedTrialCostAllocationStatus
        !== "unavailable_provider_aggregate"
      || arm.selectedOutcomeCostAllocationStatus
        !== "unavailable_provider_aggregate"
      || arm.selectedCleanSuccessCostUsd !== null
      || arm.selectedNormalFailureCostUsd !== null
      || arm.selectedExceptionFailureCostUsd !== null
      || arm.selectedExceptionWithSuccessSignalCostUsd !== null
      || arm.knownAllocatedCostUsd !== "0"
      || arm.unallocatedKnownCostUsd !== arm.selectedCostUsd
      || arm.unquantifiedAdditionalCostStatus !== "none"
    ) {
      throw new Error(
        `${label} exact provider-billed contract is invalid`,
      );
    }
    return;
  }

  if (arm.providerBilledCostUsd !== null) {
    throw new Error(
      `${label} non-billed selected cost has provider-billed value`,
    );
  }

  const outcomeStatus =
    arm.selectedOutcomeCostAllocationStatus;

  if (
    outcomeStatus === "available_provider_rate_reconstruction"
    || outcomeStatus === "available_lower_bound"
    || outcomeStatus === "available_partial_estimate"
  ) {
    validateAllocatedCurrentCost(arm, label);

    if (arm.unallocatedKnownCostUsd !== "0") {
      throw new Error(
        `${label} allocated selected cost has an unexpected residual`,
      );
    }
  } else if (
    outcomeStatus === "unavailable_no_reviewed_outcome_join"
  ) {
    if (
      arm.selectedCleanSuccessCostUsd !== null
      || arm.selectedNormalFailureCostUsd !== null
      || arm.selectedExceptionFailureCostUsd !== null
      || arm.selectedExceptionWithSuccessSignalCostUsd !== null
      || arm.knownAllocatedCostUsd !== arm.selectedCostUsd
      || arm.unallocatedKnownCostUsd !== "0"
    ) {
      throw new Error(
        `${label} unavailable outcome-join contract is invalid`,
      );
    }
  } else if (
    outcomeStatus !== "unavailable_provider_aggregate"
  ) {
    throw new Error(
      `${label} reconciled outcome allocation status is unsupported`,
    );
  }

  if (arm.selectedCostRelation === "exact") {
    if (
      arm.selectedCostBasis
        !== "provider_rate_reconstructed_retained_usage"
      || complete !== arm.trialCount
      || lower !== 0
      || unresolved !== 0
      || arm.selectedTrialCostAllocationStatus
        !== "available_provider_rate_reconstruction"
      || outcomeStatus
        !== "available_provider_rate_reconstruction"
      || arm.unquantifiedAdditionalCostStatus !== "none"
    ) {
      throw new Error(
        `${label} exact retained-usage contract is invalid`,
      );
    }
    return;
  }

  if (arm.selectedCostRelation === "lower_bound") {
    if (
      arm.selectedCostBasis
        !== "provider_rate_reconstructed_retained_usage_lower_bound"
      || lower <= 0
      || complete + lower !== arm.trialCount
      || unresolved !== lower
      || ![
        "available_with_exception_path_lower_bounds",
        "available_with_unresolved_usage_lower_bounds",
      ].includes(arm.selectedTrialCostAllocationStatus)
      || outcomeStatus !== "available_lower_bound"
      || ![
        "possible_additional_exception_path_spend",
        "possible_additional_unresolved_trial_spend",
      ].includes(arm.unquantifiedAdditionalCostStatus)
    ) {
      throw new Error(
        `${label} lower-bound selected-cost contract is invalid`,
      );
    }
    return;
  }

  if (arm.selectedCostRelation === "estimate") {
    if (
      arm.selectedCostBasis
        === "provider_rate_reconstructed_retained_usage_partial"
    ) {
      if (
        lower !== 0
        || unresolved <= 0
        || complete + unresolved !== arm.trialCount
        || arm.selectedTrialCostAllocationStatus
          !== "partial_selected_usage_reconstruction_with_unresolved_trials"
        || outcomeStatus !== "available_partial_estimate"
        || arm.unquantifiedAdditionalCostStatus
          !== "unresolved_trial_spend_and_cache_classification_uncertainty"
      ) {
        throw new Error(
          `${label} partial selected-cost estimate is invalid`,
        );
      }
      return;
    }

    if (
      ![
        "provider_rate_reconstructed_selected_run",
        "provider_rate_reconstructed_selected_run_request_tier",
      ].includes(arm.selectedCostBasis)
      || complete !== arm.trialCount
      || lower !== 0
      || unresolved !== 0
      || arm.selectedTrialCostAllocationStatus
        !== "available_provider_rate_reconstruction"
      || ![
        "available_provider_rate_reconstruction",
        "unavailable_no_reviewed_outcome_join",
      ].includes(outcomeStatus)
      || ![
        "none",
        "none_for_selected_retained_usage",
      ].includes(arm.unquantifiedAdditionalCostStatus)
    ) {
      throw new Error(
        `${label} selected-run provider-rate estimate is invalid`,
      );
    }
    return;
  }

  throw new Error(
    `${label} reconciled selected-cost relation is unsupported`,
  );
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

    "currentReconciliationStatus",
    "currentSelectedRunLabel",
    "currentRoutingAliases",
    "currentProviderModels",
    "currentEvidenceNote",

    "selectedCostRelation",
    "selectedEfficiencyRelation",
    "selectedCostBasis",
    "selectedCostConfidence",
    "selectedCostPerAnySuccessUsd",
    "selectedCostPerAttemptUsd",
    "selectedCostPerCleanSuccessUsd",
    "selectedCostUsd",

    "evidenceClass",

    "providerBilledCostUsd",
    "providerContextBilledCostUsd",
    "providerContextScope",
    "providerContextExcessUsd",
    "providerBillingReconciliationStatus",

    "completeTrialCostCount",
    "lowerBoundTrialCount",
    "confirmedZeroCostTrialCount",
    "currentUnresolvedTrialCount",

    "selectedTrialCostAllocationStatus",
    "selectedOutcomeCostAllocationStatus",

    "selectedCleanSuccessCostUsd",
    "selectedNormalFailureCostUsd",
    "selectedExceptionFailureCostUsd",
    "selectedExceptionWithSuccessSignalCostUsd",
    "knownAllocatedCostUsd",
    "unallocatedKnownCostUsd",
    "unquantifiedAdditionalCostStatus",
    "providerEvidenceAudit",
  ];

  assertExactKeys(
    item,
    [...Object.keys(historical), ...extraKeys],
    label,
  );

  for (
    const [key, historicalValue]
    of Object.entries(historical)
  ) {
    if (!sameJson(item[key], historicalValue)) {
      throw new Error(
        `${label}.${key} does not preserve the frozen historical arm`,
      );
    }
  }

  const arm: CurrentReviewedPhase3Arm = Object.freeze({
    ...historical,

    historicalHarnessRecordedCostUsd: decimal(
      item.historicalHarnessRecordedCostUsd,
      `${label}.historicalHarnessRecordedCostUsd`,
    ),
    historicalReviewedCostBasis: exact(
      item.historicalReviewedCostBasis,
      [
        "adjusted_known_cost",
        "qualified_retained_rate_estimate",
      ] as const,
      `${label}.historicalReviewedCostBasis`,
    ),
    historicalReviewedCostUsd: decimal(
      item.historicalReviewedCostUsd,
      `${label}.historicalReviewedCostUsd`,
    ),

    currentReconciliationStatus: exact(
      item.currentReconciliationStatus,
      ["reconciled", "historical_fallback"] as const,
      `${label}.currentReconciliationStatus`,
    ),
    currentSelectedRunLabel: nullableText(
      item.currentSelectedRunLabel,
      `${label}.currentSelectedRunLabel`,
    ),
    currentRoutingAliases: stringArray(
      item.currentRoutingAliases,
      `${label}.currentRoutingAliases`,
    ),
    currentProviderModels: stringArray(
      item.currentProviderModels,
      `${label}.currentProviderModels`,
    ),
    currentEvidenceNote: text(
      item.currentEvidenceNote,
      `${label}.currentEvidenceNote`,
    ),

    selectedCostRelation: exact(
      item.selectedCostRelation,
      [
        "exact",
        "estimate",
        "lower_bound",
        "historical_fallback",
      ] as const,
      `${label}.selectedCostRelation`,
    ),
    selectedEfficiencyRelation: exact(
      item.selectedEfficiencyRelation,
      [
        "exact",
        "estimate",
        "lower_bound",
        "historical_fallback",
      ] as const,
      `${label}.selectedEfficiencyRelation`,
    ),
    selectedCostBasis: exact(
      item.selectedCostBasis,
      [
        "adjusted_known_cost",
        "qualified_retained_rate_estimate",
        "provider_billed",
        "provider_rate_reconstructed_retained_usage",
        "provider_rate_reconstructed_retained_usage_lower_bound",
        "provider_rate_reconstructed_retained_usage_partial",
        "provider_rate_reconstructed_selected_run",
        "provider_rate_reconstructed_selected_run_request_tier",
      ] as const,
      `${label}.selectedCostBasis`,
    ),
    selectedCostConfidence: text(
      item.selectedCostConfidence,
      `${label}.selectedCostConfidence`,
    ),
    selectedCostPerAnySuccessUsd: decimal(
      item.selectedCostPerAnySuccessUsd,
      `${label}.selectedCostPerAnySuccessUsd`,
    ),
    selectedCostPerAttemptUsd: decimal(
      item.selectedCostPerAttemptUsd,
      `${label}.selectedCostPerAttemptUsd`,
    ),
    selectedCostPerCleanSuccessUsd: decimal(
      item.selectedCostPerCleanSuccessUsd,
      `${label}.selectedCostPerCleanSuccessUsd`,
    ),
    selectedCostUsd: decimal(
      item.selectedCostUsd,
      `${label}.selectedCostUsd`,
    ),

    evidenceClass: exact(
      item.evidenceClass,
      [
        "exact_provider_arm_total",
        "historical_reviewed_fallback",
        "provider_rate_reconstruction_with_same_day_provider_crosscheck",
        "verified_retained_artifacts_plus_official_provider_rates",
        "verified_retained_trajectories_plus_official_provider_rates",
        "verified_retained_trajectories_plus_provider_bill_validated_rates",
        "retained_artifacts_plus_official_provider_rates_trajectory_archive_unavailable",
        "complete_retained_usage_plus_provider_dashboard_validated_rates",
        "complete_retained_usage_plus_retained_published_rates",
        "partial_retained_usage_plus_retained_published_rates_cache_accounting_unverified",
        "complete_retained_usage_plus_retained_rate_constants_qualified_provenance",
      ] as const,
      `${label}.evidenceClass`,
    ),

    providerBilledCostUsd: nullableDecimal(
      item.providerBilledCostUsd,
      `${label}.providerBilledCostUsd`,
    ),
    providerContextBilledCostUsd: nullableDecimal(
      item.providerContextBilledCostUsd,
      `${label}.providerContextBilledCostUsd`,
    ),
    providerContextScope:
      item.providerContextScope === null
        ? null
        : exact(
            item.providerContextScope,
            [
              "exact_arm_total",
              "same_day_model_aggregate",
              "preselected_family_dashboard_total_through_2026-06-19",
              "preselected_glm5.1_provider_billing_table_through_2026-06-19",
              "glm5.1_billing_evidence_is_same_family_but_different_model",
              "shared_preselected_gemini_family_billing_export_through_2026-06-17_nonadditive",
              "preselected_qwen_payg_bill_detail_through_2026-06-19",
              "preselected_request_logs_and_dashboard_total_2026-06-04_to_2026-06-16",
              "broader_provider_request_log_retained_rate_reconstruction",
            ] as const,
            `${label}.providerContextScope`,
          ),
    providerContextExcessUsd: nullableDecimal(
      item.providerContextExcessUsd,
      `${label}.providerContextExcessUsd`,
    ),
    providerBillingReconciliationStatus: exact(
      item.providerBillingReconciliationStatus,
      [
        "exact_arm_total",
        "not_available_in_current_reconciliation_layer",
        "preselected_family_billing_context_not_selected_run",
        "preselected_provider_context_not_selected_run",
        "provider_invoice_unavailable",
        "provider_log_not_invoice_level_allocation_low_confidence",
        "same_day_model_aggregate_not_run_isolated",
        "selected_run_provider_invoice_unavailable",
      ] as const,
      `${label}.providerBillingReconciliationStatus`,
    ),

    completeTrialCostCount: nullableNonnegativeInteger(
      item.completeTrialCostCount,
      `${label}.completeTrialCostCount`,
    ),
    lowerBoundTrialCount: nullableNonnegativeInteger(
      item.lowerBoundTrialCount,
      `${label}.lowerBoundTrialCount`,
    ),
    confirmedZeroCostTrialCount: nullableNonnegativeInteger(
      item.confirmedZeroCostTrialCount,
      `${label}.confirmedZeroCostTrialCount`,
    ),
    currentUnresolvedTrialCount: nullableNonnegativeInteger(
      item.currentUnresolvedTrialCount,
      `${label}.currentUnresolvedTrialCount`,
    ),

    selectedTrialCostAllocationStatus: exact(
      item.selectedTrialCostAllocationStatus,
      [
        "available_for_reviewed_layer",
        "available_provider_rate_reconstruction",
        "available_with_exception_path_lower_bounds",
        "available_with_unresolved_usage_lower_bounds",
        "partial_selected_usage_reconstruction_with_unresolved_trials",
        "unavailable_provider_aggregate",
        "unresolved",
      ] as const,
      `${label}.selectedTrialCostAllocationStatus`,
    ),
    selectedOutcomeCostAllocationStatus: exact(
      item.selectedOutcomeCostAllocationStatus,
      [
        "available",
        "available_lower_bound",
        "available_partial_estimate",
        "available_provider_rate_reconstruction",
        "unavailable",
        "unavailable_no_reviewed_outcome_join",
        "unavailable_provider_aggregate",
      ] as const,
      `${label}.selectedOutcomeCostAllocationStatus`,
    ),

    selectedCleanSuccessCostUsd: nullableDecimal(
      item.selectedCleanSuccessCostUsd,
      `${label}.selectedCleanSuccessCostUsd`,
    ),
    selectedNormalFailureCostUsd: nullableDecimal(
      item.selectedNormalFailureCostUsd,
      `${label}.selectedNormalFailureCostUsd`,
    ),
    selectedExceptionFailureCostUsd: nullableDecimal(
      item.selectedExceptionFailureCostUsd,
      `${label}.selectedExceptionFailureCostUsd`,
    ),
    selectedExceptionWithSuccessSignalCostUsd: nullableDecimal(
      item.selectedExceptionWithSuccessSignalCostUsd,
      `${label}.selectedExceptionWithSuccessSignalCostUsd`,
    ),
    knownAllocatedCostUsd: nullableDecimal(
      item.knownAllocatedCostUsd,
      `${label}.knownAllocatedCostUsd`,
    ),
    unallocatedKnownCostUsd: nullableDecimal(
      item.unallocatedKnownCostUsd,
      `${label}.unallocatedKnownCostUsd`,
    ),
    unquantifiedAdditionalCostStatus: exact(
      item.unquantifiedAdditionalCostStatus,
      [
        "none",
        "none_for_selected_retained_usage",
        "not_evaluated_current_reconciliation",
        "possible_additional_exception_path_spend",
        "possible_additional_unresolved_trial_spend",
        "unresolved_trial_spend_and_cache_classification_uncertainty",
      ] as const,
      `${label}.unquantifiedAdditionalCostStatus`,
    ),
    providerEvidenceAudit: validateProviderEvidenceAudit(
      item.providerEvidenceAudit,
      `${label}.providerEvidenceAudit`,
    ),
  });

  if (
    arm.historicalHarnessRecordedCostUsd
      !== historical.recordedCostUsd
    || arm.historicalReviewedCostBasis
      !== historical.costBasis
    || arm.historicalReviewedCostUsd
      !== historicalReviewedCost(historical)
  ) {
    throw new Error(
      `${label} historical cost bridge does not match the frozen arm`,
    );
  }

  for (const [field, value] of [
    ["selectedCostUsd", arm.selectedCostUsd],
    ["selectedCostPerAttemptUsd", arm.selectedCostPerAttemptUsd],
    [
      "selectedCostPerCleanSuccessUsd",
      arm.selectedCostPerCleanSuccessUsd,
    ],
    [
      "selectedCostPerAnySuccessUsd",
      arm.selectedCostPerAnySuccessUsd,
    ],
  ] as const) {
    if (!isNonnegativeDecimal(value)) {
      throw new Error(
        `${label}.${field} must be nonnegative`,
      );
    }
  }

  if (
    !decimalRatioMatches(
      arm.selectedCostUsd,
      historical.trialCount,
      arm.selectedCostPerAttemptUsd,
    )
    || !decimalRatioMatches(
      arm.selectedCostUsd,
      historical.cleanSuccessCount,
      arm.selectedCostPerCleanSuccessUsd,
    )
    || !decimalRatioMatches(
      arm.selectedCostUsd,
      historical.successCount,
      arm.selectedCostPerAnySuccessUsd,
    )
  ) {
    throw new Error(
      `${label} selected-cost efficiency metrics are invalid`,
    );
  }

  if (arm.currentReconciliationStatus === "historical_fallback") {
    validateHistoricalFallback(
      arm,
      historical,
      label,
    );
  } else {
    validateReconciledArm(arm, label);
  }

  return arm;
}

function validateRelationCounts(
  value: unknown,
  label: string,
): CurrentSelectedCostRelationCounts {
  const item = record(value, label);

  assertExactKeys(
    item,
    [
      "exact",
      "estimate",
      "lowerBound",
      "historicalFallback",
    ],
    label,
  );

  return Object.freeze({
    exact: nonnegativeInteger(
      item.exact,
      `${label}.exact`,
    ),
    estimate: nonnegativeInteger(
      item.estimate,
      `${label}.estimate`,
    ),
    lowerBound: nonnegativeInteger(
      item.lowerBound,
      `${label}.lowerBound`,
    ),
    historicalFallback: nonnegativeInteger(
      item.historicalFallback,
      `${label}.historicalFallback`,
    ),
  });
}

function relationCountsForArms(
  arms: readonly CurrentReviewedPhase3Arm[],
): CurrentSelectedCostRelationCounts {
  return Object.freeze({
    exact: arms.filter(
      (arm) => arm.selectedCostRelation === "exact",
    ).length,
    estimate: arms.filter(
      (arm) => arm.selectedCostRelation === "estimate",
    ).length,
    lowerBound: arms.filter(
      (arm) => arm.selectedCostRelation === "lower_bound",
    ).length,
    historicalFallback: arms.filter(
      (arm) =>
        arm.selectedCostRelation === "historical_fallback",
    ).length,
  });
}

function validateSelectedCostEvidence(
  value: unknown,
  scopeId: CurrentReviewedPhase3ScopeId,
  arms: readonly CurrentReviewedPhase3Arm[],
): CurrentSelectedCostEvidence {
  const label = `${scopeId}.selectedCostEvidence`;
  const item = record(value, label);

  assertExactKeys(
    item,
    [
      "currentReconciledArmCount",
      "currentReconciledArmIds",
      "currentReconciledCostUsd",
      "currentReconciliationCoverageStatus",
      "exactProviderBilledArmCount",
      "exactProviderBilledArmIds",
      "exactProviderBilledCostUsd",
      "historicalReviewedArmSumCostUsd",
      "historicalSourceScopeCostUsd",
      "note",
      "outcomeAllocationStatus",
      "selectedCostBasis",
      "selectedCostRelation",
      "selectedCostRelationCounts",
      "selectedCostUsd",
      "sourceScopeReconciliationAdjustmentUsd",
      "sourceScopeTransformedSelectedCostUsd",
      "trialAllocationStatus",
      "unquantifiedAdditionalCostArmCount",
      "unquantifiedAdditionalCostArmIds",
    ],
    label,
  );

  const evidence: CurrentSelectedCostEvidence =
    Object.freeze({
      currentReconciledArmCount: nonnegativeInteger(
        item.currentReconciledArmCount,
        `${label}.currentReconciledArmCount`,
      ),
      currentReconciledArmIds: stringArray(
        item.currentReconciledArmIds,
        `${label}.currentReconciledArmIds`,
      ),
      currentReconciledCostUsd: decimal(
        item.currentReconciledCostUsd,
        `${label}.currentReconciledCostUsd`,
      ),
      currentReconciliationCoverageStatus: exact(
        item.currentReconciliationCoverageStatus,
        ["complete_by_arm"] as const,
        `${label}.currentReconciliationCoverageStatus`,
      ),

      exactProviderBilledArmCount: nonnegativeInteger(
        item.exactProviderBilledArmCount,
        `${label}.exactProviderBilledArmCount`,
      ),
      exactProviderBilledArmIds: stringArray(
        item.exactProviderBilledArmIds,
        `${label}.exactProviderBilledArmIds`,
      ),
      exactProviderBilledCostUsd: decimal(
        item.exactProviderBilledCostUsd,
        `${label}.exactProviderBilledCostUsd`,
      ),

      historicalReviewedArmSumCostUsd: decimal(
        item.historicalReviewedArmSumCostUsd,
        `${label}.historicalReviewedArmSumCostUsd`,
      ),
      historicalSourceScopeCostUsd: decimal(
        item.historicalSourceScopeCostUsd,
        `${label}.historicalSourceScopeCostUsd`,
      ),

      note: text(item.note, `${label}.note`),

      outcomeAllocationStatus: exact(
        item.outcomeAllocationStatus,
        ["mixed_by_arm"] as const,
        `${label}.outcomeAllocationStatus`,
      ),
      selectedCostBasis: exact(
        item.selectedCostBasis,
        ["mixed_best_available_arm_evidence"] as const,
        `${label}.selectedCostBasis`,
      ),
      selectedCostRelation: exact(
        item.selectedCostRelation,
        ["mixed_by_arm"] as const,
        `${label}.selectedCostRelation`,
      ),
      selectedCostRelationCounts: validateRelationCounts(
        item.selectedCostRelationCounts,
        `${label}.selectedCostRelationCounts`,
      ),
      selectedCostUsd: decimal(
        item.selectedCostUsd,
        `${label}.selectedCostUsd`,
      ),

      sourceScopeReconciliationAdjustmentUsd: decimal(
        item.sourceScopeReconciliationAdjustmentUsd,
        `${label}.sourceScopeReconciliationAdjustmentUsd`,
      ),
      sourceScopeTransformedSelectedCostUsd: decimal(
        item.sourceScopeTransformedSelectedCostUsd,
        `${label}.sourceScopeTransformedSelectedCostUsd`,
      ),

      trialAllocationStatus: exact(
        item.trialAllocationStatus,
        ["mixed_by_arm"] as const,
        `${label}.trialAllocationStatus`,
      ),

      unquantifiedAdditionalCostArmCount:
        nonnegativeInteger(
          item.unquantifiedAdditionalCostArmCount,
          `${label}.unquantifiedAdditionalCostArmCount`,
        ),
      unquantifiedAdditionalCostArmIds: stringArray(
        item.unquantifiedAdditionalCostArmIds,
        `${label}.unquantifiedAdditionalCostArmIds`,
      ),
    });

  const expected = SCOPE_EXPECTATIONS[scopeId];

  if (
    evidence.selectedCostUsd !== expected.selectedCostUsd
    || evidence.historicalReviewedArmSumCostUsd
      !== expected.historicalReviewedArmSumCostUsd
    || evidence.historicalSourceScopeCostUsd
      !== expected.historicalSourceScopeCostUsd
    || evidence.sourceScopeReconciliationAdjustmentUsd
      !== expected.sourceScopeReconciliationAdjustmentUsd
    || evidence.sourceScopeTransformedSelectedCostUsd
      !== expected.sourceScopeTransformedSelectedCostUsd
  ) {
    throw new Error(
      `${label} does not match the reviewed v4 scope anchors`,
    );
  }

  if (
    !decimalSumEquals(
      arms.map((arm) => arm.selectedCostUsd),
      evidence.selectedCostUsd,
    )
    || !decimalSumEquals(
      [
        evidence.selectedCostUsd,
        evidence.sourceScopeReconciliationAdjustmentUsd,
      ],
      evidence.sourceScopeTransformedSelectedCostUsd,
    )
  ) {
    throw new Error(
      `${label} selected arithmetic arm sum is invalid`,
    );
  }

  const reconciledArms = arms.filter(
    (arm) =>
      arm.currentReconciliationStatus === "reconciled",
  );
  const reconciledIds = reconciledArms
    .map((arm) => arm.armId)
    .sort();
  const expectedIds = arms
    .map((arm) => arm.armId)
    .sort();

  if (
    reconciledArms.length !== arms.length
    || evidence.currentReconciledArmCount !== arms.length
    || !sameJson(
      evidence.currentReconciledArmIds,
      reconciledIds,
    )
    || !sameJson(reconciledIds, expectedIds)
    || evidence.currentReconciledCostUsd
      !== evidence.selectedCostUsd
  ) {
    throw new Error(
      `${label} complete-by-arm reconciliation is invalid`,
    );
  }

  const billedArms = arms.filter(
    (arm) => arm.providerBilledCostUsd !== null,
  );
  const billedIds = billedArms
    .map((arm) => arm.armId)
    .sort();

  if (
    evidence.exactProviderBilledArmCount
      !== billedArms.length
    || !sameJson(
      evidence.exactProviderBilledArmIds,
      billedIds,
    )
    || !sameJson(
      billedIds,
      EXPECTED_EXACT_PROVIDER_BILLED_ARM_IDS,
    )
    || !decimalSumEquals(
      billedArms.map(
        (arm) => arm.providerBilledCostUsd as string,
      ),
      evidence.exactProviderBilledCostUsd,
    )
    || evidence.exactProviderBilledCostUsd
      !== "78.3968475"
  ) {
    throw new Error(
      `${label} exact provider-billed subtotal is invalid`,
    );
  }

  const derivedRelationCounts =
    relationCountsForArms(arms);

  if (
    !sameJson(
      evidence.selectedCostRelationCounts,
      derivedRelationCounts,
    )
    || !sameJson(
      derivedRelationCounts,
      expected.relationCounts,
    )
  ) {
    throw new Error(
      `${label} selected-cost relation counts are invalid`,
    );
  }

  const unquantifiedIds = arms
    .filter(
      (arm) =>
        ![
          "none",
          "none_for_selected_retained_usage",
        ].includes(arm.unquantifiedAdditionalCostStatus),
    )
    .map((arm) => arm.armId)
    .sort();

  if (
    evidence.unquantifiedAdditionalCostArmCount
      !== unquantifiedIds.length
    || !sameJson(
      evidence.unquantifiedAdditionalCostArmIds,
      unquantifiedIds,
    )
    || !sameJson(
      unquantifiedIds,
      EXPECTED_UNQUANTIFIED_ADDITIONAL_COST_ARM_IDS,
    )
  ) {
    throw new Error(
      `${label} unquantified additional-cost membership is invalid`,
    );
  }

  return evidence;
}

function validateScope(
  value: unknown,
  scopeId: CurrentReviewedPhase3ScopeId,
): CurrentReviewedPhase3Scope {
  const item = record(value, scopeId);
  const historical =
    PHASE3_REVIEWED_COMPARISON.scopes[scopeId];

  assertExactKeys(
    item,
    [
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
    ],
    scopeId,
  );

  if (
    item.scopeId !== historical.scopeId
    || item.displayName !== historical.displayName
    || item.presentationKind
      !== historical.presentationKind
    || item.snapshotDate !== historical.snapshotDate
    || item.armCount !== historical.armCount
    || item.trialCount !== historical.trialCount
    || item.successCount !== historical.successCount
    || finiteNumber(
      item.passRate,
      `${scopeId}.passRate`,
    ) !== historical.passRate
  ) {
    throw new Error(
      `${scopeId} does not preserve frozen reviewed scope identity`,
    );
  }

  if (
    !sameJson(
      item.historicalCostEvidence,
      historical.costEvidence,
    )
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
    throw new Error(
      `${scopeId}.arms must be an array`,
    );
  }

  if (item.arms.length !== historical.arms.length) {
    throw new Error(
      `${scopeId} arm membership changed`,
    );
  }

  const arms = item.arms.map((raw, index) => {
    const historicalArm = historical.arms[index];
    const rawArm = record(
      raw,
      `${scopeId}.arms[${index}]`,
    );

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

  const selectedCostEvidence =
    validateSelectedCostEvidence(
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
    historicalOutcomeCostCoverage:
      historical.outcomeCostCoverage,
    selectedCostEvidence,
  });
}

export type CurrentSelectedOutcomeCostEvidence =
  | Readonly<{
      status:
        | "available_lower_bound"
        | "available_partial_estimate"
        | "available_provider_rate_reconstruction";
      evidenceBasis:
        | "provider_rate_reconstruction"
        | "provider_rate_reconstruction_lower_bound"
        | "provider_rate_reconstruction_partial_estimate";
      adjustedCleanSuccessCostUsd: string;
      adjustedFailureOrIncompleteCostUsd: string;
      adjustedExceptionSuccessSignalCostUsd: string;
      failureOrIncompleteSpendShare: number;
      nonproductiveOrUncleanSpendShare: number;
    }>
  | Readonly<{
      status:
        | "unavailable_no_reviewed_outcome_join"
        | "unavailable_provider_aggregate";
      evidenceBasis: null;
      adjustedCleanSuccessCostUsd: null;
      adjustedFailureOrIncompleteCostUsd: null;
      adjustedExceptionSuccessSignalCostUsd: null;
      failureOrIncompleteSpendShare: null;
      nonproductiveOrUncleanSpendShare: null;
    }>;

export function getCurrentSelectedOutcomeCostEvidence(
  arm: CurrentReviewedPhase3Arm,
): CurrentSelectedOutcomeCostEvidence {
  const status = arm.selectedOutcomeCostAllocationStatus;

  if (
    status === "unavailable_no_reviewed_outcome_join"
    || status === "unavailable_provider_aggregate"
  ) {
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
    status !== "available_lower_bound"
    && status !== "available_partial_estimate"
    && status !== "available_provider_rate_reconstruction"
  ) {
    throw new Error(
      `${arm.armId} has an unsupported current outcome allocation`,
    );
  }

  if (
    arm.selectedCleanSuccessCostUsd === null
    || arm.selectedNormalFailureCostUsd === null
    || arm.selectedExceptionFailureCostUsd === null
    || arm.selectedExceptionWithSuccessSignalCostUsd === null
  ) {
    throw new Error(
      `${arm.armId} current selected outcome allocation is incomplete`,
    );
  }

  const failureOrIncomplete =
    sumDecimalStrings([
      arm.selectedNormalFailureCostUsd,
      arm.selectedExceptionFailureCostUsd,
    ]);

  const nonproductiveOrUnclean =
    sumDecimalStrings([
      failureOrIncomplete,
      arm.selectedExceptionWithSuccessSignalCostUsd,
    ]);

  const selected = Number(arm.selectedCostUsd);
  const failure = Number(failureOrIncomplete);
  const nonproductive = Number(nonproductiveOrUnclean);

  if (
    !Number.isFinite(selected)
    || selected <= 0
    || !Number.isFinite(failure)
    || !Number.isFinite(nonproductive)
  ) {
    throw new Error(
      `${arm.armId} current selected outcome shares are invalid`,
    );
  }

  const evidenceBasis =
    status === "available_lower_bound"
      ? "provider_rate_reconstruction_lower_bound"
      : status === "available_partial_estimate"
        ? "provider_rate_reconstruction_partial_estimate"
        : "provider_rate_reconstruction";

  return Object.freeze({
    status,
    evidenceBasis,
    adjustedCleanSuccessCostUsd:
      arm.selectedCleanSuccessCostUsd,
    adjustedFailureOrIncompleteCostUsd:
      failureOrIncomplete,
    adjustedExceptionSuccessSignalCostUsd:
      arm.selectedExceptionWithSuccessSignalCostUsd,
    failureOrIncompleteSpendShare:
      failure / selected,
    nonproductiveOrUncleanSpendShare:
      nonproductive / selected,
  });
}

export function validatePhase3CurrentReviewedComparison(
  value: unknown,
): Phase3CurrentReviewedComparison {
  const item = record(
    value,
    "current reviewed comparison",
  );

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

  if (item.reviewedAt !== "2026-08-25") {
    throw new Error(
      "current reviewed comparison reviewedAt is invalid",
    );
  }

  if (item.historicalReviewedAt !== "2026-08-05") {
    throw new Error(
      "current reviewed comparison historicalReviewedAt is invalid",
    );
  }

  const generator = record(
    item.generator,
    "generator",
  );

  assertExactKeys(
    generator,
    ["name", "version"],
    "generator",
  );

  if (
    generator.name
      !== "scripts/generate_phase3_current_reviewed_comparison_v4.py"
    || generator.version !== "3.0.0"
  ) {
    throw new Error(
      "current reviewed comparison generator identity is invalid",
    );
  }

  const inputs = validateInputs(item.inputs);
  const scopesRaw = record(
    item.scopes,
    "scopes",
  );

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
    core.arms.some(
      (arm) => arm.armId === "router-kimi-k3",
    )
    || !extended.arms.some(
      (arm) => arm.armId === "router-kimi-k3",
    )
  ) {
    throw new Error(
      "current reviewed Kimi K3 scope membership is invalid",
    );
  }

  return Object.freeze({
    schemaVersion:
      PHASE3_CURRENT_REVIEWED_COMPARISON_SCHEMA_VERSION,
    reviewedAt: "2026-08-25",
    historicalReviewedAt: "2026-08-05",
    generator: Object.freeze({
      name:
        "scripts/generate_phase3_current_reviewed_comparison_v4.py",
      version: "3.0.0",
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

  if (
    value === null
    || value === undefined
    || value === ""
  ) {
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

  if (
    value === "phase3-core"
    || value === "phase3-extended"
  ) {
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
