from pathlib import Path

import pandas as pd


def test_phase1_frozen_cost_totals():
    path = Path("results/phase1/combined.csv")
    assert path.exists()

    df = pd.read_csv(path)
    totals = df.groupby("arm_dir")["effective_cost_usd"].sum()

    expected = {
        "arm-a-anthropic": 37.2955,
        "arm-b-deepseek-pro": 2.0104,
        "arm-c-deepseek-flash": 1.1030,
    }

    for arm, want in expected.items():
        got = float(totals[arm])
        assert abs(got - want) < 0.01, (arm, got, want)


def test_phase2_frozen_cost_totals():
    path = Path("results/phase2/combined.csv")
    assert path.exists()

    df = pd.read_csv(path)
    totals = df.groupby("arm_dir")["effective_cost_usd"].sum()

    expected = {
        "arm-anthropic-haiku": 14.3106,
        "arm-anthropic-sonnet": 28.3629,
        "arm-anthropic-opus": 50.9282,
        "arm-deepseek-pro": 1.7127,
        "arm-deepseek-flash": 0.7161,
    }

    for arm, want in expected.items():
        got = float(totals[arm])
        assert abs(got - want) < 0.01, (arm, got, want)
