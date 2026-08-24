from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

import scripts.generate_phase3_current_reviewed_comparison_v3 as current


ROOT = Path(__file__).resolve().parents[1]

HISTORICAL = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_extended_reviewed_comparison_20260805.json"
)
ARMS = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260824.csv"
)
ANTHROPIC_EXCEPTIONS = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv"
)
CURRENT = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_reviewed_comparison_20260824.json"
)
DASHBOARD = (
    ROOT
    / "apps/dashboard/src/generated/"
      "phase3-current-reviewed-comparison-data-v3.ts"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def test_inputs_are_hash_bound() -> None:
    assert sha256(HISTORICAL) == (
        "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"
    )
    assert sha256(ARMS) == (
        "7fc2ac41dfd56af4888cac0cc6d80be15f5d3b8edef12b915206fd57bc9afbea"
    )
    assert sha256(ANTHROPIC_EXCEPTIONS) == (
        "9223673f2dcdd55fa558f0336d72d721f0bf3c58f409e84fadeaeb277a7dfa88"
    )


def test_provider_model_list_preserves_multi_model_composition() -> None:
    assert current.split_semicolon(
        "synthetic-primary-model;synthetic-secondary-model"
    ) == [
        "synthetic-primary-model",
        "synthetic-secondary-model",
    ]


def test_checked_outputs_are_deterministic_generator_products() -> None:
    generated = current.generate_snapshot(
        HISTORICAL,
        ARMS,
        ANTHROPIC_EXCEPTIONS,
    )

    assert CURRENT.read_text(
        encoding="utf-8"
    ) == current.serialize_snapshot(
        generated
    )

    assert DASHBOARD.read_text(
        encoding="utf-8"
    ) == current.serialize_dashboard_module(
        generated
    )

    assert generated == current.generate_snapshot(
        HISTORICAL,
        ARMS,
        ANTHROPIC_EXCEPTIONS,
    )


def test_scope_totals_are_mixed_relation_not_global_lower_bounds() -> None:
    snapshot = load_json(CURRENT)

    assert snapshot["schemaVersion"] == (
        "phase3-current-reviewed-comparison-v3"
    )
    assert snapshot["reviewedAt"] == "2026-08-24"
    assert snapshot["historicalReviewedAt"] == "2026-08-05"

    expected = {
        "phase3-core": {
            "selected": Decimal(
                "510.405678806867"
            ),
            "source": Decimal(
                "510.405678806867"
            ),
            "residual": Decimal("0"),
            "fallback": 7,
        },
        "phase3-extended": {
            "selected": Decimal(
                "541.219998206867"
            ),
            "source": Decimal(
                "541.2199982068669"
            ),
            "residual": Decimal(
                "-0.0000000000001"
            ),
            "fallback": 8,
        },
    }

    for scope_id, wanted in expected.items():
        scope = snapshot["scopes"][scope_id]
        evidence = scope["selectedCostEvidence"]

        assert evidence["selectedCostRelation"] == (
            "mixed_by_arm"
        )

        assert Decimal(
            evidence["selectedCostUsd"]
        ) == wanted["selected"]

        assert Decimal(
            evidence[
                "sourceScopeTransformedSelectedCostUsd"
            ]
        ) == wanted["source"]

        assert Decimal(
            evidence[
                "sourceScopeReconciliationAdjustmentUsd"
            ]
        ) == wanted["residual"]

        arm_sum = sum(
            (
                Decimal(
                    arm["selectedCostUsd"]
                )
                for arm in scope["arms"]
            ),
            Decimal("0"),
        )
        assert arm_sum == wanted["selected"]

        counts = evidence[
            "selectedCostRelationCounts"
        ]

        assert counts["exact"] == 4
        assert counts["estimate"] == 2
        assert counts["lowerBound"] == 2
        assert counts["historicalFallback"] == (
            wanted["fallback"]
        )

        assert evidence[
            "currentReconciledArmCount"
        ] == 8
        assert Decimal(
            evidence[
                "currentReconciledCostUsd"
            ]
        ) == Decimal(
            "251.5579261372"
        )

        assert evidence[
            "exactProviderBilledArmCount"
        ] == 2
        assert Decimal(
            evidence[
                "exactProviderBilledCostUsd"
            ]
        ) == Decimal(
            "78.3968475"
        )

        assert evidence[
            "unquantifiedAdditionalCostArmIds"
        ] == [
            "router-anthropic-opus",
            "router-anthropic-sonnet",
        ]


def test_reconciled_arm_relations_and_costs_are_preserved() -> None:
    snapshot = load_json(CURRENT)

    arms = {
        arm["armId"]: arm
        for arm in snapshot[
            "scopes"
        ]["phase3-core"]["arms"]
    }

    expected = {
        "router-anthropic-fable-5": (
            "64.805045",
            "exact",
            "provider_rate_reconstructed_retained_usage",
        ),
        "router-anthropic-haiku-sanitized": (
            "16.70224485",
            "exact",
            "provider_rate_reconstructed_retained_usage",
        ),
        "router-anthropic-opus": (
            "50.28831125",
            "lower_bound",
            "provider_rate_reconstructed_retained_usage_lower_bound",
        ),
        "router-anthropic-sonnet": (
            "38.3859171",
            "lower_bound",
            "provider_rate_reconstructed_retained_usage_lower_bound",
        ),
        "router-deepseek-flash": (
            "1.0798358032",
            "estimate",
            "provider_rate_reconstructed_selected_run",
        ),
        "router-deepseek-pro": (
            "1.899724634",
            "estimate",
            "provider_rate_reconstructed_selected_run",
        ),
        "router-gpt-5.4": (
            "29.7919335",
            "exact",
            "provider_billed",
        ),
        "router-gpt-5.5": (
            "48.604914",
            "exact",
            "provider_billed",
        ),
    }

    for arm_id, (
        cost,
        relation,
        basis,
    ) in expected.items():
        arm = arms[arm_id]

        assert arm[
            "currentReconciliationStatus"
        ] == "reconciled"
        assert Decimal(
            arm["selectedCostUsd"]
        ) == Decimal(cost)
        assert arm[
            "selectedCostRelation"
        ] == relation
        assert arm[
            "selectedEfficiencyRelation"
        ] == relation
        assert arm[
            "selectedCostBasis"
        ] == basis


def test_exact_provider_billing_is_only_openai() -> None:
    snapshot = load_json(CURRENT)

    arms = snapshot[
        "scopes"
    ]["phase3-core"]["arms"]

    billed = {
        arm["armId"]: arm
        for arm in arms
        if arm[
            "providerBilledCostUsd"
        ] is not None
    }

    assert set(billed) == {
        "router-gpt-5.4",
        "router-gpt-5.5",
    }

    assert billed[
        "router-gpt-5.4"
    ]["providerBilledCostUsd"] == "29.7919335"

    assert billed[
        "router-gpt-5.5"
    ]["providerBilledCostUsd"] == "48.604914"

    for arm in billed.values():
        assert arm[
            "selectedCostRelation"
        ] == "exact"
        assert arm[
            "selectedCostBasis"
        ] == "provider_billed"
        assert arm[
            "selectedTrialCostAllocationStatus"
        ] == "unavailable_provider_aggregate"
        assert arm[
            "selectedOutcomeCostAllocationStatus"
        ] == "unavailable_provider_aggregate"
        assert arm[
            "knownAllocatedCostUsd"
        ] == "0"
        assert arm[
            "unallocatedKnownCostUsd"
        ] == arm["selectedCostUsd"]


def test_deepseek_uses_selected_run_reconstruction_not_day_bill() -> None:
    snapshot = load_json(CURRENT)

    arms = {
        arm["armId"]: arm
        for arm in snapshot[
            "scopes"
        ]["phase3-core"]["arms"]
    }

    expected = {
        "router-deepseek-flash": (
            Decimal("1.0798358032"),
            Decimal("1.1502775424"),
            Decimal("0.0704417392"),
        ),
        "router-deepseek-pro": (
            Decimal("1.899724634"),
            Decimal("1.963511004"),
            Decimal("0.063786370"),
        ),
    }

    for arm_id, (
        selected,
        context,
        excess,
    ) in expected.items():
        arm = arms[arm_id]

        assert arm[
            "selectedCostRelation"
        ] == "estimate"
        assert Decimal(
            arm["selectedCostUsd"]
        ) == selected
        assert Decimal(
            arm[
                "providerContextBilledCostUsd"
            ]
        ) == context
        assert Decimal(
            arm[
                "providerContextExcessUsd"
            ]
        ) == excess
        assert context - selected == excess

        assert arm[
            "providerBillingReconciliationStatus"
        ] == (
            "same_day_model_aggregate_not_run_isolated"
        )


def test_anthropic_lower_bounds_preserve_allocation_and_uncertainty() -> None:
    snapshot = load_json(CURRENT)

    arms = {
        arm["armId"]: arm
        for arm in snapshot[
            "scopes"
        ]["phase3-core"]["arms"]
    }

    expected = {
        "router-anthropic-opus": {
            "selected":
                Decimal("50.28831125"),
            "complete": 58,
            "lower": 2,
        },
        "router-anthropic-sonnet": {
            "selected":
                Decimal("38.38591710"),
            "complete": 55,
            "lower": 5,
        },
    }

    for arm_id, wanted in expected.items():
        arm = arms[arm_id]

        assert arm[
            "selectedCostRelation"
        ] == "lower_bound"
        assert arm[
            "completeTrialCostCount"
        ] == wanted["complete"]
        assert arm[
            "lowerBoundTrialCount"
        ] == wanted["lower"]
        assert arm[
            "unquantifiedAdditionalCostStatus"
        ] == (
            "possible_additional_exception_path_spend"
        )

        allocated = sum(
            (
                Decimal(
                    arm[field]
                )
                for field in (
                    "selectedCleanSuccessCostUsd",
                    "selectedNormalFailureCostUsd",
                    "selectedExceptionFailureCostUsd",
                    "selectedExceptionWithSuccessSignalCostUsd",
                )
            ),
            Decimal("0"),
        )

        assert allocated == wanted["selected"]
        assert Decimal(
            arm["knownAllocatedCostUsd"]
        ) == wanted["selected"]
        assert arm[
            "unallocatedKnownCostUsd"
        ] == "0"


def test_unreconciled_arms_remain_explicit_historical_fallbacks() -> None:
    historical = load_json(HISTORICAL)
    snapshot = load_json(CURRENT)

    old_arms = {
        arm["armId"]: arm
        for arm in historical[
            "scopes"
        ]["phase3-core"]["arms"]
    }
    new_arms = {
        arm["armId"]: arm
        for arm in snapshot[
            "scopes"
        ]["phase3-core"]["arms"]
    }

    fallback_ids = (
        set(new_arms)
        - current.EXPECTED_RECONCILED_ARM_IDS
    )

    assert len(fallback_ids) == 7

    for arm_id in fallback_ids:
        old = old_arms[arm_id]
        new = new_arms[arm_id]

        assert new[
            "currentReconciliationStatus"
        ] == "historical_fallback"
        assert new[
            "selectedCostRelation"
        ] == "historical_fallback"
        assert new[
            "selectedCostBasis"
        ] == old["costBasis"]
        assert new[
            "selectedCostConfidence"
        ] == old["costConfidence"]

        assert Decimal(
            new["selectedCostUsd"]
        ) == current.historical_selected_cost(
            old
        )

        assert new[
            "providerBilledCostUsd"
        ] is None
        assert new[
            "currentSelectedRunLabel"
        ] is None
        assert new[
            "currentProviderModels"
        ] == []
        assert new[
            "completeTrialCostCount"
        ] is None


def test_frozen_historical_evidence_is_preserved_exactly() -> None:
    historical = load_json(HISTORICAL)
    snapshot = load_json(CURRENT)

    for scope_id in (
        "phase3-core",
        "phase3-extended",
    ):
        old = historical["scopes"][scope_id]
        new = snapshot["scopes"][scope_id]

        assert new[
            "historicalCostEvidence"
        ] == old["costEvidence"]
        assert new[
            "historicalOutcomeCostCoverage"
        ] == old["outcomeCostCoverage"]

        assert "costEvidence" not in new
        assert "outcomeCostCoverage" not in new


def test_supporting_exception_evidence_reproduces() -> None:
    totals, counts = (
        current.read_exception_lower_bounds(
            ANTHROPIC_EXCEPTIONS
        )
    )

    assert totals == {
        "router-anthropic-opus":
            Decimal("7.01247975"),
        "router-anthropic-sonnet":
            Decimal("10.18738545"),
    }
    assert dict(counts) == {
        "router-anthropic-opus": 2,
        "router-anthropic-sonnet": 5,
    }


def test_hash_mutation_fails_before_generation(
    tmp_path: Path,
) -> None:
    altered = tmp_path / "arms.csv"
    shutil.copy2(
        ARMS,
        altered,
    )

    altered.write_text(
        altered.read_text(
            encoding="utf-8"
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="input hash changed",
    ):
        current.generate_snapshot(
            HISTORICAL,
            altered,
            ANTHROPIC_EXCEPTIONS,
        )


def test_output_safety_protects_inputs(
    tmp_path: Path,
) -> None:
    dashboard = tmp_path / "dashboard.ts"

    with pytest.raises(
        ValueError,
        match="must not equal an input path",
    ):
        current.assert_output_safety(
            (
                HISTORICAL,
                ARMS,
                ANTHROPIC_EXCEPTIONS,
            ),
            ARMS,
            dashboard,
        )
