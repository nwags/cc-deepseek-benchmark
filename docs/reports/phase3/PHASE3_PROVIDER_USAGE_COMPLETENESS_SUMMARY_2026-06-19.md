# Phase 3 Provider Reconciliation Completeness Summary

Provider/API-key families covered: 8

## Reconciliation status counts

- accepted-internal-no-provider-export: 1
- billing-level-reconciled: 1
- payg-and-subscription-separated: 1
- provider-dashboard-total-only: 1
- provider-dashboard-total-reconciled: 1
- provider-reconciled: 3

## Full-sweep planning status counts

- accepted-for-planning: 6
- accepted-with-caveat: 1
- accepted-with-granularity-caveat: 1

## Open gaps

- Anthropic / ANTHROPIC_API_KEY: Provider usage export unavailable.
- Gemini / GEMINI_API_KEY: Detailed model/token export unavailable because provider detailed logging was not enabled.
- xAI / Grok / XAI_API_KEY: Granular model/request export unavailable; dashboard total is accepted.
- Moonshot / Kimi / MOONSHOT_API_KEY: Granular billed-cost export unavailable; request logs plus dashboard total are accepted.

## Families

- **Anthropic** (`ANTHROPIC_API_KEY`): accepted-internal-no-provider-export; accepted-for-planning. Evidence: internal-benchmark-records.
- **DeepSeek** (`DEEPSEEK_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-export-plus-artifacts.
- **OpenAI** (`OPENAI_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-export-plus-artifacts.
- **Gemini** (`GEMINI_API_KEY`): billing-level-reconciled; accepted-with-caveat. Evidence: billing-level-only.
- **xAI / Grok** (`XAI_API_KEY`): provider-dashboard-total-only; accepted-with-granularity-caveat. Evidence: provider-dashboard-total-plus-artifacts.
- **Moonshot / Kimi** (`MOONSHOT_API_KEY`): provider-dashboard-total-reconciled; accepted-for-planning. Evidence: request-log-plus-provider-dashboard-total.
- **Z.AI / GLM** (`ZAI_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-billing-table.
- **Alibaba / Qwen** (`DASHSCOPE_API_KEY`): payg-and-subscription-separated; accepted-for-planning. Evidence: provider-bill-detail.
