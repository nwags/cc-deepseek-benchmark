from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GENERATOR = (
    ROOT
    / "scripts/"
    "generate_phase3_cross_provider_consistency_20260828.py"
)

LEDGER = (
    ROOT
    / "results/phase3/reporting/"
    "phase3_current_arm_cost_reconciliation_20260825.csv"
)

CSV_OUT = (
    ROOT
    / "results/phase3/reporting/"
    "phase3_cross_provider_consistency_20260828.csv"
)

REPORT_OUT = (
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def by_arm(
    rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    return {
        row["arm_id"]: row
        for row in rows
    }


def test_selected_run_ledger_is_hash_bound() -> None:
    assert (
        sha256(LEDGER)
        == EXPECTED_LEDGER_SHA256
    )


def test_post_review_public_inputs_are_hash_bound() -> None:
    assert (
        sha256(OPENAI_SOURCE_MANIFEST)
        == EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256
    )

    assert (
        sha256(ANTHROPIC_CLOSURE)
        == EXPECTED_ANTHROPIC_CLOSURE_SHA256
    )


def test_checked_outputs_are_deterministic_offline_products() -> None:
    before = {
        path: path.read_bytes()
        for path in (
            CSV_OUT,
            REPORT_OUT,
        )
    }

    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "selected_arm_rows=16" in result.stdout
    assert (
        "generator_version=1.1.0"
        in result.stdout
    )
    assert (
        "post_review_clarification_date=2026-08-30"
        in result.stdout
    )
    assert (
        EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256
        in result.stdout
    )
    assert (
        EXPECTED_ANTHROPIC_CLOSURE_SHA256
        in result.stdout
    )
    assert (
        "normalized_reconciled_arms=10"
        in result.stdout
    )
    assert (
        "accepted_absence_arms=6"
        in result.stdout
    )
    assert (
        "private_snapshot_status="
        "not_rechecked_offline_generation"
        in result.stdout
    )

    after = {
        path: path.read_bytes()
        for path in (
            CSV_OUT,
            REPORT_OUT,
        )
    }

    assert after == before


def test_cross_provider_state_counts() -> None:
    rows = read_csv(CSV_OUT)

    assert len(rows) == 16

    assert len(
        {
            row["arm_id"]
            for row in rows
        }
    ) == 16

    assert len(
        {
            row["selected_run_label"]
            for row in rows
        }
    ) == 16

    assert len(
        {
            row["provider"]
            for row in rows
        }
    ) == 8

    counts = Counter(
        row["contract_state"]
        for row in rows
    )

    assert counts == {
        "accepted_absence_anthropic_not_normalized":
            4,
        "accepted_absence_glm_deliberate_empty":
            2,
        "normalized_exact_provider_billed":
            2,
        "normalized_qualified_lower_bound":
            3,
        "normalized_qualified_rate_estimate":
            5,
    }


def test_selected_costs_match_reviewed_ledger() -> None:
    ledger = by_arm(
        read_csv(LEDGER)
    )

    consistency = by_arm(
        read_csv(CSV_OUT)
    )

    assert set(ledger) == set(
        consistency
    )

    for arm_id, row in consistency.items():
        source = ledger[arm_id]

        assert (
            row["selected_run_label"]
            == source["selected_run_label"]
        )

        assert (
            row["provider"]
            == source["provider"]
        )

        assert (
            row["backend_model"]
            == source["backend_model"]
        )

        assert Decimal(
            row[
                "reporting_selected_cost_usd"
            ]
        ) == Decimal(
            source["selected_cost_usd"]
        )

        assert (
            row[
                "reporting_selected_cost_relation"
            ]
            == source[
                "selected_cost_relation"
            ]
        )


def test_openai_is_exact_provider_billed_authority() -> None:
    rows = by_arm(
        read_csv(CSV_OUT)
    )

    for arm_id in (
        "router-gpt-5.4",
        "router-gpt-5.5",
    ):
        row = rows[arm_id]

        assert (
            row["contract_state"]
            == "normalized_exact_provider_billed"
        )

        assert (
            row["authority_class"]
            == "selected_run_first_party_exact"
        )

        assert (
            row[
                "normalized_usage_reconciliation"
            ]
            == "true"
        )

        assert (
            row[
                "normalized_cost_reconciliation"
            ]
            == "true"
        )

        assert (
            row["usage_authority"]
            == "provider_aggregate_usage"
        )

        assert (
            row["usage_validation_status"]
            == "validated_exact"
        )

        assert (
            row["cost_basis"]
            == "provider_billed"
        )

        assert (
            row["cost_relation"]
            == "exact"
        )

        assert (
            row["cost_validation_status"]
            == "validated_exact"
        )

        assert (
            row["usage_source_roles"]
            == "aggregate_usage"
        )

        assert (
            row["cost_source_roles"]
            == "billed"
        )


def test_qualified_estimate_semantics() -> None:
    rows = by_arm(
        read_csv(CSV_OUT)
    )

    estimate_arms = {
        "router-deepseek-flash",
        "router-deepseek-pro",
        "router-gemini-3.1-pro",
        "router-kimi-k2.6",
        "router-kimi-k3",
    }

    for arm_id in estimate_arms:
        row = rows[arm_id]

        assert (
            row["contract_state"]
            == "normalized_qualified_rate_estimate"
        )

        assert (
            row["usage_authority"]
            == "harness_usage_validated"
        )

        assert (
            row["usage_validation_status"]
            == "validated_qualified"
        )

        assert (
            row["cost_basis"]
            == (
                "provider_rate_reconstructed_"
                "harness_usage_validated"
            )
        )

        assert (
            row["cost_relation"]
            == "estimate"
        )

        assert (
            row["cost_validation_status"]
            == "validated_qualified"
        )


def test_qualified_lower_bound_semantics() -> None:
    rows = by_arm(
        read_csv(CSV_OUT)
    )

    lower_bound_arms = {
        "router-grok-build-0.1",
        "router-gemini-flash",
        "router-qwen-3.7-plus",
    }

    for arm_id in lower_bound_arms:
        row = rows[arm_id]

        assert (
            row["contract_state"]
            == "normalized_qualified_lower_bound"
        )

        assert (
            row["usage_authority"]
            == "harness_usage_validated"
        )

        assert (
            row["usage_validation_status"]
            == "validated_qualified"
        )

        assert (
            row["cost_basis"]
            == "lower_bound_provider_evidence"
        )

        assert (
            row["cost_relation"]
            == "lower_bound"
        )

        assert (
            row["cost_validation_status"]
            == "validated_qualified"
        )


def test_anthropic_absence_is_explicit() -> None:
    rows = by_arm(
        read_csv(CSV_OUT)
    )

    anthropic = {
        "router-anthropic-fable-5",
        "router-anthropic-haiku-sanitized",
        "router-anthropic-opus",
        "router-anthropic-sonnet",
    }

    for arm_id in anthropic:
        row = rows[arm_id]

        assert (
            row["contract_state"]
            == (
                "accepted_absence_"
                "anthropic_not_normalized"
            )
        )

        assert (
            row[
                "normalized_usage_reconciliation"
            ]
            == "false"
        )

        assert (
            row[
                "normalized_cost_reconciliation"
            ]
            == "false"
        )

        assert row["usage_authority"] == ""
        assert row["cost_basis"] == ""
        assert row["usage_source_roles"] == ""
        assert row["cost_source_roles"] == ""

        reason = row[
            "accepted_absence_reason"
        ]

        assert (
            "Absence is accepted"
            in reason
        )

        assert (
            "ingestion defect"
            in reason
        )


def test_glm_deliberate_empty_state_is_explicit() -> None:
    rows = by_arm(
        read_csv(CSV_OUT)
    )

    for arm_id in (
        "router-glm-5.1",
        "router-glm-5.2",
    ):
        row = rows[arm_id]

        assert (
            row["contract_state"]
            == (
                "accepted_absence_"
                "glm_deliberate_empty"
            )
        )

        assert (
            row[
                "normalized_usage_reconciliation"
            ]
            == "false"
        )

        assert (
            row[
                "normalized_cost_reconciliation"
            ]
            == "false"
        )

        assert row["usage_authority"] == ""
        assert row["cost_basis"] == ""

        assert (
            "deliberately empty"
            in row[
                "accepted_absence_reason"
            ]
        )


def test_provenance_hashes_are_preserved() -> None:
    rows = read_csv(CSV_OUT)

    for row in rows:
        assert (
            row["ledger_sha256"]
            == EXPECTED_LEDGER_SHA256
        )

        assert (
            row["private_inventory_sha256"]
            == EXPECTED_INVENTORY_SHA256
        )

        assert (
            row["private_contract_sha256"]
            == EXPECTED_PRIVATE_CONTRACT_SHA256
        )


def test_report_preserves_methodology() -> None:
    report = REPORT_OUT.read_text(
        encoding="utf-8"
    )

    required = (
        (
            "# Phase 3 Cross-Provider Evidence "
            "Consistency — 2026-08-28"
        ),
        (
            "Absence is not automatically "
            "an ingestion defect."
        ),
        (
            "Provider source rows do not have "
            "to be arm-run scoped."
        ),
        "Provider-family isolation is mandatory.",
        (
            "Exact, estimate, and lower-bound "
            "semantics remain distinct."
        ),
        (
            "Historical context is not "
            "selected-run authority by default."
        ),
        (
            "Both selected GLM arms remain "
            "deliberately empty"
        ),
        (
            "No first-party Anthropic provider "
            "evidence was normalized"
        ),
        (
            "## Post-review provenance "
            "clarifications — 2026-08-30"
        ),
        "provider_time_grid_no_metrics",
        (
            "The selected June usage and cost "
            "exports supporting GPT-5.4 and GPT-5.5 "
            "were unchanged."
        ),
        (
            "does not change either OpenAI "
            "selected-run contract state"
        ),
        "`accepted_absence_anthropic_not_normalized`",
        (
            "It is not a claim that Anthropic "
            "lacks provider APIs."
        ),
        "`ANTHROPIC_ADMIN_API_KEY`",
        EXPECTED_INVENTORY_SHA256,
        EXPECTED_PRIVATE_CONTRACT_SHA256,
        EXPECTED_OPENAI_SOURCE_MANIFEST_SHA256,
        EXPECTED_ANTHROPIC_CLOSURE_SHA256,
    )

    for value in required:
        assert value in report


def test_generated_outputs_use_lf_and_one_final_newline() -> None:
    for path in (
        CSV_OUT,
        REPORT_OUT,
    ):
        payload = path.read_bytes()

        assert b"\r" not in payload, path
        assert payload.endswith(b"\n"), path
        assert not payload.endswith(
            b"\n\n"
        ), path
