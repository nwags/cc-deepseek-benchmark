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
    result = classify(
        "pytest rootdir: /tests plugins: json-ctrf-0.3.5\n"
        "================ FAILURES ================\n"
        "E AssertionError: assert 1 == 2"
    )

    assert result.primary_category == "test_assertion_failure"
    assert result.secondary_category in {"behavior_mismatch", "output_mismatch"}
    assert result.secondary_category != "verifier_environment_issue"
    assert result.confidence == "high"
    assert result.needs_manual_review is False
    assert result.matched_signal
    assert result.matched_pattern
    assert result.classification_reason


def test_pytest_collection_error_is_verifier_environment_issue():
    result = classify(
        "ERROR collecting tests/test_outputs.py\n"
        "Interrupted: 1 error during collection"
    )

    assert result.primary_category == "verifier_environment_issue"
    assert result.confidence == "high"
    assert result.needs_manual_review is False
    assert "collect" in result.matched_signal.lower()


def test_import_error_in_verifier_setup_is_environment_issue():
    result = classify("ImportError in verifier setup: cannot import helper from conftest")

    assert result.primary_category == "verifier_environment_issue"
    assert result.confidence == "high"
    assert result.needs_manual_review is False


def test_runtime_comparison_assertion_is_performance_threshold_failure():
    result = classify(
        "================ FAILURES ================\n"
        "test_compare_golden_vs_solution_runtime\n"
        "E AssertionError: assert solution_runtime <= golden_runtime"
    )

    assert result.primary_category == "test_assertion_failure"
    assert result.secondary_category == "performance_threshold_failure"
    assert result.confidence == "high"


def test_data_matches_assertion_is_numerical_or_data_mismatch():
    result = classify(
        "================ FAILURES ================\n"
        "test_data_matches\n"
        "E AssertionError: assert actual == expected"
    )

    assert result.primary_category == "test_assertion_failure"
    assert result.secondary_category == "numerical_or_data_mismatch"
    assert result.confidence == "high"


def test_named_assertion_failures_use_neutral_secondary_categories():
    expected_categories = {
        "test_hello_html_exists": "missing_expected_file_or_content",
        "test_password_match": "output_mismatch",
        "test_fibonacci_polyglot": "behavior_mismatch",
        "test_tasks_cancel_above_max_concurrent": "behavior_mismatch",
    }

    for test_name, expected_category in expected_categories.items():
        result = classify(
            "================ FAILURES ================\n"
            f"{test_name}\n"
            "E AssertionError: assert actual == expected"
        )

        assert result.primary_category == "test_assertion_failure"
        assert result.secondary_category == expected_category
        assert result.secondary_category != "verifier_environment_issue"


def test_untyped_assertion_failure_requires_manual_review():
    result = classify("================ FAILURES ================\nAssertionError")

    assert result.primary_category == "test_assertion_failure"
    assert result.secondary_category == "unknown_assertion_failure"
    assert result.confidence == "medium"
    assert result.needs_manual_review is True


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
