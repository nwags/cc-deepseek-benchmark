from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "scripts/"
      "ingest_deepseek_provider_evidence.py"
)

SPEC = importlib.util.spec_from_file_location(
    "ingest_deepseek_provider_evidence",
    SCRIPT,
)

assert SPEC is not None
assert SPEC.loader is not None

ingest = importlib.util.module_from_spec(
    SPEC
)
sys.modules[SPEC.name] = ingest
SPEC.loader.exec_module(ingest)


def test_reviewed_input_hashes_match():
    assert (
        ingest.verify_input_hashes()
        == ingest.EXPECTED_INPUT_HASHES
    )


def test_plan_matches_reviewed_v3_authority():
    plan = ingest.build_plan()

    assert (
        plan["plan_version"]
        == "deepseek-provider-evidence-v3"
    )
    assert (
        plan["reviewed_plan_sha256"]
        == "b5f105095c2b2243b0c3b2cea9a29a0a7564a37a9de812bfd5fd9ea918ff2a21"
    )
    assert (
        plan["database_writes_performed"]
        is False
    )

    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 3,
        "benchmark_provider_usage_evidence": 2,
        "benchmark_provider_pricing_snapshots": 2,
        "benchmark_provider_cost_evidence": 2,
        "benchmark_usage_reconciliations": 2,
        "benchmark_usage_reconciliation_sources": 4,
        "benchmark_cost_reconciliations": 2,
        "benchmark_cost_reconciliation_sources": 6,
        "benchmark_evidence_promotion_gates": 0,
    }


def test_plan_uses_exact_three_source_scopes():
    plan = ingest.build_plan()

    observed = {
        row["source_key"]: (
            row["evidence_kind"],
            row["source_scope"],
        )
        for row in plan["sources"]
    }

    assert observed == {
        "deepseek_provider_reconciliation": (
            "manual_capture",
            "provider_window",
        ),
        "deepseek_repository_pricing": (
            "pricing_snapshot",
            "pricing_snapshot",
        ),
        "deepseek_selected_run_reconstruction": (
            "manual_capture",
            "other",
        ),
    }


def test_provider_smoke_usage_preserves_partial_dimensions():
    plan = ingest.build_plan()

    rows = {
        row["provider_model"]: row
        for row in plan[
            "provider_usage_evidence"
        ]
    }

    assert set(rows) == {
        "deepseek-v4-flash",
        "deepseek-v4-pro",
    }

    flash = rows["deepseek-v4-flash"]
    assert (
        flash["ordinary_input_tokens"]
        is None
    )
    assert (
        flash["cache_read_input_tokens"]
        == 17_726_720
    )
    assert (
        flash["cache_creation_input_tokens"]
        is None
    )
    assert flash["output_tokens"] == 175_514
    assert flash["request_count"] == 191
    assert (
        flash["raw_metadata"][
            "provider_cache_miss_input_tokens"
        ]
        == 200_187
    )
    assert (
        flash["completeness_status"]
        == "partial"
    )

    pro = rows["deepseek-v4-pro"]
    assert (
        pro["ordinary_input_tokens"]
        is None
    )
    assert (
        pro["cache_read_input_tokens"]
        == 4_906_624
    )
    assert (
        pro["cache_creation_input_tokens"]
        is None
    )
    assert pro["output_tokens"] == 71_255
    assert pro["request_count"] == 116
    assert (
        pro["raw_metadata"][
            "provider_cache_miss_input_tokens"
        ]
        == 164_407
    )


def test_selected_usage_remains_harness_validated():
    plan = ingest.build_plan()

    assert len(
        plan["usage_reconciliations"]
    ) == 2

    for row in plan[
        "usage_reconciliations"
    ]:
        assert (
            row["selected_usage_authority"]
            == "harness_usage_validated"
        )
        assert (
            row["validation_status"]
            == "validated_qualified"
        )
        assert (
            row[
                "provider_ordinary_input_tokens"
            ]
            is None
        )
        assert (
            row[
                "provider_cache_read_input_tokens"
            ]
            is None
        )
        assert (
            row[
                "provider_cache_creation_input_tokens"
            ]
            is None
        )
        assert (
            row["provider_output_tokens"]
            is None
        )
        assert (
            row["provider_request_count"]
            is None
        )


def test_selected_cost_remains_qualified_estimate():
    plan = ingest.build_plan()

    rows = {
        row["arm_id"]: row
        for row in plan[
            "cost_reconciliations"
        ]
    }

    assert (
        rows["router-deepseek-flash"][
            "selected_cost_usd"
        ]
        == "1.0798358032"
    )
    assert (
        rows["router-deepseek-pro"][
            "selected_cost_usd"
        ]
        == "1.899724634"
    )

    for row in rows.values():
        assert (
            row["provider_billed_cost_usd"]
            is None
        )
        assert (
            row["selected_cost_basis"]
            == "provider_rate_reconstructed_harness_usage_validated"
        )
        assert (
            row["selected_cost_relation"]
            == "estimate"
        )
        assert (
            row["validation_status"]
            == "validated_qualified"
        )


def test_smoke_provider_cost_is_not_selected_run_bill():
    plan = ingest.build_plan()

    amounts = {
        row["provider_model"]:
            row["amount_usd"]
        for row in plan[
            "provider_cost_evidence"
        ]
    }

    assert amounts == {
        "deepseek-v4-flash":
            "0.126804916",
        "deepseek-v4-pro":
            "0.151295407",
    }

    for row in plan[
        "provider_cost_evidence"
    ]:
        assert (
            row["allocation_scope"]
            == "model_window"
        )
        assert (
            row["arm_run_id"]
            is None
        )


def test_unsupported_same_day_totals_stay_excluded():
    plan = ingest.build_plan()

    observed = {
        row["arm_id"]: row["value_usd"]
        for row in plan[
            "excluded_evidence"
        ]
    }

    assert observed == {
        "router-deepseek-flash":
            "1.1502775424",
        "router-deepseek-pro":
            "1.963511004",
    }


def test_script_has_only_guarded_rollback_write_surface():
    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    forbidden = (
        r"\bupdate\s+benchmark\.",
        r"\bdelete\s+from\b",
        r"\btruncate\b",
        r"\bdrop\s+table\b",
        r"\balter\s+table\b",
        r"\.commit\s*\(",
    )

    for pattern in forbidden:
        assert not re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        )

    assert (
        source.lower().count(
            "insert into benchmark."
        )
        == 8
    )

    assert "--rollback-only" in source
    assert "--apply" not in source
    assert "connection.rollback()" in source
    assert (
        "second_connection_zero_persistence"
        in source
    )


def test_cli_requires_exactly_one_explicit_mode():
    with pytest.raises(SystemExit):
        ingest.parse_args([])

    assert (
        ingest.parse_args(
            ["--plan"]
        ).plan
        is True
    )

    assert (
        ingest.parse_args(
            ["--check-only"]
        ).check_only
        is True
    )

    assert (
        ingest.parse_args(
            ["--rollback-only"]
        ).rollback_only
        is True
    )

    with pytest.raises(SystemExit):
        ingest.parse_args(
            [
                "--plan",
                "--check-only",
            ]
        )

    with pytest.raises(SystemExit):
        ingest.parse_args(
            [
                "--check-only",
                "--rollback-only",
            ]
        )



def test_failure_payload_does_not_expose_exception_message():
    secret = (
        "synthetic-sensitive-marker-"
        "do-not-expose"
    )

    diagnostics = ingest.Diagnostics(
        stage="synthetic"
    )

    payload = ingest.failure_payload(
        mode="check-only",
        diagnostics=diagnostics,
        exc=RuntimeError(secret),
    )

    serialized = json.dumps(payload)

    assert secret not in serialized
    assert "secret-password" not in serialized
    assert (
        payload["failed_stage"]
        == "synthetic"
    )


def test_target_state_classifier_reports_empty(
    monkeypatch,
):
    plan = ingest.build_plan()

    empty = {
        table: 0
        for table in ingest.TARGET_TABLES
    }

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor, supplied_plan: empty,
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert state == {
        "state": "deepseek_empty",
        "counts": empty,
    }


def test_target_state_classifier_fails_closed_on_any_deepseek_rows(
    monkeypatch,
):
    plan = ingest.build_plan()

    counts = {
        table: 0
        for table in ingest.TARGET_TABLES
    }
    counts[
        "benchmark_provider_evidence_sources"
    ] = 1

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor, supplied_plan: counts,
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert (
        state["state"]
        == "partial_or_unexpected"
    )


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False

    def execute(
        self,
        query,
        parameters=(),
    ):
        return None


class _FakeConnection:
    def __init__(self):
        self.cursor_instance = _FakeCursor()
        self.rollback_calls = 0
        self.close_calls = 0

    def cursor(self):
        return self.cursor_instance

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1


def test_check_only_ready_is_read_only(
    monkeypatch,
):
    plan = ingest.build_plan()
    connection = _FakeConnection()

    empty = {
        table: 0
        for table in ingest.TARGET_TABLES
    }

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            assert (
                db_url
                == "synthetic-db-url"
            )
            assert autocommit is False
            return connection

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        _FakePsycopg,
    )

    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan: {
            "state": "deepseek_empty",
            "counts": empty,
        },
    )

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan: {
            "router-deepseek-flash":
                "00000000-0000-0000-0000-000000000001",
            "router-deepseek-pro":
                "00000000-0000-0000-0000-000000000002",
        },
    )

    diagnostics = ingest.Diagnostics()

    result = ingest.check_only(
        plan,
        "synthetic-db-url",
        diagnostics,
    )

    assert result["status"] == "ready"
    assert (
        result["target_state"]
        == "deepseek_empty"
    )
    assert (
        result["commit_state"]
        == "not_committed"
    )
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1


def test_check_only_refuses_nonempty_target(
    monkeypatch,
):
    plan = ingest.build_plan()
    connection = _FakeConnection()

    counts = {
        table: 0
        for table in ingest.TARGET_TABLES
    }
    counts[
        "benchmark_provider_evidence_sources"
    ] = 1

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            return connection

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        _FakePsycopg,
    )

    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan: {
            "state":
                "partial_or_unexpected",
            "counts": counts,
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        ingest.IntegrationSafetyError
    ):
        ingest.check_only(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert (
        diagnostics.target_state
        == "partial_or_unexpected"
    )
    assert (
        diagnostics.commit_state
        == "not_committed"
    )
    assert connection.rollback_calls == 1
    assert connection.close_calls == 1


def test_target_state_classifier_reports_exact_deepseek_state(
    monkeypatch,
):
    plan = ingest.build_plan()

    arm_ids = {
        "router-deepseek-flash":
            "00000000-0000-0000-0000-000000000001",
        "router-deepseek-pro":
            "00000000-0000-0000-0000-000000000002",
    }

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor, supplied_plan:
            dict(plan["write_counts"]),
    )
    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            arm_ids,
    )
    monkeypatch.setattr(
        ingest,
        "verify_inserted_state",
        lambda cursor, supplied_plan, supplied_ids: {
            "transaction_counts":
                dict(plan["write_counts"]),
        },
    )
    monkeypatch.setattr(
        ingest,
        "verify_provider_evidence_details",
        lambda cursor, supplied_plan, supplied_ids: {
            "source_rows": "pass",
        },
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert (
        state["state"]
        == "exact_deepseek_state"
    )
    assert (
        state["resolved_arm_run_ids"]
        == arm_ids
    )


def test_rollback_only_rolls_back_and_proves_zero_persistence(
    monkeypatch,
):
    plan = ingest.build_plan()

    transaction = _FakeConnection()
    observer = _FakeConnection()

    connections = iter(
        (
            transaction,
            observer,
        )
    )

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            assert (
                db_url
                == "synthetic-db-url"
            )
            assert autocommit is False
            return next(connections)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        _FakePsycopg,
    )

    states = iter(
        (
            {
                "state": "deepseek_empty",
                "counts": {
                    table: 0
                    for table in ingest.TARGET_TABLES
                },
            },
            {
                "state": "exact_deepseek_state",
                "counts":
                    dict(plan["write_counts"]),
                "reconciliation_verification": {
                    "transaction_counts":
                        dict(plan["write_counts"]),
                },
                "provider_verification": {
                    "source_rows": "pass",
                },
            },
        )
    )

    monkeypatch.setattr(
        ingest,
        "acquire_ingestion_lock",
        lambda cursor: None,
    )

    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan:
            next(states),
    )

    arm_ids = {
        "router-deepseek-flash":
            "00000000-0000-0000-0000-000000000001",
        "router-deepseek-pro":
            "00000000-0000-0000-0000-000000000002",
    }

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            arm_ids,
    )

    inserted = []

    monkeypatch.setattr(
        ingest,
        "insert_plan",
        lambda cursor, supplied_plan, supplied_ids:
            inserted.append(
                (
                    supplied_plan,
                    supplied_ids,
                )
            ),
    )

    zero = {
        table: 0
        for table in ingest.TARGET_TABLES
    }

    monkeypatch.setattr(
        ingest,
        "target_table_counts",
        lambda cursor, supplied_plan:
            dict(zero),
    )

    diagnostics = ingest.Diagnostics()

    result = ingest.rollback_only(
        plan,
        "synthetic-db-url",
        diagnostics,
    )

    assert result["status"] == "passed"
    assert result["mode"] == "rollback-only"
    assert (
        result["target_state"]
        == "deepseek_empty"
    )
    assert (
        result["commit_state"]
        == "not_committed"
    )
    assert result[
        "zero_persistence_counts"
    ] == zero

    assert len(inserted) == 1
    assert inserted[0][1] == arm_ids

    assert transaction.rollback_calls == 1
    assert transaction.close_calls == 1

    assert observer.rollback_calls == 1
    assert observer.close_calls == 1
