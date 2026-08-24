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
  "Cost Coverage makes current selected cost primary while preserving the historical DR-303 model",
  () => {
    assert.match(
      page,
      /PHASE3_CURRENT_REVIEWED_COMPARISON/,
    );
    assert.match(
      page,
      /getCurrentReviewedPhase3Scope/,
    );
    assert.match(
      page,
      /currentScope\.selectedCostEvidence\.selectedCostUsd/,
    );
    assert.match(
      page,
      /Current best-supported arm cost evidence/,
    );
    assert.match(
      page,
      /Current best-supported cost by arm/,
    );
    assert.match(
      page,
      /currentCostNumber\(arm\.selectedCostUsd\)/,
    );
    assert.match(
      page,
      /maxCurrentArmCost/,
    );
    assert.match(
      page,
      /historical-cost-details/,
    );
    assert.match(
      page,
      /Historical DR-303 reconstruction and superseded benchmark-side estimates/,
    );
    assert.match(
      page,
      /not\s+redistributed into historical trial or outcome buckets/,
    );

    assert.doesNotMatch(
      model,
      /phase3-current-reviewed-comparison/,
    );
    assert.doesNotMatch(
      model,
      /providerBilledCostUsd/,
    );
  },
);

test(
  "primary arm table is current-only and historical outcome rows are collapsed",
  () => {
    assert.match(page, /Current best-supported arm cost evidence/);
    assert.match(page, /Current best-supported cost/);
    assert.match(page, /Evidence basis \/ confidence/);
    assert.match(page, /Historical outcome-cost rows \(provenance only\)/);
    assert.doesNotMatch(page, /Current selected and historical arm cost evidence/);
    assert.doesNotMatch(page, /<th>Historical reviewed cost<\/th>/);
    assert.doesNotMatch(page, /<th>Historical failure spend<\/th>/);
  },
);

test(
  "current cost chart precedes collapsed DR-303 history and operational cost focus",
  () => {
    const metrics = page.indexOf(
      'className="metric-grid"',
    );
    const currentChart = page.indexOf(
      'id="current-cost-by-arm"',
    );
    const decomposition = page.indexOf(
      "<SpendDecompositionPanel",
    );
    const focus = page.indexOf(
      'id="cost-provenance-focus"',
    );

    assert.ok(metrics >= 0);
    assert.ok(currentChart >= 0);
    assert.ok(decomposition >= 0);
    assert.ok(focus >= 0);

    assert.ok(
      metrics < currentChart,
      "current cost chart must follow current headline metrics",
    );
    assert.ok(
      currentChart < decomposition,
      "current cost chart must precede historical DR-303",
    );
    assert.ok(
      decomposition < focus,
      "historical DR-303 must precede optional operational cost focus",
    );
  },
);

test(
  "primary current-cost chart outer geometry uses current selected arm cost",
  () => {
    assert.match(
      page,
      /const currentCost = currentCostNumber\(\s*arm\.selectedCostUsd,\s*\)/,
    );
    assert.match(
      page,
      /const width =\s*\(currentCost \/ maxCurrentArmCost\) \* 100/,
    );
    assert.match(
      page,
      /className="current-cost-fill"/,
    );
  },
);

test(
  "current chart introduction describes generalized reconciliation rather than provider billing only",
  () => {
    assert.match(
      page,
      /Current reconciled evidence replaces superseded/,
    );
    assert.match(
      page,
      /exact, estimated, lower-bound, or historical fallback/,
    );
    assert.doesNotMatch(
      page,
      /Exact provider-billed totals replace superseded/,
    );
  },
);

test(
  "hybrid current bars separate current geometry from allocation evidence",
  () => {
    assert.match(
      page,
      /const currentCost = currentCostNumber\([\s\S]*arm\.selectedCostUsd/,
    );
    assert.match(
      page,
      /const width =[\s\S]*currentCost[\s\S]*\/ maxCurrentArmCost[\s\S]*\* 100/,
    );
    assert.match(
      page,
      /className="current-cost-fill"[\s\S]*style=\{\{ width: `\$\{width\}%` \}\}/,
    );
    assert.match(
      page,
      /currentCostNumber\([\s\S]*segment\.amountUsd[\s\S]*\/ currentCost/,
    );

    assert.match(
      page,
      /available_provider_rate_reconstruction/,
    );
    assert.match(
      page,
      /available_lower_bound/,
    );
    assert.match(
      page,
      /selectedCleanSuccessCostUsd/,
    );
    assert.match(
      page,
      /selectedNormalFailureCostUsd/,
    );
    assert.match(
      page,
      /selectedExceptionFailureCostUsd/,
    );
    assert.match(
      page,
      /selectedExceptionWithSuccessSignalCostUsd/,
    );
  },
);

test(
  "historical fallback colors require exact DR-303 compatibility",
  () => {
    assert.match(
      page,
      /arm\.selectedCostRelation !== "historical_fallback"/,
    );
    assert.match(
      page,
      /historicalArm\.outcomeCostAllocationStatus !== "available"/,
    );
    assert.match(
      page,
      /historicalArm\.selectedReviewedCostUsd !== arm\.selectedCostUsd/,
    );
    assert.match(
      page,
      /historical DR-303 allocation · selected historical fallback matches exactly/,
    );
  },
);

test(
  "aggregate-only and lower-bound uncertainty never fabricate outcome dollars",
  () => {
    assert.match(
      page,
      /Aggregate cost — outcome split unavailable/,
    );
    assert.match(
      page,
      /possible_additional_exception_path_spend/,
    );
    assert.match(
      page,
      /possible additional exception-path spend is not quantified/,
    );
    assert.match(
      page,
      /Possible additional lower-bound spend is labeled but never assigned invented geometry/,
    );

    assert.doesNotMatch(
      page,
      /providerContextExcessUsd[\s\S]*current-cost-segment/,
    );
  },
);

test(
  "current hybrid chart reuses outcome colors and adds a neutral allocation state",
  () => {
    assert.match(
      page,
      /spend-decomposition-segment-\$\{id\.replaceAll\("_", "-"\)\}/,
    );
    assert.match(
      page,
      /current-cost-segment-unallocated/,
    );
    assert.match(
      css,
      /\.current-cost-fill[\s\S]*display: flex/,
    );
    assert.match(
      css,
      /\.current-cost-segment-unallocated/,
    );
    assert.match(
      css,
      /\.current-cost-legend/,
    );
  },
);

test(
  "historical DR-303 stacked-dollar geometry keeps its frozen absolute scale",
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
  "historical DR-303 values are explicitly labeled as historical provenance",
  () => {
    assert.match(component, /Historical DR-303 outcome-cost reconstruction/);
    assert.match(component, /Historical DR-303 reviewed scope estimate/);
    assert.match(component, /Historical DR-303 reviewed estimate/);
    assert.doesNotMatch(component, /Selected reviewed scope cost/);
    assert.doesNotMatch(component, />Selected reviewed cost</);
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
      ".current-cost-panel",
      ".current-cost-chart",
      ".current-cost-chart-row",
      ".current-cost-track",
      ".current-cost-fill",
      ".historical-cost-details",
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

test(
  "DR-303 historical model cannot consume current selected provider fields",
  () => {
    for (const forbidden of [
      /phase3-current-reviewed-comparison/,
      /\bproviderBilledCostUsd\b/,
      /\bselectedCostUsd\b/,
      /\bselectedOutcomeCostAllocationStatus\b/,
      /\bselectedTrialCostAllocationStatus\b/,
      /\bproviderBillingReconciliationStatus\b/,
    ]) {
      assert.doesNotMatch(model, forbidden);
    }

    assert.match(
      model,
      /phase3-reviewed-comparison/,
    );
  },
);
