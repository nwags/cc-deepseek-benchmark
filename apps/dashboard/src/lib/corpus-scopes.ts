import {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
} from "./phase3-current-reviewed-comparison";
import { PHASE3_REVIEWED_COMPARISON } from "./phase3-reviewed-comparison";
import { formatTruncatedCurrency } from "./format";

export type CorpusScopeId =
  | "phase3-core"
  | "phase3-extended"
  | "valid-imported"
  | "all-imported";

export type CorpusScopeCounts = Readonly<{
  armCount: number;
  trialCount: number;
  successCount: number;
}>;

export type ObservedCorpusScopeCounts = Partial<{
  armCount: number | null;
  trialCount: number | null;
  successCount: number | null;
}>;

export type CorpusCostCoverageState =
  | "reviewed_adjusted_snapshot"
  | "reviewed_qualified_retained_rate_estimate"
  | "recorded_valid_imports"
  | "mixed_imported_evidence";

export type CorpusScopePresentationKind =
  | "historical_reviewed_snapshot"
  | "current_reviewed_corpus"
  | "dynamic_inventory";

export type CorpusScope = Readonly<{
  id: CorpusScopeId;
  displayLabel: string;
  shortDescription: string;
  includedPopulation: string;
  excludedPopulation: string;
  populationKind: "fixed_corpus" | "dynamic";
  presentationKind: CorpusScopePresentationKind;
  expectedCounts: CorpusScopeCounts | null;

  // Current decision-facing selected-cost metadata. These fields are
  // populated only for fixed reviewed Phase 3 scopes.
  selectedCostUsd: number | null;
  historicalReviewedCostUsd: number | null;
  selectedCostBasis: "mixed_best_available_arm_evidence" | null;
  currentReconciledArmCount: number | null;
  currentReconciledCostUsd: number | null;
  currentCostReviewedAt: string | null;
  selectedCostDescription: string | null;

  // Preserved historical reviewed cost metadata. These compatibility
  // fields retain the original reviewed scope semantics.
  adjustedKnownCostUsd: number | null;
  qualifiedAdjustedCostEstimateUsd: number | null;
  costDisplayLabel: string | null;

  comparisonValid: boolean;
  costCoverageState: CorpusCostCoverageState;
  costCoverageDescription: string;
  provenanceLabel: string;
  snapshotDate: string | null;
  kimiK3Disposition: "included" | "excluded" | "population_dependent";
}>;

export type CorpusScopeCountComparison = Readonly<{
  status: "match" | "mismatch" | "not_applicable";
  reason: "dynamic_scope" | "no_observed_counts" | "compared";
  expected: CorpusScopeCounts | null;
  observed: ObservedCorpusScopeCounts;
  comparedFields: readonly (keyof CorpusScopeCounts)[];
  mismatchedFields: readonly (keyof CorpusScopeCounts)[];
}>;

const PRESENTATION_LABELS: Readonly<Record<CorpusScopePresentationKind, string>> = Object.freeze({
  historical_reviewed_snapshot: "Historical reviewed snapshot",
  current_reviewed_corpus: "Current reviewed fixed full-suite corpus",
  dynamic_inventory: "Live/dynamic inventory",
});

function freezeScope(scope: CorpusScope): CorpusScope {
  return Object.freeze({
    ...scope,
    expectedCounts: scope.expectedCounts ? Object.freeze({ ...scope.expectedCounts }) : null,
  });
}

const REVIEWED_CORE = PHASE3_REVIEWED_COMPARISON.scopes["phase3-core"];
const REVIEWED_EXTENDED = PHASE3_REVIEWED_COMPARISON.scopes["phase3-extended"];

const CURRENT_REVIEWED_CORE =
  PHASE3_CURRENT_REVIEWED_COMPARISON.scopes["phase3-core"];
const CURRENT_REVIEWED_EXTENDED =
  PHASE3_CURRENT_REVIEWED_COMPARISON.scopes["phase3-extended"];

function reviewedCounts(scope: typeof REVIEWED_CORE | typeof REVIEWED_EXTENDED): CorpusScopeCounts {
  return {
    armCount: scope.armCount,
    trialCount: scope.trialCount,
    successCount: scope.successCount,
  };
}

function reviewedDecimal(value: string | null, label: string): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`${label} is not a finite reviewed decimal`);
  return parsed;
}

function reviewedKimiDisposition(
  scope: typeof REVIEWED_CORE | typeof REVIEWED_EXTENDED,
): "included" | "excluded" {
  return scope.arms.some((arm) => arm.armId === "router-kimi-k3") ? "included" : "excluded";
}

export const CORPUS_SCOPES: Readonly<Record<CorpusScopeId, CorpusScope>> = Object.freeze({
  "phase3-core": freezeScope({
    id: "phase3-core",
    displayLabel: "Phase 3 core",
    shortDescription: "Reviewed historical Phase 3 full-suite snapshot used by the original report and July 13 adjusted-cost comparison.",
    includedPopulation: `The original ${REVIEWED_CORE.armCount} valid full-suite Phase 3 arms: 20 evals with three attempts per arm.`,
    excludedPopulation: "The later router-kimi-k3 addendum and all canary, smoke, diagnostic, legacy, invalid, or quarantined runs.",
    populationKind: "fixed_corpus",
    presentationKind: REVIEWED_CORE.presentationKind,
    expectedCounts: reviewedCounts(REVIEWED_CORE),

    selectedCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_CORE.selectedCostEvidence.selectedCostUsd,
      "phase3-core current selected cost",
    ),
    historicalReviewedCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_CORE.selectedCostEvidence
        .historicalReviewedArmSumCostUsd,
      "phase3-core historical reviewed arm-sum cost",
    ),
    selectedCostBasis:
      CURRENT_REVIEWED_CORE.selectedCostEvidence.selectedCostBasis,
    currentReconciledArmCount:
      CURRENT_REVIEWED_CORE.selectedCostEvidence
        .currentReconciledArmCount,
    currentReconciledCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_CORE.selectedCostEvidence
        .currentReconciledCostUsd,
      "phase3-core provider-reconciled selected cost",
    ),
    currentCostReviewedAt:
      PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
    selectedCostDescription:
      `Current selected arm-sum cost is ${formatTruncatedCurrency(
        CURRENT_REVIEWED_CORE.selectedCostEvidence.selectedCostUsd,
      )} using mixed best-available arm evidence. `
      + `${CURRENT_REVIEWED_CORE.selectedCostEvidence.currentReconciledArmCount}/${REVIEWED_CORE.armCount} arms have current generalized reconciliation; ${CURRENT_REVIEWED_CORE.selectedCostEvidence.exactProviderBilledArmCount}/${REVIEWED_CORE.armCount} arms have exact provider-billed totals. Provider aggregates are not redistributed to trials or outcomes.`,

    adjustedKnownCostUsd: reviewedDecimal(
      REVIEWED_CORE.costEvidence.adjustedKnownCostUsd,
      "phase3-core adjusted known cost",
    ),
    qualifiedAdjustedCostEstimateUsd: null,
    costDisplayLabel: "Adjusted known cost",
    comparisonValid: true,
    costCoverageState: "reviewed_adjusted_snapshot",
    costCoverageDescription: `Reviewed adjusted-cost coverage totals $${Number(REVIEWED_CORE.costEvidence.adjustedKnownCostUsd).toFixed(2)} for the ${REVIEWED_CORE.armCount}-arm core snapshot. It does not include Kimi K3.`,
    provenanceLabel: "Original Phase 3 report and July 13, 2026 reviewed adjusted-cost reporting layer",
    snapshotDate: REVIEWED_CORE.snapshotDate,
    kimiK3Disposition: reviewedKimiDisposition(REVIEWED_CORE),
  }),
  "phase3-extended": freezeScope({
    id: "phase3-extended",
    displayLabel: "Phase 3 extended",
    shortDescription: "Current preferred full-suite quality-comparison scope: Phase 3 core plus the Kimi K3 addendum.",
    includedPopulation: `The ${REVIEWED_CORE.armCount}-arm Phase 3 core plus canonical arm router-kimi-k3, with ${REVIEWED_EXTENDED.trialCount - REVIEWED_CORE.trialCount} Kimi K3 full-suite attempts.`,
    excludedPopulation: "Canary, smoke, diagnostic, legacy, invalid, and quarantined runs.",
    populationKind: "fixed_corpus",
    presentationKind: REVIEWED_EXTENDED.presentationKind,
    expectedCounts: reviewedCounts(REVIEWED_EXTENDED),

    selectedCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_EXTENDED.selectedCostEvidence.selectedCostUsd,
      "phase3-extended current selected cost",
    ),
    historicalReviewedCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_EXTENDED.selectedCostEvidence
        .historicalReviewedArmSumCostUsd,
      "phase3-extended historical reviewed arm-sum cost",
    ),
    selectedCostBasis:
      CURRENT_REVIEWED_EXTENDED.selectedCostEvidence.selectedCostBasis,
    currentReconciledArmCount:
      CURRENT_REVIEWED_EXTENDED.selectedCostEvidence
        .currentReconciledArmCount,
    currentReconciledCostUsd: reviewedDecimal(
      CURRENT_REVIEWED_EXTENDED.selectedCostEvidence
        .currentReconciledCostUsd,
      "phase3-extended provider-reconciled selected cost",
    ),
    currentCostReviewedAt:
      PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
    selectedCostDescription:
      `Current selected arm-sum cost is ${formatTruncatedCurrency(
        CURRENT_REVIEWED_EXTENDED.selectedCostEvidence.selectedCostUsd,
      )} using mixed best-available arm evidence. `
      + `${CURRENT_REVIEWED_EXTENDED.selectedCostEvidence.currentReconciledArmCount}/${REVIEWED_EXTENDED.armCount} arms have current generalized reconciliation; ${CURRENT_REVIEWED_EXTENDED.selectedCostEvidence.exactProviderBilledArmCount}/${REVIEWED_EXTENDED.armCount} arms have exact provider-billed totals. Provider aggregates are not redistributed to trials or outcomes.`,

    adjustedKnownCostUsd: null,
    qualifiedAdjustedCostEstimateUsd: reviewedDecimal(
      REVIEWED_EXTENDED.costEvidence.qualifiedAdjustedCostEstimateUsd,
      "phase3-extended qualified adjusted-cost estimate",
    ),
    costDisplayLabel: "Phase 3 extended qualified adjusted-cost estimate",
    comparisonValid: true,
    costCoverageState: "reviewed_qualified_retained_rate_estimate",
    costCoverageDescription: `The qualified extended estimate is ${REVIEWED_EXTENDED.costEvidence.qualifiedAdjustedCostEstimateUsd === null
      ? "Unavailable"
      : formatTruncatedCurrency(
          REVIEWED_EXTENDED.costEvidence.qualifiedAdjustedCostEstimateUsd,
        )}. Kimi K3 pricing-source provenance is incomplete, arm-run allocation confidence is low, trial allocation is unresolved, and the estimate is not invoice-level or provider-billed spend.`,
    provenanceLabel: "Phase 3 core plus the reviewed Kimi K3 retained-rate reconciliation",
    snapshotDate: REVIEWED_EXTENDED.snapshotDate,
    kimiK3Disposition: reviewedKimiDisposition(REVIEWED_EXTENDED),
  }),
  "valid-imported": freezeScope({
    id: "valid-imported",
    displayLabel: "Valid imported evidence inventory",
    shortDescription: "Live aggregate of imported rows belonging to runs that remain valid.",
    includedPopulation: "Valid imported canary, smoke, full-suite, and other valid run classes represented by the dashboard inventory query.",
    excludedPopulation: "Invalid and quarantined runs; this scope does not promise a fixed full-suite denominator.",
    populationKind: "dynamic",
    presentationKind: "dynamic_inventory",
    expectedCounts: null,
    selectedCostUsd: null,
    historicalReviewedCostUsd: null,
    selectedCostBasis: null,
    currentReconciledArmCount: null,
    currentReconciledCostUsd: null,
    currentCostReviewedAt: null,
    selectedCostDescription: null,
    adjustedKnownCostUsd: null,
    qualifiedAdjustedCostEstimateUsd: null,
    costDisplayLabel: null,
    comparisonValid: false,
    costCoverageState: "recorded_valid_imports",
    costCoverageDescription: "Only recorded cost returned by the live valid-run aggregate is shown; coverage varies with imported run classes.",
    provenanceLabel: "Live Supabase valid-run aggregate",
    snapshotDate: null,
    kimiK3Disposition: "population_dependent",
  }),
  "all-imported": freezeScope({
    id: "all-imported",
    displayLabel: "All imported",
    shortDescription: "Dynamic aggregate across imported rows represented by the page's aggregate view.",
    includedPopulation: "Full-suite, canary, smoke, legacy, diagnostic, and other imported rows represented by the aggregate.",
    excludedPopulation: "No run class is implicitly promoted to a fixed full-suite denominator; page-specific views may still enforce validity rules.",
    populationKind: "dynamic",
    presentationKind: "dynamic_inventory",
    expectedCounts: null,
    selectedCostUsd: null,
    historicalReviewedCostUsd: null,
    selectedCostBasis: null,
    currentReconciledArmCount: null,
    currentReconciledCostUsd: null,
    currentCostReviewedAt: null,
    selectedCostDescription: null,
    adjustedKnownCostUsd: null,
    qualifiedAdjustedCostEstimateUsd: null,
    costDisplayLabel: null,
    comparisonValid: false,
    costCoverageState: "mixed_imported_evidence",
    costCoverageDescription: "Recorded cost and coverage can mix run classes and may differ from reviewed Phase 3 core or extended comparisons.",
    provenanceLabel: "Live dashboard aggregate views over imported benchmark rows",
    snapshotDate: null,
    kimiK3Disposition: "population_dependent",
  }),
});

export function getCorpusScope(id: CorpusScopeId): CorpusScope;
export function getCorpusScope(id: string | null | undefined): CorpusScope | null;
export function getCorpusScope(id: string | null | undefined): CorpusScope | null {
  if (!id || !Object.prototype.hasOwnProperty.call(CORPUS_SCOPES, id)) return null;
  return CORPUS_SCOPES[id as CorpusScopeId];
}

export function getCorpusScopePresentationLabel(scope: CorpusScope): string {
  return PRESENTATION_LABELS[scope.presentationKind];
}

export function compareCorpusScopeCounts(
  scope: CorpusScope,
  observed: ObservedCorpusScopeCounts,
): CorpusScopeCountComparison {
  if (!scope.expectedCounts) {
    return Object.freeze({
      status: "not_applicable",
      reason: "dynamic_scope",
      expected: null,
      observed: Object.freeze({ ...observed }),
      comparedFields: Object.freeze([]),
      mismatchedFields: Object.freeze([]),
    });
  }

  const fields: (keyof CorpusScopeCounts)[] = ["armCount", "trialCount", "successCount"];
  const comparedFields = fields.filter((field) => {
    const value = observed[field];
    return typeof value === "number" && Number.isFinite(value);
  });
  if (!comparedFields.length) {
    return Object.freeze({
      status: "not_applicable",
      reason: "no_observed_counts",
      expected: scope.expectedCounts,
      observed: Object.freeze({ ...observed }),
      comparedFields: Object.freeze([]),
      mismatchedFields: Object.freeze([]),
    });
  }

  const mismatchedFields = comparedFields.filter((field) => observed[field] !== scope.expectedCounts?.[field]);
  return Object.freeze({
    status: mismatchedFields.length ? "mismatch" : "match",
    reason: "compared",
    expected: scope.expectedCounts,
    observed: Object.freeze({ ...observed }),
    comparedFields: Object.freeze(comparedFields),
    mismatchedFields: Object.freeze(mismatchedFields),
  });
}
