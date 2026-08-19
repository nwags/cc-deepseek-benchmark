from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dr203_shared_helper_is_presentation_only() -> None:
    labels = source("apps/dashboard/src/lib/presentation-labels.ts")

    assert "MODEL_LABELS" in labels
    assert "ARM_MODEL_LABELS" in labels
    assert "PROVIDER_PRESENTATIONS" in labels
    assert "ROUTING_LABELS" in labels

    # Checked-in config display_name is not a presentation authority here.
    assert "display_name" not in labels

    # Unknown values retain their canonical source value.
    assert "MODEL_LABELS[source] ?? source" in labels
    assert "ARM_MODEL_LABELS[source] ?? source" in labels
    assert "ROUTING_LABELS[source] ?? source" in labels
    assert "familyKey: source, label: source" in labels


def test_dr203_reviewed_surfaces_use_shared_friendly_labels() -> None:
    overview = source("apps/dashboard/src/app/page.tsx")
    cost = source("apps/dashboard/src/app/cost-coverage/page.tsx")
    cross_phase = source("apps/dashboard/src/app/cross-phase/page.tsx")

    for helper in (
        "friendlyModelLabel",
        "friendlyProviderLabel",
        "friendlyRoutingLabel",
    ):
        assert helper in overview
        assert helper in cross_phase

    for helper in (
        "friendlyArmLabel",
        "friendlyProviderLabel",
        "friendlyRoutingLabel",
    ):
        assert helper in cost

    assert 'TermInfo term="Routing path"' in cross_phase


def test_dr203_reviewed_surfaces_keep_canonical_identity_and_links() -> None:
    overview = source("apps/dashboard/src/app/page.tsx")
    cost = source("apps/dashboard/src/app/cost-coverage/page.tsx")
    cross_phase = source("apps/dashboard/src/app/cross-phase/page.tsx")

    # Friendly labels are presentation only; evidence identity remains canonical.
    assert "{row.armId}" in overview
    assert "{row.selectedRunLabel}" in overview
    assert "href={row.armEvidenceHref}" in overview
    assert "href={row.selectedRunHref}" in overview

    assert "{arm.armId}" in cost
    assert "buildReviewedAggregateArmEvidenceHref(arm.armId" in cost
    assert "buildExactRunHref(chartArm.selectedRunLabel" in cost

    assert "{row.arm_id}" in cross_phase
    assert "{row.backend_model}" in cross_phase
    assert "{row.routing_path}" in cross_phase
    assert "chartArm.armHref" in cross_phase
    assert "encodeURIComponent(row.arm_id)" in cross_phase


def test_dr203_phase1_phase2_cross_phase_rows_are_not_rewritten() -> None:
    cross_phase = source("apps/dashboard/src/app/cross-phase/page.tsx")

    assert 'const isPhase3 = row.phase === "phase3";' in cross_phase
    assert (
        'const providerLabel = isPhase3 '
        '? friendlyProviderLabel(row.provider) : row.provider;'
    ) in cross_phase
    assert (
        'const modelLabel = isPhase3 '
        '? friendlyModelLabel(row.backend_model) : row.backend_model;'
    ) in cross_phase
    assert (
        'const routingLabel = isPhase3 '
        '? friendlyRoutingLabel(row.routing_path) : row.routing_path;'
    ) in cross_phase


def test_dr203_operational_surfaces_use_shared_friendly_labels() -> None:
    runs = source("apps/dashboard/src/app/runs/page.tsx")
    arms = source("apps/dashboard/src/app/arms/page.tsx")
    quality = source("apps/dashboard/src/app/trial-quality/page.tsx")
    live = source("apps/dashboard/src/app/runs/live/page.tsx")

    for page in (runs, arms):
        assert "friendlyArmLabel" in page
        assert "friendlyProviderLabel" in page

    assert "friendlyArmLabel(row.arm_id)" in quality

    assert "friendlyArmLabel(run?.arm_id, run?.backend_model)" in live
    assert "friendlyProviderLabel" in live


def test_dr203_operational_surfaces_keep_canonical_identity_and_navigation() -> None:
    runs = source("apps/dashboard/src/app/runs/page.tsx")
    arms = source("apps/dashboard/src/app/arms/page.tsx")
    quality = source("apps/dashboard/src/app/trial-quality/page.tsx")
    live = source("apps/dashboard/src/app/runs/live/page.tsx")

    # Runs keeps exact run identity for navigation and visible evidence.
    assert 'buildExactRunHref(row.run_label, "all-imported")' in runs
    assert "{row.arm_id}" in runs
    assert "{row.run_label}" in runs
    assert "encodeURIComponent(row.run_label)" in runs

    # Arms keeps the canonical arm ID as the filter/artifact identity.
    assert "{row.arm_id}" in arms
    assert "encodeURIComponent(row.arm_id)" in arms
    assert "buildArtifactHref({ arm_id: row.arm_id })" in arms

    # Trial Quality changes only the presentation surrounding the same run/arm.
    assert "{row.arm_id}" in quality
    assert 'buildExactRunHref(row.run_label, "all-imported")' in quality
    assert "{row.run_label}" in quality

    # Live execution identity stays live_run_id + canonical arm_id.
    assert "encodeURIComponent(run.live_run_id)" in live
    assert "{run.arm_id}" in live
    assert "github_run_attempt" in live


def test_dr203_does_not_relabel_router_model_as_routing_path() -> None:
    runs = source("apps/dashboard/src/app/runs/page.tsx")
    arms = source("apps/dashboard/src/app/arms/page.tsx")
    live = source("apps/dashboard/src/app/runs/live/page.tsx")
    cross_phase = source("apps/dashboard/src/app/cross-phase/page.tsx")

    # Cross-phase has an actual routing_path source and may present it.
    assert "friendlyRoutingLabel(row.routing_path)" in cross_phase

    # Operational arm metadata calls this router_model; it is not silently
    # converted into a routing-path claim.
    assert "friendlyRoutingLabel(row.router_model)" not in runs
    assert "friendlyRoutingLabel(row.router_model)" not in arms
    assert "friendlyRoutingLabel(run?.router_model)" not in live
    assert "friendlyModelLabel(run?.router_model)" not in live
    assert "run?.backend_model ?? run?.router_model" not in live
