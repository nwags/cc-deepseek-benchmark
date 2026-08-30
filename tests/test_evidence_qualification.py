from decimal import Decimal

from scripts.lib.evidence_qualification import (
    EvidenceQualificationInput,
    evaluate_evidence_promotion,
)


def candidate(**overrides):
    values = {
        "source_mode": "canary",
        "target_mode": "smoke",
        "source_run_matches_arm": True,
        "source_run_matches_mode": True,
        "usage_reconciliation_matches_source_run": True,
        "cost_reconciliation_matches_source_run": True,
        "usage_reconciliation_current": True,
        "cost_reconciliation_current": True,
        "usage_provider_evidence_visible": True,
        "cost_provider_evidence_visible": True,
        "model_identity_status": "matched",
        "usage_validation_status": "provisional",
        "cost_validation_status": "provisional",
        "selected_usage_authority": "provider_request_usage",
        "selected_cost_basis": (
            "provider_rate_reconstructed_provider_usage"
        ),
        "selected_cost_relation": "estimate",
        "selected_cost_usd": Decimal("0.01"),
        "usage_limitations_recorded": True,
        "cost_limitations_recorded": True,
    }
    values.update(overrides)
    return EvidenceQualificationInput(**values)


def test_canary_may_advance_with_documented_provisional_authority():
    decision = evaluate_evidence_promotion(candidate())

    assert decision.can_advance
    assert decision.blocker_codes == ()


def test_canary_requires_provider_usage_visibility():
    decision = evaluate_evidence_promotion(
        candidate(usage_provider_evidence_visible=False)
    )

    assert not decision.can_advance
    assert "provider_usage_evidence_not_visible" in decision.blocker_codes


def test_canary_rejects_unvalidated_harness_cost():
    decision = evaluate_evidence_promotion(
        candidate(
            selected_cost_basis="harness_reported_unvalidated"
        )
    )

    assert not decision.can_advance
    assert (
        "selected_cost_authority_not_qualified"
        in decision.blocker_codes
    )


def test_smoke_exact_authority_can_advance_to_full():
    decision = evaluate_evidence_promotion(
        candidate(
            source_mode="smoke",
            target_mode="full",
            usage_validation_status="validated_exact",
            cost_validation_status="validated_exact",
            selected_cost_relation="exact",
            usage_limitations_recorded=False,
            cost_limitations_recorded=False,
        )
    )

    assert decision.can_advance


def test_smoke_qualified_best_available_can_advance_with_limitations():
    decision = evaluate_evidence_promotion(
        candidate(
            source_mode="smoke",
            target_mode="full",
            usage_validation_status="validated_qualified",
            cost_validation_status="validated_qualified",
            selected_cost_basis="lower_bound_provider_evidence",
            selected_cost_relation="lower_bound",
        )
    )

    assert decision.can_advance


def test_smoke_provisional_cost_blocks_full_sweep():
    decision = evaluate_evidence_promotion(
        candidate(
            source_mode="smoke",
            target_mode="full",
            usage_validation_status="validated_exact",
            cost_validation_status="provisional",
            usage_limitations_recorded=False,
        )
    )

    assert not decision.can_advance
    assert (
        "smoke_cost_not_full_sweep_qualified"
        in decision.blocker_codes
    )


def test_qualified_status_requires_explicit_limitations():
    decision = evaluate_evidence_promotion(
        candidate(
            source_mode="smoke",
            target_mode="full",
            usage_validation_status="validated_qualified",
            cost_validation_status="validated_qualified",
            usage_limitations_recorded=False,
            cost_limitations_recorded=False,
        )
    )

    assert not decision.can_advance
    assert "usage_limitations_not_recorded" in decision.blocker_codes
    assert "cost_limitations_not_recorded" in decision.blocker_codes


def test_model_identity_mismatch_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(model_identity_status="mismatch")
    )

    assert not decision.can_advance
    assert "provider_model_identity_not_matched" in decision.blocker_codes


def test_selected_cost_must_exist():
    decision = evaluate_evidence_promotion(
        candidate(selected_cost_usd=None)
    )

    assert not decision.can_advance
    assert "selected_cost_missing" in decision.blocker_codes


def test_invalid_transition_fails_closed():
    decision = evaluate_evidence_promotion(
        candidate(source_mode="canary", target_mode="full")
    )

    assert not decision.can_advance
    assert "invalid_mode_transition" in decision.blocker_codes


def test_wrong_usage_reconciliation_run_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(
            usage_reconciliation_matches_source_run=False
        )
    )

    assert not decision.can_advance
    assert (
        "usage_reconciliation_wrong_arm_run"
        in decision.blocker_codes
    )


def test_wrong_cost_reconciliation_run_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(
            cost_reconciliation_matches_source_run=False
        )
    )

    assert not decision.can_advance
    assert (
        "cost_reconciliation_wrong_arm_run"
        in decision.blocker_codes
    )


def test_superseded_usage_reconciliation_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(usage_reconciliation_current=False)
    )

    assert not decision.can_advance
    assert (
        "usage_reconciliation_not_current"
        in decision.blocker_codes
    )


def test_superseded_cost_reconciliation_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(cost_reconciliation_current=False)
    )

    assert not decision.can_advance
    assert (
        "cost_reconciliation_not_current"
        in decision.blocker_codes
    )


def test_source_run_arm_mismatch_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(source_run_matches_arm=False)
    )

    assert not decision.can_advance
    assert "source_run_arm_mismatch" in decision.blocker_codes


def test_source_run_mode_mismatch_blocks_progression():
    decision = evaluate_evidence_promotion(
        candidate(source_run_matches_mode=False)
    )

    assert not decision.can_advance
    assert "source_run_mode_mismatch" in decision.blocker_codes


def test_validated_exact_cost_requires_exact_relation():
    decision = evaluate_evidence_promotion(
        candidate(
            source_mode="smoke",
            target_mode="full",
            usage_validation_status="validated_exact",
            cost_validation_status="validated_exact",
            selected_cost_relation="estimate",
            usage_limitations_recorded=False,
            cost_limitations_recorded=False,
        )
    )

    assert not decision.can_advance
    assert (
        "validated_exact_cost_relation_not_exact"
        in decision.blocker_codes
    )


def test_lower_bound_basis_requires_lower_bound_relation():
    decision = evaluate_evidence_promotion(
        candidate(
            selected_cost_basis="lower_bound_provider_evidence",
            selected_cost_relation="estimate",
        )
    )

    assert not decision.can_advance
    assert (
        "lower_bound_basis_relation_mismatch"
        in decision.blocker_codes
    )
