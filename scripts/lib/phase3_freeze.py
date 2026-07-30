from __future__ import annotations

from typing import Any, Mapping


CLOSED_PHASE3_SUITES = frozenset(
    {
        "phase3-canary-1",
        "phase3-smoke-5",
        "phase3-full-20",
    }
)


class ClosedPhase3SuiteError(RuntimeError):
    pass


def assert_phase3_publication_allowed(
    manifest: Mapping[str, Any],
    *,
    dry_run: bool,
    authorize_repair: bool,
) -> None:
    if dry_run or authorize_repair:
        return
    run = manifest.get("run") or {}
    suite_id = str(run.get("suite_id") or "")
    if suite_id in CLOSED_PHASE3_SUITES:
        raise ClosedPhase3SuiteError(
            f"completed Phase 3 suite is closed to publication: {suite_id}"
        )
