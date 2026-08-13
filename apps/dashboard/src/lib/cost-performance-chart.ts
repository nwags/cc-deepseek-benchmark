import {
  PHASE3_REVIEWED_COMPARISON,
  getReviewedPhase3Scope,
  selectReviewedPhase3Scope,
  type ReviewedPhase3Arm,
  type ReviewedPhase3Scope,
  type ReviewedScopeSelection,
} from "./phase3-reviewed-comparison";
import {
  getReviewedRunSelectionScope,
  type ReviewedSelectedRun,
  type ReviewedRunSelectionScope,
} from "./phase3-reviewed-run-selection";
import { buildReviewedRunHref } from "./overview-reviewed-comparison";
import {
  DEFAULT_CHART_SCOPE,
  stableTextCompare,
  type ChartArmDatum,
  type ChartEvidenceAmount,
  type ChartMetricAvailable,
  type ChartMetricUnavailable,
  type ChartMetricValue,
  type ChartScope,
  type ChartXAxisMetric,
} from "./cost-performance-chart-view";

export * from "./cost-performance-chart-view";

type ReviewedMoonshotProvider = "moonshot" | "moonshot-kimi";

type ChartProviderNormalization = Readonly<{
  providerFamily: "moonshot-kimi";
  label: "Moonshot / Kimi";
}>;

export const CHART_REVIEWED_PROVIDER_NORMALIZATION = Object.freeze({
  moonshot: Object.freeze({
    providerFamily: "moonshot-kimi",
    label: "Moonshot / Kimi",
  }),
  "moonshot-kimi": Object.freeze({
    providerFamily: "moonshot-kimi",
    label: "Moonshot / Kimi",
  }),
}) satisfies Readonly<Record<ReviewedMoonshotProvider, ChartProviderNormalization>>;
const DERIVED_DECIMAL_PLACES = 15;

type DecimalParts = Readonly<{ units: bigint; scale: number }>;

function decimalParts(value: string, label: string): DecimalParts {
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!match) throw new Error(`${label} is not a reviewed decimal`);
  const fraction = match[3] ?? "";
  return {
    units: BigInt(`${match[1]}${match[2]}${fraction}`),
    scale: fraction.length,
  };
}

function decimalNumber(value: string, label: string): number {
  decimalParts(value, label);
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`${label} is not finite`);
  return parsed;
}

function divideDecimal(value: string, divisor: number, label: string): Readonly<{
  decimal: string;
  value: number;
}> {
  if (!Number.isSafeInteger(divisor) || divisor <= 0) {
    throw new Error(`${label} divisor must be a positive safe integer`);
  }
  const source = decimalParts(value, label);
  const targetScale = DERIVED_DECIMAL_PLACES;
  const numerator = source.units * (10n ** BigInt(targetScale));
  const denominator = BigInt(divisor) * (10n ** BigInt(source.scale));
  const negative = numerator < 0n;
  const absoluteNumerator = negative ? -numerator : numerator;
  let quotient = absoluteNumerator / denominator;
  const remainder = absoluteNumerator % denominator;
  if (remainder * 2n >= denominator) quotient += 1n;
  if (negative) quotient = -quotient;

  const absoluteQuotient = quotient < 0n ? -quotient : quotient;
  const padded = absoluteQuotient.toString().padStart(targetScale + 1, "0");
  const whole = padded.slice(0, -targetScale);
  const fraction = padded.slice(-targetScale).replace(/0+$/, "");
  const decimal = `${quotient < 0n ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
  return { decimal, value: decimalNumber(decimal, `${label} quotient`) };
}

function providerPresentationFor(reviewedProvider: string): Readonly<{
  providerFamily: string;
  label: string;
}> {
  if (Object.prototype.hasOwnProperty.call(
    CHART_REVIEWED_PROVIDER_NORMALIZATION,
    reviewedProvider,
  )) {
    return CHART_REVIEWED_PROVIDER_NORMALIZATION[
      reviewedProvider as ReviewedMoonshotProvider
    ];
  }
  return Object.freeze({ providerFamily: reviewedProvider, label: reviewedProvider });
}

function availableDerivedMetric(
  totalUsd: string,
  trialCount: number,
  qualification: string | null,
  label: string,
): ChartMetricAvailable {
  const divided = divideDecimal(totalUsd, trialCount, label);
  return Object.freeze({
    status: "available",
    value: divided.value,
    decimalUsd: divided.decimal,
    sourceTotalUsd: totalUsd,
    derivation: "reviewed_total_divided_by_trial_count",
    qualification,
  });
}

function availableReviewedMetric(valueUsd: string, label: string): ChartMetricAvailable {
  return Object.freeze({
    status: "available",
    value: decimalNumber(valueUsd, label),
    decimalUsd: valueUsd,
    sourceTotalUsd: null,
    derivation: "reviewed_f1_cost_per_clean_success",
    qualification: null,
  });
}

function unavailableMetric(reason: string): ChartMetricUnavailable {
  return Object.freeze({
    status: "unavailable",
    value: null,
    decimalUsd: null,
    sourceTotalUsd: null,
    derivation: null,
    qualification: null,
    reason,
  });
}

function reviewedComparableCost(arm: ReviewedPhase3Arm): string | null {
  if (arm.costBasis === "adjusted_known_cost") return arm.adjustedKnownCostUsd;
  if (arm.costBasis === "qualified_retained_rate_estimate") return arm.qualifiedRetainedRateCostUsd;
  return null;
}

function adjustedMetricForArm(arm: ReviewedPhase3Arm): ChartMetricValue {
  const reviewedCost = reviewedComparableCost(arm);
  if (reviewedCost === null) {
    return unavailableMetric(
      "The reviewed F1 contract provides neither adjusted-known cost nor a qualified comparable estimate for this arm.",
    );
  }
  const qualification = arm.costBasis === "qualified_retained_rate_estimate"
    ? "Uses the reviewed qualified retained-rate estimate, not adjusted-known, invoice, provider-billed, or official-price cost."
    : null;
  return availableDerivedMetric(
    reviewedCost,
    arm.trialCount,
    qualification,
    `${arm.armId} reviewed comparable cost`,
  );
}

function cleanSuccessMetricForArm(arm: ReviewedPhase3Arm): ChartMetricValue {
  if (arm.adjustedCostPerCleanSuccessUsd === null) {
    return unavailableMetric(
      "The reviewed F1 contract marks cost per clean success unavailable; it is not derived from a qualified total by arithmetic convenience.",
    );
  }
  return availableReviewedMetric(
    arm.adjustedCostPerCleanSuccessUsd,
    `${arm.armId} reviewed cost per clean success`,
  );
}

function recordedMetricForArm(arm: ReviewedPhase3Arm): ChartMetricValue {
  const qualification = arm.missingRecordedCostCount > 0
    ? `Recorded cost is a lower bound because ${arm.missingRecordedCostCount} reviewed trial cost row${arm.missingRecordedCostCount === 1 ? " is" : "s are"} missing.`
    : null;
  return availableDerivedMetric(
    arm.recordedCostUsd,
    arm.trialCount,
    qualification,
    `${arm.armId} recorded cost`,
  );
}

function failureIncompleteSpendForArm(arm: ReviewedPhase3Arm): ChartEvidenceAmount {
  if (arm.adjustedFailureOrIncompleteCostUsd === null
    || arm.outcomeCostAllocationStatus !== "available") {
    return Object.freeze({
      status: "unavailable",
      decimalUsd: null,
      value: null,
      evidenceBasis: null,
      reason: "Reviewed F1 outcome-cost allocation is unavailable for this arm; failure/incomplete spend is not treated as zero.",
    });
  }
  return Object.freeze({
    status: "available",
    decimalUsd: arm.adjustedFailureOrIncompleteCostUsd,
    value: decimalNumber(
      arm.adjustedFailureOrIncompleteCostUsd,
      `${arm.armId} failure/incomplete spend`,
    ),
    evidenceBasis: "reviewed_adjusted_outcome_cost",
  });
}

function qualificationForArm(
  arm: ReviewedPhase3Arm,
  selection: ReviewedSelectedRun,
): string | null {
  if (arm.costBasis !== "qualified_retained_rate_estimate") return null;
  const qualifications = [
    "Qualified retained-rate estimate",
    "pricing-source provenance incomplete",
    "arm-run/provider-log allocation confidence low",
    "trial allocation unresolved",
    "not invoice-level or provider-billed spend",
  ];
  if (selection.providerLogAllocationQualification?.providerLogExclusivityStatus === "not_proven") {
    qualifications.splice(4, 0, "provider-log exclusivity not proven");
  }
  return qualifications.join("; ");
}

function armDetailHref(armId: string): string {
  const params = new URLSearchParams({ arm_id: armId });
  return `/trial-quality?${params.toString()}`;
}

function assertMatchingReviewedInputs(
  scope: ReviewedPhase3Scope,
  runSelectionScope: ReviewedRunSelectionScope,
): Map<string, ReviewedRunSelectionScope["selections"][number]> {
  if (scope.scopeId !== runSelectionScope.scopeId) {
    throw new Error("F1 chart scope and G1 run-selection scope do not match");
  }
  const selections = new Map<string, ReviewedRunSelectionScope["selections"][number]>();
  const labels = new Set<string>();
  for (const selection of runSelectionScope.selections) {
    if (selections.has(selection.armId)) {
      throw new Error(`G1 has more than one selected run for ${selection.armId}`);
    }
    if (labels.has(selection.selectedRunLabel)) {
      throw new Error(`G1 selected run label is duplicated: ${selection.selectedRunLabel}`);
    }
    selections.set(selection.armId, selection);
    labels.add(selection.selectedRunLabel);
  }
  const armIds = new Set(scope.arms.map((arm) => arm.armId));
  if (scope.arms.length !== scope.armCount
    || runSelectionScope.selections.length !== runSelectionScope.selectedRunCount
    || scope.armCount !== runSelectionScope.selectedRunCount
    || scope.trialCount !== runSelectionScope.trialCount
    || [...selections].some(([armId]) => !armIds.has(armId))) {
    throw new Error("F1 chart arms and G1 selected-run membership disagree");
  }
  return selections;
}

export function buildCostPerformanceChartArms(
  scope: ReviewedPhase3Scope,
  runSelectionScope: ReviewedRunSelectionScope,
  coreArmIds: readonly string[],
): readonly ChartArmDatum[] {
  const selections = assertMatchingReviewedInputs(scope, runSelectionScope);
  const coreIds = new Set(coreArmIds);
  if (coreIds.size !== coreArmIds.length) {
    throw new Error("F1 core membership supplied to the chart contains duplicate arm IDs");
  }
  if (scope.scopeId === "phase3-core"
    && scope.arms.some((arm) => !coreIds.has(arm.armId))) {
    throw new Error("The active F1 core scope contains an arm outside canonical core membership");
  }

  const data = scope.arms.map((arm): ChartArmDatum => {
    const selection = selections.get(arm.armId);
    if (!selection) throw new Error(`No frozen G1 selected run exists for ${arm.armId}`);
    if (selection.trialCount !== arm.trialCount) {
      throw new Error(`F1/G1 trial counts disagree for ${arm.armId}`);
    }

    const adjustedCostPerAttempt = adjustedMetricForArm(arm);
    const costPerCleanSuccess = cleanSuccessMetricForArm(arm);
    const recordedCostPerAttempt = recordedMetricForArm(arm);
    const metricAvailabilityReasons: Partial<Record<ChartXAxisMetric, string>> = {};
    for (const [metric, value] of [
      ["adjusted_cost_per_attempt", adjustedCostPerAttempt],
      ["cost_per_clean_success", costPerCleanSuccess],
      ["recorded_cost_per_attempt", recordedCostPerAttempt],
    ] as const) {
      if (value.status === "unavailable") metricAvailabilityReasons[metric] = value.reason;
    }

    const passRate = arm.successCount / arm.trialCount;
    if (!Number.isFinite(passRate)) throw new Error(`${arm.armId} pass rate is not finite`);
    const providerPresentation = providerPresentationFor(arm.provider);
    const membership: ChartScope[] = coreIds.has(arm.armId)
      ? ["phase3-core", "phase3-extended"]
      : ["phase3-extended"];
    return Object.freeze({
      armId: arm.armId,
      displayName: arm.backendModel,
      reviewedProvider: arm.provider,
      providerFamily: providerPresentation.providerFamily,
      providerFamilyLabel: providerPresentation.label,
      activeScope: scope.scopeId,
      scopeMembership: Object.freeze(membership),
      selectedRunLabel: selection.selectedRunLabel,
      trialCount: arm.trialCount,
      successCount: arm.successCount,
      passRate,
      cleanSuccessCount: arm.cleanSuccessCount,
      recordedCostUsd: arm.recordedCostUsd,
      reviewedComparableCostUsd: reviewedComparableCost(arm),
      adjustedKnownCostUsd: arm.adjustedKnownCostUsd,
      qualifiedRetainedRateCostUsd: arm.qualifiedRetainedRateCostUsd,
      costBasis: arm.costBasis,
      costBasisLabel: arm.costBasis === "qualified_retained_rate_estimate"
        ? "Qualified retained-rate estimate"
        : "Adjusted known cost",
      costSources: Object.freeze([...arm.costSources]),
      costConfidence: arm.costConfidence,
      pricingProvenanceStatus: arm.pricingProvenanceStatus,
      armRunAllocationConfidence: arm.armRunAllocationConfidence,
      trialAllocationStatus: arm.trialAllocationStatus,
      billingReconciliationStatus: arm.billingReconciliationStatus,
      providerLogExclusivityStatus:
        selection.providerLogAllocationQualification?.providerLogExclusivityStatus ?? null,
      accountingGapUsd: arm.accountingGapUsd,
      missingRecordedCostCount: arm.missingRecordedCostCount,
      unresolvedCostCount: arm.unresolvedCostCount,
      adjustedCostPerAttempt,
      costPerCleanSuccess,
      recordedCostPerAttempt,
      failureIncompleteSpend: failureIncompleteSpendForArm(arm),
      selectedRunHref: buildReviewedRunHref(selection.selectedRunLabel),
      armHref: armDetailHref(arm.armId),
      qualificationText: qualificationForArm(arm, selection),
      metricAvailabilityReasons: Object.freeze(metricAvailabilityReasons),
    });
  });

  return Object.freeze(data.sort((left, right) => stableTextCompare(left.armId, right.armId)));
}

export function getCostPerformanceChartArms(
  scopeId: ChartScope = DEFAULT_CHART_SCOPE,
): readonly ChartArmDatum[] {
  const coreArmIds = PHASE3_REVIEWED_COMPARISON.scopes["phase3-core"].arms.map(
    (arm) => arm.armId,
  );
  return buildCostPerformanceChartArms(
    getReviewedPhase3Scope(scopeId),
    getReviewedRunSelectionScope(scopeId),
    coreArmIds,
  );
}

export function selectCostPerformanceChartScope(
  value: string | readonly string[] | null | undefined,
): ReviewedScopeSelection {
  return selectReviewedPhase3Scope(value);
}
