from __future__ import annotations

from collections import Counter

from scripts.generate_phase3_cost_coverage import (
    arm_confidence,
    build_empirical_rates,
    classify_cost,
)


def test_routed_deepseek_replaces_harness_cost_with_provider_rate_reconstruction():
    adjusted, reconstructed, empirical, source, confidence, reason = (
        classify_cost(
            arm_id="router-deepseek-pro",
            backend_model="deepseek-v4-pro",
            routed=True,
            recorded_cost=99.0,
            input_tokens=1_000_000,
            cache_tokens=900_000,
            output_tokens=100_000,
            empirical_rates={},
        )
    )

    assert abs(adjusted - 0.1337625) < 1e-12
    # recorded_cost_usd already preserves the harness number, so the legacy
    # missing-cost reconstruction column is not populated for replacement.
    assert reconstructed is None
    assert empirical is None
    assert source == (
        "provider_rate_reconstructed_routed_harness_untrusted"
    )
    assert confidence == "medium"
    assert "preserved_but_not_selected" in reason


def test_routed_deepseek_missing_harness_cost_can_fill_reconstruction_column():
    adjusted, reconstructed, empirical, source, confidence, _ = (
        classify_cost(
            arm_id="router-deepseek-flash",
            backend_model="deepseek-v4-flash",
            routed=True,
            recorded_cost=None,
            input_tokens=1_000_000,
            cache_tokens=900_000,
            output_tokens=100_000,
            empirical_rates={},
        )
    )

    expected = 0.014 + 0.00252 + 0.028
    assert abs(adjusted - expected) < 1e-12
    assert abs(reconstructed - expected) < 1e-12
    assert empirical is None
    assert source == (
        "provider_rate_reconstructed_routed_harness_untrusted"
    )
    assert confidence == "medium"


def test_routed_unknown_pricing_does_not_select_harness_cost():
    adjusted, reconstructed, empirical, source, confidence, reason = (
        classify_cost(
            arm_id="router-gemini-3.1-pro",
            backend_model="gemini-3.1-pro-preview",
            routed=True,
            recorded_cost=12.34,
            input_tokens=100_000,
            cache_tokens=50_000,
            output_tokens=10_000,
            empirical_rates={
                "router-gemini-3.1-pro": 123.0,
            },
        )
    )

    assert adjusted is None
    assert reconstructed is None
    assert empirical is None
    assert source == (
        "unresolved_routed_harness_cost_not_authoritative_pricing"
    )
    assert confidence == "unknown"
    assert "preserved_but_not_selected" in reason


def test_routed_missing_tokens_does_not_select_harness_cost():
    adjusted, reconstructed, empirical, source, confidence, _ = (
        classify_cost(
            arm_id="router-deepseek-pro",
            backend_model="deepseek-v4-pro",
            routed=True,
            recorded_cost=1.23,
            input_tokens=0,
            cache_tokens=0,
            output_tokens=0,
            empirical_rates={},
        )
    )

    assert adjusted is None
    assert reconstructed is None
    assert empirical is None
    assert source == (
        "unresolved_routed_harness_cost_not_authoritative_no_token_metadata"
    )
    assert confidence == "unknown"


def test_router_rows_cannot_seed_empirical_rate_fallback():
    rows = [
        {
            "arm_id": "router-example",
            "cost_usd": 10,
            "input_tokens": 900,
            "output_tokens": 100,
        }
        for _ in range(10)
    ]

    rates = build_empirical_rates(
        rows,
        excluded_arm_ids={"router-example"},
    )

    assert rates == {}


def test_nonrouter_recorded_cost_retains_historical_behavior():
    adjusted, reconstructed, empirical, source, confidence, reason = (
        classify_cost(
            arm_id="anthropic-sonnet",
            backend_model="claude-sonnet-4-6",
            routed=False,
            recorded_cost=2.5,
            input_tokens=100,
            cache_tokens=0,
            output_tokens=10,
            empirical_rates={},
        )
    )

    assert adjusted == 2.5
    assert reconstructed is None
    assert empirical is None
    assert source == "recorded_artifact"
    assert confidence == "high"
    assert reason == ""


def test_routed_provider_reconstruction_arm_confidence_is_medium():
    counts = Counter(
        {
            "provider_rate_reconstructed_routed_harness_untrusted": 60,
        }
    )
    assert arm_confidence(counts) == "medium"


def test_routed_unresolved_arm_confidence_is_low():
    counts = Counter(
        {
            "unresolved_routed_harness_cost_not_authoritative_pricing": 60,
        }
    )
    assert arm_confidence(counts) == "low"


def test_mixed_routed_reconstruction_and_unresolved_is_mixed():
    counts = Counter(
        {
            "provider_rate_reconstructed_routed_harness_untrusted": 59,
            "unresolved_routed_harness_cost_not_authoritative_no_token_metadata": 1,
        }
    )
    assert arm_confidence(counts) == "mixed"
