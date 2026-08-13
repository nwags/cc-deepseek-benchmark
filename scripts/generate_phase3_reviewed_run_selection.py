#!/usr/bin/env python3
"""Generate the frozen reviewed Phase 3 full-suite run-selection contract.

The generator reads only retained, checked-in review evidence. It performs no
database or external-service access and writes only the canonical JSON and its
logically equivalent dashboard-local TypeScript module.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "phase3-reviewed-run-selection-v1"
GENERATOR_VERSION = "1.0.0"
REVIEWED_AT = "2026-08-09"
SUITE_ID = "phase3-full-20"
KIMI_ARM_ID = "router-kimi-k3"
KIMI_RUN_LABEL = "router-kimi-k3/2026-07-22__17-51-05"
CORE_COUNTS = (15, 900)
EXTENDED_COUNTS = (16, 960)
TASKS_PER_ARM = 20
ATTEMPTS_PER_TASK = 3

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class InputSpec:
    key: str
    role: str
    default_path: str


INPUT_SPECS = (
    InputSpec(
        "kimi_addendum",
        "kimi_full_run_identity_source",
        "docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md",
    ),
    InputSpec(
        "kimi_reconciliation",
        "kimi_run_identity_qualification_source",
        "docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md",
    ),
    InputSpec(
        "review_manifest",
        "independent_selection_integrity_manifest",
        "results/manual_verification/comprehensive_review_20260731/review_manifest.json",
    ),
    InputSpec(
        "review_run_rows",
        "independent_reviewed_selection_cross_check",
        "results/manual_verification/comprehensive_review_20260731/run_review.csv",
    ),
    InputSpec(
        "reviewed_comparison",
        "reviewed_scope_membership_cross_check",
        "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
    ),
    InputSpec(
        "trial_cost_coverage",
        "phase3_core_reviewed_run_identity_source",
        "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
    ),
)


def _fail(message: str) -> None:
    raise ValueError(message)


def _integer(value: str | None, label: str) -> int:
    if value is None or not re.fullmatch(r"\d+", value.strip()):
        _fail(f"invalid integer for {label}")
    return int(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"unable to hash input: {path}") from exc
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"unable to read text input: {path}") from exc


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON input: {label}") from exc
    if not isinstance(value, dict):
        _fail(f"{label} must contain a JSON object")
    return value


def _read_table(path: Path, delimiter: str, label: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                _fail(f"missing header: {label}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"unable to read table: {label}") from exc
    if not rows:
        _fail(f"empty table: {label}")
    return rows


def _assert_columns(rows: list[dict[str, str]], required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        _fail(f"{label} missing columns: {', '.join(missing)}")


def _core_pairs(path: Path) -> list[dict[str, Any]]:
    rows = _read_table(path, "\t", "Phase 3 trial cost coverage")
    _assert_columns(
        rows,
        ("suite_id", "arm_id", "run_label", "task_id", "attempt_index", "trial_id"),
        "Phase 3 trial cost coverage",
    )
    if len(rows) != CORE_COUNTS[1]:
        _fail(f"Phase 3 core must contain exactly {CORE_COUNTS[1]} trials")

    by_arm: dict[str, list[dict[str, str]]] = defaultdict(list)
    trial_ids: set[str] = set()
    for row in rows:
        if row["suite_id"] != SUITE_ID:
            _fail("Phase 3 core contains a non-full-suite row")
        if row["arm_id"] == KIMI_ARM_ID:
            _fail("router-kimi-k3 must not appear in the Phase 3 core source")
        if not row["trial_id"] or row["trial_id"] in trial_ids:
            _fail("Phase 3 core contains a missing or duplicate trial ID")
        trial_ids.add(row["trial_id"])
        by_arm[row["arm_id"]].append(row)

    if len(by_arm) != CORE_COUNTS[0]:
        _fail(f"Phase 3 core must contain exactly {CORE_COUNTS[0]} arms")

    selections: list[dict[str, Any]] = []
    source_path = _display_path(path)
    for arm_id, arm_rows in sorted(by_arm.items()):
        if len(arm_rows) != 60:
            _fail(f"{arm_id} must contain exactly 60 reviewed trials")
        run_labels = {row["run_label"] for row in arm_rows}
        if len(run_labels) != 1:
            _fail(f"{arm_id} must have exactly one historical reviewed run label")
        selected_run_label = next(iter(run_labels))
        if not selected_run_label.startswith(f"{arm_id}/"):
            _fail(f"{arm_id} run label does not match its arm ID")

        task_attempts: dict[str, list[int]] = defaultdict(list)
        for row in arm_rows:
            if not row["task_id"]:
                _fail(f"{arm_id} contains a trial without a task ID")
            task_attempts[row["task_id"]].append(
                _integer(row["attempt_index"], f"{arm_id}.{row['task_id']}.attempt_index")
            )
        if len(task_attempts) != TASKS_PER_ARM:
            _fail(f"{arm_id} must contain the complete {TASKS_PER_ARM}-task set")
        if any(len(attempts) != ATTEMPTS_PER_TASK or len(set(attempts)) != ATTEMPTS_PER_TASK
               for attempts in task_attempts.values()):
            _fail(f"{arm_id} must contain exactly three attempts per task")

        selections.append(
            {
                "armId": arm_id,
                "attemptsPerTask": ATTEMPTS_PER_TASK,
                "providerLogAllocationQualification": None,
                "runIdentityEvidenceStatus": "reviewed",
                "selectedRunLabel": selected_run_label,
                "selectionKind": "reviewed_full_suite_run",
                "sourcePaths": [source_path],
                "taskCount": TASKS_PER_ARM,
                "trialCount": len(arm_rows),
            }
        )
    return selections


def _comparison_membership(path: Path) -> dict[str, set[str]]:
    snapshot = _read_json(path, "reviewed Phase 3 comparison")
    if snapshot.get("schemaVersion") != "phase3-reviewed-comparison-v1":
        _fail("unexpected reviewed Phase 3 comparison schema")
    scopes = snapshot.get("scopes")
    if not isinstance(scopes, dict) or set(scopes) != {"phase3-core", "phase3-extended"}:
        _fail("reviewed Phase 3 comparison has unexpected scopes")
    memberships: dict[str, set[str]] = {}
    for scope_id, expected in (("phase3-core", CORE_COUNTS), ("phase3-extended", EXTENDED_COUNTS)):
        scope = scopes.get(scope_id)
        if not isinstance(scope, dict) or not isinstance(scope.get("arms"), list):
            _fail(f"reviewed comparison {scope_id} is malformed")
        arm_ids = [arm.get("armId") for arm in scope["arms"] if isinstance(arm, dict)]
        if len(arm_ids) != expected[0] or len(set(arm_ids)) != len(arm_ids):
            _fail(f"reviewed comparison {scope_id} arm membership is malformed")
        if scope.get("armCount") != expected[0] or scope.get("trialCount") != expected[1]:
            _fail(f"reviewed comparison {scope_id} counts do not match")
        if any(
            not isinstance(arm, dict) or arm.get("trialCount") != 60
            for arm in scope["arms"]
        ):
            _fail(f"reviewed comparison {scope_id} does not retain 60 trials per arm")
        memberships[scope_id] = set(arm_ids)
    if KIMI_ARM_ID in memberships["phase3-core"] or KIMI_ARM_ID not in memberships["phase3-extended"]:
        _fail("reviewed comparison has an invalid Kimi scope boundary")
    return memberships


def _kimi_selection(addendum_path: Path, reconciliation_path: Path) -> dict[str, Any]:
    addendum = _read_text(addendum_path)
    reconciliation = _read_text(reconciliation_path)

    result_match = re.search(
        r"Result path:\s*`results/phase3/raw/arm-router-kimi-k3/([^/`]+)/result\.json`",
        addendum,
    )
    if not result_match:
        _fail("Kimi addendum does not contain the reviewed full-run result path")
    addendum_run_label = f"{KIMI_ARM_ID}/{result_match.group(1)}"
    if addendum_run_label != KIMI_RUN_LABEL:
        _fail("Kimi addendum contains an unexpected reviewed full-run label")
    if not re.search(r"^- Trials:\s*60\s*$", addendum, flags=re.MULTILINE):
        _fail("Kimi addendum does not contain the reviewed 60-trial count")

    task_rows = re.findall(
        r"^\|\s*([^|]+?)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|\s*\d+\s*\|$",
        addendum,
        flags=re.MULTILINE,
    )
    task_rows = [(task.strip(), int(trials)) for task, trials in task_rows if task.strip() != "Task"]
    if len(task_rows) != TASKS_PER_ARM or len({task for task, _ in task_rows}) != TASKS_PER_ARM:
        _fail("Kimi addendum does not contain the complete 20-task set")
    if any(trials != ATTEMPTS_PER_TASK for _, trials in task_rows) or sum(
        trials for _, trials in task_rows
    ) != 60:
        _fail("Kimi addendum does not retain exactly three attempts per task")

    reviewed_match = re.search(
        r"selected full run is retained as\s*`([^`]+)`",
        reconciliation,
        flags=re.IGNORECASE,
    )
    if not reviewed_match or reviewed_match.group(1) != KIMI_RUN_LABEL:
        _fail("Kimi reconciliation does not confirm the reviewed full-run label")
    required_qualifications = (
        r"Arm-run/provider-log allocation\s*\|\s*Low confidence",
        r"Trial-level allocation\s*\|\s*Unresolved",
        r"no request-to-run join proves that every row belongs to the selected full run",
    )
    if any(not re.search(pattern, reconciliation, flags=re.IGNORECASE) for pattern in required_qualifications):
        _fail("Kimi reconciliation is missing required provider-log allocation limitations")

    return {
        "armId": KIMI_ARM_ID,
        "attemptsPerTask": ATTEMPTS_PER_TASK,
        "providerLogAllocationQualification": {
            "armRunAllocationConfidence": "low",
            "providerLogExclusivityStatus": "not_proven",
            "requestToTrialAllocationStatus": "unresolved",
        },
        "runIdentityEvidenceStatus": "reviewed",
        "selectedRunLabel": KIMI_RUN_LABEL,
        "selectionKind": "reviewed_full_suite_run",
        "sourcePaths": [
            _display_path(addendum_path),
            _display_path(reconciliation_path),
        ],
        "taskCount": TASKS_PER_ARM,
        "trialCount": 60,
    }


def _independent_cross_check(
    run_review_path: Path,
    manifest_path: Path,
) -> list[tuple[str, str]]:
    manifest = _read_json(manifest_path, "comprehensive-review manifest")
    if manifest.get("schema_version") != "comprehensive-evidence-review-manifest-v2":
        _fail("unexpected comprehensive-review manifest schema")
    if manifest.get("suite_id") != SUITE_ID:
        _fail("comprehensive-review manifest uses an unexpected suite")
    fingerprint_inputs = manifest.get("scope_fingerprint_inputs")
    if not isinstance(fingerprint_inputs, dict) or fingerprint_inputs.get("selected_run_count") != 16:
        _fail("comprehensive-review manifest does not retain 16 selected runs")
    outputs = manifest.get("outputs")
    run_output = outputs.get("run_review.csv") if isinstance(outputs, dict) else None
    if not isinstance(run_output, dict) or run_output.get("sha256") != _sha256(run_review_path):
        _fail("run_review.csv does not match its reviewed manifest hash")

    rows = _read_table(run_review_path, ",", "comprehensive run review")
    _assert_columns(
        rows,
        (
            "run_label",
            "suite_id",
            "arm_id",
            "trial_count",
            "task_count",
            "required_task_count",
            "full_suite_complete",
            "valid",
            "selected",
        ),
        "comprehensive run review",
    )
    selected = [row for row in rows if row["selected"] == "True"]
    if len(selected) != 16:
        _fail("comprehensive run review must contain exactly 16 selected rows")
    pairs: list[tuple[str, str]] = []
    for row in selected:
        if row["valid"] != "True" or row["full_suite_complete"] != "True":
            _fail("independent selected run is not valid and full-suite complete")
        if row["suite_id"] != SUITE_ID:
            _fail("independent selected run uses an unexpected suite")
        if (
            _integer(row["trial_count"], "cross-check trial_count") != 60
            or _integer(row["task_count"], "cross-check task_count") != TASKS_PER_ARM
            or _integer(row["required_task_count"], "cross-check required_task_count")
            != TASKS_PER_ARM
        ):
            _fail("independent selected run is not a complete 60-trial run")
        pairs.append((row["arm_id"], row["run_label"]))
    if len(set(arm for arm, _ in pairs)) != 16 or len(set(run for _, run in pairs)) != 16:
        _fail("independent selected runs contain duplicate arm IDs or run labels")
    return sorted(pairs)


def generate_snapshot(input_paths: dict[str, Path]) -> dict[str, Any]:
    missing = sorted({spec.key for spec in INPUT_SPECS} - set(input_paths))
    extra = sorted(set(input_paths) - {spec.key for spec in INPUT_SPECS})
    if missing or extra:
        _fail(f"input set mismatch; missing={missing}, extra={extra}")
    resolved = {key: Path(path).resolve() for key, path in input_paths.items()}
    for path in resolved.values():
        if not path.is_file():
            _fail(f"required input is missing: {path}")

    core = _core_pairs(resolved["trial_cost_coverage"])
    membership = _comparison_membership(resolved["reviewed_comparison"])
    core_ids = {selection["armId"] for selection in core}
    if core_ids != membership["phase3-core"]:
        _fail("core run-selection membership differs from the reviewed comparison")

    kimi = _kimi_selection(resolved["kimi_addendum"], resolved["kimi_reconciliation"])
    extended = sorted([*core, kimi], key=lambda selection: selection["armId"])
    extended_ids = {selection["armId"] for selection in extended}
    if extended_ids != membership["phase3-extended"]:
        _fail("extended run-selection membership differs from the reviewed comparison")

    cross_check = _independent_cross_check(
        resolved["review_run_rows"],
        resolved["review_manifest"],
    )
    selected_pairs = sorted(
        (selection["armId"], selection["selectedRunLabel"]) for selection in extended
    )
    if cross_check != selected_pairs:
        _fail("independent comprehensive review selected a different run cohort")

    trial_source = _display_path(resolved["trial_cost_coverage"])
    comparison_source = _display_path(resolved["reviewed_comparison"])
    run_review_source = _display_path(resolved["review_run_rows"])
    for selection in core:
        selection["sourcePaths"] = [trial_source, comparison_source, run_review_source]
    kimi["sourcePaths"] = sorted(
        [*kimi["sourcePaths"], comparison_source, run_review_source]
    )

    inputs = sorted(
        (
            {
                "path": _display_path(resolved[spec.key]),
                "role": spec.role,
                "sha256": _sha256(resolved[spec.key]),
            }
            for spec in INPUT_SPECS
        ),
        key=lambda item: item["path"],
    )
    snapshot = {
        "generator": {
            "name": "scripts/generate_phase3_reviewed_run_selection.py",
            "version": GENERATOR_VERSION,
        },
        "inputs": inputs,
        "reviewedAt": REVIEWED_AT,
        "schemaVersion": SCHEMA_VERSION,
        "selectionPolicy": {
            "attemptsPerTask": ATTEMPTS_PER_TASK,
            "completeTaskSetRequired": True,
            "fullSuiteRequired": True,
            "historicalOrderingRule": "finished_at_desc_nulls_last_then_run_label",
            "invalidRunExcluded": True,
            "requiredTaskCount": TASKS_PER_ARM,
            "selectionKind": "reviewed_full_suite_run",
            "selectionStability": "frozen_by_reviewed_artifact",
            "suiteId": SUITE_ID,
        },
        "scopes": {
            "phase3-core": {
                "armCount": CORE_COUNTS[0],
                "scopeId": "phase3-core",
                "selectedRunCount": CORE_COUNTS[0],
                "selections": core,
                "trialCount": CORE_COUNTS[1],
            },
            "phase3-extended": {
                "armCount": EXTENDED_COUNTS[0],
                "scopeId": "phase3-extended",
                "selectedRunCount": EXTENDED_COUNTS[0],
                "selections": extended,
                "trialCount": EXTENDED_COUNTS[1],
            },
        },
    }
    serialized = json.dumps(snapshot, sort_keys=True)
    prohibited = (
        r"request[_ -]?id\s*[:=]",
        r"project[_ -]?id\s*[:=]",
        r"api[_ -]?key[_ -]?id\s*[:=]",
        r"sk-[A-Za-z0-9_-]{12,}",
    )
    if any(re.search(pattern, serialized, flags=re.IGNORECASE) for pattern in prohibited):
        _fail("generated run selection contains a prohibited raw provider identifier")
    return snapshot


def serialize_snapshot(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def serialize_dashboard_module(snapshot: dict[str, Any]) -> str:
    compact = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    escaped = json.dumps(compact, ensure_ascii=False)
    return (
        "// Generated by scripts/generate_phase3_reviewed_run_selection.py. Do not edit.\n"
        f"const reviewedRunSelection = JSON.parse({escaped});\n"
        "export default reviewedRunSelection;\n"
    )


def _assert_output_safety(
    input_paths: dict[str, Path],
    output_path: Path,
    dashboard_output_path: Path,
) -> tuple[Path, Path]:
    resolved_outputs = (output_path.resolve(), dashboard_output_path.resolve())
    resolved_inputs = {Path(path).resolve() for path in input_paths.values()}
    if any(output in resolved_inputs for output in resolved_outputs):
        _fail("output path must not equal an input path")
    if resolved_outputs[0] == resolved_outputs[1]:
        _fail("generated output paths must be distinct")
    for output in (output_path, dashboard_output_path):
        if output.exists():
            for input_path in input_paths.values():
                try:
                    if output.samefile(input_path):
                        _fail("output path must not alias an input path")
                except FileNotFoundError:
                    continue
    if output_path.exists() and dashboard_output_path.exists():
        try:
            if output_path.samefile(dashboard_output_path):
                _fail("generated output paths must not alias each other")
        except FileNotFoundError:
            pass
    return resolved_outputs


def _atomic_write_text(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_snapshot(
    input_paths: dict[str, Path],
    output_path: Path,
    dashboard_output_path: Path,
) -> dict[str, Any]:
    resolved_output, resolved_dashboard = _assert_output_safety(
        input_paths,
        output_path,
        dashboard_output_path,
    )
    snapshot = generate_snapshot(input_paths)
    _atomic_write_text(resolved_output, serialize_snapshot(snapshot))
    _atomic_write_text(resolved_dashboard, serialize_dashboard_module(snapshot))
    return snapshot


def default_input_paths() -> dict[str, Path]:
    return {spec.key: REPO_ROOT / spec.default_path for spec in INPUT_SPECS}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for spec in INPUT_SPECS:
        parser.add_argument(
            f"--{spec.key.replace('_', '-')}",
            type=Path,
            default=REPO_ROOT / spec.default_path,
            help=f"Input for {spec.role} (default: {spec.default_path})",
        )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "results/phase3/reporting/phase3_reviewed_run_selection_20260809.json",
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=REPO_ROOT / "apps/dashboard/src/generated/phase3-reviewed-run-selection-data.ts",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    inputs = {spec.key: getattr(args, spec.key) for spec in INPUT_SPECS}
    write_snapshot(inputs, args.output, args.dashboard_output)
    print(f"wrote reviewed run selection: {args.output}")
    print(f"wrote dashboard data module: {args.dashboard_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
