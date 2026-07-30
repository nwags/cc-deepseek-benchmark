from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import scripts.apply_live_supervision_migration as migration


HASH = "a" * 64
REVIEWED_HASH = (
    "df828690b8ee007c3a6a96966226bd47169b3c13fa5217f2ddcd349098cb8404"
)


class RecordingCursor:
    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.statements: list[tuple[str, Any]] = []

    def __enter__(self) -> RecordingCursor:
        self.log.append("cursor_enter")
        return self

    def __exit__(self, *_args: object) -> None:
        self.log.append("cursor_exit")

    def execute(
        self,
        sql: str,
        params: Any = None,
    ) -> None:
        self.statements.append((sql, params))
        if sql == "-- migration 009":
            self.log.append("migration")
        elif "pg_advisory_xact_lock" in sql:
            self.log.append("lock")


class RecordingConnection:
    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self.log = log
        self.cursor_value = RecordingCursor(log)
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0

    def cursor(self) -> RecordingCursor:
        return self.cursor_value

    def commit(self) -> None:
        self.commits += 1
        self.log.append(f"{self.name}_commit")

    def rollback(self) -> None:
        self.rollbacks += 1
        self.log.append(f"{self.name}_rollback")

    def close(self) -> None:
        self.closed += 1
        self.log.append(f"{self.name}_close")


class RelationCursor:
    def __init__(self, present: set[str]) -> None:
        self.present = present
        self.current_relation = ""
        self.statements: list[str] = []

    def execute(self, sql: str, params: tuple[str]) -> None:
        self.statements.append(sql)
        self.current_relation = params[0]

    def fetchone(self) -> tuple[str | None]:
        if self.current_relation in self.present:
            return (self.current_relation,)
        return (None,)


def ready_preflight() -> migration.PreflightResult:
    return migration.PreflightResult(
        live_state="absent",
        present_relations=(),
        absent_relations=migration.LIVE_RELATIONS,
        missing_dependencies=(),
    )


def valid_snapshot() -> migration.SchemaSnapshot:
    indexes = [
        migration.IndexRecord(
            "live_runs",
            "semantic_live_runs_unique",
            True,
            ("live_run_id",),
        ),
        migration.IndexRecord(
            "live_run_events",
            "semantic_live_events_unique",
            True,
            ("live_run_id", "sequence"),
        ),
        migration.IndexRecord(
            "live_trials",
            "semantic_live_trials_unique",
            True,
            ("live_run_id", "trial_key"),
        ),
        migration.IndexRecord(
            "live_artifacts",
            "idx_live_artifacts_idempotent",
            True,
            (
                "live_run_id",
                "COALESCE(trial_key, ''::text)",
                "relative_local_path",
                "sha256",
            ),
        ),
    ]
    indexes.extend(
        migration.IndexRecord(table_name, index_name, False, ())
        for index_name, table_name
        in migration.EXPLICIT_INDEX_TABLES.items()
    )
    foreign_keys = (
        migration.ForeignKeyRecord(
            "live_run_events",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        migration.ForeignKeyRecord(
            "live_trials",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        migration.ForeignKeyRecord(
            "live_artifacts",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        migration.ForeignKeyRecord(
            "live_runs",
            "canonical_arm_run_id",
            "benchmark_arm_runs",
            "id",
            "n",
        ),
    )
    columns = [
        migration.ColumnRecord(
            "live_runs",
            "live_run_id",
            True,
            None,
        )
    ]
    columns.extend(
        migration.ColumnRecord(
            table_name,
            column_name,
            True,
            f"'{default}'::text",
        )
        for (table_name, column_name), default
        in migration.STATUS_DEFAULT_COLUMNS.items()
    )
    columns.extend(
        migration.ColumnRecord(
            table_name,
            column_name,
            True,
            "'{}'::jsonb",
        )
        for table_name, column_name
        in migration.JSONB_DEFAULT_COLUMNS
    )
    return migration.SchemaSnapshot(
        relations=frozenset(migration.LIVE_RELATIONS),
        indexes=tuple(indexes),
        foreign_keys=foreign_keys,
        columns=tuple(columns),
        comments={
            "live_runs": "live run comment",
            "live_run_events": "live event comment",
        },
    )


def test_permanent_mutation_requires_apply() -> None:
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(["--expected-sha256", HASH])


def test_check_only_and_apply_are_mutually_exclusive() -> None:
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            [
                "--apply",
                "--check-only",
                "--expected-sha256",
                HASH,
            ]
        )


def test_expected_hash_is_required_and_well_formed() -> None:
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(["--apply"])
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            ["--apply", "--expected-sha256", "not-a-sha256"]
        )


def test_utility_has_one_fixed_reviewed_migration() -> None:
    assert migration.MIGRATION_DISPLAY_PATH == (
        "db/migrations/phase3/009_live_run_supervision.sql"
    )
    assert migration.migration_sha256(migration.migration_bytes()) == (
        REVIEWED_HASH
    )
    assert migration.REVIEWED_MIGRATION_SHA256 == REVIEWED_HASH
    with pytest.raises(migration.ArgumentContractError):
        migration.parse_args(
            [
                "--apply",
                "--expected-sha256",
                REVIEWED_HASH,
                "--migration",
                "other.sql",
            ]
        )


def test_hash_mismatch_refuses_before_connection_or_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = tmp_path / "evidence.json"
    monkeypatch.setattr(migration, "migration_bytes", lambda: b"reviewed")
    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgresql://secret.invalid/database",
    )
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(
            connect=lambda *_args, **_kwargs: pytest.fail(
                "database connection attempted"
            )
        ),
    )

    assert migration.main(
        [
            "--apply",
            "--expected-sha256",
            "0" * 64,
            "--evidence-out",
            str(evidence),
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["failed_stage"] == "hash"
    assert result["error_type"] == "MigrationHashMismatch"
    assert result["commit_state"] == "not_committed"
    assert not evidence.exists()


def test_altered_migration_cannot_be_self_authorized_with_its_hash(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    altered = b"altered migration"
    monkeypatch.setattr(migration, "migration_bytes", lambda: altered)
    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgresql://secret.invalid/database",
    )

    assert migration.main(
        [
            "--apply",
            "--expected-sha256",
            migration.migration_sha256(altered),
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["failed_stage"] == "hash"
    assert result["error_type"] == "MigrationHashMismatch"
    assert result["commit_state"] == "not_committed"


def test_missing_database_url_reports_safely(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = migration.migration_bytes()
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    assert migration.main(
        [
            "--check-only",
            "--expected-sha256",
            REVIEWED_HASH,
        ]
    ) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["failed_stage"] == "connection"
    assert result["error_type"] == "MissingEnvironmentError"
    assert result["commit_state"] == "not_committed"
    assert "SUPABASE_DB_URL" not in json.dumps(result)


def test_all_absent_preflight_is_ready() -> None:
    cursor = RelationCursor(set(migration.REQUIRED_DEPENDENCIES))
    result = migration.database_preflight(cursor)
    migration.require_ready_preflight(result, stage="preflight")

    assert result.live_state == "absent"
    assert result.absent_relations == migration.LIVE_RELATIONS
    assert not result.missing_dependencies
    assert all(
        "to_regclass(%s::text)" in statement
        for statement in cursor.statements
    )


def test_all_present_preflight_refuses_as_already_present() -> None:
    result = migration.PreflightResult(
        live_state="present",
        present_relations=migration.LIVE_RELATIONS,
        absent_relations=(),
        missing_dependencies=(),
    )
    with pytest.raises(migration.ApplicationFailure) as raised:
        migration.require_ready_preflight(result, stage="preflight")
    assert raised.value.status == "already_present"
    assert raised.value.present_relations == migration.LIVE_RELATIONS


def test_partial_schema_lists_present_and_absent_relations() -> None:
    result = migration.PreflightResult(
        live_state="partial",
        present_relations=migration.LIVE_RELATIONS[:2],
        absent_relations=migration.LIVE_RELATIONS[2:],
        missing_dependencies=(),
    )
    with pytest.raises(migration.ApplicationFailure) as raised:
        migration.require_ready_preflight(result, stage="preflight")
    assert raised.value.status == "partial_schema"
    assert raised.value.present_relations == migration.LIVE_RELATIONS[:2]
    assert raised.value.absent_relations == migration.LIVE_RELATIONS[2:]


def test_missing_dependency_refuses_application() -> None:
    result = migration.PreflightResult(
        live_state="absent",
        present_relations=(),
        absent_relations=migration.LIVE_RELATIONS,
        missing_dependencies=("benchmark.v_dashboard_arms",),
    )
    with pytest.raises(migration.ApplicationFailure) as raised:
        migration.require_ready_preflight(result, stage="preflight")
    assert raised.value.status == "missing_dependencies"
    assert raised.value.missing_dependencies == (
        "benchmark.v_dashboard_arms",
    )


def test_advisory_lock_sql_is_explicitly_typed() -> None:
    log: list[str] = []
    cursor = RecordingCursor(log)
    migration.acquire_migration_lock(cursor)
    sql, params = cursor.statements[0]
    assert "hashtextextended(%s::text, 0::bigint)" in sql
    assert params == (migration.ADVISORY_LOCK_IDENTITY,)


def test_apply_repeats_locked_preflight_and_verifies_before_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log: list[str] = []
    connections = [
        RecordingConnection("first", log),
        RecordingConnection("second", log),
    ]
    preflight_calls = 0
    verification_calls = 0

    def preflight(_cursor: Any) -> migration.PreflightResult:
        nonlocal preflight_calls
        preflight_calls += 1
        log.append(f"preflight_{preflight_calls}")
        return ready_preflight()

    def verify(_cursor: Any) -> list[str]:
        nonlocal verification_calls
        verification_calls += 1
        log.append(f"verify_{verification_calls}")
        return []

    monkeypatch.setattr(
        migration,
        "read_database_identity",
        lambda _cursor: {
            "database_name": "postgres",
            "database_user": "app",
            "server_version": "PostgreSQL test",
        },
    )
    monkeypatch.setattr(migration, "database_preflight", preflight)
    monkeypatch.setattr(migration, "verify_live_schema", verify)
    state = migration.OperationState()

    result, identity = migration._connect_and_run(
        mode="apply",
        migration_sql="-- migration 009",
        connect=lambda: connections.pop(0),
        state=state,
    )

    assert result["status"] == "applied"
    assert result["commit_state"] == "committed"
    assert identity["database_name"] == "postgres"
    assert preflight_calls == 2
    assert verification_calls == 2
    assert log.index("lock") < log.index("preflight_2")
    assert log.index("preflight_2") < log.index("migration")
    assert log.index("migration") < log.index("verify_1")
    assert log.index("verify_1") < log.index("first_commit")
    assert log.index("first_commit") < log.index("verify_2")


def test_verification_failure_rolls_back_without_commit_or_second_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log: list[str] = []
    connection = RecordingConnection("first", log)
    connect_calls = 0

    def connect() -> RecordingConnection:
        nonlocal connect_calls
        connect_calls += 1
        return connection

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
        "verify_live_schema",
        lambda _cursor: ["foreign_key_live_trials_live_run_id"],
    )
    state = migration.OperationState()

    with pytest.raises(migration.ApplicationFailure) as raised:
        migration._connect_and_run(
            mode="apply",
            migration_sql="-- migration 009",
            connect=connect,
            state=state,
        )

    assert raised.value.stage == "same_transaction_verification"
    assert state.commit_state == "not_committed"
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert connect_calls == 1
    assert log.index("migration") < log.index("first_rollback")


def test_second_connection_failure_preserves_committed_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log: list[str] = []
    connections = [
        RecordingConnection("first", log),
        RecordingConnection("second", log),
    ]
    verification_calls = 0

    def verify(_cursor: Any) -> list[str]:
        nonlocal verification_calls
        verification_calls += 1
        if verification_calls == 1:
            return []
        return ["second_connection_schema"]

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
    monkeypatch.setattr(migration, "verify_live_schema", verify)
    state = migration.OperationState()

    with pytest.raises(migration.ApplicationFailure) as raised:
        migration._connect_and_run(
            mode="apply",
            migration_sql="-- migration 009",
            connect=lambda: connections.pop(0),
            state=state,
        )

    assert raised.value.stage == "second_connection_verification"
    assert state.commit_state == "committed"
    assert "first_commit" in log
    assert "second_rollback" in log


def test_check_only_never_locks_or_executes_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log: list[str] = []
    connection = RecordingConnection("first", log)
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

    result, _identity = migration._connect_and_run(
        mode="check-only",
        migration_sql="-- migration 009",
        connect=lambda: connection,
        state=migration.OperationState(),
    )

    assert result["status"] == "ready"
    assert result["commit_state"] == "not_committed"
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert not any(
        "pg_advisory_xact_lock" in sql
        or sql == "-- migration 009"
        for sql, _params in connection.cursor_value.statements
    )


class SyntheticPostgresError(Exception):
    sqlstate = "42P18"


def test_failure_payload_reports_only_safe_stage_and_sqlstate() -> None:
    secret = "postgresql://user:password@example.invalid/database"
    result = migration.failure_payload(
        mode="apply",
        migration_digest="digest",
        stage="migration",
        status="failed",
        error_type="SyntheticPostgresError",
        state=migration.OperationState(),
        cause=SyntheticPostgresError(secret),
    )
    assert result["failed_stage"] == "migration"
    assert result["commit_state"] == "not_committed"
    assert result["sqlstate"] == "42P18"
    assert secret not in json.dumps(result)
    assert str(SyntheticPostgresError(secret)) not in json.dumps(result)


def test_main_does_not_emit_connection_exception_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = migration.migration_bytes()
    secret = "postgresql://user:password@example.invalid/database"
    monkeypatch.setenv("SUPABASE_DB_URL", secret)

    def fail_connect(*_args: Any, **_kwargs: Any) -> None:
        raise SyntheticPostgresError(secret)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=fail_connect),
    )
    assert migration.main(
        [
            "--check-only",
            "--expected-sha256",
            REVIEWED_HASH,
        ]
    ) == 1
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["failed_stage"] == "connection"
    assert result["sqlstate"] == "42P18"
    assert result["commit_state"] == "not_committed"
    assert secret not in output


def test_main_connects_with_autocommit_disabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = migration.migration_bytes()
    calls: list[tuple[str, bool]] = []
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://not-printed")

    def connect(db_url: str, *, autocommit: bool) -> object:
        calls.append((db_url, autocommit))
        return object()

    def run_with_connection(
        *,
        mode: str,
        migration_sql: str,
        connect: Callable[[], Any],
        state: migration.OperationState,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        assert mode == "check-only"
        assert migration_sql == raw.decode()
        assert state.stage == "connection"
        connect()
        return (
            {
                "status": "ready",
                "mode": "check-only",
                "preflight": {
                    "live_relations": "absent",
                    "dependencies": "present",
                },
            },
            {
                "database_name": "postgres",
                "database_user": "app",
                "server_version": "PostgreSQL test",
            },
        )

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=connect),
    )
    monkeypatch.setattr(
        migration,
        "_connect_and_run",
        run_with_connection,
    )

    assert migration.main(
        [
            "--check-only",
            "--expected-sha256",
            REVIEWED_HASH,
        ]
    ) == 0
    assert calls == [("postgresql://not-printed", False)]
    output = capsys.readouterr().out
    assert json.loads(output)["commit_state"] == "not_committed"
    assert "postgresql://not-printed" not in output


def test_apply_success_reports_committed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://not-printed")
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=lambda *_args, **_kwargs: object()),
    )

    def apply_success(
        *,
        mode: str,
        migration_sql: str,
        connect: Callable[[], Any],
        state: migration.OperationState,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        del migration_sql, connect
        assert mode == "apply"
        state.committed = True
        state.stage = "second_connection_verification"
        return (
            {"status": "applied", "mode": "apply"},
            {
                "database_name": "postgres",
                "database_user": "app",
                "server_version": "PostgreSQL test",
            },
        )

    monkeypatch.setattr(
        migration,
        "_connect_and_run",
        apply_success,
    )
    assert migration.main(
        [
            "--apply",
            "--expected-sha256",
            REVIEWED_HASH,
        ]
    ) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert json.loads(output.out)["commit_state"] == "committed"
    assert "postgresql://not-printed" not in output.out


@pytest.mark.parametrize(
    ("failed_stage", "committed"),
    [
        ("same_transaction_verification", False),
        ("second_connection_verification", True),
    ],
)
def test_database_failure_reports_derived_commit_state(
    failed_stage: str,
    committed: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://not-printed")
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=lambda *_args, **_kwargs: object()),
    )

    def fail_database_processing(
        *,
        mode: str,
        migration_sql: str,
        connect: Callable[[], Any],
        state: migration.OperationState,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        del mode, migration_sql, connect
        state.committed = committed
        state.stage = failed_stage
        raise migration.ApplicationFailure(
            status="verification_failed",
            stage=failed_stage,
            error_type=migration.SchemaVerificationError.__name__,
            failed_verification_checks=("synthetic_check",),
        )

    monkeypatch.setattr(
        migration,
        "_connect_and_run",
        fail_database_processing,
    )
    assert migration.main(
        [
            "--apply",
            "--expected-sha256",
            REVIEWED_HASH,
        ]
    ) == 1
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert output.err == ""
    assert result["failed_stage"] == failed_stage
    assert result["commit_state"] == (
        "committed" if committed else "not_committed"
    )
    assert "postgresql://not-printed" not in output.out


def test_evidence_output_is_atomic_and_matches_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = tmp_path / "review" / "application.json"
    payload = {
        "status": "ready",
        "mode": "check-only",
        "commit_state": "not_committed",
    }

    migration._emit(payload, evidence_path=evidence)

    assert evidence.read_text() == capsys.readouterr().out
    assert not list(evidence.parent.glob("*.tmp"))
    assert json.loads(evidence.read_text()) == payload


def test_existing_regular_evidence_is_rejected_before_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text("original evidence\n")
    connect_calls = 0

    def connect(*_args: Any, **_kwargs: Any) -> None:
        nonlocal connect_calls
        connect_calls += 1
        pytest.fail("database connection attempted")

    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://not-printed")
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=connect),
    )

    assert migration.main(
        [
            "--apply",
            "--expected-sha256",
            REVIEWED_HASH,
            "--evidence-out",
            str(evidence),
        ]
    ) == 2
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert output.err == ""
    assert connect_calls == 0
    assert evidence.read_text() == "original evidence\n"
    assert result["failed_stage"] == "evidence"
    assert result["error_type"] == "EvidenceAlreadyExists"
    assert result["commit_state"] == "not_committed"
    assert str(evidence) not in output.out
    assert "postgresql://not-printed" not in output.out


def test_symlinked_evidence_output_is_rejected(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}")
    evidence = tmp_path / "evidence.json"
    evidence.symlink_to(target)
    with pytest.raises(migration.UnsafeEvidencePath):
        migration.ensure_safe_evidence_path(evidence)


def test_existing_directory_evidence_output_is_rejected(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.mkdir()
    with pytest.raises(migration.EvidenceAlreadyExists):
        migration.ensure_safe_evidence_path(evidence)


def test_symlinked_evidence_parent_is_rejected(
    tmp_path: Path,
) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    symlink_parent = tmp_path / "linked"
    symlink_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(migration.UnsafeEvidencePath):
        migration.ensure_safe_evidence_path(
            symlink_parent / "evidence.json"
        )


def test_concurrent_evidence_destination_cannot_be_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.json"
    original_link = os.link

    def create_destination_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=dst_dir_fd,
        )
        try:
            os.write(destination_fd, b"concurrent evidence\n")
        finally:
            os.close(destination_fd)
        original_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(
        migration.os,
        "link",
        create_destination_then_link,
    )
    with pytest.raises(migration.EvidenceAlreadyExists):
        migration.write_evidence_atomically(
            evidence,
            '{"status":"applied"}\n',
        )

    assert evidence.read_text() == "concurrent evidence\n"
    assert not [
        path
        for path in tmp_path.iterdir()
        if path.name.endswith(".tmp")
    ]


@pytest.mark.parametrize(
    ("mode", "committed"),
    [
        ("check-only", False),
        ("apply", True),
    ],
)
def test_evidence_failure_is_one_safe_json_with_commit_state(
    mode: str,
    committed: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = tmp_path / "evidence.json"
    secret = "postgresql://user:password@example.invalid/database"
    monkeypatch.setenv("SUPABASE_DB_URL", secret)
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=lambda *_args, **_kwargs: object()),
    )

    def database_success(
        *,
        mode: str,
        migration_sql: str,
        connect: Callable[[], Any],
        state: migration.OperationState,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        del migration_sql, connect
        state.committed = committed
        return (
            {"status": "applied" if committed else "ready", "mode": mode},
            {
                "database_name": "postgres",
                "database_user": "app",
                "server_version": "PostgreSQL test",
            },
        )

    def fail_evidence_write(
        _path: Path,
        _serialized: str,
    ) -> None:
        raise SyntheticPostgresError(secret)

    monkeypatch.setattr(
        migration,
        "_connect_and_run",
        database_success,
    )
    monkeypatch.setattr(
        migration,
        "write_evidence_atomically",
        fail_evidence_write,
    )
    assert migration.main(
        [
            f"--{mode}",
            "--expected-sha256",
            REVIEWED_HASH,
            "--evidence-out",
            str(evidence),
        ]
    ) == 1

    output = capsys.readouterr()
    lines = output.out.splitlines()
    assert output.err == ""
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert result == {
        "status": "failed",
        "mode": mode,
        "migration_path": migration.MIGRATION_DISPLAY_PATH,
        "migration_sha256": REVIEWED_HASH,
        "failed_stage": "evidence",
        "error_type": "SyntheticPostgresError",
        "sqlstate": "42P18",
        "commit_state": (
            "committed" if committed else "not_committed"
        ),
    }
    assert secret not in output.out
    assert str(evidence) not in output.out
    assert "Traceback" not in output.out
    assert not evidence.exists()


def test_complete_schema_snapshot_passes_every_check() -> None:
    assert migration.verify_schema_snapshot(valid_snapshot()) == []


@pytest.mark.parametrize(
    ("mutate", "expected_check"),
    [
        (
            lambda snapshot: replace(
                snapshot,
                relations=frozenset(
                    relation
                    for relation in snapshot.relations
                    if relation != "benchmark.live_runs"
                ),
            ),
            "live_relations",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                indexes=tuple(
                    index
                    for index in snapshot.indexes
                    if index.index_name != "semantic_live_events_unique"
                ),
            ),
            "live_run_events_live_run_id_sequence_key",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                indexes=tuple(
                    replace(index, predicate="(sequence > 10)")
                    if index.index_name == "semantic_live_events_unique"
                    else index
                    for index in snapshot.indexes
                ),
            ),
            "live_run_events_live_run_id_sequence_key",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                indexes=tuple(
                    index
                    for index in snapshot.indexes
                    if index.index_name != "idx_live_runs_active"
                ),
            ),
            "idx_live_runs_active",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                foreign_keys=tuple(
                    replace(foreign_key, delete_action="a")
                    if foreign_key.source_table == "live_trials"
                    else foreign_key
                    for foreign_key in snapshot.foreign_keys
                ),
            ),
            "foreign_key_live_trials_live_run_id",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                foreign_keys=tuple(
                    replace(foreign_key, is_validated=False)
                    if foreign_key.source_table == "live_artifacts"
                    else foreign_key
                    for foreign_key in snapshot.foreign_keys
                ),
            ),
            "foreign_key_live_artifacts_live_run_id",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                columns=tuple(
                    replace(column, default_expression=None)
                    if (
                        column.table_name,
                        column.column_name,
                    ) == ("live_runs", "status")
                    else column
                    for column in snapshot.columns
                ),
            ),
            "live_runs_status_default_starting",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                columns=tuple(
                    replace(column, not_null=False)
                    if (
                        column.table_name,
                        column.column_name,
                    ) == ("live_runs", "live_run_id")
                    else column
                    for column in snapshot.columns
                ),
            ),
            "live_runs_live_run_id_not_null",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                columns=tuple(
                    replace(column, default_expression=None)
                    if (
                        column.table_name,
                        column.column_name,
                    ) == ("live_trials", "raw_result")
                    else column
                    for column in snapshot.columns
                ),
            ),
            "live_trials_raw_result_default_empty_jsonb",
        ),
        (
            lambda snapshot: replace(
                snapshot,
                comments={
                    **snapshot.comments,
                    "live_run_events": None,
                },
            ),
            "live_run_events_comment",
        ),
    ],
)
def test_schema_verification_detects_catalog_defects(
    mutate: Callable[
        [migration.SchemaSnapshot],
        migration.SchemaSnapshot,
    ],
    expected_check: str,
) -> None:
    assert expected_check in migration.verify_schema_snapshot(
        mutate(valid_snapshot())
    )
