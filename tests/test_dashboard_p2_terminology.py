from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dr201_shared_glossary_covers_required_concepts() -> None:
    glossary = source("apps/dashboard/src/lib/glossary.ts")

    expected_terms = (
        "Attempt",
        "Confidence",
        "Unresolved",
        "Recorded cost",
        "Adjusted known cost",
        "Accounting gap",
        "Known accounting gap",
        "Routing path",
        "Execution validity",
        "Activity class",
        "Failure subtype",
        "Policy disposition",
        "Telemetry consistency",
        "Artifact completeness",
        "R2 integrity",
    )

    for term in expected_terms:
        assert glossary.count(f'term: "{term}"') == 1, term


def test_dr201_glossary_preserves_evidence_boundaries() -> None:
    glossary = source("apps/dashboard/src/lib/glossary.ts")

    assert "run-wide trial ordinal" in glossary
    assert "GitHub workflow run attempt" in glossary

    assert "not a probability" in glossary
    assert "fabricated numeric score" in glossary
    assert "failure-taxonomy registry defines diagnosis-confidence values" in glossary

    assert "selected reviewed cost measure minus recorded cost" in glossary
    assert "Kimi K3 retained-rate estimate" in glossary
    assert "is not relabeled as adjusted known cost" in glossary

    assert "activity-subtype review field" in glossary
    assert "trajectory-disposition taxonomy" in glossary

    assert "failure-taxonomy registry owns the definitions" in glossary
    assert "Missing telemetry remains not recorded" in glossary

    assert "indexed metadata or an R2 URI alone" in glossary
    assert "An R2 URI alone does not verify object bytes" in glossary


def test_dr201_primary_surfaces_use_shared_term_info() -> None:
    comprehensive = source(
        "apps/dashboard/src/app/comprehensive-review/page.tsx"
    )
    cost = source("apps/dashboard/src/app/cost-coverage/page.tsx")
    trial = source("apps/dashboard/src/app/trials/[trialId]/page.tsx")
    arms = source("apps/dashboard/src/app/arms/page.tsx")

    for term in (
        "Confidence",
        "Execution validity",
        "Activity class",
        "Failure subtype",
        "Policy disposition",
    ):
        assert f'TermInfo term="{term}"' in comprehensive

    for term in (
        "Attempt",
        "Recorded cost",
        "Adjusted known cost",
        "Known accounting gap",
        "Accounting gap",
        "Unresolved",
        "Confidence",
    ):
        assert f'TermInfo term="{term}"' in cost

    for term in (
        "Attempt",
        "Execution validity",
        "Activity class",
        "Failure subtype",
        "Policy disposition",
        "Artifact completeness",
        "R2 integrity",
        "Telemetry consistency",
    ):
        assert f'TermInfo term="{term}"' in trial

    assert 'TermInfo term="Recorded cost"' in arms


def test_dr201_cost_terminology_reuses_shared_definitions() -> None:
    cost = source("apps/dashboard/src/app/cost-coverage/page.tsx")

    for term in (
        "Recorded cost",
        "Adjusted known cost",
        "Accounting gap",
        "Exception with success signal",
    ):
        assert f'getGlossaryEntry("{term}").definition' in cost


def test_dr201_preserves_routing_and_infrastructure_attempt_boundaries() -> None:
    glossary = source("apps/dashboard/src/lib/glossary.ts")
    live = source("apps/dashboard/src/app/runs/live/page.tsx")

    # Routing is provenance context, not causal attribution.
    routing_entry = glossary.split('term: "Routing path"', 1)[1].split(
        "  },", 1
    )[0]
    assert "does not attribute a failure" in routing_entry

    # github_run_attempt is workflow retry identity, not task-local benchmark attempt.
    assert 'github_run_attempt' in live
    assert 'TermInfo term="Attempt"' not in live
