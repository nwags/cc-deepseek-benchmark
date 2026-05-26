from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenRate:
    input_cache_miss_usd_per_million: float
    output_usd_per_million: float
    input_cache_hit_usd_per_million: float | None = None


RATES: dict[str, TokenRate] = {
    "claude-sonnet-4-6": TokenRate(3.00, 15.00, 0.30),
    "claude-haiku-4-5-20251001": TokenRate(1.00, 5.00, 0.10),
    "claude-opus-4-7": TokenRate(15.00, 75.00, 1.50),

    # Validated DeepSeek cache-aware rates from Phase 1 / Phase 2 aggregation.
    "deepseek-v4-pro": TokenRate(0.435, 0.87, 0.003625),
    "deepseek-v4-pro[1m]": TokenRate(0.435, 0.87, 0.003625),
    "deepseek-v4-flash": TokenRate(0.14, 0.28, 0.0028),
}


def estimate_cost_usd(
    model: str,
    n_input_tokens: float = 0,
    n_output_tokens: float = 0,
    n_cache_tokens: float = 0,
) -> float:
    """Estimate cache-aware cost.

    Semantics match the Phase 1 / Phase 2 aggregate scripts:
    n_input_tokens is total input tokens, including cached input.
    n_cache_tokens is the cached-input subset.
    uncached input = max(n_input_tokens - n_cache_tokens, 0).
    """
    rate = RATES.get(model)
    if rate is None:
        return 0.0

    total_input = float(n_input_tokens or 0)
    cached_input = float(n_cache_tokens or 0)
    output = float(n_output_tokens or 0)
    uncached_input = max(total_input - cached_input, 0)

    cache_rate = rate.input_cache_hit_usd_per_million
    if cache_rate is None:
        cache_rate = rate.input_cache_miss_usd_per_million

    return (
        uncached_input / 1_000_000 * rate.input_cache_miss_usd_per_million
        + cached_input / 1_000_000 * cache_rate
        + output / 1_000_000 * rate.output_usd_per_million
    )