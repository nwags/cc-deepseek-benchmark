from scripts.lib.costs import estimate_cost_usd


def test_deepseek_pro_cache_aware_cost_regression():
    got = estimate_cost_usd(
        "deepseek-v4-pro[1m]",
        n_input_tokens=1_000_000,
        n_cache_tokens=900_000,
        n_output_tokens=100_000,
    )
    assert abs(got - 0.1337625) < 1e-12


def test_deepseek_flash_cache_aware_cost_regression():
    got = estimate_cost_usd(
        "deepseek-v4-flash",
        n_input_tokens=1_000_000,
        n_cache_tokens=900_000,
        n_output_tokens=100_000,
    )
    expected = 0.014 + 0.00252 + 0.028
    assert abs(got - expected) < 1e-12
