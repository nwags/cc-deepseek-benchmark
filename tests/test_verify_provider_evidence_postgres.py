from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_provider_evidence_postgres.py"

spec = importlib.util.spec_from_file_location(
    "verify_provider_evidence_postgres",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None

integration = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = integration
spec.loader.exec_module(integration)


def test_requires_explicit_rollback_only():
    with pytest.raises(SystemExit):
        integration.parse_args([])

    assert (
        integration.parse_args(
            ["--rollback-only"]
        ).rollback_only
        is True
    )


def test_reviewed_hashes_match_checked_in_migrations():
    hashes = integration.reviewed_hashes()

    assert hashes == {
        "010": (
            "20b87b8836fa76298d20349c69392fa03"
            "cc1df105849fea1bab9eecc6b5e9c45"
        ),
        "011": (
            "3d76c40b28e9aee8f8d99a1e73ac3d6"
            "411cf4cf1590b1fb750950321f613630b"
        ),
    }


def test_verifier_has_no_commit_surface():
    source = SCRIPT.read_text(encoding="utf-8")

    assert ".commit(" not in source
    assert "--apply" not in source


def test_failure_result_never_includes_exception_message():
    secret = (
        "postgresql://user:password@example.invalid/database"
    )

    class SyntheticError(RuntimeError):
        sqlstate = "23514"

    diagnostics = integration.IntegrationDiagnostics()
    result = integration.failure_result(
        hashes={
            "010": "a" * 64,
            "011": "b" * 64,
        },
        failed_stage="constraint_contract",
        exc=SyntheticError(secret),
        diagnostics=diagnostics,
    )

    text = json.dumps(result)

    assert result["sqlstate"] == "23514"
    assert secret not in text
    assert "password" not in text


def test_pre_and_post_010_contracts_are_distinct():
    pre = {
        "unresolved_trial_gap": integration.Decimal("-10"),
        "known_trial_gap": integration.Decimal("2"),
        "arm_recorded_cost": integration.Decimal("14"),
        "arm_adjusted_cost": integration.Decimal("6"),
        "arm_gap": integration.Decimal("-8"),
        "unresolved_count": 1,
        "frontier_gap": integration.Decimal("-8"),
    }

    integration.assert_pre_010_semantics(pre)

    with pytest.raises(integration.IntegrationSafetyError):
        integration.assert_post_010_semantics(pre)


def test_gate_state_requires_expected_blockers():
    integration.assert_gate_state(
        label="blocked",
        blockers=(
            "usage_reconciliation_not_current",
            "cost_reconciliation_not_current",
        ),
        effective=False,
        expected_effective=False,
        required_blockers=(
            "usage_reconciliation_not_current",
        ),
    )

    with pytest.raises(integration.IntegrationSafetyError):
        integration.assert_gate_state(
            label="bad-pass",
            blockers=("unexpected",),
            effective=True,
            expected_effective=True,
        )


def test_synthetic_manifest_preserves_requested_mode():
    manifest = integration.synthetic_manifest(
        "abc",
        label="smoke",
        logical_mode="smoke",
        trial_count=2,
    )

    assert manifest["run"]["logical_mode"] == "smoke"
    assert manifest["run"]["storage_mode"] == "rollback-only"
    assert manifest["run"]["n_total_trials"] == 2
    assert len(manifest["trials"]) == 2


def test_execute_sql_file_uses_exact_file_contents(
    tmp_path: Path,
):
    path = tmp_path / "migration.sql"
    path.write_text("select 1;\n", encoding="utf-8")

    executed = []

    class Cursor:
        def execute(self, sql):
            executed.append(sql)

    integration.execute_sql_file(Cursor(), path)

    assert executed == ["select 1;\n"]


def test_permanent_provider_schema_preflight_refuses_relation(
    monkeypatch: pytest.MonkeyPatch,
):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

    calls = 0

    def presence(_cursor, relations):
        nonlocal calls
        calls += 1
        if relations == integration.PROVIDER_EVIDENCE_RELATIONS:
            return (
                "benchmark.benchmark_provider_evidence_sources",
            )
        return ()

    monkeypatch.setattr(
        integration,
        "relation_presence",
        presence,
    )

    with pytest.raises(integration.IntegrationSafetyError):
        integration.assert_provider_schema_absent(
            Connection()
        )

    assert calls == 2


def test_permanent_provider_schema_preflight_refuses_index_collision(
    monkeypatch: pytest.MonkeyPatch,
):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

    def presence(_cursor, relations):
        if relations == integration.PROVIDER_EVIDENCE_RELATIONS:
            return ()
        if relations == integration.PROVIDER_EVIDENCE_INDEXES:
            return (
                "benchmark.idx_provider_usage_arm_run",
            )
        return ()

    monkeypatch.setattr(
        integration,
        "relation_presence",
        presence,
    )

    with pytest.raises(integration.IntegrationSafetyError):
        integration.assert_provider_schema_absent(
            Connection()
        )


def test_failure_result_exposes_safe_check_names_only():
    diagnostics = integration.IntegrationDiagnostics(
        current_stage="schema_verification",
        failed_checks=(
            "essential_columns_v_evidence_promotion_gate",
        ),
    )

    result = integration.failure_result(
        hashes={
            "010": "a" * 64,
            "011": "b" * 64,
        },
        failed_stage="schema_verification",
        exc=integration.IntegrationSafetyError(
            "do not expose this diagnostic message"
        ),
        diagnostics=diagnostics,
    )

    assert result["failed_checks"] == [
        "essential_columns_v_evidence_promotion_gate"
    ]

    serialized = json.dumps(result)
    assert "do not expose this diagnostic message" not in serialized
