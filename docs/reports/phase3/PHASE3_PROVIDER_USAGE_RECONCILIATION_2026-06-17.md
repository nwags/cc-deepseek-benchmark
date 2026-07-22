<!-- consolidation-note -->
> Consolidation note: this 2026-06-17 provider usage report is retained for historical context. Use `docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md` for current overall Phase 3 provider-usage status.

# Phase 3 Provider Usage Reconciliation — 2026-06-17

## Purpose

Sponsor funding has been approved and provided. Before full-sweep execution, the remaining work is to apply funding/credits to the relevant API accounts and verify that provider dashboards reconcile with benchmark-recorded usage.

This report tracks, per provider:

- which account/project/workspace/region owns the API key;
- how funding or credits are applied;
- where official provider usage and billing appear;
- whether provider-reported usage matches Phase 3 benchmark usage;
- whether a provider is ready for full-sweep execution.

## Current status summary

| Provider family | API account funding applied? | Dashboard usage located? | Usage reconciled? | Full-sweep readiness | Notes |
|---|---|---|---|---|---|
| Anthropic | external / no direct access | no | partial via internal records | conditional | No direct Anthropic provider-dashboard access. Need sponsor/provider confirmation of credits, spend limits, and rate limits; reconcile using internal benchmark records plus external confirmation. |
| OpenAI | TBD | TBD | TBD | TBD | Check Usage Dashboard, project budget, model usage limits, and prepaid/credit state. |
| DeepSeek | TBD | TBD | TBD | TBD | Confirm balance/top-up state and usage/cost ledger. Distinguish 402 insufficient balance from 429 rate limit. |
| Gemini / Google | TBD | TBD | TBD | TBD | Confirm billing account, project, monthly cap, rate limits, and Gemini-family concurrency limit. |
| xAI / Grok | TBD | TBD | TBD | TBD | Confirm billing/usage dashboard and available balance or spend cap. |
| Moonshot / Kimi | TBD | TBD | TBD | TBD | Confirm usage dashboard and billing balance. |
| Alibaba / Qwen | pending | partial | no | blocked for full sweep | Identity verification/funding/workspace/region/API-key mapping still needs reconciliation. |
| ZAI / GLM | TBD | TBD | TBD | TBD | Confirm usage dashboard and available balance or spend cap. |

## Internal benchmark sources of truth

Use these local sources before comparing with provider dashboards:

- `results/phase3/**/result.json`
- `results/phase3/dashboard/missing_cost_audit.json`
- phase-specific aggregate CSV/JSON files
- LiteLLM logs when provider errors or token accounting are ambiguous
- GitHub Actions run IDs and artifacts
- Supabase dashboard views after ingestion

## Provider checklist template

For each provider, fill in:

- Provider:
- API account / organization:
- Project / workspace / region:
- API key label or non-secret identifier:
- Funding source:
- Funding amount applied:
- Funding date:
- Billing mode:
- Spend cap / monthly cap:
- Rate-limit tier:
- Provider dashboard URL/page name:
- Usage export path or screenshot path:
- Benchmark run IDs reconciled:
- Benchmark-recorded tokens:
- Provider-reported tokens:
- Benchmark-recorded cost:
- Provider-reported cost:
- Difference:
- Explanation for difference:
- Full-sweep status:
- Follow-up required:

## Provider notes

### Anthropic

Status: limited-access reconciliation exception.

Direct Anthropic provider-dashboard access is not available from this project account. Anthropic full-sweep readiness therefore depends on external confirmation from the sponsor/provider-side account owner.

Checks:

- Ask sponsor/provider-side account owner to confirm API credits or billing capacity are available.
- Ask sponsor/provider-side account owner to confirm organization/workspace spend limits.
- Ask sponsor/provider-side account owner to confirm organization/workspace rate limits.
- Reconcile our benchmark-recorded Anthropic token/cost totals against any sponsor-provided usage/cost export or screenshot.
- Use internal benchmark sources as our primary local evidence: Harbor `result.json`, LiteLLM logs, GitHub Actions artifacts, and dashboard/Supabase imported rows.
- Confirm Fable remains unavailable before any Fable planning.

Full-sweep interpretation:

- Anthropic is not blocked by missing local dashboard access if the sponsor confirms funding and limits.
- Anthropic cost reconciliation should be marked `external-confirmation-required` until provider-side usage/cost evidence is supplied.

### OpenAI

Status: TBD.

Checks:

- Confirm project budget.
- Confirm organization/project usage limits.
- Confirm usage dashboard can show the relevant model/project.
- Confirm prepaid credits or billing method are active.

### DeepSeek

Status: TBD.

Checks:

- Confirm balance/top-up.
- Confirm token usage and billed cost.
- Confirm no 402 insufficient-balance risk.
- Confirm whether rate-limit increases are needed.

### Gemini / Google

Status: partial.

Checks:

- Confirm billing account is attached to the project/API key.
- Confirm monthly usage cap.
- Confirm rate limits visible in AI Studio / Google console.
- Keep Gemini-family concurrency at one arm until quota behavior is understood.

### xAI / Grok

Status: TBD.

Checks:

- Confirm billing dashboard and balance.
- Confirm rate limits.
- Reconcile Grok smoke run cost with provider dashboard.

### Moonshot / Kimi

Status: TBD.

Checks:

- Confirm billing dashboard and balance.
- Confirm usage export if available.
- Reconcile Kimi smoke run cost with provider dashboard.

### Alibaba / Qwen

Status: blocked for full sweep until verification and reconciliation complete.

Checks:

- Confirm identity verification is complete.
- Confirm Model Studio service is activated.
- Confirm API key owner account, workspace, and region.
- Confirm whether using general Model Studio pay-as-you-go key or a plan-specific key.
- Confirm funding/credits are attached to the exact account/workspace/region used by `DASHSCOPE_API_KEY`.
- Confirm where token usage appears: Model Monitoring, Bill Details export, or both.
- Reconcile Qwen smoke usage and cost against provider records.

### ZAI / GLM

Status: TBD.

Checks:

- Confirm billing dashboard and balance.
- Confirm usage export if available.
- Reconcile GLM smoke run cost with provider dashboard.

## Sponsor-facing summary draft points

- Sponsor approval and funding are complete.
- Runner concurrency is operational at three slots.
- Dashboard Stage B now validates provider-family limits before any dashboard dispatch button exists.
- Full-sweep execution is gated on operational reconciliation: funding must be applied to provider accounts, dashboards must show expected usage, and provider-specific rate limits must be respected.
- Qwen remains the highest reconciliation risk because Alibaba Cloud / Model Studio separates account, workspace, region, API key, monitoring, and bill export surfaces.
- Gemini requires provider-family throttling because simultaneous Gemini arms produced provider-side 429/rate-limit evidence.
