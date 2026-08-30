from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

METHODOLOGY = (
    ROOT
    / "docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md"
)
SMOKE_PLAN = (
    ROOT
    / "docs/plans/phase3/PHASE3_SMOKE_PLAN.md"
)
ROADMAP = (
    ROOT
    / "docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md"
)
CHECK = ROOT / "scripts/check.sh"


def methodology() -> str:
    return METHODOLOGY.read_text(encoding="utf-8")


def test_successful_execution_does_not_imply_valid_telemetry():
    text = methodology()
    normalized = " ".join(text.split())

    assert (
        "A successful benchmark execution does not establish that its "
        "telemetry is correct."
        in normalized
    )
    assert (
        "Harness telemetry is evidence, not authority, until "
        "independently qualified."
        in normalized
    )


def test_usage_and_cost_are_independent_validation_branches():
    text = methodology()

    assert "### Usage validation branch" in text
    assert "### Cost validation branch" in text

    assert "usage_validation_status" in text
    assert "cost_validation_status" in text


def test_methodology_preserves_harness_provider_and_selected_layers():
    text = methodology()

    assert "### 1. Harness evidence" in text
    assert "### 2. Provider usage evidence" in text
    assert "### 3. Provider cost evidence" in text

    assert "harness reported value" in text
    assert "provider evidence" in text
    assert "selected reviewed value" in text


def test_canary_is_a_real_provider_evidence_gate():
    text = methodology()

    assert (
        "Canary: establish evidence visibility and a candidate authority"
        in text
    )
    assert (
        "Canary may advance with `provisional` usage or cost authority"
        in text
    )
    assert (
        "the request reaches the intended provider/backend"
        in text
    )
    assert (
        "provider usage can be associated with the Canary run"
        in text
    )


def test_smoke_is_the_full_sweep_authority_gate():
    text = methodology()

    assert (
        "Smoke: validate repeatability and the best available authority"
        in text
    )
    assert (
        "`provisional` is not sufficient for Full."
        in text
    )

    assert text.count(
        "must be validated_exact or validated_qualified"
    ) >= 2


def test_full_sweep_is_not_a_telemetry_discovery_stage():
    text = methodology()
    normalized = " ".join(text.split())

    assert (
        "Full sweep is an experiment, not a telemetry-discovery stage."
        in normalized
    )
    assert (
        "If Full reveals a new usage or cost mismatch, economic "
        "qualification should fail closed"
        in normalized
    )


def test_methodology_is_harness_agnostic_for_future_agent_work():
    text = methodology()

    assert "The contract is intentionally harness-agnostic." in text
    assert "## Future harness experiments" in text
    assert (
        "a new harness requires Canary/Smoke telemetry qualification"
        in text
    )


def test_silent_failure_examples_are_explicit():
    text = methodology()

    required = (
        "nonzero token usage with zero harness cost",
        "nonzero harness cost with zero or absent usage",
        "custom/router alias not recognized by harness pricing",
        "missing provider evidence after an apparently successful "
        "benchmark run",
        "partial evidence displayed as exact",
    )

    for phrase in required:
        assert phrase in text


def test_smoke_plan_links_methodology_exactly_once():
    text = SMOKE_PLAN.read_text(encoding="utf-8")

    assert text.count(
        "docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md"
    ) == 1

    assert text.count(
        "evidence-authority gates for both usage and cost"
    ) == 1


def test_roadmap_makes_methodology_required_for_new_paid_waves():
    text = ROADMAP.read_text(encoding="utf-8")

    assert (
        "Before designing or authorizing new paid benchmark waves"
        in text
    )
    assert (
        "docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md"
        in text
    )

    assert (
        "Canary may establish a documented provisional authority "
        "for Smoke"
        in text
    )
    assert (
        "Smoke must establish validated exact or qualified usage "
        "and cost authority"
        in text
    )


def test_check_compiles_evidence_qualification_once():
    text = CHECK.read_text(encoding="utf-8")

    assert text.count(
        "python -m py_compile scripts/lib/evidence_qualification.py"
    ) == 1


def test_promotion_evidence_chain_is_exact_current_and_fail_closed():
    normalized = " ".join(methodology().split())

    assert (
        "A promotion decision is valid only for one exact evidence chain."
        in normalized
    )
    assert (
        "the usage reconciliation is no longer current"
        in normalized
    )
    assert (
        "the cost reconciliation is no longer current"
        in normalized
    )
    assert (
        "Superseding either reconciliation therefore invalidates the "
        "effective promotion status of an older gate"
        in normalized
    )
    assert (
        "`validated_exact` cost requires an `exact` selected-cost relation"
        in normalized
    )
    assert (
        "unavailable provider usage is a reconciliation state, not a "
        "fabricated provider-usage evidence row"
        in normalized
    )
    assert (
        "unavailable provider cost is a reconciliation state, not a "
        "fabricated provider-cost evidence row"
        in normalized
    )
