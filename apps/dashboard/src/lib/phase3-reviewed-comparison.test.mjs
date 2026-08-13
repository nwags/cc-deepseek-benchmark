import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const snapshot = JSON.parse(await readFile(
  resolve(here, "../../../../results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json"),
  "utf8",
));
const generatedSource = await readFile(
  resolve(here, "../generated/phase3-reviewed-comparison-data.ts"),
  "utf8",
);
const generatedCompiled = ts.transpileModule(generatedSource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const snapshotModule = `data:text/javascript;base64,${Buffer.from(generatedCompiled).toString("base64")}`;
const { default: generatedSnapshot } = await import(snapshotModule);
const source = (await readFile(join(here, "phase3-reviewed-comparison.ts"), "utf8"))
  .replace(
    '"../generated/phase3-reviewed-comparison-data"',
    `"${snapshotModule}"`,
  );
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const {
  PHASE3_REVIEWED_COMPARISON,
  getReviewedPhase3Scope,
  selectReviewedPhase3Scope,
  validatePhase3ReviewedComparison,
} = await import(moduleUrl);

const clone = () => structuredClone(snapshot);

test("app-local generated module is deeply equivalent to canonical JSON", () => {
  assert.deepEqual(generatedSnapshot, snapshot);

  const changedCanonical = clone();
  changedCanonical.reviewedAt = "2026-08-06";
  assert.throws(() => assert.deepEqual(generatedSnapshot, changedCanonical));

  const changedGenerated = structuredClone(generatedSnapshot);
  changedGenerated.scopes["phase3-core"].trialCount = 899;
  assert.throws(() => assert.deepEqual(changedGenerated, snapshot));
});

test("loader accepts and freezes the checked reviewed snapshot", () => {
  assert.equal(PHASE3_REVIEWED_COMPARISON.schemaVersion, "phase3-reviewed-comparison-v1");
  assert.equal(PHASE3_REVIEWED_COMPARISON.scopes["phase3-core"].arms.length, 15);
  assert.equal(PHASE3_REVIEWED_COMPARISON.scopes["phase3-extended"].arms.length, 16);
  assert.equal(Object.isFrozen(PHASE3_REVIEWED_COMPARISON), true);
  assert.equal(Object.isFrozen(PHASE3_REVIEWED_COMPARISON.scopes["phase3-extended"].arms), true);
  assert.equal(PHASE3_REVIEWED_COMPARISON.reviewedAt, "2026-08-05");
});

test("loader rejects unknown schemas, duplicate arms, and count mismatches", () => {
  const unknown = clone();
  unknown.schemaVersion = "future-version";
  assert.throws(() => validatePhase3ReviewedComparison(unknown), /unsupported.*schema version/i);

  const duplicate = clone();
  duplicate.scopes["phase3-core"].arms.push(structuredClone(duplicate.scopes["phase3-core"].arms[0]));
  assert.throws(() => validatePhase3ReviewedComparison(duplicate), /duplicate arm IDs/);

  const mismatch = clone();
  mismatch.scopes["phase3-extended"].trialCount = 959;
  assert.throws(
    () => validatePhase3ReviewedComparison(mismatch),
    /count totals|fixed expectations|covered and excluded trials/,
  );
});

test("loader enforces the Kimi K3 core and extended membership boundary", () => {
  const kimiInCore = clone();
  kimiInCore.scopes["phase3-core"].arms[0].armId = "router-kimi-k3";
  assert.throws(() => validatePhase3ReviewedComparison(kimiInCore), /must not appear in phase3-core/);

  const kimiMissing = clone();
  const kimi = kimiMissing.scopes["phase3-extended"].arms.find(
    (arm) => arm.armId === "router-kimi-k3",
  );
  kimi.armId = "router-kimi-k3-missing";
  assert.throws(() => validatePhase3ReviewedComparison(kimiMissing), /must contain router-kimi-k3/);
});

test("loader rejects changed arm costs, core statuses, and Kimi counts", () => {
  const changedCost = clone();
  const coreCostArm = changedCost.scopes["phase3-core"].arms[0];
  const extendedCostArm = changedCost.scopes["phase3-extended"].arms.find(
    (arm) => arm.armId === coreCostArm.armId,
  );
  for (const arm of [coreCostArm, extendedCostArm]) {
    arm.recordedCostUsd = "0";
    arm.accountingGapUsd = arm.adjustedKnownCostUsd;
  }
  assert.throws(() => validatePhase3ReviewedComparison(changedCost), /arm costs do not reconcile/);

  const changedStatus = clone();
  const coreStatusArm = changedStatus.scopes["phase3-core"].arms[0];
  const extendedStatusArm = changedStatus.scopes["phase3-extended"].arms.find(
    (arm) => arm.armId === coreStatusArm.armId,
  );
  coreStatusArm.pricingProvenanceStatus = "incomplete";
  extendedStatusArm.pricingProvenanceStatus = "incomplete";
  assert.throws(() => validatePhase3ReviewedComparison(changedStatus), /core arm cost evidence/);

  const changedKimiCounts = clone();
  const kimi = changedKimiCounts.scopes["phase3-extended"].arms.find(
    (arm) => arm.armId === "router-kimi-k3",
  );
  kimi.cleanSuccessCount = 43;
  kimi.exceptionSuccessSignalCount = 4;
  assert.throws(() => validatePhase3ReviewedComparison(changedKimiCounts), /Kimi|evidence distinctions/);

  const invalidShare = clone();
  invalidShare.scopes["phase3-core"].arms[0].failureOrIncompleteSpendShare = 1.01;
  assert.throws(() => validatePhase3ReviewedComparison(invalidShare), /between zero and one/);
});

test("outcome-cost coverage is complete for core and explicitly partial for extended", () => {
  const core = PHASE3_REVIEWED_COMPARISON.scopes["phase3-core"].outcomeCostCoverage;
  const extended = PHASE3_REVIEWED_COMPARISON.scopes["phase3-extended"].outcomeCostCoverage;
  assert.deepEqual(core.rows.map((row) => row.outcomeBucket), [
    "clean_success",
    "exception_with_success_signal",
    "normal_failure",
    "exception_failure",
  ]);
  assert.equal(core.status, "available");
  assert.equal(core.coveredTrialCount, 900);
  assert.equal(core.excludedTrialCount, 0);
  assert.deepEqual(core.excludedArmIds, []);
  assert.equal(extended.status, "partial_core_only");
  assert.equal(extended.coveredTrialCount, 900);
  assert.equal(extended.excludedTrialCount, 60);
  assert.deepEqual(extended.excludedArmIds, ["router-kimi-k3"]);
  assert.deepEqual(extended.rows, core.rows);
  assert.equal(core.sourceAdjustedKnownCostTotalUsd, "972.169845489205");
  assert.equal(core.reviewedAdjustedKnownCostTotalUsd, "972.169845489198");
  assert.equal(core.reviewedScopeReconciliationAdjustmentUsd, "-0.000000000007");
  assert.equal("reconciledOutcomeBucket" in core, false);
  assert.equal(core.rows.at(-1).sourceAdjustedKnownCostUsd, "146.688488163366");
  assert.equal(core.rows.at(-1).sourceAccountingGapUsd, "122.869706913366");
});

test("loader rejects changed source rows, adjustments, bucket reconciliation, or Kimi outcome rows", () => {
  const badSum = clone();
  const coreRow = badSum.scopes["phase3-core"].outcomeCostCoverage.rows[0];
  coreRow.sourceAdjustedKnownCostUsd = "607.88236926";
  coreRow.sourceAccountingGapUsd = "0.00000001";
  assert.throws(
    () => validatePhase3ReviewedComparison(badSum),
    /source outcome rows|source adjusted-cost rows/,
  );

  const badAdjustment = clone();
  for (const id of ["phase3-core", "phase3-extended"]) {
    badAdjustment.scopes[id].outcomeCostCoverage.reviewedScopeReconciliationAdjustmentUsd = "0";
  }
  assert.throws(() => validatePhase3ReviewedComparison(badAdjustment), /disclosed adjustment/);

  const namedBucket = clone();
  for (const id of ["phase3-core", "phase3-extended"]) {
    namedBucket.scopes[id].outcomeCostCoverage.reconciledOutcomeBucket = "exception_failure";
  }
  assert.throws(() => validatePhase3ReviewedComparison(namedBucket), /not part of the reviewed schema/);

  const differentExtended = clone();
  const extendedRow = differentExtended.scopes["phase3-extended"].outcomeCostCoverage.rows[0];
  extendedRow.recordedCostUsd = "607.88236924";
  extendedRow.sourceAccountingGapUsd = "0.00000001";
  assert.throws(() => validatePhase3ReviewedComparison(differentExtended), /must equal the reviewed core rows/);

  const kimiOutcome = clone();
  kimiOutcome.scopes["phase3-extended"].outcomeCostCoverage.rows.push({
    outcomeBucket: "router-kimi-k3",
    trialCount: 60,
    recordedCostUsd: "25.207213",
    sourceAdjustedKnownCostUsd: "0",
    sourceAccountingGapUsd: "-25.207213",
    missingRecordedCostCount: 10,
    unresolvedAdjustedCostCount: 10,
  });
  assert.throws(() => validatePhase3ReviewedComparison(kimiOutcome), /row trial counts|reviewed core rows/);
});

test("loader rejects unexpected input paths, roles, dates, generators, and third scopes", () => {
  const badPath = clone();
  badPath.inputs[0].path = "results/unreviewed.csv";
  assert.throws(() => validatePhase3ReviewedComparison(badPath), /path or role|reviewed input set/);

  const badRole = clone();
  badRole.inputs[0].role = "unreviewed_role";
  assert.throws(() => validatePhase3ReviewedComparison(badRole), /path or role|reviewed input set/);

  const badDate = clone();
  badDate.reviewedAt = "2026-08-06";
  assert.throws(() => validatePhase3ReviewedComparison(badDate), /reviewedAt/);

  const badGenerator = clone();
  badGenerator.generator.name = "scripts/other.py";
  assert.throws(() => validatePhase3ReviewedComparison(badGenerator), /generator identity/);

  const thirdScope = clone();
  thirdScope.scopes["phase3-other"] = structuredClone(thirdScope.scopes["phase3-core"]);
  assert.throws(() => validatePhase3ReviewedComparison(thirdScope), /exactly phase3-core and phase3-extended/);
});

test("null Kimi outcome-cost and latency evidence remains unavailable", () => {
  const extended = getReviewedPhase3Scope("phase3-extended");
  const kimi = extended.arms.find((arm) => arm.armId === "router-kimi-k3");
  assert.ok(kimi);
  for (const field of [
    "adjustedKnownCostUsd",
    "adjustedCostPerCleanSuccessUsd",
    "adjustedCostPerAnySuccessUsd",
    "adjustedCleanSuccessCostUsd",
    "adjustedExceptionSuccessSignalCostUsd",
    "adjustedFailureOrIncompleteCostUsd",
    "failureOrIncompleteSpendShare",
    "nonproductiveOrUncleanSpendShare",
    "medianWallClockSeconds",
  ]) {
    assert.equal(kimi[field], null, field);
  }
  assert.equal(kimi.outcomeCostAllocationStatus, "unavailable");
});

test("scope selection defaults safely and exposes invalid or repeated-value warnings", () => {
  for (const missing of [undefined, null, ""]) {
    const selection = selectReviewedPhase3Scope(missing);
    assert.equal(selection.scopeId, "phase3-extended");
    assert.equal(selection.warning, null);
    assert.equal(selection.usedDefault, true);
  }

  for (const explicit of ["phase3-core", "phase3-extended"]) {
    const selection = selectReviewedPhase3Scope(explicit);
    assert.equal(selection.scopeId, explicit);
    assert.equal(selection.warning, null);
    assert.equal(selection.usedDefault, false);
  }

  const invalid = selectReviewedPhase3Scope("all-imported");
  assert.equal(invalid.scopeId, "phase3-extended");
  assert.equal(invalid.warning, "invalid_scope");
  assert.match(invalid.warningMessage, /Unknown scope/);

  const repeated = selectReviewedPhase3Scope(["phase3-core", "phase3-extended"]);
  assert.equal(repeated.scopeId, "phase3-extended");
  assert.equal(repeated.warning, "repeated_scope");
  assert.match(repeated.warningMessage, /Repeated scope/);
});
