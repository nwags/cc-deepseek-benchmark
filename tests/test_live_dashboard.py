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
    assert "event_type not in ('process_output_chunk', 'agent_output_chunk')" in data
