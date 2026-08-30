from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GENERATOR = (
    ROOT
    / "scripts/"
      "generate_phase3_provider_evidence_audit_20260825.py"
)
BASE = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260824.csv"
)
CURRENT = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_current_arm_cost_reconciliation_20260825.csv"
)
MATRIX = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_provider_cost_evidence_matrix_20260825.csv"
)
CHRONOLOGY = (
    ROOT
    / "results/phase3/reporting/"
      "phase3_provider_run_chronology_20260825.csv"
)
REPORT = (
    ROOT
    / "docs/reports/phase3/"
      "PHASE3_PROVIDER_COST_EVIDENCE_AUDIT_20260825.md"
)

EXPECTED_BASE_SHA256 = (
    "7fc2ac41dfd56af4888cac0cc6d80be15f5d3b8edef12b915206fd57bc9afbea"
)

GENERATED_PATHS = (
    CURRENT,
    MATRIX,
    CHRONOLOGY,
    REPORT,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def by_arm(
    rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    return {
        row["arm_id"]: row
        for row in rows
    }


def test_frozen_20260824_base_is_hash_bound() -> None:
    assert sha256(BASE) == EXPECTED_BASE_SHA256


def test_checked_outputs_are_deterministic_generator_products() -> None:
    before = {
        path: path.read_bytes()
        for path in GENERATED_PATHS
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

    assert "successor reconciliation rows: 16" in result.stdout
    assert "provider evidence matrix rows: 16" in result.stdout

    after = {
        path: path.read_bytes()
        for path in GENERATED_PATHS
    }

    assert after == before


def test_successor_preserves_base_rows_exactly() -> None:
    base = read_csv(BASE)
    current = read_csv(CURRENT)

    assert len(base) == 8
    assert len(current) == 16

    base_by_arm = by_arm(base)
    current_by_arm = by_arm(current)

    assert len(base_by_arm) == 8
    assert len(current_by_arm) == 16

    for arm_id, row in base_by_arm.items():
        assert current_by_arm[arm_id] == row


def test_new_arm_selected_costs_and_relations() -> None:
    rows = by_arm(read_csv(CURRENT))

    expected = {
        "router-grok-build-0.1": (
            Decimal("6.418694"),
            "lower_bound",
            59,
            1,
        ),
        "router-glm-5.1": (
            Decimal("5.3316552"),
            "estimate",
            55,
            0,
        ),
        "router-glm-5.2": (
            Decimal("8.9016736"),
            "estimate",
            60,
            0,
        ),
        "router-gemini-3.1-pro": (
            Decimal("19.6968138"),
            "estimate",
            60,
            0,
        ),
        "router-gemini-flash": (
            Decimal("16.12091625"),
            "lower_bound",
            56,
            4,
        ),
        "router-qwen-3.7-plus": (
            Decimal("2.50442432"),
            "lower_bound",
            59,
            1,
        ),
        "router-kimi-k2.6": (
            Decimal("6.34692415"),
            "estimate",
            60,
            0,
        ),
        "router-kimi-k3": (
            Decimal("26.570403"),
            "estimate",
            60,
            0,
        ),
    }

    for arm_id, (
        cost,
        relation,
        complete,
        unresolved,
    ) in expected.items():
        row = rows[arm_id]

        assert Decimal(
            row["selected_cost_usd"]
        ) == cost
        assert row[
            "selected_cost_relation"
        ] == relation
        assert int(
            row["complete_trial_cost_count"]
        ) == complete
        assert int(
            row["lower_bound_trial_count"]
        ) == unresolved

        # None of these newly audited arms has an exact
        # selected-run provider-billed total.
        assert row[
            "provider_billed_cost_usd"
        ] == ""

        if relation == "lower_bound":
            assert row[
                "unquantified_additional_cost_status"
            ] == (
                "possible_additional_unresolved_trial_spend"
            )
        elif arm_id == "router-glm-5.1":
            assert row[
                "unquantified_additional_cost_status"
            ] == (
                "unresolved_trial_spend_and_"
                "cache_classification_uncertainty"
            )
        else:
            assert row[
                "unquantified_additional_cost_status"
            ] in {
                "none",
                "none_for_selected_retained_usage",
            }


def test_glm_5_1_is_partial_estimate_not_lower_bound() -> None:
    current = by_arm(
        read_csv(CURRENT)
    )["router-glm-5.1"]

    matrix = by_arm(
        read_csv(MATRIX)
    )["router-glm-5.1"]

    assert current[
        "selected_cost_relation"
    ] == "estimate"

    assert current[
        "selected_cost_basis"
    ] == (
        "provider_rate_reconstructed_retained_usage_partial"
    )

    assert current[
        "complete_trial_cost_count"
    ] == "55"

    assert current[
        "lower_bound_trial_count"
    ] == "0"

    assert current[
        "trial_cost_allocation_status"
    ] == (
        "partial_selected_usage_reconstruction_with_unresolved_trials"
    )

    assert current[
        "outcome_cost_allocation_status"
    ] == "available_partial_estimate"

    assert current[
        "unquantified_additional_cost_status"
    ] == (
        "unresolved_trial_spend_and_cache_classification_uncertainty"
    )

    assert matrix[
        "unresolved_trial_count"
    ] == "5"

    assert (
        "cache_accounting_unverified"
        in matrix["pricing_provenance_status"]
    )

    chronology = [
        row
        for row in read_csv(CHRONOLOGY)
        if row["arm_id"] == "router-glm-5.1"
        and row["event_type"] == "selected_full"
    ]

    assert len(chronology) == 1
    assert chronology[0]["amount_kind"] == (
        "selected_partial_rate_estimate"
    )
    assert chronology[0]["allocation_confidence"] == (
        "55_of_60_usage_bearing_"
        "cache_accounting_unverified"
    )
    assert "not a strict lower bound" in chronology[0]["notes"]


def test_successor_scope_selected_cost_totals() -> None:
    rows = by_arm(read_csv(CURRENT))

    selected = {
        arm_id: Decimal(
            row["selected_cost_usd"]
        )
        for arm_id, row in rows.items()
    }

    core = sum(
        (
            cost
            for arm_id, cost in selected.items()
            if arm_id != "router-kimi-k3"
        ),
        Decimal("0"),
    )

    extended = sum(
        selected.values(),
        Decimal("0"),
    )

    assert core == Decimal(
        "316.8790274572"
    )
    assert extended == Decimal(
        "343.4494304572"
    )


def test_kimi_k3_provider_log_is_not_mislabeled_as_billed() -> None:
    current = by_arm(
        read_csv(CURRENT)
    )["router-kimi-k3"]

    matrix = by_arm(
        read_csv(MATRIX)
    )["router-kimi-k3"]

    assert current[
        "provider_context_billed_cost_usd"
    ] == ""

    assert Decimal(
        matrix[
            "provider_context_rate_reconstruction_usd"
        ]
    ) == Decimal(
        "30.8143194"
    )

    assert Decimal(
        matrix[
            "provider_context_rate_reconstruction_excess_vs_selected_usd"
        ]
    ) == Decimal(
        "4.2439164"
    )

    assert matrix[
        "provider_context_account_spend_usd"
    ] == ""

    assert matrix[
        "provider_context_allocation_confidence"
    ] == "low"

    assert (
        "official"
        in matrix[
            "pricing_provenance_status"
        ]
        and "missing"
        in matrix[
            "pricing_provenance_status"
        ]
    )


def test_qwen_provider_context_separates_payg_and_overhead() -> None:
    row = by_arm(
        read_csv(MATRIX)
    )["router-qwen-3.7-plus"]

    assert Decimal(
        row["provider_context_billed_cost_usd"]
    ) == Decimal("1.31089")

    assert Decimal(
        row["provider_context_account_spend_usd"]
    ) == Decimal("31.31089")

    assert Decimal(
        row["provider_context_overhead_usd"]
    ) == Decimal("30")

    assert (
        "all_requests_below_256k"
        in row["trajectory_evidence_status"]
    )


def test_gemini_provider_context_is_shared_and_nonadditive() -> None:
    matrix = by_arm(
        read_csv(MATRIX)
    )

    for arm_id in (
        "router-gemini-3.1-pro",
        "router-gemini-flash",
    ):
        row = matrix[arm_id]

        assert Decimal(
            row["provider_context_billed_cost_usd"]
        ) == Decimal("26.371228")

        assert (
            "nonadditive"
            in row["provider_context_scope"]
        )

        assert row[
            "provider_context_temporal_relation"
        ] == "predates_selected_run"

    chronology = read_csv(CHRONOLOGY)

    shared = [
        row
        for row in chronology
        if row["provider"] == "google-gemini"
        and row["event_type"]
        == "provider_billing_export"
    ]

    assert len(shared) == 1
    assert Decimal(
        shared[0]["amount_usd"]
    ) == Decimal("26.371228")
    assert shared[0][
        "allocation_confidence"
    ] == "not_model_or_run_allocable"


def test_gemini_chronology_preserves_retained_runs() -> None:
    chronology = [
        row
        for row in read_csv(CHRONOLOGY)
        if row["provider"] == "google-gemini"
    ]

    actual = {
        row["run_label_or_scope"]
        for row in chronology
        if row["event_type"]
        in {"canary", "smoke", "selected_full"}
    }

    expected = {
        "router-gemini-3.1-pro/2026-06-02__21-10-28",
        "router-gemini-3.1-pro/2026-06-02__22-17-25",
        "router-gemini-flash/2026-06-02__17-59-33",
        "router-gemini-flash/2026-06-02__20-30-15",
        "router-gemini-flash/2026-06-02__20-59-54",
        "router-gemini-3.1-pro/2026-06-16__19-04-01",
        "router-gemini-flash/2026-06-16__00-58-08",
        "router-gemini-flash/2026-06-16__19-04-09",
        "router-gemini-flash/2026-06-27__01-30-20",
        "router-gemini-3.1-pro/2026-06-30__14-57-05",
    }

    assert actual == expected


def test_trajectory_evidence_qualifications_are_preserved() -> None:
    matrix = by_arm(
        read_csv(MATRIX)
    )

    grok = matrix[
        "router-grok-build-0.1"
    ]
    glm = matrix[
        "router-glm-5.1"
    ]
    flash = matrix[
        "router-gemini-flash"
    ]
    qwen = matrix[
        "router-qwen-3.7-plus"
    ]
    pro = matrix[
        "router-gemini-3.1-pro"
    ]

    assert (
        "1_zero_metric_trial"
        in grok["trajectory_evidence_status"]
    )
    assert (
        "5_zero_metric_trials"
        in glm["trajectory_evidence_status"]
    )
    assert flash[
        "trajectory_evidence_status"
    ] == (
        "selected_run_absent_from_r2_trajectory_archive"
    )
    assert (
        "1_zero_metric_trial"
        in qwen["trajectory_evidence_status"]
    )
    assert (
        "930_requests"
        in pro["trajectory_evidence_status"]
    )
    assert (
        "max_prompt_66438"
        in pro["trajectory_evidence_status"]
    )


def test_report_declares_immutable_prior_layer() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert (
        "# Phase 3 Provider Cost Evidence Audit — 2026-08-25"
        in report
    )

    for name in (
        "phase3_current_arm_cost_reconciliation_20260824.csv",
        "phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv",
        "phase3_current_reviewed_comparison_20260824.json",
    ):
        assert name in report

    assert (
        "Dashboard/current-comparison promotion "
        "should occur only after this new layer is reviewed and validated."
        in report
    )


def test_generated_outputs_use_lf_and_single_final_newline() -> None:
    for path in GENERATED_PATHS:
        payload = path.read_bytes()

        assert b"\r" not in payload, path
        assert payload.endswith(b"\n"), path
        assert not payload.endswith(b"\n\n"), path
