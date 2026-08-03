from __future__ import annotations

import csv
import importlib.util
import io
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT = Path("scripts/generate_comprehensive_evidence_review.py")
SPEC = importlib.util.spec_from_file_location("comprehensive_review", SCRIPT)
assert SPEC and SPEC.loader
review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = review
SPEC.loader.exec_module(review)


class Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class FakeConnection:
    def __init__(self, responses: list[list[dict[str, Any]]]) -> None:
        self.responses = iter(responses)

    def execute(self, _sql: str, _params: Any) -> Result:
        return Result(next(self.responses))


class Body(io.BytesIO):
    def close(self) -> None:
        super().close()


class IgnoredRangeClient:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def get_object(self, **_kwargs: Any) -> dict[str, Any]:
        return {"Body": Body(self.data), "ContentLength": len(self.data)}


class RangeClient:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.ranges: list[tuple[int, int]] = []

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        match = review.re.fullmatch(r"bytes=(\d+)-(\d+)", kwargs["Range"])
        assert match
        start, requested_end = map(int, match.groups())
        end = min(requested_end, len(self.data) - 1)
        self.ranges.append((start, requested_end))
        body = self.data[start:end + 1] if start < len(self.data) else b""
        return {
            "Body": Body(body),
            "ContentLength": len(body),
            "ContentRange": f"bytes {start}-{end}/{len(self.data)}",
        }


class MalformedContentRangeClient:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def get_object(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "Body": Body(self.data),
            "ContentLength": len(self.data),
            "ContentRange": "bytes invalid/total",
        }


def test_secret_redaction_and_uri_sanitization_preserve_safe_context() -> None:
    source = {
        "agent": {
            "model_name": "router-kimi-k3",
            "env": {
                "ANTHROPIC_AUTH_TOKEN": "sk-secret-value-1234567890",
                "ANTHROPIC_BASE_URL": "https://user:pass@router.example:4000/v1?deployment=kimi&token=secret",
            },
        },
        "timeout_multiplier": 2,
    }
    before = json.dumps(source, sort_keys=True)
    rendered = json.dumps(review.redact_structured(source), sort_keys=True)
    assert json.dumps(source, sort_keys=True) == before
    assert "sk-secret" not in rendered
    assert "user" not in rendered
    assert "pass" not in rendered
    assert "token=secret" not in rendered
    assert "router.example:4000" in rendered
    assert "deployment=kimi" in rendered
    assert "router-kimi-k3" in rendered


def test_nested_array_primitive_redaction_covers_assignments_tokens_and_signed_urls() -> None:
    source = {
        "args": [
            "Authorization: Bearer bearer-array-secret-123456",
            [
                "OPENAI_API_KEY=sk-array-provider-secret-123456",
                "https://person:password@example.test/v1?deployment=blue&X-Amz-Signature=signed-secret",
                ["XAI_API_KEY=xai-array-provider-secret-123456", "safe=value"],
            ],
        ]
    }
    before = json.dumps(source, sort_keys=True)
    rendered = json.dumps(review.redact_structured(source), sort_keys=True)
    assert json.dumps(source, sort_keys=True) == before
    for secret in ("bearer-array-secret", "sk-array-provider-secret", "person", "password", "signed-secret", "xai-array-provider-secret"):
        assert secret not in rendered
    assert "example.test/v1" in rendered
    assert "deployment=blue" in rendered
    assert "safe=value" in rendered


def test_shared_free_text_and_structured_secret_vectors_match_python_redactor() -> None:
    vectors = json.loads(Path("tests/fixtures/secret_redaction_vectors.json").read_text(encoding="utf-8"))
    for vector in vectors["text_vectors"]:
        rendered = review.redact_text(vector["input"])
        for secret in vector["forbidden"]:
            assert secret not in rendered, (vector["name"], secret)
        for safe in vector["required"]:
            assert safe in rendered, (vector["name"], safe)
    for vector in vectors["structured_vectors"]:
        before = json.dumps(vector["input"], sort_keys=True)
        rendered = json.dumps(review.redact_structured(vector["input"]), sort_keys=True)
        assert json.dumps(vector["input"], sort_keys=True) == before
        for secret in vector["forbidden"]:
            assert secret not in rendered, (vector["name"], secret)
        for safe in vector["required"]:
            assert safe in rendered, (vector["name"], safe)


def test_final_sink_password_shapes_pass_independent_strict_audit() -> None:
    source = {
        "manual_evidence": {
            "transcript_activity": {
                "visible_assistant_excerpts": [
                    "password=x",
                    'assistant emitted {"password": "abcdefghijklmnopqrst"}, then passwd=again;',
                    ["export PASSWORD='abcdefghijklmnopqrstuvwx'", "password=[REDACTED]"],
                    "ordinary prose about a password-recovery benchmark",
                ],
                "visible_result_excerpts": ["password = \"value with spaces\"."],
            },
            "verifier_stdout_excerpt": "password=verifier-one, passwd:verifier-two; password=third}",
            "ctrf_tests": [{"name": "password=case-name", "failure_message": "passwd='failure-value'"}],
            "exception_evidence": {"database_exception_summary": "PASSWORD=summary-secret"},
        },
        "evidence": [{"label": "Verifier", "value": "password=result-secret"}],
        "hidden_reasoning_retained": False,
    }
    before = json.dumps(source, sort_keys=True)
    rendered = review.sanitize_evidence_output(source)
    assert json.dumps(source, sort_keys=True) == before
    assert rendered["manual_evidence"]["transcript_activity"]["visible_assistant_excerpts"][-1] == "ordinary prose about a password-recovery benchmark"
    assert review.REDACTED in json.dumps(rendered)
    rules: set[str] = set()
    review._strict_scan_value(rendered, rules)
    assert rules == set()


def test_jsonl_final_sink_and_exact_strict_scanner_reject_unsanitized_candidates(tmp_path: Path) -> None:
    row = {
        "trial_id": "trial",
        "manual_evidence": {
            "transcript_activity": {
                "visible_assistant_excerpts": ['{"password":"assistant-secret"}'],
                "visible_result_excerpts": ["passwd=result-secret"],
            },
            "verifier_stdout_excerpt": "PASSWORD=verifier-secret",
        },
        "hidden_reasoning_retained": False,
    }
    review.write_jsonl(tmp_path / "trial_evidence.jsonl", [row])
    review.write_jsonl(tmp_path / "targeted_evidence_bundle.jsonl", [row])
    filenames = ("trial_evidence.jsonl", "targeted_evidence_bundle.jsonl")
    assert review.strict_scan_output_directory(tmp_path, filenames) == {}
    for filename in filenames:
        rendered = (tmp_path / filename).read_text(encoding="utf-8")
        assert "assistant-secret" not in rendered
        assert "result-secret" not in rendered
        assert "verifier-secret" not in rendered

    unsafe = tmp_path / "unsafe"
    unsafe.mkdir()
    (unsafe / "trial_evidence.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (unsafe / "targeted_evidence_bundle.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert review.strict_scan_output_directory(unsafe, filenames) == {
        "targeted_evidence_bundle.jsonl": ["password_assignment", "supported_credential_pattern"],
        "trial_evidence.jsonl": ["password_assignment", "supported_credential_pattern"],
    }


def test_csv_writer_uses_lf_and_preserves_rows_and_columns(tmp_path: Path) -> None:
    rows = [
        {"trial_id": "one", "summary": "first line\nsecond line", "reward": 1},
        {"trial_id": "two", "summary": "comma, quoted", "reward": 0},
    ]
    path = tmp_path / "miniature.csv"
    review.write_csv(path, rows, ["trial_id", "summary", "reward"])
    data = path.read_bytes()
    assert b"\r" not in data
    assert all(not line.endswith((b" ", b"\t")) for line in data.split(b"\n"))
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["trial_id", "summary", "reward"]
        assert list(reader) == [
            {"trial_id": "one", "summary": "first line\nsecond line", "reward": "1"},
            {"trial_id": "two", "summary": "comma, quoted", "reward": "0"},
        ]


def test_strict_output_scanner_rejects_carriage_returns_and_trailing_whitespace(tmp_path: Path) -> None:
    (tmp_path / "bad.csv").write_bytes(b"name,value\r\none,bad \r\n")
    (tmp_path / "bad.md").write_bytes(b"clean\nbad\t\n")
    assert review.strict_scan_output_directory(tmp_path, ("bad.csv", "bad.md")) == {
        "bad.csv": ["carriage_return", "trailing_whitespace"],
        "bad.md": ["trailing_whitespace"],
    }


def test_discovery_selects_latest_valid_complete_run_and_retains_invalid_provenance() -> None:
    base = {
        "arm_run_id": "arm-run",
        "run_id": "run",
        "arm_id": "arm-a",
        "suite_id": "phase3-full-20",
        "suite_type": "full",
        "logical_mode": "full",
        "storage_mode": "full",
        "status": "completed",
        "started_at": None,
        "finished_at": None,
        "trial_count": 3,
        "task_count": 1,
        "required_task_count": 1,
        "run_metadata": {},
        "invalid_reason": None,
        "invalidated_at": None,
        "invalidated_by": None,
    }
    rows = [
        {**base, "run_label": "new", "run_id": "new-id", "arm_run_id": "new-arm-run"},
        {**base, "run_label": "old", "run_id": "old-id", "arm_run_id": "old-arm-run"},
        {**base, "run_label": "invalid", "run_id": "bad-id", "arm_run_id": "bad-arm-run", "arm_id": "arm-b", "invalid_reason": "quarantined"},
    ]
    scope = review.discover_scope(FakeConnection([rows, []]), "phase3-full-20")
    assert [row["run_label"] for row in scope.eligible_runs] == ["new"]
    assert len(scope.runs) == 3
    assert next(row for row in scope.runs if row["run_label"] == "invalid")["valid"] is False


def test_ignored_range_is_hard_bounded_and_cannot_be_called_complete() -> None:
    head = json.dumps({"type": "system", "subtype": "init", "model": "safe"}).encode() + b"\n"
    middle = json.dumps({"type": "system", "padding": "x" * 8192}).encode() + b"\n"
    tail = json.dumps({"type": "result", "result": "", "usage": {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 0}}).encode() + b"\n"
    data = head + middle + tail
    result = review.read_artifact(
        IgnoredRangeClient(data),
        {"artifact_type": "agent_transcript", "r2_uri": "r2://bucket/path", "size_bytes": len(data)},
        1024,
    )
    assert result.bytes_read <= 1024
    assert result.completeness == "truncated"
    assert result.remote_total_bytes == len(data)
    assert result.read_availability == "partial"


def test_remote_total_overrides_underreported_stored_size_and_drives_tail_offset() -> None:
    head = json.dumps({"type": "system", "subtype": "init", "model": "safe"}).encode() + b"\n"
    middle = json.dumps({"type": "system", "padding": "x" * 4096}).encode() + b"\n"
    tail = json.dumps({"type": "result", "result": "done", "usage": {"input_tokens": 1, "output_tokens": 1}}).encode() + b"\n"
    data = head + middle + tail
    client = RangeClient(data)
    result = review.read_artifact(
        client,
        {"artifact_type": "agent_transcript", "r2_uri": "r2://bucket/path", "size_bytes": 100},
        1024,
    )
    assert result.total_bytes == len(data)
    assert result.size_metadata_status == "stored_underreported"
    assert result.completeness == "head_tail_only"
    assert client.ranges[1][0] == len(data) - 512


def test_overreported_stored_size_never_marks_evidence_complete_even_when_remote_object_is_fully_read() -> None:
    data = (json.dumps({"type": "result", "result": "done", "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n").encode()
    result = review.read_artifact(
        RangeClient(data),
        {
            "artifact_type": "agent_transcript", "r2_uri": "r2://bucket/path",
            "size_bytes": len(data) + 5000, "sha256": hashlib.sha256(data).hexdigest(),
        },
        1024,
    )
    assert result.remote_total_bytes == len(data)
    assert result.size_metadata_status == "stored_overreported"
    assert result.completeness != "complete"
    assert result.integrity_status == "verified"


def test_complete_object_sha256_is_verified_and_mismatch_invalidates_completeness() -> None:
    data = b"verifier output\n"
    good = review.read_artifact(
        RangeClient(data),
        {"artifact_type": "verifier_stdout", "r2_uri": "r2://bucket/path", "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
        1024,
    )
    bad = review.read_artifact(
        RangeClient(data),
        {"artifact_type": "verifier_stdout", "r2_uri": "r2://bucket/path", "size_bytes": len(data), "sha256": "0" * 64},
        1024,
    )
    assert good.completeness == "complete" and good.integrity_status == "verified"
    assert bad.completeness == "malformed" and bad.integrity_status == "mismatch"


def test_malformed_content_range_does_not_become_a_verified_remote_total() -> None:
    data = b'{"type":"result","result":"done"}\n'
    result = review.read_artifact(
        MalformedContentRangeClient(data),
        {"artifact_type": "agent_transcript", "r2_uri": "r2://bucket/path", "size_bytes": len(data)},
        1024,
    )
    assert result.remote_total_bytes is None
    assert result.size_metadata_status == "remote_unverified"
    assert result.completeness != "complete"


def test_database_exception_summary_is_separately_sanitized_and_changes_exception_expectation() -> None:
    secret = "summary-client-secret-value"
    request, metadata = review.prepare_trial(
        None,
        {
            "trial_id": "trial", "reward": 0, "runtime_seconds": 1,
            "exception_type": None,
            "exception_summary": f"api_connection_error client_secret={secret}",
            "input_tokens": None, "cache_tokens": None, "output_tokens": None,
            "cost_usd": None,
        },
        [],
        {"run_metadata": {}},
        1024,
    )
    assert request["databaseExceptionSummary"] == "api_connection_error client_secret=[REDACTED]"
    assert secret not in json.dumps(request)
    assert metadata["canonical_expected"] == 9
    assert metadata["canonical_present"] == 0


def test_review_queue_conditions_and_stratified_control_sample() -> None:
    base = {
        "trial_id": "ordinary-success", "arm_id": "arm-a", "task_id": "task",
        "raw_outcome": "success", "execution_validity": "substantive",
        "activity_subtype": "substantive_agent_activity", "policy_disposition": "none_detected",
        "failure_subtype": "none", "termination_subtype": "none", "unclassified_exception": False,
        "exception_after_substantive_activity": False, "telemetry_status": "consistent", "evidence_complete": True,
        "canonical_completeness": "8/8", "classification_confidence": "high", "cost_usd": 0.1,
        "exception_type": None, "database_result_consistency": "consistent",
        "r2_read_availability": "available", "analyzed_artifact_integrity_status": "verified", "size_metadata_status": "consistent",
        "analyzer_manual_review_priority": "low", "manual_review_priority": "low",
    }
    refusal = {
        **base, "trial_id": "refusal", "raw_outcome": "failure", "execution_validity": "policy_blocked",
        "activity_subtype": "provider_policy_refusal", "policy_disposition": "provider_policy_refusal",
        "failure_subtype": "policy_refusal", "telemetry_status": "database_zero_transcript_nonzero",
    }
    assert "policy_refusal" in review.review_reasons(refusal, high_cost_threshold=None, headline_trials=set())
    sample_rows = [base, {**base, "trial_id": "ordinary-failure", "raw_outcome": "failure", "failure_subtype": "test_assertion_failure"}, refusal]
    sample = review.manual_sample(sample_rows, 1)
    assert {row["sample_stratum"] for row in sample} == {"ordinary_success", "ordinary_failure"}
    assert all(row["trial_id"] != "refusal" for row in sample)
    assert review.combine_priority("high", ["timeout"]) == "high"


def test_control_strata_exclude_nonordinary_rows_and_keep_diagnostic_controls_separate() -> None:
    base = {
        "trial_id": "ordinary", "arm_id": "arm", "task_id": "task", "raw_outcome": "success",
        "execution_validity": "substantive", "activity_subtype": "substantive_agent_activity",
        "policy_disposition": "none_detected", "failure_subtype": "none", "termination_subtype": "none",
        "telemetry_status": "consistent", "evidence_complete": True, "classification_confidence": "high",
        "exception_type": None,
    }
    rows = [
        base,
        {**base, "trial_id": "timeout", "termination_subtype": "timeout", "failure_subtype": "timeout"},
        {**base, "trial_id": "telemetry", "telemetry_status": "nonzero_mismatch"},
        {**base, "trial_id": "exception-success", "termination_subtype": "unclassified_exception", "exception_type": "CleanupError"},
        {**base, "trial_id": "incomplete", "evidence_complete": False, "classification_confidence": "medium"},
    ]
    sample = review.manual_sample(rows, 2)
    by_stratum = {
        stratum: {row["trial_id"] for row in sample if row["sample_stratum"] == stratum}
        for stratum in {row["sample_stratum"] for row in sample}
    }
    assert by_stratum["ordinary_success"] == {"ordinary"}
    assert by_stratum["timeout_control"] == {"timeout"}
    assert by_stratum["telemetry_mismatch_control"] == {"telemetry"}
    assert by_stratum["exception_success_control"] == {"timeout", "exception-success"}
    assert by_stratum["incomplete_evidence_control"] == {"incomplete"}


def test_task_disagreements_use_arm_specific_summaries_and_explanatory_categories() -> None:
    def row(trial_id: str, arm: str, outcome: str, *, policy: str = "none_detected") -> dict[str, Any]:
        return {
            "trial_id": trial_id, "task_id": "task", "arm_id": arm, "raw_outcome": outcome,
            "execution_validity": "policy_blocked" if policy != "none_detected" else "substantive",
            "activity_subtype": "provider_policy_refusal" if policy != "none_detected" else "substantive_agent_activity",
            "policy_disposition": policy, "termination_subtype": "provider_policy_refusal" if policy != "none_detected" else "none",
            "failure_subtype": "policy_refusal" if policy != "none_detected" else "test_assertion_failure" if outcome == "failure" else "none",
        }

    rows = [
        *(row(f"a-{index}", "arm-a", "success") for index in range(3)),
        *(row(f"b-{index}", "arm-b", "failure", policy="provider_policy_refusal") for index in range(3)),
    ]
    disagreements, headline = review.task_disagreements(rows)
    assert len(disagreements) == 1
    item = disagreements[0]
    assert item["disagreement_category"] == "policy_access_difference"
    assert "arm_a_activity_summary" in item and "arm_b_policy_summary" in item
    assert "policy_or_infrastructure_explanation" not in item
    assert len(headline) == 6


def test_checkpoint_fingerprint_binds_analyzer_and_generator_source_hashes() -> None:
    trial = {"trial_id": "trial", "reward": 0, "runtime_seconds": 1, "cost_usd": None, "input_tokens": 0, "cache_tokens": 0, "output_tokens": 0, "exception_type": None, "exception_summary": "generic failure"}
    artifacts = [{"artifact_id": "a", "artifact_type": "result", "sha256": "hash", "size_bytes": 10, "r2_uri": "r2://bucket/key"}]
    first = review.fingerprint(trial, artifacts, 1024, {"analyzer": "one", "generator": "two"})
    second = review.fingerprint(trial, artifacts, 1024, {"analyzer": "changed", "generator": "two"})
    assert first != second
    changed_summary = review.fingerprint({**trial, "exception_summary": "timeout"}, artifacts, 1024, {"analyzer": "one", "generator": "two"})
    changed_options = review.fingerprint(trial, artifacts, 1024, {"analyzer": "one", "generator": "two"}, {"read_timeout_seconds": 99})
    assert first != changed_summary
    assert first != changed_options


def test_scope_fingerprint_binds_run_trial_artifact_sources_limits_and_configuration() -> None:
    run = {
        "run_id": "run", "arm_run_id": "arm-run", "run_label": "label", "arm_id": "arm",
        "suite_id": "suite", "suite_type": "full", "logical_mode": "full", "storage_mode": "full",
        "status": "completed", "started_at": None, "finished_at": None, "run_metadata": {"route": "blue"},
    }
    trial = {"trial_id": "trial"}
    artifact = {
        "artifact_id": "artifact", "trial_id": "trial", "artifact_type": "result",
        "sha256": "abc", "size_bytes": 10, "r2_uri": "r2://bucket/key",
    }
    scope = review.Scope(runs=[run], eligible_runs=[run], trials=[trial], artifacts=[artifact])
    source_hashes = {"analyzer": "one", "generator": "two"}
    options = {"stream_cap": 1024, "read_timeout_seconds": 5}
    original, descriptor = review.scope_fingerprint(scope, source_hashes, options, "suite")
    assert descriptor["selected_run_count"] == 1
    assert descriptor["trial_count"] == 1
    assert descriptor["artifact_count"] == 1
    variants = [
        review.Scope(runs=[run], eligible_runs=[run], trials=[{"trial_id": "changed"}], artifacts=[artifact]),
        review.Scope(runs=[run], eligible_runs=[run], trials=[trial], artifacts=[{**artifact, "artifact_type": "config"}]),
        review.Scope(runs=[run], eligible_runs=[run], trials=[trial], artifacts=[{**artifact, "sha256": "changed"}]),
        review.Scope(runs=[run], eligible_runs=[run], trials=[trial], artifacts=[{**artifact, "size_bytes": 11}]),
        review.Scope(runs=[{**run, "run_metadata": {"route": "green"}}], eligible_runs=[{**run, "run_metadata": {"route": "green"}}], trials=[trial], artifacts=[artifact]),
    ]
    for variant in variants:
        assert review.scope_fingerprint(variant, source_hashes, options, "suite")[0] != original
    assert review.scope_fingerprint(scope, source_hashes, {**options, "stream_cap": 2048}, "suite")[0] != original


def test_targeted_manual_evidence_retains_safe_facts_and_omits_reasoning_and_secrets() -> None:
    secret = "packet-client-secret"
    hidden = "private hidden reasoning"
    transcript_raw = "\n".join([
        json.dumps({"type": "system", "subtype": "thinking_tokens", "content": hidden, "estimated_tokens": 7}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": f"Visible work client_secret={secret}"},
            {"type": "tool_use", "name": "Write", "input": {"file_path": "/workspace/file"}},
        ]}}),
        json.dumps({"type": "result", "result": "done"}),
    ]).encode()
    sanitized, malformed = review.sanitize_transcript(transcript_raw)
    assert malformed is False
    request = {
        "databaseExceptionSummary": "generic exception password=[REDACTED]",
        "artifacts": [
            {"artifactType": "agent_transcript", "artifactId": "transcript-id", "text": sanitized},
            {"artifactType": "verifier_stdout", "artifactId": "stdout-id", "text": "FAILED safe assertion"},
            {"artifactType": "verifier_ctrf", "artifactId": "ctrf-id", "text": json.dumps({"tests": [{"name": "safe test", "status": "failed", "message": "safe failure"}]})},
        ],
    }
    analysis = {
        "visible_assistant_events": 1, "thinking_events": 1, "tool_calls": 1,
        "workspace_changing_calls": 1, "trajectory_steps": 1, "substantive_trajectory_steps": 1,
        "synthetic_retry_count": 0, "terminal_reason": None, "stop_reason": None,
        "api_error_status": None, "exception_trusted_markers": [],
        "database_exception_summary_trusted_markers": [], "unclassified_exception": True,
        "exception_after_substantive_activity": True, "result_reward_present": True,
        "result_reward_value": 0, "result_exception_present": False, "result_exception_type": None,
        "result_termination_reason": None, "result_status": "completed",
        "database_result_consistency": "consistent",
    }
    metadata = {
        "artifact_read_status": {
            "transcript-id": {"artifact_id": "transcript-id", "artifact_type": "agent_transcript"},
            "stdout-id": {"artifact_id": "stdout-id", "artifact_type": "verifier_stdout"},
        }
    }
    packet = review.manual_packet_evidence(request, analysis, metadata)
    rendered = json.dumps(packet)
    assert secret not in rendered
    assert hidden not in rendered
    assert packet["transcript_activity"]["thinking_event_count"] == 1
    assert packet["transcript_activity"]["tool_calls"] == [{"name": "Write", "workspace_changing": True}]
    assert packet["ctrf_tests"] == [{"name": "safe test", "status": "failed", "failure_message": "safe failure"}]


def test_legacy_v111_verifier_environment_provenance_rule_does_not_change_current_classification() -> None:
    analysis = {
        "activity_subtype": "substantive_agent_activity",
        "termination_subtype": "none",
        "failure_subtype": "test_assertion_failure",
    }
    request = {
        "artifacts": [{
            "artifactType": "verifier_stdout",
            "text": "Installing environment dependencies\nAssertionError: expected 1, got 2",
        }]
    }
    assert review.legacy_v111_reclassification_labels(analysis, request) == [
        "reclassified_verifier_environment_v1_1_1"
    ]
    assert analysis["failure_subtype"] == "test_assertion_failure"


def test_required_trial_review_columns_are_written(tmp_path: Path) -> None:
    row = {
        "trial_id": "trial", "run_label": "run", "suite_id": "phase3-full-20", "arm_id": "arm",
        "task_id": "task", "task_attempt": 1, "run_trial_ordinal": 1, "raw_reward_present": True,
        "raw_reward": 1, "raw_outcome": "success", "execution_validity": "substantive",
        "activity_subtype": "substantive_agent_activity", "policy_disposition": "none_detected",
        "failure_subtype": "none", "termination_subtype": "none", "unclassified_exception": False,
        "exception_after_substantive_activity": False, "result_reward_present": True, "result_reward_value": 1,
        "result_exception_present": False, "result_exception_type": None, "result_termination_reason": None,
        "result_status": "completed", "database_result_consistency": "consistent",
        "telemetry_status": "consistent", "canonical_completeness": "8/8",
        "r2_indexed_completeness": "8/8", "r2_read_availability": "available", "analyzed_artifact_integrity_status": "verified",
        "size_metadata_status": "consistent", "router_observability": "unknown", "classification_confidence": "high",
        "evidence_complete": True, "manual_review_required": False, "manual_review_priority": "low",
        "analyzer_manual_review_priority": "low",
        "evidence_reasons": "[]", "supporting_artifact_ids": "[]", "analyzer_version": review.ANALYZER_VERSION,
        "cost_usd": 0.1, "runtime_seconds": 1, "exception_type": None, "bytes_read": 10,
        "oversized_artifacts": 0, "unavailable_artifacts": 0,
    }
    run = {
        "run_id": "run-id", "run_label": "run", "suite_id": "phase3-full-20", "arm_id": "arm",
        "status": "completed", "trial_count": 1, "task_count": 1, "required_task_count": 1,
        "full_suite_complete": True, "valid": True, "selected": True, "invalid_reason": None,
        "invalidated_at": None, "started_at": None, "finished_at": None,
    }
    scope = review.Scope(runs=[run], eligible_runs=[run], trials=[], artifacts=[])
    evidence = {
        "trial_id": "trial",
        "classification": {
            "raw_outcome": "success",
            "execution_validity": "substantive",
            "activity_subtype": "substantive_agent_activity",
            "policy_disposition": "none_detected",
            "failure_subtype": "none",
            "termination_subtype": "none",
        },
        "evidence": [],
        "manual_evidence": {
            "transcript_activity": {},
            "verifier_stdout_excerpt": None,
            "ctrf_tests": [],
            "exception_evidence": {},
            "harbor_result": {},
            "artifacts": [],
        },
        "supporting_artifact_ids": [],
        "legacy_v1_1_1_reclassifications": [],
    }
    review.generate_outputs(tmp_path, scope, [row], [evidence], "2026-07-31T00:00:00Z", {"bytes_read": 10}, 1, {})
    header = (tmp_path / "trial_review.csv").read_text().splitlines()[0]
    for field in (
        "trial_id", "raw_reward_present", "raw_outcome", "execution_validity", "activity_subtype",
        "policy_disposition", "failure_subtype", "telemetry_status", "canonical_completeness",
        "r2_indexed_completeness", "r2_read_availability", "analyzed_artifact_integrity_status", "size_metadata_status",
        "result_reward_present", "database_result_consistency", "termination_subtype",
        "router_observability", "classification_confidence", "evidence_complete",
        "manual_review_required", "evidence_reasons", "supporting_artifact_ids", "analyzer_version",
        "database_exception_summary", "database_exception_summary_present",
    ):
        assert field in header
    assert (tmp_path / "review_coverage.json").exists()
    manifest = json.loads((tmp_path / "review_manifest.json").read_text())
    assert manifest["analyzer_version"] == review.ANALYZER_VERSION
    assert manifest["generator_version"] == review.GENERATOR_VERSION
    assert manifest["outputs"]["trial_review.csv"]["sha256"] == review.sha256(tmp_path / "trial_review.csv")
    assert "scope_fingerprint_inputs" in manifest
    assert (tmp_path / "targeted_evidence_bundle.jsonl").exists()
    assert (tmp_path / "targeted_evidence_bundle_manifest.json").exists()
    assert not (tmp_path / "review_checkpoint.jsonl").exists()

    for filename in review.STRICT_SCAN_OUTPUT_NAMES:
        data = (tmp_path / filename).read_bytes()
        assert b"\r" not in data, filename
        assert all(not line.endswith((b" ", b"\t")) for line in data.split(b"\n")), filename

    for filename, expected_rows in manifest["row_counts"].items():
        if not filename.endswith(".csv"):
            continue
        with (tmp_path / filename).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            parsed_rows = list(reader)
        assert len(parsed_rows) == expected_rows, filename
        if expected_rows:
            assert reader.fieldnames
            assert len(reader.fieldnames) == len(set(reader.fieldnames)), filename

    with (tmp_path / "trial_review.csv").open(newline="", encoding="utf-8") as handle:
        parsed_trial_rows = list(csv.DictReader(handle))
    assert parsed_trial_rows[0]["trial_id"] == row["trial_id"]
    assert parsed_trial_rows[0]["raw_reward"] == str(row["raw_reward"])
    assert parsed_trial_rows[0]["execution_validity"] == row["execution_validity"]

    scan = subprocess.run(
        ["make", "--no-print-directory", "review-output-scan", f"REVIEW_OUTPUT_DIR={tmp_path}"],
        cwd=Path.cwd(), text=True, capture_output=True, check=False,
    )
    assert scan.returncode == 0, scan.stdout + scan.stderr
    assert "strict_output_scan\tclean" in scan.stdout


def test_review_output_scan_skips_a_missing_optional_directory_predictably(tmp_path: Path) -> None:
    missing = tmp_path / "not-generated"
    scan = subprocess.run(
        ["make", "--no-print-directory", "review-output-scan", f"REVIEW_OUTPUT_DIR={missing}"],
        cwd=Path.cwd(), text=True, capture_output=True, check=False,
    )
    assert scan.returncode == 0, scan.stdout + scan.stderr
    assert scan.stdout.strip() == f"review_output_scan\tskipped_missing_directory\t{missing}"
    assert scan.stderr == ""
