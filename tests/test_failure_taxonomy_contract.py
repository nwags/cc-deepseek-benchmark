import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs/dashboard/failure_taxonomy_v1.json"
REVIEW_DIR = ROOT / "results/manual_verification/comprehensive_review_20260731"

EXPECTED_VALUES = {
    "response_path_class": [
        "synthetic_retry_empty_completion",
        "empty_completion_after_long_api_path_wait",
        "thinking_only_empty_completion",
        "empty_completion",
        "invalid_response_path",
        "unknown",
        "not_applicable",
    ],
    "verifier_failure_category": [
        "none",
        "verifier_environment_issue",
        "syntax_or_compile_error",
        "dependency_or_import_error",
        "wrong_file_or_path",
        "timeout_inside_verifier",
        "runtime_exception_in_solution",
        "test_assertion_failure",
        "missing_or_wrong_output",
        "no_meaningful_code_change",
        "partial_solution",
        "unclassified_failure",
    ],
    "assertion_failure_category": [
        "none",
        "performance_threshold_failure",
        "numerical_or_data_mismatch",
        "missing_expected_file_or_content",
        "behavior_mismatch",
        "output_mismatch",
        "unclassified_assertion",
    ],
    "trajectory_disposition": [
        "successful_completion",
        "no_substantive_attempt",
        "early_abandonment",
        "partial_implementation",
        "plausible_but_incorrect_completion",
        "near_miss_cleanup_or_packaging_only",
        "near_miss_one_behavioral_defect",
        "repeated_unproductive_iteration",
        "timeout_after_meaningful_progress",
        "completed_work_with_verifier_or_infrastructure_issue",
        "indeterminate",
    ],
}


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registry_has_exact_versioned_axes_labels_definitions_and_ordering() -> None:
    registry = load_registry()
    assert registry["schema_version"] == "dashboard-failure-taxonomy-registry-v1"
    assert registry["taxonomy_version"] == "1.0.0"
    assert registry["contract_status"] == "foundation_only"
    assert [axis["id"] for axis in registry["axes"]] == list(EXPECTED_VALUES)

    for expected_order, axis in enumerate(registry["axes"], start=1):
        assert axis["order"] == expected_order
        assert axis["label"].strip()
        assert axis["definition"].strip()
        assert axis["manual_review_guidance"].strip()
        entries = axis["entries"]
        assert [entry["id"] for entry in entries] == EXPECTED_VALUES[axis["id"]]
        assert [entry["order"] for entry in entries] == list(range(1, len(entries) + 1))
        assert len({entry["id"] for entry in entries}) == len(entries)
        assert all(entry["label"].strip() for entry in entries)
        assert all(entry["definition"].strip() for entry in entries)


def test_required_fallbacks_success_and_legacy_boundary_are_explicit() -> None:
    registry = load_registry()
    values = {axis["id"]: {entry["id"] for entry in axis["entries"]} for axis in registry["axes"]}
    assert "successful_completion" in values["trajectory_disposition"]
    assert "indeterminate" in values["trajectory_disposition"]
    assert "unknown" in values["response_path_class"]
    assert "not_applicable" in values["response_path_class"]
    assert "unclassified_failure" in values["verifier_failure_category"]
    assert "unclassified_assertion" in values["assertion_failure_category"]
    assert all("suspect_noop" not in entry_id for axis_values in values.values() for entry_id in axis_values)
    assert registry["legacy_compatibility"]["public_status"] == "compatibility_only"
    assert set(registry["legacy_compatibility"]["retained_fields"]) == {
        "suspect_noop_zero_token",
        "suspect_noop_count",
    }
    assert registry["normalizations"] == [{
        "source_axis": "existing_activity_subtype",
        "source_value": "empty_completion_zero_usage",
        "target_axis": "response_path_class",
        "target_value": "empty_completion",
        "reason": "The public response-path taxonomy does not encode token usage in the category name.",
    }]


def test_future_diagnosis_and_manifest_provenance_contract_is_complete() -> None:
    registry = load_registry()
    output = registry["future_output_contract"]
    assert output["generation_mode"] == "offline_second_stage"
    assert output["one_row_per_input_trial"] is True
    assert set(output["required_trial_fields"]) == {"trial_id", *EXPECTED_VALUES.keys()}
    assert {field["name"] for field in output["diagnosis_object_fields"]} == {
        "value",
        "label",
        "definition",
        "confidence",
        "evidence_basis",
        "supporting_artifact_ids",
        "manual_review_required",
    }
    bindings = " ".join(output["required_manifest_bindings"])
    for required in ["registry", "manifest", "scope fingerprint", "classifier", "SHA-256"]:
        assert required in bindings


def test_source_contract_is_bound_to_the_frozen_checked_in_review() -> None:
    registry = load_registry()
    source = registry["source_contract"]
    manifest_path = ROOT / source["manifest_path"]
    manifest = json.loads(manifest_path.read_text())
    assert source["canonical_input_directory"] == (
        "results/manual_verification/comprehensive_review_20260731"
    )
    assert source["manifest_sha256"] == sha256(manifest_path)
    assert source["scope_fingerprint"] == manifest["scope_fingerprint"]
    assert source["trial_count"] == 960
    assert source["trial_count"] == manifest["row_counts"]["trial_review.csv"]
    assert source["trial_count"] == manifest["row_counts"]["trial_evidence.jsonl"]
    for required in source["required_inputs"]:
        path = REVIEW_DIR / required["path"]
        assert required["rows"] == manifest["row_counts"][required["path"]]
        assert required["sha256"] == manifest["outputs"][required["path"]]["sha256"]
        assert required["sha256"] == sha256(path)
    assert ".review-cache" in source["forbidden_canonical_inputs"]


def test_conservative_evidence_rules_and_private_reasoning_boundary_are_explicit() -> None:
    registry = load_registry()
    rules = {rule["id"]: rule for rule in registry["eligibility_rules"]}
    assert {
        "response_path_specific_empty_class",
        "no_substantive_attempt",
        "timeout_after_meaningful_progress",
        "completed_work_with_verifier_or_infrastructure_issue",
        "near_miss_one_behavioral_defect",
        "near_miss_cleanup_or_packaging_only",
        "repeated_unproductive_iteration",
        "partial_or_plausible_completion",
        "verifier_specific_category",
        "verifier_axis_none",
        "assertion_specific_category",
        "successful_completion",
    } <= rules.keys()
    assert "missing" in rules["no_substantive_attempt"]["fallback"]
    assert "long runtime" in rules["repeated_unproductive_iteration"]["fallback"]
    assert "alone is insufficient" in rules["repeated_unproductive_iteration"]["fallback"]
    assert "Raw reward=0" in rules["partial_or_plausible_completion"]["fallback"]
    assert "Hidden or private model reasoning" in registry["evidence_policy"]["hidden_reasoning"]
    assert "provider" in registry["evidence_policy"]["attribution"]


def test_successful_completion_is_an_ordinary_success_fallback_not_raw_success_precedence() -> None:
    registry = load_registry()
    trajectory = next(axis for axis in registry["axes"] if axis["id"] == "trajectory_disposition")
    success = next(entry for entry in trajectory["entries"] if entry["id"] == "successful_completion")
    rule = next(rule for rule in registry["eligibility_rules"] if rule["id"] == "successful_completion")
    assert "does not support a more specific anomalous trajectory disposition" in success["definition"]
    assert "no positive retained evidence" in rule["requires"]
    assert "use that supported disposition instead" in rule["fallback"]
    assert "must not override stronger positive trajectory evidence" in rule["fallback"]
    assert "A retained successful raw benchmark outcome;" not in rule["requires"]


def test_verifier_axis_is_independent_and_requires_verifier_specific_failure_evidence() -> None:
    registry = load_registry()
    verifier = next(axis for axis in registry["axes"] if axis["id"] == "verifier_failure_category")
    entries = {entry["id"]: entry for entry in verifier["entries"]}
    rules = {rule["id"]: rule for rule in registry["eligibility_rules"]}
    assert "not a catch-all for response-path, policy, or termination events" in verifier["definition"]
    assert "Raw outcome=failure does not establish a verifier failure" in verifier["manual_review_guidance"]
    assert "non-successful trials" in entries["none"]["definition"]
    assert "another independent axis" in entries["none"]["definition"]
    assert "Raw benchmark failure alone does not establish" in entries["unclassified_failure"]["definition"]
    assert "Raw outcome=failure alone does not imply" in rules["verifier_specific_category"]["fallback"]
    assert "Provider-policy refusal" in rules["verifier_axis_none"]["fallback"]
    assert "invalid response path" in rules["verifier_axis_none"]["fallback"]
    assert "non-verifier timeout" in rules["verifier_axis_none"]["fallback"]
    assert "generic termination or timeout evidence is insufficient" in entries["timeout_inside_verifier"]["definition"]
    assert "verifier-specific placement" in rules["verifier_axis_none"]["fallback"]


def test_registry_order_is_display_only_and_never_implicit_classifier_precedence() -> None:
    policy = load_registry()["selection_policy"]
    assert "presentation/display order only" in policy["entry_order_semantics"]
    assert "not classifier precedence" in policy["entry_order_semantics"]
    assert "independent axes" in policy["axis_independence"]
    assert "most specific diagnosis justified by retained evidence" in policy["diagnosis_selection"]
    assert "must define and test it explicitly" in policy["classifier_precedence"]
    assert "never be inferred from registry order" in policy["classifier_precedence"]
    assert "ordinary-success fallback" in policy["ordinary_success_fallback"]


def test_typescript_consumer_is_static_and_has_no_database_or_artifact_reader_dependency() -> None:
    source = (ROOT / "apps/dashboard/src/lib/failure-taxonomy.ts").read_text()
    imports = [line.strip() for line in source.splitlines() if line.startswith("import ")]
    assert imports == [
        'import rawRegistry from "../../../../configs/dashboard/failure_taxonomy_v1.json";'
    ]
    for forbidden in ["./db", "review-data", "phase3-reviewed", "artifact-content", "@aws-sdk", '"pg"']:
        assert forbidden not in imports[0]
