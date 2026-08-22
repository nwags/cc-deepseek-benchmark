from __future__ import annotations

import json
from pathlib import Path

from scripts.lib import runtime_versions


def test_control_plane_capture_uses_exact_isolated_proxy_python(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proxy_python = (
        tmp_path
        / ".tools"
        / "litellm-proxy"
        / "bin"
        / "python"
    )
    proxy_python.parent.mkdir(parents=True)
    proxy_python.write_text(
        "#!/bin/sh\nprintf '9.9.9\\n'\n",
        encoding="utf-8",
    )
    proxy_python.chmod(0o755)

    monkeypatch.setattr(
        runtime_versions,
        "_local_distribution_version",
        lambda distribution: {
            "status": "available",
            "version": "0.6.6",
            "source": "python_distribution",
            "reason": None,
        },
    )
    monkeypatch.setattr(
        runtime_versions,
        "_command_version",
        lambda command: {
            "status": "available",
            "version": "2.1.999",
            "source": "runner_cli",
            "reason": None,
        },
    )

    captured = (
        runtime_versions.capture_control_plane_runtime_versions(
            tmp_path
        )
    )

    assert (
        captured["schema_version"]
        == "phase3-control-plane-runtime-v1"
    )
    assert captured["harbor"]["version"] == "0.6.6"
    assert captured["litellm_proxy"]["version"] == "9.9.9"
    assert (
        captured["litellm_proxy"]["source"]
        == "isolated_litellm_proxy_python_distribution"
    )
    assert captured["claude_code_runner"]["version"] == "2.1.999"


def test_observed_claude_code_versions_come_from_agent_init_records(
    tmp_path: Path,
) -> None:
    versions = ("2.1.158", "2.1.159", "2.1.159")

    for index, version in enumerate(versions, start=1):
        path = (
            tmp_path
            / f"task__{index}"
            / "agent"
            / "claude-code.txt"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "claude_code_version": version,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    observed = runtime_versions.observed_claude_code_versions(
        tmp_path
    )

    assert observed["status"] == "available"
    assert observed["transcript_count"] == 3
    assert observed["init_record_count"] == 3
    assert observed["versions"] == [
        {
            "version": "2.1.158",
            "init_record_count": 1,
        },
        {
            "version": "2.1.159",
            "init_record_count": 2,
        },
    ]


def test_runtime_provenance_preserves_missing_control_plane_explicitly(
    tmp_path: Path,
) -> None:
    provenance = runtime_versions.build_runtime_provenance(
        None,
        run_dir=tmp_path,
    )

    assert (
        provenance["schema_version"]
        == "phase3-runtime-provenance-v1"
    )
    assert (
        provenance["control_plane"]["reason"]
        == "discovery_context_missing"
    )
    assert (
        provenance["observed_claude_code"]["status"]
        == "unavailable"
    )


def test_phase3_workflow_and_publisher_persist_runtime_provenance() -> None:
    workflow = Path(
        ".github/workflows/phase3-arm-dispatch-v2.yml"
    ).read_text()
    publisher = Path(
        "scripts/publish_phase3_run.py"
    ).read_text()
    fingerprint = Path(
        "scripts/lib/publication_fingerprint.py"
    ).read_text()

    assert (
        ".tools/litellm-proxy/bin/python - <<'PY_LITELLM_VERSION'"
        in workflow
    )
    assert (
        "capture_control_plane_runtime_versions"
        in workflow
    )
    assert (
        '"runtime_versions": capture_control_plane_runtime_versions('
        in workflow
    )

    assert "build_runtime_provenance" in publisher
    assert (
        'manifest["run"]["runtime_versions"] = '
        "build_runtime_provenance("
        in publisher
    )
    assert 'context.get("runtime_versions")' in publisher

    run_fields = fingerprint[
        fingerprint.index("RUN_FIELDS = ("):
        fingerprint.index("TRIAL_FIELDS = (")
    ]
    assert "runtime_versions" not in run_fields
