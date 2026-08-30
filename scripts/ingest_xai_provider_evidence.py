#!/usr/bin/env python3
"""Plan, verify, or apply xAI Phase 3 provider-evidence ingestion."""

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
XAI_SNAPSHOT = ROOT / "results/phase3/supplemental/xai_provider_evidence_snapshot_20260827.json"
PROVIDER_REPORT = ROOT / "docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md"
PROVIDER_LEDGER = ROOT / "results/phase3/provider_usage/normalized/provider_reconciliation_ledger_2026-06-19.csv"
CURRENT_RECONCILIATION = ROOT / "results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv"
EVIDENCE_MATRIX = ROOT / "results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv"
RUN_CHRONOLOGY = ROOT / "results/phase3/reporting/phase3_provider_run_chronology_20260825.csv"
REVIEWED_PLAN_SHA256 = "eac1bc5e7070ef46d6ae9488ac4ea7f03874a9a91bf215fe48a32fb7ae9aba49"
EXPECTED_INPUT_HASHES = {
    str(XAI_SNAPSHOT.relative_to(ROOT)): "dbb0adaa14460adf1b02b9ac140c7eb430702e4dc9c45d8b879ebd9de9a8b3dc",
    str(PROVIDER_REPORT.relative_to(ROOT)): "29604cf5ce8e8b866aff51cec5ae92ef3c675def10277abae76c9143bd6962d4",
    str(PROVIDER_LEDGER.relative_to(ROOT)): "a803e70495886551ea7f810b3ee82cf8913aa70fb32e861a8b4fd5bf72225f0c",
    str(CURRENT_RECONCILIATION.relative_to(ROOT)): "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256",
    str(EVIDENCE_MATRIX.relative_to(ROOT)): "e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218",
    str(RUN_CHRONOLOGY.relative_to(ROOT)): "3ad11e7e760c1efaac72b9083a145470671ff5c2ebc149be41082379fb5c7b77",
}
ARM_CONTRACT = {
    "router-grok-build-0.1": {
        "selected_run_label": "router-grok-build-0.1/2026-06-28__13-28-55",
        "backend_model": "grok-build-0.1",
        "trial_count": 60,
        "complete_trial_cost_count": 59,
        "lower_bound_trial_count": 1,
        "retained_usage_trial_count": 59,
        "unresolved_usage_trial_count": 1,
        "harness_input_tokens": 2913256,
        "harness_cache_tokens": 0,
        "harness_cache_miss_tokens": 2913256,
        "harness_output_tokens": 1752719,
        "selected_cost_usd": Decimal("6.418694"),
        "historical_harness_cost_usd": Decimal("38.149845"),
        "historical_reviewed_cost_usd": Decimal("53.153814003353"),
        "reporting_selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "db_selected_cost_basis": "lower_bound_provider_evidence",
        "selected_cost_relation": "lower_bound",
        "selected_cost_confidence": "high_for_retained_accounting_lower_bound",
        "evidence_class": "verified_retained_trajectories_plus_official_provider_rates",
        "trial_cost_allocation_status": "available_with_unresolved_usage_lower_bounds",
        "outcome_cost_allocation_status": "available_lower_bound",
        "unquantified_additional_cost_status": "possible_additional_unresolved_trial_spend",
        "cache_hit_rate": Decimal("1"),
        "cache_miss_rate": Decimal("1"),
        "output_rate": Decimal("2"),
    }
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
INGESTION_LOCK_NAME = "cc-deepseek-bench:xai-provider-evidence-ingestion:v1"

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
    zero_persistence_counts: dict[str, int] = field(
        default_factory=dict
    )

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
        raise EvidencePlanError(
            f"reviewed xAI evidence mismatch: {label}"
        )


def verify_input_hashes() -> dict[str, str]:
    actual = {
        relative: sha256_path(ROOT / relative)
        for relative in EXPECTED_INPUT_HASHES
    }

    if actual != EXPECTED_INPUT_HASHES:
        raise EvidencePlanError(
            "reviewed xAI input hashes changed"
        )

    return actual


def reconstruct_cost(
    *,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    output_tokens: int,
    spec: Mapping[str, Any],
) -> Decimal:
    return (
        Decimal(cache_hit_tokens)
        * spec["cache_hit_rate"]
        + Decimal(cache_miss_tokens)
        * spec["cache_miss_rate"]
        + Decimal(output_tokens)
        * spec["output_rate"]
    ) / Decimal(1_000_000)



def build_plan() -> dict[str, Any]:
    hashes = verify_input_hashes()
    snapshot_raw = XAI_SNAPSHOT.read_text(encoding="utf-8")
    if ".run/review" in snapshot_raw or ".secrets/" in snapshot_raw:
        raise EvidencePlanError("sanitized xAI snapshot contains private paths")
    snapshot = json.loads(snapshot_raw)
    require_equal(snapshot.get("schema_version"), 1, "xAI snapshot schema version")
    require_equal(snapshot.get("evidence_version"), "xai-provider-evidence-20260827-v1", "xAI snapshot evidence version")
    require_equal(snapshot.get("provider"), "xai", "xAI snapshot provider")
    require_equal(snapshot.get("reviewed_private_plan_sha256"), REVIEWED_PLAN_SHA256, "xAI reviewed private plan SHA-256")
    require_equal(snapshot.get("private_recovery_paths_retained"), False, "xAI private recovery path retention")
    require_equal(snapshot.get("raw_provider_export_available"), False, "xAI raw provider export availability")
    require_equal(snapshot.get("granular_model_request_export_available"), False, "xAI granular provider export availability")

    selected_arm = snapshot.get("selected_arm")
    require_equal(selected_arm, {
        "arm_id": "router-grok-build-0.1",
        "backend_model": "grok-build-0.1",
        "run_label": "router-grok-build-0.1/2026-06-28__13-28-55",
        "trial_count": 60,
    }, "xAI selected arm")

    selected_reconciliation = snapshot.get("selected_run_reconciliation")
    require_equal(selected_reconciliation, {
        "limitation": "one selected trial remains unresolved; provider dashboard aggregates are not run-allocable",
        "provider_billed_cost_usd": None,
        "provider_dashboard_90d_cost_usd": "42.40",
        "provider_dashboard_90d_selected_run_allocable": False,
        "retained_input_tokens": 2913256,
        "retained_output_tokens": 1752719,
        "retained_reconstructed_cost_usd": "6.418694",
        "retained_usage_trials": 59,
        "selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "selected_cost_relation": "lower_bound",
        "selected_cost_usd": "6.418694",
        "unresolved_usage_trials": 1,
    }, "xAI selected-run reconciliation snapshot")

    observations = snapshot.get("provider_dashboard_observations")
    if not isinstance(observations, list) or len(observations) != 2 or not all(isinstance(row, dict) for row in observations):
        raise EvidencePlanError("xAI dashboard observations do not resolve to exactly two rows")
    by_date = {row.get("observation_date"): row for row in observations}
    require_equal(set(by_date), {"2026-06-19", "2026-08-27"}, "xAI dashboard observation dates")
    june = by_date["2026-06-19"]
    august = by_date["2026-08-27"]
    for key, expected in {
        "amount_usd": "6.36",
        "evidence_kind": "provider_dashboard_total",
        "scope": "provider_window",
        "selected_run_allocable": False,
        "selected_run_relation": "predates_selected_run",
        "source_kind": "manual_capture",
        "token_total_canonical": 5927385,
        "token_total_separately_observed": 5927462,
    }.items():
        require_equal(june.get(key), expected, f"xAI June dashboard {key}")
    for key, expected in {
        "amount_display_semantics": "total credits usage",
        "amount_usd": "42.40",
        "api_key_filter": "not_established",
        "evidence_kind": "provider_dashboard_total",
        "scope": "provider_window",
        "selected_run_allocable": False,
        "selected_run_relation": "window_contains_selected_run_date",
        "source_kind": "manual_capture",
        "window_boundaries_exact": False,
    }.items():
        require_equal(august.get(key), expected, f"xAI August dashboard {key}")

    historical_context = snapshot.get("historical_non_provider_cost_context")
    require_equal(historical_context, {
        "canary_harness_cost_usd": "0.710016",
        "canary_scaled_60_attempt_forecast_usd": "42.60096",
        "historical_full_run_recorded_cost_usd": "38.149845",
        "historical_full_run_reviewed_cost_usd": "53.153814003353",
        "provider_authority": False,
    }, "xAI historical non-provider cost context")

    require_equal(snapshot.get("principles"), {
        "historical_results_frozen": True,
        "no_historical_raw_cost_rewrite": True,
        "no_missing_usage_synthesized_as_zero": True,
        "no_synthetic_provider_allocation": True,
        "provider_dashboard_context_is_not_selected_run_billing": True,
    }, "xAI normalization principles")

    ledger_rows = [row for row in read_csv(PROVIDER_LEDGER) if row.get("provider_family") == "xAI / Grok"]
    if len(ledger_rows) != 1:
        raise EvidencePlanError("xAI provider ledger row does not resolve exactly once")
    ledger = ledger_rows[0]
    for key, expected in {
        "api_key_family": "XAI_API_KEY",
        "evidence_level": "provider-dashboard-total-plus-artifacts",
        "benchmark_marginal_cost_usd": "6.36",
        "provider_account_spend_usd": "6.36",
        "provider_tokens_known": "yes",
        "provider_cost_known": "yes",
        "primary_evidence": "xAI dashboard manually observed total tokens and cost",
        "remaining_gap": "Granular model/request export unavailable",
    }.items():
        require_equal(ledger.get(key, ""), expected, f"xAI provider ledger {key}")

    current_rows = [row for row in read_csv(CURRENT_RECONCILIATION) if row.get("arm_id") == "router-grok-build-0.1"]
    if len(current_rows) != 1:
        raise EvidencePlanError("current xAI selected-run reconciliation does not resolve exactly once")
    current = current_rows[0]
    spec = ARM_CONTRACT["router-grok-build-0.1"]
    for key, expected in {
        "selected_run_label": spec["selected_run_label"],
        "backend_model": spec["backend_model"],
        "provider_models": spec["backend_model"],
        "provider": "xai",
        "selected_cost_usd": "6.418694",
        "selected_cost_relation": "lower_bound",
        "selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "selected_cost_confidence": "high_for_retained_accounting_lower_bound",
        "evidence_class": "verified_retained_trajectories_plus_official_provider_rates",
        "provider_billed_cost_usd": "",
        "provider_context_billed_cost_usd": "6.36",
        "provider_context_scope": "preselected_family_dashboard_total_through_2026-06-19",
        "provider_billing_reconciliation_status": "preselected_provider_context_not_selected_run",
        "trial_count": "60",
        "complete_trial_cost_count": "59",
        "lower_bound_trial_count": "1",
        "confirmed_zero_cost_trial_count": "0",
        "trial_cost_allocation_status": "available_with_unresolved_usage_lower_bounds",
        "outcome_cost_allocation_status": "available_lower_bound",
        "known_allocated_cost_usd": "6.418694",
        "unquantified_additional_cost_status": "possible_additional_unresolved_trial_spend",
        "historical_harness_recorded_cost_usd": "38.149845",
        "historical_reviewed_cost_usd": "53.153814003353",
    }.items():
        require_equal(current.get(key, ""), expected, f"xAI current reconciliation {key}")
    note = current.get("evidence_note", "")
    for fact in ("$1/M input and $2/M output", "polyglot-rust-c", "$6.36 provider dashboard snapshot predates the selected June 28 run"):
        if fact not in note:
            raise EvidencePlanError(f"xAI current reconciliation fact missing: {fact}")

    matrix_rows = [row for row in read_csv(EVIDENCE_MATRIX) if row.get("arm_id") == "router-grok-build-0.1"]
    if len(matrix_rows) != 1:
        raise EvidencePlanError("xAI evidence-matrix row does not resolve exactly once")
    matrix = matrix_rows[0]
    for key, expected in {
        "provider": "xai",
        "selected_run_label": spec["selected_run_label"],
        "selected_cost_usd": "6.418694",
        "selected_cost_relation": "lower_bound",
        "selected_cost_basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "selected_cost_confidence": "high_for_retained_accounting_lower_bound",
        "trial_count": "60",
        "complete_trial_cost_count": "59",
        "unresolved_trial_count": "1",
        "selected_input_tokens": "2913256",
        "selected_cache_tokens": "0",
        "selected_output_tokens": "1752719",
        "trajectory_evidence_status": "60_trajectories_exactly_match_coverage;1_zero_metric_trial",
        "pricing_provenance_status": "official_xai_build_0.1_launch_rates",
        "provider_context_billed_cost_usd": "6.36",
        "provider_context_scope": "preselected_family_dashboard_total_through_2026-06-19",
        "provider_context_temporal_relation": "predates_selected_run",
        "provider_context_allocation_confidence": "not_allocable_to_selected_run",
        "historical_harness_recorded_cost_usd": "38.149845",
        "historical_reviewed_cost_usd": "53.153814003353",
    }.items():
        require_equal(matrix.get(key, ""), expected, f"xAI evidence matrix {key}")
    if "$1/M input and $2/M output" not in matrix.get("audit_conclusion", ""):
        raise EvidencePlanError("xAI pricing-rate audit conclusion changed")

    chronology_rows = [row for row in read_csv(RUN_CHRONOLOGY) if row.get("arm_id") == "router-grok-build-0.1" and row.get("provider") == "xai"]
    chronology_signatures = {
        (row.get("start_date", ""), row.get("end_date", ""), row.get("event_type", ""), row.get("run_label_or_scope", ""), row.get("amount_usd", ""), row.get("amount_kind", ""), row.get("relation_to_selected_run", ""), row.get("allocation_confidence", ""))
        for row in chronology_rows
    }
    require_equal(chronology_signatures, {
        ("2026-06-04", "2026-06-04", "canary", "router-grok-build-0.1/2026-06-04__03-06-37", "", "", "preselected_run", "artifact_level"),
        ("2026-06-16", "2026-06-16", "smoke", "router-grok-build-0.1/2026-06-16__14-53-30", "", "", "preselected_run", "artifact_level"),
        ("", "2026-06-19", "provider_dashboard_snapshot", "xAI family dashboard total", "6.36", "provider_dashboard_total", "predates_selected_run", "not_run_allocable"),
        ("2026-06-28", "2026-06-28", "selected_full", spec["selected_run_label"], "6.418694", "selected_retained_usage_lower_bound", "selected_run", "59_of_60_usage_bearing"),
    }, "xAI provider chronology")

    snapshot_key = "xai_sanitized_provider_snapshot"
    current_key = "xai_current_reconciliation"
    pricing_source_key = "xai_reviewed_pricing_matrix"
    pricing_key = "xai-grok-build-0.1-reviewed-rates"

    sources = [
        {"source_key": snapshot_key, "provider": "xai", "evidence_kind": "manual_capture", "source_scope": "provider_window", "provider_reference": str(XAI_SNAPSHOT.relative_to(ROOT)), "source_sha256": hashes[str(XAI_SNAPSHOT.relative_to(ROOT))], "source_format": "json", "integrity_status": "sha256_verified", "notes": "Sanitized additive xAI evidence snapshot derived from the reviewed private recovery plan. It retains the June 19 and August 27 provider dashboard observations without private recovery paths. Neither dashboard aggregate is selected-run billing.", "raw_metadata": {"reviewed_private_plan_sha256": REVIEWED_PLAN_SHA256, "dashboard_observation_count": 2, "granular_model_request_export_available": False}},
        {"source_key": current_key, "provider": "xai", "evidence_kind": "manual_capture", "source_scope": "other", "provider_reference": str(CURRENT_RECONCILIATION.relative_to(ROOT)), "source_sha256": hashes[str(CURRENT_RECONCILIATION.relative_to(ROOT))], "source_format": "csv", "integrity_status": "sha256_verified", "notes": "Reviewed current Phase 3 selected-run reconciliation for router-grok-build-0.1. This source preserves the 59-of-60 retained usage lower-bound semantics and historical cost context without rewriting frozen raw results."},
        {"source_key": pricing_source_key, "provider": "xai", "evidence_kind": "pricing_snapshot", "source_scope": "pricing_snapshot", "provider_reference": str(EVIDENCE_MATRIX.relative_to(ROOT)), "source_sha256": hashes[str(EVIDENCE_MATRIX.relative_to(ROOT))], "source_format": "csv", "integrity_status": "sha256_verified", "notes": "Reviewed provider-evidence matrix retaining the xAI grok-build-0.1 launch-rate provenance status and the $1/M input plus $2/M output reconstruction used for the selected lower bound."},
    ]
    pricing_snapshots = [{"pricing_key": pricing_key, "source_key": pricing_source_key, "provider": "xai", "provider_model": spec["backend_model"], "currency": "USD", "effective_from": None, "effective_until": None, "pricing_semantics": "input_plus_output_no_selected_cache_usage", "pricing_rules": {"input_usd_per_million": "1", "output_usd_per_million": "2", "selected_run_cache_tokens": 0, "reviewed_pricing_provenance_status": "official_xai_build_0.1_launch_rates"}, "official_source_uri": None, "notes": "Repository-retained reviewed xAI rate snapshot. The selected run has zero cache tokens; retained input is priced at $1/M and output at $2/M. No provider pricing URI is normalized into this row; provenance is the hash-pinned reviewed evidence matrix."}]
    selected_runs = [{"arm_id": "router-grok-build-0.1", "selected_run_label": spec["selected_run_label"], "backend_model": spec["backend_model"], "trial_count": spec["trial_count"], "harness_input_tokens": spec["harness_input_tokens"], "harness_cache_tokens": spec["harness_cache_tokens"], "harness_cache_miss_tokens": spec["harness_cache_miss_tokens"], "harness_output_tokens": spec["harness_output_tokens"], "selected_cost_usd": money(spec["selected_cost_usd"])}]
    usage_reconciliations = [{"arm_id": "router-grok-build-0.1", "reconciliation_version": "xai-provider-evidence-v1", "is_current": True, "harness_name": "claude-code", "harness_version": None, "configured_route_model": "router-grok-build-0.1", "configured_backend_model": spec["backend_model"], "harness_observed_model": None, "provider_observed_model": None, "model_identity_status": "matched", "harness_input_tokens": spec["harness_input_tokens"], "harness_cache_tokens": spec["harness_cache_tokens"], "harness_output_tokens": spec["harness_output_tokens"], "provider_ordinary_input_tokens": None, "provider_cache_read_input_tokens": None, "provider_cache_creation_input_tokens": None, "provider_output_tokens": None, "provider_request_count": None, "matched_provider_request_count": None, "unallocated_provider_request_count": None, "provider_evidence_visible": True, "selected_usage_authority": "harness_usage_validated", "validation_status": "validated_qualified", "limitation_codes": ["selected_run_provider_usage_export_unavailable", "selected_run_provider_billing_unavailable", "one_selected_trial_usage_unresolved", "missing_usage_not_synthesized_as_zero", "provider_dashboard_aggregates_not_run_allocable", "selected_run_provider_observed_model_unavailable"], "notes": "The selected harness aggregate contains 2,913,256 input and 1,752,719 output tokens from 59 usage-bearing trials. Retained R2 trajectories reproduce the selected usage geometry, while polyglot-rust-c has zero retained token metadata and a zero-metric trajectory. That trial remains unresolved; missing usage is not synthesized as zero. provider_observed_model is intentionally NULL because no granular selected-run xAI provider export is retained."}]
    usage_links = [{"arm_id": "router-grok-build-0.1", "source_key": current_key, "evidence_role": "aggregate_usage"}, {"arm_id": "router-grok-build-0.1", "source_key": current_key, "evidence_role": "model_identity"}]
    cost_reconciliations = [{"arm_id": "router-grok-build-0.1", "reconciliation_version": "xai-provider-evidence-v1", "is_current": True, "harness_name": "claude-code", "harness_version": None, "harness_reported_cost_usd": money(spec["historical_harness_cost_usd"]), "provider_billed_cost_usd": None, "provider_rate_reconstructed_cost_usd": money(spec["selected_cost_usd"]), "selected_cost_usd": money(spec["selected_cost_usd"]), "selected_cost_basis": spec["db_selected_cost_basis"], "selected_cost_relation": spec["selected_cost_relation"], "validation_status": "validated_qualified", "provider_evidence_visible": True, "pricing_snapshot_key": pricing_key, "limitation_codes": ["selected_run_provider_billing_unavailable", "selected_run_provider_usage_export_unavailable", "one_selected_trial_usage_unresolved", "possible_additional_unresolved_trial_spend", "provider_dashboard_june19_predates_selected_run", "provider_dashboard_90d_not_run_allocable", "provider_dashboard_90d_api_key_filter_not_established", "provider_dashboard_90d_exact_boundaries_not_retained", "missing_usage_not_synthesized_as_zero", "selected_run_provider_observed_model_unavailable"], "notes": "Selected cost is a retained-accounting lower bound reconstructed at the reviewed $1/M input and $2/M output rates. It covers 59 usage-bearing trials and totals $6.418694. One trial remains unresolved, so possible additional spend is not synthesized. The June 19 $6.36 dashboard snapshot predates the selected run. The August 27 $42.40 rolling-90-day dashboard total includes the selected-run date but is not run-allocable and has no established API-key filter state. provider_billed_cost therefore remains NULL."}]
    cost_links = [{"arm_id": "router-grok-build-0.1", "source_key": current_key, "evidence_role": "lower_bound"}, {"arm_id": "router-grok-build-0.1", "source_key": pricing_source_key, "evidence_role": "pricing"}, {"arm_id": "router-grok-build-0.1", "source_key": snapshot_key, "evidence_role": "context"}]
    provider_cost_evidence = [{"source_key": snapshot_key, "arm_run_id": None, "trial_id": None, "pricing_snapshot_key": None, "provider_model": None, "cost_kind": "provider_dashboard_total", "amount_usd": observation["amount_usd"], "currency": "USD", "allocation_scope": "provider_window", "completeness_status": "aggregate_only", "notes": f"xAI provider dashboard aggregate observed on {observation['observation_date']}. This row is provider/account-window context only and is not selected-run provider billing.", "raw_metadata": dict(observation)} for observation in observations]
    provider_usage_evidence = []
    excluded_evidence = [
        {"evidence": "june_19_6.36_dashboard_total_as_selected_run_bill", "reason": "predates the selected June 28 run", "normalized_as_selected_provider_billing": False},
        {"evidence": "august_27_42.40_rolling_90d_total_as_selected_run_bill", "reason": "window contains selected-run date but is not run-allocable; exact boundaries and API-key filter state are not retained", "normalized_as_selected_provider_billing": False},
        {"evidence": "polyglot_rust_c_missing_usage_as_zero", "reason": "zero retained token/trajectory metrics do not prove zero provider spend", "synthesized_as_zero": False},
        {"evidence": "configured_model_as_provider_observed_model", "reason": "no granular selected-run provider export is retained", "provider_observed_model_populated": False},
        {"evidence": "canonical_and_separately_observed_dashboard_token_totals_collapsed", "reason": "5,927,385 canonical retained tokens and 5,927,462 separately observed tokens remain distinct observations", "collapsed": False},
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
    require_equal(write_counts, {
        "benchmark_provider_evidence_sources": 3,
        "benchmark_provider_usage_evidence": 0,
        "benchmark_provider_pricing_snapshots": 1,
        "benchmark_provider_cost_evidence": 2,
        "benchmark_usage_reconciliations": 1,
        "benchmark_usage_reconciliation_sources": 2,
        "benchmark_cost_reconciliations": 1,
        "benchmark_cost_reconciliation_sources": 3,
        "benchmark_evidence_promotion_gates": 0,
    }, "planned xAI row cardinality")
    selected = selected_runs[0]
    reconstructed = reconstruct_cost(cache_hit_tokens=selected["harness_cache_tokens"], cache_miss_tokens=selected["harness_cache_miss_tokens"], output_tokens=selected["harness_output_tokens"], spec=spec)
    require_equal(reconstructed, spec["selected_cost_usd"], "xAI selected rate arithmetic")
    return {
        "schema_version": 1,
        "plan_version": "xai-provider-evidence-v1",
        "provider": "xai",
        "mode": "plan-only",
        "database_writes_performed": False,
        "reviewed_plan_sha256": REVIEWED_PLAN_SHA256,
        "normalized_input_hashes": hashes,
        "raw_provider_archives": {"raw_provider_export_available": False, "granular_model_request_export_available": False},
        "historical_non_provider_cost_context": historical_context,
        "provider_dashboard_observations": observations,
        "sources": sources,
        "provider_usage_evidence": provider_usage_evidence,
        "pricing_snapshots": pricing_snapshots,
        "provider_cost_evidence": provider_cost_evidence,
        "selected_runs": selected_runs,
        "usage_reconciliations": usage_reconciliations,
        "usage_reconciliation_source_links": usage_links,
        "cost_reconciliations": cost_reconciliations,
        "cost_reconciliation_source_links": cost_links,
        "excluded_evidence": excluded_evidence,
        "write_counts": write_counts,
    }

def target_table_counts(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, int]:
    arm_ids = [
        row["arm_id"]
        for row in plan["selected_runs"]
    ]

    queries: dict[str, tuple[str, tuple[Any, ...]]] = {
        "benchmark_provider_evidence_sources": (
            """
            select count(*)
            from benchmark.benchmark_provider_evidence_sources
            where provider = 'xai'
            """,
            (),
        ),
        "benchmark_provider_usage_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_usage_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'xai'
            """,
            (),
        ),
        "benchmark_provider_pricing_snapshots": (
            """
            select count(*)
            from benchmark.benchmark_provider_pricing_snapshots
            where provider = 'xai'
            """,
            (),
        ),
        "benchmark_provider_cost_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_cost_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'xai'
            """,
            (),
        ),
        "benchmark_usage_reconciliations": (
            """
            select count(*)
            from benchmark.benchmark_usage_reconciliations reconciliation
            join benchmark.benchmark_arm_runs arm_run
              on arm_run.id = reconciliation.arm_run_id
            where arm_run.arm_id = any(%s::text[])
            """,
            (arm_ids,),
        ),
        "benchmark_usage_reconciliation_sources": (
            """
            select count(*)
            from benchmark.benchmark_usage_reconciliation_sources link
            join benchmark.benchmark_usage_reconciliations reconciliation
              on reconciliation.id = link.reconciliation_id
            join benchmark.benchmark_arm_runs arm_run
              on arm_run.id = reconciliation.arm_run_id
            where arm_run.arm_id = any(%s::text[])
            """,
            (arm_ids,),
        ),
        "benchmark_cost_reconciliations": (
            """
            select count(*)
            from benchmark.benchmark_cost_reconciliations reconciliation
            join benchmark.benchmark_arm_runs arm_run
              on arm_run.id = reconciliation.arm_run_id
            where arm_run.arm_id = any(%s::text[])
            """,
            (arm_ids,),
        ),
        "benchmark_cost_reconciliation_sources": (
            """
            select count(*)
            from benchmark.benchmark_cost_reconciliation_sources link
            join benchmark.benchmark_cost_reconciliations reconciliation
              on reconciliation.id = link.reconciliation_id
            join benchmark.benchmark_arm_runs arm_run
              on arm_run.id = reconciliation.arm_run_id
            where arm_run.arm_id = any(%s::text[])
            """,
            (arm_ids,),
        ),
        "benchmark_evidence_promotion_gates": (
            """
            select count(*)
            from benchmark.benchmark_evidence_promotion_gates
            where arm_id = any(%s::text[])
            """,
            (arm_ids,),
        ),
    }

    counts: dict[str, int] = {}

    for table in TARGET_TABLES:
        query, parameters = queries[table]
        cursor.execute(query, parameters)
        counts[table] = int(
            cursor.fetchone()[0]
        )

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
            "state": "xai_empty",
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
        reconciliation_verification = (
            verify_inserted_state(
                cursor,
                plan,
                arm_run_ids,
            )
        )
        provider_verification = (
            verify_provider_evidence_details(
                cursor,
                plan,
                arm_run_ids,
            )
        )
    except Exception as exc:
        return {
            "state": "partial_or_unexpected",
            "counts": counts,
            "reason": "content_verification_failed",
            "verification_error_type":
                type(exc).__name__,
        }

    return {
        "state": "exact_xai_state",
        "counts": counts,
        "resolved_arm_run_ids": arm_run_ids,
        "reconciliation_verification":
            reconciliation_verification,
        "provider_verification":
            provider_verification,
    }


def resolve_arm_runs(
    cursor: Any,
    plan: Mapping[str, Any],
) -> dict[str, str]:
    labels = [
        row["selected_run_label"]
        for row in plan["selected_runs"]
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
                "selected xAI run does not resolve exactly once"
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
            raise IntegrationSafetyError(
                "selected xAI run resolves to wrong arm"
            )
        if suite_id != "phase3-full-20":
            raise IntegrationSafetyError(
                "selected xAI run resolves to wrong suite"
            )
        if logical_mode != "full":
            raise IntegrationSafetyError(
                "selected xAI run is not logical full mode"
            )
        if storage_mode != "raw":
            raise IntegrationSafetyError(
                "selected xAI run is not raw storage mode"
            )
        if int(n_trials) != int(
            selected["trial_count"]
        ):
            raise IntegrationSafetyError(
                "selected xAI run has unexpected trial count"
            )

        geometry = {
            "harness_input_tokens":
                int(input_tokens),
            "harness_cache_tokens":
                int(cache_tokens),
            "harness_output_tokens":
                int(output_tokens),
        }

        expected_geometry = {
            "harness_input_tokens":
                int(
                    selected[
                        "harness_input_tokens"
                    ]
                ),
            "harness_cache_tokens":
                int(
                    selected[
                        "harness_cache_tokens"
                    ]
                ),
            "harness_output_tokens":
                int(
                    selected[
                        "harness_output_tokens"
                    ]
                ),
        }

        if geometry != expected_geometry:
            raise IntegrationSafetyError(
                "selected xAI run token geometry changed"
            )

        cache_miss_tokens = (
            geometry["harness_input_tokens"]
            - geometry["harness_cache_tokens"]
        )

        if cache_miss_tokens != int(
            selected[
                "harness_cache_miss_tokens"
            ]
        ):
            raise IntegrationSafetyError(
                "selected xAI run cache-miss geometry changed"
            )

        spec = ARM_CONTRACT[arm_id]

        reconstructed = reconstruct_cost(
            cache_hit_tokens=(
                geometry["harness_cache_tokens"]
            ),
            cache_miss_tokens=cache_miss_tokens,
            output_tokens=(
                geometry["harness_output_tokens"]
            ),
            spec=spec,
        )

        if reconstructed != Decimal(
            selected["selected_cost_usd"]
        ):
            raise IntegrationSafetyError(
                "selected xAI rate reconstruction changed"
            )

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
        source_ids[source["source_key"]] = (
            cursor.fetchone()[0]
        )

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
        pricing_ids[snapshot["pricing_key"]] = (
            cursor.fetchone()[0]
        )

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
                evidence[
                    "cache_creation_input_tokens"
                ],
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
        pricing_key = evidence[
            "pricing_snapshot_key"
        ]
        if pricing_key is not None:
            pricing_snapshot_id = (
                pricing_ids[pricing_key]
            )

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

    for reconciliation in plan[
        "usage_reconciliations"
    ]:
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
                reconciliation[
                    "reconciliation_version"
                ],
                reconciliation["is_current"],
                reconciliation["harness_name"],
                reconciliation["harness_version"],
                reconciliation[
                    "configured_route_model"
                ],
                reconciliation[
                    "configured_backend_model"
                ],
                reconciliation[
                    "harness_observed_model"
                ],
                reconciliation[
                    "provider_observed_model"
                ],
                reconciliation[
                    "model_identity_status"
                ],
                reconciliation[
                    "harness_input_tokens"
                ],
                reconciliation[
                    "harness_cache_tokens"
                ],
                reconciliation[
                    "harness_output_tokens"
                ],
                reconciliation[
                    "provider_ordinary_input_tokens"
                ],
                reconciliation[
                    "provider_cache_read_input_tokens"
                ],
                reconciliation[
                    "provider_cache_creation_input_tokens"
                ],
                reconciliation[
                    "provider_output_tokens"
                ],
                reconciliation[
                    "provider_request_count"
                ],
                reconciliation[
                    "matched_provider_request_count"
                ],
                reconciliation[
                    "unallocated_provider_request_count"
                ],
                reconciliation[
                    "provider_evidence_visible"
                ],
                reconciliation[
                    "selected_usage_authority"
                ],
                reconciliation[
                    "validation_status"
                ],
                reconciliation[
                    "limitation_codes"
                ],
                reconciliation["notes"],
                Jsonb(
                    reconciliation.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )

        usage_reconciliation_ids[arm_id] = (
            cursor.fetchone()[0]
        )

    for link in plan[
        "usage_reconciliation_source_links"
    ]:
        cursor.execute(
            """
            insert into benchmark.benchmark_usage_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, %s)
            """,
            (
                usage_reconciliation_ids[
                    link["arm_id"]
                ],
                source_ids[
                    link["source_key"]
                ],
                link["evidence_role"],
            ),
        )

    for reconciliation in plan[
        "cost_reconciliations"
    ]:
        arm_id = reconciliation["arm_id"]
        pricing_snapshot_id = pricing_ids[
            reconciliation["pricing_snapshot_key"]
        ]

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
                reconciliation[
                    "reconciliation_version"
                ],
                reconciliation["is_current"],
                reconciliation["harness_name"],
                reconciliation["harness_version"],
                Decimal(
                    reconciliation[
                        "harness_reported_cost_usd"
                    ]
                ),
                reconciliation[
                    "provider_billed_cost_usd"
                ],
                Decimal(
                    reconciliation[
                        "provider_rate_reconstructed_cost_usd"
                    ]
                ),
                Decimal(
                    reconciliation[
                        "selected_cost_usd"
                    ]
                ),
                reconciliation[
                    "selected_cost_basis"
                ],
                reconciliation[
                    "selected_cost_relation"
                ],
                reconciliation[
                    "validation_status"
                ],
                reconciliation[
                    "provider_evidence_visible"
                ],
                pricing_snapshot_id,
                reconciliation[
                    "limitation_codes"
                ],
                reconciliation["notes"],
                Jsonb(
                    reconciliation.get(
                        "raw_metadata",
                        {},
                    )
                ),
            ),
        )

        cost_reconciliation_ids[arm_id] = (
            cursor.fetchone()[0]
        )

    for link in plan[
        "cost_reconciliation_source_links"
    ]:
        cursor.execute(
            """
            insert into benchmark.benchmark_cost_reconciliation_sources (
                reconciliation_id,
                source_id,
                evidence_role
            ) values (%s, %s, %s)
            """,
            (
                cost_reconciliation_ids[
                    link["arm_id"]
                ],
                source_ids[
                    link["source_key"]
                ],
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
            "transactional xAI evidence counts "
            "do not match reviewed plan"
        )

    requested_ids = list(
        arm_run_ids.values()
    )

    usage_plan = {
        row["arm_id"]: row
        for row in plan["usage_reconciliations"]
    }
    cost_plan = {
        row["arm_id"]: row
        for row in plan["cost_reconciliations"]
    }

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
            "transactional xAI usage "
            "reconciliations are incomplete"
        )

    verified_usage: dict[str, Any] = {}

    for row in usage_rows:
        arm_id = str(row[0])
        expected = usage_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected xAI usage reconciliation arm"
            )

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
                    f"{arm_id} usage reconciliation "
                    f"verification failed: {key}"
                )

        verified_usage[arm_id] = {
            "selected_usage_authority":
                row[21],
            "validation_status":
                row[22],
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
            "transactional xAI cost "
            "reconciliations are incomplete"
        )

    verified_cost: dict[str, Any] = {}

    for row in cost_rows:
        arm_id = str(row[0])
        expected = cost_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected xAI cost reconciliation arm"
            )

        numeric_fields = {
            "harness_reported_cost_usd":
                row[5],
            "provider_rate_reconstructed_cost_usd":
                row[7],
            "selected_cost_usd":
                row[8],
        }

        for key, value in numeric_fields.items():
            if Decimal(value) != Decimal(
                expected[key]
            ):
                raise IntegrationSafetyError(
                    f"{arm_id} cost reconciliation "
                    f"verification failed: {key}"
                )

        if row[6] is not None:
            raise IntegrationSafetyError(
                f"{arm_id} provider billed cost "
                "must remain NULL"
            )

        scalar_checks = {
            "reconciliation_version": row[1],
            "is_current": row[2],
            "harness_name": row[3],
            "harness_version": row[4],
            "selected_cost_basis": row[9],
            "selected_cost_relation": row[10],
            "validation_status": row[11],
            "provider_evidence_visible": row[12],
            "limitation_codes": list(row[13]),
        }

        for key, value in scalar_checks.items():
            if value != expected[key]:
                raise IntegrationSafetyError(
                    f"{arm_id} cost reconciliation "
                    f"verification failed: {key}"
                )

        backend_model = ARM_CONTRACT[
            arm_id
        ]["backend_model"]

        if (
            row[14] != "xai"
            or row[15] != backend_model
        ):
            raise IntegrationSafetyError(
                f"{arm_id} pricing snapshot linkage "
                "verification failed"
            )

        verified_cost[arm_id] = {
            "selected_cost_usd":
                str(row[8]),
            "selected_cost_basis":
                row[9],
            "selected_cost_relation":
                row[10],
            "validation_status":
                row[11],
        }

    return {
        "transaction_counts": counts,
        "usage_reconciliations":
            verified_usage,
        "cost_reconciliations":
            verified_cost,
    }


def verify_provider_evidence_details(
    cursor: Any,
    plan: Mapping[str, Any],
    arm_run_ids: Mapping[str, str],
) -> dict[str, str]:
    expected_sources = {
        row["source_key"]: row
        for row in plan["sources"]
    }

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
        where provider = 'xai'
        order by source_sha256
        """
    )

    source_rows = cursor.fetchall()

    if len(source_rows) != len(
        expected_sources
    ):
        raise IntegrationSafetyError(
            "xAI evidence source row count "
            "verification failed"
        )

    by_sha = {
        str(row[4]): row
        for row in source_rows
    }

    for expected in expected_sources.values():
        row = by_sha.get(
            expected["source_sha256"]
        )

        if row is None:
            raise IntegrationSafetyError(
                "reviewed xAI evidence source "
                "SHA-256 is missing"
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
                "xAI evidence source provenance "
                "verification failed"
            )

    pricing_plan = {
        row["provider_model"]: row
        for row in plan[
            "pricing_snapshots"
        ]
    }

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
        where pricing.provider = 'xai'
        order by pricing.provider_model
        """
    )

    pricing_rows = cursor.fetchall()

    if len(pricing_rows) != len(
        pricing_plan
    ):
        raise IntegrationSafetyError(
            "xAI pricing row count verification failed"
        )

    pricing_source_sha = expected_sources[
        "xai_reviewed_pricing_matrix"
    ]["source_sha256"]

    for row in pricing_rows:
        provider_model = str(row[2])
        expected = pricing_plan.get(
            provider_model
        )

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected xAI pricing model"
            )

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
            pricing_source_sha,
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
            raise IntegrationSafetyError(
                "xAI pricing snapshot "
                "verification failed"
            )

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = 'xai'
        """
    )

    if int(cursor.fetchone()[0]) != 0:
        raise IntegrationSafetyError(
            "xAI provider usage evidence "
            "must remain empty"
        )

    expected_cost_rows = plan[
        "provider_cost_evidence"
    ]

    if len(expected_cost_rows) != 2:
        raise IntegrationSafetyError(
            "reviewed xAI provider cost plan "
            "must contain exactly two dashboard rows"
        )

    expected_snapshot_sha = expected_sources[
        "xai_sanitized_provider_snapshot"
    ]["source_sha256"]

    cursor.execute(
        """
        select
            source.source_sha256,
            evidence.arm_run_id is null,
            evidence.trial_id is null,
            evidence.pricing_snapshot_id is null,
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
        where source.provider = 'xai'
        """
    )

    cost_rows = cursor.fetchall()

    if len(cost_rows) != 2:
        raise IntegrationSafetyError(
            "xAI provider cost row count "
            "verification failed"
        )

    expected_by_key = {
        (
            Decimal(row["amount_usd"]),
            row["raw_metadata"][
                "observation_date"
            ],
        ): row
        for row in expected_cost_rows
    }

    observed_keys: set[
        tuple[Decimal, str]
    ] = set()

    for row in cost_rows:
        metadata = row[11]

        if not isinstance(metadata, dict):
            raise IntegrationSafetyError(
                "xAI provider cost metadata "
                "verification failed"
            )

        key = (
            Decimal(row[6]),
            str(
                metadata.get(
                    "observation_date"
                )
            ),
        )

        expected = expected_by_key.get(key)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected xAI dashboard cost row"
            )

        observed_keys.add(key)

        expected_tuple = (
            expected_snapshot_sha,
            True,
            True,
            True,
            None,
            expected["cost_kind"],
            Decimal(
                expected["amount_usd"]
            ),
            expected["currency"],
            expected["allocation_scope"],
            expected["completeness_status"],
            expected["notes"],
            expected["raw_metadata"],
        )

        if tuple(row) != expected_tuple:
            raise IntegrationSafetyError(
                "xAI provider dashboard cost "
                "verification failed"
            )

    if observed_keys != set(
        expected_by_key
    ):
        raise IntegrationSafetyError(
            "xAI dashboard observations "
            "are incomplete"
        )

    requested_ids = list(
        arm_run_ids.values()
    )

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
        row["source_key"]:
            row["source_sha256"]
        for row in plan["sources"]
    }

    expected_links = {
        (
            "usage",
            link["arm_id"],
            source_sha_by_key[
                link["source_key"]
            ],
            link["evidence_role"],
        )
        for link in plan[
            "usage_reconciliation_source_links"
        ]
    } | {
        (
            "cost",
            link["arm_id"],
            source_sha_by_key[
                link["source_key"]
            ],
            link["evidence_role"],
        )
        for link in plan[
            "cost_reconciliation_source_links"
        ]
    }

    if actual_links != expected_links:
        raise IntegrationSafetyError(
            "xAI reconciliation source-link "
            "verification failed"
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
        diagnostics.enter(
            "target_state_preflight"
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "set transaction read only"
            )

            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = (
                state["state"]
            )

            if state["state"] == "xai_empty":
                diagnostics.enter(
                    "canonical_run_resolution"
                )

                resolved = resolve_arm_runs(
                    cursor,
                    plan,
                )

                result = {
                    "status": "ready",
                    "mode": "check-only",
                    "commit_state":
                        diagnostics.commit_state,
                    "target_state":
                        state["state"],
                    "counts": state["counts"],
                    "resolved_arm_run_ids":
                        resolved,
                    "checks": {
                        "reviewed_input_hashes": "pass",
                        "provider_scoped_target_empty":
                            "pass",
                        "canonical_run_resolution":
                            "pass",
                        "selected_run_token_geometry":
                            "pass",
                        "selected_run_rate_reconstruction":
                            "pass",
                        "read_only_transaction":
                            "pass",
                    },
                }

            elif (
                state["state"]
                == "exact_xai_state"
            ):
                result = {
                    "status": "already_applied",
                    "mode": "check-only",
                    "commit_state":
                        diagnostics.commit_state,
                    "target_state":
                        state["state"],
                    "counts":
                        state["counts"],
                    "resolved_arm_run_ids":
                        state[
                            "resolved_arm_run_ids"
                        ],
                    "checks": {
                        "reviewed_input_hashes":
                            "pass",
                        "exact_content_verification":
                            "pass",
                        "read_only_transaction":
                            "pass",
                    },
                }

            else:
                raise IntegrationSafetyError(
                    "xAI provider evidence target is "
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


def apply_permanent(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg

    connection: Any = None

    try:
        diagnostics.enter(
            "transaction_connection"
        )
        connection = psycopg.connect(
            db_url,
            autocommit=False,
        )

        with connection.cursor() as cursor:
            diagnostics.enter(
                "advisory_lock"
            )
            acquire_ingestion_lock(
                cursor
            )

            diagnostics.enter(
                "target_state_preflight"
            )
            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = (
                state["state"]
            )

            if (
                state["state"]
                == "exact_xai_state"
            ):
                raise IntegrationSafetyError(
                    "reviewed xAI provider evidence "
                    "is already applied"
                )

            if (
                state["state"]
                != "xai_empty"
            ):
                raise IntegrationSafetyError(
                    "xAI provider evidence target "
                    "is partially or unexpectedly populated"
                )

            diagnostics.enter(
                "canonical_run_resolution"
            )
            arm_run_ids = resolve_arm_runs(
                cursor,
                plan,
            )

            diagnostics.enter(
                "transactional_insert"
            )
            insert_plan(
                cursor,
                plan,
                arm_run_ids,
            )

            diagnostics.enter(
                "transactional_verification"
            )
            reconciliation_verification = (
                verify_inserted_state(
                    cursor,
                    plan,
                    arm_run_ids,
                )
            )
            provider_verification = (
                verify_provider_evidence_details(
                    cursor,
                    plan,
                    arm_run_ids,
                )
            )

        diagnostics.enter("commit")
        diagnostics.commit_state = "unknown"
        connection.commit()
        diagnostics.commit_state = "committed"

    except Exception:
        if (
            connection is not None
            and diagnostics.commit_state
            != "committed"
        ):
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter(
        "second_connection_verification"
    )

    observer = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with observer.cursor() as cursor:
            cursor.execute(
                "set transaction read only"
            )

            persisted_state = (
                inspect_target_state(
                    cursor,
                    plan,
                )
            )

        observer.rollback()

    finally:
        observer.close()

    diagnostics.target_state = (
        persisted_state["state"]
    )

    if (
        persisted_state["state"]
        != "exact_xai_state"
    ):
        raise IntegrationSafetyError(
            "committed xAI provider evidence "
            "failed second-connection verification"
        )

    return {
        "status": "applied",
        "mode": "apply",
        "commit_state":
            diagnostics.commit_state,
        "target_state":
            persisted_state["state"],
        "checks": {
            "reviewed_input_hashes": "pass",
            "advisory_lock": "pass",
            "provider_scoped_empty_preflight":
                "pass",
            "canonical_run_resolution": "pass",
            "transactional_insert": "pass",
            "transactional_verification": "pass",
            "commit": "pass",
            "second_connection_verification":
                "pass",
        },
        "resolved_arm_run_ids":
            arm_run_ids,
        "verification": {
            "reconciliations":
                reconciliation_verification,
            "provider_evidence":
                provider_verification,
        },
        "persisted_counts":
            persisted_state["counts"],
    }


def rollback_only(
    plan: Mapping[str, Any],
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    import psycopg

    connection: Any = None

    try:
        diagnostics.enter(
            "transaction_connection"
        )
        connection = psycopg.connect(
            db_url,
            autocommit=False,
        )

        with connection.cursor() as cursor:
            diagnostics.enter(
                "advisory_lock"
            )
            acquire_ingestion_lock(
                cursor
            )

            diagnostics.enter(
                "target_state_preflight"
            )
            state = inspect_target_state(
                cursor,
                plan,
            )
            diagnostics.target_state = (
                state["state"]
            )

            if (
                state["state"]
                != "xai_empty"
            ):
                raise IntegrationSafetyError(
                    "rollback-only xAI ingestion "
                    "requires an empty xAI target"
                )

            diagnostics.enter(
                "canonical_run_resolution"
            )
            arm_run_ids = resolve_arm_runs(
                cursor,
                plan,
            )

            diagnostics.enter(
                "transactional_insert"
            )
            insert_plan(
                cursor,
                plan,
                arm_run_ids,
            )

            diagnostics.enter(
                "transactional_verification"
            )
            inserted_state = (
                inspect_target_state(
                    cursor,
                    plan,
                )
            )

            if (
                inserted_state["state"]
                != "exact_xai_state"
            ):
                raise IntegrationSafetyError(
                    "transactional xAI insertion "
                    "did not match the reviewed exact state"
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

    diagnostics.enter(
        "second_connection_zero_persistence"
    )

    observer = psycopg.connect(
        db_url,
        autocommit=False,
    )

    try:
        with observer.cursor() as cursor:
            cursor.execute(
                "set transaction read only"
            )
            after = target_table_counts(
                cursor,
                plan,
            )
        observer.rollback()
    finally:
        observer.close()

    diagnostics.zero_persistence_counts.update(
        after
    )

    if any(after.values()):
        raise IntegrationSafetyError(
            "rollback-only xAI ingestion "
            "left persistent xAI state"
        )

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state":
            diagnostics.commit_state,
        "target_state": "xai_empty",
        "checks": {
            "reviewed_input_hashes": "pass",
            "advisory_lock": "pass",
            "provider_scoped_empty_preflight":
                "pass",
            "canonical_run_resolution": "pass",
            "transactional_insert": "pass",
            "transactional_verification": "pass",
            "rollback": "pass",
            "second_connection_zero_persistence":
                "pass",
        },
        "resolved_arm_run_ids":
            arm_run_ids,
        "verification": {
            "reconciliations":
                inserted_state[
                    "reconciliation_verification"
                ],
            "provider_evidence":
                inserted_state[
                    "provider_verification"
                ],
        },
        "zero_persistence_counts": after,
    }


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--plan",
        action="store_true",
        help=(
            "Emit the reviewed xAI evidence plan "
            "without opening a database connection."
        ),
    )

    group.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Read the real database using a read-only "
            "transaction and report whether the "
            "provider-scoped xAI target is empty "
            "and the selected canonical runs still "
            "match the reviewed contract."
        ),
    )

    group.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Insert and verify the reviewed xAI "
            "evidence inside one PostgreSQL transaction, "
            "roll it back, then prove zero persistence "
            "from a second connection."
        ),
    )

    group.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Permanently insert the reviewed xAI "
            "provider evidence only from an empty "
            "xAI target, verify it transactionally, "
            "commit once, and verify again from a "
            "second connection."
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
        "failed_stage":
            diagnostics.stage,
        "error_type":
            type(exc).__name__,
        "commit_state":
            diagnostics.commit_state,
        "zero_persistence_counts": dict(
            diagnostics.zero_persistence_counts
        ),
    }

    if diagnostics.target_state is not None:
        result["target_state"] = (
            diagnostics.target_state
        )

    sqlstate = getattr(
        exc,
        "sqlstate",
        None,
    )
    value = str(sqlstate or "")

    if len(value) == 5 and value.isalnum():
        result["sqlstate"] = (
            value.upper()
        )

    return result


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    diagnostics = Diagnostics()

    if args.plan:
        mode = "plan"
    elif args.check_only:
        mode = "check-only"
    elif args.rollback_only:
        mode = "rollback-only"
    else:
        mode = "apply"

    try:
        diagnostics.enter("plan")
        plan = build_plan()

        if args.plan:
            print(
                json.dumps(
                    plan,
                    sort_keys=True,
                )
            )
            return 0

        db_url = os.getenv(
            "SUPABASE_DB_URL"
        )

        if not db_url:
            raise MissingEnvironmentError()

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

    print(
        json.dumps(
            result,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
