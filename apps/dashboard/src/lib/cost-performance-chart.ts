import {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  getCurrentReviewedPhase3Scope,
  getCurrentSelectedOutcomeCostEvidence,
  selectCurrentReviewedPhase3Scope,
  type CurrentReviewedPhase3Arm,
  type CurrentReviewedPhase3Scope,
  type CurrentReviewedScopeSelection,
} from "./phase3-current-reviewed-comparison";
import {
  getReviewedRunSelectionScope,
  type ReviewedSelectedRun,
  type ReviewedRunSelectionScope,
} from "./phase3-reviewed-run-selection";
import { buildCostCoverageHref, buildExactRunHref } from "./evidence-links";
import { friendlyModelLabel, providerPresentation } from "./presentation-labels";
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

function availableSelectedMetric(
  valueUsd: string,
  sourceTotalUsd: string,
  derivation:
    | "current_selected_cost_per_attempt"
    | "current_selected_cost_per_clean_success",
  qualification: string | null,
  label: string,
): ChartMetricAvailable {
  return Object.freeze({
    status: "available",
    value: decimalNumber(valueUsd, label),
    decimalUsd: valueUsd,
    sourceTotalUsd,
    derivation,
    qualification,
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

function reviewedComparableCost(
  arm: CurrentReviewedPhase3Arm,
): string | null {
  if (
    arm.historicalReviewedCostBasis === "adjusted_known_cost"
  ) {
    return arm.adjustedKnownCostUsd;
  }
  if (
    arm.historicalReviewedCostBasis
      === "qualified_retained_rate_estimate"
  ) {
    return arm.qualifiedRetainedRateCostUsd;
  }
  return null;
}

function selectedMetricQualification(
  arm: CurrentReviewedPhase3Arm,
): string | null {
  if (arm.selectedCostBasis === "provider_billed") {
    return [
      "Exact provider-billed arm total",
      "current decision-oriented aggregate ratio",
      "trial and outcome allocation unavailable",
      "historical adjusted-cost evidence retained separately",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage"
  ) {
    return [
      "Exact provider-rate reconstruction from verified retained usage",
      "provider invoice unavailable",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage_lower_bound"
  ) {
    const uncertainty =
      arm.unquantifiedAdditionalCostStatus
        === "possible_additional_exception_path_spend"
        ? "possible additional exception-path spend is not quantified"
        : arm.unquantifiedAdditionalCostStatus
            === "possible_additional_unresolved_trial_spend"
          ? "possible additional unresolved-trial spend is not quantified"
          : "additional spend uncertainty is retained in the reviewed evidence";

    return [
      "Lower-bound provider-rate reconstruction from verified retained usage",
      uncertainty,
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage_partial"
  ) {
    return [
      "Partial provider-rate reconstruction from retained selected-run usage",
      "unresolved selected-run spend and cache classification uncertainty remain",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_selected_run_request_tier"
  ) {
    return [
      "Estimated selected-run provider-rate reconstruction",
      "request-level pricing tier was verified",
      "provider invoice unavailable",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_selected_run"
  ) {
    const qualifications = [
      "Estimated selected-run provider-rate reconstruction",
      "provider-context evidence, if present, is retained separately and is not added to selected cost",
    ];

    if (
      arm.selectedCostConfidence
        === "medium_qualified_pricing_provenance"
    ) {
      qualifications.push(
        "pricing-source provenance incomplete",
      );
    }

    return qualifications.join("; ");
  }

  if (
    arm.selectedCostBasis
      === "qualified_retained_rate_estimate"
  ) {
    return [
      "Historical reviewed fallback using the qualified retained-rate estimate",
      "not adjusted-known or provider-billed cost",
    ].join("; ");
  }

  if (
    arm.selectedCostRelation
      === "historical_fallback"
  ) {
    return [
      "Historical reviewed adjusted-known fallback",
      "current provider-family reconciliation is unavailable",
    ].join("; ");
  }

  return null;
}

function adjustedMetricForArm(
  arm: CurrentReviewedPhase3Arm,
): ChartMetricValue {
  return availableSelectedMetric(
    arm.selectedCostPerAttemptUsd,
    arm.selectedCostUsd,
    "current_selected_cost_per_attempt",
    selectedMetricQualification(arm),
    `${arm.armId} selected cost per attempt`,
  );
}

function cleanSuccessMetricForArm(
  arm: CurrentReviewedPhase3Arm,
): ChartMetricValue {
  return availableSelectedMetric(
    arm.selectedCostPerCleanSuccessUsd,
    arm.selectedCostUsd,
    "current_selected_cost_per_clean_success",
    selectedMetricQualification(arm),
    `${arm.armId} selected cost per clean success`,
  );
}

function recordedMetricForArm(
  arm: CurrentReviewedPhase3Arm,
): ChartMetricValue {
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

function failureIncompleteSpendForArm(
  arm: CurrentReviewedPhase3Arm,
): ChartEvidenceAmount {
  const outcomeEvidence =
    getCurrentSelectedOutcomeCostEvidence(arm);

  if (
    outcomeEvidence.status === "unavailable_no_reviewed_outcome_join"
    || outcomeEvidence.status === "unavailable_provider_aggregate"
  ) {
    const reason =
      outcomeEvidence.status
        === "unavailable_provider_aggregate"
        ? "The current selected provider-billed arm total is aggregate-only; failure/incomplete spend is unavailable and historical adjusted outcome spend is not reallocated."
        : "The current selected arm cost has no reviewed outcome-cost join; failure/incomplete spend is unavailable and is not treated as zero.";

    return Object.freeze({
      status: "unavailable",
      decimalUsd: null,
      value: null,
      evidenceBasis: null,
      reason,
    });
  }

  const failureOrIncompleteCostUsd =
    outcomeEvidence.adjustedFailureOrIncompleteCostUsd;
  const evidenceBasis = outcomeEvidence.evidenceBasis;

  if (
    failureOrIncompleteCostUsd === null
    || evidenceBasis === null
  ) {
    throw new Error(
      `${arm.armId} available current outcome evidence is incomplete`,
    );
  }

  return Object.freeze({
    status: "available",
    decimalUsd: failureOrIncompleteCostUsd,
    value: decimalNumber(
      failureOrIncompleteCostUsd,
      `${arm.armId} failure/incomplete spend`,
    ),
    evidenceBasis,
  });
}

function qualificationForArm(
  arm: CurrentReviewedPhase3Arm,
  selection: ReviewedSelectedRun,
): string | null {
  if (arm.selectedCostBasis === "provider_billed") {
    return [
      "Exact provider-billed arm total",
      "current decision-oriented cost basis",
      "trial allocation unavailable from provider aggregate",
      "outcome allocation unavailable from provider aggregate",
      "historical benchmark cost evidence retained separately",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage"
  ) {
    return [
      "Exact provider-rate reconstruction from verified retained usage",
      "provider invoice unavailable",
      "current trial and outcome allocation available",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage_lower_bound"
  ) {
    const uncertainty =
      arm.unquantifiedAdditionalCostStatus
        === "possible_additional_exception_path_spend"
        ? "possible additional exception-path spend remains unquantified"
        : arm.unquantifiedAdditionalCostStatus
            === "possible_additional_unresolved_trial_spend"
          ? "possible additional unresolved-trial spend remains unquantified"
          : "additional spend uncertainty remains qualified";

    return [
      "Lower-bound provider-rate reconstruction from verified retained usage",
      "known retained spend is allocated",
      uncertainty,
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_retained_usage_partial"
  ) {
    return [
      "Partial selected-run provider-rate reconstruction",
      "known retained spend is allocated",
      "unresolved selected-run spend remains",
      "cache classification uncertainty prevents strict lower-bound treatment",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_selected_run_request_tier"
  ) {
    return [
      "Estimated selected-run provider-rate reconstruction",
      "request-level pricing tier verified",
      "current trial and outcome allocation available",
      "provider invoice unavailable",
    ].join("; ");
  }

  if (
    arm.selectedCostBasis
      === "provider_rate_reconstructed_selected_run"
  ) {
    const qualifications = [
      "Estimated selected-run provider-rate reconstruction",
      "provider-context evidence is retained separately and is not added to selected cost",
    ];

    if (
      arm.selectedOutcomeCostAllocationStatus
        === "unavailable_no_reviewed_outcome_join"
    ) {
      qualifications.push(
        "reviewed outcome-cost join unavailable",
      );
    }

    if (
      arm.selectedCostConfidence
        === "medium_qualified_pricing_provenance"
    ) {
      qualifications.push(
        "pricing-source provenance incomplete",
      );
    }

    return qualifications.join("; ");
  }

  if (
    arm.selectedCostBasis
      === "qualified_retained_rate_estimate"
  ) {
    const qualifications = [
      "Historical reviewed fallback",
      "Qualified retained-rate estimate",
      "pricing-source provenance incomplete",
      "arm-run/provider-log allocation confidence low",
      "trial allocation unresolved",
      "not invoice-level or provider-billed spend",
    ];

    if (
      selection.providerLogAllocationQualification
        ?.providerLogExclusivityStatus === "not_proven"
    ) {
      qualifications.splice(
        5,
        0,
        "provider-log exclusivity not proven",
      );
    }

    return qualifications.join("; ");
  }

  if (
    arm.selectedCostRelation
      === "historical_fallback"
  ) {
    return [
      "Historical reviewed fallback",
      "current provider-family reconciliation is unavailable",
      "historical outcome allocation remains historical evidence",
    ].join("; ");
  }

  return null;
}

function armDetailHref(
  armId: string,
): string {
  const params = new URLSearchParams({
    arm_id: armId,
  });
  return `/trial-quality?${params.toString()}`;
}

function assertMatchingReviewedInputs(
  scope: CurrentReviewedPhase3Scope,
  runSelectionScope: ReviewedRunSelectionScope,
): Map<
  string,
  ReviewedRunSelectionScope["selections"][number]
> {
  if (scope.scopeId !== runSelectionScope.scopeId) {
    throw new Error(
      "F1 chart scope and G1 run-selection scope do not match",
    );
  }

  const selections = new Map<
    string,
    ReviewedRunSelectionScope["selections"][number]
  >();
  const labels = new Set<string>();

  for (const selection of runSelectionScope.selections) {
    if (selections.has(selection.armId)) {
      throw new Error(
        `G1 has more than one selected run for ${selection.armId}`,
      );
    }

    if (labels.has(selection.selectedRunLabel)) {
      throw new Error(
        `G1 selected run label is duplicated: ${selection.selectedRunLabel}`,
      );
    }

    selections.set(
      selection.armId,
      selection,
    );
    labels.add(selection.selectedRunLabel);
  }

  const armIds = new Set(
    scope.arms.map((arm) => arm.armId),
  );

  if (
    scope.arms.length !== scope.armCount
    || runSelectionScope.selections.length
      !== runSelectionScope.selectedRunCount
    || scope.armCount
      !== runSelectionScope.selectedRunCount
    || scope.trialCount
      !== runSelectionScope.trialCount
    || [...selections].some(
      ([armId]) => !armIds.has(armId),
    )
  ) {
    throw new Error(
      "F1 chart arms and G1 selected-run membership disagree",
    );
  }

  return selections;
}

function costBasisLabelForArm(
  arm: CurrentReviewedPhase3Arm,
):
  | "Adjusted known cost"
  | "Qualified retained-rate estimate"
  | "Provider-billed arm total"
  | "Provider-rate reconstructed retained usage"
  | "Provider-rate retained-usage lower bound"
  | "Provider-rate retained-usage partial estimate"
  | "Provider-rate reconstructed selected-run estimate"
  | "Provider-rate reconstructed request-tier estimate" {
  switch (arm.selectedCostBasis) {
    case "provider_billed":
      return "Provider-billed arm total";
    case "qualified_retained_rate_estimate":
      return "Qualified retained-rate estimate";
    case "provider_rate_reconstructed_retained_usage":
      return "Provider-rate reconstructed retained usage";
    case "provider_rate_reconstructed_retained_usage_lower_bound":
      return "Provider-rate retained-usage lower bound";
    case "provider_rate_reconstructed_retained_usage_partial":
      return "Provider-rate retained-usage partial estimate";
    case "provider_rate_reconstructed_selected_run":
      return "Provider-rate reconstructed selected-run estimate";
    case "provider_rate_reconstructed_selected_run_request_tier":
      return "Provider-rate reconstructed request-tier estimate";
    case "adjusted_known_cost":
      return "Adjusted known cost";
  }
}

export function buildCostPerformanceChartArms(
  scope: CurrentReviewedPhase3Scope,
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
    if (
      arm.currentSelectedRunLabel !== null
      && arm.currentSelectedRunLabel
        !== selection.selectedRunLabel
    ) {
      throw new Error(
        `Current reconciliation run and G1 selected run disagree for ${arm.armId}`,
      );
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
    const provider = providerPresentation(arm.provider);
    const membership: ChartScope[] = coreIds.has(arm.armId)
      ? ["phase3-core", "phase3-extended"]
      : ["phase3-extended"];
    return Object.freeze({
      armId: arm.armId,
      displayName: friendlyModelLabel(arm.backendModel),
      reviewedProvider: arm.provider,
      providerFamily: provider.familyKey,
      providerFamilyLabel: provider.label,
      activeScope: scope.scopeId,
      scopeMembership: Object.freeze(membership),
      selectedRunLabel: selection.selectedRunLabel,
      trialCount: arm.trialCount,
      successCount: arm.successCount,
      passRate,
      cleanSuccessCount: arm.cleanSuccessCount,
      recordedCostUsd: arm.recordedCostUsd,
      selectedCostUsd: arm.selectedCostUsd,
      selectedCostRelation: arm.selectedCostRelation,
      selectedEfficiencyRelation: arm.selectedEfficiencyRelation,
      historicalReviewedCostUsd: arm.historicalReviewedCostUsd,
      providerBilledCostUsd: arm.providerBilledCostUsd,
      reviewedComparableCostUsd: reviewedComparableCost(arm),
      adjustedKnownCostUsd: arm.adjustedKnownCostUsd,
      qualifiedRetainedRateCostUsd:
        arm.qualifiedRetainedRateCostUsd,
      costBasis: arm.selectedCostBasis,
      costBasisLabel: costBasisLabelForArm(arm),
      costSources: Object.freeze(
        arm.selectedCostBasis === "provider_billed"
          ? ["sanitized_provider_billing_reconciliation"]
          : [...arm.costSources],
      ),
      costConfidence: arm.selectedCostConfidence,
      pricingProvenanceStatus: arm.pricingProvenanceStatus,
      armRunAllocationConfidence:
        arm.armRunAllocationConfidence,
      trialAllocationStatus:
        arm.selectedTrialCostAllocationStatus,
      billingReconciliationStatus:
        arm.providerBillingReconciliationStatus,
      currentSelectedRunLabel: arm.currentSelectedRunLabel,
      providerLogExclusivityStatus:
        selection.providerLogAllocationQualification?.providerLogExclusivityStatus ?? null,
      accountingGapUsd: arm.accountingGapUsd,
      missingRecordedCostCount: arm.missingRecordedCostCount,
      unresolvedCostCount: arm.unresolvedCostCount,
      adjustedCostPerAttempt,
      costPerCleanSuccess,
      recordedCostPerAttempt,
      failureIncompleteSpend: failureIncompleteSpendForArm(arm),
      selectedRunHref: buildExactRunHref(selection.selectedRunLabel, scope.scopeId),
      costProvenanceHref: buildCostCoverageHref(
        scope.scopeId,
        { armId: arm.armId, runLabel: selection.selectedRunLabel },
        scope.scopeId,
      ),
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
  const coreArmIds = PHASE3_CURRENT_REVIEWED_COMPARISON.scopes["phase3-core"].arms.map(
    (arm) => arm.armId,
  );
  return buildCostPerformanceChartArms(
    getCurrentReviewedPhase3Scope(scopeId),
    getReviewedRunSelectionScope(scopeId),
    coreArmIds,
  );
}

export function selectCostPerformanceChartScope(
  value: string | readonly string[] | null | undefined,
): CurrentReviewedScopeSelection {
  return selectCurrentReviewedPhase3Scope(value);
}
