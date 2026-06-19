# Phase 3 Provider Reconciliation Completeness Summary

Provider/API-key families covered: 8

## Reconciliation status counts

- accepted-internal-no-provider-export: 1
- billing-level-reconciled: 1
- payg-and-subscription-separated: 1
- provider-export-pending: 1
- provider-reconciled: 3
- request-log-estimated: 1

## Full-sweep planning status counts

- accepted-for-planning: 5
- accepted-with-caveat: 1
- accepted-with-cost-caveat: 2

## Open gaps

- Anthropic / ANTHROPIC_API_KEY: Provider usage export unavailable
- Gemini / GEMINI_API_KEY: Detailed model/token export unavailable because provider detailed logging was not enabled
- xAI / Grok / XAI_API_KEY: Need xAI provider usage/billing export or screenshot
- Moonshot / Kimi / MOONSHOT_API_KEY: Need billed-cost export or billing screenshot

## Families

- **Anthropic** (`ANTHROPIC_API_KEY`): accepted-internal-no-provider-export; accepted-for-planning. Evidence: internal-benchmark-records.
- **DeepSeek** (`DEEPSEEK_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-export-plus-artifacts.
- **OpenAI** (`OPENAI_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-export-plus-artifacts.
- **Gemini** (`GEMINI_API_KEY`): billing-level-reconciled; accepted-with-caveat. Evidence: billing-level-only.
- **xAI / Grok** (`XAI_API_KEY`): provider-export-pending; accepted-with-cost-caveat. Evidence: artifact-side-only.
- **Moonshot / Kimi** (`MOONSHOT_API_KEY`): request-log-estimated; accepted-with-cost-caveat. Evidence: request-log-plus-artifacts.
- **Z.AI / GLM** (`ZAI_API_KEY`): provider-reconciled; accepted-for-planning. Evidence: provider-billing-table.
- **Alibaba / Qwen** (`DASHSCOPE_API_KEY`): payg-and-subscription-separated; accepted-for-planning. Evidence: provider-bill-detail.
