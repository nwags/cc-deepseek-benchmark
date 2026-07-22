from pathlib import Path

import yaml


def test_all_arm_configs_load():
    for path in Path("configs/arms").glob("*.yaml"):
        data = yaml.safe_load(path.read_text()) or {}
        assert "arm_id" in data, path
        assert "agent" in data, path
        assert "model" in data, path
        assert "job_dir_name" in data, path


def test_phase3_planned_arms_have_configs():
    phase = yaml.safe_load(Path("configs/phases/phase3-router.yaml").read_text())
    planned = phase.get("planned_arms", [])

    for arm_id in planned:
        path = Path("configs/arms") / f"{arm_id}.yaml"
        assert path.exists(), f"Missing config for planned arm: {arm_id}"
