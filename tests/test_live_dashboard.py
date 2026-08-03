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
