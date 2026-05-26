from __future__ import annotations

from pathlib import Path


def phase_results_dir(phase: str) -> Path:
    return Path("results") / phase


def phase_figures_dir(phase: str) -> Path:
    return Path("figures") / phase


def phase_reports_dir(phase: str) -> Path:
    return Path("docs/reports") / phase


def ensure_phase_dirs(phase: str) -> None:
    for path in [
        phase_results_dir(phase) / "raw",
        phase_results_dir(phase) / "smoke",
        phase_results_dir(phase) / "canary",
        phase_results_dir(phase) / "supplemental",
        phase_figures_dir(phase),
        phase_reports_dir(phase),
    ]:
        path.mkdir(parents=True, exist_ok=True)
