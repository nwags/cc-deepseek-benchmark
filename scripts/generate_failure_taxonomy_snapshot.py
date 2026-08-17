#!/usr/bin/env python3
"""Generate deterministic J2 failure-taxonomy preview or canonical outputs.

The command has no database, object-storage, HTTP, or connector dependency.
It validates the complete J1 source contract before creating any output file.
Preview output must be outside the repository. Canonical output is restricted
to the fixed, new snapshot directory and can never replace populated output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.failure_taxonomy_classifier import (
    CLASSIFIER_VERSION,
    STRICT_PRIMARY_PRECEDENCE,
    classify_trial,
    extract_pytest_failure_details,
    strict_assertion_matches,
)


GENERATOR_VERSION = "failure-taxonomy-generator-v1.1.0"
PREVIEW_MANIFEST_SCHEMA_VERSION = "failure-taxonomy-preview-manifest-v1"
CANONICAL_MANIFEST_SCHEMA_VERSION = "failure-taxonomy-manifest-v1"
TRIAL_SCHEMA_VERSION = "failure-taxonomy-trial-v1"
COUNTS_SCHEMA_VERSION = "failure-taxonomy-counts-v1"
CANONICAL_SNAPSHOT_ID = "failure_taxonomy_20260813"
REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_REVIEW_DIR = REPO_ROOT / "results/manual_verification/comprehensive_review_20260731"
CANONICAL_OUTPUT_DIR = REPO_ROOT / f"results/manual_verification/{CANONICAL_SNAPSHOT_ID}"
CANONICAL_REGISTRY = REPO_ROOT / "configs/dashboard/failure_taxonomy_v1.json"
CLASSIFIER_PATH = REPO_ROOT / "scripts/lib/failure_taxonomy_classifier.py"
GENERATOR_PATH = Path(__file__).resolve()
ACCEPTED_CLASSIFICATION_OUTPUT_HASHES = {
    "trial_failure_taxonomy.jsonl": "ccb4b9cbcc524d34336d4669abbb30c29b741cb03e7f76a9cb21c7fdd2b2eda1",
    "taxonomy_counts.json": "e1284625f3e48e2dcb69a569acb0e73ff326410ffd8b9bc8878cfe5b8863e9cd",
    "review_queue.csv": "aeb8eab2037ce5dd11bb0ef94cda4e0c28013b9c2d887aecdf129d77ea78e883",
}
AXIS_IDS = (
    "response_path_class",
    "verifier_failure_category",
    "assertion_failure_category",
    "trajectory_disposition",
)
OUTPUT_NAMES = (
    "trial_failure_taxonomy.jsonl",
    "taxonomy_counts.json",
    "review_queue.csv",
    "README.md",
)
SNAPSHOT_FILENAMES = (*OUTPUT_NAMES, "failure_taxonomy_manifest.json")


class SourceContractError(RuntimeError):
    """The frozen source does not satisfy the J1 contract."""


@dataclass(frozen=True)
class SourcePaths:
    registry: Path
    review_manifest: Path
    trial_review: Path
    trial_evidence: Path


@dataclass(frozen=True)
class ValidatedSources:
    registry: Mapping[str, Any]
    review_manifest: Mapping[str, Any]
    review_rows: tuple[Mapping[str, Any], ...]
    evidence_by_trial: Mapping[str, Mapping[str, Any]]
    hashes: Mapping[str, str]


def canonical_source_paths() -> SourcePaths:
    return SourcePaths(
        registry=CANONICAL_REGISTRY,
        review_manifest=CANONICAL_REVIEW_DIR / "review_manifest.json",
        trial_review=CANONICAL_REVIEW_DIR / "trial_review.csv",
        trial_evidence=CANONICAL_REVIEW_DIR / "trial_evidence.jsonl",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        for row in rows
    )


def _csv_bytes(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bytes:
    import io

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceContractError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise SourceContractError(f"{label} must be a JSON object")
    return value


def _load_review_rows(path: Path) -> list[Mapping[str, Any]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as error:
        raise SourceContractError(f"cannot read trial_review.csv: {error}") from error


def _load_evidence_rows(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise SourceContractError(f"trial_evidence.jsonl line {line_number} is not an object")
                rows.append(value)
    except (OSError, json.JSONDecodeError) as error:
        raise SourceContractError(f"cannot read trial_evidence.jsonl: {error}") from error
    return rows


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SourceContractError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def _unique_trial_ids(rows: Sequence[Mapping[str, Any]], label: str) -> tuple[str, ...]:
    values = tuple(str(row.get("trial_id") or "") for row in rows)
    if any(not value for value in values):
        raise SourceContractError(f"{label} contains an empty trial_id")
    if len(set(values)) != len(values):
        raise SourceContractError(f"{label} contains duplicate trial_id values")
    return values


def validate_trial_sets(
    review_rows: Sequence[Mapping[str, Any]],
    evidence_rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    review_ids = _unique_trial_ids(review_rows, "trial_review.csv")
    evidence_ids = _unique_trial_ids(evidence_rows, "trial_evidence.jsonl")
    if set(review_ids) != set(evidence_ids):
        missing_evidence = sorted(set(review_ids) - set(evidence_ids))
        extra_evidence = sorted(set(evidence_ids) - set(review_ids))
        raise SourceContractError(
            "trial set mismatch: "
            f"missing evidence={missing_evidence[:3]!r}; extra evidence={extra_evidence[:3]!r}"
        )
    return tuple(sorted(review_ids))


def validate_sources(paths: SourcePaths | None = None) -> ValidatedSources:
    paths = paths or canonical_source_paths()
    registry = _load_json(paths.registry, "taxonomy registry")
    manifest = _load_json(paths.review_manifest, "review manifest")
    source = registry.get("source_contract")
    if not isinstance(source, dict):
        raise SourceContractError("taxonomy registry source_contract is missing")

    _require_equal(
        registry.get("schema_version"),
        "dashboard-failure-taxonomy-registry-v1",
        "taxonomy schema_version",
    )
    _require_equal(sha256(paths.review_manifest), source.get("manifest_sha256"), "review manifest SHA-256")
    _require_equal(manifest.get("schema_version"), source.get("manifest_schema_version"), "manifest schema")
    _require_equal(manifest.get("scope_fingerprint"), source.get("scope_fingerprint"), "scope fingerprint")
    _require_equal(
        manifest.get("scope_fingerprint_inputs", {}).get("trial_count"),
        source.get("trial_count"),
        "scope trial count",
    )

    required_inputs = source.get("required_inputs")
    if not isinstance(required_inputs, list):
        raise SourceContractError("source_contract.required_inputs must be a list")
    expected_paths = {item.get("path"): item for item in required_inputs if isinstance(item, dict)}
    _require_equal(set(expected_paths), {"trial_review.csv", "trial_evidence.jsonl"}, "required input names")
    actual_paths = {
        "trial_review.csv": paths.trial_review,
        "trial_evidence.jsonl": paths.trial_evidence,
    }
    hashes = {
        "taxonomy_registry": sha256(paths.registry),
        "review_manifest": sha256(paths.review_manifest),
    }
    for name, path in actual_paths.items():
        digest = sha256(path)
        hashes[name] = digest
        expected = expected_paths[name]
        manifest_output = manifest.get("outputs", {}).get(name, {})
        _require_equal(digest, expected.get("sha256"), f"{name} J1 SHA-256")
        _require_equal(digest, manifest_output.get("sha256"), f"{name} manifest SHA-256")
        _require_equal(path.stat().st_size, manifest_output.get("bytes"), f"{name} byte count")
        _require_equal(expected.get("rows"), manifest.get("row_counts", {}).get(name), f"{name} row count contract")

    review_rows = _load_review_rows(paths.trial_review)
    evidence_rows = _load_evidence_rows(paths.trial_evidence)
    expected_count = int(source.get("trial_count") or 0)
    _require_equal(len(review_rows), expected_count, "trial_review.csv parsed row count")
    _require_equal(len(evidence_rows), expected_count, "trial_evidence.jsonl parsed row count")
    trial_ids = validate_trial_sets(review_rows, evidence_rows)
    expected_trial_ids_hash = manifest.get("scope_fingerprint_inputs", {}).get("trial_ids_sha256")
    actual_trial_ids_hash = hashlib.sha256("\n".join(trial_ids).encode("utf-8")).hexdigest()
    _require_equal(actual_trial_ids_hash, expected_trial_ids_hash, "trial set SHA-256")

    for evidence in evidence_rows:
        if evidence.get("hidden_reasoning_retained") is not False:
            raise SourceContractError(
                f"trial {evidence.get('trial_id')} does not retain the required private-reasoning boundary"
            )
        transcript = evidence.get("manual_evidence", {}).get("transcript_activity", {})
        if transcript.get("hidden_reasoning_retained") is not False:
            raise SourceContractError(
                f"trial {evidence.get('trial_id')} transcript violates the private-reasoning boundary"
            )

    review_sorted = tuple(sorted(review_rows, key=lambda row: str(row["trial_id"])))
    evidence_by_trial = {str(row["trial_id"]): row for row in evidence_rows}
    return ValidatedSources(
        registry=registry,
        review_manifest=manifest,
        review_rows=review_sorted,
        evidence_by_trial=evidence_by_trial,
        hashes=hashes,
    )


def _axis_values(registry: Mapping[str, Any]) -> Mapping[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for axis in registry.get("axes", []):
        axis_id = axis.get("id")
        if axis_id in AXIS_IDS:
            result[str(axis_id)] = tuple(str(entry["id"]) for entry in axis.get("entries", []))
    if set(result) != set(AXIS_IDS):
        raise SourceContractError("taxonomy registry does not contain all four J2A axes")
    return result


def _zero_table(rows: Iterable[str], columns: Iterable[str]) -> dict[str, dict[str, int]]:
    return {row: {column: 0 for column in columns} for row in rows}


def _ctrf_counts(evidence: Mapping[str, Any]) -> tuple[int, int, int]:
    tests = evidence.get("manual_evidence", {}).get("ctrf_tests", [])
    return (
        len(tests),
        sum(1 for test in tests if test.get("status") == "passed"),
        sum(1 for test in tests if test.get("status") == "failed"),
    )


def _stdout_assertion_candidate_diagnostics(sources: ValidatedSources) -> Mapping[str, int]:
    counts = {
        "accepted_assertion_failure_candidates": 0,
        "no_pytest_failures_section": 0,
        "zero_strict_assertion_subtypes": 0,
        "multiple_strict_assertion_subtypes": 0,
        "one_strict_assertion_subtype": 0,
    }
    for review in sources.review_rows:
        if review.get("failure_subtype") != "test_assertion_failure":
            continue
        counts["accepted_assertion_failure_candidates"] += 1
        details = extract_pytest_failure_details(
            sources.evidence_by_trial[str(review["trial_id"])]
        )
        if not details.has_failure_section:
            counts["no_pytest_failures_section"] += 1
            continue
        match_count = len(strict_assertion_matches(details.diagnostic_lines))
        if match_count == 0:
            counts["zero_strict_assertion_subtypes"] += 1
        elif match_count == 1:
            counts["one_strict_assertion_subtype"] += 1
        else:
            counts["multiple_strict_assertion_subtypes"] += 1
    return counts


def build_counts(
    classified: Sequence[Mapping[str, Any]],
    sources: ValidatedSources,
) -> Mapping[str, Any]:
    values = _axis_values(sources.registry)
    raw_outcomes = tuple(sorted({str(row["raw_outcome"]) for row in classified}))
    review_by_id = {str(row["trial_id"]): row for row in sources.review_rows}
    failure_subtypes = tuple(sorted({str(row.get("failure_subtype") or "not_recorded") for row in sources.review_rows}))
    task_ids = tuple(sorted({str(row.get("task_id") or "not_recorded") for row in sources.review_rows}))

    distributions = {axis: {value: 0 for value in values[axis]} for axis in AXIS_IDS}
    response_raw = _zero_table(values["response_path_class"], raw_outcomes)
    verifier_failure = _zero_table(values["verifier_failure_category"], failure_subtypes)
    assertion_task = _zero_table(values["assertion_failure_category"], task_ids)
    trajectory_raw = _zero_table(values["trajectory_disposition"], raw_outcomes)
    confidence_axis = {axis: {confidence: 0 for confidence in ("high", "medium", "low")} for axis in AXIS_IDS}
    manual_axis = {axis: {"required": 0, "not_required": 0} for axis in AXIS_IDS}
    representatives: dict[str, dict[str, list[str]]] = {
        axis: {value: [] for value in values[axis]} for axis in AXIS_IDS
    }

    for row in classified:
        review = review_by_id[str(row["trial_id"])]
        raw = str(row["raw_outcome"])
        for axis in AXIS_IDS:
            diagnosis = row[axis]
            value = str(diagnosis["value"])
            distributions[axis][value] += 1
            confidence_axis[axis][str(diagnosis["confidence"])] += 1
            key = "required" if diagnosis["manual_review_required"] else "not_required"
            manual_axis[axis][key] += 1
            if len(representatives[axis][value]) < 3:
                representatives[axis][value].append(str(row["trial_id"]))
        response_raw[row["response_path_class"]["value"]][raw] += 1
        verifier_failure[row["verifier_failure_category"]["value"]][
            str(review.get("failure_subtype") or "not_recorded")
        ] += 1
        assertion_task[row["assertion_failure_category"]["value"]][
            str(review.get("task_id") or "not_recorded")
        ] += 1
        trajectory_raw[row["trajectory_disposition"]["value"]][raw] += 1

    neutral = {
        "response_path_class": {"not_applicable"},
        "verifier_failure_category": {"none"},
        "assertion_failure_category": {"none"},
        "trajectory_disposition": {"successful_completion", "indeterminate"},
    }
    nontrivial_representatives = {
        axis: {
            value: ids
            for value, ids in representatives[axis].items()
            if distributions[axis][value] > 0 and value not in neutral[axis]
        }
        for axis in AXIS_IDS
    }

    one_test_one_failure_not_near = 0
    for row in classified:
        total, _passed, failed = _ctrf_counts(sources.evidence_by_trial[str(row["trial_id"])])
        if total == 1 and failed == 1 and row["trajectory_disposition"]["value"] not in {
            "near_miss_one_behavioral_defect",
            "near_miss_cleanup_or_packaging_only",
        }:
            one_test_one_failure_not_near += 1

    response_anomaly_values = (
        "synthetic_retry_empty_completion",
        "empty_completion_after_long_api_path_wait",
        "thinking_only_empty_completion",
        "empty_completion",
        "invalid_response_path",
    )
    diagnostics = {
        "successful_raw_outcome_with_timeout_after_meaningful_progress": sum(
            1
            for row in classified
            if row["raw_outcome"] == "success"
            and row["trajectory_disposition"]["value"] == "timeout_after_meaningful_progress"
        ),
        "one_test_one_failure_not_classified_as_near_miss": one_test_one_failure_not_near,
        "multi_test_one_failure_behavioral_near_misses": distributions["trajectory_disposition"][
            "near_miss_one_behavioral_defect"
        ],
        "response_path_anomaly_count": sum(
            distributions["response_path_class"][value] for value in response_anomaly_values
        ),
        "response_path_anomaly_subtypes": {
            value: distributions["response_path_class"][value] for value in response_anomaly_values
        },
        "verifier_strict_refinement_counts": {
            value: sum(
                1
                for row in classified
                if row["verifier_failure_category"]["value"] == value
                and f"rule=j2.verifier.strict.{value}"
                in row["verifier_failure_category"]["evidence_basis"]
            )
            for value in STRICT_PRIMARY_PRECEDENCE
        },
        "assertion_strict_refinement_counts": {
            value: sum(
                1
                for row in classified
                if row["assertion_failure_category"]["value"] == value
                and f"rule=j2.assertion.strict.{value}"
                in row["assertion_failure_category"]["evidence_basis"]
            )
            for value in values["assertion_failure_category"]
            if value not in {"none", "unclassified_assertion"}
        },
        "no_substantive_attempt_confidence": {
            confidence: sum(
                1
                for row in classified
                if row["trajectory_disposition"]["value"] == "no_substantive_attempt"
                and row["trajectory_disposition"]["confidence"] == confidence
            )
            for confidence in ("high", "medium", "low")
        },
        "manual_review_union_count": sum(
            1
            for row in classified
            if any(row[axis]["manual_review_required"] for axis in AXIS_IDS)
        ),
        "stdout_assertion_candidates": _stdout_assertion_candidate_diagnostics(sources),
    }

    return {
        "schema_version": COUNTS_SCHEMA_VERSION,
        "trial_count": len(classified),
        "axis_distributions": distributions,
        "zero_population_values": {
            axis: [value for value, count in distributions[axis].items() if count == 0]
            for axis in AXIS_IDS
        },
        "raw_outcome_counts": dict(sorted(Counter(str(row["raw_outcome"]) for row in classified).items())),
        "cross_tabs": {
            "response_path_class_x_raw_outcome": response_raw,
            "verifier_failure_category_x_existing_failure_subtype": verifier_failure,
            "assertion_failure_category_x_task_id": assertion_task,
            "trajectory_disposition_x_raw_outcome": trajectory_raw,
            "confidence_x_axis": confidence_axis,
            "manual_review_count_x_axis": manual_axis,
        },
        "representative_trial_ids": nontrivial_representatives,
        "diagnostics": diagnostics,
    }


def build_review_queue(classified: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in classified:
        required_axes = [axis for axis in AXIS_IDS if row[axis]["manual_review_required"]]
        if not required_axes:
            continue
        reasons = sorted({
            f"{axis}:{fact.removeprefix('rule=')}"
            for axis in required_axes
            for fact in row[axis]["evidence_basis"]
            if fact.startswith("rule=")
        })
        queued: dict[str, Any] = {
            "trial_id": row["trial_id"],
            "arm_id": row["arm_id"],
            "task_id": row["task_id"],
            "raw_outcome": row["raw_outcome"],
        }
        for axis in AXIS_IDS:
            queued[axis] = row[axis]["value"]
            queued[f"{axis}_confidence"] = row[axis]["confidence"]
        queued["manual_review_reasons"] = ";".join(reasons)
        rows.append(queued)
    return sorted(rows, key=lambda row: str(row["trial_id"]))


def _preview_readme(counts: Mapping[str, Any], queue_count: int) -> bytes:
    lines = [
        "# Failure taxonomy J2A preview",
        "",
        f"Classifier: `{CLASSIFIER_VERSION}`",
        "",
        f"Generator: `{GENERATOR_VERSION}`",
        "",
        f"Frozen input scope: `{counts['trial_count']}` reviewed trials.",
        "",
        f"Manual-review queue: `{queue_count}` trials.",
        "",
        "This deterministic preview is derived offline from the manifest-bound checked-in comprehensive review and the J1 taxonomy registry. It contains structured rule facts and retained artifact IDs, not source excerpts. Registry order is display-only; classifier precedence is explicit in the classifier source.",
        "",
        "`trial_failure_taxonomy.jsonl` contains one row per frozen trial. `taxonomy_counts.json` contains complete enum counts, cross-tabs, diagnostics, and representative IDs. `review_queue.csv` contains only trials with at least one diagnosis requiring manual review. `failure_taxonomy_manifest.json` binds all inputs, implementations, and output hashes.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _canonical_readme(counts: Mapping[str, Any], queue_count: int) -> bytes:
    lines = [
        "# Frozen J2 failure and trajectory taxonomy",
        "",
        f"Snapshot: `{CANONICAL_SNAPSHOT_ID}`",
        "",
        f"Classifier: `{CLASSIFIER_VERSION}`",
        "",
        f"Generator: `{GENERATOR_VERSION}`",
        "",
        f"Frozen input scope: `{counts['trial_count']}` reviewed trials.",
        "",
        f"Manual-review queue: `{queue_count}` trials.",
        "",
        "This is the frozen, offline J2 derived failure and trajectory taxonomy snapshot. Its source is the manifest-bound checked-in comprehensive review. It is derived evidence, not raw benchmark truth. Raw reward, raw outcome, exception, policy, termination, and activity remain independent source axes and are not replaced by this snapshot.",
        "",
        "Legacy suspected no-op terminology is retained only for compatibility; it is not a primary diagnosis in this taxonomy. No hidden or private model reasoning is retained, required, inferred, or displayed. These categories do not make causal attributions to a provider, router, or harness.",
        "",
        "Some taxonomy values intentionally have zero population because the classifier uses conservative evidence requirements and explicit fallback states. Medium-confidence refinements and other diagnoses marked for manual review remain reviewable through retained supporting artifact IDs rather than copied verifier or transcript excerpts.",
        "",
        "Dashboard consumers must validate and consume this manifest-bound snapshot, join it to reviewed trials by `trial_id`, and fail closed on a manifest or input mismatch. They must not reclassify trials in the browser.",
        "",
        "`trial_failure_taxonomy.jsonl` contains one row per frozen trial. `taxonomy_counts.json` contains complete enum counts, cross-tabs, diagnostics, and representative IDs. `review_queue.csv` contains the union of trials with at least one diagnosis requiring manual review. `failure_taxonomy_manifest.json` binds the frozen inputs, producer implementations, and all other snapshot outputs.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _render_data_outputs(
    sources: ValidatedSources,
) -> tuple[dict[str, bytes], Mapping[str, Any], int]:
    classified = tuple(
        classify_trial(row, sources.evidence_by_trial[str(row["trial_id"])], sources.registry)
        for row in sources.review_rows
    )
    counts = build_counts(classified, sources)
    queue = build_review_queue(classified)
    queue_fields = [
        "trial_id", "arm_id", "task_id", "raw_outcome",
        *[field for axis in AXIS_IDS for field in (axis, f"{axis}_confidence")],
        "manual_review_reasons",
    ]
    files = {
        "trial_failure_taxonomy.jsonl": _jsonl_bytes(classified),
        "taxonomy_counts.json": _json_bytes(counts),
        "review_queue.csv": _csv_bytes(queue, queue_fields),
    }
    return files, counts, len(queue)


def render_preview(sources: ValidatedSources) -> tuple[Mapping[str, bytes], Mapping[str, Any]]:
    files, counts, queue_count = _render_data_outputs(sources)
    files["README.md"] = _preview_readme(counts, queue_count)
    return files, counts


def render_canonical_snapshot(
    sources: ValidatedSources,
) -> tuple[Mapping[str, bytes], Mapping[str, Any]]:
    files, counts, queue_count = _render_data_outputs(sources)
    files["README.md"] = _canonical_readme(counts, queue_count)
    return files, counts


def _logical_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def build_manifest(
    files: Mapping[str, bytes],
    counts: Mapping[str, Any],
    sources: ValidatedSources,
    *,
    schema_version: str = PREVIEW_MANIFEST_SCHEMA_VERSION,
    snapshot_kind: str = "preview",
) -> Mapping[str, Any]:
    queue_rows = max(files["review_queue.csv"].count(b"\n") - 1, 0)
    output_rows = {
        "trial_failure_taxonomy.jsonl": int(counts["trial_count"]),
        "taxonomy_counts.json": None,
        "review_queue.csv": queue_rows,
        "README.md": None,
    }
    return {
        "schema_version": schema_version,
        "snapshot_id": CANONICAL_SNAPSHOT_ID,
        "snapshot_kind": snapshot_kind,
        "snapshot_files": list(SNAPSHOT_FILENAMES),
        "trial_schema_version": TRIAL_SCHEMA_VERSION,
        "taxonomy_schema_version": sources.registry["schema_version"],
        "taxonomy_version": sources.registry["taxonomy_version"],
        "classifier_version": CLASSIFIER_VERSION,
        "generator_version": GENERATOR_VERSION,
        "source_provenance": {
            "comprehensive_review_generated_at": sources.review_manifest.get("generated_at"),
            "note": "Source snapshot provenance; not J2 generation time.",
        },
        "scope_fingerprint": sources.review_manifest["scope_fingerprint"],
        "inputs": {
            "taxonomy_registry": {
                "path": _logical_repo_path(CANONICAL_REGISTRY),
                "sha256": sources.hashes["taxonomy_registry"],
                "schema_version": sources.registry["schema_version"],
                "taxonomy_version": sources.registry["taxonomy_version"],
            },
            "comprehensive_review_manifest": {
                "path": _logical_repo_path(CANONICAL_REVIEW_DIR / "review_manifest.json"),
                "sha256": sources.hashes["review_manifest"],
                "schema_version": sources.review_manifest.get("schema_version"),
            },
            "trial_review.csv": {
                "path": _logical_repo_path(CANONICAL_REVIEW_DIR / "trial_review.csv"),
                "sha256": sources.hashes["trial_review.csv"],
                "rows": len(sources.review_rows),
            },
            "trial_evidence.jsonl": {
                "path": _logical_repo_path(CANONICAL_REVIEW_DIR / "trial_evidence.jsonl"),
                "sha256": sources.hashes["trial_evidence.jsonl"],
                "rows": len(sources.evidence_by_trial),
            },
        },
        "implementations": {
            "classifier": {
                "path": _logical_repo_path(CLASSIFIER_PATH),
                "version": CLASSIFIER_VERSION,
                "sha256": sha256(CLASSIFIER_PATH),
            },
            "generator": {
                "path": _logical_repo_path(GENERATOR_PATH),
                "version": GENERATOR_VERSION,
                "sha256": sha256(GENERATOR_PATH),
            },
        },
        "outputs": {
            name: {
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "rows": output_rows[name],
            }
            for name, content in sorted(files.items())
        },
    }


def _validate_preview_output_path(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("J2A preview output must be outside the repository")
    if resolved.exists() and any(resolved.iterdir()):
        raise FileExistsError(f"preview output directory is not empty: {resolved}")
    return resolved


def _validate_canonical_output_path(output_dir: Path) -> Path:
    candidate = output_dir.absolute()
    expected = CANONICAL_OUTPUT_DIR.absolute()
    if candidate != expected:
        raise ValueError(
            "canonical output must be exactly "
            f"{CANONICAL_OUTPUT_DIR.relative_to(REPO_ROOT).as_posix()}"
        )
    return candidate


def _require_empty_output_directory(output_dir: Path, label: str) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise FileExistsError(f"{label} output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise FileExistsError(f"{label} output directory is not empty: {output_dir}")


def _validate_accepted_classification_hashes(files: Mapping[str, bytes]) -> None:
    for name, expected in ACCEPTED_CLASSIFICATION_OUTPUT_HASHES.items():
        actual = hashlib.sha256(files[name]).hexdigest()
        if actual != expected:
            raise SourceContractError(
                f"accepted J2A.1 output hash mismatch for {name}: "
                f"expected {expected}, got {actual}"
            )


def _write_snapshot(
    output_dir: Path,
    files: Mapping[str, bytes],
    manifest: Mapping[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (output_dir / name).write_bytes(content)
    (output_dir / "failure_taxonomy_manifest.json").write_bytes(_json_bytes(manifest))


def generate_preview(
    output_dir: Path,
    *,
    source_paths: SourcePaths | None = None,
) -> Mapping[str, Any]:
    output_dir = _validate_preview_output_path(output_dir)
    # Complete source validation intentionally precedes directory creation/writes.
    sources = validate_sources(source_paths)
    files, counts = render_preview(sources)
    manifest = build_manifest(files, counts, sources)
    _write_snapshot(output_dir, files, manifest)
    return counts


def generate_canonical_snapshot(output_dir: Path) -> Mapping[str, Any]:
    output_dir = _validate_canonical_output_path(output_dir)
    _require_empty_output_directory(output_dir, "canonical")
    # Complete source validation and accepted-byte verification intentionally
    # precede directory creation and every output write.
    sources = validate_sources()
    files, counts = render_canonical_snapshot(sources)
    _validate_accepted_classification_hashes(files)
    manifest = build_manifest(
        files,
        counts,
        sources,
        schema_version=CANONICAL_MANIFEST_SCHEMA_VERSION,
        snapshot_kind="canonical_offline_derived",
    )
    _write_snapshot(output_dir, files, manifest)
    return counts


def _print_report(output_dir: Path, counts: Mapping[str, Any], mode: str) -> None:
    print(f"{mode}_output={output_dir}")
    print(f"trial_count={counts['trial_count']}")
    for axis in AXIS_IDS:
        print(f"{axis}={json.dumps(counts['axis_distributions'][axis], sort_keys=True)}")
        print(f"{axis}.zero={json.dumps(counts['zero_population_values'][axis])}")
        print(f"{axis}.confidence={json.dumps(counts['cross_tabs']['confidence_x_axis'][axis], sort_keys=True)}")
        print(f"{axis}.manual_review={json.dumps(counts['cross_tabs']['manual_review_count_x_axis'][axis], sort_keys=True)}")
    print(f"diagnostics={json.dumps(counts['diagnostics'], sort_keys=True)}")
    print(f"representatives={json.dumps(counts['representative_trial_ids'], sort_keys=True)}")
    print("cross_tabs=response_path_class_x_raw_outcome,verifier_failure_category_x_existing_failure_subtype,assertion_failure_category_x_task_id,trajectory_disposition_x_raw_outcome,confidence_x_axis,manual_review_count_x_axis")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preview", "canonical"), default="preview")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "canonical":
        counts = generate_canonical_snapshot(args.output_dir)
    else:
        counts = generate_preview(args.output_dir)
    _print_report(args.output_dir.resolve(), counts, args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
