#!/usr/bin/env python3
"""Generate the DR-304 current Phase 3 reviewed cost-comparison layer.

Inputs are retained, sanitized repository evidence only:

1. the frozen 2026-08-05 reviewed Phase 3 comparison;
2. the sanitized 2026-08-21 OpenAI provider reconciliation.

The historical snapshot is never modified. Provider-billed arm totals replace
historical harness/reviewed estimates only in the new selected-cost fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "phase3-current-reviewed-comparison-v2"
GENERATOR_VERSION = "1.0.0"
REVIEWED_AT = "2026-08-21"

REPO_ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_PATH = (
    REPO_ROOT
    / "results/phase3/reporting/"
      "phase3_extended_reviewed_comparison_20260805.json"
)
PROVIDER_RECONCILIATION_PATH = (
    REPO_ROOT
    / "results/phase3/provider_usage/normalized/"
      "openai_provider_reconciliation_20260821.csv"
)

EXPECTED_HISTORICAL_SHA256 = (
    "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"
)
EXPECTED_PROVIDER_RECONCILIATION_SHA256 = (
    "5da12494743dc7265c3c08ffc08aa988451fbc308940453cf9b3bc6cdf71e452"
)

EXPECTED_PROVIDER_ARMS = {
    "router-gpt-5.4": {
        "backendModel": "gpt-5.4",
        "providerModel": "gpt-5.4-2026-03-05",
        "providerActivityDate": "2026-06-19",
        "selectedRunLabel": "router-gpt-5.4/2026-06-19__13-47-51",
        "providerBilledCostUsd": Decimal("29.7919335"),
        "historicalHarnessRecordedCostUsd": Decimal("173.09483"),
        "historicalReviewedCostUsd": Decimal("183.646689146806"),
    },
    "router-gpt-5.5": {
        "backendModel": "gpt-5.5",
        "providerModel": "gpt-5.5-2026-04-23",
        "providerActivityDate": "2026-06-27",
        "selectedRunLabel": "router-gpt-5.5/2026-06-27__01-30-18",
        "providerBilledCostUsd": Decimal("48.604914"),
        "historicalHarnessRecordedCostUsd": Decimal("168.708375"),
        "historicalReviewedCostUsd": Decimal("183.958832348525"),
    },
}

EXPECTED_SELECTED_SCOPE_TOTALS = {
    "phase3-core": Decimal("682.961171493867"),
    "phase3-extended": Decimal("713.775490893867"),
}

EXPECTED_SOURCE_SCOPE_TRANSFORMED_TOTALS = {
    "phase3-core": Decimal("682.961171493867"),
    "phase3-extended": Decimal("713.7754908938669"),
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


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        fail("cannot serialize non-finite decimal")
    if value == 0:
        return "0"
    return format(value, "f")


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


def assert_output_safety(
    historical_path: Path,
    provider_reconciliation_path: Path,
    output_path: Path,
    dashboard_output_path: Path,
) -> tuple[Path, Path]:
    inputs = {
        historical_path.resolve(),
        provider_reconciliation_path.resolve(),
    }
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
        for input_path in (
            historical_path,
            provider_reconciliation_path,
        ):
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
        raise ValueError(f"unable to read historical snapshot: {path}") from exc

    if value.get("schemaVersion") != "phase3-reviewed-comparison-v1":
        fail("historical snapshot schema changed")
    if value.get("reviewedAt") != "2026-08-05":
        fail("historical snapshot review date changed")
    if set(value.get("scopes", {})) != {"phase3-core", "phase3-extended"}:
        fail("historical snapshot scope membership changed")
    return value


def read_provider_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    project_rows = [
        row for row in rows
        if row.get("record_type") == "project_period"
    ]
    if len(project_rows) != 1:
        fail("expected exactly one OpenAI project-period reconciliation row")

    if decimal(
        project_rows[0].get("provider_billed_cost_usd"),
        "OpenAI project-period provider cost",
    ) != Decimal("95.24109000000000000000000000"):
        fail("OpenAI project-period provider cost changed")

    full_sweeps = {
        row["arm_id"]: row
        for row in rows
        if row.get("record_type") == "full_sweep"
    }
    if set(full_sweeps) != set(EXPECTED_PROVIDER_ARMS):
        fail("provider-reconciled arm membership changed")

    for arm_id, expected in EXPECTED_PROVIDER_ARMS.items():
        row = full_sweeps[arm_id]

        if row["backend_model"] != expected["backendModel"]:
            fail(f"{arm_id} backend model changed")
        if row["provider_model"] != expected["providerModel"]:
            fail(f"{arm_id} provider model changed")
        if row["provider_activity_date"] != expected["providerActivityDate"]:
            fail(f"{arm_id} provider activity date changed")
        if row["selected_run_label"] != expected["selectedRunLabel"]:
            fail(f"{arm_id} selected run changed")
        if row["provider_billing_reconciliation_status"] != "exact_arm_total":
            fail(f"{arm_id} is no longer exact arm-level provider billing")
        if row["trial_cost_allocation_status"] != "unavailable_provider_aggregate":
            fail(f"{arm_id} trial allocation status changed")
        if row["outcome_cost_allocation_status"] != "unavailable_provider_aggregate":
            fail(f"{arm_id} outcome allocation status changed")

        checks = {
            "provider_billed_cost_usd": expected["providerBilledCostUsd"],
            "historical_harness_recorded_cost_usd":
                expected["historicalHarnessRecordedCostUsd"],
            "historical_reviewed_adjusted_cost_usd":
                expected["historicalReviewedCostUsd"],
        }
        for field, wanted in checks.items():
            if decimal(row[field], f"{arm_id}.{field}") != wanted:
                fail(f"{arm_id}.{field} changed")

    return full_sweeps


def historical_selected_cost(arm: dict[str, Any]) -> Decimal:
    adjusted = arm.get("adjustedKnownCostUsd")
    qualified = arm.get("qualifiedRetainedRateCostUsd")

    if adjusted is not None and qualified is not None:
        fail(f"{arm['armId']} has two historical reviewed cost bases")
    if adjusted is not None:
        return decimal(adjusted, f"{arm['armId']}.adjustedKnownCostUsd")
    if qualified is not None:
        return decimal(
            qualified,
            f"{arm['armId']}.qualifiedRetainedRateCostUsd",
        )

    fail(f"{arm['armId']} has no historical reviewed cost basis")


def ratio(cost: Decimal, count: int, label: str) -> str | None:
    if count < 0:
        fail(f"negative denominator: {label}")
    if count == 0:
        return None
    return decimal_text(cost / Decimal(count))


def selected_arm(
    arm: dict[str, Any],
    provider_rows: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = deepcopy(arm)
    arm_id = result["armId"]

    historical_cost = historical_selected_cost(result)
    historical_recorded = decimal(
        result["recordedCostUsd"],
        f"{arm_id}.recordedCostUsd",
    )

    result["historicalHarnessRecordedCostUsd"] = decimal_text(
        historical_recorded
    )
    result["historicalReviewedCostUsd"] = decimal_text(historical_cost)
    result["historicalReviewedCostBasis"] = result["costBasis"]

    provider_row = provider_rows.get(arm_id)

    if provider_row is not None:
        expected = EXPECTED_PROVIDER_ARMS[arm_id]

        if result["backendModel"] != expected["backendModel"]:
            fail(f"{arm_id} frozen backend model disagrees with reconciliation")
        if historical_recorded != expected["historicalHarnessRecordedCostUsd"]:
            fail(f"{arm_id} frozen recorded cost disagrees with reconciliation")
        if historical_cost != expected["historicalReviewedCostUsd"]:
            fail(f"{arm_id} frozen reviewed cost disagrees with reconciliation")

        selected = expected["providerBilledCostUsd"]

        result["providerBilledCostUsd"] = decimal_text(selected)
        result["providerBillingReconciliationStatus"] = "exact_arm_total"
        result["providerSelectedRunLabel"] = provider_row["selected_run_label"]
        result["selectedCostBasis"] = "provider_billed"
        result["selectedCostConfidence"] = "exact_provider_arm_total"
        result["selectedTrialCostAllocationStatus"] = (
            "unavailable_provider_aggregate"
        )
        result["selectedOutcomeCostAllocationStatus"] = (
            "unavailable_provider_aggregate"
        )
    else:
        selected = historical_cost

        result["providerBilledCostUsd"] = None
        result["providerBillingReconciliationStatus"] = (
            "not_available_in_current_provider_layer"
        )
        result["providerSelectedRunLabel"] = None
        result["selectedCostBasis"] = result["historicalReviewedCostBasis"]
        result["selectedCostConfidence"] = result["costConfidence"]
        result["selectedTrialCostAllocationStatus"] = result[
            "trialAllocationStatus"
        ]
        result["selectedOutcomeCostAllocationStatus"] = result[
            "outcomeCostAllocationStatus"
        ]

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


def historical_scope_cost(scope: dict[str, Any]) -> Decimal:
    evidence = scope["costEvidence"]

    adjusted = evidence.get("adjustedKnownCostUsd")
    qualified = evidence.get("qualifiedAdjustedCostEstimateUsd")

    if adjusted is not None and qualified is not None:
        fail(f"{scope['scopeId']} has two scope cost bases")
    if adjusted is not None:
        return decimal(adjusted, f"{scope['scopeId']}.adjustedKnownCostUsd")
    if qualified is not None:
        return decimal(
            qualified,
            f"{scope['scopeId']}.qualifiedAdjustedCostEstimateUsd",
        )

    fail(f"{scope['scopeId']} has no historical scope cost")


def selected_scope(
    scope: dict[str, Any],
    provider_rows: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = deepcopy(scope)

    historical_scope_evidence = deepcopy(result["costEvidence"])
    historical_outcomes = deepcopy(result["outcomeCostCoverage"])

    arms = [
        selected_arm(arm, provider_rows)
        for arm in result["arms"]
    ]

    if len({arm["armId"] for arm in arms}) != len(arms):
        fail(f"{scope['scopeId']} contains duplicate arms")

    arm_ids = {arm["armId"] for arm in arms}
    expected_openai = set(EXPECTED_PROVIDER_ARMS)
    if not expected_openai.issubset(arm_ids):
        fail(f"{scope['scopeId']} is missing a provider-reconciled OpenAI arm")

    selected_arm_sum = sum(
        (Decimal(arm["selectedCostUsd"]) for arm in arms),
        Decimal("0"),
    )
    historical_arm_sum = sum(
        (Decimal(arm["historicalReviewedCostUsd"]) for arm in arms),
        Decimal("0"),
    )

    historical_source_scope = historical_scope_cost(scope)

    provider_delta = sum(
        (
            Decimal(arm["selectedCostUsd"])
            - Decimal(arm["historicalReviewedCostUsd"])
            for arm in arms
            if arm["providerBilledCostUsd"] is not None
        ),
        Decimal("0"),
    )

    source_scope_transformed = historical_source_scope + provider_delta
    source_scope_residual = source_scope_transformed - selected_arm_sum

    expected_total = EXPECTED_SELECTED_SCOPE_TOTALS[scope["scopeId"]]
    expected_source_total = EXPECTED_SOURCE_SCOPE_TRANSFORMED_TOTALS[
        scope["scopeId"]
    ]

    if selected_arm_sum != expected_total:
        fail(
            f"{scope['scopeId']} selected arm sum changed: "
            f"{selected_arm_sum}"
        )
    if source_scope_transformed != expected_source_total:
        fail(
            f"{scope['scopeId']} transformed source-scope total changed: "
            f"{source_scope_transformed}"
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

    result["arms"] = arms
    result["historicalCostEvidence"] = historical_scope_evidence
    result["historicalOutcomeCostCoverage"] = historical_outcomes

    # Keep the historical field for provenance, but do not let a future
    # consumer mistake it for current selected provider-aware cost evidence.
    result.pop("costEvidence", None)
    result.pop("outcomeCostCoverage", None)

    result["selectedCostEvidence"] = {
        "selectedCostUsd": decimal_text(selected_arm_sum),
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
        "providerReconciledArmIds": sorted(EXPECTED_PROVIDER_ARMS),
        "providerReconciledArmCount": len(EXPECTED_PROVIDER_ARMS),
        "providerReconciledCostUsd": decimal_text(
            sum(
                (
                    EXPECTED_PROVIDER_ARMS[arm_id][
                        "providerBilledCostUsd"
                    ]
                    for arm_id in EXPECTED_PROVIDER_ARMS
                ),
                Decimal("0"),
            )
        ),
        "providerBillingCoverageStatus": "partial_by_arm",
        "trialAllocationStatus": "mixed_by_arm",
        "outcomeAllocationStatus": "mixed_by_arm",
        "note": (
            "Primary selectedCostUsd is the exact sum of selected arm costs. "
            "The source-scope transformed value is retained separately so "
            "historical decimal reconciliation residuals are never silently "
            "allocated to an arm."
        ),
    }

    return result


def generate_snapshot(
    historical_path: Path,
    provider_reconciliation_path: Path,
) -> dict[str, Any]:
    expected_inputs = (
        (historical_path, EXPECTED_HISTORICAL_SHA256),
        (
            provider_reconciliation_path,
            EXPECTED_PROVIDER_RECONCILIATION_SHA256,
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
    provider_rows = read_provider_rows(provider_reconciliation_path)

    scopes = {
        scope_id: selected_scope(scope, provider_rows)
        for scope_id, scope in historical["scopes"].items()
    }

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "generator": {
            "name": "scripts/generate_phase3_current_reviewed_comparison.py",
            "version": GENERATOR_VERSION,
        },
        "reviewedAt": REVIEWED_AT,
        "historicalReviewedAt": historical["reviewedAt"],
        "inputs": [
            {
                "path": display_path(historical_path),
                "role": "frozen_historical_reviewed_comparison",
                "sha256": sha256(historical_path),
            },
            {
                "path": display_path(provider_reconciliation_path),
                "role": "sanitized_provider_billing_reconciliation",
                "sha256": sha256(provider_reconciliation_path),
            },
        ],
        "scopes": scopes,
    }

    serialized = json.dumps(result, sort_keys=True)

    prohibited = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"\bproj_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\bkey_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\borg-[A-Za-z0-9_-]{8,}\b"),
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    )
    if any(pattern.search(serialized) for pattern in prohibited):
        fail("generated current reviewed snapshot contains provider identifiers")

    return result


def serialize_snapshot(snapshot: dict[str, Any]) -> str:
    return (
        json.dumps(
            snapshot,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def serialize_dashboard_module(snapshot: dict[str, Any]) -> str:
    compact = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    escaped = json.dumps(compact, ensure_ascii=False)
    return (
        "// Generated by "
        "scripts/generate_phase3_current_reviewed_comparison.py. "
        "Do not edit.\n"
        f"const currentReviewedSnapshot = JSON.parse({escaped});\n"
        "export default currentReviewedSnapshot;\n"
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

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

        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--historical",
        type=Path,
        default=HISTORICAL_PATH,
    )
    parser.add_argument(
        "--provider-reconciliation",
        type=Path,
        default=PROVIDER_RECONCILIATION_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            REPO_ROOT
            / "results/phase3/reporting/"
              "phase3_current_reviewed_comparison_20260821.json"
        ),
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=(
            REPO_ROOT
            / "apps/dashboard/src/generated/"
              "phase3-current-reviewed-comparison-data.ts"
        ),
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    resolved_output, resolved_dashboard_output = assert_output_safety(
        args.historical,
        args.provider_reconciliation,
        args.output,
        args.dashboard_output,
    )

    snapshot = generate_snapshot(
        args.historical,
        args.provider_reconciliation,
    )

    atomic_write(resolved_output, serialize_snapshot(snapshot))
    atomic_write(
        resolved_dashboard_output,
        serialize_dashboard_module(snapshot),
    )

    print(f"wrote current reviewed snapshot: {args.output}")
    print(f"wrote dashboard data module: {args.dashboard_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
