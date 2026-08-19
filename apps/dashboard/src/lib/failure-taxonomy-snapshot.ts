import "server-only";
import path from "node:path";
import { createHash } from "node:crypto";
import {
  FAILURE_TAXONOMY_REGISTRY,
  FailureTaxonomyAxisId,
  getFailureTaxonomyEntry,
} from "./failure-taxonomy";

export const FAILURE_TAXONOMY_AXIS_IDS = [
  "response_path_class",
  "verifier_failure_category",
  "assertion_failure_category",
  "trajectory_disposition",
] as const satisfies readonly FailureTaxonomyAxisId[];

const SNAPSHOT_SCHEMA_VERSION = "failure-taxonomy-manifest-v1";
const FROZEN_CANONICAL_MANIFEST_SHA256 = "71e1c0fbee99d07fe18512902ed62c3fa2eb752d9e08c68c3d75a1dc1a4e3088";
const FROZEN_CLASSIFICATION_OUTPUT_SHA256 = {
  "trial_failure_taxonomy.jsonl": "ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1",
  "taxonomy_counts.json": "e1284625f3e48e2dcb69a569acb0e73ff326410ffd8b9bc8878cfe5b8863e9cd",
  "review_queue.csv": "aeb8eab2037ce5dd11bb0ef94cda4e0c28013b9c2d887aecdf129d77ea78e883",
} as const;
const TRIAL_SCHEMA_VERSION = "failure-taxonomy-trial-v1";
const COUNTS_SCHEMA_VERSION = "failure-taxonomy-counts-v1";
const SNAPSHOT_ID = "failure_taxonomy_20260813";
const SNAPSHOT_KIND = "canonical_offline_derived";
const SNAPSHOT_SCOPE = "phase3-extended";
const CLASSIFIER_VERSION = "failure-taxonomy-classifier-v1.1.0";
const GENERATOR_VERSION = "failure-taxonomy-generator-v1.1.0";
const REVIEW_MANIFEST_SCHEMA_VERSION = "comprehensive-evidence-review-manifest-v2";
const EXPECTED_TRIAL_COUNT = 960;
const EXPECTED_ARM_COUNT = 16;
const MAX_FILE_BYTES = 32 * 1024 * 1024;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const OUTPUT_NAMES = new Set([
  "README.md",
  "review_queue.csv",
  "taxonomy_counts.json",
  "trial_failure_taxonomy.jsonl",
]);
const SNAPSHOT_FILENAMES = new Set([...OUTPUT_NAMES, "failure_taxonomy_manifest.json"]);
const DIAGNOSIS_FIELDS = new Set([
  "value",
  "label",
  "definition",
  "confidence",
  "evidence_basis",
  "supporting_artifact_ids",
  "manual_review_required",
]);
const TRIAL_FIELDS = new Set([
  "trial_id",
  "arm_id",
  "task_id",
  "raw_outcome",
  ...FAILURE_TAXONOMY_AXIS_IDS,
]);
const CONFIDENCE_VALUES = new Set(
  FAILURE_TAXONOMY_REGISTRY.confidence_values.map((entry) => entry.id),
);

export type FailureTaxonomyConfidence = "high" | "medium" | "low";

export type FailureTaxonomyDiagnosis = Readonly<{
  value: string;
  label: string;
  definition: string;
  confidence: FailureTaxonomyConfidence;
  evidence_basis: readonly string[];
  supporting_artifact_ids: readonly string[];
  manual_review_required: boolean;
}>;

export type FailureTaxonomyTrial = Readonly<{
  trial_id: string;
  arm_id: string;
  task_id: string;
  raw_outcome: string;
  response_path_class: FailureTaxonomyDiagnosis;
  verifier_failure_category: FailureTaxonomyDiagnosis;
  assertion_failure_category: FailureTaxonomyDiagnosis;
  trajectory_disposition: FailureTaxonomyDiagnosis;
}>;

export type FailureTaxonomyProvenance = Readonly<{
  snapshotId: typeof SNAPSHOT_ID;
  scope: typeof SNAPSHOT_SCOPE;
  manifestSchemaVersion: typeof SNAPSHOT_SCHEMA_VERSION;
  trialSchemaVersion: typeof TRIAL_SCHEMA_VERSION;
  taxonomyVersion: string;
  classifierVersion: typeof CLASSIFIER_VERSION;
  generatorVersion: typeof GENERATOR_VERSION;
  scopeFingerprint: string;
  sourceGeneratedAt: string;
  trialCount: number;
  reviewQueueCount: number;
}>;

export type FailureTaxonomySnapshotState = "available" | "unavailable" | "invalid";

export type FailureTaxonomySnapshot = Readonly<{
  available: boolean;
  state: FailureTaxonomySnapshotState;
  message: string;
  rows: readonly FailureTaxonomyTrial[];
  provenance: FailureTaxonomyProvenance | null;
}>;

export type FailureTaxonomyReviewedSourceRow = Readonly<{
  trial_id: string;
  arm_id: string;
  task_id: string;
  raw_outcome: string;
  execution_validity: string;
  activity_subtype: string;
  failure_subtype: string;
  termination_subtype: string;
  policy_disposition: string;
  evidence_complete: string;
  classification_confidence: string;
  manual_review_required: string;
}>;

export type FailureTaxonomyReviewedSource = Readonly<{
  available: boolean;
  state: FailureTaxonomySnapshotState;
  message: string;
  reviewRows: readonly FailureTaxonomyReviewedSourceRow[];
  taxonomyRows: readonly FailureTaxonomyTrial[];
  provenance: FailureTaxonomyProvenance | null;
}>;

type FailureTaxonomyIndex = FailureTaxonomySnapshot & {
  byTrialId: ReadonlyMap<string, FailureTaxonomyTrial>;
  reviewedSourceRows: readonly FailureTaxonomyReviewedSourceRow[];
};

export type FailureTaxonomyTrialJoin =
  | Readonly<{
      status: "available";
      trial: FailureTaxonomyTrial;
      provenance: FailureTaxonomyProvenance;
    }>
  | Readonly<{
      status: "unavailable";
      reason: "outside_frozen_scope" | "snapshot_unavailable" | "snapshot_invalid";
      trialId: string;
      message: string;
      provenance: FailureTaxonomyProvenance | null;
    }>;

export type FailureTaxonomyFilters = Partial<Record<FailureTaxonomyAxisId, string>>;

type ManifestOutput = {
  sha256: string;
  bytes: number;
  rows: number | null;
};

type SnapshotManifest = {
  schema_version: string;
  snapshot_id: string;
  snapshot_kind: string;
  snapshot_files: string[];
  trial_schema_version: string;
  taxonomy_schema_version: string;
  taxonomy_version: string;
  classifier_version: string;
  generator_version: string;
  scope_fingerprint: string;
  source_provenance: { comprehensive_review_generated_at: string };
  inputs: Record<string, Record<string, unknown>>;
  implementations: Record<string, Record<string, unknown>>;
  outputs: Record<string, ManifestOutput>;
};

let cachedIndex: Promise<FailureTaxonomyIndex> | null = null;

function repoRoot() {
  return process.cwd().endsWith(path.join("apps", "dashboard"))
    ? path.resolve(process.cwd(), "..", "..")
    : process.cwd();
}

function snapshotDirectory() {
  if (process.env.DASHBOARD_FAILURE_TAXONOMY_DIR) {
    return path.resolve(process.env.DASHBOARD_FAILURE_TAXONOMY_DIR);
  }
  return path.join(repoRoot(), "results/manual_verification/failure_taxonomy_20260813");
}

function reviewDirectory() {
  if (process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR) {
    return path.resolve(process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR);
  }
  return path.join(repoRoot(), "results/manual_verification/comprehensive_review_20260731");
}

async function importFs(): Promise<typeof import("node:fs/promises")> {
  const runtimeImport = new Function("specifier", "return import(specifier)") as (
    specifier: string,
  ) => Promise<typeof import("node:fs/promises")>;
  return runtimeImport("node:fs/promises");
}

async function readBounded(filePath: string): Promise<Buffer> {
  const { readFile, stat } = await importFs();
  const metadata = await stat(filePath);
  if (!metadata.isFile() || metadata.size > MAX_FILE_BYTES) {
    throw new Error("file_unavailable_or_oversized");
  }
  return readFile(filePath);
}

function digest(value: Buffer | string) {
  return createHash("sha256").update(value).digest("hex");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, code: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(code);
  return value;
}

function requireString(value: unknown, code: string): string {
  if (typeof value !== "string" || value.trim() === "") throw new Error(code);
  return value;
}

function requireInteger(value: unknown, code: string): number {
  if (!Number.isSafeInteger(value) || Number(value) < 0) throw new Error(code);
  return Number(value);
}

function requireBoolean(value: unknown, code: string): boolean {
  if (typeof value !== "boolean") throw new Error(code);
  return value;
}

function exactKeys(value: Record<string, unknown>, expected: ReadonlySet<string>, code: string) {
  const keys = Object.keys(value);
  if (keys.length !== expected.size || keys.some((key) => !expected.has(key))) {
    throw new Error(code);
  }
}

function exactStringSet(value: unknown, expected: ReadonlySet<string>, code: string) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(code);
  }
  const actual = new Set(value);
  if (actual.size !== expected.size || [...actual].some((item) => !expected.has(item))) {
    throw new Error(code);
  }
}

function parseJson<T>(value: Buffer, code: string): T {
  try {
    return JSON.parse(value.toString("utf8")) as T;
  } catch {
    throw new Error(code);
  }
}

function parseJsonl(value: Buffer, code: string): Record<string, unknown>[] {
  try {
    return value.toString("utf8").split(/\r?\n/).filter(Boolean)
      .map((line) => JSON.parse(line) as Record<string, unknown>);
  } catch {
    throw new Error(code);
  }
}

function parseCsv(value: Buffer): Array<Record<string, string>> {
  const text = value.toString("utf8");
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') quoted = false;
      else field += character;
    } else if (character === '"') quoted = true;
    else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else field += character;
  }
  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  const [header, ...data] = rows;
  if (!header?.length) return [];
  return data.filter((values) => values.some(Boolean)).map((values) =>
    Object.fromEntries(header.map((key, index) => [key, values[index] ?? ""])),
  );
}

function validateReviewedSourceRow(
  row: Record<string, string>,
): FailureTaxonomyReviewedSourceRow {
  const trialId = requireString(
    row.trial_id,
    "reviewed_source_trial_id_invalid",
  );
  if (!UUID_PATTERN.test(trialId)) {
    throw new Error("reviewed_source_trial_id_invalid");
  }

  return Object.freeze({
    trial_id: trialId,
    arm_id: requireString(
      row.arm_id,
      "reviewed_source_arm_id_invalid",
    ),
    task_id: requireString(
      row.task_id,
      "reviewed_source_task_id_invalid",
    ),
    raw_outcome: requireString(
      row.raw_outcome,
      "reviewed_source_raw_outcome_invalid",
    ),
    execution_validity: requireString(
      row.execution_validity,
      "reviewed_source_execution_validity_invalid",
    ),
    activity_subtype: requireString(
      row.activity_subtype,
      "reviewed_source_activity_subtype_invalid",
    ),
    failure_subtype: requireString(
      row.failure_subtype,
      "reviewed_source_failure_subtype_invalid",
    ),
    termination_subtype: requireString(
      row.termination_subtype,
      "reviewed_source_termination_subtype_invalid",
    ),
    policy_disposition: requireString(
      row.policy_disposition,
      "reviewed_source_policy_disposition_invalid",
    ),
    evidence_complete: requireString(
      row.evidence_complete,
      "reviewed_source_evidence_complete_invalid",
    ),
    classification_confidence: requireString(
      row.classification_confidence,
      "reviewed_source_classification_confidence_invalid",
    ),
    manual_review_required: requireString(
      row.manual_review_required,
      "reviewed_source_manual_review_required_invalid",
    ),
  });
}

function uniqueTrialIds(rows: readonly Record<string, unknown>[], code: string): Set<string> {
  const values = rows.map((row) => requireString(row.trial_id, code));
  if (values.some((trialId) => !UUID_PATTERN.test(trialId)) || new Set(values).size !== values.length) {
    throw new Error(code);
  }
  return new Set(values);
}

function sameSet(left: ReadonlySet<string>, right: ReadonlySet<string>) {
  return left.size === right.size && [...left].every((value) => right.has(value));
}

function validateManifest(value: unknown): SnapshotManifest {
  const manifest = requireRecord(value, "manifest_not_object");
  if (manifest.schema_version !== SNAPSHOT_SCHEMA_VERSION) throw new Error("manifest_schema_mismatch");
  if (manifest.snapshot_id !== SNAPSHOT_ID || manifest.snapshot_kind !== SNAPSHOT_KIND) {
    throw new Error("snapshot_identity_mismatch");
  }
  exactStringSet(manifest.snapshot_files, SNAPSHOT_FILENAMES, "snapshot_filename_mismatch");
  if (manifest.trial_schema_version !== TRIAL_SCHEMA_VERSION) throw new Error("trial_schema_mismatch");
  if (manifest.taxonomy_schema_version !== FAILURE_TAXONOMY_REGISTRY.schema_version
    || manifest.taxonomy_version !== FAILURE_TAXONOMY_REGISTRY.taxonomy_version) {
    throw new Error("taxonomy_schema_mismatch");
  }
  if (manifest.classifier_version !== CLASSIFIER_VERSION
    || manifest.generator_version !== GENERATOR_VERSION) {
    throw new Error("producer_version_mismatch");
  }
  requireString(manifest.scope_fingerprint, "scope_fingerprint_missing");
  const sourceProvenance = requireRecord(manifest.source_provenance, "source_provenance_missing");
  requireString(sourceProvenance.comprehensive_review_generated_at, "source_generated_at_missing");
  const inputs = requireRecord(manifest.inputs, "manifest_inputs_missing");
  const implementations = requireRecord(manifest.implementations, "manifest_implementations_missing");
  const outputs = requireRecord(manifest.outputs, "manifest_outputs_missing");
  if (Object.keys(outputs).length !== OUTPUT_NAMES.size
    || Object.keys(outputs).some((name) => !OUTPUT_NAMES.has(name))) {
    throw new Error("manifest_output_whitelist_mismatch");
  }
  const parsedOutputs = Object.fromEntries(Object.entries(outputs).map(([name, raw]) => {
    const output = requireRecord(raw, "manifest_output_invalid");
    const rows = output.rows === null ? null : requireInteger(output.rows, "manifest_output_rows_invalid");
    return [name, {
      sha256: requireString(output.sha256, "manifest_output_hash_invalid"),
      bytes: requireInteger(output.bytes, "manifest_output_bytes_invalid"),
      rows,
    }];
  }));
  return {
    schema_version: String(manifest.schema_version),
    snapshot_id: String(manifest.snapshot_id),
    snapshot_kind: String(manifest.snapshot_kind),
    snapshot_files: manifest.snapshot_files as string[],
    trial_schema_version: String(manifest.trial_schema_version),
    taxonomy_schema_version: String(manifest.taxonomy_schema_version),
    taxonomy_version: String(manifest.taxonomy_version),
    classifier_version: String(manifest.classifier_version),
    generator_version: String(manifest.generator_version),
    scope_fingerprint: String(manifest.scope_fingerprint),
    source_provenance: {
      comprehensive_review_generated_at: String(sourceProvenance.comprehensive_review_generated_at),
    },
    inputs: inputs as Record<string, Record<string, unknown>>,
    implementations: implementations as Record<string, Record<string, unknown>>,
    outputs: parsedOutputs,
  };
}

function validateDiagnosis(
  value: unknown,
  axisId: FailureTaxonomyAxisId,
): FailureTaxonomyDiagnosis {
  const diagnosis = requireRecord(value, `diagnosis_invalid:${axisId}`);
  exactKeys(diagnosis, DIAGNOSIS_FIELDS, `diagnosis_fields_invalid:${axisId}`);
  const entryValue = requireString(diagnosis.value, `diagnosis_value_invalid:${axisId}`);
  const entry = getFailureTaxonomyEntry(axisId, entryValue);
  if (!entry || diagnosis.label !== entry.label || diagnosis.definition !== entry.definition) {
    throw new Error(`diagnosis_registry_mismatch:${axisId}`);
  }
  const confidence = requireString(diagnosis.confidence, `diagnosis_confidence_invalid:${axisId}`);
  if (!CONFIDENCE_VALUES.has(confidence)) throw new Error(`diagnosis_confidence_invalid:${axisId}`);
  if (!Array.isArray(diagnosis.evidence_basis) || diagnosis.evidence_basis.length === 0
    || diagnosis.evidence_basis.some((fact) =>
      typeof fact !== "string" || fact.trim() === "" || /[\r\n]/.test(fact))) {
    throw new Error(`diagnosis_evidence_basis_invalid:${axisId}`);
  }
  if (!Array.isArray(diagnosis.supporting_artifact_ids)
    || diagnosis.supporting_artifact_ids.some((artifactId) =>
      typeof artifactId !== "string" || !UUID_PATTERN.test(artifactId))) {
    throw new Error(`diagnosis_artifact_ids_invalid:${axisId}`);
  }
  return {
    value: entryValue,
    label: entry.label,
    definition: entry.definition,
    confidence: confidence as FailureTaxonomyConfidence,
    evidence_basis: diagnosis.evidence_basis as string[],
    supporting_artifact_ids: diagnosis.supporting_artifact_ids as string[],
    manual_review_required: requireBoolean(
      diagnosis.manual_review_required,
      `diagnosis_manual_review_invalid:${axisId}`,
    ),
  };
}

function validateTrial(value: unknown): FailureTaxonomyTrial {
  const row = requireRecord(value, "trial_row_invalid");
  exactKeys(row, TRIAL_FIELDS, "trial_fields_invalid");
  const trialId = requireString(row.trial_id, "trial_id_invalid");
  if (!UUID_PATTERN.test(trialId)) throw new Error("trial_id_invalid");
  return {
    trial_id: trialId,
    arm_id: requireString(row.arm_id, "trial_arm_invalid"),
    task_id: requireString(row.task_id, "trial_task_invalid"),
    raw_outcome: requireString(row.raw_outcome, "trial_outcome_invalid"),
    response_path_class: validateDiagnosis(row.response_path_class, "response_path_class"),
    verifier_failure_category: validateDiagnosis(
      row.verifier_failure_category,
      "verifier_failure_category",
    ),
    assertion_failure_category: validateDiagnosis(
      row.assertion_failure_category,
      "assertion_failure_category",
    ),
    trajectory_disposition: validateDiagnosis(
      row.trajectory_disposition,
      "trajectory_disposition",
    ),
  };
}

function requireBinding(
  value: Record<string, unknown> | undefined,
  expected: Record<string, string | number>,
  code: string,
) {
  const binding = requireRecord(value, code);
  for (const [key, expectedValue] of Object.entries(expected)) {
    if (binding[key] !== expectedValue) throw new Error(code);
  }
}

function validateCounts(counts: unknown, rows: readonly FailureTaxonomyTrial[]) {
  const value = requireRecord(counts, "counts_not_object");
  if (value.schema_version !== COUNTS_SCHEMA_VERSION || value.trial_count !== rows.length) {
    throw new Error("counts_schema_or_total_mismatch");
  }
  const distributions = requireRecord(value.axis_distributions, "axis_distributions_missing");
  for (const axis of FAILURE_TAXONOMY_REGISTRY.axes) {
    const actual = requireRecord(distributions[axis.id], `axis_distribution_missing:${axis.id}`);
    if (Object.keys(actual).length !== axis.entries.length) {
      throw new Error(`axis_distribution_shape_mismatch:${axis.id}`);
    }
    for (const entry of axis.entries) {
      const computed = rows.filter((row) => row[axis.id].value === entry.id).length;
      if (actual[entry.id] !== computed) throw new Error(`axis_distribution_mismatch:${axis.id}`);
    }
  }
}

function unavailableIndex(
  state: Exclude<FailureTaxonomySnapshotState, "available">,
  message: string,
): FailureTaxonomyIndex {
  return {
    available: false,
    state,
    message,
    rows: [],
    provenance: null,
    byTrialId: new Map(),
    reviewedSourceRows: [],
  };
}

async function loadIndex(): Promise<FailureTaxonomyIndex> {
  const directory = snapshotDirectory();
  let manifestBytes: Buffer;
  try {
    manifestBytes = await readBounded(path.join(directory, "failure_taxonomy_manifest.json"));
  } catch {
    return unavailableIndex(
      "unavailable",
      "Frozen failure taxonomy is unavailable: its canonical manifest could not be loaded.",
    );
  }

  try {
    if (digest(manifestBytes) !== FROZEN_CANONICAL_MANIFEST_SHA256) {
      throw new Error("canonical_manifest_hash_mismatch");
    }
    const manifest = validateManifest(parseJson(manifestBytes, "manifest_json_invalid"));
    for (const [name, expectedSha256] of Object.entries(FROZEN_CLASSIFICATION_OUTPUT_SHA256)) {
      if (manifest.outputs[name]?.sha256 !== expectedSha256) {
        throw new Error(`frozen_output_identity_mismatch:${name}`);
      }
    }
    const outputNames = [...OUTPUT_NAMES].sort();
    const outputContents = Object.fromEntries(await Promise.all(outputNames.map(async (name) => [
      name,
      await readBounded(path.join(directory, name)),
    ]))) as Record<string, Buffer>;
    for (const name of outputNames) {
      const expected = manifest.outputs[name];
      if (digest(outputContents[name]) !== expected.sha256
        || outputContents[name].byteLength !== expected.bytes) {
        throw new Error(`output_hash_or_size_mismatch:${name}`);
      }
    }

    const root = repoRoot();
    const reviewRoot = reviewDirectory();
    const fixedInputs = {
      taxonomy_registry: {
        file: path.join(root, "configs/dashboard/failure_taxonomy_v1.json"),
        path: "configs/dashboard/failure_taxonomy_v1.json",
      },
      comprehensive_review_manifest: {
        file: path.join(reviewRoot, "review_manifest.json"),
        path: "results/manual_verification/comprehensive_review_20260731/review_manifest.json",
      },
      "trial_review.csv": {
        file: path.join(reviewRoot, "trial_review.csv"),
        path: "results/manual_verification/comprehensive_review_20260731/trial_review.csv",
      },
      "trial_evidence.jsonl": {
        file: path.join(reviewRoot, "trial_evidence.jsonl"),
        path: "results/manual_verification/comprehensive_review_20260731/trial_evidence.jsonl",
      },
    } as const;
    const inputContents = Object.fromEntries(await Promise.all(
      Object.entries(fixedInputs).map(async ([name, input]) => [name, await readBounded(input.file)]),
    )) as Record<keyof typeof fixedInputs, Buffer>;

    requireBinding(manifest.inputs.taxonomy_registry, {
      path: fixedInputs.taxonomy_registry.path,
      sha256: digest(inputContents.taxonomy_registry),
      schema_version: FAILURE_TAXONOMY_REGISTRY.schema_version,
      taxonomy_version: FAILURE_TAXONOMY_REGISTRY.taxonomy_version,
    }, "registry_binding_mismatch");
    requireBinding(manifest.inputs.comprehensive_review_manifest, {
      path: fixedInputs.comprehensive_review_manifest.path,
      sha256: digest(inputContents.comprehensive_review_manifest),
      schema_version: REVIEW_MANIFEST_SCHEMA_VERSION,
    }, "review_manifest_binding_mismatch");

    const reviewManifest = requireRecord(
      parseJson(inputContents.comprehensive_review_manifest, "review_manifest_json_invalid"),
      "review_manifest_invalid",
    );
    if (reviewManifest.schema_version !== REVIEW_MANIFEST_SCHEMA_VERSION
      || reviewManifest.scope_fingerprint !== manifest.scope_fingerprint) {
      throw new Error("review_scope_or_schema_mismatch");
    }
    const scopeInputs = requireRecord(reviewManifest.scope_fingerprint_inputs, "review_scope_inputs_missing");
    if (scopeInputs.trial_count !== EXPECTED_TRIAL_COUNT || scopeInputs.selected_run_count !== EXPECTED_ARM_COUNT) {
      throw new Error("review_scope_population_mismatch");
    }

    const registrySource = requireRecord(
      FAILURE_TAXONOMY_REGISTRY.source_contract,
      "registry_source_contract_missing",
    );
    if (registrySource.manifest_sha256 !== digest(inputContents.comprehensive_review_manifest)
      || registrySource.scope_fingerprint !== manifest.scope_fingerprint
      || registrySource.trial_count !== EXPECTED_TRIAL_COUNT) {
      throw new Error("registry_source_contract_mismatch");
    }
    const registryRequiredInputs = Array.isArray(registrySource.required_inputs)
      ? registrySource.required_inputs.map((input) => requireRecord(input, "registry_input_invalid"))
      : [];
    const reviewOutputs = requireRecord(reviewManifest.outputs, "review_outputs_missing");
    const reviewRowCounts = requireRecord(reviewManifest.row_counts, "review_row_counts_missing");
    for (const name of ["trial_review.csv", "trial_evidence.jsonl"] as const) {
      const binding = manifest.inputs[name];
      const expectedDigest = digest(inputContents[name]);
      requireBinding(binding, {
        path: fixedInputs[name].path,
        sha256: expectedDigest,
        rows: EXPECTED_TRIAL_COUNT,
      }, `review_input_binding_mismatch:${name}`);
      const registryBinding = registryRequiredInputs.find((input) => input.path === name);
      requireBinding(registryBinding, {
        path: name,
        sha256: expectedDigest,
        rows: EXPECTED_TRIAL_COUNT,
      }, `registry_input_binding_mismatch:${name}`);
      const sourceOutput = requireRecord(reviewOutputs[name], `review_output_missing:${name}`);
      if (sourceOutput.sha256 !== expectedDigest
        || sourceOutput.bytes !== inputContents[name].byteLength
        || sourceOutput.rows !== EXPECTED_TRIAL_COUNT
        || reviewRowCounts[name] !== EXPECTED_TRIAL_COUNT) {
        throw new Error(`review_output_binding_mismatch:${name}`);
      }
    }

    const implementationFiles = {
      classifier: {
        file: path.join(root, "scripts/lib/failure_taxonomy_classifier.py"),
        path: "scripts/lib/failure_taxonomy_classifier.py",
        version: CLASSIFIER_VERSION,
      },
      generator: {
        file: path.join(root, "scripts/generate_failure_taxonomy_snapshot.py"),
        path: "scripts/generate_failure_taxonomy_snapshot.py",
        version: GENERATOR_VERSION,
      },
    } as const;
    for (const [name, implementation] of Object.entries(implementationFiles)) {
      const contents = await readBounded(implementation.file);
      requireBinding(manifest.implementations[name], {
        path: implementation.path,
        version: implementation.version,
        sha256: digest(contents),
      }, `implementation_binding_mismatch:${name}`);
    }

    const trialValues = parseJsonl(
      outputContents["trial_failure_taxonomy.jsonl"],
      "taxonomy_jsonl_invalid",
    );
    if (trialValues.length !== EXPECTED_TRIAL_COUNT
      || manifest.outputs["trial_failure_taxonomy.jsonl"].rows !== EXPECTED_TRIAL_COUNT) {
      throw new Error("taxonomy_trial_count_mismatch");
    }
    const rows = trialValues.map(validateTrial);
    const taxonomyIds = uniqueTrialIds(rows, "taxonomy_trial_set_invalid");

    const reviewRows = parseCsv(inputContents["trial_review.csv"]);
    const evidenceRows = parseJsonl(inputContents["trial_evidence.jsonl"], "review_evidence_jsonl_invalid");
    const reviewIds = uniqueTrialIds(reviewRows, "review_trial_set_invalid");
    const evidenceIds = uniqueTrialIds(evidenceRows, "review_evidence_trial_set_invalid");
    if (!sameSet(taxonomyIds, reviewIds) || !sameSet(taxonomyIds, evidenceIds)) {
      throw new Error("frozen_trial_set_mismatch");
    }
    const reviewedSourceRows = Object.freeze(
      reviewRows.map(validateReviewedSourceRow),
    );
    const sortedIds = [...taxonomyIds].sort();
    if (digest(sortedIds.join("\n")) !== scopeInputs.trial_ids_sha256) {
      throw new Error("frozen_trial_set_fingerprint_mismatch");
    }

    const reviewById = new Map(
      reviewedSourceRows.map((row) => [row.trial_id, row]),
    );
    const evidenceById = new Map(evidenceRows.map((row) => [String(row.trial_id), row]));
    const joinedRows = rows.map((row) => {
      const reviewed = reviewById.get(row.trial_id);
      const evidence = evidenceById.get(row.trial_id);
      if (!reviewed
        || reviewed.arm_id !== row.arm_id
        || reviewed.task_id !== row.task_id
        || reviewed.raw_outcome !== row.raw_outcome) {
        throw new Error("trial_id_join_identity_mismatch");
      }
      if (!evidence || evidence.hidden_reasoning_retained !== false
        || !Array.isArray(evidence.supporting_artifact_ids)) {
        throw new Error("trial_evidence_contract_mismatch");
      }
      const retainedArtifactIds = new Set(evidence.supporting_artifact_ids.map((artifactId) =>
        requireString(artifactId, "trial_evidence_artifact_id_invalid")));
      if (FAILURE_TAXONOMY_AXIS_IDS.some((axisId) =>
        row[axisId].supporting_artifact_ids.some((artifactId) => !retainedArtifactIds.has(artifactId)))) {
        throw new Error("taxonomy_artifact_not_bound_to_trial_evidence");
      }
      return row;
    });
    if (new Set(joinedRows.map((row) => row.arm_id)).size !== EXPECTED_ARM_COUNT) {
      throw new Error("reviewed_extended_arm_population_mismatch");
    }

    validateCounts(
      parseJson(outputContents["taxonomy_counts.json"], "taxonomy_counts_json_invalid"),
      joinedRows,
    );
    const queueRows = parseCsv(outputContents["review_queue.csv"]);
    const queueIds = new Set(queueRows.map((row) => row.trial_id));
    const manualReviewIds = new Set(joinedRows.filter((row) =>
      FAILURE_TAXONOMY_AXIS_IDS.some((axisId) => row[axisId].manual_review_required),
    ).map((row) => row.trial_id));
    if (queueRows.length !== queueIds.size
      || manifest.outputs["review_queue.csv"].rows !== queueRows.length
      || !sameSet(queueIds, manualReviewIds)) {
      throw new Error("review_queue_union_mismatch");
    }
    const byTrialId = new Map(joinedRows.map((row) => [row.trial_id, row]));
    for (const queueRow of queueRows) {
      const trial = byTrialId.get(queueRow.trial_id);
      if (!trial || trial.arm_id !== queueRow.arm_id || trial.task_id !== queueRow.task_id
        || trial.raw_outcome !== queueRow.raw_outcome
        || FAILURE_TAXONOMY_AXIS_IDS.some((axisId) =>
          queueRow[axisId] !== trial[axisId].value
          || queueRow[`${axisId}_confidence`] !== trial[axisId].confidence)) {
        throw new Error("review_queue_diagnosis_mismatch");
      }
    }

    const provenance: FailureTaxonomyProvenance = {
      snapshotId: SNAPSHOT_ID,
      scope: SNAPSHOT_SCOPE,
      manifestSchemaVersion: SNAPSHOT_SCHEMA_VERSION,
      trialSchemaVersion: TRIAL_SCHEMA_VERSION,
      taxonomyVersion: FAILURE_TAXONOMY_REGISTRY.taxonomy_version,
      classifierVersion: CLASSIFIER_VERSION,
      generatorVersion: GENERATOR_VERSION,
      scopeFingerprint: manifest.scope_fingerprint,
      sourceGeneratedAt: manifest.source_provenance.comprehensive_review_generated_at,
      trialCount: joinedRows.length,
      reviewQueueCount: queueRows.length,
    };
    return {
      available: true,
      state: "available",
      message: "Loaded and validated the frozen J2 failure taxonomy snapshot.",
      rows: joinedRows,
      provenance,
      byTrialId,
      reviewedSourceRows,
    };
  } catch (error) {
    const reason = error instanceof Error ? error.message : "unknown_validation_error";
    return unavailableIndex(
      "invalid",
      `Frozen failure taxonomy failed closed because validation did not pass (${reason}).`,
    );
  }
}

function getIndex() {
  cachedIndex ??= loadIndex();
  return cachedIndex;
}

export async function getFailureTaxonomySnapshot(): Promise<FailureTaxonomySnapshot> {
  const {
    byTrialId: _byTrialId,
    reviewedSourceRows: _reviewedSourceRows,
    ...snapshot
  } = await getIndex();
  return snapshot;
}

export async function getFailureTaxonomyReviewedSource(): Promise<FailureTaxonomyReviewedSource> {
  const index = await getIndex();
  return Object.freeze({
    available: index.available,
    state: index.state,
    message: index.message,
    reviewRows: index.reviewedSourceRows,
    taxonomyRows: index.rows,
    provenance: index.provenance,
  });
}

export async function getFailureTaxonomyForTrial(
  trialId: string,
): Promise<FailureTaxonomyTrialJoin> {
  const index = await getIndex();
  if (!index.available || !index.provenance) {
    return {
      status: "unavailable",
      reason: index.state === "invalid" ? "snapshot_invalid" : "snapshot_unavailable",
      trialId,
      message: index.message,
      provenance: null,
    };
  }
  const trial = index.byTrialId.get(trialId);
  if (!trial) {
    return {
      status: "unavailable",
      reason: "outside_frozen_scope",
      trialId,
      message: "Failure taxonomy unavailable: this trial is outside the frozen 960-trial J2 Phase 3 extended scope. This is an availability state, not the taxonomy value ‘Not applicable’.",
      provenance: index.provenance,
    };
  }
  return { status: "available", trial, provenance: index.provenance };
}

export function normalizeFailureTaxonomyFilters(
  values: Partial<Record<FailureTaxonomyAxisId, string | undefined>>,
): FailureTaxonomyFilters {
  return Object.fromEntries(FAILURE_TAXONOMY_AXIS_IDS.flatMap((axisId) => {
    const value = values[axisId]?.trim();
    return value && getFailureTaxonomyEntry(axisId, value) ? [[axisId, value]] : [];
  })) as FailureTaxonomyFilters;
}

export function filterFailureTaxonomyRows(
  rows: readonly FailureTaxonomyTrial[],
  filters: FailureTaxonomyFilters,
): FailureTaxonomyTrial[] {
  return rows.filter((row) => FAILURE_TAXONOMY_AXIS_IDS.every((axisId) =>
    !filters[axisId] || row[axisId].value === filters[axisId],
  ));
}

/** Test-only reset for deterministic manifest fixtures. */
export function resetFailureTaxonomySnapshotCacheForTests() {
  cachedIndex = null;
}
