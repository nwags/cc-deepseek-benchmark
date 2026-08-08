import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const snapshot = JSON.parse(await readFile(
  resolve(here, "../../../../results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json"),
  "utf8",
));
const source = await readFile(join(here, "cross-phase-reporting.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const {
  getBehaviorRows,
  getCrossPhaseRows,
  getPhaseSummaries,
  getReviewedPhase3Rows,
  getRouterComparisonRows,
} = await import(moduleUrl);

const core = snapshot.scopes["phase3-core"];
const extended = snapshot.scopes["phase3-extended"];

test("selected reviewed scope replaces only Phase 3 cross-phase rows", () => {
  const coreRows = getCrossPhaseRows(core);
  const extendedRows = getCrossPhaseRows(extended);

  assert.equal(coreRows.filter((row) => row.phase === "phase1").length, 3);
  assert.equal(coreRows.filter((row) => row.phase === "phase2").length, 5);
  assert.equal(coreRows.filter((row) => row.phase === "phase3").length, 15);
  assert.equal(extendedRows.filter((row) => row.phase === "phase3").length, 16);
  assert.equal(coreRows.some((row) => row.arm_id === "router-kimi-k3"), false);
  assert.equal(extendedRows.some((row) => row.arm_id === "router-kimi-k3"), true);
});

test("Kimi row preserves qualified cost evidence and unavailable outcome fields", () => {
  const kimi = getReviewedPhase3Rows(extended).find((row) => row.arm_id === "router-kimi-k3");
  assert.ok(kimi);
  assert.equal(kimi.trial_count, 60);
  assert.equal(kimi.success_count, 47);
  assert.equal(kimi.pass_rate, 47 / 60);
  assert.equal(kimi.recorded_cost_usd, 25.207213);
  assert.equal(kimi.adjusted_cost_usd, 30.8143194);
  assert.equal(kimi.known_accounting_gap_usd, 5.6071064);
  assert.equal(kimi.reviewed_cost_basis, "qualified_retained_rate_estimate");
  assert.equal(kimi.reviewed_cost_label, "Qualified retained-rate reconstruction");
  assert.equal(kimi.cost_per_clean_success_usd, null);
  assert.equal(kimi.failure_incomplete_spend_share, null);
  assert.equal(kimi.unclean_spend_share, null);
  assert.equal(kimi.median_wall_clock_seconds, null);
  assert.equal(kimi.pricing_provenance_status, "incomplete");
  assert.equal(kimi.arm_run_allocation_confidence, "low");
  assert.equal(kimi.trial_allocation_status, "unresolved");
  assert.equal(kimi.billing_reconciliation_status, "not_invoice_level_or_provider_billed");
});

test("Phase 3 summary uses selected reviewed scope headline values", () => {
  const extendedSummary = getPhaseSummaries(
    getCrossPhaseRows(extended),
    extended,
  ).find((row) => row.phase === "phase3");
  assert.deepEqual(
    [extendedSummary.arm_count, extendedSummary.trial_count, extendedSummary.success_count],
    [16, 960, 562],
  );
  assert.equal(extendedSummary.adjusted_cost_usd, 1002.9841648891979);
  assert.equal(extendedSummary.cost_basis, "qualified_adjusted_cost_estimate");
  assert.equal(extendedSummary.cost_per_clean_success_usd, null);
  assert.equal(extendedSummary.unclean_spend_share, null);

  const coreSummary = getPhaseSummaries(
    getCrossPhaseRows(core),
    core,
  ).find((row) => row.phase === "phase3");
  assert.deepEqual(
    [coreSummary.arm_count, coreSummary.trial_count, coreSummary.success_count],
    [15, 900, 515],
  );
  assert.equal(coreSummary.adjusted_cost_usd, 972.169845489198);
  assert.equal(coreSummary.cost_basis, "adjusted_known_cost");
});

test("historical router and behavior artifacts remain core-only", () => {
  assert.equal(getBehaviorRows().some((row) => row.arm_id === "router-kimi-k3"), false);
  assert.equal(getRouterComparisonRows().some((row) => row.router_arm_id === "router-kimi-k3"), false);
});
