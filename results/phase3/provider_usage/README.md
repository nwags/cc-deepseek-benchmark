# Phase 3 Provider Usage Artifacts

This directory stores redacted, normalized provider-usage reconciliation artifacts for Phase 3.

## Policy

Raw provider billing exports, screenshots, request logs, ZIP files, account identifiers, invoice IDs, payment IDs, and API-key-adjacent records should not be committed.

Commit only normalized summaries that are safe for the benchmark report.

## Layout

    results/phase3/provider_usage/
      README.md
      normalized/
        provider_usage_resolution_2026-06-19.csv
        full_sweep_api_key_funding_prelim_2026-06-19.csv

## Accounting columns

- `benchmark_marginal_cost_usd`: provider/model inference cost that scales with benchmark token usage.
- `provider_account_spend_usd`: actual provider account spend in the export period.
- `subscription_or_overhead_usd`: subscription, prepaid plan, account seat, or other non-token overhead.
- `free_or_credit_tokens`: usage covered by free quota or credits.
- `billable_tokens`: token usage billed as PAYG or equivalent model inference.

## Current interpretation

- Qwen/Alibaba has both PAYG model inference and a separate Token Plan Team Edition subscription.
- Z.AI/GLM is resolved from the uploaded `glm-5.1` billing table.
- Moonshot/Kimi is estimated from a request log because the export contains tokens but not billed amount.
- Grok/xAI remains pending provider export.
