from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/review_evidence_promotion.py"

spec = importlib.util.spec_from_file_location(
    "review_evidence_promotion",
    SCRIPT,
)
assert spec is not None
assert spec.loader is not None

review = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = review
spec.loader.exec_module(review)


ARM_RUN_ID = "11111111-1111-4111-8111-111111111111"
USAGE_ID = "22222222-2222-4222-8222-222222222222"
COST_ID = "33333333-3333-4333-8333-333333333333"
GATE_ID = "44444444-4444-4444-8444-444444444444"
NEW_GATE_ID = "55555555-5555-4555-8555-555555555555"


def args(
    *,
    mode: str = "--plan",
    target: str = "smoke",
    decision: str = "pass",
    extra: list[str] | None = None,
) -> list[str]:
    values = [
        mode,
        "--arm-id",
        "router-gpt-5.5",
        "--source-arm-run-id",
        ARM_RUN_ID,
        "--target-mode",
        target,
        "--decision",
        decision,
        "--reviewed-by",
        "reviewer@example",
    ]
    values.extend(extra or [])
    return values


def request(**kwargs):
    values = {
        "mode": "check-only",
        "arm_id": "router-gpt-5.5",
        "source_arm_run_id": ARM_RUN_ID,
        "source_mode": "canary",
        "target_mode": "smoke",
        "decision": "pass",
        "blocker_codes": (),
        "waiver_reason": None,
        "reviewed_by": "reviewer@example",
        "notes": None,
        "expected_usage_reconciliation_id": None,
        "expected_cost_reconciliation_id": None,
        "expected_current_gate_id": None,
        "expected_state_sha256": None,
        "current_gate_pin_was_supplied": False,
    }
    values.update(kwargs)
    return review.ReviewRequest(**values)


def chain(**kwargs):
    values = {
        "source_arm_run_id": ARM_RUN_ID,
        "arm_id": "router-gpt-5.5",
        "logical_mode": "canary",
        "suite_id": "phase3-canary-1",
        "status": "completed",
        "usage_reconciliation_id": USAGE_ID,
        "usage_validation_status": "validated_exact",
        "usage_provider_evidence_visible": True,
        "model_identity_status": "matched",
        "selected_usage_authority": "provider_aggregate_usage",
        "usage_limitation_codes": [],
        "cost_reconciliation_id": COST_ID,
        "cost_validation_status": "validated_exact",
        "cost_provider_evidence_visible": True,
        "selected_cost_usd": "1.25",
        "selected_cost_basis": "provider_billed",
        "selected_cost_relation": "exact",
        "cost_limitation_codes": [],
    }
    values.update(kwargs)
    return values


def view(**kwargs):
    values = {
        "gate_id": NEW_GATE_ID,
        "arm_id": "router-gpt-5.5",
        "source_arm_run_id": ARM_RUN_ID,
        "source_mode": "canary",
        "target_mode": "smoke",
        "usage_reconciliation_id": USAGE_ID,
        "cost_reconciliation_id": COST_ID,
        "decision": "pass",
        "blocker_codes": [],
        "derived_blocker_codes": [],
        "waiver_reason": None,
        "effective_can_advance": True,
        "reviewed_by": "reviewer@example",
        "reviewed_at": "2026-08-30 10:00:00-04",
        "usage_validation_status": "validated_exact",
        "selected_usage_authority": "provider_aggregate_usage",
        "cost_validation_status": "validated_exact",
        "selected_cost_usd": "1.25",
        "selected_cost_basis": "provider_billed",
        "selected_cost_relation": "exact",
    }
    values.update(kwargs)
    return values


def history_row(
    gate_id: str,
    *,
    is_current: bool,
) -> dict[str, object]:
    return {
        "gate_id": gate_id,
        "arm_id": "router-gpt-5.5",
        "source_arm_run_id": ARM_RUN_ID,
        "source_mode": "canary",
        "target_mode": "smoke",
        "usage_reconciliation_id": USAGE_ID,
        "cost_reconciliation_id": COST_ID,
        "decision": "pass",
        "blocker_codes": [],
        "waiver_reason": None,
        "reviewed_by": "reviewer@example",
        "reviewed_at": "2026-08-30 10:00:00-04",
        "is_current": is_current,
        "notes": None,
        "raw_metadata": "{}",
        "created_at": "2026-08-30 10:00:00-04",
    }


def test_cli_requires_exactly_one_explicit_mode():
    with pytest.raises(SystemExit):
        review.parse_args([])

    with pytest.raises(SystemExit):
        review.parse_args(
            args(mode="--plan") + ["--check-only"]
        )


def test_target_mode_determines_only_legal_source_mode():
    smoke = review.request_from_args(
        review.parse_args(args(target="smoke"))
    )
    full = review.request_from_args(
        review.parse_args(args(target="full"))
    )

    assert smoke.source_mode == "canary"
    assert full.source_mode == "smoke"


def test_pass_rejects_reviewed_blockers_and_waiver_reason():
    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(
                    extra=[
                        "--blocker-code",
                        "manual_blocker",
                    ]
                )
            )
        )

    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(
                    extra=[
                        "--waiver-reason",
                        "not applicable to pass",
                    ]
                )
            )
        )


def test_blocked_requires_explicit_blocker_codes():
    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(decision="blocked")
            )
        )

    parsed = review.request_from_args(
        review.parse_args(
            args(
                decision="blocked",
                extra=[
                    "--blocker-code",
                    "qualitative_review_failed",
                ],
            )
        )
    )

    assert parsed.blocker_codes == (
        "qualitative_review_failed",
    )


def test_waived_requires_reason_and_never_implies_pass():
    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(decision="waived")
            )
        )

    parsed = review.request_from_args(
        review.parse_args(
            args(
                decision="waived",
                extra=[
                    "--waiver-reason",
                    "documented manual exception",
                ],
            )
        )
    )

    assert parsed.waiver_reason == (
        "documented manual exception"
    )


def test_blocker_codes_are_deterministic_and_restricted():
    parsed = review.request_from_args(
        review.parse_args(
            args(
                decision="blocked",
                extra=[
                    "--blocker-code",
                    "z_blocker",
                    "--blocker-code",
                    "a_blocker",
                    "--blocker-code",
                    "a_blocker",
                ],
            )
        )
    )

    assert parsed.blocker_codes == (
        "a_blocker",
        "z_blocker",
    )

    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(
                    decision="blocked",
                    extra=[
                        "--blocker-code",
                        "unsafe blocker text",
                    ],
                )
            )
        )


def test_mutation_modes_require_all_exact_pins():
    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(mode="--apply")
            )
        )

    parsed = review.request_from_args(
        review.parse_args(
            args(
                mode="--rollback-only",
                extra=[
                    "--expected-usage-reconciliation-id",
                    USAGE_ID,
                    "--expected-cost-reconciliation-id",
                    COST_ID,
                    "--expected-current-gate-id",
                    "none",
                    "--expected-state-sha256",
                    "a" * 64,
                ],
            )
        )
    )

    assert parsed.expected_usage_reconciliation_id == USAGE_ID
    assert parsed.expected_cost_reconciliation_id == COST_ID
    assert parsed.expected_current_gate_id is None
    assert parsed.expected_state_sha256 == "a" * 64
    assert parsed.current_gate_pin_was_supplied is True


def test_plan_and_check_only_reject_mutation_pins():
    for mode in ("--plan", "--check-only"):
        with pytest.raises(review.ArgumentContractError):
            review.request_from_args(
                review.parse_args(
                    args(
                        mode=mode,
                        extra=[
                            "--expected-usage-reconciliation-id",
                            USAGE_ID,
                        ],
                    )
                )
            )


def test_plan_mode_has_no_database_dependency(
    monkeypatch,
    capsys,
):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    assert review.main(args(mode="--plan")) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["database_access"] is False
    assert result["mutation_contract"][
        "check_only_first"
    ] is True
    assert result["mutation_contract"][
        "waiver_becomes_effective_pass"
    ] is False


def test_database_modes_fail_safely_without_environment(
    monkeypatch,
    capsys,
):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    assert review.main(args(mode="--check-only")) == 2

    result = json.loads(capsys.readouterr().out)
    assert result["error_type"] == "MissingEnvironmentError"
    assert "SUPABASE_DB_URL" not in result


def test_canary_provisional_evidence_is_smoke_eligible():
    req = request()
    candidate = chain(
        usage_validation_status="provisional",
        cost_validation_status="provisional",
    )

    assert review.derive_evidence_blockers(
        req,
        candidate,
    ) == ()


def test_smoke_provisional_evidence_is_not_full_eligible():
    req = request(
        source_mode="smoke",
        target_mode="full",
    )
    candidate = chain(
        logical_mode="smoke",
        usage_validation_status="provisional",
        cost_validation_status="provisional",
    )

    assert review.derive_evidence_blockers(
        req,
        candidate,
    ) == (
        "smoke_usage_not_full_sweep_qualified",
        "smoke_cost_not_full_sweep_qualified",
    )


def test_evidence_authority_failures_are_explicit():
    blockers = review.derive_evidence_blockers(
        request(),
        chain(
            usage_provider_evidence_visible=False,
            cost_provider_evidence_visible=False,
            model_identity_status="mismatch",
            selected_usage_authority="none",
            selected_cost_usd=None,
            selected_cost_basis="none",
            selected_cost_relation="unresolved",
        ),
    )

    assert set(blockers) == {
        "provider_usage_evidence_not_visible",
        "provider_cost_evidence_not_visible",
        "provider_model_identity_not_matched",
        "selected_usage_authority_missing",
        "selected_cost_missing",
        "selected_cost_basis_missing",
        "selected_cost_relation_unresolved",
    }


def test_pass_refuses_unqualified_evidence():
    with pytest.raises(review.NotRecordableError):
        review.assert_recordable(
            request(),
            ("selected_cost_missing",),
        )


def test_blocked_and_waived_can_record_non_pass_provenance():
    for decision in ("blocked", "waived"):
        review.assert_recordable(
            request(decision=decision),
            ("selected_cost_missing",),
        )


def test_exact_mutation_pins_detect_changed_chain_or_gate():
    current = history_row(
        GATE_ID,
        is_current=True,
    )
    candidate = chain()
    fingerprint = review.review_state_sha256(
        candidate,
        current,
    )

    req = request(
        mode="apply",
        expected_usage_reconciliation_id=USAGE_ID,
        expected_cost_reconciliation_id=COST_ID,
        expected_current_gate_id=GATE_ID,
        expected_state_sha256=fingerprint,
        current_gate_pin_was_supplied=True,
    )

    review.assert_mutation_pins(
        req,
        candidate,
        current,
    )

    with pytest.raises(review.IntegrationSafetyError):
        review.assert_mutation_pins(
            req,
            chain(
                usage_reconciliation_id=NEW_GATE_ID
            ),
            current,
        )

    changed_gate = dict(current)
    changed_gate["gate_id"] = NEW_GATE_ID

    with pytest.raises(review.IntegrationSafetyError):
        review.assert_mutation_pins(
            req,
            chain(),
            changed_gate,
        )

    with pytest.raises(review.IntegrationSafetyError):
        review.assert_mutation_pins(
            req,
            chain(selected_cost_usd="1.26"),
            current,
        )

    changed_gate_same_id = dict(current)
    changed_gate_same_id["reviewed_by"] = "different-reviewer"

    with pytest.raises(review.IntegrationSafetyError):
        review.assert_mutation_pins(
            req,
            chain(),
            changed_gate_same_id,
        )


def test_inserted_pass_must_be_effective_and_blocker_free():
    result = review.verify_inserted_view(
        request(),
        chain(),
        gate_id=NEW_GATE_ID,
        view=view(),
    )

    assert result["effective_can_advance"] is True

    with pytest.raises(review.IntegrationSafetyError):
        review.verify_inserted_view(
            request(),
            chain(),
            gate_id=NEW_GATE_ID,
            view=view(
                derived_blocker_codes=[
                    "cost_reconciliation_not_current"
                ],
                effective_can_advance=False,
            ),
        )


def test_waiver_is_verified_as_non_authorizing():
    req = request(
        decision="waived",
        waiver_reason="manual exception",
    )
    result = review.verify_inserted_view(
        req,
        chain(),
        gate_id=NEW_GATE_ID,
        view=view(
            decision="waived",
            waiver_reason="manual exception",
            derived_blocker_codes=[
                "gate_decision_not_pass",
            ],
            effective_can_advance=False,
        ),
    )

    assert result["effective_can_advance"] is False
    assert "gate_decision_not_pass" in (
        result["derived_blocker_codes"]
    )


def test_blocked_review_requires_derived_non_pass_state():
    req = request(
        decision="blocked",
        blocker_codes=("qualitative_review_failed",),
    )

    result = review.verify_inserted_view(
        req,
        chain(),
        gate_id=NEW_GATE_ID,
        view=view(
            decision="blocked",
            blocker_codes=[
                "qualitative_review_failed",
            ],
            derived_blocker_codes=[
                "gate_decision_not_pass",
                "reviewed_blockers_present",
            ],
            effective_can_advance=False,
        ),
    )

    assert result["effective_can_advance"] is False


def test_persisted_history_preserves_prior_rows():
    before = [
        history_row(
            GATE_ID,
            is_current=True,
        )
    ]
    after_old = history_row(
        GATE_ID,
        is_current=False,
    )
    after_new = history_row(
        NEW_GATE_ID,
        is_current=True,
    )

    review.verify_persisted_history(
        before,
        [after_old, after_new],
        previous_gate_id=GATE_ID,
        new_gate_id=NEW_GATE_ID,
    )


def test_history_verification_rejects_unrelated_changes():
    before = [
        history_row(
            GATE_ID,
            is_current=True,
        )
    ]
    changed = history_row(
        GATE_ID,
        is_current=False,
    )
    changed["notes"] = "unexpected mutation"
    added = history_row(
        NEW_GATE_ID,
        is_current=True,
    )

    with pytest.raises(review.IntegrationSafetyError):
        review.verify_persisted_history(
            before,
            [changed, added],
            previous_gate_id=GATE_ID,
            new_gate_id=NEW_GATE_ID,
        )


def test_state_fingerprint_binds_material_review_state():
    current = history_row(
        GATE_ID,
        is_current=True,
    )
    candidate = chain()

    baseline = review.review_state_sha256(
        candidate,
        current,
    )

    assert len(baseline) == 64

    assert review.review_state_sha256(
        chain(selected_cost_usd="1.2500001"),
        current,
    ) != baseline

    changed_gate = dict(current)
    changed_gate["reviewed_at"] = "2026-08-30 10:01:00-04"

    assert review.review_state_sha256(
        candidate,
        changed_gate,
    ) != baseline

    changed_metadata = dict(current)
    changed_metadata["raw_metadata"] = '{"changed":true}'

    assert review.review_state_sha256(
        candidate,
        changed_metadata,
    ) != baseline


def test_state_fingerprint_normalizes_set_like_code_order():
    current_a = history_row(
        GATE_ID,
        is_current=True,
    )
    current_b = dict(current_a)

    current_a["blocker_codes"] = ["b", "a"]
    current_b["blocker_codes"] = ["a", "b"]

    chain_a = chain(
        usage_limitation_codes=["u2", "u1"],
        cost_limitation_codes=["c2", "c1"],
    )
    chain_b = chain(
        usage_limitation_codes=["u1", "u2"],
        cost_limitation_codes=["c1", "c2"],
    )

    assert review.review_state_sha256(
        chain_a,
        current_a,
    ) == review.review_state_sha256(
        chain_b,
        current_b,
    )


def test_public_current_gate_omits_arbitrary_stored_text():
    current = history_row(
        GATE_ID,
        is_current=True,
    )
    current["notes"] = "operator free-form text"
    current["raw_metadata"] = '{"opaque":"value"}'

    public = review.public_current_gate(current)

    assert public is not None
    assert "notes" not in public
    assert "raw_metadata" not in public
    assert public["notes_present"] is True
    assert public["raw_metadata_present"] is True


def test_expected_state_sha256_is_strictly_validated():
    parsed = review.request_from_args(
        review.parse_args(
            args(
                mode="--apply",
                extra=[
                    "--expected-usage-reconciliation-id",
                    USAGE_ID,
                    "--expected-cost-reconciliation-id",
                    COST_ID,
                    "--expected-current-gate-id",
                    "none",
                    "--expected-state-sha256",
                    "A" * 64,
                ],
            )
        )
    )

    assert parsed.expected_state_sha256 == "a" * 64

    with pytest.raises(review.ArgumentContractError):
        review.request_from_args(
            review.parse_args(
                args(
                    mode="--apply",
                    extra=[
                        "--expected-usage-reconciliation-id",
                        USAGE_ID,
                        "--expected-cost-reconciliation-id",
                        COST_ID,
                        "--expected-current-gate-id",
                        "none",
                        "--expected-state-sha256",
                        "not-a-sha256",
                    ],
                )
            )
        )


def test_failure_payload_never_exposes_exception_message():
    diagnostics = review.Diagnostics(
        stage="locked_preflight"
    )
    exc = RuntimeError(
        "do not expose database or credential details"
    )

    result = review.failure_payload(
        mode="apply",
        diagnostics=diagnostics,
        exc=exc,
    )

    serialized = json.dumps(result)
    assert "do not expose" not in serialized
    assert result["failed_stage"] == "locked_preflight"


def test_static_script_has_single_commit_and_no_delete_surface():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert source.count("connection.commit()") == 1
    assert "delete from" not in source
    assert (
        "repeatable read, read only"
        in source
    )
    assert "--expected-state-sha256" in source
    assert "pg_advisory_xact_lock" in source
    assert "--plan" in source
    assert "--check-only" in source
    assert "--rollback-only" in source
    assert "--apply" in source


def test_static_write_surface_is_promotion_gate_only():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert (
        "insert into "
        "benchmark.benchmark_evidence_promotion_gates"
    ) in source
    assert (
        "update benchmark."
        "benchmark_evidence_promotion_gates"
    ) in source

    forbidden_tables = (
        "benchmark.benchmark_runs",
        "benchmark.benchmark_arm_runs",
        "benchmark.benchmark_trials",
        "benchmark.benchmark_usage_reconciliations",
        "benchmark.benchmark_cost_reconciliations",
        "benchmark.benchmark_provider_evidence_sources",
    )

    for table in forbidden_tables:
        assert f"insert into {table}" not in source
        assert f"update {table}" not in source
        assert f"delete from {table}" not in source


def test_reviewed_timestamp_is_database_generated():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "clock_timestamp()" in source
    assert "--reviewed-at" not in source


def test_no_dashboard_or_workflow_mutation_dependency():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert "github workflow" not in source
    assert "workflow_dispatch" not in source
    assert "apps/dashboard" not in source
