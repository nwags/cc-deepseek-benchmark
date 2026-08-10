import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));

function moduleUrl(source) {
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
}

const canonical = JSON.parse(await readFile(
  resolve(here, "../../../../results/phase3/reporting/phase3_reviewed_run_selection_20260809.json"),
  "utf8",
));
const generatedSource = await readFile(
  resolve(here, "../generated/phase3-reviewed-run-selection-data.ts"),
  "utf8",
);
const generatedModuleUrl = moduleUrl(generatedSource);
const { default: generatedSelection } = await import(generatedModuleUrl);

const comparisonGeneratedSource = await readFile(
  resolve(here, "../generated/phase3-reviewed-comparison-data.ts"),
  "utf8",
);
const comparisonGeneratedModuleUrl = moduleUrl(comparisonGeneratedSource);
const comparisonLoaderSource = (await readFile(join(here, "phase3-reviewed-comparison.ts"), "utf8"))
  .replace(
    '"../generated/phase3-reviewed-comparison-data"',
    `"${comparisonGeneratedModuleUrl}"`,
  );
const comparisonLoaderModuleUrl = moduleUrl(comparisonLoaderSource);

const loaderSource = (await readFile(join(here, "phase3-reviewed-run-selection.ts"), "utf8"))
  .replace(
    '"../generated/phase3-reviewed-run-selection-data"',
    `"${generatedModuleUrl}"`,
  )
  .replace(
    '"./phase3-reviewed-comparison"',
    `"${comparisonLoaderModuleUrl}"`,
  );
const loaderModuleUrl = moduleUrl(loaderSource);
const {
  PHASE3_REVIEWED_RUN_SELECTION,
  getReviewedRunSelectionScope,
  getReviewedSelectedRun,
  getReviewedSelectedRunLabels,
  validatePhase3ReviewedRunSelection,
} = await import(loaderModuleUrl);

const clone = () => structuredClone(canonical);

test("app-local generated run selection is deeply equivalent to canonical JSON", () => {
  assert.deepEqual(generatedSelection, canonical);

  const changedCanonical = clone();
  changedCanonical.reviewedAt = "2026-08-10";
  assert.throws(() => assert.deepEqual(generatedSelection, changedCanonical));

  const changedGenerated = structuredClone(generatedSelection);
  changedGenerated.scopes["phase3-core"].trialCount = 899;
  assert.throws(() => assert.deepEqual(changedGenerated, canonical));
});

test("loader accepts, cross-checks, and freezes the checked contract", () => {
  assert.equal(PHASE3_REVIEWED_RUN_SELECTION.schemaVersion, "phase3-reviewed-run-selection-v1");
  assert.equal(PHASE3_REVIEWED_RUN_SELECTION.reviewedAt, "2026-08-09");
  assert.equal(PHASE3_REVIEWED_RUN_SELECTION.generator.name,
    "scripts/generate_phase3_reviewed_run_selection.py");
  assert.equal(PHASE3_REVIEWED_RUN_SELECTION.scopes["phase3-core"].selections.length, 15);
  assert.equal(PHASE3_REVIEWED_RUN_SELECTION.scopes["phase3-extended"].selections.length, 16);
  assert.equal(Object.isFrozen(PHASE3_REVIEWED_RUN_SELECTION), true);
  assert.equal(Object.isFrozen(
    PHASE3_REVIEWED_RUN_SELECTION.scopes["phase3-extended"].selections,
  ), true);
});

test("loader rejects schema, date, generator, and scope-set changes", () => {
  const schema = clone();
  schema.schemaVersion = "future";
  assert.throws(() => validatePhase3ReviewedRunSelection(schema), /unsupported.*schema version/i);

  const date = clone();
  date.reviewedAt = "2026-08-10";
  assert.throws(() => validatePhase3ReviewedRunSelection(date), /reviewedAt/);

  const generator = clone();
  generator.generator.name = "scripts/other.py";
  assert.throws(() => validatePhase3ReviewedRunSelection(generator), /generator identity/);

  const missingScope = clone();
  delete missingScope.scopes["phase3-core"];
  assert.throws(() => validatePhase3ReviewedRunSelection(missingScope), /exactly phase3-core/);

  const extraScope = clone();
  extraScope.scopes["phase3-other"] = structuredClone(extraScope.scopes["phase3-core"]);
  assert.throws(() => validatePhase3ReviewedRunSelection(extraScope), /exactly phase3-core/);
});

test("loader rejects duplicate arms and selected run labels", () => {
  const duplicateArm = clone();
  duplicateArm.scopes["phase3-core"].selections.push(
    structuredClone(duplicateArm.scopes["phase3-core"].selections[0]),
  );
  assert.throws(() => validatePhase3ReviewedRunSelection(duplicateArm), /duplicate arm IDs/);

  const duplicateRun = clone();
  duplicateRun.scopes["phase3-core"].selections[1].selectedRunLabel =
    duplicateRun.scopes["phase3-core"].selections[0].selectedRunLabel;
  assert.throws(
    () => validatePhase3ReviewedRunSelection(duplicateRun),
    /does not match its arm ID|duplicate selected run labels/,
  );
});

test("loader enforces Kimi scope, label, and provider-log qualifications", () => {
  const coreKimi = clone();
  coreKimi.scopes["phase3-core"].selections[0].armId = "router-kimi-k3";
  coreKimi.scopes["phase3-core"].selections[0].selectedRunLabel =
    "router-kimi-k3/2026-07-11__12-15-55";
  coreKimi.scopes["phase3-core"].selections.sort((left, right) =>
    left.armId.localeCompare(right.armId));
  assert.throws(() => validatePhase3ReviewedRunSelection(coreKimi), /router-kimi-k3/);

  const wrongLabel = clone();
  const kimi = wrongLabel.scopes["phase3-extended"].selections.find(
    (selection) => selection.armId === "router-kimi-k3",
  );
  kimi.selectedRunLabel = "router-kimi-k3/2099-01-01__00-00-00";
  assert.throws(() => validatePhase3ReviewedRunSelection(wrongLabel), /selected run label/);

  const missingQualification = clone();
  const unqualifiedKimi = missingQualification.scopes["phase3-extended"].selections.find(
    (selection) => selection.armId === "router-kimi-k3",
  );
  unqualifiedKimi.providerLogAllocationQualification = null;
  assert.throws(() => validatePhase3ReviewedRunSelection(missingQualification), /qualifications/);
});

test("loader rejects run selection that disagrees with F1 reviewed membership", () => {
  const mismatch = clone();
  for (const scopeId of ["phase3-core", "phase3-extended"]) {
    const selection = mismatch.scopes[scopeId].selections.find(
      (row) => row.armId === "router-gpt-5.5",
    );
    selection.armId = "router-unreviewed";
    selection.selectedRunLabel = selection.selectedRunLabel.replace(
      "router-gpt-5.5/",
      "router-unreviewed/",
    );
    mismatch.scopes[scopeId].selections.sort((left, right) =>
      left.armId.localeCompare(right.armId));
  }
  assert.throws(() => validatePhase3ReviewedRunSelection(mismatch), /reviewed comparison membership/);
});

test("loader rejects changed completeness or historical policy", () => {
  const incomplete = clone();
  const coreRow = incomplete.scopes["phase3-core"].selections[0];
  const extendedRow = incomplete.scopes["phase3-extended"].selections.find(
    (row) => row.armId === coreRow.armId,
  );
  coreRow.trialCount = 59;
  extendedRow.trialCount = 59;
  incomplete.scopes["phase3-core"].trialCount = 899;
  incomplete.scopes["phase3-extended"].trialCount = 959;
  assert.throws(() => validatePhase3ReviewedRunSelection(incomplete), /complete reviewed 60-trial run/);

  const policy = clone();
  policy.selectionPolicy.invalidRunExcluded = false;
  assert.throws(() => validatePhase3ReviewedRunSelection(policy), /validity requirements/);
});

test("safe lookup helpers never fall back to another arm", () => {
  const core = getReviewedRunSelectionScope("phase3-core");
  assert.equal(core.selectedRunCount, 15);
  assert.equal(
    getReviewedSelectedRun("phase3-extended", "router-kimi-k3")?.selectedRunLabel,
    "router-kimi-k3/2026-07-22__17-51-05",
  );
  assert.equal(getReviewedSelectedRun("phase3-extended", "unknown-arm"), null);

  const labels = getReviewedSelectedRunLabels("phase3-extended");
  assert.equal(labels.length, 16);
  assert.equal(new Set(labels).size, 16);
  assert.equal(Object.isFrozen(labels), true);
  assert.ok(labels.includes("router-kimi-k3/2026-07-22__17-51-05"));
});

test("input path/role/hash validation fails closed", () => {
  const badPath = clone();
  badPath.inputs[0].path = "results/unreviewed.json";
  assert.throws(() => validatePhase3ReviewedRunSelection(badPath), /path or role|input path/);

  const badRole = clone();
  badRole.inputs[0].role = "unreviewed";
  assert.throws(() => validatePhase3ReviewedRunSelection(badRole), /path or role|input path/);

  const badHash = clone();
  badHash.inputs[0].sha256 = "not-a-hash";
  assert.throws(() => validatePhase3ReviewedRunSelection(badHash), /sha256 is invalid/);
});
