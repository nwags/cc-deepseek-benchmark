# Phase 3 Usage Resolution — 2026-06-19

## Purpose

This note updates Phase 3 provider usage reconciliation after reviewing the latest provider exports for Moonshot/Kimi, Z.AI/GLM, and Alibaba/Qwen.

The goal is to distinguish:

- benchmark marginal model-inference cost;
- actual provider account spend;
- subscription/prepaid/account overhead;
- free quota or credits;
- provider exports that are billed-cost sources of truth versus request logs requiring pricing-derived estimates.

## Branch context

Phase 3 work belongs on `phase3`.

`cc-agent-model-branch` is the frozen Phase 2 baseline in substance and must not be used for active Phase 3 router/dashboard/provider work.

## Current status summary

| Provider family | API key family | Status | Benchmark marginal cost | Provider account spend | Notes |
|---|---|---:|---:|---:|---|
| OpenAI | `OPENAI_API_KEY` | resolved | see existing report | see existing report | Existing OpenAI family reconciliation remains source of truth. |
| DeepSeek | `DEEPSEEK_API_KEY` | resolved for retained June smoke | see existing report | see existing report | Existing DeepSeek family reconciliation remains source of truth. |
| Gemini | `GEMINI_API_KEY` | billing-level only | see existing report | see existing report | Provider detail remains billing-level rather than exact model-row export. |
| Anthropic | `ANTHROPIC_API_KEY` | external confirmation required | internal records only | external confirmation required | Project lacks direct provider-dashboard access. |
| xAI / Grok | `XAI_API_KEY` | provider export pending | pending | pending | Need xAI usage/billing export or screenshot. |
| Moonshot / Kimi | `MOONSHOT_API_KEY` | request-log estimated | `$1.918399` | pending | Moonshot request log contains token rows but no billed-cost column. |
| Z.AI / GLM | `ZAI_API_KEY` | provider billing resolved | `$3.094387` | `$3.094387` | Uploaded `KimiUsage` file is GLM/Z.AI `glm-5.1`, not Kimi. |
| Alibaba / Qwen | `DASHSCOPE_API_KEY` | PAYG/subscription separated | `$1.310890` | `$31.310890` | `$30.00` Token Plan Team Edition is account overhead, not marginal model inference. |

## Moonshot / Kimi

The Moonshot Openplatform request log is a true Kimi/Moonshot artifact.

Observed totals:

| Metric | Value |
|---|---:|
| Model | `kimi-k2.6` |
| Request rows | `103` |
| Date range | `2026-06-04` to `2026-06-16` |
| Input tokens | `2,608,591` |
| Cached tokens | `1,063,441` |
| Output tokens | `70,089` |
| Estimated marginal cost | `$1.918399` |

Interpretation:

- Use `$1.918399` as the current Kimi benchmark marginal-cost estimate.
- Mark as `request-log-estimated`, not provider-billed-cost resolved.
- A billed usage export or billing screenshot is still needed to convert this to provider-billing-resolved.

## Z.AI / GLM

The uploaded file named `KimiUsage` must be classified as Z.AI/GLM.

Observed totals:

| Charge type | Tokens | Cost |
|---|---:|---:|
| Input | `1,543,476` | `$2.160866` |
| Cache | `1,639,488` | `$0.426267` |
| Output | `115,285` | `$0.507254` |
| **Total** | **`3,298,249`** | **`$3.094387`** |

Interpretation:

- Provider family: Z.AI / GLM.
- Model: `glm-5.1`.
- Status: provider billing resolved.
- Do not merge this file into Kimi/Moonshot accounting.

## Alibaba / Qwen

The Alibaba export has two separate constructs:

| Construct | Amount |
|---|---:|
| PAYG model inference | `$1.310890` |
| Token Plan Team Edition subscription | `$30.000000` |
| Total account spend | `$31.310890` |

Token totals:

| Token bucket | Tokens |
|---|---:|
| Free quota consumed | `1,000,458` |
| PAYG billable tokens | `4,121,616` |
| Original/export total tokens | `5,122,074` |

Interpretation:

- Use `$1.310890` for benchmark marginal-cost comparisons.
- Track `$30.000000` as subscription/account overhead.
- Track `$31.310890` as actual exported account spend.
- Do not treat the subscription as per-token model inference cost.

## Accounting policy

Use two separate cost columns:

| Column | Meaning |
|---|---|
| `benchmark_marginal_cost_usd` | Model inference usage that scales with benchmark trial/token usage. Use this for model/provider cost comparison. |
| `provider_account_spend_usd` | Actual provider account out-of-pocket spend in the export period, including subscriptions or account overhead. |

Subscriptions, token plans, prepaid seats, account verification costs, and other provider account overhead should not be merged into per-token model quality/cost comparisons unless the report explicitly switches to total cash-spend accounting.

## Remaining usage-resolution blockers

| Provider family | Blocker |
|---|---|
| xAI / Grok | Need provider usage/billing export or screenshot. |
| Moonshot / Kimi | Need billed-cost export or billing screenshot to validate pricing-derived estimate. |
| Anthropic | Need sponsor/provider-side confirmation of funding, spend limits, rate limits, and provider-side usage/cost if available. |
| Gemini | Model-level provider export remains limited; current status is billing-level reconciliation. |

## Normalized files

- `results/phase3/provider_usage/normalized/provider_usage_resolution_2026-06-19.csv`
- `results/phase3/provider_usage/normalized/full_sweep_api_key_funding_prelim_2026-06-19.csv`
