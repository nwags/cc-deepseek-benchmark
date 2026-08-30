#!/usr/bin/env python3
"""Rollback-only PostgreSQL verification for migrations 010 and 011.

This integration harness may execute the reviewed migrations and synthetic
writes against PostgreSQL, but it never commits them. The success path ends
with an explicit rollback and a second connection proves that schema and row
state were restored.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.apply_provider_evidence_migrations import (
    MIGRATION_010_PATH,
    MIGRATION_011_PATH,
    PROVIDER_EVIDENCE_INDEXES,
    PROVIDER_EVIDENCE_RELATIONS,
    REVIEWED_MIGRATION_010_SHA256,
    REVIEWED_MIGRATION_011_SHA256,
    verify_provider_evidence_schema,
)
from scripts.ingest_phase3_run_metadata import (
    insert_manifest_into_postgres,
)


COST_VIEW_RELATIONS = (
    "benchmark.v_trial_adjusted_cost_coverage",
    "benchmark.v_arm_adjusted_cost_coverage",
    "benchmark.v_arm_outcome_cost_breakdown",
    "benchmark.v_suite_adjusted_cost_frontier",
)

SAVEPOINT_COUNTER = itertools.count(1)


class IntegrationSafetyError(RuntimeError):
    pass


class MissingEnvironmentError(RuntimeError):
    pass


@dataclass
class IntegrationDiagnostics:
    current_stage: str = "preflight"
    zero_persistence_counts: dict[str, int] = field(
        default_factory=dict
    )
    failed_checks: tuple[str, ...] = ()

    def enter(self, stage: str) -> None:
        self.current_stage = stage


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Required safety acknowledgement; migration and synthetic "
            "database changes are always rolled back."
        ),
    )
    args = parser.parse_args(argv)
    if not args.rollback_only:
        parser.error("--rollback-only is required")
    return args


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_hashes() -> dict[str, str]:
    digest_010 = sha256_path(MIGRATION_010_PATH)
    digest_011 = sha256_path(MIGRATION_011_PATH)

    if digest_010 != REVIEWED_MIGRATION_010_SHA256:
        raise IntegrationSafetyError(
            "migration 010 no longer matches reviewed hash"
        )
    if digest_011 != REVIEWED_MIGRATION_011_SHA256:
        raise IntegrationSafetyError(
            "migration 011 no longer matches reviewed hash"
        )

    return {
        "010": digest_010,
        "011": digest_011,
    }


def safe_sqlstate(
    exc: BaseException | None,
) -> str | None:
    if exc is None:
        return None

    value = getattr(exc, "sqlstate", None)
    if value is None:
        value = getattr(
            getattr(exc, "diag", None),
            "sqlstate",
            None,
        )

    text = str(value or "")
    if len(text) == 5 and text.isalnum():
        return text.upper()
    return None


def failure_result(
    *,
    hashes: Mapping[str, str],
    failed_stage: str,
    exc: BaseException,
    diagnostics: IntegrationDiagnostics,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "failed",
        "migration_010_sha256": hashes.get("010"),
        "migration_011_sha256": hashes.get("011"),
        "failed_stage": failed_stage,
        "error_type": type(exc).__name__,
        "zero_persistence_counts": dict(
            diagnostics.zero_persistence_counts
        ),
    }

    sqlstate = safe_sqlstate(exc)
    if sqlstate:
        result["sqlstate"] = sqlstate

    if diagnostics.failed_checks:
        result["failed_checks"] = list(
            diagnostics.failed_checks
        )

    return result


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


def assert_provider_schema_absent(
    connection: Any,
) -> None:
    with connection.cursor() as cursor:
        present_relations = relation_presence(
            cursor,
            PROVIDER_EVIDENCE_RELATIONS,
        )
        present_indexes = relation_presence(
            cursor,
            PROVIDER_EVIDENCE_INDEXES,
        )

    if present_relations:
        raise IntegrationSafetyError(
            "migration 011 already appears permanently applied"
        )

    if present_indexes:
        raise IntegrationSafetyError(
            "provider-evidence index names already exist permanently"
        )


def capture_view_definitions(
    connection: Any,
) -> dict[str, str]:
    definitions: dict[str, str] = {}

    with connection.cursor() as cursor:
        for relation in COST_VIEW_RELATIONS:
            cursor.execute(
                "select pg_get_viewdef(%s::regclass, true)",
                (relation,),
            )
            value = cursor.fetchone()[0]
            if value is None:
                raise IntegrationSafetyError(
                    "required migration-008 view is missing"
                )
            definitions[relation] = str(value)

    return definitions


def synthetic_manifest(
    token: str,
    *,
    label: str,
    logical_mode: str,
    trial_count: int = 1,
) -> dict[str, Any]:
    arm_id = (
        f"provider-evidence-integration-{label}-{token}"
    )
    run_label = f"{arm_id}/rollback-only"

    trials: list[dict[str, Any]] = []
    for index in range(1, trial_count + 1):
        task = f"{label}-task-{index}"
        trial_dir = (
            f".run/integration/{token}/{label}/{task}"
        )
        trials.append(
            {
                "trial_name": f"{task}__attempt-{index}",
                "task_name": task,
                "attempt_index": index,
                "trial_dir": trial_dir,
                "raw_result_path": f"{trial_dir}/result.json",
                "reward": 1 if index == 1 else 0,
                "status": "completed",
                "started_at": "2000-01-01T00:00:00Z",
                "finished_at": "2000-01-01T00:00:01Z",
                "runtime_seconds": 1,
                "cost_usd": 0,
                "input_tokens": 0,
                "cache_tokens": 0,
                "output_tokens": 0,
            }
        )

    return {
        "schema_version": 1,
        "config_summary": {
            "model_name": "integration-model",
            "agent": "claude-code",
        },
        "run": {
            "phase": "provider-evidence-integration",
            "logical_mode": logical_mode,
            "storage_mode": "rollback-only",
            "suite_id": f"provider-evidence-integration-{token}",
            "arm_id": arm_id,
            "run_label": run_label,
            "run_timestamp": "rollback-only",
            "run_dir": f".run/integration/{token}/{label}",
            "github_run_id": f"rollback-only-{label}-{token}",
            "github_run_attempt": 1,
            "execution_scoped": True,
            "status": "completed",
            "started_at": "2000-01-01T00:00:00Z",
            "finished_at": "2000-01-01T00:00:01Z",
            "n_total_trials": trial_count,
            "n_completed_trials": trial_count,
            "n_errored_trials": 0,
            "cost_usd": 0,
            "input_tokens": 0,
            "cache_tokens": 0,
            "output_tokens": 0,
        },
        "trials": trials,
        "artifacts": [],
    }


def create_arm_run(
    connection: Any,
    token: str,
    *,
    label: str,
    logical_mode: str,
    trial_count: int = 1,
) -> tuple[dict[str, Any], dict[str, str]]:
    manifest = synthetic_manifest(
        token,
        label=label,
        logical_mode=logical_mode,
        trial_count=trial_count,
    )
    ids = insert_manifest_into_postgres(
        manifest,
        connection=connection,
    )
    return manifest, ids


def trial_ids_for_arm_run(
    cursor: Any,
    arm_run_id: str,
) -> tuple[Any, ...]:
    cursor.execute(
        """
        select id
        from benchmark.benchmark_trials
        where arm_run_id = %s::uuid
        order by attempt_index, id
        """,
        (arm_run_id,),
    )
    return tuple(row[0] for row in cursor.fetchall())


def seed_cost_semantics(
    cursor: Any,
    *,
    manifest: Mapping[str, Any],
    arm_run_id: str,
    token: str,
) -> tuple[Any, Any]:
    trial_ids = trial_ids_for_arm_run(
        cursor,
        arm_run_id,
    )
    if len(trial_ids) != 2:
        raise IntegrationSafetyError(
            "cost-semantics fixture must contain exactly two trials"
        )

    unresolved_trial, known_trial = trial_ids
    run = manifest["run"]

    rows = (
        (
            unresolved_trial,
            Decimal("10"),
            None,
            "clean_success",
            "integration_unresolved",
        ),
        (
            known_trial,
            Decimal("4"),
            Decimal("6"),
            "failure",
            "integration_known",
        ),
    )

    for (
        trial_id,
        recorded,
        adjusted,
        outcome,
        source,
    ) in rows:
        cursor.execute(
            """
            insert into benchmark.benchmark_trial_cost_coverage (
                trial_id,
                suite_id,
                arm_id,
                run_label,
                input_tokens,
                cache_tokens,
                output_tokens,
                recorded_cost_usd,
                adjusted_cost_usd,
                cost_source,
                cost_confidence,
                outcome_bucket,
                cost_coverage_run_id
            ) values (
                %s, %s, %s, %s,
                100, 0, 10,
                %s, %s,
                %s, 'integration',
                %s, %s
            )
            """,
            (
                trial_id,
                run["suite_id"],
                run["arm_id"],
                run["run_label"],
                recorded,
                adjusted,
                source,
                outcome,
                f"integration-{token}",
            ),
        )

    return unresolved_trial, known_trial


def read_cost_semantics(
    cursor: Any,
    *,
    unresolved_trial: Any,
    known_trial: Any,
    arm_id: str,
) -> dict[str, Any]:
    cursor.execute(
        """
        select trial_id, known_accounting_gap_usd
        from benchmark.v_trial_adjusted_cost_coverage
        where trial_id = any(%s::uuid[])
        """,
        ([unresolved_trial, known_trial],),
    )
    trial_gaps = {
        str(trial_id): gap
        for trial_id, gap in cursor.fetchall()
    }

    cursor.execute(
        """
        select
            recorded_cost_usd,
            adjusted_known_cost_usd,
            known_accounting_gap_usd,
            unresolved_cost_count
        from benchmark.v_arm_adjusted_cost_coverage
        where arm_id = %s
        """,
        (arm_id,),
    )
    arm_row = cursor.fetchone()
    if arm_row is None:
        raise IntegrationSafetyError(
            "arm adjusted-cost row is missing"
        )

    cursor.execute(
        """
        select known_accounting_gap_usd
        from benchmark.v_suite_adjusted_cost_frontier
        where arm_id = %s
        """,
        (arm_id,),
    )
    frontier_row = cursor.fetchone()
    if frontier_row is None:
        raise IntegrationSafetyError(
            "suite adjusted-cost frontier row is missing"
        )

    return {
        "unresolved_trial_gap": trial_gaps.get(
            str(unresolved_trial)
        ),
        "known_trial_gap": trial_gaps.get(
            str(known_trial)
        ),
        "arm_recorded_cost": arm_row[0],
        "arm_adjusted_cost": arm_row[1],
        "arm_gap": arm_row[2],
        "unresolved_count": int(arm_row[3]),
        "frontier_gap": frontier_row[0],
    }


def assert_pre_010_semantics(
    values: Mapping[str, Any],
) -> None:
    expected = {
        "unresolved_trial_gap": Decimal("-10"),
        "known_trial_gap": Decimal("2"),
        "arm_recorded_cost": Decimal("14"),
        "arm_adjusted_cost": Decimal("6"),
        "arm_gap": Decimal("-8"),
        "unresolved_count": 1,
        "frontier_gap": Decimal("-8"),
    }
    if dict(values) != expected:
        raise IntegrationSafetyError(
            "database does not exhibit expected pre-010 semantics"
        )


def assert_post_010_semantics(
    values: Mapping[str, Any],
) -> None:
    expected = {
        "unresolved_trial_gap": None,
        "known_trial_gap": Decimal("2"),
        "arm_recorded_cost": Decimal("14"),
        "arm_adjusted_cost": Decimal("6"),
        "arm_gap": Decimal("2"),
        "unresolved_count": 1,
        "frontier_gap": Decimal("2"),
    }
    if dict(values) != expected:
        raise IntegrationSafetyError(
            "migration 010 accounting semantics failed"
        )


def execute_sql_file(
    cursor: Any,
    path: Path,
) -> None:
    cursor.execute(path.read_text(encoding="utf-8"))


def expect_statement_failure(
    cursor: Any,
    *,
    label: str,
    sql: str,
    params: Sequence[Any],
    expected_sqlstates: frozenset[str],
) -> str:
    savepoint = f"provider_verify_{next(SAVEPOINT_COUNTER)}"
    cursor.execute(f"savepoint {savepoint}")

    try:
        cursor.execute(sql, tuple(params))
    except Exception as exc:
        sqlstate = safe_sqlstate(exc)
        cursor.execute(f"rollback to savepoint {savepoint}")
        cursor.execute(f"release savepoint {savepoint}")

        if sqlstate not in expected_sqlstates:
            raise IntegrationSafetyError(
                f"{label} failed with unexpected SQLSTATE"
            ) from None
        return str(sqlstate)

    cursor.execute(f"rollback to savepoint {savepoint}")
    cursor.execute(f"release savepoint {savepoint}")
    raise IntegrationSafetyError(
        f"{label} unexpectedly succeeded"
    )


def insert_source(
    cursor: Any,
    *,
    arm_run_id: str,
    reference: str,
) -> Any:
    cursor.execute(
        """
        insert into benchmark.benchmark_provider_evidence_sources (
            provider,
            arm_run_id,
            evidence_kind,
            source_scope,
            provider_reference,
            integrity_status
        ) values (
            'integration-provider',
            %s::uuid,
            'provider_api_response',
            'arm_run',
            %s,
            'provider_api_record'
        )
        returning id
        """,
        (arm_run_id, reference),
    )
    return cursor.fetchone()[0]


def create_evidence_chain(
    cursor: Any,
    *,
    arm_run_id: str,
    token: str,
    label: str,
    usage_status: str,
    cost_status: str,
) -> tuple[Any, Any]:
    source_id = insert_source(
        cursor,
        arm_run_id=arm_run_id,
        reference=f"{label}-{token}",
    )

    cursor.execute(
        """
        insert into benchmark.benchmark_provider_usage_evidence (
            source_id,
            arm_run_id,
            provider_request_id,
            provider_model,
            ordinary_input_tokens,
            cache_read_input_tokens,
            cache_creation_input_tokens,
            output_tokens,
            request_count,
            allocation_scope,
            completeness_status
        ) values (
            %s, %s::uuid, %s,
            'integration-model',
            100, 20, 5, 10, 1,
            'exact_arm_run',
            'complete'
        )
        """,
        (
            source_id,
            arm_run_id,
            f"request-{label}-{token}",
        ),
    )

    exact_cost = cost_status == "validated_exact"
    cost_kind = (
        "provider_arm_run_billed"
        if exact_cost
        else "provider_rate_reconstruction"
    )

    cursor.execute(
        """
        insert into benchmark.benchmark_provider_cost_evidence (
            source_id,
            arm_run_id,
            provider_model,
            cost_kind,
            amount_usd,
            allocation_scope,
            completeness_status
        ) values (
            %s, %s::uuid,
            'integration-model',
            %s,
            1.25,
            'exact_arm_run',
            'complete'
        )
        """,
        (source_id, arm_run_id, cost_kind),
    )

    usage_limits = (
        []
        if usage_status == "validated_exact"
        else ["integration_qualification"]
    )
    cost_limits = (
        []
        if cost_status == "validated_exact"
        else ["integration_qualification"]
    )

    cursor.execute(
        """
        insert into benchmark.benchmark_usage_reconciliations (
            arm_run_id,
            reconciliation_version,
            model_identity_status,
            provider_observed_model,
            provider_evidence_visible,
            selected_usage_authority,
            validation_status,
            limitation_codes
        ) values (
            %s::uuid,
            %s,
            'matched',
            'integration-model',
            true,
            'provider_request_usage',
            %s,
            %s
        )
        returning id
        """,
        (
            arm_run_id,
            f"{label}-usage-v1",
            usage_status,
            usage_limits,
        ),
    )
    usage_id = cursor.fetchone()[0]

    if exact_cost:
        selected_basis = "provider_billed"
        selected_relation = "exact"
    else:
        selected_basis = (
            "provider_rate_reconstructed_provider_usage"
        )
        selected_relation = "estimate"

    cursor.execute(
        """
        insert into benchmark.benchmark_cost_reconciliations (
            arm_run_id,
            reconciliation_version,
            selected_cost_usd,
            selected_cost_basis,
            selected_cost_relation,
            validation_status,
            provider_evidence_visible,
            limitation_codes
        ) values (
            %s::uuid,
            %s,
            1.25,
            %s,
            %s,
            %s,
            true,
            %s
        )
        returning id
        """,
        (
            arm_run_id,
            f"{label}-cost-v1",
            selected_basis,
            selected_relation,
            cost_status,
            cost_limits,
        ),
    )
    cost_id = cursor.fetchone()[0]

    cursor.execute(
        """
        insert into benchmark.benchmark_usage_reconciliation_sources (
            reconciliation_id,
            source_id,
            evidence_role
        ) values (%s, %s, 'request_usage')
        """,
        (usage_id, source_id),
    )

    cursor.execute(
        """
        insert into benchmark.benchmark_cost_reconciliation_sources (
            reconciliation_id,
            source_id,
            evidence_role
        ) values (%s, %s, 'billed')
        """,
        (cost_id, source_id),
    )

    return usage_id, cost_id


def create_unverified_chain(
    cursor: Any,
    *,
    arm_run_id: str,
    label: str,
) -> tuple[Any, Any]:
    cursor.execute(
        """
        insert into benchmark.benchmark_usage_reconciliations (
            arm_run_id,
            reconciliation_version,
            model_identity_status,
            provider_evidence_visible,
            selected_usage_authority,
            validation_status
        ) values (
            %s::uuid,
            %s,
            'unknown',
            false,
            'none',
            'unverified'
        )
        returning id
        """,
        (arm_run_id, f"{label}-usage-unverified"),
    )
    usage_id = cursor.fetchone()[0]

    cursor.execute(
        """
        insert into benchmark.benchmark_cost_reconciliations (
            arm_run_id,
            reconciliation_version,
            validation_status,
            provider_evidence_visible
        ) values (
            %s::uuid,
            %s,
            'unverified',
            false
        )
        returning id
        """,
        (arm_run_id, f"{label}-cost-unverified"),
    )
    cost_id = cursor.fetchone()[0]

    return usage_id, cost_id


def insert_gate(
    cursor: Any,
    *,
    arm_id: str,
    source_arm_run_id: str,
    source_mode: str,
    target_mode: str,
    usage_id: Any,
    cost_id: Any,
    decision: str = "pass",
    blocker_codes: Sequence[str] = (),
    waiver_reason: str | None = None,
) -> Any:
    cursor.execute(
        """
        insert into benchmark.benchmark_evidence_promotion_gates (
            arm_id,
            source_arm_run_id,
            source_mode,
            target_mode,
            usage_reconciliation_id,
            cost_reconciliation_id,
            decision,
            blocker_codes,
            waiver_reason
        ) values (
            %s, %s::uuid, %s, %s,
            %s, %s, %s, %s, %s
        )
        returning id
        """,
        (
            arm_id,
            source_arm_run_id,
            source_mode,
            target_mode,
            usage_id,
            cost_id,
            decision,
            list(blocker_codes),
            waiver_reason,
        ),
    )
    return cursor.fetchone()[0]


def read_gate_state(
    cursor: Any,
    gate_id: Any,
) -> tuple[tuple[str, ...], bool]:
    cursor.execute(
        """
        select
            derived_blocker_codes,
            effective_can_advance
        from benchmark.v_evidence_promotion_gate
        where gate_id = %s
        """,
        (gate_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise IntegrationSafetyError(
            "promotion gate view row is missing"
        )

    return (
        tuple(str(value) for value in (row[0] or [])),
        bool(row[1]),
    )


def assert_gate_state(
    *,
    label: str,
    blockers: Sequence[str],
    effective: bool,
    expected_effective: bool,
    required_blockers: Sequence[str] = (),
) -> None:
    blocker_set = set(blockers)

    if effective is not expected_effective:
        raise IntegrationSafetyError(
            f"{label} effective promotion state is incorrect"
        )

    for blocker in required_blockers:
        if blocker not in blocker_set:
            raise IntegrationSafetyError(
                f"{label} is missing required blocker {blocker}"
            )

    if expected_effective and blocker_set:
        raise IntegrationSafetyError(
            f"{label} unexpectedly has derived blockers"
        )


def exercise_constraint_contract(
    cursor: Any,
    *,
    arm_run_id: str,
    token: str,
) -> dict[str, str]:
    source_id = insert_source(
        cursor,
        arm_run_id=arm_run_id,
        reference=f"constraints-{token}",
    )

    failures: dict[str, str] = {}

    failures["usage_unavailable_not_normalized"] = (
        expect_statement_failure(
            cursor,
            label="usage unavailable normalization",
            sql="""
                insert into benchmark.benchmark_provider_usage_evidence (
                    source_id,
                    allocation_scope,
                    completeness_status
                ) values (%s, 'exact_arm_run', 'unavailable')
            """,
            params=(source_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    failures["cost_unavailable_not_normalized"] = (
        expect_statement_failure(
            cursor,
            label="cost unavailable normalization",
            sql="""
                insert into benchmark.benchmark_provider_cost_evidence (
                    source_id,
                    cost_kind,
                    amount_usd,
                    allocation_scope,
                    completeness_status
                ) values (
                    %s,
                    'provider_arm_run_billed',
                    1,
                    'exact_arm_run',
                    'unavailable'
                )
            """,
            params=(source_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    failures["positive_usage_requires_provider_evidence"] = (
        expect_statement_failure(
            cursor,
            label="positive usage provider evidence",
            sql="""
                insert into benchmark.benchmark_usage_reconciliations (
                    arm_run_id,
                    reconciliation_version,
                    is_current,
                    model_identity_status,
                    provider_evidence_visible,
                    selected_usage_authority,
                    validation_status,
                    limitation_codes
                ) values (
                    %s::uuid,
                    'invalid-visible',
                    false,
                    'matched',
                    false,
                    'provider_request_usage',
                    'provisional',
                    array['integration']
                )
            """,
            params=(arm_run_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    failures["provisional_usage_requires_limitations"] = (
        expect_statement_failure(
            cursor,
            label="provisional usage limitations",
            sql="""
                insert into benchmark.benchmark_usage_reconciliations (
                    arm_run_id,
                    reconciliation_version,
                    is_current,
                    model_identity_status,
                    provider_evidence_visible,
                    selected_usage_authority,
                    validation_status
                ) values (
                    %s::uuid,
                    'invalid-limits',
                    false,
                    'matched',
                    true,
                    'provider_request_usage',
                    'provisional'
                )
            """,
            params=(arm_run_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    failures["validated_exact_cost_requires_exact_relation"] = (
        expect_statement_failure(
            cursor,
            label="validated exact cost relation",
            sql="""
                insert into benchmark.benchmark_cost_reconciliations (
                    arm_run_id,
                    reconciliation_version,
                    is_current,
                    selected_cost_usd,
                    selected_cost_basis,
                    selected_cost_relation,
                    validation_status,
                    provider_evidence_visible
                ) values (
                    %s::uuid,
                    'invalid-exact-relation',
                    false,
                    1,
                    'provider_billed',
                    'estimate',
                    'validated_exact',
                    true
                )
            """,
            params=(arm_run_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    failures["mismatch_cost_cannot_select_numeric_cost"] = (
        expect_statement_failure(
            cursor,
            label="mismatch selected cost",
            sql="""
                insert into benchmark.benchmark_cost_reconciliations (
                    arm_run_id,
                    reconciliation_version,
                    is_current,
                    selected_cost_usd,
                    selected_cost_basis,
                    selected_cost_relation,
                    validation_status,
                    provider_evidence_visible
                ) values (
                    %s::uuid,
                    'invalid-mismatch-cost',
                    false,
                    1,
                    'provider_billed',
                    'exact',
                    'mismatch',
                    true
                )
            """,
            params=(arm_run_id,),
            expected_sqlstates=frozenset({"23514"}),
        )
    )

    return failures


def exercise_current_uniqueness(
    cursor: Any,
    *,
    usage_id: Any,
    cost_id: Any,
) -> dict[str, str]:
    usage_state = expect_statement_failure(
        cursor,
        label="duplicate current usage reconciliation",
        sql="""
            insert into benchmark.benchmark_usage_reconciliations (
                arm_run_id,
                reconciliation_version,
                is_current,
                model_identity_status,
                provider_evidence_visible,
                selected_usage_authority,
                validation_status,
                limitation_codes
            )
            select
                arm_run_id,
                reconciliation_version || '-duplicate',
                true,
                model_identity_status,
                provider_evidence_visible,
                selected_usage_authority,
                validation_status,
                limitation_codes
            from benchmark.benchmark_usage_reconciliations
            where id = %s
        """,
        params=(usage_id,),
        expected_sqlstates=frozenset({"23505"}),
    )

    cost_state = expect_statement_failure(
        cursor,
        label="duplicate current cost reconciliation",
        sql="""
            insert into benchmark.benchmark_cost_reconciliations (
                arm_run_id,
                reconciliation_version,
                is_current,
                selected_cost_usd,
                selected_cost_basis,
                selected_cost_relation,
                validation_status,
                provider_evidence_visible,
                limitation_codes
            )
            select
                arm_run_id,
                reconciliation_version || '-duplicate',
                true,
                selected_cost_usd,
                selected_cost_basis,
                selected_cost_relation,
                validation_status,
                provider_evidence_visible,
                limitation_codes
            from benchmark.benchmark_cost_reconciliations
            where id = %s
        """,
        params=(cost_id,),
        expected_sqlstates=frozenset({"23505"}),
    )

    return {
        "usage_current_unique": usage_state,
        "cost_current_unique": cost_state,
    }


def exercise_promotion_contract(
    connection: Any,
    cursor: Any,
    *,
    token: str,
) -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}

    def make_run(
        label: str,
        mode: str,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        return create_arm_run(
            connection,
            token,
            label=label,
            logical_mode=mode,
        )

    def record(
        label: str,
        gate_id: Any,
        *,
        expected_effective: bool,
        required_blockers: Sequence[str] = (),
    ) -> None:
        blockers, effective = read_gate_state(
            cursor,
            gate_id,
        )
        assert_gate_state(
            label=label,
            blockers=blockers,
            effective=effective,
            expected_effective=expected_effective,
            required_blockers=required_blockers,
        )
        scenarios[label] = {
            "effective_can_advance": effective,
            "derived_blocker_codes": list(blockers),
        }

    manifest, ids = make_run("canary-provisional", "canary")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="canary-provisional",
        usage_status="provisional",
        cost_status="provisional",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "canary_provisional_to_smoke",
        gate_id,
        expected_effective=True,
    )

    manifest, ids = make_run("smoke-provisional", "smoke")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="smoke-provisional",
        usage_status="provisional",
        cost_status="provisional",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="smoke",
        target_mode="full",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "smoke_provisional_to_full",
        gate_id,
        expected_effective=False,
        required_blockers=(
            "smoke_usage_not_full_sweep_qualified",
            "smoke_cost_not_full_sweep_qualified",
        ),
    )

    manifest, ids = make_run("smoke-qualified", "smoke")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="smoke-qualified",
        usage_status="validated_qualified",
        cost_status="validated_exact",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="smoke",
        target_mode="full",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "smoke_qualified_to_full",
        gate_id,
        expected_effective=True,
    )

    manifest, ids = make_run("waived", "canary")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="waived",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_id,
        cost_id=cost_id,
        decision="waived",
        waiver_reason="rollback-only integration waiver",
    )
    record(
        "waived_not_effective",
        gate_id,
        expected_effective=False,
        required_blockers=("gate_decision_not_pass",),
    )

    manifest, ids = make_run("mode-mismatch", "canary")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="mode-mismatch",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="smoke",
        target_mode="full",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "source_mode_mismatch",
        gate_id,
        expected_effective=False,
        required_blockers=("source_run_mode_mismatch",),
    )

    source_manifest, source_ids = make_run(
        "arm-mismatch-source",
        "canary",
    )
    other_manifest, _other_ids = make_run(
        "arm-mismatch-other",
        "canary",
    )
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=source_ids["arm_run_id"],
        token=token,
        label="arm-mismatch-source",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=other_manifest["run"]["arm_id"],
        source_arm_run_id=source_ids["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "source_arm_mismatch",
        gate_id,
        expected_effective=False,
        required_blockers=("source_run_arm_mismatch",),
    )

    manifest_a, ids_a = make_run("wrong-recon-a", "canary")
    _manifest_b, ids_b = make_run("wrong-recon-b", "canary")

    usage_a, cost_a = create_evidence_chain(
        cursor,
        arm_run_id=ids_a["arm_run_id"],
        token=token,
        label="wrong-recon-a",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )
    usage_b, _cost_b = create_evidence_chain(
        cursor,
        arm_run_id=ids_b["arm_run_id"],
        token=token,
        label="wrong-recon-b",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )

    gate_id = insert_gate(
        cursor,
        arm_id=manifest_a["run"]["arm_id"],
        source_arm_run_id=ids_a["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_b,
        cost_id=cost_a,
    )
    record(
        "usage_reconciliation_wrong_run",
        gate_id,
        expected_effective=False,
        required_blockers=(
            "usage_reconciliation_wrong_arm_run",
        ),
    )

    manifest, ids = make_run("stale", "canary")
    usage_id, cost_id = create_evidence_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        token=token,
        label="stale",
        usage_status="validated_exact",
        cost_status="validated_exact",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    cursor.execute(
        """
        update benchmark.benchmark_usage_reconciliations
        set is_current = false
        where id = %s
        """,
        (usage_id,),
    )
    cursor.execute(
        """
        update benchmark.benchmark_cost_reconciliations
        set is_current = false
        where id = %s
        """,
        (cost_id,),
    )
    record(
        "stale_reconciliations",
        gate_id,
        expected_effective=False,
        required_blockers=(
            "usage_reconciliation_not_current",
            "cost_reconciliation_not_current",
        ),
    )

    manifest, ids = make_run("unverified", "canary")
    usage_id, cost_id = create_unverified_chain(
        cursor,
        arm_run_id=ids["arm_run_id"],
        label="unverified",
    )
    gate_id = insert_gate(
        cursor,
        arm_id=manifest["run"]["arm_id"],
        source_arm_run_id=ids["arm_run_id"],
        source_mode="canary",
        target_mode="smoke",
        usage_id=usage_id,
        cost_id=cost_id,
    )
    record(
        "missing_authority_fails_closed",
        gate_id,
        expected_effective=False,
        required_blockers=(
            "provider_usage_evidence_not_visible",
            "provider_cost_evidence_not_visible",
            "provider_model_identity_not_matched",
            "selected_usage_authority_missing",
            "selected_cost_missing",
            "selected_cost_basis_missing",
            "selected_cost_relation_unresolved",
            "canary_usage_not_smoke_eligible",
            "canary_cost_not_smoke_eligible",
        ),
    )

    return scenarios


def persistent_counts(
    connection: Any,
    *,
    token: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    with connection.cursor() as cursor:
        counts["provider_relations_present"] = len(
            relation_presence(
                cursor,
                PROVIDER_EVIDENCE_RELATIONS,
            )
        )
        counts["provider_indexes_present"] = len(
            relation_presence(
                cursor,
                PROVIDER_EVIDENCE_INDEXES,
            )
        )

        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_arms
            where arm_id like %s
            """,
            (f"%{token}%",),
        )
        counts["synthetic_arms"] = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_runs
            where phase = 'provider-evidence-integration'
              and run_label like %s
            """,
            (f"%{token}%",),
        )
        counts["synthetic_runs"] = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_trials trial
            join benchmark.benchmark_arms arm
              on arm.arm_id = trial.arm_id
            where arm.arm_id like %s
            """,
            (f"%{token}%",),
        )
        counts["synthetic_trials"] = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_trial_cost_coverage
            where cost_coverage_run_id = %s
            """,
            (f"integration-{token}",),
        )
        counts["synthetic_cost_rows"] = int(
            cursor.fetchone()[0]
        )

    return counts


def run_verification(
    db_url: str,
    *,
    token: str,
    baseline_viewdefs: Mapping[str, str],
    diagnostics: IntegrationDiagnostics,
) -> dict[str, Any]:
    import psycopg

    connection: Any = None

    try:
        diagnostics.enter("transaction_connection")
        connection = psycopg.connect(
            db_url,
            autocommit=False,
        )

        diagnostics.enter("pre_010_fixture")
        cost_manifest, cost_ids = create_arm_run(
            connection,
            token,
            label="cost-semantics",
            logical_mode="smoke",
            trial_count=2,
        )

        with connection.cursor() as cursor:
            unresolved_trial, known_trial = seed_cost_semantics(
                cursor,
                manifest=cost_manifest,
                arm_run_id=cost_ids["arm_run_id"],
                token=token,
            )

            diagnostics.enter("pre_010_semantics")
            pre_values = read_cost_semantics(
                cursor,
                unresolved_trial=unresolved_trial,
                known_trial=known_trial,
                arm_id=cost_manifest["run"]["arm_id"],
            )
            assert_pre_010_semantics(pre_values)

            diagnostics.enter("migration_010")
            execute_sql_file(
                cursor,
                MIGRATION_010_PATH,
            )

            diagnostics.enter("post_010_semantics")
            post_values = read_cost_semantics(
                cursor,
                unresolved_trial=unresolved_trial,
                known_trial=known_trial,
                arm_id=cost_manifest["run"]["arm_id"],
            )
            assert_post_010_semantics(post_values)

            diagnostics.enter("migration_011")
            execute_sql_file(
                cursor,
                MIGRATION_011_PATH,
            )

            diagnostics.enter("schema_verification")
            structural_failures = (
                verify_provider_evidence_schema(cursor)
            )
            if structural_failures:
                diagnostics.failed_checks = tuple(
                    structural_failures
                )
                raise IntegrationSafetyError(
                    "migration 011 structural verification failed"
                )

            diagnostics.enter("constraint_fixture")
            _constraint_manifest, constraint_ids = (
                create_arm_run(
                    connection,
                    token,
                    label="constraints",
                    logical_mode="canary",
                )
            )

            diagnostics.enter("constraint_contract")
            constraint_results = (
                exercise_constraint_contract(
                    cursor,
                    arm_run_id=constraint_ids["arm_run_id"],
                    token=token,
                )
            )

            diagnostics.enter("current_unique_fixture")
            _unique_manifest, unique_ids = (
                create_arm_run(
                    connection,
                    token,
                    label="current-unique",
                    logical_mode="canary",
                )
            )
            usage_id, cost_id = create_evidence_chain(
                cursor,
                arm_run_id=unique_ids["arm_run_id"],
                token=token,
                label="current-unique",
                usage_status="validated_exact",
                cost_status="validated_exact",
            )
            uniqueness_results = (
                exercise_current_uniqueness(
                    cursor,
                    usage_id=usage_id,
                    cost_id=cost_id,
                )
            )

            diagnostics.enter("promotion_contract")
            promotion_results = exercise_promotion_contract(
                connection,
                cursor,
                token=token,
            )

        diagnostics.enter("rollback")
        connection.rollback()

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter("second_connection")
    with psycopg.connect(
        db_url,
        autocommit=False,
    ) as observer:
        restored_viewdefs = capture_view_definitions(
            observer
        )
        counts = persistent_counts(
            observer,
            token=token,
        )
        observer.rollback()

    diagnostics.zero_persistence_counts.update(counts)

    if restored_viewdefs != dict(baseline_viewdefs):
        raise IntegrationSafetyError(
            "migration 010 view definitions were not restored by rollback"
        )

    if any(counts.values()):
        raise IntegrationSafetyError(
            "rollback-only verification left persistent state"
        )

    return {
        "pre_010_semantics": "pass",
        "post_010_semantics": "pass",
        "migration_011_structure": "pass",
        "constraint_results": constraint_results,
        "current_uniqueness": uniqueness_results,
        "promotion_scenarios": promotion_results,
        "rollback_restored_view_definitions": "pass",
        "second_connection_zero_persistence": "pass",
    }


def main(
    argv: list[str] | None = None,
) -> int:
    parse_args(argv)

    diagnostics = IntegrationDiagnostics()

    try:
        hashes = reviewed_hashes()
    except Exception as exc:
        result = failure_result(
            hashes={},
            failed_stage="hash",
            exc=exc,
            diagnostics=diagnostics,
        )
        print(json.dumps(result, sort_keys=True))
        return 2

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        result = failure_result(
            hashes=hashes,
            failed_stage="preflight",
            exc=MissingEnvironmentError(),
            diagnostics=diagnostics,
        )
        print(json.dumps(result, sort_keys=True))
        return 2

    try:
        import psycopg

        diagnostics.enter("permanent_preflight")
        with psycopg.connect(
            db_url,
            autocommit=False,
        ) as observer:
            assert_provider_schema_absent(observer)
            baseline_viewdefs = capture_view_definitions(
                observer
            )
            observer.rollback()

        token = uuid.uuid4().hex

        checks = run_verification(
            db_url,
            token=token,
            baseline_viewdefs=baseline_viewdefs,
            diagnostics=diagnostics,
        )

        result = {
            "status": "passed",
            "mode": "rollback-only",
            "migration_010_sha256": hashes["010"],
            "migration_011_sha256": hashes["011"],
            "checks": checks,
            "zero_persistence_counts": dict(
                diagnostics.zero_persistence_counts
            ),
        }

    except Exception as exc:
        result = failure_result(
            hashes=hashes,
            failed_stage=diagnostics.current_stage,
            exc=exc,
            diagnostics=diagnostics,
        )
        print(json.dumps(result, sort_keys=True))
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
