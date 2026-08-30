from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_qwen_provider_evidence.py"

SPEC = importlib.util.spec_from_file_location(
    "ingest_qwen_provider_evidence",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None

ingest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ingest
SPEC.loader.exec_module(ingest)


def test_reviewed_snapshot_and_source_hashes_match():
    hashes = ingest.verify_input_hashes()
    assert (
        hashes[
            "results/phase3/supplemental/qwen_provider_evidence_snapshot_20260828.json"
        ]
        == "c334c57d143dc59cf3c81af24a233ed061f07a8902f95431da1d2401e53ab556"
    )


def test_plan_matches_reviewed_authority():
    plan = ingest.build_plan()

    assert (
        plan["reviewed_plan_sha256"]
        == "0836cdb8b0078f9524f736f099d68d2d6138c8f068b2ec074bdb931b456db119"
    )
    assert plan["plan_version"] == "qwen-provider-evidence-v1"
    assert plan["provider"] == "dashscope-qwen"
    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 5,
        "benchmark_provider_usage_evidence": 0,
        "benchmark_provider_pricing_snapshots": 1,
        "benchmark_provider_cost_evidence": 3,
        "benchmark_usage_reconciliations": 1,
        "benchmark_usage_reconciliation_sources": 3,
        "benchmark_cost_reconciliations": 1,
        "benchmark_cost_reconciliation_sources": 3,
        "benchmark_evidence_promotion_gates": 0,
    }


def test_selected_cost_stays_lower_bound_and_provider_billed_null():
    row = ingest.build_plan()["cost_reconciliations"][0]

    assert Decimal(row["selected_cost_usd"]) == Decimal("2.50442432")
    assert Decimal(row["provider_rate_reconstructed_cost_usd"]) == Decimal(
        "2.50442432"
    )
    assert row["provider_billed_cost_usd"] is None
    assert row["selected_cost_basis"] == "lower_bound_provider_evidence"
    assert row["selected_cost_relation"] == "lower_bound"
    assert row["validation_status"] == "validated_qualified"


def test_selected_usage_authority_stays_harness_validated():
    row = ingest.build_plan()["usage_reconciliations"][0]

    assert row["selected_usage_authority"] == "harness_usage_validated"
    assert row["validation_status"] == "validated_qualified"
    assert row["provider_observed_model"] is None
    assert row["provider_ordinary_input_tokens"] is None
    assert row["provider_cache_read_input_tokens"] is None
    assert row["provider_cache_creation_input_tokens"] is None
    assert row["provider_output_tokens"] is None
    assert row["provider_request_count"] is None


def test_billing_line_items_are_not_mislabeled_as_provider_requests():
    plan = ingest.build_plan()

    assert plan["provider_usage_evidence"] == []
    assert plan["write_counts"]["benchmark_provider_usage_evidence"] == 0

    snapshot = json.loads(
        ingest.QWEN_SNAPSHOT.read_text(encoding="utf-8")
    )
    reason = snapshot["provider_usage_evidence_exclusion_reason"]
    assert "billing line items" in reason
    assert "request_count" in reason


def test_historical_provider_cost_context_is_not_selected_run_billing():
    rows = ingest.build_plan()["provider_cost_evidence"]

    assert len(rows) == 3

    by_kind = {row["cost_kind"]: row for row in rows}

    assert Decimal(by_kind["account_spend"]["amount_usd"]) == Decimal(
        "31.310889920"
    )
    assert Decimal(by_kind["overhead"]["amount_usd"]) == Decimal("30")
    assert Decimal(
        by_kind["provider_rate_reconstruction"]["amount_usd"]
    ) == Decimal("1.310889920")

    for row in rows:
        assert row["arm_run_id"] is None
        assert row["trial_id"] is None
        assert row["allocation_scope"] == "account_window"
        assert row["raw_metadata"]["selected_run_allocable"] is False
        assert row["raw_metadata"]["relation_to_selected_run"] == (
            "predates_selected_run"
        )


def test_pricing_discount_semantics_are_preserved():
    pricing = ingest.build_plan()["pricing_snapshots"][0]
    rules = pricing["pricing_rules"]

    assert pricing["provider_model"] == "qwen3.7-plus"
    assert rules["ordinary_input_usd_per_million"] == "0.32"
    assert rules["cached_input_usd_per_million"] == "0.064"
    assert rules["output_usd_per_million"] == "1.28"

    assert rules["raw_list_ordinary_input_usd_per_million"] == "0.4000"
    assert rules["raw_list_cached_input_usd_per_million"] == "0.08000"
    assert rules["raw_list_output_usd_per_million"] == "1.6000"
    assert rules["payable_fraction_of_list"] == "0.8"

    assert rules["selected_request_tier_max_tokens"] == 256_000
    assert rules["selected_run_max_observed_request_tokens"] == 45_509
    assert rules["selected_run_all_usage_bearing_requests_within_tier"] is True


def test_selected_rate_arithmetic_matches_reviewed_lower_bound():
    reconstructed = ingest.reconstruct_selected_cost(
        input_tokens=3_177_366,
        cache_tokens=0,
        output_tokens=1_162_240,
    )
    assert reconstructed == Decimal("2.50442432")


def test_raw_provider_source_is_sanitized_and_hash_pinned():
    plan = ingest.build_plan()
    source = next(
        row
        for row in plan["sources"]
        if row["source_key"] == "qwen_raw_alibaba_billing_export"
    )

    assert source["evidence_kind"] == "billing_export"
    assert source["source_scope"] == "account_window"
    assert source["source_sha256"] == (
        "51b2220da055056fa80fa761fe0f13a25"
        "fafe736ed3df8ccaeb44c65bece308b"
    )
    assert source["size_bytes"] == 243_803
    assert source["integrity_status"] == "sha256_verified"

    text = json.dumps(source)
    assert "/home/" not in text
    assert ".run/review" not in text
    assert "buyerId" not in text
    assert "@" not in text


def test_source_link_roles_match_reviewed_plan():
    plan = ingest.build_plan()

    assert {
        row["evidence_role"]
        for row in plan["usage_reconciliation_source_links"]
    } == {
        "aggregate_usage",
        "model_identity",
        "context",
    }

    assert {
        row["evidence_role"]
        for row in plan["cost_reconciliation_source_links"]
    } == {
        "lower_bound",
        "pricing",
        "context",
    }


def test_script_has_only_guarded_provider_write_surface():
    source = SCRIPT.read_text(encoding="utf-8")

    for pattern in (
        r"\bupdate\s+benchmark\.",
        r"\bdelete\s+from\b",
        r"\btruncate\b",
        r"\bdrop\s+table\b",
        r"\bmerge\s+into\b",
        r"\balter\s+table\b",
        r"\bon\s+conflict\b",
    ):
        assert not re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        )

    assert source.lower().count("insert into benchmark.") == 7
    assert source.count("connection.commit()") == 1
    assert "--rollback-only" in source
    assert "--apply" in source
    assert "second_connection_zero_persistence" in source
    assert "second_connection_verification" in source
    assert "apply_permanent(" in source


def test_no_other_provider_ingestion_literals_remain():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "moonshot-kimi" not in source
    assert "exact_kimi_state" not in source
    assert "xai_empty" not in source
    assert "google-gemini" not in source


def test_cli_requires_exactly_one_explicit_mode():
    with pytest.raises(SystemExit):
        ingest.parse_args([])

    assert ingest.parse_args(["--plan"]).plan is True
    assert ingest.parse_args(["--check-only"]).check_only is True
    assert ingest.parse_args(["--rollback-only"]).rollback_only is True
    assert ingest.parse_args(["--apply"]).apply is True


def test_failure_payload_does_not_expose_exception_message():
    diagnostics = ingest.Diagnostics()
    diagnostics.enter("synthetic_failure")

    payload = ingest.failure_payload(
        mode="check-only",
        diagnostics=diagnostics,
        exc=RuntimeError("secret-looking diagnostic detail"),
    )

    assert "secret-looking diagnostic detail" not in json.dumps(payload)
    assert payload["error_type"] == "RuntimeError"


def test_snapshot_contains_no_private_paths_or_identity_values():
    raw = ingest.QWEN_SNAPSHOT.read_text(encoding="utf-8")

    for forbidden in (
        "/home/",
        ".run/review",
        ".secrets/",
        "SUPABASE_DB_URL",
        "buyerId",
        "@",
    ):
        assert forbidden not in raw
