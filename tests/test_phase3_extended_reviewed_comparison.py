from __future__ import annotations

import csv
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest
import scripts.generate_phase3_extended_reviewed_comparison as generator_module

from scripts.generate_phase3_extended_reviewed_comparison import (
    EXTENDED_QUALIFIED_COST,
    SCHEMA_VERSION,
    default_input_paths,
    generate_snapshot,
    serialize_dashboard_module,
    serialize_snapshot,
    write_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
CHECKED_SNAPSHOT = (
    ROOT / "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json"
)
CHECKED_DASHBOARD_MODULE = (
    ROOT / "apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts"
)
EXPECTED_CORE_ARMS = {
    "router-anthropic-fable-5",
    "router-anthropic-haiku-sanitized",
    "router-anthropic-opus",
    "router-anthropic-sonnet",
    "router-deepseek-flash",
    "router-deepseek-pro",
    "router-gemini-3.1-pro",
    "router-gemini-flash",
    "router-glm-5.1",
    "router-glm-5.2",
    "router-gpt-5.4",
    "router-gpt-5.5",
    "router-grok-build-0.1",
    "router-kimi-k2.6",
    "router-qwen-3.7-plus",
}
EXPECTED_INPUT_HASHES = {
    "docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md": "6e36a10dffe55c67904bb5bfbc2ab886bd6aa1b60357ff21b2087d905f795f55",
    "docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md": "e18d9213e540683e6d025027424848f8c511539b176a99f85e33a474ab629604",
    "results/phase1/combined.csv": "632b4c13ba02d52a1144821a0c1776e8b75ab19a6730209d3ccdc4c0b13f074f",
    "results/phase2/combined.csv": "7e9c5a2ae64e2a96fc06a2f7f1ae2e67c4e289f7496107df5c1ec7e44b2c4367",
    "results/phase3/reporting/cross_phase_adjusted_comparison_20260714.tsv": "2b616378484cb00d854ec8b8441b2a371d097c8067e39e3a87f31a5c1d4ef524",
    "results/phase3/reporting/kimi_k3_provider_log_reconciliation_20260805.csv": "c2057dbb19e28159a301607385e22695bbf25c0c43e8b30c663f2e3023a64021",
    "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv": "59cd8eeabd98be1695ec4f0b199bf4935a3bf4c9bdde744669b8188db1845150",
    "results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv": "32d8e3659147291e39b2eaa8ac4d1714df437f1aae070bae43f2172792e06f3b",
    "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv": "dda44c435b555d3f358a47b5885c659b9ae0554511959ca9d40f76bc9539f5a3",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_dashboard_module(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    prefix = "const reviewedSnapshot = JSON.parse("
    start = source.index(prefix) + len(prefix)
    end = source.index(");\nexport default reviewedSnapshot;", start)
    compact_json = json.loads(source[start:end])
    return json.loads(compact_json)


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return generate_snapshot(default_input_paths())


def test_checked_snapshot_is_deterministic_and_has_exact_source_hashes(
    snapshot: dict, tmp_path: Path
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first_module = tmp_path / "first.ts"
    second_module = tmp_path / "second.ts"
    write_snapshot(default_input_paths(), first, first_module)
    write_snapshot(default_input_paths(), second, second_module)

    assert first.read_bytes() == second.read_bytes()
    assert first_module.read_bytes() == second_module.read_bytes()
    assert first.read_bytes() == CHECKED_SNAPSHOT.read_bytes()
    assert first_module.read_bytes() == CHECKED_DASHBOARD_MODULE.read_bytes()
    assert first.read_text(encoding="utf-8") == serialize_snapshot(snapshot)
    assert first_module.read_text(encoding="utf-8") == serialize_dashboard_module(snapshot)
    assert parse_dashboard_module(first_module) == json.loads(first.read_text(encoding="utf-8"))
    assert parse_dashboard_module(CHECKED_DASHBOARD_MODULE) == json.loads(
        CHECKED_SNAPSHOT.read_text(encoding="utf-8")
    )
    assert snapshot["schemaVersion"] == SCHEMA_VERSION
    assert snapshot["reviewedAt"] == "2026-08-05"

    recorded = {item["path"]: item["sha256"] for item in snapshot["inputs"]}
    expected = {
        path.resolve().relative_to(ROOT).as_posix(): sha256(path)
        for path in default_input_paths().values()
    }
    assert recorded == expected == EXPECTED_INPUT_HASHES


def test_core_and_extended_membership_counts_and_costs(snapshot: dict) -> None:
    core = snapshot["scopes"]["phase3-core"]
    extended = snapshot["scopes"]["phase3-extended"]
    core_ids = {arm["armId"] for arm in core["arms"]}
    extended_ids = {arm["armId"] for arm in extended["arms"]}

    assert (core["armCount"], core["trialCount"], core["successCount"]) == (15, 900, 515)
    assert (extended["armCount"], extended["trialCount"], extended["successCount"]) == (
        16,
        960,
        562,
    )
    assert core_ids == EXPECTED_CORE_ARMS
    assert "router-kimi-k3" not in core_ids
    assert extended_ids == EXPECTED_CORE_ARMS | {"router-kimi-k3"}
    assert core["costEvidence"]["adjustedKnownCostUsd"] == "972.169845489198"
    assert core["costEvidence"]["qualifiedAdjustedCostEstimateUsd"] is None
    assert extended["costEvidence"]["adjustedKnownCostUsd"] is None
    assert extended["costEvidence"]["qualifiedAdjustedCostEstimateUsd"] == str(
        EXTENDED_QUALIFIED_COST
    )
    assert extended["costEvidence"]["outcomeCostAllocationStatus"] == "partial_core_only"
    for field in (
        "adjustedCleanSuccessCostUsd",
        "adjustedExceptionSuccessSignalCostUsd",
        "adjustedFailureOrIncompleteCostUsd",
        "failureOrIncompleteSpendShare",
        "nonproductiveOrUncleanSpendShare",
        "adjustedCostPerCleanSuccessUsd",
        "adjustedCostPerAnySuccessUsd",
    ):
        assert extended["costEvidence"][field] is None


def test_core_outcome_cost_rows_preserve_source_and_extended_explicitly_excludes_kimi(
    snapshot: dict,
) -> None:
    core = snapshot["scopes"]["phase3-core"]
    extended = snapshot["scopes"]["phase3-extended"]
    core_coverage = core["outcomeCostCoverage"]
    extended_coverage = extended["outcomeCostCoverage"]
    rows = core_coverage["rows"]

    assert core_coverage["status"] == "available"
    assert core_coverage["coveredTrialCount"] == 900
    assert core_coverage["excludedTrialCount"] == 0
    assert core_coverage["excludedArmIds"] == []
    assert [row["outcomeBucket"] for row in rows] == [
        "clean_success",
        "exception_with_success_signal",
        "normal_failure",
        "exception_failure",
    ]
    assert sum(row["trialCount"] for row in rows) == 900
    assert sum((Decimal(row["recordedCostUsd"]) for row in rows), Decimal()) == Decimal(
        core["costEvidence"]["recordedCostUsd"]
    )
    source_adjusted_total = sum(
        (Decimal(row["sourceAdjustedKnownCostUsd"]) for row in rows), Decimal()
    )
    source_gap_total = sum(
        (Decimal(row["sourceAccountingGapUsd"]) for row in rows), Decimal()
    )
    assert source_adjusted_total == Decimal("972.169845489205")
    assert source_gap_total == source_adjusted_total - Decimal(
        core["costEvidence"]["recordedCostUsd"]
    )
    assert core_coverage["sourceAdjustedKnownCostTotalUsd"] == "972.169845489205"
    assert core_coverage["reviewedAdjustedKnownCostTotalUsd"] == "972.169845489198"
    assert core_coverage["reviewedScopeReconciliationAdjustmentUsd"] == "-0.000000000007"
    assert "reconciledOutcomeBucket" not in core_coverage
    assert (
        Decimal(core_coverage["sourceAdjustedKnownCostTotalUsd"])
        + Decimal(core_coverage["reviewedScopeReconciliationAdjustmentUsd"])
        == Decimal(core_coverage["reviewedAdjustedKnownCostTotalUsd"])
    )

    source_rows: dict[str, dict[str, Decimal | int]] = {}
    with default_input_paths()["phase3_trial_cost_coverage"].open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        for trial in csv.DictReader(handle, delimiter="\t"):
            bucket = trial["outcome_bucket"]
            aggregate = source_rows.setdefault(
                bucket,
                {
                    "trialCount": 0,
                    "recorded": Decimal(),
                    "adjusted": Decimal(),
                    "missingRecordedCostCount": 0,
                    "unresolvedAdjustedCostCount": 0,
                },
            )
            aggregate["trialCount"] += 1
            if trial["recorded_cost_usd"]:
                aggregate["recorded"] += Decimal(trial["recorded_cost_usd"])
            else:
                aggregate["missingRecordedCostCount"] += 1
            if trial["adjusted_cost_usd"]:
                aggregate["adjusted"] += Decimal(trial["adjusted_cost_usd"])
            else:
                aggregate["unresolvedAdjustedCostCount"] += 1
    for row in rows:
        source = source_rows[row["outcomeBucket"]]
        assert row["trialCount"] == source["trialCount"]
        assert Decimal(row["recordedCostUsd"]) == source["recorded"]
        assert Decimal(row["sourceAdjustedKnownCostUsd"]) == source["adjusted"]
        assert Decimal(row["sourceAccountingGapUsd"]) == source["adjusted"] - source["recorded"]
        assert row["missingRecordedCostCount"] == source["missingRecordedCostCount"]
        assert row["unresolvedAdjustedCostCount"] == source["unresolvedAdjustedCostCount"]

    assert extended_coverage["status"] == "partial_core_only"
    assert extended_coverage["coveredTrialCount"] == 900
    assert extended_coverage["excludedTrialCount"] == 60
    assert extended_coverage["excludedArmIds"] == ["router-kimi-k3"]
    assert extended_coverage["rows"] == rows
    assert extended_coverage == {
        **core_coverage,
        "status": "partial_core_only",
        "coveredTrialCount": 900,
        "excludedTrialCount": 60,
        "excludedArmIds": ["router-kimi-k3"],
    }


def test_kimi_cost_evidence_is_distinct_and_unavailable_is_not_zero(snapshot: dict) -> None:
    extended = snapshot["scopes"]["phase3-extended"]
    kimi = next(arm for arm in extended["arms"] if arm["armId"] == "router-kimi-k3")

    assert (kimi["trialCount"], kimi["successCount"], kimi["cleanSuccessCount"]) == (60, 47, 44)
    assert kimi["recordedCostUsd"] == "25.207213"
    assert kimi["qualifiedRetainedRateCostUsd"] == "30.8143194"
    assert kimi["accountingGapUsd"] == "5.6071064"
    assert len({
        kimi["recordedCostUsd"],
        kimi["qualifiedRetainedRateCostUsd"],
        kimi["accountingGapUsd"],
    }) == 3
    assert kimi["costBasis"] == "qualified_retained_rate_estimate"
    assert kimi["pricingProvenanceStatus"] == "incomplete"
    assert kimi["armRunAllocationConfidence"] == "low"
    assert kimi["trialAllocationStatus"] == "unresolved"
    assert kimi["billingReconciliationStatus"] == "not_invoice_level_or_provider_billed"
    assert kimi["outcomeCostAllocationStatus"] == "unavailable"

    unsupported = (
        "adjustedKnownCostUsd",
        "adjustedCostPerCleanSuccessUsd",
        "adjustedCostPerAnySuccessUsd",
        "adjustedCleanSuccessCostUsd",
        "adjustedExceptionSuccessSignalCostUsd",
        "adjustedFailureOrIncompleteCostUsd",
        "failureOrIncompleteSpendShare",
        "nonproductiveOrUncleanSpendShare",
        "medianWallClockSeconds",
    )
    assert all(kimi[field] is None for field in unsupported)
    assert not any(kimi[field] == 0 for field in unsupported)


def test_generator_does_not_modify_inputs(snapshot: dict) -> None:
    paths = default_input_paths()
    before = {key: sha256(path) for key, path in paths.items()}
    assert generate_snapshot(paths) == snapshot
    after = {key: sha256(path) for key, path in paths.items()}
    assert after == before


def test_malformed_core_input_fails_closed(tmp_path: Path) -> None:
    paths = default_input_paths()
    source = paths["phase3_core_summary"]
    malformed = tmp_path / "malformed-core.tsv"
    lines = source.read_text(encoding="utf-8").splitlines()
    malformed.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    paths["phase3_core_summary"] = malformed

    with pytest.raises(ValueError, match="core arm sources disagree|core counts mismatch"):
        generate_snapshot(paths)


def test_trial_cost_input_requires_outcome_and_cost_columns(tmp_path: Path) -> None:
    paths = default_input_paths()
    source = paths["phase3_trial_cost_coverage"]
    malformed = tmp_path / "malformed-trial-costs.tsv"
    lines = source.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    recorded_index = header.index("recorded_cost_usd")
    malformed_lines = []
    for line in lines:
        fields = line.split("\t")
        del fields[recorded_index]
        malformed_lines.append("\t".join(fields))
    malformed.write_text("\n".join(malformed_lines) + "\n", encoding="utf-8")
    paths["phase3_trial_cost_coverage"] = malformed

    with pytest.raises(ValueError, match="missing columns: recorded_cost_usd"):
        generate_snapshot(paths)


@pytest.mark.parametrize("which_output", ["json", "dashboard"])
def test_output_path_cannot_equal_any_input(tmp_path: Path, which_output: str) -> None:
    paths = default_input_paths()
    json_output = tmp_path / "snapshot.json"
    dashboard_output = tmp_path / "snapshot.ts"
    if which_output == "json":
        json_output = paths["phase3_core_summary"]
    else:
        dashboard_output = paths["phase3_core_summary"]
    with pytest.raises(ValueError, match="must not equal an input"):
        write_snapshot(paths, json_output, dashboard_output)


@pytest.mark.parametrize("which_output", ["json", "dashboard"])
def test_existing_hard_link_output_alias_is_rejected(tmp_path: Path, which_output: str) -> None:
    paths = default_input_paths()
    source = paths["phase3_core_summary"]
    output = tmp_path / f"hard-linked-output.{which_output}"
    os.link(source, output)
    before = sha256(source)
    json_output = output if which_output == "json" else tmp_path / "snapshot.json"
    dashboard_output = output if which_output == "dashboard" else tmp_path / "snapshot.ts"

    with pytest.raises(ValueError, match="must not alias an input"):
        write_snapshot(paths, json_output, dashboard_output)

    assert sha256(source) == before


@pytest.mark.parametrize("which_output", ["json", "dashboard"])
def test_existing_symlink_output_alias_is_rejected_when_supported(
    tmp_path: Path, which_output: str
) -> None:
    paths = default_input_paths()
    source = paths["phase3_core_summary"]
    output = tmp_path / f"symlink-output.{which_output}"
    try:
        output.symlink_to(source)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    before = sha256(source)
    json_output = output if which_output == "json" else tmp_path / "snapshot.json"
    dashboard_output = output if which_output == "dashboard" else tmp_path / "snapshot.ts"

    with pytest.raises(ValueError, match="must not (?:equal|alias) an input"):
        write_snapshot(paths, json_output, dashboard_output)

    assert sha256(source) == before


def test_generated_outputs_must_not_alias_each_other(tmp_path: Path) -> None:
    output = tmp_path / "shared-output"
    with pytest.raises(ValueError, match="must be distinct"):
        write_snapshot(default_input_paths(), output, output)

    json_output = tmp_path / "snapshot.json"
    dashboard_output = tmp_path / "snapshot.ts"
    json_output.write_text("existing\n", encoding="utf-8")
    try:
        os.link(json_output, dashboard_output)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    with pytest.raises(ValueError, match="must not alias each other"):
        write_snapshot(default_input_paths(), json_output, dashboard_output)


def test_generated_outputs_must_not_symlink_alias_each_other_when_supported(
    tmp_path: Path,
) -> None:
    json_output = tmp_path / "snapshot.json"
    json_output.write_text("existing\n", encoding="utf-8")
    dashboard_output = tmp_path / "snapshot.ts"
    try:
        dashboard_output.symlink_to(json_output)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ValueError, match="must be distinct|must not alias each other"):
        write_snapshot(default_input_paths(), json_output, dashboard_output)


def test_atomic_write_cleans_temporary_file_after_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "snapshot.json"
    dashboard_output = tmp_path / "snapshot.ts"

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(generator_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        write_snapshot(default_input_paths(), output, dashboard_output)

    assert not output.exists()
    assert not dashboard_output.exists()
    assert list(tmp_path.iterdir()) == []


def test_snapshot_contains_no_raw_provider_identifiers(snapshot: dict) -> None:
    serialized = json.dumps(snapshot, sort_keys=True)
    generated_outputs = serialize_snapshot(snapshot) + serialize_dashboard_module(snapshot)
    prohibited_keys = {
        "requestId",
        "request_id",
        "projectId",
        "project_id",
        "apiKeyId",
        "api_key_id",
        "providerRows",
        "rawProviderRows",
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            assert prohibited_keys.isdisjoint(value)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(snapshot)
    for content in (serialized, generated_outputs):
        assert "MoonshotAI Openplatform Request Log" not in content
        assert "request_log_part_0001.csv" not in content


def test_generated_output_equivalence_detects_either_side_changing(snapshot: dict) -> None:
    canonical = json.loads(serialize_snapshot(snapshot))
    generated = json.loads(json.dumps(parse_dashboard_module(CHECKED_DASHBOARD_MODULE)))
    assert generated == canonical

    changed_canonical = json.loads(json.dumps(canonical))
    changed_canonical["reviewedAt"] = "2026-08-06"
    assert changed_canonical != generated

    changed_generated = json.loads(json.dumps(generated))
    changed_generated["scopes"]["phase3-core"]["trialCount"] = 899
    assert changed_generated != canonical
