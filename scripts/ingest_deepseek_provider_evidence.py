#!/usr/bin/env python3
"""Plan, verify, or apply DeepSeek Phase 3 provider-evidence ingestion."""

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
      "deepseek_family_reconciliation_2026-06-17.json"
)
PROVIDER_REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "DEEPSEEK_FAMILY_USAGE_RECONCILIATION_2026-06-17.md"
)
PRICING_CODE = ROOT / "scripts/lib/costs.py"
CURRENT_RECONCILIATION = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)

REVIEWED_PLAN_SHA256 = (
    "b5f105095c2b2243b0c3b2cea9a29a0a"
    "7564a37a9de812bfd5fd9ea918ff2a21"
)

EXPECTED_INPUT_HASHES = {
    str(PROVIDER_RECONCILIATION.relative_to(ROOT)): (
        "3e8c68b6888d825caa07023d834dffe43e878b38581a9665fdab8645b7457aff"
    ),
    str(PROVIDER_REPORT.relative_to(ROOT)): (
        "ea173208461f2be437639c5631210bf99108fc323dfed99c3a954f82738cb540"
    ),
    str(PRICING_CODE.relative_to(ROOT)): (
        "965e9f52dc8499c4acf0b0e4f35004e90a7bfa127f97aac762eab993e44a7050"
    ),
    str(CURRENT_RECONCILIATION.relative_to(ROOT)): (
        "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256"
    ),
}

EXPECTED_ARCHIVES = (
    "usage_data_2026_5.zip",
    "usage_data_2026_6.zip",
)

ARM_CONTRACT = {
    "router-deepseek-flash": {
        "selected_run_label": (
            "router-deepseek-flash/2026-06-28__13-28-50"
        ),
        "backend_model": "deepseek-v4-flash",
        "trial_count": 60,
        "harness_input_tokens": 102_663_832,
        "harness_cache_tokens": 100_425_344,
        "harness_cache_miss_tokens": 2_238_488,
        "harness_output_tokens": 1_733_059,
        "selected_cost_usd": Decimal("1.0798358032"),
        "historical_harness_cost_usd": Decimal("56.35246"),
        "historical_reviewed_cost_usd": Decimal(
            "56.7953838632"
        ),
        "historical_context_cost_usd": Decimal(
            "1.1502775424"
        ),
        "provider_validation_date": "2026-06-15",
        "provider_validation_cache_hit": 17_726_720,
        "provider_validation_cache_miss": 200_187,
        "provider_validation_output": 175_514,
        "provider_validation_requests": 191,
        "provider_validation_cost_usd": Decimal(
            "0.126804916"
        ),
        "cache_hit_rate": Decimal("0.0028"),
        "cache_miss_rate": Decimal("0.14"),
        "output_rate": Decimal("0.28"),
        "days_from_validation_to_selected_run": 13,
    },
    "router-deepseek-pro": {
        "selected_run_label": (
            "router-deepseek-pro/2026-06-19__13-47-59"
        ),
        "backend_model": "deepseek-v4-pro",
        "trial_count": 60,
        "harness_input_tokens": 44_293_924,
        "harness_cache_tokens": 42_372_608,
        "harness_cache_miss_tokens": 1_921_316,
        "harness_output_tokens": 1_046_381,
        "selected_cost_usd": Decimal("1.899724634"),
        "historical_harness_cost_usd": Decimal("50.203188"),
        "historical_reviewed_cost_usd": Decimal(
            "50.439011911"
        ),
        "historical_context_cost_usd": Decimal(
            "1.963511004"
        ),
        "provider_validation_date": "2026-06-16",
        "provider_validation_cache_hit": 4_906_624,
        "provider_validation_cache_miss": 164_407,
        "provider_validation_output": 71_255,
        "provider_validation_requests": 116,
        "provider_validation_cost_usd": Decimal(
            "0.151295407"
        ),
        "cache_hit_rate": Decimal("0.003625"),
        "cache_miss_rate": Decimal("0.435"),
        "output_rate": Decimal("0.87"),
        "days_from_validation_to_selected_run": 3,
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
    "cc-deepseek-bench:deepseek-provider-evidence-ingestion:v1"
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
            f"reviewed DeepSeek evidence mismatch: {label}"
        )


def verify_input_hashes() -> dict[str, str]:
    actual = {
        relative: sha256_path(ROOT / relative)
        for relative in EXPECTED_INPUT_HASHES
    }

    if actual != EXPECTED_INPUT_HASHES:
        raise EvidencePlanError(
            "reviewed DeepSeek input hashes changed"
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

    archives = provider_data.get("usage_archives")
    require_equal(
        archives,
        list(EXPECTED_ARCHIVES),
        "private provider archive basenames",
    )

    validation_rows: dict[str, dict[str, Any]] = {}

    reconciliation = provider_data.get("reconciliation")
    if not isinstance(reconciliation, list):
        raise EvidencePlanError(
            "DeepSeek provider reconciliation rows unavailable"
        )

    for arm_id, spec in ARM_CONTRACT.items():
        matches = [
            row
            for row in reconciliation
            if isinstance(row, dict)
            and row.get("date")
            == spec["provider_validation_date"]
            and row.get("model")
            == spec["backend_model"]
        ]

        if len(matches) != 1:
            raise EvidencePlanError(
                f"{arm_id} provider validation row "
                "does not resolve exactly once"
            )

        row = matches[0]

        expected = {
            "provider_cache_hit_input":
                spec["provider_validation_cache_hit"],
            "session_cache_hit_input":
                spec["provider_validation_cache_hit"],
            "provider_cache_miss_input":
                spec["provider_validation_cache_miss"],
            "session_cache_miss_input":
                spec["provider_validation_cache_miss"],
            "provider_output_tokens":
                spec["provider_validation_output"],
            "session_output_tokens":
                spec["provider_validation_output"],
            "provider_request_count":
                spec["provider_validation_requests"],
            "session_assistant_messages":
                spec["provider_validation_requests"],
            "status": "session tokens confirmed",
        }

        for key, expected_value in expected.items():
            require_equal(
                row.get(key),
                expected_value,
                f"{arm_id} provider validation {key}",
            )

        provider_cost = Decimal(
            str(row.get("provider_cost"))
        )
        require_equal(
            provider_cost,
            spec["provider_validation_cost_usd"],
            f"{arm_id} provider validation cost",
        )

        reconstructed = reconstruct_cost(
            cache_hit_tokens=(
                spec["provider_validation_cache_hit"]
            ),
            cache_miss_tokens=(
                spec["provider_validation_cache_miss"]
            ),
            output_tokens=(
                spec["provider_validation_output"]
            ),
            spec=spec,
        )

        require_equal(
            reconstructed,
            provider_cost,
            f"{arm_id} provider validation rate arithmetic",
        )

        validation_rows[arm_id] = {
            "date": spec["provider_validation_date"],
            "provider_model": spec["backend_model"],
            "cache_hit_input_tokens": (
                spec["provider_validation_cache_hit"]
            ),
            "cache_miss_input_tokens": (
                spec["provider_validation_cache_miss"]
            ),
            "output_tokens": (
                spec["provider_validation_output"]
            ),
            "request_count": (
                spec["provider_validation_requests"]
            ),
            "provider_cost_usd": money(provider_cost),
        }

    current_rows = {
        row["arm_id"]: row
        for row in read_csv(CURRENT_RECONCILIATION)
        if row.get("arm_id") in ARM_CONTRACT
    }

    require_equal(
        set(current_rows),
        set(ARM_CONTRACT),
        "current DeepSeek reconciliation arm membership",
    )

    for arm_id, spec in ARM_CONTRACT.items():
        row = current_rows[arm_id]

        checks = {
            "selected_run_label":
                spec["selected_run_label"],
            "backend_model":
                spec["backend_model"],
            "selected_cost_usd":
                money(spec["selected_cost_usd"]),
            "selected_cost_relation":
                "estimate",
            "selected_cost_basis":
                "provider_rate_reconstructed_selected_run",
            "provider_billed_cost_usd":
                "",
            "provider_context_billed_cost_usd":
                money(spec["historical_context_cost_usd"]),
            "provider_context_scope":
                "same_day_model_aggregate",
            "provider_billing_reconciliation_status":
                "same_day_model_aggregate_not_run_isolated",
            "historical_harness_recorded_cost_usd":
                money(spec["historical_harness_cost_usd"]),
            "historical_reviewed_cost_usd":
                money(spec["historical_reviewed_cost_usd"]),
        }

        for key, expected_value in checks.items():
            require_equal(
                row.get(key, ""),
                expected_value,
                f"{arm_id} current reconciliation {key}",
            )

    sources = [
        {
            "source_key":
                "deepseek_provider_reconciliation",
            "provider": "deepseek",
            "evidence_kind": "manual_capture",
            "source_scope": "provider_window",
            "provider_reference": str(
                PROVIDER_RECONCILIATION.relative_to(ROOT)
            ),
            "source_sha256": hashes[
                str(
                    PROVIDER_RECONCILIATION.relative_to(
                        ROOT
                    )
                )
            ],
            "source_format": "json",
            "integrity_status": "sha256_verified",
            "notes": (
                "Committed sanitized reconciliation derived "
                "from two private DeepSeek provider-dashboard "
                "archive ZIPs. Raw archive identifiers are "
                "omitted; archive basenames are retained, but "
                "raw ZIP SHA-256 values are not."
            ),
        },
        {
            "source_key": "deepseek_repository_pricing",
            "provider": "deepseek",
            "evidence_kind": "pricing_snapshot",
            "source_scope": "pricing_snapshot",
            "provider_reference": str(
                PRICING_CODE.relative_to(ROOT)
            ),
            "source_sha256": hashes[
                str(PRICING_CODE.relative_to(ROOT))
            ],
            "source_format": "python",
            "integrity_status": "sha256_verified",
            "notes": (
                "Repository-pinned DeepSeek cache-aware rates. "
                "The retained June 15/16 provider totals "
                "exactly validate the arithmetic at those "
                "dates. The official provider pricing URI and "
                "complete effective period are not retained; "
                "this source supports qualified "
                "reconstruction, not exact selected-run billing."
            ),
        },
        {
            "source_key":
                "deepseek_selected_run_reconstruction",
            "provider": "deepseek",
            "evidence_kind": "manual_capture",
            "source_scope": "other",
            "provider_reference": str(
                CURRENT_RECONCILIATION.relative_to(ROOT)
            ),
            "source_sha256": hashes[
                str(
                    CURRENT_RECONCILIATION.relative_to(
                        ROOT
                    )
                )
            ],
            "source_format": "csv",
            "integrity_status": "sha256_verified",
            "notes": (
                "Reviewed repository-generated selected-run "
                "rate reconciliation. The source spans multiple "
                "providers and arms, so its scope is 'other'. "
                "Only reviewed DeepSeek selected-run rows are "
                "used. Historical same-day provider-context "
                "totals are not promoted as source-backed "
                "selected-run billing evidence."
            ),
        },
    ]

    provider_usage_evidence = []
    pricing_snapshots = []
    provider_cost_evidence = []
    selected_runs = []
    usage_reconciliations = []
    usage_links = []
    cost_reconciliations = []
    cost_links = []
    excluded_evidence = []

    for arm_id, spec in ARM_CONTRACT.items():
        validation = validation_rows[arm_id]

        provider_usage_evidence.append(
            {
                "source_key":
                    "deepseek_provider_reconciliation",
                "arm_run_id": None,
                "trial_id": None,
                "provider_request_id": None,
                "provider_model":
                    spec["backend_model"],
                "request_started_at": None,
                "request_finished_at": None,
                "ordinary_input_tokens": None,
                "cache_read_input_tokens":
                    validation[
                        "cache_hit_input_tokens"
                    ],
                "cache_creation_input_tokens": None,
                "output_tokens":
                    validation["output_tokens"],
                "request_count":
                    validation["request_count"],
                "allocation_scope": "model_window",
                "completeness_status": "partial",
                "notes": (
                    "Exact retained DeepSeek provider model/day "
                    "usage for cache-read, output, and request "
                    "count. Provider cache-miss input is exact "
                    "but cannot be split into migration-011 "
                    "ordinary versus cache-creation input "
                    "without fabrication; the combined value "
                    "is retained in raw_metadata."
                ),
                "raw_metadata": {
                    "provider_utc_date":
                        validation["date"],
                    "provider_cache_hit_input_tokens":
                        validation[
                            "cache_hit_input_tokens"
                        ],
                    "provider_cache_miss_input_tokens":
                        validation[
                            "cache_miss_input_tokens"
                        ],
                    "provider_output_tokens":
                        validation["output_tokens"],
                    "provider_request_count":
                        validation["request_count"],
                    "session_tokens_match_provider": True,
                    "cache_miss_column_mapping":
                        "unavailable_combined_class_only",
                },
            }
        )

        pricing_key = (
            f"pricing:{spec['backend_model']}"
        )

        pricing_snapshots.append(
            {
                "pricing_key": pricing_key,
                "source_key":
                    "deepseek_repository_pricing",
                "provider": "deepseek",
                "provider_model":
                    spec["backend_model"],
                "currency": "USD",
                "effective_from": None,
                "effective_until": None,
                "pricing_semantics":
                    "cache_hit_vs_cache_miss_plus_output",
                "pricing_rules": {
                    "cache_hit_input_usd_per_million":
                        money(
                            spec["cache_hit_rate"]
                        ),
                    "cache_miss_input_usd_per_million":
                        money(
                            spec["cache_miss_rate"]
                        ),
                    "output_usd_per_million":
                        money(spec["output_rate"]),
                },
                "official_source_uri": None,
                "notes": (
                    "Qualified repository-pinned pricing "
                    f"snapshot. Exactly reproduces retained "
                    f"provider billing on "
                    f"{spec['provider_validation_date']}; "
                    f"selected run occurs "
                    f"{spec['days_from_validation_to_selected_run']} "
                    "days later, and the official "
                    "effective-through date is not independently "
                    "retained."
                ),
            }
        )

        provider_cost_evidence.append(
            {
                "source_key":
                    "deepseek_provider_reconciliation",
                "arm_run_id": None,
                "trial_id": None,
                "pricing_snapshot_key": None,
                "provider_model":
                    spec["backend_model"],
                "cost_kind":
                    "provider_dashboard_total",
                "amount_usd":
                    validation["provider_cost_usd"],
                "currency": "USD",
                "allocation_scope": "model_window",
                "completeness_status": "complete",
                "notes": (
                    "Exact retained provider model/day total "
                    "from sanitized DeepSeek reconciliation; "
                    "this is smoke-window context, not "
                    "selected-full-run billing."
                ),
                "raw_metadata": {
                    "provider_utc_date":
                        validation["date"],
                    "provider_cache_hit_input_tokens":
                        validation[
                            "cache_hit_input_tokens"
                        ],
                    "provider_cache_miss_input_tokens":
                        validation[
                            "cache_miss_input_tokens"
                        ],
                    "provider_output_tokens":
                        validation["output_tokens"],
                    "provider_request_count":
                        validation["request_count"],
                    "raw_provider_archive_sha256_retained":
                        False,
                    "session_tokens_confirmed": True,
                },
            }
        )

        selected_runs.append(
            {
                "arm_id": arm_id,
                "selected_run_label":
                    spec["selected_run_label"],
                "backend_model":
                    spec["backend_model"],
                "trial_count":
                    spec["trial_count"],
                "harness_input_tokens":
                    spec["harness_input_tokens"],
                "harness_cache_tokens":
                    spec["harness_cache_tokens"],
                "harness_cache_miss_tokens":
                    spec[
                        "harness_cache_miss_tokens"
                    ],
                "harness_output_tokens":
                    spec["harness_output_tokens"],
                "selected_cost_usd":
                    money(
                        spec["selected_cost_usd"]
                    ),
            }
        )

        usage_reconciliations.append(
            {
                "arm_id": arm_id,
                "reconciliation_version":
                    "deepseek-provider-evidence-v1",
                "is_current": True,
                "harness_name": "claude-code",
                "harness_version": None,
                "configured_route_model": arm_id,
                "configured_backend_model":
                    spec["backend_model"],
                "harness_observed_model": None,
                "provider_observed_model":
                    spec["backend_model"],
                "model_identity_status": "matched",
                "harness_input_tokens":
                    spec["harness_input_tokens"],
                "harness_cache_tokens":
                    spec["harness_cache_tokens"],
                "harness_output_tokens":
                    spec["harness_output_tokens"],
                "provider_ordinary_input_tokens": None,
                "provider_cache_read_input_tokens": None,
                "provider_cache_creation_input_tokens": None,
                "provider_output_tokens": None,
                "provider_request_count": None,
                "matched_provider_request_count": None,
                "unallocated_provider_request_count": None,
                "provider_evidence_visible": True,
                "selected_usage_authority":
                    "harness_usage_validated",
                "validation_status":
                    "validated_qualified",
                "limitation_codes": [
                    "provider_validation_scope_smoke_not_selected_run",
                    "selected_run_provider_usage_unavailable",
                    "provider_model_observed_in_same_route_smoke_not_selected_full_run",
                    "cache_miss_collapses_ordinary_and_cache_creation",
                    "raw_provider_archive_hash_unavailable",
                ],
                "notes": (
                    "Selected full-run harness aggregate is "
                    "usable because the same DeepSeek "
                    "Anthropic-compatible path was validated "
                    "against exact provider/session token "
                    "matches in retained June smoke evidence. "
                    "No selected-run provider request or "
                    "aggregate usage export is retained."
                ),
            }
        )

        for role in ("model_identity", "context"):
            usage_links.append(
                {
                    "arm_id": arm_id,
                    "source_key":
                        "deepseek_provider_reconciliation",
                    "evidence_role": role,
                }
            )

        cost_reconciliations.append(
            {
                "arm_id": arm_id,
                "reconciliation_version":
                    "deepseek-provider-evidence-v1",
                "is_current": True,
                "harness_name": "claude-code",
                "harness_version": None,
                "harness_reported_cost_usd":
                    money(
                        spec[
                            "historical_harness_cost_usd"
                        ]
                    ),
                "provider_billed_cost_usd": None,
                "provider_rate_reconstructed_cost_usd":
                    money(
                        spec["selected_cost_usd"]
                    ),
                "selected_cost_usd":
                    money(
                        spec["selected_cost_usd"]
                    ),
                "selected_cost_basis":
                    "provider_rate_reconstructed_harness_usage_validated",
                "selected_cost_relation": "estimate",
                "validation_status":
                    "validated_qualified",
                "provider_evidence_visible": True,
                "pricing_snapshot_key": pricing_key,
                "limitation_codes": [
                    "selected_run_provider_billing_unavailable",
                    "selected_run_provider_usage_unavailable",
                    "pricing_effective_through_selected_run_not_independently_retained",
                    "raw_provider_archive_hash_unavailable",
                    "historical_same_day_context_not_promoted",
                ],
                "notes": (
                    "Selected cost is a cache-aware "
                    "reconstruction from the validated "
                    "selected-run harness aggregate. Provider "
                    "smoke billing exactly validates the rate "
                    "arithmetic before the selected run, but no "
                    "source-backed selected-run provider billing "
                    "total is retained."
                ),
            }
        )

        for source_key, role in (
            (
                "deepseek_selected_run_reconstruction",
                "rate_reconstruction",
            ),
            (
                "deepseek_repository_pricing",
                "pricing",
            ),
            (
                "deepseek_provider_reconciliation",
                "context",
            ),
        ):
            cost_links.append(
                {
                    "arm_id": arm_id,
                    "source_key": source_key,
                    "evidence_role": role,
                }
            )

        excluded_evidence.append(
            {
                "arm_id": arm_id,
                "value_usd": money(
                    spec[
                        "historical_context_cost_usd"
                    ]
                ),
                "scope":
                    "same_day_model_aggregate",
                "reason": (
                    "Historical reviewed context only; no "
                    "recoverable first-party provider source "
                    "lineage before commit 4ffe8e90. Not "
                    "selected-run provider billing."
                ),
            }
        )

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
        "benchmark_evidence_promotion_gates": 0,
    }

    expected_counts = {
        "benchmark_provider_evidence_sources": 3,
        "benchmark_provider_usage_evidence": 2,
        "benchmark_provider_pricing_snapshots": 2,
        "benchmark_provider_cost_evidence": 2,
        "benchmark_usage_reconciliations": 2,
        "benchmark_usage_reconciliation_sources": 4,
        "benchmark_cost_reconciliations": 2,
        "benchmark_cost_reconciliation_sources": 6,
        "benchmark_evidence_promotion_gates": 0,
    }

    require_equal(
        write_counts,
        expected_counts,
        "planned row cardinality",
    )

    return {
        "schema_version": 1,
        "plan_version":
            "deepseek-provider-evidence-v3",
        "provider": "deepseek",
        "mode": "plan-only",
        "database_writes_performed": False,
        "reviewed_plan_sha256":
            REVIEWED_PLAN_SHA256,
        "normalized_input_hashes": hashes,
        "raw_provider_archives": {
            "basenames": list(EXPECTED_ARCHIVES),
            "raw_archives_committed": False,
            "raw_archive_sha256_retained": False,
        },
        "sources": sources,
        "provider_usage_evidence":
            provider_usage_evidence,
        "pricing_snapshots": pricing_snapshots,
        "provider_cost_evidence":
            provider_cost_evidence,
        "selected_runs": selected_runs,
        "usage_reconciliations":
            usage_reconciliations,
        "usage_reconciliation_source_links":
            usage_links,
        "cost_reconciliations":
            cost_reconciliations,
        "cost_reconciliation_source_links":
            cost_links,
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
            where provider = 'deepseek'
            """,
            (),
        ),
        "benchmark_provider_usage_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_usage_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'deepseek'
            """,
            (),
        ),
        "benchmark_provider_pricing_snapshots": (
            """
            select count(*)
            from benchmark.benchmark_provider_pricing_snapshots
            where provider = 'deepseek'
            """,
            (),
        ),
        "benchmark_provider_cost_evidence": (
            """
            select count(*)
            from benchmark.benchmark_provider_cost_evidence evidence
            join benchmark.benchmark_provider_evidence_sources source
              on source.id = evidence.source_id
            where source.provider = 'deepseek'
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
            "state": "deepseek_empty",
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
        "state": "exact_deepseek_state",
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
                "selected DeepSeek run does not resolve exactly once"
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
                "selected DeepSeek run resolves to wrong arm"
            )
        if suite_id != "phase3-full-20":
            raise IntegrationSafetyError(
                "selected DeepSeek run resolves to wrong suite"
            )
        if logical_mode != "full":
            raise IntegrationSafetyError(
                "selected DeepSeek run is not logical full mode"
            )
        if storage_mode != "raw":
            raise IntegrationSafetyError(
                "selected DeepSeek run is not raw storage mode"
            )
        if int(n_trials) != int(
            selected["trial_count"]
        ):
            raise IntegrationSafetyError(
                "selected DeepSeek run has unexpected trial count"
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
                "selected DeepSeek run token geometry changed"
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
                "selected DeepSeek run cache-miss geometry changed"
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
                "selected DeepSeek rate reconstruction changed"
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
            "transactional DeepSeek evidence counts "
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
            "transactional DeepSeek usage "
            "reconciliations are incomplete"
        )

    verified_usage: dict[str, Any] = {}

    for row in usage_rows:
        arm_id = str(row[0])
        expected = usage_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected DeepSeek usage reconciliation arm"
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
            "transactional DeepSeek cost "
            "reconciliations are incomplete"
        )

    verified_cost: dict[str, Any] = {}

    for row in cost_rows:
        arm_id = str(row[0])
        expected = cost_plan.get(arm_id)

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected DeepSeek cost reconciliation arm"
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
            row[14] != "deepseek"
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
        where provider = 'deepseek'
        order by source_sha256
        """
    )

    source_rows = cursor.fetchall()

    if len(source_rows) != len(expected_sources):
        raise IntegrationSafetyError(
            "DeepSeek evidence source row count "
            "verification failed"
        )

    by_sha = {
        str(row[4]): row
        for row in source_rows
    }

    for source in expected_sources.values():
        row = by_sha.get(
            source["source_sha256"]
        )

        if row is None:
            raise IntegrationSafetyError(
                "reviewed DeepSeek evidence source "
                "SHA-256 is missing"
            )

        expected_tuple = (
            source["provider"],
            source["evidence_kind"],
            source["source_scope"],
            source["provider_reference"],
            source["source_sha256"],
            source["source_format"],
            source["integrity_status"],
            source["notes"],
            True,
            True,
            True,
            source.get(
                "raw_metadata",
                {},
            ),
        )

        if tuple(row) != expected_tuple:
            raise IntegrationSafetyError(
                "DeepSeek evidence source provenance "
                "verification failed"
            )

    pricing_plan = {
        row["provider_model"]: row
        for row in plan["pricing_snapshots"]
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
        where pricing.provider = 'deepseek'
        order by pricing.provider_model
        """
    )

    pricing_rows = cursor.fetchall()

    if len(pricing_rows) != len(pricing_plan):
        raise IntegrationSafetyError(
            "DeepSeek pricing row count verification failed"
        )

    pricing_source_sha = expected_sources[
        "deepseek_repository_pricing"
    ]["source_sha256"]

    for row in pricing_rows:
        provider_model = str(row[2])
        expected = pricing_plan.get(
            provider_model
        )

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected DeepSeek pricing model"
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
                "DeepSeek pricing snapshot verification failed"
            )

    usage_plan = {
        row["provider_model"]: row
        for row in plan[
            "provider_usage_evidence"
        ]
    }

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
        where source.provider = 'deepseek'
        order by evidence.provider_model
        """
    )

    usage_rows = cursor.fetchall()

    if len(usage_rows) != len(usage_plan):
        raise IntegrationSafetyError(
            "DeepSeek provider usage row count "
            "verification failed"
        )

    usage_source_sha = expected_sources[
        "deepseek_provider_reconciliation"
    ]["source_sha256"]

    for row in usage_rows:
        provider_model = str(row[4])
        expected = usage_plan.get(
            provider_model
        )

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected DeepSeek provider usage model"
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
            row[11],
            row[12],
            row[13],
            row[14],
            row[15],
        )

        expected_tuple = (
            usage_source_sha,
            True,
            True,
            expected["provider_request_id"],
            expected["provider_model"],
            expected["request_started_at"],
            expected["request_finished_at"],
            expected["ordinary_input_tokens"],
            expected["cache_read_input_tokens"],
            expected[
                "cache_creation_input_tokens"
            ],
            expected["output_tokens"],
            expected["request_count"],
            expected["allocation_scope"],
            expected["completeness_status"],
            expected["notes"],
            expected["raw_metadata"],
        )

        if observed != expected_tuple:
            raise IntegrationSafetyError(
                "DeepSeek provider usage verification failed"
            )

    cost_plan = {
        row["provider_model"]: row
        for row in plan[
            "provider_cost_evidence"
        ]
    }

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
        where source.provider = 'deepseek'
        order by evidence.provider_model
        """
    )

    cost_rows = cursor.fetchall()

    if len(cost_rows) != len(cost_plan):
        raise IntegrationSafetyError(
            "DeepSeek provider cost row count "
            "verification failed"
        )

    for row in cost_rows:
        provider_model = str(row[4])
        expected = cost_plan.get(
            provider_model
        )

        if expected is None:
            raise IntegrationSafetyError(
                "unexpected DeepSeek provider cost model"
            )

        if str(row[0]) != usage_source_sha:
            raise IntegrationSafetyError(
                "DeepSeek provider cost source "
                "verification failed"
            )
        if (
            row[1] is not True
            or row[2] is not True
            or row[3] is not True
        ):
            raise IntegrationSafetyError(
                "DeepSeek smoke cost evidence "
                "must remain unallocated"
            )
        if row[4] != expected["provider_model"]:
            raise IntegrationSafetyError(
                "DeepSeek provider cost model "
                "verification failed"
            )
        if row[5] != expected["cost_kind"]:
            raise IntegrationSafetyError(
                "DeepSeek provider cost kind "
                "verification failed"
            )
        if Decimal(row[6]) != Decimal(
            expected["amount_usd"]
        ):
            raise IntegrationSafetyError(
                "DeepSeek provider cost amount "
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
            expected["currency"],
            expected["allocation_scope"],
            expected["completeness_status"],
            expected["notes"],
            expected["raw_metadata"],
        )

        if scalar != expected_scalar:
            raise IntegrationSafetyError(
                "DeepSeek provider cost detail "
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
            "DeepSeek reconciliation source-link "
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

            if state["state"] == "deepseek_empty":
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
                == "exact_deepseek_state"
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
                    "DeepSeek provider evidence target is "
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
                == "exact_deepseek_state"
            ):
                raise IntegrationSafetyError(
                    "reviewed DeepSeek provider evidence "
                    "is already applied"
                )

            if (
                state["state"]
                != "deepseek_empty"
            ):
                raise IntegrationSafetyError(
                    "DeepSeek provider evidence target "
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
        != "exact_deepseek_state"
    ):
        raise IntegrationSafetyError(
            "committed DeepSeek provider evidence "
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
                != "deepseek_empty"
            ):
                raise IntegrationSafetyError(
                    "rollback-only DeepSeek ingestion "
                    "requires an empty DeepSeek target"
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
                != "exact_deepseek_state"
            ):
                raise IntegrationSafetyError(
                    "transactional DeepSeek insertion "
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
            "rollback-only DeepSeek ingestion "
            "left persistent DeepSeek state"
        )

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state":
            diagnostics.commit_state,
        "target_state": "deepseek_empty",
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
            "Emit the reviewed DeepSeek evidence plan "
            "without opening a database connection."
        ),
    )

    group.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Read the real database using a read-only "
            "transaction and report whether the "
            "provider-scoped DeepSeek target is empty "
            "and the selected canonical runs still "
            "match the reviewed contract."
        ),
    )

    group.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Insert and verify the reviewed DeepSeek "
            "evidence inside one PostgreSQL transaction, "
            "roll it back, then prove zero persistence "
            "from a second connection."
        ),
    )

    group.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Permanently insert the reviewed DeepSeek "
            "provider evidence only from an empty "
            "DeepSeek target, verify it transactionally, "
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
