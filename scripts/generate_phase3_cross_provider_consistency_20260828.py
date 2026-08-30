#!/usr/bin/env python3
"""Generate the frozen 2026-08-28 Phase 3 cross-provider consistency layer.

The checked-in CSV/report are deterministic products of:
- the reviewed 2026-08-25 selected-run cost ledger;
- the explicit consistency contract encoded below; and
- hash-bound public post-review provenance clarifications through 2026-08-30.

The post-review inputs clarify provenance without changing selected-run
contract states, selected costs, or the CSV schema.

No database or secret access is required for ordinary regeneration.

For provenance verification, callers may also provide the private read-only
2026-08-28 inventory and derived contract with --inventory and --contract.
Those inputs are hash-bound and validated but are never copied into tracked
outputs wholesale.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LEDGER = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)

OUT_CSV = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_cross_provider_consistency_20260828.csv"
)

OUT_REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "PHASE3_CROSS_PROVIDER_CONSISTENCY_20260828.md"
)

EXPECTED_LEDGER_SHA256 = (
    "43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256"
)

EXPECTED_INVENTORY_SHA256 = (
    "7c3ffad57afdfa4c672152178281699652f14b4d739336ba793076c603b3ac24"
)

EXPECTED_PRIVATE_CONTRACT_SHA256 = (
    "a7d6f1518a97b922d8c2a087c76f06e216251c629a59e27bd5ee8952085abeb0"
)

OPENAI_SOURCE_MANIFEST = (
    ROOT
    / "results/phase3/provider_usage/normalized/"
      "openai_provider_source_manifest_20260821.csv"
)

EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256 = (
    "1f8b6f52aa2d46d8dbcfb87d97a67e62317c4f0a8849a52c81e5ee6686c1ea20"
)

ANTHROPIC_CLOSURE = (
    ROOT
    / "docs/reports/phase3/"
      "ANTHROPIC_PROVIDER_EVIDENCE_CLOSURE_20260830.md"
)

EXPECTED_ANTHROPIC_CLOSURE_SHA256 = (
    "7da0313380bb690c0e4ec09371eb41eead5a5c7ada73a1c02328ad212864f789"
)

SCHEMA_VERSION = "phase3-cross-provider-consistency-v1"
GENERATOR_VERSION = "1.1.0"
REVIEW_DATE = "2026-08-28"
POST_REVIEW_CLARIFICATION_DATE = "2026-08-30"


@dataclass(frozen=True)
class ArmSpec:
    state: str
    authority_class: str
    usage_authority: str
    usage_validation_status: str
    cost_basis: str
    cost_relation: str
    cost_validation_status: str
    usage_roles: tuple[str, ...]
    cost_roles: tuple[str, ...]
    accepted_absence_reason: str


ABSENCE_ANTHROPIC = (
    "Selected-run reporting retains provider-rate reconstructed cost evidence, "
    "but no first-party Anthropic provider evidence was normalized into the "
    "migration-011 tables. Absence is accepted rather than treated as an "
    "ingestion defect."
)

ABSENCE_GLM = (
    "No allocable selected-run first-party Z.AI provider evidence is retained. "
    "Historical GLM provider context is not promoted to selected-run authority, "
    "so the normalized provider-evidence state remains deliberately empty."
)


ARM_SPECS: dict[str, ArmSpec] = {
    "router-anthropic-fable-5": ArmSpec(
        state="accepted_absence_anthropic_not_normalized",
        authority_class="reporting_only_no_normalized_reconciliation",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_ANTHROPIC,
    ),
    "router-anthropic-haiku-sanitized": ArmSpec(
        state="accepted_absence_anthropic_not_normalized",
        authority_class="reporting_only_no_normalized_reconciliation",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_ANTHROPIC,
    ),
    "router-anthropic-opus": ArmSpec(
        state="accepted_absence_anthropic_not_normalized",
        authority_class="reporting_only_no_normalized_reconciliation",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_ANTHROPIC,
    ),
    "router-anthropic-sonnet": ArmSpec(
        state="accepted_absence_anthropic_not_normalized",
        authority_class="reporting_only_no_normalized_reconciliation",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_ANTHROPIC,
    ),
    "router-deepseek-flash": ArmSpec(
        state="normalized_qualified_rate_estimate",
        authority_class=(
            "qualified_harness_usage_provider_rate_reconstruction"
        ),
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis=(
            "provider_rate_reconstructed_harness_usage_validated"
        ),
        cost_relation="estimate",
        cost_validation_status="validated_qualified",
        usage_roles=("context", "model_identity"),
        cost_roles=("context", "pricing", "rate_reconstruction"),
        accepted_absence_reason="",
    ),
    "router-deepseek-pro": ArmSpec(
        state="normalized_qualified_rate_estimate",
        authority_class=(
            "qualified_harness_usage_provider_rate_reconstruction"
        ),
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis=(
            "provider_rate_reconstructed_harness_usage_validated"
        ),
        cost_relation="estimate",
        cost_validation_status="validated_qualified",
        usage_roles=("context", "model_identity"),
        cost_roles=("context", "pricing", "rate_reconstruction"),
        accepted_absence_reason="",
    ),
    "router-gemini-3.1-pro": ArmSpec(
        state="normalized_qualified_rate_estimate",
        authority_class=(
            "qualified_harness_usage_provider_rate_reconstruction"
        ),
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis=(
            "provider_rate_reconstructed_harness_usage_validated"
        ),
        cost_relation="estimate",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "model_identity"),
        cost_roles=("context", "pricing", "rate_reconstruction"),
        accepted_absence_reason="",
    ),
    "router-gemini-flash": ArmSpec(
        state="normalized_qualified_lower_bound",
        authority_class="qualified_lower_bound_provider_evidence",
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis="lower_bound_provider_evidence",
        cost_relation="lower_bound",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "model_identity"),
        cost_roles=("context", "lower_bound", "pricing"),
        accepted_absence_reason="",
    ),
    "router-glm-5.1": ArmSpec(
        state="accepted_absence_glm_deliberate_empty",
        authority_class="reporting_estimate_not_normalized",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_GLM,
    ),
    "router-glm-5.2": ArmSpec(
        state="accepted_absence_glm_deliberate_empty",
        authority_class="reporting_estimate_not_normalized",
        usage_authority="",
        usage_validation_status="",
        cost_basis="",
        cost_relation="",
        cost_validation_status="",
        usage_roles=(),
        cost_roles=(),
        accepted_absence_reason=ABSENCE_GLM,
    ),
    "router-gpt-5.4": ArmSpec(
        state="normalized_exact_provider_billed",
        authority_class="selected_run_first_party_exact",
        usage_authority="provider_aggregate_usage",
        usage_validation_status="validated_exact",
        cost_basis="provider_billed",
        cost_relation="exact",
        cost_validation_status="validated_exact",
        usage_roles=("aggregate_usage",),
        cost_roles=("billed",),
        accepted_absence_reason="",
    ),
    "router-gpt-5.5": ArmSpec(
        state="normalized_exact_provider_billed",
        authority_class="selected_run_first_party_exact",
        usage_authority="provider_aggregate_usage",
        usage_validation_status="validated_exact",
        cost_basis="provider_billed",
        cost_relation="exact",
        cost_validation_status="validated_exact",
        usage_roles=("aggregate_usage",),
        cost_roles=("billed",),
        accepted_absence_reason="",
    ),
    "router-grok-build-0.1": ArmSpec(
        state="normalized_qualified_lower_bound",
        authority_class="qualified_lower_bound_provider_evidence",
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis="lower_bound_provider_evidence",
        cost_relation="lower_bound",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "model_identity"),
        cost_roles=("context", "lower_bound", "pricing"),
        accepted_absence_reason="",
    ),
    "router-kimi-k2.6": ArmSpec(
        state="normalized_qualified_rate_estimate",
        authority_class=(
            "qualified_harness_usage_provider_rate_reconstruction"
        ),
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis=(
            "provider_rate_reconstructed_harness_usage_validated"
        ),
        cost_relation="estimate",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "context", "model_identity"),
        cost_roles=("context", "pricing", "rate_reconstruction"),
        accepted_absence_reason="",
    ),
    "router-kimi-k3": ArmSpec(
        state="normalized_qualified_rate_estimate",
        authority_class=(
            "qualified_harness_usage_provider_rate_reconstruction"
        ),
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis=(
            "provider_rate_reconstructed_harness_usage_validated"
        ),
        cost_relation="estimate",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "context", "model_identity"),
        cost_roles=("context", "pricing", "rate_reconstruction"),
        accepted_absence_reason="",
    ),
    "router-qwen-3.7-plus": ArmSpec(
        state="normalized_qualified_lower_bound",
        authority_class="qualified_lower_bound_provider_evidence",
        usage_authority="harness_usage_validated",
        usage_validation_status="validated_qualified",
        cost_basis="lower_bound_provider_evidence",
        cost_relation="lower_bound",
        cost_validation_status="validated_qualified",
        usage_roles=("aggregate_usage", "context", "model_identity"),
        cost_roles=("context", "lower_bound", "pricing"),
        accepted_absence_reason="",
    ),
}


CSV_FIELDS = (
    "arm_id",
    "selected_run_label",
    "provider",
    "backend_model",
    "reporting_selected_cost_usd",
    "reporting_selected_cost_relation",
    "contract_state",
    "authority_class",
    "normalized_usage_reconciliation",
    "normalized_cost_reconciliation",
    "usage_authority",
    "usage_validation_status",
    "cost_basis",
    "cost_relation",
    "cost_validation_status",
    "usage_source_roles",
    "cost_source_roles",
    "accepted_absence_reason",
    "ledger_sha256",
    "private_inventory_sha256",
    "private_contract_sha256",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def fail(message: str) -> None:
    raise ValueError(message)


def normalized(spec: ArmSpec) -> bool:
    return spec.state.startswith("normalized_")


def boolean_text(value: bool) -> str:
    return "true" if value else "false"


def roles_text(roles: tuple[str, ...]) -> str:
    return ";".join(roles)


def decimal_text(value: str) -> str:
    # Validate numeric syntax while preserving ledger precision/format.
    Decimal(value)
    return value


def verify_public_post_review_inputs() -> None:
    if (
        sha256(OPENAI_SOURCE_MANIFEST)
        != EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256
    ):
        fail(
            "20260821 OpenAI source manifest SHA-256 changed; "
            "refusing to generate post-review clarification"
        )

    if (
        sha256(ANTHROPIC_CLOSURE)
        != EXPECTED_ANTHROPIC_CLOSURE_SHA256
    ):
        fail(
            "20260830 Anthropic closure SHA-256 changed; "
            "refusing to generate post-review clarification"
        )


def load_ledger() -> list[dict[str, str]]:
    if sha256(LEDGER) != EXPECTED_LEDGER_SHA256:
        fail(
            "20260825 selected-run ledger SHA-256 changed; "
            "refusing to generate consistency artifacts"
        )

    rows = read_csv(LEDGER)

    if len(rows) != 16:
        fail("expected exactly 16 selected-run ledger rows")

    by_arm = {
        row["arm_id"]: row
        for row in rows
    }

    if len(by_arm) != 16:
        fail("selected-run ledger arm IDs are not unique")

    if set(by_arm) != set(ARM_SPECS):
        fail("selected-run ledger arm set differs from contract")

    if len(
        {
            row["selected_run_label"]
            for row in rows
        }
    ) != 16:
        fail("selected-run labels are not unique")

    return rows


def build_rows(
    ledger_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_arm = {
        row["arm_id"]: row
        for row in ledger_rows
    }

    rows: list[dict[str, str]] = []

    for arm_id in sorted(ARM_SPECS):
        ledger = by_arm[arm_id]
        spec = ARM_SPECS[arm_id]
        is_normalized = normalized(spec)

        reporting_relation = ledger[
            "selected_cost_relation"
        ]

        if is_normalized:
            if spec.cost_relation != reporting_relation:
                fail(
                    f"{arm_id}: contract cost relation does not "
                    "match reviewed reporting relation"
                )
        elif arm_id.startswith("router-glm-"):
            if reporting_relation != "estimate":
                fail(
                    f"{arm_id}: GLM reviewed reporting relation "
                    "must remain estimate"
                )

        decimal_text(
            ledger["selected_cost_usd"]
        )

        rows.append(
            {
                "arm_id":
                    arm_id,
                "selected_run_label":
                    ledger[
                        "selected_run_label"
                    ],
                "provider":
                    ledger["provider"],
                "backend_model":
                    ledger[
                        "backend_model"
                    ],
                "reporting_selected_cost_usd":
                    ledger[
                        "selected_cost_usd"
                    ],
                "reporting_selected_cost_relation":
                    reporting_relation,
                "contract_state":
                    spec.state,
                "authority_class":
                    spec.authority_class,
                "normalized_usage_reconciliation":
                    boolean_text(
                        is_normalized
                    ),
                "normalized_cost_reconciliation":
                    boolean_text(
                        is_normalized
                    ),
                "usage_authority":
                    spec.usage_authority,
                "usage_validation_status":
                    spec.usage_validation_status,
                "cost_basis":
                    spec.cost_basis,
                "cost_relation":
                    spec.cost_relation,
                "cost_validation_status":
                    spec.cost_validation_status,
                "usage_source_roles":
                    roles_text(
                        spec.usage_roles
                    ),
                "cost_source_roles":
                    roles_text(
                        spec.cost_roles
                    ),
                "accepted_absence_reason":
                    spec.accepted_absence_reason,
                "ledger_sha256":
                    EXPECTED_LEDGER_SHA256,
                "private_inventory_sha256":
                    EXPECTED_INVENTORY_SHA256,
                "private_contract_sha256":
                    EXPECTED_PRIVATE_CONTRACT_SHA256,
            }
        )

    return rows


def roles_by_run(
    rows: list[dict[str, Any]],
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}

    for row in rows:
        result.setdefault(
            str(row["run_label"]),
            set(),
        ).add(
            str(row["evidence_role"])
        )

    return result


def verify_private_inputs(
    inventory_path: Path,
    contract_path: Path,
    generated_rows: list[dict[str, str]],
) -> None:
    if sha256(inventory_path) != EXPECTED_INVENTORY_SHA256:
        fail("private inventory SHA-256 mismatch")

    if sha256(contract_path) != EXPECTED_PRIVATE_CONTRACT_SHA256:
        fail("private derived contract SHA-256 mismatch")

    inventory = json.loads(
        inventory_path.read_text(
            encoding="utf-8"
        )
    )

    contract = json.loads(
        contract_path.read_text(
            encoding="utf-8"
        )
    )

    if inventory.get("status") != "captured":
        fail("private inventory status is not captured")

    if contract.get("status") != "pass":
        fail("private derived contract status is not pass")

    checks = inventory.get(
        "checks",
        {},
    )

    required_true = (
        "database_read_only",
        "required_relations_complete",
        "selected_arm_count_16",
        "selected_provider_count_8",
        "selected_run_resolution_clean",
    )

    for key in required_true:
        if checks.get(key) is not True:
            fail(
                f"private inventory prerequisite failed: {key}"
            )

    if checks.get(
        "cross_provider_source_link_mismatch_count"
    ) != 0:
        fail(
            "private inventory contains cross-provider "
            "reconciliation source links"
        )

    database = inventory.get(
        "database",
        {},
    )

    if database.get("writes_attempted") is not False:
        fail("private inventory attempted a DB write")

    if database.get("writes_performed") is not False:
        fail("private inventory performed a DB write")

    expected = {
        row["arm_id"]: row
        for row in generated_rows
    }

    selected = {
        row["arm_id"]: row
        for row in inventory.get(
            "selected_arms",
            [],
        )
    }

    derived = {
        row["arm_id"]: row
        for row in contract.get(
            "selected_arms",
            [],
        )
    }

    if set(selected) != set(expected):
        fail(
            "private inventory selected arm set "
            "differs from frozen contract"
        )

    if set(derived) != set(expected):
        fail(
            "private derived contract arm set "
            "differs from frozen contract"
        )

    usage_roles = roles_by_run(
        inventory.get(
            "selected_usage_source_roles",
            [],
        )
    )

    cost_roles = roles_by_run(
        inventory.get(
            "selected_cost_source_roles",
            [],
        )
    )

    for arm_id, output in expected.items():
        spec = ARM_SPECS[arm_id]
        observed = selected[arm_id]
        derived_row = derived[arm_id]
        run_label = output[
            "selected_run_label"
        ]

        if observed["provider"] != output["provider"]:
            fail(
                f"{arm_id}: private inventory provider mismatch"
            )

        if observed["run_label"] != run_label:
            fail(
                f"{arm_id}: private inventory run-label mismatch"
            )

        if derived_row["state"] != spec.state:
            fail(
                f"{arm_id}: private contract state mismatch"
            )

        if (
            derived_row["authority_class"]
            != spec.authority_class
        ):
            fail(
                f"{arm_id}: private contract authority mismatch"
            )

        if (
            Decimal(
                str(
                    derived_row[
                        "reporting_cost_usd"
                    ]
                )
            )
            != Decimal(
                output[
                    "reporting_selected_cost_usd"
                ]
            )
        ):
            fail(
                f"{arm_id}: private contract reporting "
                "cost mismatch"
            )

        if (
            derived_row[
                "reporting_cost_relation"
            ]
            != output[
                "reporting_selected_cost_relation"
            ]
        ):
            fail(
                f"{arm_id}: private contract reporting "
                "relation mismatch"
            )

        observed_usage_roles = usage_roles.get(
            run_label,
            set(),
        )

        observed_cost_roles = cost_roles.get(
            run_label,
            set(),
        )

        if observed_usage_roles != set(
            spec.usage_roles
        ):
            fail(
                f"{arm_id}: private inventory usage-role mismatch"
            )

        if observed_cost_roles != set(
            spec.cost_roles
        ):
            fail(
                f"{arm_id}: private inventory cost-role mismatch"
            )

        usage_rec = observed.get(
            "usage_reconciliation"
        )

        cost_rec = observed.get(
            "cost_reconciliation"
        )

        if normalized(spec):
            if usage_rec is None or cost_rec is None:
                fail(
                    f"{arm_id}: expected normalized reconciliations"
                )

            if (
                usage_rec[
                    "selected_usage_authority"
                ]
                != spec.usage_authority
            ):
                fail(
                    f"{arm_id}: private usage authority mismatch"
                )

            if (
                usage_rec[
                    "validation_status"
                ]
                != spec.usage_validation_status
            ):
                fail(
                    f"{arm_id}: private usage validation mismatch"
                )

            if (
                cost_rec[
                    "selected_cost_basis"
                ]
                != spec.cost_basis
            ):
                fail(
                    f"{arm_id}: private cost basis mismatch"
                )

            if (
                cost_rec[
                    "selected_cost_relation"
                ]
                != spec.cost_relation
            ):
                fail(
                    f"{arm_id}: private cost relation mismatch"
                )

            if (
                cost_rec[
                    "validation_status"
                ]
                != spec.cost_validation_status
            ):
                fail(
                    f"{arm_id}: private cost validation mismatch"
                )

            if Decimal(
                str(
                    cost_rec[
                        "selected_cost_usd"
                    ]
                )
            ) != Decimal(
                output[
                    "reporting_selected_cost_usd"
                ]
            ):
                fail(
                    f"{arm_id}: normalized selected cost "
                    "does not equal reviewed reporting cost"
                )

        else:
            if usage_rec is not None:
                fail(
                    f"{arm_id}: accepted-absence arm has "
                    "unexpected usage reconciliation"
                )

            if cost_rec is not None:
                fail(
                    f"{arm_id}: accepted-absence arm has "
                    "unexpected cost reconciliation"
                )

    glm_observations = inventory.get(
        "observations",
        {},
    )

    for key in (
        "glm_provider_source_rows",
        "glm_provider_usage_rows",
        "glm_provider_cost_rows",
        "glm_provider_pricing_rows",
        "glm_selected_direct_normalized_count_total",
    ):
        if int(
            glm_observations.get(
                key,
                -1,
            )
        ) != 0:
            fail(
                "GLM deliberate-empty invariant violated: "
                f"{key}"
            )


def render_csv(
    rows: list[dict[str, str]],
) -> None:
    OUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def render_report(
    rows: list[dict[str, str]],
) -> None:
    state_counts = Counter(
        row["contract_state"]
        for row in rows
    )

    provider_counts = Counter(
        row["provider"]
        for row in rows
    )

    reconciled = sum(
        row[
            "normalized_cost_reconciliation"
        ] == "true"
        for row in rows
    )

    absence = len(rows) - reconciled

    lines = [
        "# Phase 3 Cross-Provider Evidence Consistency — 2026-08-28",
        "",
        "## Scope",
        "",
        (
            "This layer freezes the cross-provider consistency interpretation "
            "for the 16 reviewed Phase 3 selected full-suite arms. It does not "
            "rewrite the 2026-08-25 cost ledger, prior provider evidence, "
            "historical benchmark results, or Phase 1."
        ),
        "",
        (
            f"- Selected arms: **{len(rows)}**"
        ),
        (
            f"- Provider families: **{len(provider_counts)}**"
        ),
        (
            f"- Selected arms with normalized current usage and cost "
            f"reconciliations: **{reconciled}**"
        ),
        (
            f"- Accepted normalized-absence arms: **{absence}**"
        ),
        "",
        "## Frozen provenance",
        "",
        (
            f"- Reviewed selected-run ledger SHA-256: "
            f"`{EXPECTED_LEDGER_SHA256}`"
        ),
        (
            f"- Private read-only normalized inventory SHA-256: "
            f"`{EXPECTED_INVENTORY_SHA256}`"
        ),
        (
            f"- Private derived consistency contract SHA-256: "
            f"`{EXPECTED_PRIVATE_CONTRACT_SHA256}`"
        ),
        (
            f"- Repaired OpenAI source manifest SHA-256: "
            f"`{EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256}`"
        ),
        (
            f"- Anthropic provider-evidence closure SHA-256: "
            f"`{EXPECTED_ANTHROPIC_CLOSURE_SHA256}`"
        ),
        "",
        (
            "The private inventory was generated against Supabase with a "
            "read-only transaction, reported no attempted or performed writes, "
            "and passed its privacy scan. The private inputs are intentionally "
            "ignored and are not required for ordinary CI regeneration."
        ),
        "",
        "## Contract principles",
        "",
        (
            "1. **Reviewed selected-run identity remains authoritative.** "
            "This layer consumes the checked-in 2026-08-25 selected-run ledger "
            "rather than selecting replacement runs."
        ),
        (
            "2. **Absence is not automatically an ingestion defect.** "
            "Anthropic and GLM have explicit accepted absence states for "
            "different evidentiary reasons."
        ),
        (
            "3. **Provider source rows do not have to be arm-run scoped.** "
            "A provider-window or account-window source may legitimately "
            "support a selected run through normalized child allocation and "
            "reconciliation links."
        ),
        (
            "4. **Provider-family isolation is mandatory.** "
            "A selected-run reconciliation must not link evidence from another "
            "provider family."
        ),
        (
            "5. **Normalized selected cost must agree with reviewed reporting.** "
            "For reconciled arms, the normalized selected cost and cost relation "
            "must equal the reviewed selected-run ledger."
        ),
        (
            "6. **Exact, estimate, and lower-bound semantics remain distinct.** "
            "The normalized basis, relation, validation status, and evidence "
            "roles must preserve that distinction."
        ),
        (
            "7. **Historical context is not selected-run authority by default.** "
            "Provider/model/account-window evidence is not promoted to "
            "selected-run authority without allocable evidence."
        ),
        (
            "8. **Promotion gates and nonselected reconciliations are outside "
            "this frozen selected-full-run completeness contract.** Their "
            "current population is informational rather than a required row "
            "count."
        ),
        "",
        "## State counts",
        "",
        "| State | Arms |",
        "| --- | ---: |",
    ]

    for state, count in sorted(
        state_counts.items()
    ):
        lines.append(
            f"| `{state}` | {count} |"
        )

    lines.extend(
        [
            "",
            "## Selected-arm consistency matrix",
            "",
            (
                "| Arm | Provider | Reviewed cost | Relation | Contract state | "
                "Usage authority | Cost basis |"
            ),
            (
                "| --- | --- | ---: | --- | --- | --- | --- |"
            ),
        ]
    )

    for row in rows:
        usage = (
            row["usage_authority"]
            or "accepted absence"
        )
        cost_basis = (
            row["cost_basis"]
            or "accepted absence"
        )

        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['arm_id']}`",
                    f"`{row['provider']}`",
                    f"${row['reporting_selected_cost_usd']}",
                    f"`{row['reporting_selected_cost_relation']}`",
                    f"`{row['contract_state']}`",
                    f"`{usage}`",
                    f"`{cost_basis}`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Accepted normalized absence",
            "",
            "### Anthropic",
            "",
            (
                "The four Anthropic selected arms remain represented by the "
                "reviewed reporting layer, including official-rate "
                "reconstruction and lower-bound qualifications where "
                "applicable. No first-party Anthropic provider evidence was "
                "normalized into the migration-011 evidence tables for these "
                "selected runs. This is recorded as an accepted evidence state, "
                "not silently filled with synthetic normalized rows."
            ),
            "",
            "### Z.AI / GLM",
            "",
            (
                "Both selected GLM arms remain deliberately empty in the "
                "normalized provider-evidence layer. Historical GLM 5.1 "
                "provider context is not allocable to the selected GLM 5.1 run, "
                "and comparable selected-run first-party evidence is not "
                "retained for GLM 5.2. The 2026-08-28 private inventory observed "
                "zero GLM provider sources, usage rows, cost rows, pricing rows, "
                "and selected-arm normalized rows."
            ),
            "",
            "## Normalized authority classes",
            "",
            (
                "- **OpenAI (2 arms):** exact selected-run provider usage and "
                "provider-billed cost."
            ),
            (
                "- **Qualified rate estimates (5 arms):** DeepSeek Flash, "
                "DeepSeek Pro, Gemini 3.1 Pro, Kimi K2.6, and Kimi K3 use "
                "validated harness usage plus provider evidence and provider "
                "rates."
            ),
            (
                "- **Qualified lower bounds (3 arms):** Grok Build 0.1, Gemini "
                "Flash, and Qwen 3.7 Plus retain lower-bound cost authority."
            ),
            "",
            (
                "## Post-review provenance clarifications — "
                f"{POST_REVIEW_CLARIFICATION_DATE}"
            ),
            "",
            "### OpenAI source-manifest repair",
            "",
            (
                "The OpenAI private-source manifest was re-audited after the "
                "original 2026-08-28 consistency snapshot. Six nonselected "
                "May/July/August files were corrected from provider usage/cost "
                "export labels to `provider_time_grid_no_metrics` because the "
                "reviewed bytes contain only start/end time-grid fields and no "
                "usage or cost metrics."
            ),
            "",
            (
                "The selected June usage and cost exports supporting GPT-5.4 "
                "and GPT-5.5 were unchanged. Therefore this provenance repair "
                "does not change either OpenAI selected-run contract state, "
                "selected cost, cost relation, or authority class. The CSV "
                "matrix remains unchanged."
            ),
            "",
            "### Anthropic evidence closure",
            "",
            (
                "The 2026-08-30 Anthropic closure confirms the existing "
                "`accepted_absence_anthropic_not_normalized` state for all "
                "four selected Anthropic arms. The accepted absence means that "
                "no retained first-party Anthropic selected-run provider "
                "source was available for normalization under the reviewed "
                "evidence and credential set."
            ),
            "",
            (
                "It is not a claim that Anthropic lacks provider APIs. The "
                "repository collector supports first-party Anthropic usage and "
                "cost APIs, but collection requires `ANTHROPIC_ADMIN_API_KEY`; "
                "the reviewed credential set does not contain that Admin key. "
                "Any future collection would still require allocation review "
                "before selected-run promotion."
            ),
            "",
            "## Reproducibility",
            "",
            (
                "Ordinary regeneration is offline and secret-free:"
            ),
            "",
            "```bash",
            (
                "uv run python "
                "scripts/generate_phase3_cross_provider_consistency_20260828.py"
            ),
            "```",
            "",
            (
                "To re-verify the original private normalized snapshot before "
                "regeneration, supply both ignored inputs:"
            ),
            "",
            "```bash",
            (
                "uv run python "
                "scripts/generate_phase3_cross_provider_consistency_20260828.py "
                "--inventory "
                ".run/review/cross-provider-evidence-inventory-20260828-01.json "
                "--contract "
                ".run/review/cross-provider-consistency-contract-20260828-01.json"
            ),
            "```",
            "",
            (
                "The second mode verifies the frozen private hashes and semantic "
                "contract but performs no database access itself."
            ),
        ]
    )

    OUT_REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT_REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--inventory",
        type=Path,
    )
    parser.add_argument(
        "--contract",
        type=Path,
    )

    args = parser.parse_args()

    if (
        args.inventory is None
    ) != (
        args.contract is None
    ):
        parser.error(
            "--inventory and --contract "
            "must be supplied together"
        )

    return args


def main() -> int:
    args = parse_args()

    verify_public_post_review_inputs()
    ledger_rows = load_ledger()
    rows = build_rows(
        ledger_rows
    )

    if args.inventory is not None:
        verify_private_inputs(
            args.inventory,
            args.contract,
            rows,
        )
        private_status = "verified"
    else:
        private_status = (
            "not_rechecked_offline_generation"
        )

    render_csv(rows)
    render_report(rows)

    state_counts = Counter(
        row["contract_state"]
        for row in rows
    )

    print(
        f"schema_version={SCHEMA_VERSION}"
    )
    print(
        f"generator_version={GENERATOR_VERSION}"
    )
    print(
        f"review_date={REVIEW_DATE}"
    )
    print(
        "post_review_clarification_date="
        f"{POST_REVIEW_CLARIFICATION_DATE}"
    )
    print(
        "openai_source_manifest_sha256="
        f"{EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256}"
    )
    print(
        "anthropic_closure_sha256="
        f"{EXPECTED_ANTHROPIC_CLOSURE_SHA256}"
    )
    print(
        f"selected_arm_rows={len(rows)}"
    )
    print(
        f"provider_families="
        f"{len({row['provider'] for row in rows})}"
    )
    print(
        "normalized_reconciled_arms="
        f"{sum(normalized(ARM_SPECS[row['arm_id']]) for row in rows)}"
    )
    print(
        "accepted_absence_arms="
        f"{sum(not normalized(ARM_SPECS[row['arm_id']]) for row in rows)}"
    )

    for state, count in sorted(
        state_counts.items()
    ):
        print(
            f"state.{state}={count}"
        )

    print(
        f"private_snapshot_status={private_status}"
    )
    print(
        f"csv={OUT_CSV.relative_to(ROOT)}"
    )
    print(
        f"report={OUT_REPORT.relative_to(ROOT)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
