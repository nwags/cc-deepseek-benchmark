from __future__ import annotations

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/ingest_gemini_provider_evidence.py"
)

SPEC = importlib.util.spec_from_file_location(
    "ingest_gemini_provider_evidence",
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
    hashes = ingest.verify_input_hashes()

    assert hashes == (
        ingest.EXPECTED_INPUT_HASHES
    )


def test_plan_matches_reviewed_v2_authority():
    plan = ingest.build_plan()

    assert (
        plan["reviewed_plan_sha256"]
        == "10fae2e8984b8cec14a0a22d04f95e3020acc7894f43f86d530033c9649de9d5"
    )

    assert (
        plan["plan_version"]
        == "gemini-provider-evidence-v2"
    )

    assert (
        plan["provider"]
        == "google-gemini"
    )

    assert plan["write_counts"] == {
        "benchmark_provider_evidence_sources": 3,
        "benchmark_provider_usage_evidence": 0,
        "benchmark_provider_pricing_snapshots": 2,
        "benchmark_provider_cost_evidence": 1,
        "benchmark_usage_reconciliations": 2,
        "benchmark_usage_reconciliation_sources": 4,
        "benchmark_cost_reconciliations": 2,
        "benchmark_cost_reconciliation_sources": 6,
        "benchmark_evidence_promotion_gates": 0,
    }


def test_plan_uses_reviewed_three_source_scopes():
    plan = ingest.build_plan()

    observed = {
        row["source_key"]: (
            row["evidence_kind"],
            row["source_scope"],
        )
        for row in plan["sources"]
    }

    assert observed == {
        "gemini_provider_reconciliation": (
            "manual_capture",
            "account_window",
        ),
        "gemini_repository_pricing_audit": (
            "pricing_snapshot",
            "pricing_snapshot",
        ),
        "gemini_current_reconciliation": (
            "manual_capture",
            "other",
        ),
    }


def test_provider_usage_evidence_stays_empty():
    plan = ingest.build_plan()

    assert (
        plan["provider_usage_evidence"]
        == []
    )


def test_shared_provider_bill_is_normalized_once():
    plan = ingest.build_plan()

    rows = plan["provider_cost_evidence"]

    assert len(rows) == 1

    row = rows[0]

    assert row["arm_run_id"] is None
    assert row["trial_id"] is None
    assert row["provider_model"] is None
    assert row["pricing_snapshot_key"] is None

    assert (
        row["cost_kind"]
        == "account_spend"
    )

    assert (
        row["allocation_scope"]
        == "account_window"
    )

    assert (
        Decimal(row["amount_usd"])
        == Decimal("26.371228")
    )


def test_pricing_snapshots_preserve_reviewed_rates():
    plan = ingest.build_plan()

    rows = {
        row["provider_model"]: row
        for row in plan[
            "pricing_snapshots"
        ]
    }

    pro = rows[
        "gemini-3.1-pro-preview"
    ]

    assert pro["pricing_rules"] == {
        "uncached_input_usd_per_million": "2",
        "cached_input_usd_per_million": "0.20",
        "output_usd_per_million": "12",
        "reviewed_request_tier_upper_bound_tokens": 200000,
        "selected_run_request_count": 930,
        "selected_run_max_prompt_tokens": 66438,
        "selected_run_all_requests_within_reviewed_tier": True,
    }

    assert (
        pro["official_source_uri"]
        is None
    )

    flash = rows[
        "gemini-3.5-flash"
    ]

    assert flash["pricing_rules"] == {
        "uncached_input_usd_per_million": "1.50",
        "cached_input_usd_per_million": "0.15",
        "output_usd_per_million": "9",
    }

    assert (
        flash["official_source_uri"]
        is None
    )


def test_selected_usage_is_qualified_without_provider_observation():
    plan = ingest.build_plan()

    rows = {
        row["arm_id"]: row
        for row in plan[
            "usage_reconciliations"
        ]
    }

    assert set(rows) == {
        "router-gemini-3.1-pro",
        "router-gemini-flash",
    }

    for row in rows.values():
        assert (
            row["provider_observed_model"]
            is None
        )
        assert (
            row["model_identity_status"]
            == "matched"
        )
        assert (
            row["selected_usage_authority"]
            == "harness_usage_validated"
        )
        assert (
            row["validation_status"]
            == "validated_qualified"
        )
        assert (
            "selected_run_provider_observed_model_unavailable"
            in row["limitation_codes"]
        )


def test_usage_model_identity_links_use_reviewed_reconciliation():
    plan = ingest.build_plan()

    identity_links = [
        row
        for row in plan[
            "usage_reconciliation_source_links"
        ]
        if (
            row["evidence_role"]
            == "model_identity"
        )
    ]

    assert len(identity_links) == 2

    assert all(
        row["source_key"]
        == "gemini_current_reconciliation"
        for row in identity_links
    )


def test_selected_cost_semantics_are_preserved():
    plan = ingest.build_plan()

    rows = {
        row["arm_id"]: row
        for row in plan[
            "cost_reconciliations"
        ]
    }

    pro = rows[
        "router-gemini-3.1-pro"
    ]

    assert (
        Decimal(
            pro["selected_cost_usd"]
        )
        == Decimal("19.6968138")
    )

    assert (
        pro["selected_cost_basis"]
        == "provider_rate_reconstructed_harness_usage_validated"
    )

    assert (
        pro["selected_cost_relation"]
        == "estimate"
    )

    assert (
        pro["provider_billed_cost_usd"]
        is None
    )

    flash = rows[
        "router-gemini-flash"
    ]

    assert (
        Decimal(
            flash["selected_cost_usd"]
        )
        == Decimal("16.12091625")
    )

    assert (
        flash["selected_cost_basis"]
        == "lower_bound_provider_evidence"
    )

    assert (
        flash["selected_cost_relation"]
        == "lower_bound"
    )

    assert (
        flash["provider_billed_cost_usd"]
        is None
    )

    assert (
        "four_selected_trials_missing_usage_metadata"
        in flash["limitation_codes"]
    )


def test_selected_rate_arithmetic_matches_reviewed_values():
    plan = ingest.build_plan()

    selected = {
        row["arm_id"]: row
        for row in plan[
            "selected_runs"
        ]
    }

    for arm_id, row in selected.items():
        spec = ingest.ARM_CONTRACT[
            arm_id
        ]

        reconstructed = (
            ingest.reconstruct_cost(
                cache_hit_tokens=(
                    row[
                        "harness_cache_tokens"
                    ]
                ),
                cache_miss_tokens=(
                    row[
                        "harness_cache_miss_tokens"
                    ]
                ),
                output_tokens=(
                    row[
                        "harness_output_tokens"
                    ]
                ),
                spec=spec,
            )
        )

        assert (
            reconstructed
            == Decimal(
                row["selected_cost_usd"]
            )
        )


def test_script_has_only_guarded_provider_write_surface():
    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    forbidden = (
        r"\bupdate\s+benchmark\.",
        r"\bdelete\s+from\b",
        r"\btruncate\b",
        r"\bdrop\s+table\b",
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

    assert (
        source.count(
            "connection.commit()"
        )
        == 1
    )

    assert "--rollback-only" in source
    assert "--apply" in source
    assert "connection.rollback()" in source
    assert (
        "second_connection_zero_persistence"
        in source
    )
    assert (
        "second_connection_verification"
        in source
    )
    assert (
        'diagnostics.commit_state = "unknown"'
        in source
    )
    assert (
        'diagnostics.commit_state = "committed"'
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

    assert (
        ingest.parse_args(
            ["--apply"]
        ).apply
        is True
    )

    incompatible = (
        ("--plan", "--check-only"),
        ("--plan", "--rollback-only"),
        ("--plan", "--apply"),
        ("--check-only", "--rollback-only"),
        ("--check-only", "--apply"),
        ("--rollback-only", "--apply"),
    )

    for left, right in incompatible:
        with pytest.raises(SystemExit):
            ingest.parse_args(
                [left, right]
            )


def test_failure_payload_does_not_expose_exception_message():
    diagnostics = ingest.Diagnostics()
    diagnostics.enter(
        "synthetic_failure"
    )

    payload = ingest.failure_payload(
        mode="check-only",
        diagnostics=diagnostics,
        exc=RuntimeError(
            "secret-looking diagnostic detail"
        ),
    )

    rendered = json.dumps(payload)

    assert (
        "secret-looking diagnostic detail"
        not in rendered
    )

    assert (
        payload["error_type"]
        == "RuntimeError"
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
        lambda cursor, supplied_plan:
            empty,
    )

    state = ingest.inspect_target_state(
        object(),
        plan,
    )

    assert state == {
        "state": "gemini_empty",
        "counts": empty,
    }


def test_target_state_classifier_fails_closed_on_any_gemini_rows(
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
        lambda cursor, supplied_plan:
            counts,
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
    def __init__(self):
        self.queries = []

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
        self.queries.append(
            (
                str(query),
                parameters,
            )
        )


class _FakeConnection:
    def __init__(
        self,
        *,
        commit_error=None,
    ):
        self.cursor_instance = (
            _FakeCursor()
        )
        self.rollback_calls = 0
        self.commit_calls = 0
        self.close_calls = 0
        self.commit_error = (
            commit_error
        )

    def cursor(self):
        return self.cursor_instance

    def rollback(self):
        self.rollback_calls += 1

    def commit(self):
        self.commit_calls += 1

        if self.commit_error is not None:
            raise self.commit_error

    def close(self):
        self.close_calls += 1


def _arm_ids():
    return {
        "router-gemini-3.1-pro":
            "00000000-0000-0000-0000-000000000001",
        "router-gemini-flash":
            "00000000-0000-0000-0000-000000000002",
    }


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
            "state": "gemini_empty",
            "counts": empty,
        },
    )

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            _arm_ids(),
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
        == "gemini_empty"
    )

    assert (
        result["commit_state"]
        == "not_committed"
    )

    assert connection.rollback_calls == 1
    assert connection.close_calls == 1

    assert any(
        "set transaction read only"
        in query.lower()
        for query, _parameters
        in connection.cursor_instance.queries
    )


def test_target_state_classifier_reports_exact_gemini_state(
    monkeypatch,
):
    plan = ingest.build_plan()
    arm_ids = _arm_ids()

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
                dict(
                    plan["write_counts"]
                ),
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
        == "exact_gemini_state"
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
                "state":
                    "gemini_empty",
                "counts": {
                    table: 0
                    for table
                    in ingest.TARGET_TABLES
                },
            },
            {
                "state":
                    "exact_gemini_state",
                "counts":
                    dict(
                        plan[
                            "write_counts"
                        ]
                    ),
                "reconciliation_verification": {
                    "transaction_counts":
                        dict(
                            plan[
                                "write_counts"
                            ]
                        ),
                },
                "provider_verification": {
                    "source_rows":
                        "pass",
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

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            _arm_ids(),
    )

    inserted = []

    monkeypatch.setattr(
        ingest,
        "insert_plan",
        lambda cursor, supplied_plan, supplied_ids:
            inserted.append(
                supplied_ids
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
    assert (
        result["target_state"]
        == "gemini_empty"
    )

    assert (
        result["zero_persistence_counts"]
        == zero
    )

    assert inserted == [_arm_ids()]

    assert transaction.rollback_calls == 1
    assert observer.rollback_calls == 1

    assert transaction.close_calls == 1
    assert observer.close_calls == 1


def test_apply_permanent_commits_once_and_verifies_second_connection(
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
            assert autocommit is False
            return next(connections)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        _FakePsycopg,
    )

    arm_ids = _arm_ids()

    zero = {
        table: 0
        for table in ingest.TARGET_TABLES
    }

    exact = {
        "state":
            "exact_gemini_state",
        "counts":
            dict(
                plan["write_counts"]
            ),
        "resolved_arm_run_ids":
            arm_ids,
        "reconciliation_verification": {
            "transaction_counts":
                dict(
                    plan[
                        "write_counts"
                    ]
                ),
        },
        "provider_verification": {
            "source_rows": "pass",
        },
    }

    states = iter(
        (
            {
                "state":
                    "gemini_empty",
                "counts": zero,
            },
            exact,
        )
    )

    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan:
            next(states),
    )

    monkeypatch.setattr(
        ingest,
        "acquire_ingestion_lock",
        lambda cursor: None,
    )

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
                supplied_ids
            ),
    )

    reconciliation = {
        "transaction_counts":
            dict(
                plan["write_counts"]
            ),
    }

    provider = {
        "source_rows": "pass",
        "pricing_rows": "pass",
        "usage_evidence_rows":
            "pass",
        "cost_evidence_rows":
            "pass",
        "reconciliation_source_links":
            "pass",
    }

    monkeypatch.setattr(
        ingest,
        "verify_inserted_state",
        lambda cursor, supplied_plan, supplied_ids:
            reconciliation,
    )

    monkeypatch.setattr(
        ingest,
        "verify_provider_evidence_details",
        lambda cursor, supplied_plan, supplied_ids:
            provider,
    )

    diagnostics = ingest.Diagnostics()

    result = ingest.apply_permanent(
        plan,
        "synthetic-db-url",
        diagnostics,
    )

    assert result["status"] == "applied"
    assert (
        result["commit_state"]
        == "committed"
    )
    assert (
        result["target_state"]
        == "exact_gemini_state"
    )
    assert (
        result["persisted_counts"]
        == plan["write_counts"]
    )

    assert inserted == [arm_ids]

    assert transaction.commit_calls == 1
    assert transaction.rollback_calls == 0
    assert transaction.close_calls == 1

    assert observer.rollback_calls == 1
    assert observer.close_calls == 1


def test_apply_permanent_refuses_existing_exact_state(
    monkeypatch,
):
    plan = ingest.build_plan()
    transaction = _FakeConnection()

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            return transaction

    monkeypatch.setitem(
        sys.modules,
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
            "state":
                "exact_gemini_state",
            "counts":
                dict(
                    plan["write_counts"]
                ),
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        ingest.IntegrationSafetyError
    ):
        ingest.apply_permanent(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert (
        diagnostics.target_state
        == "exact_gemini_state"
    )
    assert transaction.commit_calls == 0
    assert transaction.rollback_calls == 1


def test_apply_permanent_refuses_partial_state(
    monkeypatch,
):
    plan = ingest.build_plan()
    transaction = _FakeConnection()

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            return transaction

    monkeypatch.setitem(
        sys.modules,
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
            "state":
                "partial_or_unexpected",
            "counts": {
                table: (
                    1
                    if table
                    == "benchmark_provider_evidence_sources"
                    else 0
                )
                for table
                in ingest.TARGET_TABLES
            },
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        ingest.IntegrationSafetyError
    ):
        ingest.apply_permanent(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert (
        diagnostics.target_state
        == "partial_or_unexpected"
    )
    assert transaction.commit_calls == 0
    assert transaction.rollback_calls == 1


def test_apply_permanent_preserves_ambiguous_commit_state(
    monkeypatch,
):
    plan = ingest.build_plan()

    transaction = _FakeConnection(
        commit_error=RuntimeError(
            "synthetic ambiguous commit failure"
        )
    )

    class _FakePsycopg:
        @staticmethod
        def connect(
            db_url,
            autocommit=False,
        ):
            return transaction

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
                "gemini_empty",
            "counts": {
                table: 0
                for table
                in ingest.TARGET_TABLES
            },
        },
    )

    monkeypatch.setattr(
        ingest,
        "acquire_ingestion_lock",
        lambda cursor: None,
    )

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            _arm_ids(),
    )

    monkeypatch.setattr(
        ingest,
        "insert_plan",
        lambda cursor, supplied_plan, supplied_ids:
            None,
    )

    monkeypatch.setattr(
        ingest,
        "verify_inserted_state",
        lambda cursor, supplied_plan, supplied_ids: {
            "transaction_counts":
                dict(
                    plan["write_counts"]
                ),
        },
    )

    monkeypatch.setattr(
        ingest,
        "verify_provider_evidence_details",
        lambda cursor, supplied_plan, supplied_ids: {
            "source_rows": "pass",
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        RuntimeError,
        match=(
            "synthetic ambiguous commit "
            "failure"
        ),
    ):
        ingest.apply_permanent(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert transaction.commit_calls == 1
    assert transaction.rollback_calls == 1

    assert (
        diagnostics.commit_state
        == "unknown"
    )


def test_apply_permanent_preserves_committed_state_if_postcommit_check_fails(
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
            return next(connections)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        _FakePsycopg,
    )

    states = iter(
        (
            {
                "state":
                    "gemini_empty",
                "counts": {
                    table: 0
                    for table
                    in ingest.TARGET_TABLES
                },
            },
            {
                "state":
                    "partial_or_unexpected",
                "counts": {
                    table: 0
                    for table
                    in ingest.TARGET_TABLES
                },
            },
        )
    )

    monkeypatch.setattr(
        ingest,
        "inspect_target_state",
        lambda cursor, supplied_plan:
            next(states),
    )

    monkeypatch.setattr(
        ingest,
        "acquire_ingestion_lock",
        lambda cursor: None,
    )

    monkeypatch.setattr(
        ingest,
        "resolve_arm_runs",
        lambda cursor, supplied_plan:
            _arm_ids(),
    )

    monkeypatch.setattr(
        ingest,
        "insert_plan",
        lambda cursor, supplied_plan, supplied_ids:
            None,
    )

    monkeypatch.setattr(
        ingest,
        "verify_inserted_state",
        lambda cursor, supplied_plan, supplied_ids: {
            "transaction_counts":
                dict(
                    plan["write_counts"]
                ),
        },
    )

    monkeypatch.setattr(
        ingest,
        "verify_provider_evidence_details",
        lambda cursor, supplied_plan, supplied_ids: {
            "source_rows": "pass",
        },
    )

    diagnostics = ingest.Diagnostics()

    with pytest.raises(
        ingest.IntegrationSafetyError,
        match=(
            "second-connection verification"
        ),
    ):
        ingest.apply_permanent(
            plan,
            "synthetic-db-url",
            diagnostics,
        )

    assert transaction.commit_calls == 1
    assert transaction.rollback_calls == 0

    assert observer.rollback_calls == 1

    assert (
        diagnostics.commit_state
        == "committed"
    )

    assert (
        diagnostics.target_state
        == "partial_or_unexpected"
    )
