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

test("Overview freshness loaders use execution completion rather than row metadata", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    if (params.length) {
      return [{ latest_included_execution_at: "2026-08-10T00:00:00Z" }];
    }
    return [{
      run_count: 1,
      trial_count: 60,
      artifact_count: 1,
      cost_usd: 1,
      cost_row_count: 60,
      missing_cost_count: 0,
      completed_runs: 1,
      noncompleted_runs: 0,
      latest_included_execution_at: "2026-08-09T00:00:00Z",
    }];
  };

  const overview = await dashboardData.getOverview();
  const suiteLatest = await dashboardData.getValidSuiteLatestIncludedExecutionAt("phase3-full-20");

  assert.equal(overview.latest_included_execution_at, "2026-08-09T00:00:00Z");
  assert.equal(suiteLatest, "2026-08-10T00:00:00Z");
  assert.match(calls[0].sql, /max\(runs\.finished_at\)::text as latest_included_execution_at/);
  assert.doesNotMatch(calls[0].sql, /max\(runs\.(created_at|updated_at)\)/);
  assert.match(calls[1].sql, /max\(finished_at\)::text as latest_included_execution_at/);
  assert.match(calls[1].sql, /from benchmark\.v_valid_arm_run_summary/);
  assert.deepEqual(calls[1].params, ["phase3-full-20"]);
  assert.doesNotMatch(calls[1].sql, /created_at|updated_at/);
});

test("index-route freshness loaders preserve their population filters and use finished_at", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    if (sql.includes("jsonb_to_recordset")) {
      return [{
        suite_id: "phase3-full-20",
        arm_id: "arm",
        run_label: "arm/run",
        match_count: 1,
        finished_at: "2026-08-10T00:00:00Z",
      }];
    }
    return [{ latest_included_execution_at: "2026-08-10T00:00:00Z" }];
  };

  await dashboardData.getAllImportedArmLatestIncludedExecutionAt();
  await dashboardData.getAllImportedTaskLatestIncludedExecutionAt();
  await dashboardData.getArtifactBrowserLatestIncludedExecutionAt({
    run_label: "arm/run",
    artifact_type: "result",
  });
  await dashboardData.getPhase3EvalSuiteLatestIncludedExecutionAt();
  await dashboardData.getValidImportedEvalLatestIncludedExecutionAt();
  await dashboardData.getDisplayedArmRunFreshnessResolution([{
    suite_id: "phase3-full-20",
    arm_id: "arm",
    run_label: "arm/run",
  }]);

  assert.equal(calls.length, 6);
  for (const { sql } of calls.slice(0, 5)) {
    assert.match(sql, /max\([^)]*finished_at\)::text as latest_included_execution_at/);
    assert.doesNotMatch(sql, /max\([^)]*(created_at|updated_at)[^)]*\)/);
  }
  assert.match(calls[5].sql, /max\(summary\.finished_at\)::text/);
  assert.doesNotMatch(calls[5].sql, /created_at|updated_at|invalidated_at|uploaded_at/);

  assert.match(calls[0].sql, /join benchmark\.benchmark_arms a/);
  assert.match(calls[0].sql, /join benchmark\.benchmark_trials t|from benchmark\.benchmark_trials t/);
  assert.match(calls[0].sql, /join benchmark\.benchmark_runs r/);

  assert.match(calls[1].sql, /join benchmark\.benchmark_tasks task/);
  assert.match(calls[1].sql, /from benchmark\.benchmark_trials t/);

  assert.match(calls[2].sql, /from matching_artifacts/);
  assert.match(calls[2].sql, /run_label = \$1/);
  assert.match(calls[2].sql, /artifact_type = \$2/);
  assert.deepEqual(calls[2].params, ["arm/run", "result"]);

  assert.match(calls[3].sql, /from benchmark\.v_valid_arm_run_summary arm_run/);
  assert.match(calls[3].sql, /join benchmark\.benchmark_eval_suites suite/);
  assert.match(calls[3].sql, /where suite\.phase = 'phase3'/);

  assert.match(calls[4].sql, /from benchmark\.v_valid_arm_run_summary/);
  assert.match(calls[4].sql, /where trial_count > 0/);

  assert.match(calls[5].sql, /from benchmark\.v_arm_run_summary summary/);
  assert.match(calls[5].sql, /summary\.phase = 'phase3'/);
  assert.match(calls[5].sql, /summary\.suite_id is not distinct from requested\.suite_id/);
  assert.match(calls[5].sql, /summary\.arm_id = requested\.arm_id/);
  assert.match(calls[5].sql, /summary\.run_label = requested\.run_label/);
  assert.doesNotMatch(calls[5].sql, /from benchmark\.benchmark_runs/);
  assert.deepEqual(JSON.parse(calls[5].params[0]), [{
    suite_id: "phase3-full-20",
    arm_id: "arm",
    run_label: "arm/run",
  }]);
});

test("trial-quality freshness resolves exact Phase 3 identities without same-label substitution", async () => {
  let captured;
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    captured = { sql, params };
    return [{
      suite_id: "phase3-full-20",
      arm_id: "target-arm",
      run_label: "shared/run-label",
      match_count: 1,
      finished_at: "2026-08-09T00:00:00Z",
    }];
  };

  const result = await dashboardData.getDisplayedArmRunFreshnessResolution([{
    suite_id: "phase3-full-20",
    arm_id: "target-arm",
    run_label: "shared/run-label",
  }]);

  assert.equal(result.latestIncludedExecutionAt, "2026-08-09T00:00:00Z");
  assert.equal(result.resolvedIdentityCount, 1);
  assert.match(captured.sql, /summary\.phase = 'phase3'/);
  assert.match(captured.sql, /summary\.suite_id is not distinct from requested\.suite_id/);
  assert.match(captured.sql, /summary\.arm_id = requested\.arm_id/);
  assert.match(captured.sql, /summary\.run_label = requested\.run_label/);
  assert.doesNotMatch(captured.sql, /where summary\.run_label = requested\.run_label\s*$/m);
});

test("unresolved, duplicate, and timestamp-free displayed identities stay explicit", async () => {
  const identities = [
    { suite_id: "phase3-full-20", arm_id: "resolved", run_label: "resolved/run" },
    { suite_id: "phase3-full-20", arm_id: "missing", run_label: "missing/run" },
    { suite_id: "phase3-full-20", arm_id: "duplicate", run_label: "duplicate/run" },
    { suite_id: "phase3-full-20", arm_id: "unfinished", run_label: "unfinished/run" },
  ];
  globalThis.__dashboardQueryHandler = async () => [
    { ...identities[0], match_count: 1, finished_at: "2026-08-09T00:00:00Z" },
    { ...identities[1], match_count: 0, finished_at: null },
    { ...identities[2], match_count: 2, finished_at: null },
    { ...identities[3], match_count: 1, finished_at: null },
  ];

  const result = await dashboardData.getDisplayedArmRunFreshnessResolution(identities);
  assert.equal(result.latestIncludedExecutionAt, "2026-08-09T00:00:00Z");
  assert.equal(result.expectedIdentityCount, 4);
  assert.equal(result.resolvedIdentityCount, 2);
  assert.deepEqual(result.unresolvedIdentities, [identities[1]]);
  assert.deepEqual(result.duplicateIdentities, [identities[2]]);
  assert.deepEqual(result.missingFinishedAtIdentities, [identities[3]]);
});

test("duplicate requested arm-run identities are deterministically de-duplicated", async () => {
  const identity = { suite_id: "phase3-full-20", arm_id: "arm", run_label: "arm/run" };
  let requested;
  globalThis.__dashboardQueryHandler = async (_sql, params) => {
    requested = JSON.parse(params[0]);
    return [{ ...identity, match_count: 1, finished_at: "2026-08-09T00:00:00Z" }];
  };

  const result = await dashboardData.getDisplayedArmRunFreshnessResolution([identity, identity]);
  assert.deepEqual(requested, [identity]);
  assert.equal(result.expectedIdentityCount, 1);
  assert.equal(result.resolvedIdentityCount, 1);
});

test("run detail resolution fails closed when a Phase 3 label is ambiguous", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    return [
      { run_id: "run-full", phase: "phase3", mode: "full", run_label: "shared/run" },
      { run_id: "run-smoke", phase: "phase3", mode: "smoke", run_label: "shared/run" },
    ];
  };

  const ambiguous = await dashboardData.getRunDetailResolution("shared/run");
  assert.equal(ambiguous.status, "ambiguous");
  assert.equal(ambiguous.matches.length, 2);
  assert.match(calls[0].sql, /where phase = 'phase3'/);
  assert.match(calls[0].sql, /run_label = \$1/);
  assert.doesNotMatch(calls[0].sql, /limit 1|order by .*finished_at/i);
  assert.deepEqual(calls[0].params, ["shared/run"]);

  globalThis.__dashboardQueryHandler = async () => [];
  assert.equal((await dashboardData.getRunDetailResolution("missing/run")).status, "not_found");
  globalThis.__dashboardQueryHandler = async () => [
    { run_id: "one", phase: "phase3", mode: "full", run_label: "one/run" },
  ];
  assert.equal((await dashboardData.getRunDetailResolution("one/run")).status, "found");
});

test("artifact and trial detail metadata expose exact parent execution completion", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    return [];
  };

  await dashboardData.getArtifactDetail("00000000-0000-4000-8000-000000000001");
  await dashboardData.getTrialEvidence("00000000-0000-4000-8000-000000000002");

  assert.match(calls[0].sql, /r\.finished_at::text as run_finished_at/);
  assert.match(calls[0].sql, /where art\.id = \$1::uuid/);
  assert.match(calls[1].sql, /r\.finished_at::text as run_finished_at/);
  assert.match(calls[1].sql, /where t\.id = \$1::uuid/);
  for (const call of calls) {
    assert.doesNotMatch(call.sql, /(created_at|updated_at|uploaded_at|invalidated_at)::text as run_finished_at/);
  }
});

test("eval detail execution metadata is restricted to the exact displayed task population", async () => {
  let captured;
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    captured = { sql, params };
    return [{ latest_included_execution_at: "2026-08-09T00:00:00Z" }];
  };

  const latest = await dashboardData.getValidEvalTaskLatestIncludedExecutionAt("terminal-bench-2.0:task");
  assert.equal(latest, "2026-08-09T00:00:00Z");
  assert.match(captured.sql, /max\(arm_run\.finished_at\)::text/);
  assert.match(captured.sql, /from benchmark\.v_valid_arm_run_summary arm_run/);
  assert.match(captured.sql, /join benchmark\.benchmark_trials trial/);
  assert.match(captured.sql, /trial\.task_id = \$1/);
  assert.deepEqual(captured.params, ["terminal-bench-2.0:task"]);
  assert.doesNotMatch(captured.sql, /created_at|updated_at|uploaded_at|invalidated_at/);
});

test("scope-aware eval loaders preserve distinct valid and all-imported populations", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    return [];
  };

  await dashboardData.getEvalRows();
  await dashboardData.getAllImportedEvalRows();
  await dashboardData.getEvalArmComparison("terminal-bench-2.0:task");
  await dashboardData.getAllImportedEvalArmComparison("terminal-bench-2.0:task");

  assert.match(calls[0].sql, /from benchmark\.v_valid_eval_arm_comparison/);
  assert.match(calls[0].sql, /sum\(cost_row_count\)/);
  assert.match(calls[0].sql, /sum\(missing_cost_count\)/);
  assert.doesNotMatch(calls[0].sql, /v_dashboard_tasks/);

  assert.match(calls[1].sql, /from benchmark\.v_dashboard_tasks task/);
  assert.match(calls[1].sql, /from benchmark\.benchmark_trials/);
  assert.match(calls[1].sql, /count\(distinct arm_id\)/);
  assert.doesNotMatch(calls[1].sql, /v_valid_eval_arm_comparison|v_valid_arm_run_summary/);

  assert.match(calls[2].sql, /from benchmark\.v_valid_eval_arm_comparison/);
  assert.match(calls[2].sql, /'valid'::text as validity_status/);
  assert.deepEqual(calls[2].params, ["terminal-bench-2.0:task"]);

  assert.match(calls[3].sql, /from benchmark\.benchmark_trials trial/);
  assert.match(calls[3].sql, /left join benchmark\.benchmark_runs run/);
  assert.match(calls[3].sql, /left join lateral \(/);
  assert.match(calls[3].sql, /select true as is_invalid/);
  assert.match(calls[3].sql, /from benchmark\.benchmark_invalid_arm_runs invalid_record/);
  assert.match(calls[3].sql, /invalid_record\.run_label = run\.run_label/);
  assert.match(calls[3].sql, /limit 1\s+\) invalid_lookup on true/);
  assert.match(calls[3].sql, /invalid_lookup\.is_invalid is true/);
  assert.doesNotMatch(calls[3].sql, /left join benchmark\.benchmark_invalid_arm_runs/);
  assert.match(calls[3].sql, /invalid_or_quarantined/);
  assert.match(calls[3].sql, /trial\.arm_run_id is null then 'unlinked'/);
  assert.doesNotMatch(calls[3].sql, /v_valid_eval_arm_comparison|v_valid_arm_run_summary/);
  assert.deepEqual(calls[3].params, ["terminal-bench-2.0:task"]);
});

test("all-imported eval detail freshness uses the exact unfiltered task population", async () => {
  let captured;
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    captured = { sql, params };
    return [{ latest_included_execution_at: "2026-08-09T00:00:00Z" }];
  };

  const latest = await dashboardData.getAllImportedEvalTaskLatestIncludedExecutionAt(
    "terminal-bench-2.0:task",
  );
  assert.equal(latest, "2026-08-09T00:00:00Z");
  assert.match(captured.sql, /max\(run\.finished_at\)::text/);
  assert.match(captured.sql, /from benchmark\.benchmark_trials trial/);
  assert.match(captured.sql, /join benchmark\.benchmark_runs run/);
  assert.match(captured.sql, /trial\.task_id = \$1/);
  assert.doesNotMatch(captured.sql, /v_valid_|benchmark_invalid_arm_runs/);
  assert.deepEqual(captured.params, ["terminal-bench-2.0:task"]);
});


test("Planner promotion loader reads only current fail-closed gate rows", async () => {
  const expected = [{
    gate_id: "gate-1",
    arm_id: "router-gpt-5.5",
    source_arm_run_id: "arm-run-1",
    usage_reconciliation_id: "usage-1",
    cost_reconciliation_id: "cost-1",
    source_mode: "canary",
    target_mode: "smoke",
    decision: "pass",
    blocker_codes: [],
    derived_blocker_codes: [],
    waiver_reason: null,
    effective_can_advance: true,
    reviewed_by: "reviewer",
    reviewed_at: "2026-08-30T12:00:00Z",
    usage_validation_status: "validated_exact",
    cost_validation_status: "validated_exact",
    selected_usage_authority: "provider_request_usage",
    selected_cost_basis: "provider_billed",
    selected_cost_relation: "exact",
    selected_cost_usd: "1.25",
    usage_limitation_codes: [],
    cost_limitation_codes: [],
  }];

  let captured = "";
  globalThis.__dashboardQueryHandler = async (sql) => {
    captured = sql;
    return expected;
  };

  const rows = await dashboardData.getCurrentEvidencePromotionGates();

  assert.deepEqual(rows, expected);
  assert.match(
    captured,
    /from benchmark\.v_evidence_promotion_gate gate/,
  );
  assert.match(
    captured,
    /join benchmark\.benchmark_evidence_promotion_gates stored/,
  );
  assert.match(captured, /where stored\.is_current/);
  assert.match(
    captured,
    /order by gate\.arm_id, gate\.target_mode/,
  );
  assert.match(captured, /gate\.effective_can_advance/);
  assert.match(captured, /gate\.derived_blocker_codes/);
  assert.match(captured, /gate\.usage_reconciliation_id::text/);
  assert.match(captured, /gate\.cost_reconciliation_id::text/);
  assert.match(captured, /gate\.selected_cost_usd::text/);
});


test("arm loader retains first-class agent harness identity", async () => {
  let captured = "";
  globalThis.__dashboardQueryHandler = async (sql) => {
    captured = sql;
    return [{
      arm_id: "arm",
      provider_family: "provider",
      backend_model: "model",
      router_model: null,
      agent_harness: "claude-code",
      run_count: 1,
      trial_count: 1,
      success_count: 1,
      pass_rate: 1,
      trial_cost_usd: 1,
      cost_row_count: 1,
      missing_cost_count: 0,
      median_runtime_seconds: 1,
    }];
  };

  const rows = await dashboardData.getArmRows();

  assert.equal(rows[0].agent_harness, "claude-code");
  assert.match(captured, /agent_harness/);
  assert.match(captured, /from benchmark\.v_dashboard_arms/);
});

test("provider evidence browser pages source records with normalized and reconciliation context", async () => {
  const calls = [];
  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });

    if (sql.includes("total_source_count")) {
      return [{ total_source_count: 11 }];
    }

    return [{
      source_id: "11111111-1111-1111-1111-111111111111",
      provider: "openai",
      arm_run_id: null,
      artifact_id: null,
      evidence_kind: "usage_export",
      source_scope: "provider_window",
      source_uri: null,
      provider_reference: "usage.csv",
      source_sha256: "a".repeat(64),
      size_bytes: null,
      source_format: "csv",
      provider_window_started_at: null,
      provider_window_finished_at: null,
      captured_at: "2026-08-21T00:00:00Z",
      integrity_status: "sha256_verified",
      notes: "normalized source",
      phases: ["phase3"],
      suite_ids: ["phase3-full-20"],
      arm_ids: ["router-gpt-5.4"],
      run_labels: ["router-gpt-5.4/run"],
      usage_row_count: 1,
      cost_row_count: 0,
      pricing_snapshot_count: 0,
      usage_reconciliation_count: 1,
      cost_reconciliation_count: 0,
    }];
  };

  const page = await dashboardData.getProviderEvidenceBrowserPage({
    provider: "openai",
    arm_id: "router-gpt-5.4",
    page: 2,
    page_size: 10,
  });

  assert.equal(page.page, 2);
  assert.equal(page.total_source_count, 11);
  assert.equal(page.total_pages, 2);
  assert.equal(page.sources.length, 1);
  assert.deepEqual(page.sources[0].phases, ["phase3"]);
  assert.deepEqual(page.sources[0].arm_ids, ["router-gpt-5.4"]);

  assert.equal(calls.length, 2);
  assert.match(
    calls[0].sql,
    /from benchmark\.benchmark_provider_evidence_sources source/,
  );
  assert.match(
    calls[0].sql,
    /benchmark_provider_usage_evidence/,
  );
  assert.match(
    calls[0].sql,
    /benchmark_provider_cost_evidence/,
  );
  assert.match(
    calls[0].sql,
    /benchmark_usage_reconciliation_sources/,
  );
  assert.match(
    calls[0].sql,
    /benchmark_cost_reconciliation_sources/,
  );
  assert.match(
    calls[0].sql,
    /\$2 = any\(arm_ids\)/,
  );
  assert.deepEqual(calls[0].params, [
    "openai",
    "router-gpt-5.4",
  ]);
  assert.deepEqual(calls[1].params, [
    "openai",
    "router-gpt-5.4",
    10,
    10,
  ]);

  for (const call of calls) {
    assert.doesNotMatch(call.sql, /raw_metadata/);
  }
});

test("provider evidence source detail loads normalized usage cost pricing and independent reconciliations", async () => {
  const calls = [];

  globalThis.__dashboardQueryHandler = async (sql, params) => {
    calls.push({ sql, params });

    if (
      sql.includes("from provider_source_context")
      && sql.includes("where source_id = $1")
    ) {
      return [{
        source_id: "11111111-1111-1111-1111-111111111111",
        provider: "openai",
        arm_run_id: null,
        artifact_id: null,
        evidence_kind: "usage_export",
        source_scope: "provider_window",
        source_uri: null,
        provider_reference: "usage.csv",
        source_sha256: "a".repeat(64),
        size_bytes: null,
        source_format: "csv",
        provider_window_started_at: null,
        provider_window_finished_at: null,
        captured_at: "2026-08-21T00:00:00Z",
        integrity_status: "sha256_verified",
        notes: "normalized source",
        phases: ["phase3"],
        suite_ids: ["phase3-full-20"],
        arm_ids: ["router-gpt-5.4"],
        run_labels: ["router-gpt-5.4/run"],
        usage_row_count: 1,
        cost_row_count: 1,
        pricing_snapshot_count: 1,
        usage_reconciliation_count: 1,
        cost_reconciliation_count: 1,
      }];
    }

    if (
      sql.includes(
        "from benchmark.benchmark_provider_usage_evidence usage_evidence",
      )
    ) {
      return [{
        evidence_id: "usage-id",
        arm_run_id: "arm-run-id",
        arm_id: "router-gpt-5.4",
        suite_id: "phase3-full-20",
        logical_mode: "full",
        run_label: "router-gpt-5.4/run",
        trial_id: null,
        provider_request_id: null,
        provider_model: "gpt-5.4-2026-03-05",
        request_started_at: null,
        request_finished_at: null,
        ordinary_input_tokens: "10",
        cache_read_input_tokens: "20",
        cache_creation_input_tokens: null,
        output_tokens: "3",
        request_count: 4,
        allocation_scope: "exact_arm_run",
        completeness_status: "complete",
        notes: null,
        created_at: "2026-08-21T00:00:00Z",
      }];
    }

    if (
      sql.includes(
        "from benchmark.benchmark_provider_cost_evidence cost_evidence",
      )
    ) {
      return [{
        evidence_id: "cost-id",
        arm_run_id: "arm-run-id",
        arm_id: "router-gpt-5.4",
        suite_id: "phase3-full-20",
        logical_mode: "full",
        run_label: "router-gpt-5.4/run",
        trial_id: null,
        pricing_snapshot_id: null,
        provider_model: "gpt-5.4-2026-03-05",
        cost_kind: "provider_arm_run_billed",
        amount_usd: "29.7919335",
        currency: "USD",
        allocation_scope: "exact_arm_run",
        completeness_status: "complete",
        notes: null,
        created_at: "2026-08-21T00:00:00Z",
      }];
    }

    if (
      sql.includes(
        "from benchmark.benchmark_provider_pricing_snapshots pricing",
      )
    ) {
      return [{
        pricing_snapshot_id: "pricing-id",
        provider: "openai",
        provider_model: "gpt-5.4-2026-03-05",
        currency: "USD",
        effective_from: null,
        effective_until: null,
        pricing_semantics: "provider_billed",
        pricing_rules: { input: "1.25" },
        official_source_uri: "https://example.test/pricing",
        notes: null,
        created_at: "2026-08-21T00:00:00Z",
      }];
    }

    if (
      sql.includes(
        "from benchmark.benchmark_usage_reconciliation_sources source_link",
      )
    ) {
      return [{
        reconciliation_id: "usage-reconciliation-id",
        evidence_role: "aggregate_usage",
        arm_run_id: "arm-run-id",
        arm_id: "router-gpt-5.4",
        suite_id: "phase3-full-20",
        logical_mode: "full",
        run_label: "router-gpt-5.4/run",
        reconciliation_version: "v1",
        is_current: true,
        harness_name: "claude-code",
        harness_version: null,
        configured_route_model: null,
        configured_backend_model: "gpt-5.4",
        harness_observed_model: "gpt-5.4",
        provider_observed_model: "gpt-5.4-2026-03-05",
        model_identity_status: "matched",
        harness_input_tokens: "30",
        harness_cache_tokens: "20",
        harness_output_tokens: "3",
        provider_ordinary_input_tokens: "10",
        provider_cache_read_input_tokens: "20",
        provider_cache_creation_input_tokens: null,
        provider_output_tokens: "3",
        provider_request_count: 4,
        matched_provider_request_count: null,
        unallocated_provider_request_count: null,
        provider_evidence_visible: true,
        selected_usage_authority: "provider_aggregate_usage",
        validation_status: "validated_exact",
        limitation_codes: [],
        notes: null,
        created_at: "2026-08-21T00:00:00Z",
        reviewed_at: "2026-08-21T00:00:00Z",
        evidence_sources: [{
          source_id: "11111111-1111-1111-1111-111111111111",
          provider: "openai",
          evidence_kind: "usage_export",
          source_scope: "provider_window",
          evidence_role: "aggregate_usage",
        }],
      }];
    }

    if (
      sql.includes(
        "from benchmark.benchmark_cost_reconciliation_sources source_link",
      )
    ) {
      return [{
        reconciliation_id: "cost-reconciliation-id",
        evidence_role: "billed",
        arm_run_id: "arm-run-id",
        arm_id: "router-gpt-5.4",
        suite_id: "phase3-full-20",
        logical_mode: "full",
        run_label: "router-gpt-5.4/run",
        reconciliation_version: "v1",
        is_current: true,
        harness_name: "claude-code",
        harness_version: null,
        harness_reported_cost_usd: "173.09483",
        provider_billed_cost_usd: "29.7919335",
        provider_rate_reconstructed_cost_usd: null,
        selected_cost_usd: "29.7919335",
        selected_cost_basis: "provider_billed",
        selected_cost_relation: "exact",
        validation_status: "validated_exact",
        provider_evidence_visible: true,
        pricing_snapshot_id: "pricing-id",
        pricing_source_id:
          "22222222-2222-2222-2222-222222222222",
        pricing_source_provider: "openai",
        pricing_source_evidence_kind: "pricing_snapshot",
        pricing_source_scope: "pricing_snapshot",
        limitation_codes: [],
        notes: null,
        created_at: "2026-08-21T00:00:00Z",
        reviewed_at: "2026-08-21T00:00:00Z",
        evidence_sources: [{
          source_id: "11111111-1111-1111-1111-111111111111",
          provider: "openai",
          evidence_kind: "billing_export",
          source_scope: "provider_window",
          evidence_role: "billed",
        }, {
          source_id: "22222222-2222-2222-2222-222222222222",
          provider: "openai",
          evidence_kind: "pricing_snapshot",
          source_scope: "pricing_snapshot",
          evidence_role: "pricing",
        }],
      }];
    }

    throw new Error(`unexpected provider evidence query: ${sql}`);
  };

  const detail =
    await dashboardData.getProviderEvidenceSourceDetail(
      "11111111-1111-1111-1111-111111111111",
    );

  assert.ok(detail);
  assert.equal(detail.usage_rows.length, 1);
  assert.equal(detail.cost_rows.length, 1);
  assert.equal(detail.pricing_snapshots.length, 1);
  assert.equal(detail.usage_reconciliations.length, 1);
  assert.equal(detail.cost_reconciliations.length, 1);
  assert.equal(
    detail.cost_reconciliations[0].selected_cost_relation,
    "exact",
  );

  assert.equal(calls.length, 6);

  assert.match(
    calls[4].sql,
    /jsonb_agg/,
  );
  assert.match(
    calls[4].sql,
    /benchmark_usage_reconciliation_sources all_link/,
  );

  assert.match(
    calls[5].sql,
    /benchmark_provider_pricing_snapshots pricing/,
  );
  assert.match(
    calls[5].sql,
    /pricing_source_id/,
  );
  assert.match(
    calls[5].sql,
    /benchmark_cost_reconciliation_sources all_link/,
  );
  assert.match(
    calls[5].sql,
    /jsonb_agg/,
  );

  for (const call of calls) {
    assert.doesNotMatch(call.sql, /raw_metadata/);
  }
});

test("Provider Evidence routes are first-class navigation and privacy-safe normalized evidence surfaces", async () => {
  const [indexPage, detailPage, appShell] = await Promise.all([
    readFile(
      join(
        here,
        "../app/provider-evidence/page.tsx",
      ),
      "utf8",
    ),
    readFile(
      join(
        here,
        "../app/provider-evidence/[sourceId]/page.tsx",
      ),
      "utf8",
    ),
    readFile(
      join(
        here,
        "../components/AppShell.tsx",
      ),
      "utf8",
    ),
  ]);

  assert.match(
    appShell,
    /\{ href: "\/provider-evidence", label: "Provider Evidence" \}/,
  );
  assert.match(
    indexPage,
    /getProviderEvidenceBrowserPage/,
  );
  assert.match(
    indexPage,
    /getProviderEvidenceBrowserFilterOptions/,
  );
  assert.match(
    detailPage,
    /getProviderEvidenceSourceDetail/,
  );
  assert.match(
    detailPage,
    /formatTruncatedCurrency/,
  );
  assert.match(
    detailPage,
    /sanitizeEvidenceOutput/,
  );
  assert.match(
    detailPage,
    /truncateStructuredDecimalsForDisplay/,
  );
  assert.match(
    detailPage,
    /formatTruncatedNumber/,
  );
  assert.match(
    detailPage,
    /displayedCostAmount/,
  );
  assert.match(
    detailPage,
    /EvidenceSourceChain/,
  );
  assert.match(
    detailPage,
    /pricing snapshot:/,
  );
  assert.match(
    detailPage,
    /pricing source:/,
  );
  assert.match(
    detailPage,
    /row\.pricing_source_id/,
  );
  assert.doesNotMatch(
    detailPage,
    /safeText\(row\.amount_usd\)/,
  );
  assert.match(
    indexPage,
    /Private raw provider payload metadata is not rendered/,
  );
  assert.doesNotMatch(indexPage, /raw_metadata/);
  assert.doesNotMatch(detailPage, /raw_metadata/);
});
