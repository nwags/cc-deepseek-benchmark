import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import {
  dirname,
  join,
  resolve,
} from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(
  fileURLToPath(import.meta.url),
);
const root = resolve(
  here,
  "../../../..",
);

const sourceAccessorSource =
  await readFile(
    join(
      here,
      "spend-decomposition-source.ts",
    ),
    "utf8",
  );

const modelSource =
  await readFile(
    join(
      here,
      "spend-decomposition.ts",
    ),
    "utf8",
  );

const f1 = JSON.parse(
  await readFile(
    resolve(
      root,
      "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
    ),
    "utf8",
  ),
);

async function importSourceAccessor() {
  const testSource =
    sourceAccessorSource.replace(
      'import "server-only";',
      'import "data:text/javascript,export%20{}";',
    );

  const compiled =
    ts.transpileModule(
      testSource,
      {
        compilerOptions: {
          module:
            ts.ModuleKind.ES2022,
          target:
            ts.ScriptTarget.ES2022,
        },
      },
    ).outputText;

  return import(
    `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
  );
}

async function importModel() {
  const compiled =
    ts.transpileModule(
      modelSource,
      {
        compilerOptions: {
          module:
            ts.ModuleKind.ES2022,
          target:
            ts.ScriptTarget.ES2022,
        },
      },
    ).outputText;

  return import(
    `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
  );
}

const sourceModule =
  await importSourceAccessor();

const source =
  await sourceModule
    .getSpendDecompositionSource();

assert.equal(source.available, true);

const decomposition =
  await importModel();

const coreScope =
  f1.scopes["phase3-core"];

const extendedScope =
  f1.scopes["phase3-extended"];

const coreModel =
  decomposition
    .buildSpendDecompositionModel(
      source.coreRows,
      source.reviewRows,
      coreScope,
    );

const extendedModel =
  decomposition
    .buildSpendDecompositionModel(
      source.coreRows,
      source.reviewRows,
      extendedScope,
    );

function segment(
  model,
  id,
) {
  return decomposition
    .getSpendDecompositionSegment(
      model,
      id,
    );
}

function clone(value) {
  return structuredClone(value);
}

test(
  "DR-303 exact source membership joins 900 core rows to 960 reviewed rows",
  () => {
    assert.equal(
      coreModel.scopeId,
      "phase3-core",
    );
    assert.equal(
      coreModel.trialCount,
      900,
    );
    assert.equal(
      coreModel.armCount,
      15,
    );

    assert.equal(
      extendedModel.scopeId,
      "phase3-extended",
    );
    assert.equal(
      extendedModel.trialCount,
      960,
    );
    assert.equal(
      extendedModel.armCount,
      16,
    );

    assert.equal(
      extendedModel.arms.filter(
        (arm) =>
          arm.armId
          === "router-kimi-k3",
      ).length,
      1,
    );

    for (
      const arm
      of extendedModel.arms
    ) {
      assert.equal(
        arm.trialCount,
        60,
        arm.armId,
      );
    }
  },
);

test(
  "historical exception-failure retains reviewed not-recorded trials",
  () => {
    const coreById =
      new Map(
        source.coreRows.map(
          (row) =>
            [row.trial_id, row],
        ),
      );

    const notRecordedCore =
      source.reviewRows.filter(
        (row) =>
          row.arm_id
            !== "router-kimi-k3"
          && row.raw_outcome
            === "not_recorded",
      );

    assert.equal(
      notRecordedCore.length,
      28,
    );

    assert.equal(
      notRecordedCore.every(
        (row) =>
          coreById.get(
            row.trial_id,
          )?.outcome_bucket
            === "exception_failure",
      ),
      true,
    );
  },
);

test(
  "historical not-recorded compatibility is limited to exception-failure",
  () => {
    const normalCore =
      source.coreRows.find(
        (row) =>
          row.outcome_bucket
          === "normal_failure",
      );

    assert.ok(normalCore);

    const normalReview =
      source.reviewRows.map(
        (row) => ({ ...row }),
      );

    const normalIndex =
      normalReview.findIndex(
        (row) =>
          row.trial_id
          === normalCore.trial_id,
      );

    assert.notEqual(normalIndex, -1);

    normalReview[normalIndex].raw_outcome =
      "not_recorded";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            normalReview,
            extendedScope,
          ),
      /core_review_outcome_mismatch/,
    );

    const successCore =
      source.coreRows.find(
        (row) =>
          row.outcome_bucket
          === "clean_success",
      );

    assert.ok(successCore);

    const successReview =
      source.reviewRows.map(
        (row) => ({ ...row }),
      );

    const successIndex =
      successReview.findIndex(
        (row) =>
          row.trial_id
          === successCore.trial_id,
      );

    assert.notEqual(successIndex, -1);

    successReview[successIndex].raw_outcome =
      "not_recorded";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            successReview,
            extendedScope,
          ),
      /core_review_outcome_mismatch/,
    );
  },
);

test(
  "core primary stack reproduces frozen recorded buckets and reviewed cost basis",
  () => {
    assert.equal(
      segment(
        coreModel,
        "clean_success",
      ).trialCount,
      499,
    );
    assert.equal(
      segment(
        coreModel,
        "clean_success",
      ).recordedCostUsd,
      "607.88236925",
    );

    assert.equal(
      segment(
        coreModel,
        "normal_failure",
      ).trialCount,
      195,
    );
    assert.equal(
      segment(
        coreModel,
        "normal_failure",
      ).recordedCostUsd,
      "189.07357825",
    );

    assert.equal(
      segment(
        coreModel,
        "exception_failure",
      ).trialCount,
      190,
    );
    assert.equal(
      segment(
        coreModel,
        "exception_failure",
      ).recordedCostUsd,
      "23.81878125",
    );

    assert.equal(
      segment(
        coreModel,
        "exception_with_success_signal",
      ).trialCount,
      16,
    );
    assert.equal(
      segment(
        coreModel,
        "exception_with_success_signal",
      ).recordedCostUsd,
      "0",
    );

    assert.equal(
      coreModel.recordedCostUsd,
      "820.77472875",
    );
    assert.equal(
      coreModel
        .summedArmAccountingGapUsd,
      "151.395116739198",
    );
    assert.equal(
      coreModel
        .scopeAccountingGapUsd,
      "151.395116739198",
    );
    assert.equal(
      coreModel
        .summedSelectedArmCostUsd,
      "972.169845489198",
    );
    assert.equal(
      coreModel
        .scopeSelectedReviewedCostUsd,
      "972.169845489198",
    );
    assert.equal(
      coreModel
        .scopeReconciliationDeltaUsd,
      "0",
    );
    assert.equal(
      coreModel
        .missingRecordedCostCount,
      179,
    );
    assert.equal(
      coreModel
        .unresolvedCostCount,
      29,
    );
  },
);

test(
  "extended primary stack adds Kimi recorded outcomes without allocating its gap",
  () => {
    assert.equal(
      segment(
        extendedModel,
        "clean_success",
      ).trialCount,
      543,
    );
    assert.equal(
      segment(
        extendedModel,
        "clean_success",
      ).recordedCostUsd,
      "628.27639225",
    );

    assert.equal(
      segment(
        extendedModel,
        "normal_failure",
      ).trialCount,
      200,
    );
    assert.equal(
      segment(
        extendedModel,
        "normal_failure",
      ).recordedCostUsd,
      "192.79123825",
    );

    assert.equal(
      segment(
        extendedModel,
        "exception_failure",
      ).trialCount,
      198,
    );
    assert.equal(
      segment(
        extendedModel,
        "exception_failure",
      ).recordedCostUsd,
      "24.91431125",
    );

    const exceptionSuccess =
      segment(
        extendedModel,
        "exception_with_success_signal",
      );

    assert.equal(
      exceptionSuccess.trialCount,
      19,
    );
    assert.equal(
      exceptionSuccess.recordedCostUsd,
      "0",
    );
    assert.equal(
      exceptionSuccess
        .missingRecordedCostCount,
      19,
    );

    assert.equal(
      extendedModel.recordedCostUsd,
      "845.98194175",
    );
    assert.equal(
      extendedModel
        .summedArmAccountingGapUsd,
      "157.002223139198",
    );
    assert.equal(
      extendedModel
        .scopeAccountingGapUsd,
      "157.0022231391979",
    );
    assert.equal(
      extendedModel
        .summedSelectedArmCostUsd,
      "1002.984164889198",
    );
    assert.equal(
      extendedModel
        .scopeSelectedReviewedCostUsd,
      "1002.9841648891979",
    );
    assert.equal(
      extendedModel
        .scopeReconciliationDeltaUsd,
      "0.0000000000001",
    );
    assert.equal(
      extendedModel
        .scopeReconciliationToleranceUsd,
      "0.000000000001",
    );
    assert.equal(
      extendedModel
        .missingRecordedCostCount,
      189,
    );
    assert.equal(
      extendedModel
        .unresolvedCostCount,
      39,
    );
  },
);

test(
  "Kimi reproduces the exact 44/5/8/3 recorded-outcome contract",
  () => {
    const kimi =
      extendedModel.arms.find(
        (arm) =>
          arm.armId
          === "router-kimi-k3",
      );

    assert.ok(kimi);

    const byId =
      Object.fromEntries(
        kimi.segments.map(
          (value) =>
            [value.id, value],
        ),
      );

    assert.equal(
      byId.clean_success.trialCount,
      44,
    );
    assert.equal(
      byId.clean_success.recordedCostUsd,
      "20.394023",
    );
    assert.equal(
      byId.clean_success
        .missingRecordedCostCount,
      0,
    );

    assert.equal(
      byId.normal_failure.trialCount,
      5,
    );
    assert.equal(
      byId.normal_failure.recordedCostUsd,
      "3.717660",
    );
    assert.equal(
      byId.normal_failure
        .missingRecordedCostCount,
      0,
    );

    assert.equal(
      byId.exception_failure.trialCount,
      8,
    );
    assert.equal(
      byId.exception_failure.recordedCostUsd,
      "1.09553",
    );
    assert.equal(
      byId.exception_failure
        .missingRecordedCostCount,
      7,
    );

    assert.equal(
      byId.exception_with_success_signal
        .trialCount,
      3,
    );
    assert.equal(
      byId.exception_with_success_signal
        .recordedCostUsd,
      "0",
    );
    assert.equal(
      byId.exception_with_success_signal
        .missingRecordedCostCount,
      3,
    );

    assert.equal(
      kimi.recordedCostUsd,
      "25.207213",
    );
    assert.equal(
      kimi.accountingGapUsd,
      "5.6071064",
    );
    assert.equal(
      kimi.selectedReviewedCostUsd,
      "30.8143194",
    );
    assert.equal(
      kimi.missingRecordedCostCount,
      10,
    );
    assert.equal(
      kimi.unresolvedCostCount,
      10,
    );
    assert.equal(
      kimi.selectedCostBasis,
      "qualified_retained_rate_estimate",
    );
    assert.equal(
      kimi.trialAllocationStatus,
      "unresolved",
    );
    assert.equal(
      kimi.outcomeCostAllocationStatus,
      "unavailable",
    );
    assert.equal(
      kimi.costConfidence,
      "low",
    );
  },
);

test(
  "every arm reconciles four recorded outcome buckets plus one known gap",
  () => {
    for (
      const model
      of [coreModel, extendedModel]
    ) {
      for (const arm of model.arms) {
        assert.equal(
          arm.segments.reduce(
            (count, value) =>
              count + value.trialCount,
            0,
          ),
          60,
          arm.armId,
        );

        assert.equal(
          arm.missingRecordedCostCount,
          arm.segments.reduce(
            (count, value) =>
              count
              + value
                .missingRecordedCostCount,
            0,
          ),
          arm.armId,
        );

        assert.ok(
          arm.selectedReviewedCostUsd,
          arm.armId,
        );
        assert.ok(
          arm.accountingGapUsd,
          arm.armId,
        );
      }
    }
  },
);

test(
  "missing recorded cost remains distinct from unresolved cost",
  () => {
    assert.equal(
      coreModel.missingRecordedCostCount,
      179,
    );
    assert.equal(
      coreModel.unresolvedCostCount,
      29,
    );

    assert.equal(
      extendedModel
        .missingRecordedCostCount,
      189,
    );
    assert.equal(
      extendedModel
        .unresolvedCostCount,
      39,
    );

    assert.notEqual(
      coreModel.missingRecordedCostCount,
      coreModel.unresolvedCostCount,
    );
    assert.notEqual(
      extendedModel
        .missingRecordedCostCount,
      extendedModel
        .unresolvedCostCount,
    );
  },
);

test(
  "exact trial-set and ID-bound identity mutations fail closed",
  () => {
    const wrongTrial =
      source.coreRows.map(
        (row) => ({ ...row }),
      );

    wrongTrial[0].trial_id =
      "00000000-0000-4000-8000-000000000000";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            wrongTrial,
            source.reviewRows,
            extendedScope,
          ),
      /core_review_trial_set_mismatch/,
    );

    const wrongTask =
      source.coreRows.map(
        (row) => ({ ...row }),
      );

    wrongTask[0].task_id =
      `${wrongTask[0].task_id}-changed`;

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            wrongTask,
            source.reviewRows,
            extendedScope,
          ),
      /core_review_identity_mismatch/,
    );
  },
);

test(
  "unexpected Kimi reward or outcome semantics fail closed",
  () => {
    const mutated =
      source.reviewRows.map(
        (row) => ({ ...row }),
      );

    const index =
      mutated.findIndex(
        (row) =>
          row.arm_id
          === "router-kimi-k3",
      );

    assert.notEqual(index, -1);

    mutated[index].raw_reward_present =
      true;
    mutated[index].raw_reward =
      "0.5";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            mutated,
            extendedScope,
          ),
      /kimi_reward_unexpected/,
    );
  },
);

test(
  "reviewed F1 per-arm accounting mutations fail closed",
  () => {
    const mutated =
      clone(extendedScope);

    const kimi =
      mutated.arms.find(
        (arm) =>
          arm.armId
          === "router-kimi-k3",
      );

    assert.ok(kimi);

    kimi.accountingGapUsd =
      "5.6071065";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            source.reviewRows,
            mutated,
          ),
      /arm_five_part_reconciliation_mismatch/,
    );

    const missingMutation =
      clone(extendedScope);

    const kimiMissing =
      missingMutation.arms.find(
        (arm) =>
          arm.armId
          === "router-kimi-k3",
      );

    kimiMissing.missingRecordedCostCount =
      11;

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            source.reviewRows,
            missingMutation,
          ),
      /arm_missing_cost_count_mismatch/,
    );
  },
);

test(
  "scope headline drift beyond the reviewed tolerance fails closed",
  () => {
    const mutated =
      clone(extendedScope);

    mutated.costEvidence
      .qualifiedAdjustedCostEstimateUsd =
      "1002.9841648";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            source.reviewRows,
            mutated,
          ),
      /scope_selected_cost_reconciliation_mismatch/,
    );
  },
);

test(
  "scope accounting-gap drift beyond the reviewed tolerance fails closed",
  () => {
    const mutated =
      clone(extendedScope);

    mutated.costEvidence.accountingGapUsd =
      "157.0022231";

    assert.throws(
      () =>
        decomposition
          .buildSpendDecompositionModel(
            source.coreRows,
            source.reviewRows,
            mutated,
          ),
      /scope_accounting_gap_reconciliation_mismatch/,
    );
  },
);

test(
  "pure DR-303 model has no filesystem, server, database, network, J2, or runtime source dependency",
  () => {
    assert.match(
      modelSource,
      /import type/,
    );

    assert.doesNotMatch(
      modelSource,
      /import "server-only"/,
    );
    assert.doesNotMatch(
      modelSource,
      /node:fs/,
    );
    assert.doesNotMatch(
      modelSource,
      /node:path/,
    );
    assert.doesNotMatch(
      modelSource,
      /SUPABASE/i,
    );
    assert.doesNotMatch(
      modelSource,
      /\bpostgres\b/i,
    );
    assert.doesNotMatch(
      modelSource,
      /\bR2\b/,
    );
    assert.doesNotMatch(
      modelSource,
      /https?:\/\//i,
    );
    assert.doesNotMatch(
      modelSource,
      /\bfetch\s*\(/,
    );
    assert.doesNotMatch(
      modelSource,
      /process\.env/,
    );
    assert.doesNotMatch(
      modelSource,
      /failure-taxonomy/i,
    );
    assert.doesNotMatch(
      modelSource,
      /failure_taxonomy/i,
    );
    assert.doesNotMatch(
      modelSource,
      /getSpendDecompositionSource\s*\(/,
    );
  },
);
