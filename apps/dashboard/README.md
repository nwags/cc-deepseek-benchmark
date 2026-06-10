# Phase 3 Dashboard

Polished read-only dashboard for the Phase 3 Claude Code backend benchmark.

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
