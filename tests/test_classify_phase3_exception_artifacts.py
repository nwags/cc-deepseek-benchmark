import scripts.classify_phase3_exception_artifacts as classifier
from scripts.classify_phase3_exception_artifacts import EvidenceSource, classify_exception, runtime_band


def classify(snippet: str):
    return classify_exception(
        target_row={
            "task_id": "terminal-bench-2.0:synthetic",
            "exception_type": "exception_info",
            "runtime_seconds": "45",
        },
        evidence_by_type={"exception": snippet},
    )


def test_agent_timeout_classification():
    result = classify("AgentTimeoutError: agent timed out while waiting for command completion")

    assert result.primary_category == "agent_timeout"
    assert result.confidence == "high"
    assert result.needs_manual_review is False
    assert result.matched_signal == "AgentTimeoutError"
    assert result.matched_pattern
    assert result.evidence_artifact_type == "exception"
    assert "AgentTimeoutError" in result.evidence_excerpt


def test_nonzero_agent_exit_classification():
    result = classify("NonZeroAgentExitCodeError: agent exited with code 1")

    assert result.primary_category == "nonzero_agent_exit"
    assert result.confidence == "high"
    assert result.matched_signal == "NonZeroAgentExitCodeError"
    assert result.matched_pattern


def test_provider_rate_limit_classification():
    result = classify("HTTP 429 RESOURCE_EXHAUSTED: provider rate limit quota exceeded")

    assert result.primary_category == "provider_rate_limit"
    assert result.confidence == "high"
    assert result.matched_signal
    assert result.matched_pattern
    assert "429" in result.evidence_excerpt


def test_direct_match_records_artifact_provenance():
    result = classify_exception(
        target_row={"runtime_seconds": "45"},
        evidence_by_type=[
            EvidenceSource(
                artifact_type="log",
                artifact_id="artifact-123",
                source_rank=2,
                text="HTTP 403 unauthorized",
            )
        ],
    )

    assert result.primary_category == "auth_or_permission_error"
    assert result.matched_signal
    assert result.matched_pattern
    assert result.evidence_artifact_type == "log"
    assert result.evidence_artifact_id == "artifact-123"
    assert result.evidence_source_rank == 2


def test_connection_refused_classification():
    result = classify("ConnectionRefusedError: [Errno 111] connection refused")

    assert result.primary_category == "connection_refused_or_service_unavailable"
    assert result.confidence == "high"
    assert result.matched_signal == "ConnectionRefusedError"
    assert result.matched_pattern


def test_context_length_classification():
    result = classify("Request failed because context length exceeded the model context window")

    assert result.primary_category == "context_length_or_payload_error"
    assert result.confidence == "high"
    assert result.matched_signal == "context length"
    assert result.matched_pattern


def test_unknown_exception_requires_manual_review():
    result = classify("Something strange happened without a known signature")

    assert result.primary_category == "unknown_exception"
    assert result.confidence == "low"
    assert result.needs_manual_review is True
    assert result.matched_signal == ""
    assert result.matched_pattern == ""


def test_session_id_and_token_count_do_not_trigger_auth_or_provider_classification():
    result = classify(
        '{"session_id":"abc123","estimated_tokens":403,'
        '"message":"no recognized provider failure signal here"}'
    )

    assert result.primary_category == "unknown_exception"
    assert result.needs_manual_review is True
    assert result.matched_signal == ""


def test_terminal_timeout_preferred_over_rate_limit_secondary():
    result = classify(
        "AgentTimeoutError: agent timed out after provider log mentioned "
        "HTTP 429 RESOURCE_EXHAUSTED rate limit"
    )

    assert result.primary_category == "agent_timeout"
    assert result.secondary_category == "provider_rate_limit"
    assert result.confidence == "high"
    assert result.needs_manual_review is False
    assert result.matched_signal == "AgentTimeoutError"


def test_high_confidence_requires_signal_visible_in_excerpt(monkeypatch):
    monkeypatch.setattr(classifier, "safe_excerpt", lambda *args, **kwargs: "unrelated excerpt")

    result = classify("HTTP 429 RESOURCE_EXHAUSTED rate limit")

    assert result.primary_category == "provider_rate_limit"
    assert result.confidence == "medium"
    assert result.needs_manual_review is True


def test_evidence_excerpt_redacts_json_api_key_and_keeps_signal():
    result = classify(
        '{"api_key":"sk-example-secret-value-123456",'
        '"error":"HTTP 429 RESOURCE_EXHAUSTED"}'
    )

    assert result.primary_category == "provider_rate_limit"
    assert result.confidence == "high"
    assert "RESOURCE_EXHAUSTED" in result.evidence_excerpt
    assert "example-secret-value" not in result.evidence_excerpt
    assert "REDACTED" in result.evidence_excerpt


def test_runtime_bands_are_supporting_evidence():
    assert runtime_band("45") == "fast_exception_under_90s"
    assert runtime_band("90") == "mid_exception_90_to_1200s"
    assert runtime_band("1200.1") == "long_exception_over_1200s"
