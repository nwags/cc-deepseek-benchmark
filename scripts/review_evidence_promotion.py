#!/usr/bin/env python3
"""Review and durably record Phase 3 evidence-promotion decisions.

The CLI deliberately separates planning, read-only inspection, rollback-only
verification, and permanent application. Mutation modes require exact IDs
copied from a prior check-only result so a reviewer cannot silently act on an
evidence chain or current gate that changed after inspection.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import re
from typing import Any, Mapping, Sequence
import uuid


TOOL_VERSION = "phase3-promotion-review-v1"
LOCK_PREFIX = "cc-deepseek-bench:evidence-promotion:v1"

TARGET_SOURCE_MODES = {
    "smoke": "canary",
    "full": "smoke",
}

CANARY_ELIGIBLE_STATUSES = frozenset(
    {
        "validated_exact",
        "validated_qualified",
        "provisional",
    }
)
FULL_ELIGIBLE_STATUSES = frozenset(
    {
        "validated_exact",
        "validated_qualified",
    }
)

BLOCKER_CODE_RE = re.compile(
    r"^[a-z0-9][a-z0-9_.:-]{0,127}$"
)


class PromotionReviewError(RuntimeError):
    """Base error for safe promotion-review failures."""


class ArgumentContractError(PromotionReviewError):
    """The requested review does not satisfy CLI semantics."""


class IntegrationSafetyError(PromotionReviewError):
    """Database state differs from the reviewed/pinned state."""


class MissingEnvironmentError(PromotionReviewError):
    """Required database configuration is unavailable."""


class NotRecordableError(PromotionReviewError):
    """A requested pass cannot be recorded on this evidence chain."""

    def __init__(self, blockers: Sequence[str]) -> None:
        super().__init__("promotion decision is not recordable")
        self.blockers = tuple(blockers)


@dataclass
class Diagnostics:
    stage: str = "arguments"
    commit_state: str = "not_committed"

    def enter(self, stage: str) -> None:
        self.stage = stage


@dataclass(frozen=True)
class ReviewRequest:
    mode: str
    arm_id: str
    source_arm_run_id: str
    source_mode: str
    target_mode: str
    decision: str
    blocker_codes: tuple[str, ...]
    waiver_reason: str | None
    reviewed_by: str
    notes: str | None
    expected_usage_reconciliation_id: str | None
    expected_cost_reconciliation_id: str | None
    expected_current_gate_id: str | None
    expected_state_sha256: str | None
    current_gate_pin_was_supplied: bool


def _clean_required(
    value: str,
    *,
    label: str,
    limit: int,
) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ArgumentContractError(f"{label} must not be empty")
    if len(cleaned) > limit:
        raise ArgumentContractError(f"{label} is too long")
    return cleaned


def _clean_optional(
    value: str | None,
    *,
    label: str,
    limit: int,
) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise ArgumentContractError(f"{label} is too long")
    return cleaned


def _canonical_uuid(value: str, *, label: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ArgumentContractError(
            f"{label} must be a UUID"
        ) from exc
    return str(parsed)


def _canonical_expected_gate(value: str) -> str | None:
    cleaned = value.strip().lower()
    if cleaned == "none":
        return None
    return _canonical_uuid(
        value,
        label="expected current gate id",
    )


def _canonical_sha256(value: str) -> str:
    cleaned = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", cleaned):
        raise ArgumentContractError(
            "expected state SHA-256 must be 64 hexadecimal characters"
        )
    return cleaned


def _normalize_blockers(
    values: Sequence[str],
) -> tuple[str, ...]:
    cleaned: list[str] = []

    for raw in values:
        value = raw.strip()
        if not BLOCKER_CODE_RE.fullmatch(value):
            raise ArgumentContractError(
                "blocker codes must use lowercase letters, digits, "
                "'.', '_', ':', or '-'"
            )
        if value not in cleaned:
            cleaned.append(value)

    return tuple(sorted(cleaned))


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--plan",
        action="store_true",
        help="Validate and print the requested decision without a DB.",
    )
    modes.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Read the exact source/evidence/current-gate state in a "
            "read-only transaction and emit mutation pins."
        ),
    )
    modes.add_argument(
        "--rollback-only",
        action="store_true",
        help=(
            "Apply the pinned review in one transaction, verify it, "
            "roll back, then prove the prior gate history was restored."
        ),
    )
    modes.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply the pinned review, commit once, and verify the "
            "persisted current gate from a second connection."
        ),
    )

    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--source-arm-run-id", required=True)
    parser.add_argument(
        "--target-mode",
        required=True,
        choices=tuple(TARGET_SOURCE_MODES),
    )
    parser.add_argument(
        "--decision",
        required=True,
        choices=("pass", "blocked", "waived"),
    )
    parser.add_argument(
        "--blocker-code",
        action="append",
        default=[],
    )
    parser.add_argument("--waiver-reason")
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--notes")

    parser.add_argument("--expected-usage-reconciliation-id")
    parser.add_argument("--expected-cost-reconciliation-id")
    parser.add_argument(
        "--expected-current-gate-id",
        help=(
            "Exact current gate UUID reported by --check-only, or "
            "the literal 'none' when no current gate existed."
        ),
    )
    parser.add_argument(
        "--expected-state-sha256",
        help=(
            "Exact state fingerprint reported by --check-only. "
            "Mutation modes fail closed if any material reviewed "
            "source/reconciliation/current-gate field changed."
        ),
    )

    return parser.parse_args(argv)


def request_from_args(
    args: argparse.Namespace,
) -> ReviewRequest:
    if args.plan:
        mode = "plan"
    elif args.check_only:
        mode = "check-only"
    elif args.rollback_only:
        mode = "rollback-only"
    else:
        mode = "apply"

    arm_id = _clean_required(
        args.arm_id,
        label="arm id",
        limit=200,
    )
    source_arm_run_id = _canonical_uuid(
        args.source_arm_run_id,
        label="source arm-run id",
    )
    reviewed_by = _clean_required(
        args.reviewed_by,
        label="reviewed by",
        limit=200,
    )
    notes = _clean_optional(
        args.notes,
        label="notes",
        limit=4000,
    )
    waiver_reason = _clean_optional(
        args.waiver_reason,
        label="waiver reason",
        limit=2000,
    )
    blocker_codes = _normalize_blockers(
        args.blocker_code
    )

    if args.decision == "pass":
        if blocker_codes:
            raise ArgumentContractError(
                "pass decisions cannot contain reviewed blockers"
            )
        if waiver_reason is not None:
            raise ArgumentContractError(
                "pass decisions cannot contain a waiver reason"
            )

    elif args.decision == "blocked":
        if not blocker_codes:
            raise ArgumentContractError(
                "blocked decisions require at least one blocker code"
            )
        if waiver_reason is not None:
            raise ArgumentContractError(
                "blocked decisions cannot contain a waiver reason"
            )

    elif args.decision == "waived":
        if waiver_reason is None:
            raise ArgumentContractError(
                "waived decisions require a non-empty waiver reason"
            )

    pin_values = (
        args.expected_usage_reconciliation_id,
        args.expected_cost_reconciliation_id,
        args.expected_current_gate_id,
        args.expected_state_sha256,
    )
    mutation_mode = mode in {"rollback-only", "apply"}

    if mutation_mode:
        if any(value is None for value in pin_values):
            raise ArgumentContractError(
                "mutation modes require expected usage, cost, and "
                "current-gate pins from --check-only"
            )

        expected_usage = _canonical_uuid(
            args.expected_usage_reconciliation_id,
            label="expected usage reconciliation id",
        )
        expected_cost = _canonical_uuid(
            args.expected_cost_reconciliation_id,
            label="expected cost reconciliation id",
        )
        expected_gate = _canonical_expected_gate(
            args.expected_current_gate_id
        )
        expected_state_sha256 = _canonical_sha256(
            args.expected_state_sha256
        )
        current_gate_pin_was_supplied = True

    else:
        if any(value is not None for value in pin_values):
            raise ArgumentContractError(
                "expected mutation pins are accepted only by "
                "--rollback-only or --apply"
            )

        expected_usage = None
        expected_cost = None
        expected_gate = None
        expected_state_sha256 = None
        current_gate_pin_was_supplied = False

    return ReviewRequest(
        mode=mode,
        arm_id=arm_id,
        source_arm_run_id=source_arm_run_id,
        source_mode=TARGET_SOURCE_MODES[args.target_mode],
        target_mode=args.target_mode,
        decision=args.decision,
        blocker_codes=blocker_codes,
        waiver_reason=waiver_reason,
        reviewed_by=reviewed_by,
        notes=notes,
        expected_usage_reconciliation_id=expected_usage,
        expected_cost_reconciliation_id=expected_cost,
        expected_current_gate_id=expected_gate,
        expected_state_sha256=expected_state_sha256,
        current_gate_pin_was_supplied=current_gate_pin_was_supplied,
    )


def build_plan(
    request: ReviewRequest,
) -> dict[str, Any]:
    return {
        "status": "planned",
        "mode": request.mode,
        "tool_version": TOOL_VERSION,
        "database_access": False,
        "arm_id": request.arm_id,
        "source_arm_run_id": request.source_arm_run_id,
        "transition": {
            "source_mode": request.source_mode,
            "target_mode": request.target_mode,
        },
        "review": {
            "decision": request.decision,
            "blocker_codes": list(request.blocker_codes),
            "waiver_reason": request.waiver_reason,
            "reviewed_by": request.reviewed_by,
            "notes": request.notes,
        },
        "mutation_contract": {
            "check_only_first": True,
            "exact_usage_reconciliation_pin_required": True,
            "exact_cost_reconciliation_pin_required": True,
            "exact_current_gate_pin_required": True,
            "exact_state_sha256_required": True,
            "prior_decisions_are_preserved": True,
            "waiver_becomes_effective_pass": False,
        },
    }


def connect_db(db_url: str) -> Any:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(
        db_url,
        autocommit=False,
        row_factory=dict_row,
    )


def _fetch_exactly_one(
    cursor: Any,
    *,
    label: str,
) -> Mapping[str, Any]:
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise IntegrationSafetyError(
            f"{label} did not resolve exactly one row"
        )
    return rows[0]


def read_evidence_chain(
    cursor: Any,
    request: ReviewRequest,
    *,
    lock: bool,
) -> dict[str, Any]:
    arm_lock = " for share" if lock else ""
    reconciliation_lock = " for update" if lock else ""

    cursor.execute(
        f"""
        select
            id::text as source_arm_run_id,
            arm_id,
            logical_mode,
            suite_id,
            status
        from benchmark.benchmark_arm_runs
        where id = %s::uuid
        {arm_lock}
        """,
        (request.source_arm_run_id,),
    )
    arm_run = _fetch_exactly_one(
        cursor,
        label="source arm run",
    )

    if arm_run["arm_id"] != request.arm_id:
        raise IntegrationSafetyError(
            "source arm run belongs to a different arm"
        )
    if arm_run["logical_mode"] != request.source_mode:
        raise IntegrationSafetyError(
            "source arm run has the wrong logical mode"
        )

    cursor.execute(
        f"""
        select
            id::text as usage_reconciliation_id,
            validation_status as usage_validation_status,
            provider_evidence_visible
                as usage_provider_evidence_visible,
            model_identity_status,
            selected_usage_authority,
            limitation_codes as usage_limitation_codes
        from benchmark.benchmark_usage_reconciliations
        where arm_run_id = %s::uuid
          and is_current
        {reconciliation_lock}
        """,
        (request.source_arm_run_id,),
    )
    usage = _fetch_exactly_one(
        cursor,
        label="current usage reconciliation",
    )

    cursor.execute(
        f"""
        select
            id::text as cost_reconciliation_id,
            validation_status as cost_validation_status,
            provider_evidence_visible
                as cost_provider_evidence_visible,
            selected_cost_usd::text as selected_cost_usd,
            selected_cost_basis,
            selected_cost_relation,
            limitation_codes as cost_limitation_codes
        from benchmark.benchmark_cost_reconciliations
        where arm_run_id = %s::uuid
          and is_current
        {reconciliation_lock}
        """,
        (request.source_arm_run_id,),
    )
    cost = _fetch_exactly_one(
        cursor,
        label="current cost reconciliation",
    )

    return {
        **dict(arm_run),
        **dict(usage),
        **dict(cost),
    }


def derive_evidence_blockers(
    request: ReviewRequest,
    chain: Mapping[str, Any],
) -> tuple[str, ...]:
    blockers: list[str] = []

    if chain["usage_provider_evidence_visible"] is not True:
        blockers.append("provider_usage_evidence_not_visible")

    if chain["cost_provider_evidence_visible"] is not True:
        blockers.append("provider_cost_evidence_not_visible")

    if chain["model_identity_status"] != "matched":
        blockers.append("provider_model_identity_not_matched")

    if chain["selected_usage_authority"] in {None, "none"}:
        blockers.append("selected_usage_authority_missing")

    if chain["selected_cost_usd"] is None:
        blockers.append("selected_cost_missing")

    if chain["selected_cost_basis"] in {None, "none"}:
        blockers.append("selected_cost_basis_missing")

    if chain["selected_cost_relation"] in {None, "unresolved"}:
        blockers.append("selected_cost_relation_unresolved")

    usage_status = chain["usage_validation_status"]
    cost_status = chain["cost_validation_status"]

    if request.target_mode == "smoke":
        if usage_status not in CANARY_ELIGIBLE_STATUSES:
            blockers.append("canary_usage_not_smoke_eligible")
        if cost_status not in CANARY_ELIGIBLE_STATUSES:
            blockers.append("canary_cost_not_smoke_eligible")

    else:
        if usage_status not in FULL_ELIGIBLE_STATUSES:
            blockers.append(
                "smoke_usage_not_full_sweep_qualified"
            )
        if cost_status not in FULL_ELIGIBLE_STATUSES:
            blockers.append(
                "smoke_cost_not_full_sweep_qualified"
            )

    return tuple(blockers)


def read_current_gate(
    cursor: Any,
    *,
    arm_id: str,
    target_mode: str,
    lock: bool,
) -> dict[str, Any] | None:
    lock_clause = " for update" if lock else ""

    cursor.execute(
        f"""
        select
            id::text as gate_id,
            arm_id,
            source_arm_run_id::text,
            source_mode,
            target_mode,
            usage_reconciliation_id::text,
            cost_reconciliation_id::text,
            decision,
            blocker_codes,
            waiver_reason,
            reviewed_by,
            reviewed_at::text,
            is_current,
            notes,
            raw_metadata::text,
            created_at::text
        from benchmark.benchmark_evidence_promotion_gates
        where arm_id = %s
          and target_mode = %s
          and is_current
        {lock_clause}
        """,
        (arm_id, target_mode),
    )

    rows = cursor.fetchall()
    if len(rows) > 1:
        raise IntegrationSafetyError(
            "multiple current promotion gates exist"
        )
    if not rows:
        return None
    return dict(rows[0])


def snapshot_gate_history(
    cursor: Any,
    *,
    arm_id: str,
    target_mode: str,
) -> list[dict[str, Any]]:
    cursor.execute(
        """
        select
            id::text as gate_id,
            arm_id,
            source_arm_run_id::text,
            source_mode,
            target_mode,
            usage_reconciliation_id::text,
            cost_reconciliation_id::text,
            decision,
            blocker_codes,
            waiver_reason,
            reviewed_by,
            reviewed_at::text,
            is_current,
            notes,
            raw_metadata::text,
            created_at::text
        from benchmark.benchmark_evidence_promotion_gates
        where arm_id = %s
          and target_mode = %s
        order by id
        """,
        (arm_id, target_mode),
    )
    return [dict(row) for row in cursor.fetchall()]


def review_state_payload(
    chain: Mapping[str, Any],
    current_gate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    gate_payload: dict[str, Any] | None

    if current_gate is None:
        gate_payload = None
    else:
        gate_payload = {
            "gate_id": current_gate["gate_id"],
            "arm_id": current_gate["arm_id"],
            "source_arm_run_id":
                current_gate["source_arm_run_id"],
            "source_mode": current_gate["source_mode"],
            "target_mode": current_gate["target_mode"],
            "usage_reconciliation_id":
                current_gate["usage_reconciliation_id"],
            "cost_reconciliation_id":
                current_gate["cost_reconciliation_id"],
            "decision": current_gate["decision"],
            "blocker_codes": sorted(
                str(value)
                for value in (
                    current_gate["blocker_codes"] or []
                )
            ),
            "waiver_reason": current_gate["waiver_reason"],
            "reviewed_by": current_gate["reviewed_by"],
            "reviewed_at": current_gate["reviewed_at"],
            "is_current": current_gate["is_current"],
            "notes": current_gate["notes"],
            "raw_metadata": current_gate["raw_metadata"],
            "created_at": current_gate["created_at"],
        }

    return {
        "source_run": {
            "source_arm_run_id":
                chain["source_arm_run_id"],
            "arm_id": chain["arm_id"],
            "logical_mode": chain["logical_mode"],
            "suite_id": chain["suite_id"],
            "status": chain["status"],
        },
        "usage_reconciliation": {
            "usage_reconciliation_id":
                chain["usage_reconciliation_id"],
            "usage_validation_status":
                chain["usage_validation_status"],
            "usage_provider_evidence_visible":
                chain["usage_provider_evidence_visible"],
            "model_identity_status":
                chain["model_identity_status"],
            "selected_usage_authority":
                chain["selected_usage_authority"],
            "usage_limitation_codes": sorted(
                str(value)
                for value in (
                    chain["usage_limitation_codes"] or []
                )
            ),
        },
        "cost_reconciliation": {
            "cost_reconciliation_id":
                chain["cost_reconciliation_id"],
            "cost_validation_status":
                chain["cost_validation_status"],
            "cost_provider_evidence_visible":
                chain["cost_provider_evidence_visible"],
            "selected_cost_usd":
                chain["selected_cost_usd"],
            "selected_cost_basis":
                chain["selected_cost_basis"],
            "selected_cost_relation":
                chain["selected_cost_relation"],
            "cost_limitation_codes": sorted(
                str(value)
                for value in (
                    chain["cost_limitation_codes"] or []
                )
            ),
        },
        "current_gate": gate_payload,
    }


def review_state_sha256(
    chain: Mapping[str, Any],
    current_gate: Mapping[str, Any] | None,
) -> str:
    payload = review_state_payload(
        chain,
        current_gate,
    )
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def public_current_gate(
    current_gate: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if current_gate is None:
        return None

    return {
        "gate_id": current_gate["gate_id"],
        "arm_id": current_gate["arm_id"],
        "source_arm_run_id":
            current_gate["source_arm_run_id"],
        "source_mode": current_gate["source_mode"],
        "target_mode": current_gate["target_mode"],
        "usage_reconciliation_id":
            current_gate["usage_reconciliation_id"],
        "cost_reconciliation_id":
            current_gate["cost_reconciliation_id"],
        "decision": current_gate["decision"],
        "blocker_codes": list(
            current_gate["blocker_codes"] or []
        ),
        "waiver_reason": current_gate["waiver_reason"],
        "reviewed_by": current_gate["reviewed_by"],
        "reviewed_at": current_gate["reviewed_at"],
        "is_current": current_gate["is_current"],
        "created_at": current_gate["created_at"],
        "notes_present": bool(current_gate["notes"]),
        "raw_metadata_present": (
            current_gate["raw_metadata"] not in {
                None,
                "",
                "{}",
            }
        ),
    }


def mutation_pins(
    chain: Mapping[str, Any],
    current_gate: Mapping[str, Any] | None,
) -> dict[str, str]:
    return {
        "expected_usage_reconciliation_id":
            str(chain["usage_reconciliation_id"]),
        "expected_cost_reconciliation_id":
            str(chain["cost_reconciliation_id"]),
        "expected_current_gate_id":
            (
                str(current_gate["gate_id"])
                if current_gate is not None
                else "none"
            ),
        "expected_state_sha256":
            review_state_sha256(
                chain,
                current_gate,
            ),
    }


def assert_mutation_pins(
    request: ReviewRequest,
    chain: Mapping[str, Any],
    current_gate: Mapping[str, Any] | None,
) -> None:
    if not request.current_gate_pin_was_supplied:
        raise IntegrationSafetyError(
            "mutation was attempted without a current-gate pin"
        )

    if (
        chain["usage_reconciliation_id"]
        != request.expected_usage_reconciliation_id
    ):
        raise IntegrationSafetyError(
            "current usage reconciliation changed after review"
        )

    if (
        chain["cost_reconciliation_id"]
        != request.expected_cost_reconciliation_id
    ):
        raise IntegrationSafetyError(
            "current cost reconciliation changed after review"
        )

    observed_gate_id = (
        current_gate["gate_id"]
        if current_gate is not None
        else None
    )

    if observed_gate_id != request.expected_current_gate_id:
        raise IntegrationSafetyError(
            "current promotion gate changed after review"
        )

    observed_state_sha256 = review_state_sha256(
        chain,
        current_gate,
    )

    if (
        observed_state_sha256
        != request.expected_state_sha256
    ):
        raise IntegrationSafetyError(
            "reviewed promotion state changed after check-only"
        )


def assert_recordable(
    request: ReviewRequest,
    evidence_blockers: Sequence[str],
) -> None:
    if request.decision == "pass" and evidence_blockers:
        raise NotRecordableError(evidence_blockers)


def acquire_review_lock(
    cursor: Any,
    request: ReviewRequest,
) -> None:
    lock_name = (
        f"{LOCK_PREFIX}:{request.arm_id}:{request.target_mode}"
    )

    cursor.execute(
        """
        select pg_advisory_xact_lock(
            hashtextextended(%s, 0)
        )
        """,
        (lock_name,),
    )
    cursor.fetchone()


def insert_review(
    cursor: Any,
    request: ReviewRequest,
    chain: Mapping[str, Any],
    current_gate: Mapping[str, Any] | None,
) -> str:
    previous_gate_id = (
        str(current_gate["gate_id"])
        if current_gate is not None
        else None
    )

    if previous_gate_id is not None:
        cursor.execute(
            """
            update benchmark.benchmark_evidence_promotion_gates
            set is_current = false
            where id = %s::uuid
              and is_current
            """,
            (previous_gate_id,),
        )

        if cursor.rowcount != 1:
            raise IntegrationSafetyError(
                "current promotion gate could not be superseded exactly"
            )

    raw_metadata = json.dumps(
        {
            "tool": "scripts/review_evidence_promotion.py",
            "tool_version": TOOL_VERSION,
            "supersedes_gate_id": previous_gate_id,
            "pinned_source_arm_run_id":
                request.source_arm_run_id,
            "pinned_usage_reconciliation_id":
                chain["usage_reconciliation_id"],
            "pinned_cost_reconciliation_id":
                chain["cost_reconciliation_id"],
        },
        sort_keys=True,
    )

    cursor.execute(
        """
        insert into benchmark.benchmark_evidence_promotion_gates (
            arm_id,
            source_arm_run_id,
            source_mode,
            target_mode,
            usage_reconciliation_id,
            cost_reconciliation_id,
            decision,
            blocker_codes,
            waiver_reason,
            reviewed_by,
            reviewed_at,
            is_current,
            notes,
            raw_metadata
        ) values (
            %s,
            %s::uuid,
            %s,
            %s,
            %s::uuid,
            %s::uuid,
            %s,
            %s,
            %s,
            %s,
            clock_timestamp(),
            true,
            %s,
            %s::jsonb
        )
        returning id::text
        """,
        (
            request.arm_id,
            request.source_arm_run_id,
            request.source_mode,
            request.target_mode,
            chain["usage_reconciliation_id"],
            chain["cost_reconciliation_id"],
            request.decision,
            list(request.blocker_codes),
            request.waiver_reason,
            request.reviewed_by,
            request.notes,
            raw_metadata,
        ),
    )

    row = cursor.fetchone()
    if row is None:
        raise IntegrationSafetyError(
            "promotion review insert returned no gate id"
        )

    return str(row["id"])


def read_gate_view(
    cursor: Any,
    gate_id: str,
) -> dict[str, Any]:
    cursor.execute(
        """
        select
            gate_id::text,
            arm_id,
            source_arm_run_id::text,
            source_mode,
            target_mode,
            usage_reconciliation_id::text,
            cost_reconciliation_id::text,
            decision,
            blocker_codes,
            derived_blocker_codes,
            waiver_reason,
            effective_can_advance,
            reviewed_by,
            reviewed_at::text,
            usage_validation_status,
            selected_usage_authority,
            cost_validation_status,
            selected_cost_usd::text,
            selected_cost_basis,
            selected_cost_relation
        from benchmark.v_evidence_promotion_gate
        where gate_id = %s::uuid
        """,
        (gate_id,),
    )

    row = cursor.fetchone()
    if row is None:
        raise IntegrationSafetyError(
            "promotion gate is missing from fail-closed view"
        )
    return dict(row)


def verify_inserted_view(
    request: ReviewRequest,
    chain: Mapping[str, Any],
    *,
    gate_id: str,
    view: Mapping[str, Any],
) -> dict[str, Any]:
    expected = {
        "gate_id": gate_id,
        "arm_id": request.arm_id,
        "source_arm_run_id": request.source_arm_run_id,
        "source_mode": request.source_mode,
        "target_mode": request.target_mode,
        "usage_reconciliation_id":
            chain["usage_reconciliation_id"],
        "cost_reconciliation_id":
            chain["cost_reconciliation_id"],
        "decision": request.decision,
        "waiver_reason": request.waiver_reason,
        "reviewed_by": request.reviewed_by,
    }

    for key, value in expected.items():
        if view[key] != value:
            raise IntegrationSafetyError(
                f"inserted promotion gate mismatch: {key}"
            )

    if tuple(sorted(view["blocker_codes"] or [])) != (
        request.blocker_codes
    ):
        raise IntegrationSafetyError(
            "inserted reviewed blocker codes changed"
        )

    if not view["reviewed_at"]:
        raise IntegrationSafetyError(
            "database did not record reviewed_at"
        )

    derived = tuple(view["derived_blocker_codes"] or [])
    effective = bool(view["effective_can_advance"])

    if request.decision == "pass":
        if derived or not effective:
            raise IntegrationSafetyError(
                "pass decision did not become an effective pass"
            )
    else:
        if effective:
            raise IntegrationSafetyError(
                "non-pass decision became effective authorization"
            )
        if "gate_decision_not_pass" not in derived:
            raise IntegrationSafetyError(
                "non-pass decision lost fail-closed blocker"
            )

        if (
            request.blocker_codes
            and "reviewed_blockers_present" not in derived
        ):
            raise IntegrationSafetyError(
                "reviewed blockers are missing from derived state"
            )

    return {
        "gate_id": gate_id,
        "effective_can_advance": effective,
        "derived_blocker_codes": list(derived),
        "reviewed_at": view["reviewed_at"],
    }


def inspect_state(
    cursor: Any,
    request: ReviewRequest,
    *,
    lock: bool,
) -> dict[str, Any]:
    chain = read_evidence_chain(
        cursor,
        request,
        lock=lock,
    )
    evidence_blockers = derive_evidence_blockers(
        request,
        chain,
    )
    current_gate = read_current_gate(
        cursor,
        arm_id=request.arm_id,
        target_mode=request.target_mode,
        lock=lock,
    )

    return {
        "chain": chain,
        "evidence_blockers": evidence_blockers,
        "current_gate": current_gate,
    }


def check_only(
    request: ReviewRequest,
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    connection = connect_db(db_url)

    try:
        diagnostics.enter("read_only_preflight")

        with connection.cursor() as cursor:
            cursor.execute(
                "set transaction isolation level "
                "repeatable read, read only"
            )

            state = inspect_state(
                cursor,
                request,
                lock=False,
            )

        connection.rollback()

    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise

    finally:
        connection.close()

    blockers = state["evidence_blockers"]
    recordable = not (
        request.decision == "pass" and blockers
    )

    return {
        "status": "ready" if recordable else "blocked",
        "mode": "check-only",
        "commit_state": diagnostics.commit_state,
        "recordable": recordable,
        "transition": {
            "source_mode": request.source_mode,
            "target_mode": request.target_mode,
        },
        "source_evidence": state["chain"],
        "evidence_blocker_codes": list(blockers),
        "current_gate": public_current_gate(
            state["current_gate"]
        ),
        "mutation_pins": mutation_pins(
            state["chain"],
            state["current_gate"],
        ),
        "checks": {
            "read_only_transaction": "pass",
            "exact_source_arm_run": "pass",
            "current_reconciliations": "pass",
            "current_gate_observed": "pass",
        },
    }


def rollback_only(
    request: ReviewRequest,
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    connection: Any = None

    try:
        diagnostics.enter("transaction_connection")
        connection = connect_db(db_url)

        with connection.cursor() as cursor:
            diagnostics.enter("advisory_lock")
            acquire_review_lock(cursor, request)

            diagnostics.enter("locked_preflight")
            state = inspect_state(
                cursor,
                request,
                lock=True,
            )
            assert_mutation_pins(
                request,
                state["chain"],
                state["current_gate"],
            )
            assert_recordable(
                request,
                state["evidence_blockers"],
            )

            before_history = snapshot_gate_history(
                cursor,
                arm_id=request.arm_id,
                target_mode=request.target_mode,
            )

            diagnostics.enter("transactional_review")
            new_gate_id = insert_review(
                cursor,
                request,
                state["chain"],
                state["current_gate"],
            )

            diagnostics.enter("transactional_verification")
            view = read_gate_view(cursor, new_gate_id)
            verification = verify_inserted_view(
                request,
                state["chain"],
                gate_id=new_gate_id,
                view=view,
            )

        diagnostics.enter("rollback")
        connection.rollback()

    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter("second_connection_restore_verification")
    observer = connect_db(db_url)

    try:
        with observer.cursor() as cursor:
            cursor.execute(
                "set transaction isolation level "
                "repeatable read, read only"
            )
            after_history = snapshot_gate_history(
                cursor,
                arm_id=request.arm_id,
                target_mode=request.target_mode,
            )
        observer.rollback()
    finally:
        observer.close()

    if after_history != before_history:
        raise IntegrationSafetyError(
            "rollback-only review did not restore exact gate history"
        )

    return {
        "status": "passed",
        "mode": "rollback-only",
        "commit_state": diagnostics.commit_state,
        "checks": {
            "advisory_lock": "pass",
            "exact_mutation_pins": "pass",
            "transactional_review": "pass",
            "fail_closed_view_verification": "pass",
            "rollback": "pass",
            "second_connection_exact_history_restore": "pass",
        },
        "transactional_verification": verification,
        "persistent_gate_history_unchanged": True,
    }


def verify_persisted_history(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    *,
    previous_gate_id: str | None,
    new_gate_id: str,
) -> None:
    if len(after) != len(before) + 1:
        raise IntegrationSafetyError(
            "persistent gate history did not grow by exactly one row"
        )

    before_by_id = {
        str(row["gate_id"]): dict(row)
        for row in before
    }
    after_by_id = {
        str(row["gate_id"]): dict(row)
        for row in after
    }

    if set(after_by_id) != set(before_by_id) | {new_gate_id}:
        raise IntegrationSafetyError(
            "unexpected gate-history identity change after commit"
        )

    for gate_id, original in before_by_id.items():
        expected = dict(original)

        if gate_id == previous_gate_id:
            expected["is_current"] = False

        if after_by_id[gate_id] != expected:
            raise IntegrationSafetyError(
                "historical promotion gate changed unexpectedly"
            )

    if after_by_id[new_gate_id]["is_current"] is not True:
        raise IntegrationSafetyError(
            "new promotion review is not the current gate"
        )


def apply_permanent(
    request: ReviewRequest,
    db_url: str,
    diagnostics: Diagnostics,
) -> dict[str, Any]:
    connection: Any = None

    try:
        diagnostics.enter("transaction_connection")
        connection = connect_db(db_url)

        with connection.cursor() as cursor:
            diagnostics.enter("advisory_lock")
            acquire_review_lock(cursor, request)

            diagnostics.enter("locked_preflight")
            state = inspect_state(
                cursor,
                request,
                lock=True,
            )
            assert_mutation_pins(
                request,
                state["chain"],
                state["current_gate"],
            )
            assert_recordable(
                request,
                state["evidence_blockers"],
            )

            before_history = snapshot_gate_history(
                cursor,
                arm_id=request.arm_id,
                target_mode=request.target_mode,
            )
            previous_gate_id = (
                state["current_gate"]["gate_id"]
                if state["current_gate"] is not None
                else None
            )

            diagnostics.enter("transactional_review")
            new_gate_id = insert_review(
                cursor,
                request,
                state["chain"],
                state["current_gate"],
            )

            diagnostics.enter("transactional_verification")
            view = read_gate_view(cursor, new_gate_id)
            transactional_verification = verify_inserted_view(
                request,
                state["chain"],
                gate_id=new_gate_id,
                view=view,
            )

        diagnostics.enter("commit")
        diagnostics.commit_state = "unknown"
        connection.commit()
        diagnostics.commit_state = "committed"

    except Exception:
        if (
            connection is not None
            and diagnostics.commit_state != "committed"
        ):
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    finally:
        if connection is not None:
            connection.close()

    diagnostics.enter("second_connection_verification")
    observer = connect_db(db_url)

    try:
        with observer.cursor() as cursor:
            cursor.execute(
                "set transaction isolation level "
                "repeatable read, read only"
            )

            current_gate = read_current_gate(
                cursor,
                arm_id=request.arm_id,
                target_mode=request.target_mode,
                lock=False,
            )
            if (
                current_gate is None
                or current_gate["gate_id"] != new_gate_id
            ):
                raise IntegrationSafetyError(
                    "new review is not the persisted current gate"
                )

            persisted_view = read_gate_view(
                cursor,
                new_gate_id,
            )
            persisted_verification = verify_inserted_view(
                request,
                state["chain"],
                gate_id=new_gate_id,
                view=persisted_view,
            )

            after_history = snapshot_gate_history(
                cursor,
                arm_id=request.arm_id,
                target_mode=request.target_mode,
            )

        observer.rollback()

    finally:
        observer.close()

    verify_persisted_history(
        before_history,
        after_history,
        previous_gate_id=previous_gate_id,
        new_gate_id=new_gate_id,
    )

    return {
        "status": "applied",
        "mode": "apply",
        "commit_state": diagnostics.commit_state,
        "gate_id": new_gate_id,
        "checks": {
            "advisory_lock": "pass",
            "exact_mutation_pins": "pass",
            "transactional_review": "pass",
            "transactional_verification": "pass",
            "commit": "pass",
            "second_connection_verification": "pass",
            "historical_gate_preservation": "pass",
        },
        "transactional_verification":
            transactional_verification,
        "persisted_verification": persisted_verification,
    }


def failure_payload(
    *,
    mode: str,
    diagnostics: Diagnostics,
    exc: BaseException,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "failed",
        "mode": mode,
        "failed_stage": diagnostics.stage,
        "error_type": type(exc).__name__,
        "commit_state": diagnostics.commit_state,
    }

    if isinstance(exc, NotRecordableError):
        result["evidence_blocker_codes"] = list(
            exc.blockers
        )

    sqlstate = getattr(exc, "sqlstate", None)
    value = str(sqlstate or "")

    if len(value) == 5 and value.isalnum():
        result["sqlstate"] = value.upper()

    return result


def main(
    argv: list[str] | None = None,
) -> int:
    diagnostics = Diagnostics()
    mode = "arguments"

    try:
        args = parse_args(argv)
        request = request_from_args(args)
        mode = request.mode

        if request.mode == "plan":
            print(
                json.dumps(
                    build_plan(request),
                    sort_keys=True,
                )
            )
            return 0

        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise MissingEnvironmentError(
                "SUPABASE_DB_URL is required"
            )

        if request.mode == "check-only":
            result = check_only(
                request,
                db_url,
                diagnostics,
            )
            print(json.dumps(result, sort_keys=True))
            return 0 if result["recordable"] else 3

        if request.mode == "rollback-only":
            result = rollback_only(
                request,
                db_url,
                diagnostics,
            )
        else:
            result = apply_permanent(
                request,
                db_url,
                diagnostics,
            )

        print(json.dumps(result, sort_keys=True))
        return 0

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
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
