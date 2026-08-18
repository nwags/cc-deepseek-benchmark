import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const comparison = JSON.parse(await readFile(
  resolve(here, "../../../../results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json"),
  "utf8",
));
const runSelection = JSON.parse(await readFile(
  resolve(here, "../../../../results/phase3/reporting/phase3_reviewed_run_selection_20260809.json"),
  "utf8",
));
const source = await readFile(join(here, "overview-reviewed-comparison.ts"), "utf8");
const linksSource = await readFile(join(here, "evidence-links.ts"), "utf8");
const linksCompiled = ts.transpileModule(linksSource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText.replace(/^import .*;$/gm, "");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(`${linksCompiled}\n${compiled}`).toString("base64")}`;
const {
  buildOverviewReviewedComparison,
  buildReviewedRunHref,
} = await import(moduleUrl);

const scope = comparison.scopes["phase3-extended"];
const selectionScope = runSelection.scopes["phase3-extended"];

function databaseRunRows() {
  const armById = new Map(scope.arms.map((arm) => [arm.armId, arm]));
  return selectionScope.selections.map((selection, index) => {
    const arm = armById.get(selection.armId);
    return {
      arm_run_id: `arm-run-${index}`,
      run_id: `run-${index}`,
      run_label: selection.selectedRunLabel,
      arm_id: selection.armId,
      provider_family: arm.provider,
      backend_model: arm.backendModel,
      router_model: null,
      suite_id: "phase3-full-20",
      suite_type: "full",
      logical_mode: "full",
      storage_mode: "full",
      status: "completed",
      started_at: "2026-07-01T00:00:00Z",
      finished_at: "2026-07-01T01:00:00Z",
      task_count: 20,
      trial_count: arm.trialCount,
      success_count: arm.successCount,
      failure_count: arm.trialCount - arm.successCount,
      median_runtime_seconds: arm.medianWallClockSeconds,
      trial_cost_usd: arm.recordedCostUsd,
      cost_row_count: arm.trialCount - arm.missingRecordedCostCount,
      missing_cost_count: arm.missingRecordedCostCount,
      artifact_count: 1,
      r2_artifact_count: 1,
    };
  });
}

function databaseCostRows() {
  const armById = new Map(scope.arms.map((arm) => [arm.armId, arm]));
  return selectionScope.selections.map((selection) => {
    const arm = armById.get(selection.armId);
    const kimi = arm.armId === "router-kimi-k3";
    return {
      run_label: selection.selectedRunLabel,
      arm_id: arm.armId,
      suite_id: "phase3-full-20",
      trial_count: arm.trialCount,
      recorded_cost_usd: arm.recordedCostUsd,
      adjusted_known_cost_usd: kimi ? null : arm.adjustedKnownCostUsd,
      accounting_gap_usd: kimi ? null : arm.accountingGapUsd,
      missing_recorded_cost_count: arm.missingRecordedCostCount,
      unresolved_adjusted_cost_count: arm.unresolvedCostCount,
      adjusted_cost_sources: [...arm.costSources],
      adjusted_cost_confidences: [arm.costConfidence],
    };
  });
}

function build(overrides = {}) {
  return buildOverviewReviewedComparison({
    scope,
    runSelectionScope: selectionScope,
    comparisonReviewedAt: comparison.reviewedAt,
    runSelectionReviewedAt: runSelection.reviewedAt,
    databaseRunReadStatus: "available",
    databaseRunRows: databaseRunRows(),
    databaseCostReadStatus: "available",
    databaseAdjustedCostRows: databaseCostRows(),
    ...overrides,
  });
}

function rowFor(result, armId) {
  const row = result.rows.find((candidate) => candidate.armId === armId);
  assert.ok(row, `missing ${armId}`);
  return row;
}

test("joins all 16 F1 arms to exactly one frozen G1 selected run", () => {
  const result = build();
  assert.deepEqual([result.armCount, result.trialCount, result.successCount], [16, 960, 562]);
  assert.equal(result.rows.length, 16);
  assert.equal(new Set(result.rows.map((row) => row.selectedRunLabel)).size, 16);
  const kimi = rowFor(result, "router-kimi-k3");
  assert.equal(kimi.selectedRunLabel, "router-kimi-k3/2026-07-22__17-51-05");
  assert.equal(kimi.selectedRunHref, "/runs/router-kimi-k3%2F2026-07-22__17-51-05?source_scope=phase3-extended");
  assert.equal(buildReviewedRunHref(kimi.selectedRunLabel), kimi.selectedRunHref);
  const costUrl = new URL(kimi.costProvenanceHref, "https://dashboard.invalid");
  assert.equal(costUrl.searchParams.get("scope"), "phase3-extended");
  assert.equal(costUrl.searchParams.get("arm_id"), kimi.armId);
  assert.equal(costUrl.searchParams.get("run_label"), kimi.selectedRunLabel);
  assert.equal(costUrl.searchParams.get("source_scope"), "phase3-extended");
  assert.equal(costUrl.hash, "#cost-provenance-focus");
  assert.equal(new URL(kimi.armEvidenceHref, "https://dashboard.invalid").searchParams.get("trial_arm"), kimi.armId);
});

test("a missing exact database run never selects another row for the same arm", () => {
  const runs = databaseRunRows();
  const kimiIndex = runs.findIndex((row) => row.arm_id === "router-kimi-k3");
  runs.splice(kimiIndex, 1);
  runs.push({
    ...databaseRunRows()[kimiIndex],
    arm_run_id: "newer-run",
    run_label: "router-kimi-k3/2099-01-01__00-00-00",
  });
  const result = build({ databaseRunRows: runs });
  const kimi = rowFor(result, "router-kimi-k3");
  assert.equal(kimi.databaseRunEvidenceStatus, "missing");
  assert.equal(kimi.databaseRunEvidence, null);
  assert.equal(kimi.reconciliationIssues.includes("missing_database_run"), true);
  assert.equal(result.databaseEvidenceWarnings.length, 1);
});

test("duplicate exact database runs are explicit", () => {
  const runs = databaseRunRows();
  runs.push({ ...runs[0], arm_run_id: "duplicate" });
  const row = rowFor(build({ databaseRunRows: runs }), runs[0].arm_id);
  assert.equal(row.databaseRunEvidenceStatus, "duplicate");
  assert.equal(row.reconciliationStatus, "duplicate_database_run");
});

test("wrong arm and wrong suite are detected", () => {
  const wrongArm = databaseRunRows();
  wrongArm[0] = { ...wrongArm[0], arm_id: "not-the-reviewed-arm" };
  assert.equal(rowFor(build({ databaseRunRows: wrongArm }), scope.arms[0].armId).databaseRunEvidenceStatus, "arm_mismatch");

  const wrongSuite = databaseRunRows();
  wrongSuite[0] = { ...wrongSuite[0], suite_id: "phase3-smoke" };
  assert.equal(rowFor(build({ databaseRunRows: wrongSuite }), scope.arms[0].armId).databaseRunEvidenceStatus, "suite_mismatch");
});

test("trial and success count mismatches are detected", () => {
  const trials = databaseRunRows();
  trials[0] = { ...trials[0], trial_count: 59 };
  assert.equal(rowFor(build({ databaseRunRows: trials }), scope.arms[0].armId).databaseRunEvidenceStatus, "count_mismatch");

  const successes = databaseRunRows();
  successes[0] = { ...successes[0], success_count: successes[0].success_count - 1 };
  assert.equal(rowFor(build({ databaseRunRows: successes }), scope.arms[0].armId).databaseRunEvidenceStatus, "count_mismatch");
});

test("core recorded and adjusted cost mismatches are detected without float equality", () => {
  const armId = scope.arms.find((arm) => arm.armId !== "router-kimi-k3").armId;
  const recorded = databaseRunRows();
  const runIndex = recorded.findIndex((row) => row.arm_id === armId);
  recorded[runIndex] = { ...recorded[runIndex], trial_cost_usd: "999.123456789" };
  assert.equal(rowFor(build({ databaseRunRows: recorded }), armId).reconciliationIssues.includes("cost_mismatch"), true);

  const adjusted = databaseCostRows();
  const costIndex = adjusted.findIndex((row) => row.arm_id === armId);
  adjusted[costIndex] = { ...adjusted[costIndex], adjusted_known_cost_usd: "999.123456789" };
  const mismatch = rowFor(build({ databaseAdjustedCostRows: adjusted }), armId);
  assert.equal(mismatch.databaseCostEvidenceStatus, "mismatch");
  assert.equal(mismatch.reconciliationIssues.includes("cost_mismatch"), true);

  const matching = rowFor(build(), armId);
  assert.equal(matching.databaseCostEvidenceStatus, "match");
});

test("unavailable database reads retain reviewed identity and costs", () => {
  const result = build({
    databaseRunReadStatus: "unavailable",
    databaseRunRows: [],
    databaseCostReadStatus: "unavailable",
    databaseAdjustedCostRows: [],
  });
  const row = result.rows[0];
  assert.equal(row.databaseRunEvidenceStatus, "unavailable");
  assert.equal(row.databaseCostEvidenceStatus, "unavailable");
  assert.equal(row.databaseRunEvidence, null);
  assert.equal(row.reviewedRecordedCostUsd, scope.arms.find((arm) => arm.armId === row.armId).recordedCostUsd);
});

test("Kimi database evidence cannot become adjusted-known cost", () => {
  const costs = databaseCostRows();
  const index = costs.findIndex((row) => row.arm_id === "router-kimi-k3");
  costs[index] = {
    ...costs[index],
    adjusted_known_cost_usd: "999.999",
    accounting_gap_usd: "974.791787",
  };
  const kimi = rowFor(build({ databaseAdjustedCostRows: costs }), "router-kimi-k3");
  assert.equal(kimi.reviewedAdjustedKnownCostUsd, null);
  assert.equal(kimi.reviewedQualifiedRetainedRateCostUsd, "30.8143194");
  assert.equal(kimi.reviewedRecordedCostUsd, "25.207213");
  assert.equal(kimi.reviewedAccountingGapUsd, "5.6071064");
  assert.equal(kimi.databaseCostEvidenceStatus, "qualified_not_authoritative");
  assert.equal(kimi.pricingProvenanceStatus, "incomplete");
  assert.equal(kimi.armRunAllocationConfidence, "low");
  assert.equal(kimi.providerLogExclusivityStatus, "not_proven");
  assert.equal(kimi.trialAllocationStatus, "unresolved");
  assert.equal(kimi.billingReconciliationStatus, "not_invoice_level_or_provider_billed");
});

test("F1 and G1 membership disagreement fails instead of falling back", () => {
  const mismatched = structuredClone(selectionScope);
  mismatched.selections.pop();
  mismatched.armCount -= 1;
  mismatched.selectedRunCount -= 1;
  mismatched.trialCount -= 60;
  assert.throws(
    () => build({ runSelectionScope: mismatched }),
    /F1 reviewed arms and G1 selected-run membership disagree/,
  );
});
