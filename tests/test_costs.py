from scripts.lib.costs import (
    estimate_cost_usd,
    harbor_aggregate_reconstruction_safe,
)


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

def test_glm_5_2_cache_aware_cost_regression():
    from scripts.lib.costs import estimate_cost_usd

    got = estimate_cost_usd(
        "glm-5.2",
        n_input_tokens=1_000_000,
        n_cache_tokens=250_000,
        n_output_tokens=100_000,
    )
    expected = 0.75 * 1.40 + 0.25 * 0.26 + 0.10 * 4.40
    assert abs(got - expected) < 1e-12


def test_harbor_aggregate_reconstruction_is_explicitly_deepseek_only():
    assert harbor_aggregate_reconstruction_safe(
        "deepseek-v4-pro"
    )
    assert harbor_aggregate_reconstruction_safe(
        "deepseek-v4-pro[1m]"
    )
    assert harbor_aggregate_reconstruction_safe(
        "deepseek-v4-flash"
    )

    # Anthropic cache-write pricing needs token classes that Harbor's
    # aggregate AgentContext does not preserve separately.
    assert not harbor_aggregate_reconstruction_safe(
        "claude-sonnet-4-6"
    )

    # GLM remains fail-closed until its cache accounting has been
    # explicitly qualified for Harbor's collapsed representation.
    assert not harbor_aggregate_reconstruction_safe(
        "glm-5.1"
    )
    assert not harbor_aggregate_reconstruction_safe(
        "glm-5.2"
    )
