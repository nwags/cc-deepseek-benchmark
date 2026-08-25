from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


VALIDATION_STATUSES = frozenset(
    {
        "validated_exact",
        "validated_qualified",
        "provisional",
        "mismatch",
        "unverified",
        "unavailable",
    }
)

USAGE_AUTHORITIES = frozenset(
    {
        "provider_request_usage",
        "provider_aggregate_usage",
        "harness_usage_validated",
        "none",
    }
)

COST_RELATIONS = frozenset(
    {
        "exact",
        "estimate",
        "lower_bound",
        "unresolved",
    }
)


COST_BASES = frozenset(
    {
        "provider_billed",
        "provider_request_billed",
        "provider_rate_reconstructed_provider_usage",
        "provider_rate_reconstructed_harness_usage_validated",
        "harness_reported_validated",
        "lower_bound_provider_evidence",
        "harness_reported_unvalidated",
        "none",
    }
)

VALID_TRANSITIONS = frozenset(
    {
        ("canary", "smoke"),
        ("smoke", "full"),
    }
)


@dataclass(frozen=True)
class EvidenceQualificationInput:
    source_mode: str
    target_mode: str
    source_run_matches_arm: bool
    source_run_matches_mode: bool
    usage_reconciliation_matches_source_run: bool
    cost_reconciliation_matches_source_run: bool
    usage_reconciliation_current: bool
    cost_reconciliation_current: bool
    usage_provider_evidence_visible: bool
    cost_provider_evidence_visible: bool
    model_identity_status: str
    usage_validation_status: str
    cost_validation_status: str
    selected_usage_authority: str
    selected_cost_basis: str
    selected_cost_relation: str
    selected_cost_usd: Decimal | None
    usage_limitations_recorded: bool = False
    cost_limitations_recorded: bool = False


@dataclass(frozen=True)
class EvidenceQualificationDecision:
    can_advance: bool
    blocker_codes: tuple[str, ...]


def evaluate_evidence_promotion(
    value: EvidenceQualificationInput,
) -> EvidenceQualificationDecision:
    blockers: list[str] = []

    transition = (value.source_mode, value.target_mode)
    if transition not in VALID_TRANSITIONS:
        blockers.append("invalid_mode_transition")

    if not value.source_run_matches_arm:
        blockers.append("source_run_arm_mismatch")

    if not value.source_run_matches_mode:
        blockers.append("source_run_mode_mismatch")

    if not value.usage_reconciliation_matches_source_run:
        blockers.append("usage_reconciliation_wrong_arm_run")

    if not value.cost_reconciliation_matches_source_run:
        blockers.append("cost_reconciliation_wrong_arm_run")

    if not value.usage_reconciliation_current:
        blockers.append("usage_reconciliation_not_current")

    if not value.cost_reconciliation_current:
        blockers.append("cost_reconciliation_not_current")

    if not value.usage_provider_evidence_visible:
        blockers.append("provider_usage_evidence_not_visible")

    if not value.cost_provider_evidence_visible:
        blockers.append("provider_cost_evidence_not_visible")

    if value.model_identity_status != "matched":
        blockers.append("provider_model_identity_not_matched")

    if value.usage_validation_status not in VALIDATION_STATUSES:
        blockers.append("unknown_usage_validation_status")

    if value.cost_validation_status not in VALIDATION_STATUSES:
        blockers.append("unknown_cost_validation_status")

    if value.selected_usage_authority not in USAGE_AUTHORITIES:
        blockers.append("unknown_selected_usage_authority")
    elif value.selected_usage_authority == "none":
        blockers.append("selected_usage_authority_missing")

    if value.selected_cost_basis not in COST_BASES:
        blockers.append("unknown_selected_cost_basis")
    elif value.selected_cost_basis in {
        "none",
        "harness_reported_unvalidated",
    }:
        blockers.append("selected_cost_authority_not_qualified")

    if value.selected_cost_relation not in COST_RELATIONS:
        blockers.append("unknown_selected_cost_relation")
    elif value.selected_cost_relation == "unresolved":
        blockers.append("selected_cost_relation_unresolved")

    if value.selected_cost_usd is None:
        blockers.append("selected_cost_missing")

    if (
        value.cost_validation_status == "validated_exact"
        and value.selected_cost_relation != "exact"
    ):
        blockers.append(
            "validated_exact_cost_relation_not_exact"
        )

    if (
        value.selected_cost_basis
        == "lower_bound_provider_evidence"
        and value.selected_cost_relation != "lower_bound"
    ):
        blockers.append(
            "lower_bound_basis_relation_mismatch"
        )

    if value.usage_validation_status in {
        "validated_qualified",
        "provisional",
    } and not value.usage_limitations_recorded:
        blockers.append("usage_limitations_not_recorded")

    if value.cost_validation_status in {
        "validated_qualified",
        "provisional",
    } and not value.cost_limitations_recorded:
        blockers.append("cost_limitations_not_recorded")

    if transition == ("canary", "smoke"):
        allowed = {
            "validated_exact",
            "validated_qualified",
            "provisional",
        }
        if value.usage_validation_status not in allowed:
            blockers.append("canary_usage_not_smoke_eligible")
        if value.cost_validation_status not in allowed:
            blockers.append("canary_cost_not_smoke_eligible")

    if transition == ("smoke", "full"):
        allowed = {
            "validated_exact",
            "validated_qualified",
        }
        if value.usage_validation_status not in allowed:
            blockers.append("smoke_usage_not_full_sweep_qualified")
        if value.cost_validation_status not in allowed:
            blockers.append("smoke_cost_not_full_sweep_qualified")

    return EvidenceQualificationDecision(
        can_advance=not blockers,
        blocker_codes=tuple(dict.fromkeys(blockers)),
    )
