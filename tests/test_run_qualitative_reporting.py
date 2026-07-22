from pathlib import Path

from scripts.run_qualitative_reporting import (
    build_reporting_plan,
    main,
    missing_environment_variables,
)


def test_build_reporting_plan_constructs_full_refresh_commands():
    plan = build_reporting_plan(
        suite_id="phase3-full-20",
        datestamp="20260709",
        focus_arms=["router-anthropic-sonnet", "router-gemini-flash"],
        include_invalid=True,
        run_exception_classification=True,
        run_normal_failure_classification=True,
    )

    assert [command.label for command in plan.commands] == [
        "qualitative audit generation",
        "exception artifact classification",
        "normal failure classification",
    ]
    assert plan.commands[0].argv == (
        "uv",
        "run",
        "--with",
        "psycopg[binary]",
        "python",
        "scripts/generate_phase3_qualitative_audit.py",
        "--suite-id",
        "phase3-full-20",
        "--date",
        "20260709",
        "--focus-arm",
        "router-anthropic-sonnet",
        "--focus-arm",
        "router-gemini-flash",
        "--include-invalid",
    )
    assert plan.commands[1].argv == (
        "uv",
        "run",
        "--with",
        "psycopg[binary]",
        "python",
        "scripts/classify_phase3_exception_artifacts.py",
        "--targets",
        "results/phase3/reporting/phase3_exception_review_targets_20260709.tsv",
        "--date",
        "20260709",
        "--docs-report",
        "docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_20260709.md",
    )
    assert plan.commands[2].argv == (
        "uv",
        "run",
        "--with",
        "psycopg[binary]",
        "python",
        "scripts/classify_phase3_normal_failures.py",
        "--trial-evidence",
        "results/phase3/reporting/phase3_trial_evidence_audit_20260709.tsv",
        "--date",
        "20260709",
        "--docs-report",
        "docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_20260709.md",
        "--focus-arm",
        "router-anthropic-sonnet",
        "--focus-arm",
        "router-gemini-flash",
    )


def test_build_reporting_plan_can_skip_classification_steps():
    plan = build_reporting_plan(
        suite_id="phase3-full-20",
        datestamp="20260709",
        focus_arms=[],
        include_invalid=False,
        run_exception_classification=False,
        run_normal_failure_classification=False,
    )

    assert [command.label for command in plan.commands] == ["qualitative audit generation"]
    assert Path("results/phase3/reporting/phase3_exception_classification_20260709.tsv") not in plan.output_paths
    assert Path("results/phase3/reporting/phase3_normal_failure_classification_20260709.tsv") not in plan.output_paths


def test_missing_environment_variables_requires_only_supabase_when_classifications_are_skipped():
    missing = missing_environment_variables(
        {},
        run_exception_classification=False,
        run_normal_failure_classification=False,
    )

    assert missing == ["SUPABASE_DB_URL"]


def test_missing_environment_variables_requires_r2_for_any_classification_step():
    missing = missing_environment_variables(
        {"SUPABASE_DB_URL": "postgres://example", "R2_ENDPOINT_URL": "https://example.invalid"},
        run_exception_classification=True,
        run_normal_failure_classification=False,
    )

    assert missing == ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]


def test_missing_environment_variables_accepts_complete_required_env_without_exposing_values():
    missing = missing_environment_variables(
        {
            "SUPABASE_DB_URL": "postgres://secret.example",
            "R2_ENDPOINT_URL": "https://r2.example",
            "R2_ACCESS_KEY_ID": "access-key",
            "R2_SECRET_ACCESS_KEY": "secret-key",
        },
        run_exception_classification=True,
        run_normal_failure_classification=True,
    )

    assert missing == []


def test_main_missing_env_message_prints_names_only(monkeypatch, capsys):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://secret.example")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2.example")
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)

    result = main(["--date", "20260709", "--skip-normal-failure-classification"])

    captured = capsys.readouterr()
    assert result == 2
    assert "R2_ACCESS_KEY_ID" in captured.err
    assert "R2_SECRET_ACCESS_KEY" in captured.err
    assert "postgres://secret.example" not in captured.err
    assert "https://r2.example" not in captured.err
