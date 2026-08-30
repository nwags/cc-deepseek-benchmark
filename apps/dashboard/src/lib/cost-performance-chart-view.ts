import type {
  CurrentSelectedCostRelation,
} from "./current-cost-relation";

export type ChartScope = "phase3-core" | "phase3-extended";

export type ChartXAxisMetric =
  | "adjusted_cost_per_attempt"
  | "cost_per_clean_success"
  | "recorded_cost_per_attempt";

export type ChartMetricAvailable = Readonly<{
  status: "available";
  value: number;
  decimalUsd: string;
  sourceTotalUsd: string | null;
  derivation:
    | "reviewed_total_divided_by_trial_count"
    | "current_selected_cost_per_attempt"
    | "current_selected_cost_per_clean_success";
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
      evidenceBasis:
        | "historical_reviewed_selected_cost"
        | "provider_rate_reconstruction"
        | "provider_rate_reconstruction_lower_bound"
        | "provider_rate_reconstruction_partial_estimate";
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
  selectedCostUsd: string;
  selectedCostRelation: CurrentSelectedCostRelation;
  selectedEfficiencyRelation: CurrentSelectedCostRelation;
  historicalReviewedCostUsd: string;
  providerBilledCostUsd: string | null;
  reviewedComparableCostUsd: string | null;
  adjustedKnownCostUsd: string | null;
  qualifiedRetainedRateCostUsd: string | null;
  costBasis:
    | "adjusted_known_cost"
    | "qualified_retained_rate_estimate"
    | "provider_billed"
    | "provider_rate_reconstructed_retained_usage"
    | "provider_rate_reconstructed_retained_usage_lower_bound"
    | "provider_rate_reconstructed_retained_usage_partial"
    | "provider_rate_reconstructed_selected_run"
    | "provider_rate_reconstructed_selected_run_request_tier";
  costBasisLabel:
    | "Adjusted known cost"
    | "Qualified retained-rate estimate"
    | "Provider-billed arm total"
    | "Provider-rate reconstructed retained usage"
    | "Provider-rate retained-usage lower bound"
    | "Provider-rate retained-usage partial estimate"
    | "Provider-rate reconstructed selected-run estimate"
    | "Provider-rate reconstructed request-tier estimate";
  costSources: readonly string[];
  costConfidence: string;
  pricingProvenanceStatus: "historical_reviewed_layer" | "incomplete";
  armRunAllocationConfidence: "reviewed_core_layer" | "low";
  trialAllocationStatus:
    | "available_for_reviewed_layer"
    | "available_provider_rate_reconstruction"
    | "available_with_exception_path_lower_bounds"
    | "available_with_unresolved_usage_lower_bounds"
    | "partial_selected_usage_reconstruction_with_unresolved_trials"
    | "unresolved"
    | "unavailable_provider_aggregate";
  billingReconciliationStatus:
    | "exact_arm_total"
    | "not_available_in_current_reconciliation_layer"
    | "preselected_family_billing_context_not_selected_run"
    | "preselected_provider_context_not_selected_run"
    | "provider_invoice_unavailable"
    | "provider_log_not_invoice_level_allocation_low_confidence"
    | "same_day_model_aggregate_not_run_isolated"
    | "selected_run_provider_invoice_unavailable";
  currentSelectedRunLabel: string | null;
  providerLogExclusivityStatus: "not_proven" | null;
  accountingGapUsd: string;
  missingRecordedCostCount: number;
  unresolvedCostCount: number;
  adjustedCostPerAttempt: ChartMetricValue;
  costPerCleanSuccess: ChartMetricValue;
  recordedCostPerAttempt: ChartMetricValue;
  failureIncompleteSpend: ChartEvidenceAmount;
  selectedRunHref: string;
  costProvenanceHref: string;
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
  xMetricRelation: CurrentSelectedCostRelation | null;
  selectedCostUsd: string;
  selectedCostRelation: CurrentSelectedCostRelation;
  selectedEfficiencyRelation: CurrentSelectedCostRelation;
  historicalReviewedCostUsd: string;
  providerBilledCostUsd: string | null;
  costBasis: ChartArmDatum["costBasis"];
  costBasisLabel: ChartArmDatum["costBasisLabel"];
  costSources: readonly string[];
  costConfidence: string;
  pricingProvenanceStatus: ChartArmDatum["pricingProvenanceStatus"];
  armRunAllocationConfidence: ChartArmDatum["armRunAllocationConfidence"];
  trialAllocationStatus: ChartArmDatum["trialAllocationStatus"];
  billingReconciliationStatus: ChartArmDatum["billingReconciliationStatus"];
  currentSelectedRunLabel: string | null;
  providerLogExclusivityStatus: ChartArmDatum["providerLogExclusivityStatus"];
  accountingGapUsd: string;
  failureIncompleteSpend: ChartEvidenceAmount;
  qualificationText: string | null;
  armHref: string;
  selectedRunHref: string;
  costProvenanceHref: string;
}>;

export const DEFAULT_CHART_SCOPE: ChartScope = "phase3-extended";
export const DEFAULT_CHART_X_AXIS_METRIC: ChartXAxisMetric = "adjusted_cost_per_attempt";

/** Values within this absolute tolerance are treated as equal on either axis. */
export const PARETO_FLOAT_TOLERANCE = 1e-12;

export const CHART_X_AXIS_OPTIONS: readonly Readonly<{
  metric: ChartXAxisMetric;
  label: string;
}>[] = Object.freeze([
  Object.freeze({ metric: "adjusted_cost_per_attempt", label: "Selected cost per attempt" }),
  Object.freeze({ metric: "cost_per_clean_success", label: "Cost per clean success" }),
  Object.freeze({ metric: "recorded_cost_per_attempt", label: "Recorded cost per attempt" }),
]);

const CHART_X_AXIS_METRICS = new Set<ChartXAxisMetric>(
  CHART_X_AXIS_OPTIONS.map((option) => option.metric),
);

export function stableTextCompare(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function freezeStrings(values: Iterable<string>): readonly string[] {
  return Object.freeze([...new Set(values)].sort(stableTextCompare));
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

export function metricRelationForArm(
  arm: Pick<ChartArmDatum, "selectedEfficiencyRelation">,
  metric: ChartXAxisMetric,
): CurrentSelectedCostRelation | null {
  return metric === "recorded_cost_per_attempt"
    ? null
    : arm.selectedEfficiencyRelation;
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
    xMetricRelation: metricRelationForArm(arm, metric),
    selectedCostUsd: arm.selectedCostUsd,
    selectedCostRelation: arm.selectedCostRelation,
    selectedEfficiencyRelation: arm.selectedEfficiencyRelation,
    historicalReviewedCostUsd: arm.historicalReviewedCostUsd,
    providerBilledCostUsd: arm.providerBilledCostUsd,
    costBasis: arm.costBasis,
    costBasisLabel: arm.costBasisLabel,
    costSources: arm.costSources,
    costConfidence: arm.costConfidence,
    pricingProvenanceStatus: arm.pricingProvenanceStatus,
    armRunAllocationConfidence: arm.armRunAllocationConfidence,
    trialAllocationStatus: arm.trialAllocationStatus,
    billingReconciliationStatus: arm.billingReconciliationStatus,
    currentSelectedRunLabel: arm.currentSelectedRunLabel,
    providerLogExclusivityStatus: arm.providerLogExclusivityStatus,
    accountingGapUsd: arm.accountingGapUsd,
    failureIncompleteSpend: arm.failureIncompleteSpend,
    qualificationText: arm.qualificationText,
    armHref: arm.armHref,
    selectedRunHref: arm.selectedRunHref,
    costProvenanceHref: arm.costProvenanceHref,
  })));
}
