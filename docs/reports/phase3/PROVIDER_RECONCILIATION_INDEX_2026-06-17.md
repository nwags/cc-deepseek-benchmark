# Phase 3 Provider Usage Reconciliation Index

This index summarizes the current provider-billing / usage-reconciliation status for Phase 3 router benchmark work.

## Current status

| Provider family | Status | Evidence | Notes |
|---|---|---|---|
| OpenAI | Resolved at provider family/model level | `docs/reports/phase3/OPENAI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Provider model-level token/cost export reconciled against Claude Code session JSONL. GPT-5.4 and GPT-5.5 smoke usage confirmed; provider cost is the funding source of truth because cached-input billing differs from benchmark estimates. |
| DeepSeek | Resolved for current retained June smoke runs; older May rows documented as partial/outside retained artifacts | `docs/reports/phase3/DEEPSEEK_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Provider archive rows parse cleanly. June 15 Flash and June 16 Pro smoke usage reconcile exactly. Older provider-family rows are retained for spend context. |
| Gemini | Billing-level only | `docs/reports/phase3/GEMINI_FAMILY_USAGE_RECONCILIATION_2026-06-17.md` | Google Cloud Billing shows Gemini API spend, but AI Studio detailed logging was off, so provider model/token attribution is unavailable. Artifact-side usage is documented separately. |
| Anthropic | Access exception / not provider-export reconciled | `docs/reports/phase3/ANTHROPIC_RECONCILIATION_ACCESS_EXCEPTION.md` | Anthropic reconciliation is documented as an access/export limitation rather than exact provider token reconciliation. |

## Current funding/source-of-truth principle

Provider billing exports are the source of truth for funding estimates when available. Benchmark aggregate costs remain useful for internal comparisons, but provider-side cache billing, timeout-edge behavior, and service-level billing can diverge from benchmark estimates.

## Dashboard implications

The dashboard should store separate fields for:

- benchmark run directory timestamp;
- run start time;
- run end time;
- assistant-message UTC dates from session JSONL;
- provider billing UTC date;
- provider family;
- routed arm;
- observed backend model;
- benchmark-estimated cost;
- provider-billed cost when available;
- reconciliation status.

This avoids the date-boundary and timeout-edge ambiguities observed during OpenAI, DeepSeek, and Gemini reconciliation.

## Recommended next provider families

Next families should be reconciled in this order, depending on artifact and provider-export availability:

1. Grok
2. Kimi
3. Qwen
4. GLM

For each, reconcile provider family totals first, then split by model only when the provider export exposes reliable model-level rows.
