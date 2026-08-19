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
const labelsSource = await readFile(join(here, "presentation-labels.ts"), "utf8");
const labelsCompiled = ts.transpileModule(labelsSource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const viewSource = await readFile(join(here, "cost-performance-chart-view.ts"), "utf8");
const viewCompiled = ts.transpileModule(viewSource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const source = await readFile(join(here, "cost-performance-chart.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText
  .replace(/^import .*;$/gm, "")
  .replace(/^export \* .*;$/gm, "");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(`
  const PHASE3_REVIEWED_COMPARISON = ${JSON.stringify(comparison)};
  const PHASE3_REVIEWED_RUN_SELECTION = ${JSON.stringify(runSelection)};
  const getReviewedPhase3Scope = (scopeId) => PHASE3_REVIEWED_COMPARISON.scopes[scopeId];
  const getReviewedRunSelectionScope = (scopeId) => PHASE3_REVIEWED_RUN_SELECTION.scopes[scopeId];
  const selectReviewedPhase3Scope = (value) => ({
    scopeId: value === "phase3-core" ? "phase3-core" : "phase3-extended",
    scope: getReviewedPhase3Scope(value === "phase3-core" ? "phase3-core" : "phase3-extended"),
    warning: null,
    warningMessage: null,
    usedDefault: value !== "phase3-core" && value !== "phase3-extended",
  });
  const buildExactRunHref = (runLabel, sourceScope) =>
    \`/runs/\${encodeURIComponent(runLabel)}?source_scope=\${sourceScope}\`;
  const buildCostCoverageHref = (scope, focus, sourceScope) => {
    const params = new URLSearchParams({ scope, arm_id: focus.armId, run_label: focus.runLabel, source_scope: sourceScope });
    return \`/cost-coverage?\${params.toString()}#cost-provenance-focus\`;
  };
  ${labelsCompiled}
  ${viewCompiled}
  ${compiled}
`).toString("base64")}`;
const chart = await import(moduleUrl);

const coreScope = comparison.scopes["phase3-core"];
const extendedScope = comparison.scopes["phase3-extended"];
const coreSelection = runSelection.scopes["phase3-core"];
const extendedSelection = runSelection.scopes["phase3-extended"];
const coreArmIds = coreScope.arms.map((arm) => arm.armId);
const coreArms = chart.buildCostPerformanceChartArms(coreScope, coreSelection, coreArmIds);
const extendedArms = chart.buildCostPerformanceChartArms(
  extendedScope,
  extendedSelection,
  coreArmIds,
);

function armFor(arms, armId) {
  const arm = arms.find((item) => item.armId === armId);
  assert.ok(arm, `missing chart arm ${armId}`);
  return arm;
}

function allProviders(arms) {
  return chart.selectAllProviderFamilies(chart.deriveProviderFilterOptions(arms));
}

function allArmIds(arms) {
  return chart.selectAllChartArmIds(arms);
}

function view(arms, metric, overrides = {}) {
  return chart.deriveCostPerformanceChartView({
    arms,
    metric,
    selectedProviderFamilies: allProviders(arms),
    selectedArmIds: allArmIds(arms),
    ...overrides,
  });
}

function point(armId, xValue, passRate) {
  return { arm: {}, armId, xValue, xDecimalUsd: String(xValue), passRate };
}

test("reviewed chart scopes contain exactly 15 core and 16 extended arms", () => {
  assert.equal(chart.DEFAULT_CHART_SCOPE, "phase3-extended");
  assert.equal(chart.getCostPerformanceChartArms().length, 16);
  assert.equal(chart.selectCostPerformanceChartScope(undefined).scopeId, "phase3-extended");
  assert.equal(coreArms.length, 15);
  assert.equal(extendedArms.length, 16);
  assert.equal(coreArms.some((arm) => arm.armId === "router-kimi-k3"), false);
  assert.equal(extendedArms.filter((arm) => arm.armId === "router-kimi-k3").length, 1);
  assert.deepEqual(
    extendedArms.filter((arm) => !coreArmIds.includes(arm.armId)).map((arm) => arm.armId),
    ["router-kimi-k3"],
  );
  assert.deepEqual(armFor(extendedArms, "router-kimi-k3").scopeMembership, ["phase3-extended"]);
  assert.deepEqual(
    armFor(extendedArms, "router-gpt-5.5").scopeMembership,
    ["phase3-core", "phase3-extended"],
  );
});

test("every datum resolves exactly one frozen G1 run without a latest-run fallback", () => {
  const selectedByArm = new Map(extendedSelection.selections.map((row) => [row.armId, row]));
  assert.equal(selectedByArm.size, extendedArms.length);
  for (const arm of extendedArms) {
    assert.equal(arm.selectedRunLabel, selectedByArm.get(arm.armId)?.selectedRunLabel);
    assert.equal(arm.selectedRunHref, `/runs/${encodeURIComponent(arm.selectedRunLabel)}?source_scope=phase3-extended`);
    const costUrl = new URL(arm.costProvenanceHref, "https://dashboard.invalid");
    assert.equal(costUrl.searchParams.get("scope"), "phase3-extended");
    assert.equal(costUrl.searchParams.get("arm_id"), arm.armId);
    assert.equal(costUrl.searchParams.get("run_label"), arm.selectedRunLabel);
    assert.equal(costUrl.searchParams.get("source_scope"), "phase3-extended");
    assert.equal(costUrl.hash, "#cost-provenance-focus");
  }
  const kimi = armFor(extendedArms, "router-kimi-k3");
  assert.equal(kimi.selectedRunLabel, "router-kimi-k3/2026-07-22__17-51-05");
  assert.equal(kimi.selectedRunHref, "/runs/router-kimi-k3%2F2026-07-22__17-51-05?source_scope=phase3-extended");
  assert.doesNotMatch(source, /latest[-_ ]run|getRecentRuns|latestRun/i);
});

test("pass-rate numerator and denominator remain exact reviewed counts", () => {
  const kimi = armFor(extendedArms, "router-kimi-k3");
  assert.equal(kimi.successCount, 47);
  assert.equal(kimi.trialCount, 60);
  assert.equal(kimi.passRate, 47 / 60);
  assert.equal(kimi.cleanSuccessCount, 44);
  const row = chart.buildAccessibleChartRows([kimi], "adjusted_cost_per_attempt")[0];
  assert.equal(row.successCount, 47);
  assert.equal(row.trialCount, 60);
  assert.equal(row.passRate, 47 / 60);
});

test("per-attempt costs use deterministic reviewed decimal division", () => {
  const kimi = armFor(extendedArms, "router-kimi-k3");
  assert.deepEqual(
    {
      status: kimi.recordedCostPerAttempt.status,
      decimalUsd: kimi.recordedCostPerAttempt.decimalUsd,
      sourceTotalUsd: kimi.recordedCostPerAttempt.sourceTotalUsd,
    },
    {
      status: "available",
      decimalUsd: "0.420120216666667",
      sourceTotalUsd: "25.207213",
    },
  );
  assert.equal(kimi.recordedCostPerAttempt.value, Number("0.420120216666667"));
});

test("Kimi adjusted metric preserves its qualified retained-rate basis", () => {
  const kimi = armFor(extendedArms, "router-kimi-k3");
  assert.equal(kimi.adjustedKnownCostUsd, null);
  assert.equal(kimi.qualifiedRetainedRateCostUsd, "30.8143194");
  assert.equal(kimi.reviewedComparableCostUsd, "30.8143194");
  assert.equal(kimi.costBasis, "qualified_retained_rate_estimate");
  assert.equal(kimi.adjustedCostPerAttempt.status, "available");
  assert.equal(kimi.adjustedCostPerAttempt.decimalUsd, "0.51357199");
  assert.match(kimi.adjustedCostPerAttempt.qualification, /qualified retained-rate estimate/);
  assert.match(kimi.adjustedCostPerAttempt.qualification, /not adjusted-known, invoice, provider-billed, or official-price/);
  assert.match(kimi.qualificationText, /pricing-source provenance incomplete/);
  assert.match(kimi.qualificationText, /trial allocation unresolved/);
});

test("unsupported Kimi outcome-cost metrics stay unavailable instead of becoming zero", () => {
  const kimi = armFor(extendedArms, "router-kimi-k3");
  const cleanSuccess = chart.metricValueForArm(kimi, "cost_per_clean_success");
  assert.equal(cleanSuccess.status, "unavailable");
  assert.equal(cleanSuccess.value, null);
  assert.match(cleanSuccess.reason, /not derived.*arithmetic convenience/);
  assert.equal(kimi.failureIncompleteSpend.status, "unavailable");
  assert.equal(kimi.failureIncompleteSpend.value, null);
  assert.match(kimi.failureIncompleteSpend.reason, /not treated as zero/);
  assert.equal(armFor(coreArms, "router-gpt-5.5").failureIncompleteSpend.status, "available");
});

test("provider options preserve canonical family keys with shared friendly presentation", () => {
  const kimiK2 = armFor(extendedArms, "router-kimi-k2.6");
  const kimiK3 = armFor(extendedArms, "router-kimi-k3");
  assert.equal(kimiK2.reviewedProvider, "moonshot-kimi");
  assert.equal(kimiK3.reviewedProvider, "moonshot");
  assert.equal(kimiK2.providerFamily, "moonshot-kimi");
  assert.equal(kimiK3.providerFamily, "moonshot-kimi");
  assert.equal(kimiK2.providerFamilyLabel, "Moonshot / Kimi");
  assert.equal(kimiK3.providerFamilyLabel, "Moonshot / Kimi");
  assert.equal(armFor(extendedArms, "router-gpt-5.5").displayName, "GPT-5.5");
  assert.equal(armFor(extendedArms, "router-glm-5.2").displayName, "GLM 5.2");
  assert.equal(
    armFor(extendedArms, "router-gemini-flash").displayName,
    "Gemini 3.5 Flash",
  );

  const options = chart.deriveProviderFilterOptions(extendedArms);
  assert.deepEqual(options.map((option) => option.providerFamily), [
    "anthropic",
    "dashscope-qwen",
    "deepseek",
    "google-gemini",
    "moonshot-kimi",
    "openai",
    "xai",
    "zai-glm",
  ]);
  assert.deepEqual(
    chart.deriveProviderFilterOptions([...extendedArms].reverse()),
    options,
  );
  assert.deepEqual(
    Object.fromEntries(
      options.map((option) => [option.providerFamily, option.label]),
    ),
    {
      anthropic: "Anthropic",
      "dashscope-qwen": "Alibaba / Qwen",
      deepseek: "DeepSeek",
      "google-gemini": "Google / Gemini",
      "moonshot-kimi": "Moonshot / Kimi",
      openai: "OpenAI",
      xai: "xAI / Grok",
      "zai-glm": "Z.AI / GLM",
    },
  );
  assert.equal(options.find((option) => option.providerFamily === "anthropic")?.armCount, 4);
  const moonshot = options.filter((option) => option.providerFamily === "moonshot-kimi");
  assert.equal(moonshot.length, 1);
  assert.deepEqual(moonshot[0], {
    providerFamily: "moonshot-kimi",
    label: "Moonshot / Kimi",
    armCount: 2,
  });
  assert.deepEqual(
    chart.filterProviderVisibleArms(extendedArms, ["moonshot-kimi"]).map((arm) => arm.armId),
    ["router-kimi-k2.6", "router-kimi-k3"],
  );
  const deepseek = chart.filterProviderVisibleArms(extendedArms, ["deepseek"]);
  assert.deepEqual(deepseek.map((arm) => arm.armId), [
    "router-deepseek-flash",
    "router-deepseek-pro",
  ]);
  assert.ok(deepseek.every((arm) => arm.reviewedProvider === "deepseek"));
  assert.equal(deepseek.some((arm) => arm.reviewedProvider === "openai"), false);
  assert.deepEqual(chart.filterProviderVisibleArms(extendedArms, []), []);
});

test("arm select-all and clear are independent from provider visibility", () => {
  assert.equal(chart.selectAllChartArmIds(extendedArms).length, 16);
  assert.deepEqual(chart.clearChartArmIds(), []);
  assert.equal(chart.selectAllProviderFamilies(chart.deriveProviderFilterOptions(extendedArms)).length, 8);
  assert.deepEqual(chart.clearProviderFamilies(), []);

  const selectedIds = allArmIds(extendedArms);
  const noProviders = view(extendedArms, "adjusted_cost_per_attempt", {
    selectedProviderFamilies: [],
    selectedArmIds: selectedIds,
  });
  assert.deepEqual(noProviders.selectedArmIds, selectedIds);
  assert.equal(noProviders.providerVisibleArms.length, 0);
  assert.equal(noProviders.plotPoints.length, 0);

  const noArms = view(extendedArms, "adjusted_cost_per_attempt", {
    selectedProviderFamilies: allProviders(extendedArms),
    selectedArmIds: [],
  });
  assert.equal(noArms.providerVisibleArms.length, 16);
  assert.equal(noArms.selectedVisibleArms.length, 0);
  assert.equal(noArms.plotPoints.length, 0);
});

test("a selected metric-unavailable arm remains represented but is not plotted", () => {
  const result = view(extendedArms, "cost_per_clean_success", {
    selectedProviderFamilies: ["moonshot-kimi"],
    selectedArmIds: ["router-kimi-k3"],
  });
  assert.deepEqual(result.selectedArmIds, ["router-kimi-k3"]);
  assert.deepEqual(result.selectedVisibleArms.map((arm) => arm.armId), ["router-kimi-k3"]);
  assert.equal(result.plotPoints.length, 0);
  assert.deepEqual(result.unavailableMetricArms.map((arm) => arm.armId), ["router-kimi-k3"]);
  const accessible = chart.buildAccessibleChartRows(
    result.selectedVisibleArms,
    "cost_per_clean_success",
  );
  assert.equal(accessible[0].xMetricValue.status, "unavailable");
  assert.match(accessible[0].xMetricValue.reason, /reviewed F1 contract/);
});

test("Pareto frontier uses lower cost and higher pass rate dominance", () => {
  const frontier = chart.deriveParetoFrontier([
    point("middle-dominated", 2, 0.4),
    point("cheap", 1, 0.5),
    point("strong", 2, 0.7),
    point("expensive-dominated", 3, 0.7),
  ]);
  assert.deepEqual(frontier.map((item) => item.armId), ["cheap", "strong"]);
});

test("identical and near-equal points do not falsely dominate one another", () => {
  const identical = chart.deriveParetoFrontier([
    point("tie-b", 1, 0.5),
    point("tie-a", 1, 0.5),
  ]);
  assert.deepEqual(identical.map((item) => item.armId), ["tie-a", "tie-b"]);

  const nearEqual = chart.deriveParetoFrontier([
    point("near-a", 1, 0.5),
    point("near-b", 1 + chart.PARETO_FLOAT_TOLERANCE / 2, 0.5),
  ]);
  assert.deepEqual(nearEqual.map((item) => item.armId), ["near-a", "near-b"]);
});

test("Pareto result is invariant to input order", () => {
  const points = [
    point("a", 1, 0.5),
    point("b", 2, 0.4),
    point("c", 2, 0.7),
    point("d", 3, 0.8),
  ];
  const forward = chart.deriveParetoFrontier(points).map((item) => item.armId);
  const reverse = chart.deriveParetoFrontier([...points].reverse()).map((item) => item.armId);
  assert.deepEqual(forward, reverse);
});

test("scope, provider, arm selection, and x metric recalculate the frontier", () => {
  const core = view(coreArms, "adjusted_cost_per_attempt");
  const extended = view(extendedArms, "adjusted_cost_per_attempt");
  assert.notDeepEqual(
    core.frontier.map((item) => item.armId),
    extended.frontier.map((item) => item.armId),
  );
  assert.ok(extended.frontier.some((item) => item.armId === "router-kimi-k3"));

  const anthropicOnly = view(extendedArms, "adjusted_cost_per_attempt", {
    selectedProviderFamilies: ["anthropic"],
  });
  assert.ok(anthropicOnly.frontier.every((item) => item.arm.providerFamily === "anthropic"));
  assert.notDeepEqual(
    anthropicOnly.frontier.map((item) => item.armId),
    extended.frontier.map((item) => item.armId),
  );

  const removedFrontierArm = extended.frontier[0].armId;
  const withoutOne = view(extendedArms, "adjusted_cost_per_attempt", {
    selectedArmIds: allArmIds(extendedArms).filter((armId) => armId !== removedFrontierArm),
  });
  assert.equal(withoutOne.frontier.some((item) => item.armId === removedFrontierArm), false);
  assert.notDeepEqual(
    withoutOne.frontier.map((item) => item.armId),
    extended.frontier.map((item) => item.armId),
  );

  const cleanSuccess = view(extendedArms, "cost_per_clean_success");
  assert.notDeepEqual(
    cleanSuccess.frontier.map((item) => item.armId),
    extended.frontier.map((item) => item.armId),
  );
});

test("accessible rows retain confidence, gap, qualifications, and both evidence links", () => {
  const kimi = chart.buildAccessibleChartRows(
    [armFor(extendedArms, "router-kimi-k3")],
    "adjusted_cost_per_attempt",
  )[0];
  assert.equal(kimi.costConfidence, "low");
  assert.equal(kimi.reviewedProvider, "moonshot");
  assert.equal(kimi.providerFamily, "moonshot-kimi");
  assert.equal(kimi.providerFamilyLabel, "Moonshot / Kimi");
  assert.deepEqual(kimi.costSources, [
    "provider_log_retained_rate_reconstruction",
    "recorded_trial_artifact",
  ]);
  assert.equal(kimi.armRunAllocationConfidence, "low");
  assert.equal(kimi.providerLogExclusivityStatus, "not_proven");
  assert.equal(kimi.accountingGapUsd, "5.6071064");
  assert.equal(kimi.failureIncompleteSpend.status, "unavailable");
  assert.match(kimi.qualificationText, /not invoice-level or provider-billed spend/);
  assert.equal(kimi.armHref, "/trial-quality?arm_id=router-kimi-k3");
  assert.equal(kimi.selectedRunHref, "/runs/router-kimi-k3%2F2026-07-22__17-51-05?source_scope=phase3-extended");
  assert.match(kimi.costProvenanceHref, /scope=phase3-extended/);
  assert.match(kimi.costProvenanceHref, /arm_id=router-kimi-k3/);
  assert.match(kimi.costProvenanceHref, /run_label=router-kimi-k3%2F2026-07-22__17-51-05/);
  assert.match(kimi.costProvenanceHref, /#cost-provenance-focus$/);
});

test("x-axis validation defaults deterministically and accepts only the reviewed metric set", () => {
  assert.deepEqual(chart.selectChartXAxisMetric(undefined), {
    metric: "adjusted_cost_per_attempt",
    warning: null,
    warningMessage: null,
    usedDefault: true,
  });
  assert.equal(chart.selectChartXAxisMetric("cost_per_clean_success").metric, "cost_per_clean_success");
  assert.equal(chart.selectChartXAxisMetric("not-a-metric").warning, "invalid_metric");
  assert.equal(chart.selectChartXAxisMetric(["recorded_cost_per_attempt"]).warning, "repeated_metric");
});
