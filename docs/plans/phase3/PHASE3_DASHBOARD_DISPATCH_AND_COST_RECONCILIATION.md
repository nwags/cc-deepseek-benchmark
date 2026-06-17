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

## Alibaba / Qwen identity-verification note

Alibaba Cloud / Model Studio may require individual identity verification before Model Studio or DashScope usage is fully enabled. This may include submitting a government photo ID.

Before any Qwen full-sweep run:

- Confirm Alibaba Cloud identity verification status is `Verification Successful`.
- Confirm the DashScope/API key is attached to the intended account, workspace, project, and region.
- Confirm whether usage is billed through direct token usage, free quota, prepaid quota, subscription, or cloud credits.
- Confirm where Qwen API usage appears in Alibaba's official billing/usage dashboards.
- Record any official-dashboard discrepancy between benchmark token usage and Alibaba-reported usage.

If verification remains pending or usage does not appear in official dashboards, treat Qwen as billing-reconciliation-risk and avoid full-sweep execution until resolved.

## Provider-family concurrency rule

The 2026-06-16 three-slot smoke wave showed that runner-slot concurrency and provider-family concurrency must be modeled separately.

The runner fleet successfully executed three simultaneous smoke jobs across three runner slots, but two simultaneous Gemini-family arms produced provider-side `429 Too Many Requests` errors.

Dashboard dispatch should therefore validate both:

- runner-slot demand, such as 3 jobs across 3 runner slots; and
- provider-family demand, such as Gemini arms per wave.

Initial provider-family rules:

- Gemini: max 1 concurrent arm until quota/rate-limit behavior is verified or raised.
- Qwen: blocked for full sweep until Alibaba identity verification and usage-metering reconciliation are complete.
- Fable: blocked until Anthropic availability/access is restored.
- Other provider families: allow 1 per arm initially, then update after more evidence.

The dashboard should surface this as a run-plan warning before paid dispatch.
