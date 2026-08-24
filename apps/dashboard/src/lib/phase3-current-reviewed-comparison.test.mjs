import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

async function transpiledDataUrl(source) {
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;

  return `data:text/javascript;base64,${Buffer.from(
    compiled,
  ).toString("base64")}`;
}

const currentCanonical = JSON.parse(
  await readFile(
    resolve(
      here,
      "../../../../results/phase3/reporting/phase3_current_reviewed_comparison_20260824.json",
    ),
    "utf8",
  ),
);

const currentGeneratedSource = await readFile(
  resolve(
    here,
    "../generated/phase3-current-reviewed-comparison-data-v3.ts",
  ),
  "utf8",
);

const currentGeneratedModuleUrl =
  await transpiledDataUrl(currentGeneratedSource);

const { default: currentGeneratedSnapshot } =
  await import(currentGeneratedModuleUrl);

const historicalGeneratedSource = await readFile(
  resolve(
    here,
    "../generated/phase3-reviewed-comparison-data.ts",
  ),
  "utf8",
);

const historicalGeneratedModuleUrl =
  await transpiledDataUrl(historicalGeneratedSource);

const historicalLoaderSource = (
  await readFile(
    join(here, "phase3-reviewed-comparison.ts"),
    "utf8",
  )
).replace(
  '"../generated/phase3-reviewed-comparison-data"',
  `"${historicalGeneratedModuleUrl}"`,
);

const historicalLoaderModuleUrl =
  await transpiledDataUrl(historicalLoaderSource);

const currentLoaderSource = (
  await readFile(
    join(here, "phase3-current-reviewed-comparison.ts"),
    "utf8",
  )
)
  .replace(
    '"../generated/phase3-current-reviewed-comparison-data-v3"',
    `"${currentGeneratedModuleUrl}"`,
  )
  .replace(
    '"./phase3-reviewed-comparison"',
    `"${historicalLoaderModuleUrl}"`,
  );

const currentLoaderModuleUrl =
  await transpiledDataUrl(currentLoaderSource);

const {
  PHASE3_CURRENT_REVIEWED_COMPARISON,
  getCurrentReviewedPhase3Scope,
  getCurrentSelectedOutcomeCostEvidence,
  selectCurrentReviewedPhase3Scope,
  validatePhase3CurrentReviewedComparison,
} = await import(currentLoaderModuleUrl);

const clone = () => structuredClone(currentCanonical);

function armFor(scope, armId) {
  const arm = scope.arms.find(
    (candidate) => candidate.armId === armId,
  );
  assert.ok(arm, `missing ${armId}`);
  return arm;
}

test(
  "generated v3 dashboard module exactly matches canonical current-reviewed JSON",
  () => {
    assert.deepEqual(
      currentGeneratedSnapshot,
      currentCanonical,
    );
  },
);

test(
  "current provider model identity preserves multi-model composition",
  () => {
    const mutated = clone();
    const providerModels = [
      "synthetic-primary-cost-model",
      "synthetic-secondary-cost-model",
    ];

    for (const scopeId of [
      "phase3-core",
      "phase3-extended",
    ]) {
      const arm = mutated.scopes[scopeId].arms.find(
        (candidate) =>
          candidate.armId === "router-anthropic-fable-5",
      );
      assert.ok(arm);
      arm.currentProviderModels = [...providerModels];
    }

    const validated =
      validatePhase3CurrentReviewedComparison(mutated);

    for (const scopeId of [
      "phase3-core",
      "phase3-extended",
    ]) {
      const arm = armFor(
        validated.scopes[scopeId],
        "router-anthropic-fable-5",
      );

      assert.deepEqual(
        arm.currentProviderModels,
        providerModels,
      );
      assert.equal(
        Object.isFrozen(arm.currentProviderModels),
        true,
      );
    }
  },
);

test(
  "current-reviewed v3 loader exposes mixed-evidence scope anchors without calling them global lower bounds",
  () => {
    const core =
      getCurrentReviewedPhase3Scope("phase3-core");
    const extended =
      getCurrentReviewedPhase3Scope("phase3-extended");

    assert.equal(
      PHASE3_CURRENT_REVIEWED_COMPARISON.schemaVersion,
      "phase3-current-reviewed-comparison-v3",
    );
    assert.equal(
      PHASE3_CURRENT_REVIEWED_COMPARISON.reviewedAt,
      "2026-08-24",
    );
    assert.equal(
      PHASE3_CURRENT_REVIEWED_COMPARISON.historicalReviewedAt,
      "2026-08-05",
    );

    assert.equal(
      core.selectedCostEvidence.selectedCostUsd,
      "510.405678806867",
    );
    assert.equal(
      extended.selectedCostEvidence.selectedCostUsd,
      "541.219998206867",
    );

    for (const scope of [core, extended]) {
      assert.equal(
        scope.selectedCostEvidence.selectedCostRelation,
        "mixed_by_arm",
      );
      assert.equal(
        scope.selectedCostEvidence.currentReconciledArmCount,
        8,
      );
      assert.equal(
        scope.selectedCostEvidence.currentReconciledCostUsd,
        "251.5579261372",
      );
      assert.equal(
        scope.selectedCostEvidence.exactProviderBilledArmCount,
        2,
      );
      assert.equal(
        scope.selectedCostEvidence.exactProviderBilledCostUsd,
        "78.3968475",
      );
      assert.deepEqual(
        scope.selectedCostEvidence
          .unquantifiedAdditionalCostArmIds,
        [
          "router-anthropic-opus",
          "router-anthropic-sonnet",
        ],
      );
    }

    assert.deepEqual(
      core.selectedCostEvidence.selectedCostRelationCounts,
      {
        exact: 4,
        estimate: 2,
        lowerBound: 2,
        historicalFallback: 7,
      },
    );

    assert.deepEqual(
      extended.selectedCostEvidence
        .selectedCostRelationCounts,
      {
        exact: 4,
        estimate: 2,
        lowerBound: 2,
        historicalFallback: 8,
      },
    );

    assert.equal(Object.isFrozen(core), true);
    assert.equal(Object.isFrozen(extended.arms), true);
  },
);

test(
  "OpenAI remains exact provider-billed aggregate evidence without fabricated allocation",
  () => {
    const scope =
      getCurrentReviewedPhase3Scope("phase3-extended");

    const gpt54 =
      armFor(scope, "router-gpt-5.4");
    const gpt55 =
      armFor(scope, "router-gpt-5.5");

    assert.equal(gpt54.selectedCostUsd, "29.7919335");
    assert.equal(gpt54.selectedCostRelation, "exact");
    assert.equal(gpt54.selectedCostBasis, "provider_billed");
    assert.equal(
      gpt54.providerBilledCostUsd,
      "29.7919335",
    );
    assert.equal(
      gpt54.currentSelectedRunLabel,
      "router-gpt-5.4/2026-06-19__13-47-51",
    );

    assert.equal(gpt55.selectedCostUsd, "48.604914");
    assert.equal(gpt55.selectedCostRelation, "exact");
    assert.equal(gpt55.selectedCostBasis, "provider_billed");
    assert.equal(
      gpt55.providerBilledCostUsd,
      "48.604914",
    );

    for (const arm of [gpt54, gpt55]) {
      assert.equal(
        arm.providerBillingReconciliationStatus,
        "exact_arm_total",
      );
      assert.equal(
        arm.selectedTrialCostAllocationStatus,
        "unavailable_provider_aggregate",
      );
      assert.equal(
        arm.selectedOutcomeCostAllocationStatus,
        "unavailable_provider_aggregate",
      );
      assert.equal(arm.knownAllocatedCostUsd, "0");
      assert.equal(
        arm.unallocatedKnownCostUsd,
        arm.selectedCostUsd,
      );

      const outcome =
        getCurrentSelectedOutcomeCostEvidence(arm);

      assert.equal(
        outcome.status,
        "unavailable_provider_aggregate",
      );
      assert.equal(outcome.evidenceBasis, null);
    }
  },
);

test(
  "Anthropic retained accounting distinguishes exact reconstruction from lower bounds",
  () => {
    const scope =
      getCurrentReviewedPhase3Scope("phase3-core");

    const fable =
      armFor(scope, "router-anthropic-fable-5");
    const haiku =
      armFor(
        scope,
        "router-anthropic-haiku-sanitized",
      );
    const opus =
      armFor(scope, "router-anthropic-opus");
    const sonnet =
      armFor(scope, "router-anthropic-sonnet");

    for (const arm of [fable, haiku]) {
      assert.equal(arm.selectedCostRelation, "exact");
      assert.equal(
        arm.selectedCostBasis,
        "provider_rate_reconstructed_retained_usage",
      );
      assert.equal(
        arm.providerBillingReconciliationStatus,
        "provider_invoice_unavailable",
      );
      assert.equal(
        arm.completeTrialCostCount,
        arm.trialCount,
      );
      assert.equal(arm.lowerBoundTrialCount, 0);

      const outcome =
        getCurrentSelectedOutcomeCostEvidence(arm);

      assert.equal(
        outcome.status,
        "available_provider_rate_reconstruction",
      );
      assert.equal(
        outcome.evidenceBasis,
        "provider_rate_reconstruction",
      );
    }

    assert.equal(fable.selectedCostUsd, "64.80504500");
    assert.equal(haiku.selectedCostUsd, "16.70224485");

    for (const arm of [opus, sonnet]) {
      assert.equal(
        arm.selectedCostRelation,
        "lower_bound",
      );
      assert.equal(
        arm.selectedCostBasis,
        "provider_rate_reconstructed_retained_usage_lower_bound",
      );
      assert.equal(
        arm.unquantifiedAdditionalCostStatus,
        "possible_additional_exception_path_spend",
      );
      assert.equal(
        arm.knownAllocatedCostUsd,
        arm.selectedCostUsd,
      );
      assert.equal(arm.unallocatedKnownCostUsd, "0");

      const outcome =
        getCurrentSelectedOutcomeCostEvidence(arm);

      assert.equal(
        outcome.status,
        "available_lower_bound",
      );
      assert.equal(
        outcome.evidenceBasis,
        "provider_rate_reconstruction_lower_bound",
      );
    }

    assert.equal(opus.selectedCostUsd, "50.28831125");
    assert.equal(opus.completeTrialCostCount, 58);
    assert.equal(opus.lowerBoundTrialCount, 2);

    assert.equal(sonnet.selectedCostUsd, "38.38591710");
    assert.equal(sonnet.completeTrialCostCount, 55);
    assert.equal(sonnet.lowerBoundTrialCount, 5);
  },
);

test(
  "DeepSeek uses selected-run provider-rate estimates while preserving broader provider context",
  () => {
    const scope =
      getCurrentReviewedPhase3Scope("phase3-core");

    const expected = new Map([
      [
        "router-deepseek-flash",
        {
          selected: "1.0798358032",
          context: "1.1502775424",
          excess: "0.0704417392",
        },
      ],
      [
        "router-deepseek-pro",
        {
          selected: "1.899724634",
          context: "1.963511004",
          excess: "0.063786370",
        },
      ],
    ]);

    for (const [armId, wanted] of expected) {
      const arm = armFor(scope, armId);

      assert.equal(
        arm.selectedCostRelation,
        "estimate",
      );
      assert.equal(
        arm.selectedCostBasis,
        "provider_rate_reconstructed_selected_run",
      );
      assert.equal(
        arm.selectedCostUsd,
        wanted.selected,
      );
      assert.equal(
        arm.providerBilledCostUsd,
        null,
      );
      assert.equal(
        arm.providerContextBilledCostUsd,
        wanted.context,
      );
      assert.equal(
        arm.providerContextExcessUsd,
        wanted.excess,
      );
      assert.equal(
        arm.providerContextScope,
        "same_day_model_aggregate",
      );
      assert.equal(
        arm.providerBillingReconciliationStatus,
        "same_day_model_aggregate_not_run_isolated",
      );

      const outcome =
        getCurrentSelectedOutcomeCostEvidence(arm);

      assert.equal(
        outcome.status,
        "available_provider_rate_reconstruction",
      );
      assert.equal(
        outcome.evidenceBasis,
        "provider_rate_reconstruction",
      );
    }
  },
);

test(
  "unreconciled arms are explicit historical fallbacks rather than silently current-reconciled",
  () => {
    const scope =
      getCurrentReviewedPhase3Scope("phase3-extended");

    const gemini =
      armFor(scope, "router-gemini-3.1-pro");
    const kimi =
      armFor(scope, "router-kimi-k3");

    assert.equal(
      gemini.currentReconciliationStatus,
      "historical_fallback",
    );
    assert.equal(
      gemini.selectedCostRelation,
      "historical_fallback",
    );
    assert.equal(
      gemini.selectedCostUsd,
      gemini.historicalReviewedCostUsd,
    );
    assert.equal(gemini.currentSelectedRunLabel, null);
    assert.deepEqual(gemini.currentProviderModels, []);
    assert.deepEqual(gemini.currentRoutingAliases, []);

    const geminiOutcome =
      getCurrentSelectedOutcomeCostEvidence(gemini);

    assert.equal(geminiOutcome.status, "available");
    assert.equal(
      geminiOutcome.evidenceBasis,
      "historical_reviewed_selected_cost",
    );

    assert.equal(
      kimi.currentReconciliationStatus,
      "historical_fallback",
    );
    assert.equal(
      kimi.selectedCostRelation,
      "historical_fallback",
    );
    assert.equal(kimi.selectedCostUsd, "30.8143194");

    const kimiOutcome =
      getCurrentSelectedOutcomeCostEvidence(kimi);

    assert.equal(kimiOutcome.status, "unavailable");
  },
);

test(
  "loader fails closed on scope, provider-context, allocation, relation, and historical mutations",
  () => {
    const wrongTotal = clone();
    wrongTotal.scopes["phase3-core"]
      .selectedCostEvidence.selectedCostUsd = "1";

    assert.throws(
      () =>
        validatePhase3CurrentReviewedComparison(
          wrongTotal,
        ),
      /scope anchors|arithmetic arm sum/i,
    );

    const wrongContext = clone();
    const deepseek = wrongContext.scopes[
      "phase3-core"
    ].arms.find(
      (arm) => arm.armId === "router-deepseek-pro",
    );
    assert.ok(deepseek);
    deepseek.providerContextExcessUsd = "0";

    assert.throws(
      () =>
        validatePhase3CurrentReviewedComparison(
          wrongContext,
        ),
      /selected-run provider-rate estimate/i,
    );

    const wrongProviderAllocation = clone();
    const gpt54 = wrongProviderAllocation.scopes[
      "phase3-core"
    ].arms.find(
      (arm) => arm.armId === "router-gpt-5.4",
    );
    assert.ok(gpt54);
    gpt54.selectedTrialCostAllocationStatus =
      "available_provider_rate_reconstruction";

    assert.throws(
      () =>
        validatePhase3CurrentReviewedComparison(
          wrongProviderAllocation,
        ),
      /provider-billed contract/i,
    );

    const wrongLowerBoundRelation = clone();
    const opus = wrongLowerBoundRelation.scopes[
      "phase3-core"
    ].arms.find(
      (arm) => arm.armId === "router-anthropic-opus",
    );
    assert.ok(opus);
    opus.selectedCostRelation = "exact";

    assert.throws(
      () =>
        validatePhase3CurrentReviewedComparison(
          wrongLowerBoundRelation,
        ),
      /identity|lower-bound contract/i,
    );

    const historicalDrift = clone();
    historicalDrift.scopes["phase3-core"]
      .arms[0].recordedCostUsd = "0";

    assert.throws(
      () =>
        validatePhase3CurrentReviewedComparison(
          historicalDrift,
        ),
      /does not preserve the frozen historical arm/i,
    );
  },
);

test(
  "scope selection defaults deterministically to extended and rejects repeated or unknown values",
  () => {
    assert.equal(
      selectCurrentReviewedPhase3Scope(undefined).scopeId,
      "phase3-extended",
    );

    assert.equal(
      selectCurrentReviewedPhase3Scope(
        "phase3-core",
      ).scopeId,
      "phase3-core",
    );

    const repeated =
      selectCurrentReviewedPhase3Scope([
        "phase3-core",
        "phase3-extended",
      ]);

    assert.equal(
      repeated.scopeId,
      "phase3-extended",
    );
    assert.equal(
      repeated.warning,
      "repeated_scope",
    );

    const invalid =
      selectCurrentReviewedPhase3Scope(
        "future-scope",
      );

    assert.equal(
      invalid.scopeId,
      "phase3-extended",
    );
    assert.equal(
      invalid.warning,
      "invalid_scope",
    );
  },
);
