#!/usr/bin/env python3
"""Generate the 2026-08-25 Phase 3 current-reviewed V4 comparison.

V4 promotes the additive provider-evidence audit into a fully reconciled
current selected-cost layer while preserving every frozen V3 / 2026-08-24
artifact unchanged.

Cost source of truth:
- phase3_current_arm_cost_reconciliation_20260825.csv

Provider provenance enrichment:
- phase3_provider_cost_evidence_matrix_20260825.csv

Historical benchmark identity and outcome counts continue to come from the
frozen 2026-08-05 reviewed comparison. Supporting Anthropic exception evidence
remains independently hash-bound.

All 15 core arms and all 16 extended arms have current reconciliation rows.
The resulting scope totals mix exact values, estimates, partial estimates, and
retained-usage lower bounds. They are therefore neither exact provider bills
nor global lower bounds.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "phase3-current-reviewed-comparison-v4"
GENERATOR_VERSION = "3.0.0"
REVIEWED_AT = "2026-08-25"

REPO_ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_extended_reviewed_comparison_20260805.json"
)
ARM_RECONCILIATION_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)
PROVIDER_MATRIX_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_provider_cost_evidence_matrix_20260825.csv"
)

ANTHROPIC_EXCEPTION_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv"
)

OUTPUT_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_current_reviewed_comparison_20260825.json"
)
DASHBOARD_OUTPUT_PATH = (
    REPO_ROOT
    / "apps/dashboard/src/generated/"
      "phase3-current-reviewed-comparison-data-v4.ts"
)

EXPECTED_HISTORICAL_SHA256 = (
    "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"
)
EXPECTED_ARM_RECONCILIATION_SHA256 = (
    "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256"
)
EXPECTED_PROVIDER_MATRIX_SHA256 = (
    "e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218"
)
EXPECTED_ANTHROPIC_EXCEPTION_SHA256 = (
    "9223673f2dcdd55fa558f0336d72d721f0bf3c58f409e84fadeaeb277a7dfa88"
)

EXPECTED_RECONCILED_ARM_IDS = frozenset({
    "router-anthropic-fable-5",
    "router-anthropic-haiku-sanitized",
    "router-anthropic-opus",
    "router-anthropic-sonnet",
    "router-deepseek-flash",
    "router-deepseek-pro",
    "router-gemini-3.1-pro",
    "router-gemini-flash",
    "router-glm-5.1",
    "router-glm-5.2",
    "router-gpt-5.4",
    "router-gpt-5.5",
    "router-grok-build-0.1",
    "router-kimi-k2.6",
    "router-kimi-k3",
    "router-qwen-3.7-plus",
})

EXPECTED_EXACT_PROVIDER_BILLED_ARM_IDS = frozenset({
    "router-gpt-5.4",
    "router-gpt-5.5",
})

EXPECTED_SCOPE_TOTALS = {
    "phase3-core": Decimal("316.8790274572"),
    "phase3-extended": Decimal("343.4494304572"),
}

EXPECTED_SOURCE_SCOPE_TRANSFORMED_TOTALS = {
    "phase3-core": Decimal("316.879027457200"),
    "phase3-extended": Decimal("343.4494304571999"),
}

EXPECTED_SCOPE_RECONCILED_COSTS = {
    "phase3-core": Decimal("316.8790274572"),
    "phase3-extended": Decimal("343.4494304572"),
}

EXPECTED_SCOPE_RELATION_COUNTS = {
    "phase3-core": {
        "exact": 4,
        "estimate": 6,
        "lower_bound": 5,
        "historical_fallback": 0,
    },
    "phase3-extended": {
        "exact": 4,
        "estimate": 7,
        "lower_bound": 5,
        "historical_fallback": 0,
    },
}

EXPECTED_UNQUANTIFIED_ADDITIONAL_COST_ARM_IDS = frozenset({
    "router-anthropic-opus",
    "router-anthropic-sonnet",
    "router-grok-build-0.1",
    "router-glm-5.1",
    "router-gemini-flash",
    "router-qwen-3.7-plus",
})

EXPECTED_EXACT_PROVIDER_BILLED_COST = Decimal("78.3968475")

# The 20260825 provider audit inherited three historical reviewed-cost
# values from pre-existing aggregate calculations whose final decimal
# differs from the frozen 20260805 reviewed snapshot by 1-2e-12.
#
# These are provenance bridge residuals only. V4 continues to use the
# frozen 20260805 values as its canonical historicalReviewedCostUsd.
# Pin the exact known residuals rather than applying a general tolerance.
EXPECTED_HISTORICAL_REVIEWED_BRIDGE_DELTAS = {
    "router-gemini-3.1-pro": Decimal("0.000000000001"),
    "router-gemini-flash": Decimal("0.000000000002"),
    "router-qwen-3.7-plus": Decimal("0.000000000002"),
}

EXPECTED_EXCEPTION_LOWER_BOUND_TOTALS = {
    "router-anthropic-opus": Decimal("7.01247975"),
    "router-anthropic-sonnet": Decimal("10.18738545"),
}

EXPECTED_EXCEPTION_LOWER_BOUND_COUNTS = {
    "router-anthropic-opus": 2,
    "router-anthropic-sonnet": 5,
}

ARM_FIELDS = [
    "arm_id",
    "selected_run_label",
    "routing_aliases",
    "backend_model",
    "provider_models",
    "provider",
    "selected_cost_usd",
    "selected_cost_relation",
    "selected_cost_basis",
    "selected_cost_confidence",
    "evidence_class",
    "provider_billed_cost_usd",
    "provider_context_billed_cost_usd",
    "provider_context_scope",
    "provider_context_excess_usd",
    "provider_billing_reconciliation_status",
    "trial_count",
    "complete_trial_cost_count",
    "lower_bound_trial_count",
    "confirmed_zero_cost_trial_count",
    "trial_cost_allocation_status",
    "outcome_cost_allocation_status",
    "clean_success_cost_usd",
    "normal_failure_cost_usd",
    "exception_failure_cost_usd",
    "exception_with_success_signal_cost_usd",
    "known_allocated_cost_usd",
    "unallocated_known_cost_usd",
    "unquantified_additional_cost_status",
    "historical_harness_recorded_cost_usd",
    "historical_reviewed_cost_usd",
    "evidence_note",
]

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

EXCEPTION_FIELDS = [
    "arm_id",
    "task_id",
    "attempt_index",
    "outcome_bucket",
    "provider_model",
    "retained_input_tokens",
    "retained_cache_read_tokens",
    "retained_cache_creation_tokens",
    "retained_ordinary_input_tokens",
    "retained_output_tokens",
    "transcript_unique_message_cache_creation_tokens",
    "transcript_cache_creation_excess_tokens",
    "transcript_observed_cache_tier",
    "input_rate_usd_per_million",
    "cache_creation_5m_rate_usd_per_million",
    "cache_read_rate_usd_per_million",
    "output_rate_usd_per_million",
    "retained_usage_lower_bound_cost_usd",
    "cost_relation",
    "evidence_status",
]

SELECTED_RELATIONS = {
    "exact",
    "estimate",
    "lower_bound",
}

AVAILABLE_OUTCOME_STATUSES = {
    "available_provider_rate_reconstruction",
    "available_lower_bound",
    "available_partial_estimate",
}

UNAVAILABLE_OUTCOME_STATUSES = {
    "unavailable_provider_aggregate",
    "unavailable_no_reviewed_outcome_join",
}

NO_UNQUANTIFIED_COST_STATUSES = {
    "none",
    "none_for_selected_retained_usage",
}


def fail(message: str) -> None:
    raise ValueError(message)


def decimal(value: str | None, label: str) -> Decimal:
    if value is None or value.strip() == "":
        fail(f"missing decimal: {label}")
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid decimal: {label}") from exc
    if not parsed.is_finite():
        fail(f"non-finite decimal: {label}")
    return parsed


def optional_decimal(value: str | None, label: str) -> Decimal | None:
    if value is None or value.strip() == "":
        return None
    return decimal(value, label)


def nonnegative_integer(value: str | None, label: str) -> int:
    if value is None or value.strip() == "":
        fail(f"missing integer: {label}")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid integer: {label}") from exc
    if parsed < 0:
        fail(f"negative integer: {label}")
    return parsed


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        fail("cannot serialize non-finite decimal")
    if value == 0:
        return "0"
    return format(value, "f")


def optional_decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else decimal_text(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def split_semicolon(value: str) -> list[str]:
    return [part for part in value.split(";") if part]


def ratio(cost: Decimal, count: int, label: str) -> str | None:
    if count < 0:
        fail(f"negative denominator: {label}")
    if count == 0:
        return None
    return decimal_text(cost / Decimal(count))


def assert_output_safety(
    input_paths: tuple[Path, ...],
    output_path: Path,
    dashboard_output_path: Path,
) -> tuple[Path, Path]:
    inputs = {path.resolve() for path in input_paths}
    outputs = (
        output_path.resolve(),
        dashboard_output_path.resolve(),
    )

    if outputs[0] == outputs[1]:
        fail("generated output paths must be distinct")

    if any(output in inputs for output in outputs):
        fail("generated output path must not equal an input path")

    for output in (output_path, dashboard_output_path):
        if not output.exists():
            continue

        for input_path in input_paths:
            if not input_path.exists():
                continue
            try:
                if output.samefile(input_path):
                    fail("generated output path must not alias an input path")
            except FileNotFoundError:
                continue

    if output_path.exists() and dashboard_output_path.exists():
        try:
            if output_path.samefile(dashboard_output_path):
                fail("generated output paths must not alias each other")
        except FileNotFoundError:
            pass

    return outputs


def read_historical(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"unable to read historical snapshot: {path}"
        ) from exc

    if value.get("schemaVersion") != "phase3-reviewed-comparison-v1":
        fail("historical snapshot schema changed")
    if value.get("reviewedAt") != "2026-08-05":
        fail("historical snapshot review date changed")
    if set(value.get("scopes", {})) != {
        "phase3-core",
        "phase3-extended",
    }:
        fail("historical snapshot scope membership changed")

    return value


def historical_selected_cost(arm: dict[str, Any]) -> Decimal:
    adjusted = arm.get("adjustedKnownCostUsd")
    qualified = arm.get("qualifiedRetainedRateCostUsd")

    if adjusted is not None and qualified is not None:
        fail(f"{arm['armId']} has two historical reviewed cost bases")
    if adjusted is not None:
        return decimal(
            adjusted,
            f"{arm['armId']}.adjustedKnownCostUsd",
        )
    if qualified is not None:
        return decimal(
            qualified,
            f"{arm['armId']}.qualifiedRetainedRateCostUsd",
        )

    fail(f"{arm['armId']} has no historical reviewed cost basis")


def historical_scope_cost(scope: dict[str, Any]) -> Decimal:
    evidence = scope["costEvidence"]
    adjusted = evidence.get("adjustedKnownCostUsd")
    qualified = evidence.get("qualifiedAdjustedCostEstimateUsd")

    if adjusted is not None and qualified is not None:
        fail(f"{scope['scopeId']} has two historical scope cost bases")
    if adjusted is not None:
        return decimal(
            adjusted,
            f"{scope['scopeId']}.adjustedKnownCostUsd",
        )
    if qualified is not None:
        return decimal(
            qualified,
            f"{scope['scopeId']}.qualifiedAdjustedCostEstimateUsd",
        )

    fail(f"{scope['scopeId']} has no historical scope cost")


def historical_arm_index(
    historical: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    extended = historical["scopes"]["phase3-extended"]["arms"]
    core = historical["scopes"]["phase3-core"]["arms"]

    result = {
        arm["armId"]: arm
        for arm in extended
    }

    if len(result) != len(extended):
        fail("historical extended scope contains duplicate arms")

    core_ids = {
        arm["armId"]
        for arm in core
    }

    if not core_ids.issubset(result):
        fail("historical core is not a subset of extended")

    if set(result) != EXPECTED_RECONCILED_ARM_IDS:
        fail("historical extended arm membership changed")

    return result

def read_exception_lower_bounds(
    path: Path,
) -> tuple[dict[str, Decimal], Counter[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXCEPTION_FIELDS:
            fail("Anthropic exception evidence columns changed")
        rows = list(reader)

    if len(rows) != 7:
        fail("expected exactly seven Anthropic exception evidence rows")

    million = Decimal("1000000")
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    counts: Counter[str] = Counter()

    for index, row in enumerate(rows):
        label = f"anthropic_exception[{index}]"

        if row["arm_id"] not in EXPECTED_EXCEPTION_LOWER_BOUND_TOTALS:
            fail(f"{label} unexpected arm")
        if row["outcome_bucket"] != "exception_failure":
            fail(f"{label} outcome bucket changed")
        if row["cost_relation"] != "lower_bound":
            fail(f"{label} cost relation changed")
        if (
            row["transcript_observed_cache_tier"]
            != "5m_only"
        ):
            fail(f"{label} cache tier changed")
        if row["evidence_status"] != (
            "retained_trajectory_matches_harbor_but_"
            "raw_api_activity_exceeds_retained_accounting"
        ):
            fail(f"{label} evidence status changed")

        total_input = decimal(
            row["retained_input_tokens"],
            f"{label}.retained_input_tokens",
        )
        cache_read = decimal(
            row["retained_cache_read_tokens"],
            f"{label}.retained_cache_read_tokens",
        )
        cache_creation = decimal(
            row["retained_cache_creation_tokens"],
            f"{label}.retained_cache_creation_tokens",
        )
        ordinary = decimal(
            row["retained_ordinary_input_tokens"],
            f"{label}.retained_ordinary_input_tokens",
        )
        output = decimal(
            row["retained_output_tokens"],
            f"{label}.retained_output_tokens",
        )

        if total_input - cache_read - cache_creation != ordinary:
            fail(f"{label} retained ordinary-input identity changed")

        transcript_creation = decimal(
            row[
                "transcript_unique_message_cache_creation_tokens"
            ],
            f"{label}.transcript_unique_message_cache_creation_tokens",
        )
        transcript_excess = decimal(
            row["transcript_cache_creation_excess_tokens"],
            f"{label}.transcript_cache_creation_excess_tokens",
        )

        if transcript_creation - cache_creation != transcript_excess:
            fail(f"{label} transcript cache-creation excess changed")
        if transcript_excess <= 0:
            fail(f"{label} must retain positive omitted API evidence")

        rin = decimal(
            row["input_rate_usd_per_million"],
            f"{label}.input_rate",
        )
        rcreate = decimal(
            row["cache_creation_5m_rate_usd_per_million"],
            f"{label}.cache_creation_rate",
        )
        rread = decimal(
            row["cache_read_rate_usd_per_million"],
            f"{label}.cache_read_rate",
        )
        rout = decimal(
            row["output_rate_usd_per_million"],
            f"{label}.output_rate",
        )

        calculated = (
            ordinary * rin
            + cache_creation * rcreate
            + cache_read * rread
            + output * rout
        ) / million

        retained_cost = decimal(
            row["retained_usage_lower_bound_cost_usd"],
            f"{label}.retained_usage_lower_bound_cost_usd",
        )

        if calculated != retained_cost:
            fail(f"{label} lower-bound cost no longer reproduces")

        totals[row["arm_id"]] += retained_cost
        counts[row["arm_id"]] += 1

    if dict(totals) != EXPECTED_EXCEPTION_LOWER_BOUND_TOTALS:
        fail("Anthropic exception lower-bound arm totals changed")
    if dict(counts) != EXPECTED_EXCEPTION_LOWER_BOUND_COUNTS:
        fail("Anthropic exception lower-bound arm counts changed")

    return dict(totals), counts


def read_arm_reconciliation(
    path: Path,
    historical: dict[str, Any],
    exception_totals: dict[str, Decimal],
    exception_counts: Counter[str],
) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ARM_FIELDS:
            fail("current arm reconciliation columns changed")
        rows = list(reader)

    by_arm = {
        row["arm_id"]: row
        for row in rows
    }

    if len(by_arm) != len(rows):
        fail("current arm reconciliation contains duplicate arms")
    if set(by_arm) != EXPECTED_RECONCILED_ARM_IDS:
        fail("current reconciled arm membership changed")

    historical_arms = historical_arm_index(historical)

    for arm_id, row in by_arm.items():
        label = f"reconciliation.{arm_id}"
        historical_arm = historical_arms[arm_id]

        if row["backend_model"] != historical_arm["backendModel"]:
            fail(f"{label} backend model disagrees with frozen arm")

        if arm_id == "router-kimi-k3":
            if (
                historical_arm["provider"] != "moonshot"
                or row["provider"] != "moonshot-kimi"
            ):
                fail(f"{label} Kimi provider identity changed")
        elif row["provider"] != historical_arm["provider"]:
            fail(f"{label} provider disagrees with frozen arm")

        historical_recorded = decimal(
            historical_arm["recordedCostUsd"],
            f"{arm_id}.historical.recordedCostUsd",
        )
        historical_reviewed = historical_selected_cost(
            historical_arm
        )

        if decimal(
            row["historical_harness_recorded_cost_usd"],
            f"{label}.historical_harness_recorded_cost_usd",
        ) != historical_recorded:
            fail(f"{label} historical recorded-cost bridge changed")

        historical_bridge = decimal(
            row["historical_reviewed_cost_usd"],
            f"{label}.historical_reviewed_cost_usd",
        )
        historical_bridge_delta = (
            historical_bridge - historical_reviewed
        )
        expected_bridge_delta = (
            EXPECTED_HISTORICAL_REVIEWED_BRIDGE_DELTAS.get(
                arm_id,
                Decimal("0"),
            )
        )

        if historical_bridge_delta != expected_bridge_delta:
            fail(
                f"{label} historical reviewed-cost bridge changed: "
                f"expected delta {expected_bridge_delta}, "
                f"got {historical_bridge_delta}"
            )

        selected = decimal(
            row["selected_cost_usd"],
            f"{label}.selected_cost_usd",
        )
        allocated = decimal(
            row["known_allocated_cost_usd"],
            f"{label}.known_allocated_cost_usd",
        )
        unallocated = decimal(
            row["unallocated_known_cost_usd"],
            f"{label}.unallocated_known_cost_usd",
        )

        if min(selected, allocated, unallocated) < 0:
            fail(f"{label} contains negative selected-cost evidence")

        if allocated + unallocated != selected:
            fail(f"{label} selected cost does not reconcile")

        relation = row["selected_cost_relation"]
        if relation not in SELECTED_RELATIONS:
            fail(f"{label} selected-cost relation changed")

        trial_count = nonnegative_integer(
            row["trial_count"],
            f"{label}.trial_count",
        )
        complete_count = nonnegative_integer(
            row["complete_trial_cost_count"],
            f"{label}.complete_trial_cost_count",
        )
        lower_count = nonnegative_integer(
            row["lower_bound_trial_count"],
            f"{label}.lower_bound_trial_count",
        )
        zero_count = nonnegative_integer(
            row["confirmed_zero_cost_trial_count"],
            f"{label}.confirmed_zero_cost_trial_count",
        )

        if trial_count != int(historical_arm["trialCount"]):
            fail(f"{label} trial count disagrees with frozen arm")

        if (
            complete_count > trial_count
            or lower_count > trial_count
            or zero_count > trial_count
        ):
            fail(f"{label} trial coverage exceeds trial count")

        outcome_status = row["outcome_cost_allocation_status"]
        outcome_fields = (
            "clean_success_cost_usd",
            "normal_failure_cost_usd",
            "exception_failure_cost_usd",
            "exception_with_success_signal_cost_usd",
        )

        if outcome_status in AVAILABLE_OUTCOME_STATUSES:
            outcome_values = [
                decimal(
                    row[field],
                    f"{label}.{field}",
                )
                for field in outcome_fields
            ]

            if (
                sum(outcome_values, Decimal("0"))
                != allocated
            ):
                fail(
                    f"{label} outcome allocation does not reconcile"
                )

        elif outcome_status in UNAVAILABLE_OUTCOME_STATUSES:
            if any(
                row[field] != ""
                for field in outcome_fields
            ):
                fail(
                    f"{label} unavailable outcomes contain allocations"
                )
        else:
            fail(f"{label} outcome allocation status changed")

        provider_billed = optional_decimal(
            row["provider_billed_cost_usd"],
            f"{label}.provider_billed_cost_usd",
        )
        provider_context = optional_decimal(
            row["provider_context_billed_cost_usd"],
            f"{label}.provider_context_billed_cost_usd",
        )
        provider_excess = optional_decimal(
            row["provider_context_excess_usd"],
            f"{label}.provider_context_excess_usd",
        )

        if (
            provider_context is not None
            and provider_excess is not None
            and provider_context - selected != provider_excess
        ):
            fail(f"{label} provider-context delta changed")

        if row["selected_cost_basis"] == "provider_billed":
            if (
                arm_id
                not in EXPECTED_EXACT_PROVIDER_BILLED_ARM_IDS
                or relation != "exact"
                or provider_billed != selected
                or row[
                    "provider_billing_reconciliation_status"
                ] != "exact_arm_total"
                or allocated != 0
                or unallocated != selected
                or outcome_status
                != "unavailable_provider_aggregate"
            ):
                fail(
                    f"{label} exact provider-billed semantics changed"
                )
        elif provider_billed is not None:
            fail(
                f"{label} unexpectedly claims exact provider billing"
            )

        additional = row[
            "unquantified_additional_cost_status"
        ]

        if relation == "lower_bound":
            if (
                lower_count <= 0
                or additional not in {
                    "possible_additional_exception_path_spend",
                    "possible_additional_unresolved_trial_spend",
                }
            ):
                fail(f"{label} lower-bound semantics changed")

            if arm_id in EXPECTED_EXCEPTION_LOWER_BOUND_TOTALS:
                if (
                    additional
                    != "possible_additional_exception_path_spend"
                    or exception_counts[arm_id] != lower_count
                    or exception_totals[arm_id] > selected
                ):
                    fail(
                        f"{label} Anthropic lower-bound detail changed"
                    )
            else:
                if (
                    additional
                    != "possible_additional_unresolved_trial_spend"
                    or exception_counts[arm_id] != 0
                ):
                    fail(
                        f"{label} unresolved-usage lower bound changed"
                    )

        else:
            if lower_count != 0:
                fail(
                    f"{label} non-lower-bound arm has lower-bound trials"
                )

            if relation == "exact":
                if additional != "none":
                    fail(
                        f"{label} exact arm has unquantified cost"
                    )

            elif relation == "estimate":
                if additional not in {
                    "none",
                    "none_for_selected_retained_usage",
                    "unresolved_trial_spend_and_cache_classification_uncertainty",
                }:
                    fail(
                        f"{label} estimate uncertainty changed"
                    )

    extended_sum = sum(
        (
            decimal(
                row["selected_cost_usd"],
                f"{arm_id}.selected_cost_usd",
            )
            for arm_id, row in by_arm.items()
        ),
        Decimal("0"),
    )

    if (
        extended_sum
        != EXPECTED_SCOPE_RECONCILED_COSTS[
            "phase3-extended"
        ]
    ):
        fail("extended reconciled selected-cost subtotal changed")

    provider_billed_sum = sum(
        (
            decimal(
                row["provider_billed_cost_usd"],
                f"{arm_id}.provider_billed_cost_usd",
            )
            for arm_id, row in by_arm.items()
            if row["provider_billed_cost_usd"] != ""
        ),
        Decimal("0"),
    )

    if (
        provider_billed_sum
        != EXPECTED_EXACT_PROVIDER_BILLED_COST
    ):
        fail("exact provider-billed subtotal changed")

    return by_arm


def read_provider_matrix(
    path: Path,
    reconciliation_rows: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MATRIX_FIELDS:
            fail("provider evidence matrix columns changed")
        rows = list(reader)

    by_arm = {
        row["arm_id"]: row
        for row in rows
    }

    if len(by_arm) != len(rows):
        fail("provider evidence matrix contains duplicate arms")
    if set(by_arm) != EXPECTED_RECONCILED_ARM_IDS:
        fail("provider evidence matrix membership changed")

    mirrored_fields = (
        "provider",
        "selected_run_label",
        "selected_cost_relation",
        "selected_cost_basis",
        "selected_cost_confidence",
        "evidence_class",
        "trial_count",
        "complete_trial_cost_count",
        "provider_context_billed_cost_usd",
        "provider_context_scope",
        "historical_harness_recorded_cost_usd",
        "historical_reviewed_cost_usd",
    )

    token_fields = (
        "selected_input_tokens",
        "selected_cache_tokens",
        "selected_output_tokens",
    )

    for arm_id, row in by_arm.items():
        label = f"provider_matrix.{arm_id}"
        reconciliation = reconciliation_rows[arm_id]

        for field in mirrored_fields:
            if row[field] != reconciliation[field]:
                fail(
                    f"{label}.{field} disagrees with reconciliation"
                )

        if decimal(
            row["selected_cost_usd"],
            f"{label}.selected_cost_usd",
        ) != decimal(
            reconciliation["selected_cost_usd"],
            f"reconciliation.{arm_id}.selected_cost_usd",
        ):
            fail(f"{label} selected cost disagrees")

        unresolved = nonnegative_integer(
            row["unresolved_trial_count"],
            f"{label}.unresolved_trial_count",
        )
        trial_count = nonnegative_integer(
            row["trial_count"],
            f"{label}.trial_count",
        )

        if unresolved > trial_count:
            fail(f"{label} unresolved trial count is invalid")

        relation = row["selected_cost_relation"]
        lower_count = nonnegative_integer(
            reconciliation["lower_bound_trial_count"],
            f"reconciliation.{arm_id}.lower_bound_trial_count",
        )

        if (
            relation == "lower_bound"
            and unresolved != lower_count
        ):
            fail(
                f"{label} lower-bound unresolved count changed"
            )

        if (
            arm_id == "router-glm-5.1"
            and unresolved != 5
        ):
            fail(
                f"{label} GLM partial unresolved count changed"
            )

        for field in token_fields:
            if row[field] != "":
                nonnegative_integer(
                    row[field],
                    f"{label}.{field}",
                )

        rate_reconstruction = optional_decimal(
            row[
                "provider_context_rate_reconstruction_usd"
            ],
            f"{label}.provider_context_rate_reconstruction_usd",
        )
        rate_excess = optional_decimal(
            row[
                "provider_context_rate_reconstruction_excess_vs_selected_usd"
            ],
            f"{label}.provider_context_rate_reconstruction_excess_vs_selected_usd",
        )

        # A contextual rate reconstruction can describe an earlier
        # provider window with no meaningful selected-run delta. Kimi K2.6
        # is the retained example. If an excess-vs-selected value *is*
        # supplied, however, both the reconstruction and its exact delta
        # remain fail-closed.
        if rate_excess is not None:
            if rate_reconstruction is None:
                fail(
                    f"{label} contextual rate excess has no reconstruction"
                )

            selected = decimal(
                row["selected_cost_usd"],
                f"{label}.selected_cost_usd",
            )

            if rate_reconstruction - selected != rate_excess:
                fail(
                    f"{label} contextual rate reconstruction delta changed"
                )

        account_spend = optional_decimal(
            row["provider_context_account_spend_usd"],
            f"{label}.provider_context_account_spend_usd",
        )
        overhead = optional_decimal(
            row["provider_context_overhead_usd"],
            f"{label}.provider_context_overhead_usd",
        )
        context_billed = optional_decimal(
            row["provider_context_billed_cost_usd"],
            f"{label}.provider_context_billed_cost_usd",
        )

        # Account-spend decomposition is asserted only when an
        # account-spend total exists. Some rows intentionally retain an
        # explicit zero overhead without any account total (for example,
        # GLM 5.2 and Kimi K3); zero alone must not fabricate a billing
        # decomposition.
        if account_spend is not None:
            if (
                overhead is None
                or context_billed is None
                or context_billed + overhead != account_spend
            ):
                fail(
                    f"{label} account-overhead decomposition changed"
                )
        elif (
            overhead is not None
            and overhead != Decimal("0")
        ):
            fail(
                f"{label} has nonzero overhead without account spend"
            )

        if row["audit_scope"] not in {
            "inherited_20260824_current_reconciliation",
            "provider_evidence_audit_20260825",
        }:
            fail(f"{label} audit scope changed")

        for required in (
            "trajectory_evidence_status",
            "pricing_provenance_status",
            "provider_context_temporal_relation",
            "provider_context_allocation_confidence",
            "audit_conclusion",
        ):
            if row[required] == "":
                fail(f"{label}.{required} is empty")

    return by_arm

def selected_arm(
    arm: dict[str, Any],
    reconciliation_rows: dict[str, dict[str, str]],
    matrix_rows: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = deepcopy(arm)
    arm_id = result["armId"]

    row = reconciliation_rows.get(arm_id)
    matrix = matrix_rows.get(arm_id)

    if row is None or matrix is None:
        fail(
            f"{arm_id} is missing from the complete V4 reconciliation"
        )

    historical_cost = historical_selected_cost(result)
    historical_recorded = decimal(
        result["recordedCostUsd"],
        f"{arm_id}.recordedCostUsd",
    )

    result["historicalHarnessRecordedCostUsd"] = decimal_text(
        historical_recorded
    )
    result["historicalReviewedCostUsd"] = decimal_text(
        historical_cost
    )
    result["historicalReviewedCostBasis"] = result["costBasis"]

    selected = decimal(
        row["selected_cost_usd"],
        f"{arm_id}.selected_cost_usd",
    )

    result["currentReconciliationStatus"] = "reconciled"
    result["currentSelectedRunLabel"] = row[
        "selected_run_label"
    ]
    result["currentRoutingAliases"] = split_semicolon(
        row["routing_aliases"]
    )
    result["currentProviderModels"] = split_semicolon(
        row["provider_models"]
    )

    result["selectedCostRelation"] = row[
        "selected_cost_relation"
    ]
    result["selectedCostBasis"] = row[
        "selected_cost_basis"
    ]
    result["selectedCostConfidence"] = row[
        "selected_cost_confidence"
    ]
    result["selectedEfficiencyRelation"] = row[
        "selected_cost_relation"
    ]
    result["evidenceClass"] = row["evidence_class"]

    result["providerBilledCostUsd"] = optional_decimal_text(
        optional_decimal(
            row["provider_billed_cost_usd"],
            f"{arm_id}.provider_billed_cost_usd",
        )
    )
    result["providerContextBilledCostUsd"] = (
        optional_decimal_text(
            optional_decimal(
                row["provider_context_billed_cost_usd"],
                f"{arm_id}.provider_context_billed_cost_usd",
            )
        )
    )
    result["providerContextScope"] = (
        row["provider_context_scope"] or None
    )
    result["providerContextExcessUsd"] = optional_decimal_text(
        optional_decimal(
            row["provider_context_excess_usd"],
            f"{arm_id}.provider_context_excess_usd",
        )
    )
    result["providerBillingReconciliationStatus"] = row[
        "provider_billing_reconciliation_status"
    ]

    result["completeTrialCostCount"] = nonnegative_integer(
        row["complete_trial_cost_count"],
        f"{arm_id}.complete_trial_cost_count",
    )
    result["lowerBoundTrialCount"] = nonnegative_integer(
        row["lower_bound_trial_count"],
        f"{arm_id}.lower_bound_trial_count",
    )
    result["confirmedZeroCostTrialCount"] = (
        nonnegative_integer(
            row["confirmed_zero_cost_trial_count"],
            f"{arm_id}.confirmed_zero_cost_trial_count",
        )
    )
    result["currentUnresolvedTrialCount"] = (
        nonnegative_integer(
            matrix["unresolved_trial_count"],
            f"{arm_id}.unresolved_trial_count",
        )
    )

    result["selectedTrialCostAllocationStatus"] = row[
        "trial_cost_allocation_status"
    ]
    result["selectedOutcomeCostAllocationStatus"] = row[
        "outcome_cost_allocation_status"
    ]

    outcome_map = {
        "selectedCleanSuccessCostUsd":
            "clean_success_cost_usd",
        "selectedNormalFailureCostUsd":
            "normal_failure_cost_usd",
        "selectedExceptionFailureCostUsd":
            "exception_failure_cost_usd",
        "selectedExceptionWithSuccessSignalCostUsd":
            "exception_with_success_signal_cost_usd",
    }

    for output_field, input_field in outcome_map.items():
        result[output_field] = optional_decimal_text(
            optional_decimal(
                row[input_field],
                f"{arm_id}.{input_field}",
            )
        )

    result["knownAllocatedCostUsd"] = decimal_text(
        decimal(
            row["known_allocated_cost_usd"],
            f"{arm_id}.known_allocated_cost_usd",
        )
    )
    result["unallocatedKnownCostUsd"] = decimal_text(
        decimal(
            row["unallocated_known_cost_usd"],
            f"{arm_id}.unallocated_known_cost_usd",
        )
    )
    result["unquantifiedAdditionalCostStatus"] = row[
        "unquantified_additional_cost_status"
    ]
    result["currentEvidenceNote"] = row["evidence_note"]

    result["providerEvidenceAudit"] = {
        "provider": matrix["provider"],
        "auditScope": matrix["audit_scope"],
        "auditConclusion": matrix["audit_conclusion"],
        "trajectoryEvidenceStatus":
            matrix["trajectory_evidence_status"],
        "pricingProvenanceStatus":
            matrix["pricing_provenance_status"],
        "providerContextTemporalRelation":
            matrix["provider_context_temporal_relation"],
        "providerContextAllocationConfidence":
            matrix["provider_context_allocation_confidence"],
        "providerContextRateReconstructionUsd":
            optional_decimal_text(
                optional_decimal(
                    matrix[
                        "provider_context_rate_reconstruction_usd"
                    ],
                    f"{arm_id}.provider_context_rate_reconstruction_usd",
                )
            ),
        "providerContextRateReconstructionExcessVsSelectedUsd":
            optional_decimal_text(
                optional_decimal(
                    matrix[
                        "provider_context_rate_reconstruction_excess_vs_selected_usd"
                    ],
                    f"{arm_id}.provider_context_rate_reconstruction_excess_vs_selected_usd",
                )
            ),
        "providerContextAccountSpendUsd":
            optional_decimal_text(
                optional_decimal(
                    matrix["provider_context_account_spend_usd"],
                    f"{arm_id}.provider_context_account_spend_usd",
                )
            ),
        "providerContextOverheadUsd":
            optional_decimal_text(
                optional_decimal(
                    matrix["provider_context_overhead_usd"],
                    f"{arm_id}.provider_context_overhead_usd",
                )
            ),
        "selectedInputTokens":
            matrix["selected_input_tokens"] or None,
        "selectedCacheTokens":
            matrix["selected_cache_tokens"] or None,
        "selectedOutputTokens":
            matrix["selected_output_tokens"] or None,
    }

    result["selectedCostUsd"] = decimal_text(selected)
    result["selectedCostPerAttemptUsd"] = ratio(
        selected,
        int(result["trialCount"]),
        f"{arm_id}.trialCount",
    )
    result["selectedCostPerCleanSuccessUsd"] = ratio(
        selected,
        int(result["cleanSuccessCount"]),
        f"{arm_id}.cleanSuccessCount",
    )
    result["selectedCostPerAnySuccessUsd"] = ratio(
        selected,
        int(result["successCount"]),
        f"{arm_id}.successCount",
    )

    return result

def scope_relation(
    arms: list[dict[str, Any]],
) -> str:
    relations = {
        arm["selectedCostRelation"]
        for arm in arms
    }

    if relations == {"exact"}:
        return "exact"

    if (
        relations.issubset({"exact", "lower_bound"})
        and "lower_bound" in relations
    ):
        return "lower_bound"

    return "mixed_by_arm"


def selected_scope(
    scope: dict[str, Any],
    reconciliation_rows: dict[str, dict[str, str]],
    matrix_rows: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = deepcopy(scope)

    historical_scope_evidence = deepcopy(
        result["costEvidence"]
    )
    historical_outcomes = deepcopy(
        result["outcomeCostCoverage"]
    )

    arms = [
        selected_arm(
            arm,
            reconciliation_rows,
            matrix_rows,
        )
        for arm in result["arms"]
    ]

    if len({arm["armId"] for arm in arms}) != len(arms):
        fail(f"{scope['scopeId']} contains duplicate arms")

    scope_arm_ids = {
        arm["armId"]
        for arm in arms
    }

    expected_scope_ids = (
        EXPECTED_RECONCILED_ARM_IDS
        - {"router-kimi-k3"}
        if scope["scopeId"] == "phase3-core"
        else EXPECTED_RECONCILED_ARM_IDS
    )

    if scope_arm_ids != expected_scope_ids:
        fail(
            f"{scope['scopeId']} current reconciled membership changed"
        )

    selected_arm_sum = sum(
        (
            decimal(
                arm["selectedCostUsd"],
                f"{arm['armId']}.selectedCostUsd",
            )
            for arm in arms
        ),
        Decimal("0"),
    )

    historical_arm_sum = sum(
        (
            decimal(
                arm["historicalReviewedCostUsd"],
                f"{arm['armId']}.historicalReviewedCostUsd",
            )
            for arm in arms
        ),
        Decimal("0"),
    )

    historical_source_scope = historical_scope_cost(scope)

    current_delta = sum(
        (
            decimal(
                arm["selectedCostUsd"],
                f"{arm['armId']}.selectedCostUsd",
            )
            - decimal(
                arm["historicalReviewedCostUsd"],
                f"{arm['armId']}.historicalReviewedCostUsd",
            )
            for arm in arms
        ),
        Decimal("0"),
    )

    source_scope_transformed = (
        historical_source_scope + current_delta
    )
    source_scope_residual = (
        source_scope_transformed - selected_arm_sum
    )

    expected_total = EXPECTED_SCOPE_TOTALS[
        scope["scopeId"]
    ]
    expected_source_total = (
        EXPECTED_SOURCE_SCOPE_TRANSFORMED_TOTALS[
            scope["scopeId"]
        ]
    )

    if selected_arm_sum != expected_total:
        fail(
            f"{scope['scopeId']} selected arm sum changed: "
            f"{selected_arm_sum}"
        )

    if source_scope_transformed != expected_source_total:
        fail(
            f"{scope['scopeId']} transformed source-scope total "
            f"changed: {source_scope_transformed}"
        )

    expected_residual = (
        Decimal("0")
        if scope["scopeId"] == "phase3-core"
        else Decimal("-0.0000000000001")
    )

    if source_scope_residual != expected_residual:
        fail(
            f"{scope['scopeId']} source-scope residual changed: "
            f"{source_scope_residual}"
        )

    reconciled_cost = selected_arm_sum

    if (
        reconciled_cost
        != EXPECTED_SCOPE_RECONCILED_COSTS[
            scope["scopeId"]
        ]
    ):
        fail(
            f"{scope['scopeId']} reconciled subtotal changed"
        )

    exact_provider_arms = [
        arm
        for arm in arms
        if arm["providerBilledCostUsd"] is not None
    ]

    exact_provider_cost = sum(
        (
            decimal(
                arm["providerBilledCostUsd"],
                f"{arm['armId']}.providerBilledCostUsd",
            )
            for arm in exact_provider_arms
        ),
        Decimal("0"),
    )

    if exact_provider_cost != EXPECTED_EXACT_PROVIDER_BILLED_COST:
        fail(
            f"{scope['scopeId']} exact provider subtotal changed"
        )

    relation_counts = Counter(
        arm["selectedCostRelation"]
        for arm in arms
    )

    expected_counts = EXPECTED_SCOPE_RELATION_COUNTS[
        scope["scopeId"]
    ]

    for relation, expected_count in expected_counts.items():
        if relation_counts[relation] != expected_count:
            fail(
                f"{scope['scopeId']} relation count changed: "
                f"{relation}"
            )

    unquantified_arms = sorted(
        arm["armId"]
        for arm in arms
        if arm["unquantifiedAdditionalCostStatus"]
        not in NO_UNQUANTIFIED_COST_STATUSES
    )

    if (
        set(unquantified_arms)
        != EXPECTED_UNQUANTIFIED_ADDITIONAL_COST_ARM_IDS
    ):
        fail(
            f"{scope['scopeId']} unquantified-cost membership changed"
        )

    result["arms"] = arms
    result["historicalCostEvidence"] = historical_scope_evidence
    result["historicalOutcomeCostCoverage"] = historical_outcomes

    result.pop("costEvidence", None)
    result.pop("outcomeCostCoverage", None)

    result["selectedCostEvidence"] = {
        "selectedCostUsd": decimal_text(selected_arm_sum),
        "selectedCostRelation": scope_relation(arms),
        "selectedCostBasis": "mixed_best_available_arm_evidence",
        "historicalReviewedArmSumCostUsd": decimal_text(
            historical_arm_sum
        ),
        "historicalSourceScopeCostUsd": decimal_text(
            historical_source_scope
        ),
        "sourceScopeTransformedSelectedCostUsd": decimal_text(
            source_scope_transformed
        ),
        "sourceScopeReconciliationAdjustmentUsd": decimal_text(
            source_scope_residual
        ),
        "currentReconciledArmIds": sorted(scope_arm_ids),
        "currentReconciledArmCount": len(arms),
        "currentReconciledCostUsd": decimal_text(
            reconciled_cost
        ),
        "exactProviderBilledArmIds": sorted(
            arm["armId"]
            for arm in exact_provider_arms
        ),
        "exactProviderBilledArmCount": len(
            exact_provider_arms
        ),
        "exactProviderBilledCostUsd": decimal_text(
            exact_provider_cost
        ),
        "currentReconciliationCoverageStatus":
            "complete_by_arm",
        "selectedCostRelationCounts": {
            "exact": relation_counts["exact"],
            "estimate": relation_counts["estimate"],
            "lowerBound": relation_counts["lower_bound"],
            "historicalFallback":
                relation_counts["historical_fallback"],
        },
        "unquantifiedAdditionalCostArmIds":
            unquantified_arms,
        "unquantifiedAdditionalCostArmCount":
            len(unquantified_arms),
        "trialAllocationStatus": "mixed_by_arm",
        "outcomeAllocationStatus": "mixed_by_arm",
        "note": (
            "selectedCostUsd is the arithmetic sum of all current "
            "reconciled arm values. Every arm in this scope has a "
            "2026-08-25 reconciliation row, so there are no historical "
            "fallback costs. The scope still mixes exact values, "
            "estimates, one partial estimate with unresolved usage, "
            "and retained-usage lower bounds. It is therefore neither "
            "an exact provider bill nor a global scope lower bound."
        ),
    }

    return result

def generate_snapshot(
    historical_path: Path,
    arm_reconciliation_path: Path,
    provider_matrix_path: Path,
    anthropic_exception_path: Path,
) -> dict[str, Any]:
    expected_inputs = (
        (
            historical_path,
            EXPECTED_HISTORICAL_SHA256,
        ),
        (
            arm_reconciliation_path,
            EXPECTED_ARM_RECONCILIATION_SHA256,
        ),
        (
            provider_matrix_path,
            EXPECTED_PROVIDER_MATRIX_SHA256,
        ),
        (
            anthropic_exception_path,
            EXPECTED_ANTHROPIC_EXCEPTION_SHA256,
        ),
    )

    for input_path, expected_hash in expected_inputs:
        actual = sha256(input_path)
        if actual != expected_hash:
            fail(
                f"input hash changed for {input_path}: "
                f"expected {expected_hash}, got {actual}"
            )

    historical = read_historical(historical_path)

    exception_totals, exception_counts = (
        read_exception_lower_bounds(
            anthropic_exception_path
        )
    )

    reconciliation_rows = read_arm_reconciliation(
        arm_reconciliation_path,
        historical,
        exception_totals,
        exception_counts,
    )

    matrix_rows = read_provider_matrix(
        provider_matrix_path,
        reconciliation_rows,
    )

    scopes = {
        scope_id: selected_scope(
            scope,
            reconciliation_rows,
            matrix_rows,
        )
        for scope_id, scope
        in historical["scopes"].items()
    }

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "generator": {
            "name":
                "scripts/"
                "generate_phase3_current_reviewed_comparison_v4.py",
            "version": GENERATOR_VERSION,
        },
        "reviewedAt": REVIEWED_AT,
        "historicalReviewedAt": historical["reviewedAt"],
        "inputs": [
            {
                "path": display_path(historical_path),
                "role":
                    "frozen_historical_reviewed_comparison",
                "sha256": sha256(historical_path),
            },
            {
                "path":
                    display_path(arm_reconciliation_path),
                "role":
                    "sanitized_current_arm_cost_reconciliation",
                "sha256": sha256(arm_reconciliation_path),
            },
            {
                "path":
                    display_path(provider_matrix_path),
                "role":
                    "sanitized_provider_cost_evidence_matrix",
                "sha256": sha256(provider_matrix_path),
            },
            {
                "path":
                    display_path(anthropic_exception_path),
                "role":
                    "supporting_anthropic_exception_lower_bound_evidence",
                "sha256": sha256(anthropic_exception_path),
            },
        ],
        "scopes": scopes,
    }

    serialized = json.dumps(
        result,
        sort_keys=True,
    )

    prohibited = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"\bproj_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\bkey_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\borg-[A-Za-z0-9_-]{8,}\b"),
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        re.compile(r"postgres(?:ql)?://", re.I),
        re.compile(r"\br2://", re.I),
    )

    if any(
        pattern.search(serialized)
        for pattern in prohibited
    ):
        fail(
            "generated current reviewed V4 snapshot contains "
            "prohibited provider/infrastructure identifiers"
        )

    return result

def serialize_snapshot(
    snapshot: dict[str, Any],
) -> str:
    return (
        json.dumps(
            snapshot,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def serialize_dashboard_module(
    snapshot: dict[str, Any],
) -> str:
    compact = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    escaped = json.dumps(
        compact,
        ensure_ascii=False,
    )

    return (
        "// Generated by "
        "scripts/generate_phase3_current_reviewed_comparison_v4.py. "
        "Do not edit.\n"
        f"const currentReviewedSnapshot = JSON.parse({escaped});\n"
        "export default currentReviewedSnapshot;\n"
    )


def atomic_write(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary,
            path,
        )
    finally:
        temporary.unlink(
            missing_ok=True
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--historical",
        type=Path,
        default=HISTORICAL_PATH,
    )
    parser.add_argument(
        "--arm-reconciliation",
        type=Path,
        default=ARM_RECONCILIATION_PATH,
    )
    parser.add_argument(
        "--provider-matrix",
        type=Path,
        default=PROVIDER_MATRIX_PATH,
    )
    parser.add_argument(
        "--anthropic-exception-evidence",
        type=Path,
        default=ANTHROPIC_EXCEPTION_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=DASHBOARD_OUTPUT_PATH,
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    assert_output_safety(
        (
            args.historical,
            args.arm_reconciliation,
            args.provider_matrix,
            args.anthropic_exception_evidence,
        ),
        args.output,
        args.dashboard_output,
    )

    snapshot = generate_snapshot(
        args.historical,
        args.arm_reconciliation,
        args.provider_matrix,
        args.anthropic_exception_evidence,
    )

    atomic_write(
        args.output,
        serialize_snapshot(snapshot),
    )
    atomic_write(
        args.dashboard_output,
        serialize_dashboard_module(snapshot),
    )

    print(
        "wrote current reviewed v4 snapshot:",
        args.output,
    )
    print(
        "wrote current reviewed v4 dashboard module:",
        args.dashboard_output,
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
