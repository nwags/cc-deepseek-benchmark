import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../../..");

const reviewPath = resolve(
  root,
  "results/manual_verification/comprehensive_review_20260731/trial_review.csv",
);
const taxonomyPath = resolve(
  root,
  "results/manual_verification/failure_taxonomy_20260813/trial_failure_taxonomy.jsonl",
);

const reviewBytes = await readFile(reviewPath);
const taxonomyBytes = await readFile(taxonomyPath);

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];

    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }

  const [header, ...data] = rows;
  if (!header?.length) return [];

  return data
    .filter((values) => values.some(Boolean))
    .map((values) =>
      Object.fromEntries(
        header.map((key, index) => [key, values[index] ?? ""]),
      ),
    );
}

const reviewRows = parseCsv(reviewBytes.toString("utf8"));
const taxonomyRows = taxonomyBytes
  .toString("utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

const taxonomyById = new Map(
  taxonomyRows.map((row) => [row.trial_id, row]),
);

const modelSource = await readFile(
  join(here, "failure-composition.ts"),
  "utf8",
);
const compiled = ts.transpileModule(modelSource, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl =
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const composition = await import(moduleUrl);

const model = composition.buildFailureCompositionModel(
  reviewRows,
  taxonomyRows,
);

function globalCounts(value = model) {
  return Object.fromEntries(
    value.categories.map((category) => [category.id, category.count]),
  );
}

function classificationFor(row) {
  const taxonomy = taxonomyById.get(row.trial_id);
  assert.ok(taxonomy, `missing J2 row for ${row.trial_id}`);
  return composition.classifyFailureCompositionTrial(row, taxonomy);
}

test("DR-302 model retains exact frozen source identities and global partition", () => {
  assert.equal(
    sha256(reviewBytes),
    "c6945d114e3a2e0610dfd091bad8ea4e9bc17707db678e90f4e0f8058fc56501",
  );
  assert.equal(
    sha256(taxonomyBytes),
    "ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1",
  );

  assert.equal(model.scopeId, "phase3-extended");
  assert.equal(model.trialCount, 960);
  assert.equal(model.armCount, 16);
  assert.equal(model.trialsPerArm, 60);
  assert.deepEqual(
    model.arms.map((arm) => arm.armId),
    [
      "router-anthropic-fable-5",
      "router-anthropic-haiku-sanitized",
      "router-anthropic-opus",
      "router-anthropic-sonnet",
      "router-deepseek-flash",
      "router-deepseek-pro",
      "router-gemini-3.1-pro",
      "router-gemini-flash",
      "router-glm-5.1",
      "router-glm-5.2",
      "router-gpt-5.4",
      "router-gpt-5.5",
      "router-grok-build-0.1",
      "router-kimi-k2.6",
      "router-kimi-k3",
      "router-qwen-3.7-plus",
    ],
  );
  assert.equal(model.rawFailureCount, 370);
  assert.equal(model.successCount, 562);
  assert.equal(model.notRecordedCount, 28);
  assert.equal(model.successfulTimeoutAfterMeaningfulActivityCount, 19);

  assert.deepEqual(globalCounts(), {
    verifier_task_failure: 167,
    timeout_after_meaningful_activity: 127,
    provider_policy_refusal: 9,
    invalid_response_path: 4,
    missing_required_output: 7,
    extraneous_output_artifacts: 22,
    unknown_or_incomplete_evidence: 34,
  });

  assert.equal(
    model.categories.reduce((sum, category) => sum + category.count, 0),
    370,
  );
});

test("every arm retains 60 reviewed trials and partitions only its raw failures", () => {
  assert.equal(model.arms.length, 16);

  for (const arm of model.arms) {
    assert.equal(arm.trialCount, 60, arm.armId);
    assert.equal(
      arm.rawFailureCount + arm.successCount + arm.notRecordedCount,
      60,
      arm.armId,
    );
    assert.equal(
      arm.categories.reduce((sum, category) => sum + category.count, 0),
      arm.rawFailureCount,
      arm.armId,
    );

    for (const category of arm.categories) {
      assert.equal(
        category.shareOfRawFailures,
        arm.rawFailureCount === 0
          ? 0
          : category.count / arm.rawFailureCount,
        `${arm.armId}:${category.id}`,
      );
    }
  }
});

test("display precedence preserves invalid response and output-specific buckets", () => {
  const invalidRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && row.execution_validity === "invalid_response_path",
  );
  assert.equal(invalidRows.length, 4);

  for (const row of invalidRows) {
    assert.equal(row.failure_subtype, "missing_required_output");
    assert.notEqual(
      taxonomyById.get(row.trial_id).verifier_failure_category.value,
      "none",
    );
    assert.equal(
      classificationFor(row),
      "invalid_response_path",
    );
  }

  const missingRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && row.failure_subtype === "missing_required_output"
      && row.execution_validity !== "invalid_response_path",
  );
  assert.equal(missingRows.length, 7);
  assert.ok(
    missingRows.every(
      (row) => classificationFor(row) === "missing_required_output",
    ),
  );

  const extraneousRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && row.failure_subtype === "extraneous_output_artifacts",
  );
  assert.equal(extraneousRows.length, 22);
  assert.ok(
    extraneousRows.every(
      (row) => classificationFor(row) === "extraneous_output_artifacts",
    ),
  );
});

test("display-only precedence is executable from most specific exception to residual", () => {
  const taxonomy = {
    verifier_failure_category: {
      value: "test_assertion_failure",
    },
  };

  const allSignals = {
    raw_outcome: "failure",
    policy_disposition: "provider_policy_refusal",
    execution_validity: "invalid_response_path",
    failure_subtype: "missing_required_output",
    activity_subtype: "timeout_after_meaningful_activity",
  };

  assert.equal(
    composition.classifyFailureCompositionTrial(allSignals, taxonomy),
    "provider_policy_refusal",
  );

  const noPolicy = {
    ...allSignals,
    policy_disposition: "none_detected",
  };
  assert.equal(
    composition.classifyFailureCompositionTrial(noPolicy, taxonomy),
    "invalid_response_path",
  );

  const validPath = {
    ...noPolicy,
    execution_validity: "substantive",
  };
  assert.equal(
    composition.classifyFailureCompositionTrial(validPath, taxonomy),
    "missing_required_output",
  );

  const extraneous = {
    ...validPath,
    failure_subtype: "extraneous_output_artifacts",
  };
  assert.equal(
    composition.classifyFailureCompositionTrial(extraneous, taxonomy),
    "extraneous_output_artifacts",
  );

  const timeout = {
    ...extraneous,
    failure_subtype: "timeout",
  };
  assert.equal(
    composition.classifyFailureCompositionTrial(timeout, taxonomy),
    "timeout_after_meaningful_activity",
  );

  const verifierOnly = {
    ...timeout,
    activity_subtype: "substantive_agent_activity",
  };
  assert.equal(
    composition.classifyFailureCompositionTrial(verifierOnly, taxonomy),
    "verifier_task_failure",
  );

  assert.equal(
    composition.classifyFailureCompositionTrial(
      verifierOnly,
      { verifier_failure_category: { value: "none" } },
    ),
    "unknown_or_incomplete_evidence",
  );
});

test("remaining verifier and meaningful-timeout failures use their own buckets", () => {
  const verifierRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && classificationFor(row) === "verifier_task_failure",
  );
  assert.equal(verifierRows.length, 167);

  const timeoutRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && classificationFor(row) === "timeout_after_meaningful_activity",
  );
  assert.equal(timeoutRows.length, 127);
});

test("successful and not-recorded timeout anomalies stay outside failure composition", () => {
  const successfulTimeouts = reviewRows.filter(
    (row) =>
      row.raw_outcome === "success"
      && row.activity_subtype === "timeout_after_meaningful_activity",
  );
  assert.equal(successfulTimeouts.length, 19);
  assert.ok(
    successfulTimeouts.every((row) => classificationFor(row) === null),
  );

  const notRecordedTimeouts = reviewRows.filter(
    (row) =>
      row.raw_outcome === "not_recorded"
      && row.activity_subtype === "timeout_after_meaningful_activity",
  );
  assert.equal(notRecordedTimeouts.length, 28);
  assert.ok(
    notRecordedTimeouts.every((row) => classificationFor(row) === null),
  );
});

test("unknown residual preserves evidence-complete and incomplete semantics", () => {
  assert.deepEqual(model.residualBreakdown, {
    count: 34,
    evidenceCompleteCount: 27,
    evidenceIncompleteCount: 7,
    highConfidenceCount: 27,
    mediumConfidenceCount: 7,
    noSubstantiveAttemptCount: 27,
    indeterminateCount: 7,
  });

  const residualRows = reviewRows.filter(
    (row) =>
      row.raw_outcome === "failure"
      && classificationFor(row) === "unknown_or_incomplete_evidence",
  );
  assert.equal(residualRows.length, 34);
  assert.ok(
    residualRows.every(
      (row) =>
        row.execution_validity === "unknown"
        && row.activity_subtype === "activity_unknown"
        && row.manual_review_required === "True",
    ),
  );
});

test("selection precedence is explicit presentation policy and separate from display order", () => {
  assert.deepEqual(
    [...composition.FAILURE_COMPOSITION_CATEGORY_IDS],
    [
      "verifier_task_failure",
      "timeout_after_meaningful_activity",
      "provider_policy_refusal",
      "invalid_response_path",
      "missing_required_output",
      "extraneous_output_artifacts",
      "unknown_or_incomplete_evidence",
    ],
  );

  assert.deepEqual(
    [...composition.FAILURE_COMPOSITION_SELECTION_PRECEDENCE],
    [
      "provider_policy_refusal",
      "invalid_response_path",
      "missing_required_output",
      "extraneous_output_artifacts",
      "timeout_after_meaningful_activity",
      "verifier_task_failure",
      "unknown_or_incomplete_evidence",
    ],
  );

  assert.notDeepEqual(
    composition.FAILURE_COMPOSITION_CATEGORY_IDS,
    composition.FAILURE_COMPOSITION_SELECTION_PRECEDENCE,
  );

  assert.match(
    modelSource,
    /for \(const id of FAILURE_COMPOSITION_SELECTION_PRECEDENCE\)/,
  );
});

test("model fails closed on duplicate, mismatched, or repartitioned frozen inputs", () => {
  const duplicateReview = reviewRows.map((row) => ({ ...row }));
  duplicateReview[duplicateReview.length - 1] = {
    ...duplicateReview[0],
  };
  assert.throws(
    () =>
      composition.buildFailureCompositionModel(
        duplicateReview,
        taxonomyRows,
      ),
    /review_trial_id_duplicate/,
  );

  const mismatchedTaxonomy = taxonomyRows.map((row) => ({
    ...row,
  }));
  mismatchedTaxonomy[mismatchedTaxonomy.length - 1] = {
    ...mismatchedTaxonomy[mismatchedTaxonomy.length - 1],
    trial_id: "00000000-0000-4000-8000-000000000000",
  };
  assert.throws(
    () =>
      composition.buildFailureCompositionModel(
        reviewRows,
        mismatchedTaxonomy,
      ),
    /failure_composition_trial_set_mismatch/,
  );

  const renamedReview = reviewRows.map((row) => ({
    ...row,
    arm_id:
      row.arm_id === "router-kimi-k3"
        ? "router-unexpected-arm"
        : row.arm_id,
  }));
  const renamedTaxonomy = taxonomyRows.map((row) => ({
    ...row,
    arm_id:
      row.arm_id === "router-kimi-k3"
        ? "router-unexpected-arm"
        : row.arm_id,
  }));
  assert.throws(
    () =>
      composition.buildFailureCompositionModel(
        renamedReview,
        renamedTaxonomy,
      ),
    /failure_composition_arm_membership_mismatch/,
  );

  const repartitioned = reviewRows.map((row) => ({ ...row }));
  const target = repartitioned.findIndex(
    (row) =>
      row.raw_outcome === "failure"
      && row.activity_subtype === "timeout_after_meaningful_activity",
  );
  assert.notEqual(target, -1);
  repartitioned[target] = {
    ...repartitioned[target],
    activity_subtype: "activity_unknown",
  };
  assert.throws(
    () =>
      composition.buildFailureCompositionModel(
        repartitioned,
        taxonomyRows,
      ),
    /failure_composition_category_count_mismatch|failure_composition_residual_semantics_mismatch/,
  );
});

test("pure DR-302 model has no server, database, network, or runtime-classifier dependency", () => {
  assert.doesNotMatch(modelSource, /^\s*import\s/m);
  assert.doesNotMatch(modelSource, /process\.env/);
  assert.doesNotMatch(modelSource, /\bfetch\s*\(/);
  assert.doesNotMatch(modelSource, /new Function\s*\(/);
  assert.doesNotMatch(modelSource, /server-only/);
});
