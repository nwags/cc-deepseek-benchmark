from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_helper(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env["ARM_RUNTIME_SERVICES_DRY_RUN"] = "1"
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "scripts/ensure_arm_runtime_services.sh", *args],
        cwd=REPO_ROOT,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_sanitized_haiku_resolves_to_anthropic_sanitizer() -> None:
    proc = run_helper("router-anthropic-haiku-sanitized")

    assert proc.returncode == 0
    assert "Would ensure runtime service for router-anthropic-haiku-sanitized: anthropic-sanitizer" in proc.stdout


def test_ordinary_arm_resolves_to_no_runtime_services() -> None:
    proc = run_helper("router-anthropic-sonnet")

    assert proc.returncode == 0
    assert "No runtime services declared for arm: router-anthropic-sonnet" in proc.stdout


def test_unknown_runtime_service_fails_clearly(tmp_path: Path) -> None:
    (tmp_path / "bad-arm.yaml").write_text(
        "\n".join(
            [
                "arm_id: bad-arm",
                "agent: claude-code",
                "model: bad-model",
                "job_dir_name: arm-bad-arm",
                "runtime_services:",
                "- mystery-sidecar",
                "",
            ]
        ),
        encoding="utf-8",
    )

    proc = run_helper("bad-arm", env={"ARM_CONFIG_DIR": str(tmp_path)})

    assert proc.returncode == 1
    assert "Unknown runtime service 'mystery-sidecar' declared for arm bad-arm" in proc.stderr
