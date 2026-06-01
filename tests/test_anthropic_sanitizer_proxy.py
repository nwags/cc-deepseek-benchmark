from __future__ import annotations

from scripts.anthropic_sanitizer_proxy import sanitize_payload


def test_sanitizes_haiku_only() -> None:
    payload = {
        "model": "router-anthropic-haiku",
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "hello"}],
        "output_config": {"effort": "low"},
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
        "effort": "low",
    }

    clean, stripped = sanitize_payload(payload, {"router-anthropic-haiku"})

    assert clean["model"] == "router-anthropic-haiku"
    assert "messages" in clean
    assert set(stripped) == {"output_config", "thinking", "reasoning_effort", "effort"}
    assert "output_config" not in clean
    assert "thinking" not in clean
    assert "reasoning_effort" not in clean
    assert "effort" not in clean

    assert "output_config" in payload


def test_does_not_sanitize_other_models() -> None:
    payload = {
        "model": "router-anthropic-sonnet",
        "messages": [{"role": "user", "content": "hello"}],
        "output_config": {"effort": "low"},
        "thinking": {"type": "enabled"},
    }

    clean, stripped = sanitize_payload(payload, {"router-anthropic-haiku"})

    assert stripped == []
    assert clean["output_config"] == {"effort": "low"}
    assert clean["thinking"] == {"type": "enabled"}


def test_sanitizer_returns_copy_not_original() -> None:
    payload = {
        "model": "router-anthropic-haiku",
        "messages": [{"role": "user", "content": "hello"}],
        "effort": "low",
    }

    clean, stripped = sanitize_payload(payload, {"router-anthropic-haiku"})

    assert stripped == ["effort"]
    assert "effort" not in clean
    assert payload["effort"] == "low"
