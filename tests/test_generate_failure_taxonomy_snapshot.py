from __future__ import annotations

import ast
import csv
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from scripts.generate_failure_taxonomy_snapshot import (
    AXIS_IDS,
    SourceContractError,
    SourcePaths,
    canonical_source_paths,
    generate_preview,
    sha256,
    validate_trial_sets,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs/dashboard/failure_taxonomy_v1.json"
REVIEW_DIR = ROOT / "results/manual_verification/comprehensive_review_20260731"
KNOWN_RESPONSE_PATH_IDS = {
    "6ebd9061-3c69-443d-8a76-be789b50344d": "synthetic_retry_empty_completion",
    "9ce7bde7-ce6e-4f32-93af-04848273f93c": "synthetic_retry_empty_completion",
    "7eceb1c8-4a7b-4899-9650-b54f7d432d24": "empty_completion_after_long_api_path_wait",
    "b59e45f0-050e-448e-8a97-abee2f4b89c6": "thinking_only_empty_completion",
}
SUCCESSFUL_TIMEOUT_ID = "06069bcf-6f36-4000-aa41-85501e197164"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def preview_tmp_dir():
    path = Path(tempfile.mkdtemp(prefix="cc-j2a-preview-test-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def test_source_contract_hash_mismatch_fails_before_output_write(
    tmp_path: Path, preview_tmp_dir: Path,
) -> None:
    registry = json.loads(REGISTRY_PATH.read_text())
    registry["source_contract"]["required_inputs"][0]["sha256"] = "0" * 64
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry))
    canonical = canonical_source_paths()
    output = preview_tmp_dir / "preview"
    with pytest.raises(SourceContractError, match="J1 SHA-256"):
        generate_preview(output, source_paths=SourcePaths(
            registry=registry_path,
            review_manifest=canonical.review_manifest,
            trial_review=canonical.trial_review,
            trial_evidence=canonical.trial_evidence,
        ))
    assert not output.exists()


def test_trial_set_mismatch_fails_closed() -> None:
    with pytest.raises(SourceContractError, match="trial set mismatch"):
        validate_trial_sets(
            [{"trial_id": "trial-a"}, {"trial_id": "trial-b"}],
            [{"trial_id": "trial-a"}, {"trial_id": "trial-c"}],
        )


def test_manifest_bound_trial_set_mismatch_fails_before_output_write(
    tmp_path: Path, preview_tmp_dir: Path,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    review_path = source_dir / "trial_review.csv"
    evidence_path = source_dir / "trial_evidence.jsonl"
    manifest_path = source_dir / "review_manifest.json"
    shutil.copy2(REVIEW_DIR / "trial_review.csv", review_path)
    shutil.copy2(REVIEW_DIR / "review_manifest.json", manifest_path)

    lines = (REVIEW_DIR / "trial_evidence.jsonl").read_text().splitlines()
    first = json.loads(lines[0])
    first["trial_id"] = "00000000-0000-0000-0000-000000000099"
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    evidence_path.write_text("\n".join(lines) + "\n")

    evidence_hash = sha256(evidence_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["outputs"]["trial_evidence.jsonl"]["sha256"] = evidence_hash
    manifest["outputs"]["trial_evidence.jsonl"]["bytes"] = evidence_path.stat().st_size
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))

    registry = json.loads(REGISTRY_PATH.read_text())
    required = next(
        item for item in registry["source_contract"]["required_inputs"]
        if item["path"] == "trial_evidence.jsonl"
    )
    required["sha256"] = evidence_hash
    registry["source_contract"]["manifest_sha256"] = sha256(manifest_path)
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry, sort_keys=True))

    output = preview_tmp_dir / "preview"
    with pytest.raises(SourceContractError, match="trial set mismatch"):
        generate_preview(output, source_paths=SourcePaths(
            registry=registry_path,
            review_manifest=manifest_path,
            trial_review=review_path,
            trial_evidence=evidence_path,
        ))
    assert not output.exists()


def test_actual_preview_is_deterministic_complete_and_manifest_bound(preview_tmp_dir: Path) -> None:
    first = preview_tmp_dir / "first"
    second = preview_tmp_dir / "second"
    counts_first = generate_preview(first)
    counts_second = generate_preview(second)
    assert counts_first == counts_second
    expected_names = {
        "trial_failure_taxonomy.jsonl",
        "taxonomy_counts.json",
        "review_queue.csv",
        "failure_taxonomy_manifest.json",
        "README.md",
    }
    assert {path.name for path in first.iterdir()} == expected_names
    assert {path.name for path in second.iterdir()} == expected_names
    for name in expected_names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name

    rows = read_jsonl(first / "trial_failure_taxonomy.jsonl")
    input_ids = {
        row["trial_id"]
        for row in csv.DictReader((REVIEW_DIR / "trial_review.csv").open())
    }
    assert len(rows) == 960
    assert {row["trial_id"] for row in rows} == input_ids
    assert [row["trial_id"] for row in rows] == sorted(input_ids)
    assert all(set(row) == {"trial_id", "arm_id", "task_id", "raw_outcome", *AXIS_IDS} for row in rows)

    manifest = json.loads((first / "failure_taxonomy_manifest.json").read_text())
    assert manifest["scope_fingerprint"] == json.loads(
        (REVIEW_DIR / "review_manifest.json").read_text()
    )["scope_fingerprint"]
    for name, metadata in manifest["outputs"].items():
        assert metadata["sha256"] == sha256(first / name)
        assert metadata["bytes"] == (first / name).stat().st_size

    diagnostics = counts_first["diagnostics"]
    assert diagnostics["verifier_strict_refinement_counts"] == {
        "verifier_environment_issue": 0,
        "dependency_or_import_error": 5,
        "syntax_or_compile_error": 0,
        "timeout_inside_verifier": 0,
        "runtime_exception_in_solution": 0,
        "wrong_file_or_path": 0,
    }
    assert diagnostics["assertion_strict_refinement_counts"] == {
        "performance_threshold_failure": 0,
        "numerical_or_data_mismatch": 0,
        "missing_expected_file_or_content": 2,
        "behavior_mismatch": 0,
        "output_mismatch": 0,
    }
    assert diagnostics["stdout_assertion_candidates"] == {
        "accepted_assertion_failure_candidates": 167,
        "no_pytest_failures_section": 56,
        "zero_strict_assertion_subtypes": 109,
        "multiple_strict_assertion_subtypes": 0,
        "one_strict_assertion_subtype": 2,
    }
    assert diagnostics["no_substantive_attempt_confidence"] == {
        "high": 10,
        "medium": 27,
        "low": 0,
    }
    assert diagnostics["manual_review_union_count"] == 243


def test_actual_response_path_ids_and_successful_timeout_are_preserved(preview_tmp_dir: Path) -> None:
    output = preview_tmp_dir / "preview"
    generate_preview(output)
    rows = {row["trial_id"]: row for row in read_jsonl(output / "trial_failure_taxonomy.jsonl")}
    assert {
        trial_id: rows[trial_id]["response_path_class"]["value"]
        for trial_id in KNOWN_RESPONSE_PATH_IDS
    } == KNOWN_RESPONSE_PATH_IDS
    assert rows[SUCCESSFUL_TIMEOUT_ID]["raw_outcome"] == "success"
    assert rows[SUCCESSFUL_TIMEOUT_ID]["trajectory_disposition"]["value"] == (
        "timeout_after_meaningful_progress"
    )
    assert rows[SUCCESSFUL_TIMEOUT_ID]["trajectory_disposition"]["value"] != "successful_completion"


def test_preview_has_no_source_excerpt_or_private_reasoning_fields(preview_tmp_dir: Path) -> None:
    output = preview_tmp_dir / "preview"
    generate_preview(output)
    forbidden_keys = {
        "hidden_reasoning_retained",
        "verifier_stdout_excerpt",
        "failure_message",
        "visible_assistant_excerpts",
        "visible_result_excerpts",
    }

    def walk(value):
        if isinstance(value, dict):
            assert forbidden_keys.isdisjoint(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for row in read_jsonl(output / "trial_failure_taxonomy.jsonl"):
        walk(row)


def test_classifier_and_generator_have_no_database_r2_or_network_imports() -> None:
    paths = [
        ROOT / "scripts/lib/failure_taxonomy_classifier.py",
        ROOT / "scripts/generate_failure_taxonomy_snapshot.py",
    ]
    forbidden_roots = {
        "boto3", "botocore", "httpx", "psycopg", "requests", "socket", "urllib",
        "live_db", "artifact_content",
    }
    for path in paths:
        tree = ast.parse(path.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert imports.isdisjoint(forbidden_roots), (path, imports & forbidden_roots)


def test_frozen_review_hashes_still_match_j1_contract() -> None:
    registry = json.loads(REGISTRY_PATH.read_text())
    source = registry["source_contract"]
    assert sha256(REVIEW_DIR / "review_manifest.json") == source["manifest_sha256"]
    for required in source["required_inputs"]:
        assert sha256(REVIEW_DIR / required["path"]) == required["sha256"]


def test_output_directory_is_explicit_preview_only_and_outside_repository(preview_tmp_dir: Path) -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        generate_preview(ROOT / "results/manual_verification/forbidden-j2a-preview")
    existing = preview_tmp_dir / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("keep")
    with pytest.raises(FileExistsError, match="not empty"):
        generate_preview(existing)
