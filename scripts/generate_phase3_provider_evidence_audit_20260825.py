#!/usr/bin/env python3
"""Generate the 2026-08-25 Phase 3 provider-evidence audit layer.

This generator is intentionally additive. It does not modify the frozen
2026-08-24 V3 current-cost reconciliation or its generated dashboard data.

Outputs:
- results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv
- results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv
- results/phase3/reporting/phase3_provider_run_chronology_20260825.csv
- docs/reports/phase3/PHASE3_PROVIDER_COST_EVIDENCE_AUDIT_20260825.md
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BASE_RECON = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260824.csv"
)
COVERAGE = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_trial_cost_coverage_20260712.tsv"
)
K3_RECOMPUTE = (
    ROOT
    / "results/phase3/reporting/"
      "kimi_k3_full_cost_recompute_20260722.tsv"
)

OUT_RECON = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)
OUT_MATRIX = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_provider_cost_evidence_matrix_20260825.csv"
)
OUT_CHRONOLOGY = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_provider_run_chronology_20260825.csv"
)
OUT_REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "PHASE3_PROVIDER_COST_EVIDENCE_AUDIT_20260825.md"
)

EXPECTED_BASE_SHA256 = (
    "7fc2ac41dfd56af4888cac0cc6d80be15f5d3b8edef12b915206fd57bc9afbea"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    text = str(value).strip()
    if not text or text == "NA":
        return Decimal("0")
    return Decimal(text)


def text(value: Decimal | str | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        if value == 0:
            return "0"
        rendered = format(value, "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered
    return str(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


if sha256(BASE_RECON) != EXPECTED_BASE_SHA256:
    raise ValueError(
        "Frozen 20260824 reconciliation SHA-256 changed; "
        "refusing to generate successor artifacts."
    )

base_rows = read_csv(BASE_RECON)
coverage_rows = read_tsv(COVERAGE)

if not base_rows:
    raise ValueError("20260824 base reconciliation is empty")

ARM_FIELDS = list(base_rows[0].keys())

EXPECTED_BASE_ARMS = {
    "router-anthropic-fable-5",
    "router-anthropic-haiku-sanitized",
    "router-anthropic-opus",
    "router-anthropic-sonnet",
    "router-deepseek-flash",
    "router-deepseek-pro",
    "router-gpt-5.4",
    "router-gpt-5.5",
}

if {row["arm_id"] for row in base_rows} != EXPECTED_BASE_ARMS:
    raise ValueError("Unexpected 20260824 base arm set")


RATE_SPECS = {
    # input_tokens includes the cached subset.
    "router-grok-build-0.1": (
        Decimal("1"),
        Decimal("0"),
        Decimal("2"),
    ),
    "router-glm-5.1": (
        Decimal("1.40"),
        Decimal("0.26"),
        Decimal("4.40"),
    ),
    "router-glm-5.2": (
        Decimal("1.40"),
        Decimal("0.26"),
        Decimal("4.40"),
    ),
    # Request-level trajectory audit proved all 930 Pro requests <=200K.
    "router-gemini-3.1-pro": (
        Decimal("2"),
        Decimal("0.20"),
        Decimal("12"),
    ),
    "router-gemini-flash": (
        Decimal("1.50"),
        Decimal("0.15"),
        Decimal("9"),
    ),
    # Request-level trajectory audit proved all selected Qwen requests
    # with retained usage <=256K.
    "router-qwen-3.7-plus": (
        Decimal("0.32"),
        Decimal("0.064"),
        Decimal("1.28"),
    ),
    "router-kimi-k2.6": (
        Decimal("0.95"),
        Decimal("0.16"),
        Decimal("4"),
    ),
}


META: dict[str, dict[str, Any]] = {
    "router-grok-build-0.1": {
        "run": "router-grok-build-0.1/2026-06-28__13-28-55",
        "backend": "grok-build-0.1",
        "provider_models": "grok-build-0.1",
        "provider": "xai",
        "expected_cost": Decimal("6.418694"),
        "relation": "lower_bound",
        "basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "confidence": "high_for_retained_accounting_lower_bound",
        "evidence_class": "verified_retained_trajectories_plus_official_provider_rates",
        "provider_context_billed": Decimal("6.36"),
        "provider_context_scope": "preselected_family_dashboard_total_through_2026-06-19",
        "provider_status": "preselected_provider_context_not_selected_run",
        "historical_recorded": Decimal("38.149845"),
        "historical_reviewed": Decimal("53.153814003353"),
        "trajectory_status": "60_trajectories_exactly_match_coverage;1_zero_metric_trial",
        "pricing_status": "official_xai_build_0.1_launch_rates",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "not_allocable_to_selected_run",
        "context_rate_reconstruction": None,
        "context_account_spend": Decimal("6.36"),
        "context_overhead": Decimal("0"),
        "note": (
            "Selected retained usage repriced at $1/M input and $2/M output. "
            "R2 trajectories exactly reproduce retained usage; the one "
            "polyglot-rust-c zero-token trial also has a zero-metric trajectory. "
            "The $6.36 provider dashboard snapshot predates the selected June 28 run."
        ),
    },
    "router-glm-5.1": {
        "run": "router-glm-5.1/2026-06-28__13-28-50",
        "backend": "glm-5.1",
        "provider_models": "glm-5.1",
        "provider": "zai-glm",
        "expected_cost": Decimal("5.3316552"),
        "relation": "estimate",
        "basis": "provider_rate_reconstructed_retained_usage_partial",
        "confidence": "medium",
        "evidence_class": "partial_retained_usage_plus_retained_published_rates_cache_accounting_unverified",
        "lower_bound_trial_count": 0,
        "trial_status": "partial_selected_usage_reconstruction_with_unresolved_trials",
        "outcome_status": "available_partial_estimate",
        "additional_status": "unresolved_trial_spend_and_cache_classification_uncertainty",
        "provider_context_billed": Decimal("3.094387"),
        "provider_context_scope": "preselected_glm5.1_provider_billing_table_through_2026-06-19",
        "provider_status": "preselected_provider_context_not_selected_run",
        "historical_recorded": Decimal("18.652610"),
        "historical_reviewed": Decimal("20.2970310"),
        "trajectory_status": "60_trajectories_exactly_match_coverage;5_zero_metric_trials",
        "pricing_status": "retained_published_rates_cache_accounting_unverified",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "not_allocable_to_selected_run",
        "context_rate_reconstruction": None,
        "context_account_spend": Decimal("3.094387"),
        "context_overhead": Decimal("0"),
        "note": (
            "55 trials retain usage. Five zero-token exception trials have "
            "zero-metric R2 trajectories, so no hidden usage is recoverable "
            "from durable artifacts. Selected-run cache classification remains "
            "unverified, so $5.3316552 is a partial rate estimate rather than "
            "a strict lower bound. The $3.094387 Z.AI billing table covers "
            "earlier glm-5.1 activity and predates the selected June 28 run."
        ),
    },
    "router-glm-5.2": {
        "run": "router-glm-5.2/2026-06-19__13-47-51",
        "backend": "glm-5.2",
        "provider_models": "glm-5.2",
        "provider": "zai-glm",
        "expected_cost": Decimal("8.9016736"),
        "relation": "estimate",
        "basis": "provider_rate_reconstructed_selected_run",
        "confidence": "high",
        "evidence_class": "complete_retained_usage_plus_retained_published_rates",
        "provider_context_billed": None,
        "provider_context_scope": "glm5.1_billing_evidence_is_same_family_but_different_model",
        "provider_status": "selected_run_provider_invoice_unavailable",
        "historical_recorded": Decimal("20.549075"),
        "historical_reviewed": Decimal("25.3166398"),
        "trajectory_status": "not_needed_all_60_selected_trials_have_retained_usage",
        "pricing_status": "retained_published_glm5.2_rates",
        "context_temporal_relation": "same_family_different_model_not_allocable",
        "context_allocation_confidence": "not_allocable",
        "context_rate_reconstruction": None,
        "context_account_spend": None,
        "context_overhead": Decimal("0"),
        "note": (
            "All 60 selected-run trials carry retained usage. The earlier "
            "Z.AI billing table is glm-5.1 evidence only and is not attributed "
            "to the glm-5.2 selected run."
        ),
    },
    "router-gemini-3.1-pro": {
        "run": "router-gemini-3.1-pro/2026-06-30__14-57-05",
        "backend": "gemini-3.1-pro-preview",
        "provider_models": "gemini-3.1-pro-preview",
        "provider": "google-gemini",
        "expected_cost": Decimal("19.6968138"),
        "relation": "estimate",
        "basis": "provider_rate_reconstructed_selected_run_request_tier",
        "confidence": "high",
        "evidence_class": "verified_retained_trajectories_plus_official_provider_rates",
        "provider_context_billed": Decimal("26.371228"),
        "provider_context_scope": "shared_preselected_gemini_family_billing_export_through_2026-06-17_nonadditive",
        "provider_status": "preselected_family_billing_context_not_selected_run",
        "historical_recorded": Decimal("38.1007875"),
        "historical_reviewed": Decimal("46.469402372844"),
        "trajectory_status": "60_trajectories;930_requests;exact_token_crosscheck;max_prompt_66438",
        "pricing_status": "official_google_rates_request_tier_verified",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "family_total_not_model_or_run_allocable",
        "context_rate_reconstruction": None,
        "context_account_spend": Decimal("26.371228"),
        "context_overhead": Decimal("0"),
        "note": (
            "R2 trajectories exactly reproduce 25,122,141 input, "
            "20,368,769 cached, and 509,693 output tokens. All 930 requests "
            "are <=200K prompt tokens; max request is 66,438. The June 17 "
            "Gemini-family billing total predates the June 30 selected run."
        ),
    },
    "router-gemini-flash": {
        "run": "router-gemini-flash/2026-06-27__01-30-20",
        "backend": "gemini-3.5-flash",
        "provider_models": "gemini-3.5-flash",
        "provider": "google-gemini",
        "expected_cost": Decimal("16.12091625"),
        "relation": "lower_bound",
        "basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "confidence": "high_for_retained_accounting_lower_bound",
        "evidence_class": "retained_artifacts_plus_official_provider_rates_trajectory_archive_unavailable",
        "provider_context_billed": Decimal("26.371228"),
        "provider_context_scope": "shared_preselected_gemini_family_billing_export_through_2026-06-17_nonadditive",
        "provider_status": "preselected_family_billing_context_not_selected_run",
        "historical_recorded": Decimal("23.6669395"),
        "historical_reviewed": Decimal("43.534953854955"),
        "trajectory_status": "selected_run_absent_from_r2_trajectory_archive",
        "pricing_status": "official_google_flash_rates",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "family_total_not_model_or_run_allocable",
        "context_rate_reconstruction": None,
        "context_account_spend": Decimal("26.371228"),
        "context_overhead": Decimal("0"),
        "note": (
            "56 trials retain usage and four have no token metadata. "
            "The selected run is absent from R2 even under a broad arm-prefix "
            "search, so trajectory recovery is unavailable. The June 17 "
            "Gemini-family billing export predates the selected June 27 run."
        ),
    },
    "router-qwen-3.7-plus": {
        "run": "router-qwen-3.7-plus/2026-06-29__03-16-06",
        "backend": "qwen3.7-plus",
        "provider_models": "qwen3.7-plus",
        "provider": "dashscope-qwen",
        "expected_cost": Decimal("2.50442432"),
        "relation": "lower_bound",
        "basis": "provider_rate_reconstructed_retained_usage_lower_bound",
        "confidence": "high_for_retained_accounting_lower_bound",
        "evidence_class": "verified_retained_trajectories_plus_provider_bill_validated_rates",
        "provider_context_billed": Decimal("1.310890"),
        "provider_context_scope": "preselected_qwen_payg_bill_detail_through_2026-06-19",
        "provider_status": "preselected_provider_context_not_selected_run",
        "historical_recorded": Decimal("20.430720"),
        "historical_reviewed": Decimal("34.944370078781"),
        "trajectory_status": "60_trajectories;59_usage_bearing;1_zero_metric_trial;all_requests_below_256k",
        "pricing_status": "historical_provider_bill_exactly_validates_discounted_singapore_rates",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "not_allocable_to_selected_run",
        "context_rate_reconstruction": None,
        "context_account_spend": Decimal("31.310890"),
        "context_overhead": Decimal("30.000000"),
        "note": (
            "The June 19 provider PAYG bill exactly validates $0.32/M ordinary "
            "input, $0.064/M cached input, and $1.28/M output for the configured "
            "Singapore endpoint. The selected run's largest aggregate-input "
            "trial decomposes into 86 requests; max request is 45,509, so all "
            "usage-bearing selected requests remain in the <=256K tier. "
            "Attempt 58 has a zero-metric trajectory and remains unresolved. "
            "The $30 Token Plan is account overhead, not marginal inference."
        ),
    },
    "router-kimi-k2.6": {
        "run": "router-kimi-k2.6/2026-06-28__13-28-55",
        "backend": "kimi-k2.6",
        "provider_models": "kimi-k2.6",
        "provider": "moonshot-kimi",
        "expected_cost": Decimal("6.34692415"),
        "relation": "estimate",
        "basis": "provider_rate_reconstructed_selected_run",
        "confidence": "high",
        "evidence_class": "complete_retained_usage_plus_provider_dashboard_validated_rates",
        "provider_context_billed": Decimal("1.91830"),
        "provider_context_scope": "preselected_request_logs_and_dashboard_total_2026-06-04_to_2026-06-16",
        "provider_status": "preselected_provider_context_not_selected_run",
        "historical_recorded": Decimal("25.985730"),
        "historical_reviewed": Decimal("35.131541559739"),
        "trajectory_status": "not_needed_all_60_selected_trials_have_retained_usage",
        "pricing_status": "historical_request_log_plus_dashboard_validates_rate_formula",
        "context_temporal_relation": "predates_selected_run",
        "context_allocation_confidence": "historical_usage_only_not_selected_run",
        "context_rate_reconstruction": Decimal("1.918399"),
        "context_account_spend": Decimal("1.91830"),
        "context_overhead": Decimal("0"),
        "note": (
            "All 60 selected-run trials carry retained usage. Historical "
            "Moonshot request logs reproduce $1.918399 from the retained rates "
            "and the provider dashboard reports $1.91830, independently "
            "validating token semantics and the rate formula before the "
            "selected June 28 run."
        ),
    },
}


def rows_for(arm: str, run_label: str) -> list[dict[str, str]]:
    return [
        row
        for row in coverage_rows
        if row.get("arm_id") == arm
        and row.get("run_label") == run_label
    ]


def rate_cost(
    arm: str,
    input_tokens: Decimal,
    cache_tokens: Decimal,
    output_tokens: Decimal,
) -> Decimal:
    input_rate, cache_rate, output_rate = RATE_SPECS[arm]

    if cache_tokens > input_tokens:
        raise ValueError(f"{arm}: cache exceeds input")

    ordinary_input = input_tokens - cache_tokens

    return (
        ordinary_input * input_rate / Decimal(1_000_000)
        + cache_tokens * cache_rate / Decimal(1_000_000)
        + output_tokens * output_rate / Decimal(1_000_000)
    )


new_rows: list[dict[str, str]] = []
audit_details: dict[str, dict[str, Any]] = {}

for arm, meta in META.items():
    rows = rows_for(arm, meta["run"])

    if len(rows) != 60:
        raise ValueError(f"{arm}: expected 60 selected-run rows, got {len(rows)}")

    input_total = sum((dec(row.get("input_tokens")) for row in rows), Decimal("0"))
    cache_total = sum((dec(row.get("cache_tokens")) for row in rows), Decimal("0"))
    output_total = sum((dec(row.get("output_tokens")) for row in rows), Decimal("0"))

    zero_rows = [
        row
        for row in rows
        if (
            dec(row.get("input_tokens")) == 0
            and dec(row.get("cache_tokens")) == 0
            and dec(row.get("output_tokens")) == 0
        )
    ]

    bucket_costs: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for row in rows:
        bucket = row.get("outcome_bucket") or ""
        bucket_costs[bucket] += rate_cost(
            arm,
            dec(row.get("input_tokens")),
            dec(row.get("cache_tokens")),
            dec(row.get("output_tokens")),
        )

    selected_cost = sum(bucket_costs.values(), Decimal("0"))

    if selected_cost != meta["expected_cost"]:
        raise ValueError(
            f"{arm}: audited cost mismatch: "
            f"{selected_cost} != {meta['expected_cost']}"
        )

    complete = 60 - len(zero_rows)
    lower_bound_count = int(
        meta.get(
            "lower_bound_trial_count",
            len(zero_rows)
            if meta["relation"] == "lower_bound"
            else 0,
        )
    )

    trial_status = str(
        meta.get(
            "trial_status",
            (
                "available_with_unresolved_usage_lower_bounds"
                if meta["relation"] == "lower_bound"
                else "available_provider_rate_reconstruction"
            ),
        )
    )

    outcome_status = str(
        meta.get(
            "outcome_status",
            (
                "available_lower_bound"
                if meta["relation"] == "lower_bound"
                else "available_provider_rate_reconstruction"
            ),
        )
    )

    additional = str(
        meta.get(
            "additional_status",
            (
                "possible_additional_unresolved_trial_spend"
                if meta["relation"] == "lower_bound"
                else "none"
            ),
        )
    )

    new_rows.append({
        "arm_id": arm,
        "selected_run_label": meta["run"],
        "routing_aliases": arm,
        "backend_model": meta["backend"],
        "provider_models": meta["provider_models"],
        "provider": meta["provider"],
        "selected_cost_usd": text(selected_cost),
        "selected_cost_relation": meta["relation"],
        "selected_cost_basis": meta["basis"],
        "selected_cost_confidence": meta["confidence"],
        "evidence_class": meta["evidence_class"],
        "provider_billed_cost_usd": "",
        "provider_context_billed_cost_usd": text(meta["provider_context_billed"]),
        "provider_context_scope": meta["provider_context_scope"],
        "provider_context_excess_usd": "",
        "provider_billing_reconciliation_status": meta["provider_status"],
        "trial_count": "60",
        "complete_trial_cost_count": str(complete),
        "lower_bound_trial_count": str(lower_bound_count),
        "confirmed_zero_cost_trial_count": "0",
        "trial_cost_allocation_status": trial_status,
        "outcome_cost_allocation_status": outcome_status,
        "clean_success_cost_usd": text(bucket_costs["clean_success"]),
        "normal_failure_cost_usd": text(bucket_costs["normal_failure"]),
        "exception_failure_cost_usd": text(bucket_costs["exception_failure"]),
        "exception_with_success_signal_cost_usd": text(
            bucket_costs["exception_with_success_signal"]
        ),
        "known_allocated_cost_usd": text(selected_cost),
        "unallocated_known_cost_usd": "0",
        "unquantified_additional_cost_status": additional,
        "historical_harness_recorded_cost_usd": text(meta["historical_recorded"]),
        "historical_reviewed_cost_usd": text(meta["historical_reviewed"]),
        "evidence_note": meta["note"],
    })

    audit_details[arm] = {
        **meta,
        "input_tokens": input_total,
        "cache_tokens": cache_total,
        "output_tokens": output_total,
        "complete_trials": complete,
        "unresolved_trials": len(zero_rows),
        "selected_cost": selected_cost,
    }


# Kimi K3 is the extended-corpus arm and postdates the July 12 coverage layer.
k3_rows = [
    row
    for row in read_tsv(K3_RECOMPUTE)
    if row.get("record_type") == "trial_result"
]

if len(k3_rows) != 60:
    raise ValueError(f"Kimi K3: expected 60 trial rows, got {len(k3_rows)}")

k3_input = sum((dec(row["n_input_tokens"]) for row in k3_rows), Decimal("0"))
k3_cache = sum((dec(row["n_cache_tokens"]) for row in k3_rows), Decimal("0"))
k3_output = sum((dec(row["n_output_tokens"]) for row in k3_rows), Decimal("0"))
k3_selected = sum(
    (dec(row["official_k3_if_input_includes_cache_usd"]) for row in k3_rows),
    Decimal("0"),
)
k3_observed = sum(
    (
        dec(row["observed_cost_usd"])
        for row in k3_rows
        if row.get("observed_cost_usd") not in {"", "NA", None}
    ),
    Decimal("0"),
)

if k3_selected != Decimal("26.570403000000"):
    raise ValueError(f"Unexpected Kimi K3 selected reconstruction: {k3_selected}")

if k3_observed != Decimal("25.207213000000"):
    raise ValueError(f"Unexpected Kimi K3 observed cost: {k3_observed}")

k3_provider_context_rate = Decimal("30.8143194")
k3_context_excess = k3_provider_context_rate - k3_selected

new_rows.append({
    "arm_id": "router-kimi-k3",
    "selected_run_label": "router-kimi-k3/2026-07-22__17-51-05",
    "routing_aliases": "router-kimi-k3",
    "backend_model": "kimi-k3",
    "provider_models": "kimi-k3",
    "provider": "moonshot-kimi",
    "selected_cost_usd": text(k3_selected),
    "selected_cost_relation": "estimate",
    "selected_cost_basis": "provider_rate_reconstructed_selected_run",
    "selected_cost_confidence": "medium_qualified_pricing_provenance",
    "evidence_class": "complete_retained_usage_plus_retained_rate_constants_qualified_provenance",
    "provider_billed_cost_usd": "",
    # The $30.8143194 provider-log number is not billed-dollar evidence.
    "provider_context_billed_cost_usd": "",
    "provider_context_scope": "broader_provider_request_log_retained_rate_reconstruction",
    "provider_context_excess_usd": "",
    "provider_billing_reconciliation_status": "provider_log_not_invoice_level_allocation_low_confidence",
    "trial_count": "60",
    "complete_trial_cost_count": "60",
    "lower_bound_trial_count": "0",
    "confirmed_zero_cost_trial_count": "0",
    "trial_cost_allocation_status": "available_provider_rate_reconstruction",
    "outcome_cost_allocation_status": "unavailable_no_reviewed_outcome_join",
    "clean_success_cost_usd": "",
    "normal_failure_cost_usd": "",
    "exception_failure_cost_usd": "",
    "exception_with_success_signal_cost_usd": "",
    "known_allocated_cost_usd": text(k3_selected),
    "unallocated_known_cost_usd": "0",
    "unquantified_additional_cost_status": "none_for_selected_retained_usage",
    "historical_harness_recorded_cost_usd": text(k3_observed),
    "historical_reviewed_cost_usd": text(k3_provider_context_rate),
    "evidence_note": (
        "All 60 selected-run trials carry token usage and reprice to "
        "$26.570403 under the retained K3 rate constants. The broader "
        "1,273-request provider log reconstructs to $30.8143194 but has no "
        "request-to-run join and no charged-dollar field. Its excess over "
        "selected retained usage is $4.2439164. Official dated pricing-source "
        "provenance remains incomplete."
    ),
})

audit_details["router-kimi-k3"] = {
    "run": "router-kimi-k3/2026-07-22__17-51-05",
    "backend": "kimi-k3",
    "provider": "moonshot-kimi",
    "selected_cost": k3_selected,
    "relation": "estimate",
    "basis": "provider_rate_reconstructed_selected_run",
    "confidence": "medium_qualified_pricing_provenance",
    "evidence_class": "complete_retained_usage_plus_retained_rate_constants_qualified_provenance",
    "provider_context_billed": None,
    "provider_context_scope": "broader_provider_request_log_retained_rate_reconstruction",
    "provider_status": "provider_log_not_invoice_level_allocation_low_confidence",
    "historical_recorded": k3_observed,
    "historical_reviewed": k3_provider_context_rate,
    "trajectory_status": "not_required_selected_trial_token_rows_complete",
    "pricing_status": "retained_2026-07-22_rate_constants_official_snapshot_missing",
    "context_temporal_relation": "provider_window_overlaps_same_day_but_timezone_unproven",
    "context_allocation_confidence": "low",
    "context_rate_reconstruction": k3_provider_context_rate,
    "context_account_spend": None,
    "context_overhead": Decimal("0"),
    "input_tokens": k3_input,
    "cache_tokens": k3_cache,
    "output_tokens": k3_output,
    "complete_trials": 60,
    "unresolved_trials": 0,
    "context_excess": k3_context_excess,
    "note": new_rows[-1]["evidence_note"],
}


all_rows = base_rows + new_rows

if len(all_rows) != 16:
    raise ValueError(f"Expected 16 reconciliation rows, got {len(all_rows)}")

if len({row["arm_id"] for row in all_rows}) != 16:
    raise ValueError("Duplicate arm in successor reconciliation")


OUT_RECON.parent.mkdir(parents=True, exist_ok=True)

with OUT_RECON.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=ARM_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(all_rows)


MATRIX_FIELDS = [
    "arm_id",
    "provider",
    "selected_run_label",
    "selected_cost_usd",
    "selected_cost_relation",
    "selected_cost_basis",
    "selected_cost_confidence",
    "evidence_class",
    "trial_count",
    "complete_trial_cost_count",
    "unresolved_trial_count",
    "selected_input_tokens",
    "selected_cache_tokens",
    "selected_output_tokens",
    "trajectory_evidence_status",
    "pricing_provenance_status",
    "provider_context_billed_cost_usd",
    "provider_context_rate_reconstruction_usd",
    "provider_context_rate_reconstruction_excess_vs_selected_usd",
    "provider_context_account_spend_usd",
    "provider_context_overhead_usd",
    "provider_context_scope",
    "provider_context_temporal_relation",
    "provider_context_allocation_confidence",
    "historical_harness_recorded_cost_usd",
    "historical_reviewed_cost_usd",
    "audit_scope",
    "audit_conclusion",
]

matrix_rows: list[dict[str, str]] = []

for row in base_rows:
    matrix_rows.append({
        "arm_id": row["arm_id"],
        "provider": row["provider"],
        "selected_run_label": row["selected_run_label"],
        "selected_cost_usd": row["selected_cost_usd"],
        "selected_cost_relation": row["selected_cost_relation"],
        "selected_cost_basis": row["selected_cost_basis"],
        "selected_cost_confidence": row["selected_cost_confidence"],
        "evidence_class": row["evidence_class"],
        "trial_count": row["trial_count"],
        "complete_trial_cost_count": row["complete_trial_cost_count"],
        "unresolved_trial_count": row["lower_bound_trial_count"],
        "selected_input_tokens": "",
        "selected_cache_tokens": "",
        "selected_output_tokens": "",
        "trajectory_evidence_status": "not_reaudited_in_20260825_provider_pass",
        "pricing_provenance_status": "inherited_from_20260824_reconciliation",
        "provider_context_billed_cost_usd": row["provider_context_billed_cost_usd"],
        "provider_context_rate_reconstruction_usd": "",
        "provider_context_rate_reconstruction_excess_vs_selected_usd": "",
        "provider_context_account_spend_usd": "",
        "provider_context_overhead_usd": "",
        "provider_context_scope": row["provider_context_scope"],
        "provider_context_temporal_relation": "inherited_from_20260824",
        "provider_context_allocation_confidence": "inherited_from_20260824",
        "historical_harness_recorded_cost_usd":
            row["historical_harness_recorded_cost_usd"],
        "historical_reviewed_cost_usd": row["historical_reviewed_cost_usd"],
        "audit_scope": "inherited_20260824_current_reconciliation",
        "audit_conclusion": row["evidence_note"],
    })

for arm, detail in audit_details.items():
    matrix_rows.append({
        "arm_id": arm,
        "provider": detail["provider"],
        "selected_run_label": detail["run"],
        "selected_cost_usd": text(detail["selected_cost"]),
        "selected_cost_relation": detail["relation"],
        "selected_cost_basis": detail["basis"],
        "selected_cost_confidence": detail["confidence"],
        "evidence_class": detail["evidence_class"],
        "trial_count": "60",
        "complete_trial_cost_count": str(detail["complete_trials"]),
        "unresolved_trial_count": str(detail["unresolved_trials"]),
        "selected_input_tokens": text(detail["input_tokens"]),
        "selected_cache_tokens": text(detail["cache_tokens"]),
        "selected_output_tokens": text(detail["output_tokens"]),
        "trajectory_evidence_status": detail["trajectory_status"],
        "pricing_provenance_status": detail["pricing_status"],
        "provider_context_billed_cost_usd": text(detail["provider_context_billed"]),
        "provider_context_rate_reconstruction_usd":
            text(detail.get("context_rate_reconstruction")),
        "provider_context_rate_reconstruction_excess_vs_selected_usd":
            text(detail.get("context_excess")),
        "provider_context_account_spend_usd":
            text(detail.get("context_account_spend")),
        "provider_context_overhead_usd":
            text(detail.get("context_overhead")),
        "provider_context_scope": detail["provider_context_scope"],
        "provider_context_temporal_relation": detail["context_temporal_relation"],
        "provider_context_allocation_confidence":
            detail["context_allocation_confidence"],
        "historical_harness_recorded_cost_usd":
            text(detail["historical_recorded"]),
        "historical_reviewed_cost_usd":
            text(detail["historical_reviewed"]),
        "audit_scope": "provider_evidence_audit_20260825",
        "audit_conclusion": detail["note"],
    })

with OUT_MATRIX.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=MATRIX_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(matrix_rows)


CHRONOLOGY_FIELDS = [
    "provider",
    "arm_id",
    "start_date",
    "end_date",
    "event_type",
    "run_label_or_scope",
    "amount_usd",
    "amount_kind",
    "relation_to_selected_run",
    "allocation_confidence",
    "notes",
]

chronology = [
    # Grok
    ("xai", "router-grok-build-0.1", "2026-06-04", "2026-06-04",
     "canary", "router-grok-build-0.1/2026-06-04__03-06-37",
     "", "", "preselected_run", "artifact_level", ""),
    ("xai", "router-grok-build-0.1", "2026-06-16", "2026-06-16",
     "smoke", "router-grok-build-0.1/2026-06-16__14-53-30",
     "", "", "preselected_run", "artifact_level", ""),
    ("xai", "router-grok-build-0.1", "", "2026-06-19",
     "provider_dashboard_snapshot", "xAI family dashboard total",
     "6.36", "provider_dashboard_total",
     "predates_selected_run", "not_run_allocable",
     "5,927,385 canonical retained dashboard tokens; user separately observed 5,927,462."),
    ("xai", "router-grok-build-0.1", "2026-06-28", "2026-06-28",
     "selected_full", "router-grok-build-0.1/2026-06-28__13-28-55",
     "6.418694", "selected_retained_usage_lower_bound",
     "selected_run", "59_of_60_usage_bearing",
     "One polyglot-rust-c trial remains unresolved."),

    # GLM
    ("zai-glm", "router-glm-5.1", "2026-06-04", "2026-06-04",
     "canary", "router-glm-5.1/2026-06-04__12-40-42",
     "", "", "preselected_run", "artifact_level", ""),
    ("zai-glm", "router-glm-5.1", "2026-06-16", "2026-06-16",
     "smoke", "router-glm-5.1/2026-06-16__14-53-29",
     "", "", "preselected_run", "artifact_level", ""),
    ("zai-glm", "router-glm-5.1", "", "2026-06-19",
     "provider_billing_table", "glm-5.1 historical provider usage",
     "3.094387", "provider_billed",
     "predates_selected_run", "exact_for_historical_scope_not_selected_run", ""),
    ("zai-glm", "router-glm-5.2", "", "2026-06-19",
     "same_family_provider_context", "glm-5.1 billing evidence only",
     "", "", "different_model_not_allocable", "not_allocable", ""),
    ("zai-glm", "router-glm-5.2", "2026-06-19", "2026-06-19",
     "selected_full", "router-glm-5.2/2026-06-19__13-47-51",
     "8.9016736", "selected_rate_reconstruction",
     "selected_run", "60_of_60_usage_bearing", ""),
    ("zai-glm", "router-glm-5.1", "2026-06-28", "2026-06-28",
     "selected_full", "router-glm-5.1/2026-06-28__13-28-50",
     "5.3316552", "selected_partial_rate_estimate",
     "selected_run",
     "55_of_60_usage_bearing_cache_accounting_unverified",
     "Five zero-metric trajectory trials remain unresolved; selected-run "
     "cache classification is unverified, so this is not a strict lower bound."),

    # Gemini
    ("google-gemini", "router-gemini-3.1-pro", "2026-06-02", "2026-06-02",
     "canary", "router-gemini-3.1-pro/2026-06-02__21-10-28",
     "", "", "preselected_run", "artifact_level",
     "Errored canary with zero aggregate usage."),
    ("google-gemini", "router-gemini-3.1-pro", "2026-06-02", "2026-06-02",
     "canary", "router-gemini-3.1-pro/2026-06-02__22-17-25",
     "", "", "preselected_run", "artifact_level",
     "Successful retained canary; session-side activity crosses into UTC June 3."),
    ("google-gemini", "router-gemini-flash", "2026-06-02", "2026-06-02",
     "canary", "router-gemini-flash/2026-06-02__17-59-33",
     "", "", "preselected_run", "artifact_level",
     "Successful retained canary."),
    ("google-gemini", "router-gemini-flash", "2026-06-02", "2026-06-02",
     "canary", "router-gemini-flash/2026-06-02__20-30-15",
     "", "", "preselected_run", "artifact_level",
     "Errored retained canary with nonzero usage."),
    ("google-gemini", "router-gemini-flash", "2026-06-02", "2026-06-02",
     "canary", "router-gemini-flash/2026-06-02__20-59-54",
     "", "", "preselected_run", "artifact_level",
     "Successful retained canary."),
    ("google-gemini", "router-gemini-3.1-pro", "2026-06-16", "2026-06-16",
     "smoke", "router-gemini-3.1-pro/2026-06-16__19-04-01",
     "", "", "preselected_run", "artifact_level",
     "Five-trial retained smoke."),
    ("google-gemini", "router-gemini-flash", "2026-06-16", "2026-06-16",
     "smoke", "router-gemini-flash/2026-06-16__00-58-08",
     "", "", "preselected_run", "artifact_level",
     "Five-trial retained smoke."),
    ("google-gemini", "router-gemini-flash", "2026-06-16", "2026-06-16",
     "smoke", "router-gemini-flash/2026-06-16__19-04-09",
     "", "", "preselected_run", "artifact_level",
     "Second five-trial retained smoke."),
    ("google-gemini", "router-gemini-3.1-pro;router-gemini-flash", "", "2026-06-17",
     "provider_billing_export", "shared Gemini API service-level billing",
     "26.371228", "provider_billed_family_total",
     "predates_both_selected_runs", "not_model_or_run_allocable",
     "Shared family context; amount must not be summed once per arm."),
    ("google-gemini", "router-gemini-flash", "2026-06-27", "2026-06-27",
     "selected_full", "router-gemini-flash/2026-06-27__01-30-20",
     "16.12091625", "selected_retained_usage_lower_bound",
     "selected_run", "56_of_60_usage_bearing",
     "Selected run absent from R2 trajectory archive."),
    ("google-gemini", "router-gemini-3.1-pro", "2026-06-30", "2026-06-30",
     "selected_full", "router-gemini-3.1-pro/2026-06-30__14-57-05",
     "19.6968138", "selected_request_tier_rate_reconstruction",
     "selected_run", "60_of_60_and_930_request_tiers_verified",
     "All 930 requests <=200K; max prompt 66,438."),

    # Qwen
    ("dashscope-qwen", "router-qwen-3.7-plus", "2026-06-04", "2026-06-04",
     "canary", "router-qwen-3.7-plus/2026-06-04__02-32-42",
     "", "", "preselected_run", "artifact_level", ""),
    ("dashscope-qwen", "router-qwen-3.7-plus", "2026-06-15", "2026-06-15",
     "smoke", "router-qwen-3.7-plus/2026-06-15__22-23-20",
     "", "", "preselected_run", "artifact_level", ""),
    ("dashscope-qwen", "router-qwen-3.7-plus", "", "2026-06-19",
     "provider_bill_detail", "historical Qwen PAYG inference",
     "1.310890", "provider_billed_payg",
     "predates_selected_run", "historical_scope_only",
     "$30 Token Plan overhead tracked separately."),
    ("dashscope-qwen", "router-qwen-3.7-plus", "2026-06-29", "2026-06-29",
     "selected_full", "router-qwen-3.7-plus/2026-06-29__03-16-06",
     "2.50442432", "selected_retained_usage_lower_bound",
     "selected_run", "59_of_60_usage_bearing",
     "All retained requests <=256K; one zero-metric trial unresolved."),

    # Kimi K2.6
    ("moonshot-kimi", "router-kimi-k2.6", "2026-06-04", "2026-06-04",
     "canary", "router-kimi-k2.6/2026-06-04__03-08-21",
     "", "", "preselected_run", "artifact_level", ""),
    ("moonshot-kimi", "router-kimi-k2.6", "2026-06-16", "2026-06-16",
     "smoke", "router-kimi-k2.6/2026-06-16__04-43-33",
     "", "", "preselected_run", "artifact_level", ""),
    ("moonshot-kimi", "router-kimi-k2.6", "2026-06-04", "2026-06-16",
     "provider_request_logs_and_dashboard", "103 requests / historical usage",
     "1.91830", "provider_dashboard_total",
     "predates_selected_run", "historical_scope_only",
     "Pricing-derived request-log estimate $1.918399."),
    ("moonshot-kimi", "router-kimi-k2.6", "2026-06-28", "2026-06-28",
     "selected_full", "router-kimi-k2.6/2026-06-28__13-28-55",
     "6.34692415", "selected_rate_reconstruction",
     "selected_run", "60_of_60_usage_bearing", ""),

    # Kimi K3
    ("moonshot-kimi", "router-kimi-k3", "2026-07-22", "2026-07-22",
     "canary", "router-kimi-k3/2026-07-22__14-54-02",
     "", "", "preselected_run", "artifact_level", "Earlier canary."),
    ("moonshot-kimi", "router-kimi-k3", "2026-07-22", "2026-07-22",
     "canary", "router-kimi-k3/2026-07-22__15-08-32",
     "", "", "preselected_run", "artifact_level", "Successful retained canary."),
    ("moonshot-kimi", "router-kimi-k3", "2026-07-22", "2026-07-22",
     "smoke", "router-kimi-k3/2026-07-22__15-25-50",
     "", "", "preselected_run", "artifact_level", ""),
    ("moonshot-kimi", "router-kimi-k3", "2026-07-22", "2026-07-22",
     "selected_full", "router-kimi-k3/2026-07-22__17-51-05",
     "26.570403", "selected_rate_reconstruction",
     "selected_run", "60_of_60_usage_bearing",
     "Retained rate constants; official dated pricing snapshot unavailable."),
    ("moonshot-kimi", "router-kimi-k3", "2026-07-22", "2026-07-23",
     "provider_request_log", "1,273-request kimi-k3 export",
     "30.8143194", "provider_log_rate_reconstruction_not_billed",
     "overlaps_same_day_but_timezone_unproven", "low",
     "No request-to-run join; excess over selected retained usage is $4.2439164."),
]

with OUT_CHRONOLOGY.open("w", newline="") as handle:
    writer = csv.writer(
        handle,
        lineterminator="\n",
    )
    writer.writerow(CHRONOLOGY_FIELDS)
    writer.writerows(chronology)


audited_order = [
    "router-grok-build-0.1",
    "router-glm-5.1",
    "router-glm-5.2",
    "router-gemini-3.1-pro",
    "router-gemini-flash",
    "router-qwen-3.7-plus",
    "router-kimi-k2.6",
    "router-kimi-k3",
]

report_lines = [
    "# Phase 3 Provider Cost Evidence Audit — 2026-08-25",
    "",
    "## Purpose",
    "",
    "This audit extends the frozen 2026-08-24 current-cost reconciliation "
    "without modifying that snapshot. It resolves the remaining Phase 3 "
    "provider/model arms using selected-run retained usage, provider-side "
    "historical evidence, official or retained price evidence, and where "
    "available durable R2 trajectories.",
    "",
    "Two rules govern the successor layer:",
    "",
    "1. A provider snapshot that predates a selected run cannot reconcile or "
    "confirm that selected run's billed cost.",
    "2. Provider-family/window aggregates remain context when they cannot be "
    "cleanly allocated to the selected run; selected-run token reconstructions "
    "are reported separately.",
    "",
    "## Newly audited selected-run costs",
    "",
    "| Arm | Selected cost | Relation | Complete trials | Unresolved | Basis |",
    "|---|---:|---|---:|---:|---|",
]

for arm in audited_order:
    d = audit_details[arm]
    report_lines.append(
        f"| `{arm}` | `${text(d['selected_cost'])}` | "
        f"`{d['relation']}` | {d['complete_trials']}/60 | "
        f"{d['unresolved_trials']} | `{d['basis']}` |"
    )

report_lines += [
    "",
    "## Key findings",
    "",
    "- **Grok Build 0.1:** R2 trajectories exactly match retained coverage. "
    "One zero-token `polyglot-rust-c` trial also has zero trajectory metrics. "
    "`$6.418694` is therefore a retained-usage lower bound, not provider-billed "
    "selected-run cost.",
    "- **GLM 5.1:** all five zero-token trials also have zero-metric R2 "
    "trajectories. Selected-run cache classification remains unverified, so "
    "`$5.3316552` is a partial rate estimate with five unresolved trials, "
    "not a strict lower bound.",
    "- **GLM 5.2:** all 60 trials retain usage. `$8.9016736` is a complete "
    "selected-run rate reconstruction; the historical Z.AI bill is GLM 5.1 "
    "evidence and is not attributed to GLM 5.2.",
    "- **Gemini 3.1 Pro:** 60 trajectories / 930 model responses exactly "
    "reproduce selected-run token totals. Every request is below Google's "
    "200K tier boundary (max prompt 66,438), resolving the selected-run "
    "reconstruction to `$19.6968138`.",
    "- **Gemini 3.5 Flash:** 56 trials retain usage and four do not. The "
    "selected run is absent from R2 even under a broad arm-prefix search, "
    "so trajectory recovery is unavailable. `$16.12091625` remains a lower bound.",
    "- **Qwen 3.7 Plus:** historical Alibaba PAYG billing exactly validates "
    "the discounted Singapore token rates. Request-level trajectory evidence "
    "proves all retained selected-run requests are below 256K. One zero-metric "
    "trial remains unresolved, producing a `$2.50442432` lower bound.",
    "- **Kimi K2.6:** historical Moonshot request logs and the dashboard total "
    "independently validate the token semantics/rate formula. All 60 selected "
    "trials retain usage; selected reconstruction is `$6.34692415`.",
    "- **Kimi K3:** all 60 selected trials retain usage and reconstruct to "
    "`$26.570403`. The broader provider request log reconstructs to "
    "`$30.8143194`, but request-to-run allocation is low-confidence and "
    "official dated pricing-source provenance remains incomplete.",
    "",
    "## Provider context chronology",
    "",
    "See `results/phase3/reporting/"
    "phase3_provider_run_chronology_20260825.csv` for the dated evidence/run "
    "sequence. In particular, the historical xAI, GLM 5.1, Gemini, Qwen, and "
    "Kimi K2.6 provider-side totals precede their selected full sweeps and are "
    "therefore context/calibration evidence rather than selected-run billing.",
    "",
    "## Immutable prior layer",
    "",
    "The following 2026-08-24 artifacts remain frozen and are not modified:",
    "",
    "- `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260824.csv`",
    "- `results/phase3/reporting/phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv`",
    "- `results/phase3/reporting/phase3_current_reviewed_comparison_20260824.json`",
    "- the generated V3 dashboard source.",
    "",
    "The new `phase3_current_arm_cost_reconciliation_20260825.csv` is an "
    "additive successor evidence layer. Dashboard/current-comparison promotion "
    "should occur only after this new layer is reviewed and validated.",
    "",
]

OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text(
    "\n".join(report_lines).rstrip() + "\n",
    encoding="utf-8",
)


print("generated:")
for path in (
    OUT_RECON,
    OUT_MATRIX,
    OUT_CHRONOLOGY,
    OUT_REPORT,
):
    print(" ", path.relative_to(ROOT))

print()
print("successor reconciliation rows:", len(all_rows))
print("provider evidence matrix rows:", len(matrix_rows))
print("chronology rows:", len(chronology))
print("newly audited arms:", len(audited_order))

print()
print("newly audited selected costs:")
for arm in audited_order:
    d = audit_details[arm]
    print(
        f"  {arm}: "
        f"{text(d['selected_cost'])} "
        f"({d['relation']}, "
        f"{d['complete_trials']}/60 complete, "
        f"{d['unresolved_trials']} unresolved)"
    )
