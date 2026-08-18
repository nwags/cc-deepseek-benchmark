import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(here, "../..");
const readDashboard = (path) => readFile(join(dashboardRoot, path), "utf8");

const [
  chartModel,
  chartComponent,
  chartTable,
  overviewPage,
  costPage,
  crossPhasePage,
  armsPage,
  runDetailPage,
  comprehensivePage,
] = await Promise.all([
  readDashboard("src/lib/cost-performance-chart.ts"),
  readDashboard("src/components/CostPerformanceChart.tsx"),
  readDashboard("src/components/CostPerformanceChartTable.tsx"),
  readDashboard("src/app/page.tsx"),
  readDashboard("src/app/cost-coverage/page.tsx"),
  readDashboard("src/app/cross-phase/page.tsx"),
  readDashboard("src/app/arms/page.tsx"),
  readDashboard("src/app/runs/[runLabel]/page.tsx"),
  readDashboard("src/app/comprehensive-review/page.tsx"),
]);

test("reviewed chart and Overview use exact frozen run and focused cost contracts", () => {
  assert.match(chartModel, /buildExactRunHref\(selection\.selectedRunLabel, scope\.scopeId\)/);
  assert.match(chartModel, /buildCostCoverageHref\([\s\S]*scope\.scopeId[\s\S]*armId: arm\.armId, runLabel: selection\.selectedRunLabel/);
  assert.doesNotMatch(chartModel, /latest[-_ ]run|getRecentRuns|latestRun/i);
  assert.match(overviewPage, /href=\{row\.armEvidenceHref\}/);
  assert.match(overviewPage, /href=\{row\.selectedRunHref\}/);
  assert.match(overviewPage, /linkedReviewedUsd\(row\.reviewedRecordedCostUsd, row\.costProvenanceHref\)/);
  assert.match(chartComponent, /href=\{arm\.costProvenanceHref\}/);
  assert.match(chartTable, /linkedMetric\(row\.xMetricValue, row\.costProvenanceHref\)/);
});

test("Cost Coverage joins each reviewed arm to the exact frozen selected run", () => {
  assert.match(costPage, /getCostPerformanceChartArms\(selection\.scopeId\)/);
  assert.match(costPage, /No exact frozen selected run exists/);
  assert.match(costPage, /armId: arm\.armId, runLabel: chartArm\.selectedRunLabel/);
  assert.match(costPage, /buildExactRunHref\(chartArm\.selectedRunLabel, onwardSourceScope\)/);
  assert.match(costPage, /buildReviewedAggregateArmEvidenceHref\(arm\.armId, onwardSourceScope\)/);
  assert.doesNotMatch(costPage, /getRecentRuns|latestRun|findLatestRun/i);
});

test("Cross-phase links only Phase 3 reviewed rows to frozen run and cost evidence", () => {
  assert.match(crossPhasePage, /row\.phase === "phase3" \? chartArmById\.get\(row\.arm_id\) : null/);
  assert.match(crossPhasePage, /chartArm \? linkedMoney\(row\.recorded_cost_usd/);
  assert.match(crossPhasePage, /chartArm \? linkedMoney\(row\.adjusted_cost_usd/);
  assert.match(crossPhasePage, /chartArm \? linkedMoney\(row\.cost_per_clean_success_usd/);
  assert.match(crossPhasePage, /<div className="muted">Frozen aggregate row<\/div>/);
});

test("all-imported arm-only inventory is not sent to frozen Comprehensive Review", () => {
  assert.doesNotMatch(armsPage, /buildReviewedAggregateArmEvidenceHref/);
  assert.doesNotMatch(armsPage, /comprehensive-review/);
});

test("run-detail one-trial rows put the exact contextual trial action first", () => {
  const trialHeader = runDetailPage.indexOf('<th className="sticky-id-column">Trial</th>');
  const taskHeader = runDetailPage.indexOf("<th>Task</th>", trialHeader);
  assert.ok(trialHeader >= 0 && taskHeader > trialHeader);
  assert.match(runDetailPage, /buildExactTrialHref\(trial\.trial_id, sourceScopeSelection\.sourceScope\)/);
  assert.doesNotMatch(runDetailPage, /href=\{`\/trials\/\$\{encodeURIComponent\(trial\.trial_id\)\}/);
});

test("only exactly reproducible frozen arm-summary counts are linked", () => {
  for (const predicate of [
    'raw_outcome === "success" && row.execution_validity === "substantive"',
    'raw_outcome === "failure" && row.execution_validity === "substantive"',
    'policy_disposition === "provider_policy_refusal"',
    'termination_subtype === "timeout"',
    'termination_subtype === "setup_or_transport_exception"',
  ]) assert.ok(comprehensivePage.includes(predicate), predicate);
  for (const unsupported of [
    "<td>{arm.empty_completions}</td>",
    "<td>{arm.telemetry_mismatches}</td>",
    "<td>{arm.unknown_classifications}</td>",
    "<td>{arm.manual_review_queue}</td>",
  ]) assert.ok(comprehensivePage.includes(unsupported), unsupported);
});

test("source-surface wiring adds no mutation path", () => {
  const combined = [chartModel, overviewPage, costPage, crossPhasePage, runDetailPage, comprehensivePage]
    .join("\n").toLowerCase();
  for (const forbidden of ["fs.write", "writefile", "insert into", "update benchmark.", "delete from", "put_object"])
    assert.equal(combined.includes(forbidden), false, forbidden);
});
