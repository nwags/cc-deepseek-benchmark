import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

async function transpiledDataUrl(source) {
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  return `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
}

const formatSource = await readFile(
  join(here, "format.ts"),
  "utf8",
);
const formatModuleUrl = await transpiledDataUrl(formatSource);

const historicalGeneratedSource = await readFile(
  resolve(here, "../generated/phase3-reviewed-comparison-data.ts"),
  "utf8",
);
const historicalGeneratedModuleUrl =
  await transpiledDataUrl(historicalGeneratedSource);

const historicalLoaderSource = (
  await readFile(join(here, "phase3-reviewed-comparison.ts"), "utf8")
).replace(
  '"../generated/phase3-reviewed-comparison-data"',
  `"${historicalGeneratedModuleUrl}"`,
);
const reviewedModuleUrl =
  await transpiledDataUrl(historicalLoaderSource);
const { PHASE3_REVIEWED_COMPARISON } =
  await import(reviewedModuleUrl);

const currentGeneratedSource = await readFile(
  resolve(
    here,
    "../generated/phase3-current-reviewed-comparison-data-v4.ts",
  ),
  "utf8",
);
const currentGeneratedModuleUrl =
  await transpiledDataUrl(currentGeneratedSource);

const currentLoaderSource = (
  await readFile(
    join(here, "phase3-current-reviewed-comparison.ts"),
    "utf8",
  )
)
  .replace(
    '"../generated/phase3-current-reviewed-comparison-data-v4"',
    `"${currentGeneratedModuleUrl}"`,
  )
  .replace(
    '"./phase3-reviewed-comparison"',
    `"${reviewedModuleUrl}"`,
  );
const currentModuleUrl =
  await transpiledDataUrl(currentLoaderSource);
const { PHASE3_CURRENT_REVIEWED_COMPARISON } =
  await import(currentModuleUrl);

const source = (
  await readFile(join(here, "corpus-scopes.ts"), "utf8")
)
  .replace(
    'from "./phase3-current-reviewed-comparison"',
    `from "${currentModuleUrl}"`,
  )
  .replace(
    'from "./phase3-reviewed-comparison"',
    `from "${reviewedModuleUrl}"`,
  )
  .replace(
    'from "./format"',
    `from "${formatModuleUrl}"`,
  );
const moduleUrl = await transpiledDataUrl(source);
const {
  CORPUS_SCOPES,
  compareCorpusScopeCounts,
  getCorpusScope,
  getCorpusScopePresentationLabel,
} = await import(moduleUrl);

test("registry defines all four immutable corpus scopes", () => {
  assert.deepEqual(Object.keys(CORPUS_SCOPES).sort(), [
    "all-imported", "phase3-core", "phase3-extended", "valid-imported",
  ]);
  assert.equal(Object.isFrozen(CORPUS_SCOPES), true);
  for (const scope of Object.values(CORPUS_SCOPES)) assert.equal(Object.isFrozen(scope), true);
});

test("presentation classification distinguishes historical, current reviewed, and dynamic scopes", () => {
  const core = getCorpusScope("phase3-core");
  const extended = getCorpusScope("phase3-extended");
  const validImported = getCorpusScope("valid-imported");
  const allImported = getCorpusScope("all-imported");

  assert.equal(core.presentationKind, "historical_reviewed_snapshot");
  assert.equal(getCorpusScopePresentationLabel(core), "Historical reviewed snapshot");
  assert.equal(extended.presentationKind, "current_reviewed_corpus");
  assert.equal(getCorpusScopePresentationLabel(extended), "Current reviewed fixed full-suite corpus");
  assert.equal(validImported.presentationKind, "dynamic_inventory");
  assert.equal(getCorpusScopePresentationLabel(validImported), "Live/dynamic inventory");
  assert.equal(allImported.presentationKind, "dynamic_inventory");
  assert.equal(getCorpusScopePresentationLabel(allImported), "Live/dynamic inventory");
});

test("fixed core and extended scopes retain reviewed counts and Kimi K3 boundaries", () => {
  const core = getCorpusScope("phase3-core");
  const extended = getCorpusScope("phase3-extended");
  assert.deepEqual(core.expectedCounts, { armCount: 15, trialCount: 900, successCount: 515 });
  assert.equal(Object.isFrozen(core.expectedCounts), true);
  assert.equal(core.selectedCostUsd, 316.8790274572);
  assert.equal(core.historicalReviewedCostUsd, 972.169845489198);
  assert.equal(
    core.selectedCostBasis,
    "mixed_best_available_arm_evidence",
  );
  assert.equal(core.currentReconciledArmCount, 15);
  assert.equal(core.currentReconciledCostUsd, 316.8790274572);
  assert.equal(core.currentCostReviewedAt, "2026-08-25");
  assert.match(
    core.selectedCostDescription,
    /current generalized reconciliation/,
  );

  assert.equal(core.adjustedKnownCostUsd, 972.169845489198);
  assert.equal(core.qualifiedAdjustedCostEstimateUsd, null);
  assert.equal(core.costDisplayLabel, "Adjusted known cost");
  assert.equal(core.comparisonValid, true);
  assert.equal(core.costCoverageState, "reviewed_adjusted_snapshot");
  assert.equal(core.kimiK3Disposition, "excluded");
  assert.match(core.excludedPopulation, /router-kimi-k3/);
  assert.deepEqual(extended.expectedCounts, { armCount: 16, trialCount: 960, successCount: 562 });
  assert.equal(Object.isFrozen(extended.expectedCounts), true);
  assert.equal(extended.comparisonValid, true);
  assert.equal(extended.selectedCostUsd, 343.4494304572);
  assert.equal(
    extended.historicalReviewedCostUsd,
    1002.984164889198,
  );
  assert.equal(
    extended.selectedCostBasis,
    "mixed_best_available_arm_evidence",
  );
  assert.equal(extended.currentReconciledArmCount, 16);
  assert.equal(extended.currentReconciledCostUsd, 343.4494304572);
  assert.equal(extended.currentCostReviewedAt, "2026-08-25");
  assert.match(
    extended.selectedCostDescription,
    /Provider aggregates are not redistributed/,
  );

  assert.equal(extended.adjustedKnownCostUsd, null);
  assert.equal(extended.qualifiedAdjustedCostEstimateUsd, 1002.9841648891979);
  assert.equal(extended.costDisplayLabel, "Phase 3 extended qualified adjusted-cost estimate");
  assert.equal(extended.costCoverageState, "reviewed_qualified_retained_rate_estimate");
  assert.match(extended.costCoverageDescription, /not invoice-level or provider-billed/);
  assert.equal(extended.kimiK3Disposition, "included");
  assert.match(extended.includedPopulation, /router-kimi-k3/);
});

test("fixed registry facts must agree with the validated reviewed comparison", () => {
  for (const id of ["phase3-core", "phase3-extended"]) {
    const registry = getCorpusScope(id);
    const reviewed = PHASE3_REVIEWED_COMPARISON.scopes[id];
    const current =
      PHASE3_CURRENT_REVIEWED_COMPARISON.scopes[id];

    assert.deepEqual(registry.expectedCounts, {
      armCount: reviewed.armCount,
      trialCount: reviewed.trialCount,
      successCount: reviewed.successCount,
    });
    assert.equal(registry.presentationKind, reviewed.presentationKind);
    assert.equal(registry.snapshotDate, reviewed.snapshotDate);

    assert.equal(
      registry.selectedCostUsd,
      Number(current.selectedCostEvidence.selectedCostUsd),
    );
    assert.equal(
      registry.historicalReviewedCostUsd,
      Number(
        current.selectedCostEvidence
          .historicalReviewedArmSumCostUsd,
      ),
    );
    assert.equal(
      registry.selectedCostBasis,
      current.selectedCostEvidence.selectedCostBasis,
    );
    assert.equal(
      registry.currentReconciledArmCount,
      current.selectedCostEvidence.currentReconciledArmCount,
    );
    assert.equal(
      registry.currentReconciledCostUsd,
      Number(
        current.selectedCostEvidence.currentReconciledCostUsd,
      ),
    );
    assert.equal(
      registry.currentCostReviewedAt,
      PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
    );
    assert.equal(registry.adjustedKnownCostUsd, reviewed.costEvidence.adjustedKnownCostUsd === null
      ? null
      : Number(reviewed.costEvidence.adjustedKnownCostUsd));
    assert.equal(
      registry.qualifiedAdjustedCostEstimateUsd,
      reviewed.costEvidence.qualifiedAdjustedCostEstimateUsd === null
        ? null
        : Number(reviewed.costEvidence.qualifiedAdjustedCostEstimateUsd),
    );
    assert.equal(
      registry.kimiK3Disposition,
      reviewed.arms.some((arm) => arm.armId === "router-kimi-k3") ? "included" : "excluded",
    );
  }
});

test("dynamic imported scopes fabricate no fixed totals or comparison validity", () => {
  for (const id of ["valid-imported", "all-imported"]) {
    const scope = getCorpusScope(id);
    assert.equal(scope.populationKind, "dynamic");
    assert.equal(scope.expectedCounts, null);
    assert.equal(scope.selectedCostUsd, null);
    assert.equal(scope.historicalReviewedCostUsd, null);
    assert.equal(scope.selectedCostBasis, null);
    assert.equal(scope.currentReconciledArmCount, null);
    assert.equal(scope.currentReconciledCostUsd, null);
    assert.equal(scope.currentCostReviewedAt, null);
    assert.equal(scope.selectedCostDescription, null);
    assert.equal(scope.adjustedKnownCostUsd, null);
    assert.equal(scope.qualifiedAdjustedCostEstimateUsd, null);
    assert.equal(scope.costDisplayLabel, null);
    assert.equal(scope.comparisonValid, false);
    assert.equal(scope.kimiK3Disposition, "population_dependent");
  }
  assert.equal(getCorpusScope("unknown-scope"), null);
});

test("count comparison supports full and partial fixed matches", () => {
  const core = getCorpusScope("phase3-core");
  const full = compareCorpusScopeCounts(core, { armCount: 15, trialCount: 900, successCount: 515 });
  assert.equal(full.status, "match");
  assert.equal(full.reason, "compared");
  assert.deepEqual(full.comparedFields, ["armCount", "trialCount", "successCount"]);
  assert.deepEqual(full.mismatchedFields, []);

  const partial = compareCorpusScopeCounts(core, { trialCount: 900 });
  assert.equal(partial.status, "match");
  assert.equal(partial.reason, "compared");
  assert.deepEqual(partial.comparedFields, ["trialCount"]);
  assert.deepEqual(partial.mismatchedFields, []);
});

test("count comparison reports partial mismatch and ignores omitted or null fields", () => {
  const extended = getCorpusScope("phase3-extended");
  const mismatch = compareCorpusScopeCounts(extended, {
    armCount: 15,
    trialCount: null,
  });
  assert.equal(mismatch.status, "mismatch");
  assert.equal(mismatch.reason, "compared");
  assert.deepEqual(mismatch.comparedFields, ["armCount"]);
  assert.deepEqual(mismatch.mismatchedFields, ["armCount"]);

  const nullAndOmitted = compareCorpusScopeCounts(extended, {
    armCount: 16,
    trialCount: null,
  });
  assert.equal(nullAndOmitted.status, "match");
  assert.deepEqual(nullAndOmitted.comparedFields, ["armCount"]);
  assert.deepEqual(nullAndOmitted.mismatchedFields, []);
});

test("zero is an observed count and mismatches a nonzero fixed expectation", () => {
  const core = getCorpusScope("phase3-core");
  const comparison = compareCorpusScopeCounts(core, { successCount: 0 });
  assert.equal(comparison.status, "mismatch");
  assert.equal(comparison.reason, "compared");
  assert.deepEqual(comparison.comparedFields, ["successCount"]);
  assert.deepEqual(comparison.mismatchedFields, ["successCount"]);
});

test("fixed scope without numeric observations has its own non-applicable reason", () => {
  const core = getCorpusScope("phase3-core");
  for (const observed of [{}, { armCount: null, trialCount: undefined }]) {
    const comparison = compareCorpusScopeCounts(core, observed);
    assert.equal(comparison.status, "not_applicable");
    assert.equal(comparison.reason, "no_observed_counts");
    assert.equal(comparison.expected, core.expectedCounts);
    assert.deepEqual(comparison.comparedFields, []);
    assert.deepEqual(comparison.mismatchedFields, []);
  }
});

test("dynamic scope comparison is not applicable regardless of observations", () => {
  const dynamic = getCorpusScope("valid-imported");
  const notApplicable = compareCorpusScopeCounts(dynamic, { trialCount: 1_234 });
  assert.equal(notApplicable.status, "not_applicable");
  assert.equal(notApplicable.reason, "dynamic_scope");
  assert.equal(notApplicable.expected, null);
  assert.deepEqual(notApplicable.comparedFields, []);
  assert.deepEqual(notApplicable.mismatchedFields, []);
});
