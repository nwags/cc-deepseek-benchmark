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

const currentCanonical = JSON.parse(await readFile(
  resolve(
    here,
    "../../../../results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json",
  ),
  "utf8",
));

const currentGeneratedSource = await readFile(
  resolve(
    here,
    "../generated/phase3-current-reviewed-comparison-data.ts",
  ),
  "utf8",
);
const currentGeneratedModuleUrl =
  await transpiledDataUrl(currentGeneratedSource);
const { default: currentGeneratedSnapshot } =
  await import(currentGeneratedModuleUrl);

const historicalGeneratedSource = await readFile(
  resolve(
    here,
    "../generated/phase3-reviewed-comparison-data.ts",
  ),
  "utf8",
);
const historicalGeneratedModuleUrl =
  await transpiledDataUrl(historicalGeneratedSource);

const historicalLoaderSource = (
  await readFile(
    join(here, "phase3-reviewed-comparison.ts"),
    "utf8",
  )
).replace(
  '"../generated/phase3-reviewed-comparison-data"',
  `"${historicalGeneratedModuleUrl}"`,
);
const historicalLoaderModuleUrl =
  await transpiledDataUrl(historicalLoaderSource);

const currentLoaderSource = (
  await readFile(
    join(here, "phase3-current-reviewed-comparison.ts"),
    "utf8",
  )
)
  .replace(
    '"../generated/phase3-current-reviewed-comparison-data"',
    `"${currentGeneratedModuleUrl}"`,
  )
  .replace(
    '"./phase3-reviewed-comparison"',
    `"${historicalLoaderModuleUrl}"`,
  );

const currentLoaderModuleUrl =
  await transpiledDataUrl(currentLoaderSource);

const {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  getCurrentReviewedPhase3Scope,
  selectCurrentReviewedPhase3Scope,
  validatePhase3CurrentReviewedComparison,
} = await import(currentLoaderModuleUrl);

const clone = () => structuredClone(currentCanonical);

test("generated v2 dashboard module exactly matches canonical current-reviewed JSON", () => {
  assert.deepEqual(currentGeneratedSnapshot, currentCanonical);
});

test("current-reviewed loader exposes exact scope selected-cost anchors", () => {
  const core = getCurrentReviewedPhase3Scope("phase3-core");
  const extended = getCurrentReviewedPhase3Scope("phase3-extended");

  assert.equal(
    PHASE3_CURRENT_REVIEWED_COMPARISON.schemaVersion,
    "phase3-current-reviewed-comparison-v2",
  );
  assert.equal(
    PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
    "2026-08-21",
  );
  assert.equal(
    PHASE3_CURRENT_REVIEWED_COMPARISON.historicalReviewedAt,
    "2026-08-05",
  );

  assert.equal(
    core.selectedCostEvidence.selectedCostUsd,
    "682.961171493867",
  );
  assert.equal(
    extended.selectedCostEvidence.selectedCostUsd,
    "713.775490893867",
  );
  assert.equal(
    extended.selectedCostEvidence
      .sourceScopeTransformedSelectedCostUsd,
    "713.7754908938669",
  );
  assert.equal(
    extended.selectedCostEvidence
      .sourceScopeReconciliationAdjustmentUsd,
    "-0.0000000000001",
  );

  assert.equal(Object.isFrozen(core), true);
  assert.equal(Object.isFrozen(extended.arms), true);
});

test("OpenAI full-sweep arms select exact provider-billed totals without fabricated allocation", () => {
  const extended =
    getCurrentReviewedPhase3Scope("phase3-extended");

  const gpt54 = extended.arms.find(
    (arm) => arm.armId === "router-gpt-5.4",
  );
  const gpt55 = extended.arms.find(
    (arm) => arm.armId === "router-gpt-5.5",
  );

  assert.ok(gpt54);
  assert.ok(gpt55);

  assert.equal(gpt54.selectedCostUsd, "29.7919335");
  assert.equal(gpt54.selectedCostBasis, "provider_billed");
  assert.equal(
    gpt54.selectedCostPerAttemptUsd,
    "0.496532225",
  );
  assert.equal(
    gpt54.selectedCostPerCleanSuccessUsd,
    "0.78399825",
  );
  assert.equal(
    gpt54.selectedTrialCostAllocationStatus,
    "unavailable_provider_aggregate",
  );
  assert.equal(
    gpt54.selectedOutcomeCostAllocationStatus,
    "unavailable_provider_aggregate",
  );

  assert.equal(gpt55.selectedCostUsd, "48.604914");
  assert.equal(gpt55.selectedCostBasis, "provider_billed");
  assert.equal(
    gpt55.selectedCostPerAttemptUsd,
    "0.8100819",
  );
  assert.equal(
    gpt55.selectedCostPerCleanSuccessUsd,
    "1.157259857142857142857142857",
  );
  assert.equal(
    gpt55.selectedTrialCostAllocationStatus,
    "unavailable_provider_aggregate",
  );
  assert.equal(
    gpt55.selectedOutcomeCostAllocationStatus,
    "unavailable_provider_aggregate",
  );
});

test("historical cost evidence remains separately available and unchanged", () => {
  const extended =
    getCurrentReviewedPhase3Scope("phase3-extended");

  const gpt54 = extended.arms.find(
    (arm) => arm.armId === "router-gpt-5.4",
  );
  const gpt55 = extended.arms.find(
    (arm) => arm.armId === "router-gpt-5.5",
  );
  const kimi = extended.arms.find(
    (arm) => arm.armId === "router-kimi-k3",
  );

  assert.ok(gpt54);
  assert.ok(gpt55);
  assert.ok(kimi);

  assert.equal(
    gpt54.historicalHarnessRecordedCostUsd,
    "173.09483",
  );
  assert.equal(
    gpt54.historicalReviewedCostUsd,
    "183.646689146806",
  );
  assert.equal(
    gpt55.historicalHarnessRecordedCostUsd,
    "168.708375",
  );
  assert.equal(
    gpt55.historicalReviewedCostUsd,
    "183.958832348525",
  );

  assert.equal(kimi.providerBilledCostUsd, null);
  assert.equal(
    kimi.selectedCostBasis,
    "qualified_retained_rate_estimate",
  );
  assert.equal(kimi.selectedCostUsd, "30.8143194");

  assert.equal(
    extended.historicalCostEvidence
      .qualifiedAdjustedCostEstimateUsd,
    "1002.9841648891979",
  );
});

test("loader fails closed on selected-cost, provider-allocation, and historical mutations", () => {
  const wrongTotal = clone();
  wrongTotal.scopes["phase3-core"]
    .selectedCostEvidence.selectedCostUsd = "1";
  assert.throws(
    () => validatePhase3CurrentReviewedComparison(wrongTotal),
    /selected-cost contract|exact arm sum/i,
  );

  const wrongProviderAllocation = clone();
  const gpt54 = wrongProviderAllocation.scopes[
    "phase3-extended"
  ].arms.find(
    (arm) => arm.armId === "router-gpt-5.4",
  );
  gpt54.selectedTrialCostAllocationStatus =
    "available_for_reviewed_layer";
  assert.throws(
    () =>
      validatePhase3CurrentReviewedComparison(
        wrongProviderAllocation,
      ),
    /OpenAI provider-billed selection/i,
  );

  const historicalDrift = clone();
  historicalDrift.scopes["phase3-core"]
    .arms[0].recordedCostUsd = "0";
  assert.throws(
    () =>
      validatePhase3CurrentReviewedComparison(
        historicalDrift,
      ),
    /does not preserve the frozen historical arm/i,
  );

  const nonProviderMetricDrift = clone();
  const nonProviderArm = nonProviderMetricDrift.scopes[
    "phase3-core"
  ].arms.find(
    (arm) => arm.selectedCostBasis !== "provider_billed",
  );
  assert.ok(nonProviderArm);
  nonProviderArm.selectedCostPerAttemptUsd = "0";
  assert.throws(
    () =>
      validatePhase3CurrentReviewedComparison(
        nonProviderMetricDrift,
      ),
    /selected-cost efficiency metrics/i,
  );

  const qualifiedMetricDrift = clone();
  const kimi = qualifiedMetricDrift.scopes[
    "phase3-extended"
  ].arms.find(
    (arm) => arm.armId === "router-kimi-k3",
  );
  assert.ok(kimi);
  kimi.selectedCostPerCleanSuccessUsd = "0";
  assert.throws(
    () =>
      validatePhase3CurrentReviewedComparison(
        qualifiedMetricDrift,
      ),
    /selected-cost efficiency metrics/i,
  );
});

test("scope selection defaults deterministically to extended and rejects repeated or unknown values", () => {
  assert.equal(
    selectCurrentReviewedPhase3Scope(undefined).scopeId,
    "phase3-extended",
  );
  assert.equal(
    selectCurrentReviewedPhase3Scope(
      "phase3-core",
    ).scopeId,
    "phase3-core",
  );

  const repeated =
    selectCurrentReviewedPhase3Scope([
      "phase3-core",
      "phase3-extended",
    ]);
  assert.equal(repeated.scopeId, "phase3-extended");
  assert.equal(repeated.warning, "repeated_scope");

  const invalid =
    selectCurrentReviewedPhase3Scope("future-scope");
  assert.equal(invalid.scopeId, "phase3-extended");
  assert.equal(invalid.warning, "invalid_scope");
});
