from __future__ import annotations

import csv
import hashlib
import re
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

NORMALIZED = ROOT / "results/phase3/provider_usage/normalized"
MANIFEST = NORMALIZED / "openai_provider_source_manifest_20260821.csv"
ACTIVITY = NORMALIZED / "openai_provider_activity_20260821.csv"
RECON = NORMALIZED / "openai_provider_reconciliation_20260821.csv"

FROZEN_HASHES = {
    "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json":
        "49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d",
    "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv":
        "dda44c435b555d3f358a47b5885c659b9ae0554511959ca9d40f76bc9539f5a3",
    "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv":
        "59cd8eeabd98be1695ec4f0b199bf4935a3bf4c9bdde744669b8188db1845150",
    "results/manual_verification/comprehensive_review_20260731/trial_review.csv":
        "c6945d114e3a2e0610dfd091bad8ea4e9bc17707db678e90f4e0f8058fc56501",
}

RAW_HASHES = {
    "cost_2026-05-01_2026-05-31.csv":
        "51448a7ed68e3ee0c3abc3e00d02edb0498bfe822bb1388d4786103b33d3f3cc",
    "cost_2026-06-01_2026-07-01.csv":
        "04cea7cd630c0dd7a4aef144d005eb3640a70072f24f4c6a5132016ea3bfd12d",
    "cost_2026-07-02_2026-08-01.csv":
        "e2e012c326f11e7c5b258e1bf8b0e0e8bbf5bb46e9f7036aba85b13ddd868dbc",
    "cost_2026-08-02_2026-08-21.csv":
        "16674614b40a9a112347a651e1ee98e7a3d857db75172c85def6e44c2c8c7416",
    "completions_usage_2026-05-01_2026-05-31.csv":
        "51448a7ed68e3ee0c3abc3e00d02edb0498bfe822bb1388d4786103b33d3f3cc",
    "completions_usage_2026-06-01_2026-07-01.csv":
        "9c4dc05dd36164ba34cb387f9ca97fb63255b8ac0aeff2782b00784a6cf2d108",
    "completions_usage_2026-07-02_2026-08-01.csv":
        "e2e012c326f11e7c5b258e1bf8b0e0e8bbf5bb46e9f7036aba85b13ddd868dbc",
    "completions_usage_2026-08-02_2026-08-21.csv":
        "16674614b40a9a112347a651e1ee98e7a3d857db75172c85def6e44c2c8c7416",
}

PRIVATE_PATTERNS = (
    re.compile(r"\bproj_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bkey_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\borg-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _assert_sanitized(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in PRIVATE_PATTERNS:
        assert not pattern.search(text)


def test_frozen_dr303_sources_remain_byte_identical() -> None:
    for relative, expected in FROZEN_HASHES.items():
        assert _sha256(ROOT / relative) == expected


def test_private_source_manifest_is_complete_and_sanitized() -> None:
    rows = _rows(MANIFEST)
    assert len(rows) == 8
    assert {row["source_file"] for row in rows} == set(RAW_HASHES)

    for row in rows:
        assert row["sha256"] == RAW_HASHES[row["source_file"]]
        assert row["raw_source_committed"] == "false"
        assert row["contains_private_identifiers"] == "true"

    by_file = {
        row["source_file"]: row
        for row in rows
    }

    selected_types = {
        "cost_2026-06-01_2026-07-01.csv": "provider_cost_export",
        (
            "completions_usage_2026-06-01_2026-07-01.csv"
        ): "provider_usage_export",
    }
    selected_rule = (
        "raw file remains private; only aggregate/date/model/token/cost "
        "facts are retained"
    )

    for source_file, source_type in selected_types.items():
        assert by_file[source_file]["source_type"] == source_type
        assert (
            by_file[source_file]["sanitization_rule"]
            == selected_rule
        )

    nonselected = set(RAW_HASHES) - set(selected_types)
    nonselected_rule = (
        "raw file remains private; reviewed bytes contain only "
        "start_time/end_time time-grid fields and no usage or cost metrics"
    )

    assert len(nonselected) == 6

    for source_file in nonselected:
        assert (
            by_file[source_file]["source_type"]
            == "provider_time_grid_no_metrics"
        )
        assert (
            by_file[source_file]["sanitization_rule"]
            == nonselected_rule
        )

    _assert_sanitized(MANIFEST)


def test_sanitized_provider_activity_reconciles_project_period() -> None:
    rows = _rows(ACTIVITY)
    cost_rows = [row for row in rows if row["record_type"] == "daily_provider_cost"]
    usage_rows = [row for row in rows if row["record_type"] == "model_usage"]

    assert len(cost_rows) == 4
    assert len(usage_rows) == 6

    assert {
        row["provider_activity_date"]: Decimal(row["provider_billed_cost_usd"])
        for row in cost_rows
    } == {
        "2026-06-03": Decimal("1.1812985"),
        "2026-06-16": Decimal("15.662944"),
        "2026-06-19": Decimal("29.7919335"),
        "2026-06-27": Decimal("48.604914"),
    }

    assert sum(
        Decimal(row["provider_billed_cost_usd"]) for row in cost_rows
    ) == Decimal("95.2410900")

    assert sum(int(row["request_count"]) for row in usage_rows) == 2964
    assert sum(int(row["input_tokens"]) for row in usage_rows) == 74364964
    assert sum(int(row["cached_input_tokens"]) for row in usage_rows) == 66424320
    assert sum(int(row["uncached_input_tokens"]) for row in usage_rows) == 7940644
    assert sum(int(row["output_tokens"]) for row in usage_rows) == 2047316

    for row in usage_rows:
        assert int(row["input_tokens"]) == (
            int(row["cached_input_tokens"])
            + int(row["uncached_input_tokens"])
        )

    _assert_sanitized(ACTIVITY)


def test_full_sweep_provider_costs_match_frozen_selected_runs() -> None:
    recon_rows = _rows(RECON)
    project = [row for row in recon_rows if row["record_type"] == "project_period"]
    sweeps = {
        row["arm_id"]: row
        for row in recon_rows
        if row["record_type"] == "full_sweep"
    }

    assert len(project) == 1
    assert Decimal(project[0]["provider_billed_cost_usd"]) == Decimal("95.2410900")
    assert project[0]["active_project_count"] == "1"
    assert project[0]["active_api_key_count"] == "1"

    assert set(sweeps) == {"router-gpt-5.4", "router-gpt-5.5"}

    gpt54 = sweeps["router-gpt-5.4"]
    gpt55 = sweeps["router-gpt-5.5"]

    assert gpt54["selected_run_label"] == (
        "router-gpt-5.4/2026-06-19__13-47-51"
    )
    assert gpt55["selected_run_label"] == (
        "router-gpt-5.5/2026-06-27__01-30-18"
    )

    assert Decimal(gpt54["provider_billed_cost_usd"]) == Decimal("29.7919335")
    assert Decimal(gpt55["provider_billed_cost_usd"]) == Decimal("48.604914")

    assert (
        Decimal(gpt54["provider_billed_cost_usd"])
        + Decimal(gpt55["provider_billed_cost_usd"])
        == Decimal("78.3968475")
    )

    assert Decimal(gpt54["historical_harness_recorded_cost_usd"]) == Decimal(
        "173.09483"
    )
    assert Decimal(gpt55["historical_harness_recorded_cost_usd"]) == Decimal(
        "168.708375"
    )
    assert Decimal(gpt54["historical_reviewed_adjusted_cost_usd"]) == Decimal(
        "183.646689146806"
    )
    assert Decimal(gpt55["historical_reviewed_adjusted_cost_usd"]) == Decimal(
        "183.958832348525"
    )

    for row in sweeps.values():
        assert row["provider_billing_reconciliation_status"] == "exact_arm_total"
        assert row["trial_cost_allocation_status"] == (
            "unavailable_provider_aggregate"
        )
        assert row["outcome_cost_allocation_status"] == (
            "unavailable_provider_aggregate"
        )

    _assert_sanitized(RECON)


def test_reconciliation_selected_run_membership_matches_frozen_review() -> None:
    recon = {
        row["arm_id"]: row
        for row in _rows(RECON)
        if row["record_type"] == "full_sweep"
    }

    run_review = _rows(
        ROOT
        / "results/manual_verification/comprehensive_review_20260731/run_review.csv"
    )
    selected = {
        row["arm_id"]: row
        for row in run_review
        if row["arm_id"] in recon and row["selected"] == "True"
    }

    assert set(selected) == set(recon)

    for arm_id, row in recon.items():
        assert selected[arm_id]["run_label"] == row["selected_run_label"]
        assert selected[arm_id]["trial_count"] == "60"
        assert selected[arm_id]["valid"] == "True"


def test_reconciliation_preserves_historical_cost_values_as_diagnostics() -> None:
    recon = {
        row["arm_id"]: row
        for row in _rows(RECON)
        if row["record_type"] == "full_sweep"
    }

    coverage = {
        row["arm_id"]: row
        for row in _rows(
            ROOT / "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv",
            delimiter="\t",
        )
        if row["arm_id"] in recon
    }

    assert set(coverage) == set(recon)

    for arm_id, row in recon.items():
        assert Decimal(coverage[arm_id]["recorded_cost_usd"]) == Decimal(
            row["historical_harness_recorded_cost_usd"]
        )
        assert Decimal(coverage[arm_id]["adjusted_cost_usd"]) == Decimal(
            row["historical_reviewed_adjusted_cost_usd"]
        )
