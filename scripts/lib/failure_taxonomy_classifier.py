"""Pure J2A failure and trajectory classification over frozen reviewed facts.

The classifier accepts already-loaded review/evidence mappings and the J1
registry. It performs no file, database, object-storage, or network access.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


CLASSIFIER_VERSION = "failure-taxonomy-classifier-v1.1.0-preview"

# Explicit classifier precedence. Registry ``order`` is display-only.
STRICT_PRIMARY_PRECEDENCE = (
    "verifier_environment_issue",
    "dependency_or_import_error",
    "syntax_or_compile_error",
    "timeout_inside_verifier",
    "runtime_exception_in_solution",
    "wrong_file_or_path",
)

_STRICT_PRIMARY_PATTERNS: Mapping[str, tuple[re.Pattern[str], ...]] = {
    "verifier_environment_issue": (
        re.compile(r"\b(?:verifier|test environment)\s+(?:is\s+)?(?:broken|unavailable|misconfigured)\b", re.I),
        re.compile(r"\bpytest\s+(?:internal|collection|configuration)\s+error\b", re.I),
    ),
    "dependency_or_import_error": (
        re.compile(r"\bModuleNotFoundError:"),
        re.compile(r"\bImportError:"),
        re.compile(r"\bNo module named\b", re.I),
        re.compile(r"\bcannot import name\b", re.I),
    ),
    "syntax_or_compile_error": (
        re.compile(r"\bSyntaxError:"),
        re.compile(r"\bIndentationError:"),
        re.compile(r"\bcompilation terminated\b", re.I),
        re.compile(r"\bundefined reference\b", re.I),
    ),
    "timeout_inside_verifier": (
        re.compile(r"\b(?:subprocess\.)?TimeoutExpired\b"),
        re.compile(r"\bpytest[-_ ]timeout\b", re.I),
        re.compile(r"\bverifier-invoked command timed out\b", re.I),
    ),
    "runtime_exception_in_solution": (
        re.compile(
            r"\b(?:TypeError|ValueError|KeyError|IndexError|AttributeError|RuntimeError|"
            r"ZeroDivisionError|OverflowError|RecursionError):"
        ),
        re.compile(r"\bsegmentation fault\b|\bcore dumped\b|\bprocess crashed\b", re.I),
    ),
    "wrong_file_or_path": (
        re.compile(r"\b(?:wrong|incorrect)\s+(?:file|path|directory)\b", re.I),
        re.compile(
            r"\b(?:wrote|written|created|placed)\s+(?:the\s+)?(?:file|output)\s+"
            r"(?:at|in)\s+(?:the\s+)?wrong\s+(?:path|directory|location)\b",
            re.I,
        ),
    ),
}

_ASSERTION_PATTERNS: Mapping[str, tuple[re.Pattern[str], ...]] = {
    "performance_threshold_failure": (
        re.compile(
            r"\b(?:performance|latency|throughput|memory usage|peak memory|resource usage)\b"
            r".{0,100}\b(?:threshold|limit|budget|requirement)\b",
            re.I | re.S,
        ),
        re.compile(
            r"\b(?:threshold|limit|budget|requirement)\b.{0,100}"
            r"\b(?:performance|latency|throughput|memory usage|peak memory|resource usage)\b",
            re.I | re.S,
        ),
    ),
    "numerical_or_data_mismatch": (
        re.compile(r"\b(?:allclose|isclose)\b", re.I),
        re.compile(r"\b(?:numeric|numerical)\s+(?:mismatch|difference)\b", re.I),
        re.compile(r"\b(?:shape|dtype)\s+mismatch\b", re.I),
        re.compile(r"\bexpected\s+[-+]?\d+(?:\.\d+)?\s*(?:,|but)\s+(?:got|received)\s+[-+]?\d", re.I),
    ),
    "missing_expected_file_or_content": (
        re.compile(
            r"\b(?:expected|required)\s+(?:file|content)\b.{0,100}\b(?:missing|absent|not found)\b",
            re.I | re.S,
        ),
        re.compile(
            r"\b(?:missing|absent)\s+(?:the\s+)?(?:expected|required)\s+(?:file|content)\b",
            re.I,
        ),
        re.compile(r"\bassert\b.{0,300}\.(?:exists|is_file|is_dir)\(\)", re.I),
    ),
    "behavior_mismatch": (
        re.compile(r"\bshould\s+(?:return|raise|reject|accept|preserve|produce|emit)\b", re.I),
        re.compile(r"\bexpected\s+(?:function|method|command|program|service)\s+to\b", re.I),
        re.compile(r"\bbehavio(?:u)?r(?:al)?\s+mismatch\b|\brequired behavio(?:u)?r\b", re.I),
    ),
    "output_mismatch": (
        re.compile(
            r"\b(?:stdout|stderr|output format|exact output|rendered output)\b"
            r".{0,100}\b(?:mismatch|differ(?:s|ed)?|expected|incorrect|wrong)\b",
            re.I | re.S,
        ),
        re.compile(
            r"\b(?:mismatch|incorrect|wrong)\b.{0,100}"
            r"\b(?:stdout|stderr|output format|exact output|rendered output)\b",
            re.I | re.S,
        ),
    ),
}

_PACKAGING_PATTERNS = (
    re.compile(r"\b(?:extraneous|unexpected|forbidden|extra)\s+(?:output\s+)?(?:file|artifact)\b", re.I),
    re.compile(r"\bpackag(?:e|ing)\s+(?:failure|issue|error)\b", re.I),
    re.compile(r"\b(?:wrong|incorrect)\s+(?:output\s+)?(?:path|placement|location)\b", re.I),
)

_BASELINE_VERIFIER_MAPPING = {
    "none": "none",
    "policy_refusal": "none",
    "extraneous_output_artifacts": "missing_or_wrong_output",
    "missing_required_output": "missing_or_wrong_output",
    "test_assertion_failure": "test_assertion_failure",
    "timeout": "none",
    "no_meaningful_code_change": "no_meaningful_code_change",
    "partial_solution": "partial_solution",
}

_ESTABLISHED_GENERIC_VERIFIER_FAILURES = {
    "normal_failure",
    "solution_failure",
    "task_failure",
    "verifier_failure",
}

_AXIS_ARTIFACT_TYPES = {
    "response_path_class": {"agent_transcript", "trajectory", "result"},
    "verifier_failure_category": {"verifier_stdout", "verifier_ctrf", "result"},
    "assertion_failure_category": {"verifier_ctrf", "verifier_stdout"},
    "trajectory_disposition": {"agent_transcript", "trajectory", "result", "exception"},
}


@dataclass(frozen=True)
class DiagnosisSpec:
    value: str
    confidence: str
    evidence_basis: tuple[str, ...]
    manual_review_required: bool


@dataclass(frozen=True)
class PytestFailureDetails:
    """Strict diagnostics retained from a pytest failure section only."""

    has_failure_section: bool
    diagnostic_lines: tuple[str, ...]


_PYTEST_FAILURES_HEADER = re.compile(r"^=+\s+FAILURES\s+=+$", re.I)
_PYTEST_SHORT_SUMMARY_HEADER = re.compile(
    r"^=+\s+short test summary info\s+=+$",
    re.I,
)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _source_confidence(review: Mapping[str, Any]) -> str:
    return "high" if (
        review.get("classification_confidence") == "high"
        and _as_bool(review.get("evidence_complete"))
    ) else "medium"


def _registry_entries(registry: Mapping[str, Any], axis_id: str) -> Mapping[str, Mapping[str, Any]]:
    for axis in registry.get("axes", []):
        if axis.get("id") == axis_id:
            return {entry["id"]: entry for entry in axis.get("entries", [])}
    raise ValueError(f"taxonomy axis missing: {axis_id}")


def _supporting_ids(
    evidence: Mapping[str, Any],
    review: Mapping[str, Any],
    axis_id: str,
) -> list[str]:
    raw_supporting = evidence.get("supporting_artifact_ids")
    if not isinstance(raw_supporting, list):
        try:
            raw_supporting = json.loads(str(review.get("supporting_artifact_ids") or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_supporting = []
    accepted = {str(value) for value in raw_supporting if value}
    artifacts = evidence.get("manual_evidence", {}).get("artifacts", [])
    relevant = _AXIS_ARTIFACT_TYPES[axis_id]
    return sorted({
        str(artifact.get("artifact_id"))
        for artifact in artifacts
        if isinstance(artifact, Mapping)
        and artifact.get("artifact_type") in relevant
        and artifact.get("artifact_id") in accepted
    })


def _failed_ctrf_messages(evidence: Mapping[str, Any]) -> tuple[str, ...]:
    tests = evidence.get("manual_evidence", {}).get("ctrf_tests", [])
    return tuple(
        str(test.get("failure_message"))
        for test in tests
        if isinstance(test, Mapping)
        and test.get("status") == "failed"
        and isinstance(test.get("failure_message"), str)
        and test.get("failure_message", "").strip()
    )


def extract_pytest_failure_details(evidence: Mapping[str, Any]) -> PytestFailureDetails:
    """Extract only pytest failure diagnostics from the reviewed stdout field.

    Text before the standard ``FAILURES`` header is ignored. Within that
    section, only pytest ``E   ...`` diagnostics and the explicitly marked
    failing ``> assert ...`` source line are eligible. The extracted text is
    used transiently for matching and is never placed in a diagnosis.
    """

    stdout = evidence.get("manual_evidence", {}).get("verifier_stdout_excerpt")
    if not isinstance(stdout, str):
        return PytestFailureDetails(False, ())

    lines = stdout.splitlines()
    start = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if _PYTEST_FAILURES_HEADER.fullmatch(line.strip())
        ),
        None,
    )
    if start is None:
        return PytestFailureDetails(False, ())

    end = next(
        (
            index
            for index in range(start, len(lines))
            if _PYTEST_SHORT_SUMMARY_HEADER.fullmatch(lines[index].strip())
        ),
        len(lines),
    )
    diagnostics: list[str] = []
    for line in lines[start:end]:
        left = line.lstrip()
        if re.match(r"^E\s{2,}\S", left):
            diagnostics.append(re.sub(r"^E\s+", "", left))
            continue
        if left.startswith(">"):
            failing_source = left[1:].strip()
            if re.match(r"^assert\b", failing_source):
                diagnostics.append(failing_source)

    return PytestFailureDetails(True, tuple(dict.fromkeys(diagnostics)))


def _matches(messages: Iterable[str], patterns: Sequence[re.Pattern[str]]) -> bool:
    return any(pattern.search(message) for message in messages for pattern in patterns)


def strict_primary_matches(messages: Iterable[str]) -> tuple[str, ...]:
    """Return field-scoped strict matches in explicit classifier precedence."""

    materialized = tuple(messages)
    return tuple(
        category
        for category in STRICT_PRIMARY_PRECEDENCE
        if _matches(materialized, _STRICT_PRIMARY_PATTERNS[category])
    )


def strict_assertion_matches(messages: Iterable[str]) -> tuple[str, ...]:
    """Return distinct assertion subtypes; registry order is not consulted."""

    materialized = tuple(messages)
    return tuple(
        category
        for category, patterns in _ASSERTION_PATTERNS.items()
        if _matches(materialized, patterns)
    )


def _strict_match_facts(
    value: str,
    ctrf_matches: Sequence[str],
    stdout_matches: Sequence[str],
) -> tuple[str, ...]:
    facts: list[str] = []
    if value in ctrf_matches:
        facts.append(f"ctrf.failed_message_match={value}")
    if value in stdout_matches:
        facts.append(f"verifier_stdout.failure_section_match={value}")
    return tuple(facts)


def _diagnosis(
    registry: Mapping[str, Any],
    axis_id: str,
    spec: DiagnosisSpec,
    evidence: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    entry = _registry_entries(registry, axis_id).get(spec.value)
    if entry is None:
        raise ValueError(f"taxonomy value missing: {axis_id}.{spec.value}")
    if not spec.evidence_basis:
        raise ValueError(f"empty evidence basis: {axis_id}.{spec.value}")
    return {
        "value": spec.value,
        "label": entry["label"],
        "definition": entry["definition"],
        "confidence": spec.confidence,
        "evidence_basis": list(spec.evidence_basis),
        "supporting_artifact_ids": _supporting_ids(evidence, review, axis_id),
        "manual_review_required": spec.manual_review_required,
    }


def classify_response_path(review: Mapping[str, Any]) -> DiagnosisSpec:
    activity = str(review.get("activity_subtype") or "")
    validity = str(review.get("execution_validity") or "")
    confidence = _source_confidence(review)
    mappings = {
        "synthetic_retry_empty_completion": "synthetic_retry_empty_completion",
        "empty_completion_after_long_api_path_wait": "empty_completion_after_long_api_path_wait",
        "thinking_only_empty_completion": "thinking_only_empty_completion",
        "empty_completion_zero_usage": "empty_completion",
    }
    if activity in mappings:
        value = "empty_completion" if activity == "empty_completion_zero_usage" else activity
        return DiagnosisSpec(
            value=value,
            confidence=confidence,
            evidence_basis=(
                f"rule=j2.response_path.{mappings[activity]}",
                f"review.activity_subtype={activity}",
                f"review.execution_validity={validity or 'not_recorded'}",
            ),
            manual_review_required=False,
        )
    if validity == "invalid_response_path":
        return DiagnosisSpec(
            value="invalid_response_path",
            confidence=confidence,
            evidence_basis=(
                "rule=j2.response_path.accepted_invalid_response_path",
                "review.execution_validity=invalid_response_path",
            ),
            manual_review_required=False,
        )
    if validity == "unknown":
        return DiagnosisSpec(
            value="unknown",
            confidence="low",
            evidence_basis=(
                "rule=j2.response_path.unknown",
                "review.execution_validity=unknown",
            ),
            manual_review_required=True,
        )
    return DiagnosisSpec(
        value="not_applicable",
        confidence=confidence,
        evidence_basis=(
            "rule=j2.response_path.not_applicable",
            f"review.execution_validity={validity or 'not_recorded'}",
        ),
        manual_review_required=False,
    )


def classify_verifier_failure(
    review: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> DiagnosisSpec:
    failure = str(review.get("failure_subtype") or "")
    baseline = _BASELINE_VERIFIER_MAPPING.get(failure)

    # Accepted independent/non-verifier categories and accepted output
    # categories are authoritative gates. Residual verifier text cannot
    # override them.
    if failure in {"none", "policy_refusal", "extraneous_output_artifacts", "missing_required_output"}:
        assert baseline is not None
        rule = "accepted_none" if baseline == "none" else "accepted_coarse_mapping"
        return DiagnosisSpec(
            value=baseline,
            confidence=_source_confidence(review),
            evidence_basis=(
                f"rule=j2.verifier.{rule}",
                f"review.failure_subtype={failure}",
            ),
            manual_review_required=False,
        )

    ctrf_matches = strict_primary_matches(_failed_ctrf_messages(evidence))
    stdout_matches = strict_primary_matches(
        extract_pytest_failure_details(evidence).diagnostic_lines
    )
    supported = set(ctrf_matches) | set(stdout_matches)

    # A generic termination timeout may refine only when the retained evidence
    # explicitly places the timeout inside verifier execution.
    if failure == "timeout":
        if "timeout_inside_verifier" in supported:
            value = "timeout_inside_verifier"
            return DiagnosisSpec(
                value=value,
                confidence="medium",
                evidence_basis=(
                    f"rule=j2.verifier.strict.{value}",
                    *_strict_match_facts(value, ctrf_matches, stdout_matches),
                    f"classifier.strict_primary_precedence={STRICT_PRIMARY_PRECEDENCE.index(value) + 1}",
                ),
                manual_review_required=True,
            )
        return DiagnosisSpec(
            value="none",
            confidence=_source_confidence(review),
            evidence_basis=(
                "rule=j2.verifier.accepted_none",
                "review.failure_subtype=timeout",
                "derived.verifier_specific_timeout=not_supported",
            ),
            manual_review_required=False,
        )

    # Accepted assertion failures are the J2A.1 source category eligible for
    # strict, field-scoped primary refinement. Precedence is explicit here and
    # never inferred from registry display order.
    if failure == "test_assertion_failure":
        strict = tuple(value for value in STRICT_PRIMARY_PRECEDENCE if value in supported)
        if strict:
            value = strict[0]
            return DiagnosisSpec(
                value=value,
                confidence="medium",
                evidence_basis=(
                    f"rule=j2.verifier.strict.{value}",
                    *_strict_match_facts(value, ctrf_matches, stdout_matches),
                    f"classifier.strict_primary_precedence={STRICT_PRIMARY_PRECEDENCE.index(value) + 1}",
                ),
                manual_review_required=True,
            )

    if baseline is not None:
        rule = "accepted_none" if baseline == "none" else "accepted_coarse_mapping"
        return DiagnosisSpec(
            value=baseline,
            confidence=_source_confidence(review),
            evidence_basis=(
                f"rule=j2.verifier.{rule}",
                f"review.failure_subtype={failure}",
            ),
            manual_review_required=False,
        )

    if failure in _ESTABLISHED_GENERIC_VERIFIER_FAILURES:
        return DiagnosisSpec(
            value="unclassified_failure",
            confidence="low",
            evidence_basis=(
                "rule=j2.verifier.established_unclassified_failure",
                f"review.failure_subtype={failure}",
            ),
            manual_review_required=True,
        )

    # Unknown source values do not turn raw failure into verifier failure.
    return DiagnosisSpec(
        value="none",
        confidence="low",
        evidence_basis=(
            "rule=j2.verifier.no_supported_verifier_category",
            f"review.failure_subtype={failure or 'not_recorded'}",
            f"review.raw_outcome={review.get('raw_outcome') or 'not_recorded'}",
        ),
        manual_review_required=True,
    )


def classify_assertion_failure(
    verifier: DiagnosisSpec,
    evidence: Mapping[str, Any],
) -> DiagnosisSpec:
    if verifier.value != "test_assertion_failure":
        return DiagnosisSpec(
            value="none",
            confidence="high",
            evidence_basis=(
                "rule=j2.assertion.not_applicable",
                f"derived.verifier_failure_category={verifier.value}",
            ),
            manual_review_required=False,
        )

    ctrf_matches = strict_assertion_matches(_failed_ctrf_messages(evidence))
    stdout_matches = strict_assertion_matches(
        extract_pytest_failure_details(evidence).diagnostic_lines
    )
    supported = set(ctrf_matches) | set(stdout_matches)
    matches = tuple(category for category in _ASSERTION_PATTERNS if category in supported)
    if len(matches) == 1:
        value = matches[0]
        match_facts = []
        if value in ctrf_matches:
            match_facts.append(f"ctrf.failed_message_match={value}")
        if value in stdout_matches:
            match_facts.append(f"verifier_stdout.failure_section_match={value}")
        return DiagnosisSpec(
            value=value,
            confidence="medium",
            evidence_basis=(
                f"rule=j2.assertion.strict.{value}",
                *match_facts,
            ),
            manual_review_required=True,
        )

    reason = "multiple_strict_matches" if len(matches) > 1 else "no_strict_match"
    basis = [
        "rule=j2.assertion.unclassified_assertion",
        f"derived.assertion_match_status={reason}",
    ]
    if ctrf_matches:
        basis.append(f"ctrf.assertion_matches={','.join(sorted(ctrf_matches))}")
    if stdout_matches:
        basis.append(
            f"verifier_stdout.failure_section_matches={','.join(sorted(stdout_matches))}"
        )
    return DiagnosisSpec(
        value="unclassified_assertion",
        confidence="low",
        evidence_basis=tuple(basis),
        manual_review_required=True,
    )


def _ctrf_counts(evidence: Mapping[str, Any]) -> tuple[int, int, int]:
    tests = evidence.get("manual_evidence", {}).get("ctrf_tests", [])
    passed = sum(1 for test in tests if isinstance(test, Mapping) and test.get("status") == "passed")
    failed = sum(1 for test in tests if isinstance(test, Mapping) and test.get("status") == "failed")
    return len(tests), passed, failed


def _absence_evidence_complete(review: Mapping[str, Any], evidence: Mapping[str, Any]) -> bool:
    if not _as_bool(review.get("evidence_complete")):
        return False
    completeness = evidence.get("read_completeness", {})
    return all(
        completeness.get(channel) == "complete"
        for channel in ("agent_transcript", "trajectory", "result", "verifier_stdout")
    )


def classify_trajectory(
    review: Mapping[str, Any],
    evidence: Mapping[str, Any],
    response: DiagnosisSpec,
    verifier: DiagnosisSpec,
    assertion: DiagnosisSpec,
) -> DiagnosisSpec:
    raw_outcome = str(review.get("raw_outcome") or "not_recorded")
    activity = str(review.get("activity_subtype") or "")
    termination = str(review.get("termination_subtype") or "")
    validity = str(review.get("execution_validity") or "")
    failure = str(review.get("failure_subtype") or "")
    confidence = _source_confidence(review)
    transcript = evidence.get("manual_evidence", {}).get("transcript_activity", {})
    total_tests, passed_tests, failed_tests = _ctrf_counts(evidence)

    if activity == "timeout_after_meaningful_activity" and termination == "timeout":
        return DiagnosisSpec(
            value="timeout_after_meaningful_progress",
            confidence=confidence,
            evidence_basis=(
                "rule=j2.trajectory.timeout_after_meaningful_progress",
                "review.activity_subtype=timeout_after_meaningful_activity",
                "review.termination_subtype=timeout",
                f"review.raw_outcome={raw_outcome}",
            ),
            manual_review_required=False,
        )

    packaging_evidence = _matches(_failed_ctrf_messages(evidence), _PACKAGING_PATTERNS)
    if (
        raw_outcome != "success"
        and validity == "substantive"
        and failure == "extraneous_output_artifacts"
        and _as_bool(review.get("evidence_complete"))
        and total_tests >= 2
        and failed_tests == 1
        and passed_tests >= 1
        and packaging_evidence
    ):
        return DiagnosisSpec(
            value="near_miss_cleanup_or_packaging_only",
            confidence="medium",
            evidence_basis=(
                "rule=j2.trajectory.near_miss_cleanup_or_packaging_only",
                "review.failure_subtype=extraneous_output_artifacts",
                f"ctrf.total_tests={total_tests}",
                "ctrf.failed_tests=1",
                f"ctrf.passed_tests={passed_tests}",
                "ctrf.failed_message_match=packaging_or_placement",
            ),
            manual_review_required=True,
        )

    no_independent_termination = (
        termination not in {"timeout", "provider_policy_refusal"}
        and failure not in {"timeout", "policy_refusal"}
        and response.value == "not_applicable"
    )
    if (
        raw_outcome != "success"
        and validity == "substantive"
        and verifier.value == "test_assertion_failure"
        and assertion.value == "behavior_mismatch"
        and _as_bool(review.get("evidence_complete"))
        and total_tests >= 2
        and failed_tests == 1
        and passed_tests >= 1
        and no_independent_termination
    ):
        return DiagnosisSpec(
            value="near_miss_one_behavioral_defect",
            confidence="medium",
            evidence_basis=(
                "rule=j2.trajectory.near_miss_one_behavioral_defect",
                "derived.verifier_failure_category=test_assertion_failure",
                "derived.assertion_failure_category=behavior_mismatch",
                f"ctrf.total_tests={total_tests}",
                "ctrf.failed_tests=1",
                f"ctrf.passed_tests={passed_tests}",
            ),
            manual_review_required=True,
        )

    absence_complete = _absence_evidence_complete(review, evidence)
    no_substantive_classification = (
        validity != "substantive"
        and activity not in {"substantive_agent_activity", "timeout_after_meaningful_activity"}
    )
    tool_calls = _as_int(transcript.get("tool_call_count"))
    workspace_calls = _as_int(transcript.get("workspace_changing_call_count"))
    substantive_steps = _as_int(transcript.get("substantive_trajectory_step_count"))
    if (
        absence_complete
        and no_substantive_classification
        and tool_calls == 0
        and workspace_calls == 0
        and substantive_steps == 0
    ):
        no_attempt_confidence = "medium" if activity == "activity_unknown" else "high"
        return DiagnosisSpec(
            value="no_substantive_attempt",
            confidence=no_attempt_confidence,
            evidence_basis=(
                "rule=j2.trajectory.no_substantive_attempt",
                "review.evidence_complete=true",
                f"review.execution_validity={validity or 'not_recorded'}",
                f"review.activity_subtype={activity or 'not_recorded'}",
                "transcript.tool_call_count=0",
                "transcript.workspace_changing_call_count=0",
                "transcript.substantive_trajectory_step_count=0",
            ),
            manual_review_required=True,
        )

    if raw_outcome == "success":
        return DiagnosisSpec(
            value="successful_completion",
            confidence=confidence,
            evidence_basis=(
                "rule=j2.trajectory.successful_completion",
                "review.raw_outcome=success",
                "derived.stronger_trajectory_disposition=not_supported",
            ),
            manual_review_required=False,
        )

    return DiagnosisSpec(
        value="indeterminate",
        confidence="low",
        evidence_basis=(
            "rule=j2.trajectory.indeterminate",
            f"review.raw_outcome={raw_outcome}",
            f"review.execution_validity={validity or 'not_recorded'}",
            "derived.specific_trajectory_rule=not_satisfied",
        ),
        manual_review_required=True,
    )


def classify_trial(
    review: Mapping[str, Any],
    evidence: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one frozen reviewed trial without mutating its inputs."""

    trial_id = str(review.get("trial_id") or "")
    if not trial_id or evidence.get("trial_id") != trial_id:
        raise ValueError("review/evidence trial identity mismatch")

    response = classify_response_path(review)
    verifier = classify_verifier_failure(review, evidence)
    assertion = classify_assertion_failure(verifier, evidence)
    trajectory = classify_trajectory(review, evidence, response, verifier, assertion)

    return {
        "trial_id": trial_id,
        "arm_id": str(review.get("arm_id") or ""),
        "task_id": str(review.get("task_id") or ""),
        "raw_outcome": str(review.get("raw_outcome") or "not_recorded"),
        "response_path_class": _diagnosis(registry, "response_path_class", response, evidence, review),
        "verifier_failure_category": _diagnosis(
            registry, "verifier_failure_category", verifier, evidence, review
        ),
        "assertion_failure_category": _diagnosis(
            registry, "assertion_failure_category", assertion, evidence, review
        ),
        "trajectory_disposition": _diagnosis(
            registry, "trajectory_disposition", trajectory, evidence, review
        ),
    }
