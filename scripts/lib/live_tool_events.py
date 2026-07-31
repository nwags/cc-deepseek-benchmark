from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from scripts.lib.path_safety import PathBoundaryError, resolve_under


MAX_TRANSCRIPT_READ_BYTES = 2 * 1024 * 1024
MAX_TRANSCRIPT_BUFFER_BYTES = 16 * 1024 * 1024
MAX_TRAJECTORY_BYTES = 32 * 1024 * 1024
MAX_SUMMARY_CHARS = 500
TOOL_EVENT_TYPES = frozenset(
    {"tool_call_started", "tool_result", "tool_call_finished"}
)
CONTENT_ARGUMENT_KEYS = frozenset(
    {
        "content",
        "new_string",
        "old_string",
        "prompt",
        "instructions",
        "notebook_cell_source",
    }
)


@dataclass(frozen=True)
class ToolLifecycleEvent:
    event_type: str
    message: str
    payload: dict[str, Any]


@dataclass
class FileCursor:
    inode: int
    offset: int = 0
    pending: bytes = b""


def _event_id(trial_key: str, tool_call_id: str, phase: str) -> str:
    value = f"{trial_key}\0{tool_call_id}\0{phase}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:32]


def _truncate(value: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: max(limit - 16, 0)] + "...[truncated]"


def _safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or "/"
        return _truncate(f"{parsed.scheme}://{host}{port}{path}")
    except ValueError:
        return "<url>"


def _value_shape(value: Any) -> str:
    if isinstance(value, str):
        return f"<{len(value)} chars>"
    if isinstance(value, Mapping):
        return f"<{len(value)} keys>"
    if isinstance(value, (list, tuple, set)):
        return f"<{len(value)} items>"
    return f"<{type(value).__name__}>"


def summarize_tool_arguments(arguments: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(arguments, Mapping):
        return "no structured arguments", {}

    safe: dict[str, Any] = {}
    for raw_key, value in arguments.items():
        key = str(raw_key)
        lower = key.lower()
        if lower in CONTENT_ARGUMENT_KEYS:
            safe[key] = _value_shape(value)
        elif lower in {
            "file_path",
            "path",
            "notebook_path",
            "pattern",
            "query",
            "description",
            "subagent_type",
        }:
            safe[key] = _truncate(str(value), 300)
        elif lower in {"command", "cmd"}:
            safe[key] = _truncate(str(value), 400)
        elif lower == "url":
            safe[key] = _safe_url(str(value))
        elif value is None or isinstance(value, (bool, int, float)):
            safe[key] = value
        else:
            safe[key] = _value_shape(value)

    rendered = ", ".join(f"{key}={value}" for key, value in safe.items())
    return (_truncate(rendered) if rendered else "no arguments"), safe


def summarize_tool_result(content: Any) -> tuple[str, int]:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, Mapping):
                continue
            value = item.get("text") or item.get("content")
            if isinstance(value, str):
                parts.append(value)
        text = "\n".join(parts)
    elif content is None:
        return "empty result", 0
    else:
        return _value_shape(content), 0

    first_line = next(
        (line.strip() for line in text.splitlines() if line.strip()),
        "empty result",
    )
    summary = _truncate(first_line, 240)
    if len(text) > len(first_line):
        summary = f"{summary} ({len(text)} chars)"
    return summary, len(text)


def _result_is_error(
    block: Mapping[str, Any],
    record: Mapping[str, Any],
) -> bool:
    tool_use_result = record.get("tool_use_result")
    values = [block.get("is_error"), record.get("is_error")]
    if isinstance(tool_use_result, Mapping):
        values.append(tool_use_result.get("is_error"))
    return any(value is True for value in values)


def _content_blocks(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    message = record.get("message")
    if not isinstance(message, Mapping):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, Mapping)]


class IncrementalToolEventParser:
    """Tail Claude Code JSONL and reconcile final ATIF trajectories.

    Only tool-use and tool-result records are emitted. Thinking/reasoning blocks are
    intentionally ignored. Event ids are deterministic so transcript and trajectory
    observations of the same call collapse to one lifecycle.
    """

    def __init__(self, *, seen_event_ids: Iterable[str] = ()) -> None:
        self._seen_event_ids = {str(value) for value in seen_event_ids if value}
        self._cursors: dict[Path, FileCursor] = {}
        self._trajectory_signatures: dict[Path, tuple[int, int]] = {}
        self._tool_names: dict[tuple[str, str], str] = {}

    @property
    def seen_event_ids(self) -> frozenset[str]:
        return frozenset(self._seen_event_ids)

    def scan_trial(
        self,
        trial_dir: Path,
        *,
        trial_key: str,
        workspace: Path,
    ) -> list[ToolLifecycleEvent]:
        agent_dir = self._existing_directory(
            trial_dir / "agent",
            parent=trial_dir,
            workspace=workspace,
        )
        if agent_dir is None:
            return []

        workspace_resolved = workspace.resolve(strict=True)
        events: list[ToolLifecycleEvent] = []
        transcript = self._existing_file(
            agent_dir / "claude-code.txt",
            parent=agent_dir,
            workspace=workspace,
        )
        if transcript is not None:
            source_path = transcript.relative_to(workspace_resolved).as_posix()
            for record in self._new_jsonl_records(transcript):
                events.extend(
                    self._events_from_record(
                        record,
                        trial_key=trial_key,
                        source_path=source_path,
                        source_kind="transcript",
                    )
                )

        trajectory = self._existing_file(
            agent_dir / "trajectory.json",
            parent=agent_dir,
            workspace=workspace,
        )
        if trajectory is not None:
            events.extend(
                self._events_from_trajectory(
                    trajectory,
                    trial_key=trial_key,
                    workspace=workspace,
                )
            )
        return events

    @staticmethod
    def _existing_directory(
        path: Path,
        *,
        parent: Path,
        workspace: Path,
    ) -> Path | None:
        if path.is_symlink():
            raise PathBoundaryError("live tool source directory must not be a symbolic link")
        if not path.exists():
            return None
        return resolve_under(
            path,
            workspace=workspace,
            parent=parent,
            require_directory=True,
            label="live tool source directory",
        )

    @staticmethod
    def _existing_file(
        path: Path,
        *,
        parent: Path,
        workspace: Path,
    ) -> Path | None:
        if path.is_symlink():
            raise PathBoundaryError("live tool source must not be a symbolic link")
        if not path.exists():
            return None
        return resolve_under(
            path,
            workspace=workspace,
            parent=parent,
            require_file=True,
            label="live tool source",
        )

    def _new_jsonl_records(self, path: Path) -> list[Mapping[str, Any]]:
        stat = path.stat()
        cursor = self._cursors.get(path)
        if cursor is None or cursor.inode != stat.st_ino or stat.st_size < cursor.offset:
            cursor = FileCursor(inode=stat.st_ino)
            self._cursors[path] = cursor

        with path.open("rb") as handle:
            handle.seek(cursor.offset)
            data = handle.read(MAX_TRANSCRIPT_READ_BYTES)
        if not data:
            return []
        cursor.offset += len(data)
        combined = cursor.pending + data
        parts = combined.split(b"\n")
        if combined.endswith(b"\n"):
            complete, cursor.pending = parts[:-1], b""
        else:
            complete, cursor.pending = parts[:-1], parts[-1]
        if len(cursor.pending) > MAX_TRANSCRIPT_BUFFER_BYTES:
            cursor.pending = b""

        records: list[Mapping[str, Any]] = []
        for line in complete:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, Mapping):
                records.append(value)
        return records

    def _events_from_record(
        self,
        record: Mapping[str, Any],
        *,
        trial_key: str,
        source_path: str,
        source_kind: str,
    ) -> list[ToolLifecycleEvent]:
        events: list[ToolLifecycleEvent] = []
        source_timestamp = record.get("timestamp")
        for block in _content_blocks(record):
            block_type = block.get("type")
            if block_type == "tool_use":
                tool_call_id = str(block.get("id") or "").strip()
                tool_name = str(block.get("name") or "unknown").strip() or "unknown"
                if not tool_call_id:
                    continue
                self._tool_names[(trial_key, tool_call_id)] = tool_name
                input_summary, safe_arguments = summarize_tool_arguments(block.get("input"))
                event = self._started_event(
                    trial_key=trial_key,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    input_summary=input_summary,
                    safe_arguments=safe_arguments,
                    source_path=source_path,
                    source_kind=source_kind,
                    source_timestamp=source_timestamp,
                )
                if event is not None:
                    events.append(event)
            elif block_type == "tool_result":
                tool_call_id = str(block.get("tool_use_id") or "").strip()
                if not tool_call_id:
                    continue
                tool_name = self._tool_names.get((trial_key, tool_call_id), "unknown")
                result_summary, result_chars = summarize_tool_result(block.get("content"))
                events.extend(
                    self._result_events(
                        trial_key=trial_key,
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        result_summary=result_summary,
                        result_chars=result_chars,
                        is_error=_result_is_error(block, record),
                        source_path=source_path,
                        source_kind=source_kind,
                        source_timestamp=source_timestamp,
                    )
                )
        return events

    def _events_from_trajectory(
        self,
        path: Path,
        *,
        trial_key: str,
        workspace: Path,
    ) -> list[ToolLifecycleEvent]:
        stat = path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        if self._trajectory_signatures.get(path) == signature:
            return []
        if stat.st_size > MAX_TRAJECTORY_BYTES:
            self._trajectory_signatures[path] = signature
            return []
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []
        if not isinstance(document, Mapping) or not isinstance(document.get("steps"), list):
            return []
        self._trajectory_signatures[path] = signature

        source_path = path.relative_to(workspace.resolve(strict=True)).as_posix()
        events: list[ToolLifecycleEvent] = []
        for step in document["steps"]:
            if not isinstance(step, Mapping):
                continue
            source_timestamp = step.get("timestamp")
            calls = step.get("tool_calls")
            if isinstance(calls, list):
                for call in calls:
                    if not isinstance(call, Mapping):
                        continue
                    tool_call_id = str(
                        call.get("tool_call_id") or call.get("id") or ""
                    ).strip()
                    tool_name = str(
                        call.get("function_name") or call.get("name") or "unknown"
                    ).strip() or "unknown"
                    if not tool_call_id:
                        continue
                    self._tool_names[(trial_key, tool_call_id)] = tool_name
                    input_summary, safe_arguments = summarize_tool_arguments(
                        call.get("arguments") or call.get("input")
                    )
                    event = self._started_event(
                        trial_key=trial_key,
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        input_summary=input_summary,
                        safe_arguments=safe_arguments,
                        source_path=source_path,
                        source_kind="trajectory",
                        source_timestamp=source_timestamp,
                    )
                    if event is not None:
                        events.append(event)

            observation = step.get("observation")
            results = (
                observation.get("results")
                if isinstance(observation, Mapping)
                else None
            )
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, Mapping):
                    continue
                tool_call_id = str(
                    result.get("source_call_id")
                    or result.get("tool_use_id")
                    or ""
                ).strip()
                if not tool_call_id:
                    continue
                tool_name = self._tool_names.get((trial_key, tool_call_id), "unknown")
                result_summary, result_chars = summarize_tool_result(result.get("content"))
                events.extend(
                    self._result_events(
                        trial_key=trial_key,
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        result_summary=result_summary,
                        result_chars=result_chars,
                        is_error=result.get("is_error") is True,
                        source_path=source_path,
                        source_kind="trajectory",
                        source_timestamp=source_timestamp,
                    )
                )
        return events

    def _started_event(
        self,
        *,
        trial_key: str,
        tool_call_id: str,
        tool_name: str,
        input_summary: str,
        safe_arguments: Mapping[str, Any],
        source_path: str,
        source_kind: str,
        source_timestamp: Any,
    ) -> ToolLifecycleEvent | None:
        event_id = _event_id(trial_key, tool_call_id, "started")
        if event_id in self._seen_event_ids:
            return None
        self._seen_event_ids.add(event_id)
        return ToolLifecycleEvent(
            event_type="tool_call_started",
            message=f"{tool_name} started: {input_summary}",
            payload={
                "tool_event_id": event_id,
                "trial_key": trial_key,
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "status": "running",
                "input_summary": input_summary,
                "safe_arguments": dict(safe_arguments),
                "source_path": source_path,
                "source_kind": source_kind,
                "source_timestamp": source_timestamp,
            },
        )

    def _result_events(
        self,
        *,
        trial_key: str,
        tool_call_id: str,
        tool_name: str,
        result_summary: str,
        result_chars: int,
        is_error: bool,
        source_path: str,
        source_kind: str,
        source_timestamp: Any,
    ) -> list[ToolLifecycleEvent]:
        status = "failed" if is_error else "succeeded"
        events: list[ToolLifecycleEvent] = []
        result_id = _event_id(trial_key, tool_call_id, "result")
        if result_id not in self._seen_event_ids:
            self._seen_event_ids.add(result_id)
            events.append(
                ToolLifecycleEvent(
                    event_type="tool_result",
                    message=f"{tool_name} result: {result_summary}",
                    payload={
                        "tool_event_id": result_id,
                        "trial_key": trial_key,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "status": status,
                        "result_summary": result_summary,
                        "result_chars": result_chars,
                        "source_path": source_path,
                        "source_kind": source_kind,
                        "source_timestamp": source_timestamp,
                    },
                )
            )
        finished_id = _event_id(trial_key, tool_call_id, "finished")
        if finished_id not in self._seen_event_ids:
            self._seen_event_ids.add(finished_id)
            events.append(
                ToolLifecycleEvent(
                    event_type="tool_call_finished",
                    message=f"{tool_name} finished ({status})",
                    payload={
                        "tool_event_id": finished_id,
                        "trial_key": trial_key,
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "status": status,
                        "source_path": source_path,
                        "source_kind": source_kind,
                        "source_timestamp": source_timestamp,
                    },
                )
            )
        return events


def load_seen_tool_event_ids(event_path: Path) -> set[str]:
    if not event_path.exists() or not event_path.is_file():
        return set()
    seen: set[str] = set()
    try:
        with event_path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    not isinstance(event, Mapping)
                    or event.get("event_type") not in TOOL_EVENT_TYPES
                ):
                    continue
                payload = event.get("payload")
                event_id = (
                    payload.get("tool_event_id")
                    if isinstance(payload, Mapping)
                    else None
                )
                if isinstance(event_id, str) and event_id:
                    seen.add(event_id)
    except OSError:
        return seen
    return seen
