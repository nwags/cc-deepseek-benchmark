#!/usr/bin/env python3
"""Generate the reviewed Phase 3 core/extended comparison snapshot.

This generator reads only retained, sanitized repository evidence. It never
reads raw provider exports and writes only the two explicitly selected,
logically equivalent reviewed-data outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "phase3-reviewed-comparison-v1"
GENERATOR_VERSION = "1.0.0"
REVIEWED_AT = "2026-08-05"
KIMI_ARM_ID = "router-kimi-k3"
CORE_COUNTS = (15, 900, 515)
EXTENDED_COUNTS = (16, 960, 562)
EXTENDED_QUALIFIED_COST = Decimal("1002.9841648891979")
OUTCOME_BUCKET_ORDER = (
    "clean_success",
    "exception_with_success_signal",
    "normal_failure",
    "exception_failure",
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class InputSpec:
    key: str
    role: str
    default_path: str


INPUT_SPECS = (
    InputSpec("phase1_combined", "phase1_quality_source", "results/phase1/combined.csv"),
    InputSpec("phase2_combined", "phase2_quality_source", "results/phase2/combined.csv"),
    InputSpec(
        "phase3_core_summary",
        "phase3_core_quality_and_cost_source",
        "results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv",
    ),
    InputSpec(
        "phase3_trial_cost_coverage",
        "phase3_core_trial_cost_source",
        "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
    ),
    InputSpec(
        "phase3_arm_cost_coverage",
        "phase3_core_arm_cost_source",
        "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv",
    ),
    InputSpec(
        "cross_phase_adjusted_comparison",
        "cross_phase_quality_and_cost_confirmation",
        "results/phase3/reporting/cross_phase_adjusted_comparison_20260714.tsv",
    ),
    InputSpec(
        "kimi_addendum",
        "kimi_quality_source",
        "docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md",
    ),
    InputSpec(
        "kimi_reconciliation_report",
        "kimi_cost_qualification_source",
        "docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md",
    ),
    InputSpec(
        "kimi_reconciliation_csv",
        "kimi_cost_arithmetic_source",
        "results/phase3/reporting/kimi_k3_provider_log_reconciliation_20260805.csv",
    ),
)


def _fail(message: str) -> None:
    raise ValueError(message)


def _decimal(value: str | None, label: str) -> Decimal:
    if value is None or value.strip() == "":
        _fail(f"missing decimal: {label}")
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid decimal for {label}") from exc
    if not parsed.is_finite():
        _fail(f"non-finite decimal for {label}")
    return parsed


def _integer(value: str | None, label: str) -> int:
    if value is None or not re.fullmatch(r"-?\d+", value.strip()):
        _fail(f"invalid integer for {label}")
    return int(value)


def _optional_decimal_string(value: str | None, label: str) -> str | None:
    if value is None or value.strip() == "":
        return None
    return str(_decimal(value, label))


def _decimal_string(value: Decimal) -> str:
    """Serialize a finite Decimal without binary conversion or exponent notation."""
    if not value.is_finite():
        _fail("cannot serialize a non-finite decimal")
    return format(value, "f")


def _optional_float(value: str | None, label: str) -> float | None:
    if value is None or value.strip() == "":
        return None
    parsed = float(_decimal(value, label))
    if not math.isfinite(parsed):
        _fail(f"non-finite float for {label}")
    return parsed


def _read_table(path: Path, delimiter: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                _fail(f"missing header: {path}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"unable to read table: {path}") from exc
    if not rows:
        _fail(f"empty table: {path}")
    return rows


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"unable to read text input: {path}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"unable to hash input: {path}") from exc
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _assert_columns(rows: list[dict[str, str]], required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        _fail(f"{label} missing columns: {', '.join(missing)}")


def _parse_cost_source_counts(value: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in value.split(","):
        name, separator, count = item.partition(":")
        if not separator or not name or not count.isdigit():
            _fail("malformed cost_source_counts")
        result[name] = int(count)
    return result


def _parse_outcome_counts(value: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in value.split(","):
        name, separator, count = item.partition(":")
        if not separator or not name or not count.isdigit():
            _fail("malformed outcome_cost_counts")
        result[name] = int(count)
    return result


def _csv_metric(rows: list[dict[str, str]], name: str) -> str:
    matches = [row.get("Value", "") for row in rows if row.get("Metric") == name]
    if len(matches) != 1:
        _fail(f"expected one Kimi reconciliation metric: {name}")
    return matches[0]


def _assert_markdown_fact(text: str, pattern: str, label: str) -> None:
    if not re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
        _fail(f"missing required evidence in {label}")


def _pass_rate(successes: int, trials: int) -> float:
    if trials <= 0 or successes < 0 or successes > trials:
        _fail("invalid success/trial counts")
    return successes / trials


def _core_arm(
    summary: dict[str, str],
    coverage: dict[str, str],
    cross_phase: dict[str, str],
    source_paths: list[str],
) -> dict[str, Any]:
    arm_id = summary["arm_id"]
    if coverage["arm_id"] != arm_id or cross_phase["arm_id"] != arm_id:
        _fail(f"core arm join mismatch: {arm_id}")

    trials = _integer(summary["trial_count"], f"{arm_id}.trial_count")
    successes = _integer(summary["success_count"], f"{arm_id}.success_count")
    clean_successes = _integer(coverage["clean_success_count"], f"{arm_id}.clean_success_count")
    exception_successes = _integer(
        coverage["exception_success_signal_count"], f"{arm_id}.exception_success_signal_count"
    )
    failures = _integer(
        coverage["failure_or_incomplete_count"], f"{arm_id}.failure_or_incomplete_count"
    )
    if successes != clean_successes + exception_successes or trials != successes + failures:
        _fail(f"inconsistent outcome counts for {arm_id}")
    if (
        _integer(coverage["trial_count"], f"coverage {arm_id}.trial_count") != trials
        or _integer(coverage["success_count"], f"coverage {arm_id}.success_count") != successes
        or _integer(cross_phase["trial_count"], f"cross-phase {arm_id}.trial_count") != trials
        or _integer(cross_phase["success_count"], f"cross-phase {arm_id}.success_count") != successes
        or _integer(cross_phase["clean_success_count"], f"cross-phase {arm_id}.clean_success_count")
        != clean_successes
    ):
        _fail(f"core outcome totals disagree for {arm_id}")

    for field in ("backend_model", "provider"):
        if summary[field] != coverage[field] or summary[field] != cross_phase[field]:
            _fail(f"core {field} mismatch for {arm_id}")

    for summary_field, coverage_field in (
        ("recorded_cost_usd", "recorded_cost_usd"),
        ("adjusted_cost_usd", "adjusted_cost_usd"),
    ):
        if _decimal(summary[summary_field], f"summary {arm_id}.{summary_field}") != _decimal(
            coverage[coverage_field], f"coverage {arm_id}.{coverage_field}"
        ):
            _fail(f"core cost mismatch for {arm_id}.{summary_field}")
        if _decimal(summary[summary_field], f"summary {arm_id}.{summary_field}") != _decimal(
            cross_phase[summary_field], f"cross-phase {arm_id}.{summary_field}"
        ):
            _fail(f"core cross-phase cost mismatch for {arm_id}.{summary_field}")
    derived_gap = _decimal(summary["adjusted_cost_usd"], f"{arm_id}.adjusted_cost_usd") - _decimal(
        summary["recorded_cost_usd"], f"{arm_id}.recorded_cost_usd"
    )
    if abs(derived_gap - _decimal(summary["known_accounting_gap_usd"], f"{arm_id}.source_gap")) > Decimal("1e-12"):
        _fail(f"core source accounting gap mismatch for {arm_id}")

    cost_sources = _parse_cost_source_counts(coverage["cost_source_counts"])
    outcomes = _parse_outcome_counts(coverage["outcome_cost_counts"])
    if sum(cost_sources.values()) != trials or sum(outcomes.values()) != trials:
        _fail(f"coverage count mismatch for {arm_id}")

    return {
        "armId": arm_id,
        "backendModel": summary["backend_model"],
        "provider": summary["provider"],
        "routingPath": cross_phase["routing_path"],
        "trialCount": trials,
        "successCount": successes,
        "cleanSuccessCount": clean_successes,
        "exceptionSuccessSignalCount": exception_successes,
        "failureOrIncompleteCount": failures,
        "passRate": _pass_rate(successes, trials),
        "recordedCostUsd": str(_decimal(summary["recorded_cost_usd"], f"{arm_id}.recorded_cost_usd")),
        "adjustedKnownCostUsd": str(_decimal(summary["adjusted_cost_usd"], f"{arm_id}.adjusted_cost_usd")),
        "qualifiedRetainedRateCostUsd": None,
        "accountingGapUsd": _decimal_string(
            _decimal(summary["adjusted_cost_usd"], f"{arm_id}.adjusted_cost_usd")
            - _decimal(summary["recorded_cost_usd"], f"{arm_id}.recorded_cost_usd")
        ),
        "adjustedCostPerCleanSuccessUsd": _optional_decimal_string(
            coverage["adjusted_cost_per_clean_success"], f"{arm_id}.adjusted_cost_per_clean_success"
        ),
        "adjustedCostPerAnySuccessUsd": _optional_decimal_string(
            coverage["adjusted_cost_per_any_success"], f"{arm_id}.adjusted_cost_per_any_success"
        ),
        "adjustedCleanSuccessCostUsd": _optional_decimal_string(
            coverage["adjusted_clean_success_cost_usd"], f"{arm_id}.adjusted_clean_success_cost_usd"
        ),
        "adjustedExceptionSuccessSignalCostUsd": _optional_decimal_string(
            coverage["adjusted_exception_success_signal_cost_usd"],
            f"{arm_id}.adjusted_exception_success_signal_cost_usd",
        ),
        "adjustedFailureOrIncompleteCostUsd": _optional_decimal_string(
            coverage["adjusted_failure_or_incomplete_cost_usd"],
            f"{arm_id}.adjusted_failure_or_incomplete_cost_usd",
        ),
        "failureOrIncompleteSpendShare": _optional_float(
            summary["failure_incomplete_spend_share"], f"{arm_id}.failure_incomplete_spend_share"
        ),
        "nonproductiveOrUncleanSpendShare": _optional_float(
            coverage["nonproductive_or_unclean_spend_share"],
            f"{arm_id}.nonproductive_or_unclean_spend_share",
        ),
        "medianWallClockSeconds": _optional_float(
            cross_phase["median_wall_clock_seconds"], f"{arm_id}.median_wall_clock_seconds"
        ),
        "missingRecordedCostCount": _integer(coverage["missing_cost_count"], f"{arm_id}.missing_cost_count"),
        "unresolvedCostCount": _integer(
            coverage["unresolved_missing_cost_count"], f"{arm_id}.unresolved_missing_cost_count"
        ),
        "costSources": sorted(cost_sources),
        "costConfidence": summary["cost_confidence"],
        "costBasis": "adjusted_known_cost",
        "pricingProvenanceStatus": "historical_reviewed_layer",
        "armRunAllocationConfidence": "reviewed_core_layer",
        "trialAllocationStatus": "available_for_reviewed_layer",
        "billingReconciliationStatus": "not_invoice_level",
        "outcomeCostAllocationStatus": "available",
        "sourcePaths": source_paths,
    }


def _scope_cost(
    *,
    recorded: Decimal,
    adjusted_known: Decimal | None,
    qualified: Decimal | None,
    gap: Decimal,
    basis: str,
    label: str,
    pricing_status: str,
    allocation_confidence: str,
    trial_status: str,
    billing_status: str,
    outcome_status: str,
    missing_recorded_count: int,
    unresolved_count: int,
    adjusted_clean_success: Decimal | None,
    adjusted_exception_success: Decimal | None,
    adjusted_failure: Decimal | None,
    failure_share: float | None,
    nonproductive_share: float | None,
    adjusted_per_clean_success: Decimal | None,
    adjusted_per_any_success: Decimal | None,
    cost_sources: list[str],
    cost_confidence: str,
    source_paths: list[str],
) -> dict[str, Any]:
    return {
        "recordedCostUsd": str(recorded),
        "adjustedKnownCostUsd": str(adjusted_known) if adjusted_known is not None else None,
        "qualifiedAdjustedCostEstimateUsd": str(qualified) if qualified is not None else None,
        "accountingGapUsd": str(gap),
        "costBasis": basis,
        "costLabel": label,
        "pricingProvenanceStatus": pricing_status,
        "armRunAllocationConfidence": allocation_confidence,
        "trialAllocationStatus": trial_status,
        "billingReconciliationStatus": billing_status,
        "outcomeCostAllocationStatus": outcome_status,
        "missingRecordedCostCount": missing_recorded_count,
        "unresolvedCostCount": unresolved_count,
        "adjustedCleanSuccessCostUsd": (
            str(adjusted_clean_success) if adjusted_clean_success is not None else None
        ),
        "adjustedExceptionSuccessSignalCostUsd": (
            str(adjusted_exception_success) if adjusted_exception_success is not None else None
        ),
        "adjustedFailureOrIncompleteCostUsd": str(adjusted_failure) if adjusted_failure is not None else None,
        "failureOrIncompleteSpendShare": failure_share,
        "nonproductiveOrUncleanSpendShare": nonproductive_share,
        "adjustedCostPerCleanSuccessUsd": (
            str(adjusted_per_clean_success) if adjusted_per_clean_success is not None else None
        ),
        "adjustedCostPerAnySuccessUsd": (
            str(adjusted_per_any_success) if adjusted_per_any_success is not None else None
        ),
        "costSources": cost_sources,
        "costConfidence": cost_confidence,
        "sourcePaths": source_paths,
    }


def _outcome_cost_coverage(
    trial_rows: list[dict[str, str]],
    *,
    core_recorded: Decimal,
    core_adjusted: Decimal,
) -> dict[str, Any]:
    aggregates: dict[str, dict[str, Any]] = {}
    for row in trial_rows:
        bucket = row["outcome_bucket"].strip()
        if not bucket:
            _fail(f"trial {row['trial_id']} has no outcome bucket")
        aggregate = aggregates.setdefault(
            bucket,
            {
                "trialCount": 0,
                "recorded": Decimal(0),
                "adjusted": Decimal(0),
                "missingRecordedCostCount": 0,
                "unresolvedAdjustedCostCount": 0,
            },
        )
        aggregate["trialCount"] += 1
        recorded_value = row["recorded_cost_usd"].strip()
        adjusted_value = row["adjusted_cost_usd"].strip()
        if recorded_value:
            aggregate["recorded"] += _decimal(recorded_value, f"trial {row['trial_id']}.recorded_cost_usd")
        else:
            aggregate["missingRecordedCostCount"] += 1
        if adjusted_value:
            aggregate["adjusted"] += _decimal(adjusted_value, f"trial {row['trial_id']}.adjusted_cost_usd")
        else:
            aggregate["unresolvedAdjustedCostCount"] += 1

    ordered_buckets = [bucket for bucket in OUTCOME_BUCKET_ORDER if bucket in aggregates]
    ordered_buckets.extend(sorted(set(aggregates) - set(OUTCOME_BUCKET_ORDER)))
    if not ordered_buckets:
        _fail("Phase 3 core has no outcome buckets")

    source_adjusted_total = sum((aggregates[bucket]["adjusted"] for bucket in ordered_buckets), Decimal(0))
    adjustment = core_adjusted - source_adjusted_total
    # Historical trial rows contain decimal text emitted through float-backed
    # aggregation and differ from the reviewed arm total by $0.000000000007.
    # Preserve every source bucket exactly and disclose the residual only at
    # scope level; no outcome bucket is evidence for this serialization delta.
    rows: list[dict[str, Any]] = []
    for bucket in ordered_buckets:
        aggregate = aggregates[bucket]
        adjusted = aggregate["adjusted"]
        recorded = aggregate["recorded"]
        rows.append(
            {
                "outcomeBucket": bucket,
                "trialCount": aggregate["trialCount"],
                "recordedCostUsd": _decimal_string(recorded),
                "sourceAdjustedKnownCostUsd": _decimal_string(adjusted),
                "sourceAccountingGapUsd": _decimal_string(adjusted - recorded),
                "missingRecordedCostCount": aggregate["missingRecordedCostCount"],
                "unresolvedAdjustedCostCount": aggregate["unresolvedAdjustedCostCount"],
            }
        )

    if sum(row["trialCount"] for row in rows) != CORE_COUNTS[1]:
        _fail("outcome-cost trial counts do not match the Phase 3 core")
    if sum((Decimal(row["recordedCostUsd"]) for row in rows), Decimal(0)) != core_recorded:
        _fail("outcome recorded-cost rows do not match the Phase 3 core")
    if sum((Decimal(row["sourceAdjustedKnownCostUsd"]) for row in rows), Decimal(0)) != source_adjusted_total:
        _fail("source outcome adjusted-cost rows do not match their source total")
    if sum((Decimal(row["sourceAccountingGapUsd"]) for row in rows), Decimal(0)) != source_adjusted_total - core_recorded:
        _fail("source outcome accounting-gap rows do not match their source total")
    if source_adjusted_total + adjustment != core_adjusted:
        _fail("source outcome total and reviewed scope adjustment do not reconcile")

    return {
        "status": "available",
        "coveredTrialCount": CORE_COUNTS[1],
        "excludedTrialCount": 0,
        "excludedArmIds": [],
        "sourceAdjustedKnownCostTotalUsd": _decimal_string(source_adjusted_total),
        "reviewedAdjustedKnownCostTotalUsd": _decimal_string(core_adjusted),
        "reviewedScopeReconciliationAdjustmentUsd": _decimal_string(adjustment),
        "rows": rows,
    }


def generate_snapshot(input_paths: dict[str, Path]) -> dict[str, Any]:
    expected_keys = {spec.key for spec in INPUT_SPECS}
    if set(input_paths) != expected_keys:
        _fail("input path keys do not match the required input set")
    resolved = {key: Path(path).resolve() for key, path in input_paths.items()}
    for key, path in resolved.items():
        if not path.is_file():
            _fail(f"required input missing: {key}")

    phase1 = _read_table(resolved["phase1_combined"], ",")
    phase2 = _read_table(resolved["phase2_combined"], ",")
    summary = _read_table(resolved["phase3_core_summary"], "\t")
    trial_costs = _read_table(resolved["phase3_trial_cost_coverage"], "\t")
    arm_costs = _read_table(resolved["phase3_arm_cost_coverage"], "\t")
    cross_phase = _read_table(resolved["cross_phase_adjusted_comparison"], "\t")
    addendum = _read_text(resolved["kimi_addendum"])
    reconciliation_report = _read_text(resolved["kimi_reconciliation_report"])
    reconciliation_csv = _read_table(resolved["kimi_reconciliation_csv"], ",")

    _assert_columns(summary, (
        "arm_id", "backend_model", "provider", "success_count", "trial_count",
        "recorded_cost_usd", "adjusted_cost_usd", "known_accounting_gap_usd",
        "failure_incomplete_spend_share", "cost_confidence",
    ), "phase3 summary")
    _assert_columns(arm_costs, (
        "arm_id", "backend_model", "provider", "trial_count", "success_count",
        "clean_success_count", "exception_success_signal_count", "failure_or_incomplete_count",
        "recorded_cost_usd", "missing_cost_count", "unresolved_missing_cost_count",
        "adjusted_cost_usd", "adjusted_clean_success_cost_usd",
        "adjusted_exception_success_signal_cost_usd", "adjusted_failure_or_incomplete_cost_usd",
        "nonproductive_or_unclean_spend_share", "adjusted_cost_per_clean_success",
        "adjusted_cost_per_any_success", "cost_source_counts", "outcome_cost_counts",
    ), "phase3 arm cost coverage")
    _assert_columns(cross_phase, (
        "phase", "arm_id", "backend_model", "provider", "routing_path",
        "success_count", "clean_success_count", "trial_count", "recorded_cost_usd",
        "adjusted_cost_usd", "median_wall_clock_seconds",
    ), "cross-phase comparison")
    _assert_columns(
        trial_costs,
        ("arm_id", "trial_id", "reward", "outcome_bucket", "recorded_cost_usd", "adjusted_cost_usd"),
        "trial costs",
    )
    _assert_columns(reconciliation_csv, ("Metric", "Value", "Unit"), "Kimi reconciliation")

    def combined_counts(rows: list[dict[str, str]], label: str) -> tuple[int, int, int]:
        _assert_columns(rows, ("arm_dir", "reward", "success"), label)
        arms = {row["arm_dir"] for row in rows}
        valid_success_values = {"true", "false"}
        normalized_successes = [(row["success"] or "").strip().lower() for row in rows]
        if any(value not in valid_success_values for value in normalized_successes):
            _fail(f"invalid success marker in {label}")
        successes = sum(value == "true" for value in normalized_successes)
        return len(arms), len(rows), successes

    if combined_counts(phase1, "phase1") != (3, 180, 118):
        _fail("Phase 1 source counts differ from the reviewed cross-phase baseline")
    if combined_counts(phase2, "phase2") != (5, 300, 185):
        _fail("Phase 2 source counts differ from the reviewed cross-phase baseline")

    core_cross = [row for row in cross_phase if row["phase"] == "phase3"]
    phase1_cross = [row for row in cross_phase if row["phase"] == "phase1"]
    phase2_cross = [row for row in cross_phase if row["phase"] == "phase2"]
    if (len(phase1_cross), sum(_integer(row["trial_count"], "phase1 cross trials") for row in phase1_cross),
        sum(_integer(row["success_count"], "phase1 cross successes") for row in phase1_cross)) != (3, 180, 118):
        _fail("Phase 1 combined and cross-phase sources disagree")
    if (len(phase2_cross), sum(_integer(row["trial_count"], "phase2 cross trials") for row in phase2_cross),
        sum(_integer(row["success_count"], "phase2 cross successes") for row in phase2_cross)) != (5, 300, 185):
        _fail("Phase 2 combined and cross-phase sources disagree")

    summary_by_arm = {row["arm_id"]: row for row in summary}
    cost_by_arm = {row["arm_id"]: row for row in arm_costs}
    cross_by_arm = {row["arm_id"]: row for row in core_cross}
    if len(summary_by_arm) != len(summary) or len(cost_by_arm) != len(arm_costs) or len(cross_by_arm) != len(core_cross):
        _fail("duplicate Phase 3 core arm ID")
    if set(summary_by_arm) != set(cost_by_arm) or set(summary_by_arm) != set(cross_by_arm):
        _fail("Phase 3 core arm sources disagree")
    if KIMI_ARM_ID in summary_by_arm:
        _fail("router-kimi-k3 must not appear in Phase 3 core")

    core_source_paths = [
        _display_path(resolved["phase3_core_summary"]),
        _display_path(resolved["phase3_trial_cost_coverage"]),
        _display_path(resolved["phase3_arm_cost_coverage"]),
        _display_path(resolved["cross_phase_adjusted_comparison"]),
    ]
    core_arms = [
        _core_arm(summary_by_arm[arm_id], cost_by_arm[arm_id], cross_by_arm[arm_id], core_source_paths)
        for arm_id in sorted(summary_by_arm)
    ]
    core_counts = (
        len(core_arms),
        sum(arm["trialCount"] for arm in core_arms),
        sum(arm["successCount"] for arm in core_arms),
    )
    if core_counts != CORE_COUNTS:
        _fail(f"Phase 3 core counts mismatch: {core_counts}")
    if len(trial_costs) != CORE_COUNTS[1] or {row["arm_id"] for row in trial_costs} != set(summary_by_arm):
        _fail("Phase 3 trial cost coverage does not contain the reviewed 900-trial core")
    trial_reward_successes = sum(
        _decimal(row["reward"], f"trial {row['trial_id']}.reward") > 0
        for row in trial_costs
        if row["reward"].strip()
    )
    if trial_reward_successes != CORE_COUNTS[2]:
        _fail("Phase 3 trial cost coverage success total differs from the reviewed core")
    trial_adjusted_total = sum(
        (
            _decimal(row["adjusted_cost_usd"], f"trial {row['trial_id']}.adjusted_cost_usd")
            for row in trial_costs
            if row["adjusted_cost_usd"].strip()
        ),
        Decimal(0),
    )
    core_recorded = sum((Decimal(arm["recordedCostUsd"]) for arm in core_arms), Decimal(0))
    core_adjusted = sum((Decimal(arm["adjustedKnownCostUsd"]) for arm in core_arms), Decimal(0))
    summed_arm_gaps = sum((Decimal(arm["accountingGapUsd"]) for arm in core_arms), Decimal(0))
    core_gap = core_adjusted - core_recorded
    if abs(summed_arm_gaps - core_gap) > Decimal("1e-12"):
        _fail("Phase 3 arm accounting gaps disagree with adjusted minus recorded cost")
    if abs(trial_adjusted_total - core_adjusted) > Decimal("1e-9"):
        _fail("Phase 3 trial and arm adjusted-cost totals disagree")

    _assert_markdown_fact(addendum, r"- Trials:\s*60\b", "Kimi addendum")
    _assert_markdown_fact(addendum, r"- Successes:\s*47\b", "Kimi addendum")
    _assert_markdown_fact(addendum, r"\| Clean success \| 44 \|", "Kimi addendum")
    _assert_markdown_fact(addendum, r"\| Exception with success signal \| 3 \|", "Kimi addendum")
    _assert_markdown_fact(addendum, r"\| Clean failure \| 5 \|", "Kimi addendum")
    _assert_markdown_fact(addendum, r"\| Exception failure \| 8 \|", "Kimi addendum")
    _assert_markdown_fact(addendum, r"Missing observed trial costs \| 10", "Kimi addendum")
    for pattern in (
        r"pricing-source provenance remains incomplete",
        r"Arm-run/provider-log allocation \| Low confidence",
        r"Trial-level allocation \| Unresolved",
        r"not invoice-level reconciliation",
    ):
        _assert_markdown_fact(reconciliation_report, pattern, "Kimi reconciliation report")

    requests = _integer(_csv_metric(reconciliation_csv, "Requests"), "Kimi requests")
    duplicate_requests = _integer(_csv_metric(reconciliation_csv, "Duplicate request IDs"), "duplicate Kimi requests")
    recorded = _decimal(_csv_metric(reconciliation_csv, "Recorded trial cost"), "Kimi recorded cost")
    retained_rate = _decimal(
        _csv_metric(reconciliation_csv, "Provider-log retained-rate reconstruction"), "Kimi retained-rate cost"
    )
    gap = _decimal(
        _csv_metric(reconciliation_csv, "Known accounting gap relative to provider-log retained-rate reconstruction"),
        "Kimi accounting gap",
    )
    extended_cost = _decimal(
        _csv_metric(reconciliation_csv, "Phase 3 extended qualified adjusted-cost estimate (core + Kimi K3)"),
        "extended qualified cost",
    )
    if requests != 1273 or duplicate_requests != 0:
        _fail("unexpected Kimi provider-log request counts")
    if (recorded, retained_rate, gap) != (Decimal("25.207213"), Decimal("30.8143194"), Decimal("5.607106")):
        _fail("unexpected Kimi cost evidence")
    exact_gap = retained_rate - recorded
    if exact_gap != Decimal("5.6071064") or abs(gap - exact_gap) > Decimal("0.0000005"):
        _fail("Kimi accounting gap arithmetic mismatch")
    if extended_cost != EXTENDED_QUALIFIED_COST or abs((core_adjusted + retained_rate) - extended_cost) > Decimal("1e-12"):
        _fail("extended qualified adjusted-cost estimate mismatch")
    if (
        _integer(_csv_metric(reconciliation_csv, "Phase 3 extended arms"), "extended arms"),
        _integer(_csv_metric(reconciliation_csv, "Phase 3 extended trials"), "extended trials"),
        _integer(_csv_metric(reconciliation_csv, "Phase 3 extended successes"), "extended successes"),
    ) != EXTENDED_COUNTS:
        _fail("Kimi reconciliation extended counts mismatch")

    kimi_source_paths = [
        _display_path(resolved["kimi_addendum"]),
        _display_path(resolved["kimi_reconciliation_report"]),
        _display_path(resolved["kimi_reconciliation_csv"]),
    ]
    kimi_arm = {
        "armId": KIMI_ARM_ID,
        "backendModel": "kimi-k3",
        "provider": "moonshot",
        "routingPath": "phase3_router_addendum",
        "trialCount": 60,
        "successCount": 47,
        "cleanSuccessCount": 44,
        "exceptionSuccessSignalCount": 3,
        "failureOrIncompleteCount": 13,
        "passRate": _pass_rate(47, 60),
        "recordedCostUsd": str(recorded),
        "adjustedKnownCostUsd": None,
        "qualifiedRetainedRateCostUsd": str(retained_rate),
        "accountingGapUsd": str(exact_gap),
        "adjustedCostPerCleanSuccessUsd": None,
        "adjustedCostPerAnySuccessUsd": None,
        "adjustedCleanSuccessCostUsd": None,
        "adjustedExceptionSuccessSignalCostUsd": None,
        "adjustedFailureOrIncompleteCostUsd": None,
        "failureOrIncompleteSpendShare": None,
        "nonproductiveOrUncleanSpendShare": None,
        "medianWallClockSeconds": None,
        "missingRecordedCostCount": 10,
        "unresolvedCostCount": 10,
        "costSources": ["provider_log_retained_rate_reconstruction", "recorded_trial_artifact"],
        "costConfidence": "low",
        "costBasis": "qualified_retained_rate_estimate",
        "pricingProvenanceStatus": "incomplete",
        "armRunAllocationConfidence": "low",
        "trialAllocationStatus": "unresolved",
        "billingReconciliationStatus": "not_invoice_level_or_provider_billed",
        "outcomeCostAllocationStatus": "unavailable",
        "sourcePaths": kimi_source_paths,
    }

    extended_arms = sorted([*core_arms, kimi_arm], key=lambda arm: arm["armId"])
    extended_counts = (
        len(extended_arms),
        sum(arm["trialCount"] for arm in extended_arms),
        sum(arm["successCount"] for arm in extended_arms),
    )
    if extended_counts != EXTENDED_COUNTS or not any(arm["armId"] == KIMI_ARM_ID for arm in extended_arms):
        _fail(f"Phase 3 extended counts or Kimi membership mismatch: {extended_counts}")

    inputs = [
        {
            "path": _display_path(resolved[spec.key]),
            "role": spec.role,
            "sha256": _sha256(resolved[spec.key]),
        }
        for spec in INPUT_SPECS
    ]
    inputs.sort(key=lambda item: item["path"])

    core_cost = _scope_cost(
        recorded=core_recorded,
        adjusted_known=core_adjusted,
        qualified=None,
        gap=core_gap,
        basis="adjusted_known_cost",
        label="Adjusted known cost",
        pricing_status="historical_reviewed_layer",
        allocation_confidence="mixed_by_arm",
        trial_status="available_for_reviewed_layer",
        billing_status="not_invoice_level",
        outcome_status="available",
        missing_recorded_count=sum(arm["missingRecordedCostCount"] for arm in core_arms),
        unresolved_count=sum(arm["unresolvedCostCount"] for arm in core_arms),
        adjusted_clean_success=sum(
            (Decimal(arm["adjustedCleanSuccessCostUsd"]) for arm in core_arms), Decimal(0)
        ),
        adjusted_exception_success=sum(
            (Decimal(arm["adjustedExceptionSuccessSignalCostUsd"]) for arm in core_arms), Decimal(0)
        ),
        adjusted_failure=sum(
            (Decimal(arm["adjustedFailureOrIncompleteCostUsd"]) for arm in core_arms), Decimal(0)
        ),
        failure_share=float(
            sum((Decimal(arm["adjustedFailureOrIncompleteCostUsd"]) for arm in core_arms), Decimal(0))
            / core_adjusted
        ),
        nonproductive_share=float(
            (core_adjusted - sum((Decimal(arm["adjustedCleanSuccessCostUsd"]) for arm in core_arms), Decimal(0)))
            / core_adjusted
        ),
        adjusted_per_clean_success=core_adjusted / Decimal(
            sum(arm["cleanSuccessCount"] for arm in core_arms)
        ),
        adjusted_per_any_success=core_adjusted / Decimal(CORE_COUNTS[2]),
        cost_sources=sorted({source for arm in core_arms for source in arm["costSources"]}),
        cost_confidence="mixed_by_arm",
        source_paths=core_source_paths,
    )
    extended_recorded = core_recorded + recorded
    extended_gap = EXTENDED_QUALIFIED_COST - extended_recorded
    extended_cost_evidence = _scope_cost(
        recorded=extended_recorded,
        adjusted_known=None,
        qualified=EXTENDED_QUALIFIED_COST,
        gap=extended_gap,
        basis="qualified_adjusted_cost_estimate",
        label="Phase 3 extended qualified adjusted-cost estimate",
        pricing_status="incomplete",
        allocation_confidence="low",
        trial_status="unresolved",
        billing_status="not_invoice_level_or_provider_billed",
        outcome_status="partial_core_only",
        missing_recorded_count=sum(arm["missingRecordedCostCount"] for arm in extended_arms),
        unresolved_count=sum(arm["unresolvedCostCount"] for arm in extended_arms),
        adjusted_clean_success=None,
        adjusted_exception_success=None,
        adjusted_failure=None,
        failure_share=None,
        nonproductive_share=None,
        adjusted_per_clean_success=None,
        adjusted_per_any_success=None,
        cost_sources=sorted({source for arm in extended_arms for source in arm["costSources"]}),
        cost_confidence="low",
        source_paths=[*core_source_paths, *kimi_source_paths],
    )
    core_outcome_cost_coverage = _outcome_cost_coverage(
        trial_costs,
        core_recorded=core_recorded,
        core_adjusted=core_adjusted,
    )
    extended_outcome_cost_coverage = {
        **core_outcome_cost_coverage,
        "status": "partial_core_only",
        "coveredTrialCount": CORE_COUNTS[1],
        "excludedTrialCount": 60,
        "excludedArmIds": [KIMI_ARM_ID],
        "rows": [dict(row) for row in core_outcome_cost_coverage["rows"]],
    }

    snapshot = {
        "generator": {
            "name": "scripts/generate_phase3_extended_reviewed_comparison.py",
            "version": GENERATOR_VERSION,
        },
        "inputs": inputs,
        "reviewedAt": REVIEWED_AT,
        "schemaVersion": SCHEMA_VERSION,
        "scopes": {
            "phase3-core": {
                "armCount": CORE_COUNTS[0],
                "arms": core_arms,
                "costEvidence": core_cost,
                "displayName": "Phase 3 core — reviewed historical snapshot",
                "outcomeCostCoverage": core_outcome_cost_coverage,
                "passRate": _pass_rate(CORE_COUNTS[2], CORE_COUNTS[1]),
                "presentationKind": "historical_reviewed_snapshot",
                "scopeId": "phase3-core",
                "snapshotDate": "2026-07-13",
                "successCount": CORE_COUNTS[2],
                "trialCount": CORE_COUNTS[1],
            },
            "phase3-extended": {
                "armCount": EXTENDED_COUNTS[0],
                "arms": extended_arms,
                "costEvidence": extended_cost_evidence,
                "displayName": "Phase 3 extended — current reviewed comparison",
                "outcomeCostCoverage": extended_outcome_cost_coverage,
                "passRate": _pass_rate(EXTENDED_COUNTS[2], EXTENDED_COUNTS[1]),
                "presentationKind": "current_reviewed_corpus",
                "scopeId": "phase3-extended",
                "snapshotDate": REVIEWED_AT,
                "successCount": EXTENDED_COUNTS[2],
                "trialCount": EXTENDED_COUNTS[1],
            },
        },
    }
    serialized = json.dumps(snapshot, sort_keys=True)
    prohibited = (
        r"request[_ -]?id\s*[:=]",
        r"project[_ -]?id\s*[:=]",
        r"api[_ -]?key[_ -]?id\s*[:=]",
        r"sk-[A-Za-z0-9_-]{12,}",
    )
    if any(re.search(pattern, serialized, flags=re.IGNORECASE) for pattern in prohibited):
        _fail("generated snapshot contains a prohibited raw provider identifier")
    return snapshot


def serialize_snapshot(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def serialize_dashboard_module(snapshot: dict[str, Any]) -> str:
    compact_json = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    escaped_json = json.dumps(compact_json, ensure_ascii=False)
    return (
        "// Generated by scripts/generate_phase3_extended_reviewed_comparison.py. Do not edit.\n"
        f"const reviewedSnapshot = JSON.parse({escaped_json});\n"
        "export default reviewedSnapshot;\n"
    )


def _assert_output_safety(
    input_paths: dict[str, Path],
    output_path: Path,
    dashboard_output_path: Path,
) -> tuple[Path, Path]:
    resolved_outputs = (output_path.resolve(), dashboard_output_path.resolve())
    resolved_inputs = {Path(path).resolve() for path in input_paths.values()}
    if any(output in resolved_inputs for output in resolved_outputs):
        _fail("output path must not equal an input path")
    if resolved_outputs[0] == resolved_outputs[1]:
        _fail("generated output paths must be distinct")
    for output in (output_path, dashboard_output_path):
        if output.exists():
            for input_path in input_paths.values():
                try:
                    if output.samefile(input_path):
                        _fail("output path must not alias an input path")
                except FileNotFoundError:
                    continue
    if output_path.exists() and dashboard_output_path.exists():
        try:
            if output_path.samefile(dashboard_output_path):
                _fail("generated output paths must not alias each other")
        except FileNotFoundError:
            pass
    return resolved_outputs


def _atomic_write_text(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_snapshot(
    input_paths: dict[str, Path],
    output_path: Path,
    dashboard_output_path: Path,
) -> dict[str, Any]:
    resolved_output, resolved_dashboard_output = _assert_output_safety(
        input_paths,
        output_path,
        dashboard_output_path,
    )
    snapshot = generate_snapshot(input_paths)
    _atomic_write_text(resolved_output, serialize_snapshot(snapshot))
    _atomic_write_text(resolved_dashboard_output, serialize_dashboard_module(snapshot))
    return snapshot


def default_input_paths() -> dict[str, Path]:
    return {spec.key: REPO_ROOT / spec.default_path for spec in INPUT_SPECS}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for spec in INPUT_SPECS:
        parser.add_argument(
            f"--{spec.key.replace('_', '-')}",
            type=Path,
            default=REPO_ROOT / spec.default_path,
            help=f"Input for {spec.role} (default: {spec.default_path})",
        )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=REPO_ROOT / "apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_paths = {spec.key: getattr(args, spec.key) for spec in INPUT_SPECS}
    write_snapshot(input_paths, args.output, args.dashboard_output)
    print(f"wrote reviewed snapshot: {args.output}")
    print(f"wrote dashboard data module: {args.dashboard_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
