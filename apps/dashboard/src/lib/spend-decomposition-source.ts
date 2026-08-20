import "server-only";

import { createHash } from "node:crypto";
import path from "node:path";

const CORE_COST_RELATIVE_PATH =
  "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv";
const REVIEW_RELATIVE_PATH =
  "results/manual_verification/comprehensive_review_20260731/trial_review.csv";

const EXPECTED_CORE_COST_SHA256 =
  "dda44c435b555d3f358a47b5885c659b9ae0554511959ca9d40f76bc9539f5a3";
const EXPECTED_REVIEW_SHA256 =
  "c6945d114e3a2e0610dfd091bad8ea4e9bc17707db678e90f4e0f8058fc56501";

const EXPECTED_CORE_TRIAL_COUNT = 900;
const EXPECTED_CORE_ARM_COUNT = 15;
const EXPECTED_REVIEW_TRIAL_COUNT = 960;
const EXPECTED_REVIEW_ARM_COUNT = 16;
const EXPECTED_TRIALS_PER_ARM = 60;

const MAX_FILE_BYTES = 32 * 1024 * 1024;

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const NONNEGATIVE_DECIMAL_PATTERN =
  /^(?:0|[1-9]\d*)(?:\.\d+)?$/;

export const SPEND_DECOMPOSITION_OUTCOME_BUCKETS = [
  "clean_success",
  "normal_failure",
  "exception_failure",
  "exception_with_success_signal",
] as const;

export type SpendDecompositionOutcomeBucket =
  (typeof SPEND_DECOMPOSITION_OUTCOME_BUCKETS)[number];

export type SpendDecompositionCoreSourceRow = Readonly<{
  trial_id: string;
  arm_id: string;
  task_id: string;
  outcome_bucket: SpendDecompositionOutcomeBucket;
  recorded_cost_usd: string;
  cost_source: string;
}>;

export type SpendDecompositionReviewSourceRow = Readonly<{
  trial_id: string;
  arm_id: string;
  task_id: string;
  raw_outcome: "success" | "failure" | "not_recorded";
  raw_reward_present: boolean;
  raw_reward: string;
  cost_usd: string;
  exception_type: string;
}>;

export type SpendDecompositionSourceProvenance = Readonly<{
  coreCostPath: typeof CORE_COST_RELATIVE_PATH;
  coreCostSha256: typeof EXPECTED_CORE_COST_SHA256;
  reviewPath: typeof REVIEW_RELATIVE_PATH;
  reviewSha256: typeof EXPECTED_REVIEW_SHA256;
  coreTrialCount: typeof EXPECTED_CORE_TRIAL_COUNT;
  reviewTrialCount: typeof EXPECTED_REVIEW_TRIAL_COUNT;
}>;

export type SpendDecompositionSourceState =
  | "available"
  | "unavailable"
  | "invalid";

export type SpendDecompositionSource = Readonly<{
  available: boolean;
  state: SpendDecompositionSourceState;
  message: string;
  coreRows: readonly SpendDecompositionCoreSourceRow[];
  reviewRows: readonly SpendDecompositionReviewSourceRow[];
  provenance: SpendDecompositionSourceProvenance | null;
}>;

type ValidatedSpendDecompositionSource = Readonly<{
  coreRows: readonly SpendDecompositionCoreSourceRow[];
  reviewRows: readonly SpendDecompositionReviewSourceRow[];
  provenance: SpendDecompositionSourceProvenance;
}>;

let cachedSource: Promise<SpendDecompositionSource> | null = null;

function repoRoot(): string {
  return process.cwd().endsWith(path.join("apps", "dashboard"))
    ? path.resolve(process.cwd(), "..", "..")
    : process.cwd();
}

async function importFs(): Promise<typeof import("node:fs/promises")> {
  const runtimeImport = new Function(
    "specifier",
    "return import(specifier)",
  ) as (
    specifier: string,
  ) => Promise<typeof import("node:fs/promises")>;

  return runtimeImport("node:fs/promises");
}

async function readBounded(relativePath: string): Promise<Buffer> {
  const { readFile, stat } = await importFs();
  const filePath = path.join(repoRoot(), relativePath);
  const metadata = await stat(filePath);

  if (!metadata.isFile() || metadata.size > MAX_FILE_BYTES) {
    throw new Error("file_unavailable_or_oversized");
  }

  return readFile(filePath);
}

function digest(value: Buffer | string): string {
  return createHash("sha256").update(value).digest("hex");
}

function parseDelimited(
  contents: Buffer,
  delimiter: "," | "\t",
  label: string,
): readonly Record<string, string>[] {
  const text = contents.toString("utf8");
  const parsedRows: string[][] = [];

  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];

    if (quoted) {
      if (character === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        field += character;
      }
      continue;
    }

    if (character === '"') {
      if (field.length !== 0) {
        throw new Error(`${label}_malformed_quote`);
      }
      quoted = true;
      continue;
    }

    if (character === delimiter) {
      row.push(field);
      field = "";
      continue;
    }

    if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value !== "")) {
        parsedRows.push(row);
      }
      row = [];
      field = "";
      continue;
    }

    field += character;
  }

  if (quoted) {
    throw new Error(`${label}_unterminated_quote`);
  }

  if (field.length !== 0 || row.length !== 0) {
    row.push(field.replace(/\r$/, ""));
    if (row.some((value) => value !== "")) {
      parsedRows.push(row);
    }
  }

  const [rawHeader, ...data] = parsedRows;
  if (!rawHeader?.length) {
    throw new Error(`${label}_missing_header`);
  }

  const header = rawHeader.map((value, index) =>
    index === 0 ? value.replace(/^\uFEFF/, "") : value,
  );

  if (
    header.some((value) => value === "")
    || new Set(header).size !== header.length
  ) {
    throw new Error(`${label}_invalid_header`);
  }

  return Object.freeze(
    data.map((values, index) => {
      if (values.length !== header.length) {
        throw new Error(`${label}_column_count_mismatch:${index + 2}`);
      }

      return Object.freeze(
        Object.fromEntries(
          header.map((key, column) => [key, values[column]]),
        ),
      );
    }),
  );
}

function field(
  row: Readonly<Record<string, string>>,
  name: string,
  code: string,
): string {
  if (!Object.prototype.hasOwnProperty.call(row, name)) {
    throw new Error(code);
  }
  return row[name];
}

function requiredText(
  row: Readonly<Record<string, string>>,
  name: string,
  code: string,
): string {
  const value = field(row, name, code);
  if (value.trim() === "") {
    throw new Error(code);
  }
  return value;
}

function optionalDecimal(
  row: Readonly<Record<string, string>>,
  name: string,
  code: string,
): string {
  const value = field(row, name, code).trim();

  if (
    value !== ""
    && !NONNEGATIVE_DECIMAL_PATTERN.test(value)
  ) {
    throw new Error(code);
  }

  return value;
}

function booleanField(
  row: Readonly<Record<string, string>>,
  name: string,
  code: string,
): boolean {
  const normalized = requiredText(row, name, code)
    .trim()
    .toLowerCase();

  if (normalized === "true") return true;
  if (normalized === "false") return false;

  throw new Error(code);
}

function requireUuid(value: string, code: string): string {
  if (!UUID_PATTERN.test(value)) {
    throw new Error(code);
  }
  return value;
}

function validateCoreRow(
  row: Readonly<Record<string, string>>,
): SpendDecompositionCoreSourceRow {
  const outcomeBucket = requiredText(
    row,
    "outcome_bucket",
    "core_outcome_bucket_invalid",
  );

  if (
    !SPEND_DECOMPOSITION_OUTCOME_BUCKETS.includes(
      outcomeBucket as SpendDecompositionOutcomeBucket,
    )
  ) {
    throw new Error("core_outcome_bucket_invalid");
  }

  return Object.freeze({
    trial_id: requireUuid(
      requiredText(row, "trial_id", "core_trial_id_invalid"),
      "core_trial_id_invalid",
    ),
    arm_id: requiredText(
      row,
      "arm_id",
      "core_arm_id_invalid",
    ),
    task_id: requiredText(
      row,
      "task_id",
      "core_task_id_invalid",
    ),
    outcome_bucket:
      outcomeBucket as SpendDecompositionOutcomeBucket,
    recorded_cost_usd: optionalDecimal(
      row,
      "recorded_cost_usd",
      "core_recorded_cost_invalid",
    ),
    cost_source: requiredText(
      row,
      "cost_source",
      "core_cost_source_invalid",
    ),
  });
}

function validateReviewRow(
  row: Readonly<Record<string, string>>,
): SpendDecompositionReviewSourceRow {
  const rawOutcome = requiredText(
    row,
    "raw_outcome",
    "review_raw_outcome_invalid",
  );

  if (
    rawOutcome !== "success"
    && rawOutcome !== "failure"
    && rawOutcome !== "not_recorded"
  ) {
    throw new Error("review_raw_outcome_invalid");
  }

  const rawRewardPresent = booleanField(
    row,
    "raw_reward_present",
    "review_raw_reward_present_invalid",
  );

  const rawReward = optionalDecimal(
    row,
    "raw_reward",
    "review_raw_reward_invalid",
  );

  if (rawRewardPresent && rawReward === "") {
    throw new Error("review_raw_reward_missing");
  }

  if (!rawRewardPresent && rawReward !== "") {
    throw new Error("review_raw_reward_present_mismatch");
  }

  return Object.freeze({
    trial_id: requireUuid(
      requiredText(row, "trial_id", "review_trial_id_invalid"),
      "review_trial_id_invalid",
    ),
    arm_id: requiredText(
      row,
      "arm_id",
      "review_arm_id_invalid",
    ),
    task_id: requiredText(
      row,
      "task_id",
      "review_task_id_invalid",
    ),
    raw_outcome: rawOutcome,
    raw_reward_present: rawRewardPresent,
    raw_reward: rawReward,
    cost_usd: optionalDecimal(
      row,
      "cost_usd",
      "review_cost_invalid",
    ),
    exception_type: field(
      row,
      "exception_type",
      "review_exception_type_missing",
    ),
  });
}

function validatePopulation<T extends {
  trial_id: string;
  arm_id: string;
}>(
  rows: readonly T[],
  expectedTrialCount: number,
  expectedArmCount: number,
  label: string,
): void {
  if (rows.length !== expectedTrialCount) {
    throw new Error(
      `${label}_trial_count_mismatch:${rows.length}:${expectedTrialCount}`,
    );
  }

  const ids = rows.map((row) => row.trial_id);
  if (new Set(ids).size !== ids.length) {
    throw new Error(`${label}_duplicate_trial_id`);
  }

  const armCounts = new Map<string, number>();
  for (const row of rows) {
    armCounts.set(
      row.arm_id,
      (armCounts.get(row.arm_id) ?? 0) + 1,
    );
  }

  if (armCounts.size !== expectedArmCount) {
    throw new Error(
      `${label}_arm_count_mismatch:${armCounts.size}:${expectedArmCount}`,
    );
  }

  for (const [armId, count] of armCounts) {
    if (count !== EXPECTED_TRIALS_PER_ARM) {
      throw new Error(
        `${label}_arm_trial_count_mismatch:${armId}:${count}`,
      );
    }
  }
}

function validateSourceBytes(
  coreBytes: Buffer,
  reviewBytes: Buffer,
): ValidatedSpendDecompositionSource {
  if (digest(coreBytes) !== EXPECTED_CORE_COST_SHA256) {
    throw new Error("core_cost_hash_mismatch");
  }

  if (digest(reviewBytes) !== EXPECTED_REVIEW_SHA256) {
    throw new Error("comprehensive_review_hash_mismatch");
  }

  const coreRows = Object.freeze(
    parseDelimited(
      coreBytes,
      "\t",
      "core_cost_source",
    ).map(validateCoreRow),
  );

  const reviewRows = Object.freeze(
    parseDelimited(
      reviewBytes,
      ",",
      "comprehensive_review_source",
    ).map(validateReviewRow),
  );

  validatePopulation(
    coreRows,
    EXPECTED_CORE_TRIAL_COUNT,
    EXPECTED_CORE_ARM_COUNT,
    "core_cost_source",
  );

  validatePopulation(
    reviewRows,
    EXPECTED_REVIEW_TRIAL_COUNT,
    EXPECTED_REVIEW_ARM_COUNT,
    "comprehensive_review_source",
  );

  return Object.freeze({
    coreRows,
    reviewRows,
    provenance: Object.freeze({
      coreCostPath: CORE_COST_RELATIVE_PATH,
      coreCostSha256: EXPECTED_CORE_COST_SHA256,
      reviewPath: REVIEW_RELATIVE_PATH,
      reviewSha256: EXPECTED_REVIEW_SHA256,
      coreTrialCount: EXPECTED_CORE_TRIAL_COUNT,
      reviewTrialCount: EXPECTED_REVIEW_TRIAL_COUNT,
    }),
  });
}

function unavailableSource(
  state: Exclude<SpendDecompositionSourceState, "available">,
  message: string,
): SpendDecompositionSource {
  return Object.freeze({
    available: false,
    state,
    message,
    coreRows: Object.freeze([]),
    reviewRows: Object.freeze([]),
    provenance: null,
  });
}

async function loadSource(): Promise<SpendDecompositionSource> {
  let coreBytes: Buffer;
  let reviewBytes: Buffer;

  try {
    [coreBytes, reviewBytes] = await Promise.all([
      readBounded(CORE_COST_RELATIVE_PATH),
      readBounded(REVIEW_RELATIVE_PATH),
    ]);
  } catch {
    return unavailableSource(
      "unavailable",
      "Frozen DR-303 spend sources are unavailable.",
    );
  }

  try {
    const validated = validateSourceBytes(
      coreBytes,
      reviewBytes,
    );

    return Object.freeze({
      available: true,
      state: "available",
      message:
        "Frozen DR-303 spend sources passed exact hash and population validation.",
      coreRows: validated.coreRows,
      reviewRows: validated.reviewRows,
      provenance: validated.provenance,
    });
  } catch (error) {
    const reason =
      error instanceof Error
        ? error.message
        : "unknown_validation_error";

    return unavailableSource(
      "invalid",
      `Frozen DR-303 spend sources failed validation: ${reason}.`,
    );
  }
}

export function validateSpendDecompositionSourceBytesForTests(
  coreBytes: Buffer,
  reviewBytes: Buffer,
): ValidatedSpendDecompositionSource {
  return validateSourceBytes(coreBytes, reviewBytes);
}

export async function getSpendDecompositionSource(): Promise<
  SpendDecompositionSource
> {
  cachedSource ??= loadSource();
  return cachedSource;
}

export function resetSpendDecompositionSourceCacheForTests(): void {
  cachedSource = null;
}
