from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


class ConfigError(RuntimeError):
    """Raised when a phase or arm config is invalid."""


def _require_yaml() -> None:
    if yaml is None:
        raise ConfigError(
            "PyYAML is required to read configs/*.yaml. Install it with "
            "`uv add pyyaml` or add it to pyproject.toml."
        ) from _YAML_IMPORT_ERROR


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a dictionary."""
    _require_yaml()
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config must be a mapping: {p}")
    return data


def phase_config_path(phase: str) -> Path:
    return Path("configs/phases") / f"{phase}.yaml"


def arm_config_path(arm: str) -> Path:
    return Path("configs/arms") / f"{arm}.yaml"


def load_phase(phase: str) -> dict[str, Any]:
    data = load_yaml(phase_config_path(phase))
    data.setdefault("phase_id", phase)
    return data


def load_arm(arm: str) -> dict[str, Any]:
    data = load_yaml(arm_config_path(arm))
    data.setdefault("arm_id", arm)
    return data


def job_dir_name(phase: dict[str, Any], arm: dict[str, Any]) -> str:
    phase_id = str(phase.get("phase_id", ""))
    by_phase = arm.get("job_dir_name_by_phase") or {}
    if isinstance(by_phase, dict) and phase_id in by_phase:
        return str(by_phase[phase_id])
    return str(arm.get("job_dir_name") or arm.get("arm_id"))


def task_file_for_mode(phase: dict[str, Any], mode: str) -> Path:
    if mode == "canary":
        key = "canary_task_file"
    elif mode == "smoke":
        key = "smoke_task_file"
    else:
        key = "task_file"
    return Path(str(phase.get(key) or phase.get("task_file")))


def results_dir_for_mode(phase: dict[str, Any], arm: dict[str, Any], mode: str) -> Path:
    root = Path(str(phase.get("results_root", f"results/{phase.get('phase_id', 'phase')}")))
    subdirs = phase.get("mode_results_subdirs") or {}
    subdir = str(subdirs.get(mode, "raw" if mode == "full" else mode))
    return root / subdir / job_dir_name(phase, arm)


def read_task_list(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Task list not found: {p}")
    tasks = [
        line.strip()
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not tasks:
        raise ConfigError(f"Task list is empty: {p}")
    return tasks
