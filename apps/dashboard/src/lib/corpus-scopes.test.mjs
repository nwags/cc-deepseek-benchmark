import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "corpus-scopes.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
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
  assert.equal(core.adjustedKnownCostUsd, 972.17);
  assert.equal(core.comparisonValid, true);
  assert.equal(core.costCoverageState, "reviewed_adjusted_snapshot");
  assert.equal(core.kimiK3Disposition, "excluded");
  assert.match(core.excludedPopulation, /router-kimi-k3/);
  assert.deepEqual(extended.expectedCounts, { armCount: 16, trialCount: 960, successCount: 562 });
  assert.equal(Object.isFrozen(extended.expectedCounts), true);
  assert.equal(extended.comparisonValid, true);
  assert.equal(extended.adjustedKnownCostUsd, null);
  assert.equal(extended.costCoverageState, "partial_observed_unreconciled");
  assert.equal(extended.kimiK3Disposition, "included");
  assert.match(extended.includedPopulation, /router-kimi-k3/);
});

test("dynamic imported scopes fabricate no fixed totals or comparison validity", () => {
  for (const id of ["valid-imported", "all-imported"]) {
    const scope = getCorpusScope(id);
    assert.equal(scope.populationKind, "dynamic");
    assert.equal(scope.expectedCounts, null);
    assert.equal(scope.adjustedKnownCostUsd, null);
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
