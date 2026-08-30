#!/usr/bin/env python3
"""Plan, verify, or apply Gemini Phase 3 provider-evidence ingestion."""

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

PROVIDER_RECONCILIATION = (
    ROOT
    / "results/phase3/supplemental/"
      "gemini_family_reconciliation_2026-06-17.json"
)

PROVIDER_REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "GEMINI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md"
)

PRICING_CODE = (
    ROOT
    / "scripts/"
      "generate_phase3_provider_evidence_audit_20260825.py"
)

PROVIDER_AUDIT_REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "PHASE3_PROVIDER_COST_EVIDENCE_AUDIT_20260825.md"
)

CURRENT_RECONCILIATION = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)

REVIEWED_PLAN_SHA256 = (
    "10fae2e8984b8cec14a0a22d04f95e3020acc7894f43f86d530033c9649de9d5"
)

EXPECTED_INPUT_HASHES = {
    str(PROVIDER_RECONCILIATION.relative_to(ROOT)): (
        "c28ec21baec0759ac02939f9007635f98b82a9faf5f85c564ad47f3c510c6751"
    ),
    str(PROVIDER_REPORT.relative_to(ROOT)): (
        "bed52c669e5e3fd7058a93b466ac7a26012a36bde8a91576b7e7ac469602e836"
    ),
    str(PRICING_CODE.relative_to(ROOT)): (
        "45b98842469dcd72275fa26a9aaeae6a7f524080044d7667f08bf17fe7b88a74"
    ),
    str(PROVIDER_AUDIT_REPORT.relative_to(ROOT)): (
        "3daf2efe67c3f5ede8b523bcc5f0f1caaa7df76dda5f23c61384c1ecd398437b"
    ),
    str(CURRENT_RECONCILIATION.relative_to(ROOT)): (
        "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256"
    ),
}

ARM_CONTRACT = {
    "router-gemini-3.1-pro": {
        "selected_run_label": (
            "router-gemini-3.1-pro/2026-06-30__14-57-05"
        ),
        "backend_model":
            "gemini-3.1-pro-preview",
        "trial_count": 60,
        "complete_trial_cost_count": 60,
        "lower_bound_trial_count": 0,
        "harness_input_tokens": 25_122_141,
        "harness_cache_tokens": 20_368_769,
        "harness_cache_miss_tokens": 4_753_372,
        "harness_output_tokens": 509_693,
        "selected_cost_usd":
            Decimal("19.6968138"),
        "historical_harness_cost_usd":
            Decimal("38.1007875"),
        "historical_reviewed_cost_usd":
            Decimal("46.469402372844"),
        "reporting_selected_cost_basis":
            "provider_rate_reconstructed_selected_run_request_tier",
        "db_selected_cost_basis":
            "provider_rate_reconstructed_harness_usage_validated",
        "selected_cost_relation":
            "estimate",
        "selected_cost_confidence":
            "high",
        "evidence_class":
            "verified_retained_trajectories_plus_official_provider_rates",
        "trial_cost_allocation_status":
            "available_provider_rate_reconstruction",
        "outcome_cost_allocation_status":
            "available_provider_rate_reconstruction",
        "unquantified_additional_cost_status":
            "none",
        "cache_hit_rate":
            Decimal("0.20"),
        "cache_miss_rate":
            Decimal("2"),
        "output_rate":
            Decimal("12"),
        "selected_request_count": 930,
        "selected_max_prompt_tokens": 66_438,
        "request_tier_upper_bound": 200_000,
    },
    "router-gemini-flash": {
        "selected_run_label": (
            "router-gemini-flash/2026-06-27__01-30-20"
        ),
        "backend_model":
            "gemini-3.5-flash",
        "trial_count": 60,
        "complete_trial_cost_count": 56,
        "lower_bound_trial_count": 4,
        "harness_input_tokens": 17_250_634,
        "harness_cache_tokens": 10_792_465,
        "harness_cache_miss_tokens": 6_458_169,
        "harness_output_tokens": 534_977,
        "selected_cost_usd":
            Decimal("16.12091625"),
        "historical_harness_cost_usd":
            Decimal("23.6669395"),
        "historical_reviewed_cost_usd":
            Decimal("43.534953854955"),
        "reporting_selected_cost_basis":
            "provider_rate_reconstructed_retained_usage_lower_bound",
        "db_selected_cost_basis":
            "lower_bound_provider_evidence",
        "selected_cost_relation":
            "lower_bound",
        "selected_cost_confidence":
            "high_for_retained_accounting_lower_bound",
        "evidence_class":
            "retained_artifacts_plus_official_provider_rates_trajectory_archive_unavailable",
        "trial_cost_allocation_status":
            "available_with_unresolved_usage_lower_bounds",
        "outcome_cost_allocation_status":
            "available_lower_bound",
        "unquantified_additional_cost_status":
            "possible_additional_unresolved_trial_spend",
        "cache_hit_rate":
            Decimal("0.15"),
        "cache_miss_rate":
            Decimal("1.50"),
        "output_rate":
            Decimal("9"),
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

INGESTION_LOCK_NAME = (
    "cc-deepseek-bench:gemini-provider-evidence-ingestion:v1"
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
            f"reviewed Gemini evidence mismatch: {label}"
        )


def verify_input_hashes() -> dict[str, str]:
    actual = {
        relative: sha256_path(ROOT / relative)
        for relative in EXPECTED_INPUT_HASHES
    }

    if actual != EXPECTED_INPUT_HASHES:
        raise EvidencePlanError(
            "reviewed Gemini input hashes changed"
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

    provider_data = json.loads(
        PROVIDER_RECONCILIATION.read_text(
            encoding="utf-8"
        )
    )

    billing_export = provider_data.get(
        "billing_export"
    )
    require_equal(
        billing_export,
        (
            "My Billing Account_Reports, "
            "2026-06-01 — 2026-06-30.csv"
        ),
        "Gemini billing export basename",
    )

    billing_rows = provider_data.get(
        "provider_billing_rows"
    )

    if (
        not isinstance(billing_rows, list)
        or len(billing_rows) != 1
        or not isinstance(billing_rows[0], dict)
    ):
        raise EvidencePlanError(
            "Gemini provider billing row "
            "does not resolve exactly once"
        )

    billing_row = billing_rows[0]

    require_equal(
        billing_row.get(
            "service_description"
        ),
        "Gemini API",
        "Gemini provider billing service",
    )

    billing_total = Decimal(
        str(
            billing_row.get(
                "unrounded_subtotal"
            )
        )
    )

    require_equal(
        billing_total,
        Decimal("26.371228"),
        "Gemini provider family billing total",
    )

    current_rows = {
        row["arm_id"]: row
        for row in read_csv(
            CURRENT_RECONCILIATION
        )
        if row.get("arm_id") in ARM_CONTRACT
    }

    require_equal(
        set(current_rows),
        set(ARM_CONTRACT),
        "current Gemini reconciliation arm membership",
    )

    provider_context_scope = (
        "shared_preselected_gemini_family_"
        "billing_export_through_2026-06-17_"
        "nonadditive"
    )

    billing_status = (
        "preselected_family_billing_context_"
        "not_selected_run"
    )

    for arm_id, spec in ARM_CONTRACT.items():
        row = current_rows[arm_id]

        checks = {
            "selected_run_label":
                spec["selected_run_label"],
            "backend_model":
                spec["backend_model"],
            "provider_models":
                spec["backend_model"],
            "provider":
                "google-gemini",
            "selected_cost_usd":
                money(
                    spec["selected_cost_usd"]
                ),
            "selected_cost_relation":
                spec[
                    "selected_cost_relation"
                ],
            "selected_cost_basis":
                spec[
                    "reporting_selected_cost_basis"
                ],
            "selected_cost_confidence":
                spec[
                    "selected_cost_confidence"
                ],
            "evidence_class":
                spec["evidence_class"],
            "provider_billed_cost_usd":
                "",
            "provider_context_billed_cost_usd":
                "26.371228",
            "provider_context_scope":
                provider_context_scope,
            "provider_billing_reconciliation_status":
                billing_status,
            "trial_count":
                str(spec["trial_count"]),
            "complete_trial_cost_count":
                str(
                    spec[
                        "complete_trial_cost_count"
                    ]
                ),
            "lower_bound_trial_count":
                str(
                    spec[
                        "lower_bound_trial_count"
                    ]
                ),
            "confirmed_zero_cost_trial_count":
                "0",
            "trial_cost_allocation_status":
                spec[
                    "trial_cost_allocation_status"
                ],
            "outcome_cost_allocation_status":
                spec[
                    "outcome_cost_allocation_status"
                ],
            "unquantified_additional_cost_status":
                spec[
                    "unquantified_additional_cost_status"
                ],
            "historical_harness_recorded_cost_usd":
                money(
                    spec[
                        "historical_harness_cost_usd"
                    ]
                ),
            "historical_reviewed_cost_usd":
                money(
                    spec[
                        "historical_reviewed_cost_usd"
                    ]
                ),
        }

        for key, expected_value in checks.items():
            require_equal(
                row.get(key, ""),
                expected_value,
                f"{arm_id} current reconciliation {key}",
            )

    pricing_text = PRICING_CODE.read_text(
        encoding="utf-8"
    )

    pricing_facts = (
        '"router-gemini-3.1-pro"',
        'Decimal("2")',
        'Decimal("0.20")',
        'Decimal("12")',
        '"router-gemini-flash"',
        'Decimal("1.50")',
        'Decimal("0.15")',
        'Decimal("9")',
        "all 930 Pro requests <=200K",
    )

    for fact in pricing_facts:
        if fact not in pricing_text:
            raise EvidencePlanError(
                "Gemini retained pricing audit "
                f"fact missing: {fact}"
            )

    sources = [
        {
            "source_key":
                "gemini_provider_reconciliation",
            "provider": "google-gemini",
            "evidence_kind": "manual_capture",
            "source_scope": "account_window",
            "provider_reference": str(
                PROVIDER_RECONCILIATION.relative_to(
                    ROOT
                )
            ),
            "source_sha256": hashes[
                str(
                    PROVIDER_RECONCILIATION.relative_to(
                        ROOT
                    )
                )
            ],
            "source_format": "json",
            "integrity_status":
                "sha256_verified",
            "notes": (
                "Committed sanitized Gemini family "
                "reconciliation derived from the Google "
                "Cloud Billing export and retained session "
                "artifacts. The raw billing export basename "
                "is retained, but the raw export SHA-256 is "
                "not retained. Detailed AI Studio provider "
                "model/token logging was unavailable."
            ),
        },
        {
            "source_key":
                "gemini_repository_pricing_audit",
            "provider": "google-gemini",
            "evidence_kind": "pricing_snapshot",
            "source_scope": "pricing_snapshot",
            "provider_reference": str(
                PRICING_CODE.relative_to(ROOT)
            ),
            "source_sha256": hashes[
                str(
                    PRICING_CODE.relative_to(ROOT)
                )
            ],
            "source_format": "python",
            "integrity_status":
                "sha256_verified",
            "notes": (
                "Repository-retained provider-evidence "
                "audit generator containing the exact "
                "Google Gemini rates used for the "
                "2026-08-25 reviewed reconstruction. The "
                "reviewed repository provenance search did "
                "not retain an official Google pricing-page "
                "URI; only the Google rate-limits page was "
                "found. Therefore this source supports "
                "qualified rate reconstruction, not "
                "selected-run provider billing."
            ),
        },
        {
            "source_key":
                "gemini_current_reconciliation",
            "provider": "google-gemini",
            "evidence_kind": "manual_capture",
            "source_scope": "other",
            "provider_reference": str(
                CURRENT_RECONCILIATION.relative_to(
                    ROOT
                )
            ),
            "source_sha256": hashes[
                str(
                    CURRENT_RECONCILIATION.relative_to(
                        ROOT
                    )
                )
            ],
            "source_format": "csv",
            "integrity_status":
                "sha256_verified",
            "notes": (
                "Reviewed Phase 3 selected-run Gemini "
                "reconciliation. Preserves selected costs, "
                "complete/unresolved trial counts, selected "
                "model identities, provider context "
                "semantics, and selected-run evidence "
                "limitations."
            ),
        },
    ]

    provider_usage_evidence: list[
        dict[str, Any]
    ] = []

    pricing_snapshots = []
    selected_runs = []
    usage_reconciliations = []
    usage_links = []
    cost_reconciliations = []
    cost_links = []

    for arm_id, spec in ARM_CONTRACT.items():
        pricing_key = (
            f"pricing:{spec['backend_model']}"
        )

        pricing_rules = {
            "uncached_input_usd_per_million":
                money(
                    spec["cache_miss_rate"]
                ),
            "cached_input_usd_per_million":
                (
                    "0.20"
                    if arm_id
                    == "router-gemini-3.1-pro"
                    else "0.15"
                ),
            "output_usd_per_million":
                money(
                    spec["output_rate"]
                ),
        }

        if arm_id == "router-gemini-3.1-pro":
            pricing_rules.update(
                {
                    "reviewed_request_tier_upper_bound_tokens":
                        200_000,
                    "selected_run_request_count":
                        930,
                    "selected_run_max_prompt_tokens":
                        66_438,
                    "selected_run_all_requests_within_reviewed_tier":
                        True,
                }
            )

        pricing_snapshots.append(
            {
                "pricing_key":
                    pricing_key,
                "source_key":
                    "gemini_repository_pricing_audit",
                "provider":
                    "google-gemini",
                "provider_model":
                    spec["backend_model"],
                "currency": "USD",
                "effective_from": None,
                "effective_until": None,
                "pricing_semantics": (
                    "request_tiered_cache_aware_"
                    "input_plus_output"
                    if arm_id
                    == "router-gemini-3.1-pro"
                    else
                    "cache_aware_input_plus_output"
                ),
                "pricing_rules":
                    pricing_rules,
                "official_source_uri": None,
                "notes": (
                    (
                        "Qualified repository-retained Google "
                        "rate snapshot. The 2026-08-25 "
                        "trajectory audit proves all 930 "
                        "selected-run model responses are at "
                        "or below the 200K prompt tier "
                        "boundary; maximum prompt is 66,438. "
                    )
                    if arm_id
                    == "router-gemini-3.1-pro"
                    else
                    (
                        "Qualified repository-retained Google "
                        "Flash rate snapshot used by the "
                        "2026-08-25 provider-evidence audit. "
                        "The selected Flash run lacks a "
                        "recoverable R2 trajectory archive and "
                        "four trials have no usage metadata, "
                        "so the selected reconstruction "
                        "remains a lower bound. "
                    )
                )
                + (
                    "The official pricing-page URI and "
                    "independently verified effective-through "
                    "date are not durably retained."
                ),
            }
        )

        selected_runs.append(
            {
                "arm_id": arm_id,
                "selected_run_label":
                    spec[
                        "selected_run_label"
                    ],
                "backend_model":
                    spec["backend_model"],
                "trial_count":
                    spec["trial_count"],
                "harness_input_tokens":
                    spec[
                        "harness_input_tokens"
                    ],
                "harness_cache_tokens":
                    spec[
                        "harness_cache_tokens"
                    ],
                "harness_cache_miss_tokens":
                    spec[
                        "harness_cache_miss_tokens"
                    ],
                "harness_output_tokens":
                    spec[
                        "harness_output_tokens"
                    ],
                "selected_cost_usd":
                    money(
                        spec[
                            "selected_cost_usd"
                        ]
                    ),
            }
        )

        if arm_id == "router-gemini-3.1-pro":
            usage_limitations = [
                "selected_run_provider_usage_export_unavailable",
                "selected_run_provider_billing_unavailable",
                "raw_google_billing_export_hash_unavailable",
                "official_pricing_page_uri_not_retained",
                "selected_raw_result_artifact_unavailable",
                "selected_run_provider_observed_model_unavailable",
            ]

            usage_notes = (
                "Selected-run harness aggregate is validated "
                "by the retained R2 trajectory audit: 60 "
                "trajectories and 930 model responses exactly "
                "reproduce 25,122,141 input, 20,368,769 "
                "cached input, and 509,693 output tokens. No "
                "selected-run Google provider usage export is "
                "retained. provider_observed_model is "
                "intentionally NULL: the retained Google "
                "billing evidence has no selected-run "
                "model/token detail. model_identity_status "
                "remains matched because the configured "
                "backend model agrees with the reviewed "
                "selected-run identity; this does not "
                "represent an independent provider "
                "observation."
            )

            cost_limitations = [
                "selected_run_provider_billing_unavailable",
                "selected_run_provider_usage_export_unavailable",
                "provider_billing_context_predates_selected_run",
                "raw_google_billing_export_hash_unavailable",
                "official_pricing_page_uri_not_retained",
                "pricing_effective_through_selected_run_not_independently_retained",
                "selected_raw_result_artifact_unavailable",
                "selected_run_provider_observed_model_unavailable",
            ]

            cost_notes = (
                "Selected cost is a request-tier-qualified "
                "cache-aware reconstruction from the "
                "validated selected-run harness aggregate. "
                "All 930 retained model responses are within "
                "the reviewed <=200K tier. The June 17 "
                "$26.371228 Gemini billing total predates "
                "this June 30 selected run and is context "
                "only, not selected-run provider billing. "
                "The selected provider-observed model is not "
                "independently available from detailed "
                "Google usage evidence; model-specific "
                "pricing is grounded in the configured/"
                "reviewed selected-run identity."
            )

        else:
            usage_limitations = [
                "selected_run_provider_usage_export_unavailable",
                "selected_run_provider_billing_unavailable",
                "four_selected_trials_missing_usage_metadata",
                "selected_run_r2_trajectory_archive_unavailable",
                "selected_raw_result_artifact_unavailable",
                "raw_google_billing_export_hash_unavailable",
                "official_pricing_page_uri_not_retained",
                "selected_run_provider_observed_model_unavailable",
            ]

            usage_notes = (
                "The selected harness aggregate represents "
                "retained usage from 56 of 60 trials. Four "
                "selected trials have no token metadata and "
                "the selected run is absent from the "
                "recoverable R2 trajectory archive. The "
                "retained aggregate is therefore usable only "
                "with an explicit qualified incompleteness "
                "limitation; missing usage is not synthesized "
                "as zero. provider_observed_model is "
                "intentionally NULL: the retained Google "
                "billing evidence has no selected-run "
                "model/token detail. model_identity_status "
                "remains matched because the configured "
                "backend model agrees with the reviewed "
                "selected-run identity; this does not "
                "represent an independent provider "
                "observation."
            )

            cost_limitations = [
                "selected_run_provider_billing_unavailable",
                "selected_run_provider_usage_export_unavailable",
                "four_selected_trials_missing_usage_metadata",
                "selected_run_r2_trajectory_archive_unavailable",
                "possible_additional_unresolved_trial_spend",
                "provider_billing_context_predates_selected_run",
                "raw_google_billing_export_hash_unavailable",
                "official_pricing_page_uri_not_retained",
                "pricing_effective_through_selected_run_not_independently_retained",
                "selected_raw_result_artifact_unavailable",
                "selected_run_provider_observed_model_unavailable",
            ]

            cost_notes = (
                "Selected cost is the cache-aware "
                "reconstruction of retained usage from 56 of "
                "60 selected trials. Four trials have no "
                "token metadata and the selected R2 "
                "trajectory archive is unavailable, so "
                "$16.12091625 is a strict retained-accounting "
                "lower bound, not an estimate of complete "
                "selected-run spend. Missing trial cost is "
                "not synthesized as zero. The selected "
                "provider-observed model is not independently "
                "available from detailed Google usage "
                "evidence; model-specific pricing is grounded "
                "in the configured/reviewed selected-run "
                "identity."
            )

        usage_reconciliations.append(
            {
                "arm_id":
                    arm_id,
                "reconciliation_version":
                    "gemini-provider-evidence-v1",
                "is_current": True,
                "harness_name":
                    "claude-code",
                "harness_version": None,
                "configured_route_model":
                    arm_id,
                "configured_backend_model":
                    spec["backend_model"],
                "harness_observed_model":
                    None,
                "provider_observed_model":
                    None,
                "model_identity_status":
                    "matched",
                "harness_input_tokens":
                    spec[
                        "harness_input_tokens"
                    ],
                "harness_cache_tokens":
                    spec[
                        "harness_cache_tokens"
                    ],
                "harness_output_tokens":
                    spec[
                        "harness_output_tokens"
                    ],
                "provider_ordinary_input_tokens":
                    None,
                "provider_cache_read_input_tokens":
                    None,
                "provider_cache_creation_input_tokens":
                    None,
                "provider_output_tokens":
                    None,
                "provider_request_count":
                    None,
                "matched_provider_request_count":
                    None,
                "unallocated_provider_request_count":
                    None,
                "provider_evidence_visible":
                    True,
                "selected_usage_authority":
                    "harness_usage_validated",
                "validation_status":
                    "validated_qualified",
                "limitation_codes":
                    usage_limitations,
                "notes":
                    usage_notes,
            }
        )

        for role in (
            "aggregate_usage",
            "model_identity",
        ):
            usage_links.append(
                {
                    "arm_id":
                        arm_id,
                    "source_key":
                        "gemini_current_reconciliation",
                    "evidence_role":
                        role,
                }
            )

        cost_reconciliations.append(
            {
                "arm_id":
                    arm_id,
                "reconciliation_version":
                    "gemini-provider-evidence-v1",
                "is_current": True,
                "harness_name":
                    "claude-code",
                "harness_version":
                    None,
                "harness_reported_cost_usd":
                    money(
                        spec[
                            "historical_harness_cost_usd"
                        ]
                    ),
                "provider_billed_cost_usd":
                    None,
                "provider_rate_reconstructed_cost_usd":
                    money(
                        spec[
                            "selected_cost_usd"
                        ]
                    ),
                "selected_cost_usd":
                    money(
                        spec[
                            "selected_cost_usd"
                        ]
                    ),
                "selected_cost_basis":
                    spec[
                        "db_selected_cost_basis"
                    ],
                "selected_cost_relation":
                    spec[
                        "selected_cost_relation"
                    ],
                "validation_status":
                    "validated_qualified",
                "provider_evidence_visible":
                    True,
                "pricing_snapshot_key":
                    pricing_key,
                "limitation_codes":
                    cost_limitations,
                "notes":
                    cost_notes,
            }
        )

        for source_key, role in (
            (
                "gemini_current_reconciliation",
                (
                    "rate_reconstruction"
                    if arm_id
                    == "router-gemini-3.1-pro"
                    else "lower_bound"
                ),
            ),
            (
                "gemini_repository_pricing_audit",
                "pricing",
            ),
            (
                "gemini_provider_reconciliation",
                "context",
            ),
        ):
            cost_links.append(
                {
                    "arm_id":
                        arm_id,
                    "source_key":
                        source_key,
                    "evidence_role":
                        role,
                }
            )

    provider_cost_evidence = [
        {
            "source_key":
                "gemini_provider_reconciliation",
            "arm_run_id": None,
            "trial_id": None,
            "pricing_snapshot_key":
                None,
            "provider_model":
                None,
            "cost_kind":
                "account_spend",
            "amount_usd":
                "26.371228",
            "currency": "USD",
            "allocation_scope":
                "account_window",
            "completeness_status":
                "complete",
            "notes": (
                "Exact unrounded Gemini API subtotal from "
                "the retained sanitized Google Cloud Billing "
                "reconciliation. This is one shared "
                "pre-selected Gemini-family/account context "
                "total and is not allocable to either "
                "selected full run."
            ),
            "raw_metadata": {
                "billing_export_basename":
                    billing_export,
                "provider_service_description":
                    "Gemini API",
                "rounded_subtotal_usd":
                    str(
                        billing_row.get(
                            "subtotal"
                        )
                    ),
                "unrounded_subtotal_usd":
                    "26.371228",
                "provider_context_through_date":
                    "2026-06-17",
                "predates_selected_runs":
                    True,
                "nonadditive_shared_family_context":
                    True,
                "raw_billing_export_sha256_retained":
                    False,
                "detailed_ai_studio_model_token_logging":
                    False,
            },
        }
    ]

    excluded_evidence = [
        {
            "evidence":
                "raw_google_cloud_billing_csv",
            "reason": (
                "basename retained but raw SHA-256/source "
                "artifact is not retained"
            ),
            "normalized": False,
        },
        {
            "evidence":
                "shared_26.371228_gemini_family_bill_as_selected_run_bill",
            "reason": (
                "predates both selected full runs and is "
                "not model/run allocable"
            ),
            "normalized_as_selected_provider_billing":
                False,
        },
        {
            "evidence":
                "missing_flash_trial_usage_or_cost",
            "reason": (
                "four trials lack usage metadata and selected "
                "R2 trajectory recovery is unavailable"
            ),
            "synthesized_as_zero":
                False,
        },
        {
            "evidence":
                "official_google_pricing_page_uri",
            "reason": (
                "not durably retained in reviewed repository "
                "sources"
            ),
            "invented": False,
        },
        {
            "evidence":
                "configured_model_as_provider_observed_model",
            "reason": (
                "The retained Google billing export contains "
                "no selected-run model/token detail. "
                "Configured/reviewed model identity must not "
                "be relabeled as provider observation."
            ),
            "provider_observed_model_populated":
                False,
        },
    ]

    write_counts = {
        "benchmark_provider_evidence_sources":
            len(sources),
        "benchmark_provider_usage_evidence":
            len(provider_usage_evidence),
        "benchmark_provider_pricing_snapshots":
            len(pricing_snapshots),
        "benchmark_provider_cost_evidence":
            len(provider_cost_evidence),
        "benchmark_usage_reconciliations":
            len(usage_reconciliations),
        "benchmark_usage_reconciliation_sources":
            len(usage_links),
        "benchmark_cost_reconciliations":
            len(cost_reconciliations),
        "benchmark_cost_reconciliation_sources":
            len(cost_links),
        "benchmark_evidence_promotion_gates":
            0,
    }

    expected_counts = {
        "benchmark_provider_evidence_sources":
            3,
        "benchmark_provider_usage_evidence":
            0,
        "benchmark_provider_pricing_snapshots":
            2,
        "benchmark_provider_cost_evidence":
            1,
        "benchmark_usage_reconciliations":
            2,
        "benchmark_usage_reconciliation_sources":
            4,
        "benchmark_cost_reconciliations":
            2,
        "benchmark_cost_reconciliation_sources":
            6,
        "benchmark_evidence_promotion_gates":
            0,
    }

    require_equal(
        write_counts,
        expected_counts,
        "planned row cardinality",
    )

    for selected in selected_runs:
        spec = ARM_CONTRACT[
            selected["arm_id"]
        ]

        reconstructed = reconstruct_cost(
            cache_hit_tokens=(
                selected[
                    "harness_cache_tokens"
                ]
            ),
            cache_miss_tokens=(
                selected[
                    "harness_cache_miss_tokens"
                ]
            ),
            output_tokens=(
                selected[
                    "harness_output_tokens"
                ]
            ),
            spec=spec,
        )

        require_equal(
            reconstructed,
            spec["selected_cost_usd"],
            (
                f"{selected['arm_id']} "
                "selected rate arithmetic"
            ),
        )

    return {
        "schema_version": 1,
        "plan_version":
            "gemini-provider-evidence-v2",
        "provider":
            "google-gemini",
        "mode":
            "plan-only",
        "database_writes_performed":
            False,
        "reviewed_plan_sha256":
            REVIEWED_PLAN_SHA256,
        "normalized_input_hashes":
            hashes,
        "raw_provider_archives": {
            "billing_export_basename":
                billing_export,
            "raw_billing_export_committed":
                False,
            "raw_billing_export_sha256_retained":
                False,
            "detailed_ai_studio_model_token_logging_available":
                False,
        },
        "sources":
            sources,
        "provider_usage_evidence":
            provider_usage_evidence,
        "pricing_snapshots":
            pricing_snapshots,
        "provider_cost_evidence":
            provider_cost_evidence,
        "selected_runs":
            selected_runs,
        "usage_reconciliations":
            usage_reconciliations,
        "usage_reconciliation_source_links":
            usage_links,
        "cost_reconciliations":
            cost_reconciliations,
        "cost_reconciliation_source_links":
            cost_links,
        "excluded_evidence":
            excluded_evidence,
        "write_counts":
            write_counts,
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
            where provider = 'google-gemini'
            """,
            (),
        ),
        "benchmark_provider_usage_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_usage_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'google-gemini'
            """,
            (),
        ),
        "benchmark_provider_pricing_snapshots": (
            """
            select count(*)
            from benchmark.benchmark_provider_pricing_snapshots
            where provider = 'google-gemini'
            """,
            (),
        ),
        "benchmark_provider_cost_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_cost_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'google-gemini'
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
            "state": "gemini_empty",
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
        "state": "exact_gemini_state",
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
                "selected Gemini run does not resolve exactly once"
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
                "selected Gemini run resolves to wrong arm"
            )
        if suite_id != "phase3-full-20":
            raise IntegrationSafetyError(
                "selected Gemini run resolves to wrong suite"
            )
        if logical_mode != "full":
            raise IntegrationSafetyError(
                "selected Gemini run is not logical full mode"
            )
        if storage_mode != "raw":
            raise IntegrationSafetyError(
                "selected Gemini run is not raw storage mode"
            )
        if int(n_trials) != int(
            selected["trial_count"]
        ):
            raise IntegrationSafetyError(
                "selected Gemini run has unexpected trial count"
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
                "selected Gemini run token geometry changed"
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
                "selected Gemini run cache-miss geometry changed"
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
                "selected Gemini rate reconstruction changed"
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
            "transactional Gemini evidence counts "
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
            "transactional Gemini usage "
            "reconciliations are incomplete"
        )

    verified_usage: dict[str, Any] = {}

    for row in usage_rows:
        arm_id = str(row[0])
        expected = usage_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected Gemini usage reconciliation arm"
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
            "transactional Gemini cost "
            "reconciliations are incomplete"
        )

    verified_cost: dict[str, Any] = {}

    for row in cost_rows:
        arm_id = str(row[0])
        expected = cost_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected Gemini cost reconciliation arm"
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
            row[14] != "google-gemini"
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
        where provider = 'google-gemini'
        order by source_sha256
        """
    )

    source_rows = cursor.fetchall()

    if len(source_rows) != len(
        expected_sources
    ):
        raise IntegrationSafetyError(
            "Gemini evidence source row count "
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
                "reviewed Gemini evidence source "
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
                "Gemini evidence source provenance "
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
        where pricing.provider = 'google-gemini'
        order by pricing.provider_model
        """
    )

    pricing_rows = cursor.fetchall()

    if len(pricing_rows) != len(
        pricing_plan
    ):
        raise IntegrationSafetyError(
            "Gemini pricing row count verification failed"
        )

    pricing_source_sha = expected_sources[
        "gemini_repository_pricing_audit"
    ]["source_sha256"]

    for row in pricing_rows:
        provider_model = str(row[2])
        expected = pricing_plan.get(
            provider_model
        )

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected Gemini pricing model"
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
                "Gemini pricing snapshot "
                "verification failed"
            )

    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_provider_usage_evidence evidence
        join benchmark.benchmark_provider_evidence_sources source
          on source.id = evidence.source_id
        where source.provider = 'google-gemini'
        """
    )

    if int(cursor.fetchone()[0]) != 0:
        raise IntegrationSafetyError(
            "Gemini provider usage evidence "
            "must remain empty"
        )

    expected_cost_rows = plan[
        "provider_cost_evidence"
    ]

    if len(expected_cost_rows) != 1:
        raise IntegrationSafetyError(
            "reviewed Gemini provider cost "
            "plan must contain exactly one row"
        )

    expected_cost = expected_cost_rows[0]

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
        where source.provider = 'google-gemini'
        """
    )

    cost_rows = cursor.fetchall()

    if len(cost_rows) != 1:
        raise IntegrationSafetyError(
            "Gemini provider cost row count "
            "verification failed"
        )

    row = cost_rows[0]

    provider_source_sha = expected_sources[
        "gemini_provider_reconciliation"
    ]["source_sha256"]

    if str(row[0]) != provider_source_sha:
        raise IntegrationSafetyError(
            "Gemini provider cost source "
            "verification failed"
        )

    if (
        row[1] is not True
        or row[2] is not True
        or row[3] is not True
    ):
        raise IntegrationSafetyError(
            "Gemini shared provider cost evidence "
            "must remain unallocated"
        )

    if row[4] is not None:
        raise IntegrationSafetyError(
            "Gemini shared provider cost evidence "
            "must not claim a provider model"
        )

    if row[5] != expected_cost[
        "cost_kind"
    ]:
        raise IntegrationSafetyError(
            "Gemini provider cost kind "
            "verification failed"
        )

    if Decimal(row[6]) != Decimal(
        expected_cost["amount_usd"]
    ):
        raise IntegrationSafetyError(
            "Gemini provider cost amount "
            "verification failed"
        )

    scalar = (
        row[7],
        row[8],
        row[9],
        row[10],
        row[11],
    )

    expected_scalar = (
        expected_cost["currency"],
        expected_cost["allocation_scope"],
        expected_cost[
            "completeness_status"
        ],
        expected_cost["notes"],
        expected_cost["raw_metadata"],
    )

    if scalar != expected_scalar:
        raise IntegrationSafetyError(
            "Gemini provider cost detail "
            "verification failed"
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
            "Gemini reconciliation source-link "
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

            if state["state"] == "gemini_empty":
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
                == "exact_gemini_state"
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
                    "Gemini provider evidence target is "
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
                == "exact_gemini_state"
            ):
                raise IntegrationSafetyError(
                    "reviewed Gemini provider evidence "
                    "is already applied"
                )

            if (
                state["state"]
                != "gemini_empty"
            ):
                raise IntegrationSafetyError(
                    "Gemini provider evidence target "
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
        != "exact_gemini_state"
    ):
        raise IntegrationSafetyError(
            "committed Gemini provider evidence "
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
                != "gemini_empty"
            ):
                raise IntegrationSafetyError(
                    "rollback-only Gemini ingestion "
                    "requires an empty Gemini target"
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
                != "exact_gemini_state"
            ):
                raise IntegrationSafetyError(
                    "transactional Gemini insertion "
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
            "rollback-only Gemini ingestion "
            "left persistent Gemini state"
        )

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state":
            diagnostics.commit_state,
        "target_state": "gemini_empty",
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
            "Emit the reviewed Gemini evidence plan "
            "without opening a database connection."
        ),
    )

    group.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Read the real database using a read-only "
            "transaction and report whether the "
            "provider-scoped Gemini target is empty "
            "and the selected canonical runs still "
            "match the reviewed contract."
        ),
    )

    group.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Insert and verify the reviewed Gemini "
            "evidence inside one PostgreSQL transaction, "
            "roll it back, then prove zero persistence "
            "from a second connection."
        ),
    )

    group.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Permanently insert the reviewed Gemini "
            "provider evidence only from an empty "
            "Gemini target, verify it transactionally, "
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
