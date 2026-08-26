#!/usr/bin/env python3
"""Plan or check DeepSeek Phase 3 provider-evidence ingestion readiness."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass
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

    return {
        "state": "partial_or_unexpected",
        "counts": counts,
        "reason":
            "existing_deepseek_evidence_or_reconciliation_rows",
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

            if state["state"] != "deepseek_empty":
                connection.rollback()
                raise IntegrationSafetyError(
                    "DeepSeek provider evidence target is "
                    "partially or unexpectedly populated"
                )

            diagnostics.enter(
                "canonical_run_resolution"
            )

            resolved = resolve_arm_runs(
                cursor,
                plan,
            )

        connection.rollback()

    finally:
        connection.close()

    return {
        "status": "ready",
        "mode": "check-only",
        "commit_state":
            diagnostics.commit_state,
        "target_state":
            diagnostics.target_state,
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

    mode = (
        "plan"
        if args.plan
        else "check-only"
    )

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

        result = check_only(
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
