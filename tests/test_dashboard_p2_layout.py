from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dr202_widens_only_the_large_desktop_app_shell_contract() -> None:
    css = source("apps/dashboard/src/app/globals.css")

    assert "width: min(1760px, calc(100vw - 48px));" in css
    assert "width: min(1480px, calc(100vw - 48px));" not in css

    # Preserve the accepted narrower-desktop behavior.
    assert "@media (max-width: 1000px)" in css
    assert "width: min(1320px, calc(100vw - 32px));" in css


def test_dr202_preserves_horizontal_containment_and_adds_visible_affordance() -> None:
    css = source("apps/dashboard/src/app/globals.css")

    assert ".table-wrap {" in css
    assert "overflow-x: auto;" in css
    assert "overscroll-behavior-inline: contain;" in css
    assert "scrollbar-gutter: stable;" in css
    assert "scrollbar-color:" in css

    # Do not hide overflow globally to make layout problems disappear.
    assert "overflow-x: hidden" not in css
    assert "overflow-x: clip" not in css


def test_dr202_defines_opt_in_long_table_sticky_header_contract() -> None:
    css = source("apps/dashboard/src/app/globals.css")

    assert ".table-wrap-long {" in css
    assert "max-height: min(70vh, 48rem);" in css
    assert ".table-wrap-long thead th {" in css
    assert "position: sticky;" in css
    assert "top: 0;" in css
    assert ".table-wrap-long thead .sticky-id-column {" in css

    # Existing accepted left identity behavior remains authoritative.
    assert ".sticky-id-column {" in css
    assert "left: 0;" in css
    assert "overflow-wrap: anywhere;" in css


def test_dr202_defines_reusable_column_width_contracts() -> None:
    css = source("apps/dashboard/src/app/globals.css")

    for class_name in (
        ".table-col-compact",
        ".table-col-context",
        ".table-col-identity",
    ):
        assert class_name in css

    assert "min-width: 5.5rem;" in css
    assert "max-width: 8rem;" in css
    assert "min-width: 10rem;" in css
    assert "max-width: 18rem;" in css
    assert "min-width: 15rem;" in css
    assert "max-width: 24rem;" in css


def test_dr202_section_navigation_is_reusable_and_fragment_only() -> None:
    component = source("apps/dashboard/src/components/SectionNav.tsx")
    css = source("apps/dashboard/src/app/globals.css")

    assert "export type SectionNavItem" in component
    assert "export function SectionNav" in component
    assert 'href: `#${string}`;' in component
    assert 'className="section-nav"' in component
    assert "aria-label={ariaLabel}" in component
    assert "href={item.href}" in component
    assert "On this page" in component

    assert 'from "next/navigation"' not in component
    assert 'from "next/link"' not in component

    assert ".section-nav {" in css
    assert ".section-nav-links {" in css


def test_dr202_long_pages_adopt_local_navigation_and_table_contracts() -> None:
    review = source(
        "apps/dashboard/src/app/comprehensive-review/page.tsx"
    )
    trial = source("apps/dashboard/src/app/trials/[trialId]/page.tsx")

    assert (
        'import { SectionNav } from "../../components/SectionNav";'
        in review
    )
    assert (
        'import { SectionNav } from "../../../components/SectionNav";'
        in trial
    )

    for section_id in (
        "review-coverage",
        "reviewed-trials",
        "review-queue",
        "control-strata",
        "arm-summaries",
        "task-disagreements",
    ):
        assert f'#{section_id}' in review
        assert f'id="{section_id}"' in review

    # Only genuinely long review tables receive internal vertical scrolling.
    assert review.count("table-wrap table-wrap-long") == 4

    # Preserve the DR-106 leftmost Trial identity contract.
    assert 'className="sticky-id-column">Trial</th>' in review

    # Explicit DR-202 width contracts are applied to the remaining dense
    # context/identity/compact columns.
    assert "table-col-compact" in review
    assert "table-col-context" in review
    assert "table-col-identity" in review

    for section_id in (
        "trial-summary",
        "failure-taxonomy",
        "quick-diagnosis",
        "read-next",
        "trial-configuration",
        "trial-artifacts",
        "task-text",
    ):
        assert f'#{section_id}' in trial

    # FailureTaxonomyDetails remains the single owner of this established ID.
    assert "<FailureTaxonomyDetails result={failureTaxonomy} />" in trial
    assert 'id="failure-taxonomy"' not in trial

    for section_id in (
        "trial-summary",
        "quick-diagnosis",
        "read-next",
        "trial-configuration",
        "trial-artifacts",
        "task-text",
    ):
        assert f'id="{section_id}"' in trial


def test_dr202_preserves_reviewed_trial_fragment_contract() -> None:
    review = source(
        "apps/dashboard/src/app/comprehensive-review/page.tsx"
    )
    links = source("apps/dashboard/src/lib/evidence-links.ts")
    filters = source("apps/dashboard/src/lib/reviewed-trial-filters.ts")

    assert review.count('id="reviewed-trials"') == 1
    assert "#reviewed-trials" in links
    assert "#reviewed-trials" in filters


def test_dr202_live_runs_uses_local_navigation_and_bounded_histories() -> None:
    live = source("apps/dashboard/src/app/runs/live/page.tsx")

    assert (
        'import { SectionNav } from "../../../components/SectionNav";'
        in live
    )
    assert 'ariaLabel="Live Runs sections"' in live

    for section_id in (
        "live-executions",
        "selected-execution",
        "live-warnings",
        "tool-activity",
        "observable-output",
        "partial-trials",
        "progressive-artifacts",
        "event-tail",
    ):
        assert f'#{section_id}' in live
        assert f'id="{section_id}"' in live

    # DR-202 explicitly bounds these two long operational histories.
    tool = live.split('id="tool-activity"', 1)[1].split(
        "</section>", 1
    )[0]
    event_tail = live.split('id="event-tail"', 1)[1].split(
        "</section>", 1
    )[0]
    assert 'className="table-wrap table-wrap-long"' in tool
    assert 'className="table-wrap table-wrap-long"' in event_tail

    # Warning evidence remains independently prominent rather than being
    # collapsed into the bounded operational histories.
    warnings = live.split('id="live-warnings"', 1)[1].split(
        "</section>", 1
    )[0]
    assert 'className="table-wrap table-wrap-long"' not in warnings

    # Output history already had its own compact bounded presentation.
    output = live.split('id="observable-output"', 1)[1].split(
        "</section>", 1
    )[0]
    assert (
        'className="content-preview content-preview-compact"'
        in output
    )

    assert live.count('className="table-wrap table-wrap-long"') == 2


def test_dr202_live_artifact_primary_action_is_left_and_sticky() -> None:
    live = source("apps/dashboard/src/app/runs/live/page.tsx")
    artifacts = live.split('id="progressive-artifacts"', 1)[1].split(
        "</section>", 1
    )[0]

    assert (
        '<th className="sticky-id-column">Trial / action</th>'
        in artifacts
    )
    assert '<td className="sticky-id-column">' in artifacts
    assert '<div className="row-action-links">' in artifacts
    assert (
        '<Link href={`/live-artifacts/'
        '${encodeURIComponent(artifact.artifact_id)}`}>Preview</Link>'
        in artifacts
    )

    # The action is no longer a far-right dedicated column.
    assert "<th>Content</th>" not in artifacts
    assert artifacts.count(">Preview</Link>") == 1
