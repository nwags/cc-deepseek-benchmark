#!/usr/bin/env python3
"""Plan or rollback-test normalized OpenAI Phase 3 provider evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "results/phase3/provider_usage/normalized"

SOURCE_MANIFEST = (
    NORMALIZED / "openai_provider_source_manifest_20260821.csv"
)
ACTIVITY = (
    NORMALIZED / "openai_provider_activity_20260821.csv"
)
RECONCILIATION = (
    NORMALIZED / "openai_provider_reconciliation_20260821.csv"
)

NORMALIZED_HASHES = {
    "source_manifest": (
        "2c458c3122c012b97aea5bc8c7a14d566dfae69292263add"
        "9d7f4bb3c8a901f8"
    ),
    "activity": (
        "69004a2c5d13aa40091122a818047d1fbd44a23bad611f791"
        "2abf985302ebc28"
    ),
    "reconciliation": (
        "5da12494743dc7265c3c08ffc08aa988451fbc308940453cf9"
        "b3bc6cdf71e452"
    ),
}

SOURCE_CONTRACT = {
    "usage": {
        "source_file": "completions_usage_2026-06-01_2026-07-01.csv",
        "source_type": "provider_usage_export",
        "sha256": (
            "9c4dc05dd36164ba34cb387f9ca97fb63255b8ac0aeff278"
            "2b00784a6cf2d108"
        ),
        "evidence_kind": "usage_export",
    },
    "cost": {
        "source_file": "cost_2026-06-01_2026-07-01.csv",
        "source_type": "provider_cost_export",
        "sha256": (
            "04cea7cd630c0dd7a4aef144d005eb3640a70072f24f4c6a"
            "5132016ea3bfd12d"
        ),
        "evidence_kind": "billing_export",
    },
}

ARM_CONTRACT = {
    "router-gpt-5.4": {
        "selected_run_label": (
            "router-gpt-5.4/2026-06-19__13-47-51"
        ),
        "backend_model": "gpt-5.4",
        "provider_model": "gpt-5.4-2026-03-05",
        "trial_count": 60,
        "request_count": 1256,
        "input_tokens": 32807457,
        "cached_input_tokens": 30833664,
        "uncached_input_tokens": 1973793,
        "output_tokens": 1143269,
        "provider_billed_cost_usd": Decimal("29.7919335"),
        "historical_harness_recorded_cost_usd": Decimal(
            "173.09483"
        ),
    },
    "router-gpt-5.5": {
        "selected_run_label": (
            "router-gpt-5.5/2026-06-27__01-30-18"
        ),
        "backend_model": "gpt-5.5",
        "provider_model": "gpt-5.5-2026-04-23",
        "trial_count": 60,
        "request_count": 1480,
        "input_tokens": 35226942,
        "cached_input_tokens": 33033728,
        "uncached_input_tokens": 2193214,
        "output_tokens": 704066,
        "provider_billed_cost_usd": Decimal("48.604914"),
        "historical_harness_recorded_cost_usd": Decimal(
            "168.708375"
        ),
    },
}

TARGET_TABLES = (
    "benchmark_provider_evidence_sources",
    "benchmark_provider_usage_evidence",
    "benchmark_provider_pricing_snapshots",
    "benchmark_provider_cost_evidence",
    "benchmark_usage_reconciliations",
    "benchmark_usage_reconciliation_sources",
    "benchmark_cost_reconciliations",
    "benchmark_cost_reconciliation_sources",
    "benchmark_evidence_promotion_gates",
)


class EvidencePlanError(RuntimeError):
    pass


class IntegrationSafetyError(RuntimeError):
    pass


class MissingEnvironmentError(RuntimeError):
    pass


@dataclass
class Diagnostics:
    stage: str = "arguments"
    zero_persistence_counts: dict[str, int] = field(
        default_factory=dict
    )

    def enter(self, stage: str) -> None:
        self.stage = stage


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def verify_normalized_hashes() -> dict[str, str]:
    actual = {
        "source_manifest": sha256_path(SOURCE_MANIFEST),
        "activity": sha256_path(ACTIVITY),
        "reconciliation": sha256_path(RECONCILIATION),
    }

    if actual != NORMALIZED_HASHES:
        raise EvidencePlanError(
            "normalized OpenAI evidence no longer matches reviewed hashes"
        )

    return actual


def _require_equal(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if actual != expected:
        raise EvidencePlanError(
            f"reviewed OpenAI evidence mismatch: {label}"
        )


def build_plan() -> dict[str, Any]:
    hashes = verify_normalized_hashes()

    manifest_rows = read_csv(SOURCE_MANIFEST)
    reconciliation_rows = read_csv(RECONCILIATION)

    sources: list[dict[str, Any]] = []

    for source_key, expected in SOURCE_CONTRACT.items():
        matches = [
            row
            for row in manifest_rows
            if row["source_file"] == expected["source_file"]
        ]

        _require_equal(
            len(matches),
            1,
            f"{source_key} source multiplicity",
        )

        row = matches[0]

        _require_equal(
            row["source_type"],
            expected["source_type"],
            f"{source_key} source type",
        )
        _require_equal(
            row["sha256"],
            expected["sha256"],
            f"{source_key} source sha256",
        )
        _require_equal(
            row["raw_source_committed"],
            "false",
            f"{source_key} raw source committed state",
        )
        _require_equal(
            row["contains_private_identifiers"],
            "true",
            f"{source_key} private identifier state",
        )

        sources.append(
            {
                "source_key": source_key,
                "provider": "openai",
                "evidence_kind": expected["evidence_kind"],
                "source_scope": "provider_window",
                "provider_reference": expected["source_file"],
                "source_sha256": expected["sha256"],
                "source_format": "csv",
                "integrity_status": "sha256_verified",
                "notes": (
                    "Private OpenAI provider export; raw bytes remain "
                    "outside Git. Provenance is retained through the "
                    "reviewed sanitized source manifest."
                ),
                "raw_metadata": {
                    "source_type": expected["source_type"],
                    "source_manifest": str(
                        SOURCE_MANIFEST.relative_to(ROOT)
                    ),
                    "raw_source_committed": False,
                    "contains_private_identifiers": True,
                },
            }
        )

    full_sweeps = {
        row["arm_id"]: row
        for row in reconciliation_rows
        if row["record_type"] == "full_sweep"
    }

    _require_equal(
        set(full_sweeps),
        set(ARM_CONTRACT),
        "full-sweep arm membership",
    )

    arms: list[dict[str, Any]] = []

    for arm_id, expected in ARM_CONTRACT.items():
        row = full_sweeps[arm_id]

        checks = {
            "selected_run_label": row["selected_run_label"],
            "backend_model": row["backend_model"],
            "provider_model": row["provider_model"],
            "trial_count": int(row["trial_count"]),
            "request_count": int(row["request_count"]),
            "input_tokens": int(row["input_tokens"]),
            "cached_input_tokens": int(
                row["cached_input_tokens"]
            ),
            "uncached_input_tokens": int(
                row["uncached_input_tokens"]
            ),
            "output_tokens": int(row["output_tokens"]),
            "provider_billed_cost_usd": Decimal(
                row["provider_billed_cost_usd"]
            ),
            "historical_harness_recorded_cost_usd": Decimal(
                row["historical_harness_recorded_cost_usd"]
            ),
        }

        for key, expected_value in expected.items():
            _require_equal(
                checks[key],
                expected_value,
                f"{arm_id} {key}",
            )

        _require_equal(
            checks["input_tokens"],
            (
                checks["cached_input_tokens"]
                + checks["uncached_input_tokens"]
            ),
            f"{arm_id} input partition",
        )

        _require_equal(
            row["provider_billing_reconciliation_status"],
            "exact_arm_total",
            f"{arm_id} billing status",
        )
        _require_equal(
            row["trial_cost_allocation_status"],
            "unavailable_provider_aggregate",
            f"{arm_id} trial allocation status",
        )
        _require_equal(
            row["outcome_cost_allocation_status"],
            "unavailable_provider_aggregate",
            f"{arm_id} outcome allocation status",
        )

        arms.append(
            {
                "arm_id": arm_id,
                "selected_run_label": checks[
                    "selected_run_label"
                ],
                "backend_model": checks["backend_model"],
                "provider_model": checks["provider_model"],
                "trial_count": checks["trial_count"],
                "provider_usage": {
                    "ordinary_input_tokens": checks[
                        "uncached_input_tokens"
                    ],
                    "cache_read_input_tokens": checks[
                        "cached_input_tokens"
                    ],
                    "cache_creation_input_tokens": None,
                    "output_tokens": checks["output_tokens"],
                    "request_count": checks["request_count"],
                    "allocation_scope": "exact_arm_run",
                    "completeness_status": "complete",
                },
                "provider_cost": {
                    "amount_usd": str(
                        checks["provider_billed_cost_usd"]
                    ),
                    "cost_kind": "provider_arm_run_billed",
                    "allocation_scope": "exact_arm_run",
                    "completeness_status": "complete",
                },
                "usage_reconciliation": {
                    "model_identity_status": "matched",
                    "provider_evidence_visible": True,
                    "selected_usage_authority": (
                        "provider_aggregate_usage"
                    ),
                    "validation_status": "validated_exact",
                },
                "cost_reconciliation": {
                    "harness_reported_cost_usd": str(
                        checks[
                            "historical_harness_recorded_cost_usd"
                        ]
                    ),
                    "provider_billed_cost_usd": str(
                        checks["provider_billed_cost_usd"]
                    ),
                    "selected_cost_usd": str(
                        checks["provider_billed_cost_usd"]
                    ),
                    "selected_cost_basis": "provider_billed",
                    "selected_cost_relation": "exact",
                    "validation_status": "validated_exact",
                    "provider_evidence_visible": True,
                },
                "allocation_policy": {
                    "trial_cost": (
                        "unavailable_provider_aggregate"
                    ),
                    "outcome_cost": (
                        "unavailable_provider_aggregate"
                    ),
                },
            }
        )

    return {
        "schema_version": 1,
        "provider": "openai",
        "source_scope": "selected_phase3_full_sweeps",
        "normalized_input_hashes": hashes,
        "sources": sources,
        "arm_runs": arms,
        "write_counts": {
            "benchmark_provider_evidence_sources": 2,
            "benchmark_provider_usage_evidence": 2,
            "benchmark_provider_pricing_snapshots": 0,
            "benchmark_provider_cost_evidence": 2,
            "benchmark_usage_reconciliations": 2,
            "benchmark_usage_reconciliation_sources": 2,
            "benchmark_cost_reconciliations": 2,
            "benchmark_cost_reconciliation_sources": 2,
            "benchmark_evidence_promotion_gates": 0,
        },
    }


def target_table_counts(cursor: Any) -> dict[str, int]:
    counts: dict[str, int] = {}

    for table in TARGET_TABLES:
        cursor.execute(
            f"select count(*) from benchmark.{table}"
        )
        counts[table] = int(cursor.fetchone()[0])

    return counts


def resolve_arm_runs(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, str]:
    labels = [
        arm["selected_run_label"]
        for arm in plan["arm_runs"]
    ]

    cursor.execute(
        """
        select
            arm_run.id::text,
            arm_run.arm_id,
            benchmark_run.run_label,
            arm_run.suite_id,
            arm_run.logical_mode,
            arm_run.storage_mode,
            arm_run.n_trials
        from benchmark.benchmark_arm_runs arm_run
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where benchmark_run.run_label = any(%s::text[])
        order by benchmark_run.run_label, arm_run.arm_id
        """,
        (labels,),
    )

    rows = cursor.fetchall()

    by_label: dict[str, list[Any]] = {}
    for row in rows:
        by_label.setdefault(str(row[2]), []).append(row)

    resolved: dict[str, str] = {}

    for arm in plan["arm_runs"]:
        label = arm["selected_run_label"]
        matches = by_label.get(label, [])

        if len(matches) != 1:
            raise IntegrationSafetyError(
                "selected OpenAI run does not resolve exactly once"
            )

        (
            arm_run_id,
            stored_arm_id,
            _run_label,
            suite_id,
            logical_mode,
            storage_mode,
            n_trials,
        ) = matches[0]

        if stored_arm_id != arm["arm_id"]:
            raise IntegrationSafetyError(
                "selected OpenAI run resolves to wrong arm"
            )
        if suite_id != "phase3-full-20":
            raise IntegrationSafetyError(
                "selected OpenAI run resolves to wrong suite"
            )
        if logical_mode != "full":
            raise IntegrationSafetyError(
                "selected OpenAI run is not logical full mode"
            )
        if storage_mode != "raw":
            raise IntegrationSafetyError(
                "selected OpenAI run is not raw storage mode"
            )
        if int(n_trials) != int(arm["trial_count"]):
            raise IntegrationSafetyError(
                "selected OpenAI run has unexpected trial count"
            )

        resolved[arm["arm_id"]] = str(arm_run_id)

    return resolved


def insert_plan(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> None:
    from psycopg.types.json import Jsonb

    source_ids: dict[str, Any] = {}

    for source in plan["sources"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_provider_evidence_sources (
                provider,
                evidence_kind,
                source_scope,
                provider_reference,
                source_sha256,
                source_format,
                integrity_status,
                notes,
                raw_metadata
            ) values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            returning id
            """,
            (
                source["provider"],
                source["evidence_kind"],
                source["source_scope"],
                source["provider_reference"],
                source["source_sha256"],
                source["source_format"],
                source["integrity_status"],
                source["notes"],
                Jsonb(source["raw_metadata"]),
            ),
        )
        source_ids[source["source_key"]] = (
            cursor.fetchone()[0]
        )

    for arm in plan["arm_runs"]:
        arm_id = arm["arm_id"]
        arm_run_id = arm_run_ids[arm_id]
        usage = arm["provider_usage"]
        cost = arm["provider_cost"]

        common_metadata = {
            "selected_run_label": arm["selected_run_label"],
            "normalized_reconciliation_source": str(
                RECONCILIATION.relative_to(ROOT)
            ),
            "trial_cost_allocation_status": (
                arm["allocation_policy"]["trial_cost"]
            ),
            "outcome_cost_allocation_status": (
                arm["allocation_policy"]["outcome_cost"]
            ),
        }

        cursor.execute(
            """
            insert into benchmark.benchmark_provider_usage_evidence (
                source_id,
                arm_run_id,
                provider_model,
                ordinary_input_tokens,
                cache_read_input_tokens,
                cache_creation_input_tokens,
                output_tokens,
                request_count,
                allocation_scope,
                completeness_status,
                notes,
                raw_metadata
            ) values (
                %s, %s::uuid, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                source_ids["usage"],
                arm_run_id,
                arm["provider_model"],
                usage["ordinary_input_tokens"],
                usage["cache_read_input_tokens"],
                usage["cache_creation_input_tokens"],
                usage["output_tokens"],
                usage["request_count"],
                usage["allocation_scope"],
                usage["completeness_status"],
                (
                    "Exact provider aggregate usage for the selected "
                    "arm run; no request-level or trial-level "
                    "allocation is asserted."
                ),
                Jsonb(common_metadata),
            ),
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
                completeness_status,
                notes,
                raw_metadata
            ) values (
                %s, %s::uuid, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                source_ids["cost"],
                arm_run_id,
                arm["provider_model"],
                cost["cost_kind"],
                Decimal(cost["amount_usd"]),
                cost["allocation_scope"],
                cost["completeness_status"],
                (
                    "Exact provider-billed arm-run total; trial and "
                    "outcome allocation remain unavailable."
                ),
                Jsonb(common_metadata),
            ),
        )

        usage_version = (
            f"openai-provider-20260821-{arm_id}-usage-v1"
        )

        cursor.execute(
            """
            insert into benchmark.benchmark_usage_reconciliations (
                arm_run_id,
                reconciliation_version,
                configured_backend_model,
                provider_observed_model,
                model_identity_status,
                provider_ordinary_input_tokens,
                provider_cache_read_input_tokens,
                provider_cache_creation_input_tokens,
                provider_output_tokens,
                provider_request_count,
                provider_evidence_visible,
                selected_usage_authority,
                validation_status,
                notes,
                raw_metadata
            ) values (
                %s::uuid, %s, %s, %s, 'matched',
                %s, %s, %s, %s, %s,
                true, 'provider_aggregate_usage',
                'validated_exact', %s, %s
            )
            returning id
            """,
            (
                arm_run_id,
                usage_version,
                arm["backend_model"],
                arm["provider_model"],
                usage["ordinary_input_tokens"],
                usage["cache_read_input_tokens"],
                usage["cache_creation_input_tokens"],
                usage["output_tokens"],
                usage["request_count"],
                (
                    "Provider aggregate usage is authoritative for "
                    "this selected arm run. Cache creation is NULL "
                    "because OpenAI evidence does not expose that "
                    "Anthropic-style dimension."
                ),
                Jsonb(common_metadata),
            ),
        )
        usage_reconciliation_id = cursor.fetchone()[0]

        cursor.execute(
            """
            insert into benchmark.benchmark_usage_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, 'aggregate_usage')
            """,
            (
                usage_reconciliation_id,
                source_ids["usage"],
            ),
        )

        cost_reconciliation = arm["cost_reconciliation"]
        cost_version = (
            f"openai-provider-20260821-{arm_id}-cost-v1"
        )

        cursor.execute(
            """
            insert into benchmark.benchmark_cost_reconciliations (
                arm_run_id,
                reconciliation_version,
                harness_reported_cost_usd,
                provider_billed_cost_usd,
                selected_cost_usd,
                selected_cost_basis,
                selected_cost_relation,
                validation_status,
                provider_evidence_visible,
                notes,
                raw_metadata
            ) values (
                %s::uuid, %s, %s, %s, %s,
                'provider_billed',
                'exact',
                'validated_exact',
                true,
                %s,
                %s
            )
            returning id
            """,
            (
                arm_run_id,
                cost_version,
                Decimal(
                    cost_reconciliation[
                        "harness_reported_cost_usd"
                    ]
                ),
                Decimal(
                    cost_reconciliation[
                        "provider_billed_cost_usd"
                    ]
                ),
                Decimal(
                    cost_reconciliation[
                        "selected_cost_usd"
                    ]
                ),
                (
                    "Exact OpenAI provider-billed arm total "
                    "supersedes historical harness cost for current "
                    "comparative reporting without rewriting "
                    "historical benchmark records."
                ),
                Jsonb(common_metadata),
            ),
        )
        cost_reconciliation_id = cursor.fetchone()[0]

        cursor.execute(
            """
            insert into benchmark.benchmark_cost_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, 'billed')
            """,
            (
                cost_reconciliation_id,
                source_ids["cost"],
            ),
        )


def verify_inserted_state(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> dict[str, Any]:
    counts = target_table_counts(cursor)

    if counts != plan["write_counts"]:
        raise IntegrationSafetyError(
            "transactional OpenAI evidence counts do not match plan"
        )

    requested_ids = list(arm_run_ids.values())

    cursor.execute(
        """
        select
            arm.arm_id,
            usage.provider_ordinary_input_tokens,
            usage.provider_cache_read_input_tokens,
            usage.provider_cache_creation_input_tokens,
            usage.provider_output_tokens,
            usage.provider_request_count,
            usage.model_identity_status,
            usage.selected_usage_authority,
            usage.validation_status,
            usage.provider_evidence_visible,
            cost.provider_billed_cost_usd,
            cost.selected_cost_usd,
            cost.selected_cost_basis,
            cost.selected_cost_relation,
            cost.validation_status,
            cost.provider_evidence_visible
        from benchmark.benchmark_arm_runs arm_run
        join benchmark.benchmark_arms arm
          on arm.arm_id = arm_run.arm_id
        join benchmark.benchmark_usage_reconciliations usage
          on usage.arm_run_id = arm_run.id
         and usage.is_current
        join benchmark.benchmark_cost_reconciliations cost
          on cost.arm_run_id = arm_run.id
         and cost.is_current
        where arm_run.id = any(%s::uuid[])
        order by arm.arm_id
        """,
        (requested_ids,),
    )

    rows = cursor.fetchall()

    if len(rows) != len(ARM_CONTRACT):
        raise IntegrationSafetyError(
            "transactional OpenAI reconciliations are incomplete"
        )

    verified: dict[str, Any] = {}

    for row in rows:
        arm_id = str(row[0])
        expected = ARM_CONTRACT.get(arm_id)
        if expected is None:
            raise IntegrationSafetyError(
                "unexpected OpenAI arm in transactional verification"
            )

        if int(row[1]) != expected["uncached_input_tokens"]:
            raise IntegrationSafetyError(
                "ordinary input token verification failed"
            )
        if int(row[2]) != expected["cached_input_tokens"]:
            raise IntegrationSafetyError(
                "cache-read token verification failed"
            )
        if row[3] is not None:
            raise IntegrationSafetyError(
                "cache-creation evidence must remain NULL"
            )
        if int(row[4]) != expected["output_tokens"]:
            raise IntegrationSafetyError(
                "output token verification failed"
            )
        if int(row[5]) != expected["request_count"]:
            raise IntegrationSafetyError(
                "request count verification failed"
            )
        if row[6] != "matched":
            raise IntegrationSafetyError(
                "model identity verification failed"
            )
        if row[7] != "provider_aggregate_usage":
            raise IntegrationSafetyError(
                "usage authority verification failed"
            )
        if row[8] != "validated_exact" or row[9] is not True:
            raise IntegrationSafetyError(
                "usage validation verification failed"
            )
        if Decimal(row[10]) != expected[
            "provider_billed_cost_usd"
        ]:
            raise IntegrationSafetyError(
                "provider billed cost verification failed"
            )
        if Decimal(row[11]) != expected[
            "provider_billed_cost_usd"
        ]:
            raise IntegrationSafetyError(
                "selected cost verification failed"
            )
        if row[12] != "provider_billed":
            raise IntegrationSafetyError(
                "selected cost basis verification failed"
            )
        if row[13] != "exact":
            raise IntegrationSafetyError(
                "selected cost relation verification failed"
            )
        if row[14] != "validated_exact" or row[15] is not True:
            raise IntegrationSafetyError(
                "cost validation verification failed"
            )

        verified[arm_id] = {
            "usage_authority": row[7],
            "usage_validation": row[8],
            "selected_cost_usd": str(row[11]),
            "selected_cost_basis": row[12],
            "selected_cost_relation": row[13],
            "cost_validation": row[14],
        }

    return {
        "transaction_counts": counts,
        "arm_reconciliations": verified,
    }


def rollback_only(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg

    connection: Any = None

    try:
        diagnostics.enter("transaction_connection")
        connection = psycopg.connect(
            db_url,
            autocommit=False,
        )

        with connection.cursor() as cursor:
            diagnostics.enter("empty_target_preflight")
            before = target_table_counts(cursor)

            if any(before.values()):
                raise IntegrationSafetyError(
                    "provider evidence target tables are not empty"
                )

            diagnostics.enter("canonical_run_resolution")
            arm_run_ids = resolve_arm_runs(
                cursor,
                plan,
            )

            diagnostics.enter("transactional_insert")
            insert_plan(
                cursor,
                plan,
                arm_run_ids,
            )

            diagnostics.enter("transactional_verification")
            verification = verify_inserted_state(
                cursor,
                plan,
                arm_run_ids,
            )

        diagnostics.enter("rollback")
        connection.rollback()

    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter("second_connection_zero_persistence")

    observer = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with observer.cursor() as cursor:
            after = target_table_counts(cursor)
        observer.rollback()
    finally:
        observer.close()

    diagnostics.zero_persistence_counts.update(after)

    if any(after.values()):
        raise IntegrationSafetyError(
            "rollback-only OpenAI ingestion left persistent state"
        )

    return {
        "status": "passed",
        "mode": "rollback-only",
        "checks": {
            "reviewed_input_hashes": "pass",
            "canonical_run_resolution": "pass",
            "empty_target_preflight": "pass",
            "transactional_insert": "pass",
            "transactional_verification": "pass",
            "second_connection_zero_persistence": "pass",
        },
        "resolved_arm_run_ids": arm_run_ids,
        "verification": verification,
        "zero_persistence_counts": after,
    }


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--plan",
        action="store_true",
        help="Emit the reviewed normalized write plan without a database.",
    )
    group.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Insert and verify the reviewed plan inside a PostgreSQL "
            "transaction, then roll it back and prove zero persistence."
        ),
    )

    return parser.parse_args(argv)


def failure_payload(
    *,
    mode: str,
    diagnostics: Diagnostics,
    exc: BaseException,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "failed",
        "mode": mode,
        "failed_stage": diagnostics.stage,
        "error_type": type(exc).__name__,
        "zero_persistence_counts": dict(
            diagnostics.zero_persistence_counts
        ),
    }

    sqlstate = getattr(exc, "sqlstate", None)
    text = str(sqlstate or "")

    if len(text) == 5 and text.isalnum():
        result["sqlstate"] = text.upper()

    return result


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    diagnostics = Diagnostics()

    mode = "plan" if args.plan else "rollback-only"

    try:
        diagnostics.enter("plan")
        plan = build_plan()

        if args.plan:
            print(json.dumps(plan, sort_keys=True))
            return 0

        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise MissingEnvironmentError()

        result = rollback_only(
            plan,
            db_url,
            diagnostics,
        )

    except Exception as exc:
        print(
            json.dumps(
                failure_payload(
                    mode=mode,
                    diagnostics=diagnostics,
                    exc=exc,
                ),
                sort_keys=True,
            )
        )
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
