import path from "node:path";
import { createHash } from "node:crypto";
import { ANALYZER_VERSION } from "./trial-analysis-core";

export type ReviewCoverage = {
  analyzer_version: string;
  generated_at: string;
  runs_discovered: number;
  valid_runs_reviewed: number;
  trials_reviewed: number;
  artifact_rows_discovered: number;
  complete_evidence_trials: number;
  incomplete_evidence_trials: number;
  confidence: Record<string, number>;
  manual_review_queue: number;
  manual_control_sample: number;
  manual_control_strata?: Record<string, number>;
  review_queue_priorities?: Record<string, number>;
  review_queue_strata?: Record<string, number>;
  task_disagreement_rows: number;
  task_disagreement_categories?: Record<string, number>;
  targeted_evidence_packet?: number;
  r2_read_availability?: Record<string, number>;
  analyzed_artifact_integrity_status?: Record<string, number>;
  size_metadata_status?: Record<string, number>;
};

export type ArmReviewSummary = Record<string, string> & { arm_id: string };

export type TaskDisagreementReview = Record<string, string> & {
  task_id: string;
  arm_a: string;
  arm_b: string;
  disagreement_category: string;
  headline_relevant: string;
  supporting_trial_links: string;
  arm_a_raw_outcome_summary?: string;
  arm_b_raw_outcome_summary?: string;
};

export type ReviewQueueRow = Record<string, string> & {
  trial_id: string;
  arm_id: string;
  task_id: string;
  manual_review_priority: string;
  review_reasons: string;
  review_strata: string;
  trial_link: string;
};

export type ControlSampleRow = Record<string, string> & {
  sample_stratum: string;
  arm_id: string;
  trial_id: string;
  task_id: string;
  trial_link: string;
};

export type SnapshotEvidence = {
  label: string;
  value: string;
  source: string;
  artifactType?: string;
  artifactId?: string;
};

export type ComprehensiveTrialReview = {
  [key: string]: unknown;
  trial_id: string;
  run_label: string;
  suite_id: string;
  arm_id: string;
  task_id: string;
  raw_outcome: string;
  activity_subtype: string;
  execution_validity: string;
  failure_subtype: string;
  termination_subtype: string;
  policy_disposition: string;
  telemetry_status: string;
  database_result_consistency: string;
  classification_confidence: string;
  evidence_complete: string;
  manual_review_required: string;
  manual_review_priority: string;
  analyzer_version: string;
  router_observability: string;
  result_reward_present: string;
  result_reward_value: string;
  result_exception_present: string;
  result_exception_type: string;
  result_termination_reason: string;
  result_status: string;
  database_exception_summary: string;
  database_exception_summary_present: string;
  database_exception_summary_trusted_markers: string;
  r2_indexed_completeness: string;
  r2_read_availability: string;
  analyzed_artifact_integrity_status: string;
  size_metadata_status: string;
  snapshot_summary?: string;
  snapshot_evidence?: SnapshotEvidence[];
  snapshot_configuration?: Record<string, string | null>;
};

type ManifestOutput = { sha256: string; bytes: number; rows?: number | null };
export type ReviewManifest = {
  schema_version: string;
  analyzer_version: string;
  generator_version: string;
  source_hashes: { analyzer: string; generator: string };
  generated_at: string;
  selected_run_ids: string[];
  scope_fingerprint: string;
  scope_fingerprint_inputs?: Record<string, unknown>;
  row_counts: Record<string, number>;
  outputs: Record<string, ManifestOutput>;
};

export type ReviewState = "available" | "unavailable" | "stale" | "mixed_output";

export type ComprehensiveReviewData = {
  available: boolean;
  state: ReviewState;
  directory: string;
  message: string;
  manifest: ReviewManifest | null;
  coverage: ReviewCoverage | null;
  arms: ArmReviewSummary[];
  disagreements: TaskDisagreementReview[];
  queue: ReviewQueueRow[];
  controls: ControlSampleRow[];
  reviewedTrials: ComprehensiveTrialReview[];
};

type ReviewIndex = ComprehensiveReviewData & { trials: Map<string, ComprehensiveTrialReview> };

const MANIFEST_SCHEMA_VERSION = "comprehensive-evidence-review-manifest-v2";
const MAX_REVIEW_FILE_BYTES = 32 * 1024 * 1024;
const MANIFEST_OUTPUT_NAMES = new Set([
  "README.md",
  "arm_review_summary.csv",
  "manual_control_sample.csv",
  "review_coverage.json",
  "review_queue.csv",
  "run_review.csv",
  "targeted_evidence_bundle.jsonl",
  "targeted_evidence_bundle_manifest.json",
  "targeted_evidence_packet.csv",
  "task_disagreement_review.csv",
  "trial_evidence.jsonl",
  "trial_review.csv",
]);
let cachedReviewIndex: Promise<ReviewIndex> | null = null;

async function importFs(): Promise<typeof import("node:fs/promises")> {
  const runtimeImport = new Function("specifier", "return import(specifier)") as (
    specifier: string
  ) => Promise<typeof import("node:fs/promises")>;
  return runtimeImport("node:fs/promises");
}

function reviewDirectory() {
  if (process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR) return path.resolve(process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR);
  const suffix = path.join("results", "manual_verification", "comprehensive_review_20260731");
  return process.cwd().endsWith(path.join("apps", "dashboard"))
    ? path.resolve(process.cwd(), "..", "..", suffix)
    : path.resolve(process.cwd(), suffix);
}

function repoRoot() {
  return process.cwd().endsWith(path.join("apps", "dashboard"))
    ? path.resolve(process.cwd(), "..", "..") : process.cwd();
}

async function readBounded(filePath: string) {
  const { readFile, stat } = await importFs();
  const file = await stat(filePath);
  if (!file.isFile() || file.size > MAX_REVIEW_FILE_BYTES) throw new Error("review_file_unavailable_or_oversized");
  return readFile(filePath, "utf8");
}

function digest(text: string) {
  return createHash("sha256").update(text).digest("hex");
}

export function parseCsv(text: string): Array<Record<string, string>> {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') { field += '"'; index += 1; }
      else if (character === '"') quoted = false;
      else field += character;
    } else if (character === '"') quoted = true;
    else if (character === ",") { row.push(field); field = ""; }
    else if (character === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += character;
  }
  if (field || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  const [header, ...data] = rows;
  if (!header?.length) return [];
  return data.filter((values) => values.some(Boolean))
    .map((values) => Object.fromEntries(header.map((key, index) => [key, values[index] ?? ""])));
}

function jsonl(text: string): Array<Record<string, unknown>> {
  return text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line) as Record<string, unknown>);
}

function trialIdsFromLinks(value: string) {
  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed)
      ? parsed.flatMap((item) => typeof item === "string" && /^\/trials\/[0-9a-f-]{36}$/i.test(item)
        ? [item.slice("/trials/".length)] : [])
      : [];
  } catch {
    return [];
  }
}

function outcomeSummary(rows: ComprehensiveTrialReview[]) {
  const order = ["success", "failure", "not_recorded"];
  const counts = new Map<string, number>();
  for (const row of rows) counts.set(row.raw_outcome, (counts.get(row.raw_outcome) ?? 0) + 1);
  return order.filter((outcome) => counts.has(outcome))
    .map((outcome) => `${outcome}:${counts.get(outcome)}`)
    .join(";") || "none recorded";
}

export function enrichDisagreementOutcomes(
  disagreements: TaskDisagreementReview[],
  trialRows: ComprehensiveTrialReview[]
) {
  const byId = new Map(trialRows.map((row) => [row.trial_id, row]));
  return disagreements.map((row) => {
    const trials = trialIdsFromLinks(row.supporting_trial_links)
      .flatMap((trialId) => byId.get(trialId) ? [byId.get(trialId)!] : []);
    return {
      ...row,
      arm_a_raw_outcome_summary: outcomeSummary(trials.filter((trial) => trial.arm_id === row.arm_a)),
      arm_b_raw_outcome_summary: outcomeSummary(trials.filter((trial) => trial.arm_id === row.arm_b)),
    };
  });
}

function emptyIndex(directory: string, state: ReviewState, message: string): ReviewIndex {
  return { available: false, state, directory, message, manifest: null, coverage: null, arms: [], disagreements: [], queue: [], controls: [], reviewedTrials: [], trials: new Map() };
}

async function loadReviewIndex(): Promise<ReviewIndex> {
  const directory = reviewDirectory();
  let manifest: ReviewManifest;
  try {
    manifest = JSON.parse(await readBounded(path.join(directory, "review_manifest.json"))) as ReviewManifest;
  } catch {
    return emptyIndex(directory, "unavailable", "Validated comprehensive-review snapshot is unavailable: review_manifest.json could not be loaded.");
  }
  if (manifest.schema_version !== MANIFEST_SCHEMA_VERSION || manifest.analyzer_version !== ANALYZER_VERSION) {
    return { ...emptyIndex(directory, "stale", "The comprehensive-review snapshot uses an unsupported schema or analyzer version."), manifest };
  }

  const names = Object.keys(manifest.outputs).sort();
  if (names.length !== MANIFEST_OUTPUT_NAMES.size || names.some((name) =>
    !MANIFEST_OUTPUT_NAMES.has(name)
    || path.isAbsolute(name)
    || path.basename(name) !== name
    || name.includes("..")
  )) {
    return { ...emptyIndex(directory, "mixed_output", "Manifest output filenames are incomplete or outside the exact review-output whitelist."), manifest };
  }
  let contents: Record<string, string>;
  try {
    contents = Object.fromEntries(await Promise.all(names.map(async (name) => [name, await readBounded(path.join(directory, name))])));
  } catch {
    return { ...emptyIndex(directory, "mixed_output", "One or more manifest-bound review outputs are missing or oversized."), manifest };
  }
  for (const name of names) {
    const expected = manifest.outputs[name];
    if (digest(contents[name]) !== expected.sha256 || Buffer.byteLength(contents[name]) !== expected.bytes) {
      return { ...emptyIndex(directory, "mixed_output", `Manifest validation failed for ${name}.`), manifest };
    }
  }

  try {
    const [analyzerSource, generatorSource] = await Promise.all([
      readBounded(path.join(repoRoot(), "apps/dashboard/src/lib/trial-analysis-core.ts")),
      readBounded(path.join(repoRoot(), "scripts/generate_comprehensive_evidence_review.py"))
    ]);
    if (digest(analyzerSource) !== manifest.source_hashes.analyzer || digest(generatorSource) !== manifest.source_hashes.generator) {
      return { ...emptyIndex(directory, "stale", "The validated snapshot was generated by different analyzer or generator source."), manifest };
    }
  } catch {
    return { ...emptyIndex(directory, "stale", "Current analyzer/generator sources could not be verified against the snapshot."), manifest };
  }

  try {
    const coverage = JSON.parse(contents["review_coverage.json"]) as ReviewCoverage;
    const arms = parseCsv(contents["arm_review_summary.csv"]) as ArmReviewSummary[];
    const disagreementRows = parseCsv(contents["task_disagreement_review.csv"]) as TaskDisagreementReview[];
    const queue = parseCsv(contents["review_queue.csv"]) as ReviewQueueRow[];
    const controls = parseCsv(contents["manual_control_sample.csv"]) as ControlSampleRow[];
    const trialRows = parseCsv(contents["trial_review.csv"]) as ComprehensiveTrialReview[];
    const disagreements = enrichDisagreementOutcomes(disagreementRows, trialRows);
    const evidenceByTrial = new Map(jsonl(contents["trial_evidence.jsonl"]).map((row) => [String(row.trial_id), row]));
    for (const [name, expectedRows] of Object.entries(manifest.row_counts)) {
      const actual = name.endsWith(".jsonl") ? jsonl(contents[name]).length : parseCsv(contents[name]).length;
      if (actual !== expectedRows) return { ...emptyIndex(directory, "mixed_output", `Manifest row count failed for ${name}.`), manifest };
    }
    const trials = new Map(trialRows.map((row) => {
      const evidence = evidenceByTrial.get(row.trial_id);
      return [row.trial_id, {
        ...row,
        snapshot_summary: typeof evidence?.summary === "string" ? evidence.summary : undefined,
        snapshot_evidence: Array.isArray(evidence?.evidence) ? evidence.evidence as SnapshotEvidence[] : undefined,
        snapshot_configuration: evidence?.configuration && typeof evidence.configuration === "object"
          ? evidence.configuration as Record<string, string | null> : undefined
      } satisfies ComprehensiveTrialReview];
    }));
    return {
      available: true, state: "available", directory,
      message: "Loaded and validated the manifest-bound comprehensive-review snapshot.",
      manifest, coverage, arms, disagreements, queue, controls, reviewedTrials: trialRows, trials
    };
  } catch {
    return { ...emptyIndex(directory, "mixed_output", "Manifest-bound review outputs could not be parsed consistently."), manifest };
  }
}

function getIndex() {
  cachedReviewIndex ??= loadReviewIndex();
  return cachedReviewIndex;
}

export async function getComprehensiveReviewData(): Promise<ComprehensiveReviewData> {
  const { trials: _trials, ...data } = await getIndex();
  return data;
}

export async function getComprehensiveTrialReview(trialId: string): Promise<ComprehensiveTrialReview | null> {
  if (!/^[0-9a-f-]{36}$/i.test(trialId)) return null;
  return (await getIndex()).trials.get(trialId) ?? null;
}

/** Test-only reset for deterministic manifest fixtures. */
export function resetReviewDataCacheForTests() {
  cachedReviewIndex = null;
}
