from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.live_events import (
    BoundedQueue,
    LocalEventWriter,
    Redactor,
    SharedOutputSampler,
    deterministic_live_run_id,
)


def test_live_run_id_is_deterministic_and_attempt_and_runner_specific() -> None:
    inputs = {
        "github_run_id": "12345",
        "github_run_attempt": 1,
        "runner_name": "vps-phase3-vps2-slot4",
        "arm_id": "router-gemini-flash",
        "mode": "canary",
    }
    first = deterministic_live_run_id(**inputs)
    assert first == deterministic_live_run_id(**inputs)
    assert first != deterministic_live_run_id(**{**inputs, "github_run_attempt": 2})
    assert first != deterministic_live_run_id(**{**inputs, "runner_name": "opaque-other-name"})
    assert "vps-phase3-vps2-slot4" in first


def test_redactor_removes_known_and_obvious_secrets() -> None:
    redactor = Redactor(["known-secret-value"])
    text = redactor.text(
        "Authorization: Bearer abcdefghijklmnop "
        "password=supersecretvalue "
        "postgresql://user:pass@example.invalid/db "
        "known-secret-value"
    )
    assert "abcdefghijklmnop" not in text
    assert "supersecretvalue" not in text
    assert "user:pass" not in text
    assert "known-secret-value" not in text
    assert "[REDACTED" in text


def test_local_ndjson_is_written_before_shared_sink(tmp_path: Path) -> None:
    seen: list[dict[str, object]] = []
    writer = LocalEventWriter(
        live_run_id="live-test",
        out_dir=tmp_path,
        metadata={"arm_id": "router-test"},
        redactor=Redactor(["very-secret-value"]),
        sink=lambda event: seen.append(event) or True,
    )
    event = writer.emit("process_output_chunk", message="token=very-secret-value")
    writer.close()

    rows = [json.loads(line) for line in writer.event_path.read_text().splitlines()]
    assert rows == [event]
    assert rows[0]["event_type"] == "process_output_chunk"
    assert rows[0]["run_id"] == "live-test"
    assert "very-secret-value" not in writer.event_path.read_text()
    assert seen == [event]
    assert json.loads(writer.latest_path.read_text())["sequence"] == 1


def test_bounded_queue_rejects_overflow() -> None:
    queue = BoundedQueue(max_size=2)
    assert queue.offer("one")
    assert queue.offer("two")
    assert not queue.offer("three")
    assert queue.size == 2
    assert queue.dropped == 1
    assert queue.drain(10) == ["one", "two"]


def test_runtime_env_file_values_are_redacted_without_persisting_secret_pairs(
    tmp_path: Path,
) -> None:
    secret = "arbitrary provider credential with spaces %#42"
    secret_dir = tmp_path / ".secrets"
    secret_dir.mkdir()
    (secret_dir / "provider.env").write_text(
        f"UNUSUAL_PROVIDER_CREDENTIAL={json.dumps(secret)}\n"
    )
    redactor = Redactor.from_runtime_sources(tmp_path, env={})
    writer = LocalEventWriter(
        live_run_id="live-runtime-secret",
        out_dir=tmp_path / ".run" / "live",
        metadata={},
        redactor=redactor,
    )
    writer.emit(
        "process_output_chunk",
        message=f"UNUSUAL_PROVIDER_CREDENTIAL={secret}",
    )
    writer.close()

    serialized = writer.event_path.read_text()
    assert secret not in serialized
    assert "UNUSUAL_PROVIDER_CREDENTIAL=" in serialized
    assert "[REDACTED_SECRET]" in serialized


def test_shared_output_sampler_keeps_early_events_then_samples() -> None:
    sampler = SharedOutputSampler(sample_every=3, initial_events=2)
    assert [sampler.should_publish() for _ in range(7)] == [
        True,
        True,
        True,
        False,
        False,
        True,
        False,
    ]
