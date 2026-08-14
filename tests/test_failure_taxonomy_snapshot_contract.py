from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.generate_failure_taxonomy_snapshot import (
    ACCEPTED_CLASSIFICATION_OUTPUT_HASHES,
    AXIS_IDS,
    CANONICAL_MANIFEST_SCHEMA_VERSION,
    CLASSIFIER_PATH,
    CLASSIFIER_VERSION,
    COUNTS_SCHEMA_VERSION,
    GENERATOR_PATH,
    GENERATOR_VERSION,
    TRIAL_SCHEMA_VERSION,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "results/manual_verification/failure_taxonomy_20260813"
REVIEW_DIR = ROOT / "results/manual_verification/comprehensive_review_20260731"
REGISTRY = ROOT / "configs/dashboard/failure_taxonomy_v1.json"
EXPECTED_FILES = {
    "trial_failure_taxonomy.jsonl",
    "taxonomy_counts.json",
    "review_queue.csv",
    "failure_taxonomy_manifest.json",
    "README.md",
}
EXPECTED_DISTRIBUTIONS = {
    "response_path_class": {
        "synthetic_retry_empty_completion": 2,
        "empty_completion_after_long_api_path_wait": 1,
        "thinking_only_empty_completion": 1,
        "empty_completion": 0,
        "invalid_response_path": 0,
        "unknown": 34,
        "not_applicable": 922,
    },
    "verifier_failure_category": {
        "none": 760,
        "verifier_environment_issue": 0,
        "syntax_or_compile_error": 0,
        "dependency_or_import_error": 5,
        "wrong_file_or_path": 0,
        "timeout_inside_verifier": 0,
        "runtime_exception_in_solution": 0,
        "test_assertion_failure": 162,
        "missing_or_wrong_output": 33,
        "no_meaningful_code_change": 0,
        "partial_solution": 0,
        "unclassified_failure": 0,
    },
    "assertion_failure_category": {
        "none": 798,
        "performance_threshold_failure": 0,
        "numerical_or_data_mismatch": 0,
        "missing_expected_file_or_content": 2,
        "behavior_mismatch": 0,
        "output_mismatch": 0,
        "unclassified_assertion": 160,
    },
    "trajectory_disposition": {
        "successful_completion": 543,
        "no_substantive_attempt": 37,
        "early_abandonment": 0,
        "partial_implementation": 0,
        "plausible_but_incorrect_completion": 0,
        "near_miss_cleanup_or_packaging_only": 0,
        "near_miss_one_behavioral_defect": 0,
        "repeated_unproductive_iteration": 0,
        "timeout_after_meaningful_progress": 174,
        "completed_work_with_verifier_or_infrastructure_issue": 0,
        "indeterminate": 206,
    },
}
KNOWN_RESPONSE_PATHS = {
    "7eceb1c8-4a7b-4899-9650-b54f7d432d24": "empty_completion_after_long_api_path_wait",
    "b59e45f0-050e-448e-8a97-abee2f4b89c6": "thinking_only_empty_completion",
    "9ce7bde7-ce6e-4f32-93af-04848273f93c": "synthetic_retry_empty_completion",
    "6ebd9061-3c69-443d-8a76-be789b50344d": "synthetic_retry_empty_completion",
}
MISSING_CONTENT_IDS = {
    "7810f2c3-3555-4279-8654-6ae0ee9813b0",
    "e7c90fe6-f9a5-4bcc-9b31-66f843688aa2",
}
SUCCESSFUL_TIMEOUT_ID = "06069bcf-6f36-4000-aa41-85501e197164"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_canonical_snapshot_files_rows_hashes_and_distributions() -> None:
    assert {path.name for path in SNAPSHOT.iterdir()} == EXPECTED_FILES
    for name, expected_hash in ACCEPTED_CLASSIFICATION_OUTPUT_HASHES.items():
        assert sha256(SNAPSHOT / name) == expected_hash

    rows = read_jsonl(SNAPSHOT / "trial_failure_taxonomy.jsonl")
    frozen_ids = {
        row["trial_id"]
        for row in csv.DictReader((REVIEW_DIR / "trial_review.csv").open())
    }
    assert len(rows) == 960
    assert len({row["trial_id"] for row in rows}) == 960
    assert {row["trial_id"] for row in rows} == frozen_ids
    assert [row["trial_id"] for row in rows] == sorted(frozen_ids)

    counts = json.loads((SNAPSHOT / "taxonomy_counts.json").read_text())
    assert counts["schema_version"] == COUNTS_SCHEMA_VERSION
    assert counts["trial_count"] == 960
    assert counts["axis_distributions"] == EXPECTED_DISTRIBUTIONS
    assert counts["diagnostics"]["no_substantive_attempt_confidence"] == {
        "high": 10,
        "medium": 27,
        "low": 0,
    }
    assert counts["diagnostics"][
        "successful_raw_outcome_with_timeout_after_meaningful_progress"
    ] == 19
    assert counts["diagnostics"]["multi_test_one_failure_behavioral_near_misses"] == 0
    assert counts["diagnostics"]["response_path_anomaly_count"] == 4


def test_canonical_review_queue_is_exact_manual_review_union() -> None:
    rows = read_jsonl(SNAPSHOT / "trial_failure_taxonomy.jsonl")
    expected_ids = {
        row["trial_id"]
        for row in rows
        if any(row[axis]["manual_review_required"] for axis in AXIS_IDS)
    }
    with (SNAPSHOT / "review_queue.csv").open(newline="") as handle:
        queue = list(csv.DictReader(handle))
    queue_ids = [row["trial_id"] for row in queue]
    assert len(queue_ids) == 243
    assert len(set(queue_ids)) == 243
    assert set(queue_ids) == expected_ids
    assert queue_ids == sorted(queue_ids)


def test_canonical_known_classifications_are_frozen() -> None:
    rows = {
        row["trial_id"]: row
        for row in read_jsonl(SNAPSHOT / "trial_failure_taxonomy.jsonl")
    }
    assert {
        trial_id: rows[trial_id]["response_path_class"]["value"]
        for trial_id in KNOWN_RESPONSE_PATHS
    } == KNOWN_RESPONSE_PATHS

    missing_ids = {
        trial_id
        for trial_id, row in rows.items()
        if row["assertion_failure_category"]["value"]
        == "missing_expected_file_or_content"
    }
    assert missing_ids == MISSING_CONTENT_IDS

    dependencies = [
        row
        for row in rows.values()
        if row["verifier_failure_category"]["value"] == "dependency_or_import_error"
    ]
    assert len(dependencies) == 5
    assert {row["task_id"] for row in dependencies} == {
        "terminal-bench-2.0:openssl-selfsigned-cert"
    }

    control = rows[SUCCESSFUL_TIMEOUT_ID]
    assert control["raw_outcome"] == "success"
    assert control["trajectory_disposition"]["value"] == (
        "timeout_after_meaningful_progress"
    )


def test_canonical_manifest_binds_sources_implementations_and_outputs() -> None:
    manifest = json.loads((SNAPSHOT / "failure_taxonomy_manifest.json").read_text())
    registry = json.loads(REGISTRY.read_text())
    review_manifest = json.loads((REVIEW_DIR / "review_manifest.json").read_text())

    assert manifest["schema_version"] == CANONICAL_MANIFEST_SCHEMA_VERSION
    assert manifest["snapshot_id"] == "failure_taxonomy_20260813"
    assert manifest["snapshot_kind"] == "canonical_offline_derived"
    assert set(manifest["snapshot_files"]) == EXPECTED_FILES
    assert manifest["trial_schema_version"] == TRIAL_SCHEMA_VERSION
    assert manifest["taxonomy_version"] == registry["taxonomy_version"]
    assert manifest["scope_fingerprint"] == review_manifest["scope_fingerprint"]
    assert "generated_at" not in manifest
    assert manifest["source_provenance"]["comprehensive_review_generated_at"] == (
        review_manifest["generated_at"]
    )

    inputs = manifest["inputs"]
    assert inputs["taxonomy_registry"] == {
        "path": "configs/dashboard/failure_taxonomy_v1.json",
        "sha256": sha256(REGISTRY),
        "schema_version": registry["schema_version"],
        "taxonomy_version": registry["taxonomy_version"],
    }
    assert inputs["comprehensive_review_manifest"] == {
        "path": "results/manual_verification/comprehensive_review_20260731/review_manifest.json",
        "sha256": sha256(REVIEW_DIR / "review_manifest.json"),
        "schema_version": review_manifest["schema_version"],
    }
    for name in ("trial_review.csv", "trial_evidence.jsonl"):
        assert inputs[name]["path"] == (
            f"results/manual_verification/comprehensive_review_20260731/{name}"
        )
        assert inputs[name]["sha256"] == sha256(REVIEW_DIR / name)
        assert inputs[name]["rows"] == 960

    assert manifest["implementations"]["classifier"] == {
        "path": "scripts/lib/failure_taxonomy_classifier.py",
        "version": CLASSIFIER_VERSION,
        "sha256": sha256(CLASSIFIER_PATH),
    }
    assert manifest["implementations"]["generator"] == {
        "path": "scripts/generate_failure_taxonomy_snapshot.py",
        "version": GENERATOR_VERSION,
        "sha256": sha256(GENERATOR_PATH),
    }

    assert set(manifest["outputs"]) == EXPECTED_FILES - {
        "failure_taxonomy_manifest.json"
    }
    for name, metadata in manifest["outputs"].items():
        data = (SNAPSHOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
        assert len(data) == metadata["bytes"]
    assert manifest["outputs"]["trial_failure_taxonomy.jsonl"]["rows"] == 960
    assert manifest["outputs"]["review_queue.csv"]["rows"] == 243
    assert "failure_taxonomy_manifest.json" not in manifest["outputs"]


def test_canonical_output_retains_no_raw_excerpt_or_private_reasoning_fields() -> None:
    forbidden_keys = {
        "hidden_reasoning_retained",
        "verifier_stdout_excerpt",
        "failure_message",
        "visible_assistant_excerpts",
        "visible_result_excerpts",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            assert forbidden_keys.isdisjoint(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for row in read_jsonl(SNAPSHOT / "trial_failure_taxonomy.jsonl"):
        walk(row)

    readme = (SNAPSHOT / "README.md").read_text()
    assert "derived evidence, not raw benchmark truth" in readme
    assert "remain independent source axes" in readme
    assert "Legacy suspected no-op terminology" in readme
    assert "No hidden or private model reasoning is retained" in readme
    assert "do not make causal attributions to a provider, router, or harness" in readme
    assert "intentionally have zero population" in readme
    assert "must not reclassify trials in the browser" in readme
    assert "verifier_stdout_excerpt" not in readme
