import type {
  ReviewedPhase3Arm,
  ReviewedPhase3Scope,
  ReviewedPhase3ScopeId,
} from "./phase3-reviewed-comparison";

import type {
  SpendDecompositionCoreSourceRow,
  SpendDecompositionOutcomeBucket,
  SpendDecompositionReviewSourceRow,
} from "./spend-decomposition-source";

export const SPEND_DECOMPOSITION_KIMI_ARM_ID =
  "router-kimi-k3" as const;

export const SPEND_DECOMPOSITION_SEGMENTS = Object.freeze([
  {
    id: "clean_success",
    label: "Recorded clean-success spend",
  },
  {
    id: "normal_failure",
    label: "Recorded normal-failure spend",
  },
  {
    id: "exception_failure",
    label: "Recorded exception-failure spend",
  },
  {
    id: "exception_with_success_signal",
    label: "Recorded exception-with-success-signal spend",
  },
] as const);

export type SpendDecompositionSegmentId =
  (typeof SPEND_DECOMPOSITION_SEGMENTS)[number]["id"];

export type SpendDecompositionSegment = Readonly<{
  id: SpendDecompositionSegmentId;
  label: string;
  trialCount: number;
  recordedCostUsd: string;
  missingRecordedCostCount: number;
}>;

export type SpendDecompositionArm = Readonly<{
  armId: string;
  trialCount: number;
  successCount: number;
  failureOrIncompleteCount: number;
  segments: readonly SpendDecompositionSegment[];
  recordedCostUsd: string;
  accountingGapUsd: string;
  selectedReviewedCostUsd: string;
  selectedCostBasis:
    | "adjusted_known_cost"
    | "qualified_retained_rate_estimate";
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  costConfidence: string;
  pricingProvenanceStatus:
    | "historical_reviewed_layer"
    | "incomplete";
  armRunAllocationConfidence:
    | "reviewed_core_layer"
    | "low";
  trialAllocationStatus:
    | "available_for_reviewed_layer"
    | "unresolved";
  billingReconciliationStatus:
    | "not_invoice_level"
    | "not_invoice_level_or_provider_billed";
  outcomeCostAllocationStatus:
    | "available"
    | "unavailable";
}>;

export type SpendDecompositionModel = Readonly<{
  scopeId: ReviewedPhase3ScopeId;
  armCount: number;
  trialCount: number;
  successCount: number;
  segments: readonly SpendDecompositionSegment[];
  recordedCostUsd: string;
  summedArmAccountingGapUsd: string;
  scopeAccountingGapUsd: string;
  summedSelectedArmCostUsd: string;
  scopeSelectedReviewedCostUsd: string;
  scopeSelectedCostBasis:
    | "adjusted_known_cost"
    | "qualified_adjusted_cost_estimate";
  scopeReconciliationDeltaUsd: string;
  scopeReconciliationToleranceUsd: "0.000000000001";
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  arms: readonly SpendDecompositionArm[];
}>;

type DecimalParts = Readonly<{
  units: bigint;
  scale: number;
}>;

type NormalizedSpendTrial = Readonly<{
  trialId: string;
  armId: string;
  taskId: string;
  bucket: SpendDecompositionOutcomeBucket;
  recordedCostUsd: string;
  unresolvedFromCoreSource: boolean | null;
}>;

const EXPECTED_CORE_TRIAL_COUNT = 900;
const EXPECTED_REVIEW_TRIAL_COUNT = 960;
const EXPECTED_CORE_ARM_COUNT = 15;
const EXPECTED_EXTENDED_ARM_COUNT = 16;
const EXPECTED_TRIALS_PER_ARM = 60;
const EXPECTED_KIMI_TRIAL_COUNT = 60;
const RECONCILIATION_TOLERANCE_USD =
  "0.000000000001" as const;

const DECIMAL_PATTERN =
  /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/;

const NONNEGATIVE_DECIMAL_PATTERN =
  /^(?:0|[1-9]\d*)(?:\.\d+)?$/;

function decimalParts(
  value: string,
  label: string,
): DecimalParts {
  if (!DECIMAL_PATTERN.test(value)) {
    throw new Error(`${label}_invalid_decimal`);
  }

  const negative = value.startsWith("-");
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ""] = unsigned.split(".");
  const digits = `${negative ? "-" : ""}${whole}${fraction}`;

  return {
    units: BigInt(digits),
    scale: fraction.length,
  };
}

function scaleUnits(
  value: DecimalParts,
  scale: number,
): bigint {
  return value.units
    * (10n ** BigInt(scale - value.scale));
}

function formatDecimal(
  units: bigint,
  scale: number,
): string {
  if (units === 0n) return "0";

  const negative = units < 0n;
  const absolute = negative ? -units : units;
  const digits = absolute.toString();

  if (scale === 0) {
    return `${negative ? "-" : ""}${digits}`;
  }

  const padded = digits.padStart(scale + 1, "0");
  const whole = padded.slice(0, -scale);
  const fraction = padded.slice(-scale);

  return `${negative ? "-" : ""}${whole}.${fraction}`;
}

function decimalEqual(
  left: string,
  right: string,
): boolean {
  const leftParts = decimalParts(
    left,
    "left_decimal",
  );
  const rightParts = decimalParts(
    right,
    "right_decimal",
  );
  const scale = Math.max(
    leftParts.scale,
    rightParts.scale,
  );

  return (
    scaleUnits(leftParts, scale)
    === scaleUnits(rightParts, scale)
  );
}

function sumDecimals(
  values: readonly string[],
): string {
  if (values.length === 0) return "0";

  const parts = values.map((value) =>
    decimalParts(value, "summed_decimal"),
  );

  const scale = Math.max(
    ...parts.map((value) => value.scale),
  );

  const total = parts.reduce(
    (sum, value) =>
      sum + scaleUnits(value, scale),
    0n,
  );

  return formatDecimal(total, scale);
}

function sumPresentDecimals(
  values: readonly string[],
): string {
  return sumDecimals(
    values.filter((value) => value !== ""),
  );
}

function subtractDecimals(
  left: string,
  right: string,
): string {
  const leftParts = decimalParts(
    left,
    "left_decimal",
  );
  const rightParts = decimalParts(
    right,
    "right_decimal",
  );

  const scale = Math.max(
    leftParts.scale,
    rightParts.scale,
  );

  return formatDecimal(
    scaleUnits(leftParts, scale)
      - scaleUnits(rightParts, scale),
    scale,
  );
}

function decimalAbsWithin(
  value: string,
  tolerance: string,
): boolean {
  const valueParts = decimalParts(
    value,
    "difference_decimal",
  );
  const toleranceParts = decimalParts(
    tolerance,
    "tolerance_decimal",
  );

  if (toleranceParts.units < 0n) {
    throw new Error("negative_reconciliation_tolerance");
  }

  const scale = Math.max(
    valueParts.scale,
    toleranceParts.scale,
  );

  const scaled = scaleUnits(
    valueParts,
    scale,
  );

  const absolute =
    scaled < 0n ? -scaled : scaled;

  return (
    absolute
    <= scaleUnits(toleranceParts, scale)
  );
}

function requireNonnegativeDecimal(
  value: string,
  code: string,
): string {
  if (!NONNEGATIVE_DECIMAL_PATTERN.test(value)) {
    throw new Error(code);
  }
  return value;
}

function sameSet(
  left: ReadonlySet<string>,
  right: ReadonlySet<string>,
): boolean {
  return (
    left.size === right.size
    && [...left].every((value) =>
      right.has(value),
    )
  );
}

function indexByTrialId<T extends {
  trial_id: string;
}>(
  rows: readonly T[],
  label: string,
): ReadonlyMap<string, T> {
  const result = new Map<string, T>();

  for (const row of rows) {
    if (result.has(row.trial_id)) {
      throw new Error(
        `${label}_duplicate_trial_id`,
      );
    }
    result.set(row.trial_id, row);
  }

  return result;
}

function countByArm<T extends {
  arm_id: string;
}>(
  rows: readonly T[],
): ReadonlyMap<string, number> {
  const counts = new Map<string, number>();

  for (const row of rows) {
    counts.set(
      row.arm_id,
      (counts.get(row.arm_id) ?? 0) + 1,
    );
  }

  return counts;
}

function requireArmCounts(
  rows: readonly {
    arm_id: string;
  }[],
  expectedArmCount: number,
  label: string,
): ReadonlyMap<string, number> {
  const counts = countByArm(rows);

  if (counts.size !== expectedArmCount) {
    throw new Error(
      `${label}_arm_count_mismatch`,
    );
  }

  for (const [armId, count] of counts) {
    if (count !== EXPECTED_TRIALS_PER_ARM) {
      throw new Error(
        `${label}_arm_trial_count_mismatch:${armId}`,
      );
    }
  }

  return counts;
}

function coreReviewOutcomeCompatible(
  bucket: SpendDecompositionOutcomeBucket,
  rawOutcome: SpendDecompositionReviewSourceRow["raw_outcome"],
): boolean {
  if (
    bucket === "clean_success"
    || bucket
      === "exception_with_success_signal"
  ) {
    return rawOutcome === "success";
  }

  if (bucket === "normal_failure") {
    return rawOutcome === "failure";
  }

  return (
    rawOutcome === "failure"
    || rawOutcome === "not_recorded"
  );
}

function validateSourceRelationship(
  coreRows:
    readonly SpendDecompositionCoreSourceRow[],
  reviewRows:
    readonly SpendDecompositionReviewSourceRow[],
): Readonly<{
  kimiRows:
    readonly SpendDecompositionReviewSourceRow[];
  coreArmIds: ReadonlySet<string>;
  reviewArmIds: ReadonlySet<string>;
}> {
  if (coreRows.length !== EXPECTED_CORE_TRIAL_COUNT) {
    throw new Error(
      "core_trial_count_mismatch",
    );
  }

  if (
    reviewRows.length
    !== EXPECTED_REVIEW_TRIAL_COUNT
  ) {
    throw new Error(
      "review_trial_count_mismatch",
    );
  }

  const coreById = indexByTrialId(
    coreRows,
    "core",
  );
  const reviewById = indexByTrialId(
    reviewRows,
    "review",
  );

  const reviewCoreRows = reviewRows.filter(
    (row) =>
      row.arm_id
      !== SPEND_DECOMPOSITION_KIMI_ARM_ID,
  );

  const kimiRows = reviewRows.filter(
    (row) =>
      row.arm_id
      === SPEND_DECOMPOSITION_KIMI_ARM_ID,
  );

  if (
    reviewCoreRows.length
    !== EXPECTED_CORE_TRIAL_COUNT
  ) {
    throw new Error(
      "review_core_trial_count_mismatch",
    );
  }

  if (
    kimiRows.length
    !== EXPECTED_KIMI_TRIAL_COUNT
  ) {
    throw new Error(
      "kimi_trial_count_mismatch",
    );
  }

  const reviewCoreIds = new Set(
    reviewCoreRows.map((row) => row.trial_id),
  );

  const coreIds = new Set(coreById.keys());

  if (!sameSet(coreIds, reviewCoreIds)) {
    throw new Error(
      "core_review_trial_set_mismatch",
    );
  }

  for (const core of coreRows) {
    const review = reviewById.get(
      core.trial_id,
    );

    if (!review) {
      throw new Error(
        "core_review_trial_missing",
      );
    }

    if (
      review.arm_id !== core.arm_id
      || review.task_id !== core.task_id
    ) {
      throw new Error(
        "core_review_identity_mismatch",
      );
    }

    if (
      !coreReviewOutcomeCompatible(
        core.outcome_bucket,
        review.raw_outcome,
      )
    ) {
      throw new Error(
        "core_review_outcome_mismatch",
      );
    }
  }

  const coreArmCounts = requireArmCounts(
    coreRows,
    EXPECTED_CORE_ARM_COUNT,
    "core",
  );

  const reviewArmCounts = requireArmCounts(
    reviewRows,
    EXPECTED_EXTENDED_ARM_COUNT,
    "review",
  );

  if (
    coreArmCounts.has(
      SPEND_DECOMPOSITION_KIMI_ARM_ID,
    )
  ) {
    throw new Error(
      "kimi_present_in_core_source",
    );
  }

  if (
    reviewArmCounts.get(
      SPEND_DECOMPOSITION_KIMI_ARM_ID,
    )
    !== EXPECTED_KIMI_TRIAL_COUNT
  ) {
    throw new Error(
      "kimi_review_population_mismatch",
    );
  }

  return Object.freeze({
    kimiRows: Object.freeze([...kimiRows]),
    coreArmIds: new Set(
      coreArmCounts.keys(),
    ),
    reviewArmIds: new Set(
      reviewArmCounts.keys(),
    ),
  });
}

function classifyKimiRow(
  row: SpendDecompositionReviewSourceRow,
): SpendDecompositionOutcomeBucket {
  if (!row.raw_reward_present) {
    throw new Error(
      `kimi_reward_missing:${row.trial_id}`,
    );
  }

  const isSuccess =
    decimalEqual(row.raw_reward, "1");
  const isFailure =
    decimalEqual(row.raw_reward, "0");
  const hasException =
    row.exception_type.trim() !== "";

  if (!isSuccess && !isFailure) {
    throw new Error(
      `kimi_reward_unexpected:${row.trial_id}`,
    );
  }

  const expectedOutcome =
    isSuccess ? "success" : "failure";

  if (row.raw_outcome !== expectedOutcome) {
    throw new Error(
      `kimi_outcome_mismatch:${row.trial_id}`,
    );
  }

  if (isSuccess) {
    return hasException
      ? "exception_with_success_signal"
      : "clean_success";
  }

  return hasException
    ? "exception_failure"
    : "normal_failure";
}

function normalizeCoreRows(
  rows:
    readonly SpendDecompositionCoreSourceRow[],
): readonly NormalizedSpendTrial[] {
  return Object.freeze(
    rows.map((row) =>
      Object.freeze({
        trialId: row.trial_id,
        armId: row.arm_id,
        taskId: row.task_id,
        bucket: row.outcome_bucket,
        recordedCostUsd:
          row.recorded_cost_usd,
        unresolvedFromCoreSource:
          row.cost_source.startsWith(
            "unresolved_",
          ),
      }),
    ),
  );
}

function normalizeKimiRows(
  rows:
    readonly SpendDecompositionReviewSourceRow[],
): readonly NormalizedSpendTrial[] {
  return Object.freeze(
    rows.map((row) =>
      Object.freeze({
        trialId: row.trial_id,
        armId: row.arm_id,
        taskId: row.task_id,
        bucket: classifyKimiRow(row),
        recordedCostUsd: row.cost_usd,
        unresolvedFromCoreSource: null,
      }),
    ),
  );
}

function segmentLabel(
  id: SpendDecompositionSegmentId,
): string {
  const segment =
    SPEND_DECOMPOSITION_SEGMENTS.find(
      (candidate) =>
        candidate.id === id,
    );

  if (!segment) {
    throw new Error(
      `unknown_spend_segment:${id}`,
    );
  }

  return segment.label;
}

function buildSegment(
  id: SpendDecompositionSegmentId,
  rows: readonly NormalizedSpendTrial[],
): SpendDecompositionSegment {
  const matching = rows.filter(
    (row) => row.bucket === id,
  );

  return Object.freeze({
    id,
    label: segmentLabel(id),
    trialCount: matching.length,
    recordedCostUsd:
      sumPresentDecimals(
        matching.map(
          (row) => row.recordedCostUsd,
        ),
      ),
    missingRecordedCostCount:
      matching.filter(
        (row) =>
          row.recordedCostUsd === "",
      ).length,
  });
}

function selectedArmCost(
  arm: ReviewedPhase3Arm,
): Readonly<{
  amount: string;
  basis:
    | "adjusted_known_cost"
    | "qualified_retained_rate_estimate";
}> {
  if (
    arm.armId
    === SPEND_DECOMPOSITION_KIMI_ARM_ID
  ) {
    if (
      arm.adjustedKnownCostUsd !== null
      || arm.qualifiedRetainedRateCostUsd
        === null
      || arm.costBasis
        !== "qualified_retained_rate_estimate"
    ) {
      throw new Error(
        "kimi_selected_cost_basis_invalid",
      );
    }

    return Object.freeze({
      amount:
        requireNonnegativeDecimal(
          arm.qualifiedRetainedRateCostUsd,
          "kimi_selected_cost_invalid",
        ),
      basis:
        "qualified_retained_rate_estimate",
    });
  }

  if (
    arm.adjustedKnownCostUsd === null
    || arm.qualifiedRetainedRateCostUsd
      !== null
    || arm.costBasis
      !== "adjusted_known_cost"
  ) {
    throw new Error(
      `core_selected_cost_basis_invalid:${arm.armId}`,
    );
  }

  return Object.freeze({
    amount:
      requireNonnegativeDecimal(
        arm.adjustedKnownCostUsd,
        "core_selected_cost_invalid",
      ),
    basis: "adjusted_known_cost",
  });
}

function buildArm(
  arm: ReviewedPhase3Arm,
  rows: readonly NormalizedSpendTrial[],
): SpendDecompositionArm {
  if (
    rows.length
    !== EXPECTED_TRIALS_PER_ARM
  ) {
    throw new Error(
      `arm_trial_count_mismatch:${arm.armId}`,
    );
  }

  const segments =
    SPEND_DECOMPOSITION_SEGMENTS.map(
      (definition) =>
        buildSegment(
          definition.id,
          rows,
        ),
    );

  const trialCount = segments.reduce(
    (total, segment) =>
      total + segment.trialCount,
    0,
  );

  const successCount =
    segments.find(
      (segment) =>
        segment.id === "clean_success",
    )!.trialCount
    + segments.find(
      (segment) =>
        segment.id
        === "exception_with_success_signal",
    )!.trialCount;

  const failureOrIncompleteCount =
    segments.find(
      (segment) =>
        segment.id === "normal_failure",
    )!.trialCount
    + segments.find(
      (segment) =>
        segment.id === "exception_failure",
    )!.trialCount;

  if (
    trialCount !== arm.trialCount
    || successCount !== arm.successCount
    || failureOrIncompleteCount
      !== arm.failureOrIncompleteCount
  ) {
    throw new Error(
      `arm_outcome_count_mismatch:${arm.armId}`,
    );
  }

  if (
    arm.successCount
    !== arm.cleanSuccessCount
      + arm.exceptionSuccessSignalCount
  ) {
    throw new Error(
      `arm_reviewed_success_count_invalid:${arm.armId}`,
    );
  }

  const cleanCount =
    segments.find(
      (segment) =>
        segment.id === "clean_success",
    )!.trialCount;

  const exceptionSuccessCount =
    segments.find(
      (segment) =>
        segment.id
        === "exception_with_success_signal",
    )!.trialCount;

  if (
    cleanCount !== arm.cleanSuccessCount
    || exceptionSuccessCount
      !== arm.exceptionSuccessSignalCount
  ) {
    throw new Error(
      `arm_success_bucket_mismatch:${arm.armId}`,
    );
  }

  const recordedCostUsd =
    sumDecimals(
      segments.map(
        (segment) =>
          segment.recordedCostUsd,
      ),
    );

  if (
    !decimalEqual(
      recordedCostUsd,
      requireNonnegativeDecimal(
        arm.recordedCostUsd,
        "arm_recorded_cost_invalid",
      ),
    )
  ) {
    throw new Error(
      `arm_recorded_cost_mismatch:${arm.armId}`,
    );
  }

  const missingRecordedCostCount =
    segments.reduce(
      (total, segment) =>
        total
        + segment.missingRecordedCostCount,
      0,
    );

  if (
    missingRecordedCostCount
    !== arm.missingRecordedCostCount
  ) {
    throw new Error(
      `arm_missing_cost_count_mismatch:${arm.armId}`,
    );
  }

  if (
    arm.armId
    === SPEND_DECOMPOSITION_KIMI_ARM_ID
  ) {
    if (
      arm.unresolvedCostCount
        !== missingRecordedCostCount
      || arm.trialAllocationStatus
        !== "unresolved"
      || arm.outcomeCostAllocationStatus
        !== "unavailable"
    ) {
      throw new Error(
        "kimi_unresolved_cost_contract_mismatch",
      );
    }
  } else {
    const sourceUnresolvedCount =
      rows.filter(
        (row) =>
          row.unresolvedFromCoreSource
          === true,
      ).length;

    if (
      sourceUnresolvedCount
      !== arm.unresolvedCostCount
    ) {
      throw new Error(
        `arm_unresolved_cost_count_mismatch:${arm.armId}`,
      );
    }

    if (
      arm.trialAllocationStatus
        !== "available_for_reviewed_layer"
      || arm.outcomeCostAllocationStatus
        !== "available"
    ) {
      throw new Error(
        `core_allocation_contract_mismatch:${arm.armId}`,
      );
    }
  }

  const selected = selectedArmCost(arm);

  const accountingGapUsd =
    requireNonnegativeDecimal(
      arm.accountingGapUsd,
      "arm_accounting_gap_invalid",
    );

  if (
    !decimalEqual(
      sumDecimals([
        recordedCostUsd,
        accountingGapUsd,
      ]),
      selected.amount,
    )
  ) {
    throw new Error(
      `arm_five_part_reconciliation_mismatch:${arm.armId}`,
    );
  }

  return Object.freeze({
    armId: arm.armId,
    trialCount,
    successCount,
    failureOrIncompleteCount,
    segments: Object.freeze(segments),
    recordedCostUsd,
    accountingGapUsd,
    selectedReviewedCostUsd:
      selected.amount,
    selectedCostBasis:
      selected.basis,
    missingRecordedCostCount,
    unresolvedCostCount:
      arm.unresolvedCostCount,
    costConfidence:
      arm.costConfidence,
    pricingProvenanceStatus:
      arm.pricingProvenanceStatus,
    armRunAllocationConfidence:
      arm.armRunAllocationConfidence,
    trialAllocationStatus:
      arm.trialAllocationStatus,
    billingReconciliationStatus:
      arm.billingReconciliationStatus,
    outcomeCostAllocationStatus:
      arm.outcomeCostAllocationStatus,
  });
}

function selectedScopeCost(
  scope: ReviewedPhase3Scope,
): Readonly<{
  amount: string;
  basis:
    | "adjusted_known_cost"
    | "qualified_adjusted_cost_estimate";
}> {
  if (scope.scopeId === "phase3-core") {
    if (
      scope.costEvidence.adjustedKnownCostUsd
        === null
      || scope.costEvidence
        .qualifiedAdjustedCostEstimateUsd
        !== null
      || scope.costEvidence.costBasis
        !== "adjusted_known_cost"
    ) {
      throw new Error(
        "core_scope_selected_cost_invalid",
      );
    }

    return Object.freeze({
      amount:
        requireNonnegativeDecimal(
          scope.costEvidence
            .adjustedKnownCostUsd,
          "core_scope_cost_invalid",
        ),
      basis: "adjusted_known_cost",
    });
  }

  if (
    scope.costEvidence.adjustedKnownCostUsd
      !== null
    || scope.costEvidence
      .qualifiedAdjustedCostEstimateUsd
      === null
    || scope.costEvidence.costBasis
      !== "qualified_adjusted_cost_estimate"
  ) {
    throw new Error(
      "extended_scope_selected_cost_invalid",
    );
  }

  return Object.freeze({
    amount:
      requireNonnegativeDecimal(
        scope.costEvidence
          .qualifiedAdjustedCostEstimateUsd,
        "extended_scope_cost_invalid",
      ),
    basis:
      "qualified_adjusted_cost_estimate",
  });
}

function validateScopeMembership(
  scope: ReviewedPhase3Scope,
  coreArmIds: ReadonlySet<string>,
  reviewArmIds: ReadonlySet<string>,
): void {
  const expectedArmIds =
    scope.scopeId === "phase3-core"
      ? coreArmIds
      : reviewArmIds;

  const actualArmIds =
    new Set(
      scope.arms.map(
        (arm) => arm.armId,
      ),
    );

  if (
    !sameSet(
      actualArmIds,
      expectedArmIds,
    )
  ) {
    throw new Error(
      "scope_arm_membership_mismatch",
    );
  }

  const expectedArmCount =
    scope.scopeId === "phase3-core"
      ? EXPECTED_CORE_ARM_COUNT
      : EXPECTED_EXTENDED_ARM_COUNT;

  const expectedTrialCount =
    scope.scopeId === "phase3-core"
      ? EXPECTED_CORE_TRIAL_COUNT
      : EXPECTED_REVIEW_TRIAL_COUNT;

  if (
    scope.armCount !== expectedArmCount
    || scope.arms.length
      !== expectedArmCount
    || scope.trialCount
      !== expectedTrialCount
  ) {
    throw new Error(
      "scope_population_mismatch",
    );
  }
}

function aggregateSegments(
  arms: readonly SpendDecompositionArm[],
): readonly SpendDecompositionSegment[] {
  return Object.freeze(
    SPEND_DECOMPOSITION_SEGMENTS.map(
      (definition) => {
        const armSegments =
          arms.map((arm) => {
            const segment =
              arm.segments.find(
                (candidate) =>
                  candidate.id
                  === definition.id,
              );

            if (!segment) {
              throw new Error(
                `arm_segment_missing:${arm.armId}:${definition.id}`,
              );
            }

            return segment;
          });

        return Object.freeze({
          id: definition.id,
          label: definition.label,
          trialCount:
            armSegments.reduce(
              (total, segment) =>
                total
                + segment.trialCount,
              0,
            ),
          recordedCostUsd:
            sumDecimals(
              armSegments.map(
                (segment) =>
                  segment.recordedCostUsd,
              ),
            ),
          missingRecordedCostCount:
            armSegments.reduce(
              (total, segment) =>
                total
                + segment
                  .missingRecordedCostCount,
              0,
            ),
        });
      },
    ),
  );
}

export function buildSpendDecompositionModel(
  coreRows:
    readonly SpendDecompositionCoreSourceRow[],
  reviewRows:
    readonly SpendDecompositionReviewSourceRow[],
  scope: ReviewedPhase3Scope,
): SpendDecompositionModel {
  const relationship =
    validateSourceRelationship(
      coreRows,
      reviewRows,
    );

  validateScopeMembership(
    scope,
    relationship.coreArmIds,
    relationship.reviewArmIds,
  );

  const coreTrials =
    normalizeCoreRows(coreRows);

  const kimiTrials =
    normalizeKimiRows(
      relationship.kimiRows,
    );

  const allTrials =
    Object.freeze([
      ...coreTrials,
      ...kimiTrials,
    ]);

  const selectedTrials =
    scope.scopeId === "phase3-core"
      ? coreTrials
      : allTrials;

  const arms =
    scope.arms.map((reviewedArm) => {
      const rows =
        selectedTrials.filter(
          (row) =>
            row.armId
            === reviewedArm.armId,
        );

      return buildArm(
        reviewedArm,
        rows,
      );
    });

  const segments =
    aggregateSegments(arms);

  const trialCount =
    arms.reduce(
      (total, arm) =>
        total + arm.trialCount,
      0,
    );

  const successCount =
    arms.reduce(
      (total, arm) =>
        total + arm.successCount,
      0,
    );

  if (
    trialCount !== scope.trialCount
    || successCount !== scope.successCount
  ) {
    throw new Error(
      "scope_outcome_count_mismatch",
    );
  }

  const recordedCostUsd =
    sumDecimals(
      arms.map(
        (arm) =>
          arm.recordedCostUsd,
      ),
    );

  if (
    !decimalEqual(
      recordedCostUsd,
      requireNonnegativeDecimal(
        scope.costEvidence
          .recordedCostUsd,
        "scope_recorded_cost_invalid",
      ),
    )
  ) {
    throw new Error(
      "scope_recorded_cost_mismatch",
    );
  }

  const summedArmAccountingGapUsd =
    sumDecimals(
      arms.map(
        (arm) =>
          arm.accountingGapUsd,
      ),
    );

  const scopeAccountingGapUsd =
    requireNonnegativeDecimal(
      scope.costEvidence
        .accountingGapUsd,
      "scope_accounting_gap_invalid",
    );

  const gapDelta =
    subtractDecimals(
      summedArmAccountingGapUsd,
      scopeAccountingGapUsd,
    );

  if (
    !decimalAbsWithin(
      gapDelta,
      RECONCILIATION_TOLERANCE_USD,
    )
  ) {
    throw new Error(
      "scope_accounting_gap_reconciliation_mismatch",
    );
  }

  const summedSelectedArmCostUsd =
    sumDecimals(
      arms.map(
        (arm) =>
          arm.selectedReviewedCostUsd,
      ),
    );

  if (
    !decimalEqual(
      sumDecimals([
        recordedCostUsd,
        summedArmAccountingGapUsd,
      ]),
      summedSelectedArmCostUsd,
    )
  ) {
    throw new Error(
      "scope_five_part_reconciliation_mismatch",
    );
  }

  const selectedScope =
    selectedScopeCost(scope);

  const scopeReconciliationDeltaUsd =
    subtractDecimals(
      summedSelectedArmCostUsd,
      selectedScope.amount,
    );

  if (
    !decimalAbsWithin(
      scopeReconciliationDeltaUsd,
      RECONCILIATION_TOLERANCE_USD,
    )
  ) {
    throw new Error(
      "scope_selected_cost_reconciliation_mismatch",
    );
  }

  const missingRecordedCostCount =
    arms.reduce(
      (total, arm) =>
        total
        + arm.missingRecordedCostCount,
      0,
    );

  const unresolvedCostCount =
    arms.reduce(
      (total, arm) =>
        total
        + arm.unresolvedCostCount,
      0,
    );

  if (
    missingRecordedCostCount
      !== scope.costEvidence
        .missingRecordedCostCount
    || unresolvedCostCount
      !== scope.costEvidence
        .unresolvedCostCount
  ) {
    throw new Error(
      "scope_missing_or_unresolved_count_mismatch",
    );
  }

  const segmentTrialCount =
    segments.reduce(
      (total, segment) =>
        total + segment.trialCount,
      0,
    );

  if (segmentTrialCount !== trialCount) {
    throw new Error(
      "scope_segment_trial_count_mismatch",
    );
  }

  const segmentRecordedCost =
    sumDecimals(
      segments.map(
        (segment) =>
          segment.recordedCostUsd,
      ),
    );

  if (
    !decimalEqual(
      segmentRecordedCost,
      recordedCostUsd,
    )
  ) {
    throw new Error(
      "scope_segment_recorded_cost_mismatch",
    );
  }

  return Object.freeze({
    scopeId: scope.scopeId,
    armCount: arms.length,
    trialCount,
    successCount,
    segments,
    recordedCostUsd,
    summedArmAccountingGapUsd,
    scopeAccountingGapUsd,
    summedSelectedArmCostUsd,
    scopeSelectedReviewedCostUsd:
      selectedScope.amount,
    scopeSelectedCostBasis:
      selectedScope.basis,
    scopeReconciliationDeltaUsd,
    scopeReconciliationToleranceUsd:
      RECONCILIATION_TOLERANCE_USD,
    missingRecordedCostCount,
    unresolvedCostCount,
    arms: Object.freeze(arms),
  });
}

export function getSpendDecompositionSegment(
  model: SpendDecompositionModel,
  id: SpendDecompositionSegmentId,
): SpendDecompositionSegment {
  const segment =
    model.segments.find(
      (candidate) =>
        candidate.id === id,
    );

  if (!segment) {
    throw new Error(
      `spend_segment_missing:${id}`,
    );
  }

  return segment;
}
