#!/usr/bin/env python3
"""Plan, verify, rollback-test, or apply Qwen Phase 3 provider-evidence ingestion."""

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

QWEN_SNAPSHOT = (
    ROOT / "results/phase3/supplemental/qwen_provider_evidence_snapshot_20260828.json"
)
CURRENT_RECONCILIATION = (
    ROOT / "results/phase3/reporting/"
    "phase3_current_arm_cost_reconciliation_20260825.csv"
)
EVIDENCE_MATRIX = (
    ROOT / "results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv"
)

REVIEWED_PLAN_SHA256 = "0836cdb8b0078f9524f736f099d68d2d6138c8f068b2ec074bdb931b456db119"
EXPECTED_SNAPSHOT_SHA256 = "c334c57d143dc59cf3c81af24a233ed061f07a8902f95431da1d2401e53ab556"

ARM_ID = "router-qwen-3.7-plus"
RUN_LABEL = "router-qwen-3.7-plus/2026-06-29__03-16-06"
BACKEND_MODEL = "qwen3.7-plus"
PROVIDER = "dashscope-qwen"

ARM_CONTRACT: dict[str, Any] = {
    "selected_run_label": RUN_LABEL,
    "backend_model": BACKEND_MODEL,
    "trial_count": 60,
    "complete_trial_cost_count": 59,
    "unresolved_trial_count": 1,
    "harness_input_tokens": 3_177_366,
    "harness_cache_tokens": 0,
    "harness_cache_miss_tokens": 3_177_366,
    "harness_output_tokens": 1_162_240,
    "historical_harness_cost_usd": Decimal("20.43072"),
    "historical_reviewed_cost_usd": Decimal("34.944370078781"),
    "ordinary_input_rate": Decimal("0.32"),
    "cache_read_rate": Decimal("0.064"),
    "output_rate": Decimal("1.28"),
    "selected_cost_usd": Decimal("2.50442432"),
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

INGESTION_LOCK_NAME = "cc-deepseek-bench:qwen-provider-evidence-ingestion:v1"


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
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def money(value: Decimal) -> str:
    return format(value, "f")


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise EvidencePlanError(f"reviewed Qwen evidence mismatch: {label}")


def reconstruct_selected_cost(
    *,
    input_tokens: int,
    cache_tokens: int,
    output_tokens: int,
) -> Decimal:
    ordinary_tokens = input_tokens - cache_tokens
    return (
        Decimal(ordinary_tokens) * ARM_CONTRACT["ordinary_input_rate"]
        + Decimal(cache_tokens) * ARM_CONTRACT["cache_read_rate"]
        + Decimal(output_tokens) * ARM_CONTRACT["output_rate"]
    ) / Decimal(1_000_000)


def _source_format(path_or_reference: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    suffix = Path(path_or_reference).suffix.lower()
    return {
        ".json": "json",
        ".csv": "csv",
        ".tsv": "tsv",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".py": "python",
    }.get(suffix, suffix.lstrip(".") or "text")


def verify_input_hashes(
    snapshot: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    actual_snapshot = sha256_path(QWEN_SNAPSHOT)
    if actual_snapshot != EXPECTED_SNAPSHOT_SHA256:
        raise EvidencePlanError("reviewed Qwen snapshot hash changed")

    if snapshot is None:
        snapshot = json.loads(QWEN_SNAPSHOT.read_text(encoding="utf-8"))

    actual: dict[str, str] = {
        str(QWEN_SNAPSHOT.relative_to(ROOT)): actual_snapshot,
    }

    source_rows = snapshot.get("provider_source_rows")
    provenance_rows = snapshot.get("provenance_only_sources")

    if not isinstance(source_rows, list):
        raise EvidencePlanError("Qwen snapshot provider sources are malformed")
    if not isinstance(provenance_rows, list):
        raise EvidencePlanError("Qwen snapshot provenance sources are malformed")

    for row in source_rows + provenance_rows:
        if not isinstance(row, dict):
            raise EvidencePlanError("Qwen snapshot source row is malformed")

        relative = row.get("path")
        expected = row.get("sha256")

        if relative is None:
            continue

        if not isinstance(relative, str) or not isinstance(expected, str):
            raise EvidencePlanError("Qwen snapshot source hash contract is malformed")

        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise EvidencePlanError("Qwen snapshot source escapes repository") from exc

        if not path.is_file():
            raise EvidencePlanError("reviewed Qwen input is missing")

        actual_hash = sha256_path(path)
        if actual_hash != expected:
            raise EvidencePlanError("reviewed Qwen input hashes changed")

        actual[relative] = actual_hash

    raw_provenance = snapshot.get("raw_provider_artifact_provenance")
    if not isinstance(raw_provenance, dict):
        raise EvidencePlanError("Qwen raw provider provenance is malformed")

    require_equal(
        raw_provenance.get("raw_export_sha256"),
        "51b2220da055056fa80fa761fe0f13a25fafe736ed3df8ccaeb44c65bece308b",
        "raw export SHA-256",
    )
    require_equal(
        raw_provenance.get("raw_export_size_bytes"),
        243_803,
        "raw export size",
    )
    require_equal(
        raw_provenance.get("raw_bytes_committed"),
        False,
        "raw export repository retention",
    )

    return actual


def _validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    require_equal(snapshot.get("schema_version"), 1, "snapshot schema version")
    require_equal(
        snapshot.get("evidence_version"),
        "qwen-provider-evidence-20260828-v1",
        "snapshot evidence version",
    )
    require_equal(snapshot.get("provider"), PROVIDER, "snapshot provider")
    require_equal(
        snapshot.get("reviewed_private_plan_sha256"),
        REVIEWED_PLAN_SHA256,
        "reviewed private plan SHA-256",
    )
    require_equal(snapshot.get("private_paths_retained"), False, "private path retention")
    require_equal(
        snapshot.get("database_write_authorized"),
        False,
        "snapshot database authorization",
    )
    require_equal(snapshot.get("apply_authorized"), False, "snapshot apply authorization")

    expected_principles = {
        "historical_results_frozen": True,
        "no_historical_raw_cost_rewrite": True,
        "no_missing_usage_synthesized_as_zero": True,
        "no_synthetic_provider_allocation": True,
        "historical_provider_bill_not_selected_run_billing": True,
        "subscription_overhead_not_marginal_inference_cost": True,
        "billing_line_items_not_mislabeled_as_api_requests": True,
        "selected_provider_usage_fields_remain_null": True,
        "selected_provider_billed_cost_remains_null": True,
        "selected_cost_remains_lower_bound": True,
    }
    require_equal(snapshot.get("principles"), expected_principles, "normalization principles")

    require_equal(
        snapshot.get("planned_row_counts"),
        {
            "benchmark_provider_evidence_sources": 5,
            "benchmark_provider_usage_evidence": 0,
            "benchmark_provider_pricing_snapshots": 1,
            "benchmark_provider_cost_evidence": 3,
            "benchmark_usage_reconciliations": 1,
            "benchmark_usage_reconciliation_sources": 3,
            "benchmark_cost_reconciliations": 1,
            "benchmark_cost_reconciliation_sources": 3,
            "benchmark_evidence_promotion_gates": 0,
        },
        "planned row cardinality",
    )

    selected = snapshot.get("selected_arm")
    if not isinstance(selected, dict):
        raise EvidencePlanError("Qwen selected-arm snapshot is malformed")

    expected_selected = {
        "arm_id": ARM_ID,
        "run_label": RUN_LABEL,
        "configured_backend_model": BACKEND_MODEL,
        "provider_observed_selected_run_model": None,
        "trial_count": 60,
        "complete_trial_cost_count": 59,
        "unresolved_trial_count": 1,
        "harness_input_tokens": 3_177_366,
        "harness_cache_tokens": 0,
        "harness_output_tokens": 1_162_240,
        "provider_selected_run_tokens": None,
        "selected_usage_authority": "harness_usage_validated",
        "usage_validation_status": "validated_qualified",
        "historical_harness_reported_cost_usd": "20.43072",
        "historical_reviewed_cost_usd": "34.944370078781",
        "provider_billed_cost_usd": None,
        "provider_rate_reconstructed_cost_usd": "2.50442432",
        "selected_cost_usd": "2.50442432",
        "selected_cost_basis": "lower_bound_provider_evidence",
        "selected_cost_relation": "lower_bound",
        "cost_validation_status": "validated_qualified",
    }
    for key, expected in expected_selected.items():
        require_equal(selected.get(key), expected, f"selected arm {key}")

    limitations = selected.get("limitations")
    if not isinstance(limitations, list) or len(limitations) != 6:
        raise EvidencePlanError("Qwen limitation contract is malformed")

    require_equal(snapshot.get("provider_usage_evidence"), [], "provider usage evidence")
    reason = snapshot.get("provider_usage_evidence_exclusion_reason")
    if not isinstance(reason, str) or "billing line items" not in reason:
        raise EvidencePlanError("Qwen provider-usage exclusion reason is malformed")

    context = snapshot.get("historical_provider_context")
    if not isinstance(context, dict):
        raise EvidencePlanError("Qwen historical provider context is malformed")

    context_checks = {
        "billing_window_start_date": "2026-06-04",
        "billing_window_end_date": "2026-06-16",
        "selected_run_allocable": False,
        "relation_to_selected_run": "predates_selected_run",
        "billing_row_count": 111,
        "inference_billing_row_count": 109,
        "non_inference_billing_row_count": 2,
        "account_payable_usd": "31.310889920",
        "inference_payable_usd": "1.310889920",
        "subscription_payable_usd": "30",
        "original_tokens": 5_122_074,
        "deducted_tokens": 1_000_458,
        "billable_tokens": 4_121_616,
        "payable_fraction_of_list": "0.8",
    }
    for key, expected in context_checks.items():
        require_equal(context.get(key), expected, f"historical provider context {key}")

    pricing = snapshot.get("pricing_snapshots")
    if not isinstance(pricing, list) or len(pricing) != 1:
        raise EvidencePlanError("Qwen pricing snapshot is malformed")

    rate = pricing[0]
    for key, expected in {
        "id": "qwen3.7-plus-reviewed-effective-rates",
        "provider_model": BACKEND_MODEL,
        "ordinary_input_usd_per_million": "0.32",
        "cache_read_usd_per_million": "0.064",
        "output_usd_per_million": "1.28",
        "payable_fraction_of_list": "0.8",
        "selected_request_tier_max_tokens": 256_000,
        "selected_run_max_observed_request_tokens": 45_509,
        "selected_run_all_usage_bearing_requests_within_tier": True,
        "official_dated_provider_snapshot_retained": False,
        "historical_bill_validates_rates": True,
    }.items():
        require_equal(rate.get(key), expected, f"pricing snapshot {key}")

    costs = snapshot.get("provider_cost_evidence")
    if not isinstance(costs, list) or len(costs) != 3:
        raise EvidencePlanError("Qwen provider cost snapshot is malformed")

    by_id = {row["id"]: row for row in costs if isinstance(row, dict)}
    expected_costs = {
        "qwen_historical_account_spend": ("31.310889920", "account_spend"),
        "qwen_historical_subscription_overhead": ("30", "overhead"),
        "qwen_historical_inference_rate_reconstruction": (
            "1.310889920",
            "provider_rate_reconstruction",
        ),
    }
    require_equal(set(by_id), set(expected_costs), "provider cost evidence membership")
    for key, (amount, kind) in expected_costs.items():
        row = by_id[key]
        require_equal(row.get("amount_usd"), amount, f"{key} amount")
        require_equal(row.get("cost_kind"), kind, f"{key} kind")
        require_equal(row.get("allocation_scope"), "account_window", f"{key} scope")
        require_equal(row.get("completeness_status"), "complete", f"{key} completeness")
        require_equal(row.get("selected_run_allocable"), False, f"{key} allocation")


def _validate_repository_reconciliation() -> None:
    current_rows = [
        row
        for row in read_csv(CURRENT_RECONCILIATION)
        if row.get("arm_id") == ARM_ID
    ]
    matrix_rows = [
        row
        for row in read_csv(EVIDENCE_MATRIX)
        if row.get("arm_id") == ARM_ID
    ]

    if len(current_rows) != 1 or len(matrix_rows) != 1:
        raise EvidencePlanError("reviewed Qwen reconciliation rows do not resolve exactly once")

    current = current_rows[0]
    matrix = matrix_rows[0]

    current_checks = {
        "selected_run_label": RUN_LABEL,
        "backend_model": BACKEND_MODEL,
        "provider_models": BACKEND_MODEL,
        "provider": PROVIDER,
        "selected_cost_usd": "2.50442432",
        "selected_cost_relation": "lower_bound",
        "selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "provider_billed_cost_usd": "",
        "provider_context_billed_cost_usd": "1.31089",
        "trial_count": "60",
        "complete_trial_cost_count": "59",
        "lower_bound_trial_count": "1",
        "historical_harness_recorded_cost_usd": "20.43072",
    }
    for key, expected in current_checks.items():
        require_equal(current.get(key, ""), expected, f"current reconciliation {key}")

    matrix_checks = {
        "provider": PROVIDER,
        "selected_run_label": RUN_LABEL,
        "selected_cost_usd": "2.50442432",
        "selected_cost_relation": "lower_bound",
        "selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "trial_count": "60",
        "complete_trial_cost_count": "59",
        "unresolved_trial_count": "1",
        "selected_input_tokens": "3177366",
        "selected_cache_tokens": "0",
        "selected_output_tokens": "1162240",
        "provider_context_billed_cost_usd": "1.31089",
        "provider_context_account_spend_usd": "31.31089",
        "provider_context_overhead_usd": "30",
        "provider_context_temporal_relation": "predates_selected_run",
        "provider_context_allocation_confidence": "not_allocable_to_selected_run",
    }
    for key, expected in matrix_checks.items():
        require_equal(matrix.get(key, ""), expected, f"evidence matrix {key}")


def build_plan() -> dict[str, Any]:
    raw = QWEN_SNAPSHOT.read_text(encoding="utf-8")
    for forbidden in (
        ".run/review",
        ".secrets/",
        "SUPABASE_DB_URL",
        "/home/",
        "buyerId",
        "@",
    ):
        if forbidden in raw:
            raise EvidencePlanError("sanitized Qwen snapshot contains private material")

    snapshot = json.loads(raw)
    _validate_snapshot(snapshot)
    verify_input_hashes(snapshot)
    _validate_repository_reconciliation()

    source_rows = snapshot["provider_source_rows"]
    provenance = snapshot["raw_provider_artifact_provenance"]

    sources: list[dict[str, Any]] = []
    for row in source_rows:
        path = row.get("path")
        provider_reference = row.get("provider_reference") or path
        if not isinstance(provider_reference, str):
            raise EvidencePlanError("Qwen source lacks safe provider reference")

        raw_metadata = {
            "reviewed_private_plan_sha256": REVIEWED_PLAN_SHA256,
            "snapshot_source_id": row["id"],
            "snapshot_role": row["role"],
        }
        if row["id"] == "qwen_raw_alibaba_billing_export":
            raw_metadata.update(
                {
                    "raw_export_size_bytes": row["size_bytes"],
                    "authoritative_private_raw_reconciliation_sha256": provenance[
                        "authoritative_private_raw_reconciliation_sha256"
                    ],
                    "read_only_db_inventory_sha256": provenance[
                        "read_only_db_inventory_sha256"
                    ],
                    "raw_bytes_committed": False,
                    "selected_run_allocable": False,
                    "relation_to_selected_run": "predates_selected_run",
                }
            )

        sources.append(
            {
                "source_key": row["id"],
                "provider": PROVIDER,
                "evidence_kind": row["evidence_kind"],
                "source_scope": row["source_scope"],
                "provider_reference": provider_reference,
                "source_sha256": row["sha256"],
                "size_bytes": row.get("size_bytes"),
                "source_format": _source_format(
                    path or provider_reference,
                    row.get("source_format"),
                ),
                "integrity_status": "sha256_verified",
                "notes": row["role"],
                "raw_metadata": raw_metadata,
            }
        )

    pricing_snapshot = snapshot["pricing_snapshots"][0]
    pricing_snapshots = [
        {
            "pricing_key": pricing_snapshot["id"],
            "source_key": "qwen_raw_alibaba_billing_export",
            "provider": PROVIDER,
            "provider_model": BACKEND_MODEL,
            "currency": "USD",
            "effective_from": None,
            "effective_until": None,
            "pricing_semantics": "cache_aware_input_plus_output_effective_payable_discounted",
            "pricing_rules": {
                "ordinary_input_usd_per_million": pricing_snapshot[
                    "ordinary_input_usd_per_million"
                ],
                "cached_input_usd_per_million": pricing_snapshot[
                    "cache_read_usd_per_million"
                ],
                "output_usd_per_million": pricing_snapshot[
                    "output_usd_per_million"
                ],
                "raw_list_ordinary_input_usd_per_million": pricing_snapshot[
                    "raw_list_ordinary_input_usd_per_million"
                ],
                "raw_list_cached_input_usd_per_million": pricing_snapshot[
                    "raw_list_cache_read_usd_per_million"
                ],
                "raw_list_output_usd_per_million": pricing_snapshot[
                    "raw_list_output_usd_per_million"
                ],
                "payable_fraction_of_list": pricing_snapshot["payable_fraction_of_list"],
                "selected_request_tier_max_tokens": pricing_snapshot[
                    "selected_request_tier_max_tokens"
                ],
                "selected_run_max_observed_request_tokens": pricing_snapshot[
                    "selected_run_max_observed_request_tokens"
                ],
                "selected_run_all_usage_bearing_requests_within_tier": pricing_snapshot[
                    "selected_run_all_usage_bearing_requests_within_tier"
                ],
                "historical_bill_validates_rates": True,
                "official_dated_provider_snapshot_retained": False,
            },
            "official_source_uri": None,
            "notes": (
                "Effective payable Qwen 3.7 Plus rates validated by the retained "
                "historical Alibaba billing export. The export demonstrates a 20% "
                "discount from list price. It predates the selected June 29 run; "
                "the pricing row records reviewed rate semantics, not selected-run billing."
            ),
            "raw_metadata": {
                "historical_validation_window": "2026-06-04_to_2026-06-16",
                "selected_run_allocable": False,
            },
        }
    ]

    selected = snapshot["selected_arm"]
    selected_runs = [
        {
            "arm_id": ARM_ID,
            "selected_run_label": RUN_LABEL,
            "backend_model": BACKEND_MODEL,
            "trial_count": 60,
            "harness_input_tokens": 3_177_366,
            "harness_cache_tokens": 0,
            "harness_cache_miss_tokens": 3_177_366,
            "harness_output_tokens": 1_162_240,
            "selected_cost_usd": "2.50442432",
        }
    ]

    provider_cost_evidence: list[dict[str, Any]] = []
    for row in snapshot["provider_cost_evidence"]:
        pricing_key = row.get("pricing_snapshot_key")
        notes_by_kind = {
            "account_spend": (
                "First-party Alibaba account-window payable total through June 16. "
                "It includes inference consumption plus the Token Plan purchase and "
                "predates the selected June 29 run."
            ),
            "overhead": (
                "Alibaba Token Plan Team Edition prepaid subscription purchase. "
                "This is account overhead and is not marginal inference cost or "
                "selected-run billing."
            ),
            "provider_rate_reconstruction": (
                "Historical inference payable reconstructed from the raw export's "
                "billable token buckets and effective discounted rates. It exactly "
                "matches the inference payable component but is account-window "
                "context only, not selected-run billing."
            ),
        }
        raw_metadata = {
            "selected_run_allocable": False,
            "relation_to_selected_run": "predates_selected_run",
            "billing_window": "2026-06-04_to_2026-06-16",
        }
        if row["cost_kind"] == "provider_rate_reconstruction":
            raw_metadata.update(
                {
                    "provider_payable_match": True,
                    "historical_inference_gross_usd": "1.63861240",
                    "historical_inference_discount_usd": "0.327722480",
                    "historical_inference_payable_usd": "1.310889920",
                }
            )
        if row["cost_kind"] == "overhead":
            raw_metadata["overhead_semantics"] = (
                "account_subscription_overhead_not_marginal_inference_cost"
            )

        provider_cost_evidence.append(
            {
                "source_key": "qwen_raw_alibaba_billing_export",
                "arm_run_id": None,
                "trial_id": None,
                "pricing_snapshot_key": pricing_key,
                "provider_model": None,
                "cost_kind": row["cost_kind"],
                "amount_usd": row["amount_usd"],
                "currency": "USD",
                "allocation_scope": "account_window",
                "completeness_status": "complete",
                "notes": notes_by_kind[row["cost_kind"]],
                "raw_metadata": raw_metadata,
            }
        )

    limitations = list(selected["limitations"])

    usage_reconciliations = [
        {
            "arm_id": ARM_ID,
            "reconciliation_version": "qwen-provider-evidence-v1",
            "is_current": True,
            "harness_name": "claude-code",
            "harness_version": None,
            "configured_route_model": ARM_ID,
            "configured_backend_model": BACKEND_MODEL,
            "harness_observed_model": None,
            "provider_observed_model": None,
            "model_identity_status": "matched",
            "harness_input_tokens": 3_177_366,
            "harness_cache_tokens": 0,
            "harness_output_tokens": 1_162_240,
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
                "Selected-run usage authority remains the reviewed retained harness "
                "aggregate. The historical Alibaba export is billing-line evidence, "
                "not API-request usage, and is not copied into selected-run provider "
                "token fields. provider_observed_model remains NULL; matched denotes "
                "the reviewed configured/backend identity rather than an independent "
                "selected-run provider observation."
            ),
            "raw_metadata": {
                "provider_usage_evidence_rows": 0,
                "billing_line_items_not_api_requests": True,
                "provider_context_not_selected_run_usage": True,
                "complete_trial_cost_count": 59,
                "unresolved_trial_count": 1,
                "unresolved_trial_has_zero_metric_trajectory": True,
            },
        }
    ]

    cost_reconciliations = [
        {
            "arm_id": ARM_ID,
            "reconciliation_version": "qwen-provider-evidence-v1",
            "is_current": True,
            "harness_name": "claude-code",
            "harness_version": None,
            "harness_reported_cost_usd": "20.43072",
            "provider_billed_cost_usd": None,
            "provider_rate_reconstructed_cost_usd": "2.50442432",
            "selected_cost_usd": "2.50442432",
            "selected_cost_basis": "lower_bound_provider_evidence",
            "selected_cost_relation": "lower_bound",
            "validation_status": "validated_qualified",
            "provider_evidence_visible": True,
            "pricing_snapshot_key": "qwen3.7-plus-reviewed-effective-rates",
            "limitation_codes": limitations,
            "notes": (
                "Selected cost is the reviewed retained-usage lower bound repriced "
                "at the provider-bill-validated effective rates. One zero-metric "
                "selected trial remains unresolved, so provider_billed_cost remains "
                "NULL and the selected relation remains lower_bound. Historical "
                "Alibaba account-window billing predates the selected run and is not "
                "synthetically allocated to it."
            ),
            "raw_metadata": {
                "provider_context_not_selected_run_billing": True,
                "complete_trial_cost_count": 59,
                "unresolved_trial_count": 1,
                "possible_additional_unresolved_trial_spend": True,
                "reporting_selected_cost_basis": (
                    "provider_rate_reconstructed_retained_usage_lower_bound"
                ),
            },
        }
    ]

    usage_links = [
        {
            "arm_id": ARM_ID,
            "source_key": row["source_key"],
            "evidence_role": row["evidence_role"],
        }
        for row in snapshot["planned_source_links"]["usage"]
    ]
    cost_links = [
        {
            "arm_id": ARM_ID,
            "source_key": row["source_key"],
            "evidence_role": row["evidence_role"],
        }
        for row in snapshot["planned_source_links"]["cost"]
    ]

    return {
        "provider": PROVIDER,
        "plan_version": "qwen-provider-evidence-v1",
        "reviewed_plan_sha256": REVIEWED_PLAN_SHA256,
        "snapshot_sha256": EXPECTED_SNAPSHOT_SHA256,
        "sources": sources,
        "pricing_snapshots": pricing_snapshots,
        "provider_usage_evidence": [],
        "provider_cost_evidence": provider_cost_evidence,
        "selected_runs": selected_runs,
        "usage_reconciliations": usage_reconciliations,
        "cost_reconciliations": cost_reconciliations,
        "usage_reconciliation_source_links": usage_links,
        "cost_reconciliation_source_links": cost_links,
        "excluded_evidence": snapshot["excluded_evidence"],
        "write_counts": snapshot["planned_row_counts"],
    }


def target_table_counts(cursor: Any, plan: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_provider_evidence_sources
        where provider = %s
        """,
        (PROVIDER,),
    )
    counts["benchmark_provider_evidence_sources"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = %s
        """,
        (PROVIDER,),
    )
    counts["benchmark_provider_usage_evidence"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_provider_pricing_snapshots
        where provider = %s
        """,
        (PROVIDER,),
    )
    counts["benchmark_provider_pricing_snapshots"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_provider_cost_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = %s
        """,
        (PROVIDER,),
    )
    counts["benchmark_provider_cost_evidence"] = int(cursor.fetchone()["count"])

    params = (ARM_ID, RUN_LABEL)

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_usage_reconciliations reconciliation
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = %s
          and benchmark_run.run_label = %s
        """,
        params,
    )
    counts["benchmark_usage_reconciliations"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_usage_reconciliation_sources link
        join benchmark.benchmark_usage_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = %s
          and benchmark_run.run_label = %s
        """,
        params,
    )
    counts["benchmark_usage_reconciliation_sources"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_cost_reconciliations reconciliation
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = %s
          and benchmark_run.run_label = %s
        """,
        params,
    )
    counts["benchmark_cost_reconciliations"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_cost_reconciliation_sources link
        join benchmark.benchmark_cost_reconciliations reconciliation
          on reconciliation.id = link.reconciliation_id
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = reconciliation.arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where arm_run.arm_id = %s
          and benchmark_run.run_label = %s
        """,
        params,
    )
    counts["benchmark_cost_reconciliation_sources"] = int(cursor.fetchone()["count"])

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_evidence_promotion_gates gate
        join benchmark.benchmark_arm_runs arm_run
          on arm_run.id = gate.source_arm_run_id
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where gate.arm_id = %s
          and benchmark_run.run_label = %s
        """,
        params,
    )
    counts["benchmark_evidence_promotion_gates"] = int(cursor.fetchone()["count"])

    return counts


def resolve_arm_runs(cursor: Any, plan: Mapping[str, Any]) -> dict[str, str]:
    del plan
    cursor.execute(
        """
        select
            arm_run.id::text as arm_run_id,
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
        where benchmark_run.run_label = %s
        order by arm_run.arm_id
        """,
        (RUN_LABEL,),
    )
    rows = cursor.fetchall()

    if len(rows) != 1:
        raise IntegrationSafetyError(
            "selected Qwen run does not resolve exactly once"
        )

    row = rows[0]
    expected = {
        "arm_id": ARM_ID,
        "run_label": RUN_LABEL,
        "suite_id": "phase3-full-20",
        "logical_mode": "full",
        "storage_mode": "raw",
        "n_trials": 60,
        "input_tokens": 3_177_366,
        "cache_tokens": 0,
        "output_tokens": 1_162_240,
    }
    observed = {
        "arm_id": row["arm_id"],
        "run_label": row["run_label"],
        "suite_id": row["suite_id"],
        "logical_mode": row["logical_mode"],
        "storage_mode": row["storage_mode"],
        "n_trials": int(row["n_trials"]),
        "input_tokens": int(row["input_tokens"]),
        "cache_tokens": int(row["cache_tokens"]),
        "output_tokens": int(row["output_tokens"]),
    }
    if observed != expected:
        raise IntegrationSafetyError("selected Qwen run geometry changed")

    reconstructed = reconstruct_selected_cost(
        input_tokens=observed["input_tokens"],
        cache_tokens=observed["cache_tokens"],
        output_tokens=observed["output_tokens"],
    )
    if reconstructed != ARM_CONTRACT["selected_cost_usd"]:
        raise IntegrationSafetyError("selected Qwen lower-bound reconstruction changed")

    return {ARM_ID: str(row["arm_run_id"])}


def acquire_ingestion_lock(cursor: Any) -> None:
    cursor.execute(
        """
        select pg_advisory_xact_lock(
            hashtextextended(%s, 0)
        ) as locked
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

    for source in plan["sources"]:
        cursor.execute(
            """
            insert into benchmark.benchmark_provider_evidence_sources (
                provider,
                evidence_kind,
                source_scope,
                provider_reference,
                source_sha256,
                size_bytes,
                source_format,
                integrity_status,
                notes,
                raw_metadata
            ) values (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            returning id
            """,
            (
                source["provider"],
                source["evidence_kind"],
                source["source_scope"],
                source["provider_reference"],
                source["source_sha256"],
                source["size_bytes"],
                source["source_format"],
                source["integrity_status"],
                source["notes"],
                Jsonb(source.get("raw_metadata", {})),
            ),
        )
        source_ids[source["source_key"]] = cursor.fetchone()["id"]

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
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
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
                Jsonb(snapshot.get("raw_metadata", {})),
            ),
        )
        pricing_ids[snapshot["pricing_key"]] = cursor.fetchone()["id"]

    for evidence in plan["provider_cost_evidence"]:
        pricing_key = evidence["pricing_snapshot_key"]
        pricing_id = None if pricing_key is None else pricing_ids[pricing_key]
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
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """,
            (
                source_ids[evidence["source_key"]],
                evidence["arm_run_id"],
                evidence["trial_id"],
                pricing_id,
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

    usage_reconciliation_ids: dict[str, Any] = {}
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
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
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
                Jsonb(reconciliation["raw_metadata"]),
            ),
        )
        usage_reconciliation_ids[arm_id] = cursor.fetchone()["id"]

    cost_reconciliation_ids: dict[str, Any] = {}
    for reconciliation in plan["cost_reconciliations"]:
        arm_id = reconciliation["arm_id"]
        pricing_key = reconciliation["pricing_snapshot_key"]
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
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s
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
                pricing_ids[pricing_key],
                reconciliation["limitation_codes"],
                reconciliation["notes"],
                Jsonb(reconciliation["raw_metadata"]),
            ),
        )
        cost_reconciliation_ids[arm_id] = cursor.fetchone()["id"]

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
    counts = target_table_counts(cursor, plan)
    if counts != plan["write_counts"]:
        raise IntegrationSafetyError("transactional Qwen row counts do not match plan")

    expected_usage = plan["usage_reconciliations"][0]
    cursor.execute(
        """
        select
            reconciliation.reconciliation_version,
            reconciliation.is_current,
            reconciliation.harness_name,
            reconciliation.harness_version,
            reconciliation.configured_route_model,
            reconciliation.configured_backend_model,
            reconciliation.harness_observed_model,
            reconciliation.provider_observed_model,
            reconciliation.model_identity_status,
            reconciliation.harness_input_tokens,
            reconciliation.harness_cache_tokens,
            reconciliation.harness_output_tokens,
            reconciliation.provider_ordinary_input_tokens,
            reconciliation.provider_cache_read_input_tokens,
            reconciliation.provider_cache_creation_input_tokens,
            reconciliation.provider_output_tokens,
            reconciliation.provider_request_count,
            reconciliation.matched_provider_request_count,
            reconciliation.unallocated_provider_request_count,
            reconciliation.provider_evidence_visible,
            reconciliation.selected_usage_authority,
            reconciliation.validation_status,
            reconciliation.limitation_codes,
            reconciliation.raw_metadata
        from benchmark.benchmark_usage_reconciliations reconciliation
        where reconciliation.arm_run_id = %s
        """,
        (arm_run_ids[ARM_ID],),
    )
    usage_rows = cursor.fetchall()
    if len(usage_rows) != 1:
        raise IntegrationSafetyError("Qwen usage reconciliation count verification failed")
    usage = usage_rows[0]

    usage_checks = {
        "reconciliation_version": expected_usage["reconciliation_version"],
        "is_current": expected_usage["is_current"],
        "harness_name": expected_usage["harness_name"],
        "harness_version": expected_usage["harness_version"],
        "configured_route_model": expected_usage["configured_route_model"],
        "configured_backend_model": expected_usage["configured_backend_model"],
        "harness_observed_model": None,
        "provider_observed_model": None,
        "model_identity_status": "matched",
        "harness_input_tokens": 3_177_366,
        "harness_cache_tokens": 0,
        "harness_output_tokens": 1_162_240,
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
    }
    for key, expected in usage_checks.items():
        if usage[key] != expected:
            raise IntegrationSafetyError(f"Qwen usage verification failed: {key}")
    if list(usage["limitation_codes"]) != expected_usage["limitation_codes"]:
        raise IntegrationSafetyError("Qwen usage limitation-code verification failed")
    if usage["raw_metadata"] != expected_usage["raw_metadata"]:
        raise IntegrationSafetyError("Qwen usage raw-metadata verification failed")

    expected_cost = plan["cost_reconciliations"][0]
    cursor.execute(
        """
        select
            reconciliation.reconciliation_version,
            reconciliation.is_current,
            reconciliation.harness_name,
            reconciliation.harness_version,
            reconciliation.harness_reported_cost_usd,
            reconciliation.provider_billed_cost_usd,
            reconciliation.provider_rate_reconstructed_cost_usd,
            reconciliation.selected_cost_usd,
            reconciliation.selected_cost_basis,
            reconciliation.selected_cost_relation,
            reconciliation.validation_status,
            reconciliation.provider_evidence_visible,
            reconciliation.limitation_codes,
            reconciliation.raw_metadata,
            pricing.provider,
            pricing.provider_model
        from benchmark.benchmark_cost_reconciliations reconciliation
        join benchmark.benchmark_provider_pricing_snapshots pricing
          on pricing.id = reconciliation.pricing_snapshot_id
        where reconciliation.arm_run_id = %s
        """,
        (arm_run_ids[ARM_ID],),
    )
    cost_rows = cursor.fetchall()
    if len(cost_rows) != 1:
        raise IntegrationSafetyError("Qwen cost reconciliation count verification failed")
    cost = cost_rows[0]

    if Decimal(cost["harness_reported_cost_usd"]) != Decimal(
        expected_cost["harness_reported_cost_usd"]
    ):
        raise IntegrationSafetyError("Qwen cost verification failed: harness cost")
    if cost["provider_billed_cost_usd"] is not None:
        raise IntegrationSafetyError("Qwen provider billed cost must remain NULL")
    if Decimal(cost["provider_rate_reconstructed_cost_usd"]) != Decimal("2.50442432"):
        raise IntegrationSafetyError("Qwen reconstructed cost verification failed")
    if Decimal(cost["selected_cost_usd"]) != Decimal("2.50442432"):
        raise IntegrationSafetyError("Qwen selected cost verification failed")

    for key, expected in {
        "reconciliation_version": expected_cost["reconciliation_version"],
        "is_current": True,
        "harness_name": "claude-code",
        "harness_version": None,
        "selected_cost_basis": "lower_bound_provider_evidence",
        "selected_cost_relation": "lower_bound",
        "validation_status": "validated_qualified",
        "provider_evidence_visible": True,
        "provider": PROVIDER,
        "provider_model": BACKEND_MODEL,
    }.items():
        if cost[key] != expected:
            raise IntegrationSafetyError(f"Qwen cost verification failed: {key}")
    if list(cost["limitation_codes"]) != expected_cost["limitation_codes"]:
        raise IntegrationSafetyError("Qwen cost limitation-code verification failed")
    if cost["raw_metadata"] != expected_cost["raw_metadata"]:
        raise IntegrationSafetyError("Qwen cost raw-metadata verification failed")

    return {
        "transaction_counts": counts,
        "usage_reconciliation": {
            "selected_usage_authority": usage["selected_usage_authority"],
            "validation_status": usage["validation_status"],
            "provider_selected_run_tokens_are_null": True,
        },
        "cost_reconciliation": {
            "selected_cost_usd": str(cost["selected_cost_usd"]),
            "selected_cost_basis": cost["selected_cost_basis"],
            "selected_cost_relation": cost["selected_cost_relation"],
            "validation_status": cost["validation_status"],
            "provider_billed_cost_is_null": True,
        },
    }


def verify_provider_evidence_details(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> dict[str, str]:
    del arm_run_ids
    expected_sources = {row["source_key"]: row for row in plan["sources"]}

    cursor.execute(
        """
        select
            provider,
            evidence_kind,
            source_scope,
            provider_reference,
            source_sha256,
            size_bytes,
            source_format,
            integrity_status,
            notes,
            arm_run_id is null as arm_run_is_null,
            artifact_id is null as artifact_is_null,
            source_uri is null as source_uri_is_null,
            raw_metadata
        from benchmark.benchmark_provider_evidence_sources
        where provider = %s
        order by source_sha256
        """,
        (PROVIDER,),
    )
    source_rows = cursor.fetchall()
    if len(source_rows) != len(expected_sources):
        raise IntegrationSafetyError("Qwen evidence source row count verification failed")
    by_sha = {str(row["source_sha256"]): row for row in source_rows}
    for expected in expected_sources.values():
        row = by_sha.get(expected["source_sha256"])
        if row is None:
            raise IntegrationSafetyError("reviewed Qwen evidence source SHA-256 is missing")
        checks = {
            "provider": expected["provider"],
            "evidence_kind": expected["evidence_kind"],
            "source_scope": expected["source_scope"],
            "provider_reference": expected["provider_reference"],
            "source_sha256": expected["source_sha256"],
            "size_bytes": expected["size_bytes"],
            "source_format": expected["source_format"],
            "integrity_status": expected["integrity_status"],
            "notes": expected["notes"],
            "arm_run_is_null": True,
            "artifact_is_null": True,
            "source_uri_is_null": True,
            "raw_metadata": expected.get("raw_metadata", {}),
        }
        for key, value in checks.items():
            if row[key] != value:
                raise IntegrationSafetyError(f"Qwen source provenance verification failed: {key}")

    pricing = plan["pricing_snapshots"][0]
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
        where pricing.provider = %s
        """,
        (PROVIDER,),
    )
    pricing_rows = cursor.fetchall()
    if len(pricing_rows) != 1:
        raise IntegrationSafetyError("Qwen pricing row count verification failed")
    row = pricing_rows[0]
    source_sha = expected_sources[pricing["source_key"]]["source_sha256"]
    pricing_checks = {
        "source_sha256": source_sha,
        "provider": PROVIDER,
        "provider_model": BACKEND_MODEL,
        "currency": "USD",
        "effective_from": None,
        "effective_until": None,
        "pricing_semantics": pricing["pricing_semantics"],
        "pricing_rules": pricing["pricing_rules"],
        "official_source_uri": None,
        "notes": pricing["notes"],
        "raw_metadata": pricing["raw_metadata"],
    }
    for key, value in pricing_checks.items():
        if row[key] != value:
            raise IntegrationSafetyError(f"Qwen pricing verification failed: {key}")

    cursor.execute(
        """
        select count(*) as count
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = %s
        """,
        (PROVIDER,),
    )
    if int(cursor.fetchone()["count"]) != 0:
        raise IntegrationSafetyError("Qwen provider usage evidence must remain empty")

    expected_cost_rows = plan["provider_cost_evidence"]
    cursor.execute(
        """
        select
            source.source_sha256,
            evidence.arm_run_id is null as arm_run_is_null,
            evidence.trial_id is null as trial_is_null,
            pricing.provider_model as pricing_provider_model,
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
        where source.provider = %s
        order by evidence.cost_kind, evidence.amount_usd
        """,
        (PROVIDER,),
    )
    observed_cost_rows = cursor.fetchall()
    if len(observed_cost_rows) != len(expected_cost_rows):
        raise IntegrationSafetyError("Qwen provider cost row count verification failed")

    expected_by_kind = {
        row["cost_kind"]: row for row in expected_cost_rows
    }
    for row in observed_cost_rows:
        expected = expected_by_kind.get(row["cost_kind"])
        if expected is None:
            raise IntegrationSafetyError("unexpected Qwen provider cost kind")
        pricing_model = (
            None
            if expected["pricing_snapshot_key"] is None
            else BACKEND_MODEL
        )
        checks = {
            "source_sha256": expected_sources[expected["source_key"]]["source_sha256"],
            "arm_run_is_null": True,
            "trial_is_null": True,
            "pricing_provider_model": pricing_model,
            "provider_model": None,
            "currency": "USD",
            "allocation_scope": "account_window",
            "completeness_status": "complete",
            "notes": expected["notes"],
            "raw_metadata": expected["raw_metadata"],
        }
        for key, value in checks.items():
            if row[key] != value:
                raise IntegrationSafetyError(f"Qwen provider cost verification failed: {key}")
        if Decimal(row["amount_usd"]) != Decimal(expected["amount_usd"]):
            raise IntegrationSafetyError("Qwen provider cost amount verification failed")

    cursor.execute(
        """
        select
            'usage' as reconciliation_type,
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
        where arm_run.arm_id = %s
        union all
        select
            'cost' as reconciliation_type,
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
        where arm_run.arm_id = %s
        """,
        (ARM_ID, ARM_ID),
    )
    actual_links = {
        (
            str(row["reconciliation_type"]),
            str(row["arm_id"]),
            str(row["source_sha256"]),
            str(row["evidence_role"]),
        )
        for row in cursor.fetchall()
    }
    source_sha_by_key = {
        row["source_key"]: row["source_sha256"] for row in plan["sources"]
    }
    expected_links = {
        (
            "usage",
            ARM_ID,
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan["usage_reconciliation_source_links"]
    } | {
        (
            "cost",
            ARM_ID,
            source_sha_by_key[row["source_key"]],
            row["evidence_role"],
        )
        for row in plan["cost_reconciliation_source_links"]
    }
    if actual_links != expected_links:
        raise IntegrationSafetyError("Qwen reconciliation source-link verification failed")

    return {
        "source_rows": "pass",
        "pricing_rows": "pass",
        "usage_evidence_rows": "pass_zero",
        "cost_evidence_rows": "pass",
        "reconciliation_source_links": "pass",
    }


def inspect_target_state(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    counts = target_table_counts(cursor, plan)
    if not any(counts.values()):
        return {"state": "qwen_empty", "counts": counts}

    if counts != plan["write_counts"]:
        return {
            "state": "partial_or_unexpected",
            "counts": counts,
            "reason": "unexpected_table_counts",
        }

    try:
        arm_run_ids = resolve_arm_runs(cursor, plan)
        reconciliation = verify_inserted_state(cursor, plan, arm_run_ids)
        provider = verify_provider_evidence_details(cursor, plan, arm_run_ids)
    except Exception as exc:
        return {
            "state": "partial_or_unexpected",
            "counts": counts,
            "reason": "content_verification_failed",
            "verification_error_type": type(exc).__name__,
        }

    return {
        "state": "exact_qwen_state",
        "counts": counts,
        "resolved_arm_run_ids": arm_run_ids,
        "reconciliation_verification": reconciliation,
        "provider_verification": provider,
    }


def check_only(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    connection = psycopg.connect(
        db_url,
        autocommit=False,
        row_factory=dict_row,
    )
    try:
        diagnostics.enter("target_state_preflight")
        with connection.cursor() as cursor:
            cursor.execute("set transaction read only")
            state = inspect_target_state(cursor, plan)
            diagnostics.target_state = state["state"]

            if state["state"] == "qwen_empty":
                diagnostics.enter("canonical_run_resolution")
                resolved = resolve_arm_runs(cursor, plan)
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
                        "selected_run_lower_bound_reconstruction": "pass",
                        "read_only_transaction": "pass",
                    },
                }
            elif state["state"] == "exact_qwen_state":
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
                    "Qwen provider evidence target is partially or unexpectedly populated"
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
    from psycopg.rows import dict_row

    connection = psycopg.connect(
        db_url,
        autocommit=False,
        row_factory=dict_row,
    )
    try:
        with connection.cursor() as cursor:
            diagnostics.enter("advisory_lock")
            acquire_ingestion_lock(cursor)

            diagnostics.enter("target_state_preflight")
            state = inspect_target_state(cursor, plan)
            diagnostics.target_state = state["state"]
            if state["state"] != "qwen_empty":
                raise IntegrationSafetyError(
                    "Qwen rollback-only requires an empty provider target"
                )

            diagnostics.enter("canonical_run_resolution")
            arm_run_ids = resolve_arm_runs(cursor, plan)

            diagnostics.enter("transactional_insert")
            insert_plan(cursor, plan, arm_run_ids)

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
            transaction_counts = target_table_counts(cursor, plan)

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
        row_factory=dict_row,
    )
    try:
        with observer.cursor() as cursor:
            cursor.execute("set transaction read only")
            zero_counts = target_table_counts(cursor, plan)
            diagnostics.zero_persistence_counts = zero_counts
            if any(zero_counts.values()):
                raise IntegrationSafetyError(
                    "Qwen rollback-only left persistent provider rows"
                )
        observer.rollback()
    finally:
        observer.close()

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state": diagnostics.commit_state,
        "target_state": "qwen_empty",
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
    from psycopg.rows import dict_row

    connection: Any = None
    try:
        diagnostics.enter("transaction_connection")
        connection = psycopg.connect(
            db_url,
            autocommit=False,
            row_factory=dict_row,
        )
        with connection.cursor() as cursor:
            diagnostics.enter("advisory_lock")
            acquire_ingestion_lock(cursor)

            diagnostics.enter("target_state_preflight")
            state = inspect_target_state(cursor, plan)
            diagnostics.target_state = state["state"]

            if state["state"] == "exact_qwen_state":
                raise IntegrationSafetyError(
                    "reviewed Qwen provider evidence is already applied"
                )
            if state["state"] != "qwen_empty":
                raise IntegrationSafetyError(
                    "Qwen provider evidence target is partially or unexpectedly populated"
                )

            diagnostics.enter("canonical_run_resolution")
            arm_run_ids = resolve_arm_runs(cursor, plan)

            diagnostics.enter("transactional_insert")
            insert_plan(cursor, plan, arm_run_ids)

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
        row_factory=dict_row,
    )
    try:
        with observer.cursor() as cursor:
            cursor.execute("set transaction read only")
            state = inspect_target_state(cursor, plan)
            if state["state"] != "exact_qwen_state":
                raise IntegrationSafetyError(
                    "committed Qwen evidence failed second-connection verification"
                )
            persisted_counts = state["counts"]
        observer.rollback()
    finally:
        observer.close()

    return {
        "status": "applied",
        "mode": "apply",
        "commit_state": diagnostics.commit_state,
        "target_state": "exact_qwen_state",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, verify, rollback-test, or apply reviewed Qwen provider evidence."
        )
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--rollback-only", action="store_true")
    modes.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def _mode_name(args: argparse.Namespace) -> str:
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


def _plan_payload(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "planned",
        "mode": "plan",
        "provider": plan["provider"],
        "plan_version": plan["plan_version"],
        "reviewed_plan_sha256": plan["reviewed_plan_sha256"],
        "snapshot_sha256": plan["snapshot_sha256"],
        "write_counts": plan["write_counts"],
        "selected_runs": plan["selected_runs"],
        "provider_usage_evidence_rows": len(plan["provider_usage_evidence"]),
        "excluded_evidence": plan["excluded_evidence"],
    }


def main(argv: list[str] | None = None) -> int:
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
                result = check_only(plan, db_url, diagnostics)
            elif args.rollback_only:
                result = rollback_only(plan, db_url, diagnostics)
            else:
                result = apply_permanent(plan, db_url, diagnostics)

        print(json.dumps(result, indent=2, sort_keys=True))
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
