#!/usr/bin/env python3
"""Plan, verify, or apply Moonshot/Kimi Phase 3 provider-evidence ingestion."""

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

KIMI_SNAPSHOT = (
    ROOT / "results/phase3/supplemental/kimi_provider_evidence_snapshot_20260827.json"
)
CURRENT_RECONCILIATION = (
    ROOT / "results/phase3/reporting/"
    "phase3_current_arm_cost_reconciliation_20260825.csv"
)
EVIDENCE_MATRIX = (
    ROOT / "results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv"
)

REVIEWED_PLAN_SHA256 = (
    "c6ca40c1c0958373b87ff2298a71f7da69022c1a10a33087cd920c972f4594cb"
)
EXPECTED_SNAPSHOT_SHA256 = (
    "929d489496b730ac053a2fa57f8f5c8e1d5701905fd482be788c67913a909f1d"
)

ARM_CONTRACT: dict[str, dict[str, Any]] = {
    "router-kimi-k2.6": {
        "selected_run_label": ("router-kimi-k2.6/2026-06-28__13-28-55"),
        "backend_model": "kimi-k2.6",
        "trial_count": 60,
        "harness_input_tokens": 1_754_257,
        "harness_cache_tokens": 0,
        "harness_cache_miss_tokens": 1_754_257,
        "harness_output_tokens": 1_170_095,
        "selected_cost_usd": Decimal("6.34692415"),
        "historical_harness_cost_usd": Decimal("25.98573"),
        "cache_hit_rate": Decimal("0.16"),
        "cache_miss_rate": Decimal("0.95"),
        "output_rate": Decimal("4"),
    },
    "router-kimi-k3": {
        "selected_run_label": ("router-kimi-k3/2026-07-22__17-51-05"),
        "backend_model": "kimi-k3",
        "trial_count": 60,
        "harness_input_tokens": 35_753_434,
        "harness_cache_tokens": 34_309_120,
        "harness_cache_miss_tokens": 1_444_314,
        "harness_output_tokens": 796_315,
        "selected_cost_usd": Decimal("26.570403"),
        "historical_harness_cost_usd": Decimal("25.207213"),
        "cache_hit_rate": Decimal("0.30"),
        "cache_miss_rate": Decimal("3"),
        "output_rate": Decimal("15"),
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

INGESTION_LOCK_NAME = "cc-deepseek-bench:kimi-provider-evidence-ingestion:v1"


class EvidencePlanError(RuntimeError):
    pass


class IntegrationSafetyError(RuntimeError):
    pass


class MissingEnvironmentError(RuntimeError):
    pass


@dataclass
class Diagnostics:
    stage: str = "arguments"
    commit_state: str = "not_committed"
    target_state: str | None = None
    zero_persistence_counts: dict[str, int] = field(default_factory=dict)

    def enter(self, stage: str) -> None:
        self.stage = stage


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        return list(csv.DictReader(handle))


def money(value: Decimal) -> str:
    return format(value, "f")


def require_equal(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if actual != expected:
        raise EvidencePlanError(f"reviewed Kimi evidence mismatch: {label}")


def reconstruct_cost(
    *,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    output_tokens: int,
    spec: Mapping[str, Any],
) -> Decimal:
    return (
        Decimal(cache_hit_tokens) * spec["cache_hit_rate"]
        + Decimal(cache_miss_tokens) * spec["cache_miss_rate"]
        + Decimal(output_tokens) * spec["output_rate"]
    ) / Decimal(1_000_000)


def _source_format(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".json": "json",
        ".csv": "csv",
        ".tsv": "tsv",
        ".md": "markdown",
        ".py": "python",
    }.get(suffix, suffix.lstrip(".") or "text")


def verify_input_hashes(
    snapshot: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    actual_snapshot = sha256_path(KIMI_SNAPSHOT)
    if actual_snapshot != EXPECTED_SNAPSHOT_SHA256:
        raise EvidencePlanError("reviewed Kimi snapshot hash changed")

    if snapshot is None:
        snapshot = json.loads(KIMI_SNAPSHOT.read_text(encoding="utf-8"))

    actual: dict[str, str] = {
        str(KIMI_SNAPSHOT.relative_to(ROOT)): actual_snapshot,
    }

    source_rows = snapshot.get("provider_source_rows")
    provenance_rows = snapshot.get("provenance_only_sources")

    if not isinstance(source_rows, list):
        raise EvidencePlanError("Kimi snapshot provider sources are malformed")
    if not isinstance(provenance_rows, list):
        raise EvidencePlanError("Kimi snapshot provenance sources are malformed")

    for row in source_rows + provenance_rows:
        if not isinstance(row, dict):
            raise EvidencePlanError("Kimi snapshot source row is malformed")

        relative = row.get("path")
        expected = row.get("sha256")

        if not isinstance(relative, str) or not isinstance(expected, str):
            raise EvidencePlanError("Kimi snapshot source hash contract is malformed")

        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise EvidencePlanError("Kimi snapshot source escapes repository") from exc

        if not path.is_file():
            raise EvidencePlanError("reviewed Kimi input is missing")

        actual_hash = sha256_path(path)
        if actual_hash != expected:
            raise EvidencePlanError("reviewed Kimi input hashes changed")

        actual[relative] = actual_hash

    return actual


def _validate_snapshot(
    snapshot: Mapping[str, Any],
) -> None:
    require_equal(
        snapshot.get("schema_version"),
        1,
        "snapshot schema version",
    )
    require_equal(
        snapshot.get("evidence_version"),
        "kimi-provider-evidence-20260827-v1",
        "snapshot evidence version",
    )
    require_equal(
        snapshot.get("provider"),
        "moonshot-kimi",
        "snapshot provider",
    )
    require_equal(
        snapshot.get("reviewed_private_plan_sha256"),
        REVIEWED_PLAN_SHA256,
        "reviewed private plan SHA-256",
    )
    require_equal(
        snapshot.get("private_paths_retained"),
        False,
        "private path retention",
    )
    require_equal(
        snapshot.get("database_write_authorized"),
        False,
        "snapshot database authorization",
    )
    require_equal(
        snapshot.get("apply_authorized"),
        False,
        "snapshot apply authorization",
    )

    expected_principles = {
        "historical_results_frozen": True,
        "no_historical_raw_cost_rewrite": True,
        "no_missing_usage_synthesized_as_zero": True,
        "no_synthetic_provider_allocation": True,
        "duplicate_k3_export_counted_once": True,
        "k2_historical_context_not_selected_run_billing": True,
        "k3_provider_log_not_selected_run_allocation": True,
    }
    require_equal(
        snapshot.get("principles"),
        expected_principles,
        "normalization principles",
    )

    require_equal(
        snapshot.get("planned_row_counts"),
        {
            "benchmark_provider_evidence_sources": 6,
            "benchmark_provider_usage_evidence": 2,
            "benchmark_provider_pricing_snapshots": 2,
            "benchmark_provider_cost_evidence": 3,
            "benchmark_usage_reconciliations": 2,
            "benchmark_usage_reconciliation_sources": 6,
            "benchmark_cost_reconciliations": 2,
            "benchmark_cost_reconciliation_sources": 6,
            "benchmark_evidence_promotion_gates": 0,
        },
        "planned row cardinality",
    )

    selected = snapshot.get("selected_arms")
    if (
        not isinstance(selected, list)
        or len(selected) != 2
        or not all(isinstance(row, dict) for row in selected)
    ):
        raise EvidencePlanError("Kimi selected-arm snapshot is malformed")

    by_arm = {row["arm_id"]: row for row in selected}
    require_equal(
        set(by_arm),
        set(ARM_CONTRACT),
        "selected arm membership",
    )

    for arm_id, spec in ARM_CONTRACT.items():
        row = by_arm[arm_id]
        checks = {
            "run_label": spec["selected_run_label"],
            "configured_backend_model": spec["backend_model"],
            "provider_observed_selected_run_model": None,
            "harness_input_tokens": spec["harness_input_tokens"],
            "harness_cache_tokens": spec["harness_cache_tokens"],
            "harness_output_tokens": spec["harness_output_tokens"],
            "provider_selected_run_tokens": None,
            "selected_usage_authority": "harness_usage_validated",
            "usage_validation_status": "validated_qualified",
            "provider_billed_cost_usd": None,
            "provider_rate_reconstructed_cost_usd": money(spec["selected_cost_usd"]),
            "selected_cost_usd": money(spec["selected_cost_usd"]),
            "selected_cost_basis": "provider_rate_reconstructed_harness_usage_validated",
            "selected_cost_relation": "estimate",
            "cost_validation_status": "validated_qualified",
        }
        for key, expected in checks.items():
            require_equal(
                row.get(key),
                expected,
                f"{arm_id} snapshot {key}",
            )

    usage = snapshot.get("provider_usage_evidence")
    if not isinstance(usage, list) or len(usage) != 2:
        raise EvidencePlanError("Kimi provider usage snapshot is malformed")

    usage_by_id = {row["id"]: row for row in usage if isinstance(row, dict)}

    require_equal(
        usage_by_id["kimi_k2_6_historical_request_log"],
        {
            "id": "kimi_k2_6_historical_request_log",
            "provider_model": "kimi-k2.6",
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "request_count": 103,
            "window_start": "2026-06-04",
            "window_end": "2026-06-16",
            "ordinary_input_tokens": 1_545_150,
            "cache_read_input_tokens": 1_063_441,
            "output_tokens": 70_089,
            "total_input_tokens_including_cache": 2_608_591,
            "selected_run_allocable": False,
            "relation_to_selected_run": "predates_selected_run",
        },
        "K2.6 provider usage context",
    )

    require_equal(
        usage_by_id["kimi_k3_provider_request_log"],
        {
            "id": "kimi_k3_provider_request_log",
            "provider_model": "kimi-k3",
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "request_count": 1273,
            "window_start_text": "2026-07-22 22:29:03",
            "window_end_text": "2026-07-23 04:44:16",
            "timezone_retained": False,
            "ordinary_input_tokens": 1_654_986,
            "cache_read_input_tokens": 38_341_888,
            "output_tokens": 956_453,
            "total_input_tokens_including_cache": 39_996_874,
            "selected_run_allocable": False,
            "relation_to_selected_run": "window_overlaps_same_day_but_timezone_unproven",
        },
        "K3 provider usage context",
    )

    costs = snapshot.get("provider_cost_evidence")
    if not isinstance(costs, list) or len(costs) != 3:
        raise EvidencePlanError("Kimi provider cost snapshot is malformed")

    by_cost_id = {row["id"]: row for row in costs if isinstance(row, dict)}

    expected_costs = {
        "kimi_k2_6_dashboard_total": (
            "1.91830",
            "provider_dashboard_total",
            "provider_window",
        ),
        "kimi_k2_6_historical_rate_reconstruction": (
            "1.918399",
            "provider_rate_reconstruction",
            "model_window",
        ),
        "kimi_k3_provider_log_rate_reconstruction": (
            "30.8143194",
            "provider_rate_reconstruction",
            "model_window",
        ),
    }

    for key, (
        amount,
        kind,
        scope,
    ) in expected_costs.items():
        row = by_cost_id[key]
        require_equal(
            row.get("amount_usd"),
            amount,
            f"{key} amount",
        )
        require_equal(
            row.get("cost_kind"),
            kind,
            f"{key} kind",
        )
        require_equal(
            row.get("allocation_scope"),
            scope,
            f"{key} allocation scope",
        )
        require_equal(
            row.get("selected_run_allocable"),
            False,
            f"{key} selected-run allocation",
        )

    raw_provenance = snapshot.get("raw_provider_artifact_provenance")
    if not isinstance(raw_provenance, dict):
        raise EvidencePlanError("Kimi raw provider provenance is malformed")

    require_equal(
        raw_provenance["k2_6"]["raw_request_log_hash_retained"],
        False,
        "K2 raw request-log hash retention",
    )
    require_equal(
        raw_provenance["k3"]["duplicate_archives_are_identical"],
        True,
        "K3 duplicate export identity",
    )
    require_equal(
        raw_provenance["k3"]["count_as_independent_exports"],
        1,
        "K3 duplicate export count",
    )


def _validate_repository_reconciliation() -> None:
    current = {
        row["arm_id"]: row
        for row in read_csv(CURRENT_RECONCILIATION)
        if row.get("arm_id") in ARM_CONTRACT
    }
    matrix = {
        row["arm_id"]: row
        for row in read_csv(EVIDENCE_MATRIX)
        if row.get("arm_id") in ARM_CONTRACT
    }

    require_equal(
        set(current),
        set(ARM_CONTRACT),
        "current Kimi reconciliation arms",
    )
    require_equal(
        set(matrix),
        set(ARM_CONTRACT),
        "Kimi evidence-matrix arms",
    )

    for arm_id, spec in ARM_CONTRACT.items():
        current_row = current[arm_id]
        matrix_row = matrix[arm_id]

        for key, expected in {
            "selected_run_label": spec["selected_run_label"],
            "backend_model": spec["backend_model"],
            "provider_models": spec["backend_model"],
            "provider": "moonshot-kimi",
            "selected_cost_usd": money(spec["selected_cost_usd"]),
            "selected_cost_relation": "estimate",
            "selected_cost_basis": "provider_rate_reconstructed_selected_run",
            "provider_billed_cost_usd": "",
            "trial_count": "60",
            "complete_trial_cost_count": "60",
            "lower_bound_trial_count": "0",
            "confirmed_zero_cost_trial_count": "0",
            "historical_harness_recorded_cost_usd": money(
                spec["historical_harness_cost_usd"]
            ),
        }.items():
            require_equal(
                current_row.get(key, ""),
                expected,
                f"{arm_id} current reconciliation {key}",
            )

        for key, expected in {
            "selected_run_label": spec["selected_run_label"],
            "provider": "moonshot-kimi",
            "selected_cost_usd": money(spec["selected_cost_usd"]),
            "selected_cost_relation": "estimate",
            "selected_cost_basis": "provider_rate_reconstructed_selected_run",
            "trial_count": "60",
            "complete_trial_cost_count": "60",
            "unresolved_trial_count": "0",
            "selected_input_tokens": str(spec["harness_input_tokens"]),
            "selected_cache_tokens": str(spec["harness_cache_tokens"]),
            "selected_output_tokens": str(spec["harness_output_tokens"]),
        }.items():
            require_equal(
                matrix_row.get(key, ""),
                expected,
                f"{arm_id} evidence matrix {key}",
            )


def build_plan() -> dict[str, Any]:
    raw = KIMI_SNAPSHOT.read_text(encoding="utf-8")
    for forbidden in (
        ".run/review",
        ".secrets/",
        "SUPABASE_DB_URL",
        "MOONSHOT_API_KEY",
    ):
        if forbidden in raw:
            raise EvidencePlanError("sanitized Kimi snapshot contains private material")

    snapshot = json.loads(raw)
    _validate_snapshot(snapshot)
    hashes = verify_input_hashes(snapshot)
    _validate_repository_reconciliation()

    source_rows = snapshot["provider_source_rows"]
    source_by_id = {row["id"]: row for row in source_rows}

    sources: list[dict[str, Any]] = []

    for row in source_rows:
        raw_metadata = {
            "reviewed_private_plan_sha256": REVIEWED_PLAN_SHA256,
            "snapshot_source_id": row["id"],
            "snapshot_role": row["role"],
        }

        if "underlying_archive_sha256" in row:
            raw_metadata["underlying_archive_sha256"] = row["underlying_archive_sha256"]

        if "underlying_csv_sha256" in row:
            raw_metadata["underlying_csv_sha256"] = row["underlying_csv_sha256"]

        sources.append(
            {
                "source_key": row["id"],
                "provider": "moonshot-kimi",
                "evidence_kind": row["evidence_kind"],
                "source_scope": row["source_scope"],
                "provider_reference": row["path"],
                "source_sha256": row["sha256"],
                "source_format": _source_format(row["path"]),
                "integrity_status": "sha256_verified",
                "notes": row["role"],
                "raw_metadata": raw_metadata,
            }
        )

    pricing_plan = {row["id"]: row for row in snapshot["pricing_snapshots"]}

    pricing_snapshots = [
        {
            "pricing_key": "kimi-k2.6-reviewed-rates",
            "source_key": "kimi_k2_retained_pricing_record",
            "provider": "moonshot-kimi",
            "provider_model": "kimi-k2.6",
            "currency": "USD",
            "effective_from": None,
            "effective_until": None,
            "pricing_semantics": "cache_aware_input_plus_output",
            "pricing_rules": {
                "ordinary_input_usd_per_million": "0.95",
                "cached_input_usd_per_million": "0.16",
                "output_usd_per_million": "4",
                "reviewed_pricing_provenance": pricing_plan["kimi_k2_6_retained_rates"][
                    "provenance"
                ],
                "official_dated_provider_snapshot_retained": False,
            },
            "official_source_uri": None,
            "notes": (
                "Repository-retained K2.6 rate record. "
                "Historical Moonshot request-log usage "
                "reconstructs to $1.918399 and the "
                "provider dashboard reports $1.91830, "
                "which validates the retained rate formula "
                "for the historical window. No official "
                "dated provider pricing snapshot is retained."
            ),
            "raw_metadata": {},
        },
        {
            "pricing_key": "kimi-k3-reviewed-rates",
            "source_key": "kimi_k3_retained_pricing_record",
            "provider": "moonshot-kimi",
            "provider_model": "kimi-k3",
            "currency": "USD",
            "effective_from": None,
            "effective_until": None,
            "pricing_semantics": "cache_aware_input_plus_output",
            "pricing_rules": {
                "ordinary_input_usd_per_million": "3",
                "cached_input_usd_per_million": "0.30",
                "output_usd_per_million": "15",
                "repository_pricing_record_date": "2026-07-22",
                "reviewed_pricing_provenance": pricing_plan["kimi_k3_retained_rates"][
                    "provenance"
                ],
                "official_dated_provider_snapshot_retained": False,
            },
            "official_source_uri": None,
            "notes": (
                "Repository-retained K3 pricing record "
                "used for the July 22 selected-run "
                "reconstruction. The repository record date "
                "is not normalized as a verified provider "
                "effective date, and no official dated "
                "provider pricing snapshot is retained."
            ),
            "raw_metadata": {},
        },
    ]

    selected_runs = []

    for arm_id, spec in ARM_CONTRACT.items():
        selected_runs.append(
            {
                "arm_id": arm_id,
                "selected_run_label": spec["selected_run_label"],
                "backend_model": spec["backend_model"],
                "trial_count": spec["trial_count"],
                "harness_input_tokens": spec["harness_input_tokens"],
                "harness_cache_tokens": spec["harness_cache_tokens"],
                "harness_cache_miss_tokens": spec["harness_cache_miss_tokens"],
                "harness_output_tokens": spec["harness_output_tokens"],
                "selected_cost_usd": money(spec["selected_cost_usd"]),
            }
        )

    snapshot_usage = {row["id"]: row for row in snapshot["provider_usage_evidence"]}

    k2_usage = snapshot_usage["kimi_k2_6_historical_request_log"]
    k3_usage = snapshot_usage["kimi_k3_provider_request_log"]

    provider_usage_evidence = [
        {
            "source_key": "kimi_k2_historical_provider_context",
            "arm_run_id": None,
            "trial_id": None,
            "provider_request_id": None,
            "provider_model": "kimi-k2.6",
            "request_started_at": None,
            "request_finished_at": None,
            "ordinary_input_tokens": k2_usage["ordinary_input_tokens"],
            "cache_read_input_tokens": k2_usage["cache_read_input_tokens"],
            "cache_creation_input_tokens": None,
            "output_tokens": k2_usage["output_tokens"],
            "request_count": k2_usage["request_count"],
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "notes": (
                "Historical Moonshot K2.6 aggregate "
                "request-log usage from June 4 through "
                "June 16. It predates the selected June 28 "
                "run and is not selected-run usage."
            ),
            "raw_metadata": {
                "window_start_date": k2_usage["window_start"],
                "window_end_date": k2_usage["window_end"],
                "total_input_tokens_including_cache": k2_usage[
                    "total_input_tokens_including_cache"
                ],
                "selected_run_allocable": False,
                "relation_to_selected_run": "predates_selected_run",
                "raw_request_log_hash_retained": False,
            },
        },
        {
            "source_key": "kimi_k3_provider_log_context",
            "arm_run_id": None,
            "trial_id": None,
            "provider_request_id": None,
            "provider_model": "kimi-k3",
            "request_started_at": None,
            "request_finished_at": None,
            "ordinary_input_tokens": k3_usage["ordinary_input_tokens"],
            "cache_read_input_tokens": k3_usage["cache_read_input_tokens"],
            "cache_creation_input_tokens": None,
            "output_tokens": k3_usage["output_tokens"],
            "request_count": k3_usage["request_count"],
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "notes": (
                "First-party Moonshot K3 aggregate "
                "request-log usage. The retained timestamp "
                "strings lack a proven timezone and there is "
                "no request-to-selected-run join, so the DB "
                "timestamp fields and selected-run allocation "
                "remain NULL."
            ),
            "raw_metadata": {
                "window_start_text": k3_usage["window_start_text"],
                "window_end_text": k3_usage["window_end_text"],
                "timezone_retained": False,
                "total_input_tokens_including_cache": k3_usage[
                    "total_input_tokens_including_cache"
                ],
                "selected_run_allocable": False,
                "relation_to_selected_run": k3_usage["relation_to_selected_run"],
                "underlying_archive_sha256": source_by_id[
                    "kimi_k3_provider_log_context"
                ]["underlying_archive_sha256"],
                "underlying_csv_sha256": source_by_id["kimi_k3_provider_log_context"][
                    "underlying_csv_sha256"
                ],
                "duplicate_archives_counted_as": 1,
            },
        },
    ]

    cost_snapshot = {row["id"]: row for row in snapshot["provider_cost_evidence"]}

    provider_cost_evidence = [
        {
            "source_key": "kimi_k2_historical_provider_context",
            "arm_run_id": None,
            "trial_id": None,
            "pricing_snapshot_key": None,
            "provider_model": None,
            "cost_kind": "provider_dashboard_total",
            "amount_usd": cost_snapshot["kimi_k2_6_dashboard_total"]["amount_usd"],
            "currency": "USD",
            "allocation_scope": "provider_window",
            "completeness_status": "aggregate_only",
            "notes": (
                "Moonshot dashboard Total Consumption "
                "for the historical K2.6 request-log "
                "window. It predates the selected June 28 "
                "run and is not selected-run billing."
            ),
            "raw_metadata": {
                "selected_run_allocable": False,
                "relation_to_selected_run": "predates_selected_run",
                "historical_window": "2026-06-04_to_2026-06-16",
            },
        },
        {
            "source_key": "kimi_k2_historical_provider_context",
            "arm_run_id": None,
            "trial_id": None,
            "pricing_snapshot_key": "kimi-k2.6-reviewed-rates",
            "provider_model": "kimi-k2.6",
            "cost_kind": "provider_rate_reconstruction",
            "amount_usd": cost_snapshot["kimi_k2_6_historical_rate_reconstruction"][
                "amount_usd"
            ],
            "currency": "USD",
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "notes": (
                "Historical K2.6 request-log usage "
                "reconstructed with the retained rates. "
                "The result independently matches the "
                "$1.91830 dashboard total within rounding, "
                "but it is not selected-run billing."
            ),
            "raw_metadata": {
                "selected_run_allocable": False,
                "relation_to_selected_run": "predates_selected_run",
            },
        },
        {
            "source_key": "kimi_k3_provider_log_context",
            "arm_run_id": None,
            "trial_id": None,
            "pricing_snapshot_key": "kimi-k3-reviewed-rates",
            "provider_model": "kimi-k3",
            "cost_kind": "provider_rate_reconstruction",
            "amount_usd": cost_snapshot["kimi_k3_provider_log_rate_reconstruction"][
                "amount_usd"
            ],
            "currency": "USD",
            "allocation_scope": "model_window",
            "completeness_status": "complete",
            "notes": (
                "K3 first-party provider request-log "
                "aggregate reconstructed under the retained "
                "K3 rate constants. It is not billed-dollar "
                "evidence and cannot be allocated to the "
                "selected run because no request-to-run join "
                "or proven timezone is retained."
            ),
            "raw_metadata": {
                "selected_run_allocable": False,
                "provider_billed": False,
                "relation_to_selected_run": "allocation_low_confidence_timezone_unproven",
                "excess_vs_selected_usd": "4.2439164",
            },
        },
    ]

    usage_reconciliations = []
    cost_reconciliations = []

    snapshot_selected = {row["arm_id"]: row for row in snapshot["selected_arms"]}

    for arm_id, spec in ARM_CONTRACT.items():
        selected = snapshot_selected[arm_id]
        limitations = list(selected["limitations"])

        usage_reconciliations.append(
            {
                "arm_id": arm_id,
                "reconciliation_version": "kimi-provider-evidence-v1",
                "is_current": True,
                "harness_name": "claude-code",
                "harness_version": None,
                "configured_route_model": arm_id,
                "configured_backend_model": spec["backend_model"],
                "harness_observed_model": None,
                "provider_observed_model": None,
                "model_identity_status": "matched",
                "harness_input_tokens": spec["harness_input_tokens"],
                "harness_cache_tokens": spec["harness_cache_tokens"],
                "harness_output_tokens": spec["harness_output_tokens"],
                "provider_ordinary_input_tokens": None,
                "provider_cache_read_input_tokens": None,
                "provider_cache_creation_input_tokens": None,
                "provider_output_tokens": None,
                "provider_request_count": None,
                "matched_provider_request_count": None,
                "unallocated_provider_request_count": None,
                "provider_evidence_visible": True,
                "selected_usage_authority": "harness_usage_validated",
                "validation_status": "validated_qualified",
                "limitation_codes": limitations,
                "notes": (
                    "Selected-run usage authority is the "
                    "reviewed harness aggregate. Provider "
                    "request-log evidence is retained as "
                    "historical/model-window context only "
                    "and is not copied into selected-run "
                    "provider token fields. "
                    "provider_observed_model remains NULL; "
                    "model_identity_status=matched denotes "
                    "the reviewed configured/backend identity, "
                    "not an independent selected-run provider "
                    "observation."
                ),
                "raw_metadata": {
                    "provider_context_not_selected_run_usage": True,
                },
            }
        )

        cost_reconciliations.append(
            {
                "arm_id": arm_id,
                "reconciliation_version": "kimi-provider-evidence-v1",
                "is_current": True,
                "harness_name": "claude-code",
                "harness_version": None,
                "harness_reported_cost_usd": money(spec["historical_harness_cost_usd"]),
                "provider_billed_cost_usd": None,
                "provider_rate_reconstructed_cost_usd": money(
                    spec["selected_cost_usd"]
                ),
                "selected_cost_usd": money(spec["selected_cost_usd"]),
                "selected_cost_basis": "provider_rate_reconstructed_harness_usage_validated",
                "selected_cost_relation": "estimate",
                "validation_status": "validated_qualified",
                "provider_evidence_visible": True,
                "pricing_snapshot_key": (
                    "kimi-k2.6-reviewed-rates"
                    if arm_id == "router-kimi-k2.6"
                    else "kimi-k3-reviewed-rates"
                ),
                "limitation_codes": limitations,
                "notes": (
                    "Selected cost is reconstructed from "
                    "the reviewed selected-run harness token "
                    "aggregate and retained Kimi rate "
                    "constants. provider_billed_cost remains "
                    "NULL. Provider-window request-log and "
                    "dashboard/reconstructed costs are "
                    "context only and are not synthetically "
                    "allocated to the selected run."
                ),
                "raw_metadata": {
                    "provider_context_not_selected_run_billing": True,
                },
            }
        )

    usage_links = (
        [
            {
                "arm_id": arm_id,
                "source_key": "kimi_provider_evidence_matrix",
                "evidence_role": "aggregate_usage",
            }
            for arm_id in ARM_CONTRACT
        ]
        + [
            {
                "arm_id": arm_id,
                "source_key": "kimi_current_reconciliation",
                "evidence_role": "model_identity",
            }
            for arm_id in ARM_CONTRACT
        ]
        + [
            {
                "arm_id": "router-kimi-k2.6",
                "source_key": "kimi_k2_historical_provider_context",
                "evidence_role": "context",
            },
            {
                "arm_id": "router-kimi-k3",
                "source_key": "kimi_k3_provider_log_context",
                "evidence_role": "context",
            },
        ]
    )

    cost_links = [
        {
            "arm_id": arm_id,
            "source_key": "kimi_current_reconciliation",
            "evidence_role": "rate_reconstruction",
        }
        for arm_id in ARM_CONTRACT
    ] + [
        {
            "arm_id": "router-kimi-k2.6",
            "source_key": "kimi_k2_retained_pricing_record",
            "evidence_role": "pricing",
        },
        {
            "arm_id": "router-kimi-k3",
            "source_key": "kimi_k3_retained_pricing_record",
            "evidence_role": "pricing",
        },
        {
            "arm_id": "router-kimi-k2.6",
            "source_key": "kimi_k2_historical_provider_context",
            "evidence_role": "context",
        },
        {
            "arm_id": "router-kimi-k3",
            "source_key": "kimi_k3_provider_log_context",
            "evidence_role": "context",
        },
    ]

    write_counts = {
        "benchmark_provider_evidence_sources": len(sources),
        "benchmark_provider_usage_evidence": len(provider_usage_evidence),
        "benchmark_provider_pricing_snapshots": len(pricing_snapshots),
        "benchmark_provider_cost_evidence": len(provider_cost_evidence),
        "benchmark_usage_reconciliations": len(usage_reconciliations),
        "benchmark_usage_reconciliation_sources": len(usage_links),
        "benchmark_cost_reconciliations": len(cost_reconciliations),
        "benchmark_cost_reconciliation_sources": len(cost_links),
        "benchmark_evidence_promotion_gates": 0,
    }

    require_equal(
        write_counts,
        snapshot["planned_row_counts"],
        "planned write counts",
    )

    for selected in selected_runs:
        spec = ARM_CONTRACT[selected["arm_id"]]
        reconstructed = reconstruct_cost(
            cache_hit_tokens=(selected["harness_cache_tokens"]),
            cache_miss_tokens=(selected["harness_cache_miss_tokens"]),
            output_tokens=(selected["harness_output_tokens"]),
            spec=spec,
        )
        require_equal(
            reconstructed,
            spec["selected_cost_usd"],
            f"{selected['arm_id']} rate arithmetic",
        )

    excluded_evidence = [
        {
            "evidence": "k2_historical_request_log_as_selected_run_usage",
            "reason": "historical provider window predates the selected run",
            "normalized_as_selected_provider_usage": False,
        },
        {
            "evidence": "k2_dashboard_total_as_selected_run_bill",
            "reason": "historical dashboard total predates the selected run",
            "normalized_as_selected_provider_billing": False,
        },
        {
            "evidence": "k3_provider_log_as_selected_run_usage",
            "reason": "no request-to-run join and retained timestamps lack proven timezone",
            "normalized_as_selected_provider_usage": False,
        },
        {
            "evidence": "k3_provider_log_rate_reconstruction_as_billed_cost",
            "reason": "request log has no charged-dollar field and is not invoice-level evidence",
            "normalized_as_selected_provider_billing": False,
        },
        {
            "evidence": "duplicate_k3_export_as_second_independent_source",
            "reason": "reviewed archives are byte-identical",
            "counted_as_independent_exports": 1,
        },
        {
            "evidence": "configured_model_as_provider_observed_model",
            "reason": "selected-run provider model observation is unavailable",
            "provider_observed_model_populated": False,
        },
    ]

    return {
        "schema_version": 1,
        "plan_version": "kimi-provider-evidence-v1",
        "provider": "moonshot-kimi",
        "reviewed_plan_sha256": REVIEWED_PLAN_SHA256,
        "reviewed_input_hashes": hashes,
        "sources": sources,
        "pricing_snapshots": pricing_snapshots,
        "provider_usage_evidence": provider_usage_evidence,
        "provider_cost_evidence": provider_cost_evidence,
        "selected_runs": selected_runs,
        "usage_reconciliations": usage_reconciliations,
        "usage_reconciliation_source_links": usage_links,
        "cost_reconciliations": cost_reconciliations,
        "cost_reconciliation_source_links": cost_links,
        "excluded_evidence": excluded_evidence,
        "write_counts": write_counts,
    }


def _selected_filter(
    plan: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    arm_ids = [row["arm_id"] for row in plan["selected_runs"]]
    labels = [row["selected_run_label"] for row in plan["selected_runs"]]
    return arm_ids, labels


def target_table_counts(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, int]:
    provider = plan["provider"]
    arm_ids, labels = _selected_filter(plan)
    counts: dict[str, int] = {}

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_evidence_sources
        where provider = %s
        """,
        (provider,),
    )
    counts["benchmark_provider_evidence_sources"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = %s
        """,
        (provider,),
    )
    counts["benchmark_provider_usage_evidence"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_pricing_snapshots
        where provider = %s
        """,
        (provider,),
    )
    counts["benchmark_provider_pricing_snapshots"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_cost_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = %s
        """,
        (provider,),
    )
    counts["benchmark_provider_cost_evidence"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_usage_reconciliations reconciliation
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = any(%s::text[])
          and benchmark_run.run_label = any(%s::text[])
        """,
        (arm_ids, labels),
    )
    counts["benchmark_usage_reconciliations"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_usage_reconciliation_sources link
        join benchmark.benchmark_usage_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = any(%s::text[])
          and benchmark_run.run_label = any(%s::text[])
        """,
        (arm_ids, labels),
    )
    counts["benchmark_usage_reconciliation_sources"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_cost_reconciliations reconciliation
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = any(%s::text[])
          and benchmark_run.run_label = any(%s::text[])
        """,
        (arm_ids, labels),
    )
    counts["benchmark_cost_reconciliations"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_cost_reconciliation_sources link
        join benchmark.benchmark_cost_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = any(%s::text[])
          and benchmark_run.run_label = any(%s::text[])
        """,
        (arm_ids, labels),
    )
    counts["benchmark_cost_reconciliation_sources"] = int(cursor.fetchone()[0])

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_evidence_promotion_gates gate
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = gate.source_arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where gate.arm_id = any(%s::text[])
          and benchmark_run.run_label = any(%s::text[])
        """,
        (arm_ids, labels),
    )
    counts["benchmark_evidence_promotion_gates"] = int(cursor.fetchone()[0])

    return counts


def inspect_target_state(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    counts = target_table_counts(
        cursor,
        plan,
    )

    if not any(counts.values()):
        return {
            "state": "kimi_empty",
            "counts": counts,
        }

    if counts != plan["write_counts"]:
        return {
            "state": "partial_or_unexpected",
            "counts": counts,
            "reason": "unexpected_table_counts",
        }

    try:
        arm_run_ids = resolve_arm_runs(
            cursor,
            plan,
        )
        reconciliation = verify_inserted_state(
            cursor,
            plan,
            arm_run_ids,
        )
        provider = verify_provider_evidence_details(
            cursor,
            plan,
            arm_run_ids,
        )
    except Exception as exc:
        return {
            "state": "partial_or_unexpected",
            "counts": counts,
            "reason": "content_verification_failed",
            "verification_error_type": type(exc).__name__,
        }

    return {
        "state": "exact_kimi_state",
        "counts": counts,
        "resolved_arm_run_ids": arm_run_ids,
        "reconciliation_verification": reconciliation,
        "provider_verification": provider,
    }


def resolve_arm_runs(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, str]:
    labels = [row["selected_run_label"] for row in plan["selected_runs"]]

    cursor.execute(
        """
        select
            arm_run.id::text,
            arm_run.arm_id,
            benchmark_run.run_label,
            arm_run.suite_id,
            arm_run.logical_mode,
            arm_run.storage_mode,
            arm_run.n_trials,
            arm_run.input_tokens,
            arm_run.cache_tokens,
            arm_run.output_tokens
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
        by_label.setdefault(
            str(row[2]),
            [],
        ).append(row)

    resolved: dict[str, str] = {}

    for selected in plan["selected_runs"]:
        arm_id = selected["arm_id"]
        label = selected["selected_run_label"]
        matches = by_label.get(label, [])

        if len(matches) != 1:
            raise IntegrationSafetyError(
                "selected Kimi run does not resolve exactly once"
            )

        (
            arm_run_id,
            stored_arm_id,
            _run_label,
            suite_id,
            logical_mode,
            storage_mode,
            n_trials,
            input_tokens,
            cache_tokens,
            output_tokens,
        ) = matches[0]

        if stored_arm_id != arm_id:
            raise IntegrationSafetyError("selected Kimi run resolves to wrong arm")
        if suite_id != "phase3-full-20":
            raise IntegrationSafetyError("selected Kimi run resolves to wrong suite")
        if logical_mode != "full":
            raise IntegrationSafetyError("selected Kimi run is not logical full mode")
        if storage_mode != "raw":
            raise IntegrationSafetyError("selected Kimi run is not raw storage mode")
        if int(n_trials) != int(selected["trial_count"]):
            raise IntegrationSafetyError("selected Kimi run has unexpected trial count")

        geometry = {
            "harness_input_tokens": int(input_tokens),
            "harness_cache_tokens": int(cache_tokens),
            "harness_output_tokens": int(output_tokens),
        }

        expected_geometry = {
            key: int(selected[key])
            for key in (
                "harness_input_tokens",
                "harness_cache_tokens",
                "harness_output_tokens",
            )
        }

        if geometry != expected_geometry:
            raise IntegrationSafetyError("selected Kimi run token geometry changed")

        cache_miss_tokens = (
            geometry["harness_input_tokens"] - geometry["harness_cache_tokens"]
        )

        if cache_miss_tokens != int(selected["harness_cache_miss_tokens"]):
            raise IntegrationSafetyError(
                "selected Kimi run cache-miss geometry changed"
            )

        spec = ARM_CONTRACT[arm_id]
        reconstructed = reconstruct_cost(
            cache_hit_tokens=(geometry["harness_cache_tokens"]),
            cache_miss_tokens=cache_miss_tokens,
            output_tokens=(geometry["harness_output_tokens"]),
            spec=spec,
        )

        if reconstructed != Decimal(selected["selected_cost_usd"]):
            raise IntegrationSafetyError("selected Kimi rate reconstruction changed")

        resolved[arm_id] = str(arm_run_id)

    return resolved


def acquire_ingestion_lock(
    cursor: Any,
) -> None:
    cursor.execute(
        """
        select pg_advisory_xact_lock(
            hashtextextended(%s, 0)
        )
        """,
        (INGESTION_LOCK_NAME,),
    )
    cursor.fetchone()


def insert_plan(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> None:
    from psycopg.types.json import Jsonb

    source_ids: dict[str, Any] = {}
    pricing_ids: dict[str, Any] = {}
    usage_reconciliation_ids: dict[str, Any] = {}
    cost_reconciliation_ids: dict[str, Any] = {}

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
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
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
                Jsonb(
                    source.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )
        source_ids[source["source_key"]] = cursor.fetchone()[0]

    for snapshot in plan["pricing_snapshots"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_provider_pricing_snapshots (
                source_id,
                provider,
                provider_model,
                currency,
                effective_from,
                effective_until,
                pricing_semantics,
                pricing_rules,
                official_source_uri,
                notes,
                raw_metadata
            ) values (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            returning id
            """,
            (
                source_ids[snapshot["source_key"]],
                snapshot["provider"],
                snapshot["provider_model"],
                snapshot["currency"],
                snapshot["effective_from"],
                snapshot["effective_until"],
                snapshot["pricing_semantics"],
                Jsonb(snapshot["pricing_rules"]),
                snapshot["official_source_uri"],
                snapshot["notes"],
                Jsonb(
                    snapshot.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )
        pricing_ids[snapshot["pricing_key"]] = cursor.fetchone()[0]

    for evidence in plan["provider_usage_evidence"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_provider_usage_evidence (
                source_id,
                arm_run_id,
                trial_id,
                provider_request_id,
                provider_model,
                request_started_at,
                request_finished_at,
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
                %s, %s::uuid, %s::uuid, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                source_ids[evidence["source_key"]],
                evidence["arm_run_id"],
                evidence["trial_id"],
                evidence["provider_request_id"],
                evidence["provider_model"],
                evidence["request_started_at"],
                evidence["request_finished_at"],
                evidence["ordinary_input_tokens"],
                evidence["cache_read_input_tokens"],
                evidence["cache_creation_input_tokens"],
                evidence["output_tokens"],
                evidence["request_count"],
                evidence["allocation_scope"],
                evidence["completeness_status"],
                evidence["notes"],
                Jsonb(evidence["raw_metadata"]),
            ),
        )

    for evidence in plan["provider_cost_evidence"]:
        pricing_snapshot_id = None
        pricing_key = evidence["pricing_snapshot_key"]

        if pricing_key is not None:
            pricing_snapshot_id = pricing_ids[pricing_key]

        cursor.execute(
            """
            insert into benchmark.benchmark_provider_cost_evidence (
                source_id,
                arm_run_id,
                trial_id,
                pricing_snapshot_id,
                provider_model,
                cost_kind,
                amount_usd,
                currency,
                allocation_scope,
                completeness_status,
                notes,
                raw_metadata
            ) values (
                %s, %s::uuid, %s::uuid, %s::uuid,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                source_ids[evidence["source_key"]],
                evidence["arm_run_id"],
                evidence["trial_id"],
                pricing_snapshot_id,
                evidence["provider_model"],
                evidence["cost_kind"],
                Decimal(evidence["amount_usd"]),
                evidence["currency"],
                evidence["allocation_scope"],
                evidence["completeness_status"],
                evidence["notes"],
                Jsonb(evidence["raw_metadata"]),
            ),
        )

    for reconciliation in plan["usage_reconciliations"]:
        arm_id = reconciliation["arm_id"]

        cursor.execute(
            """
            insert into benchmark.benchmark_usage_reconciliations (
                arm_run_id,
                reconciliation_version,
                is_current,
                harness_name,
                harness_version,
                configured_route_model,
                configured_backend_model,
                harness_observed_model,
                provider_observed_model,
                model_identity_status,
                harness_input_tokens,
                harness_cache_tokens,
                harness_output_tokens,
                provider_ordinary_input_tokens,
                provider_cache_read_input_tokens,
                provider_cache_creation_input_tokens,
                provider_output_tokens,
                provider_request_count,
                matched_provider_request_count,
                unallocated_provider_request_count,
                provider_evidence_visible,
                selected_usage_authority,
                validation_status,
                limitation_codes,
                notes,
                raw_metadata
            ) values (
                %s::uuid, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s::text[], %s, %s
            )
            returning id
            """,
            (
                arm_run_ids[arm_id],
                reconciliation["reconciliation_version"],
                reconciliation["is_current"],
                reconciliation["harness_name"],
                reconciliation["harness_version"],
                reconciliation["configured_route_model"],
                reconciliation["configured_backend_model"],
                reconciliation["harness_observed_model"],
                reconciliation["provider_observed_model"],
                reconciliation["model_identity_status"],
                reconciliation["harness_input_tokens"],
                reconciliation["harness_cache_tokens"],
                reconciliation["harness_output_tokens"],
                reconciliation["provider_ordinary_input_tokens"],
                reconciliation["provider_cache_read_input_tokens"],
                reconciliation["provider_cache_creation_input_tokens"],
                reconciliation["provider_output_tokens"],
                reconciliation["provider_request_count"],
                reconciliation["matched_provider_request_count"],
                reconciliation["unallocated_provider_request_count"],
                reconciliation["provider_evidence_visible"],
                reconciliation["selected_usage_authority"],
                reconciliation["validation_status"],
                reconciliation["limitation_codes"],
                reconciliation["notes"],
                Jsonb(
                    reconciliation.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )
        usage_reconciliation_ids[arm_id] = cursor.fetchone()[0]

    for link in plan["usage_reconciliation_source_links"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_usage_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, %s)
            """,
            (
                usage_reconciliation_ids[link["arm_id"]],
                source_ids[link["source_key"]],
                link["evidence_role"],
            ),
        )

    for reconciliation in plan["cost_reconciliations"]:
        arm_id = reconciliation["arm_id"]
        pricing_snapshot_id = pricing_ids[reconciliation["pricing_snapshot_key"]]

        cursor.execute(
            """
            insert into benchmark.benchmark_cost_reconciliations (
                arm_run_id,
                reconciliation_version,
                is_current,
                harness_name,
                harness_version,
                harness_reported_cost_usd,
                provider_billed_cost_usd,
                provider_rate_reconstructed_cost_usd,
                selected_cost_usd,
                selected_cost_basis,
                selected_cost_relation,
                validation_status,
                provider_evidence_visible,
                pricing_snapshot_id,
                limitation_codes,
                notes,
                raw_metadata
            ) values (
                %s::uuid, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s::uuid,
                %s::text[], %s, %s
            )
            returning id
            """,
            (
                arm_run_ids[arm_id],
                reconciliation["reconciliation_version"],
                reconciliation["is_current"],
                reconciliation["harness_name"],
                reconciliation["harness_version"],
                Decimal(reconciliation["harness_reported_cost_usd"]),
                reconciliation["provider_billed_cost_usd"],
                Decimal(reconciliation["provider_rate_reconstructed_cost_usd"]),
                Decimal(reconciliation["selected_cost_usd"]),
                reconciliation["selected_cost_basis"],
                reconciliation["selected_cost_relation"],
                reconciliation["validation_status"],
                reconciliation["provider_evidence_visible"],
                pricing_snapshot_id,
                reconciliation["limitation_codes"],
                reconciliation["notes"],
                Jsonb(
                    reconciliation.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )
        cost_reconciliation_ids[arm_id] = cursor.fetchone()[0]

    for link in plan["cost_reconciliation_source_links"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_cost_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, %s)
            """,
            (
                cost_reconciliation_ids[link["arm_id"]],
                source_ids[link["source_key"]],
                link["evidence_role"],
            ),
        )


def verify_inserted_state(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> dict[str, Any]:
    counts = target_table_counts(
        cursor,
        plan,
    )

    if counts != plan["write_counts"]:
        raise IntegrationSafetyError(
            "transactional Kimi evidence counts do not match reviewed plan"
        )

    requested_ids = list(arm_run_ids.values())

    usage_plan = {row["arm_id"]: row for row in plan["usage_reconciliations"]}
    cost_plan = {row["arm_id"]: row for row in plan["cost_reconciliations"]}

    cursor.execute(
        """
        select
            arm_run.arm_id,
            usage.reconciliation_version,
            usage.is_current,
            usage.harness_name,
            usage.harness_version,
            usage.configured_route_model,
            usage.configured_backend_model,
            usage.harness_observed_model,
            usage.provider_observed_model,
            usage.model_identity_status,
            usage.harness_input_tokens,
            usage.harness_cache_tokens,
            usage.harness_output_tokens,
            usage.provider_ordinary_input_tokens,
            usage.provider_cache_read_input_tokens,
            usage.provider_cache_creation_input_tokens,
            usage.provider_output_tokens,
            usage.provider_request_count,
            usage.matched_provider_request_count,
            usage.unallocated_provider_request_count,
            usage.provider_evidence_visible,
            usage.selected_usage_authority,
            usage.validation_status,
            usage.limitation_codes
        from benchmark.benchmark_usage_reconciliations usage
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = usage.arm_run_id
        where usage.arm_run_id = any(%s::uuid[])
          and usage.is_current
        order by arm_run.arm_id
        """,
        (requested_ids,),
    )

    usage_rows = cursor.fetchall()

    if len(usage_rows) != len(usage_plan):
        raise IntegrationSafetyError(
            "transactional Kimi usage reconciliations are incomplete"
        )

    verified_usage: dict[str, Any] = {}

    for row in usage_rows:
        arm_id = str(row[0])
        expected = usage_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError("unexpected Kimi usage reconciliation arm")

        observed = {
            "reconciliation_version": row[1],
            "is_current": row[2],
            "harness_name": row[3],
            "harness_version": row[4],
            "configured_route_model": row[5],
            "configured_backend_model": row[6],
            "harness_observed_model": row[7],
            "provider_observed_model": row[8],
            "model_identity_status": row[9],
            "harness_input_tokens": row[10],
            "harness_cache_tokens": row[11],
            "harness_output_tokens": row[12],
            "provider_ordinary_input_tokens": row[13],
            "provider_cache_read_input_tokens": row[14],
            "provider_cache_creation_input_tokens": row[15],
            "provider_output_tokens": row[16],
            "provider_request_count": row[17],
            "matched_provider_request_count": row[18],
            "unallocated_provider_request_count": row[19],
            "provider_evidence_visible": row[20],
            "selected_usage_authority": row[21],
            "validation_status": row[22],
            "limitation_codes": list(row[23]),
        }

        for key, value in observed.items():
            if value != expected[key]:
                raise IntegrationSafetyError(
                    f"{arm_id} Kimi usage verification failed: {key}"
                )

        verified_usage[arm_id] = {
            "selected_usage_authority": row[21],
            "validation_status": row[22],
        }

    cursor.execute(
        """
        select
            arm_run.arm_id,
            cost.reconciliation_version,
            cost.is_current,
            cost.harness_name,
            cost.harness_version,
            cost.harness_reported_cost_usd,
            cost.provider_billed_cost_usd,
            cost.provider_rate_reconstructed_cost_usd,
            cost.selected_cost_usd,
            cost.selected_cost_basis,
            cost.selected_cost_relation,
            cost.validation_status,
            cost.provider_evidence_visible,
            cost.limitation_codes,
            pricing.provider,
            pricing.provider_model
        from benchmark.benchmark_cost_reconciliations cost
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = cost.arm_run_id
        left join benchmark.benchmark_provider_pricing_snapshots pricing
          on pricing.id = cost.pricing_snapshot_id
        where cost.arm_run_id = any(%s::uuid[])
          and cost.is_current
        order by arm_run.arm_id
        """,
        (requested_ids,),
    )

    cost_rows = cursor.fetchall()

    if len(cost_rows) != len(cost_plan):
        raise IntegrationSafetyError(
            "transactional Kimi cost reconciliations are incomplete"
        )

    verified_cost: dict[str, Any] = {}

    for row in cost_rows:
        arm_id = str(row[0])
        expected = cost_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError("unexpected Kimi cost reconciliation arm")

        for key, value in {
            "harness_reported_cost_usd": row[5],
            "provider_rate_reconstructed_cost_usd": row[7],
            "selected_cost_usd": row[8],
        }.items():
            if Decimal(value) != Decimal(expected[key]):
                raise IntegrationSafetyError(
                    f"{arm_id} Kimi cost verification failed: {key}"
                )

        if row[6] is not None:
            raise IntegrationSafetyError(
                f"{arm_id} provider billed cost must remain NULL"
            )

        for key, value in {
            "reconciliation_version": row[1],
            "is_current": row[2],
            "harness_name": row[3],
            "harness_version": row[4],
            "selected_cost_basis": row[9],
            "selected_cost_relation": row[10],
            "validation_status": row[11],
            "provider_evidence_visible": row[12],
            "limitation_codes": list(row[13]),
        }.items():
            if value != expected[key]:
                raise IntegrationSafetyError(
                    f"{arm_id} Kimi cost verification failed: {key}"
                )

        spec = ARM_CONTRACT[arm_id]
        if row[14] != "moonshot-kimi" or row[15] != spec["backend_model"]:
            raise IntegrationSafetyError(
                f"{arm_id} Kimi pricing linkage verification failed"
            )

        verified_cost[arm_id] = {
            "selected_cost_usd": str(row[8]),
            "selected_cost_basis": row[9],
            "selected_cost_relation": row[10],
            "validation_status": row[11],
        }

    return {
        "transaction_counts": counts,
        "usage_reconciliations": verified_usage,
        "cost_reconciliations": verified_cost,
    }


def verify_provider_evidence_details(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> dict[str, str]:
    expected_sources = {row["source_key"]: row for row in plan["sources"]}

    cursor.execute(
        """
        select
            provider,
            evidence_kind,
            source_scope,
            provider_reference,
            source_sha256,
            source_format,
            integrity_status,
            notes,
            arm_run_id is null,
            artifact_id is null,
            source_uri is null,
            raw_metadata
        from benchmark.benchmark_provider_evidence_sources
        where provider = 'moonshot-kimi'
        order by source_sha256
        """
    )

    source_rows = cursor.fetchall()

    if len(source_rows) != len(expected_sources):
        raise IntegrationSafetyError(
            "Kimi evidence source row count verification failed"
        )

    by_sha = {str(row[4]): row for row in source_rows}

    for expected in expected_sources.values():
        row = by_sha.get(expected["source_sha256"])

        if row is None:
            raise IntegrationSafetyError(
                "reviewed Kimi evidence source SHA-256 is missing"
            )

        expected_tuple = (
            expected["provider"],
            expected["evidence_kind"],
            expected["source_scope"],
            expected["provider_reference"],
            expected["source_sha256"],
            expected["source_format"],
            expected["integrity_status"],
            expected["notes"],
            True,
            True,
            True,
            expected.get(
                "raw_metadata",
                {},
            ),
        )

        if tuple(row) != expected_tuple:
            raise IntegrationSafetyError(
                "Kimi evidence source provenance verification failed"
            )

    pricing_plan = {row["provider_model"]: row for row in plan["pricing_snapshots"]}

    cursor.execute(
        """
        select
            source.source_sha256,
            pricing.provider,
            pricing.provider_model,
            pricing.currency,
            pricing.effective_from,
            pricing.effective_until,
            pricing.pricing_semantics,
            pricing.pricing_rules,
            pricing.official_source_uri,
            pricing.notes,
            pricing.raw_metadata
        from benchmark.benchmark_provider_pricing_snapshots pricing
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = pricing.source_id
        where pricing.provider = 'moonshot-kimi'
        order by pricing.provider_model
        """
    )

    pricing_rows = cursor.fetchall()

    if len(pricing_rows) != len(pricing_plan):
        raise IntegrationSafetyError("Kimi pricing row count verification failed")

    for row in pricing_rows:
        provider_model = str(row[2])
        expected = pricing_plan.get(provider_model)

        if expected is None:
            raise IntegrationSafetyError("unexpected Kimi pricing model")

        source_sha = expected_sources[expected["source_key"]]["source_sha256"]

        observed = (
            str(row[0]),
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
        )

        expected_tuple = (
            source_sha,
            expected["provider"],
            expected["provider_model"],
            expected["currency"],
            expected["effective_from"],
            expected["effective_until"],
            expected["pricing_semantics"],
            expected["pricing_rules"],
            expected["official_source_uri"],
            expected["notes"],
            expected.get(
                "raw_metadata",
                {},
            ),
        )

        if observed != expected_tuple:
            raise IntegrationSafetyError("Kimi pricing snapshot verification failed")

    usage_plan = plan["provider_usage_evidence"]

    cursor.execute(
        """
        select
            source.source_sha256,
            evidence.arm_run_id is null,
            evidence.trial_id is null,
            evidence.provider_request_id,
            evidence.provider_model,
            evidence.request_started_at,
            evidence.request_finished_at,
            evidence.ordinary_input_tokens,
            evidence.cache_read_input_tokens,
            evidence.cache_creation_input_tokens,
            evidence.output_tokens,
            evidence.request_count,
            evidence.allocation_scope,
            evidence.completeness_status,
            evidence.notes,
            evidence.raw_metadata
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = 'moonshot-kimi'
        order by evidence.provider_model
        """
    )

    usage_rows = cursor.fetchall()

    if len(usage_rows) != len(usage_plan):
        raise IntegrationSafetyError(
            "Kimi provider usage row count verification failed"
        )

    expected_usage = {row["provider_model"]: row for row in usage_plan}

    for row in usage_rows:
        model = str(row[4])
        expected = expected_usage.get(model)

        if expected is None:
            raise IntegrationSafetyError("unexpected Kimi provider usage model")

        expected_tuple = (
            expected_sources[expected["source_key"]]["source_sha256"],
            True,
            True,
            None,
            expected["provider_model"],
            None,
            None,
            expected["ordinary_input_tokens"],
            expected["cache_read_input_tokens"],
            expected["cache_creation_input_tokens"],
            expected["output_tokens"],
            expected["request_count"],
            expected["allocation_scope"],
            expected["completeness_status"],
            expected["notes"],
            expected["raw_metadata"],
        )

        if tuple(row) != expected_tuple:
            raise IntegrationSafetyError("Kimi provider usage verification failed")

    cost_plan = plan["provider_cost_evidence"]

    cursor.execute(
        """
        select
            source.source_sha256,
            evidence.arm_run_id is null,
            evidence.trial_id is null,
            evidence.pricing_snapshot_id is null,
            pricing.provider_model,
            evidence.provider_model,
            evidence.cost_kind,
            evidence.amount_usd,
            evidence.currency,
            evidence.allocation_scope,
            evidence.completeness_status,
            evidence.notes,
            evidence.raw_metadata
        from benchmark.benchmark_provider_cost_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        left join benchmark.benchmark_provider_pricing_snapshots pricing
          on pricing.id = evidence.pricing_snapshot_id
        where source.provider = 'moonshot-kimi'
        order by evidence.amount_usd, evidence.cost_kind
        """
    )

    cost_rows = cursor.fetchall()

    if len(cost_rows) != len(cost_plan):
        raise IntegrationSafetyError("Kimi provider cost row count verification failed")

    expected_cost = {
        (
            Decimal(row["amount_usd"]),
            row["cost_kind"],
            row["provider_model"],
        ): row
        for row in cost_plan
    }

    observed_keys: set[tuple[Decimal, str, str | None]] = set()

    for row in cost_rows:
        key = (
            Decimal(row[7]),
            str(row[6]),
            (None if row[5] is None else str(row[5])),
        )
        expected = expected_cost.get(key)

        if expected is None:
            raise IntegrationSafetyError("unexpected Kimi provider cost row")

        observed_keys.add(key)

        pricing_key = expected["pricing_snapshot_key"]
        expected_pricing_model = None

        if pricing_key is not None:
            expected_pricing_model = next(
                row_["provider_model"]
                for row_ in plan["pricing_snapshots"]
                if row_["pricing_key"] == pricing_key
            )

        expected_tuple = (
            expected_sources[expected["source_key"]]["source_sha256"],
            True,
            True,
            pricing_key is None,
            expected_pricing_model,
            expected["provider_model"],
            expected["cost_kind"],
            Decimal(expected["amount_usd"]),
            expected["currency"],
            expected["allocation_scope"],
            expected["completeness_status"],
            expected["notes"],
            expected["raw_metadata"],
        )

        if tuple(row) != expected_tuple:
            raise IntegrationSafetyError("Kimi provider cost verification failed")

    if observed_keys != set(expected_cost):
        raise IntegrationSafetyError("Kimi provider cost evidence is incomplete")

    requested_ids = list(arm_run_ids.values())

    cursor.execute(
        """
        select
            'usage' as reconciliation_kind,
            arm_run.arm_id,
            source.source_sha256,
            link.evidence_role
        from benchmark.benchmark_usage_reconciliation_sources link
        join benchmark.benchmark_usage_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = link.source_id
        where reconciliation.arm_run_id = any(%s::uuid[])

        union all

        select
            'cost' as reconciliation_kind,
            arm_run.arm_id,
            source.source_sha256,
            link.evidence_role
        from benchmark.benchmark_cost_reconciliation_sources link
        join benchmark.benchmark_cost_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = link.source_id
        where reconciliation.arm_run_id = any(%s::uuid[])

        order by reconciliation_kind, arm_id, evidence_role
        """,
        (
            requested_ids,
            requested_ids,
        ),
    )

    actual_links = {
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
        )
        for row in cursor.fetchall()
    }

    source_sha_by_key = {
        row["source_key"]: row["source_sha256"] for row in plan["sources"]
    }

    expected_links = {
        (
            "usage",
            link["arm_id"],
            source_sha_by_key[link["source_key"]],
            link["evidence_role"],
        )
        for link in plan["usage_reconciliation_source_links"]
    } | {
        (
            "cost",
            link["arm_id"],
            source_sha_by_key[link["source_key"]],
            link["evidence_role"],
        )
        for link in plan["cost_reconciliation_source_links"]
    }

    if actual_links != expected_links:
        raise IntegrationSafetyError(
            "Kimi reconciliation source-link verification failed"
        )

    return {
        "source_rows": "pass",
        "pricing_rows": "pass",
        "usage_evidence_rows": "pass",
        "cost_evidence_rows": "pass",
        "reconciliation_source_links": "pass",
    }


def check_only(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg

    connection = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        diagnostics.enter("target_state_preflight")

        with connection.cursor() as cursor:
            cursor.execute("set transaction read only")

            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = state["state"]

            if state["state"] == "kimi_empty":
                diagnostics.enter("canonical_run_resolution")
                resolved = resolve_arm_runs(
                    cursor,
                    plan,
                )

                result = {
                    "status": "ready",
                    "mode": "check-only",
                    "commit_state": diagnostics.commit_state,
                    "target_state": state["state"],
                    "counts": state["counts"],
                    "resolved_arm_run_ids": resolved,
                    "checks": {
                        "reviewed_input_hashes": "pass",
                        "provider_scoped_target_empty": "pass",
                        "canonical_run_resolution": "pass",
                        "selected_run_token_geometry": "pass",
                        "selected_run_rate_reconstruction": "pass",
                        "read_only_transaction": "pass",
                    },
                }

            elif state["state"] == "exact_kimi_state":
                result = {
                    "status": "already_applied",
                    "mode": "check-only",
                    "commit_state": diagnostics.commit_state,
                    "target_state": state["state"],
                    "counts": state["counts"],
                    "resolved_arm_run_ids": state["resolved_arm_run_ids"],
                    "checks": {
                        "reviewed_input_hashes": "pass",
                        "exact_content_verification": "pass",
                        "read_only_transaction": "pass",
                    },
                }

            else:
                raise IntegrationSafetyError(
                    "Kimi provider evidence target is "
                    "partially or unexpectedly populated"
                )

        connection.rollback()

    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise

    finally:
        connection.close()

    return result


def rollback_only(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg

    connection = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with connection.cursor() as cursor:
            diagnostics.enter("advisory_lock")
            acquire_ingestion_lock(cursor)

            diagnostics.enter("target_state_preflight")
            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = state["state"]

            if state["state"] != "kimi_empty":
                raise IntegrationSafetyError(
                    "Kimi rollback-only requires an empty provider target"
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
            reconciliation = verify_inserted_state(
                cursor,
                plan,
                arm_run_ids,
            )
            provider = verify_provider_evidence_details(
                cursor,
                plan,
                arm_run_ids,
            )

            transaction_counts = target_table_counts(
                cursor,
                plan,
            )

        diagnostics.enter("rollback")
        connection.rollback()

    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise

    finally:
        connection.close()

    diagnostics.enter("second_connection_zero_persistence")
    observer = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with observer.cursor() as cursor:
            cursor.execute("set transaction read only")
            zero_counts = target_table_counts(
                cursor,
                plan,
            )
            diagnostics.zero_persistence_counts = zero_counts
            if any(zero_counts.values()):
                raise IntegrationSafetyError(
                    "Kimi rollback-only left persistent provider rows"
                )
        observer.rollback()
    finally:
        observer.close()

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state": diagnostics.commit_state,
        "target_state": "kimi_empty",
        "resolved_arm_run_ids": arm_run_ids,
        "transaction_counts": transaction_counts,
        "zero_persistence_counts": zero_counts,
        "verification": {
            "provider_evidence": provider,
            "reconciliations": reconciliation,
        },
        "checks": {
            "reviewed_input_hashes": "pass",
            "advisory_lock": "pass",
            "provider_scoped_empty_preflight": "pass",
            "canonical_run_resolution": "pass",
            "transactional_insert": "pass",
            "transactional_verification": "pass",
            "rollback": "pass",
            "second_connection_zero_persistence": "pass",
        },
    }


def apply_permanent(
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
            diagnostics.enter("advisory_lock")
            acquire_ingestion_lock(cursor)

            diagnostics.enter("target_state_preflight")
            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = state["state"]

            if state["state"] == "exact_kimi_state":
                raise IntegrationSafetyError(
                    "reviewed Kimi provider evidence is already applied"
                )

            if state["state"] != "kimi_empty":
                raise IntegrationSafetyError(
                    "Kimi provider evidence target "
                    "is partially or unexpectedly populated"
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
            reconciliation = verify_inserted_state(
                cursor,
                plan,
                arm_run_ids,
            )
            provider = verify_provider_evidence_details(
                cursor,
                plan,
                arm_run_ids,
            )

        diagnostics.enter("commit")
        diagnostics.commit_state = "unknown"
        connection.commit()
        diagnostics.commit_state = "committed"

    except Exception:
        if connection is not None and diagnostics.commit_state != "committed":
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter("second_connection_verification")

    observer = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with observer.cursor() as cursor:
            cursor.execute("set transaction read only")
            state = inspect_target_state(
                cursor,
                plan,
            )

            if state["state"] != "exact_kimi_state":
                raise IntegrationSafetyError(
                    "committed Kimi evidence failed second-connection verification"
                )

            persisted_counts = state["counts"]

        observer.rollback()

    finally:
        observer.close()

    return {
        "status": "applied",
        "mode": "apply",
        "commit_state": diagnostics.commit_state,
        "target_state": "exact_kimi_state",
        "persisted_counts": persisted_counts,
        "resolved_arm_run_ids": state["resolved_arm_run_ids"],
        "verification": {
            "provider_evidence": provider,
            "reconciliations": reconciliation,
        },
        "checks": {
            "reviewed_input_hashes": "pass",
            "advisory_lock": "pass",
            "provider_scoped_empty_preflight": "pass",
            "canonical_run_resolution": "pass",
            "transactional_insert": "pass",
            "transactional_verification": "pass",
            "commit": "pass",
            "second_connection_verification": "pass",
        },
    }


def failure_payload(
    *,
    mode: str,
    diagnostics: Diagnostics,
    exc: Exception,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "failed",
        "mode": mode,
        "stage": diagnostics.stage,
        "commit_state": diagnostics.commit_state,
        "target_state": diagnostics.target_state,
        "error_type": type(exc).__name__,
    }

    if diagnostics.zero_persistence_counts:
        payload["zero_persistence_counts"] = diagnostics.zero_persistence_counts

    return payload


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, verify, rollback-test, or apply reviewed Kimi provider evidence."
        )
    )

    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--plan",
        action="store_true",
    )
    modes.add_argument(
        "--check-only",
        action="store_true",
    )
    modes.add_argument(
        "--rollback-only",
        action="store_true",
    )
    modes.add_argument(
        "--apply",
        action="store_true",
    )

    return parser.parse_args(argv)


def _mode_name(
    args: argparse.Namespace,
) -> str:
    if args.plan:
        return "plan"
    if args.check_only:
        return "check-only"
    if args.rollback_only:
        return "rollback-only"
    return "apply"


def _database_url() -> str:
    value = os.environ.get("SUPABASE_DB_URL")
    if not value:
        raise MissingEnvironmentError("SUPABASE_DB_URL is required")
    return value


def _plan_payload(
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "planned",
        "mode": "plan",
        "provider": plan["provider"],
        "plan_version": plan["plan_version"],
        "reviewed_plan_sha256": plan["reviewed_plan_sha256"],
        "write_counts": plan["write_counts"],
        "selected_runs": plan["selected_runs"],
        "excluded_evidence": plan["excluded_evidence"],
    }


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    mode = _mode_name(args)
    diagnostics = Diagnostics()

    try:
        diagnostics.enter("reviewed_input_validation")
        plan = build_plan()

        if args.plan:
            result = _plan_payload(plan)
        else:
            diagnostics.enter("database_environment")
            db_url = _database_url()

            if args.check_only:
                result = check_only(
                    plan,
                    db_url,
                    diagnostics,
                )
            elif args.rollback_only:
                result = rollback_only(
                    plan,
                    db_url,
                    diagnostics,
                )
            else:
                result = apply_permanent(
                    plan,
                    db_url,
                    diagnostics,
                )

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    except Exception as exc:
        print(
            json.dumps(
                failure_payload(
                    mode=mode,
                    diagnostics=diagnostics,
                    exc=exc,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
