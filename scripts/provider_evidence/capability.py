from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderEvidenceCapability:
    provider: str
    credential_env: str
    actual_usage_api: bool
    actual_cost_api: bool
    usage_bucket_widths: tuple[str, ...]
    cost_bucket_widths: tuple[str, ...]
    usage_allocation_dimensions: tuple[str, ...]
    cost_allocation_dimensions: tuple[str, ...]
    cost_amount_unit: str | None
    expected_reporting_delay: str | None
    limitations: tuple[str, ...] = ()


ANTHROPIC = ProviderEvidenceCapability(
    provider="anthropic",
    credential_env="ANTHROPIC_ADMIN_API_KEY",
    actual_usage_api=True,
    actual_cost_api=True,
    usage_bucket_widths=(
        "1m",
        "1h",
        "1d",
    ),
    cost_bucket_widths=("1d",),
    usage_allocation_dimensions=(
        "api_key_id",
        "workspace_id",
        "model",
    ),
    cost_allocation_dimensions=(
        "workspace_id",
        "description",
    ),
    cost_amount_unit="cent",
    expected_reporting_delay="typically_about_5_minutes",
    limitations=(
        "admin_api_key_required",
        "standard_cost_api_daily_granularity",
        "standard_cost_api_not_api_key_allocable",
        "priority_tier_cost_not_in_standard_cost_endpoint",
        "usage_run_attribution_requires_distinguishable_"
        "allocation_dimensions",
        "cost_run_attribution_requires_workspace_day_"
        "isolation_or_independent_allocation",
        "overlapping_indistinguishable_runs_must_not_be_"
        "allocated",
    ),
)


CAPABILITIES = {
    ANTHROPIC.provider: ANTHROPIC,
}


def get_capability(
    provider: str,
) -> ProviderEvidenceCapability:
    try:
        return CAPABILITIES[provider]
    except KeyError as exc:
        raise ValueError(
            f"unsupported provider: {provider}"
        ) from exc
