#!/usr/bin/env python3
"""Safely apply reviewed Phase 3 provider-evidence migrations 010 and 011.

This utility is intentionally fixed to exactly two reviewed migrations.
It does not accept arbitrary migration paths or SQL.

Application order:
    preflight
    advisory transaction lock
    locked preflight
    migration 010
    migration 011
    same-transaction schema verification
    commit
    second-connection schema verification
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]

MIGRATION_010_DISPLAY_PATH = (
    "db/migrations/phase3/010_cost_authority_semantics.sql"
)
MIGRATION_011_DISPLAY_PATH = (
    "db/migrations/phase3/011_provider_evidence_contract.sql"
)

MIGRATION_010_PATH = REPO_ROOT / MIGRATION_010_DISPLAY_PATH
MIGRATION_011_PATH = REPO_ROOT / MIGRATION_011_DISPLAY_PATH

REVIEWED_MIGRATION_010_SHA256 = (
    "20b87b8836fa76298d20349c69392fa03cc1df105849fea1bab9eecc6b5e9c45"
)
REVIEWED_MIGRATION_011_SHA256 = (
    "3d76c40b28e9aee8f8d99a1e73ac3d6411cf4cf1590b1fb750950321f613630b"
)

ADVISORY_LOCK_IDENTITY = (
    "cc-deepseek-bench|phase3|010_011_provider_evidence"
)

BASELINE_RELATIONS = (
    "benchmark.benchmark_trial_cost_coverage",
    "benchmark.benchmark_invalid_arm_runs",
    "benchmark.benchmark_arm_runs",
    "benchmark.benchmark_arms",
    "benchmark.benchmark_artifacts",
    "benchmark.benchmark_trials",
    "benchmark.v_trial_adjusted_cost_coverage",
    "benchmark.v_arm_adjusted_cost_coverage",
    "benchmark.v_arm_outcome_cost_breakdown",
    "benchmark.v_suite_adjusted_cost_frontier",
)

PROVIDER_EVIDENCE_RELATIONS = (
    "benchmark.benchmark_provider_evidence_sources",
    "benchmark.benchmark_provider_usage_evidence",
    "benchmark.benchmark_provider_pricing_snapshots",
    "benchmark.benchmark_provider_cost_evidence",
    "benchmark.benchmark_usage_reconciliations",
    "benchmark.benchmark_usage_reconciliation_sources",
    "benchmark.benchmark_cost_reconciliations",
    "benchmark.benchmark_cost_reconciliation_sources",
    "benchmark.benchmark_evidence_promotion_gates",
    "benchmark.v_evidence_promotion_gate",
)

PROVIDER_EVIDENCE_INDEXES = (
    "benchmark.idx_provider_evidence_source_sha256",
    "benchmark.idx_provider_evidence_source_provider",
    "benchmark.idx_provider_usage_request_identity",
    "benchmark.idx_provider_usage_arm_run",
    "benchmark.idx_provider_usage_trial",
    "benchmark.idx_provider_pricing_model",
    "benchmark.idx_provider_cost_arm_run",
    "benchmark.idx_provider_cost_trial",
    "benchmark.idx_usage_reconciliation_current",
    "benchmark.idx_cost_reconciliation_current",
    "benchmark.idx_evidence_promotion_gate_current",
)


PROVIDER_EVIDENCE_INDEX_TABLES: Mapping[str, str] = {
    "benchmark.idx_provider_evidence_source_sha256": (
        "benchmark.benchmark_provider_evidence_sources"
    ),
    "benchmark.idx_provider_evidence_source_provider": (
        "benchmark.benchmark_provider_evidence_sources"
    ),
    "benchmark.idx_provider_usage_request_identity": (
        "benchmark.benchmark_provider_usage_evidence"
    ),
    "benchmark.idx_provider_usage_arm_run": (
        "benchmark.benchmark_provider_usage_evidence"
    ),
    "benchmark.idx_provider_usage_trial": (
        "benchmark.benchmark_provider_usage_evidence"
    ),
    "benchmark.idx_provider_pricing_model": (
        "benchmark.benchmark_provider_pricing_snapshots"
    ),
    "benchmark.idx_provider_cost_arm_run": (
        "benchmark.benchmark_provider_cost_evidence"
    ),
    "benchmark.idx_provider_cost_trial": (
        "benchmark.benchmark_provider_cost_evidence"
    ),
    "benchmark.idx_usage_reconciliation_current": (
        "benchmark.benchmark_usage_reconciliations"
    ),
    "benchmark.idx_cost_reconciliation_current": (
        "benchmark.benchmark_cost_reconciliations"
    ),
    "benchmark.idx_evidence_promotion_gate_current": (
        "benchmark.benchmark_evidence_promotion_gates"
    ),
}


ESSENTIAL_COLUMNS: Mapping[str, frozenset[str]] = {
    "v_trial_adjusted_cost_coverage": frozenset(
        {
            "has_adjusted_cost",
            "known_accounting_gap_usd",
        }
    ),
    "v_arm_adjusted_cost_coverage": frozenset(
        {
            "adjusted_known_cost_usd",
            "known_accounting_gap_usd",
            "unresolved_cost_count",
        }
    ),
    "v_arm_outcome_cost_breakdown": frozenset(
        {
            "adjusted_known_cost_usd",
            "known_accounting_gap_usd",
        }
    ),
    "benchmark_provider_evidence_sources": frozenset(
        {
            "provider",
            "source_uri",
            "provider_reference",
            "source_sha256",
            "integrity_status",
        }
    ),
    "benchmark_provider_usage_evidence": frozenset(
        {
            "ordinary_input_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "output_tokens",
            "request_count",
            "allocation_scope",
            "completeness_status",
        }
    ),
    "benchmark_provider_pricing_snapshots": frozenset(
        {
            "provider",
            "provider_model",
            "pricing_semantics",
            "pricing_rules",
        }
    ),
    "benchmark_provider_cost_evidence": frozenset(
        {
            "cost_kind",
            "amount_usd",
            "allocation_scope",
            "completeness_status",
        }
    ),
    "benchmark_usage_reconciliations": frozenset(
        {
            "arm_run_id",
            "is_current",
            "provider_evidence_visible",
            "selected_usage_authority",
            "validation_status",
            "limitation_codes",
        }
    ),
    "benchmark_cost_reconciliations": frozenset(
        {
            "arm_run_id",
            "is_current",
            "provider_evidence_visible",
            "selected_cost_usd",
            "selected_cost_basis",
            "selected_cost_relation",
            "validation_status",
            "limitation_codes",
        }
    ),
    "benchmark_evidence_promotion_gates": frozenset(
        {
            "source_arm_run_id",
            "source_mode",
            "target_mode",
            "usage_reconciliation_id",
            "cost_reconciliation_id",
            "decision",
            "blocker_codes",
            "is_current",
        }
    ),
    "v_evidence_promotion_gate": frozenset(
        {
            "derived_blocker_codes",
            "effective_can_advance",
            "usage_reconciliation_is_current",
            "cost_reconciliation_is_current",
        }
    ),
}


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


class ExistingProviderEvidenceSchemaError(RuntimeError):
    pass


class PartialProviderEvidenceSchemaError(RuntimeError):
    pass


class ProviderEvidenceIndexCollisionError(RuntimeError):
    pass


class MissingBaselineDependencyError(RuntimeError):
    pass


class SchemaVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightResult:
    provider_schema_state: str
    present_provider_relations: tuple[str, ...]
    absent_provider_relations: tuple[str, ...]
    missing_baseline_relations: tuple[str, ...]
    present_provider_indexes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaSnapshot:
    baseline_relations: frozenset[str]
    provider_relations: frozenset[str]
    provider_indexes: frozenset[str]
    columns: frozenset[tuple[str, str]]
    provider_index_bindings: frozenset[
        tuple[str, str]
    ] = frozenset()


@dataclass
class OperationState:
    stage: str
    committed: bool = False
    identity: dict[str, str] | None = None

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
        cause: BaseException | None = None,
        present_relations: Sequence[str] = (),
        absent_relations: Sequence[str] = (),
        missing_dependencies: Sequence[str] = (),
        failed_verification_checks: Sequence[str] = (),
        conflicting_indexes: Sequence[str] = (),
    ) -> None:
        super().__init__(status)
        self.status = status
        self.stage = stage
        self.error_type = error_type
        self.cause = cause
        self.present_relations = tuple(present_relations)
        self.absent_relations = tuple(absent_relations)
        self.missing_dependencies = tuple(missing_dependencies)
        self.failed_verification_checks = tuple(
            failed_verification_checks
        )
        self.conflicting_indexes = tuple(conflicting_indexes)


def _sha256_argument(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64:
        raise argparse.ArgumentTypeError(
            "expected SHA-256 must contain exactly 64 hexadecimal characters"
        )
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "expected SHA-256 must be hexadecimal"
        ) from exc
    return normalized


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--expected-010-sha256",
        required=True,
        type=_sha256_argument,
    )
    parser.add_argument(
        "--expected-011-sha256",
        required=True,
        type=_sha256_argument,
    )
    parser.add_argument("--evidence-out")
    return parser.parse_args(argv)


def requested_mode(argv: Sequence[str]) -> str:
    return "apply" if "--apply" in argv else "check-only"


def migration_bytes(path: Path) -> bytes:
    return path.read_bytes()


def migration_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_reviewed_hashes(
    raw_010: bytes,
    raw_011: bytes,
    *,
    expected_010: str,
    expected_011: str,
) -> tuple[str, str]:
    digest_010 = migration_sha256(raw_010)
    digest_011 = migration_sha256(raw_011)

    if (
        digest_010 != expected_010
        or expected_010 != REVIEWED_MIGRATION_010_SHA256
        or digest_011 != expected_011
        or expected_011 != REVIEWED_MIGRATION_011_SHA256
    ):
        raise MigrationHashMismatch(
            "migration bytes do not match the reviewed hash pins"
        )

    return digest_010, digest_011


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


def classify_provider_relations(
    present_relations: Sequence[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    present_set = set(present_relations)
    present = tuple(
        relation
        for relation in PROVIDER_EVIDENCE_RELATIONS
        if relation in present_set
    )
    absent = tuple(
        relation
        for relation in PROVIDER_EVIDENCE_RELATIONS
        if relation not in present_set
    )

    if not present:
        state = "absent"
    elif not absent:
        state = "present"
    else:
        state = "partial"

    return state, present, absent


def database_preflight(cursor: Any) -> PreflightResult:
    present_provider = relation_presence(
        cursor,
        PROVIDER_EVIDENCE_RELATIONS,
    )
    provider_state, present, absent = classify_provider_relations(
        present_provider
    )

    present_baseline = set(
        relation_presence(cursor, BASELINE_RELATIONS)
    )
    missing_baseline = tuple(
        relation
        for relation in BASELINE_RELATIONS
        if relation not in present_baseline
    )

    present_provider_indexes = relation_presence(
        cursor,
        PROVIDER_EVIDENCE_INDEXES,
    )

    return PreflightResult(
        provider_schema_state=provider_state,
        present_provider_relations=present,
        absent_provider_relations=absent,
        missing_baseline_relations=missing_baseline,
        present_provider_indexes=present_provider_indexes,
    )


def require_ready_preflight(
    result: PreflightResult,
    *,
    stage: str,
) -> None:
    if result.provider_schema_state == "present":
        raise ApplicationFailure(
            status="already_present",
            stage=stage,
            error_type=ExistingProviderEvidenceSchemaError.__name__,
            present_relations=result.present_provider_relations,
            absent_relations=result.absent_provider_relations,
            missing_dependencies=result.missing_baseline_relations,
        )

    if result.provider_schema_state == "partial":
        raise ApplicationFailure(
            status="partial_schema",
            stage=stage,
            error_type=PartialProviderEvidenceSchemaError.__name__,
            present_relations=result.present_provider_relations,
            absent_relations=result.absent_provider_relations,
            missing_dependencies=result.missing_baseline_relations,
        )

    if result.present_provider_indexes:
        raise ApplicationFailure(
            status="index_collision",
            stage=stage,
            error_type=ProviderEvidenceIndexCollisionError.__name__,
            present_relations=result.present_provider_relations,
            absent_relations=result.absent_provider_relations,
            missing_dependencies=result.missing_baseline_relations,
            conflicting_indexes=result.present_provider_indexes,
        )

    if result.missing_baseline_relations:
        raise ApplicationFailure(
            status="missing_dependencies",
            stage=stage,
            error_type=MissingBaselineDependencyError.__name__,
            present_relations=result.present_provider_relations,
            absent_relations=result.absent_provider_relations,
            missing_dependencies=result.missing_baseline_relations,
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
    baseline = frozenset(
        relation_presence(cursor, BASELINE_RELATIONS)
    )
    provider = frozenset(
        relation_presence(cursor, PROVIDER_EVIDENCE_RELATIONS)
    )
    provider_index_names = [
        relation.rsplit(".", 1)[-1]
        for relation in PROVIDER_EVIDENCE_INDEXES
    ]
    cursor.execute(
        """
        select
            index_class.relname,
            table_class.relname,
            index_catalog.indisvalid
        from pg_catalog.pg_index index_catalog
        join pg_catalog.pg_class index_class
          on index_class.oid = index_catalog.indexrelid
        join pg_catalog.pg_namespace index_namespace
          on index_namespace.oid = index_class.relnamespace
        join pg_catalog.pg_class table_class
          on table_class.oid = index_catalog.indrelid
        join pg_catalog.pg_namespace table_namespace
          on table_namespace.oid = table_class.relnamespace
        where index_namespace.nspname = 'benchmark'
          and table_namespace.nspname = 'benchmark'
          and index_class.relname = any(%s::text[])
        order by index_class.relname
        """,
        (provider_index_names,),
    )
    index_rows = tuple(cursor.fetchall())

    indexes = frozenset(
        f"benchmark.{index_name}"
        for index_name, _table_name, is_valid in index_rows
        if is_valid
    )
    index_bindings = frozenset(
        (
            f"benchmark.{index_name}",
            f"benchmark.{table_name}",
        )
        for index_name, table_name, is_valid in index_rows
        if is_valid
    )

    relevant_table_names = sorted(ESSENTIAL_COLUMNS)
    cursor.execute(
        """
        select table_name, column_name
        from information_schema.columns
        where table_schema = 'benchmark'
          and table_name = any(%s::text[])
        order by table_name, ordinal_position
        """,
        (relevant_table_names,),
    )
    columns = frozenset(
        (str(table_name), str(column_name))
        for table_name, column_name in cursor.fetchall()
    )

    return SchemaSnapshot(
        baseline_relations=baseline,
        provider_relations=provider,
        provider_indexes=indexes,
        columns=columns,
        provider_index_bindings=index_bindings,
    )


def verify_schema_snapshot(snapshot: SchemaSnapshot) -> list[str]:
    failed: list[str] = []

    if snapshot.baseline_relations != frozenset(BASELINE_RELATIONS):
        failed.append("baseline_relations")

    if snapshot.provider_relations != frozenset(
        PROVIDER_EVIDENCE_RELATIONS
    ):
        failed.append("provider_evidence_relations")

    if snapshot.provider_indexes != frozenset(
        PROVIDER_EVIDENCE_INDEXES
    ):
        failed.append("provider_evidence_indexes")

    expected_index_bindings = frozenset(
        PROVIDER_EVIDENCE_INDEX_TABLES.items()
    )
    if snapshot.provider_index_bindings != expected_index_bindings:
        failed.append("provider_evidence_index_bindings")

    for table_name, required_columns in ESSENTIAL_COLUMNS.items():
        actual = {
            column_name
            for candidate_table, column_name in snapshot.columns
            if candidate_table == table_name
        }
        if not required_columns.issubset(actual):
            failed.append(f"essential_columns_{table_name}")

    return failed


def verify_provider_evidence_schema(cursor: Any) -> list[str]:
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
    migration_010_sql: str,
    migration_011_sql: str,
    connect: Callable[[], Any],
    state: OperationState,
) -> tuple[dict[str, Any], dict[str, str]]:
    connection: Any = None

    try:
        state.stage = "connection"
        connection = connect()

        state.stage = "identity"
        with connection.cursor() as cursor:
            state.identity = read_database_identity(cursor)

            state.stage = "preflight"
            preflight = database_preflight(cursor)
            require_ready_preflight(
                preflight,
                stage=state.stage,
            )

            if mode == "check-only":
                connection.rollback()
                return (
                    {
                        "status": "ready",
                        "mode": "check-only",
                        "commit_state": state.commit_state,
                        "preflight": {
                            "baseline": "present",
                            "provider_evidence_schema": "absent",
                            "provider_evidence_indexes": "absent",
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

            state.stage = "migration_010"
            cursor.execute(migration_010_sql)

            state.stage = "migration_011"
            cursor.execute(migration_011_sql)

            state.stage = "same_transaction_verification"
            failed_checks = verify_provider_evidence_schema(cursor)
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
            failed_checks = verify_provider_evidence_schema(cursor)
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
                "baseline_preflight": "pass",
                "provider_schema_absent": "pass",
                "provider_index_collision_absent": "pass",
                "advisory_lock": "pass",
                "locked_preflight": "pass",
                "migration_010": "pass",
                "migration_011": "pass",
                "same_transaction_schema": "pass",
                "commit": "pass",
                "second_connection_schema": "pass",
            },
        },
        state.identity or {},
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
                next_fd = os.open(
                    part,
                    flags,
                    dir_fd=current_fd,
                )
            except FileNotFoundError:
                try:
                    os.mkdir(
                        part,
                        mode=0o700,
                        dir_fd=current_fd,
                    )
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


def write_evidence_atomically(
    path: Path,
    serialized: str,
) -> None:
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
                os.unlink(
                    temporary_name,
                    dir_fd=parent_fd,
                )
            except FileNotFoundError:
                pass

        os.close(parent_fd)


def failure_payload(
    *,
    mode: str,
    digest_010: str | None,
    digest_011: str | None,
    stage: str,
    status: str,
    error_type: str,
    state: OperationState,
    cause: BaseException | None = None,
    present_relations: Sequence[str] = (),
    absent_relations: Sequence[str] = (),
    missing_dependencies: Sequence[str] = (),
    failed_verification_checks: Sequence[str] = (),
    conflicting_indexes: Sequence[str] = (),
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "mode": mode,
        "migration_010_path": MIGRATION_010_DISPLAY_PATH,
        "migration_010_sha256": digest_010,
        "migration_011_path": MIGRATION_011_DISPLAY_PATH,
        "migration_011_sha256": digest_011,
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
        result["missing_dependencies"] = list(
            missing_dependencies
        )

    if failed_verification_checks:
        result["failed_verification_checks"] = list(
            failed_verification_checks
        )

    if conflicting_indexes:
        result["conflicting_indexes"] = list(
            conflicting_indexes
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
        write_evidence_atomically(
            evidence_path,
            serialized,
        )
    sys.stdout.write(serialized)


def _emit_safely(
    payload: Mapping[str, Any],
    *,
    evidence_path: Path | None,
    mode: str,
    digest_010: str | None,
    digest_011: str | None,
    state: OperationState,
) -> bool:
    serialized = _serialize(payload)

    if evidence_path is not None:
        try:
            write_evidence_atomically(
                evidence_path,
                serialized,
            )
        except Exception as exc:
            sys.stdout.write(
                _serialize(
                    failure_payload(
                        mode=mode,
                        digest_010=digest_010,
                        digest_011=digest_011,
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
    raw_argv = list(
        argv if argv is not None else sys.argv[1:]
    )
    mode = requested_mode(raw_argv)
    state = OperationState(stage="arguments")

    try:
        args = parse_args(raw_argv)
    except ArgumentContractError as exc:
        _emit_safely(
            failure_payload(
                mode=mode,
                digest_010=None,
                digest_011=None,
                stage="arguments",
                status="failed",
                error_type=type(exc).__name__,
                state=state,
            ),
            evidence_path=None,
            mode=mode,
            digest_010=None,
            digest_011=None,
            state=state,
        )
        return 2

    mode = "apply" if args.apply else "check-only"

    state.stage = "hash"
    try:
        raw_010 = migration_bytes(MIGRATION_010_PATH)
        raw_011 = migration_bytes(MIGRATION_011_PATH)
        digest_010, digest_011 = require_reviewed_hashes(
            raw_010,
            raw_011,
            expected_010=args.expected_010_sha256,
            expected_011=args.expected_011_sha256,
        )
    except Exception as exc:
        actual_010 = None
        actual_011 = None
        try:
            actual_010 = migration_sha256(
                migration_bytes(MIGRATION_010_PATH)
            )
        except Exception:
            pass
        try:
            actual_011 = migration_sha256(
                migration_bytes(MIGRATION_011_PATH)
            )
        except Exception:
            pass

        _emit_safely(
            failure_payload(
                mode=mode,
                digest_010=actual_010,
                digest_011=actual_011,
                stage="hash",
                status="failed",
                error_type=type(exc).__name__,
                state=state,
            ),
            evidence_path=None,
            mode=mode,
            digest_010=actual_010,
            digest_011=actual_011,
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
                    digest_010=digest_010,
                    digest_011=digest_011,
                    stage="evidence",
                    status="failed",
                    error_type=type(exc).__name__,
                    state=state,
                ),
                evidence_path=None,
                mode=mode,
                digest_010=digest_010,
                digest_011=digest_011,
                state=state,
            )
            return 2

    state.stage = "connection"
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        emitted = _emit_safely(
            failure_payload(
                mode=mode,
                digest_010=digest_010,
                digest_011=digest_011,
                stage="connection",
                status="failed",
                error_type=MissingEnvironmentError.__name__,
                state=state,
            ),
            evidence_path=evidence_path,
            mode=mode,
            digest_010=digest_010,
            digest_011=digest_011,
            state=state,
        )
        return 2 if emitted else 1

    try:
        import psycopg

        result, identity = _connect_and_run(
            mode=mode,
            migration_010_sql=raw_010.decode("utf-8"),
            migration_011_sql=raw_011.decode("utf-8"),
            connect=lambda: psycopg.connect(
                db_url,
                autocommit=False,
            ),
            state=state,
        )

        result.update(
            {
                "migration_010_path": (
                    MIGRATION_010_DISPLAY_PATH
                ),
                "migration_010_sha256": digest_010,
                "migration_011_path": (
                    MIGRATION_011_DISPLAY_PATH
                ),
                "migration_011_sha256": digest_011,
                "database": identity,
                "commit_state": state.commit_state,
            }
        )

    except ApplicationFailure as exc:
        result = failure_payload(
            mode=mode,
            digest_010=digest_010,
            digest_011=digest_011,
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
            conflicting_indexes=exc.conflicting_indexes,
        )
        _emit_safely(
            result,
            evidence_path=evidence_path,
            mode=mode,
            digest_010=digest_010,
            digest_011=digest_011,
            state=state,
        )
        return 1

    except Exception as exc:
        result = failure_payload(
            mode=mode,
            digest_010=digest_010,
            digest_011=digest_011,
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
            digest_010=digest_010,
            digest_011=digest_011,
            state=state,
        )
        return 1

    emitted = _emit_safely(
        result,
        evidence_path=evidence_path,
        mode=mode,
        digest_010=digest_010,
        digest_011=digest_011,
        state=state,
    )
    return 0 if emitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
