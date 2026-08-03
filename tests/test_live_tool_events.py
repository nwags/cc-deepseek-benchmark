from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.live_tool_events import (
    IncrementalToolEventParser,
    load_seen_tool_event_ids,
)
from scripts.lib.path_safety import PathBoundaryError


def append_jsonl(path: Path, value: object, *, newline: bool = True) -> None:
    encoded = json.dumps(value)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        if newline:
            handle.write("\n")


def assistant_tool(tool_id: str, name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "type": "assistant",
        "timestamp": "2026-07-31T02:05:36Z",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": name,
                    "input": arguments,
                }
            ]
        },
    }


def user_result(tool_id: str, content: str, *, is_error: bool = False) -> dict[str, object]:
    return {
        "type": "user",
        "timestamp": "2026-07-31T02:05:37Z",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": content,
                    "is_error": is_error,
                }
            ]
        },
    }


def make_trial(tmp_path: Path) -> tuple[Path, Path, Path]:
    trial = tmp_path / "results" / "run" / "task-one__abc"
    agent = trial / "agent"
    agent.mkdir(parents=True)
    transcript = agent / "claude-code.txt"
    transcript.touch()
    return trial, agent, transcript


def test_transcript_emits_explicit_tool_lifecycle_without_reasoning_or_content(
    tmp_path: Path,
) -> None:
    trial, _agent, transcript = make_trial(tmp_path)
    append_jsonl(
        transcript,
        assistant_tool(
            "call-1",
            "Write",
            {"file_path": "/app/out.py", "content": "sensitive body"},
        ),
    )
    append_jsonl(
        transcript,
        user_result("call-1", "created file\npassword=not-for-live-output"),
    )

    parser = IncrementalToolEventParser()
    events = parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    )

    assert [event.event_type for event in events] == [
        "tool_call_started",
        "tool_result",
        "tool_call_finished",
    ]
    assert events[0].payload["tool_name"] == "Write"
    assert events[0].payload["safe_arguments"]["content"] == "<14 chars>"
    serialized = json.dumps([event.payload for event in events])
    assert "sensitive body" not in serialized
    assert "not-for-live-output" not in serialized
    assert "created file" in events[1].message
    assert parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    ) == []


def test_thinking_blocks_are_ignored(tmp_path: Path) -> None:
    trial, _agent, transcript = make_trial(tmp_path)
    append_jsonl(
        transcript,
        {
            "type": "assistant",
            "timestamp": "2026-07-31T02:05:36Z",
            "message": {
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "PRIVATE-REASONING-SENTINEL",
                    },
                    {
                        "type": "tool_use",
                        "id": "call-thinking",
                        "name": "Read",
                        "input": {"file_path": "/app/input.txt"},
                    },
                ]
            },
        },
    )

    parser = IncrementalToolEventParser()
    events = parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    )

    assert [event.event_type for event in events] == ["tool_call_started"]
    serialized = json.dumps(
        [
            {"message": event.message, "payload": event.payload}
            for event in events
        ]
    )
    assert "PRIVATE-REASONING-SENTINEL" not in serialized


def test_failed_tool_result_emits_failed_result_and_finish(
    tmp_path: Path,
) -> None:
    trial, _agent, transcript = make_trial(tmp_path)
    append_jsonl(
        transcript,
        assistant_tool(
            "call-failed",
            "Bash",
            {"command": "python /app/missing.py"},
        ),
    )
    append_jsonl(
        transcript,
        user_result(
            "call-failed",
            "command failed",
            is_error=True,
        ),
    )

    parser = IncrementalToolEventParser()
    events = parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    )

    assert [event.event_type for event in events] == [
        "tool_call_started",
        "tool_result",
        "tool_call_finished",
    ]
    assert [event.payload["status"] for event in events] == [
        "running",
        "failed",
        "failed",
    ]


def test_partial_jsonl_line_waits_for_completion(tmp_path: Path) -> None:
    trial, _agent, transcript = make_trial(tmp_path)
    record = json.dumps(assistant_tool("call-partial", "Read", {"file_path": "/app/x"}))
    midpoint = len(record) // 2
    transcript.write_text(record[:midpoint], encoding="utf-8")

    parser = IncrementalToolEventParser()
    assert parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    ) == []

    with transcript.open("a", encoding="utf-8") as handle:
        handle.write(record[midpoint:] + "\n")
    events = parser.scan_trial(
        trial,
        trial_key=trial.name,
        workspace=tmp_path,
    )
    assert [event.event_type for event in events] == ["tool_call_started"]


def test_final_trajectory_backfills_missing_calls_and_deduplicates_transcript(
    tmp_path: Path,
) -> None:
    trial, agent, transcript = make_trial(tmp_path)
    append_jsonl(transcript, assistant_tool("call-1", "Read", {"file_path": "/app/a"}))
    append_jsonl(transcript, user_result("call-1", "ok"))
    parser = IncrementalToolEventParser()
    first = parser.scan_trial(trial, trial_key=trial.name, workspace=tmp_path)
    assert len(first) == 3

    trajectory = {
        "schema_version": "ATIF-v1.2",
        "steps": [
            {
                "timestamp": "2026-07-31T02:05:36Z",
                "tool_calls": [
                    {
                        "tool_call_id": "call-1",
                        "function_name": "Read",
                        "arguments": {"file_path": "/app/a"},
                    },
                    {
                        "tool_call_id": "call-2",
                        "function_name": "Bash",
                        "arguments": {"command": "python /app/a"},
                    },
                ],
                "observation": {
                    "results": [
                        {"source_call_id": "call-1", "content": "ok"},
                        {"source_call_id": "call-2", "content": "done"},
                    ]
                },
            }
        ],
    }
    (agent / "trajectory.json").write_text(json.dumps(trajectory), encoding="utf-8")
    second = parser.scan_trial(trial, trial_key=trial.name, workspace=tmp_path)
    assert [event.event_type for event in second] == [
        "tool_call_started",
        "tool_result",
        "tool_call_finished",
    ]
    assert {event.payload["tool_call_id"] for event in second} == {"call-2"}


def test_tool_source_symlink_escape_is_rejected(tmp_path: Path) -> None:
    trial = tmp_path / "results" / "run" / "task-one__abc"
    trial.mkdir(parents=True)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-agent"
    outside.mkdir()
    (trial / "agent").symlink_to(outside, target_is_directory=True)

    parser = IncrementalToolEventParser()
    with pytest.raises(PathBoundaryError):
        parser.scan_trial(trial, trial_key=trial.name, workspace=tmp_path)


def test_seen_event_ids_are_recovered_from_local_ndjson(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_path = tmp_path / "events.ndjson"
    event_path.write_text(
        json.dumps(
            {
                "event_type": "tool_call_started",
                "payload": {"tool_event_id": "stable-id"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def fail_read_text(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("restart recovery must stream instead of read_text")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    assert load_seen_tool_event_ids(event_path) == {"stable-id"}
