import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sourceRoot = resolve(here, "..");

const component = await readFile(
  join(here, "SpendDecompositionPanel.tsx"),
  "utf8",
);

const page = await readFile(
  join(sourceRoot, "app/cost-coverage/page.tsx"),
  "utf8",
);

const css = await readFile(
  join(sourceRoot, "app/globals.css"),
  "utf8",
);

const model = await readFile(
  join(sourceRoot, "lib/spend-decomposition.ts"),
  "utf8",
);

test(
  "Cost Coverage builds DR-303 only from the validated frozen source and reviewed scope",
  () => {
    assert.match(
      page,
      /getSpendDecompositionSource/,
    );
    assert.match(
      page,
      /buildSpendDecompositionModel/,
    );
    assert.match(
      page,
      /selection\.scope/,
    );
    assert.match(
      page,
      /Frozen DR-303 source relationship failed closed/,
    );

    assert.match(
      component,
      /Spend decomposition unavailable\./,
    );
    assert.match(
      component,
      /No operational source is substituted\./,
    );
  },
);

test(
  "DR-303 follows reviewed headline metrics and precedes operational cost focus",
  () => {
    const metrics = page.indexOf(
      'className="metric-grid"',
    );
    const decomposition = page.indexOf(
      "\n      <SpendDecompositionPanel",
    );
    const focus = page.indexOf(
      'id="cost-provenance-focus"',
    );

    assert.ok(metrics >= 0);
    assert.ok(decomposition >= 0);
    assert.ok(focus >= 0);

    assert.ok(
      metrics < decomposition,
      "DR-303 must follow reviewed headline metrics",
    );
    assert.ok(
      decomposition < focus,
      "DR-303 must precede optional operational cost focus",
    );
  },
);

test(
  "stacked-dollar geometry uses one shared absolute arm-cost scale",
  () => {
    assert.match(
      component,
      /maxSelectedCost = Math\.max/,
    );
    assert.match(
      component,
      /geometryUsd\(arm\.selectedReviewedCostUsd\)/,
    );
    assert.match(
      component,
      /geometryUsd\(segment\.recordedCostUsd\)[\s\S]*\/ maxSelectedCost/,
    );
    assert.match(
      component,
      /geometryUsd\(arm\.accountingGapUsd\)[\s\S]*\/ maxSelectedCost/,
    );

    assert.doesNotMatch(
      component,
      /segment\.recordedCostUsd[\s\S]*\/ geometryUsd\(arm\.selectedReviewedCostUsd\)/,
    );
  },
);

test(
  "fixed legend and exact table retain all four recorded buckets plus the known gap",
  () => {
    assert.match(
      component,
      /SPEND_DECOMPOSITION_SEGMENTS\.map/,
    );

    for (const marker of [
      "Recorded clean-success spend",
      "Recorded normal-failure spend",
      "Recorded exception-failure spend",
      "Recorded exception-with-success-signal spend",
    ]) {
      assert.ok(
        model.includes(marker),
        `missing model-owned DR-303 category ${marker}`,
      );
    }

    assert.match(
      component,
      /\{segment\.label\}/,
    );
    assert.ok(
      component.includes("Known accounting gap"),
      "missing presentation-owned accounting-gap category",
    );

    assert.match(
      component,
      /not an outcome\s+classification/,
    );
    assert.match(
      component,
      /exceptionSuccess\.recordedCostUsd/,
    );
    assert.match(
      component,
      /exceptionSuccess\.missingRecordedCostCount/,
    );
  },
);

test(
  "decorative chart contains no focusable links while the exact table retains evidence links",
  () => {
    const chartStart = component.indexOf(
      'className="spend-decomposition-chart"',
    );
    const chartEnd = component.indexOf(
      '<p className="spend-decomposition-note">',
      chartStart,
    );

    assert.ok(chartStart >= 0);
    assert.ok(chartEnd > chartStart);

    const chart = component.slice(
      chartStart,
      chartEnd,
    );

    assert.match(
      component,
      /className="spend-decomposition-chart"\s+aria-hidden="true"/,
    );
    assert.doesNotMatch(
      chart,
      /<Link\b/,
    );

    assert.match(
      component,
      /links\.armEvidenceHref/,
    );
    assert.match(
      component,
      /links\?\.costProvenanceHref/,
    );
  },
);

test(
  "visible table exposes exact decimal values, counts, friendly labels, and canonical arm IDs",
  () => {
    assert.match(
      component,
      /<table className="spend-decomposition-table">/,
    );
    assert.match(
      component,
      /exactUsd\(segment\.recordedCostUsd\)/,
    );
    assert.match(
      component,
      /arm\.recordedCostUsd/,
    );
    assert.match(
      component,
      /arm\.accountingGapUsd/,
    );
    assert.match(
      component,
      /arm\.selectedReviewedCostUsd/,
    );
    assert.match(
      component,
      /friendlyArmLabel\(arm\.armId\)/,
    );
    assert.match(
      component,
      /className="muted mono">\{arm\.armId\}/,
    );
    assert.match(
      component,
      /segment\.trialCount/,
    );
    assert.match(
      component,
      /segment\.missingRecordedCostCount/,
    );
  },
);

test(
  "missing and unresolved evidence stay counts and Kimi allocation stays qualified",
  () => {
    for (const marker of [
      "arm.missingRecordedCostCount",
      "arm.unresolvedCostCount",
      "arm.costConfidence",
      "arm.pricingProvenanceStatus",
      "arm.armRunAllocationConfidence",
      "arm.trialAllocationStatus",
      "arm.outcomeCostAllocationStatus",
      "arm.billingReconciliationStatus",
    ]) {
      assert.ok(
        component.includes(marker),
        `missing evidence qualification ${marker}`,
      );
    }

    assert.match(
      component,
      /evidence counts, not dollar segments/,
    );
    assert.match(
      component,
      /provider-log remainder is not allocated to Kimi outcomes/,
    );
    assert.doesNotMatch(
      component,
      /unresolved.*\*.*100/i,
    );
  },
);

test(
  "DR-303 reuses only exact arm-level evidence links and invents no bucket deep link",
  () => {
    assert.match(
      page,
      /buildReviewedAggregateArmEvidenceHref/,
    );
    assert.match(
      page,
      /buildCostCoverageHref/,
    );
    assert.match(
      component,
      /links\.armEvidenceHref/,
    );
    assert.match(
      component,
      /links\?\.costProvenanceHref/,
    );

    assert.doesNotMatch(
      component,
      /exactArmValue\(\s*segment\.recordedCostUsd/,
    );
  },
);

test(
  "DR-303 presentation has dedicated responsive styles and five segment styles",
  () => {
    for (const selector of [
      ".spend-decomposition-panel",
      ".spend-decomposition-provenance",
      ".spend-decomposition-summary-grid",
      ".spend-decomposition-legend",
      ".spend-decomposition-chart",
      ".spend-decomposition-chart-row",
      ".spend-decomposition-track",
      ".spend-decomposition-table",
      ".spend-decomposition-boundary",
    ]) {
      assert.ok(
        css.includes(selector),
        `missing ${selector}`,
      );
    }

    for (const category of [
      "clean-success",
      "normal-failure",
      "exception-failure",
      "exception-with-success-signal",
      "accounting-gap",
    ]) {
      assert.ok(
        css.includes(
          `.spend-decomposition-segment-${category}`,
        ),
        `missing category style ${category}`,
      );
    }
  },
);

test(
  "DR-303 remains server-rendered and adds no chart dependency or interaction boundary",
  () => {
    assert.doesNotMatch(
      component,
      /"use client"/,
    );
    assert.doesNotMatch(
      component,
      /onClick=/,
    );
    assert.doesNotMatch(
      component,
      /\brecharts\b|\bd3\b|\bchart\.js\b|\bvega\b/i,
    );
  },
);
