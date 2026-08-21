from __future__ import annotations

import csv
import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

import scripts.generate_phase3_current_reviewed_comparison as current


ROOT = Path(__file__).resolve().parents[1]

HISTORICAL = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_extended_reviewed_comparison_20260805.json"
)
PROVIDER = (
    ROOT
    / "results/phase3/provider_usage/normalized/"
      "openai_provider_reconciliation_20260821.csv"
)
CURRENT = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_reviewed_comparison_20260821.json"
)
DASHBOARD = (
    ROOT
    / "apps/dashboard/src/generated/"
      "phase3-current-reviewed-comparison-data.ts"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_cost(arm: dict) -> Decimal:
    adjusted = arm["adjustedKnownCostUsd"]
    qualified = arm["qualifiedRetainedRateCostUsd"]

    assert not (adjusted is not None and qualified is not None)

    value = adjusted if adjusted is not None else qualified
    assert value is not None

    return Decimal(value)


def test_inputs_are_hash_bound_and_frozen_history_is_unchanged() -> None:
    assert sha256(HISTORICAL) == (
        "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"
    )
    assert sha256(PROVIDER) == (
        "5da12494743dc7265c3c08ffc08aa988451fbc308940453cf9b3bc6cdf71e452"
    )


def test_checked_outputs_are_exact_deterministic_generator_products() -> None:
    generated = current.generate_snapshot(HISTORICAL, PROVIDER)

    assert CURRENT.read_text(encoding="utf-8") == (
        current.serialize_snapshot(generated)
    )
    assert DASHBOARD.read_text(encoding="utf-8") == (
        current.serialize_dashboard_module(generated)
    )

    assert generated == current.generate_snapshot(HISTORICAL, PROVIDER)


def test_selected_scope_costs_use_exact_arm_sums_and_preserve_residual() -> None:
    snapshot = load_json(CURRENT)

    assert snapshot["schemaVersion"] == (
        "phase3-current-reviewed-comparison-v2"
    )
    assert snapshot["reviewedAt"] == "2026-08-21"
    assert snapshot["historicalReviewedAt"] == "2026-08-05"

    expected = {
        "phase3-core": {
            "selected": Decimal("682.961171493867"),
            "source": Decimal("682.961171493867"),
            "residual": Decimal("0"),
        },
        "phase3-extended": {
            "selected": Decimal("713.775490893867"),
            "source": Decimal("713.7754908938669"),
            "residual": Decimal("-0.0000000000001"),
        },
    }

    for scope_id, wanted in expected.items():
        scope = snapshot["scopes"][scope_id]
        evidence = scope["selectedCostEvidence"]

        arm_sum = sum(
            (
                Decimal(arm["selectedCostUsd"])
                for arm in scope["arms"]
            ),
            Decimal("0"),
        )

        assert Decimal(evidence["selectedCostUsd"]) == wanted["selected"]
        assert arm_sum == wanted["selected"]

        assert Decimal(
            evidence["sourceScopeTransformedSelectedCostUsd"]
        ) == wanted["source"]

        assert Decimal(
            evidence["sourceScopeReconciliationAdjustmentUsd"]
        ) == wanted["residual"]

        assert (
            Decimal(evidence["sourceScopeTransformedSelectedCostUsd"])
            - Decimal(evidence["selectedCostUsd"])
            == wanted["residual"]
        )

        assert evidence["providerReconciledArmIds"] == [
            "router-gpt-5.4",
            "router-gpt-5.5",
        ]
        assert evidence["providerReconciledArmCount"] == 2
        assert Decimal(evidence["providerReconciledCostUsd"]) == Decimal(
            "78.3968475"
        )

        assert "costEvidence" not in scope
        assert "outcomeCostCoverage" not in scope


def test_openai_selected_costs_are_provider_billed_and_unallocated() -> None:
    snapshot = load_json(CURRENT)
    arms = {
        arm["armId"]: arm
        for arm in snapshot["scopes"]["phase3-core"]["arms"]
    }

    expected = {
        "router-gpt-5.4": {
            "provider": "29.7919335",
            "historical_recorded": "173.09483",
            "historical_reviewed": "183.646689146806",
            "attempt": "0.496532225",
            "clean": "0.78399825",
            "success":
                "0.7638957307692307692307692308",
            "run":
                "router-gpt-5.4/2026-06-19__13-47-51",
        },
        "router-gpt-5.5": {
            "provider": "48.604914",
            "historical_recorded": "168.708375",
            "historical_reviewed": "183.958832348525",
            "attempt": "0.8100819",
            "clean":
                "1.157259857142857142857142857",
            "success":
                "1.104657136363636363636363636",
            "run":
                "router-gpt-5.5/2026-06-27__01-30-18",
        },
    }

    for arm_id, wanted in expected.items():
        arm = arms[arm_id]

        assert arm["providerBilledCostUsd"] == wanted["provider"]
        assert arm["selectedCostUsd"] == wanted["provider"]
        assert arm["selectedCostBasis"] == "provider_billed"
        assert arm["selectedCostConfidence"] == (
            "exact_provider_arm_total"
        )

        assert arm["historicalHarnessRecordedCostUsd"] == (
            wanted["historical_recorded"]
        )
        assert arm["historicalReviewedCostUsd"] == (
            wanted["historical_reviewed"]
        )

        assert arm["selectedCostPerAttemptUsd"] == wanted["attempt"]
        assert arm["selectedCostPerCleanSuccessUsd"] == wanted["clean"]
        assert arm["selectedCostPerAnySuccessUsd"] == wanted["success"]

        assert arm["providerSelectedRunLabel"] == wanted["run"]
        assert arm["providerBillingReconciliationStatus"] == (
            "exact_arm_total"
        )

        assert arm["selectedTrialCostAllocationStatus"] == (
            "unavailable_provider_aggregate"
        )
        assert arm["selectedOutcomeCostAllocationStatus"] == (
            "unavailable_provider_aggregate"
        )


def test_non_openai_arms_preserve_historical_selected_cost() -> None:
    historical = load_json(HISTORICAL)
    snapshot = load_json(CURRENT)

    provider_arms = {"router-gpt-5.4", "router-gpt-5.5"}

    for scope_id in ("phase3-core", "phase3-extended"):
        old_arms = {
            arm["armId"]: arm
            for arm in historical["scopes"][scope_id]["arms"]
        }
        new_arms = {
            arm["armId"]: arm
            for arm in snapshot["scopes"][scope_id]["arms"]
        }

        assert set(old_arms) == set(new_arms)

        for arm_id in sorted(set(old_arms) - provider_arms):
            old = old_arms[arm_id]
            new = new_arms[arm_id]

            expected_cost = historical_cost(old)

            assert Decimal(new["selectedCostUsd"]) == expected_cost
            assert Decimal(new["historicalReviewedCostUsd"]) == (
                expected_cost
            )
            assert new["historicalHarnessRecordedCostUsd"] == (
                old["recordedCostUsd"]
            )

            assert new["providerBilledCostUsd"] is None
            assert new["providerSelectedRunLabel"] is None
            assert new["providerBillingReconciliationStatus"] == (
                "not_available_in_current_provider_layer"
            )
            assert new["selectedCostBasis"] == old["costBasis"]


def test_historical_cost_and_outcome_evidence_remain_exact_diagnostics() -> None:
    historical = load_json(HISTORICAL)
    snapshot = load_json(CURRENT)

    for scope_id in ("phase3-core", "phase3-extended"):
        old = historical["scopes"][scope_id]
        new = snapshot["scopes"][scope_id]

        assert new["historicalCostEvidence"] == old["costEvidence"]
        assert new["historicalOutcomeCostCoverage"] == (
            old["outcomeCostCoverage"]
        )


def test_hash_mutation_fails_before_generation(tmp_path: Path) -> None:
    altered = tmp_path / "historical.json"
    shutil.copy2(HISTORICAL, altered)

    altered.write_text(
        altered.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="input hash changed"):
        current.generate_snapshot(altered, PROVIDER)


def test_provider_semantic_mutation_fails_closed(tmp_path: Path) -> None:
    altered = tmp_path / "provider.csv"

    with PROVIDER.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])

    target = next(
        row
        for row in rows
        if row["arm_id"] == "router-gpt-5.4"
    )
    target["provider_billing_reconciliation_status"] = (
        "not_invoice_level"
    )

    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(
        ValueError,
        match="no longer exact arm-level provider billing",
    ):
        current.read_provider_rows(altered)


def test_output_safety_protects_frozen_inputs_and_distinct_outputs(
    tmp_path: Path,
) -> None:
    dashboard = tmp_path / "dashboard.ts"

    with pytest.raises(
        ValueError,
        match="must not equal an input path",
    ):
        current.assert_output_safety(
            HISTORICAL,
            PROVIDER,
            HISTORICAL,
            dashboard,
        )

    with pytest.raises(
        ValueError,
        match="must not equal an input path",
    ):
        current.assert_output_safety(
            HISTORICAL,
            PROVIDER,
            PROVIDER,
            dashboard,
        )

    same = tmp_path / "same.json"

    with pytest.raises(
        ValueError,
        match="output paths must be distinct",
    ):
        current.assert_output_safety(
            HISTORICAL,
            PROVIDER,
            same,
            same,
        )
