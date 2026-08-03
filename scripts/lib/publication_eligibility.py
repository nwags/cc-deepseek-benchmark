from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from scripts.lib.path_safety import PathBoundaryError, resolve_under


@dataclass(frozen=True)
class PublicationEligibility:
    eligible: bool
    reasons: tuple[str, ...]
    expected_trial_count: int | None
    declared_trial_count: int | None
    declared_completed_count: int | None
    declared_error_count: int | None
    discovered_trial_count: int
    discovered_error_count: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _ordered(started: datetime | None, finished: datetime | None) -> bool:
    if started is None or finished is None:
        return False
    try:
        return finished >= started
    except TypeError:
        return False


def _read_object(path: Path, *, workspace: Path, parent: Path) -> dict[str, Any] | None:
    resolved = resolve_under(
        path,
        workspace=workspace,
        parent=parent,
        require_file=True,
        label="publication result",
    )
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def evaluate_canonical_eligibility(
    run_dir: Path,
    *,
    workspace: Path,
    expected_trial_count: int | None,
    benchmark_status: str | None = None,
) -> PublicationEligibility:
    reasons: list[str] = []
    run_dir = resolve_under(
        run_dir,
        workspace=workspace,
        require_directory=True,
        label="canonical run directory",
    )
    if benchmark_status in {"interrupted", "starting", "running", "partial"}:
        reasons.append(f"benchmark lifecycle is {benchmark_status}")

    root = _read_object(run_dir / "result.json", workspace=workspace, parent=run_dir)
    declared_total: int | None = None
    declared_completed: int | None = None
    declared_errors: int | None = None
    if root is None:
        reasons.append("root result.json is not a parseable object")
        stats: Mapping[str, Any] = {}
    else:
        started = _timestamp(root.get("started_at"))
        finished = _timestamp(root.get("finished_at"))
        if started is None or finished is None:
            reasons.append("root result is missing parseable final timestamps")
        elif not _ordered(started, finished):
            reasons.append("root result final timestamp precedes its start")
        declared_total = _integer(root.get("n_total_trials"))
        if declared_total is None:
            reasons.append("root total trial count is missing or invalid")
        elif declared_total == 0:
            reasons.append("root total trial count must be positive")
        stats_value = root.get("stats")
        stats = stats_value if isinstance(stats_value, Mapping) else {}
        if not stats:
            reasons.append("root result statistics are missing")
        declared_completed = _integer(stats.get("n_completed_trials"))
        declared_errors = _integer(stats.get("n_errored_trials"))
        if declared_completed is None or declared_errors is None:
            reasons.append("root completed/error statistics are missing or invalid")
        for name in ("n_running_trials", "n_pending_trials", "n_cancelled_trials"):
            value = _integer(stats.get(name))
            if value is None:
                reasons.append(f"root {name} statistic is missing or invalid")
            elif value != 0:
                reasons.append(f"root {name} must be zero for canonical publication")

    discovered = 0
    discovered_errors = 0
    for child in sorted(run_dir.iterdir()):
        if "__" not in child.name:
            continue
        if child.is_symlink():
            raise PathBoundaryError("trial directory must not be a symbolic link")
        if not child.is_dir():
            continue
        trial_dir = resolve_under(
            child,
            workspace=workspace,
            parent=run_dir,
            require_directory=True,
            label="trial directory",
        )
        try:
            trial = _read_object(
                trial_dir / "result.json",
                workspace=workspace,
                parent=trial_dir,
            )
        except PathBoundaryError:
            raise
        if trial is None:
            reasons.append(f"trial {child.name} has no parseable final result")
            continue
        started = _timestamp(trial.get("started_at"))
        finished = _timestamp(trial.get("finished_at"))
        final_evidence = isinstance(trial.get("verifier_result"), Mapping) or bool(
            trial.get("exception_info")
        )
        if not _ordered(started, finished) or not final_evidence:
            reasons.append(f"trial {child.name} is incomplete")
            continue
        discovered += 1
        if trial.get("exception_info"):
            discovered_errors += 1

    if expected_trial_count is not None and discovered != expected_trial_count:
        reasons.append(
            "finalized trial count does not match the live expected trial count "
            f"({discovered} != {expected_trial_count})"
        )
    if declared_total is not None and discovered != declared_total:
        reasons.append(
            f"finalized trial count does not match root total ({discovered} != {declared_total})"
        )
    if declared_total is not None and declared_completed is not None:
        if declared_completed != declared_total:
            reasons.append(
                "root completed count does not equal root total "
                f"({declared_completed} != {declared_total})"
            )
    if declared_completed is not None and declared_errors is not None:
        if declared_errors > declared_completed:
            reasons.append("root error count exceeds root completed count")
    if declared_errors is not None and discovered_errors != declared_errors:
        reasons.append(
            "trial exception count does not match root error count "
            f"({discovered_errors} != {declared_errors})"
        )

    unique_reasons = tuple(dict.fromkeys(reasons))
    return PublicationEligibility(
        eligible=not unique_reasons,
        reasons=unique_reasons,
        expected_trial_count=expected_trial_count,
        declared_trial_count=declared_total,
        declared_completed_count=declared_completed,
        declared_error_count=declared_errors,
        discovered_trial_count=discovered,
        discovered_error_count=discovered_errors,
    )
