from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any


CONTROL_PLANE_SCHEMA_VERSION = "phase3-control-plane-runtime-v1"
RUNTIME_PROVENANCE_SCHEMA_VERSION = "phase3-runtime-provenance-v1"


def _unavailable(reason: str, *, source: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "version": None,
        "source": source,
        "reason": reason,
    }


def _local_distribution_version(distribution: str) -> dict[str, Any]:
    try:
        value = package_version(distribution)
    except PackageNotFoundError:
        return _unavailable(
            "distribution_not_installed",
            source="python_distribution",
        )

    return {
        "status": "available",
        "version": value,
        "source": "python_distribution",
        "reason": None,
    }


def _python_distribution_version(
    python_path: Path,
    distribution: str,
    *,
    source: str,
) -> dict[str, Any]:
    if not python_path.is_file():
        return _unavailable(
            "python_environment_not_present",
            source=source,
        )

    script = (
        "from importlib.metadata import version; "
        f"print(version({distribution!r}))"
    )

    try:
        result = subprocess.run(
            [str(python_path), "-c", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return _unavailable(
            "version_probe_failed",
            source=source,
        )

    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        return _unavailable(
            "version_probe_failed",
            source=source,
        )

    return {
        "status": "available",
        "version": value,
        "source": source,
        "reason": None,
    }


def _command_version(command: str) -> dict[str, Any]:
    executable = shutil.which(command)
    if executable is None:
        return _unavailable(
            "command_not_found",
            source="runner_cli",
        )

    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return _unavailable(
            "version_probe_failed",
            source="runner_cli",
        )

    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0 or not output:
        return _unavailable(
            "version_probe_failed",
            source="runner_cli",
        )

    token = output.split()[0]
    return {
        "status": "available",
        "version": token,
        "source": "runner_cli",
        "reason": None,
    }


def capture_control_plane_runtime_versions(
    workspace: Path,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    proxy_python = (
        workspace
        / ".tools"
        / "litellm-proxy"
        / "bin"
        / "python"
    )

    return {
        "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
        "harbor": _local_distribution_version("harbor"),
        "litellm_proxy": _python_distribution_version(
            proxy_python,
            "litellm",
            source="isolated_litellm_proxy_python_distribution",
        ),
        "claude_code_runner": _command_version("claude"),
    }


def observed_claude_code_versions(
    run_dir: Path,
) -> dict[str, Any]:
    versions: dict[str, int] = {}
    init_records = 0
    transcript_count = 0

    for path in sorted(run_dir.rglob("agent/claude-code.txt")):
        if not path.is_file():
            continue

        transcript_count += 1

        try:
            with path.open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:
                for line_number, line in enumerate(handle, start=1):
                    if line_number > 100:
                        break

                    stripped = line.strip()
                    if not stripped.startswith("{"):
                        continue

                    try:
                        record = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue

                    if (
                        not isinstance(record, dict)
                        or record.get("type") != "system"
                        or record.get("subtype") != "init"
                    ):
                        continue

                    init_records += 1
                    value = (
                        record.get("claude_code_version")
                        or record.get("claudeCodeVersion")
                    )
                    if isinstance(value, str) and value.strip():
                        normalized = value.strip()
                        versions[normalized] = (
                            versions.get(normalized, 0) + 1
                        )
                    break
        except OSError:
            continue

    if not versions:
        return {
            "status": "unavailable",
            "source": "agent_init_records",
            "versions": [],
            "transcript_count": transcript_count,
            "init_record_count": init_records,
            "reason": "no_versioned_agent_init_record",
        }

    return {
        "status": "available",
        "source": "agent_init_records",
        "versions": [
            {
                "version": version,
                "init_record_count": count,
            }
            for version, count in sorted(versions.items())
        ],
        "transcript_count": transcript_count,
        "init_record_count": init_records,
        "reason": None,
    }


def build_runtime_provenance(
    control_plane: Any,
    *,
    run_dir: Path,
) -> dict[str, Any]:
    if isinstance(control_plane, Mapping):
        control_plane_value: dict[str, Any] = dict(control_plane)
    else:
        control_plane_value = {
            "schema_version": CONTROL_PLANE_SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "discovery_context_missing",
        }

    return {
        "schema_version": RUNTIME_PROVENANCE_SCHEMA_VERSION,
        "control_plane": control_plane_value,
        "observed_claude_code": observed_claude_code_versions(
            run_dir
        ),
    }
