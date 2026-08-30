from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/apply_provider_evidence_migrations.py"

spec = importlib.util.spec_from_file_location(
    "apply_provider_evidence_migrations",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None
migration = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = migration
spec.loader.exec_module(migration)


def ready_preflight():
    return migration.PreflightResult(
        provider_schema_state="absent",
        present_provider_relations=(),
        absent_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS
        ),
        missing_baseline_relations=(),
    )


def complete_snapshot():
    columns: set[tuple[str, str]] = set()
    for table_name, required in migration.ESSENTIAL_COLUMNS.items():
        for column_name in required:
            columns.add((table_name, column_name))

    return migration.SchemaSnapshot(
        baseline_relations=frozenset(
            migration.BASELINE_RELATIONS
        ),
        provider_relations=frozenset(
            migration.PROVIDER_EVIDENCE_RELATIONS
        ),
        provider_indexes=frozenset(
            migration.PROVIDER_EVIDENCE_INDEXES
        ),
        columns=frozenset(columns),
        provider_index_bindings=frozenset(
            migration.PROVIDER_EVIDENCE_INDEX_TABLES.items()
        ),
    )


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(
        self,
        sql: str,
        params: Any = None,
    ) -> None:
        self.executed.append((sql, params))


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_value = FakeCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_value

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_utility_is_fixed_to_exact_reviewed_migrations():
    assert migration.MIGRATION_010_DISPLAY_PATH == (
        "db/migrations/phase3/"
        "010_cost_authority_semantics.sql"
    )
    assert migration.MIGRATION_011_DISPLAY_PATH == (
        "db/migrations/phase3/"
        "011_provider_evidence_contract.sql"
    )

    assert migration.REVIEWED_MIGRATION_010_SHA256 == (
        "20b87b8836fa76298d20349c69392fa03cc1df105849fea"
        "1bab9eecc6b5e9c45"
    )
    assert migration.REVIEWED_MIGRATION_011_SHA256 == (
        "3d76c40b28e9aee8f8d99a1e73ac3d6411cf4cf1590b1"
        "fb750950321f613630b"
    )


def test_cli_has_no_arbitrary_migration_path():
    args = migration.parse_args(
        [
            "--check-only",
            "--expected-010-sha256",
            migration.REVIEWED_MIGRATION_010_SHA256,
            "--expected-011-sha256",
            migration.REVIEWED_MIGRATION_011_SHA256,
        ]
    )
    assert args.check_only is True

    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            [
                "--check-only",
                "--expected-010-sha256",
                migration.REVIEWED_MIGRATION_010_SHA256,
                "--expected-011-sha256",
                migration.REVIEWED_MIGRATION_011_SHA256,
                "--migration",
                "arbitrary.sql",
            ]
        )


def test_apply_and_check_only_are_mutually_exclusive():
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            [
                "--check-only",
                "--apply",
                "--expected-010-sha256",
                migration.REVIEWED_MIGRATION_010_SHA256,
                "--expected-011-sha256",
                migration.REVIEWED_MIGRATION_011_SHA256,
            ]
        )


def test_both_operator_hashes_are_required():
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            [
                "--check-only",
                "--expected-010-sha256",
                migration.REVIEWED_MIGRATION_010_SHA256,
            ]
        )


def test_checked_in_migrations_match_reviewed_hashes():
    raw_010 = migration.migration_bytes(
        migration.MIGRATION_010_PATH
    )
    raw_011 = migration.migration_bytes(
        migration.MIGRATION_011_PATH
    )

    assert migration.require_reviewed_hashes(
        raw_010,
        raw_011,
        expected_010=migration.REVIEWED_MIGRATION_010_SHA256,
        expected_011=migration.REVIEWED_MIGRATION_011_SHA256,
    ) == (
        migration.REVIEWED_MIGRATION_010_SHA256,
        migration.REVIEWED_MIGRATION_011_SHA256,
    )


def test_altered_migration_cannot_self_authorize():
    raw_010 = migration.migration_bytes(
        migration.MIGRATION_010_PATH
    )
    altered_011 = b"select 'altered';\n"
    altered_digest = migration.migration_sha256(
        altered_011
    )

    with pytest.raises(migration.MigrationHashMismatch):
        migration.require_reviewed_hashes(
            raw_010,
            altered_011,
            expected_010=(
                migration.REVIEWED_MIGRATION_010_SHA256
            ),
            expected_011=altered_digest,
        )


def test_provider_relation_state_classification():
    state, present, absent = (
        migration.classify_provider_relations(())
    )
    assert state == "absent"
    assert present == ()
    assert absent == migration.PROVIDER_EVIDENCE_RELATIONS

    state, present, absent = (
        migration.classify_provider_relations(
            migration.PROVIDER_EVIDENCE_RELATIONS[:1]
        )
    )
    assert state == "partial"
    assert len(present) == 1
    assert len(absent) == 9

    state, present, absent = (
        migration.classify_provider_relations(
            migration.PROVIDER_EVIDENCE_RELATIONS
        )
    )
    assert state == "present"
    assert present == migration.PROVIDER_EVIDENCE_RELATIONS
    assert absent == ()


def test_partial_provider_schema_refuses():
    result = migration.PreflightResult(
        provider_schema_state="partial",
        present_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS[0],
        ),
        absent_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS[1:]
        ),
        missing_baseline_relations=(),
    )

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration.require_ready_preflight(
            result,
            stage="preflight",
        )

    assert caught.value.status == "partial_schema"
    assert caught.value.stage == "preflight"


def test_complete_provider_schema_refuses_reapplication():
    result = migration.PreflightResult(
        provider_schema_state="present",
        present_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS
        ),
        absent_provider_relations=(),
        missing_baseline_relations=(),
    )

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration.require_ready_preflight(
            result,
            stage="preflight",
        )

    assert caught.value.status == "already_present"


def test_missing_any_migration_008_baseline_refuses():
    result = migration.PreflightResult(
        provider_schema_state="absent",
        present_provider_relations=(),
        absent_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS
        ),
        missing_baseline_relations=(
            "benchmark.v_suite_adjusted_cost_frontier",
        ),
    )

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration.require_ready_preflight(
            result,
            stage="preflight",
        )

    assert caught.value.status == "missing_dependencies"
    assert (
        "benchmark.v_suite_adjusted_cost_frontier"
        in caught.value.missing_dependencies
    )


def test_complete_schema_snapshot_passes():
    assert (
        migration.verify_schema_snapshot(
            complete_snapshot()
        )
        == []
    )


def test_schema_snapshot_detects_missing_index():
    snapshot = complete_snapshot()
    missing = next(
        iter(migration.PROVIDER_EVIDENCE_INDEXES)
    )

    defective = migration.SchemaSnapshot(
        baseline_relations=snapshot.baseline_relations,
        provider_relations=snapshot.provider_relations,
        provider_indexes=frozenset(
            index
            for index in snapshot.provider_indexes
            if index != missing
        ),
        columns=snapshot.columns,
    )

    assert "provider_evidence_indexes" in (
        migration.verify_schema_snapshot(defective)
    )


def test_schema_snapshot_detects_missing_essential_column():
    snapshot = complete_snapshot()

    defective = migration.SchemaSnapshot(
        baseline_relations=snapshot.baseline_relations,
        provider_relations=snapshot.provider_relations,
        provider_indexes=snapshot.provider_indexes,
        columns=frozenset(
            pair
            for pair in snapshot.columns
            if pair
            != (
                "v_evidence_promotion_gate",
                "effective_can_advance",
            )
        ),
    )

    assert (
        "essential_columns_v_evidence_promotion_gate"
        in migration.verify_schema_snapshot(defective)
    )


def test_advisory_lock_is_explicitly_typed():
    cursor = FakeCursor()

    migration.acquire_migration_lock(cursor)

    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "pg_advisory_xact_lock" in sql
    assert "hashtextextended(%s::text, 0::bigint)" in sql
    assert params == (migration.ADVISORY_LOCK_IDENTITY,)


def test_check_only_never_executes_migrations_or_lock(
    monkeypatch: pytest.MonkeyPatch,
):
    connection = FakeConnection()

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {
            "database_name": "test",
            "database_user": "test",
            "server_version": "test",
        },
    )
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )

    state = migration.OperationState(stage="test")

    result, _identity = migration._connect_and_run(
        mode="check-only",
        migration_010_sql="MIGRATION 010",
        migration_011_sql="MIGRATION 011",
        connect=lambda: connection,
        state=state,
    )

    assert result["status"] == "ready"
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.cursor_value.executed == []


def test_apply_executes_010_then_011_and_verifies_before_commit(
    monkeypatch: pytest.MonkeyPatch,
):
    first = FakeConnection()
    second = FakeConnection()
    connections = iter((first, second))

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {
            "database_name": "test",
            "database_user": "test",
            "server_version": "test",
        },
    )
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )

    verification_calls: list[FakeCursor] = []

    def verify(cursor):
        verification_calls.append(cursor)
        return []

    monkeypatch.setattr(
        migration,
        "verify_provider_evidence_schema",
        verify,
    )

    state = migration.OperationState(stage="test")

    result, _identity = migration._connect_and_run(
        mode="apply",
        migration_010_sql="MIGRATION 010",
        migration_011_sql="MIGRATION 011",
        connect=lambda: next(connections),
        state=state,
    )

    executed = [
        sql.strip()
        for sql, _params in first.cursor_value.executed
    ]

    assert any(
        "pg_advisory_xact_lock" in sql
        for sql in executed
    )
    assert executed[-2:] == [
        "MIGRATION 010",
        "MIGRATION 011",
    ]
    assert len(verification_calls) == 2
    assert verification_calls[0] is first.cursor_value
    assert verification_calls[1] is second.cursor_value
    assert first.commits == 1
    assert first.rollbacks == 0
    assert second.rollbacks == 1
    assert state.committed is True
    assert result["status"] == "applied"


def test_same_transaction_verification_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
):
    connection = FakeConnection()

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {},
    )
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )
    monkeypatch.setattr(
        migration,
        "verify_provider_evidence_schema",
        lambda _cursor: ["provider_evidence_indexes"],
    )

    state = migration.OperationState(stage="test")

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration._connect_and_run(
            mode="apply",
            migration_010_sql="MIGRATION 010",
            migration_011_sql="MIGRATION 011",
            connect=lambda: connection,
            state=state,
        )

    assert caught.value.status == "verification_failed"
    assert caught.value.stage == (
        "same_transaction_verification"
    )
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert state.committed is False


def test_second_connection_failure_preserves_committed_state(
    monkeypatch: pytest.MonkeyPatch,
):
    first = FakeConnection()
    second = FakeConnection()
    connections = iter((first, second))

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {},
    )
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )

    calls = 0

    def verify(_cursor):
        nonlocal calls
        calls += 1
        if calls == 1:
            return []
        return ["provider_evidence_relations"]

    monkeypatch.setattr(
        migration,
        "verify_provider_evidence_schema",
        verify,
    )

    state = migration.OperationState(stage="test")

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration._connect_and_run(
            mode="apply",
            migration_010_sql="MIGRATION 010",
            migration_011_sql="MIGRATION 011",
            connect=lambda: next(connections),
            state=state,
        )

    assert caught.value.stage == (
        "second_connection_verification"
    )
    assert state.committed is True
    assert first.commits == 1


def test_existing_evidence_destination_is_rejected(
    tmp_path: Path,
):
    destination = tmp_path / "evidence.json"
    destination.write_text("existing\n", encoding="utf-8")

    with pytest.raises(migration.EvidenceAlreadyExists):
        migration.ensure_safe_evidence_path(destination)


def test_missing_database_url_reports_names_not_secret_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    result = migration.main(
        [
            "--check-only",
            "--expected-010-sha256",
            migration.REVIEWED_MIGRATION_010_SHA256,
            "--expected-011-sha256",
            migration.REVIEWED_MIGRATION_011_SHA256,
        ]
    )

    assert result == 2
    payload_text = capsys.readouterr().out
    payload = json.loads(payload_text)

    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "connection"
    assert payload["error_type"] == "MissingEnvironmentError"
    assert "SUPABASE_DB_URL" not in payload_text


def test_apply_repeats_preflight_after_lock(
    monkeypatch: pytest.MonkeyPatch,
):
    first = FakeConnection()
    second = FakeConnection()
    connections = iter((first, second))
    preflight_calls = 0

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {},
    )

    def preflight(_cursor):
        nonlocal preflight_calls
        preflight_calls += 1
        return ready_preflight()

    monkeypatch.setattr(
        migration,
        "database_preflight",
        preflight,
    )
    monkeypatch.setattr(
        migration,
        "verify_provider_evidence_schema",
        lambda _cursor: [],
    )

    state = migration.OperationState(stage="test")

    migration._connect_and_run(
        mode="apply",
        migration_010_sql="MIGRATION 010",
        migration_011_sql="MIGRATION 011",
        connect=lambda: next(connections),
        state=state,
    )

    assert preflight_calls == 2


def test_hash_mismatch_refuses_before_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(
        migration,
        "migration_bytes",
        lambda path: (
            b"altered\n"
            if path == migration.MIGRATION_011_PATH
            else migration.MIGRATION_010_PATH.read_bytes()
        ),
    )
    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgresql://secret.invalid/database",
    )

    class ForbiddenPsycopg:
        @staticmethod
        def connect(*_args, **_kwargs):
            raise AssertionError(
                "database connection must not be attempted"
            )

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        ForbiddenPsycopg,
    )

    result = migration.main(
        [
            "--check-only",
            "--expected-010-sha256",
            migration.REVIEWED_MIGRATION_010_SHA256,
            "--expected-011-sha256",
            migration.REVIEWED_MIGRATION_011_SHA256,
        ]
    )

    assert result == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["failed_stage"] == "hash"
    assert payload["error_type"] == "MigrationHashMismatch"


def test_main_connects_with_autocommit_disabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    calls: list[tuple[str, dict[str, Any]]] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params

        def fetchone(self):
            return ("testdb", "testuser", "PostgreSQL test")

    class Connection:
        def cursor(self):
            return Cursor()

        def rollback(self):
            pass

        def close(self):
            pass

    class FakePsycopg:
        @staticmethod
        def connect(url, **kwargs):
            calls.append((url, kwargs))
            return Connection()

    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgresql://secret.invalid/database",
    )
    monkeypatch.setitem(sys.modules, "psycopg", FakePsycopg)
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )

    result = migration.main(
        [
            "--check-only",
            "--expected-010-sha256",
            migration.REVIEWED_MIGRATION_010_SHA256,
            "--expected-011-sha256",
            migration.REVIEWED_MIGRATION_011_SHA256,
        ]
    )

    assert result == 0
    assert len(calls) == 1
    assert calls[0][1] == {"autocommit": False}

    output = capsys.readouterr().out
    assert "secret.invalid" not in output


def test_connection_failure_does_not_emit_exception_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    secret = "postgresql://user:password@example.invalid/database"

    class SyntheticError(RuntimeError):
        pass

    class FakePsycopg:
        @staticmethod
        def connect(*_args, **_kwargs):
            raise SyntheticError(secret)

    monkeypatch.setenv("SUPABASE_DB_URL", secret)
    monkeypatch.setitem(sys.modules, "psycopg", FakePsycopg)

    result = migration.main(
        [
            "--check-only",
            "--expected-010-sha256",
            migration.REVIEWED_MIGRATION_010_SHA256,
            "--expected-011-sha256",
            migration.REVIEWED_MIGRATION_011_SHA256,
        ]
    )

    assert result == 1

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["failed_stage"] == "connection"
    assert payload["error_type"] == "SyntheticError"
    assert secret not in output
    assert "password" not in output


def test_evidence_output_matches_stdout_and_does_not_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    path = tmp_path / "evidence.json"
    payload = {
        "status": "ready",
        "commit_state": "not_committed",
    }

    migration._emit(
        payload,
        evidence_path=path,
    )

    stdout = capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == stdout
    assert json.loads(stdout) == payload

    with pytest.raises(migration.EvidenceAlreadyExists):
        migration._emit(
            payload,
            evidence_path=path,
        )


def test_symlinked_evidence_destination_is_rejected(
    tmp_path: Path,
):
    target = tmp_path / "target.json"
    target.write_text("protected\n", encoding="utf-8")

    destination = tmp_path / "evidence.json"
    destination.symlink_to(target)

    with pytest.raises(migration.EvidenceAlreadyExists):
        migration.ensure_safe_evidence_path(destination)

    assert target.read_text(encoding="utf-8") == "protected\n"


def test_failure_payload_reports_sqlstate_not_exception_text():
    secret = "postgresql://user:password@example.invalid/database"

    class SyntheticError(RuntimeError):
        sqlstate = "23505"

    state = migration.OperationState(stage="migration_011")

    payload = migration.failure_payload(
        mode="apply",
        digest_010=migration.REVIEWED_MIGRATION_010_SHA256,
        digest_011=migration.REVIEWED_MIGRATION_011_SHA256,
        stage="migration_011",
        status="failed",
        error_type="SyntheticError",
        state=state,
        cause=SyntheticError(secret),
    )

    serialized = json.dumps(payload)

    assert payload["sqlstate"] == "23505"
    assert secret not in serialized
    assert "password" not in serialized


def test_success_result_records_committed_state(
    monkeypatch: pytest.MonkeyPatch,
):
    first = FakeConnection()
    second = FakeConnection()
    connections = iter((first, second))

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {},
    )
    monkeypatch.setattr(
        migration,
        "database_preflight",
        lambda _cursor: ready_preflight(),
    )
    monkeypatch.setattr(
        migration,
        "verify_provider_evidence_schema",
        lambda _cursor: [],
    )

    state = migration.OperationState(stage="test")

    result, _identity = migration._connect_and_run(
        mode="apply",
        migration_010_sql="MIGRATION 010",
        migration_011_sql="MIGRATION 011",
        connect=lambda: next(connections),
        state=state,
    )

    assert result["status"] == "applied"
    assert result["commit_state"] == "committed"
    assert state.commit_state == "committed"
    assert result["checks"]["migration_010"] == "pass"
    assert result["checks"]["migration_011"] == "pass"
    assert result["checks"]["second_connection_schema"] == "pass"



def test_preexisting_provider_index_name_refuses_application():
    conflicting = (
        "benchmark.idx_provider_usage_arm_run",
    )
    result = migration.PreflightResult(
        provider_schema_state="absent",
        present_provider_relations=(),
        absent_provider_relations=(
            migration.PROVIDER_EVIDENCE_RELATIONS
        ),
        missing_baseline_relations=(),
        present_provider_indexes=conflicting,
    )

    with pytest.raises(
        migration.ApplicationFailure
    ) as caught:
        migration.require_ready_preflight(
            result,
            stage="preflight",
        )

    assert caught.value.status == "index_collision"
    assert caught.value.error_type == (
        "ProviderEvidenceIndexCollisionError"
    )
    assert caught.value.conflicting_indexes == conflicting


def test_schema_snapshot_detects_wrong_index_table_binding():
    snapshot = complete_snapshot()

    index_name = (
        "benchmark.idx_provider_usage_arm_run"
    )
    wrong_binding = (
        index_name,
        "benchmark.benchmark_provider_cost_evidence",
    )

    bindings = {
        pair
        for pair in snapshot.provider_index_bindings
        if pair[0] != index_name
    }
    bindings.add(wrong_binding)

    defective = migration.SchemaSnapshot(
        baseline_relations=snapshot.baseline_relations,
        provider_relations=snapshot.provider_relations,
        provider_indexes=snapshot.provider_indexes,
        columns=snapshot.columns,
        provider_index_bindings=frozenset(bindings),
    )

    assert (
        "provider_evidence_index_bindings"
        in migration.verify_schema_snapshot(defective)
    )


def test_failure_payload_reports_index_collision_without_db_details():
    state = migration.OperationState(stage="preflight")

    payload = migration.failure_payload(
        mode="check-only",
        digest_010=migration.REVIEWED_MIGRATION_010_SHA256,
        digest_011=migration.REVIEWED_MIGRATION_011_SHA256,
        stage="preflight",
        status="index_collision",
        error_type="ProviderEvidenceIndexCollisionError",
        state=state,
        conflicting_indexes=(
            "benchmark.idx_provider_usage_arm_run",
        ),
    )

    assert payload["conflicting_indexes"] == [
        "benchmark.idx_provider_usage_arm_run"
    ]
    assert payload["commit_state"] == "not_committed"


def test_promotion_gate_current_columns_match_reviewed_migration():
    required = migration.ESSENTIAL_COLUMNS[
        "v_evidence_promotion_gate"
    ]

    expected = {
        "usage_reconciliation_is_current",
        "cost_reconciliation_is_current",
    }
    stale = {
        "usage_reconciliation_current",
        "cost_reconciliation_current",
    }

    assert expected.issubset(required)
    assert required.isdisjoint(stale)

    sql = migration.MIGRATION_011_PATH.read_text(
        encoding="utf-8"
    )

    for column_name in expected:
        assert column_name in sql
