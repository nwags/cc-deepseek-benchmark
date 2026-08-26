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


def test_script_has_single_guarded_commit_surface():
    source = SCRIPT.read_text(encoding="utf-8")

    assert source.count("connection.commit()") == 1
    assert source.count("--apply") == 1
    assert source.count("--check-only") == 1
    assert "--rollback-only" in source
    assert "--plan" in source


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


def test_cli_requires_exactly_one_explicit_mode():
    with pytest.raises(SystemExit):
        ingest.parse_args([])

    assert ingest.parse_args(["--plan"]).plan is True
    assert ingest.parse_args(["--check-only"]).check_only is True
    assert (
        ingest.parse_args(["--rollback-only"]).rollback_only
        is True
    )
    assert ingest.parse_args(["--apply"]).apply is True

    with pytest.raises(SystemExit):
        ingest.parse_args(["--check-only", "--apply"])


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



def test_target_state_classifier_reports_empty(monkeypatch):
    plan = ingest.build_plan()
    empty = {
        table: 0
        for table in ingest.TARGET_TABLES
    }

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor: empty,
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert state == {
        "state": "empty",
        "counts": empty,
    }


def test_target_state_classifier_reports_exact_state(monkeypatch):
    plan = ingest.build_plan()
    arm_ids = {
        "router-gpt-5.4": "00000000-0000-0000-0000-000000000054",
        "router-gpt-5.5": "00000000-0000-0000-0000-000000000055",
    }

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor: dict(plan["write_counts"]),
    )
    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan: arm_ids,
    )
    monkeypatch.setattr(
        ingest,
        "verify_inserted_state",
        lambda cursor, supplied_plan, supplied_ids: {
            "transaction_counts": dict(plan["write_counts"]),
            "arm_reconciliations": {},
        },
    )
    monkeypatch.setattr(
        ingest,
        "verify_provider_evidence_details",
        lambda cursor, supplied_plan, supplied_ids: {
            "source_rows": "pass",
            "usage_evidence_rows": "pass",
            "cost_evidence_rows": "pass",
            "reconciliation_source_links": "pass",
        },
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert state["state"] == "exact_openai_state"
    assert state["resolved_arm_run_ids"] == arm_ids


def test_target_state_classifier_fails_closed_on_partial_counts(
    monkeypatch,
):
    plan = ingest.build_plan()
    partial = dict(plan["write_counts"])
    partial["benchmark_provider_usage_evidence"] = 1

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor: partial,
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert state["state"] == "partial_or_unexpected"
    assert state["reason"] == "unexpected_table_counts"


def test_failure_payload_reports_commit_and_target_state():
    diagnostics = ingest.Diagnostics(
        stage="second_connection_verification",
        commit_state="committed",
        target_state="partial_or_unexpected",
    )

    payload = ingest.failure_payload(
        mode="apply",
        diagnostics=diagnostics,
        exc=RuntimeError("safe synthetic failure"),
    )

    assert payload["commit_state"] == "committed"
    assert payload["target_state"] == "partial_or_unexpected"
    assert (
        payload["failed_stage"]
        == "second_connection_verification"
    )


def test_permanent_path_reuses_reviewed_insert_function():
    source = SCRIPT.read_text(encoding="utf-8")

    assert source.count("insert_plan(") >= 3
    assert source.count("connection.commit()") == 1
    assert "second_connection_verification" in source
    assert "exact_openai_state" in source
    assert "partial_or_unexpected" in source


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _FakeConnection:
    def __init__(self):
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def cursor(self):
        return _FakeCursor()

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1


def test_check_only_reports_exact_existing_openai_state(monkeypatch):
    plan = ingest.build_plan()
    connection = _FakeConnection()

    exact_state = {
        "state": "exact_openai_state",
        "counts": dict(plan["write_counts"]),
        "resolved_arm_run_ids": {
            "router-gpt-5.4":
                "00000000-0000-0000-0000-000000000054",
            "router-gpt-5.5":
                "00000000-0000-0000-0000-000000000055",
        },
    }

    class _FakePsycopg:
        @staticmethod
        def connect(db_url, autocommit=False):
            assert db_url == "synthetic-db-url"
            assert autocommit is False
            return connection

    monkeypatch.setitem(
        __import__("sys").modules,
        "psycopg",
        _FakePsycopg,
    )
    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan: exact_state,
    )

    diagnostics = ingest.Diagnostics()

    result = ingest.check_only(
        plan,
        "synthetic-db-url",
        diagnostics,
    )

    assert result["status"] == "already_applied"
    assert result["target_state"] == "exact_openai_state"
    assert result["commit_state"] == "not_committed"
    assert connection.commit_calls == 0
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1


@pytest.mark.parametrize(
    ("state_name", "expected_fragment"),
    [
        (
            "exact_openai_state",
            "already applied",
        ),
        (
            "partial_or_unexpected",
            "partially or unexpectedly populated",
        ),
    ],
)
def test_apply_refuses_nonempty_state_before_commit(
    monkeypatch,
    state_name,
    expected_fragment,
):
    plan = ingest.build_plan()
    connection = _FakeConnection()

    class _FakePsycopg:
        @staticmethod
        def connect(db_url, autocommit=False):
            assert db_url == "synthetic-db-url"
            assert autocommit is False
            return connection

    monkeypatch.setitem(
        __import__("sys").modules,
        "psycopg",
        _FakePsycopg,
    )
    monkeypatch.setattr(
        ingest,
        "acquire_ingestion_lock",
        lambda cursor: None,
    )
    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan: {
            "state": state_name,
            "counts": dict(plan["write_counts"]),
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        ingest.IntegrationSafetyError,
        match=expected_fragment,
    ):
        ingest.apply_permanent(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert diagnostics.target_state == state_name
    assert diagnostics.commit_state == "not_committed"
    assert connection.commit_calls == 0
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1
