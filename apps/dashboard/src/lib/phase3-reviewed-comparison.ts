import reviewedSnapshotJson from "../generated/phase3-reviewed-comparison-data";

export const PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION = "phase3-reviewed-comparison-v1" as const;
export type ReviewedPhase3ScopeId = "phase3-core" | "phase3-extended";

export type ReviewedComparisonInput = Readonly<{
  path: string;
  role: string;
  sha256: string;
}>;

export type ReviewedCostEvidence = Readonly<{
  recordedCostUsd: string;
  adjustedKnownCostUsd: string | null;
  qualifiedAdjustedCostEstimateUsd: string | null;
  accountingGapUsd: string;
  costBasis: "adjusted_known_cost" | "qualified_adjusted_cost_estimate";
  costLabel: string;
  pricingProvenanceStatus: "historical_reviewed_layer" | "incomplete";
  armRunAllocationConfidence: "mixed_by_arm" | "low";
  trialAllocationStatus: "available_for_reviewed_layer" | "unresolved";
  billingReconciliationStatus: "not_invoice_level" | "not_invoice_level_or_provider_billed";
  outcomeCostAllocationStatus: "available" | "partial_core_only";
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  adjustedCleanSuccessCostUsd: string | null;
  adjustedExceptionSuccessSignalCostUsd: string | null;
  adjustedFailureOrIncompleteCostUsd: string | null;
  failureOrIncompleteSpendShare: number | null;
  nonproductiveOrUncleanSpendShare: number | null;
  adjustedCostPerCleanSuccessUsd: string | null;
  adjustedCostPerAnySuccessUsd: string | null;
  costSources: readonly string[];
  costConfidence: string;
  sourcePaths: readonly string[];
}>;

export type ReviewedPhase3Arm = Readonly<{
  armId: string;
  backendModel: string;
  provider: string;
  routingPath: string;
  trialCount: number;
  successCount: number;
  cleanSuccessCount: number;
  exceptionSuccessSignalCount: number;
  failureOrIncompleteCount: number;
  passRate: number;
  recordedCostUsd: string;
  adjustedKnownCostUsd: string | null;
  qualifiedRetainedRateCostUsd: string | null;
  accountingGapUsd: string;
  adjustedCostPerCleanSuccessUsd: string | null;
  adjustedCostPerAnySuccessUsd: string | null;
  adjustedCleanSuccessCostUsd: string | null;
  adjustedExceptionSuccessSignalCostUsd: string | null;
  adjustedFailureOrIncompleteCostUsd: string | null;
  failureOrIncompleteSpendShare: number | null;
  nonproductiveOrUncleanSpendShare: number | null;
  medianWallClockSeconds: number | null;
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  costSources: readonly string[];
  costConfidence: string;
  costBasis: "adjusted_known_cost" | "qualified_retained_rate_estimate";
  pricingProvenanceStatus: "historical_reviewed_layer" | "incomplete";
  armRunAllocationConfidence: "reviewed_core_layer" | "low";
  trialAllocationStatus: "available_for_reviewed_layer" | "unresolved";
  billingReconciliationStatus: "not_invoice_level" | "not_invoice_level_or_provider_billed";
  outcomeCostAllocationStatus: "available" | "unavailable";
  sourcePaths: readonly string[];
}>;

export type ReviewedOutcomeCostRow = Readonly<{
  outcomeBucket: string;
  trialCount: number;
  recordedCostUsd: string;
  sourceAdjustedKnownCostUsd: string;
  sourceAccountingGapUsd: string;
  missingRecordedCostCount: number;
  unresolvedAdjustedCostCount: number;
}>;

export type ReviewedOutcomeCostCoverage = Readonly<{
  status: "available" | "partial_core_only";
  coveredTrialCount: number;
  excludedTrialCount: number;
  excludedArmIds: readonly string[];
  sourceAdjustedKnownCostTotalUsd: string;
  reviewedAdjustedKnownCostTotalUsd: string;
  reviewedScopeReconciliationAdjustmentUsd: string;
  rows: readonly ReviewedOutcomeCostRow[];
}>;

export type ReviewedPhase3Scope = Readonly<{
  scopeId: ReviewedPhase3ScopeId;
  displayName: string;
  presentationKind: "historical_reviewed_snapshot" | "current_reviewed_corpus";
  snapshotDate: string;
  armCount: number;
  trialCount: number;
  successCount: number;
  passRate: number;
  costEvidence: ReviewedCostEvidence;
  outcomeCostCoverage: ReviewedOutcomeCostCoverage;
  arms: readonly ReviewedPhase3Arm[];
}>;

export type Phase3ReviewedComparison = Readonly<{
  schemaVersion: typeof PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION;
  reviewedAt: string;
  generator: Readonly<{ name: string; version: string }>;
  inputs: readonly ReviewedComparisonInput[];
  scopes: Readonly<Record<ReviewedPhase3ScopeId, ReviewedPhase3Scope>>;
}>;

export type ReviewedScopeSelection = Readonly<{
  scopeId: ReviewedPhase3ScopeId;
  scope: ReviewedPhase3Scope;
  warning: "invalid_scope" | "repeated_scope" | null;
  warningMessage: string | null;
  usedDefault: boolean;
}>;

const DECIMAL_PATTERN = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;
const SCOPE_IDS: readonly ReviewedPhase3ScopeId[] = ["phase3-core", "phase3-extended"];
const EXPECTED_REVIEWED_AT = "2026-08-05";
const EXPECTED_GENERATOR_NAME = "scripts/generate_phase3_extended_reviewed_comparison.py";
const EXPECTED_GENERATOR_VERSION = "1.0.0";
const EXPECTED_INPUT_ROLES = new Map<string, string>([
  ["docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md", "kimi_quality_source"],
  ["docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md", "kimi_cost_qualification_source"],
  ["results/phase1/combined.csv", "phase1_quality_source"],
  ["results/phase2/combined.csv", "phase2_quality_source"],
  ["results/phase3/reporting/cross_phase_adjusted_comparison_20260714.tsv", "cross_phase_quality_and_cost_confirmation"],
  ["results/phase3/reporting/kimi_k3_provider_log_reconciliation_20260805.csv", "kimi_cost_arithmetic_source"],
  ["results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv", "phase3_core_arm_cost_source"],
  ["results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv", "phase3_core_quality_and_cost_source"],
  ["results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv", "phase3_core_trial_cost_source"],
]);
const OUTCOME_BUCKET_ORDER = [
  "clean_success",
  "exception_with_success_signal",
  "normal_failure",
  "exception_failure",
] as const;
const EXPECTED_CORE_OUTCOME_ROWS: readonly ReviewedOutcomeCostRow[] = [
  {
    outcomeBucket: "clean_success",
    trialCount: 499,
    recordedCostUsd: "607.88236925",
    sourceAdjustedKnownCostUsd: "607.88236925",
    sourceAccountingGapUsd: "0.00000000",
    missingRecordedCostCount: 0,
    unresolvedAdjustedCostCount: 0,
  },
  {
    outcomeBucket: "exception_with_success_signal",
    trialCount: 16,
    recordedCostUsd: "0",
    sourceAdjustedKnownCostUsd: "28.525409825839",
    sourceAccountingGapUsd: "28.525409825839",
    missingRecordedCostCount: 16,
    unresolvedAdjustedCostCount: 0,
  },
  {
    outcomeBucket: "normal_failure",
    trialCount: 195,
    recordedCostUsd: "189.07357825",
    sourceAdjustedKnownCostUsd: "189.07357825",
    sourceAccountingGapUsd: "0.00000000",
    missingRecordedCostCount: 4,
    unresolvedAdjustedCostCount: 4,
  },
  {
    outcomeBucket: "exception_failure",
    trialCount: 190,
    recordedCostUsd: "23.81878125",
    sourceAdjustedKnownCostUsd: "146.688488163366",
    sourceAccountingGapUsd: "122.869706913366",
    missingRecordedCostCount: 159,
    unresolvedAdjustedCostCount: 25,
  },
];

type DecimalParts = Readonly<{ units: bigint; scale: number }>;

function decimalParts(value: string, label: string): DecimalParts {
  if (!DECIMAL_PATTERN.test(value)) throw new Error(`${label} must be a decimal string`);
  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = unsigned.split(".");
  const units = BigInt(`${negative ? "-" : ""}${whole}${fraction}`);
  return { units, scale: fraction.length };
}

function scaleUnits(value: DecimalParts, scale: number): bigint {
  return value.units * (10n ** BigInt(scale - value.scale));
}

function decimalEqual(left: string, right: string): boolean {
  const leftParts = decimalParts(left, "left decimal");
  const rightParts = decimalParts(right, "right decimal");
  const scale = Math.max(leftParts.scale, rightParts.scale);
  return scaleUnits(leftParts, scale) === scaleUnits(rightParts, scale);
}

function decimalSumEquals(values: readonly string[], expected: string): boolean {
  const parts = values.map((value) => decimalParts(value, "summed decimal"));
  const expectedParts = decimalParts(expected, "expected decimal");
  const scale = Math.max(expectedParts.scale, ...parts.map((value) => value.scale));
  const sum = parts.reduce((total, value) => total + scaleUnits(value, scale), 0n);
  return sum === scaleUnits(expectedParts, scale);
}

function decimalDifferenceEquals(minuend: string, subtrahend: string, expected: string): boolean {
  const values = [decimalParts(minuend, "minuend"), decimalParts(subtrahend, "subtrahend")];
  const expectedParts = decimalParts(expected, "expected difference");
  const scale = Math.max(expectedParts.scale, ...values.map((value) => value.scale));
  return scaleUnits(values[0], scale) - scaleUnits(values[1], scale) === scaleUnits(expectedParts, scale);
}

function decimalSumWithin(values: readonly string[], expected: string, tolerance: string): boolean {
  const parts = values.map((value) => decimalParts(value, "summed decimal"));
  const expectedParts = decimalParts(expected, "expected decimal");
  const toleranceParts = decimalParts(tolerance, "decimal tolerance");
  const scale = Math.max(expectedParts.scale, toleranceParts.scale, ...parts.map((value) => value.scale));
  const sum = parts.reduce((total, value) => total + scaleUnits(value, scale), 0n);
  const difference = sum - scaleUnits(expectedParts, scale);
  const absoluteDifference = difference < 0n ? -difference : difference;
  return absoluteDifference <= scaleUnits(toleranceParts, scale);
}

function assertUnitInterval(value: number | null, label: string): void {
  if (value !== null && (value < 0 || value > 1)) {
    throw new Error(`${label} must be between zero and one`);
  }
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.length) throw new Error(`${label} must be a non-empty string`);
  return value;
}

function decimal(value: unknown, label: string): string {
  const parsed = text(value, label);
  if (!DECIMAL_PATTERN.test(parsed)) throw new Error(`${label} must be a decimal string`);
  return parsed;
}

function nullableDecimal(value: unknown, label: string): string | null {
  return value === null ? null : decimal(value, label);
}

function finiteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${label} must be finite`);
  return value;
}

function integer(value: unknown, label: string): number {
  const parsed = finiteNumber(value, label);
  if (!Number.isInteger(parsed) || parsed < 0) throw new Error(`${label} must be a nonnegative integer`);
  return parsed;
}

function nullableNumber(value: unknown, label: string): number | null {
  return value === null ? null : finiteNumber(value, label);
}

function exact<T extends string>(value: unknown, allowed: readonly T[], label: string): T {
  if (typeof value !== "string" || !allowed.includes(value as T)) {
    throw new Error(`${label} has an unsupported value`);
  }
  return value as T;
}

function strings(value: unknown, label: string): readonly string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.length)) {
    throw new Error(`${label} must be a string array`);
  }
  return value;
}

function validateCostEvidence(value: unknown, label: string): ReviewedCostEvidence {
  const item = record(value, label);
  return {
    recordedCostUsd: decimal(item.recordedCostUsd, `${label}.recordedCostUsd`),
    adjustedKnownCostUsd: nullableDecimal(item.adjustedKnownCostUsd, `${label}.adjustedKnownCostUsd`),
    qualifiedAdjustedCostEstimateUsd: nullableDecimal(
      item.qualifiedAdjustedCostEstimateUsd,
      `${label}.qualifiedAdjustedCostEstimateUsd`,
    ),
    accountingGapUsd: decimal(item.accountingGapUsd, `${label}.accountingGapUsd`),
    costBasis: exact(item.costBasis, ["adjusted_known_cost", "qualified_adjusted_cost_estimate"], `${label}.costBasis`),
    costLabel: text(item.costLabel, `${label}.costLabel`),
    pricingProvenanceStatus: exact(
      item.pricingProvenanceStatus,
      ["historical_reviewed_layer", "incomplete"],
      `${label}.pricingProvenanceStatus`,
    ),
    armRunAllocationConfidence: exact(
      item.armRunAllocationConfidence,
      ["mixed_by_arm", "low"],
      `${label}.armRunAllocationConfidence`,
    ),
    trialAllocationStatus: exact(
      item.trialAllocationStatus,
      ["available_for_reviewed_layer", "unresolved"],
      `${label}.trialAllocationStatus`,
    ),
    billingReconciliationStatus: exact(
      item.billingReconciliationStatus,
      ["not_invoice_level", "not_invoice_level_or_provider_billed"],
      `${label}.billingReconciliationStatus`,
    ),
    outcomeCostAllocationStatus: exact(
      item.outcomeCostAllocationStatus,
      ["available", "partial_core_only"],
      `${label}.outcomeCostAllocationStatus`,
    ),
    missingRecordedCostCount: integer(item.missingRecordedCostCount, `${label}.missingRecordedCostCount`),
    unresolvedCostCount: integer(item.unresolvedCostCount, `${label}.unresolvedCostCount`),
    adjustedCleanSuccessCostUsd: nullableDecimal(
      item.adjustedCleanSuccessCostUsd,
      `${label}.adjustedCleanSuccessCostUsd`,
    ),
    adjustedExceptionSuccessSignalCostUsd: nullableDecimal(
      item.adjustedExceptionSuccessSignalCostUsd,
      `${label}.adjustedExceptionSuccessSignalCostUsd`,
    ),
    adjustedFailureOrIncompleteCostUsd: nullableDecimal(
      item.adjustedFailureOrIncompleteCostUsd,
      `${label}.adjustedFailureOrIncompleteCostUsd`,
    ),
    failureOrIncompleteSpendShare: nullableNumber(
      item.failureOrIncompleteSpendShare,
      `${label}.failureOrIncompleteSpendShare`,
    ),
    nonproductiveOrUncleanSpendShare: nullableNumber(
      item.nonproductiveOrUncleanSpendShare,
      `${label}.nonproductiveOrUncleanSpendShare`,
    ),
    adjustedCostPerCleanSuccessUsd: nullableDecimal(
      item.adjustedCostPerCleanSuccessUsd,
      `${label}.adjustedCostPerCleanSuccessUsd`,
    ),
    adjustedCostPerAnySuccessUsd: nullableDecimal(
      item.adjustedCostPerAnySuccessUsd,
      `${label}.adjustedCostPerAnySuccessUsd`,
    ),
    costSources: strings(item.costSources, `${label}.costSources`),
    costConfidence: text(item.costConfidence, `${label}.costConfidence`),
    sourcePaths: strings(item.sourcePaths, `${label}.sourcePaths`),
  };
}

function validateOutcomeCostCoverage(
  value: unknown,
  scopeId: ReviewedPhase3ScopeId,
  scopeTrialCount: number,
  costEvidence: ReviewedCostEvidence,
): ReviewedOutcomeCostCoverage {
  const label = `scopes.${scopeId}.outcomeCostCoverage`;
  const item = record(value, label);
  if (!Array.isArray(item.rows) || item.rows.length === 0) {
    throw new Error(`${label}.rows must be a non-empty array`);
  }
  const rows = item.rows.map((value, index): ReviewedOutcomeCostRow => {
    const rowLabel = `${label}.rows[${index}]`;
    const row = record(value, rowLabel);
    const parsed: ReviewedOutcomeCostRow = {
      outcomeBucket: text(row.outcomeBucket, `${rowLabel}.outcomeBucket`),
      trialCount: integer(row.trialCount, `${rowLabel}.trialCount`),
      recordedCostUsd: decimal(row.recordedCostUsd, `${rowLabel}.recordedCostUsd`),
      sourceAdjustedKnownCostUsd: decimal(
        row.sourceAdjustedKnownCostUsd,
        `${rowLabel}.sourceAdjustedKnownCostUsd`,
      ),
      sourceAccountingGapUsd: decimal(
        row.sourceAccountingGapUsd,
        `${rowLabel}.sourceAccountingGapUsd`,
      ),
      missingRecordedCostCount: integer(
        row.missingRecordedCostCount,
        `${rowLabel}.missingRecordedCostCount`,
      ),
      unresolvedAdjustedCostCount: integer(
        row.unresolvedAdjustedCostCount,
        `${rowLabel}.unresolvedAdjustedCostCount`,
      ),
    };
    if (parsed.missingRecordedCostCount > parsed.trialCount
      || parsed.unresolvedAdjustedCostCount > parsed.trialCount) {
      throw new Error(`${rowLabel} missing or unresolved counts exceed its trial count`);
    }
    if (!decimalDifferenceEquals(
      parsed.sourceAdjustedKnownCostUsd,
      parsed.recordedCostUsd,
      parsed.sourceAccountingGapUsd,
    )) {
      throw new Error(`${rowLabel}.sourceAccountingGapUsd does not equal source adjusted minus recorded`);
    }
    return parsed;
  });
  if (new Set(rows.map((row) => row.outcomeBucket)).size !== rows.length) {
    throw new Error(`${label} contains duplicate outcome buckets`);
  }
  const expectedOrder = [...rows.map((row) => row.outcomeBucket)].sort((left, right) => {
    const leftIndex = OUTCOME_BUCKET_ORDER.indexOf(left as typeof OUTCOME_BUCKET_ORDER[number]);
    const rightIndex = OUTCOME_BUCKET_ORDER.indexOf(right as typeof OUTCOME_BUCKET_ORDER[number]);
    if (leftIndex >= 0 || rightIndex >= 0) {
      if (leftIndex < 0) return 1;
      if (rightIndex < 0) return -1;
      return leftIndex - rightIndex;
    }
    return left < right ? -1 : left > right ? 1 : 0;
  });
  if (JSON.stringify(rows.map((row) => row.outcomeBucket)) !== JSON.stringify(expectedOrder)) {
    throw new Error(`${label} outcome buckets are not in stable review order`);
  }
  if (Object.prototype.hasOwnProperty.call(item, "reconciledOutcomeBucket")) {
    throw new Error(`${label}.reconciledOutcomeBucket is not part of the reviewed schema`);
  }

  const coverage: ReviewedOutcomeCostCoverage = {
    status: exact(item.status, ["available", "partial_core_only"], `${label}.status`),
    coveredTrialCount: integer(item.coveredTrialCount, `${label}.coveredTrialCount`),
    excludedTrialCount: integer(item.excludedTrialCount, `${label}.excludedTrialCount`),
    excludedArmIds: strings(item.excludedArmIds, `${label}.excludedArmIds`),
    sourceAdjustedKnownCostTotalUsd: decimal(
      item.sourceAdjustedKnownCostTotalUsd,
      `${label}.sourceAdjustedKnownCostTotalUsd`,
    ),
    reviewedAdjustedKnownCostTotalUsd: decimal(
      item.reviewedAdjustedKnownCostTotalUsd,
      `${label}.reviewedAdjustedKnownCostTotalUsd`,
    ),
    reviewedScopeReconciliationAdjustmentUsd: decimal(
      item.reviewedScopeReconciliationAdjustmentUsd,
      `${label}.reviewedScopeReconciliationAdjustmentUsd`,
    ),
    rows,
  };
  if (coverage.coveredTrialCount + coverage.excludedTrialCount !== scopeTrialCount) {
    throw new Error(`${label} covered and excluded trials do not match the scope`);
  }
  if (rows.reduce((total, row) => total + row.trialCount, 0) !== coverage.coveredTrialCount) {
    throw new Error(`${label} row trial counts do not match coveredTrialCount`);
  }
  if (scopeId === "phase3-core") {
    if (JSON.stringify(rows) !== JSON.stringify(EXPECTED_CORE_OUTCOME_ROWS)) {
      throw new Error(`${label} source outcome rows differ from the reviewed historical source`);
    }
    if (!decimalSumEquals(rows.map((row) => row.recordedCostUsd), costEvidence.recordedCostUsd)) {
      throw new Error(`${label} recorded-cost rows do not match scope cost evidence`);
    }
    if (!decimalSumEquals(
      rows.map((row) => row.sourceAdjustedKnownCostUsd),
      coverage.sourceAdjustedKnownCostTotalUsd,
    )) {
      throw new Error(`${label} source adjusted-cost rows do not match their source total`);
    }
    if (!decimalSumEquals(
      [...rows.map((row) => row.sourceAccountingGapUsd), costEvidence.recordedCostUsd],
      coverage.sourceAdjustedKnownCostTotalUsd,
    )) {
      throw new Error(`${label} source accounting-gap rows do not match their source total`);
    }
    if (costEvidence.adjustedKnownCostUsd === null
      || !decimalEqual(coverage.reviewedAdjustedKnownCostTotalUsd, costEvidence.adjustedKnownCostUsd)) {
      throw new Error(`${label} reviewed adjusted total does not match reviewed core cost evidence`);
    }
    if (!decimalSumEquals(
      [coverage.sourceAdjustedKnownCostTotalUsd, coverage.reviewedScopeReconciliationAdjustmentUsd],
      coverage.reviewedAdjustedKnownCostTotalUsd,
    )) {
      throw new Error(`${label} source total and disclosed adjustment do not reconcile`);
    }
  }
  return coverage;
}

function validateArm(value: unknown, label: string): ReviewedPhase3Arm {
  const item = record(value, label);
  return {
    armId: text(item.armId, `${label}.armId`),
    backendModel: text(item.backendModel, `${label}.backendModel`),
    provider: text(item.provider, `${label}.provider`),
    routingPath: text(item.routingPath, `${label}.routingPath`),
    trialCount: integer(item.trialCount, `${label}.trialCount`),
    successCount: integer(item.successCount, `${label}.successCount`),
    cleanSuccessCount: integer(item.cleanSuccessCount, `${label}.cleanSuccessCount`),
    exceptionSuccessSignalCount: integer(
      item.exceptionSuccessSignalCount,
      `${label}.exceptionSuccessSignalCount`,
    ),
    failureOrIncompleteCount: integer(item.failureOrIncompleteCount, `${label}.failureOrIncompleteCount`),
    passRate: finiteNumber(item.passRate, `${label}.passRate`),
    recordedCostUsd: decimal(item.recordedCostUsd, `${label}.recordedCostUsd`),
    adjustedKnownCostUsd: nullableDecimal(item.adjustedKnownCostUsd, `${label}.adjustedKnownCostUsd`),
    qualifiedRetainedRateCostUsd: nullableDecimal(
      item.qualifiedRetainedRateCostUsd,
      `${label}.qualifiedRetainedRateCostUsd`,
    ),
    accountingGapUsd: decimal(item.accountingGapUsd, `${label}.accountingGapUsd`),
    adjustedCostPerCleanSuccessUsd: nullableDecimal(
      item.adjustedCostPerCleanSuccessUsd,
      `${label}.adjustedCostPerCleanSuccessUsd`,
    ),
    adjustedCostPerAnySuccessUsd: nullableDecimal(
      item.adjustedCostPerAnySuccessUsd,
      `${label}.adjustedCostPerAnySuccessUsd`,
    ),
    adjustedCleanSuccessCostUsd: nullableDecimal(
      item.adjustedCleanSuccessCostUsd,
      `${label}.adjustedCleanSuccessCostUsd`,
    ),
    adjustedExceptionSuccessSignalCostUsd: nullableDecimal(
      item.adjustedExceptionSuccessSignalCostUsd,
      `${label}.adjustedExceptionSuccessSignalCostUsd`,
    ),
    adjustedFailureOrIncompleteCostUsd: nullableDecimal(
      item.adjustedFailureOrIncompleteCostUsd,
      `${label}.adjustedFailureOrIncompleteCostUsd`,
    ),
    failureOrIncompleteSpendShare: nullableNumber(
      item.failureOrIncompleteSpendShare,
      `${label}.failureOrIncompleteSpendShare`,
    ),
    nonproductiveOrUncleanSpendShare: nullableNumber(
      item.nonproductiveOrUncleanSpendShare,
      `${label}.nonproductiveOrUncleanSpendShare`,
    ),
    medianWallClockSeconds: nullableNumber(item.medianWallClockSeconds, `${label}.medianWallClockSeconds`),
    missingRecordedCostCount: integer(item.missingRecordedCostCount, `${label}.missingRecordedCostCount`),
    unresolvedCostCount: integer(item.unresolvedCostCount, `${label}.unresolvedCostCount`),
    costSources: strings(item.costSources, `${label}.costSources`),
    costConfidence: text(item.costConfidence, `${label}.costConfidence`),
    costBasis: exact(
      item.costBasis,
      ["adjusted_known_cost", "qualified_retained_rate_estimate"],
      `${label}.costBasis`,
    ),
    pricingProvenanceStatus: exact(
      item.pricingProvenanceStatus,
      ["historical_reviewed_layer", "incomplete"],
      `${label}.pricingProvenanceStatus`,
    ),
    armRunAllocationConfidence: exact(
      item.armRunAllocationConfidence,
      ["reviewed_core_layer", "low"],
      `${label}.armRunAllocationConfidence`,
    ),
    trialAllocationStatus: exact(
      item.trialAllocationStatus,
      ["available_for_reviewed_layer", "unresolved"],
      `${label}.trialAllocationStatus`,
    ),
    billingReconciliationStatus: exact(
      item.billingReconciliationStatus,
      ["not_invoice_level", "not_invoice_level_or_provider_billed"],
      `${label}.billingReconciliationStatus`,
    ),
    outcomeCostAllocationStatus: exact(
      item.outcomeCostAllocationStatus,
      ["available", "unavailable"],
      `${label}.outcomeCostAllocationStatus`,
    ),
    sourcePaths: strings(item.sourcePaths, `${label}.sourcePaths`),
  };
}

function validateScope(value: unknown, expectedId: ReviewedPhase3ScopeId): ReviewedPhase3Scope {
  const label = `scopes.${expectedId}`;
  const item = record(value, label);
  const scopeId = exact(item.scopeId, SCOPE_IDS, `${label}.scopeId`);
  if (scopeId !== expectedId) throw new Error(`${label}.scopeId does not match its key`);
  if (!Array.isArray(item.arms)) throw new Error(`${label}.arms must be an array`);
  const arms = item.arms.map((arm, index) => validateArm(arm, `${label}.arms[${index}]`));
  const ids = new Set(arms.map((arm) => arm.armId));
  if (ids.size !== arms.length) throw new Error(`${label} contains duplicate arm IDs`);

  const trialCount = integer(item.trialCount, `${label}.trialCount`);
  const costEvidence = validateCostEvidence(item.costEvidence, `${label}.costEvidence`);
  const scope: ReviewedPhase3Scope = {
    scopeId,
    displayName: text(item.displayName, `${label}.displayName`),
    presentationKind: exact(
      item.presentationKind,
      ["historical_reviewed_snapshot", "current_reviewed_corpus"],
      `${label}.presentationKind`,
    ),
    snapshotDate: text(item.snapshotDate, `${label}.snapshotDate`),
    armCount: integer(item.armCount, `${label}.armCount`),
    trialCount,
    successCount: integer(item.successCount, `${label}.successCount`),
    passRate: finiteNumber(item.passRate, `${label}.passRate`),
    costEvidence,
    outcomeCostCoverage: validateOutcomeCostCoverage(
      item.outcomeCostCoverage,
      expectedId,
      trialCount,
      costEvidence,
    ),
    arms,
  };
  const trialTotal = arms.reduce((total, arm) => total + arm.trialCount, 0);
  const successTotal = arms.reduce((total, arm) => total + arm.successCount, 0);
  if (scope.armCount !== arms.length || scope.trialCount !== trialTotal || scope.successCount !== successTotal) {
    throw new Error(`${label} count totals do not match its arms`);
  }
  if (scope.trialCount === 0) throw new Error(`${label}.trialCount must be positive`);
  if (Math.abs(scope.passRate - scope.successCount / scope.trialCount) > 1e-12) {
    throw new Error(`${label}.passRate does not match its counts`);
  }
  if (scope.passRate < 0 || scope.passRate > 1) throw new Error(`${label}.passRate is outside [0, 1]`);
  if (scope.costEvidence.missingRecordedCostCount > scope.trialCount
    || scope.costEvidence.unresolvedCostCount > scope.trialCount) {
    throw new Error(`${label} missing or unresolved cost counts exceed its trial count`);
  }
  assertUnitInterval(
    scope.costEvidence.failureOrIncompleteSpendShare,
    `${label}.costEvidence.failureOrIncompleteSpendShare`,
  );
  assertUnitInterval(
    scope.costEvidence.nonproductiveOrUncleanSpendShare,
    `${label}.costEvidence.nonproductiveOrUncleanSpendShare`,
  );
  for (const arm of arms) {
    if (arm.trialCount === 0) throw new Error(`${label}.${arm.armId}.trialCount must be positive`);
    if (arm.successCount !== arm.cleanSuccessCount + arm.exceptionSuccessSignalCount) {
      throw new Error(`${label}.${arm.armId} success categories do not add up`);
    }
    if (arm.trialCount !== arm.successCount + arm.failureOrIncompleteCount) {
      throw new Error(`${label}.${arm.armId} outcome categories do not add up`);
    }
    if (Math.abs(arm.passRate - arm.successCount / arm.trialCount) > 1e-12) {
      throw new Error(`${label}.${arm.armId} passRate does not match its counts`);
    }
    if (arm.passRate < 0 || arm.passRate > 1) throw new Error(`${label}.${arm.armId} passRate is outside [0, 1]`);
    if (arm.missingRecordedCostCount > arm.trialCount || arm.unresolvedCostCount > arm.trialCount) {
      throw new Error(`${label}.${arm.armId} missing or unresolved counts exceed its trial count`);
    }
    assertUnitInterval(arm.failureOrIncompleteSpendShare, `${label}.${arm.armId}.failureOrIncompleteSpendShare`);
    assertUnitInterval(
      arm.nonproductiveOrUncleanSpendShare,
      `${label}.${arm.armId}.nonproductiveOrUncleanSpendShare`,
    );
  }
  return scope;
}

function deepFreeze<T>(value: T): Readonly<T> {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

export function validatePhase3ReviewedComparison(value: unknown): Phase3ReviewedComparison {
  const root = record(value, "snapshot");
  if (root.schemaVersion !== PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION) {
    throw new Error("unsupported Phase 3 reviewed comparison schema version");
  }
  if (!Array.isArray(root.inputs) || root.inputs.length !== 9) {
    throw new Error("snapshot.inputs must contain the nine reviewed inputs");
  }
  const inputs = root.inputs.map((value, index): ReviewedComparisonInput => {
    const item = record(value, `inputs[${index}]`);
    const sha256 = text(item.sha256, `inputs[${index}].sha256`);
    if (!SHA256_PATTERN.test(sha256)) throw new Error(`inputs[${index}].sha256 is invalid`);
    return {
      path: text(item.path, `inputs[${index}].path`),
      role: text(item.role, `inputs[${index}].role`),
      sha256,
    };
  });
  if (new Set(inputs.map((item) => item.path)).size !== inputs.length) {
    throw new Error("snapshot.inputs contains duplicate paths");
  }
  for (const input of inputs) {
    if (EXPECTED_INPUT_ROLES.get(input.path) !== input.role) {
      throw new Error(`snapshot input path or role is not in the reviewed input set: ${input.path}`);
    }
  }
  if (inputs.some((input) => !EXPECTED_INPUT_ROLES.has(input.path))
    || [...EXPECTED_INPUT_ROLES].some(([path, role]) => !inputs.some(
      (input) => input.path === path && input.role === role,
    ))) {
    throw new Error("snapshot inputs do not exactly match the reviewed input set");
  }
  const generator = record(root.generator, "snapshot.generator");
  const scopesRecord = record(root.scopes, "snapshot.scopes");
  const scopeKeys = Object.keys(scopesRecord).sort();
  if (JSON.stringify(scopeKeys) !== JSON.stringify([...SCOPE_IDS].sort())) {
    throw new Error("snapshot.scopes must contain exactly phase3-core and phase3-extended");
  }
  if (root.reviewedAt !== EXPECTED_REVIEWED_AT) throw new Error("snapshot.reviewedAt is not the reviewed date");
  if (generator.name !== EXPECTED_GENERATOR_NAME || generator.version !== EXPECTED_GENERATOR_VERSION) {
    throw new Error("snapshot.generator identity is unexpected");
  }
  const core = validateScope(scopesRecord["phase3-core"], "phase3-core");
  const extended = validateScope(scopesRecord["phase3-extended"], "phase3-extended");

  if ((core.armCount !== 15 || core.trialCount !== 900 || core.successCount !== 515)
    || (extended.armCount !== 16 || extended.trialCount !== 960 || extended.successCount !== 562)) {
    throw new Error("reviewed Phase 3 scope counts do not match fixed expectations");
  }
  if (core.arms.some((arm) => arm.armId === "router-kimi-k3")) {
    throw new Error("router-kimi-k3 must not appear in phase3-core");
  }
  const kimiArms = extended.arms.filter((arm) => arm.armId === "router-kimi-k3");
  if (kimiArms.length !== 1) throw new Error("phase3-extended must contain router-kimi-k3 exactly once");
  const coreById = new Map(core.arms.map((arm) => [arm.armId, arm]));
  for (const arm of extended.arms) {
    if (arm.armId === "router-kimi-k3") continue;
    const coreArm = coreById.get(arm.armId);
    if (!coreArm || JSON.stringify(coreArm) !== JSON.stringify(arm)) {
      throw new Error(`extended core arm differs from historical core: ${arm.armId}`);
    }
  }
  if (coreById.size !== extended.arms.length - 1) {
    throw new Error("phase3-extended and phase3-core arm membership differs beyond Kimi K3");
  }
  if (core.presentationKind !== "historical_reviewed_snapshot"
    || core.snapshotDate !== "2026-07-13"
    || extended.presentationKind !== "current_reviewed_corpus"
    || extended.snapshotDate !== EXPECTED_REVIEWED_AT) {
    throw new Error("reviewed Phase 3 presentation kinds are invalid");
  }

  if (core.costEvidence.recordedCostUsd !== "820.77472875"
    || core.costEvidence.adjustedKnownCostUsd !== "972.169845489198"
    || core.costEvidence.qualifiedAdjustedCostEstimateUsd !== null
    || core.costEvidence.accountingGapUsd !== "151.395116739198"
    || core.costEvidence.costBasis !== "adjusted_known_cost"
    || core.costEvidence.pricingProvenanceStatus !== "historical_reviewed_layer"
    || core.costEvidence.armRunAllocationConfidence !== "mixed_by_arm"
    || core.costEvidence.trialAllocationStatus !== "available_for_reviewed_layer"
    || core.costEvidence.billingReconciliationStatus !== "not_invoice_level"
    || core.costEvidence.outcomeCostAllocationStatus !== "available") {
    throw new Error("phase3-core cost evidence distinctions are invalid");
  }
  if (extended.costEvidence.recordedCostUsd !== "845.98194175"
    || extended.costEvidence.adjustedKnownCostUsd !== null
    || extended.costEvidence.qualifiedAdjustedCostEstimateUsd !== "1002.9841648891979"
    || extended.costEvidence.accountingGapUsd !== "157.0022231391979"
    || extended.costEvidence.costBasis !== "qualified_adjusted_cost_estimate"
    || extended.costEvidence.pricingProvenanceStatus !== "incomplete"
    || extended.costEvidence.armRunAllocationConfidence !== "low"
    || extended.costEvidence.trialAllocationStatus !== "unresolved"
    || extended.costEvidence.billingReconciliationStatus !== "not_invoice_level_or_provider_billed"
    || extended.costEvidence.outcomeCostAllocationStatus !== "partial_core_only") {
    throw new Error("phase3-extended cost evidence distinctions are invalid");
  }
  const unsupportedExtendedOutcomeCosts = [
    extended.costEvidence.adjustedCleanSuccessCostUsd,
    extended.costEvidence.adjustedExceptionSuccessSignalCostUsd,
    extended.costEvidence.adjustedFailureOrIncompleteCostUsd,
    extended.costEvidence.failureOrIncompleteSpendShare,
    extended.costEvidence.nonproductiveOrUncleanSpendShare,
    extended.costEvidence.adjustedCostPerCleanSuccessUsd,
    extended.costEvidence.adjustedCostPerAnySuccessUsd,
  ];
  if (unsupportedExtendedOutcomeCosts.some((item) => item !== null)) {
    throw new Error("unsupported phase3-extended outcome-cost values must remain unavailable");
  }
  for (const arm of core.arms) {
    if (arm.costBasis !== "adjusted_known_cost"
      || arm.adjustedKnownCostUsd === null
      || arm.qualifiedRetainedRateCostUsd !== null
      || arm.pricingProvenanceStatus !== "historical_reviewed_layer"
      || arm.armRunAllocationConfidence !== "reviewed_core_layer"
      || arm.trialAllocationStatus !== "available_for_reviewed_layer"
      || arm.outcomeCostAllocationStatus !== "available") {
      throw new Error(`phase3-core arm cost evidence is invalid: ${arm.armId}`);
    }
    if (!decimalDifferenceEquals(arm.adjustedKnownCostUsd, arm.recordedCostUsd, arm.accountingGapUsd)) {
      throw new Error(`phase3-core arm accounting gap is invalid: ${arm.armId}`);
    }
  }
  if (!decimalSumEquals(core.arms.map((arm) => arm.recordedCostUsd), core.costEvidence.recordedCostUsd)
    || !decimalSumEquals(
      core.arms.map((arm) => arm.adjustedKnownCostUsd as string),
      core.costEvidence.adjustedKnownCostUsd as string,
    )
    || !decimalSumEquals(core.arms.map((arm) => arm.accountingGapUsd), core.costEvidence.accountingGapUsd)) {
    throw new Error("phase3-core arm costs do not reconcile to scope cost evidence");
  }
  if (!decimalSumEquals(extended.arms.map((arm) => arm.recordedCostUsd), extended.costEvidence.recordedCostUsd)) {
    throw new Error("phase3-extended arm recorded costs do not reconcile to scope cost evidence");
  }
  const kimi = kimiArms[0];
  if (kimi.trialCount !== 60
    || kimi.successCount !== 47
    || kimi.cleanSuccessCount !== 44
    || kimi.exceptionSuccessSignalCount !== 3
    || kimi.failureOrIncompleteCount !== 13
    || kimi.missingRecordedCostCount !== 10
    || kimi.unresolvedCostCount !== 10
    || kimi.recordedCostUsd !== "25.207213"
    || kimi.qualifiedRetainedRateCostUsd !== "30.8143194"
    || kimi.accountingGapUsd !== "5.6071064"
    || kimi.adjustedKnownCostUsd !== null
    || kimi.costBasis !== "qualified_retained_rate_estimate"
    || kimi.pricingProvenanceStatus !== "incomplete"
    || kimi.armRunAllocationConfidence !== "low"
    || kimi.trialAllocationStatus !== "unresolved"
    || kimi.billingReconciliationStatus !== "not_invoice_level_or_provider_billed"
    || kimi.outcomeCostAllocationStatus !== "unavailable") {
    throw new Error("router-kimi-k3 evidence distinctions are invalid");
  }
  if (!decimalDifferenceEquals(
    kimi.qualifiedRetainedRateCostUsd as string,
    kimi.recordedCostUsd,
    kimi.accountingGapUsd,
  )) {
    throw new Error("router-kimi-k3 accounting gap is invalid");
  }
  if (!decimalSumWithin(
    [core.costEvidence.adjustedKnownCostUsd as string, kimi.qualifiedRetainedRateCostUsd as string],
    extended.costEvidence.qualifiedAdjustedCostEstimateUsd as string,
    "0.000000000001",
  )) {
    throw new Error("core adjusted cost plus Kimi retained-rate cost does not reconcile to extended estimate");
  }
  if (!decimalDifferenceEquals(
    extended.costEvidence.qualifiedAdjustedCostEstimateUsd as string,
    extended.costEvidence.recordedCostUsd,
    extended.costEvidence.accountingGapUsd,
  )) {
    throw new Error("phase3-extended accounting gap is invalid");
  }
  const coreOutcome = core.outcomeCostCoverage;
  const extendedOutcome = extended.outcomeCostCoverage;
  if (coreOutcome.status !== "available"
    || coreOutcome.coveredTrialCount !== 900
    || coreOutcome.excludedTrialCount !== 0
    || coreOutcome.excludedArmIds.length !== 0
    || coreOutcome.sourceAdjustedKnownCostTotalUsd !== "972.169845489205"
    || coreOutcome.reviewedAdjustedKnownCostTotalUsd !== "972.169845489198"
    || coreOutcome.reviewedScopeReconciliationAdjustmentUsd !== "-0.000000000007") {
    throw new Error("phase3-core outcome-cost coverage metadata is invalid");
  }
  if (extendedOutcome.status !== "partial_core_only"
    || extendedOutcome.coveredTrialCount !== 900
    || extendedOutcome.excludedTrialCount !== 60
    || JSON.stringify(extendedOutcome.excludedArmIds) !== JSON.stringify(["router-kimi-k3"])) {
    throw new Error("phase3-extended outcome-cost coverage must explicitly exclude Kimi K3");
  }
  if (JSON.stringify(extendedOutcome.rows) !== JSON.stringify(coreOutcome.rows)) {
    throw new Error("phase3-extended partial outcome-cost rows must equal the reviewed core rows");
  }
  for (const field of [
    "sourceAdjustedKnownCostTotalUsd",
    "reviewedAdjustedKnownCostTotalUsd",
    "reviewedScopeReconciliationAdjustmentUsd",
  ] as const) {
    if (extendedOutcome[field] !== coreOutcome[field]) {
      throw new Error(`phase3-extended outcome-cost provenance differs from core: ${field}`);
    }
  }
  const unavailableKimiFields = [
    kimi.adjustedCostPerCleanSuccessUsd,
    kimi.adjustedCostPerAnySuccessUsd,
    kimi.adjustedCleanSuccessCostUsd,
    kimi.adjustedExceptionSuccessSignalCostUsd,
    kimi.adjustedFailureOrIncompleteCostUsd,
    kimi.failureOrIncompleteSpendShare,
    kimi.nonproductiveOrUncleanSpendShare,
    kimi.medianWallClockSeconds,
  ];
  if (unavailableKimiFields.some((item) => item !== null)) {
    throw new Error("unsupported router-kimi-k3 values must remain unavailable");
  }

  return deepFreeze({
    schemaVersion: PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION,
    reviewedAt: EXPECTED_REVIEWED_AT,
    generator: {
      name: EXPECTED_GENERATOR_NAME,
      version: EXPECTED_GENERATOR_VERSION,
    },
    inputs,
    scopes: { "phase3-core": core, "phase3-extended": extended },
  }) as Phase3ReviewedComparison;
}

export const PHASE3_REVIEWED_COMPARISON = validatePhase3ReviewedComparison(reviewedSnapshotJson);

export function getReviewedPhase3Scope(scopeId: ReviewedPhase3ScopeId): ReviewedPhase3Scope {
  return PHASE3_REVIEWED_COMPARISON.scopes[scopeId];
}

export function selectReviewedPhase3Scope(
  value: string | readonly string[] | null | undefined,
): ReviewedScopeSelection {
  if (value === null || value === undefined || value === "") {
    return {
      scopeId: "phase3-extended",
      scope: getReviewedPhase3Scope("phase3-extended"),
      warning: null,
      warningMessage: null,
      usedDefault: true,
    };
  }
  if (Array.isArray(value)) {
    return {
      scopeId: "phase3-extended",
      scope: getReviewedPhase3Scope("phase3-extended"),
      warning: "repeated_scope",
      warningMessage: "Repeated scope values are not supported; Phase 3 extended was selected.",
      usedDefault: true,
    };
  }
  if (value === "phase3-core" || value === "phase3-extended") {
    return {
      scopeId: value,
      scope: getReviewedPhase3Scope(value),
      warning: null,
      warningMessage: null,
      usedDefault: false,
    };
  }
  return {
    scopeId: "phase3-extended",
    scope: getReviewedPhase3Scope("phase3-extended"),
    warning: "invalid_scope",
    warningMessage: "Unknown scope value; Phase 3 extended was selected.",
    usedDefault: true,
  };
}
