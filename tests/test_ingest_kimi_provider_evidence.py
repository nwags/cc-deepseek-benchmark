from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_kimi_provider_evidence.py"

SPEC = importlib.util.spec_from_file_location(
    "ingest_kimi_provider_evidence",
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
            "results/phase3/supplemental/kimi_provider_evidence_snapshot_20260827.json"
        ]
        == "929d489496b730ac053a2fa57f8f5c8e1d5701905fd482be788c67913a909f1d"
    )


def test_plan_matches_reviewed_authority():
    plan = ingest.build_plan()

    assert (
        plan["reviewed_plan_sha256"]
        == "c6ca40c1c0958373b87ff2298a71f7da69022c1a10a33087cd920c972f4594cb"
    )
    assert plan["plan_version"] == "kimi-provider-evidence-v1"
    assert plan["provider"] == "moonshot-kimi"
    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 6,
        "benchmark_provider_usage_evidence": 2,
        "benchmark_provider_pricing_snapshots": 2,
        "benchmark_provider_cost_evidence": 3,
        "benchmark_usage_reconciliations": 2,
        "benchmark_usage_reconciliation_sources": 6,
        "benchmark_cost_reconciliations": 2,
        "benchmark_cost_reconciliation_sources": 6,
        "benchmark_evidence_promotion_gates": 0,
    }


def test_selected_arm_cost_semantics_are_preserved():
    plan = ingest.build_plan()

    by_arm = {row["arm_id"]: row for row in plan["cost_reconciliations"]}

    assert set(by_arm) == {
        "router-kimi-k2.6",
        "router-kimi-k3",
    }

    assert Decimal(by_arm["router-kimi-k2.6"]["selected_cost_usd"]) == Decimal(
        "6.34692415"
    )
    assert Decimal(by_arm["router-kimi-k3"]["selected_cost_usd"]) == Decimal(
        "26.570403"
    )

    for row in by_arm.values():
        assert row["provider_billed_cost_usd"] is None
        assert (
            row["selected_cost_basis"]
            == "provider_rate_reconstructed_harness_usage_validated"
        )
        assert row["selected_cost_relation"] == "estimate"
        assert row["validation_status"] == "validated_qualified"


def test_selected_usage_authority_stays_harness_validated():
    rows = ingest.build_plan()["usage_reconciliations"]

    assert len(rows) == 2

    for row in rows:
        assert row["selected_usage_authority"] == "harness_usage_validated"
        assert row["validation_status"] == "validated_qualified"
        assert row["provider_observed_model"] is None
        assert row["provider_ordinary_input_tokens"] is None
        assert row["provider_cache_read_input_tokens"] is None
        assert row["provider_output_tokens"] is None


def test_provider_usage_context_is_not_selected_run_allocated():
    rows = ingest.build_plan()["provider_usage_evidence"]

    assert len(rows) == 2

    by_model = {row["provider_model"]: row for row in rows}

    k2 = by_model["kimi-k2.6"]
    assert k2["arm_run_id"] is None
    assert k2["trial_id"] is None
    assert k2["request_started_at"] is None
    assert k2["request_finished_at"] is None
    assert k2["request_count"] == 103
    assert k2["ordinary_input_tokens"] == 1_545_150
    assert k2["cache_read_input_tokens"] == 1_063_441
    assert k2["output_tokens"] == 70_089
    assert k2["allocation_scope"] == "model_window"
    assert k2["raw_metadata"]["selected_run_allocable"] is False

    k3 = by_model["kimi-k3"]
    assert k3["arm_run_id"] is None
    assert k3["trial_id"] is None
    assert k3["request_started_at"] is None
    assert k3["request_finished_at"] is None
    assert k3["request_count"] == 1273
    assert k3["ordinary_input_tokens"] == 1_654_986
    assert k3["cache_read_input_tokens"] == 38_341_888
    assert k3["output_tokens"] == 956_453
    assert k3["raw_metadata"]["timezone_retained"] is False
    assert k3["raw_metadata"]["duplicate_archives_counted_as"] == 1


def test_provider_cost_context_is_never_selected_run_billing():
    rows = ingest.build_plan()["provider_cost_evidence"]

    assert len(rows) == 3

    amounts = {Decimal(row["amount_usd"]) for row in rows}
    assert amounts == {
        Decimal("1.91830"),
        Decimal("1.918399"),
        Decimal("30.8143194"),
    }

    for row in rows:
        assert row["arm_run_id"] is None
        assert row["trial_id"] is None
        assert row["raw_metadata"]["selected_run_allocable"] is False

    dashboard = next(
        row for row in rows if row["cost_kind"] == "provider_dashboard_total"
    )
    assert dashboard["provider_model"] is None
    assert dashboard["pricing_snapshot_key"] is None
    assert dashboard["allocation_scope"] == "provider_window"
    assert dashboard["completeness_status"] == "aggregate_only"

    k3 = next(
        row for row in rows if Decimal(row["amount_usd"]) == Decimal("30.8143194")
    )
    assert k3["raw_metadata"]["provider_billed"] is False
    assert k3["raw_metadata"]["excess_vs_selected_usd"] == "4.2439164"


def test_selected_rate_arithmetic_matches_reviewed_estimates():
    plan = ingest.build_plan()

    for selected in plan["selected_runs"]:
        spec = ingest.ARM_CONTRACT[selected["arm_id"]]
        reconstructed = ingest.reconstruct_cost(
            cache_hit_tokens=(selected["harness_cache_tokens"]),
            cache_miss_tokens=(selected["harness_cache_miss_tokens"]),
            output_tokens=(selected["harness_output_tokens"]),
            spec=spec,
        )
        assert reconstructed == Decimal(selected["selected_cost_usd"])


def test_k3_duplicate_export_is_counted_once():
    plan = ingest.build_plan()

    excluded = {row["evidence"]: row for row in plan["excluded_evidence"]}

    row = excluded["duplicate_k3_export_as_second_independent_source"]
    assert row["counted_as_independent_exports"] == 1


def test_source_link_roles_match_reviewed_plan():
    plan = ingest.build_plan()

    usage_roles = {}
    for row in plan["usage_reconciliation_source_links"]:
        usage_roles.setdefault(
            row["arm_id"],
            set(),
        ).add(row["evidence_role"])

    cost_roles = {}
    for row in plan["cost_reconciliation_source_links"]:
        cost_roles.setdefault(
            row["arm_id"],
            set(),
        ).add(row["evidence_role"])

    for arm in ingest.ARM_CONTRACT:
        assert usage_roles[arm] == {
            "aggregate_usage",
            "model_identity",
            "context",
        }
        assert cost_roles[arm] == {
            "rate_reconstruction",
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

    assert source.lower().count("insert into benchmark.") == 8
    assert source.count("connection.commit()") == 1
    assert "--rollback-only" in source
    assert "--apply" in source
    assert "second_connection_zero_persistence" in source
    assert "second_connection_verification" in source
    assert "apply_permanent(" in source


def test_no_xai_or_gemini_provider_literals_remain():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "exact_xai_state" not in source
    assert "xai_empty" not in source
    assert "google-gemini" not in source
    assert "Gemini" not in source


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


def test_provider_detail_verifier_accepts_reviewed_kimi_plan_shape():
    plan = ingest.build_plan()

    source_by_key = {row["source_key"]: row for row in plan["sources"]}
    source_sha_by_key = {
        key: row["source_sha256"] for key, row in source_by_key.items()
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
            source_sha_by_key[row["source_key"]],
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

    usage_rows = [
        (
            source_sha_by_key[row["source_key"]],
            True,
            True,
            None,
            row["provider_model"],
            None,
            None,
            row["ordinary_input_tokens"],
            row["cache_read_input_tokens"],
            row["cache_creation_input_tokens"],
            row["output_tokens"],
            row["request_count"],
            row["allocation_scope"],
            row["completeness_status"],
            row["notes"],
            row["raw_metadata"],
        )
        for row in plan["provider_usage_evidence"]
    ]

    pricing_model_by_key = {
        row["pricing_key"]: row["provider_model"] for row in plan["pricing_snapshots"]
    }

    cost_rows = [
        (
            source_sha_by_key[row["source_key"]],
            True,
            True,
            row["pricing_snapshot_key"] is None,
            (
                None
                if row["pricing_snapshot_key"] is None
                else pricing_model_by_key[row["pricing_snapshot_key"]]
            ),
            row["provider_model"],
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

    link_rows = [
        (
            "usage",
            row["arm_id"],
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan["usage_reconciliation_source_links"]
    ] + [
        (
            "cost",
            row["arm_id"],
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan["cost_reconciliation_source_links"]
    ]

    class FakeCursor:
        def __init__(self):
            self.rows = []

        def execute(
            self,
            query,
            parameters=(),
        ):
            del parameters

            sql = " ".join(str(query).lower().split())
            self.rows = []

            if (
                "from benchmark.benchmark_provider_evidence_sources" in sql
                and "select provider," in sql
            ):
                self.rows = source_rows

            elif "from benchmark.benchmark_provider_pricing_snapshots pricing" in sql:
                self.rows = pricing_rows

            elif "from benchmark.benchmark_provider_usage_evidence evidence" in sql:
                self.rows = usage_rows

            elif "from benchmark.benchmark_provider_cost_evidence evidence" in sql:
                self.rows = cost_rows

            elif (
                "from benchmark.benchmark_usage_reconciliation_sources link" in sql
                and "union all" in sql
            ):
                self.rows = link_rows

            else:
                raise AssertionError("unexpected verifier query: " + sql)

        def fetchall(self):
            return list(self.rows)

    result = ingest.verify_provider_evidence_details(
        FakeCursor(),
        plan,
        {
            "router-kimi-k2.6": "00000000-0000-0000-0000-000000000001",
            "router-kimi-k3": "00000000-0000-0000-0000-000000000002",
        },
    )

    assert result == {
        "source_rows": "pass",
        "pricing_rows": "pass",
        "usage_evidence_rows": "pass",
        "cost_evidence_rows": "pass",
        "reconciliation_source_links": "pass",
    }
