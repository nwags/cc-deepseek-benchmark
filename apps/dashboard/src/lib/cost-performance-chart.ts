import {
  PHASE3_REVIEWED_COMPARISON,
  getReviewedPhase3Scope,
  selectReviewedPhase3Scope,
  type ReviewedPhase3Arm,
  type ReviewedPhase3Scope,
  type ReviewedPhase3ScopeId,
  type ReviewedScopeSelection,
} from "./phase3-reviewed-comparison";
import {
  getReviewedRunSelectionScope,
  type ReviewedSelectedRun,
  type ReviewedRunSelectionScope,
} from "./phase3-reviewed-run-selection";
import { buildReviewedRunHref } from "./overview-reviewed-comparison";

export type ChartScope = ReviewedPhase3ScopeId;

export type ChartXAxisMetric =
  | "adjusted_cost_per_attempt"
  | "cost_per_clean_success"
  | "recorded_cost_per_attempt";

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

export type ChartMetricAvailable = Readonly<{
  status: "available";
  value: number;
  decimalUsd: string;
  sourceTotalUsd: string | null;
  derivation:
    | "reviewed_total_divided_by_trial_count"
    | "reviewed_f1_cost_per_clean_success";
  qualification: string | null;
}>;

export type ChartMetricUnavailable = Readonly<{
  status: "unavailable";
  value: null;
  decimalUsd: null;
  sourceTotalUsd: null;
  derivation: null;
  qualification: null;
  reason: string;
}>;

export type ChartMetricValue = ChartMetricAvailable | ChartMetricUnavailable;

export type ChartEvidenceAmount =
  | Readonly<{
      status: "available";
      decimalUsd: string;
      value: number;
      evidenceBasis: "reviewed_adjusted_outcome_cost";
    }>
  | Readonly<{
      status: "unavailable";
      decimalUsd: null;
      value: null;
      evidenceBasis: null;
      reason: string;
    }>;

export type ChartArmDatum = Readonly<{
  armId: string;
  displayName: string;
  reviewedProvider: string;
  providerFamily: string;
  providerFamilyLabel: string;
  activeScope: ChartScope;
  scopeMembership: readonly ChartScope[];
  selectedRunLabel: string;
  trialCount: number;
  successCount: number;
  passRate: number;
  cleanSuccessCount: number;
  recordedCostUsd: string;
  reviewedComparableCostUsd: string | null;
  adjustedKnownCostUsd: string | null;
  qualifiedRetainedRateCostUsd: string | null;
  costBasis: ReviewedPhase3Arm["costBasis"];
  costBasisLabel: "Adjusted known cost" | "Qualified retained-rate estimate";
  costSources: readonly string[];
  costConfidence: string;
  pricingProvenanceStatus: ReviewedPhase3Arm["pricingProvenanceStatus"];
  armRunAllocationConfidence: ReviewedPhase3Arm["armRunAllocationConfidence"];
  trialAllocationStatus: ReviewedPhase3Arm["trialAllocationStatus"];
  billingReconciliationStatus: ReviewedPhase3Arm["billingReconciliationStatus"];
  providerLogExclusivityStatus: "not_proven" | null;
  accountingGapUsd: string;
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  adjustedCostPerAttempt: ChartMetricValue;
  costPerCleanSuccess: ChartMetricValue;
  recordedCostPerAttempt: ChartMetricValue;
  failureIncompleteSpend: ChartEvidenceAmount;
  selectedRunHref: string;
  armHref: string;
  qualificationText: string | null;
  metricAvailabilityReasons: Readonly<Partial<Record<ChartXAxisMetric, string>>>;
}>;

export type ChartProviderFilterOption = Readonly<{
  providerFamily: string;
  label: string;
  armCount: number;
}>;

export type ChartMetricSelection = Readonly<{
  metric: ChartXAxisMetric;
  warning: "invalid_metric" | "repeated_metric" | null;
  warningMessage: string | null;
  usedDefault: boolean;
}>;

export type ChartPlotPoint = Readonly<{
  arm: ChartArmDatum;
  armId: string;
  xValue: number;
  xDecimalUsd: string;
  passRate: number;
}>;

export type ChartMetricEligibility = Readonly<{
  eligiblePoints: readonly ChartPlotPoint[];
  unavailableArms: readonly ChartArmDatum[];
}>;

export type CostPerformanceChartView = Readonly<{
  metric: ChartXAxisMetric;
  selectedArmIds: readonly string[];
  selectedProviderFamilies: readonly string[];
  providerVisibleArms: readonly ChartArmDatum[];
  selectedVisibleArms: readonly ChartArmDatum[];
  plotPoints: readonly ChartPlotPoint[];
  unavailableMetricArms: readonly ChartArmDatum[];
  frontier: readonly ChartPlotPoint[];
}>;

export type AccessibleChartRow = Readonly<{
  armId: string;
  displayName: string;
  reviewedProvider: string;
  providerFamily: string;
  providerFamilyLabel: string;
  scopeMembership: readonly ChartScope[];
  selectedRunLabel: string;
  successCount: number;
  trialCount: number;
  passRate: number;
  xMetric: ChartXAxisMetric;
  xMetricValue: ChartMetricValue;
  costBasis: ChartArmDatum["costBasis"];
  costBasisLabel: ChartArmDatum["costBasisLabel"];
  costSources: readonly string[];
  costConfidence: string;
  pricingProvenanceStatus: ChartArmDatum["pricingProvenanceStatus"];
  armRunAllocationConfidence: ChartArmDatum["armRunAllocationConfidence"];
  trialAllocationStatus: ChartArmDatum["trialAllocationStatus"];
  billingReconciliationStatus: ChartArmDatum["billingReconciliationStatus"];
  providerLogExclusivityStatus: ChartArmDatum["providerLogExclusivityStatus"];
  accountingGapUsd: string;
  failureIncompleteSpend: ChartEvidenceAmount;
  qualificationText: string | null;
  armHref: string;
  selectedRunHref: string;
}>;

export const DEFAULT_CHART_SCOPE: ChartScope = "phase3-extended";
export const DEFAULT_CHART_X_AXIS_METRIC: ChartXAxisMetric = "adjusted_cost_per_attempt";

/** Values within this absolute tolerance are treated as equal on either axis. */
export const PARETO_FLOAT_TOLERANCE = 1e-12;

export const CHART_X_AXIS_OPTIONS: readonly Readonly<{
  metric: ChartXAxisMetric;
  label: string;
}>[] = Object.freeze([
  Object.freeze({ metric: "adjusted_cost_per_attempt", label: "Adjusted cost per attempt" }),
  Object.freeze({ metric: "cost_per_clean_success", label: "Cost per clean success" }),
  Object.freeze({ metric: "recorded_cost_per_attempt", label: "Recorded cost per attempt" }),
]);

const CHART_X_AXIS_METRICS = new Set<ChartXAxisMetric>(
  CHART_X_AXIS_OPTIONS.map((option) => option.metric),
);
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

function stableTextCompare(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
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

function freezeStrings(values: Iterable<string>): readonly string[] {
  return Object.freeze([...new Set(values)].sort(stableTextCompare));
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

export function selectChartXAxisMetric(
  value: string | readonly string[] | null | undefined,
): ChartMetricSelection {
  if (value === null || value === undefined || value === "") {
    return Object.freeze({
      metric: DEFAULT_CHART_X_AXIS_METRIC,
      warning: null,
      warningMessage: null,
      usedDefault: true,
    });
  }
  if (Array.isArray(value)) {
    return Object.freeze({
      metric: DEFAULT_CHART_X_AXIS_METRIC,
      warning: "repeated_metric",
      warningMessage: "Repeated x-axis metric values are not supported; adjusted cost per attempt was selected.",
      usedDefault: true,
    });
  }
  if (CHART_X_AXIS_METRICS.has(value as ChartXAxisMetric)) {
    return Object.freeze({
      metric: value as ChartXAxisMetric,
      warning: null,
      warningMessage: null,
      usedDefault: false,
    });
  }
  return Object.freeze({
    metric: DEFAULT_CHART_X_AXIS_METRIC,
    warning: "invalid_metric",
    warningMessage: "Unknown x-axis metric; adjusted cost per attempt was selected.",
    usedDefault: true,
  });
}

export function deriveProviderFilterOptions(
  arms: readonly ChartArmDatum[],
): readonly ChartProviderFilterOption[] {
  const providers = new Map<string, { label: string; armCount: number }>();
  for (const arm of arms) {
    const current = providers.get(arm.providerFamily);
    if (current && current.label !== arm.providerFamilyLabel) {
      throw new Error(`Provider family ${arm.providerFamily} has conflicting presentation labels`);
    }
    providers.set(arm.providerFamily, {
      label: arm.providerFamilyLabel,
      armCount: (current?.armCount ?? 0) + 1,
    });
  }
  return Object.freeze(
    [...providers]
      .sort(([left], [right]) => stableTextCompare(left, right))
      .map(([providerFamily, option]) => Object.freeze({
        providerFamily,
        label: option.label,
        armCount: option.armCount,
      })),
  );
}

export function selectAllProviderFamilies(
  options: readonly ChartProviderFilterOption[],
): readonly string[] {
  return freezeStrings(options.map((option) => option.providerFamily));
}

export function clearProviderFamilies(): readonly string[] {
  return Object.freeze([]);
}

export function selectAllChartArmIds(arms: readonly ChartArmDatum[]): readonly string[] {
  return freezeStrings(arms.map((arm) => arm.armId));
}

export function clearChartArmIds(): readonly string[] {
  return Object.freeze([]);
}

export function filterProviderVisibleArms(
  arms: readonly ChartArmDatum[],
  selectedProviderFamilies: readonly string[],
): readonly ChartArmDatum[] {
  const providers = new Set(selectedProviderFamilies);
  return Object.freeze(arms.filter((arm) => providers.has(arm.providerFamily)));
}

export function filterSelectedVisibleArms(
  providerVisibleArms: readonly ChartArmDatum[],
  selectedArmIds: readonly string[],
): readonly ChartArmDatum[] {
  const selected = new Set(selectedArmIds);
  return Object.freeze(providerVisibleArms.filter((arm) => selected.has(arm.armId)));
}

export function metricValueForArm(
  arm: ChartArmDatum,
  metric: ChartXAxisMetric,
): ChartMetricValue {
  if (metric === "adjusted_cost_per_attempt") return arm.adjustedCostPerAttempt;
  if (metric === "cost_per_clean_success") return arm.costPerCleanSuccess;
  return arm.recordedCostPerAttempt;
}

export function deriveMetricEligibility(
  arms: readonly ChartArmDatum[],
  metric: ChartXAxisMetric,
): ChartMetricEligibility {
  const eligiblePoints: ChartPlotPoint[] = [];
  const unavailableArms: ChartArmDatum[] = [];
  for (const arm of arms) {
    const metricValue = metricValueForArm(arm, metric);
    if (metricValue.status === "unavailable") {
      unavailableArms.push(arm);
      continue;
    }
    eligiblePoints.push(Object.freeze({
      arm,
      armId: arm.armId,
      xValue: metricValue.value,
      xDecimalUsd: metricValue.decimalUsd,
      passRate: arm.passRate,
    }));
  }
  eligiblePoints.sort((left, right) => left.xValue - right.xValue
    || right.passRate - left.passRate
    || stableTextCompare(left.armId, right.armId));
  unavailableArms.sort((left, right) => stableTextCompare(left.armId, right.armId));
  return Object.freeze({
    eligiblePoints: Object.freeze(eligiblePoints),
    unavailableArms: Object.freeze(unavailableArms),
  });
}

function compareWithTolerance(left: number, right: number, tolerance: number): -1 | 0 | 1 {
  if (left < right - tolerance) return -1;
  if (left > right + tolerance) return 1;
  return 0;
}

function dominates(
  candidate: ChartPlotPoint,
  point: ChartPlotPoint,
  tolerance: number,
): boolean {
  const costComparison = compareWithTolerance(candidate.xValue, point.xValue, tolerance);
  const passRateComparison = compareWithTolerance(candidate.passRate, point.passRate, tolerance);
  return costComparison <= 0
    && passRateComparison >= 0
    && (costComparison < 0 || passRateComparison > 0);
}

export function deriveParetoFrontier(
  eligiblePoints: readonly ChartPlotPoint[],
  tolerance: number = PARETO_FLOAT_TOLERANCE,
): readonly ChartPlotPoint[] {
  if (!Number.isFinite(tolerance) || tolerance < 0) {
    throw new Error("Pareto tolerance must be a nonnegative finite number");
  }
  const ids = new Set<string>();
  for (const point of eligiblePoints) {
    if (ids.has(point.armId)) throw new Error(`Duplicate Pareto point for ${point.armId}`);
    if (!Number.isFinite(point.xValue) || !Number.isFinite(point.passRate)) {
      throw new Error(`Pareto point for ${point.armId} must be finite`);
    }
    ids.add(point.armId);
  }
  const frontier = eligiblePoints.filter((point) => !eligiblePoints.some(
    (candidate) => candidate.armId !== point.armId && dominates(candidate, point, tolerance),
  ));
  return Object.freeze([...frontier].sort((left, right) => left.xValue - right.xValue
    || right.passRate - left.passRate
    || stableTextCompare(left.armId, right.armId)));
}

export function deriveCostPerformanceChartView(input: Readonly<{
  arms: readonly ChartArmDatum[];
  selectedProviderFamilies: readonly string[];
  selectedArmIds: readonly string[];
  metric: ChartXAxisMetric;
  paretoTolerance?: number;
}>): CostPerformanceChartView {
  const providerVisibleArms = filterProviderVisibleArms(
    input.arms,
    input.selectedProviderFamilies,
  );
  const selectedVisibleArms = filterSelectedVisibleArms(
    providerVisibleArms,
    input.selectedArmIds,
  );
  const eligibility = deriveMetricEligibility(selectedVisibleArms, input.metric);
  return Object.freeze({
    metric: input.metric,
    selectedArmIds: freezeStrings(input.selectedArmIds),
    selectedProviderFamilies: freezeStrings(input.selectedProviderFamilies),
    providerVisibleArms,
    selectedVisibleArms,
    plotPoints: eligibility.eligiblePoints,
    unavailableMetricArms: eligibility.unavailableArms,
    frontier: deriveParetoFrontier(eligibility.eligiblePoints, input.paretoTolerance),
  });
}

export function buildAccessibleChartRows(
  arms: readonly ChartArmDatum[],
  metric: ChartXAxisMetric,
): readonly AccessibleChartRow[] {
  return Object.freeze(arms.map((arm) => Object.freeze({
    armId: arm.armId,
    displayName: arm.displayName,
    reviewedProvider: arm.reviewedProvider,
    providerFamily: arm.providerFamily,
    providerFamilyLabel: arm.providerFamilyLabel,
    scopeMembership: arm.scopeMembership,
    selectedRunLabel: arm.selectedRunLabel,
    successCount: arm.successCount,
    trialCount: arm.trialCount,
    passRate: arm.passRate,
    xMetric: metric,
    xMetricValue: metricValueForArm(arm, metric),
    costBasis: arm.costBasis,
    costBasisLabel: arm.costBasisLabel,
    costSources: arm.costSources,
    costConfidence: arm.costConfidence,
    pricingProvenanceStatus: arm.pricingProvenanceStatus,
    armRunAllocationConfidence: arm.armRunAllocationConfidence,
    trialAllocationStatus: arm.trialAllocationStatus,
    billingReconciliationStatus: arm.billingReconciliationStatus,
    providerLogExclusivityStatus: arm.providerLogExclusivityStatus,
    accountingGapUsd: arm.accountingGapUsd,
    failureIncompleteSpend: arm.failureIncompleteSpend,
    qualificationText: arm.qualificationText,
    armHref: arm.armHref,
    selectedRunHref: arm.selectedRunHref,
  })));
}
