#!/usr/bin/env python3
"""Run the full Phase 3 qualitative reporting refresh.

The runner is generically named because this reporting workflow is expected to
survive the Phase 3 branch, while its current defaults remain Phase 3-specific.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.classify_phase3_exception_artifacts import generated_paths as exception_generated_paths
from scripts.classify_phase3_normal_failures import generated_paths as normal_generated_paths
from scripts.generate_phase3_qualitative_audit import (
    DEFAULT_SUITE_ID,
    generated_paths as audit_generated_paths,
    utc_datestamp,
)


DEFAULT_OUTPUT_DIR = Path("results/phase3/reporting")
DEFAULT_DOCS_DIR = Path("docs/reports/phase3")
PSYCOPG_UV_PREFIX = ("uv", "run", "--with", "psycopg[binary]", "python")
AUDIT_REQUIRED_ENV = ("SUPABASE_DB_URL",)
R2_REQUIRED_ENV = ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")


@dataclass(frozen=True)
class ReportingCommand:
    label: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class ReportingPlan:
    commands: tuple[ReportingCommand, ...]
    output_paths: tuple[Path, ...]


def script_command(script_path: str, *args: str) -> tuple[str, ...]:
    return (*PSYCOPG_UV_PREFIX, script_path, *args)


def build_reporting_plan(
    *,
    suite_id: str,
    datestamp: str,
    focus_arms: Sequence[str],
    include_invalid: bool,
    run_exception_classification: bool,
    run_normal_failure_classification: bool,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    docs_dir: Path = DEFAULT_DOCS_DIR,
) -> ReportingPlan:
    audit_files = audit_generated_paths(output_dir, docs_dir, datestamp)
    docs_report = audit_files.markdown_review

    audit_args = ["--suite-id", suite_id, "--date", datestamp]
    for arm in focus_arms:
        audit_args.extend(["--focus-arm", arm])
    if include_invalid:
        audit_args.append("--include-invalid")

    commands = [
        ReportingCommand(
            label="qualitative audit generation",
            argv=script_command("scripts/generate_phase3_qualitative_audit.py", *audit_args),
        )
    ]
    output_paths = list(audit_files.as_list())

    if run_exception_classification:
        exception_classification, exception_summary = exception_generated_paths(output_dir, datestamp)
        commands.append(
            ReportingCommand(
                label="exception artifact classification",
                argv=script_command(
                    "scripts/classify_phase3_exception_artifacts.py",
                    "--targets",
                    audit_files.exception_review_targets.as_posix(),
                    "--date",
                    datestamp,
                    "--docs-report",
                    docs_report.as_posix(),
                ),
            )
        )
        output_paths.extend([exception_classification, exception_summary, docs_report])

    if run_normal_failure_classification:
        normal_classification, normal_summary = normal_generated_paths(output_dir, datestamp)
        normal_args = [
            "--trial-evidence",
            audit_files.trial_evidence.as_posix(),
            "--date",
            datestamp,
            "--docs-report",
            docs_report.as_posix(),
        ]
        for arm in focus_arms:
            normal_args.extend(["--focus-arm", arm])
        commands.append(
            ReportingCommand(
                label="normal failure classification",
                argv=script_command("scripts/classify_phase3_normal_failures.py", *normal_args),
            )
        )
        output_paths.extend([normal_classification, normal_summary, docs_report])

    return ReportingPlan(commands=tuple(commands), output_paths=dedupe_paths(output_paths))


def dedupe_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def missing_environment_variables(
    env: Mapping[str, str | None],
    *,
    run_exception_classification: bool,
    run_normal_failure_classification: bool,
) -> list[str]:
    required = list(AUDIT_REQUIRED_ENV)
    if run_exception_classification or run_normal_failure_classification:
        required.extend(R2_REQUIRED_ENV)
    return [name for name in required if not env.get(name)]


def run_command(command: ReportingCommand) -> None:
    print(f"Running {command.label}: {shlex.join(command.argv)}")
    subprocess.run(command.argv, cwd=REPO_ROOT, check=True)


def print_output_paths(paths: Sequence[Path]) -> None:
    print("Generated output paths:")
    for path in paths:
        print(path.as_posix())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-id", default=DEFAULT_SUITE_ID)
    parser.add_argument("--date", default=utc_datestamp(), help="UTC datestamp in YYYYMMDD format.")
    parser.add_argument("--focus-arm", action="append", default=[], help="Arm to include. Repeatable.")
    parser.add_argument("--include-invalid", action="store_true", help="Include invalid/quarantined rows and label them.")
    parser.add_argument(
        "--skip-exception-classification",
        action="store_true",
        help="Run audit generation but skip exception artifact classification.",
    )
    parser.add_argument(
        "--skip-normal-failure-classification",
        action="store_true",
        help="Run audit generation but skip normal verifier failure classification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_exception_classification = not args.skip_exception_classification
    run_normal_failure_classification = not args.skip_normal_failure_classification

    missing = missing_environment_variables(
        os.environ,
        run_exception_classification=run_exception_classification,
        run_normal_failure_classification=run_normal_failure_classification,
    )
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    plan = build_reporting_plan(
        suite_id=args.suite_id,
        datestamp=args.date,
        focus_arms=args.focus_arm,
        include_invalid=args.include_invalid,
        run_exception_classification=run_exception_classification,
        run_normal_failure_classification=run_normal_failure_classification,
    )

    try:
        for command in plan.commands:
            run_command(command)
    except subprocess.CalledProcessError as exc:
        return exc.returncode

    print_output_paths(plan.output_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
