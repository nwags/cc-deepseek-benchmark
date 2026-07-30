#!/usr/bin/env python3
"""Exercise live supervision against PostgreSQL without persisting migration 009."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_phase3_run_metadata import insert_manifest_into_postgres
from scripts.lib.canonical_publication import (
    CanonicalVerificationError,
    publish_manifest_transactionally,
)
from scripts.lib.live_verification import (
    ExistingCanonicalPublication,
    inspect_completed_publication_with_cursor,
    update_live_run_publication_with_cursor,
    verify_canonical_publication_with_cursor,
)
from scripts.lib.publication_fingerprint import publication_fingerprint


MIGRATION_PATH = Path("db/migrations/phase3/009_live_run_supervision.sql")
LIVE_TABLES = (
    "benchmark.live_runs",
    "benchmark.live_run_events",
    "benchmark.live_trials",
    "benchmark.live_artifacts",
)


class IntegrationSafetyError(RuntimeError):
    pass


class MissingEnvironmentError(RuntimeError):
    pass


class StagedIntegrationError(RuntimeError):
    def __init__(self, stage: str, cause: BaseException) -> None:
        super().__init__(stage)
        self.stage = stage
        self.cause = cause


@dataclass
class IntegrationDiagnostics:
    current_stage: str = "preflight"
    zero_persistence_counts: dict[str, int] = field(default_factory=dict)

    def enter(self, stage: str) -> None:
        self.current_stage = stage

    def record_counts(
        self,
        prefix: str,
        counts: Mapping[str, int],
    ) -> None:
        self.zero_persistence_counts.update(
            {f"{prefix}_{key}": value for key, value in counts.items()}
        )


def safe_sqlstate(exc: BaseException) -> str | None:
    value = getattr(exc, "sqlstate", None)
    if value is None:
        value = getattr(getattr(exc, "diag", None), "sqlstate", None)
    text = str(value or "")
    if len(text) == 5 and text.isalnum():
        return text.upper()
    return None


def failure_result(
    *,
    migration_digest: str,
    failed_stage: str,
    exc: BaseException,
    zero_persistence_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "migration_sha256": migration_digest,
        "status": "failed",
        "failed_stage": failed_stage,
        "error_type": type(exc).__name__,
        "zero_persistence_counts": dict(zero_persistence_counts or {}),
    }
    sqlstate = safe_sqlstate(exc)
    if sqlstate:
        result["sqlstate"] = sqlstate
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rollback-only",
        action="store_true",
        help="Required safety acknowledgement; every transaction is rolled back.",
    )
    args = parser.parse_args(argv)
    if not args.rollback_only:
        parser.error("--rollback-only is required")
    return args


def migration_sha256(path: Path | None = None) -> str:
    path = path or MIGRATION_PATH
    return hashlib.sha256(path.read_bytes()).hexdigest()


def permanently_present_live_tables(connection: Any) -> tuple[str, ...]:
    present: list[str] = []
    with connection.cursor() as cursor:
        for relation in LIVE_TABLES:
            cursor.execute("select to_regclass(%s)", (relation,))
            if cursor.fetchone()[0] is not None:
                present.append(relation)
    return tuple(present)


def assert_migration_not_permanently_applied(connection: Any) -> None:
    present = permanently_present_live_tables(connection)
    if present:
        raise IntegrationSafetyError(
            "migration 009 already appears permanently applied"
        )


def synthetic_manifest(token: str) -> dict[str, Any]:
    arm_id = f"live-supervision-integration-{token}"
    run_label = f"{arm_id}/rollback-only"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run": {
            "phase": "live-supervision-integration",
            "logical_mode": "ad-hoc",
            "storage_mode": "ad-hoc",
            "suite_id": f"live-supervision-integration-{token}",
            "arm_id": arm_id,
            "run_label": run_label,
            "run_timestamp": "rollback-only",
            "run_dir": f".run/integration/{token}",
            "github_run_id": f"rollback-only-{token}",
            "github_run_attempt": 1,
            "execution_scoped": True,
            "status": "completed",
            "started_at": "2000-01-01T00:00:00Z",
            "finished_at": "2000-01-01T00:00:01Z",
            "n_total_trials": 1,
            "n_completed_trials": 1,
            "n_errored_trials": 0,
            "cost_usd": 0,
            "input_tokens": 0,
            "cache_tokens": 0,
            "output_tokens": 0,
        },
        "trials": [
            {
                "trial_name": "synthetic-task__attempt-1",
                "task_name": "synthetic-task",
                "attempt_index": 1,
                "trial_dir": (
                    f".run/integration/{token}/"
                    "synthetic-task__attempt-1"
                ),
                "raw_result_path": (
                    f".run/integration/{token}/"
                    "synthetic-task__attempt-1/result.json"
                ),
                "reward": 1,
                "status": "completed",
                "started_at": "2000-01-01T00:00:00Z",
                "finished_at": "2000-01-01T00:00:01Z",
                "runtime_seconds": 1,
                "cost_usd": 0,
                "input_tokens": 0,
                "cache_tokens": 0,
                "output_tokens": 0,
            }
        ],
        "artifacts": [
            {
                "artifact_type": "trial_result",
                "local_path": (
                    f".run/integration/{token}/"
                    "synthetic-task__attempt-1/result.json"
                ),
                "sha256": hashlib.sha256(b"{}").hexdigest(),
                "size_bytes": 2,
                "r2_uri": None,
                "r2_key": None,
            }
        ],
    }
    manifest["run"]["publication_fingerprint"] = publication_fingerprint(
        manifest
    )
    return manifest


def insert_synthetic_live_run(
    connection: Any,
    *,
    live_run_id: str,
    manifest: Mapping[str, Any],
) -> None:
    run = manifest["run"]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into benchmark.live_runs (
                live_run_id, github_run_id, github_run_attempt, github_job,
                runner_name, workspace_name, workspace_fingerprint, arm_id,
                phase, mode, run_kind, scored, status, benchmark_status,
                live_publication_status, progressive_artifact_status,
                canonical_publication_status, expected_trial_count,
                completed_trial_count, success_count, failure_count,
                exception_count, started_at, finished_at, returncode,
                latest_message, raw_metadata
            ) values (
                %s, %s, %s, 'rollback-only', 'rollback-only-runner',
                'rollback-only', 'rollback-only', %s, %s, %s,
                'integration', false, 'completed', 'completed', 'completed',
                'disabled', 'pending', 1, 1, 1, 0, 0,
                %s, %s, 0, 'Synthetic rollback-only execution', '{}'::jsonb
            )
            """,
            (
                live_run_id,
                run["github_run_id"],
                run["github_run_attempt"],
                run["arm_id"],
                run["phase"],
                run["logical_mode"],
                run["started_at"],
                run["finished_at"],
            ),
        )


class RollbackOnlyAdapter:
    """Use production helpers while suppressing success-path commit."""

    def __init__(
        self,
        connection: Any,
        *,
        force_verification_failure: bool = False,
        rollback_stage: str | None = None,
    ) -> None:
        self.connection = connection
        self.force_verification_failure = force_verification_failure
        self.rollback_stage = rollback_stage
        self.commit_requested = False
        self.rollback_requested = False
        self.close_requested = False

    def insert_manifest(self, manifest: dict[str, Any]) -> dict[str, str]:
        return insert_manifest_into_postgres(
            manifest,
            connection=self.connection,
        )

    def lock_publication_identity(
        self,
        manifest: Mapping[str, Any],
    ) -> None:
        run = manifest["run"]
        identity = "|".join(
            str(run.get(field) or "")
            for field in (
                "phase",
                "storage_mode",
                "run_label",
                "arm_id",
                "github_run_id",
                "github_run_attempt",
            )
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (identity,),
            )

    def transition_live_run(self, **kwargs: Any) -> str:
        with self.connection.cursor() as cursor:
            return update_live_run_publication_with_cursor(cursor, **kwargs)

    def inspect_completed(
        self,
        **kwargs: Any,
    ) -> ExistingCanonicalPublication | None:
        with self.connection.cursor() as cursor:
            return inspect_completed_publication_with_cursor(cursor, **kwargs)

    def verify(self, **kwargs: Any) -> dict[str, Any]:
        with self.connection.cursor() as cursor:
            result = verify_canonical_publication_with_cursor(cursor, **kwargs)
        if self.force_verification_failure:
            return {
                **result,
                "ok": False,
                "errors": [
                    *result.get("errors", []),
                    "forced rollback-only verification failure",
                ],
            }
        return result

    def commit(self) -> None:
        self.commit_requested = True

    def rollback(self) -> None:
        self.rollback_requested = True
        try:
            self.connection.rollback()
        except Exception as exc:
            if self.rollback_stage:
                raise StagedIntegrationError(
                    self.rollback_stage,
                    exc,
                ) from None
            raise

    def close(self) -> None:
        self.close_requested = True


def classification_checks(
    connection: Any,
    *,
    manifest: dict[str, Any],
    ids: Mapping[str, str],
    live_run_id: str,
) -> tuple[str, str, str]:
    fingerprint = str(manifest["run"]["publication_fingerprint"])
    with connection.cursor() as cursor:
        valid = verify_canonical_publication_with_cursor(
            cursor,
            manifest=manifest,
            run_id=ids["run_id"],
            arm_run_id=ids["arm_run_id"],
            live_run_id=live_run_id,
            require_r2=False,
            r2_integrity_verified=False,
        )
        cursor.execute(
            """
            insert into benchmark.benchmark_invalid_arm_runs (
                suite_id, arm_id, run_label, reason, invalidated_by
            ) values (%s, %s, %s, 'rollback-only', 'rollback-only')
            """,
            (
                manifest["run"]["suite_id"],
                manifest["run"]["arm_id"],
                manifest["run"]["run_label"],
            ),
        )
        invalid = verify_canonical_publication_with_cursor(
            cursor,
            manifest=manifest,
            run_id=ids["run_id"],
            arm_run_id=ids["arm_run_id"],
            live_run_id=live_run_id,
            require_r2=False,
            r2_integrity_verified=False,
        )
        cursor.execute(
            "delete from benchmark.benchmark_invalid_arm_runs "
            "where suite_id = %s and arm_id = %s and run_label = %s",
            (
                manifest["run"]["suite_id"],
                manifest["run"]["arm_id"],
                manifest["run"]["run_label"],
            ),
        )
        cursor.execute(
            "update benchmark.benchmark_arm_runs set suite_id = null "
            "where id = %s::uuid",
            (ids["arm_run_id"],),
        )
        unclassified_manifest = deepcopy(manifest)
        unclassified_manifest["run"]["suite_id"] = None
        unclassified_manifest["run"]["publication_fingerprint"] = fingerprint
        unclassified = verify_canonical_publication_with_cursor(
            cursor,
            manifest=unclassified_manifest,
            run_id=ids["run_id"],
            arm_run_id=ids["arm_run_id"],
            live_run_id=live_run_id,
            require_r2=False,
            r2_integrity_verified=False,
        )
    states = (
        str(valid["suite_classification"]),
        str(invalid["suite_classification"]),
        str(unclassified["suite_classification"]),
    )
    if states != ("valid", "invalid", "unclassified"):
        raise IntegrationSafetyError("classification visibility checks failed")
    if not valid["ok"] or not invalid["ok"] or not unclassified["ok"]:
        raise IntegrationSafetyError("canonical visibility checks failed")
    return states


def persistence_counts(
    connection: Any,
    *,
    manifest: Mapping[str, Any],
    live_run_id: str,
) -> dict[str, int]:
    run = manifest["run"]
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        live_tables_present = 0
        for relation in LIVE_TABLES:
            cursor.execute("select to_regclass(%s)", (relation,))
            exists = cursor.fetchone()[0] is not None
            key = relation.rsplit(".", 1)[-1]
            if not exists:
                counts[key] = 0
                continue
            live_tables_present += 1
            if relation == "benchmark.live_runs":
                cursor.execute(
                    "select count(*) from benchmark.live_runs "
                    "where live_run_id = %s",
                    (live_run_id,),
                )
            else:
                cursor.execute(
                    f"select count(*) from {relation} where live_run_id = %s",
                    (live_run_id,),
                )
            counts[key] = int(cursor.fetchone()[0])
        counts["live_tables_present"] = live_tables_present
        cursor.execute(
            "select count(*) from benchmark.benchmark_runs "
            "where phase = %s and mode = %s and run_label = %s",
            (
                run["phase"],
                run["storage_mode"],
                run["run_label"],
            ),
        )
        counts["canonical_runs"] = int(cursor.fetchone()[0])
        cursor.execute(
            "select count(*) from benchmark.benchmark_arms where arm_id = %s",
            (run["arm_id"],),
        )
        counts["canonical_arms"] = int(cursor.fetchone()[0])
        cursor.execute(
            "select count(*) from benchmark.benchmark_trials "
            "where arm_id = %s",
            (run["arm_id"],),
        )
        counts["canonical_trials"] = int(cursor.fetchone()[0])
        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_artifacts artifact
            join benchmark.benchmark_runs run on run.id = artifact.run_id
            where run.phase = %s and run.run_label = %s
            """,
            (run["phase"], run["run_label"]),
        )
        counts["canonical_artifacts"] = int(cursor.fetchone()[0])
    return counts


def execute_migration(connection: Any, path: Path | None = None) -> None:
    path = path or MIGRATION_PATH
    with connection.cursor() as cursor:
        cursor.execute(path.read_text(encoding="utf-8"))


def run_success_path(
    db_url: str,
    token: str,
    diagnostics: IntegrationDiagnostics,
) -> tuple[dict[str, int], tuple[str, ...]]:
    import psycopg

    manifest = synthetic_manifest(token)
    live_run_id = f"rollback-only-live-{token}"
    connection: Any = None
    try:
        diagnostics.enter("success_migration")
        connection = psycopg.connect(db_url)
        execute_migration(connection)
        diagnostics.enter("success_publication")
        insert_synthetic_live_run(
            connection,
            live_run_id=live_run_id,
            manifest=manifest,
        )
        adapter = RollbackOnlyAdapter(
            connection,
            rollback_stage="success_rollback",
        )
        ids, verification, status = publish_manifest_transactionally(
            adapter,
            manifest=manifest,
            live_run_id=live_run_id,
            verify=True,
            require_r2=False,
            r2_integrity_verified=False,
            publication_fingerprint=str(
                manifest["run"]["publication_fingerprint"]
            ),
        )
        if (
            status != "completed"
            or not verification
            or not verification["ok"]
            or not adapter.commit_requested
        ):
            raise IntegrationSafetyError(
                "successful application publication did not request commit"
            )
        diagnostics.enter("success_classification")
        classifications = classification_checks(
            connection,
            manifest=manifest,
            ids=ids,
            live_run_id=live_run_id,
        )
        diagnostics.enter("success_rollback")
        connection.rollback()
    finally:
        if connection is not None:
            connection.close()
    diagnostics.enter("success_second_connection")
    with psycopg.connect(db_url) as observer:
        counts = persistence_counts(
            observer,
            manifest=manifest,
            live_run_id=live_run_id,
        )
    diagnostics.record_counts("success", counts)
    if any(counts.values()):
        raise IntegrationSafetyError(
            "successful rollback-only path left persistent rows"
        )
    return counts, classifications


def run_forced_failure_path(
    db_url: str,
    token: str,
    diagnostics: IntegrationDiagnostics,
) -> dict[str, int]:
    import psycopg

    manifest = synthetic_manifest(token)
    live_run_id = f"rollback-only-live-{token}"
    connection: Any = None
    try:
        diagnostics.enter("forced_failure_migration")
        connection = psycopg.connect(db_url)
        execute_migration(connection)
        diagnostics.enter("forced_failure_publication")
        insert_synthetic_live_run(
            connection,
            live_run_id=live_run_id,
            manifest=manifest,
        )
        adapter = RollbackOnlyAdapter(
            connection,
            force_verification_failure=True,
            rollback_stage="forced_failure_rollback",
        )
        try:
            publish_manifest_transactionally(
                adapter,
                manifest=manifest,
                live_run_id=live_run_id,
                verify=True,
                require_r2=False,
                r2_integrity_verified=False,
                publication_fingerprint=str(
                    manifest["run"]["publication_fingerprint"]
                ),
            )
        except CanonicalVerificationError:
            pass
        else:
            raise IntegrationSafetyError(
                "forced verification failure unexpectedly succeeded"
            )
        diagnostics.enter("forced_failure_rollback")
        if not adapter.rollback_requested:
            raise IntegrationSafetyError(
                "production publication path did not request rollback"
            )
    finally:
        if connection is not None:
            connection.close()
    diagnostics.enter("forced_failure_second_connection")
    with psycopg.connect(db_url) as observer:
        counts = persistence_counts(
            observer,
            manifest=manifest,
            live_run_id=live_run_id,
        )
    diagnostics.record_counts("forced_failure", counts)
    if any(counts.values()):
        raise IntegrationSafetyError(
            "forced failure rollback left persistent rows"
        )
    return counts


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)
    digest = migration_sha256()
    db_url = os.getenv("SUPABASE_DB_URL")
    diagnostics = IntegrationDiagnostics()
    if not db_url:
        result = failure_result(
            migration_digest=digest,
            failed_stage="preflight",
            exc=MissingEnvironmentError(),
        )
        print(json.dumps(result, sort_keys=True))
        return 2
    try:
        import psycopg

        diagnostics.enter("preflight")
        with psycopg.connect(db_url) as observer:
            assert_migration_not_permanently_applied(observer)
        success_token = uuid.uuid4().hex
        failure_token = uuid.uuid4().hex
        success_counts, classifications = run_success_path(
            db_url,
            success_token,
            diagnostics,
        )
        failure_counts = run_forced_failure_path(
            db_url,
            failure_token,
            diagnostics,
        )
        all_counts = {
            f"success_{key}": value
            for key, value in success_counts.items()
        } | {
            f"forced_failure_{key}": value
            for key, value in failure_counts.items()
        }
        result = {
            "migration_sha256": digest,
            "checks": {
                "migration_not_permanently_applied": "pass",
                "successful_commit_requested": "pass",
                "same_transaction_visibility": "pass",
                "classifications": list(classifications),
                "forced_failure_rollback_requested": "pass",
                "second_connection_absence": "pass",
            },
            "zero_persistence_counts": all_counts,
        }
    except Exception as exc:
        failed_stage = diagnostics.current_stage
        cause: BaseException = exc
        if isinstance(exc, StagedIntegrationError):
            failed_stage = exc.stage
            cause = exc.cause
        result = failure_result(
            migration_digest=digest,
            failed_stage=failed_stage,
            exc=cause,
            zero_persistence_counts=(
                diagnostics.zero_persistence_counts
            ),
        )
        print(json.dumps(result, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
