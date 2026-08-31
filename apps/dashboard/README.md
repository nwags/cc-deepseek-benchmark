# Benchmark Dashboard

Polished read-only dashboard for Claude Code backend benchmark results.

## Required onboarding entry point

If you are a new team member, do not use this dashboard README or the Overview
page as a substitute for project onboarding.

Start with the required hand-off/onboarding index:

`docs/guides/README.md`

That checklist requires review of all 16 principal dashboard surfaces, all
three primary handoff guides, and the evidence-tracing exercises. If dashboard
access or required credentials are unavailable, record and resolve that as an
onboarding blocker rather than silently skipping dashboard review.

## Local setup

Copy the example env file:

cp .env.local.example .env.local

Set SUPABASE_DB_URL in .env.local. This is a server-side secret and must not be committed.

Install and run:

npm install
npm run dev

Open the local URL printed by Next.js.

## Data source

The dashboard reads Supabase Postgres views in the benchmark schema:

- benchmark.v_dashboard_runs
- benchmark.v_dashboard_arms
- benchmark.v_dashboard_tasks
- benchmark.live_runs
- benchmark.live_run_events
- benchmark.live_trials
- benchmark.live_artifacts
- benchmark.benchmark_provider_evidence_sources
- benchmark.benchmark_provider_usage_evidence
- benchmark.benchmark_provider_pricing_snapshots
- benchmark.benchmark_provider_cost_evidence
- benchmark.benchmark_usage_reconciliations
- benchmark.benchmark_usage_reconciliation_sources
- benchmark.benchmark_cost_reconciliations
- benchmark.benchmark_cost_reconciliation_sources
- benchmark.v_evidence_promotion_gate

The Data Model route documents the wider checked-in relationship set; individual
pages query only the sources required by their declared evidence contract.

Large artifacts remain in Cloudflare R2. `/runs/live` reads shared Supabase
state published by remote runners and shows bounded event, partial-trial, and
progressive-artifact data. It marks active rows stale after 90 seconds without
a heartbeat and refreshes automatically while a non-stale execution remains
active. A stale orphan alone does not keep the page on an eight-second loop.

The workstation-local `.run/live` reader is development-only. Set
`DASHBOARD_LIVE_LOCAL_FALLBACK=true` to use it only when shared live state is
unavailable.

## Read-only and presentation contracts

Operational dashboard database reads use the shared `queryRows()` boundary,
which opens an explicit read-only transaction for each query and rolls back on
failure. Dashboard pages should not bypass that boundary with direct pool
queries.

The dashboard also has a presentation-only precision ceiling of four
fractional digits. Values that exceed the ceiling are truncated toward zero,
not rounded. Lower intentional precision remains lower precision. Stored,
generated, reviewed, and retained evidence precision is unchanged, and missing
or unavailable values never become zero merely for display.

## Current dashboard role

The dashboard is a read-only research and evidence interface. The primary
navigation currently contains:

- **Overview** — current reviewed Phase 3 comparison plus clearly separated
  dynamic inventory evidence.
- **Architecture** — execution, scoring, live observation, canonical
  publication, provider evidence/reconciliation, promotion review, and storage
  flow.
- **Data Model** — live, canonical experimental identity, provider evidence,
  reviewed authority, derived, R2, reviewed-snapshot, dashboard-consumer, and
  future-phase extension layers.
- **Glossary** — shared benchmark terminology.
- **Trial Quality** — reviewed failure/trajectory analysis plus operational
  quality evidence.
- **Cross-phase** — Phase 1/2 historical comparison with the current reviewed
  Phase 3 cost layer.
- **Eval Suites** — suite-level evidence.
- **Evals** — task/eval comparison with explicit inventory scope.
- **Runs** — canonical imported run inventory and run detail.
- **Live Runs** — mutable live execution observation; not canonical truth.
- **Arms** — imported arm inventory including canonical agent-harness
  identity when recorded.
- **Artifacts** — retained artifact inventory and bounded evidence access.
- **Provider Evidence** — source-centric normalized provider usage, pricing,
  cost, and reconciliation provenance with complete supporting-source and
  cross-source pricing links; it is read-only and does not call provider APIs.
- **Evidence Review** — manifest-validated frozen comprehensive review.
- **Planner** — review-first run-plan construction/validation that reads
  the current fail-closed predecessor promotion gate; it does not write gates
  or dispatch benchmark work.
- **Cost Coverage** — current selected cost alongside historical reviewed
  accounting/decomposition.

Retired or contained historical routes may still exist for provenance, but they
are not primary navigation.

For page-specific interpretation of all 16 principal dashboard surfaces, use:

```text
docs/guides/dashboard/README.md
```

That manual documents each page's route, data source, population/authority,
controls, caveats, common workflows, and evidence-tracing path.

For cross-page research workflow guidance, use:

```text
docs/guides/DASHBOARD_RESEARCH_GUIDE.md
```

For the current durable Canary/Smoke promotion-review procedure, use:

```text
docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md
```

For provider usage/cost capability, collection, reconciliation, and future
collector-automation guidance, use:

```text
docs/reference/PROVIDER_USAGE_COST_AUTOMATION.md
```

For protected server-side dispatch as possible future work, use:

```text
docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md
```

<!-- phase3-2026-06-12-alignment:start -->
## Historical 2026-06-12 dashboard usage alignment

> The section below is preserved as historical dashboard/planner planning
> context. Its navigation names and operating assumptions are not the current
> primary dashboard contract.

The dashboard should be used as the benchmark operating console:

- Overview: current status, cost coverage, and blockers.
- Runs: imported run roots and run detail debugging.
- Arms: route/model status and canary/smoke readiness.
- Tasks: task-level pass/fail patterns.
- Artifacts: logs, verifier output, trajectories, and R2/GitHub artifact references.
- Runner Fleet: runner readiness, labels, Docker/firewall readiness, and hosted-NIM readiness.
- Sweep Planner: reviewable payloads for `canary`, `smoke`, `full-sweep`, and `ad-hoc`.
- Cost Coverage: distinguish valid metered runs from infra failures and missing-cost rows.
- Provider / Route Readiness: direct API, LiteLLM route, Claude Code route, and Harbor canary checks.

The dashboard should not silently mutate benchmark configuration or promote ad-hoc runs into scored results.
<!-- phase3-2026-06-12-alignment:end -->
