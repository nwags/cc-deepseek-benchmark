import rawRegistry from "../../../../configs/dashboard/failure_taxonomy_v1.json";

export type FailureTaxonomyAxisId =
  | "response_path_class"
  | "verifier_failure_category"
  | "assertion_failure_category"
  | "trajectory_disposition";

export type FailureTaxonomyEntry = Readonly<{
  id: string;
  order: number;
  label: string;
  definition: string;
}>;

export type FailureTaxonomyAxis = Readonly<{
  id: FailureTaxonomyAxisId;
  dr: string;
  order: number;
  label: string;
  definition: string;
  manual_review_guidance: string;
  entries: readonly FailureTaxonomyEntry[];
}>;

export type FailureTaxonomyRegistry = Readonly<{
  schema_version: "dashboard-failure-taxonomy-registry-v1";
  taxonomy_version: string;
  contract_status: "foundation_only";
  description: string;
  selection_policy: Readonly<Record<string, unknown>>;
  source_contract: Readonly<Record<string, unknown>>;
  future_output_contract: Readonly<Record<string, unknown>>;
  confidence_values: readonly FailureTaxonomyEntry[];
  axes: readonly FailureTaxonomyAxis[];
  normalizations: readonly Readonly<Record<string, unknown>>[];
  legacy_compatibility: Readonly<Record<string, unknown>>;
  evidence_policy: Readonly<Record<string, unknown>>;
  eligibility_rules: readonly Readonly<Record<string, unknown>>[];
}>;

const AXIS_IDS: readonly FailureTaxonomyAxisId[] = [
  "response_path_class",
  "verifier_failure_category",
  "assertion_failure_category",
  "trajectory_disposition",
];

const REQUIRED_DIAGNOSIS_FIELDS = [
  "value",
  "label",
  "definition",
  "confidence",
  "evidence_basis",
  "supporting_artifact_ids",
  "manual_review_required",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${label} must be an object`);
  return value;
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function requirePositiveInteger(value: unknown, label: string): number {
  if (!Number.isInteger(value) || Number(value) < 1) {
    throw new Error(`${label} must be a positive integer`);
  }
  return Number(value);
}

function requireUnique(values: readonly (string | number)[], label: string): void {
  if (new Set(values).size !== values.length) throw new Error(`${label} must be unique`);
}

function requireContiguousOrdering(values: readonly number[], label: string): void {
  const expected = values.map((_, index) => index + 1);
  if (values.some((value, index) => value !== expected[index])) {
    throw new Error(`${label} must be contiguous and start at 1`);
  }
}

function validateEntries(value: unknown, label: string): readonly FailureTaxonomyEntry[] {
  if (!Array.isArray(value) || value.length === 0) throw new Error(`${label} must be a non-empty array`);
  const entries = value.map((candidate, index) => {
    const entry = requireRecord(candidate, `${label}[${index}]`);
    return {
      id: requireString(entry.id, `${label}[${index}].id`),
      order: requirePositiveInteger(entry.order, `${label}[${index}].order`),
      label: requireString(entry.label, `${label}[${index}].label`),
      definition: requireString(entry.definition, `${label}[${index}].definition`),
    };
  });
  requireUnique(entries.map((entry) => entry.id), `${label} ids`);
  requireUnique(entries.map((entry) => entry.order), `${label} ordering`);
  requireContiguousOrdering(entries.map((entry) => entry.order), `${label} ordering`);
  return entries;
}

function validateAxis(value: unknown, index: number): FailureTaxonomyAxis {
  const axis = requireRecord(value, `axes[${index}]`);
  const id = requireString(axis.id, `axes[${index}].id`);
  if (!AXIS_IDS.includes(id as FailureTaxonomyAxisId)) {
    throw new Error(`axes[${index}].id is not a supported taxonomy axis`);
  }
  return {
    id: id as FailureTaxonomyAxisId,
    dr: requireString(axis.dr, `axes[${index}].dr`),
    order: requirePositiveInteger(axis.order, `axes[${index}].order`),
    label: requireString(axis.label, `axes[${index}].label`),
    definition: requireString(axis.definition, `axes[${index}].definition`),
    manual_review_guidance: requireString(
      axis.manual_review_guidance,
      `axes[${index}].manual_review_guidance`,
    ),
    entries: validateEntries(axis.entries, `axes[${index}].entries`),
  };
}

function validateDiagnosisFields(outputContract: Record<string, unknown>): void {
  const fields = outputContract.diagnosis_object_fields;
  if (!Array.isArray(fields)) throw new Error("future_output_contract.diagnosis_object_fields must be an array");
  const names = fields.map((candidate, index) => {
    const field = requireRecord(candidate, `diagnosis_object_fields[${index}]`);
    requireString(field.type, `diagnosis_object_fields[${index}].type`);
    requireString(field.description, `diagnosis_object_fields[${index}].description`);
    return requireString(field.name, `diagnosis_object_fields[${index}].name`);
  });
  requireUnique(names, "diagnosis object field names");
  for (const required of REQUIRED_DIAGNOSIS_FIELDS) {
    if (!names.includes(required)) throw new Error(`diagnosis object field ${required} is required`);
  }
}

export function validateFailureTaxonomyRegistry(value: unknown): FailureTaxonomyRegistry {
  const registry = requireRecord(value, "failure taxonomy registry");
  if (registry.schema_version !== "dashboard-failure-taxonomy-registry-v1") {
    throw new Error("unsupported failure taxonomy registry schema_version");
  }
  requireString(registry.taxonomy_version, "taxonomy_version");
  if (registry.contract_status !== "foundation_only") {
    throw new Error("J1 taxonomy contract must remain foundation_only");
  }
  requireString(registry.description, "description");
  const selectionPolicy = requireRecord(registry.selection_policy, "selection_policy");
  const sourceContract = requireRecord(registry.source_contract, "source_contract");
  const outputContract = requireRecord(registry.future_output_contract, "future_output_contract");
  validateDiagnosisFields(outputContract);
  const confidenceValues = validateEntries(registry.confidence_values, "confidence_values");
  if (!Array.isArray(registry.axes)) throw new Error("axes must be an array");
  const axes = registry.axes.map(validateAxis);
  requireUnique(axes.map((axis) => axis.id), "axis ids");
  requireUnique(axes.map((axis) => axis.order), "axis ordering");
  requireContiguousOrdering(axes.map((axis) => axis.order), "axis ordering");
  for (const required of AXIS_IDS) {
    if (!axes.some((axis) => axis.id === required)) throw new Error(`taxonomy axis ${required} is required`);
  }
  if (!Array.isArray(registry.normalizations)) throw new Error("normalizations must be an array");
  if (!Array.isArray(registry.eligibility_rules) || registry.eligibility_rules.length === 0) {
    throw new Error("eligibility_rules must be a non-empty array");
  }
  const normalizations = registry.normalizations.map((item, index) =>
    requireRecord(item, `normalizations[${index}]`));
  const eligibilityRules = registry.eligibility_rules.map((item, index) =>
    requireRecord(item, `eligibility_rules[${index}]`));

  return {
    schema_version: "dashboard-failure-taxonomy-registry-v1",
    taxonomy_version: requireString(registry.taxonomy_version, "taxonomy_version"),
    contract_status: "foundation_only",
    description: requireString(registry.description, "description"),
    selection_policy: selectionPolicy,
    source_contract: sourceContract,
    future_output_contract: outputContract,
    confidence_values: confidenceValues,
    axes,
    normalizations,
    legacy_compatibility: requireRecord(registry.legacy_compatibility, "legacy_compatibility"),
    evidence_policy: requireRecord(registry.evidence_policy, "evidence_policy"),
    eligibility_rules: eligibilityRules,
  };
}

function deepFreeze<T>(value: T): T {
  if (typeof value !== "object" || value === null || Object.isFrozen(value)) return value;
  Object.freeze(value);
  for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
  return value;
}

export const FAILURE_TAXONOMY_REGISTRY = deepFreeze(
  validateFailureTaxonomyRegistry(rawRegistry),
);

export function getFailureTaxonomyAxis(axisId: FailureTaxonomyAxisId): FailureTaxonomyAxis {
  const axis = FAILURE_TAXONOMY_REGISTRY.axes.find((candidate) => candidate.id === axisId);
  if (!axis) throw new Error(`Unknown failure taxonomy axis: ${axisId}`);
  return axis;
}

export function getFailureTaxonomyEntry(
  axisId: FailureTaxonomyAxisId,
  value: string,
): FailureTaxonomyEntry | null {
  return getFailureTaxonomyAxis(axisId).entries.find((entry) => entry.id === value) ?? null;
}
