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
  | "partial_observed_unreconciled"
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
  adjustedKnownCostUsd: number | null;
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

export const CORPUS_SCOPES: Readonly<Record<CorpusScopeId, CorpusScope>> = Object.freeze({
  "phase3-core": freezeScope({
    id: "phase3-core",
    displayLabel: "Phase 3 core",
    shortDescription: "Reviewed historical Phase 3 full-suite snapshot used by the original report and July 13 adjusted-cost comparison.",
    includedPopulation: "The original 15 valid full-suite Phase 3 arms: 20 evals with three attempts per arm.",
    excludedPopulation: "The later router-kimi-k3 addendum and all canary, smoke, diagnostic, legacy, invalid, or quarantined runs.",
    populationKind: "fixed_corpus",
    presentationKind: "historical_reviewed_snapshot",
    expectedCounts: { armCount: 15, trialCount: 900, successCount: 515 },
    adjustedKnownCostUsd: 972.17,
    comparisonValid: true,
    costCoverageState: "reviewed_adjusted_snapshot",
    costCoverageDescription: "Reviewed adjusted-cost coverage totals $972.17 for the 15-arm core snapshot. It does not include Kimi K3.",
    provenanceLabel: "Original Phase 3 report and July 13, 2026 reviewed adjusted-cost reporting layer",
    snapshotDate: "2026-07-13",
    kimiK3Disposition: "excluded",
  }),
  "phase3-extended": freezeScope({
    id: "phase3-extended",
    displayLabel: "Phase 3 extended",
    shortDescription: "Current preferred full-suite quality-comparison scope: Phase 3 core plus the Kimi K3 addendum.",
    includedPopulation: "The 15-arm Phase 3 core plus canonical arm router-kimi-k3, each with 60 full-suite attempts.",
    excludedPopulation: "Canary, smoke, diagnostic, legacy, invalid, and quarantined runs.",
    populationKind: "fixed_corpus",
    presentationKind: "current_reviewed_corpus",
    expectedCounts: { armCount: 16, trialCount: 960, successCount: 562 },
    adjustedKnownCostUsd: null,
    comparisonValid: true,
    costCoverageState: "partial_observed_unreconciled",
    costCoverageDescription: "Quality evidence is comparable across 16 arms, but Kimi K3 has only partial observed cost evidence and unresolved official-price reconciliation. No extended adjusted-cost total is asserted.",
    provenanceLabel: "Phase 3 core with the reviewed Kimi K3 addendum",
    snapshotDate: "2026-07-31",
    kimiK3Disposition: "included",
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
    adjustedKnownCostUsd: null,
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
    adjustedKnownCostUsd: null,
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
