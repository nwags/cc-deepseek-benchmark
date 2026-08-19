export const FAILURE_COMPOSITION_SCOPE_ID = "phase3-extended" as const;

export const FAILURE_COMPOSITION_ARM_IDS = [
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
] as const;

export const FAILURE_COMPOSITION_CATEGORY_IDS = [
  "verifier_task_failure",
  "timeout_after_meaningful_activity",
  "provider_policy_refusal",
  "invalid_response_path",
  "missing_required_output",
  "extraneous_output_artifacts",
  "unknown_or_incomplete_evidence",
] as const;

export type FailureCompositionCategoryId =
  (typeof FAILURE_COMPOSITION_CATEGORY_IDS)[number];

/**
 * This is presentation precedence only. It is deliberately distinct from
 * taxonomy registry display order and from J2 classifier precedence.
 */
export const FAILURE_COMPOSITION_SELECTION_PRECEDENCE = [
  "provider_policy_refusal",
  "invalid_response_path",
  "missing_required_output",
  "extraneous_output_artifacts",
  "timeout_after_meaningful_activity",
  "verifier_task_failure",
  "unknown_or_incomplete_evidence",
] as const satisfies readonly FailureCompositionCategoryId[];

export const FAILURE_COMPOSITION_CATEGORIES = Object.freeze([
  {
    id: "verifier_task_failure",
    label: "Verifier / task failure",
    description:
      "A remaining raw failure with an established J2 verifier, task, or submitted-solution failure category.",
  },
  {
    id: "timeout_after_meaningful_activity",
    label: "Timeout after meaningful activity",
    description:
      "A remaining raw failure whose accepted activity classification records meaningful agent activity before timeout.",
  },
  {
    id: "provider_policy_refusal",
    label: "Provider-policy refusal",
    description:
      "A raw failure whose accepted policy disposition records a provider-policy refusal.",
  },
  {
    id: "invalid_response_path",
    label: "Invalid response path",
    description:
      "A raw failure whose accepted execution-validity classification records an invalid response path.",
  },
  {
    id: "missing_required_output",
    label: "Missing required output",
    description:
      "A remaining raw failure whose accepted source failure subtype records missing required output.",
  },
  {
    id: "extraneous_output_artifacts",
    label: "Extraneous output artifacts",
    description:
      "A remaining raw failure whose accepted source failure subtype records extraneous output artifacts.",
  },
  {
    id: "unknown_or_incomplete_evidence",
    label: "Unknown / incomplete evidence",
    description:
      "A remaining raw failure whose retained evidence does not justify one of the preceding DR-302 buckets. This is not synonymous with evidence being incomplete.",
  },
] as const);

export type FailureCompositionReviewRow = Readonly<{
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

export type FailureCompositionDiagnosis = Readonly<{
  value: string;
}>;

export type FailureCompositionTaxonomyRow = Readonly<{
  trial_id: string;
  arm_id: string;
  task_id: string;
  raw_outcome: string;
  response_path_class: FailureCompositionDiagnosis;
  verifier_failure_category: FailureCompositionDiagnosis;
  trajectory_disposition: FailureCompositionDiagnosis;
}>;

export type FailureCompositionCategoryCount = Readonly<{
  id: FailureCompositionCategoryId;
  label: string;
  count: number;
  shareOfRawFailures: number;
}>;

export type FailureCompositionArm = Readonly<{
  armId: string;
  trialCount: number;
  rawFailureCount: number;
  successCount: number;
  notRecordedCount: number;
  categories: readonly FailureCompositionCategoryCount[];
}>;

export type FailureCompositionResidualBreakdown = Readonly<{
  count: number;
  evidenceCompleteCount: number;
  evidenceIncompleteCount: number;
  highConfidenceCount: number;
  mediumConfidenceCount: number;
  noSubstantiveAttemptCount: number;
  indeterminateCount: number;
}>;

export type FailureCompositionModel = Readonly<{
  scopeId: typeof FAILURE_COMPOSITION_SCOPE_ID;
  trialCount: number;
  armCount: number;
  trialsPerArm: number;
  rawFailureCount: number;
  successCount: number;
  notRecordedCount: number;
  successfulTimeoutAfterMeaningfulActivityCount: number;
  categories: readonly FailureCompositionCategoryCount[];
  residualBreakdown: FailureCompositionResidualBreakdown;
  arms: readonly FailureCompositionArm[];
}>;

const EXPECTED_TRIAL_COUNT = 960;
const EXPECTED_ARM_COUNT = FAILURE_COMPOSITION_ARM_IDS.length;
const EXPECTED_TRIALS_PER_ARM = 60;
const EXPECTED_RAW_FAILURE_COUNT = 370;
const EXPECTED_SUCCESS_COUNT = 562;
const EXPECTED_NOT_RECORDED_COUNT = 28;
const EXPECTED_SUCCESSFUL_TIMEOUT_COUNT = 19;

const EXPECTED_GLOBAL_CATEGORY_COUNTS: Readonly<
  Record<FailureCompositionCategoryId, number>
> = Object.freeze({
  verifier_task_failure: 167,
  timeout_after_meaningful_activity: 127,
  provider_policy_refusal: 9,
  invalid_response_path: 4,
  missing_required_output: 7,
  extraneous_output_artifacts: 22,
  unknown_or_incomplete_evidence: 34,
});

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function stableTextCompare(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function requireExactCount(
  actual: number,
  expected: number,
  code: string,
): void {
  if (actual !== expected) {
    throw new Error(`${code}:${actual}:${expected}`);
  }
}

function indexRows<T extends { trial_id: string }>(
  rows: readonly T[],
  label: string,
): ReadonlyMap<string, T> {
  const result = new Map<string, T>();
  for (const row of rows) {
    if (!UUID_PATTERN.test(row.trial_id)) {
      throw new Error(`${label}_trial_id_invalid`);
    }
    if (result.has(row.trial_id)) {
      throw new Error(`${label}_trial_id_duplicate`);
    }
    result.set(row.trial_id, row);
  }
  return result;
}

function emptyCategoryCounts(): Record<FailureCompositionCategoryId, number> {
  return Object.fromEntries(
    FAILURE_COMPOSITION_CATEGORY_IDS.map((id) => [id, 0]),
  ) as Record<FailureCompositionCategoryId, number>;
}

function categoryLabel(id: FailureCompositionCategoryId): string {
  const category = FAILURE_COMPOSITION_CATEGORIES.find(
    (candidate) => candidate.id === id,
  );
  if (!category) throw new Error(`failure_composition_category_unknown:${id}`);
  return category.label;
}

function matchesFailureCompositionCategory(
  id: FailureCompositionCategoryId,
  review: FailureCompositionReviewRow,
  taxonomy: FailureCompositionTaxonomyRow,
): boolean {
  switch (id) {
    case "provider_policy_refusal":
      return review.policy_disposition === "provider_policy_refusal";
    case "invalid_response_path":
      return review.execution_validity === "invalid_response_path";
    case "missing_required_output":
      return review.failure_subtype === "missing_required_output";
    case "extraneous_output_artifacts":
      return review.failure_subtype === "extraneous_output_artifacts";
    case "timeout_after_meaningful_activity":
      return review.activity_subtype === "timeout_after_meaningful_activity";
    case "verifier_task_failure":
      return taxonomy.verifier_failure_category.value !== "none";
    case "unknown_or_incomplete_evidence":
      return true;
  }
}

export function classifyFailureCompositionTrial(
  review: FailureCompositionReviewRow,
  taxonomy: FailureCompositionTaxonomyRow,
): FailureCompositionCategoryId | null {
  if (review.raw_outcome !== "failure") return null;

  for (const id of FAILURE_COMPOSITION_SELECTION_PRECEDENCE) {
    if (matchesFailureCompositionCategory(id, review, taxonomy)) {
      return id;
    }
  }

  throw new Error("failure_composition_selection_precedence_incomplete");
}

function frozenCategoryCounts(
  counts: Readonly<Record<FailureCompositionCategoryId, number>>,
  denominator: number,
): readonly FailureCompositionCategoryCount[] {
  return Object.freeze(
    FAILURE_COMPOSITION_CATEGORY_IDS.map((id) =>
      Object.freeze({
        id,
        label: categoryLabel(id),
        count: counts[id],
        shareOfRawFailures:
          denominator === 0 ? 0 : counts[id] / denominator,
      }),
    ),
  );
}

export function buildFailureCompositionModel(
  reviewRows: readonly FailureCompositionReviewRow[],
  taxonomyRows: readonly FailureCompositionTaxonomyRow[],
): FailureCompositionModel {
  requireExactCount(
    reviewRows.length,
    EXPECTED_TRIAL_COUNT,
    "review_trial_count_mismatch",
  );
  requireExactCount(
    taxonomyRows.length,
    EXPECTED_TRIAL_COUNT,
    "taxonomy_trial_count_mismatch",
  );

  const reviewById = indexRows(reviewRows, "review");
  const taxonomyById = indexRows(taxonomyRows, "taxonomy");

  if (
    reviewById.size !== taxonomyById.size
    || [...reviewById.keys()].some((trialId) => !taxonomyById.has(trialId))
  ) {
    throw new Error("failure_composition_trial_set_mismatch");
  }

  const allowedOutcomes = new Set(["failure", "success", "not_recorded"]);
  if (reviewRows.some((row) => !allowedOutcomes.has(row.raw_outcome))) {
    throw new Error("failure_composition_raw_outcome_unknown");
  }

  for (const review of reviewRows) {
    const taxonomy = taxonomyById.get(review.trial_id);
    if (!taxonomy) {
      throw new Error("failure_composition_trial_join_missing");
    }
    if (
      taxonomy.arm_id !== review.arm_id
      || taxonomy.task_id !== review.task_id
      || taxonomy.raw_outcome !== review.raw_outcome
    ) {
      throw new Error("failure_composition_trial_join_identity_mismatch");
    }
  }

  const armIds = [...new Set(reviewRows.map((row) => row.arm_id))]
    .sort(stableTextCompare);

  requireExactCount(
    armIds.length,
    EXPECTED_ARM_COUNT,
    "failure_composition_arm_count_mismatch",
  );

  if (
    armIds.length !== FAILURE_COMPOSITION_ARM_IDS.length
    || armIds.some(
      (armId, index) => armId !== FAILURE_COMPOSITION_ARM_IDS[index],
    )
  ) {
    throw new Error("failure_composition_arm_membership_mismatch");
  }

  for (const armId of armIds) {
    requireExactCount(
      reviewRows.filter((row) => row.arm_id === armId).length,
      EXPECTED_TRIALS_PER_ARM,
      `failure_composition_arm_trial_count_mismatch:${armId}`,
    );
  }

  const rawFailureCount = reviewRows.filter(
    (row) => row.raw_outcome === "failure",
  ).length;
  const successCount = reviewRows.filter(
    (row) => row.raw_outcome === "success",
  ).length;
  const notRecordedCount = reviewRows.filter(
    (row) => row.raw_outcome === "not_recorded",
  ).length;
  const successfulTimeoutAfterMeaningfulActivityCount = reviewRows.filter(
    (row) =>
      row.raw_outcome === "success"
      && row.activity_subtype === "timeout_after_meaningful_activity",
  ).length;

  requireExactCount(
    rawFailureCount,
    EXPECTED_RAW_FAILURE_COUNT,
    "failure_composition_raw_failure_count_mismatch",
  );
  requireExactCount(
    successCount,
    EXPECTED_SUCCESS_COUNT,
    "failure_composition_success_count_mismatch",
  );
  requireExactCount(
    notRecordedCount,
    EXPECTED_NOT_RECORDED_COUNT,
    "failure_composition_not_recorded_count_mismatch",
  );
  requireExactCount(
    successfulTimeoutAfterMeaningfulActivityCount,
    EXPECTED_SUCCESSFUL_TIMEOUT_COUNT,
    "failure_composition_successful_timeout_count_mismatch",
  );

  const globalCounts = emptyCategoryCounts();
  const perArmCounts = new Map<
    string,
    Record<FailureCompositionCategoryId, number>
  >(
    armIds.map((armId) => [armId, emptyCategoryCounts()]),
  );

  const residualTrials: Array<{
    review: FailureCompositionReviewRow;
    taxonomy: FailureCompositionTaxonomyRow;
  }> = [];

  for (const review of reviewRows) {
    const taxonomy = taxonomyById.get(review.trial_id)!;
    const category = classifyFailureCompositionTrial(review, taxonomy);
    if (!category) continue;

    globalCounts[category] += 1;

    const armCounts = perArmCounts.get(review.arm_id);
    if (!armCounts) {
      throw new Error("failure_composition_arm_membership_missing");
    }
    armCounts[category] += 1;

    if (category === "unknown_or_incomplete_evidence") {
      residualTrials.push({ review, taxonomy });
    }
  }

  requireExactCount(
    Object.values(globalCounts).reduce((sum, count) => sum + count, 0),
    rawFailureCount,
    "failure_composition_partition_total_mismatch",
  );

  for (const id of FAILURE_COMPOSITION_CATEGORY_IDS) {
    requireExactCount(
      globalCounts[id],
      EXPECTED_GLOBAL_CATEGORY_COUNTS[id],
      `failure_composition_category_count_mismatch:${id}`,
    );
  }

  if (
    residualTrials.some(
      ({ review, taxonomy }) =>
        review.execution_validity !== "unknown"
        || review.activity_subtype !== "activity_unknown"
        || review.failure_subtype !== "timeout"
        || review.termination_subtype !== "timeout"
        || review.manual_review_required !== "True"
        || taxonomy.response_path_class.value !== "unknown"
        || taxonomy.verifier_failure_category.value !== "none",
    )
  ) {
    throw new Error("failure_composition_residual_semantics_mismatch");
  }

  const evidenceCompleteCount = residualTrials.filter(
    ({ review }) => review.evidence_complete === "True",
  ).length;
  const evidenceIncompleteCount = residualTrials.filter(
    ({ review }) => review.evidence_complete === "False",
  ).length;
  const highConfidenceCount = residualTrials.filter(
    ({ review }) => review.classification_confidence === "high",
  ).length;
  const mediumConfidenceCount = residualTrials.filter(
    ({ review }) => review.classification_confidence === "medium",
  ).length;
  const noSubstantiveAttemptCount = residualTrials.filter(
    ({ taxonomy }) =>
      taxonomy.trajectory_disposition.value === "no_substantive_attempt",
  ).length;
  const indeterminateCount = residualTrials.filter(
    ({ taxonomy }) =>
      taxonomy.trajectory_disposition.value === "indeterminate",
  ).length;

  requireExactCount(
    residualTrials.length,
    34,
    "failure_composition_residual_count_mismatch",
  );
  requireExactCount(
    evidenceCompleteCount,
    27,
    "failure_composition_residual_complete_mismatch",
  );
  requireExactCount(
    evidenceIncompleteCount,
    7,
    "failure_composition_residual_incomplete_mismatch",
  );
  requireExactCount(
    highConfidenceCount,
    27,
    "failure_composition_residual_high_confidence_mismatch",
  );
  requireExactCount(
    mediumConfidenceCount,
    7,
    "failure_composition_residual_medium_confidence_mismatch",
  );
  requireExactCount(
    noSubstantiveAttemptCount,
    27,
    "failure_composition_residual_no_attempt_mismatch",
  );
  requireExactCount(
    indeterminateCount,
    7,
    "failure_composition_residual_indeterminate_mismatch",
  );

  const arms = armIds.map((armId): FailureCompositionArm => {
    const rows = reviewRows.filter((row) => row.arm_id === armId);
    const rawFailures = rows.filter(
      (row) => row.raw_outcome === "failure",
    ).length;
    const armCounts = perArmCounts.get(armId)!;

    requireExactCount(
      Object.values(armCounts).reduce((sum, count) => sum + count, 0),
      rawFailures,
      `failure_composition_arm_partition_mismatch:${armId}`,
    );

    return Object.freeze({
      armId,
      trialCount: rows.length,
      rawFailureCount: rawFailures,
      successCount: rows.filter(
        (row) => row.raw_outcome === "success",
      ).length,
      notRecordedCount: rows.filter(
        (row) => row.raw_outcome === "not_recorded",
      ).length,
      categories: frozenCategoryCounts(armCounts, rawFailures),
    });
  });

  return Object.freeze({
    scopeId: FAILURE_COMPOSITION_SCOPE_ID,
    trialCount: reviewRows.length,
    armCount: armIds.length,
    trialsPerArm: EXPECTED_TRIALS_PER_ARM,
    rawFailureCount,
    successCount,
    notRecordedCount,
    successfulTimeoutAfterMeaningfulActivityCount,
    categories: frozenCategoryCounts(globalCounts, rawFailureCount),
    residualBreakdown: Object.freeze({
      count: residualTrials.length,
      evidenceCompleteCount,
      evidenceIncompleteCount,
      highConfidenceCount,
      mediumConfidenceCount,
      noSubstantiveAttemptCount,
      indeterminateCount,
    }),
    arms: Object.freeze(arms),
  });
}
