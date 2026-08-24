import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(here, "../..");
const repositoryRoot = resolve(dashboardRoot, "../..");
const componentSource = await readFile(join(here, "CostPerformanceChart.tsx"), "utf8");
const tableSource = await readFile(join(here, "CostPerformanceChartTable.tsx"), "utf8");
const pageSource = await readFile(resolve(here, "../app/page.tsx"), "utf8");
const packageSource = await readFile(resolve(dashboardRoot, "package.json"), "utf8");
const viewSource = await readFile(
  resolve(here, "../lib/cost-performance-chart-view.ts"),
  "utf8",
);
const geometrySource = await readFile(
  resolve(here, "../lib/cost-performance-chart-geometry.ts"),
  "utf8",
);
const geometryCompiled = ts.transpileModule(geometrySource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const geometry = await import(
  `data:text/javascript;base64,${Buffer.from(geometryCompiled).toString("base64")}`
);

function assertFiniteDomain(domain) {
  assert.equal(domain.length, 2);
  assert.ok(domain.every(Number.isFinite));
  assert.ok(domain[0] < domain[1]);
}

test("scale geometry handles empty, single, identical, tiny, and large domains", () => {
  assert.deepEqual(geometry.paddedLinearDomain([]), [0, 1]);

  for (const values of [[0.42], [0.42, 0.42], [0.0000012, 0.0000013], [1_000, 5_000]]) {
    const domain = geometry.paddedLinearDomain(values, { minimumPadding: 1e-9 });
    assertFiniteDomain(domain);
    const position = geometry.linearScale(domain, [80, 920]);
    for (const value of values) assert.ok(Number.isFinite(position(value)));
  }

  const positiveDomain = geometry.paddedLinearDomain([0.0000012]);
  assert.ok(positiveDomain[0] > 0, "zero is not injected for a positive reviewed value");
  const passRateDomain = geometry.paddedLinearDomain([1], {
    minimumPadding: 0.01,
    clampMinimum: 0,
    clampMaximum: 1,
  });
  assert.deepEqual(passRateDomain, [0.92, 1]);
  assert.ok(geometry.linearTicks(passRateDomain, 5).every(Number.isFinite));
});

test("invalid geometry inputs cannot produce NaN or Infinity SVG coordinates", () => {
  assert.throws(() => geometry.paddedLinearDomain([Number.NaN]), /must be finite/);
  assert.throws(() => geometry.paddedLinearDomain([Number.POSITIVE_INFINITY]), /must be finite/);
  assert.throws(() => geometry.linearScale([1, 1], [0, 100]), /must increase/);
  const scale = geometry.linearScale([1, 2], [0, 100]);
  assert.throws(() => scale(Number.NaN), /must be finite/);
});

test("Overview constructs the chart from current-reviewed cost scope and frozen run evidence on the server", () => {
  assert.match(pageSource, /chart_scope\?: string \| string\[\]/);
  assert.match(pageSource, /selectCostPerformanceChartScope\(query\.chart_scope\)/);
  assert.doesNotMatch(pageSource, /selectCostPerformanceChartScope\(query\.scope\)/);
  assert.match(pageSource, /getCostPerformanceChartArms\(chartScopeSelection\.scopeId\)/);
  assert.match(pageSource, /deriveProviderFilterOptions\(chartArms\)/);
  assert.match(pageSource, /key=\{chartScopeSelection\.scopeId\}/);
  assert.match(pageSource, /scopeWarningMessage=\{chartScopeSelection\.warningMessage\}/);
  assert.match(pageSource, /getCurrentReviewedPhase3Scope\("phase3-extended"\)/);
  assert.match(pageSource, /getReviewedRunSelectionScope\("phase3-extended"\)/);
  assert.match(pageSource, /getReviewedSelectedRunLabels\("phase3-extended"\)/);
  assert.ok(
    pageSource.indexOf("Reviewed full-suite comparison") < pageSource.indexOf("<CostPerformanceChart"),
    "chart follows the reviewed leaderboard",
  );
  assert.ok(
    pageSource.indexOf("<CostPerformanceChart") < pageSource.indexOf("Different population below"),
    "chart precedes the dynamic-population boundary",
  );
});

test("chart scope is explicit URL state and preserves unrelated parameters", () => {
  assert.match(componentSource, /new URLSearchParams\(window\.location\.search\)/);
  assert.match(componentSource, /parameters\.set\("chart_scope", nextScope\)/);
  assert.doesNotMatch(componentSource, /parameters\.set\("scope", nextScope\)/);
  assert.match(componentSource, /<legend>Reviewed chart scope<\/legend>/);
  assert.match(componentSource, /value="phase3-extended"/);
  assert.match(componentSource, /value="phase3-core"/);
});

test("client-boundary modules import only the pure chart view layer", () => {
  assert.match(componentSource, /from "\.\.\/lib\/cost-performance-chart-view"/);
  assert.doesNotMatch(componentSource, /from "\.\.\/lib\/cost-performance-chart"/);
  assert.match(tableSource, /from "\.\.\/lib\/cost-performance-chart-view"/);
  assert.doesNotMatch(tableSource, /from "\.\.\/lib\/cost-performance-chart"/);
  for (const forbiddenReference of [
    "phase3-reviewed-comparison",
    "phase3-current-reviewed-comparison",
    "phase3-reviewed-run-selection",
    "overview-reviewed-comparison",
    "generated/",
  ]) {
    assert.doesNotMatch(viewSource, new RegExp(forbiddenReference));
  }
  assert.match(
    viewSource,
    /import type \{\s*CurrentSelectedCostRelation,\s*\} from "\.\/current-cost-relation";/,
  );
  assert.doesNotMatch(
    viewSource,
    /^import(?!\s+type\b)\s/m,
  );

  const viewImports = [
    ...viewSource.matchAll(/^import[\s\S]*?;$/gm),
  ].map((match) => match[0]);

  assert.deepEqual(
    viewImports,
    [
      [
        "import type {",
        "  CurrentSelectedCostRelation,",
        '} from "./current-cost-relation";',
      ].join("\n"),
    ],
  );
});

test("the client delegates metric eligibility and frontier policy to H1", () => {
  assert.match(componentSource, /deriveCostPerformanceChartView\(\{/);
  assert.match(componentSource, /metricValueForArm\(arm, xMetric\)/);
  assert.match(componentSource, /view\.frontier\.map/);
  assert.match(componentSource, /data-frontier-arm-ids=\{view\.frontier/);
  assert.doesNotMatch(componentSource, /deriveParetoFrontier|function dominates|candidate\.xValue/);
  assert.match(viewSource, /export function deriveParetoFrontier/);
  assert.match(viewSource, /function dominates/);
  assert.doesNotMatch(componentSource, /cleanSuccessCount\s*[)/]/);
  assert.match(componentSource, /DEFAULT_CHART_X_AXIS_METRIC/);
  assert.match(componentSource, /CHART_X_AXIS_OPTIONS\.map/);
});

test("provider and arm controls preserve independent selection semantics", () => {
  assert.match(componentSource, /selectAllProviderFamilies\(providerOptions\)/);
  assert.match(componentSource, /clearProviderFamilies\(\)/);
  assert.match(componentSource, /selectAllChartArmIds\(arms\)/);
  assert.match(componentSource, /clearChartArmIds\(\)/);
  const toggleProvider = componentSource.split("function toggleProvider", 2)[1]
    .split("function toggleArm", 1)[0];
  assert.doesNotMatch(toggleProvider, /setSelectedArmIds/);
  assert.match(componentSource, /providerColor\(point\.arm\.providerFamily\)/);
  assert.match(componentSource, /providerColor\(option\.providerFamily\)/);
  assert.doesNotMatch(componentSource, /providerColor\([^)]*reviewedProvider/);
  assert.equal((componentSource.match(/"moonshot-kimi": "#62d98b"/g) ?? []).length, 1);
});

test("points and controls expose keyboard interaction and persistent evidence details", () => {
  for (const required of (
    [
      'role="button"',
      "tabIndex={0}",
      'event.key === "Enter"',
      'event.key === " "',
      "onFocus={() => activatePoint(point.armId)}",
      "onMouseEnter={() => activatePoint(point.armId)}",
      "Arm evidence →",
      "Frozen selected-run evidence →",
      "costProvenanceHref",
      "successes",
      "Historical reviewed accounting gap",
      "Historical pricing provenance",
      "Provider billing reconciliation",
      "Provider-log exclusivity",
      "Failure / incomplete spend",
    ]
  )) assert.ok(componentSource.includes(required), `missing ${required}`);

  assert.match(componentSource, /Qualified retained-rate estimate — not adjusted-known, invoice, or provider-billed cost/);
  assert.match(componentSource, /Pricing provenance is incomplete; allocation confidence is low; trial allocation is unresolved; provider-log exclusivity is not proven/);
  assert.match(componentSource, /Exact provider-billed arm total — current decision-oriented cost basis/);
  assert.match(componentSource, /historical adjusted-cost evidence remains separate and is not reallocated/i);
  assert.match(componentSource, /Selected cost total/);
  assert.match(componentSource, /Historical reviewed cost total/);
  assert.match(tableSource, /Selected total/);
  assert.match(tableSource, /Historical reviewed total/);
  assert.match(componentSource, /cost-performance-point-qualified/);
});

test("SVG title is one computed string rather than mixed React children", () => {
  assert.match(
    componentSource,
    /<title id="cost-performance-svg-title">\{`\$\{selectedMetricLabel\} against reviewed pass rate`\}<\/title>/,
  );
  assert.doesNotMatch(
    componentSource,
    /<title id="cost-performance-svg-title">\{selectedMetricLabel\} against reviewed pass rate<\/title>/,
  );
});

test("metric-unavailable arms remain explicit in the visible evidence table", () => {
  assert.match(componentSource, /view\.unavailableMetricArms\.map/);
  assert.match(componentSource, /arms=\{view\.selectedVisibleArms\}/);
  assert.match(componentSource, /Unavailable —/);
  assert.match(componentSource, /Selected but unavailable for/);
  assert.match(componentSource, /No provider families are enabled\./);
  assert.match(componentSource, /No arms are selected\./);
  assert.match(componentSource, /One eligible point is visible; no frontier segment is drawn\./);
  assert.match(componentSource, /Skip to non-hover evidence table/);
});

test("H2 adds no chart package and retains protected reviewed input bytes", async () => {
  const packageJson = JSON.parse(packageSource);
  assert.equal(packageJson.dependencies.d3, undefined);
  assert.equal(packageJson.dependencies.recharts, undefined);
  assert.equal(packageJson.dependencies.plotly, undefined);
  assert.equal(packageJson.dependencies.vega, undefined);

  const expectedHashes = new Map([
    ["results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json", "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"],
    ["apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts", "51963cf066c74c7af7819ebead5c0c06e70852028f87d7be5535424299bda068"],
    ["results/phase3/reporting/phase3_reviewed_run_selection_20260809.json", "5f551c62833adc8a5220ffd7390a5cd50a8f483109536c65b831b66fcd6cf181"],
    ["apps/dashboard/src/generated/phase3-reviewed-run-selection-data.ts", "8cc74625cbfabc5ef8d1822af3b9b2f36672ae0364aac4751e09de54d1d97776"],
  ]);
  for (const [path, expectedHash] of expectedHashes) {
    const contents = await readFile(resolve(repositoryRoot, path));
    assert.equal(createHash("sha256").update(contents).digest("hex"), expectedHash, path);
  }
});
