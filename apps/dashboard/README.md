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

Large artifacts remain in Cloudflare R2. This first dashboard scaffold displays artifact metadata only; signed R2 artifact links can be added later through server-side routes.

<!-- phase3-2026-06-12-alignment:start -->
## 2026-06-12 dashboard usage alignment

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
