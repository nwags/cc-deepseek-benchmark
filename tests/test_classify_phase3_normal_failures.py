from scripts.classify_phase3_normal_failures import classify_normal_failure


def classify(snippet: str):
    return classify_normal_failure(
        target_row={
            "task_id": "terminal-bench-2.0:synthetic",
            "runtime_seconds": "45",
        },
        evidence_by_type={"verifier_stdout": snippet},
    )


def test_pytest_assertion_failure_classification():
    result = classify("pytest reported failures\nE AssertionError: assert 1 == 2")

    assert result.primary_category == "test_assertion_failure"
    assert result.confidence == "high"
    assert result.needs_manual_review is False
    assert result.matched_signal
    assert result.matched_pattern


def test_dependency_or_import_error_classification():
    result = classify("ModuleNotFoundError: No module named 'missing_package'")

    assert result.primary_category == "dependency_or_import_error"
    assert result.confidence == "high"
    assert result.matched_signal == "ModuleNotFoundError"


def test_syntax_or_compile_error_classification():
    result = classify("SyntaxError: invalid syntax while importing solution.py")

    assert result.primary_category == "syntax_or_compile_error"
    assert result.confidence == "high"
    assert result.matched_signal == "SyntaxError"


def test_wrong_file_or_path_classification():
    result = classify("FileNotFoundError: [Errno 2] No such file or directory: '/app/output.txt'")

    assert result.primary_category == "wrong_file_or_path"
    assert result.confidence == "high"
    assert result.matched_signal == "FileNotFoundError"


def test_timeout_inside_verifier_classification():
    result = classify("The verifier command timed out after 60 seconds")

    assert result.primary_category == "timeout_inside_verifier"
    assert result.confidence == "high"
    assert "timed out" in result.evidence_excerpt


def test_unknown_normal_failure_requires_manual_review():
    result = classify("The answer was not accepted, but no recognizable diagnostic was emitted.")

    assert result.primary_category == "unknown_normal_failure"
    assert result.confidence == "low"
    assert result.needs_manual_review is True
    assert result.matched_signal == ""
    assert result.matched_pattern == ""
