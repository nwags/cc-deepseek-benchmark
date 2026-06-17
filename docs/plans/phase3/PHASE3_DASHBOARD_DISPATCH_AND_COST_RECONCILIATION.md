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

## Stage B validator-first implementation

Stage B begins with a read-only dashboard run-plan validator before any dashboard dispatch button exists.

The validator should show:

- runner-slot demand separately from provider-family demand.
- effective task parallelism as `selected_runner_jobs * harbor_n_concurrent`.
- provider-family warnings and blockers.
- arm configuration metadata used for classification.

Initial hard rules:

- Gemini: block or warn when more than one Gemini-family arm appears in the same wave.
- Qwen: block full-sweep use until Alibaba identity verification and usage-metering reconciliation are complete.
- Fable: block until provider availability/access is restored.
- Runner slots: show current 3-slot capacity separately from provider-family limits.

This validator is a guardrail for later dashboard dry-run dispatch. It must not launch paid work.


## Stage B planner workflow refinement

The first validator pass exposed a workflow split: the run-plan validator handled multi-arm provider/running constraints, while the planner controls still generated a single-arm terminal command. That made the planner page hard to reason about.

Stage B should use one integrated run-plan builder:

- select existing arms from the dashboard arm registry instead of typing arm IDs;
- use one term, `Run mode`, matching the workflow modes `canary`, `smoke`, and `full`;
- validate runner-slot and provider-family constraints for the selected wave;
- generate one reviewed GitHub Actions dispatch command per selected arm;
- keep dashboard dispatch disabled until a later protected server-side dispatch stage.

The arm scaffold page remains the place to generate reviewable YAML snippets for new arms.

## Stage B validation extraction and tests

The run-plan provider-family and runner-capacity rules are extracted into `apps/dashboard/src/lib/run-plan-validation.ts` so they can be tested independently from the React planner UI.

Coverage includes:

- three selected arms with `n_concurrent=1` yielding effective concurrency 3;
- three selected arms with `n_concurrent=2` yielding effective concurrency 6 plus a warning;
- two Gemini-family arms producing a blocker;
- Qwen full-sweep plans producing a blocker;
- Fable plans producing a blocker;
- more selected arms than runner slots producing a runner-capacity blocker.

The UI now labels this control as `Harbor n_concurrent per arm job` and labels the computed metric as max task concurrency to avoid confusing arm-wave concurrency with Harbor task concurrency.

