import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here =
  dirname(fileURLToPath(import.meta.url));

const snapshot = JSON.parse(
  await readFile(
    resolve(
      here,
      "../../../../results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json",
    ),
    "utf8",
  ),
);

const source = await readFile(
  join(here, "cross-phase-reporting.ts"),
  "utf8",
);

const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl =
  `data:text/javascript;base64,${
    Buffer.from(compiled).toString("base64")
  }`;

const {
  getBehaviorRows,
  getCrossPhaseRows,
  getCurrentReviewedPhase3Rows,
  getPhaseSummaries,
  getRouterComparisonRows,
} = await import(moduleUrl);

const core = snapshot.scopes["phase3-core"];
const extended =
  snapshot.scopes["phase3-extended"];

test(
  "current-reviewed scope replaces only Phase 3 cross-phase rows",
  () => {
    const coreRows = getCrossPhaseRows(core);
    const extendedRows =
      getCrossPhaseRows(extended);

    assert.equal(
      coreRows.filter(
        (row) => row.phase === "phase1",
      ).length,
      3,
    );
    assert.equal(
      coreRows.filter(
        (row) => row.phase === "phase2",
      ).length,
      5,
    );
    assert.equal(
      coreRows.filter(
        (row) => row.phase === "phase3",
      ).length,
      15,
    );
    assert.equal(
      extendedRows.filter(
        (row) => row.phase === "phase3",
      ).length,
      16,
    );

    assert.equal(
      coreRows.some(
        (row) =>
          row.arm_id === "router-kimi-k3",
      ),
      false,
    );
    assert.equal(
      extendedRows.some(
        (row) =>
          row.arm_id === "router-kimi-k3",
      ),
      true,
    );

    const phase1 = coreRows.find(
      (row) => row.arm_id === "arm-a-anthropic",
    );
    assert.ok(phase1);
    assert.equal(
      phase1.comparison_cost_usd,
      37.29553755,
    );
    assert.equal(
      phase1.comparison_cost_layer,
      "frozen_historical_baseline",
    );
  },
);

test(
  "OpenAI rows use exact provider-selected cost while historical allocation stays separate",
  () => {
    const rows =
      getCurrentReviewedPhase3Rows(extended);

    const gpt54 = rows.find(
      (row) =>
        row.arm_id === "router-gpt-5.4",
    );
    const gpt55 = rows.find(
      (row) =>
        row.arm_id === "router-gpt-5.5",
    );

    assert.ok(gpt54);
    assert.ok(gpt55);

    assert.equal(
      gpt54.comparison_cost_usd,
      29.7919335,
    );
    assert.equal(
      gpt54.comparison_cost_per_clean_success_usd,
      0.78399825,
    );
    assert.equal(
      gpt54.historical_reviewed_cost_usd,
      183.646689146806,
    );
    assert.equal(
      gpt54.historical_unclean_spend_share,
      0.215650439062,
    );
    assert.equal(
      gpt54.comparison_cost_basis,
      "provider_billed",
    );
    assert.equal(
      gpt54.comparison_cost_relation,
      "exact",
    );
    assert.equal(
      gpt54.comparison_efficiency_relation,
      "exact",
    );
    assert.equal(
      gpt54.provider_billing_reconciliation_status,
      "exact_arm_total",
    );
    assert.equal(
      gpt54.selected_trial_allocation_status,
      "unavailable_provider_aggregate",
    );
    assert.equal(
      gpt54.selected_outcome_allocation_status,
      "unavailable_provider_aggregate",
    );

    assert.equal(
      gpt55.comparison_cost_usd,
      48.604914,
    );
    assert.equal(
      gpt55.comparison_cost_per_clean_success_usd,
      Number(
        "1.157259857142857142857142857",
      ),
    );
    assert.equal(
      gpt55.historical_reviewed_cost_usd,
      183.958832348525,
    );
    assert.equal(
      gpt55.provider_billing_reconciliation_status,
      "exact_arm_total",
    );
  },
);

test(
  "Kimi selected aggregate efficiency is available without outcome allocation",
  () => {
    const kimi =
      getCurrentReviewedPhase3Rows(extended)
        .find(
          (row) =>
            row.arm_id === "router-kimi-k3",
        );

    assert.ok(kimi);
    assert.equal(kimi.trial_count, 60);
    assert.equal(kimi.success_count, 47);
    assert.equal(kimi.pass_rate, 47 / 60);

    assert.equal(
      kimi.comparison_cost_usd,
      26.570403,
    );
    assert.equal(
      kimi.comparison_cost_per_clean_success_usd,
      Number(
        "0.6038727954545454545454545455",
      ),
    );
    assert.equal(
      kimi.comparison_cost_basis,
      "provider_rate_reconstructed_selected_run",
    );
    assert.equal(
      kimi.comparison_cost_relation,
      "estimate",
    );
    assert.equal(
      kimi.comparison_efficiency_relation,
      "estimate",
    );

    // Historical reviewed/provider-log context remains separate.
    assert.equal(
      kimi.historical_reviewed_cost_usd,
      30.8143194,
    );
    assert.equal(
      kimi.historical_unclean_spend_share,
      null,
    );

    assert.equal(
      kimi.selected_trial_allocation_status,
      "available_provider_rate_reconstruction",
    );
    assert.equal(
      kimi.selected_outcome_allocation_status,
      "unavailable_no_reviewed_outcome_join",
    );
    assert.equal(
      kimi.provider_billed_cost_usd,
      null,
    );
  },
);

test(
  "Phase 3 summary uses current selected total and preserves historical total separately",
  () => {
    const extendedSummary =
      getPhaseSummaries(
        getCrossPhaseRows(extended),
        extended,
      ).find(
        (row) => row.phase === "phase3",
      );

    assert.ok(extendedSummary);

    assert.deepEqual(
      [
        extendedSummary.arm_count,
        extendedSummary.trial_count,
        extendedSummary.success_count,
      ],
      [16, 960, 562],
    );

    assert.equal(
      extendedSummary.comparison_cost_usd,
      343.4494304572,
    );
    assert.equal(
      extendedSummary.historical_reviewed_cost_usd,
      1002.984164889198,
    );
    assert.equal(
      extendedSummary.comparison_cost_basis,
      "mixed_best_available_arm_evidence",
    );
    assert.equal(
      extendedSummary.comparison_cost_label,
      "Mixed best-supported arm sum",
    );

    const extendedCleanSuccesses =
      extended.arms.reduce(
        (sum, arm) =>
          sum + arm.cleanSuccessCount,
        0,
      );

    assert.equal(
      extendedSummary
        .comparison_cost_per_clean_success_usd,
      343.4494304572
        / extendedCleanSuccesses,
    );

    assert.equal(
      extendedSummary
        .historical_unclean_spend_share,
      null,
    );

    const coreSummary =
      getPhaseSummaries(
        getCrossPhaseRows(core),
        core,
      ).find(
        (row) => row.phase === "phase3",
      );

    assert.ok(coreSummary);
    assert.deepEqual(
      [
        coreSummary.arm_count,
        coreSummary.trial_count,
        coreSummary.success_count,
      ],
      [15, 900, 515],
    );

    assert.equal(
      coreSummary.comparison_cost_usd,
      316.8790274572,
    );
    assert.equal(
      coreSummary.historical_reviewed_cost_usd,
      972.169845489198,
    );
    assert.equal(
      coreSummary.historical_unclean_spend_share,
      core.historicalCostEvidence
        .nonproductiveOrUncleanSpendShare,
    );
  },
);

test(
  "current selected totals are never multiplied by historical outcome shares",
  () => {
    assert.doesNotMatch(
      source,
      /comparison_cost_usd[^\n;]*\*[^\n;]*historical_unclean_spend_share/,
    );
    assert.doesNotMatch(
      source,
      /selectedCostUsd[^\n;]*\*[^\n;]*nonproductiveOrUncleanSpendShare/,
    );
  },
);

test(
  "historical router and behavior artifacts remain core-only",
  () => {
    assert.equal(
      getBehaviorRows().some(
        (row) =>
          row.arm_id === "router-kimi-k3",
      ),
      false,
    );
    assert.equal(
      getRouterComparisonRows().some(
        (row) =>
          row.router_arm_id
            === "router-kimi-k3",
      ),
      false,
    );
  },
);
