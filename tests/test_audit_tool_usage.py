from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_tool_usage import audit_roots


def write_line(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) + "\n", encoding="utf-8")


def test_init_web_tools_available_is_not_actual_usage(tmp_path: Path) -> None:
    transcript = tmp_path / "claude-code.txt"
    write_line(
        transcript,
        {
            "type": "system",
            "subtype": "init",
            "tools": ["Bash", "Read", "WebFetch", "WebSearch"],
        },
    )

    report = audit_roots([tmp_path])

    assert report.actual_events == []
    assert len(report.init_availability_events) == 2
    assert {event.tool for event in report.init_availability_events} == {"WebFetch", "WebSearch"}


def test_actual_websearch_tool_use_is_detected_in_jsonl(tmp_path: Path) -> None:
    session = tmp_path / "agent" / "sessions" / "projects" / "-app" / "session.jsonl"
    write_line(
        session,
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "WebSearch",
                        "input": {"query": "benchmark answer"},
                    }
                ]
            },
        },
    )

    report = audit_roots([tmp_path])

    assert len(report.actual_events) == 1
    assert report.actual_events[0].tool == "WebSearch"


def test_actual_webfetch_tool_use_is_detected_in_trajectory_json(tmp_path: Path) -> None:
    trajectory = tmp_path / "trajectory.json"
    trajectory.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "source": "agent",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "WebFetch",
                                    "input": {"url": "https://example.com"},
                                }
                            ]
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = audit_roots([tmp_path])

    assert len(report.actual_events) == 1
    assert report.actual_events[0].tool == "WebFetch"


def test_non_web_tool_use_is_ignored(tmp_path: Path) -> None:
    transcript = tmp_path / "claude-code.txt"
    write_line(
        transcript,
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pytest -q"},
                    }
                ]
            },
        },
    )

    report = audit_roots([tmp_path])

    assert report.actual_events == []
    assert report.init_availability_events == []


def test_init_availability_can_be_failed_by_policy(tmp_path: Path) -> None:
    transcript = tmp_path / "claude-code.txt"
    write_line(
        transcript,
        {
            "type": "system",
            "subtype": "init",
            "tools": ["Bash", "Read", "WebFetch"],
        },
    )

    report = audit_roots([tmp_path])

    assert len(report.actual_events) == 0
    assert len(report.init_availability_events) == 1
    assert report.init_availability_events[0].tool == "WebFetch"
