import type {
  ReviewedSelectedArmRunDbRow,
  ReviewedSelectedRunAdjustedCostDbRow,
} from "./dashboard-data";
import type {
  ReviewedPhase3Arm,
  ReviewedPhase3Scope,
} from "./phase3-reviewed-comparison";
import type {
  ReviewedRunSelectionScope,
  ReviewedSelectedRun,
} from "./phase3-reviewed-run-selection";
import {
  buildCostCoverageHref,
  buildExactRunHref,
  buildReviewedAggregateArmEvidenceHref,
} from "./evidence-links";

export const OVERVIEW_COST_RECONCILIATION_TOLERANCE_USD = "0.000000001";

export type DatabaseReadStatus = "available" | "unavailable";

export type OverviewReconciliationIssue =
  | "database_run_unavailable"
  | "missing_database_run"
  | "duplicate_database_run"
  | "arm_mismatch"
  | "suite_mismatch"
  | "count_mismatch"
  | "database_cost_unavailable"
  | "missing_database_cost"
  | "duplicate_database_cost"
  | "cost_mismatch"
  | "partial_cost_evidence"
  | "qualified_kimi_cost";

export type DatabaseRunEvidenceStatus =
  | "match"
  | "unavailable"
  | "missing"
  | "duplicate"
  | "arm_mismatch"
  | "suite_mismatch"
  | "count_mismatch";

export type DatabaseCostEvidenceStatus =
  | "match"
  | "unavailable"
  | "missing"
  | "duplicate"
  | "mismatch"
  | "partial"
  | "qualified_not_authoritative";

export type OverviewReviewedComparisonRow = Readonly<{
  rank: number;
  armId: string;
  reviewedTrialCount: number;
  reviewedSuccessCount: number;
  reviewedPassRate: number;
  selectedRunLabel: string;
  selectedRunHref: string;
  armEvidenceHref: string;
  costProvenanceHref: string;
  selectionKind: "reviewed_full_suite_run";
  runIdentityEvidenceStatus: "reviewed";
  databaseRunEvidenceStatus: DatabaseRunEvidenceStatus;
  databaseCostEvidenceStatus: DatabaseCostEvidenceStatus;
  databaseRunEvidence: ReviewedSelectedArmRunDbRow | null;
  databaseAdjustedCostEvidence: ReviewedSelectedRunAdjustedCostDbRow | null;
  reviewedRecordedCostUsd: string;
  reviewedAdjustedKnownCostUsd: string | null;
  reviewedQualifiedRetainedRateCostUsd: string | null;
  reviewedAccountingGapUsd: string;
  reviewedCostBasis: ReviewedPhase3Arm["costBasis"];
  missingRecordedCostCount: number;
  unresolvedAdjustedCostCount: number;
  costSources: readonly string[];
  costConfidence: string;
  pricingProvenanceStatus: ReviewedPhase3Arm["pricingProvenanceStatus"];
  armRunAllocationConfidence: ReviewedPhase3Arm["armRunAllocationConfidence"];
  trialAllocationStatus: ReviewedPhase3Arm["trialAllocationStatus"];
  billingReconciliationStatus: ReviewedPhase3Arm["billingReconciliationStatus"];
  providerLogExclusivityStatus: "not_proven" | null;
  reconciliationStatus: "match" | OverviewReconciliationIssue;
  reconciliationIssues: readonly OverviewReconciliationIssue[];
  reconciliationMessages: readonly string[];
}>;

export type OverviewReviewedComparison = Readonly<{
  scopeId: "phase3-extended";
  armCount: number;
  trialCount: number;
  successCount: number;
  reviewedAt: string;
  runSelectionReviewedAt: string;
  rows: readonly OverviewReviewedComparisonRow[];
  databaseEvidenceWarnings: readonly string[];
}>;

export type BuildOverviewReviewedComparisonInput = Readonly<{
  scope: ReviewedPhase3Scope;
  runSelectionScope: ReviewedRunSelectionScope;
  comparisonReviewedAt: string;
  runSelectionReviewedAt: string;
  databaseRunReadStatus: DatabaseReadStatus;
  databaseRunRows: readonly ReviewedSelectedArmRunDbRow[];
  databaseCostReadStatus: DatabaseReadStatus;
  databaseAdjustedCostRows: readonly ReviewedSelectedRunAdjustedCostDbRow[];
}>;

type DecimalParts = Readonly<{ units: bigint; scale: number }>;

function decimalParts(value: string): DecimalParts {
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value);
  if (!match) throw new Error(`Invalid decimal evidence: ${value}`);
  const fraction = match[3] ?? "";
  return {
    units: BigInt(`${match[1]}${match[2]}${fraction}`),
    scale: fraction.length,
  };
}

function scaledUnits(value: DecimalParts, scale: number): bigint {
  return value.units * (10n ** BigInt(scale - value.scale));
}

export function decimalEvidenceWithinTolerance(
  left: string,
  right: string,
  tolerance = OVERVIEW_COST_RECONCILIATION_TOLERANCE_USD,
): boolean {
  const leftParts = decimalParts(left);
  const rightParts = decimalParts(right);
  const toleranceParts = decimalParts(tolerance);
  const scale = Math.max(leftParts.scale, rightParts.scale, toleranceParts.scale);
  const difference = scaledUnits(leftParts, scale) - scaledUnits(rightParts, scale);
  const absoluteDifference = difference < 0n ? -difference : difference;
  return absoluteDifference <= scaledUnits(toleranceParts, scale);
}

export function buildReviewedRunHref(runLabel: string): string {
  return buildExactRunHref(runLabel, "phase3-extended");
}

function rowsByRunLabel<T extends { run_label: string }>(rows: readonly T[]): Map<string, T[]> {
  const indexed = new Map<string, T[]>();
  for (const row of rows) {
    const current = indexed.get(row.run_label) ?? [];
    current.push(row);
    indexed.set(row.run_label, current);
  }
  return indexed;
}

function assertReviewedMembership(
  scope: ReviewedPhase3Scope,
  runSelectionScope: ReviewedRunSelectionScope,
): void {
  if (scope.scopeId !== "phase3-extended" || runSelectionScope.scopeId !== scope.scopeId) {
    throw new Error("Overview requires matching phase3-extended reviewed contracts");
  }
  const armIds = scope.arms.map((arm) => arm.armId).sort();
  const selectionArmIds = runSelectionScope.selections.map((selection) => selection.armId).sort();
  if (JSON.stringify(armIds) !== JSON.stringify(selectionArmIds)) {
    throw new Error("F1 reviewed arms and G1 selected-run membership disagree");
  }
  if (scope.armCount !== scope.arms.length
    || runSelectionScope.selectedRunCount !== runSelectionScope.selections.length
    || scope.armCount !== runSelectionScope.selectedRunCount
    || scope.trialCount !== runSelectionScope.trialCount) {
    throw new Error("F1 and G1 reviewed scope totals disagree");
  }
}

function addIssue(
  issues: OverviewReconciliationIssue[],
  messages: string[],
  issue: OverviewReconciliationIssue,
  message: string,
): void {
  if (!issues.includes(issue)) issues.push(issue);
  if (!messages.includes(message)) messages.push(message);
}

const ISSUE_PRECEDENCE: readonly OverviewReconciliationIssue[] = [
  "database_run_unavailable",
  "duplicate_database_run",
  "missing_database_run",
  "arm_mismatch",
  "suite_mismatch",
  "count_mismatch",
  "database_cost_unavailable",
  "duplicate_database_cost",
  "missing_database_cost",
  "cost_mismatch",
  "partial_cost_evidence",
  "qualified_kimi_cost",
];

function primaryStatus(issues: readonly OverviewReconciliationIssue[]): "match" | OverviewReconciliationIssue {
  return ISSUE_PRECEDENCE.find((issue) => issues.includes(issue)) ?? "match";
}

function runEvidenceFor(
  arm: ReviewedPhase3Arm,
  selection: ReviewedSelectedRun,
  readStatus: DatabaseReadStatus,
  matches: readonly ReviewedSelectedArmRunDbRow[],
  issues: OverviewReconciliationIssue[],
  messages: string[],
): { status: DatabaseRunEvidenceStatus; row: ReviewedSelectedArmRunDbRow | null } {
  if (readStatus === "unavailable") {
    addIssue(
      issues,
      messages,
      "database_run_unavailable",
      "Current stored run evidence could not be read; the frozen reviewed run identity is still shown.",
    );
    return { status: "unavailable", row: null };
  }
  if (matches.length === 0) {
    addIssue(
      issues,
      messages,
      "missing_database_run",
      "No current valid arm-run row exists for this exact reviewed run label; no newer run was substituted.",
    );
    return { status: "missing", row: null };
  }
  if (matches.length !== 1) {
    addIssue(
      issues,
      messages,
      "duplicate_database_run",
      "More than one current arm-run row resolved to this exact reviewed run label.",
    );
    return { status: "duplicate", row: null };
  }

  const row = matches[0];
  if (row.arm_id !== arm.armId) {
    addIssue(issues, messages, "arm_mismatch", "The stored run arm does not match the reviewed arm identity.");
    return { status: "arm_mismatch", row };
  }
  if (row.suite_id !== "phase3-full-20") {
    addIssue(issues, messages, "suite_mismatch", "The stored run is not assigned to the reviewed full-suite ID.");
    return { status: "suite_mismatch", row };
  }
  if (row.trial_count !== arm.trialCount
    || row.success_count !== arm.successCount
    || row.task_count !== selection.taskCount) {
    addIssue(issues, messages, "count_mismatch", "Stored run task, trial, or success counts differ from the reviewed facts.");
    return { status: "count_mismatch", row };
  }
  if (row.trial_cost_usd === null || row.cost_row_count === 0) {
    addIssue(issues, messages, "partial_cost_evidence", "The stored run summary does not contain recorded-cost evidence.");
  } else if (!decimalEvidenceWithinTolerance(row.trial_cost_usd, arm.recordedCostUsd)) {
    addIssue(issues, messages, "cost_mismatch", "Stored run recorded cost differs from the reviewed recorded cost.");
  }
  if (row.missing_cost_count !== arm.missingRecordedCostCount) {
    addIssue(issues, messages, "partial_cost_evidence", "Stored run missing-cost coverage differs from the reviewed layer.");
  }
  return { status: "match", row };
}

function costEvidenceFor(
  arm: ReviewedPhase3Arm,
  readStatus: DatabaseReadStatus,
  matches: readonly ReviewedSelectedRunAdjustedCostDbRow[],
  issues: OverviewReconciliationIssue[],
  messages: string[],
): { status: DatabaseCostEvidenceStatus; row: ReviewedSelectedRunAdjustedCostDbRow | null } {
  if (readStatus === "unavailable") {
    addIssue(
      issues,
      messages,
      "database_cost_unavailable",
      "Current selected-run adjusted-cost evidence could not be read; reviewed costs remain unchanged.",
    );
    return { status: "unavailable", row: null };
  }
  if (matches.length === 0) {
    addIssue(issues, messages, "missing_database_cost", "No adjusted-cost rows exist for this exact reviewed run label.");
    return { status: "missing", row: null };
  }
  if (matches.length !== 1) {
    addIssue(issues, messages, "duplicate_database_cost", "Adjusted-cost evidence resolved to multiple arm/suite groups.");
    return { status: "duplicate", row: null };
  }

  const row = matches[0];
  if (row.arm_id !== arm.armId) {
    addIssue(issues, messages, "arm_mismatch", "Adjusted-cost evidence belongs to a different arm.");
    return { status: "mismatch", row };
  }
  if (row.suite_id !== "phase3-full-20") {
    addIssue(issues, messages, "suite_mismatch", "Adjusted-cost evidence belongs to a different suite.");
    return { status: "mismatch", row };
  }
  if (row.trial_count !== arm.trialCount) {
    addIssue(issues, messages, "partial_cost_evidence", "Adjusted-cost evidence does not cover all reviewed trials.");
    return { status: "partial", row };
  }

  const recordedMatches = row.recorded_cost_usd !== null
    && decimalEvidenceWithinTolerance(row.recorded_cost_usd, arm.recordedCostUsd);
  if (!recordedMatches) {
    addIssue(issues, messages, "cost_mismatch", "Selected-run recorded cost differs from the reviewed recorded cost.");
  }

  if (arm.armId === "router-kimi-k3") {
    if (row.missing_recorded_cost_count !== arm.missingRecordedCostCount
      || row.unresolved_adjusted_cost_count !== arm.unresolvedCostCount) {
      addIssue(issues, messages, "partial_cost_evidence", "Stored Kimi cost coverage differs from the reviewed coverage counts.");
    }
    addIssue(
      issues,
      messages,
      "qualified_kimi_cost",
      "Database adjusted-cost rows do not upgrade Kimi K3's qualified retained-rate estimate to adjusted-known cost.",
    );
    return { status: "qualified_not_authoritative", row };
  }

  const adjustedMatches = arm.adjustedKnownCostUsd !== null
    && row.adjusted_known_cost_usd !== null
    && decimalEvidenceWithinTolerance(row.adjusted_known_cost_usd, arm.adjustedKnownCostUsd);
  const gapMatches = row.accounting_gap_usd !== null
    && decimalEvidenceWithinTolerance(row.accounting_gap_usd, arm.accountingGapUsd);
  const coverageMatches = row.missing_recorded_cost_count === arm.missingRecordedCostCount
    && row.unresolved_adjusted_cost_count === arm.unresolvedCostCount;

  if (!adjustedMatches || !gapMatches) {
    addIssue(issues, messages, "cost_mismatch", "Selected-run adjusted cost or accounting gap differs from the reviewed layer.");
  }
  if (!coverageMatches) {
    addIssue(issues, messages, "partial_cost_evidence", "Selected-run missing or unresolved cost counts differ from the reviewed layer.");
  }
  if (!recordedMatches || !adjustedMatches || !gapMatches) return { status: "mismatch", row };
  if (!coverageMatches) return { status: "partial", row };
  return { status: "match", row };
}

export function buildOverviewReviewedComparison(
  input: BuildOverviewReviewedComparisonInput,
): OverviewReviewedComparison {
  assertReviewedMembership(input.scope, input.runSelectionScope);

  const selectionsByArm = new Map(
    input.runSelectionScope.selections.map((selection) => [selection.armId, selection]),
  );
  const databaseRunsByLabel = rowsByRunLabel(input.databaseRunRows);
  const databaseCostsByLabel = rowsByRunLabel(input.databaseAdjustedCostRows);
  const selectedLabels = new Set(
    input.runSelectionScope.selections.map((selection) => selection.selectedRunLabel),
  );
  const databaseEvidenceWarnings: string[] = [];
  if (input.databaseRunRows.some((row) => !selectedLabels.has(row.run_label))) {
    databaseEvidenceWarnings.push("The exact-run query returned an unexpected run label; it was not used as a substitute.");
  }
  if (input.databaseAdjustedCostRows.some((row) => !selectedLabels.has(row.run_label))) {
    databaseEvidenceWarnings.push("The exact-run cost query returned an unexpected run label; it was not used.");
  }

  const unsortedRows = input.scope.arms.map((arm) => {
    const selection = selectionsByArm.get(arm.armId);
    if (!selection) throw new Error(`No reviewed selected run exists for ${arm.armId}`);
    const issues: OverviewReconciliationIssue[] = [];
    const messages: string[] = [];
    const databaseRun = runEvidenceFor(
      arm,
      selection,
      input.databaseRunReadStatus,
      databaseRunsByLabel.get(selection.selectedRunLabel) ?? [],
      issues,
      messages,
    );
    const databaseCost = costEvidenceFor(
      arm,
      input.databaseCostReadStatus,
      databaseCostsByLabel.get(selection.selectedRunLabel) ?? [],
      issues,
      messages,
    );
    if (arm.armId === "router-kimi-k3" && !issues.includes("qualified_kimi_cost")) {
      addIssue(
        issues,
        messages,
        "qualified_kimi_cost",
        "Kimi K3 retains qualified retained-rate evidence with low allocation confidence and unresolved trial allocation.",
      );
    }

    return {
      rank: 0,
      armId: arm.armId,
      reviewedTrialCount: arm.trialCount,
      reviewedSuccessCount: arm.successCount,
      reviewedPassRate: arm.passRate,
      selectedRunLabel: selection.selectedRunLabel,
      selectedRunHref: buildReviewedRunHref(selection.selectedRunLabel),
      armEvidenceHref: buildReviewedAggregateArmEvidenceHref(arm.armId, "phase3-extended"),
      costProvenanceHref: buildCostCoverageHref(
        "phase3-extended",
        { armId: arm.armId, runLabel: selection.selectedRunLabel },
        "phase3-extended",
      ),
      selectionKind: selection.selectionKind,
      runIdentityEvidenceStatus: selection.runIdentityEvidenceStatus,
      databaseRunEvidenceStatus: databaseRun.status,
      databaseCostEvidenceStatus: databaseCost.status,
      databaseRunEvidence: databaseRun.row,
      databaseAdjustedCostEvidence: databaseCost.row,
      reviewedRecordedCostUsd: arm.recordedCostUsd,
      reviewedAdjustedKnownCostUsd: arm.adjustedKnownCostUsd,
      reviewedQualifiedRetainedRateCostUsd: arm.qualifiedRetainedRateCostUsd,
      reviewedAccountingGapUsd: arm.accountingGapUsd,
      reviewedCostBasis: arm.costBasis,
      missingRecordedCostCount: arm.missingRecordedCostCount,
      unresolvedAdjustedCostCount: arm.unresolvedCostCount,
      costSources: arm.costSources,
      costConfidence: arm.costConfidence,
      pricingProvenanceStatus: arm.pricingProvenanceStatus,
      armRunAllocationConfidence: arm.armRunAllocationConfidence,
      trialAllocationStatus: arm.trialAllocationStatus,
      billingReconciliationStatus: arm.billingReconciliationStatus,
      providerLogExclusivityStatus:
        selection.providerLogAllocationQualification?.providerLogExclusivityStatus ?? null,
      reconciliationStatus: primaryStatus(issues),
      reconciliationIssues: issues,
      reconciliationMessages: messages,
    } satisfies OverviewReviewedComparisonRow;
  });

  const rows = unsortedRows
    .sort((left, right) => right.reviewedPassRate - left.reviewedPassRate
      || left.armId.localeCompare(right.armId))
    .map((row, index) => ({ ...row, rank: index + 1 }));

  return {
    scopeId: "phase3-extended",
    armCount: input.scope.armCount,
    trialCount: input.scope.trialCount,
    successCount: input.scope.successCount,
    reviewedAt: input.comparisonReviewedAt,
    runSelectionReviewedAt: input.runSelectionReviewedAt,
    rows,
    databaseEvidenceWarnings,
  };
}
