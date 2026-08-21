import csv
import hashlib
import json
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


def test_live_and_api_routes_complete_freshness_provenance_without_threshold_leakage() -> None:
    live_page = Path("apps/dashboard/src/app/runs/live/page.tsx").read_text()
    live_artifact = Path("apps/dashboard/src/app/live-artifacts/[artifactId]/page.tsx").read_text()
    live_download = Path("apps/dashboard/src/app/live-artifacts/[artifactId]/download/route.ts").read_text()
    health = Path("apps/dashboard/src/app/api/health/route.ts").read_text()
    live_data = Path("apps/dashboard/src/lib/live-data.ts").read_text()
    freshness = Path("apps/dashboard/src/lib/data-freshness.ts").read_text()
    freshness_server = Path("apps/dashboard/src/lib/data-freshness-server.ts").read_text()
    sources = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()
    liveness_notice = Path("apps/dashboard/src/components/LiveLivenessNotice.tsx").read_text()

    for relation in (
        "benchmark.live_runs",
        "benchmark.live_run_events",
        "benchmark.live_trials",
        "benchmark.live_artifacts",
        "benchmark.v_dashboard_runs",
    ):
        assert relation in sources

    assert "LiveLivenessNotice" in live_page
    assert "LIVE_ROUTE_FRESHNESS_SOURCES.liveRunsCloud" in live_page
    assert "LIVE_ROUTE_FRESHNESS_SOURCES.localFallback" in live_page
    assert 'queryStatus: errorState ? "unavailable" : "available"' in live_page
    assert 'queryStatus: "available"' in live_page
    assert "DASHBOARD_LIVE_LOCAL_FALLBACK" in live_page
    assert "explicitly enabled local-development fallback" in live_page
    assert "Cloud operational database" in liveness_notice
    assert "Local development fallback, not cloud state" in liveness_notice
    assert "applies only to live reporting liveness" in liveness_notice
    assert "Canonical publication time:" in liveness_notice
    assert "Not recorded" in liveness_notice
    assert "heartbeatThresholdSeconds: LIVE_STALE_AFTER_SECONDS" in live_page
    assert "cloudActiveRuns.map((run) => run.last_heartbeat_at)" in live_page
    assert "active.map((run) => run.last_heartbeat_at)" in live_page
    assert "LIVE_STALE_AFTER_SECONDS = 90" in live_data
    assert "heartbeat_within_live_threshold" in freshness
    assert "heartbeat_timestamp_in_future" in freshness
    assert "No live heartbeat timestamp is available; the run is not classified as active" in freshness
    assert "90" not in freshness
    assert "staleAfterSeconds: null" in freshness_server

    assert "DataFreshnessNotice" in live_artifact
    assert "ArtifactProvenanceNotice" in live_artifact
    assert "LIVE_ROUTE_FRESHNESS_SOURCES.liveArtifactMetadata" in live_artifact
    assert "buildArtifactProvenance" in live_artifact
    assert "readFreshnessMetadata(() => getLiveRun(artifact.live_run_id))" in live_artifact
    assert "artifact metadata remains visible" in live_artifact.lower()
    assert "Artifact upload time" in live_artifact
    assert "not canonical publication time" in live_artifact
    assert "R2 indexed" in live_artifact
    assert "R2 available" not in live_artifact

    assert "getLiveArtifact" in live_download
    assert "fetchArtifactDownload" in live_download
    assert "previewArtifactContent" not in live_download
    assert "DASHBOARD_ENABLE_LOCAL_ARTIFACT_PREVIEW" not in live_download
    assert "relative_local_path" in live_download
    assert "new Response(upstream.body" in live_download
    assert "redact" not in live_download.lower()

    assert "LIVE_ROUTE_FRESHNESS_SOURCES.apiHealth" in health
    assert "benchmark.v_dashboard_runs" in health
    assert "max(finished_at)::text as latest_included_execution_at" in health
    assert 'canonical_publication_status: freshness.canonicalPublicationStatus' in health
    assert 'query_status: freshness.queryStatus' in health
    assert "status: 503" in health
    assert "LIVE_STALE_AFTER_SECONDS" not in health
    assert "90" not in health
    for metadata_timestamp in ("created_at", "updated_at", "uploaded_at", "invalidated_at"):
        assert metadata_timestamp not in health


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


def test_dr106a_evidence_destinations_are_exact_scoped_and_read_only() -> None:
    links = Path("apps/dashboard/src/lib/evidence-links.ts").read_text()
    filters = Path("apps/dashboard/src/lib/reviewed-trial-filters.ts").read_text()
    cost_page = Path("apps/dashboard/src/app/cost-coverage/page.tsx").read_text()
    comprehensive = Path("apps/dashboard/src/app/comprehensive-review/page.tsx").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    review_data = Path("apps/dashboard/src/lib/review-data.ts").read_text()
    context = Path("apps/dashboard/src/components/EvidenceSourceContextNotice.tsx").read_text()
    run_detail = Path("apps/dashboard/src/app/runs/[runLabel]/page.tsx").read_text()
    trial_detail = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert "buildExactRunHref" in links
    assert "buildExactTrialHref" in links
    assert "buildReviewedAggregateArmEvidenceHref" in links
    assert "buildAggregateArmEvidenceHref" not in links
    assert "buildCostCoverageHref" in links
    assert "buildReviewedFailureEvidenceHref" in links
    assert 'source: "operational_or_unsupported"' in links
    assert "return null" in links
    assert "new URLSearchParams" in links
    assert "latest" not in links.lower()
    assert '"valid-imported"' in links and '"all-imported"' in links
    assert "Cost Coverage requires a reviewed Phase 3 scope" in links
    assert "source_scope is navigation context only" in links
    assert "never changes a destination evidence population" in links
    assert "selectEvidenceSourceScope" in context
    assert "EVIDENCE_SOURCE_SCOPE_NOTE" in context
    assert "<EvidenceSourceContextNotice value={query.source_scope}" in run_detail
    assert "<EvidenceSourceContextNotice value={query.source_scope}" in trial_detail
    assert "buildExactRunHref(trial.run_label, sourceScope)" in trial_detail
    assert 'href={`/runs/${encodeURIComponent(trial.run_label)}`}' not in trial_detail

    assert "getCostProvenanceFocusRows" in cost_page
    assert "selectEvidenceSourceScope(params.source_scope)" in cost_page
    assert "<EvidenceSourceContextNotice value={params.source_scope}" in cost_page
    assert "buildExactTrialHref(row.trial_id, onwardSourceScope)" in cost_page
    assert "buildExactRunHref(row.run_label, onwardSourceScope)" in cost_page
    assert "Cost provenance focus" in cost_page
    assert "never changes the reviewed scope totals above" in cost_page
    assert "arm-only focus may span multiple valid runs" in cost_page.lower()
    assert "No latest, prefix, or alternate-trial fallback" in cost_page
    assert "benchmark.v_trial_adjusted_cost_coverage" in data
    assert "trial_id = $${parameters.length}::uuid" in data
    assert "run_label = $${parameters.length}" in data
    assert "arm_id = $${parameters.length}" in data
    cost_query = data.split("export async function getCostProvenanceFocusRows", 1)[1]
    cost_query = cost_query.split("export ", 1)[0]
    assert " like " not in cost_query.lower()
    assert "latest" not in cost_query.lower()
    assert "insert " not in cost_query.lower()
    assert "update " not in cost_query.lower()
    assert "delete " not in cost_query.lower()

    assert 'id="reviewed-trials"' in comprehensive
    assert "selectEvidenceSourceScope(params.source_scope)" in comprehensive
    assert "<EvidenceSourceContextNotice value={params.source_scope}" in comprehensive
    assert "buildReviewedTrialPageHref(params, trialFilters" in comprehensive
    assert "reviewedTrialsPageHref" not in comprehensive
    assert "review.reviewedTrials.filter" in comprehensive
    assert "matchesReviewedTrial(row, trialFilters)" in comprehensive
    assert 'priority: first(params.priority) || "high"' in comprehensive
    for name in (
        "trial_id", "trial_arm", "trial_run", "trial_task",
        "trial_outcome", "trial_failure", "trial_execution", "trial_termination",
        "trial_policy", "trial_page", "trial_page_size",
    ):
        assert name in comprehensive
    assert 'className="sticky-id-column">Trial</th>' in comprehensive
    assert "buildExactTrialHref(row.trial_id, reviewedSourceScope)" in comprehensive
    assert "complete frozen reviewed-trial result surface" in comprehensive
    assert "not the" in comprehensive and "manual-review queue below" in comprehensive
    assert "reviewedTrials: ComprehensiveTrialReview[]" in review_data
    assert "reviewedTrials: trialRows" in review_data
    assert "row.trial_id === filters.trialId" in filters
    assert "row.run_label === filters.runLabel" in filters
    assert "row.failure_subtype === filters.failureSubtype" in filters
    assert "row.execution_validity === filters.executionValidity" in filters
    assert "row.termination_subtype === filters.terminationSubtype" in filters
    assert "row.policy_disposition === filters.policyDisposition" in filters
    assert "includes(" not in filters
    assert "test:evidence-links" in package

    assert '"results", "manual_verification", "comprehensive_review_20260731"' in review_data
    combined = links + filters + cost_page + comprehensive + context
    for forbidden in ("fs.write", "writefile", "insert into", "update benchmark.", "put_object"):
        assert forbidden not in combined.lower()
    assert "failure_taxonomy_classifier" not in comprehensive
    assert "@aws-sdk" not in comprehensive


def test_dr106b_frozen_arm_summary_links_use_exact_equal_count_predicates() -> None:
    review_dir = Path("results/manual_verification/comprehensive_review_20260731")
    with (review_dir / "trial_review.csv").open(newline="") as handle:
        trials = list(csv.DictReader(handle))
    with (review_dir / "arm_review_summary.csv").open(newline="") as handle:
        summaries = list(csv.DictReader(handle))

    by_arm: dict[str, list[dict[str, str]]] = {}
    for row in trials:
        by_arm.setdefault(row["arm_id"], []).append(row)

    assert len(trials) == 960
    assert {row["arm_id"] for row in summaries} == set(by_arm)
    for summary in summaries:
        rows = by_arm[summary["arm_id"]]
        expected = {
            "trials_reviewed": len(rows),
            "substantive_successes": sum(
                row["raw_outcome"] == "success" and row["execution_validity"] == "substantive"
                for row in rows
            ),
            "substantive_failures": sum(
                row["raw_outcome"] == "failure" and row["execution_validity"] == "substantive"
                for row in rows
            ),
            "policy_refusals": sum(row["policy_disposition"] == "provider_policy_refusal" for row in rows),
            "timeouts": sum(row["termination_subtype"] == "timeout" for row in rows),
            "setup_transport_failures": sum(
                row["termination_subtype"] == "setup_or_transport_exception" for row in rows
            ),
        }
        assert {name: int(summary[name]) for name in expected} == expected

    page = Path("apps/dashboard/src/app/comprehensive-review/page.tsx").read_text()
    assert 'rawOutcome: "failure", executionValidity: "substantive"' in page
    assert 'policyDisposition: "provider_policy_refusal"' in page
    assert 'terminationSubtype: "timeout"' in page
    assert 'terminationSubtype: "setup_or_transport_exception"' in page
    for deliberately_unlinked in (
        "<td>{arm.empty_completions}</td>",
        "<td>{arm.telemetry_mismatches}</td>",
        "<td>{arm.unknown_classifications}</td>",
        "<td>{arm.manual_review_queue}</td>",
    ):
        assert deliberately_unlinked in page


def test_dr106b_trial_actions_and_population_boundaries_are_explicit() -> None:
    run_detail = Path("apps/dashboard/src/app/runs/[runLabel]/page.tsx").read_text()
    arms = Path("apps/dashboard/src/app/arms/page.tsx").read_text()
    cross_phase = Path("apps/dashboard/src/app/cross-phase/page.tsx").read_text()
    cost = Path("apps/dashboard/src/app/cost-coverage/page.tsx").read_text()

    assert run_detail.index('className="sticky-id-column">Trial</th>') < run_detail.index("<th>Task</th>")
    assert "buildExactTrialHref(trial.trial_id, sourceScopeSelection.sourceScope)" in run_detail
    assert "buildReviewedAggregateArmEvidenceHref" not in arms
    assert 'row.phase === "phase3" ? chartArmById.get(row.arm_id) : null' in cross_phase
    assert "Frozen aggregate row" in cross_phase
    assert "getCostPerformanceChartArms(selection.scopeId)" in cost
    assert "No exact frozen selected run exists" in cost


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
    assert "new URLSearchParams({ scope: option.id })" in selector
    assert 'query.set("source_scope", sourceScope)' in selector
    assert 'href={`${pathname}?${query.toString()}`}' in selector
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
    eval_detail = Path("apps/dashboard/src/app/evals/[taskId]/page.tsx").read_text()
    eval_scopes = Path("apps/dashboard/src/lib/eval-scopes.ts").read_text()
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

    assert "selectEvalInventoryScope(params.scope)" in evals
    assert "EvalScopeSelector" in evals
    assert 'scopeId={selection.scopeId}' in evals
    assert '"valid-imported"' in eval_scopes
    assert '"all-imported"' in eval_scopes
    assert "Valid imported" in evals
    assert "All imported" in evals
    assert "Invalid and quarantined arm runs are excluded" in evals
    assert "not a fixed full-suite leaderboard denominator" in evals
    assert "selectEvalInventoryScope(query.scope)" in eval_detail
    assert 'href={`/evals?scope=${selection.scopeId}`}' in eval_detail
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


def test_dr104_consolidates_tasks_into_scope_aware_evals_without_population_substitution() -> None:
    index = Path("apps/dashboard/src/app/evals/page.tsx").read_text()
    detail = Path("apps/dashboard/src/app/evals/[taskId]/page.tsx").read_text()
    tasks = Path("apps/dashboard/src/app/tasks/page.tsx").read_text()
    selector = Path("apps/dashboard/src/components/EvalScopeSelector.tsx").read_text()
    scopes = Path("apps/dashboard/src/lib/eval-scopes.ts").read_text()
    data = Path("apps/dashboard/src/lib/dashboard-data.ts").read_text()
    freshness = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()
    shell = Path("apps/dashboard/src/components/AppShell.tsx").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert 'DEFAULT_EVAL_INVENTORY_SCOPE: EvalInventoryScopeId = "valid-imported"' in scopes
    assert 'value === "valid-imported" || value === "all-imported"' in scopes
    assert 'warning: "invalid_scope"' in scopes
    assert 'warning: "repeated_scope"' in scopes
    assert "Unknown scope value; Valid imported was selected." in scopes
    assert "Repeated scope values are not supported; Valid imported was selected." in scopes
    assert "selection.warningMessage" in index
    assert 'role="alert"' in index
    assert "selection.warningMessage" in detail
    assert 'role="alert"' in detail
    assert 'href={`/evals?scope=${option.id}`}' in selector
    assert "Valid imported" in selector
    assert "All imported" in selector

    assert "allImported ? getAllImportedEvalRows() : getEvalRows()" in index
    assert "getValidImportedEvalLatestIncludedExecutionAt()" in index
    assert "getAllImportedTaskLatestIncludedExecutionAt()" in index
    assert "INDEX_ROUTE_FRESHNESS_SOURCES.evals[selection.scopeId]" in index
    assert 'href={`/evals/${encodeURIComponent(row.task_id)}?scope=${selection.scopeId}`}' in index
    assert "formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)" in index
    assert "not a fixed full-suite" in index

    valid_index = data[data.index("export async function getEvalRows") : data.index(
        "export async function getAllImportedEvalRows"
    )]
    all_index = data[data.index("export async function getAllImportedEvalRows") : data.index(
        "export async function getValidImportedEvalLatestIncludedExecutionAt"
    )]
    valid_detail = data[data.index("export async function getEvalArmComparison") : data.index(
        "export async function getAllImportedEvalArmComparison"
    )]
    all_detail = data[data.index("export async function getAllImportedEvalArmComparison") : data.index(
        "export async function getValidEvalTaskLatestIncludedExecutionAt"
    )]
    assert "benchmark.v_valid_eval_arm_comparison" in valid_index
    assert "benchmark.v_dashboard_tasks" not in valid_index
    assert "benchmark.v_dashboard_tasks" in all_index
    assert "benchmark.benchmark_trials" in all_index
    assert "benchmark.v_valid_eval_arm_comparison" not in all_index
    assert "cost_row_count" in valid_index and "missing_cost_count" in valid_index
    assert "cost_row_count" in all_index and "missing_cost_count" in all_index
    assert "benchmark.v_valid_eval_arm_comparison" in valid_detail
    assert "benchmark.benchmark_trials trial" in all_detail
    assert "left join lateral (" in all_detail
    assert "benchmark.benchmark_invalid_arm_runs invalid_record" in all_detail
    assert "select true as is_invalid" in all_detail
    assert "invalid_record.run_label = run.run_label" in all_detail
    assert "limit 1" in all_detail
    assert ") invalid_lookup on true" in all_detail
    assert "invalid_lookup.is_invalid is true" in all_detail
    assert "left join benchmark.benchmark_invalid_arm_runs" not in all_detail
    assert "invalid_or_quarantined" in all_detail
    assert "trial.arm_run_id is null then 'unlinked'" in all_detail
    assert "benchmark.v_valid_eval_arm_comparison" not in all_detail

    assert "allImported ? getAllImportedEvalArmComparison(decodedTaskId)" in detail
    assert "getEvalArmComparison(decodedTaskId)" in detail
    assert 'href={`/evals?scope=${selection.scopeId}`}' in detail
    assert "DETAIL_ROUTE_FRESHNESS_SOURCES.evalTaskDetail[selection.scopeId]" in detail
    assert "Invalid / quarantined" in detail
    assert "Linked / unflagged" in detail
    assert "Valid / unflagged" not in detail
    assert "Imported / unlinked" in detail

    assert '"valid-imported": Object.freeze({' in freshness
    assert '"all-imported": Object.freeze({' in freshness
    assert "Supabase/Postgres valid-imported eval inventory" in freshness
    assert "Supabase/Postgres all-imported eval inventory" in freshness
    assert "Supabase/Postgres valid-imported eval/task detail" in freshness
    assert "Supabase/Postgres all-imported eval/task detail" in freshness

    assert 'redirect("/evals?scope=all-imported")' in tasks
    assert '{ href: "/tasks", label: "Tasks" }' not in shell
    assert '{ href: "/evals", label: "Evals" }' in shell
    assert "eval-scopes.test.mjs" in package


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
    assert 'buildExactRunHref(runLabel, "phase3-extended")' in reconciliation
    assert "buildCostCoverageHref" in reconciliation
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


def test_cost_performance_chart_foundation_uses_current_reviewed_cost_and_frozen_g1_contracts() -> None:
    model = Path("apps/dashboard/src/lib/cost-performance-chart.ts").read_text()
    presentation = Path(
        "apps/dashboard/src/lib/presentation-labels.ts"
    ).read_text()
    view = Path("apps/dashboard/src/lib/cost-performance-chart-view.ts").read_text()
    table = Path(
        "apps/dashboard/src/components/CostPerformanceChartTable.tsx"
    ).read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert "PHASE3_CURRENT_REVIEWED_COMPARISON" in model
    assert "getCurrentReviewedPhase3Scope" in model
    assert "getReviewedRunSelectionScope" in model
    assert "buildExactRunHref" in model
    assert "buildCostCoverageHref" in model
    assert "getArmRows" not in model
    assert "dashboard-data" not in model
    assert "./db" not in model
    assert "latest" not in model.lower()

    assert "displayName: friendlyModelLabel(arm.backendModel)" in model
    assert "reviewedProvider: arm.provider" in model
    assert "const provider = providerPresentation(arm.provider);" in model
    assert "providerFamily: provider.familyKey" in model
    assert "providerFamilyLabel: provider.label" in model
    assert '"moonshot-kimi": Object.freeze({' in presentation
    assert 'familyKey: "moonshot-kimi"' in presentation
    assert 'label: "Moonshot / Kimi"' in presentation
    assert "const passRate = arm.successCount / arm.trialCount" in model
    assert "arm.selectedCostBasis" in model
    assert '"qualified_retained_rate_estimate"' in model
    assert 'arm.selectedCostBasis === "provider_billed"' in model
    assert "arm.selectedCostPerAttemptUsd" in model
    assert "arm.selectedCostPerCleanSuccessUsd" in model
    assert "arm.selectedOutcomeCostAllocationStatus" in model
    assert '"unavailable_provider_aggregate"' in model
    assert "arm.providerSelectedRunLabel" in model
    assert "historical adjusted outcome spend is not reallocated" in model
    assert "not adjusted-known or provider-billed cost" in model
    assert 'export * from "./cost-performance-chart-view"' in model
    assert "PARETO_FLOAT_TOLERANCE = 1e-12" in view
    assert "candidate.xValue" in view
    assert "candidate.passRate" in view
    assert "metricAvailabilityReasons" in model
    assert 'from "../lib/cost-performance-chart-view"' in table
    assert 'from "../lib/cost-performance-chart"' not in table
    for forbidden_reference in (
        "phase3-reviewed-comparison",
        "phase3-current-reviewed-comparison",
        "phase3-reviewed-run-selection",
        "overview-reviewed-comparison",
        "generated/",
    ):
        assert forbidden_reference not in view

    for material_fact in (
        "Arm",
        "Provider",
        "Scope membership",
        "Selected reviewed run",
        "Successes / trials",
        "Pass rate",
        "Cost basis",
        "Confidence and provenance",
        "Accounting gap",
        "Failure / incomplete spend",
        "Qualification",
        "Arm evidence",
    ):
        assert material_fact in table
    assert 'aria-label="Accessible cost and performance chart data"' in table
    assert "Unavailable —" in table
    assert "Reviewed provider value:" in table
    assert "CostPerformanceChartTable" in table
    assert "cost-performance-chart.test.mjs" in package


def test_h1_does_not_modify_canonical_or_generated_f1_g1_inputs() -> None:
    expected_hashes = {
        "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json":
            "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d",
        "apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts":
            "51963cf066c74c7af7819ebead5c0c06e70852028f87d7be5535424299bda068",
        "results/phase3/reporting/phase3_reviewed_run_selection_20260809.json":
            "5f551c62833adc8a5220ffd7390a5cd50a8f483109536c65b831b66fcd6cf181",
        "apps/dashboard/src/generated/phase3-reviewed-run-selection-data.ts":
            "8cc74625cbfabc5ef8d1822af3b9b2f36672ae0364aac4751e09de54d1d97776",
    }
    for path, expected_hash in expected_hashes.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected_hash


def test_cost_performance_chart_h2_renders_h1_view_on_overview() -> None:
    overview = Path("apps/dashboard/src/app/page.tsx").read_text()
    chart = Path(
        "apps/dashboard/src/components/CostPerformanceChart.tsx"
    ).read_text()
    geometry = Path(
        "apps/dashboard/src/lib/cost-performance-chart-geometry.ts"
    ).read_text()
    package = json.loads(Path("apps/dashboard/package.json").read_text())

    assert '"use client"' in chart
    assert "selectCostPerformanceChartScope(query.chart_scope)" in overview
    assert "selectCostPerformanceChartScope(query.scope)" not in overview
    assert "getCostPerformanceChartArms(chartScopeSelection.scopeId)" in overview
    assert "deriveProviderFilterOptions(chartArms)" in overview
    assert "key={chartScopeSelection.scopeId}" in overview
    assert overview.index("Reviewed full-suite comparison") < overview.index(
        "<CostPerformanceChart"
    ) < overview.index("Different population below")

    assert "Reviewed Phase 3 cost/performance frontier" in chart
    assert "checked-in reviewed" in chart
    assert "F1 snapshot" in chart
    assert "frozen G1 selection" in chart
    assert "DEFAULT_CHART_X_AXIS_METRIC" in chart
    assert "deriveCostPerformanceChartView" in chart
    assert "metricValueForArm" in chart
    assert "view.frontier" in chart
    assert "deriveParetoFrontier" not in chart
    assert "function dominates" not in chart
    assert 'from "../lib/cost-performance-chart-view"' in chart
    assert 'from "../lib/cost-performance-chart"' not in chart
    assert 'parameters.set("chart_scope", nextScope)' in chart
    assert 'parameters.set("scope", nextScope)' not in chart
    assert "Reviewed chart scope" in chart

    assert 'getReviewedPhase3Scope("phase3-extended")' in overview
    assert 'getReviewedRunSelectionScope("phase3-extended")' in overview
    assert 'getReviewedSelectedRunLabels("phase3-extended")' in overview

    assert "Phase 3 extended" in chart
    assert "16 arms" in chart
    assert "Phase 3 core" in chart
    assert "15 arms" in chart
    assert "selectAllProviderFamilies" in chart
    assert "clearProviderFamilies" in chart
    assert "selectAllChartArmIds" in chart
    assert "clearChartArmIds" in chart
    assert '"moonshot-kimi": "#62d98b"' in chart
    assert "providerColor(point.arm.providerFamily)" in chart
    assert "providerColor(point.arm.reviewedProvider)" not in chart

    assert 'role="button"' in chart
    assert "tabIndex={0}" in chart
    assert 'event.key === "Enter"' in chart
    assert 'event.key === " "' in chart
    assert "cost-performance-point-qualified" in chart
    assert "not adjusted-known, invoice, or provider-billed cost" in chart
    assert "arms={view.selectedVisibleArms}" in chart
    assert "Skip to non-hover evidence table" in chart
    assert "No provider families are enabled." in chart
    assert "No arms are selected." in chart
    assert "One eligible point is visible; no frontier segment is drawn." in chart

    assert "paddedLinearDomain" in geometry
    assert "minimum > 0 && lower <= 0" in geometry
    assert "Chart domain values must be finite" in geometry
    assert "CostPerformanceChart.test.mjs" in package["scripts"]["test:trial-analysis"]
    for dependency in ("d3", "plotly", "recharts", "vega"):
        assert dependency not in package["dependencies"]


def test_dr013_heatmap_headers_wrap_and_phase_summaries_are_structured() -> None:
    heatmap = Path("apps/dashboard/src/components/SuiteHeatmap.tsx").read_text()
    cross_phase = Path("apps/dashboard/src/app/cross-phase/page.tsx").read_text()
    css = Path("apps/dashboard/src/app/globals.css").read_text()

    assert 'className="heatmap-arm-heading"' in heatmap
    assert 'className="heatmap-arm-label"' in heatmap
    assert 'title={arm} aria-label={arm}' in heatmap
    assert 'const arms = Array.from(new Set(rows.map((row) => row.arm_id))).sort();' in heatmap
    assert heatmap.count("{arms.map((arm) =>") == 2
    assert "const cell = task.cells.get(arm);" in heatmap
    assert ".heatmap-table .heatmap-arm-heading" in css
    assert "white-space: normal;" in css
    assert ".heatmap-arm-label" in css
    assert "overflow-wrap: anywhere;" in css
    assert "text-overflow: ellipsis" not in css

    assert '<section className="phase-summary-grid"' in cross_phase
    assert 'className="metric-card phase-summary-card"' in cross_phase
    assert '<dl className="phase-summary-details">' in cross_phase
    for label in ("Population", "Results", "Reviewed cost", "Cost basis"):
        assert f"<dt>{label}</dt>" in cross_phase
    assert "summary.success_count}/{summary.trial_count} successes" in cross_phase
    assert "summary.adjusted_cost_usd" in cross_phase
    assert "grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));" in css


def test_dr013_omits_only_meaningless_secondary_arm_labels_and_aligns_runner_body() -> None:
    cost = Path("apps/dashboard/src/app/cost-coverage/page.tsx").read_text()
    table = Path("apps/dashboard/src/components/CostPerformanceChartTable.tsx").read_text()
    runners = Path("apps/dashboard/src/app/runners/page.tsx").read_text()
    shell = Path("apps/dashboard/src/components/AppShell.tsx").read_text()
    css = Path("apps/dashboard/src/app/globals.css").read_text()

    assert "friendlyArmLabel" in cost
    assert "friendlyProviderLabel" in cost
    assert "friendlyRoutingLabel" in cost
    assert "const modelLabel = friendlyArmLabel(arm.armId, arm.backendModel);" in cost
    assert '<div className="muted mono">{arm.armId}</div>' in cost
    assert '<div className="muted">{providerLabel} · {routingLabel}</div>' in cost
    assert 'if (value === null) return "Unavailable";' in cost
    assert 'value === null ? "Unavailable" : formatPercent(value)' in cost
    assert "Unavailable —" in table

    assert 'className="runner-fleet-body"' in runners
    assert ".runner-fleet-body" in css
    assert "padding: 0 24px 24px;" in css
    assert "not a live fleet-status source" in runners
    assert "does not assert runner count, availability, capacity, or queue depth" in runners
    assert '{ href: "/runners"' not in shell


def test_dr013_tables_keep_right_edge_scrollable_without_page_wide_clipping() -> None:
    css = Path("apps/dashboard/src/app/globals.css").read_text()
    overview = Path("apps/dashboard/src/app/page.tsx").read_text()
    cross_phase = Path("apps/dashboard/src/app/cross-phase/page.tsx").read_text()
    cost = Path("apps/dashboard/src/app/cost-coverage/page.tsx").read_text()
    trial_quality = Path("apps/dashboard/src/app/trial-quality/page.tsx").read_text()
    chart = Path("apps/dashboard/src/components/CostPerformanceChart.tsx").read_text()

    assert ".table-wrap {" in css
    assert "overflow-x: auto;" in css
    assert "overscroll-behavior-inline: contain;" in css
    assert "scrollbar-gutter: stable;" in css
    assert ".table-wrap > table" in css
    assert "width: max-content;" in css
    assert ".table-wrap thead th" in css
    assert ".table-wrap .mono" in css
    assert ".table-cell-wrap" in css
    assert "overflow-x: hidden" not in css
    assert "overflow-x: clip" not in css

    assert 'className="table-cell-wrap"' in overview
    assert cross_phase.count('className="table-cell-wrap"') >= 2
    assert 'className="table-cell-wrap"' in cost
    assert 'className="table-cell-wrap"' in trial_quality
    assert "Reviewed Phase 3 cost/performance frontier" in chart
    assert 'className="cost-performance-svg"' in chart
    assert "cost-performance-point" in chart


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
    assert "All imported trial-bearing task rows across run classes and validity states" in sources

    latest_execution_section = data[data.index(
        "export async function getAllImportedArmLatestIncludedExecutionAt"
    ) :]
    assert "max(r.finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(arm_run.finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(finished_at)::text as latest_included_execution_at" in latest_execution_section
    assert "max(r.created_at)" not in latest_execution_section
    assert "max(r.updated_at)" not in latest_execution_section

    tasks = Path("apps/dashboard/src/app/tasks/page.tsx").read_text()
    assert 'redirect("/evals?scope=all-imported")' in tasks
    assert "DataFreshnessNotice" not in tasks
    assert "getTaskRows" not in tasks

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
    assert "getAllImportedEvalTaskLatestIncludedExecutionAt(decodedTaskId)" in task_page
    assert "DETAIL_ROUTE_FRESHNESS_SOURCES.evalTaskDetail[selection.scopeId]" in task_page
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
    assert '{ href: "/scaffold", label: "Arm Scaffold" }' not in shell
    assert '{ href: "/tasks", label: "Tasks" }' not in shell
    assert '{ href: "/evals", label: "Evals" }' in shell


def test_dr105_consolidates_planner_and_arm_scaffold_without_mutation() -> None:
    planner = Path("apps/dashboard/src/app/planner/page.tsx").read_text()
    scaffold = Path("apps/dashboard/src/app/scaffold/page.tsx").read_text()
    selector = Path("apps/dashboard/src/components/PlannerModeSelector.tsx").read_text()
    run_builder = Path("apps/dashboard/src/components/RunPlanBuilder.tsx").read_text()
    arm_builder = Path("apps/dashboard/src/components/ArmConfigDraftBuilder.tsx").read_text()
    mode_source = Path("apps/dashboard/src/lib/planner-modes.ts").read_text()
    draft_source = Path("apps/dashboard/src/lib/arm-config-draft.ts").read_text()
    validation = Path("apps/dashboard/src/lib/run-plan-validation.ts").read_text()
    package = Path("apps/dashboard/package.json").read_text()

    assert 'DEFAULT_PLANNER_MODE: PlannerMode = "run"' in mode_source
    assert 'value === "run" || value === "arm"' in mode_source
    assert 'warning: "invalid_mode"' in mode_source
    assert 'warning: "repeated_mode"' in mode_source
    assert "Unknown or empty planner mode" in mode_source
    assert "Repeated planner mode values" in mode_source
    assert "selectPlannerMode(query.mode)" in planner
    assert "selection.warningMessage" in planner
    assert 'role="alert"' in planner
    assert 'href={`/planner?mode=${option.id}`}' in selector
    assert 'aria-current={selected ? "page" : undefined}' in selector
    assert "Plan benchmark run" in mode_source
    assert "Draft new arm configuration" in mode_source

    assert 'redirect("/planner?mode=arm")' in scaffold
    assert "RunPlanBuilder" in planner
    assert 'selection.mode === "run"' in planner
    assert "ArmConfigDraftBuilder" in planner
    assert "existingArmIds={arms.map((arm) => arm.arm_id)}" in planner
    assert 'href="/planner?mode=arm"' in run_builder
    assert not Path("apps/dashboard/src/components/PlannerCommandBuilder.tsx").exists()
    assert not Path("apps/dashboard/src/components/PlaceholderPanel.tsx").exists()
    assert "../lib/planner-types" in run_builder

    assert "Draft only — no repository file is created" in arm_builder
    assert "normal Git review" in arm_builder
    assert "does not request or generate API keys or tokens" in arm_builder
    assert "not ready to run" in arm_builder
    assert "existing checked-in arm" in arm_builder
    assert "router: litellm" in draft_source
    assert "agent: claude-code" in draft_source
    assert "existingArmIds.includes(input.armId)" in draft_source
    for forbidden_mutation in ("writeFile", "appendFile", "createWriteStream", "use server", "fetch("):
        assert forbidden_mutation not in arm_builder
        assert forbidden_mutation not in draft_source
    assert "gh workflow" not in arm_builder
    assert "gh workflow" not in draft_source

    assert "Checked-in planning assumptions" in planner
    assert "not live runner-capacity, provider-availability, quota, or readiness observations" in planner
    assert "configured planner assumption" in validation
    assert "checked-in planner concurrency assumption" in validation
    assert "current runner slots" not in validation
    assert "current safe setting" not in validation
    assert "export const DEFAULT_RUNNER_SLOTS = 3" in validation
    assert "harborConcurrency > 1" in validation
    assert "(providerCounts.gemini ?? 0) > 1" in validation
    assert 'hasQwen && input.runMode === "full"' in validation
    assert "if (hasFable)" in validation

    assert "planner-modes.test.mjs" in package
    assert "arm-config-draft.test.mjs" in package


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
    assert 'className="runner-fleet-body"' in page
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


def test_dr014_architecture_explains_scoring_evidence_and_workflow_switches() -> None:
    page = Path("apps/dashboard/src/app/architecture/page.tsx").read_text()

    assert "are not the task instructions the agent is solving from" in page
    assert "After the agent finishes, they inspect the resulting workspace" in page
    assert "determine benchmark correctness and reward" in page
    assert "dashboard diagnosis as interpretation rather than scoring authority" in page
    assert "No LLM judge determines the benchmark reward" in page
    assert "does not rescore the trial" in page

    for artifact_type in (
        "result",
        "agent_transcript",
        "verifier_stdout",
        "trajectory",
        "verifier_ctrf",
        "verifier_reward",
        "config",
        "log",
        "exception",
    ):
        assert f"<code>{artifact_type}</code>" in page
    assert "availability varies by trial" in page
    assert "No trial is represented as having every optional artifact" in page
    assert "private model reasoning is not exposed" in page
    assert 'href="/artifacts"' in page
    assert 'href="/trial-quality"' in page

    assert "supervise_live=true" in page
    assert "Wraps the benchmark command with" in page
    assert "Shared live database" in page
    assert "depends on configured credentials" in page
    assert "neither scores nor changes Harbor" in page
    assert "supervise_live=false" in page
    assert "without <code>scripts/run_arm_live.py</code> supervision" in page
    assert "A separately requested final" in page
    assert "progressive_artifacts=true" in page
    assert "requires both <code>supervise_live=true</code> and <code>publish_results=true</code>" in page
    assert "publish_results=true" in page
    assert "whether or not live supervision was enabled" in page
    assert "Current workflow_dispatch defaults" in page
    assert "publish_results=false" in page
    assert "does not mean canonical publication is globally disabled" in page

    assert "is the workflow final canonical publisher" in page
    assert "discovers the eligible final Harbor result directory" in page
    assert "eligibility and path-safety checks" in page
    assert "ingestion-manifest functionality" in page
    assert "live database spool and progressive-artifact evidence" in page
    assert "verifies checksum, size, and object integrity" in page
    assert "transaction/rollback verification use one transaction" in page
    assert "Final counts and" in page
    assert "applicable live run is linked to its canonical arm run" in page
    assert "Final publication without live supervision is supported" in page
    assert 'href="/data-model"' in page


def test_dr014_data_model_page_and_diagram_share_audited_relationships() -> None:
    page_path = Path("apps/dashboard/src/app/data-model/page.tsx")
    diagram_path = Path("docs/diagrams/DASHBOARD_DATA_MODEL_20260812.mmd")
    page = page_path.read_text()
    diagram = diagram_path.read_text()
    shell = Path("apps/dashboard/src/components/AppShell.tsx").read_text()
    css = Path("apps/dashboard/src/app/globals.css").read_text()

    assert page_path.is_file()
    assert diagram_path.is_file()
    assert '{ href: "/data-model", label: "Data Model" }' in shell
    assert shell.index('{ href: "/architecture"') < shell.index('{ href: "/data-model"') < shell.index('{ href: "/glossary"')
    assert '{ href: "/runners"' not in shell
    assert '{ href: "/readiness"' not in shell
    assert "not a live schema inspector" in page
    assert "without querying Supabase or R2" in page

    for relation in (
        "benchmark.live_runs",
        "benchmark.live_run_events",
        "benchmark.live_trials",
        "benchmark.live_artifacts",
        "benchmark.benchmark_runs",
        "benchmark.benchmark_arms",
        "benchmark.benchmark_tasks",
        "benchmark.benchmark_trials",
        "benchmark.benchmark_artifacts",
        "benchmark.benchmark_eval_suites",
        "benchmark.benchmark_eval_suite_items",
        "benchmark.benchmark_arm_runs",
    ):
        assert relation in page
        assert relation in diagram

    relationship_pairs = (
        ("live_run_events.live_run_id", "live_runs.live_run_id"),
        ("live_trials.live_run_id", "live_runs.live_run_id"),
        ("live_artifacts.live_run_id", "live_runs.live_run_id"),
        ("live_runs.canonical_arm_run_id", "benchmark_arm_runs.id"),
        ("benchmark_arm_runs.run_id", "benchmark_runs.id"),
        ("benchmark_arm_runs.arm_id", "benchmark_arms.arm_id"),
        ("benchmark_arm_runs.suite_id", "benchmark_eval_suites.suite_id"),
        ("benchmark_trials.run_id", "benchmark_runs.id"),
        ("benchmark_trials.arm_id", "benchmark_arms.arm_id"),
        ("benchmark_trials.task_id", "benchmark_tasks.task_id"),
        ("benchmark_trials.arm_run_id", "benchmark_arm_runs.id"),
        ("benchmark_artifacts.run_id", "benchmark_runs.id"),
        ("benchmark_artifacts.trial_id", "benchmark_trials.id"),
    )
    for child, parent in relationship_pairs:
        assert child in page
        assert parent in page
        assert f"{child} references {parent}" in diagram

    assert "the only direct live-to-canonical foreign key" in page
    assert "only direct live-to-canonical FK" in diagram
    assert "There is no direct" in page
    assert "per-trial or per-artifact canonical foreign key" in page
    assert "LTRIAL -->" in diagram
    assert "LART -->" in diagram
    assert "LTRIAL --> BTRIAL" not in diagram
    assert "LART --> BART" not in diagram
    assert "live_trials.trial_id references benchmark_trials.id" not in page + diagram
    assert "live_artifacts.artifact_id references benchmark_artifacts.id" not in page + diagram

    for relation in (
        "benchmark.benchmark_invalid_arm_runs",
        "benchmark.v_valid_arm_run_summary",
        "benchmark.v_valid_suite_arm_comparison",
        "benchmark.v_valid_eval_arm_comparison",
        "benchmark.v_valid_suite_arm_quality_summary",
        "benchmark.v_trial_quality_flags",
        "benchmark.v_arm_run_quality_summary",
        "benchmark.v_arm_run_summary",
        "benchmark.v_arm_run_trials",
        "benchmark.v_dashboard_runs",
        "benchmark.v_dashboard_arms",
        "benchmark.v_dashboard_tasks",
        "benchmark.benchmark_trial_cost_coverage",
        "benchmark.v_trial_adjusted_cost_coverage",
        "benchmark.v_arm_outcome_cost_breakdown",
        "benchmark.v_suite_adjusted_cost_frontier",
    ):
        assert relation in page
    assert "not a second source of benchmark truth" in page

    assert "live_artifacts.r2_uri" in page
    assert "benchmark_artifacts.r2_uri" in page
    assert "storage references, not database foreign keys" in page
    assert "does not prove" in page
    assert "bytes were retrieved, complete, or verified against recorded hash and size" in page
    assert "r2_uri storage reference, not FK" in diagram
    assert "F1 reviewed Phase 3 comparison snapshot" in page
    assert "G1 reviewed run-selection snapshot" in page
    assert "not silently refreshed from newer stored evidence" in page
    for consumer in (
        "/runs/live",
        "/live-artifacts/[artifactId]",
        "/runs",
        "/artifacts",
        "/trials/[trialId]",
        "/arms",
        "/eval-suites",
        "/evals",
        "/trial-quality",
        "/cross-phase",
        "/cost-coverage",
        "/comprehensive-review",
    ):
        assert consumer in page
    assert "semantic HTML below" in page
    assert "accessible text equivalent" in page
    assert "DASHBOARD_DATA_MODEL_20260812.mmd" in page
    assert 'href="/architecture"' in page
    assert 'href="/glossary"' in page
    assert ".data-model-layer-body" in css
    assert "grid-template-columns: repeat(auto-fit" in css
    assert "@media (max-width: 1100px)" in css
    assert ".data-model-snapshot-list li" in css
    assert "overflow-wrap: anywhere" in css


def test_dr015_glossary_related_links_reuse_typed_registry_and_term_info() -> None:
    glossary = Path("apps/dashboard/src/lib/glossary.ts").read_text()
    page = Path("apps/dashboard/src/app/glossary/page.tsx").read_text()
    term_info = Path("apps/dashboard/src/components/TermInfo.tsx").read_text()

    assert "links?: readonly" in glossary
    assert "href: string;" in glossary
    assert "label: string;" in glossary
    assert 'export type GlossaryTerm = (typeof glossaryEntries)[number]["term"]' in glossary
    assert "as const satisfies readonly GlossaryEntry[]" in glossary
    assert "dangerouslySetInnerHTML" not in glossary + page + term_info

    linked_terms = {
        "Arm": ('href: "/arms"', "Open Arms"),
        "Arm run": ('href: "/runs"', "Open Runs"),
        "Eval": ('href: "/evals"', "Open Evals"),
        "Eval suite": ('href: "/eval-suites"', "Open Eval Suites"),
        "Trial": ('href: "/trial-quality"', "Open Trial Quality"),
        "R2 artifact": ('href: "/artifacts"', "Open Artifacts"),
        "Trajectory": ('href: "/artifacts"', "Open Artifacts"),
        "Benchmark run class": ('href: "/runs"', "Open Runs"),
        "Result source/storage location": ('href: "/data-model"', "Open Data Model"),
        "Recorded cost": ('href: "/cost-coverage"', "Open Cost Coverage"),
        "Adjusted known cost": ('href: "/cost-coverage"', "Open Cost Coverage"),
        "Known accounting gap": ('href: "/cost-coverage"', "Open Cost Coverage"),
        "Failure/incomplete spend": ('href: "/cost-coverage"', "Open Cost Coverage"),
        "Cost per clean success": ('href: "/"', "Open Overview Chart"),
    }
    for term, (href, label) in linked_terms.items():
        entry = glossary.split(f'term: "{term}"', 1)[1].split("  },", 1)[0]
        assert href in entry
        assert label in entry

    href_lines = [line for line in glossary.splitlines() if "href:" in line and "href: string" not in line]
    assert href_lines
    assert all("?" not in line and "#" not in line for line in href_lines)
    assert 'className="glossary-related-links"' in page
    assert "aria-label={`Related pages for ${entry.term}`}" in page
    assert "{link.label} →" in page
    assert "entry.links?.[0]" in term_info
    assert "{entry.links[0].label} →" in term_info
    assert "Glossary →" in term_info
    assert "createPortal" in term_info
    assert 'event.key === "Escape"' in term_info
    assert "onFocus={clearCloseTimer}" in term_info
    assert "onBlur={scheduleClose}" in term_info
    assert "aria-expanded={open}" in term_info

    logical_mode = glossary.split('term: "Logical mode"', 1)[1].split("  },", 1)[0]
    storage_mode = glossary.split('term: "Storage mode"', 1)[1].split("  },", 1)[0]
    assert "internal field" in logical_mode
    assert "public primary label" in logical_mode
    assert "Benchmark run class" in logical_mode
    assert "internal field" in storage_mode
    assert "public Result source/storage location label" in storage_mode


def test_architecture_glossary_uses_public_terms_and_retains_internal_compatibility() -> None:
    page = Path("apps/dashboard/src/app/architecture/page.tsx").read_text()
    glossary = Path("apps/dashboard/src/lib/glossary.ts").read_text()
    css = Path("apps/dashboard/src/app/globals.css").read_text()
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
    assert 'className="concept-grid architecture-terminology-grid"' in page
    assert page.count('className="term-label architecture-terminology-label"') == 4
    assert page.count('className="architecture-terminology-text"') == 4
    assert ".architecture-terminology-label" in css
    assert ".architecture-terminology-text" in css
    assert "white-space: normal;" in css
    assert "overflow-wrap: anywhere;" in css
    assert ".architecture-terminology-label .term-info-wrap" in css
    assert "flex: 0 0 auto;" in css


def test_j2c_failure_taxonomy_loader_is_manifest_bound_and_fail_closed() -> None:
    import re

    loader = Path("apps/dashboard/src/lib/failure-taxonomy-snapshot.ts").read_text()
    package = Path("apps/dashboard/package.json").read_text()
    next_config = Path("apps/dashboard/next.config.mjs").read_text()

    assert 'SNAPSHOT_SCHEMA_VERSION = "failure-taxonomy-manifest-v1"' in loader
    assert 'import "server-only"' in loader
    assert 'FROZEN_CANONICAL_MANIFEST_SHA256 = "71e1c0fbee99d07fe18512902ed62c3fa2eb752d9e08c68c3d75a1dc1a4e3088"' in loader
    assert "canonical_manifest_hash_mismatch" in loader
    assert "FROZEN_CLASSIFICATION_OUTPUT_SHA256" in loader
    assert "frozen_output_identity_mismatch" in loader
    assert 'TRIAL_SCHEMA_VERSION = "failure-taxonomy-trial-v1"' in loader
    assert 'SNAPSHOT_SCOPE = "phase3-extended"' in loader
    assert "EXPECTED_TRIAL_COUNT = 960" in loader
    assert "EXPECTED_ARM_COUNT = 16" in loader
    assert 'path.join(directory, "failure_taxonomy_manifest.json")' in loader
    assert "output_hash_or_size_mismatch" in loader
    assert "registry_binding_mismatch" in loader
    assert "review_scope_or_schema_mismatch" in loader
    assert "implementation_binding_mismatch" in loader
    assert "frozen_trial_set_mismatch" in loader
    assert "frozen_trial_set_fingerprint_mismatch" in loader
    assert "review_queue_union_mismatch" in loader
    assert "taxonomy_artifact_not_bound_to_trial_evidence" in loader
    assert "byTrialId.get(trialId)" in loader
    assert "reviewById.get(row.trial_id)" in loader
    assert "outside_frozen_scope" in loader
    assert "not the taxonomy value ‘Not applicable’" in loader
    assert "rows: []" in loader
    assert 'state === "invalid" ? "snapshot_invalid"' in loader
    imports = re.findall(r'from\s+["\']([^"\']+)["\']', loader)
    for forbidden in ("./db", "dashboard-data", "@aws-sdk", "node:http", "failure_taxonomy_classifier"):
        assert all(forbidden not in specifier for specifier in imports)
    assert "failure-taxonomy-snapshot.test.mjs" in package
    assert 'new URL("../..", import.meta.url)' in next_config
    assert "outputFileTracingRoot: repositoryRoot" in next_config
    assert '"/trial-quality": failureTaxonomyRuntimeFiles' in next_config
    assert '"/trials/**": failureTaxonomyRuntimeFiles' in next_config
    assert "turbopack:" not in next_config
    assert "root: repositoryRoot" not in next_config
    for required_runtime_file in (
        "../../configs/dashboard/failure_taxonomy_v1.json",
        "../../results/manual_verification/failure_taxonomy_20260813/failure_taxonomy_manifest.json",
        "../../results/manual_verification/failure_taxonomy_20260813/trial_failure_taxonomy.jsonl",
        "../../results/manual_verification/failure_taxonomy_20260813/taxonomy_counts.json",
        "../../results/manual_verification/failure_taxonomy_20260813/review_queue.csv",
        "../../results/manual_verification/failure_taxonomy_20260813/README.md",
        "../../results/manual_verification/comprehensive_review_20260731/review_manifest.json",
        "../../results/manual_verification/comprehensive_review_20260731/trial_review.csv",
        "../../results/manual_verification/comprehensive_review_20260731/trial_evidence.jsonl",
        "../../scripts/lib/failure_taxonomy_classifier.py",
        "../../scripts/generate_failure_taxonomy_snapshot.py",
    ):
        assert required_runtime_file in next_config


def test_j2c_trial_quality_uses_exact_registry_filters_and_frozen_details() -> None:
    page = Path("apps/dashboard/src/app/trial-quality/page.tsx").read_text()
    detail_page = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    component = Path("apps/dashboard/src/components/FailureTaxonomyDetails.tsx").read_text()
    css = Path("apps/dashboard/src/app/globals.css").read_text()

    assert "getFailureTaxonomyReviewedSource()" in page
    assert "normalizeFailureTaxonomyFilters(rawTaxonomyFilters)" in page
    assert 'name={axisId}' in page
    assert 'value={entry.id}' in page
    assert "Apply exact filters" in page
    assert "Filters accept only canonical registry IDs" in page
    assert "getFailureTaxonomyAxis(axisId)" in page
    assert "axis.definition" in page
    assert "entry.definition" in page
    assert "FailureTaxonomyCompactDiagnosis" in page
    assert "no operational source is substituted" in page
    assert "Legacy suspect no-op zero-token compatibility rows" in page
    assert "not a primary J2 failure or trajectory diagnosis" in page

    assert "getFailureTaxonomyForTrial(decodedTrialId)" in detail_page
    assert "<FailureTaxonomyDetails result={failureTaxonomy} />" in detail_page
    assert "FAILURE_TAXONOMY_AXIS_IDS.map" in component
    assert "diagnosis.label" in component
    assert "diagnosis.definition" in component
    assert "diagnosis.confidence" in component
    assert "diagnosis.manual_review_required" in component
    assert "diagnosis.evidence_basis.map" in component
    assert "diagnosis.supporting_artifact_ids.map" in component
    assert '`/artifacts/${encodeURIComponent(artifactId)}`' in component
    assert "No database, live artifact, or browser-side classification is used as a fallback" in component
    assert "does not retain or infer hidden/private reasoning" in component
    assert "manifest verified" in component
    assert ".taxonomy-filter-grid" in css
    assert ".taxonomy-axis-detail-grid" in css
    assert ".taxonomy-table" in css


def test_j2d_trial_detail_keeps_operational_live_analysis_separate_from_j2() -> None:
    detail_page = Path("apps/dashboard/src/app/trials/[trialId]/page.tsx").read_text()
    taxonomy_component = Path("apps/dashboard/src/components/FailureTaxonomyDetails.tsx").read_text()
    live_sources = Path("apps/dashboard/src/lib/data-freshness-sources.ts").read_text()

    assert '"live fallback"' not in detail_page
    assert '"operational live analysis"' in detail_page
    assert "This operational live analysis is separate from the frozen J2 taxonomy" in detail_page
    assert "does not fill or replace an unavailable J2 diagnosis" in detail_page
    assert "showing bounded operational live analysis" in detail_page
    assert "No database, live artifact, or browser-side classification is used as a fallback" in taxonomy_component
    assert 'sourceKind: "cloud_operational" | "local_fallback"' in live_sources


def test_j2c_frozen_classification_outputs_retain_accepted_hashes() -> None:
    import hashlib

    snapshot = Path("results/manual_verification/failure_taxonomy_20260813")
    expected = {
        "trial_failure_taxonomy.jsonl": "ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1",
        "taxonomy_counts.json": "e1284625f3e48e2dcb69a569acb0e73ff326410ffd8b9bc8878cfe5b8863e9cd",
        "review_queue.csv": "aeb8eab2037ce5dd11bb0ef94cda4e0c28013b9c2d887aecdf129d77ea78e883",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((snapshot / name).read_bytes()).hexdigest() == digest
