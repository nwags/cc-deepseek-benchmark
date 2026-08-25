from __future__ import annotations

import csv
import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

import scripts.generate_phase3_current_reviewed_comparison_v4 as current


ROOT = Path(__file__).resolve().parents[1]

HISTORICAL = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_extended_reviewed_comparison_20260805.json"
)
ARMS = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)
MATRIX = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_provider_cost_evidence_matrix_20260825.csv"
)
ANTHROPIC_EXCEPTIONS = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv"
)

CURRENT = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_reviewed_comparison_20260825.json"
)
DASHBOARD = (
    ROOT
    / "apps/dashboard/src/generated/"
      "phase3-current-reviewed-comparison-data-v4.ts"
)

V3_GENERATOR = (
    ROOT
    / "scripts/"
      "generate_phase3_current_reviewed_comparison_v3.py"
)
V3_CURRENT = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_reviewed_comparison_20260824.json"
)
V3_DASHBOARD = (
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


def arm_index(
    snapshot: dict,
    scope_id: str,
) -> dict[str, dict]:
    return {
        arm["armId"]: arm
        for arm in snapshot[
            "scopes"
        ][scope_id]["arms"]
    }


def test_inputs_are_hash_bound() -> None:
    assert sha256(HISTORICAL) == (
        "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d"
    )
    assert sha256(ARMS) == (
        "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256"
    )
    assert sha256(MATRIX) == (
        "e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218"
    )
    assert sha256(ANTHROPIC_EXCEPTIONS) == (
        "9223673f2dcdd55fa558f0336d72d721f0bf3c58f409e84fadeaeb277a7dfa88"
    )


def test_v4_outputs_are_distinct_from_frozen_v3() -> None:
    assert current.OUTPUT_PATH.resolve() != V3_CURRENT.resolve()
    assert (
        current.DASHBOARD_OUTPUT_PATH.resolve()
        != V3_DASHBOARD.resolve()
    )
    assert (
        Path(current.__file__).resolve()
        != V3_GENERATOR.resolve()
    )


def test_checked_outputs_are_deterministic_generator_products() -> None:
    generated = current.generate_snapshot(
        HISTORICAL,
        ARMS,
        MATRIX,
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
        MATRIX,
        ANTHROPIC_EXCEPTIONS,
    )


def test_v4_scope_totals_and_complete_reconciliation() -> None:
    snapshot = load_json(CURRENT)

    assert snapshot["schemaVersion"] == (
        "phase3-current-reviewed-comparison-v4"
    )
    assert snapshot["reviewedAt"] == "2026-08-25"
    assert snapshot["historicalReviewedAt"] == "2026-08-05"

    expected = {
        "phase3-core": {
            "arms": 15,
            "selected": Decimal(
                "316.8790274572"
            ),
            "source": Decimal(
                "316.879027457200"
            ),
            "exact": 4,
            "estimate": 6,
            "lower": 5,
        },
        "phase3-extended": {
            "arms": 16,
            "selected": Decimal(
                "343.4494304572"
            ),
            "source": Decimal(
                "343.4494304571999"
            ),
            "exact": 4,
            "estimate": 7,
            "lower": 5,
        },
    }

    for scope_id, wanted in expected.items():
        scope = snapshot["scopes"][scope_id]
        evidence = scope["selectedCostEvidence"]

        assert scope["armCount"] == wanted["arms"]
        assert len(scope["arms"]) == wanted["arms"]

        assert evidence[
            "currentReconciliationCoverageStatus"
        ] == "complete_by_arm"

        assert evidence[
            "currentReconciledArmCount"
        ] == wanted["arms"]

        assert len(
            evidence["currentReconciledArmIds"]
        ) == wanted["arms"]

        assert Decimal(
            evidence["selectedCostUsd"]
        ) == wanted["selected"]

        assert Decimal(
            evidence["currentReconciledCostUsd"]
        ) == wanted["selected"]

        assert Decimal(
            evidence[
                "sourceScopeTransformedSelectedCostUsd"
            ]
        ) == wanted["source"]

        counts = evidence[
            "selectedCostRelationCounts"
        ]

        assert counts == {
            "exact": wanted["exact"],
            "estimate": wanted["estimate"],
            "lowerBound": wanted["lower"],
            "historicalFallback": 0,
        }

        assert all(
            arm["currentReconciliationStatus"]
            == "reconciled"
            for arm in scope["arms"]
        )

        assert all(
            arm["selectedCostRelation"]
            != "historical_fallback"
            for arm in scope["arms"]
        )


def test_core_and_extended_membership_preserve_kimi_boundary() -> None:
    snapshot = load_json(CURRENT)

    core = arm_index(
        snapshot,
        "phase3-core",
    )
    extended = arm_index(
        snapshot,
        "phase3-extended",
    )

    assert "router-kimi-k3" not in core
    assert "router-kimi-k3" in extended
    assert set(core).issubset(extended)
    assert len(core) == 15
    assert len(extended) == 16


def test_exact_provider_billing_remains_openai_only() -> None:
    snapshot = load_json(CURRENT)
    arms = arm_index(
        snapshot,
        "phase3-extended",
    )

    billed = {
        arm_id: arm
        for arm_id, arm in arms.items()
        if arm["providerBilledCostUsd"] is not None
    }

    assert set(billed) == {
        "router-gpt-5.4",
        "router-gpt-5.5",
    }

    assert sum(
        (
            Decimal(
                arm["providerBilledCostUsd"]
            )
            for arm in billed.values()
        ),
        Decimal("0"),
    ) == Decimal("78.3968475")


def test_lower_bounds_and_unquantified_membership_are_explicit() -> None:
    snapshot = load_json(CURRENT)
    arms = arm_index(
        snapshot,
        "phase3-core",
    )

    lower = {
        arm_id
        for arm_id, arm in arms.items()
        if arm["selectedCostRelation"] == "lower_bound"
    }

    assert lower == {
        "router-anthropic-opus",
        "router-anthropic-sonnet",
        "router-grok-build-0.1",
        "router-gemini-flash",
        "router-qwen-3.7-plus",
    }

    evidence = snapshot[
        "scopes"
    ]["phase3-core"]["selectedCostEvidence"]

    assert set(
        evidence["unquantifiedAdditionalCostArmIds"]
    ) == {
        "router-anthropic-opus",
        "router-anthropic-sonnet",
        "router-grok-build-0.1",
        "router-glm-5.1",
        "router-gemini-flash",
        "router-qwen-3.7-plus",
    }

    assert evidence[
        "unquantifiedAdditionalCostArmCount"
    ] == 6


def test_glm_5_1_remains_partial_estimate_with_unresolved_usage() -> None:
    snapshot = load_json(CURRENT)
    glm = arm_index(
        snapshot,
        "phase3-core",
    )["router-glm-5.1"]

    assert glm["selectedCostUsd"] == "5.3316552"
    assert glm["selectedCostRelation"] == "estimate"
    assert glm["selectedCostBasis"] == (
        "provider_rate_reconstructed_retained_usage_partial"
    )
    assert glm["selectedCostConfidence"] == "medium"

    assert glm["completeTrialCostCount"] == 55
    assert glm["lowerBoundTrialCount"] == 0
    assert glm["currentUnresolvedTrialCount"] == 5

    assert glm[
        "selectedTrialCostAllocationStatus"
    ] == (
        "partial_selected_usage_reconstruction_with_unresolved_trials"
    )

    assert glm[
        "selectedOutcomeCostAllocationStatus"
    ] == "available_partial_estimate"

    assert glm[
        "unquantifiedAdditionalCostStatus"
    ] == (
        "unresolved_trial_spend_and_"
        "cache_classification_uncertainty"
    )

    audit = glm["providerEvidenceAudit"]

    assert audit["pricingProvenanceStatus"] == (
        "retained_published_rates_"
        "cache_accounting_unverified"
    )
    assert audit["trajectoryEvidenceStatus"] == (
        "60_trajectories_exactly_match_coverage;"
        "5_zero_metric_trials"
    )


def test_kimi_k3_selected_cost_and_provider_context_remain_separate() -> None:
    snapshot = load_json(CURRENT)
    k3 = arm_index(
        snapshot,
        "phase3-extended",
    )["router-kimi-k3"]

    assert k3["provider"] == "moonshot"
    assert k3["selectedCostUsd"] == "26.570403"
    assert k3["selectedCostRelation"] == "estimate"
    assert k3["currentUnresolvedTrialCount"] == 0
    assert k3["providerBilledCostUsd"] is None
    assert k3["providerContextBilledCostUsd"] is None

    assert k3[
        "selectedOutcomeCostAllocationStatus"
    ] == "unavailable_no_reviewed_outcome_join"

    audit = k3["providerEvidenceAudit"]

    assert audit["provider"] == "moonshot-kimi"
    assert audit[
        "providerContextRateReconstructionUsd"
    ] == "30.8143194"
    assert audit[
        "providerContextRateReconstructionExcessVsSelectedUsd"
    ] == "4.2439164"
    assert audit[
        "providerContextAllocationConfidence"
    ] == "low"
    assert audit["pricingProvenanceStatus"] == (
        "retained_2026-07-22_rate_constants_"
        "official_snapshot_missing"
    )


def test_gemini_pro_retains_request_tier_provenance() -> None:
    snapshot = load_json(CURRENT)
    pro = arm_index(
        snapshot,
        "phase3-core",
    )["router-gemini-3.1-pro"]

    assert pro["selectedCostUsd"] == "19.6968138"
    assert pro["selectedCostRelation"] == "estimate"
    assert pro["selectedCostBasis"] == (
        "provider_rate_reconstructed_selected_run_request_tier"
    )

    audit = pro["providerEvidenceAudit"]

    assert audit["trajectoryEvidenceStatus"] == (
        "60_trajectories;930_requests;"
        "exact_token_crosscheck;max_prompt_66438"
    )
    assert audit["pricingProvenanceStatus"] == (
        "official_google_rates_request_tier_verified"
    )


def test_qwen_account_overhead_is_not_selected_inference_cost() -> None:
    snapshot = load_json(CURRENT)
    qwen = arm_index(
        snapshot,
        "phase3-core",
    )["router-qwen-3.7-plus"]

    audit = qwen["providerEvidenceAudit"]

    assert qwen["selectedCostUsd"] == "2.50442432"
    assert audit["providerContextAccountSpendUsd"] == "31.31089"
    assert audit["providerContextOverheadUsd"] == "30"
    assert qwen["providerContextBilledCostUsd"] == "1.31089"


def test_historical_reviewed_bridge_residuals_are_explicit() -> None:
    historical = load_json(HISTORICAL)
    historical_arms = {
        arm["armId"]: arm
        for arm in historical[
            "scopes"
        ]["phase3-extended"]["arms"]
    }

    with ARMS.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    actual = {}

    for row in rows:
        arm = historical_arms[row["arm_id"]]

        frozen_text = (
            arm.get("adjustedKnownCostUsd")
            or arm.get("qualifiedRetainedRateCostUsd")
        )

        assert frozen_text is not None

        delta = (
            Decimal(row["historical_reviewed_cost_usd"])
            - Decimal(frozen_text)
        )

        if delta:
            actual[row["arm_id"]] = delta

    expected = {
        "router-gemini-3.1-pro":
            Decimal("0.000000000001"),
        "router-gemini-flash":
            Decimal("0.000000000002"),
        "router-qwen-3.7-plus":
            Decimal("0.000000000002"),
    }

    assert actual == expected
    assert (
        current.EXPECTED_HISTORICAL_REVIEWED_BRIDGE_DELTAS
        == expected
    )


def test_provider_matrix_context_fields_preserve_distinct_semantics() -> None:
    with MATRIX.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = {
            row["arm_id"]: row
            for row in csv.DictReader(handle)
        }

    glm52 = rows["router-glm-5.2"]

    assert glm52[
        "provider_context_billed_cost_usd"
    ] == ""
    assert glm52[
        "provider_context_account_spend_usd"
    ] == ""
    assert glm52[
        "provider_context_overhead_usd"
    ] == "0"
    assert glm52[
        "provider_context_temporal_relation"
    ] == "same_family_different_model_not_allocable"

    k26 = rows["router-kimi-k2.6"]

    assert k26[
        "provider_context_rate_reconstruction_usd"
    ] == "1.918399"
    assert k26[
        "provider_context_rate_reconstruction_excess_vs_selected_usd"
    ] == ""
    assert k26[
        "provider_context_temporal_relation"
    ] == "predates_selected_run"

    k3 = rows["router-kimi-k3"]

    assert k3[
        "provider_context_account_spend_usd"
    ] == ""
    assert k3[
        "provider_context_overhead_usd"
    ] == "0"
    assert k3[
        "provider_context_rate_reconstruction_usd"
    ] == "30.8143194"
    assert k3[
        "provider_context_rate_reconstruction_excess_vs_selected_usd"
    ] == "4.2439164"

    assert (
        Decimal(
            k3[
                "provider_context_rate_reconstruction_usd"
            ]
        )
        - Decimal(k3["selected_cost_usd"])
        == Decimal(
            k3[
                "provider_context_rate_reconstruction_excess_vs_selected_usd"
            ]
        )
    )

    qwen = rows["router-qwen-3.7-plus"]

    assert (
        Decimal(qwen["provider_context_billed_cost_usd"])
        + Decimal(qwen["provider_context_overhead_usd"])
        == Decimal(
            qwen["provider_context_account_spend_usd"]
        )
    )


def test_modified_provider_matrix_is_rejected_by_hash_pin(
    tmp_path: Path,
) -> None:
    changed = tmp_path / MATRIX.name
    shutil.copyfile(MATRIX, changed)

    text = changed.read_text(encoding="utf-8")
    changed.write_text(
        text.replace(
            "26.570403",
            "26.570404",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="input hash changed",
    ):
        current.generate_snapshot(
            HISTORICAL,
            ARMS,
            changed,
            ANTHROPIC_EXCEPTIONS,
        )
