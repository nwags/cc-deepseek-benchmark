from __future__ import annotations

import pytest

from scripts.lib.phase3_freeze import (
    CLOSED_PHASE3_SUITES,
    ClosedPhase3SuiteError,
    assert_phase3_publication_allowed,
)


@pytest.mark.parametrize("suite_id", sorted(CLOSED_PHASE3_SUITES))
def test_completed_phase3_suites_are_closed_by_default(suite_id: str) -> None:
    with pytest.raises(ClosedPhase3SuiteError):
        assert_phase3_publication_allowed(
            {"run": {"suite_id": suite_id}},
            dry_run=False,
            authorize_repair=False,
        )


def test_dry_run_does_not_require_phase3_repair_authorization() -> None:
    assert_phase3_publication_allowed(
        {"run": {"suite_id": "phase3-full-20"}},
        dry_run=True,
        authorize_repair=False,
    )


def test_explicit_repair_authorization_opens_closed_suite() -> None:
    assert_phase3_publication_allowed(
        {"run": {"suite_id": "phase3-full-20"}},
        dry_run=False,
        authorize_repair=True,
    )
