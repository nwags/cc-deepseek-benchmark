# Phase 3 Dashboard Dispatch and Cost Reconciliation Plan

## Dashboard dispatch

Current state: the dashboard/planner is review-first. Benchmark execution is still launched through reviewed GitHub Actions workflow dispatch commands.

Target state: authenticated dashboard dispatch through a server-side API that calls GitHub Actions `workflow_dispatch`.

Required controls:

- Server-side GitHub token only; no browser-exposed dispatch token.
- Allow-list of valid Phase 3 arms and modes.
- Default to dry-run dispatch.
- Explicit paid-run confirmation gate.
- Queue/concurrency awareness for available runner slots.
- Audit log of dispatched runs.
- Links from dashboard dispatch record to GitHub Actions run and later ingested artifacts.
- Result ingestion refresh after run completion.

Rollout:

1. Stage A: dashboard emits reviewed dispatch commands.
2. Stage B: protected dashboard button for dry-runs.
3. Stage C: protected dashboard button for paid runs.
4. Stage D: queued multi-run plans with provider-aware concurrency limits.

## Provider and infrastructure cost reconciliation

Before full sweep, produce a sponsor-facing usage/cost reconciliation report.

Internal sources:

- Harbor `result.json`
- Phase-specific aggregate CSV/JSON files
- LiteLLM token accounting
- GitHub Actions run IDs
- Artifact IDs and result paths
- Dashboard/Supabase ingested records

Provider sources to reconcile:

- Anthropic
- OpenAI
- DeepSeek
- Google/Gemini
- xAI/Grok
- Moonshot/Kimi
- Alibaba Cloud / Model Studio / DashScope / Qwen
- ZAI / GLM

Infrastructure sources:

- VPS / OVH
- Supabase
- Cloudflare R2
- GitHub Actions self-hosted runner assumptions

Qwen / Alibaba specific questions:

- Which account, workspace, region, and project owns the DashScope key?
- Is usage billed through DashScope direct API, Model Studio subscription, prepaid quota, or cloud credits?
- Where does official usage appear?
- Are calls consuming credits without appearing in the expected usage dashboard?
- Are model subscriptions required in addition to token-based API billing?
- Which Qwen model IDs map to our `router-qwen-*` arms?
- What rate limits and quotas apply to the current key?

Deliverable:

A sponsor update that separates benchmark model spend from infrastructure spend, flags unreconciled provider dashboards, and identifies any provider-specific billing risks before the full sweep.
