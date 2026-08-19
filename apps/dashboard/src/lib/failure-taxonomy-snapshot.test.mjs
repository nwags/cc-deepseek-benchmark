import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import { cp, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../../..");
const canonicalDirectory = resolve(root, "results/manual_verification/failure_taxonomy_20260813");
const registry = JSON.parse(await readFile(resolve(root, "configs/dashboard/failure_taxonomy_v1.json"), "utf8"));
const source = await readFile(join(here, "failure-taxonomy-snapshot.ts"), "utf8");
const digest = (value) => createHash("sha256").update(value).digest("hex");
const canonicalManifestSha = "71e1c0fbee99d07fe18512902ed62c3fa2eb752d9e08c68c3d75a1dc1a4e3088";
const canonicalOutputShas = {
  "trial_failure_taxonomy.jsonl": "ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1",
  "taxonomy_counts.json": "e1284625f3e48e2dcb69a569acb0e73ff326410ffd8b9bc8878cfe5b8863e9cd",
  "review_queue.csv": "aeb8eab2037ce5dd11bb0ef94cda4e0c28013b9c2d887aecdf129d77ea78e883",
};
const previousDirectory = process.env.DASHBOARD_FAILURE_TAXONOMY_DIR;
let moduleNonce = 0;

const taxonomyStub = `data:text/javascript;base64,${Buffer.from(`
  export const FAILURE_TAXONOMY_REGISTRY = ${JSON.stringify(registry)};
  export const getFailureTaxonomyEntry = (axisId, value) =>
    FAILURE_TAXONOMY_REGISTRY.axes.find((axis) => axis.id === axisId)?.entries.find((entry) => entry.id === value) ?? null;
`).toString("base64")}`;

async function importLoader({
  manifestSha = canonicalManifestSha,
  outputShas = canonicalOutputShas,
} = {}) {
  let testSource = source
    .replace('import "server-only";', 'import "data:text/javascript,export%20{}";')
    .replace('from "./failure-taxonomy"', `from "${taxonomyStub}"`)
    .replace(canonicalManifestSha, manifestSha);
  for (const [name, canonicalSha] of Object.entries(canonicalOutputShas)) {
    testSource = testSource.replace(canonicalSha, outputShas[name] ?? canonicalSha);
  }
  testSource += `\n// isolated-test-module-${moduleNonce += 1}\n`;
  const compiled = ts.transpileModule(testSource, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}

async function readManifest(directory) {
  return JSON.parse(await readFile(join(directory, "failure_taxonomy_manifest.json"), "utf8"));
}

async function writeManifest(directory, manifest) {
  await writeFile(join(directory, "failure_taxonomy_manifest.json"), `${JSON.stringify(manifest)}\n`);
}

async function rebindOutput(directory, name, contents, rows = undefined) {
  await writeFile(join(directory, name), contents);
  const manifest = await readManifest(directory);
  manifest.outputs[name].sha256 = digest(contents);
  manifest.outputs[name].bytes = Buffer.byteLength(contents);
  if (rows !== undefined) manifest.outputs[name].rows = rows;
  await writeManifest(directory, manifest);
}

async function mutateFirstTrial(directory, mutate) {
  const filePath = join(directory, "trial_failure_taxonomy.jsonl");
  const lines = (await readFile(filePath, "utf8")).trimEnd().split("\n");
  const row = JSON.parse(lines[0]);
  await mutate(row, lines);
  lines[0] = JSON.stringify(row);
  await rebindOutput(directory, "trial_failure_taxonomy.jsonl", `${lines.join("\n")}\n`, lines.length);
}

async function fixtureLoader(directory, { repinOutputs = true } = {}) {
  const manifestBytes = await readFile(join(directory, "failure_taxonomy_manifest.json"));
  const manifest = JSON.parse(manifestBytes.toString("utf8"));
  return importLoader({
    manifestSha: digest(manifestBytes),
    outputShas: repinOutputs
      ? Object.fromEntries(Object.keys(canonicalOutputShas).map((name) => [name, manifest.outputs[name].sha256]))
      : canonicalOutputShas,
  });
}

async function loadFrom(module, directory) {
  process.env.DASHBOARD_FAILURE_TAXONOMY_DIR = directory;
  module.resetFailureTaxonomySnapshotCacheForTests();
  return module.getFailureTaxonomySnapshot();
}

async function assertInvalidFixture(directory, expectedReason) {
  const module = await fixtureLoader(directory);
  const result = await loadFrom(module, directory);
  assert.equal(result.state, "invalid");
  assert.equal(result.available, false);
  assert.deepEqual(result.rows, []);
  assert.match(result.message, expectedReason);

  const reviewedSource =
    await module.getFailureTaxonomyReviewedSource();
  assert.equal(reviewedSource.state, "invalid");
  assert.equal(reviewedSource.available, false);
  assert.deepEqual(reviewedSource.reviewRows, []);
  assert.deepEqual(reviewedSource.taxonomyRows, []);
  assert.match(reviewedSource.message, expectedReason);
}

async function copyFixture(fixtureRoot, name) {
  const directory = join(fixtureRoot, name);
  await cp(canonicalDirectory, directory, { recursive: true });
  return directory;
}

function registryEntry(axisId, value) {
  return registry.axes.find((axis) => axis.id === axisId).entries.find((entry) => entry.id === value);
}

test.after(() => {
  if (previousDirectory === undefined) delete process.env.DASHBOARD_FAILURE_TAXONOMY_DIR;
  else process.env.DASHBOARD_FAILURE_TAXONOMY_DIR = previousDirectory;
});

test("canonical loader validates 960 exact-ID rows and exposes canonical filtering", { concurrency: false }, async () => {
  delete process.env.DASHBOARD_FAILURE_TAXONOMY_DIR;
  const snapshotModule = await importLoader();
  const snapshot = await snapshotModule.getFailureTaxonomySnapshot();
  assert.equal(snapshot.available, true);
  assert.equal(snapshot.state, "available");
  assert.equal(snapshot.rows.length, 960);
  assert.equal(new Set(snapshot.rows.map((row) => row.trial_id)).size, 960);
  assert.equal(snapshot.provenance.scope, "phase3-extended");
  assert.equal(snapshot.provenance.reviewQueueCount, 243);

  const reviewedSource =
    await snapshotModule.getFailureTaxonomyReviewedSource();
  assert.equal(reviewedSource.available, true);
  assert.equal(reviewedSource.state, "available");
  assert.equal(reviewedSource.reviewRows.length, 960);
  assert.equal(reviewedSource.taxonomyRows.length, 960);
  assert.deepEqual(
    new Set(reviewedSource.reviewRows.map((row) => row.trial_id)),
    new Set(snapshot.rows.map((row) => row.trial_id)),
  );
  assert.equal(
    reviewedSource.reviewRows.filter(
      (row) => row.raw_outcome === "failure",
    ).length,
    370,
  );
  assert.equal(
    reviewedSource.reviewRows.filter(
      (row) =>
        row.raw_outcome === "success"
        && row.activity_subtype
          === "timeout_after_meaningful_activity",
    ).length,
    19,
  );
  assert.equal(
    reviewedSource.reviewRows.filter(
      (row) =>
        row.raw_outcome === "not_recorded"
        && row.activity_subtype
          === "timeout_after_meaningful_activity",
    ).length,
    28,
  );

  const timeout = await snapshotModule.getFailureTaxonomyForTrial("06069bcf-6f36-4000-aa41-85501e197164");
  assert.equal(timeout.status, "available");
  assert.equal(timeout.trial.trajectory_disposition.value, "timeout_after_meaningful_progress");

  const anomalies = new Map([
    ["7eceb1c8-4a7b-4899-9650-b54f7d432d24", "empty_completion_after_long_api_path_wait"],
    ["b59e45f0-050e-448e-8a97-abee2f4b89c6", "thinking_only_empty_completion"],
    ["9ce7bde7-ce6e-4f32-93af-04848273f93c", "synthetic_retry_empty_completion"],
    ["6ebd9061-3c69-443d-8a76-be789b50344d", "synthetic_retry_empty_completion"],
  ]);
  for (const [trialId, expected] of anomalies) {
    const result = await snapshotModule.getFailureTaxonomyForTrial(trialId);
    assert.equal(result.status, "available");
    assert.equal(result.trial.response_path_class.value, expected);
  }

  const filters = snapshotModule.normalizeFailureTaxonomyFilters({
    verifier_failure_category: "dependency_or_import_error",
    response_path_class: "not_applicable",
  });
  assert.deepEqual(filters, {
    response_path_class: "not_applicable",
    verifier_failure_category: "dependency_or_import_error",
  });
  assert.equal(snapshotModule.filterFailureTaxonomyRows(snapshot.rows, filters).length, 5);
  assert.deepEqual(snapshotModule.normalizeFailureTaxonomyFilters({ trajectory_disposition: "not-a-value" }), {});

  const outside = await snapshotModule.getFailureTaxonomyForTrial("00000000-0000-4000-8000-000000000000");
  assert.equal(outside.status, "unavailable");
  assert.equal(outside.reason, "outside_frozen_scope");
  assert.match(outside.message, /not the taxonomy value ‘Not applicable’/);
});

test("canonical manifest pin rejects altered and self-consistently rebound snapshots", { concurrency: false }, async (t) => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), "failure-taxonomy-pin-"));
  const snapshotModule = await importLoader();
  try {
    await t.test("byte-only canonical manifest SHA mismatch", async () => {
      const directory = await copyFixture(fixtureRoot, "manifest-byte-change");
      const manifestPath = join(directory, "failure_taxonomy_manifest.json");
      await writeFile(manifestPath, `${await readFile(manifestPath, "utf8")}\n`);
      const result = await loadFrom(snapshotModule, directory);
      assert.equal(result.state, "invalid");
      assert.deepEqual(result.rows, []);
      assert.match(result.message, /canonical_manifest_hash_mismatch/);
    });

    await t.test("valid alternate diagnosis with consistent counts and manifest rebinding", async () => {
      const directory = await copyFixture(fixtureRoot, "self-consistent-alternate");
      await mutateFirstTrial(directory, (row) => {
        assert.equal(row.response_path_class.value, "not_applicable");
        const replacement = registryEntry("response_path_class", "unknown");
        row.response_path_class.value = replacement.id;
        row.response_path_class.label = replacement.label;
        row.response_path_class.definition = replacement.definition;
      });
      const counts = JSON.parse(await readFile(join(directory, "taxonomy_counts.json"), "utf8"));
      counts.axis_distributions.response_path_class.not_applicable -= 1;
      counts.axis_distributions.response_path_class.unknown += 1;
      await rebindOutput(directory, "taxonomy_counts.json", `${JSON.stringify(counts, null, 2)}\n`);

      const rejected = await loadFrom(snapshotModule, directory);
      assert.equal(rejected.state, "invalid");
      assert.deepEqual(rejected.rows, []);
      assert.match(rejected.message, /canonical_manifest_hash_mismatch/);

      const manifestRepinnedOnly = await fixtureLoader(directory, { repinOutputs: false });
      const outputIdentityRejected = await loadFrom(manifestRepinnedOnly, directory);
      assert.equal(outputIdentityRejected.state, "invalid");
      assert.match(outputIdentityRejected.message, /frozen_output_identity_mismatch/);

      const fullyRepinnedTestModule = await fixtureLoader(directory);
      const otherwiseSelfConsistent = await loadFrom(fullyRepinnedTestModule, directory);
      assert.equal(otherwiseSelfConsistent.state, "available");
      assert.equal(otherwiseSelfConsistent.rows.length, 960);
    });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test("diagnosis schema and evidence mutations fail closed after valid test-only rebinding", { concurrency: false }, async (t) => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), "failure-taxonomy-diagnosis-"));
  try {
    const cases = [
      ["wrong stored label", (row) => { row.response_path_class.label = "Incorrect stored label"; }, /diagnosis_registry_mismatch/],
      ["wrong stored definition", (row) => { row.response_path_class.definition = "Incorrect stored definition"; }, /diagnosis_registry_mismatch/],
      ["unknown enum", (row) => { row.response_path_class.value = "not_in_registry"; }, /diagnosis_registry_mismatch/],
      ["invalid confidence", (row) => { row.response_path_class.confidence = "certain"; }, /diagnosis_confidence_invalid/],
      ["empty evidence basis", (row) => { row.response_path_class.evidence_basis = []; }, /diagnosis_evidence_basis_invalid/],
      ["malformed evidence basis", (row) => { row.response_path_class.evidence_basis = ["rule=valid", "raw\nexcerpt"]; }, /diagnosis_evidence_basis_invalid/],
      ["malformed artifact IDs", (row) => { row.response_path_class.supporting_artifact_ids = ["not-an-artifact-id"]; }, /diagnosis_artifact_ids_invalid/],
      ["forbidden diagnosis field", (row) => { row.response_path_class.raw_verifier_excerpt = "must not be retained"; }, /diagnosis_fields_invalid/],
      ["forbidden trial field", (row) => { row.private_reasoning = "must not be retained"; }, /trial_fields_invalid/],
    ];
    for (const [name, mutate, reason] of cases) {
      await t.test(name, async () => {
        const directory = await copyFixture(fixtureRoot, name.replaceAll(" ", "-"));
        await mutateFirstTrial(directory, mutate);
        await assertInvalidFixture(directory, reason);
      });
    }

    await t.test("artifact belongs to another trial rather than the same reviewed inventory", async () => {
      const directory = await copyFixture(fixtureRoot, "cross-trial-artifact");
      const sourceRows = (await readFile(join(directory, "trial_failure_taxonomy.jsonl"), "utf8"))
        .trimEnd().split("\n").slice(0, 10).map(JSON.parse);
      const firstArtifacts = new Set(sourceRows[0].response_path_class.supporting_artifact_ids);
      const foreignArtifact = sourceRows.slice(1).flatMap((row) =>
        row.response_path_class.supporting_artifact_ids).find((artifactId) => !firstArtifacts.has(artifactId));
      assert.ok(foreignArtifact);
      await mutateFirstTrial(directory, (row) => {
        row.response_path_class.supporting_artifact_ids = [foreignArtifact];
      });
      await assertInvalidFixture(directory, /taxonomy_artifact_not_bound_to_trial_evidence/);
    });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test("counts, queue, and trial-set mutations fail closed after output rebinding", { concurrency: false }, async (t) => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), "failure-taxonomy-relations-"));
  try {
    await t.test("taxonomy counts distribution mismatch", async () => {
      const directory = await copyFixture(fixtureRoot, "counts");
      const counts = JSON.parse(await readFile(join(directory, "taxonomy_counts.json"), "utf8"));
      counts.axis_distributions.response_path_class.not_applicable += 1;
      await rebindOutput(directory, "taxonomy_counts.json", `${JSON.stringify(counts, null, 2)}\n`);
      await assertInvalidFixture(directory, /axis_distribution_mismatch/);
    });

    await t.test("review queue union mismatch", async () => {
      const directory = await copyFixture(fixtureRoot, "queue");
      const lines = (await readFile(join(directory, "review_queue.csv"), "utf8")).trimEnd().split("\n");
      const contents = `${[lines[0], ...lines.slice(2)].join("\n")}\n`;
      await rebindOutput(directory, "review_queue.csv", contents, lines.length - 2);
      await assertInvalidFixture(directory, /review_queue_union_mismatch/);
    });

    await t.test("duplicate taxonomy trial ID", async () => {
      const directory = await copyFixture(fixtureRoot, "duplicate-trial");
      const filePath = join(directory, "trial_failure_taxonomy.jsonl");
      const lines = (await readFile(filePath, "utf8")).trimEnd().split("\n");
      const first = JSON.parse(lines[0]);
      const second = JSON.parse(lines[1]);
      second.trial_id = first.trial_id;
      lines[1] = JSON.stringify(second);
      await rebindOutput(directory, "trial_failure_taxonomy.jsonl", `${lines.join("\n")}\n`, lines.length);
      await assertInvalidFixture(directory, /taxonomy_trial_set_invalid/);
    });

    await t.test("unique but wrong taxonomy trial set", async () => {
      const directory = await copyFixture(fixtureRoot, "wrong-trial-set");
      await mutateFirstTrial(directory, (row) => { row.trial_id = "00000000-0000-4000-8000-000000000000"; });
      await assertInvalidFixture(directory, /frozen_trial_set_mismatch/);
    });
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test("unbound output changes and altered manifest schema/scope fail closed", { concurrency: false }, async (t) => {
  const fixtureRoot = await mkdtemp(join(tmpdir(), "failure-taxonomy-boundary-"));
  const snapshotModule = await importLoader();
  try {
    await t.test("output bytes differ from the pinned manifest", async () => {
      const directory = await copyFixture(fixtureRoot, "output");
      await writeFile(join(directory, "taxonomy_counts.json"), "{}\n");
      const result = await loadFrom(snapshotModule, directory);
      assert.equal(result.state, "invalid");
      assert.deepEqual(result.rows, []);
      assert.match(result.message, /output_hash_or_size_mismatch/);
    });

    for (const [name, mutate] of [
      ["schema", (manifest) => { manifest.schema_version = "unsupported"; }],
      ["scope", (manifest) => { manifest.scope_fingerprint = "0".repeat(64); }],
    ]) {
      await t.test(`${name} mismatch reaches its deep check with a test-only manifest pin`, async () => {
        const directory = await copyFixture(fixtureRoot, name);
        const manifest = await readManifest(directory);
        mutate(manifest);
        await writeManifest(directory, manifest);
        await assertInvalidFixture(directory, name === "schema" ? /manifest_schema_mismatch/ : /review_scope_or_schema_mismatch/);
      });
    }
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
});

test("server loader has no database, R2, HTTP, classifier-runtime, or client fallback dependency", () => {
  const imports = [...source.matchAll(/from\s+["']([^"']+)["']/g)].map((match) => match[1]);
  for (const forbidden of ["./db", "dashboard-data", "@aws-sdk", "fetch", "http", "failure_taxonomy_classifier", "generate_failure_taxonomy_snapshot"]) {
    assert.equal(imports.some((specifier) => specifier.includes(forbidden)), false, forbidden);
  }
  assert.doesNotMatch(source, /arm_id.*get\(|task_id.*get\(|run_label.*get\(/);
  assert.match(source, /byTrialId\.get\(trialId\)/);
});
