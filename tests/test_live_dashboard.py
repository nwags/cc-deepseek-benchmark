from pathlib import Path


def test_local_fallback_remains_terminal_after_post_finish_warning() -> None:
    source = Path("apps/dashboard/src/lib/live-local-fallback.ts").read_text()
    assert 'record.event_type === "run_finished"' in source
    assert "const active = !finished;" in source


def test_stale_orphan_alone_does_not_trigger_continuous_refresh() -> None:
    source = Path("apps/dashboard/src/app/runs/live/page.tsx").read_text()
    assert "active.some((run) => !run.is_stale)" in source


def test_live_dashboard_separates_output_and_preserves_warnings() -> None:
    page = Path("apps/dashboard/src/app/runs/live/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/live-data.ts").read_text()

    assert "getLiveOutputEvents" in page
    assert "getLiveRunWarnings" in page
    assert "Warnings and diagnostic signals" in page
    assert "Observable output history" in page
    assert ".slice(-20)" not in page
    assert "LIVE_EVENT_LIMIT = 200" in data
    assert "LIVE_OUTPUT_EVENT_LIMIT = 300" in data
    assert "LIVE_WARNING_EVENT_LIMIT = 100" in data
    assert "event_type in ('publication_warning', 'runtime_warning')" in data
    event_query = data.split(
        "export async function getLiveRunEvents", 1
    )[1].split(
        "export async function getLiveOutputEvents", 1
    )[0]
    assert "event_type not in (" in event_query
    for event_type in (
        "process_output_chunk",
        "agent_output_chunk",
        "tool_call_started",
        "tool_result",
        "tool_call_finished",
    ):
        assert f"'{event_type}'" in event_query


def test_live_dashboard_exposes_artifact_content_and_tool_lifecycle() -> None:
    page = Path("apps/dashboard/src/app/runs/live/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/live-data.ts").read_text()
    artifact_content = Path("apps/dashboard/src/lib/artifact-content.ts").read_text()
    artifact_page = Path(
        "apps/dashboard/src/app/live-artifacts/[artifactId]/page.tsx"
    ).read_text()
    download_route = Path(
        "apps/dashboard/src/app/live-artifacts/[artifactId]/download/route.ts"
    ).read_text()
    supervision = Path("scripts/lib/live_supervision.py").read_text()

    assert "getLiveToolEvents" in page
    assert "Tool activity" in page
    assert "Thinking and reasoning content is not parsed or displayed" in page
    assert "/live-artifacts/" in page
    assert "LIVE_TOOL_EVENT_LIMIT = 300" in data
    assert "'tool_call_started', 'tool_result', 'tool_call_finished'" in data
    assert "id::text as artifact_id" in data
    assert "fetchArtifactDownload" in artifact_content
    assert "configuredBucket" in artifact_content
    assert "x-amz-meta-sha256" in artifact_content
    assert "x-amz-meta-size_bytes" in artifact_content
    assert "integrityMismatch" in artifact_content
    assert "previewArtifactContent" in artifact_page
    assert "Download immutable R2 object" in artifact_page
    assert "content-disposition" in download_route
    assert "sha256: artifact.sha256" in download_route
    assert "IncrementalToolEventParser" in supervision


def test_artifact_browser_paginates_complete_evidence_groups() -> None:
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    page = Path("apps/dashboard/src/app/artifacts/page.tsx").read_text()

    assert "matching_groups as" in data
    assert "paged_groups as" in data
    assert "join artifact_context ac on ac.group_key = pg.group_key" in data
    assert "matching_artifact_count" in data
    assert "count(distinct artifact_id)" in data
    assert "expanded_artifact_count" in data
    assert "artifact_type = $param" in data
    assert "const page = Math.min(requestedPage, totalPages);" in data
    assert "group.artifacts.map" in page
    assert "Groups per page" in page
    assert "paginationHref(filters" in page
    assert "select distinct on (trial_id)" in data
    assert "t.id is not null and t.arm_run_id is null" in data
    assert "limit 500" in data


def test_artifact_browser_uses_task_local_window_numbering() -> None:
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    page = Path("apps/dashboard/src/app/artifacts/page.tsx").read_text()

    assert "row_number() over (" in data
    assert "partition by t.run_id, t.task_id" in data
    assert "task_attempt_count" in data
    assert "run_task_first_positions" in data
    assert "Task ${group.task_ordinal" in page
    assert "Attempt ${group.task_attempt_number" in page
    assert "Run trial #${group.run_trial_number" in page


def test_artifact_lifecycle_and_completeness_are_separate_from_router_evidence() -> None:
    guide = Path("apps/dashboard/src/components/ArtifactEvidenceGuide.tsx").read_text()
    artifact_types = Path("apps/dashboard/src/lib/artifact-types.ts").read_text()
    page = Path("apps/dashboard/src/app/artifacts/page.tsx").read_text()

    assert "Artifact lifecycle and investigation guide" in guide
    assert "Claude Code ↔ router ↔ provider" in guide
    assert "Complete artifacts likewise do not imply substantive execution" in guide
    assert 'canonicalTrialArtifactTypes' in artifact_types
    assert 'routerArtifactTypes' in artifact_types
    assert 'routerRetentionContract === "not_retained"' in artifact_types
    assert 'artifacts.length > 0 ? "not_retained"' not in artifact_types
    assert "Router observability" in page
    assert "canonical_expected_count" in page


def test_trial_diagnosis_keeps_axes_and_null_telemetry_distinct() -> None:
    page = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    analysis = Path("apps/dashboard/src/lib/trial-analysis-core.ts").read_text()

    for heading in (
        "Raw outcome",
        "Execution validity",
        "Agent activity",
        "Policy disposition",
        "Verifier failure subtype",
        "Termination / exception",
        "Evidence completeness",
        "Database/result consistency",
        "Telemetry",
        "Router observability",
    ):
        assert heading in page
    assert '"not recorded"' in page
    assert "trial.input_tokens ?? 0" not in page
    assert "provider_policy_refusal" in analysis
    assert "policy_blocked" in analysis
    assert "database_missing_transcript_present" in analysis
    assert "database_zero_transcript_nonzero" in analysis
    assert "nonzero_mismatch" in analysis
    assert "empty_completion_after_long_api_path_wait" in analysis
    assert "empty_completion_after_long_provider_wait" not in analysis
    assert "unclassified_exception" in analysis
    assert "database_result_consistency" in analysis
    assert "Database reward (raw source of truth)" in analysis
    assert "validated snapshot" in page
    assert "live_analysis=1" in page
    assert "Snapshot/live difference" in page


def test_trial_analysis_never_renders_thinking_content() -> None:
    page = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    analysis = Path("apps/dashboard/src/lib/trial-analysis-core.ts").read_text()
    content = Path("apps/dashboard/src/lib/artifact-content.ts").read_text()

    assert "Thinking and reasoning content is not parsed or displayed" in page
    assert "isHiddenReasoningNode" in analysis
    assert "redactHiddenReasoningPreview" in content
    assert "[hidden reasoning not displayed]" in content


def test_artifact_reader_is_bounded_type_aware_and_secret_safe() -> None:
    content = Path("apps/dashboard/src/lib/artifact-content.ts").read_text()
    safe_display = Path("apps/dashboard/src/lib/safe-display.ts").read_text()
    detail = Path("apps/dashboard/src/app/artifacts/[artifactId]/page.tsx").read_text()

    assert "DEFAULT_ANALYSIS_BYTES = 8 * 1024 * 1024" in content
    assert "readResponseWithByteLimit" in content
    assert "newlineAlignedHeadTail" in content
    assert '"head_tail_only"' in content
    assert "AbortController" in content
    assert "sanitizeTranscriptRecord" in content
    assert "redactStructuredValue" in content
    assert "ANTHROPIC_AUTH_TOKEN" not in detail
    assert "sanitizeDisplayedUri" in detail
    assert "SECRET_QUERY_PATTERN" in safe_display
    assert "url.username = \"\"" in safe_display
    assert "redactSecretsInText" in detail
    assert "INLINE_CREDENTIAL_PATTERN" in safe_display


def test_behavioral_analyzer_and_query_tests_are_wired_into_make_check() -> None:
    makefile = Path("Makefile").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert "npm run test:trial-analysis" in makefile
    assert "review-output-scan" in makefile
    assert "python3 scripts/scan_comprehensive_review_outputs.py" in makefile
    assert "$(MAKE) review-output-scan" in makefile
    assert "artifact-content.test.mjs" in package
    assert "dashboard-data.test.mjs" in package
    assert "trial-analysis.test.mjs" in package
    assert "review-data.test.mjs" in package


def test_comprehensive_review_is_read_only_and_does_not_replace_rates() -> None:
    generator = Path("scripts/generate_comprehensive_evidence_review.py").read_text()
    page = Path("apps/dashboard/src/app/comprehensive-review/page.tsx").read_text()
    review_data = Path("apps/dashboard/src/lib/review-data.ts").read_text()

    assert "begin transaction read only" in generator
    assert "put_object" not in generator
    assert "insert into" not in generator.lower()
    for output in (
        "run_review.csv", "trial_review.csv", "trial_evidence.jsonl",
        "review_queue.csv", "manual_control_sample.csv",
        "task_disagreement_review.csv", "arm_review_summary.csv",
        "targeted_evidence_packet.csv", "targeted_evidence_bundle.jsonl",
        "targeted_evidence_bundle_manifest.json", "review_coverage.json", "review_manifest.json",
    ):
        assert output in generator
    assert "never changes benchmark rewards" in page
    assert "No aggregate rate or denominator is changed" in page
    assert "MAX_REVIEW_FILE_BYTES" in review_data
    assert "review_queue.csv" in review_data
    assert "mixed_output" in review_data
    assert "scope_fingerprint" in review_data
    assert "cachedReviewIndex" in review_data
    assert "review_manifest.json" in generator
    assert "r2_indexed_completeness" in generator
    assert "analyzed_artifact_integrity_status" in generator
    assert "scope_fingerprint_inputs" in generator
    assert 'DEFAULT_CHECKPOINT = Path(".review-cache/' in generator


def test_comprehensive_review_queue_and_disagreements_are_filterable_and_paginated() -> None:
    page = Path("apps/dashboard/src/app/comprehensive-review/page.tsx").read_text()
    review_data = Path("apps/dashboard/src/lib/review-data.ts").read_text()

    assert 'priority: first(params.priority) || "high"' in page
    assert "Displaying {matchingQueue.length" in page
    assert "Review queue pagination" in page
    assert "disagreement_arm" in page
    assert "disagreement_task" in page
    assert "disagreement_category" in page
    assert "disagreement_outcome" in page
    assert "disagreement_policy" in page
    assert "arm_a_raw_outcome_summary" in page
    assert "enrichDisagreementOutcomes" in review_data
    assert "Displaying {matchingDisagreements.length" in page
    assert "Task disagreement pagination" in page
    assert "MANIFEST_OUTPUT_NAMES" in review_data
    assert "path.isAbsolute(name)" in review_data
    assert "path.basename(name) !== name" in review_data
    assert 'name.includes("..")' in review_data


def test_database_exception_summary_is_sourced_sanitized_and_cache_bound() -> None:
    analysis = Path("apps/dashboard/src/lib/trial-analysis-core.ts").read_text()
    live_analysis = Path("apps/dashboard/src/lib/trial-analysis.ts").read_text()
    generator = Path("scripts/generate_comprehensive_evidence_review.py").read_text()
    trial_page = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()

    assert "databaseExceptionSummary" in analysis
    assert 'databaseEvidence("database_exception_summary")' in analysis
    assert "databaseExceptionSummaryTrustedMarkers" in analysis
    assert "trial.exception_summary" in live_analysis
    assert "trial.cost_usd" in live_analysis
    assert "database_exception_summary_sha256" in generator
    assert 'redact_text(str(trial["exception_summary"]))' in generator
    assert "trial.exception_type || trial.exception_summary" in trial_page


def test_exception_and_live_free_text_use_secret_redaction() -> None:
    safe_display = Path("apps/dashboard/src/lib/safe-display.ts").read_text()
    artifact = Path("apps/dashboard/src/app/artifacts/[artifactId]/page.tsx").read_text()
    trial = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    live = Path("apps/dashboard/src/app/runs/live/page.tsx").read_text()
    validity = Path("apps/dashboard/src/components/ValidityContext.tsx").read_text()

    assert "redactSecretsInText" in safe_display
    for source in (artifact, live):
        assert "redactSecretsInText" in source
    for source in (trial, validity):
        assert "sanitizeEvidenceText" in source
    assert "title={trial.exception_summary ? safeText(trial.exception_summary)" in live


def test_run_trial_rows_use_unique_trial_keys_across_three_task_attempts() -> None:
    page = Path("apps/dashboard/src/app/runs/[runLabel]/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()

    assert "<tr key={trial.trial_id}>" in page
    assert "key={`${trial.task_id}-${trial.arm_id}`}" not in page
    assert "id::text as trial_id" in data
    assert "partition by run_id, task_id" in data
    assert "task_attempt" in data
    attempt_rows = [
        {"trial_id": f"trial-{attempt}", "task_id": "task", "arm_id": "arm", "task_attempt": attempt}
        for attempt in (1, 2, 3)
    ]
    assert len({row["trial_id"] for row in attempt_rows}) == 3


def test_dashboard_corpus_scopes_are_centralized_and_visible() -> None:
    scopes = Path("apps/dashboard/src/lib/corpus-scopes.ts").read_text()
    notice = Path("apps/dashboard/src/components/CorpusScopeNotice.tsx").read_text()
    selector = Path("apps/dashboard/src/components/CorpusScopeSelector.tsx").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    for scope_id in (
        "phase3-core",
        "phase3-extended",
        "valid-imported",
        "all-imported",
    ):
        assert f'"{scope_id}"' in scopes
    assert "presentationKind: CorpusScopePresentationKind" in scopes
    assert "comparedFields" in scopes
    assert 'reason: "dynamic_scope"' in scopes
    assert 'reason: "no_observed_counts"' in scopes
    assert "compareCorpusScopeCounts" in notice
    assert "getCorpusScopePresentationLabel" in notice
    assert "qualifiedAdjustedCostEstimateUsd" in notice
    assert "costDisplayLabel" in notice
    assert 'role="alert"' in notice
    assert "not a full-suite leaderboard denominator" in notice
    assert 'href={`${pathname}?scope=${option.id}`}' in selector
    assert 'aria-current={selected ? "page" : undefined}' in selector
    assert "current reviewed comparison" in selector.lower()
    assert "historical reviewed snapshot" in selector.lower()
    assert "corpus-scopes.test.mjs" in package
    assert "cross-phase-reporting.test.mjs" in package


def test_comparative_pages_disclose_their_distinct_corpus_scopes() -> None:
    overview = Path("apps/dashboard/src/app/page.tsx").read_text()
    cross_phase = Path("apps/dashboard/src/app/cross-phase/page.tsx").read_text()
    arms = Path("apps/dashboard/src/app/arms/page.tsx").read_text()
    evals = Path("apps/dashboard/src/app/evals/page.tsx").read_text()
    cost = Path("apps/dashboard/src/app/cost-coverage/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()

    assert 'scopeId="phase3-extended"' in overview
    assert "Phase 3 extended full-suite comparison" in overview
    assert 'scopeId="valid-imported"' in overview
    assert "Valid imported evidence inventory" in overview

    for page in (cross_phase, cost):
        assert "selectReviewedPhase3Scope" in page
        assert "CorpusScopeSelector" in page
        assert "selection.warningMessage" in page
        assert 'role="alert"' in page
        assert "scopeId={selection.scopeId}" in page
        assert "phase3_extended_reviewed_comparison_20260805.json" in page

    assert "getCrossPhaseRows(selectedScope)" in cross_phase
    assert "getPhaseSummaries(rows, selectedScope)" in cross_phase
    assert "reviewed 2026-08-05 comparison layer" in cross_phase
    assert "retained 15-arm Phase 3 core comparison" in cross_phase
    assert "does not include Kimi K3 or inherit the selected extended denominator" in cross_phase

    assert 'scopeId="all-imported"' in arms
    assert "All imported" in arms
    assert "not a valid full-suite leaderboard denominator" in arms

    assert 'scopeId="valid-imported"' in evals
    assert "Valid imported inventory" in evals
    assert "Invalid and quarantined arm runs are excluded" in evals
    assert "not a fixed full-suite leaderboard denominator" in evals
    assert "from benchmark.v_valid_eval_arm_comparison" in data

    assert "scope.costEvidence" in cost
    assert "scope.outcomeCostCoverage" in cost
    assert "scope.arms" in cost
    assert "getAdjustedCostOverview" not in cost
    assert "getAdjustedCostArmRows" not in cost
    assert "getAdjustedOutcomeCostRows" not in cost
    assert "Phase 3 extended qualified adjusted-cost estimate" in Path(
        "apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts"
    ).read_text()
    assert "Qualified retained-rate reconstruction" in cost
    assert "Pricing-source provenance incomplete" in cost
    assert "arm-run/provider-log allocation confidence low" in cost
    assert "trial-level allocation unresolved" in cost
    assert "not invoice-level or provider-billed spend" in cost
    assert 'return "Unavailable"' in cost
    assert "900-trial Phase 3 core only" in cost
    assert "Kimi K3&apos;s 60 trials are excluded" in cost
    assert "cover all {formatNumber(outcomes.coveredTrialCount)}/{formatNumber(scope.trialCount)} trials" in cost
    assert "not assigned to any outcome bucket" in cost
    assert "sponsor-facing" not in cost
    assert "intentionally does not synthesize an extended adjusted-cost total" not in cost
    assert "getAdjustedCostOverview" in data


def test_overview_uses_frozen_reviewed_runs_and_exact_database_reconciliation() -> None:
    overview = Path("apps/dashboard/src/app/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    reconciliation = Path(
        "apps/dashboard/src/lib/overview-reviewed-comparison.ts"
    ).read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert "PHASE3_REVIEWED_COMPARISON" in overview
    assert "getReviewedPhase3Scope" in overview
    assert "PHASE3_REVIEWED_RUN_SELECTION" in overview
    assert "getReviewedRunSelectionScope" in overview
    assert "getReviewedSelectedRunLabels" in overview
    assert "buildOverviewReviewedComparison" in overview
    assert "getSuiteArmComparison" not in overview
    assert "getValidSuiteArmRunRows" not in overview

    assert "getReviewedSelectedArmRunRows" in overview
    assert "getReviewedSelectedRunAdjustedCostRows" in overview
    assert "from benchmark.v_valid_arm_run_summary" in data
    assert "from benchmark.v_trial_adjusted_cost_coverage" in data
    assert "where run_label = any($1::text[])" in data
    assert "group by run_label, arm_id, suite_id" in data

    assert "The reviewed comparison freezes one complete valid full-suite run per arm" in overview
    assert "do not automatically change when" in overview
    assert "the database does not select a newer run" in overview
    assert "no mutable suite/arm aggregate is used as a fallback" in overview
    assert "href={row.selectedRunHref}" in overview
    assert "encodeURIComponent(runLabel)" in reconciliation
    assert "/runs/router-kimi-k3%2F2026-07-22__17-51-05" in Path(
        "apps/dashboard/src/lib/overview-reviewed-comparison.test.mjs"
    ).read_text()

    assert "16 selected runs" in overview
    assert 'scopeId="valid-imported"' in overview
    assert "Valid imported evidence inventory" in overview
    assert "Qualified retained-rate estimate" in overview
    assert "Adjusted known cost: Unavailable" in overview
    assert "Pricing-source provenance incomplete" in overview
    assert "Provider-log allocation confidence low" in overview
    assert "Provider-log exclusivity not proven" in overview
    assert "Trial allocation unresolved" in overview
    assert "Not invoice-level or provider-billed spend" in overview
    assert "Missing recorded" in overview
    assert "Unresolved adjusted" in overview

    assert "Dynamic valid-imported full-suite heatmap" in overview
    assert "not restricted to the frozen" in overview
    assert "can combine multiple valid imports for an arm" in overview
    assert "overview-reviewed-comparison.test.mjs" in package


def test_overview_has_population_specific_freshness_and_snapshot_provenance() -> None:
    overview = Path("apps/dashboard/src/app/page.tsx").read_text()
    freshness = Path("apps/dashboard/src/lib/data-freshness.ts").read_text()
    sources = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()
    notice = Path("apps/dashboard/src/components/DataFreshnessNotice.tsx").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert "DataFreshnessNotice" in overview
    assert "buildReviewedSnapshotFreshness" in overview
    assert "PHASE3_REVIEWED_COMPARISON" in overview
    assert "PHASE3_REVIEWED_RUN_SELECTION" in overview
    assert "reviewedComparisonFreshness" in overview
    assert "reviewedRunSelectionFreshness" in overview
    assert "selectedRunEvidenceFreshness" in overview
    assert "validImportedFreshness" in overview
    assert "dynamicSuiteFreshness" in overview
    assert "selectedRunRead.value ?? []" in overview
    assert ".map((row) => row.finished_at)" in overview
    assert "getValidSuiteLatestIncludedExecutionAt" in overview
    assert "summarizeExpectedLabelCoverage" in overview
    assert "expectedLabelCoverageWarning" in overview
    assert "selectedRunCoverage" in overview
    assert "selectedCostCoverage" in overview
    assert "selectedQualityCoverage" in overview
    assert 'expectedLabelCoverageWarning("Stored run-summary evidence"' in overview
    assert 'expectedLabelCoverageWarning("Stored adjusted-cost evidence"' in overview
    assert 'expectedLabelCoverageWarning("Stored quality context"' in overview

    for relation in (
        "benchmark.v_valid_arm_run_summary",
        "benchmark.benchmark_trials",
        "benchmark.v_trial_adjusted_cost_coverage",
        "benchmark.v_arm_run_quality_summary",
        "benchmark.v_dashboard_runs",
        "benchmark.v_valid_eval_arm_comparison",
    ):
        assert relation in sources
    assert "PHASE3_REVIEWED_COMPARISON.reviewedAt" in sources
    assert "PHASE3_REVIEWED_RUN_SELECTION.reviewedAt" in sources
    assert "phase3-reviewed-comparison-v1" in Path(
        "apps/dashboard/src/lib/phase3-reviewed-comparison.ts"
    ).read_text()
    assert "phase3-reviewed-run-selection-v1" in Path(
        "apps/dashboard/src/lib/phase3-reviewed-run-selection.ts"
    ).read_text()

    assert "Canonical publication:" in notice
    assert "canonicalPublicationText" in notice
    assert 'return "Not recorded"' in freshness
    assert 'canonicalPublicationStatus: "not_recorded"' not in overview
    assert "latestCanonicalPublishedAt: null" in overview
    assert "Reviewed snapshot, not live inventory" in notice
    assert 'queryStatus === "unavailable"' in notice
    assert "Operational data is unavailable" in notice
    assert "threshold_not_configured" in freshness
    assert "staleAfterSeconds: null" in overview
    assert "90" not in freshness
    assert "90" not in overview

    freshness_section = data[data.index("export async function getOverview") :]
    assert "max(runs.finished_at)::text as latest_included_execution_at" in freshness_section
    assert "max(finished_at)::text as latest_included_execution_at" in freshness_section
    assert "max(runs.created_at)" not in freshness_section
    assert "max(runs.updated_at)" not in freshness_section
    assert "data-freshness.test.mjs" in package


def test_primary_cloud_indexes_use_population_specific_freshness_contracts() -> None:
    page_sources = {
        "arms": Path("apps/dashboard/src/app/arms/page.tsx").read_text(),
        "artifacts": Path("apps/dashboard/src/app/artifacts/page.tsx").read_text(),
        "evalSuites": Path("apps/dashboard/src/app/eval-suites/page.tsx").read_text(),
        "evals": Path("apps/dashboard/src/app/evals/page.tsx").read_text(),
        "runs": Path("apps/dashboard/src/app/runs/page.tsx").read_text(),
        "tasks": Path("apps/dashboard/src/app/tasks/page.tsx").read_text(),
        "trialQuality": Path("apps/dashboard/src/app/trial-quality/page.tsx").read_text(),
    }
    sources = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()
    server = Path("apps/dashboard/src/lib/data-freshness-server.ts").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()

    for source_key, page in page_sources.items():
        assert "DataFreshnessNotice" in page
        assert f"INDEX_ROUTE_FRESHNESS_SOURCES.{source_key}" in page
        assert "buildRegisteredOperationalFreshness" in page
        assert "new Date().toISOString()" in page

    for relation in (
        "benchmark.v_dashboard_arms",
        "benchmark.benchmark_artifacts",
        "benchmark.benchmark_eval_suites",
        "benchmark.benchmark_eval_suite_items",
        "benchmark.v_valid_suite_arm_comparison",
        "benchmark.v_valid_eval_arm_comparison",
        "benchmark.v_arm_run_summary",
        "benchmark.v_dashboard_tasks",
        "benchmark.v_arm_run_quality_summary",
        "benchmark.v_trial_quality_flags",
        "benchmark.benchmark_invalid_arm_runs",
    ):
        assert relation in sources

    assert "latestCanonicalPublishedAt: null" in server
    assert "staleAfterSeconds: null" in server
    assert 'queryStatus: "unavailable", value: null' in server
    assert "armRunFreshnessCoverageWarning" in server
    assert "90" not in server

    assert (
        "All registered arms; latest execution is derived from imported "
        "trial-bearing runs across run classes"
    ) in sources
    assert (
        "All registered tasks; latest execution is derived from imported "
        "trial-bearing runs across run classes"
    ) in sources

    latest_execution_section = data[data.index(
        "export async function getAllImportedArmLatestIncludedExecutionAt"
    ) :]
    assert "max(r.finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(arm_run.finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(r.created_at)" not in latest_execution_section
    assert "max(r.updated_at)" not in latest_execution_section

    tasks = page_sources["tasks"]
    assert "Tasks — All imported" in tasks
    assert "all imported run classes" in tasks
    assert "full-suite, smoke, canary, diagnostic, legacy" in tasks
    assert "imported canary and smoke trials" not in tasks

    eval_suites = page_sources["evalSuites"]
    assert "distinct arms represented by valid imported rows" in eval_suites
    assert "invalid and quarantined arm runs are excluded" in eval_suites
    assert "all imported arms" not in eval_suites

    artifacts = page_sources["artifacts"]
    assert "getArtifactBrowserLatestIncludedExecutionAt" in artifacts
    assert "getArtifactContent" not in artifacts
    assert "getLiveArtifactBytes" not in artifacts

    assert "findLatestIncludedExecutionAt" in page_sources["runs"]
    assert "row.finished_at" in page_sources["runs"]
    trial_quality = page_sources["trialQuality"]
    assert "getDisplayedArmRunFreshnessResolution" in trial_quality
    assert "deduplicateDisplayedArmRunFreshnessIdentities" in trial_quality
    assert "displayedArmRunIdentities" in trial_quality
    assert "armRunFreshnessCoverageWarning" in trial_quality
    assert "getRunLabelsLatestIncludedExecutionAt" not in trial_quality
    assert "getRunLabelsLatestIncludedExecutionAt" not in data
    assert "from benchmark.v_arm_run_summary summary" in data
    assert "summary.phase = 'phase3'" in data
    assert "summary.suite_id is not distinct from requested.suite_id" in data
    assert "summary.arm_id = requested.arm_id" in data
    assert "summary.run_label = requested.run_label" in data
    trial_quality_freshness = data[data.index(
        "export async function getDisplayedArmRunFreshnessResolution"
    ) : data.index("export async function getSuspectNoopTrialRows")]
    assert "benchmark.benchmark_runs" not in trial_quality_freshness
    for metadata_timestamp in ("created_at", "updated_at", "invalidated_at", "uploaded_at"):
        assert metadata_timestamp not in trial_quality_freshness


def test_cloud_detail_routes_expose_exact_freshness_and_artifact_provenance() -> None:
    pages = {
        "artifactMetadata": Path("apps/dashboard/src/app/artifacts/[artifactId]/page.tsx").read_text(),
        "trialMetadata": Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text(),
        "runDetail": Path("apps/dashboard/src/app/runs/[runLabel]/page.tsx").read_text(),
        "evalSuiteDetail": Path("apps/dashboard/src/app/eval-suites/[suiteId]/page.tsx").read_text(),
        "evalTaskDetail": Path("apps/dashboard/src/app/evals/[taskId]/page.tsx").read_text(),
    }
    arm_run_redirect = Path("apps/dashboard/src/app/arm-runs/[armRunId]/page.tsx").read_text()
    sources = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()
    notice = Path("apps/dashboard/src/components/DataFreshnessNotice.tsx").read_text()
    artifact_notice = Path("apps/dashboard/src/components/ArtifactProvenanceNotice.tsx").read_text()
    artifact_content = Path("apps/dashboard/src/lib/artifact-content.ts").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()

    for source_key, page in pages.items():
        assert "DataFreshnessNotice" in page
        assert f"DETAIL_ROUTE_FRESHNESS_SOURCES.{source_key}" in page
        assert "buildRegisteredOperationalFreshness" in page
        assert "new Date().toISOString()" in page

    for relation in (
        "benchmark.benchmark_artifacts",
        "benchmark.benchmark_trials",
        "benchmark.v_dashboard_runs",
        "benchmark.v_valid_suite_arm_comparison",
        "benchmark.v_valid_eval_arm_comparison",
        "benchmark.v_valid_arm_run_summary",
    ):
        assert relation in sources

    artifact_page = pages["artifactMetadata"]
    assert "ArtifactProvenanceNotice" in artifact_page
    assert "buildArtifactProvenance" in artifact_page
    assert "artifact.run_finished_at" in artifact_page
    assert "Artifact object storage" in artifact_notice
    assert "Retrieval time is not benchmark execution or canonical publication time" in artifact_notice
    assert 'freshness.sourceKind === "artifact"' in notice
    assert "Artifact object storage" in notice
    assert "R2 URI presence alone does not verify object bytes" in artifact_content
    assert 'integrityStatus: "verified"' in artifact_content
    assert '"bounded_preview"' in artifact_content

    trial_page = pages["trialMetadata"]
    assert "trial.run_finished_at" in trial_page
    assert "Artifact-byte retrieval:</strong> not performed by this render" in trial_page
    assert "bounded R2-first analysis was requested or used as fallback" in trial_page
    assert "does not prove that bytes were read or verified" in trial_page

    run_page = pages["runDetail"]
    assert "getRunDetailResolution" in run_page
    assert 'resolution.status === "ambiguous"' in run_page
    assert "No latest row or alternate phase/mode was selected" in run_page
    run_resolution = data[data.index("export async function getRunDetailResolution") : data.index("export async function getRunTrials")]
    assert "where phase = 'phase3'" in run_resolution
    assert "and run_label = $1" in run_resolution
    assert "limit 1" not in run_resolution
    assert "finished_at desc" not in run_resolution

    assert "getRunLabelForArmRunId" in arm_run_redirect
    assert "UUID_RE" in arm_run_redirect
    assert "redirect(`/runs/${encodeURIComponent(runLabel)}`)" in arm_run_redirect

    suite_page = pages["evalSuiteDetail"]
    assert "getValidSuiteLatestIncludedExecutionAt(decodedSuiteId)" in suite_page
    assert "valid-imported comparison population" in suite_page
    task_page = pages["evalTaskDetail"]
    assert "getValidEvalTaskLatestIncludedExecutionAt(decodedTaskId)" in task_page
    eval_freshness = data[data.index("export async function getValidEvalTaskLatestIncludedExecutionAt") :]
    assert "max(arm_run.finished_at)::text" in eval_freshness
    assert "join benchmark.benchmark_trials trial" in eval_freshness
    assert "where trial.task_id = $1" in eval_freshness
    for metadata_timestamp in ("created_at", "updated_at", "uploaded_at", "invalidated_at"):
        assert metadata_timestamp not in eval_freshness

    assert "latestCanonicalPublishedAt: null" in Path("apps/dashboard/src/lib/data-freshness-server.ts").read_text()
    assert "staleAfterSeconds: null" in Path("apps/dashboard/src/lib/data-freshness-server.ts").read_text()
    assert "90" not in artifact_notice
    assert "90" not in pages["runDetail"]


def test_stale_operational_pages_are_removed_from_primary_navigation() -> None:
    shell = Path("apps/dashboard/src/components/AppShell.tsx").read_text()

    assert '{ href: "/runners"' not in shell
    assert '{ href: "/readiness"' not in shell
    assert '{ href: "/runs/live", label: "Live Runs" }' in shell
    assert '{ href: "/planner", label: "Planner" }' in shell


def test_runner_fleet_route_is_a_non_live_deprecation_destination() -> None:
    page = Path("apps/dashboard/src/app/runners/page.tsx").read_text()

    assert 'href="/runs/live"' in page
    assert 'href="/runs"' in page
    assert "deprecated operational page" in page
    assert "retained for old links" in page.lower()
    assert "not a live fleet-status source" in page
    assert "does not assert runner count, availability, capacity, or queue depth" in page
    assert "execution-level runner names" in page
    assert "complete fleet model" in page
    for stale_claim in ("one OVH", "Current state", "runner is active"):
        assert stale_claim not in page


def test_route_readiness_is_a_dated_historical_planning_snapshot() -> None:
    page = Path("apps/dashboard/src/app/readiness/page.tsx").read_text()

    assert "historical planning snapshot" in page
    assert "2026-08-05" in page
    assert "No provider, LiteLLM, Claude Code, Harbor, or runner probes were run" in page
    assert "underlying observations were not revalidated" in page
    assert 'href="/planner"' in page
    assert 'href="/runs/live"' in page
    assert 'href="/runs"' in page
    assert "Current non-standard" not in page
    assert 'className="status"' not in page
    assert "historicalRouteNotes" in page
    assert "statusRows" not in page
    assert "This process reference does not prove that any gate is currently satisfied" in page
    for route in (
        "router-anthropic-fable-5",
        "claude-mythos-5",
        "opusplan",
        "hosted NVIDIA NIM",
        "local open-weight serving",
    ):
        assert route in page
    assert "original event date not recorded" in page


def test_architecture_documents_execution_live_publication_and_read_paths() -> None:
    page = Path("apps/dashboard/src/app/architecture/page.tsx").read_text()
    normalized = page.lower()

    for phrase in (
        "Benchmark questions",
        "Benchmark design and arm selection",
        "Local or GitHub Actions dispatch",
        "self-hosted runner",
        "OVH VPS",
        "Harbor task container",
        "Claude Code agent harness",
        "LiteLLM route when applicable",
        "Provider/model backend",
        "Held-out verifier/test execution",
        "No LLM judge determines the benchmark reward",
        "scripts/run_arm_live.py",
        "scripts/publish_phase3_run.py",
        "scripts/ingest_phase3_run_metadata.py",
        "Supabase live metadata/state",
        "Cloudflare R2 artifact bytes",
        "eligibility, and path-safety checks",
        "transaction/rollback verification",
        "Final publication without live supervision",
        "Historical file-backed review snapshots",
    ):
        assert phrase in page
    assert "raw reward and result" in normalized
    assert "the dashboard reads shared supabase/r2 services and does not connect directly to the vps" in normalized
    assert "not the sole current workflow publication path" in page
    assert "Local dispatch executes in the selected local workspace" in page
    assert "GitHub Actions uses a selected self-hosted runner workspace on an OVH VPS" in page
    assert "When shared database publication is enabled" in page
    assert "local redacted NDJSON remains available independently" in page
    assert "Progressive artifacts are reconciled when present" in page
    assert "Whether or not live supervision ran" in page
    assert "uploads any missing canonical artifacts before R2 verification and canonical database publication" in page
    for href in ('href="/runs/live"', 'href="/artifacts"', 'href="/cross-phase"'):
        assert href in page
    for stale_phrase in (
        "Sponsor questions",
        "Model-arm plan",
        "Sponsor-facing",
        ">Logical mode<",
        ">Storage mode<",
    ):
        assert stale_phrase not in page


def test_architecture_glossary_uses_public_terms_and_retains_internal_compatibility() -> None:
    page = Path("apps/dashboard/src/app/architecture/page.tsx").read_text()
    glossary = Path("apps/dashboard/src/lib/glossary.ts").read_text()
    r2_entry = glossary.split('term: "R2 artifact"', 1)[1].split("  },", 1)[0]

    assert 'term: "Benchmark run class"' in glossary
    assert 'term: "Result source/storage location"' in glossary
    assert "logical_mode is an internal field used to represent benchmark run class" in glossary
    assert "storage_mode is an internal field used for the physical result-directory or legacy ingestion key" in glossary
    assert 'TermInfo term="Benchmark run class"' in page
    assert 'TermInfo term="Result source/storage location"' in page
    assert 'export type GlossaryTerm = (typeof glossaryEntries)[number]["term"]' in glossary
    assert "Sponsor-facing run type" not in glossary
    assert "preferred benchmark cost for sponsor-facing comparisons" not in glossary
    assert "published progressively during supervised execution" in r2_entry
    assert "by final canonical publication" in r2_entry
    assert "Supabase stores the corresponding metadata and relationships" in r2_entry
    assert "other files collected during ingestion" not in r2_entry
