# Phase 3 Provider Usage Artifacts

This directory stores redacted, normalized provider-usage reconciliation artifacts for Phase 3.

## Policy

Raw provider billing exports, screenshots, request logs, ZIP files, account identifiers, invoice IDs, payment IDs, and API-key-adjacent records should not be committed.

Commit only normalized summaries that are safe for benchmark reporting.

## Canonical files

    docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md
    results/phase3/provider_usage/normalized/provider_reconciliation_ledger_2026-06-19.csv
    results/phase3/provider_usage/normalized/provider_reconciliation_completeness_audit_2026-06-19.csv
    results/phase3/provider_usage/normalized/full_sweep_api_key_funding_prelim_2026-06-19.csv

## Accounting columns

- `benchmark_marginal_cost_usd`: provider/model inference cost that scales with benchmark token usage.
- `provider_account_spend_usd`: actual provider account spend in the export period.
- `subscription_or_overhead_usd`: subscription, prepaid plan, account seat, or other non-token overhead.
- `free_or_credit_tokens`: usage covered by free quota or credits.
- `billable_tokens`: token usage billed as PAYG or equivalent model inference.

## Current interpretation

- OpenAI and DeepSeek are provider-export reconciled.
- Gemini is billing-level reconciled, with detailed model/token export unavailable.
- Anthropic provider export is unavailable; internal records are accepted for canary/smoke planning because Phase 1/2 cost behavior appeared correct.
- Qwen/Alibaba has both PAYG model inference and a separate Token Plan Team Edition subscription.
- Z.AI/GLM is resolved from the uploaded `glm-5.1` billing table.
- Moonshot/Kimi is reconciled from request-log token totals plus Kimi dashboard Total Consumption.
- Grok/xAI is reconciled at provider-dashboard-total level; granular model/request export remains unavailable.

## Usage

Use the canonical ledger for dashboard ingestion and full-sweep funding planning. Older family reports are retained as component evidence and should not be deleted.
