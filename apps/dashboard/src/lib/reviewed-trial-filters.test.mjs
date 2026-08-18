import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "reviewed-trial-filters.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const filtersModule = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

const row = {
  trial_id: "00000000-0000-0000-0000-000000000001",
  arm_id: "arm-a",
  run_label: "arm-a/run-1",
  task_id: "suite:task-a",
  raw_outcome: "failure",
  failure_subtype: "test_assertion_failure",
  execution_validity: "substantive",
  termination_subtype: "timeout",
  policy_disposition: "provider_policy_refusal",
};

test("reviewed-trial filters use exact equality across every retained field", () => {
  const selection = filtersModule.selectReviewedTrialFilters({
    trial_id: row.trial_id,
    trial_arm: row.arm_id,
    trial_run: row.run_label,
    trial_task: row.task_id,
    trial_outcome: row.raw_outcome,
    trial_failure: row.failure_subtype,
    trial_execution: row.execution_validity,
    trial_termination: row.termination_subtype,
    trial_policy: row.policy_disposition,
  });
  assert.equal(filtersModule.matchesReviewedTrial(row, selection.filters), true);

  for (const [field, value] of [
    ["trialId", `${row.trial_id}-suffix`],
    ["armId", "arm"],
    ["runLabel", "arm-a/run"],
    ["taskId", "task-a"],
    ["rawOutcome", "fail"],
    ["failureSubtype", "assertion"],
    ["executionValidity", "invalid"],
    ["terminationSubtype", "none"],
    ["policyDisposition", "none_detected"],
  ]) {
    assert.equal(
      filtersModule.matchesReviewedTrial(row, { ...selection.filters, [field]: value }),
      false,
      field,
    );
  }
});

test("repeated namespaced filters fail closed without affecting unrelated queue parameters", () => {
  const selection = filtersModule.selectReviewedTrialFilters({
    trial_arm: ["arm-a", "arm-b"],
    trial_outcome: "failure",
    priority: "high",
  });
  assert.equal(selection.filters.armId, "");
  assert.equal(selection.filters.rawOutcome, "failure");
  assert.deepEqual(selection.repeatedFilterNames, ["trial_arm"]);
  assert.match(selection.warningMessage, /trial_arm/);
  assert.equal(Object.hasOwn(selection.filters, "priority"), false);
});

test("reviewed-trial ordering is deterministic by exact trial ID", () => {
  const rows = [{ trial_id: "c" }, { trial_id: "a" }, { trial_id: "b" }];
  assert.deepEqual(filtersModule.sortReviewedTrialsById(rows).map((item) => item.trial_id), ["a", "b", "c"]);
  assert.deepEqual(rows.map((item) => item.trial_id), ["c", "a", "b"]);
});

test("reviewed-trial pagination serializes validated filters instead of repeated raw values", () => {
  const raw = {
    trial_arm: ["arm-a", "arm-b"],
    trial_outcome: "failure",
    trial_page: "1",
    trial_page_size: "25",
    priority: "high",
    source_scope: "valid-imported",
  };
  const selection = filtersModule.selectReviewedTrialFilters(raw);
  assert.equal(selection.filters.armId, "");
  assert.equal(selection.filters.rawOutcome, "failure");
  assert.match(selection.warningMessage, /trial_arm/);

  const href = filtersModule.buildReviewedTrialPageHref(raw, selection.filters, 2, 50);
  const url = new URL(href, "https://dashboard.invalid");
  assert.equal(url.searchParams.has("trial_arm"), false);
  assert.equal(url.searchParams.get("trial_outcome"), "failure");
  assert.equal(url.searchParams.get("trial_page"), "2");
  assert.equal(url.searchParams.get("trial_page_size"), "50");
  assert.equal(url.searchParams.get("priority"), "high");
  assert.equal(url.searchParams.get("source_scope"), "valid-imported");
  assert.equal(url.hash, "#reviewed-trials");
});
