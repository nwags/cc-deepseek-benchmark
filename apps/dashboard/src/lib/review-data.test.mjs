import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const compile = (source) => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
}).outputText;
const digest = (text) => createHash("sha256").update(text).digest("hex");

const reviewDir = await mkdtemp(join(tmpdir(), "cc-review-manifest-"));
const previousDirectory = process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR;
process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR = reviewDir;

const coreSource = await readFile(join(here, "trial-analysis-core.ts"), "utf8");
const generatorSource = await readFile(resolve(here, "../../../../scripts/generate_comprehensive_evidence_review.py"), "utf8");
const analyzerVersion = coreSource.match(/ANALYZER_VERSION = "([^"]+)"/)?.[1];
assert.ok(analyzerVersion);
const coreStub = `data:text/javascript;base64,${Buffer.from(`export const ANALYZER_VERSION=${JSON.stringify(analyzerVersion)};`).toString("base64")}`;
const reviewSource = (await readFile(join(here, "review-data.ts"), "utf8"))
  .replace('from "./trial-analysis-core"', `from "${coreStub}"`);
const reviewUrl = `data:text/javascript;base64,${Buffer.from(compile(reviewSource)).toString("base64")}`;
const reviewModule = await import(reviewUrl);

test.after(async () => {
  if (previousDirectory === undefined) delete process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR;
  else process.env.DASHBOARD_COMPREHENSIVE_REVIEW_DIR = previousDirectory;
  await rm(reviewDir, { recursive: true, force: true });
});

async function writeSnapshot() {
  const outputs = {
    "README.md": "safe review\n",
    "review_coverage.json": JSON.stringify({ analyzer_version: analyzerVersion, generated_at: "2026-08-01T00:00:00Z", runs_discovered: 1, valid_runs_reviewed: 1, trials_reviewed: 1, artifact_rows_discovered: 8, complete_evidence_trials: 1, incomplete_evidence_trials: 0, confidence: { high: 1 }, manual_review_queue: 1, manual_control_sample: 1, task_disagreement_rows: 0 }) + "\n",
    "run_review.csv": "run_id,selected\nrun,True\n",
    "arm_review_summary.csv": "arm_id,trials_reviewed\narm,1\n",
    "task_disagreement_review.csv": "task_id,arm_a,arm_b,disagreement_category,headline_relevant,supporting_trial_links\n",
    "review_queue.csv": "trial_id,arm_id,task_id,manual_review_priority,review_reasons,review_strata,trial_link\n00000000-0000-0000-0000-000000000001,arm,task,high,timeout,correctness_anomaly,/trials/00000000-0000-0000-0000-000000000001\n",
    "manual_control_sample.csv": "sample_stratum,arm_id,trial_id,task_id,trial_link\nordinary_success,arm,00000000-0000-0000-0000-000000000001,task,/trials/00000000-0000-0000-0000-000000000001\n",
    "trial_review.csv": "trial_id,raw_outcome,activity_subtype,execution_validity,failure_subtype,termination_subtype,policy_disposition,telemetry_status,database_result_consistency,classification_confidence,evidence_complete,manual_review_required,manual_review_priority,analyzer_version,router_observability,result_reward_present,result_reward_value,result_exception_present,result_exception_type,result_termination_reason,result_status,analyzed_artifact_integrity_status\n00000000-0000-0000-0000-000000000001,success,substantive_agent_activity,substantive,none,none,none_detected,consistent,consistent,high,True,False,low,${analyzerVersion},unknown,True,1,False,,,completed,verified\n",
    "trial_evidence.jsonl": JSON.stringify({ trial_id: "00000000-0000-0000-0000-000000000001", summary: "safe", evidence: [], configuration: {} }) + "\n",
    "targeted_evidence_packet.csv": "packet_strata,trial_id\ncontrols,00000000-0000-0000-0000-000000000001\n",
    "targeted_evidence_bundle.jsonl": JSON.stringify({ identity: { trial_id: "00000000-0000-0000-0000-000000000001" }, hidden_reasoning_retained: false }) + "\n",
    "targeted_evidence_bundle_manifest.json": JSON.stringify({ schema_version: "targeted-manual-evidence-bundle-v1", trial_count: 1 }) + "\n"
  };
  await Promise.all(Object.entries(outputs).map(([name, text]) => writeFile(join(reviewDir, name), text)));
  const rowCounts = Object.fromEntries(Object.entries(outputs).filter(([name]) => name.endsWith(".csv") || name.endsWith(".jsonl")).map(([name, text]) => [name, name.endsWith(".jsonl") ? text.trim().split("\n").length : Math.max(text.trim().split("\n").length - 1, 0)]));
  const manifest = {
    schema_version: "comprehensive-evidence-review-manifest-v2",
    analyzer_version: analyzerVersion,
    generator_version: "comprehensive-evidence-review-v1.3.0",
    source_hashes: { analyzer: digest(coreSource), generator: digest(generatorSource) },
    generated_at: "2026-08-01T00:00:00Z", selected_run_ids: ["run"], scope_fingerprint: "scope",
    row_counts: rowCounts,
    outputs: Object.fromEntries(Object.entries(outputs).map(([name, text]) => [name, { sha256: digest(text), bytes: Buffer.byteLength(text), rows: rowCounts[name] ?? null }]))
  };
  await writeFile(join(reviewDir, "review_manifest.json"), JSON.stringify(manifest));
}

test("manifest-bound snapshot is indexed once and tampering becomes an explicit mixed-output state", async () => {
  await writeSnapshot();
  reviewModule.resetReviewDataCacheForTests();
  const valid = await reviewModule.getComprehensiveReviewData();
  assert.equal(valid.state, "available");
  assert.equal(valid.queue.length, 1);
  const trial = await reviewModule.getComprehensiveTrialReview("00000000-0000-0000-0000-000000000001");
  assert.equal(trial.raw_outcome, "success");
  assert.equal(trial.snapshot_summary, "safe");

  await writeFile(join(reviewDir, "review_queue.csv"), "tampered\n");
  reviewModule.resetReviewDataCacheForTests();
  const mixed = await reviewModule.getComprehensiveReviewData();
  assert.equal(mixed.state, "mixed_output");
  assert.equal(mixed.available, false);
});

test("manifest rejects unknown, traversal, and absolute output filenames before reading them", async () => {
  for (const unsafeName of ["unknown.csv", "../outside.csv", "/tmp/absolute.csv"]) {
    await writeSnapshot();
    const manifestPath = join(reviewDir, "review_manifest.json");
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    manifest.outputs[unsafeName] = manifest.outputs["review_queue.csv"];
    await writeFile(manifestPath, JSON.stringify(manifest));
    reviewModule.resetReviewDataCacheForTests();
    const rejected = await reviewModule.getComprehensiveReviewData();
    assert.equal(rejected.state, "mixed_output", unsafeName);
    assert.equal(rejected.available, false, unsafeName);
  }
});

test("disagreement outcome summaries distinguish success, failure, and missing rewards per arm", () => {
  const trialIds = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
    "00000000-0000-0000-0000-000000000003",
    "00000000-0000-0000-0000-000000000004",
    "00000000-0000-0000-0000-000000000005",
    "00000000-0000-0000-0000-000000000006",
  ];
  const trials = trialIds.map((trial_id, index) => ({
    trial_id,
    arm_id: index < 3 ? "arm-a" : "arm-b",
    raw_outcome: ["success", "failure", "not_recorded", "failure", "failure", "success"][index],
  }));
  const [row] = reviewModule.enrichDisagreementOutcomes([{
    task_id: "task",
    arm_a: "arm-a",
    arm_b: "arm-b",
    supporting_trial_links: JSON.stringify(trialIds.map((trialId) => `/trials/${trialId}`)),
  }], trials);
  assert.equal(row.arm_a_raw_outcome_summary, "success:1;failure:1;not_recorded:1");
  assert.equal(row.arm_b_raw_outcome_summary, "success:1;failure:2");
});
