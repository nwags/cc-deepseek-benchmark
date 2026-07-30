from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shlex
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from scripts.lib.path_safety import (
    ensure_workspace_directory,
    ensure_workspace_output_path,
)


MAX_EVENT_TEXT_CHARS = 8_000
SENSITIVE_ENV_FRAGMENTS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "DATABASE_URL",
    "DB_URL",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_component(value: str | None, *, fallback: str = "unknown", limit: int = 48) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-._")
    return (cleaned or fallback)[:limit]


def deterministic_live_run_id(
    *,
    github_run_id: str | None,
    github_run_attempt: int | str | None,
    runner_name: str | None,
    arm_id: str,
    mode: str,
) -> str:
    """Build a stable execution id without interpreting the runner display name."""
    parts = (
        str(github_run_id or "local"),
        str(github_run_attempt or 1),
        str(runner_name or "local-runner"),
        arm_id,
        mode,
    )
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:12]
    return "-".join(
        (
            "live",
            safe_component(parts[0], limit=24),
            f"a{safe_component(parts[1], limit=8)}",
            safe_component(parts[2], limit=32),
            safe_component(arm_id, limit=40),
            safe_component(mode, limit=16),
            digest,
        )
    )


def workspace_metadata(workspace: Path) -> dict[str, str]:
    resolved = workspace.resolve()
    return {
        "workspace_name": resolved.name,
        "workspace_fingerprint": hashlib.sha256(str(resolved).encode("utf-8")).hexdigest(),
    }


class Redactor:
    """Redact shared-output text and structured values without logging secrets."""

    _patterns = (
        (
            re.compile(r"(?i)\bAuthorization\s*:\s*[^\s,;]+(?:\s+[^\s,;]+)?"),
            "Authorization: [REDACTED]",
        ),
        (
            re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
            "Bearer [REDACTED]",
        ),
        (
            re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql)://[^\s\"']+"),
            "[REDACTED_DATABASE_URL]",
        ),
        (
            re.compile(r"\b(?:sk|xai)-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
            "[REDACTED_API_KEY]",
        ),
        (
            re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
            "[REDACTED_ACCESS_KEY]",
        ),
        (
            re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
            "[REDACTED_API_KEY]",
        ),
        (
            re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
            "[REDACTED_TOKEN]",
        ),
        (
            re.compile(
                r"""(?ix)
                ["']?
                (?:api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password)
                ["']?\s*[:=]\s*["']?[^\s"',}\]]{8,}
                """
            ),
            "[REDACTED_SECRET]",
        ),
    )

    def __init__(self, known_secrets: Iterable[str] = ()) -> None:
        self.known_secrets = tuple(
            sorted(
                {value for value in known_secrets if value and len(value) >= 8},
                key=len,
                reverse=True,
            )
        )

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> "Redactor":
        source = os.environ if env is None else env
        values = [
            value
            for key, value in source.items()
            if value and any(fragment in key.upper() for fragment in SENSITIVE_ENV_FRAGMENTS)
        ]
        return cls(values)

    @classmethod
    def from_runtime_sources(
        cls,
        workspace: Path,
        env: Mapping[str, str] | None = None,
    ) -> "Redactor":
        source = os.environ if env is None else env
        values = [
            value
            for key, value in source.items()
            if value and any(fragment in key.upper() for fragment in SENSITIVE_ENV_FRAGMENTS)
        ]
        workspace_resolved = workspace.resolve(strict=True)
        secret_dir = workspace_resolved / ".secrets"
        if secret_dir.is_dir() and not secret_dir.is_symlink():
            for path in sorted(secret_dir.glob("*.env")):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    path.resolve(strict=True).relative_to(workspace_resolved)
                    lines = path.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
                for line in lines:
                    try:
                        tokens = shlex.split(line, comments=True, posix=True)
                    except ValueError:
                        continue
                    if not tokens:
                        continue
                    token = tokens[-1] if tokens[0] == "export" else tokens[0]
                    if "=" not in token:
                        continue
                    _name, value = token.split("=", 1)
                    if value:
                        values.append(value)
        return cls(values)

    def text(self, value: Any, *, limit: int | None = MAX_EVENT_TEXT_CHARS) -> str:
        redacted = str(value)
        for secret in self.known_secrets:
            redacted = redacted.replace(secret, "[REDACTED_SECRET]")
        for pattern, replacement in self._patterns:
            redacted = pattern.sub(replacement, redacted)
        if limit is not None and len(redacted) > limit:
            redacted = redacted[: max(limit - 16, 0)] + "...[truncated]"
        return redacted

    def value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            return {str(key): self.value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self.value(item) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self.text(value)

    def command(self, command: Sequence[str]) -> list[str]:
        return [self.text(part, limit=1_000) for part in command]


@dataclass(frozen=True)
class LiveEvent:
    sequence: int
    event_type: str
    occurred_at: str
    elapsed_seconds: float
    live_run_id: str
    stream: str | None
    message: str | None
    payload: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        # Older MVP readers use run_id and timestamp.
        record["run_id"] = self.live_run_id
        record["timestamp"] = self.occurred_at
        return record


EventSink = Callable[[dict[str, Any]], bool]


class LocalEventWriter:
    """Append redacted NDJSON first, then offer the same event to a shared sink."""

    def __init__(
        self,
        *,
        live_run_id: str,
        out_dir: Path,
        metadata: Mapping[str, Any],
        redactor: Redactor,
        sink: EventSink | None = None,
        workspace: Path | None = None,
    ) -> None:
        self.live_run_id = live_run_id
        self.workspace = workspace
        if workspace is None:
            self.out_dir = out_dir
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self.event_path = self.out_dir / f"{live_run_id}.ndjson"
            self.latest_path = self.out_dir / "latest.json"
            self.context_path = self.out_dir / f"{live_run_id}.context.json"
        else:
            self.out_dir = ensure_workspace_directory(
                out_dir,
                workspace=workspace,
                create=True,
                label="live event directory",
            )
            self.event_path = ensure_workspace_output_path(
                self.out_dir / f"{live_run_id}.ndjson",
                workspace=workspace,
                label="live NDJSON",
            )
            self.latest_path = ensure_workspace_output_path(
                self.out_dir / "latest.json",
                workspace=workspace,
                label="live latest index",
            )
            self.context_path = ensure_workspace_output_path(
                self.out_dir / f"{live_run_id}.context.json",
                workspace=workspace,
                label="live context",
            )
        self.metadata = redactor.value(dict(metadata))
        self.redactor = redactor
        self.sink = sink
        self.sequence = self._existing_sequence()
        self.started = time.monotonic()
        self._lock = threading.RLock()
        self._handle = self.event_path.open("a", encoding="utf-8", buffering=1)

    def _existing_sequence(self) -> int:
        if not self.event_path.exists():
            return 0
        sequence = 0
        try:
            with self.event_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        sequence = max(sequence, int(json.loads(line).get("sequence") or 0))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        continue
        except OSError:
            return 0
        return sequence

    def set_sink(self, sink: EventSink | None) -> None:
        self.sink = sink

    def write_context(self, context: Mapping[str, Any]) -> None:
        payload = self.redactor.value(dict(context))
        temp_path = self.context_path.with_suffix(".json.tmp")
        if self.workspace is not None:
            self.context_path = ensure_workspace_output_path(
                self.context_path,
                workspace=self.workspace,
                label="live context",
            )
            temp_path = ensure_workspace_output_path(
                temp_path,
                workspace=self.workspace,
                label="temporary live context",
            )
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.context_path)

    def emit(
        self,
        event_type: str,
        *,
        stream: str | None = None,
        message: str | None = None,
        publish_shared: bool = True,
        **payload: Any,
    ) -> dict[str, Any]:
        with self._lock:
            self.sequence += 1
            event = LiveEvent(
                sequence=self.sequence,
                event_type=safe_component(event_type, fallback="event", limit=64),
                occurred_at=utc_now(),
                elapsed_seconds=round(time.monotonic() - self.started, 3),
                live_run_id=self.live_run_id,
                stream=safe_component(stream, fallback="", limit=16) if stream else None,
                message=self.redactor.text(message) if message is not None else None,
                payload=self.redactor.value({**dict(self.metadata), **payload}),
            ).as_record()
            self._handle.write(json.dumps(event, sort_keys=True) + "\n")
            self._handle.flush()
            self._write_latest(event)

        if publish_shared and self.sink is not None:
            self.sink(event)
        return event

    def _write_latest(self, event: Mapping[str, Any]) -> None:
        latest = {
            "live_run_id": self.live_run_id,
            "run_id": self.live_run_id,
            "event_path": self.event_path.name,
            "updated_at": event["occurred_at"],
            "last_event_type": event["event_type"],
            "sequence": event["sequence"],
            **dict(self.metadata),
        }
        temp_path = self.latest_path.with_suffix(".json.tmp")
        if self.workspace is not None:
            self.latest_path = ensure_workspace_output_path(
                self.latest_path,
                workspace=self.workspace,
                label="live latest index",
            )
            temp_path = ensure_workspace_output_path(
                temp_path,
                workspace=self.workspace,
                label="temporary live latest index",
            )
        temp_path.write_text(json.dumps(latest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.latest_path)

    def close(self) -> None:
        with self._lock:
            if not self._handle.closed:
                self._handle.flush()
                self._handle.close()

    def __enter__(self) -> "LocalEventWriter":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


class BoundedQueue:
    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=max_size)
        self.dropped = 0

    @property
    def size(self) -> int:
        return self._queue.qsize()

    def offer(self, item: Any) -> bool:
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            self.dropped += 1
            return False

    def put(self, item: Any, *, timeout: float | None = None) -> bool:
        try:
            self._queue.put(item, timeout=timeout)
            return True
        except queue.Full:
            return False

    def get(self, timeout: float | None = None) -> Any:
        return self._queue.get(timeout=timeout)

    def get_nowait(self) -> Any:
        return self._queue.get_nowait()

    def drain(self, limit: int) -> list[Any]:
        items: list[Any] = []
        while len(items) < limit:
            try:
                items.append(self.get_nowait())
            except queue.Empty:
                break
        return items


class SharedOutputSampler:
    """Keep all local output while bounding shared high-volume event traffic."""

    def __init__(self, sample_every: int = 5, initial_events: int = 20) -> None:
        if sample_every <= 0 or initial_events < 0:
            raise ValueError("output sampling bounds are invalid")
        self.sample_every = sample_every
        self.initial_events = initial_events
        self.seen = 0

    def should_publish(self) -> bool:
        self.seen += 1
        return self.seen <= self.initial_events or self.seen % self.sample_every == 0


def bounded_backoff_delays(
    *,
    attempts: int = 4,
    initial_seconds: float = 0.25,
    maximum_seconds: float = 5.0,
) -> tuple[float, ...]:
    return tuple(min(initial_seconds * (2**index), maximum_seconds) for index in range(max(attempts, 0)))
