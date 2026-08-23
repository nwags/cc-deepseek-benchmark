# Benchmark Dashboard

Polished read-only dashboard for Claude Code backend benchmark results.

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

Large artifacts remain in Cloudflare R2. `/runs/live` reads shared Supabase
state published by remote runners and shows bounded event, partial-trial, and
progressive-artifact data. It marks active rows stale after 90 seconds without
a heartbeat and refreshes automatically while a non-stale execution remains
active. A stale orphan alone does not keep the page on an eight-second loop.

The workstation-local `.run/live` reader is development-only. Set
`DASHBOARD_LIVE_LOCAL_FALLBACK=true` to use it only when shared live state is
unavailable.

## Current dashboard role

The dashboard is a read-only research and evidence interface. The primary
navigation currently contains:

- **Overview** — current reviewed Phase 3 comparison plus clearly separated
  dynamic inventory evidence.
- **Architecture** — execution, scoring, live observation, canonical
  publication, and storage flow.
- **Data Model** — live, canonical, derived, R2, reviewed-snapshot, and
  dashboard-consumer layers.
- **Glossary** — shared benchmark terminology.
- **Trial Quality** — reviewed failure/trajectory analysis plus operational
  quality evidence.
- **Cross-phase** — Phase 1/2 historical comparison with the current reviewed
  Phase 3 cost layer.
- **Eval Suites** — suite-level evidence.
- **Evals** — task/eval comparison with explicit inventory scope.
- **Runs** — canonical imported run inventory and run detail.
- **Live Runs** — mutable live execution observation; not canonical truth.
- **Arms** — imported arm inventory.
- **Artifacts** — retained artifact inventory and bounded evidence access.
- **Evidence Review** — manifest-validated frozen comprehensive review.
- **Planner** — review-first run-plan construction/validation; it does not
  dispatch benchmark work.
- **Cost Coverage** — current selected cost alongside historical reviewed
  accounting/decomposition.

Retired or contained historical routes may still exist for provenance, but they
are not primary navigation.

For research workflow guidance, use:

```text
docs/guides/DASHBOARD_RESEARCH_GUIDE.md
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
