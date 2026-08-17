import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const registryPath = resolve(here, "../../../../configs/dashboard/failure_taxonomy_v1.json");
const registry = JSON.parse(await readFile(registryPath, "utf8"));
const source = await readFile(join(here, "failure-taxonomy.ts"), "utf8");
const imports = [...source.matchAll(/from\s+["']([^"']+)["']/g)].map((match) => match[1]);
const sourceWithEmbeddedRegistry = source.replace(
  'import rawRegistry from "../../../../configs/dashboard/failure_taxonomy_v1.json";',
  `const rawRegistry = ${JSON.stringify(registry)};`,
);
const compiled = ts.transpileModule(sourceWithEmbeddedRegistry, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const taxonomy = await import(moduleUrl);

const expectedValues = {
  response_path_class: [
    "synthetic_retry_empty_completion",
    "empty_completion_after_long_api_path_wait",
    "thinking_only_empty_completion",
    "empty_completion",
    "invalid_response_path",
    "unknown",
    "not_applicable",
  ],
  verifier_failure_category: [
    "none",
    "verifier_environment_issue",
    "syntax_or_compile_error",
    "dependency_or_import_error",
    "wrong_file_or_path",
    "timeout_inside_verifier",
    "runtime_exception_in_solution",
    "test_assertion_failure",
    "missing_or_wrong_output",
    "no_meaningful_code_change",
    "partial_solution",
    "unclassified_failure",
  ],
  assertion_failure_category: [
    "none",
    "performance_threshold_failure",
    "numerical_or_data_mismatch",
    "missing_expected_file_or_content",
    "behavior_mismatch",
    "output_mismatch",
    "unclassified_assertion",
  ],
  trajectory_disposition: [
    "successful_completion",
    "no_substantive_attempt",
    "early_abandonment",
    "partial_implementation",
    "plausible_but_incorrect_completion",
    "near_miss_cleanup_or_packaging_only",
    "near_miss_one_behavioral_defect",
    "repeated_unproductive_iteration",
    "timeout_after_meaningful_progress",
    "completed_work_with_verifier_or_infrastructure_issue",
    "indeterminate",
  ],
};

test("TypeScript consumes the canonical registry and exposes the exact ordered enum sets", () => {
  assert.deepEqual(imports, ["../../../../configs/dashboard/failure_taxonomy_v1.json"]);
  assert.equal(taxonomy.FAILURE_TAXONOMY_REGISTRY.schema_version, "dashboard-failure-taxonomy-registry-v1");
  assert.equal(taxonomy.FAILURE_TAXONOMY_REGISTRY.contract_status, "foundation_only");
  assert.equal(Object.isFrozen(taxonomy.FAILURE_TAXONOMY_REGISTRY), true);

  for (const [axisId, ids] of Object.entries(expectedValues)) {
    const axis = taxonomy.getFailureTaxonomyAxis(axisId);
    assert.deepEqual(axis.entries.map((entry) => entry.id), ids);
    assert.equal(Object.isFrozen(axis), true);
    assert.equal(Object.isFrozen(axis.entries), true);
  }
});

test("lookup returns registry display metadata and no legacy suspect-noop primary value", () => {
  const success = taxonomy.getFailureTaxonomyEntry("trajectory_disposition", "successful_completion");
  assert.equal(success.label, "Successful completion");
  assert.match(success.definition, /successful/);
  assert.equal(taxonomy.getFailureTaxonomyEntry("response_path_class", "suspect_noop_zero_token"), null);
  assert.equal(taxonomy.getFailureTaxonomyEntry("response_path_class", "missing"), null);
});

test("selection policy makes order display-only and success an evidence-qualified fallback", () => {
  const policy = taxonomy.FAILURE_TAXONOMY_REGISTRY.selection_policy;
  assert.match(policy.entry_order_semantics, /presentation\/display order only/);
  assert.match(policy.entry_order_semantics, /not classifier precedence/);
  assert.match(policy.axis_independence, /independent axes/);
  assert.match(policy.ordinary_success_fallback, /after checking/);

  const success = taxonomy.getFailureTaxonomyEntry("trajectory_disposition", "successful_completion");
  assert.match(success.definition, /does not support a more specific anomalous trajectory disposition/);
  assert.match(success.definition, /never overrides stronger positive trajectory evidence/);
});

test("runtime validation rejects duplicate ids, invalid ordering, and incomplete diagnosis fields", () => {
  const duplicate = structuredClone(registry);
  duplicate.axes[0].entries[1].id = duplicate.axes[0].entries[0].id;
  assert.throws(() => taxonomy.validateFailureTaxonomyRegistry(duplicate), /ids must be unique/);

  const invalidOrder = structuredClone(registry);
  invalidOrder.axes[0].entries[1].order = 8;
  assert.throws(() => taxonomy.validateFailureTaxonomyRegistry(invalidOrder), /ordering must be contiguous/);

  const missingField = structuredClone(registry);
  missingField.future_output_contract.diagnosis_object_fields = missingField.future_output_contract
    .diagnosis_object_fields.filter((field) => field.name !== "evidence_basis");
  assert.throws(() => taxonomy.validateFailureTaxonomyRegistry(missingField), /evidence_basis is required/);
});

test("the client-safe loader introduces no database, reviewed-loader, or artifact-reader import", () => {
  assert.deepEqual(imports, ["../../../../configs/dashboard/failure_taxonomy_v1.json"]);
  for (const forbidden of ["./db", "review-data", "phase3-reviewed", "artifact-content", "@aws-sdk", "pg"]) {
    assert.equal(imports.some((specifier) => specifier.includes(forbidden)), false, forbidden);
  }
});
