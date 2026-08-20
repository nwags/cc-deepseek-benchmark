import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../../..");

const sourcePath = resolve(
  here,
  "spend-decomposition-source.ts",
);

const corePath = resolve(
  root,
  "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
);

const reviewPath = resolve(
  root,
  "results/manual_verification/comprehensive_review_20260731/trial_review.csv",
);

const source = await readFile(sourcePath, "utf8");
const coreBytes = await readFile(corePath);
const reviewBytes = await readFile(reviewPath);

const canonicalCoreSha =
  "dda44c435b555d3f358a47b5885c659b9ae0554511959ca9d40f76bc9539f5a3";
const canonicalReviewSha =
  "c6945d114e3a2e0610dfd091bad8ea4e9bc17707db678e90f4e0f8058fc56501";

const digest = (value) =>
  createHash("sha256").update(value).digest("hex");

let moduleNonce = 0;

async function importLoader({
  coreSha = canonicalCoreSha,
  reviewSha = canonicalReviewSha,
} = {}) {
  let testSource = source
    .replace(
      'import "server-only";',
      'import "data:text/javascript,export%20{}";',
    )
    .replace(canonicalCoreSha, coreSha)
    .replace(canonicalReviewSha, reviewSha);

  testSource +=
    `\n// isolated-spend-source-test-${moduleNonce += 1}\n`;

  const compiled = ts.transpileModule(testSource, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;

  return import(
    `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
  );
}

test(
  "canonical DR-303 source validates exact frozen files and populations",
  async () => {
    const module = await importLoader();
    const result = await module.getSpendDecompositionSource();

    assert.equal(result.available, true);
    assert.equal(result.state, "available");
    assert.equal(result.coreRows.length, 900);
    assert.equal(result.reviewRows.length, 960);

    assert.equal(
      new Set(result.coreRows.map((row) => row.trial_id)).size,
      900,
    );
    assert.equal(
      new Set(result.reviewRows.map((row) => row.trial_id)).size,
      960,
    );

    assert.equal(
      new Set(result.coreRows.map((row) => row.arm_id)).size,
      15,
    );
    assert.equal(
      new Set(result.reviewRows.map((row) => row.arm_id)).size,
      16,
    );

    assert.equal(
      result.provenance.coreCostSha256,
      canonicalCoreSha,
    );
    assert.equal(
      result.provenance.reviewSha256,
      canonicalReviewSha,
    );

    const kimi = result.reviewRows.filter(
      (row) => row.arm_id === "router-kimi-k3",
    );

    assert.equal(kimi.length, 60);
    assert.equal(
      kimi.filter((row) => row.cost_usd === "").length,
      10,
    );

    assert.equal(
      result.coreRows.some(
        (row) => row.arm_id === "router-kimi-k3",
      ),
      false,
    );

    const exceptionSuccess = result.coreRows.filter(
      (row) =>
        row.outcome_bucket
        === "exception_with_success_signal",
    );

    assert.equal(exceptionSuccess.length, 16);
    assert.equal(
      exceptionSuccess.every(
        (row) => row.recorded_cost_usd === "",
      ),
      true,
    );
  },
);

test(
  "source hash pins reject altered core and review bytes",
  async () => {
    const module = await importLoader();

    const alteredCore = Buffer.from(coreBytes);
    alteredCore[alteredCore.length - 2] ^= 1;

    assert.throws(
      () =>
        module.validateSpendDecompositionSourceBytesForTests(
          alteredCore,
          reviewBytes,
        ),
      /core_cost_hash_mismatch/,
    );

    const alteredReview = Buffer.from(reviewBytes);
    alteredReview[alteredReview.length - 2] ^= 1;

    assert.throws(
      () =>
        module.validateSpendDecompositionSourceBytesForTests(
          coreBytes,
          alteredReview,
        ),
      /comprehensive_review_hash_mismatch/,
    );
  },
);

test(
  "self-consistently repinned population mutations still fail closed",
  async () => {
    const coreText = coreBytes.toString("utf8");
    const mutatedCoreText = coreText.replace(
      "router-anthropic-fable-5",
      "router-kimi-k3",
    );

    assert.notEqual(mutatedCoreText, coreText);

    const mutatedCore = Buffer.from(mutatedCoreText);
    const module = await importLoader({
      coreSha: digest(mutatedCore),
    });

    assert.throws(
      () =>
        module.validateSpendDecompositionSourceBytesForTests(
          mutatedCore,
          reviewBytes,
        ),
      /core_cost_source_(arm_count|arm_trial_count)_mismatch/,
    );

    const reviewText = reviewBytes.toString("utf8");
    const reviewArmToken = ",router-kimi-k3,";

    assert.equal(
      reviewText.split(reviewArmToken).length - 1,
      60,
    );

    const mutatedReviewText = reviewText.replace(
      reviewArmToken,
      ",router-kimi-k2.6,",
    );

    assert.notEqual(mutatedReviewText, reviewText);

    const mutatedReview = Buffer.from(mutatedReviewText);
    const reviewModule = await importLoader({
      reviewSha: digest(mutatedReview),
    });

    assert.throws(
      () =>
        reviewModule.validateSpendDecompositionSourceBytesForTests(
          coreBytes,
          mutatedReview,
        ),
      /comprehensive_review_source_arm_trial_count_mismatch/,
    );
  },
);

test(
  "DR-303 source accessor has no operational or J2 dependency",
  async () => {
    assert.match(source, /import "server-only"/);
    assert.match(
      source,
      /phase3_trial_cost_coverage_20260712\.tsv/,
    );
    assert.match(
      source,
      /comprehensive_review_20260731\/trial_review\.csv/,
    );

    assert.doesNotMatch(source, /SUPABASE/i);
    assert.doesNotMatch(source, /\bpostgres\b/i);
    assert.doesNotMatch(source, /\bR2\b/);
    assert.doesNotMatch(source, /https?:\/\//i);
    assert.doesNotMatch(source, /\bfetch\s*\(/);
    assert.doesNotMatch(source, /failure-taxonomy/i);
    assert.doesNotMatch(source, /failure_taxonomy/i);
    assert.doesNotMatch(source, /process\.env/);
  },
);
