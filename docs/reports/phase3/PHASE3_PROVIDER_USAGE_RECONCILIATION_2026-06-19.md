# Phase 3 Provider Usage Reconciliation — Canonical Status

Date: 2026-06-19  
Branch: `phase3`

## Purpose

This is the canonical Phase 3 provider-usage reconciliation report. It consolidates the earlier family-specific reports, the 2026-06-19 usage-resolution note, and the normalized provider-usage CSV artifacts.

This report distinguishes:

- benchmark marginal model-inference cost;
- provider account spend;
- subscription/prepaid/account overhead;
- free quota or credit usage;
- provider-billed source-of-truth costs;
- pricing-derived estimates;
- billing-level-only reconciliation;
- internal benchmark records accepted when provider export access is unavailable.

## Canonical files

| File | Role |
|---|---|
| `docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md` | Human-readable canonical status. |
| `results/phase3/provider_usage/normalized/provider_reconciliation_ledger_2026-06-19.csv` | Machine-readable provider/API-key reconciliation ledger. |
| `results/phase3/provider_usage/normalized/provider_reconciliation_completeness_audit_2026-06-19.csv` | Machine-readable completeness audit. |
| `results/phase3/provider_usage/normalized/full_sweep_api_key_funding_prelim_2026-06-19.csv` | Preliminary full-sweep funding reserve by shared API-key family. |

## Source-of-truth policy

Provider billing exports are the funding source of truth when available.

When provider export access is unavailable, use the best available substitute and make the limitation explicit:

| Evidence level | Meaning |
|---|---|
| `provider-export-plus-artifacts` | Provider export reconciled against benchmark artifacts. |
| `provider-billing-table` / `provider-bill-detail` | Provider-side billing export or bill detail exists and is parsed. |
| `billing-level-only` | Provider spend is visible, but detailed model/token export is unavailable. |
| `request-log-plus-artifacts` | Request log provides tokens but not billed cost; cost is pricing-derived. |
| `artifact-side-only` | Benchmark artifacts exist, but provider export is still pending. |
| `internal-benchmark-records` | Internal benchmark records are accepted because provider export access is unavailable. |

Subscriptions, prepaid plans, account seats, verification/setup fees, and other provider-account overhead must not be merged into marginal per-token model comparisons unless a report explicitly switches to total cash-spend accounting.

## API-key-family reconciliation ledger

| Provider family | API key family | Status | Evidence level | Planning status | Remaining gap |
|---|---|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | accepted-internal-no-provider-export | internal-benchmark-records | accepted-for-planning | Provider usage export unavailable. |
| DeepSeek | `DEEPSEEK_API_KEY` | provider-reconciled | provider-export-plus-artifacts | accepted-for-planning | None for retained June smoke. |
| OpenAI | `OPENAI_API_KEY` | provider-reconciled | provider-export-plus-artifacts | accepted-for-planning | None for retained smoke. |
| Gemini | `GEMINI_API_KEY` | billing-level-reconciled | billing-level-only | accepted-with-caveat | Detailed model/token export unavailable. |
| xAI / Grok | `XAI_API_KEY` | provider-export-pending | artifact-side-only | accepted-with-cost-caveat | Need xAI provider usage/billing export or screenshot. |
| Moonshot / Kimi | `MOONSHOT_API_KEY` | request-log-estimated | request-log-plus-artifacts | accepted-with-cost-caveat | Need billed-cost export or billing screenshot. |
| Z.AI / GLM | `ZAI_API_KEY` | provider-reconciled | provider-billing-table | accepted-for-planning | None for `glm-5.1` billing table. |
| Alibaba / Qwen | `DASHSCOPE_API_KEY` | payg-and-subscription-separated | provider-bill-detail | accepted-for-planning | None for PAYG/subscription split. |

## Resolved and partially resolved provider families

### OpenAI

Status: provider-reconciled.

Use `docs/reports/phase3/OPENAI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` as component evidence. Provider model-level token/cost export reconciles against Claude Code session JSONL. Provider cost remains the funding source of truth because cached-input billing differs from benchmark estimates.

### DeepSeek

Status: provider-reconciled for retained June smoke.

Use `docs/reports/phase3/DEEPSEEK_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` as component evidence. Provider archive rows parse cleanly. June 15 Flash and June 16 Pro smoke usage reconcile exactly. Older May rows remain spend-context only.

### Gemini

Status: billing-level-reconciled.

Use `docs/reports/phase3/GEMINI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` as component evidence. Google Cloud Billing shows Gemini API spend, but detailed model/token logging was not available. Use billing-level spend plus artifact-side usage and keep this caveat visible.

### Anthropic

Status: accepted-internal-no-provider-export.

Provider usage data is not currently available. Phase 1 and Phase 2 Anthropic cost behavior appeared correct, and Phase 3 Anthropic canary/smoke results can be accepted for planning using internal benchmark records. This is not exact provider-export reconciliation.

### xAI / Grok

Status: provider-export-pending.

Artifact-side evidence exists, but provider usage/billing export or screenshot is still needed. Full-sweep planning can proceed with conservative funding reserve and an explicit cost caveat.

### Moonshot / Kimi

Status: request-log-estimated.

The Moonshot request log is a true Kimi artifact and contains token rows, but no billed-cost column. Current estimated marginal cost is `$1.918399`. A billed usage export or billing screenshot is still needed to convert this to provider-billed-cost resolved.

### Z.AI / GLM

Status: provider-reconciled.

The uploaded file named `KimiUsage` is actually Z.AI/GLM `glm-5.1` billing data. It should not be merged into Kimi/Moonshot. Current provider-billed cost is `$3.094387`.

### Alibaba / Qwen

Status: payg-and-subscription-separated.

Alibaba bill detail separates ordinary PAYG model inference from a Token Plan Team Edition subscription. Use `$1.310890` as benchmark marginal cost and `$31.310890` as actual exported account spend. The `$30.000000` subscription is overhead/account spend, not marginal model inference.

## Completeness audit summary

| Area | Status | Meaning |
|---|---|---|
| API-key family coverage | Pass | All active Phase 3 API-key families are represented. |
| Provider-billed cost coverage | Partial | OpenAI, DeepSeek, GLM, and Qwen have provider-side billing/export evidence. |
| Billing-level coverage | Partial | Gemini is billing-level only. |
| Internal accepted coverage | Partial | Anthropic is accepted using internal records because provider export is unavailable. |
| Estimated coverage | Partial | Kimi/Moonshot uses request-log tokens plus pricing-derived estimate. |
| Pending export coverage | Open | xAI/Grok remains provider-export pending. |
| Overhead separation | Pass | Qwen subscription overhead is not merged into benchmark marginal cost. |
| Full-sweep funding readiness | Pass with caveats | Sufficient for preliminary API-key-family funding; update after smoke-derived estimates and any new provider exports. |

## Dashboard implications

The dashboard should expose the canonical ledger fields:

- provider family;
- API-key family;
- routed arms;
- reconciliation status;
- evidence level;
- benchmark marginal cost;
- provider account spend;
- subscription/account overhead;
- free or credit tokens;
- billable tokens;
- provider token/cost known flags;
- full-sweep planning status;
- primary evidence;
- remaining gap.

The dashboard cost views should distinguish missing cost, zero-token infrastructure failures, pricing-derived estimates, billing-level-only costs, and provider-billed costs.

## Relationship to older files

Older family reports are retained as component evidence. This canonical 2026-06-19 report is the report to cite for overall Phase 3 provider-usage status.

| Older file | Role after consolidation |
|---|---|
| `OPENAI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Component evidence. |
| `DEEPSEEK_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Component evidence. |
| `GEMINI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Component evidence. |
| `PHASE3_USAGE_RESOLUTION_2026-06-19.md` | Component evidence for Kimi, GLM, and Qwen. |
| `PROVIDER_RECONCILIATION_INDEX_2026-06-17.md` | Superseded index; keep for history. |
| `REMAINING_PROVIDER_ARTIFACT_STATUS_2026-06-17.md` | Artifact-side evidence; original pending statuses superseded by this report. |
