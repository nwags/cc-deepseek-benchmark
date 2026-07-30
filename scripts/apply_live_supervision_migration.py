#!/usr/bin/env python3
"""Apply only the reviewed live-supervision migration 009."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DISPLAY_PATH = (
    "db/migrations/phase3/009_live_run_supervision.sql"
)
MIGRATION_PATH = REPO_ROOT / MIGRATION_DISPLAY_PATH
REVIEWED_MIGRATION_SHA256 = (
    "df828690b8ee007c3a6a96966226bd47169b3c13fa5217f2ddcd349098cb8404"
)
ADVISORY_LOCK_IDENTITY = (
    "cc-deepseek-bench|phase3|009_live_run_supervision"
)
LIVE_RELATIONS = (
    "benchmark.live_runs",
    "benchmark.live_run_events",
    "benchmark.live_trials",
    "benchmark.live_artifacts",
)
REQUIRED_DEPENDENCIES = (
    "benchmark.benchmark_arm_runs",
    "benchmark.benchmark_runs",
    "benchmark.benchmark_trials",
    "benchmark.benchmark_artifacts",
    "benchmark.benchmark_arms",
    "benchmark.v_dashboard_arms",
    "benchmark.v_valid_arm_run_summary",
    "benchmark.benchmark_invalid_arm_runs",
)
EXPLICIT_INDEX_TABLES = {
    "idx_live_runs_newest": "live_runs",
    "idx_live_runs_active": "live_runs",
    "idx_live_runs_stale_heartbeat": "live_runs",
    "idx_live_runs_github_execution": "live_runs",
    "idx_live_runs_runner": "live_runs",
    "idx_live_run_events_ordered": "live_run_events",
    "idx_live_trials_run_status": "live_trials",
    "idx_live_artifacts_run_trial": "live_artifacts",
}
JSONB_DEFAULT_COLUMNS = (
    ("live_runs", "command_summary"),
    ("live_runs", "raw_metadata"),
    ("live_run_events", "payload"),
    ("live_trials", "completion_evidence"),
    ("live_trials", "raw_result"),
    ("live_artifacts", "raw_metadata"),
)
STATUS_DEFAULT_COLUMNS = {
    ("live_runs", "status"): "starting",
    ("live_trials", "status"): "detected",
    ("live_trials", "stability_state"): "observed",
    ("live_artifacts", "stability_state"): "stable",
}
COMMENTED_TABLES = ("live_runs", "live_run_events")


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ArgumentContractError(message)


class ArgumentContractError(RuntimeError):
    pass


class MigrationHashMismatch(RuntimeError):
    pass


class MissingEnvironmentError(RuntimeError):
    pass


class UnsafeEvidencePath(RuntimeError):
    pass


class EvidenceAlreadyExists(UnsafeEvidencePath):
    pass


class ExistingLiveSchemaError(RuntimeError):
    pass


class PartialLiveSchemaError(RuntimeError):
    pass


class MissingDependencyError(RuntimeError):
    pass


class SchemaVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightResult:
    live_state: str
    present_relations: tuple[str, ...]
    absent_relations: tuple[str, ...]
    missing_dependencies: tuple[str, ...]


@dataclass(frozen=True)
class IndexRecord:
    table_name: str
    index_name: str
    is_unique: bool
    terms: tuple[str, ...]
    is_valid: bool = True
    predicate: str | None = None


@dataclass(frozen=True)
class ForeignKeyRecord:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    delete_action: str
    is_validated: bool = True


@dataclass(frozen=True)
class ColumnRecord:
    table_name: str
    column_name: str
    not_null: bool
    default_expression: str | None


@dataclass(frozen=True)
class SchemaSnapshot:
    relations: frozenset[str]
    indexes: tuple[IndexRecord, ...]
    foreign_keys: tuple[ForeignKeyRecord, ...]
    columns: tuple[ColumnRecord, ...]
    comments: Mapping[str, str | None]


@dataclass
class OperationState:
    stage: str = "connection"
    committed: bool = False
    identity: dict[str, str] = field(default_factory=dict)

    @property
    def commit_state(self) -> str:
        return "committed" if self.committed else "not_committed"


class ApplicationFailure(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        stage: str,
        error_type: str,
        present_relations: Sequence[str] = (),
        absent_relations: Sequence[str] = (),
        missing_dependencies: Sequence[str] = (),
        failed_verification_checks: Sequence[str] = (),
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(error_type)
        self.status = status
        self.stage = stage
        self.error_type = error_type
        self.present_relations = tuple(present_relations)
        self.absent_relations = tuple(absent_relations)
        self.missing_dependencies = tuple(missing_dependencies)
        self.failed_verification_checks = tuple(
            failed_verification_checks
        )
        self.cause = cause


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description=__doc__, add_help=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--evidence-out")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        raise ArgumentContractError(
            "--expected-sha256 must be 64 lowercase hexadecimal characters"
        )
    return args


def requested_mode(argv: Sequence[str]) -> str:
    if "--apply" in argv:
        return "apply"
    if "--check-only" in argv:
        return "check-only"
    return "unknown"


def migration_bytes(path: Path | None = None) -> bytes:
    return (path or MIGRATION_PATH).read_bytes()


def migration_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_sqlstate(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    value = getattr(exc, "sqlstate", None)
    if value is None:
        value = getattr(getattr(exc, "diag", None), "sqlstate", None)
    text = str(value or "")
    if len(text) == 5 and text.isalnum():
        return text.upper()
    return None


def relation_presence(
    cursor: Any,
    relations: Sequence[str],
) -> tuple[str, ...]:
    present: list[str] = []
    for relation in relations:
        cursor.execute(
            "select to_regclass(%s::text)",
            (relation,),
        )
        if cursor.fetchone()[0] is not None:
            present.append(relation)
    return tuple(present)


def classify_live_relations(
    present_relations: Sequence[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    present = tuple(
        relation
        for relation in LIVE_RELATIONS
        if relation in set(present_relations)
    )
    absent = tuple(
        relation for relation in LIVE_RELATIONS if relation not in present
    )
    if not present:
        state = "absent"
    elif not absent:
        state = "present"
    else:
        state = "partial"
    return state, present, absent


def database_preflight(cursor: Any) -> PreflightResult:
    present_live = relation_presence(cursor, LIVE_RELATIONS)
    live_state, present, absent = classify_live_relations(present_live)
    present_dependencies = set(
        relation_presence(cursor, REQUIRED_DEPENDENCIES)
    )
    missing_dependencies = tuple(
        dependency
        for dependency in REQUIRED_DEPENDENCIES
        if dependency not in present_dependencies
    )
    return PreflightResult(
        live_state=live_state,
        present_relations=present,
        absent_relations=absent,
        missing_dependencies=missing_dependencies,
    )


def require_ready_preflight(
    result: PreflightResult,
    *,
    stage: str,
) -> None:
    if result.live_state == "present":
        raise ApplicationFailure(
            status="already_present",
            stage=stage,
            error_type=ExistingLiveSchemaError.__name__,
            present_relations=result.present_relations,
            absent_relations=result.absent_relations,
            missing_dependencies=result.missing_dependencies,
        )
    if result.live_state == "partial":
        raise ApplicationFailure(
            status="partial_schema",
            stage=stage,
            error_type=PartialLiveSchemaError.__name__,
            present_relations=result.present_relations,
            absent_relations=result.absent_relations,
            missing_dependencies=result.missing_dependencies,
        )
    if result.missing_dependencies:
        raise ApplicationFailure(
            status="missing_dependencies",
            stage=stage,
            error_type=MissingDependencyError.__name__,
            present_relations=result.present_relations,
            absent_relations=result.absent_relations,
            missing_dependencies=result.missing_dependencies,
        )


def read_database_identity(cursor: Any) -> dict[str, str]:
    cursor.execute("select current_database(), current_user, version()")
    database_name, database_user, server_version = cursor.fetchone()
    return {
        "database_name": str(database_name),
        "database_user": str(database_user),
        "server_version": str(server_version),
    }


def collect_schema_snapshot(cursor: Any) -> SchemaSnapshot:
    relations = frozenset(relation_presence(cursor, LIVE_RELATIONS))
    table_names = [relation.rsplit(".", 1)[-1] for relation in LIVE_RELATIONS]
    cursor.execute(
        """
        select
            table_class.relname,
            index_class.relname,
            index_catalog.indisunique,
            index_catalog.indisvalid,
            pg_get_expr(
                index_catalog.indpred,
                index_catalog.indrelid
            ),
            array(
                select case
                    when index_key.attnum = 0
                        then pg_get_indexdef(
                            index_catalog.indexrelid,
                            index_key.ordinality::integer,
                            true
                        )
                    else indexed_column.attname
                end
                from unnest(index_catalog.indkey::smallint[])
                    with ordinality as index_key(attnum, ordinality)
                left join pg_catalog.pg_attribute indexed_column
                  on indexed_column.attrelid = table_class.oid
                 and indexed_column.attnum = index_key.attnum
                order by index_key.ordinality
            )
        from pg_catalog.pg_index index_catalog
        join pg_catalog.pg_class table_class
          on table_class.oid = index_catalog.indrelid
        join pg_catalog.pg_namespace table_namespace
          on table_namespace.oid = table_class.relnamespace
        join pg_catalog.pg_class index_class
          on index_class.oid = index_catalog.indexrelid
        where table_namespace.nspname = 'benchmark'
          and table_class.relname = any(%s::text[])
        order by table_class.relname, index_class.relname
        """,
        (table_names,),
    )
    indexes = tuple(
        IndexRecord(
            table_name=str(table_name),
            index_name=str(index_name),
            is_unique=bool(is_unique),
            terms=tuple(str(term) for term in (terms or [])),
            is_valid=bool(is_valid),
            predicate=(
                str(predicate) if predicate is not None else None
            ),
        )
        for (
            table_name,
            index_name,
            is_unique,
            is_valid,
            predicate,
            terms,
        ) in cursor.fetchall()
    )

    cursor.execute(
        """
        select
            source_table.relname,
            source_column.attname,
            target_table.relname,
            target_column.attname,
            constraint_catalog.confdeltype,
            constraint_catalog.convalidated
        from pg_catalog.pg_constraint constraint_catalog
        join pg_catalog.pg_class source_table
          on source_table.oid = constraint_catalog.conrelid
        join pg_catalog.pg_namespace source_namespace
          on source_namespace.oid = source_table.relnamespace
        join pg_catalog.pg_class target_table
          on target_table.oid = constraint_catalog.confrelid
        join pg_catalog.pg_namespace target_namespace
          on target_namespace.oid = target_table.relnamespace
        cross join lateral unnest(
            constraint_catalog.conkey,
            constraint_catalog.confkey
        ) with ordinality as key_pair(
            source_attnum,
            target_attnum,
            ordinality
        )
        join pg_catalog.pg_attribute source_column
          on source_column.attrelid = source_table.oid
         and source_column.attnum = key_pair.source_attnum
        join pg_catalog.pg_attribute target_column
          on target_column.attrelid = target_table.oid
         and target_column.attnum = key_pair.target_attnum
        where constraint_catalog.contype = 'f'
          and source_namespace.nspname = 'benchmark'
          and target_namespace.nspname = 'benchmark'
          and source_table.relname = any(%s::text[])
        order by source_table.relname, source_column.attname
        """,
        (table_names,),
    )
    foreign_keys = tuple(
        ForeignKeyRecord(
            source_table=str(source_table),
            source_column=str(source_column),
            target_table=str(target_table),
            target_column=str(target_column),
            delete_action=str(delete_action),
            is_validated=bool(is_validated),
        )
        for (
            source_table,
            source_column,
            target_table,
            target_column,
            delete_action,
            is_validated,
        ) in cursor.fetchall()
    )

    cursor.execute(
        """
        select
            table_class.relname,
            column_catalog.attname,
            column_catalog.attnotnull,
            pg_get_expr(
                default_catalog.adbin,
                default_catalog.adrelid
            )
        from pg_catalog.pg_class table_class
        join pg_catalog.pg_namespace table_namespace
          on table_namespace.oid = table_class.relnamespace
        join pg_catalog.pg_attribute column_catalog
          on column_catalog.attrelid = table_class.oid
         and column_catalog.attnum > 0
         and not column_catalog.attisdropped
        left join pg_catalog.pg_attrdef default_catalog
          on default_catalog.adrelid = table_class.oid
         and default_catalog.adnum = column_catalog.attnum
        where table_namespace.nspname = 'benchmark'
          and table_class.relname = any(%s::text[])
        order by table_class.relname, column_catalog.attnum
        """,
        (table_names,),
    )
    columns = tuple(
        ColumnRecord(
            table_name=str(table_name),
            column_name=str(column_name),
            not_null=bool(not_null),
            default_expression=(
                str(default_expression)
                if default_expression is not None
                else None
            ),
        )
        for table_name, column_name, not_null, default_expression
        in cursor.fetchall()
    )

    cursor.execute(
        """
        select
            table_class.relname,
            obj_description(table_class.oid, 'pg_class')
        from pg_catalog.pg_class table_class
        join pg_catalog.pg_namespace table_namespace
          on table_namespace.oid = table_class.relnamespace
        where table_namespace.nspname = 'benchmark'
          and table_class.relname = any(%s::text[])
        """,
        (list(COMMENTED_TABLES),),
    )
    comments = {
        str(table_name): (
            str(comment) if comment is not None else None
        )
        for table_name, comment in cursor.fetchall()
    }
    return SchemaSnapshot(
        relations=relations,
        indexes=indexes,
        foreign_keys=foreign_keys,
        columns=columns,
        comments=comments,
    )


def _normalized_term(value: str) -> str:
    return re.sub(r"\s+", "", value.lower().replace('"', ""))


def _index_terms_match(
    record: IndexRecord,
    expected_terms: Sequence[str],
) -> bool:
    actual = tuple(_normalized_term(term) for term in record.terms)
    expected = tuple(_normalized_term(term) for term in expected_terms)
    return actual == expected


def verify_schema_snapshot(snapshot: SchemaSnapshot) -> list[str]:
    failed: list[str] = []
    if snapshot.relations != frozenset(LIVE_RELATIONS):
        failed.append("live_relations")

    semantic_unique_indexes = (
        (
            "live_runs_live_run_id_key",
            "live_runs",
            ("live_run_id",),
        ),
        (
            "live_run_events_live_run_id_sequence_key",
            "live_run_events",
            ("live_run_id", "sequence"),
        ),
        (
            "live_trials_live_run_id_trial_key_key",
            "live_trials",
            ("live_run_id", "trial_key"),
        ),
        (
            "idx_live_artifacts_idempotent",
            "live_artifacts",
            (
                "live_run_id",
                "coalesce(trial_key, ''::text)",
                "relative_local_path",
                "sha256",
            ),
        ),
    )
    for check_name, table_name, terms in semantic_unique_indexes:
        if not any(
            index.table_name == table_name
            and index.is_unique
            and index.is_valid
            and index.predicate is None
            and _index_terms_match(index, terms)
            for index in snapshot.indexes
        ):
            failed.append(check_name)

    index_pairs = {
        (index.index_name, index.table_name)
        for index in snapshot.indexes
        if index.is_valid
    }
    for index_name, table_name in EXPLICIT_INDEX_TABLES.items():
        if (index_name, table_name) not in index_pairs:
            failed.append(index_name)

    expected_foreign_keys = (
        ForeignKeyRecord(
            "live_run_events",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        ForeignKeyRecord(
            "live_trials",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        ForeignKeyRecord(
            "live_artifacts",
            "live_run_id",
            "live_runs",
            "live_run_id",
            "c",
        ),
        ForeignKeyRecord(
            "live_runs",
            "canonical_arm_run_id",
            "benchmark_arm_runs",
            "id",
            "n",
        ),
    )
    foreign_key_set = set(snapshot.foreign_keys)
    for foreign_key in expected_foreign_keys:
        if foreign_key not in foreign_key_set:
            failed.append(
                "foreign_key_"
                f"{foreign_key.source_table}_{foreign_key.source_column}"
            )

    columns = {
        (column.table_name, column.column_name): column
        for column in snapshot.columns
    }
    live_run_id = columns.get(("live_runs", "live_run_id"))
    if live_run_id is None or not live_run_id.not_null:
        failed.append("live_runs_live_run_id_not_null")

    for key, expected_default in STATUS_DEFAULT_COLUMNS.items():
        column = columns.get(key)
        expression = (
            _normalized_term(column.default_expression or "")
            if column is not None
            else ""
        )
        if (
            column is None
            or not column.not_null
            or expression != f"'{expected_default}'::text"
        ):
            failed.append(
                f"{key[0]}_{key[1]}_default_{expected_default}"
            )

    for key in JSONB_DEFAULT_COLUMNS:
        column = columns.get(key)
        expression = (
            _normalized_term(column.default_expression or "")
            if column is not None
            else ""
        )
        if (
            column is None
            or not column.not_null
            or expression != "'{}'::jsonb"
        ):
            failed.append(f"{key[0]}_{key[1]}_default_empty_jsonb")

    for table_name in COMMENTED_TABLES:
        if not snapshot.comments.get(table_name):
            failed.append(f"{table_name}_comment")
    return failed


def verify_live_schema(cursor: Any) -> list[str]:
    return verify_schema_snapshot(collect_schema_snapshot(cursor))


def acquire_migration_lock(cursor: Any) -> None:
    cursor.execute(
        """
        select pg_advisory_xact_lock(
            hashtextextended(%s::text, 0::bigint)
        )
        """,
        (ADVISORY_LOCK_IDENTITY,),
    )


def _connect_and_run(
    *,
    mode: str,
    migration_sql: str,
    connect: Callable[[], Any],
    state: OperationState,
) -> tuple[dict[str, Any], dict[str, str]]:
    connection: Any = None
    preflight: PreflightResult | None = None
    try:
        state.stage = "connection"
        connection = connect()
        state.stage = "identity"
        with connection.cursor() as cursor:
            state.identity = read_database_identity(cursor)
            state.stage = "preflight"
            preflight = database_preflight(cursor)
            require_ready_preflight(preflight, stage=state.stage)

            if mode == "check-only":
                connection.rollback()
                return (
                    {
                        "status": "ready",
                        "mode": "check-only",
                        "commit_state": state.commit_state,
                        "preflight": {
                            "live_relations": "absent",
                            "dependencies": "present",
                        },
                    },
                    state.identity,
                )

            state.stage = "lock"
            acquire_migration_lock(cursor)
            state.stage = "locked_preflight"
            locked_preflight = database_preflight(cursor)
            require_ready_preflight(
                locked_preflight,
                stage=state.stage,
            )
            state.stage = "migration"
            cursor.execute(migration_sql)
            state.stage = "same_transaction_verification"
            failed_checks = verify_live_schema(cursor)
            if failed_checks:
                raise ApplicationFailure(
                    status="verification_failed",
                    stage=state.stage,
                    error_type=SchemaVerificationError.__name__,
                    failed_verification_checks=failed_checks,
                )
        state.stage = "commit"
        connection.commit()
        state.committed = True
    except ApplicationFailure:
        if connection is not None and not state.committed:
            connection.rollback()
        raise
    except Exception as exc:
        if connection is not None and not state.committed:
            try:
                connection.rollback()
            except Exception:
                pass
        raise ApplicationFailure(
            status="failed",
            stage=state.stage,
            error_type=type(exc).__name__,
            cause=exc,
        ) from None
    finally:
        if connection is not None:
            connection.close()

    second_connection: Any = None
    try:
        state.stage = "second_connection_verification"
        second_connection = connect()
        with second_connection.cursor() as cursor:
            failed_checks = verify_live_schema(cursor)
        second_connection.rollback()
        if failed_checks:
            raise ApplicationFailure(
                status="verification_failed",
                stage=state.stage,
                error_type=SchemaVerificationError.__name__,
                failed_verification_checks=failed_checks,
            )
    except ApplicationFailure:
        raise
    except Exception as exc:
        raise ApplicationFailure(
            status="failed",
            stage=state.stage,
            error_type=type(exc).__name__,
            cause=exc,
        ) from None
    finally:
        if second_connection is not None:
            second_connection.close()

    return (
        {
            "status": "applied",
            "mode": "apply",
            "commit_state": state.commit_state,
            "checks": {
                "hash_match": "pass",
                "preflight_absent": "pass",
                "advisory_lock": "pass",
                "same_transaction_schema": "pass",
                "commit": "pass",
                "second_connection_schema": "pass",
            },
        },
        state.identity,
    )


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_safe_evidence_parent(parent: Path) -> int:
    flags = _directory_open_flags()
    try:
        current_fd = os.open(parent.anchor, flags)
    except OSError as exc:
        raise UnsafeEvidencePath(
            "evidence root must be a real directory"
        ) from exc
    try:
        for part in parent.parts[1:]:
            try:
                next_fd = os.open(part, flags, dir_fd=current_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
                try:
                    next_fd = os.open(
                        part,
                        flags,
                        dir_fd=current_fd,
                    )
                except OSError as exc:
                    raise UnsafeEvidencePath(
                        "evidence parent must be a real directory"
                    ) from exc
            except OSError as exc:
                raise UnsafeEvidencePath(
                    "evidence parent must be a real directory"
                ) from exc
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _require_absent_evidence_destination(
    parent_fd: int,
    filename: str,
) -> None:
    try:
        os.stat(
            filename,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        raise UnsafeEvidencePath(
            "evidence destination could not be inspected"
        ) from exc
    raise EvidenceAlreadyExists(
        "evidence destination must not already exist"
    )


def ensure_safe_evidence_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    if not absolute.name:
        raise UnsafeEvidencePath(
            "evidence destination must name a file"
        )
    parent_fd = _open_safe_evidence_parent(absolute.parent)
    try:
        _require_absent_evidence_destination(
            parent_fd,
            absolute.name,
        )
    finally:
        os.close(parent_fd)
    return absolute


def write_evidence_atomically(path: Path, serialized: str) -> None:
    safe_path = ensure_safe_evidence_path(path)
    parent_fd = _open_safe_evidence_parent(safe_path.parent)
    temporary_name: str | None = None
    temporary_fd: int | None = None
    try:
        _require_absent_evidence_destination(
            parent_fd,
            safe_path.name,
        )
        for _attempt in range(16):
            temporary_name = (
                f".{safe_path.name}.{secrets.token_hex(8)}.tmp"
            )
            try:
                temporary_fd = os.open(
                    temporary_name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=parent_fd,
                )
                break
            except FileExistsError:
                temporary_name = None
        if temporary_fd is None or temporary_name is None:
            raise UnsafeEvidencePath(
                "could not reserve an evidence temporary file"
            )
        with os.fdopen(
            temporary_fd,
            mode="w",
            encoding="utf-8",
        ) as temporary:
            temporary_fd = None
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(
                temporary_name,
                safe_path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            raise EvidenceAlreadyExists(
                "evidence destination appeared during finalization"
            ) from None
    finally:
        if temporary_fd is not None:
            os.close(temporary_fd)
        if temporary_name is not None:
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)


def failure_payload(
    *,
    mode: str,
    migration_digest: str | None,
    stage: str,
    status: str,
    error_type: str,
    state: OperationState,
    cause: BaseException | None = None,
    present_relations: Sequence[str] = (),
    absent_relations: Sequence[str] = (),
    missing_dependencies: Sequence[str] = (),
    failed_verification_checks: Sequence[str] = (),
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "mode": mode,
        "migration_path": MIGRATION_DISPLAY_PATH,
        "migration_sha256": migration_digest,
        "failed_stage": stage,
        "error_type": error_type,
        "commit_state": state.commit_state,
    }
    sqlstate = safe_sqlstate(cause)
    if sqlstate:
        result["sqlstate"] = sqlstate
    if present_relations:
        result["present_relations"] = list(present_relations)
    if absent_relations:
        result["absent_relations"] = list(absent_relations)
    if missing_dependencies:
        result["missing_dependencies"] = list(missing_dependencies)
    if failed_verification_checks:
        result["failed_verification_checks"] = list(
            failed_verification_checks
        )
    return result


def _serialize(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _emit(
    payload: Mapping[str, Any],
    *,
    evidence_path: Path | None,
) -> None:
    serialized = _serialize(payload)
    if evidence_path is not None:
        write_evidence_atomically(evidence_path, serialized)
    sys.stdout.write(serialized)


def _emit_safely(
    payload: Mapping[str, Any],
    *,
    evidence_path: Path | None,
    mode: str,
    migration_digest: str | None,
    state: OperationState,
) -> bool:
    serialized = _serialize(payload)
    if evidence_path is not None:
        try:
            write_evidence_atomically(evidence_path, serialized)
        except Exception as exc:
            sys.stdout.write(
                _serialize(
                    failure_payload(
                        mode=mode,
                        migration_digest=migration_digest,
                        stage="evidence",
                        status="failed",
                        error_type=type(exc).__name__,
                        cause=exc,
                        state=state,
                    )
                )
            )
            return False
    sys.stdout.write(serialized)
    return True


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv if argv is not None else sys.argv[1:])
    mode = requested_mode(raw_argv)
    state = OperationState(stage="arguments")
    try:
        args = parse_args(raw_argv)
    except ArgumentContractError as exc:
        _emit_safely(
            failure_payload(
                mode=mode,
                migration_digest=None,
                stage="arguments",
                status="failed",
                error_type=type(exc).__name__,
                state=state,
            ),
            evidence_path=None,
            mode=mode,
            migration_digest=None,
            state=state,
        )
        return 2

    mode = "apply" if args.apply else "check-only"
    state.stage = "hash"
    try:
        raw_migration = migration_bytes()
    except Exception as exc:
        _emit_safely(
            failure_payload(
                mode=mode,
                migration_digest=None,
                stage="hash",
                status="failed",
                error_type=type(exc).__name__,
                state=state,
            ),
            evidence_path=None,
            mode=mode,
            migration_digest=None,
            state=state,
        )
        return 2
    digest = migration_sha256(raw_migration)
    if (
        digest != args.expected_sha256
        or args.expected_sha256 != REVIEWED_MIGRATION_SHA256
    ):
        _emit_safely(
            failure_payload(
                mode=mode,
                migration_digest=digest,
                stage="hash",
                status="failed",
                error_type=MigrationHashMismatch.__name__,
                state=state,
            ),
            evidence_path=None,
            mode=mode,
            migration_digest=digest,
            state=state,
        )
        return 2

    evidence_path: Path | None = None
    if args.evidence_out:
        state.stage = "evidence"
        try:
            evidence_path = ensure_safe_evidence_path(
                Path(args.evidence_out)
            )
        except Exception as exc:
            _emit_safely(
                failure_payload(
                    mode=mode,
                    migration_digest=digest,
                    stage="evidence",
                    status="failed",
                    error_type=type(exc).__name__,
                    state=state,
                ),
                evidence_path=None,
                mode=mode,
                migration_digest=digest,
                state=state,
            )
            return 2

    state.stage = "connection"
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        emitted = _emit_safely(
            failure_payload(
                mode=mode,
                migration_digest=digest,
                stage="connection",
                status="failed",
                error_type=MissingEnvironmentError.__name__,
                state=state,
            ),
            evidence_path=evidence_path,
            mode=mode,
            migration_digest=digest,
            state=state,
        )
        return 2 if emitted else 1

    try:
        import psycopg

        result, identity = _connect_and_run(
            mode=mode,
            migration_sql=raw_migration.decode("utf-8"),
            connect=lambda: psycopg.connect(
                db_url,
                autocommit=False,
            ),
            state=state,
        )
        result.update(
            {
                "migration_path": MIGRATION_DISPLAY_PATH,
                "migration_sha256": digest,
                "database": identity,
                "commit_state": state.commit_state,
            }
        )
    except ApplicationFailure as exc:
        result = failure_payload(
            mode=mode,
            migration_digest=digest,
            stage=exc.stage,
            status=exc.status,
            error_type=exc.error_type,
            state=state,
            cause=exc.cause,
            present_relations=exc.present_relations,
            absent_relations=exc.absent_relations,
            missing_dependencies=exc.missing_dependencies,
            failed_verification_checks=(
                exc.failed_verification_checks
            ),
        )
        _emit_safely(
            result,
            evidence_path=evidence_path,
            mode=mode,
            migration_digest=digest,
            state=state,
        )
        return 1
    except Exception as exc:
        result = failure_payload(
            mode=mode,
            migration_digest=digest,
            stage=state.stage,
            status="failed",
            error_type=type(exc).__name__,
            state=state,
            cause=exc,
        )
        _emit_safely(
            result,
            evidence_path=evidence_path,
            mode=mode,
            migration_digest=digest,
            state=state,
        )
        return 1

    emitted = _emit_safely(
        result,
        evidence_path=evidence_path,
        mode=mode,
        migration_digest=digest,
        state=state,
    )
    return 0 if emitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
