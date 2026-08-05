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
    assert 'role="alert"' in notice
    assert "not a full-suite leaderboard denominator" in notice
    assert "corpus-scopes.test.mjs" in package


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

    assert 'scopeId="phase3-core"' in cross_phase
    assert "getCorpusScopePresentationLabel" in cross_phase
    assert "Historical comparison provenance" in cross_phase
    assert "July 13 adjusted-cost comparison" in cross_phase

    assert 'scopeId="all-imported"' in arms
    assert "All imported" in arms
    assert "not a valid full-suite leaderboard denominator" in arms

    assert 'scopeId="valid-imported"' in evals
    assert "Valid imported inventory" in evals
    assert "Invalid and quarantined arm runs are excluded" in evals
    assert "not a fixed full-suite leaderboard denominator" in evals
    assert "from benchmark.v_valid_eval_arm_comparison" in data

    assert 'scopeId="phase3-core"' in cost
    assert 'getCorpusScope("phase3-core")' in cost
    assert "Reviewed adjusted-cost coverage layer" in cost
    assert "intentionally does not synthesize an extended adjusted-cost total" in cost
    assert "sponsor-facing" not in cost
    for source in (cross_phase, cost):
        assert "15 arms / 900 trials / 515 successes" not in source
        assert "$972.17" not in source
        assert "Kimi K3 is not included" not in source


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
