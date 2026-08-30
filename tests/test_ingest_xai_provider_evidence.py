from __future__ import annotations
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_xai_provider_evidence.py"
SPEC = importlib.util.spec_from_file_location("ingest_xai_provider_evidence", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ingest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ingest
SPEC.loader.exec_module(ingest)

def test_reviewed_input_hashes_match():
    assert ingest.verify_input_hashes() == ingest.EXPECTED_INPUT_HASHES

def test_plan_matches_reviewed_authority():
    plan = ingest.build_plan()
    assert plan["reviewed_plan_sha256"] == "eac1bc5e7070ef46d6ae9488ac4ea7f03874a9a91bf215fe48a32fb7ae9aba49"
    assert plan["plan_version"] == "xai-provider-evidence-v1"
    assert plan["provider"] == "xai"
    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 3,
        "benchmark_provider_usage_evidence": 0,
        "benchmark_provider_pricing_snapshots": 1,
        "benchmark_provider_cost_evidence": 2,
        "benchmark_usage_reconciliations": 1,
        "benchmark_usage_reconciliation_sources": 2,
        "benchmark_cost_reconciliations": 1,
        "benchmark_cost_reconciliation_sources": 3,
        "benchmark_evidence_promotion_gates": 0,
    }

def test_provider_usage_evidence_stays_empty():
    assert ingest.build_plan()["provider_usage_evidence"] == []

def test_two_dashboard_totals_are_context_only():
    rows = ingest.build_plan()["provider_cost_evidence"]
    assert len(rows) == 2
    by_date = {row["raw_metadata"]["observation_date"]: row for row in rows}
    assert set(by_date) == {"2026-06-19", "2026-08-27"}
    assert Decimal(by_date["2026-06-19"]["amount_usd"]) == Decimal("6.36")
    assert Decimal(by_date["2026-08-27"]["amount_usd"]) == Decimal("42.40")
    for row in rows:
        assert row["arm_run_id"] is None
        assert row["trial_id"] is None
        assert row["provider_model"] is None
        assert row["cost_kind"] == "provider_dashboard_total"
        assert row["allocation_scope"] == "provider_window"
        assert row["completeness_status"] == "aggregate_only"
        assert row["raw_metadata"]["selected_run_allocable"] is False

def test_june_dashboard_token_discrepancy_is_preserved():
    june = next(row["raw_metadata"] for row in ingest.build_plan()["provider_cost_evidence"] if row["raw_metadata"]["observation_date"] == "2026-06-19")
    assert june["token_total_canonical"] == 5927385
    assert june["token_total_separately_observed"] == 5927462
    assert june["token_total_canonical"] != june["token_total_separately_observed"]

def test_selected_cost_semantics_are_preserved():
    row = ingest.build_plan()["cost_reconciliations"][0]
    assert Decimal(row["selected_cost_usd"]) == Decimal("6.418694")
    assert row["provider_billed_cost_usd"] is None
    assert row["selected_cost_basis"] == "lower_bound_provider_evidence"
    assert row["selected_cost_relation"] == "lower_bound"
    assert row["validation_status"] == "validated_qualified"

def test_selected_rate_arithmetic_matches_reviewed_lower_bound():
    plan = ingest.build_plan()
    selected = plan["selected_runs"][0]
    spec = ingest.ARM_CONTRACT[selected["arm_id"]]
    reconstructed = ingest.reconstruct_cost(cache_hit_tokens=selected["harness_cache_tokens"], cache_miss_tokens=selected["harness_cache_miss_tokens"], output_tokens=selected["harness_output_tokens"], spec=spec)
    assert reconstructed == Decimal("6.418694")

def test_script_has_only_guarded_provider_write_surface():
    source = SCRIPT.read_text(encoding="utf-8")
    for pattern in (r"\bupdate\s+benchmark\.", r"\bdelete\s+from\b", r"\btruncate\b", r"\bdrop\s+table\b"):
        assert not re.search(pattern, source, flags=re.IGNORECASE)
    assert source.lower().count("insert into benchmark.") == 8
    assert source.count("connection.commit()") == 1
    assert "--rollback-only" in source
    assert "--apply" in source
    assert "second_connection_zero_persistence" in source
    assert "second_connection_verification" in source
    assert "apply_permanent(" in source

def test_no_gemini_provider_literals_remain():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "google-gemini" not in source
    assert "Gemini" not in source
    assert "gemini_empty" not in source
    assert "exact_gemini_state" not in source

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
    payload = ingest.failure_payload(mode="check-only", diagnostics=diagnostics, exc=RuntimeError("secret-looking diagnostic detail"))
    assert "secret-looking diagnostic detail" not in json.dumps(payload)
    assert payload["error_type"] == "RuntimeError"

def test_provider_detail_verifier_accepts_reviewed_xai_plan_shape():
    plan = ingest.build_plan()
    source_by_key = {
        row["source_key"]: row
        for row in plan["sources"]
    }

    source_rows = [
        (
            row["provider"],
            row["evidence_kind"],
            row["source_scope"],
            row["provider_reference"],
            row["source_sha256"],
            row["source_format"],
            row["integrity_status"],
            row["notes"],
            True,
            True,
            True,
            row.get("raw_metadata", {}),
        )
        for row in plan["sources"]
    ]

    pricing_rows = [
        (
            source_by_key[row["source_key"]]["source_sha256"],
            row["provider"],
            row["provider_model"],
            row["currency"],
            row["effective_from"],
            row["effective_until"],
            row["pricing_semantics"],
            row["pricing_rules"],
            row["official_source_uri"],
            row["notes"],
            row.get("raw_metadata", {}),
        )
        for row in plan["pricing_snapshots"]
    ]

    snapshot_sha = source_by_key[
        "xai_sanitized_provider_snapshot"
    ]["source_sha256"]

    cost_rows = [
        (
            snapshot_sha,
            True,
            True,
            True,
            None,
            row["cost_kind"],
            Decimal(row["amount_usd"]),
            row["currency"],
            row["allocation_scope"],
            row["completeness_status"],
            row["notes"],
            row["raw_metadata"],
        )
        for row in plan["provider_cost_evidence"]
    ]

    source_sha_by_key = {
        key: row["source_sha256"]
        for key, row in source_by_key.items()
    }

    link_rows = [
        (
            "usage",
            row["arm_id"],
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan[
            "usage_reconciliation_source_links"
        ]
    ] + [
        (
            "cost",
            row["arm_id"],
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan[
            "cost_reconciliation_source_links"
        ]
    ]

    class FakeCursor:
        def __init__(self):
            self.rows = []
            self.one = None

        def execute(
            self,
            query,
            parameters=(),
        ):
            sql = " ".join(
                str(query).lower().split()
            )
            self.rows = []
            self.one = None

            if (
                "from benchmark.benchmark_provider_evidence_sources"
                in sql
                and "select provider," in sql
            ):
                self.rows = source_rows
            elif (
                "from benchmark.benchmark_provider_pricing_snapshots pricing"
                in sql
            ):
                self.rows = pricing_rows
            elif (
                "select count(*)"
                in sql
                and "benchmark_provider_usage_evidence"
                in sql
            ):
                self.one = (0,)
            elif (
                "from benchmark.benchmark_provider_cost_evidence evidence"
                in sql
            ):
                self.rows = cost_rows
            elif (
                "from benchmark.benchmark_usage_reconciliation_sources link"
                in sql
                and "union all"
                in sql
            ):
                self.rows = link_rows
            else:
                raise AssertionError(
                    f"unexpected verifier query: {sql}"
                )

        def fetchall(self):
            return list(self.rows)

        def fetchone(self):
            if self.one is None:
                raise AssertionError(
                    "fetchone called without one-row result"
                )
            return self.one

    result = ingest.verify_provider_evidence_details(
        FakeCursor(),
        plan,
        {
            "router-grok-build-0.1":
                "00000000-0000-0000-0000-000000000001",
        },
    )

    assert result == {
        "source_rows": "pass",
        "pricing_rows": "pass",
        "usage_evidence_rows": "pass",
        "cost_evidence_rows": "pass",
        "reconciliation_source_links": "pass",
    }
