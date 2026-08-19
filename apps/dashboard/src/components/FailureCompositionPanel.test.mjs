import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sourceRoot = resolve(here, "..");

const component = await readFile(
  join(here, "FailureCompositionPanel.tsx"),
  "utf8",
);
const page = await readFile(
  join(sourceRoot, "app/trial-quality/page.tsx"),
  "utf8",
);
const css = await readFile(
  join(sourceRoot, "app/globals.css"),
  "utf8",
);

test("Trial Quality uses the validated J2 reviewed-source accessor for DR-302", () => {
  assert.match(
    page,
    /getFailureTaxonomyReviewedSource/,
  );
  assert.match(
    page,
    /buildFailureCompositionModel/,
  );
  assert.doesNotMatch(
    page,
    /getComprehensiveReviewData/,
  );
});

test("failure composition fails closed without operational substitution", () => {
  assert.match(
    page,
    /Failure composition failed closed because the validated frozen source relationship did not satisfy the DR-302 contract/,
  );
  assert.match(
    component,
    /Failure composition unavailable\./,
  );
  assert.match(
    component,
    /No operational source is substituted\./,
  );
});

test("DR-302 panel exposes exact denominator exclusions and residual semantics", () => {
  assert.match(component, /model\.rawFailureCount/);
  assert.match(component, /model\.successCount/);
  assert.match(component, /model\.notRecordedCount/);
  assert.match(
    component,
    /model\.successfulTimeoutAfterMeaningfulActivityCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.evidenceCompleteCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.evidenceIncompleteCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.highConfidenceCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.mediumConfidenceCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.noSubstantiveAttemptCount/,
  );
  assert.match(
    component,
    /model\.residualBreakdown\.indeterminateCount/,
  );
  assert.match(component, /no_substantive_attempt/);
  assert.match(component, /indeterminate/);
  assert.doesNotMatch(
    component,
    /evidence-complete, high-confidence/,
  );
});

test("stacked bars use one shared raw-failure count scale", () => {
  assert.match(
    component,
    /maxRawFailures = Math\.max/,
  );
  assert.match(
    component,
    /\(category\.count \/ maxRawFailures\) \* 100/,
  );
  assert.doesNotMatch(
    component,
    /category\.shareOfRawFailures \* 100/,
  );
});

test("visual chart is decorative and the exact accessible table remains visible", () => {
  assert.match(
    component,
    /className="failure-composition-chart"\s+aria-hidden="true"/,
  );
  assert.match(
    component,
    /<table className="failure-composition-table">/,
  );
  assert.match(
    component,
    /Shares use each arm&apos;s raw-failure count/,
  );
  assert.match(
    component,
    /category\.shareOfRawFailures/,
  );
  assert.match(
    component,
    /friendlyArmLabel\(arm\.armId\)/,
  );
  assert.match(
    component,
    /className="muted mono">\{arm\.armId\}/,
  );
});

test("frozen taxonomy precedes DR-302 composition and both precede operational quality sections", () => {
  const taxonomySection = page.indexOf(
    'id="failure-taxonomy"',
  );
  const compositionPanel = page.indexOf(
    "\n      <FailureCompositionPanel",
  );
  const invalidRuns = page.indexOf(
    'id="invalid-runs"',
  );

  assert.ok(taxonomySection >= 0);
  assert.ok(compositionPanel >= 0);
  assert.ok(invalidRuns >= 0);

  assert.ok(
    taxonomySection < compositionPanel,
    "failure composition must follow the frozen taxonomy",
  );
  assert.ok(
    compositionPanel < invalidRuns,
    "failure composition must remain before operational sections",
  );

  const taxonomyNav = page.indexOf(
    'href: "#failure-taxonomy"',
  );
  const compositionNav = page.indexOf(
    'href: "#failure-composition"',
  );

  assert.ok(taxonomyNav >= 0);
  assert.ok(compositionNav >= 0);
  assert.ok(
    taxonomyNav < compositionNav,
    "local navigation should match rendered section order",
  );
});

test("Trial Quality adds local navigation and stable section anchors", () => {
  assert.match(page, /import \{ SectionNav \}/);
  for (const marker of [
    '#failure-composition',
    '#failure-taxonomy',
    '#invalid-runs',
    '#interpretation-policy',
    '#quality-definitions',
    '#arm-run-summary',
    '#suspect-noop-trials',
  ]) {
    assert.ok(
      page.includes(marker),
      `missing section-nav marker ${marker}`,
    );
  }

  for (const id of [
    'id="invalid-runs"',
    'id="interpretation-policy"',
    'id="quality-definitions"',
    'id="arm-run-summary"',
  ]) {
    assert.ok(page.includes(id), `missing section id ${id}`);
  }
});

test("DR-302 presentation has dedicated responsive styles and seven segment styles", () => {
  for (const selector of [
    ".failure-composition-panel",
    ".failure-composition-provenance",
    ".failure-composition-summary-grid",
    ".failure-composition-legend",
    ".failure-composition-chart",
    ".failure-composition-chart-row",
    ".failure-composition-track",
    ".failure-composition-table",
    ".failure-composition-boundary",
  ]) {
    assert.ok(css.includes(selector), `missing ${selector}`);
  }

  for (const category of [
    "verifier-task-failure",
    "timeout-after-meaningful-activity",
    "provider-policy-refusal",
    "invalid-response-path",
    "missing-required-output",
    "extraneous-output-artifacts",
    "unknown-or-incomplete-evidence",
  ]) {
    assert.ok(
      css.includes(
        `.failure-composition-segment-${category}`,
      ),
      `missing category style ${category}`,
    );
  }
});

test("DR-302 panel adds no category deep link or client-side chart boundary", () => {
  assert.doesNotMatch(component, /from "next\/link"/);
  assert.doesNotMatch(component, /"use client"/);
  assert.doesNotMatch(component, /onClick=/);
  assert.doesNotMatch(component, /href=/);
});
