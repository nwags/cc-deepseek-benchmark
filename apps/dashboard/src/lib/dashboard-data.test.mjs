import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const stubSource = `export async function queryRows(sql, params = []) { return globalThis.__dashboardQueryHandler(sql, params); }`;
const stubUrl = `data:text/javascript;base64,${Buffer.from(stubSource).toString("base64")}`;
const source = await readFile(join(here, "dashboard-data.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
}).outputText.replace('from "./db"', `from "${stubUrl}"`);
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const dashboardData = await import(moduleUrl);
const analysisStubUrl = `data:text/javascript;base64,${Buffer.from(`
  export async function readArtifactForAnalysis() { throw new Error("not used"); }
  export function deriveEvidenceCompleteness() { return {}; }
  export function classifyTrialEvidence() { return {}; }
`).toString("base64")}`;
const trialAnalysisSource = await readFile(join(here, "trial-analysis.ts"), "utf8");
const trialAnalysisCompiled = ts.transpileModule(trialAnalysisSource, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 }
}).outputText
  .replace('from "./artifact-content"', `from "${analysisStubUrl}"`)
  .replace('from "./artifact-types"', `from "${analysisStubUrl}"`)
  .replace('from "./trial-analysis-core"', `from "${analysisStubUrl}"`);
const trialAnalysis = await import(`data:text/javascript;base64,${Buffer.from(trialAnalysisCompiled).toString("base64")}`);

function artifactRows() {
  const types = ["agent_transcript", "config", "log", "result", "trajectory", "verifier_ctrf", "verifier_reward", "verifier_stdout"];
  return [1, 2, 3].flatMap((attempt, groupIndex) => types.map((artifactType, artifactIndex) => ({
    group_key: `trial-${attempt}`,
    artifact_id: `artifact-${attempt}-${artifactIndex}`,
    run_id: "run-id",
    run_label: "router-anthropic-haiku-sanitized/2026-07-12__03-25-22",
    arm_run_id: "arm-run-id",
    suite_id: "phase3-full-20",
    logical_mode: "full",
    storage_mode: "full",
    arm_id: "router-anthropic-haiku-sanitized",
    trial_id: `trial-${attempt}`,
    task_id: "terminal-bench-2.0:multi-source-data-merger",
    attempt_index: 31 + groupIndex,
    run_trial_number: 31 + groupIndex,
    task_attempt_number: attempt,
    task_attempt_count: 3,
    task_ordinal: 11,
    run_task_count: 20,
    reward: attempt === 1 ? 0.5 : 1,
    quality_flag: attempt === 1 ? "normal_failed_trial" : null,
    exception_type: null,
    exception_summary: null,
    artifact_path: `trials/${attempt}/${artifactType}.json`,
    artifact_type: artifactType,
    r2_uri: `r2://bucket/trials/${attempt}/${artifactType}.json`,
    size_bytes: 100,
    created_at: "2026-07-12T00:00:00Z",
    matching_artifact: artifactType === "verifier_reward"
  })));
}

test("group pagination selects matching groups then expands all eight artifacts per Haiku attempt", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    if (sql.includes("total_group_count")) return [{ total_group_count: 3, matching_artifact_count: 3 }];
    return artifactRows();
  };
  const page = await dashboardData.getArtifactBrowserPage({
    run_label: "router-anthropic-haiku-sanitized/2026-07-12__03-25-22",
    task_id: "terminal-bench-2.0:multi-source-data-merger",
    artifact_type: "verifier_reward",
    page: 99,
    page_size: 10
  });
  assert.equal(page.page, 1, "out-of-range page is clamped");
  assert.equal(page.total_group_count, 3);
  assert.equal(page.matching_artifact_count, 3);
  assert.equal(page.expanded_artifact_count, 24);
  assert.deepEqual(page.groups.map((group) => group.task_attempt_number), [1, 2, 3]);
  assert.deepEqual(page.groups.map((group) => group.run_trial_number), [31, 32, 33]);
  assert.deepEqual(page.groups.map((group) => group.artifacts.length), [8, 8, 8]);
  assert.deepEqual(page.groups.map((group) => group.artifacts.filter((row) => row.matching_artifact).length), [1, 1, 1]);

  const countSql = calls[0].sql;
  const expansionSql = calls[1].sql;
  assert.match(countSql, /matching_artifacts[\s\S]+matching_groups/);
  assert.match(countSql, /count\(distinct artifact_id\)/);
  assert.match(expansionSql, /paged_groups[\s\S]+join artifact_context ac on ac\.group_key = pg\.group_key/);
  assert.match(expansionSql, /partition by t\.run_id, t\.task_id/);
  assert.match(expansionSql, /where task_id is not null/);
  assert.match(expansionSql, /select distinct on \(trial_id\)/);
  assert.match(expansionSql, /t\.id is not null and t\.arm_run_id is null/);
});

test("filter option query returns bounded distinct sets and does not attach run-root arm context", async () => {
  let captured = "";
  globalThis.__dashboardQueryHandler = async (sql) => {
    captured = sql;
    return [{
      run_labels: ["run"], suite_ids: ["suite"], arm_ids: ["arm"], task_ids: ["task"],
      quality_flags: ["normal_failed_trial"], exception_types: [], artifact_types: ["result"]
    }];
  };
  const options = await dashboardData.getArtifactBrowserFilterOptions();
  assert.deepEqual(options.artifact_types, ["result"]);
  assert.match(captured, /limit 500/);
  assert.match(captured, /t\.id is not null and t\.arm_run_id is null/);
  assert.match(captured, /select distinct on \(trial_id\)/);
});

test("live analysis cache key changes with database cost and exception summary", () => {
  const base = {
    trial_id: "trial", reward: 0, exception_type: null, exception_summary: "generic failure",
    input_tokens: 1, cache_tokens: 2, output_tokens: 3, cost_usd: 0.1
  };
  const artifacts = [{ artifact_id: "artifact", sha256: "abc", size_bytes: 10, r2_uri: "r2://bucket/key" }];
  const original = trialAnalysis.liveAnalysisKey(base, artifacts);
  assert.notEqual(trialAnalysis.liveAnalysisKey({ ...base, exception_summary: "timeout" }, artifacts), original);
  assert.notEqual(trialAnalysis.liveAnalysisKey({ ...base, cost_usd: 0.2 }, artifacts), original);
});

test("snapshot/live comparison reports only changed diagnosis axes", () => {
  const snapshot = {
    raw_outcome: "failure", execution_validity: "substantive",
    activity_subtype: "substantive_agent_activity", policy_disposition: "none_detected",
    failure_subtype: "test_assertion_failure", termination_subtype: "none",
    telemetry_status: "consistent", unrelated: "snapshot"
  };
  const live = { ...snapshot, activity_subtype: "activity_unknown", telemetry_status: "partial", unrelated: "live" };
  assert.deepEqual(trialAnalysis.changedAnalysisAxes(snapshot, live), ["activity_subtype", "telemetry_status"]);
  assert.deepEqual(trialAnalysis.changedAnalysisAxes(snapshot, { ...snapshot }), []);
});

test("reviewed Overview loaders resolve only supplied exact run labels", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    return [];
  };
  const labels = [
    "router-anthropic-haiku-sanitized/2026-07-12__03-25-22",
    "router-kimi-k3/2026-07-22__17-51-05",
  ];

  await dashboardData.getReviewedSelectedArmRunRows(labels);
  await dashboardData.getReviewedSelectedRunAdjustedCostRows(labels);

  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0].params, [labels]);
  assert.match(calls[0].sql, /from benchmark\.v_valid_arm_run_summary/);
  assert.match(calls[0].sql, /where run_label = any\(\$1::text\[\]\)/);
  assert.doesNotMatch(calls[0].sql, /limit|row_number|started_at desc/i);
  assert.match(calls[1].sql, /from benchmark\.v_trial_adjusted_cost_coverage/);
  assert.match(calls[1].sql, /where run_label = any\(\$1::text\[\]\)/);
  assert.match(calls[1].sql, /group by run_label, arm_id, suite_id/);
});

test("reviewed Overview loaders reject repeated requested run labels", async () => {
  const labels = ["arm/run", "arm/run"];
  await assert.rejects(
    dashboardData.getReviewedSelectedArmRunRows(labels),
    /must be unique/,
  );
  await assert.rejects(
    dashboardData.getReviewedSelectedRunAdjustedCostRows(labels),
    /must be unique/,
  );
});
