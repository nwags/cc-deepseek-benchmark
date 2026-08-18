import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "evidence-links.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const links = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("exact run and trial links safely encode identity and preserve validated navigation context", () => {
  assert.equal(
    links.buildExactRunHref("arm/run label?#", "phase3-core"),
    "/runs/arm%2Frun%20label%3F%23?source_scope=phase3-core",
  );
  assert.equal(
    links.buildExactTrialHref("trial/id ?", "all-imported"),
    "/trials/trial%2Fid%20%3F?source_scope=all-imported",
  );
  assert.match(links.EVIDENCE_SOURCE_SCOPE_NOTE, /navigation context only/);
  assert.match(links.EVIDENCE_SOURCE_SCOPE_NOTE, /never changes a destination evidence population/);
});

test("aggregate arm evidence stays arm-filtered and never invents a run", () => {
  const href = links.buildReviewedAggregateArmEvidenceHref("arm/id & one", "all-imported");
  const url = new URL(href, "https://dashboard.invalid");
  assert.equal(url.pathname, "/comprehensive-review");
  assert.equal(url.searchParams.get("trial_arm"), "arm/id & one");
  assert.equal(url.searchParams.get("source_scope"), "all-imported");
  assert.equal(url.searchParams.has("trial_run"), false);
  assert.equal(url.hash, "#reviewed-trials");
  assert.doesNotMatch(href, /latest/i);
});

test("Cost Coverage links accept reviewed scopes only and encode exact focus values", () => {
  for (const [scope, sourceScope] of [
    ["phase3-core", "valid-imported"],
    ["phase3-extended", "all-imported"],
  ]) {
    const href = links.buildCostCoverageHref(scope, {
      armId: "arm & one",
      runLabel: "arm/run?label",
      trialId: "00000000-0000-0000-0000-000000000001",
    }, sourceScope);
    const url = new URL(href, "https://dashboard.invalid");
    assert.equal(url.searchParams.get("scope"), scope);
    assert.equal(url.searchParams.get("arm_id"), "arm & one");
    assert.equal(url.searchParams.get("run_label"), "arm/run?label");
    assert.equal(url.searchParams.get("trial_id"), "00000000-0000-0000-0000-000000000001");
    assert.equal(url.searchParams.get("source_scope"), sourceScope);
  }
  assert.throws(() => links.buildCostCoverageHref("valid-imported"), /reviewed Phase 3 scope/);
  assert.throws(() => links.buildCostCoverageHref("all-imported"), /reviewed Phase 3 scope/);
});

test("reviewed trial evidence preserves validated navigation context independently", () => {
  const href = links.buildReviewedTrialEvidenceHref({
    trialId: "00000000-0000-0000-0000-000000000001",
    rawOutcome: "failure",
  }, "all-imported");
  const url = new URL(href, "https://dashboard.invalid");
  assert.equal(url.searchParams.get("trial_id"), "00000000-0000-0000-0000-000000000001");
  assert.equal(url.searchParams.get("trial_outcome"), "failure");
  assert.equal(url.searchParams.get("source_scope"), "all-imported");
  assert.equal(url.hash, "#reviewed-trials");
});

test("failure evidence links use the exact frozen predicate and reject unsupported count semantics", () => {
  const href = links.buildReviewedFailureEvidenceHref({
    source: "frozen_comprehensive_review",
    armId: "arm-a",
    runLabel: "arm-a/run-1",
    failureSubtype: "test_assertion_failure",
    sourceScope: "phase3-core",
  });
  const url = new URL(href, "https://dashboard.invalid");
  assert.equal(url.searchParams.get("trial_arm"), "arm-a");
  assert.equal(url.searchParams.get("trial_run"), "arm-a/run-1");
  assert.equal(url.searchParams.get("trial_outcome"), "failure");
  assert.equal(url.searchParams.get("trial_failure"), "test_assertion_failure");
  assert.equal(url.searchParams.get("source_scope"), "phase3-core");
  assert.equal(url.hash, "#reviewed-trials");
  assert.equal(
    links.buildReviewedFailureEvidenceHref({ source: "operational_or_unsupported" }),
    null,
  );
});

test("source_scope accepts only known context IDs and fails repeated or arbitrary values safely", () => {
  assert.deepEqual(links.selectEvidenceSourceScope(undefined), {
    sourceScope: null, warning: null, warningMessage: null,
  });
  for (const value of ["phase3-core", "phase3-extended", "valid-imported", "all-imported"]) {
    assert.equal(links.selectEvidenceSourceScope(value).sourceScope, value);
  }
  assert.equal(links.selectEvidenceSourceScope("other").warning, "invalid_source_scope");
  assert.equal(links.selectEvidenceSourceScope("").warning, "invalid_source_scope");
  assert.equal(links.selectEvidenceSourceScope(["phase3-core", "phase3-extended"]).warning, "repeated_source_scope");
});

test("cost focus rejects repeated parameters and malformed exact trial identity", () => {
  assert.equal(links.selectCostProvenanceFocus({}).focus, null);
  assert.equal(
    links.selectCostProvenanceFocus({ armId: ["arm-a", "arm-b"] }).warning,
    "repeated_focus",
  );
  assert.equal(
    links.selectCostProvenanceFocus({ trialId: "not-a-uuid" }).warning,
    "invalid_trial_id",
  );
  assert.deepEqual(
    links.selectCostProvenanceFocus({
      armId: "arm-a",
      runLabel: "arm-a/run-1",
      trialId: "00000000-0000-0000-0000-000000000001",
    }).focus,
    {
      armId: "arm-a",
      runLabel: "arm-a/run-1",
      trialId: "00000000-0000-0000-0000-000000000001",
    },
  );
});
