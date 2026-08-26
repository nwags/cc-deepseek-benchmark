from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_openai_provider_evidence.py"

spec = importlib.util.spec_from_file_location(
    "ingest_openai_provider_evidence",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None

ingest = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ingest
spec.loader.exec_module(ingest)


def test_reviewed_normalized_hashes_match():
    assert ingest.verify_normalized_hashes() == (
        ingest.NORMALIZED_HASHES
    )


def test_plan_contains_exact_two_selected_openai_sweeps():
    plan = ingest.build_plan()

    assert plan["provider"] == "openai"
    assert {
        row["arm_id"]
        for row in plan["arm_runs"]
    } == {
        "router-gpt-5.4",
        "router-gpt-5.5",
    }


def test_plan_uses_two_distinct_june_provider_sources():
    plan = ingest.build_plan()
    sources = {
        row["source_key"]: row
        for row in plan["sources"]
    }

    assert set(sources) == {"usage", "cost"}
    assert (
        sources["usage"]["source_sha256"]
        != sources["cost"]["source_sha256"]
    )

    assert sources["usage"]["evidence_kind"] == "usage_export"
    assert sources["cost"]["evidence_kind"] == "billing_export"


def test_plan_preserves_openai_cache_semantics():
    plan = ingest.build_plan()

    for arm in plan["arm_runs"]:
        usage = arm["provider_usage"]

        assert usage["cache_creation_input_tokens"] is None
        assert (
            usage["ordinary_input_tokens"]
            + usage["cache_read_input_tokens"]
            == ingest.ARM_CONTRACT[arm["arm_id"]]["input_tokens"]
        )


def test_plan_uses_provider_aggregate_usage_authority():
    plan = ingest.build_plan()

    for arm in plan["arm_runs"]:
        reconciliation = arm["usage_reconciliation"]

        assert (
            reconciliation["selected_usage_authority"]
            == "provider_aggregate_usage"
        )
        assert (
            reconciliation["validation_status"]
            == "validated_exact"
        )
        assert (
            reconciliation["model_identity_status"]
            == "matched"
        )


def test_plan_uses_exact_provider_billed_cost():
    plan = ingest.build_plan()

    for arm in plan["arm_runs"]:
        reconciliation = arm["cost_reconciliation"]

        assert (
            reconciliation["selected_cost_basis"]
            == "provider_billed"
        )
        assert (
            reconciliation["selected_cost_relation"]
            == "exact"
        )
        assert (
            reconciliation["validation_status"]
            == "validated_exact"
        )


def test_plan_does_not_fabricate_trial_or_outcome_cost():
    plan = ingest.build_plan()

    for arm in plan["arm_runs"]:
        assert arm["allocation_policy"] == {
            "trial_cost": "unavailable_provider_aggregate",
            "outcome_cost": "unavailable_provider_aggregate",
        }


def test_expected_write_surface_is_new_evidence_schema_only():
    plan = ingest.build_plan()

    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 2,
        "benchmark_provider_usage_evidence": 2,
        "benchmark_provider_pricing_snapshots": 0,
        "benchmark_provider_cost_evidence": 2,
        "benchmark_usage_reconciliations": 2,
        "benchmark_usage_reconciliation_sources": 2,
        "benchmark_cost_reconciliations": 2,
        "benchmark_cost_reconciliation_sources": 2,
        "benchmark_evidence_promotion_gates": 0,
    }


def test_script_has_no_commit_or_permanent_write_mode():
    source = SCRIPT.read_text(encoding="utf-8")

    assert ".commit(" not in source
    assert "--apply" not in source


def test_script_has_no_historical_insert_update_delete_surface():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    forbidden = (
        "insert into benchmark.benchmark_trials",
        "update benchmark.benchmark_trials",
        "delete from benchmark.benchmark_trials",
        "insert into benchmark.benchmark_runs",
        "update benchmark.benchmark_runs",
        "delete from benchmark.benchmark_runs",
        "insert into benchmark.benchmark_arm_runs",
        "update benchmark.benchmark_arm_runs",
        "delete from benchmark.benchmark_arm_runs",
        "insert into benchmark.benchmark_trial_cost_coverage",
        "update benchmark.benchmark_trial_cost_coverage",
        "delete from benchmark.benchmark_trial_cost_coverage",
    )

    for phrase in forbidden:
        assert phrase not in source


def test_cli_requires_explicit_mode():
    with pytest.raises(SystemExit):
        ingest.parse_args([])

    assert ingest.parse_args(["--plan"]).plan is True
    assert (
        ingest.parse_args(["--rollback-only"]).rollback_only
        is True
    )


def test_failure_payload_does_not_expose_exception_message():
    secret = (
        "postgresql://user:password@example.invalid/database"
    )

    diagnostics = ingest.Diagnostics(stage="synthetic")

    payload = ingest.failure_payload(
        mode="rollback-only",
        diagnostics=diagnostics,
        exc=RuntimeError(secret),
    )

    serialized = json.dumps(payload)

    assert secret not in serialized
    assert "password" not in serialized
    assert payload["failed_stage"] == "synthetic"
