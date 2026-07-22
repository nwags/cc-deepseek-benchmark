import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path

from scripts.generate_phase3_qualitative_audit import (
    build_generation_command,
    build_arm_summary,
    build_arm_task_matrix,
    build_task_summary,
    filter_evidence_rows,
    format_tsv_row,
    generated_paths,
)


def sample_rows():
    return [
        {
            "arm_id": "router-anthropic-sonnet",
            "task_id": "task-a",
            "quality_flag": "success",
            "reward": Decimal("1"),
            "cost_usd": Decimal("0.25"),
            "missing_cost": False,
        },
        {
            "arm_id": "router-anthropic-sonnet",
            "task_id": "task-a",
            "quality_flag": "exception",
            "reward": Decimal("0"),
            "exception_type": "RuntimeError",
            "missing_cost": True,
        },
        {
            "arm_id": "router-anthropic-sonnet",
            "task_id": "task-b",
            "quality_flag": "suspect_noop_zero_token",
            "reward": Decimal("0"),
            "missing_cost": False,
        },
        {
            "arm_id": "router-gemini-flash",
            "task_id": "task-a",
            "quality_flag": "normal_failed_trial",
            "reward": Decimal("0"),
            "missing_cost": False,
        },
    ]


def test_filter_evidence_rows_excludes_plain_successes_by_default():
    rows = filter_evidence_rows(sample_rows())

    assert [row["quality_flag"] for row in rows] == [
        "exception",
        "suspect_noop_zero_token",
        "normal_failed_trial",
    ]


def test_filter_evidence_rows_can_include_successes():
    rows = filter_evidence_rows(sample_rows(), include_successes=True)

    assert len(rows) == 4


def test_build_arm_task_matrix_counts_quality_classes():
    matrix = build_arm_task_matrix(sample_rows())

    sonnet_task_a = next(
        row
        for row in matrix
        if row["arm_id"] == "router-anthropic-sonnet" and row["task_id"] == "task-a"
    )

    assert sonnet_task_a == {
        "arm_id": "router-anthropic-sonnet",
        "task_id": "task-a",
        "attempt_count": 2,
        "success_count": 1,
        "normal_failure_count": 0,
        "exception_count": 1,
        "suspect_noop_count": 0,
        "missing_cost_count": 1,
        "representative_exception_type": "RuntimeError",
        "review_status": "pending",
        "qualitative_summary": "",
    }


def test_build_arm_summary_sets_priority_from_anomalies():
    summary = build_arm_summary(sample_rows())
    by_arm = {row["arm_id"]: row for row in summary}

    assert by_arm["router-anthropic-sonnet"]["trial_count"] == 3
    assert by_arm["router-anthropic-sonnet"]["success_count"] == 1
    assert by_arm["router-anthropic-sonnet"]["exception_count"] == 1
    assert by_arm["router-anthropic-sonnet"]["suspect_noop_count"] == 1
    assert by_arm["router-anthropic-sonnet"]["dominant_exception_type"] == "RuntimeError"
    assert by_arm["router-anthropic-sonnet"]["review_priority"] == "medium"


def test_build_task_summary_counts_distinct_arms():
    summary = build_task_summary(sample_rows())
    by_task = {row["task_id"]: row for row in summary}

    assert by_task["task-a"]["arm_count"] == 2
    assert by_task["task-a"]["trial_count"] == 3
    assert by_task["task-a"]["success_count"] == 1
    assert by_task["task-a"]["exception_count"] == 1
    assert by_task["task-a"]["normal_failure_count"] == 1


def test_generated_paths_include_exception_review_targets():
    files = generated_paths(
        output_dir=Path("results/phase3/reporting"),
        docs_dir=Path("docs/reports/phase3"),
        datestamp="20260706",
    )

    assert files.exception_review_targets.as_posix() == (
        "results/phase3/reporting/phase3_exception_review_targets_20260706.tsv"
    )
    assert "phase3_exception_review_targets_20260706.tsv" in [
        path.name for path in files.as_list()
    ]


def test_build_generation_command_is_concrete_for_sonnet_focus():
    command = build_generation_command(
        suite_id="phase3-full-20",
        focus_arms=["router-anthropic-sonnet"],
        include_invalid=False,
        include_successes=False,
    )

    assert command == (
        "uv run --with 'psycopg[binary]' python "
        "scripts/generate_phase3_qualitative_audit.py "
        "--suite-id phase3-full-20 --focus-arm router-anthropic-sonnet"
    )
    assert "..." not in command


def test_format_tsv_row_preserves_trailing_empty_fields_without_trailing_tabs():
    line = format_tsv_row(["value", "", ""])

    assert line == 'value\t""\t""\n'
    assert not line.removesuffix("\n").endswith(("\t", " "))
    assert next(csv.reader(StringIO(line), delimiter="\t")) == ["value", "", ""]
