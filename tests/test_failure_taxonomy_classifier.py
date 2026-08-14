from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from scripts.lib.failure_taxonomy_classifier import (
    DiagnosisSpec,
    classify_trajectory,
    classify_trial,
    extract_pytest_failure_details,
)


REGISTRY = json.loads(Path("configs/dashboard/failure_taxonomy_v1.json").read_text())
DIAGNOSIS_FIELDS = {
    "value",
    "label",
    "definition",
    "confidence",
    "evidence_basis",
    "supporting_artifact_ids",
    "manual_review_required",
}


def review(**overrides: Any) -> dict[str, Any]:
    row = {
        "trial_id": "00000000-0000-0000-0000-000000000001",
        "arm_id": "fixture-arm",
        "task_id": "terminal-bench-2.0:fixture-task",
        "raw_outcome": "success",
        "execution_validity": "substantive",
        "activity_subtype": "substantive_agent_activity",
        "failure_subtype": "none",
        "termination_subtype": "none",
        "classification_confidence": "high",
        "evidence_complete": "True",
        "supporting_artifact_ids": json.dumps([
            "artifact-transcript",
            "artifact-trajectory",
            "artifact-result",
            "artifact-verifier",
            "artifact-ctrf",
        ]),
    }
    row.update(overrides)
    return row


def ctrf(status: str, message: str | None = None, name: str = "test_fixture") -> dict[str, Any]:
    return {"status": status, "failure_message": message, "name": name}


def evidence(
    *,
    tests: list[dict[str, Any]] | None = None,
    tool_calls: int = 2,
    workspace_calls: int = 1,
    substantive_steps: int = 3,
    complete: bool = True,
    verifier_stdout: str = "",
) -> dict[str, Any]:
    completeness = "complete" if complete else "partial"
    return {
        "trial_id": "00000000-0000-0000-0000-000000000001",
        "hidden_reasoning_retained": False,
        "supporting_artifact_ids": [
            "artifact-transcript",
            "artifact-trajectory",
            "artifact-result",
            "artifact-verifier",
            "artifact-ctrf",
        ],
        "read_completeness": {
            "agent_transcript": completeness,
            "trajectory": completeness,
            "result": completeness,
            "verifier_stdout": completeness,
            "verifier_ctrf": completeness,
        },
        "manual_evidence": {
            "artifacts": [
                {"artifact_id": "artifact-transcript", "artifact_type": "agent_transcript"},
                {"artifact_id": "artifact-trajectory", "artifact_type": "trajectory"},
                {"artifact_id": "artifact-result", "artifact_type": "result"},
                {"artifact_id": "artifact-verifier", "artifact_type": "verifier_stdout"},
                {"artifact_id": "artifact-ctrf", "artifact_type": "verifier_ctrf"},
            ],
            "ctrf_tests": tests or [],
            "verifier_stdout_excerpt": verifier_stdout,
            "transcript_activity": {
                "hidden_reasoning_retained": False,
                "tool_call_count": tool_calls,
                "workspace_changing_call_count": workspace_calls,
                "substantive_trajectory_step_count": substantive_steps,
            },
        },
    }


def pytest_failure_stdout(*diagnostics: str, setup: str = "") -> str:
    body = "\n".join(diagnostics)
    return (
        f"{setup}\n"
        "=================================== FAILURES ===================================\n"
        "_______________________________ test_fixture _______________________________\n"
        f"{body}\n"
        "=========================== short test summary info ============================\n"
        "FAILED test_fixture.py::test_fixture\n"
    )


def classify(row: dict[str, Any] | None = None, packet: dict[str, Any] | None = None, registry: Any = None):
    return classify_trial(row or review(), packet or evidence(), registry or REGISTRY)


def test_every_axis_has_exact_j1_diagnosis_fields_and_structured_nonempty_basis() -> None:
    result = classify()
    for axis in (
        "response_path_class",
        "verifier_failure_category",
        "assertion_failure_category",
        "trajectory_disposition",
    ):
        diagnosis = result[axis]
        assert set(diagnosis) == DIAGNOSIS_FIELDS
        assert diagnosis["evidence_basis"]
        assert all("excerpt" not in fact.lower() for fact in diagnosis["evidence_basis"])
        assert all(artifact_id.startswith("artifact-") for artifact_id in diagnosis["supporting_artifact_ids"])


def test_empty_completion_zero_usage_normalizes_to_public_empty_completion() -> None:
    result = classify(review(activity_subtype="empty_completion_zero_usage", execution_validity="invalid_response_path"))
    assert result["response_path_class"]["value"] == "empty_completion"


def test_successful_timeout_precedes_ordinary_successful_completion() -> None:
    result = classify(review(
        raw_outcome="success",
        activity_subtype="timeout_after_meaningful_activity",
        termination_subtype="timeout",
    ))
    assert result["trajectory_disposition"]["value"] == "timeout_after_meaningful_progress"
    assert result["trajectory_disposition"]["value"] != "successful_completion"


def test_ordinary_success_without_stronger_trajectory_evidence_is_successful_completion() -> None:
    assert classify()["trajectory_disposition"]["value"] == "successful_completion"


def test_policy_refusal_and_generic_timeout_remain_independent_from_verifier_axis() -> None:
    refused = classify(review(
        raw_outcome="failure",
        execution_validity="policy_blocked",
        activity_subtype="provider_policy_refusal",
        failure_subtype="policy_refusal",
        termination_subtype="provider_policy_refusal",
    ))
    assert refused["verifier_failure_category"]["value"] == "none"

    timed_out = classify(review(
        raw_outcome="failure",
        activity_subtype="activity_unknown",
        execution_validity="unknown",
        failure_subtype="timeout",
        termination_subtype="timeout",
    ), evidence(tests=[ctrf("failed", "The test failed in the call phase")]))
    assert timed_out["verifier_failure_category"]["value"] == "none"
    assert timed_out["verifier_failure_category"]["value"] != "timeout_inside_verifier"

    verifier_timeout = classify(
        review(raw_outcome="failure", failure_subtype="timeout", termination_subtype="timeout"),
        evidence(tests=[ctrf("failed", "subprocess.TimeoutExpired while verifier-invoked command ran")]),
    )
    assert verifier_timeout["verifier_failure_category"]["value"] == "timeout_inside_verifier"


def test_residual_strict_markers_cannot_override_policy_or_generic_timeout() -> None:
    residual = evidence(
        tests=[ctrf("failed", "ModuleNotFoundError: No module named 'stale'")],
        verifier_stdout=pytest_failure_stdout(
            "E       ModuleNotFoundError: No module named 'stale'",
            "E       RuntimeError: stale diagnostic",
        ),
    )
    refused = classify(
        review(
            raw_outcome="failure",
            execution_validity="policy_blocked",
            activity_subtype="provider_policy_refusal",
            failure_subtype="policy_refusal",
            termination_subtype="provider_policy_refusal",
        ),
        residual,
    )
    assert refused["verifier_failure_category"]["value"] == "none"

    ordinary_success = classify(review(failure_subtype="none"), residual)
    assert ordinary_success["verifier_failure_category"]["value"] == "none"

    timed_out = classify(
        review(
            raw_outcome="failure",
            execution_validity="unknown",
            activity_subtype="activity_unknown",
            failure_subtype="timeout",
            termination_subtype="timeout",
        ),
        residual,
    )
    assert timed_out["verifier_failure_category"]["value"] == "none"


def test_explicit_verifier_timeout_remains_eligible_for_timeout_refinement() -> None:
    result = classify(
        review(raw_outcome="failure", failure_subtype="timeout", termination_subtype="timeout"),
        evidence(verifier_stdout=pytest_failure_stdout("E       subprocess.TimeoutExpired: verifier command")),
    )
    assert result["verifier_failure_category"]["value"] == "timeout_inside_verifier"
    assert "verifier_stdout.failure_section_match=timeout_inside_verifier" in result[
        "verifier_failure_category"
    ]["evidence_basis"]


def test_pytest_extractor_ignores_setup_and_keeps_only_failure_diagnostics() -> None:
    packet = evidence(verifier_stdout=pytest_failure_stdout(
        ">       assert output == expected",
        "E       AssertionError: assert 'actual' == 'expected'",
        setup="ModuleNotFoundError: setup probe was optional",
    ))
    details = extract_pytest_failure_details(packet)
    assert details.has_failure_section is True
    assert details.diagnostic_lines == (
        "assert output == expected",
        "AssertionError: assert 'actual' == 'expected'",
    )
    result = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        packet,
    )
    assert result["verifier_failure_category"]["value"] == "test_assertion_failure"
    assert result["assertion_failure_category"]["value"] == "unclassified_assertion"


def test_task_id_and_ctrf_test_name_cannot_trigger_strict_categories() -> None:
    row = review(
        raw_outcome="failure",
        task_id="terminal-bench-2.0:custom-memory-heap-crash",
        failure_subtype="test_assertion_failure",
    )
    packet = evidence(tests=[ctrf(
        "failed",
        "The test failed in the call phase due to an assertion error",
        "wrong file timeout output ModuleNotFoundError SyntaxError",
    )])
    result = classify(row, packet)
    assert result["verifier_failure_category"]["value"] == "test_assertion_failure"
    assert result["assertion_failure_category"]["value"] == "unclassified_assertion"


def test_strict_dependency_and_syntax_messages_refine_primary_category() -> None:
    base = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    dependency = classify(base, evidence(tests=[ctrf("failed", "ModuleNotFoundError: No module named 'widget'")]))
    assert dependency["verifier_failure_category"]["value"] == "dependency_or_import_error"
    assert dependency["assertion_failure_category"]["value"] == "none"

    syntax = classify(base, evidence(tests=[ctrf("failed", "SyntaxError: invalid syntax at submitted.py:4")]))
    assert syntax["verifier_failure_category"]["value"] == "syntax_or_compile_error"
    assert syntax["assertion_failure_category"]["value"] == "none"

    wrong_path = classify(base, evidence(tests=[ctrf(
        "failed", "The submitted file was created in the wrong directory",
    )]))
    assert wrong_path["verifier_failure_category"]["value"] == "wrong_file_or_path"


def test_failure_section_dependency_refines_assertion_primary_without_copying_text() -> None:
    marker = "private-looking-but-sanitized-fixture-marker"
    packet = evidence(verifier_stdout=pytest_failure_stdout(
        f"E       ModuleNotFoundError: No module named '{marker}'",
    ))
    result = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        packet,
    )
    diagnosis = result["verifier_failure_category"]
    assert diagnosis["value"] == "dependency_or_import_error"
    assert "verifier_stdout.failure_section_match=dependency_or_import_error" in diagnosis[
        "evidence_basis"
    ]
    assert "artifact-verifier" in diagnosis["supporting_artifact_ids"]
    assert marker not in json.dumps(result)


def test_traceback_alone_does_not_refine_runtime_exception() -> None:
    result = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        evidence(verifier_stdout=pytest_failure_stdout("E       Traceback (most recent call last):")),
    )
    assert result["verifier_failure_category"]["value"] == "test_assertion_failure"


def test_generic_error_does_not_trigger_syntax_compile_or_runtime_category() -> None:
    result = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        evidence(tests=[ctrf("failed", "The test reported a generic error")]),
    )
    assert result["verifier_failure_category"]["value"] == "test_assertion_failure"


def test_extraneous_output_maps_to_missing_or_wrong_output() -> None:
    result = classify(review(raw_outcome="failure", failure_subtype="extraneous_output_artifacts"))
    assert result["verifier_failure_category"]["value"] == "missing_or_wrong_output"


def test_assertion_subtype_requires_final_assertion_primary_and_unique_message_match() -> None:
    behavior_message = "The service should return 200 for a valid request"
    not_assertion = classify(
        review(raw_outcome="failure", failure_subtype="missing_required_output"),
        evidence(tests=[ctrf("failed", behavior_message)]),
    )
    assert not_assertion["assertion_failure_category"]["value"] == "none"

    unique = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        evidence(tests=[ctrf("failed", behavior_message)]),
    )
    assert unique["assertion_failure_category"]["value"] == "behavior_mismatch"


def test_zero_or_multiple_strict_assertion_matches_are_unclassified() -> None:
    row = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    zero = classify(row, evidence(tests=[ctrf("failed", "The test failed in the call phase")]))
    assert zero["assertion_failure_category"]["value"] == "unclassified_assertion"

    multiple = classify(row, evidence(tests=[ctrf(
        "failed",
        "The service should return 200, but the exact output format mismatch was incorrect",
    )]))
    assert multiple["assertion_failure_category"]["value"] == "unclassified_assertion"


def test_failure_section_exists_assertion_is_missing_content_but_generic_equality_is_not() -> None:
    row = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    missing = classify(
        row,
        evidence(verifier_stdout=pytest_failure_stdout(
            ">       assert expected_path.exists()",
            "E       AssertionError: assert False",
        )),
    )
    diagnosis = missing["assertion_failure_category"]
    assert diagnosis["value"] == "missing_expected_file_or_content"
    assert "verifier_stdout.failure_section_match=missing_expected_file_or_content" in diagnosis[
        "evidence_basis"
    ]

    equality = classify(
        row,
        evidence(verifier_stdout=pytest_failure_stdout(
            ">       assert actual == expected",
            "E       AssertionError: assert 1 == 2",
        )),
    )
    assert equality["assertion_failure_category"]["value"] == "unclassified_assertion"


def test_multiple_failure_section_assertion_subtypes_remain_unclassified() -> None:
    result = classify(
        review(raw_outcome="failure", failure_subtype="test_assertion_failure"),
        evidence(verifier_stdout=pytest_failure_stdout(
            "E       AssertionError: service should return the required behavior",
            "E       AssertionError: exact output format mismatch",
        )),
    )
    diagnosis = result["assertion_failure_category"]
    assert diagnosis["value"] == "unclassified_assertion"
    assert any("multiple_strict_matches" in fact for fact in diagnosis["evidence_basis"])


def test_single_test_failure_is_not_near_miss_but_supported_multi_test_behavior_can_be() -> None:
    row = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    failed = ctrf("failed", "The service should return 200 for a valid request")
    single = classify(row, evidence(tests=[failed]))
    assert single["trajectory_disposition"]["value"] != "near_miss_one_behavioral_defect"

    multi = classify(row, evidence(tests=[failed, ctrf("passed")]))
    assert multi["assertion_failure_category"]["value"] == "behavior_mismatch"
    assert multi["trajectory_disposition"]["value"] == "near_miss_one_behavioral_defect"
    assert multi["trajectory_disposition"]["manual_review_required"] is True


def test_unknown_response_path_cannot_produce_behavioral_near_miss() -> None:
    row = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    packet = evidence(tests=[
        ctrf("failed", "The service should return 200 for a valid request"),
        ctrf("passed"),
    ])
    result = classify_trajectory(
        row,
        packet,
        DiagnosisSpec("unknown", "low", ("fixture=response_unknown",), True),
        DiagnosisSpec(
            "test_assertion_failure", "high", ("fixture=assertion_primary",), False
        ),
        DiagnosisSpec("behavior_mismatch", "medium", ("fixture=behavior",), True),
    )
    assert result.value != "near_miss_one_behavioral_defect"


def test_incomplete_absence_evidence_is_indeterminate_but_complete_zero_activity_is_no_attempt() -> None:
    row = review(
        raw_outcome="failure",
        execution_validity="unknown",
        activity_subtype="activity_unknown",
        failure_subtype="timeout",
        termination_subtype="timeout",
    )
    incomplete = classify(
        review(**{**row, "evidence_complete": "False"}),
        evidence(tool_calls=0, workspace_calls=0, substantive_steps=0, complete=False),
    )
    assert incomplete["trajectory_disposition"]["value"] == "indeterminate"

    complete = classify(row, evidence(tool_calls=0, workspace_calls=0, substantive_steps=0))
    assert complete["trajectory_disposition"]["value"] == "no_substantive_attempt"
    assert complete["trajectory_disposition"]["confidence"] == "medium"
    assert complete["trajectory_disposition"]["manual_review_required"] is True


def test_classifier_precedence_is_explicit_and_not_registry_display_order() -> None:
    row = review(raw_outcome="failure", failure_subtype="test_assertion_failure")
    packet = evidence(tests=[ctrf("failed", "ModuleNotFoundError: followed by SyntaxError:")])
    baseline = classify(row, packet)
    assert baseline["verifier_failure_category"]["value"] == "dependency_or_import_error"

    reordered = copy.deepcopy(REGISTRY)
    for axis in reordered["axes"]:
        for index, entry in enumerate(reversed(axis["entries"]), start=1):
            entry["order"] = index
    changed_order = classify(row, packet, reordered)
    assert changed_order["verifier_failure_category"]["value"] == "dependency_or_import_error"
