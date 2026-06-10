# Phase 3 Dashboard and Runner Fleet Plan

## Goal

Build a polished benchmark dashboard early without coupling the benchmark runner, database, artifacts, and UI too tightly.

## Architecture

- GitHub remains the source of truth for code, arm configs, workflow definitions, and small report artifacts.
- Supabase Postgres stores benchmark metadata, summaries, audit records, and dashboard read models.
- Cloudflare R2 stores large run artifacts and trajectory outputs.
- OVH VPS instances run benchmark jobs as GitHub self-hosted runners.
- The dashboard is a separate Next.js application that reads Supabase and R2 metadata.

## Dashboard application

Initial app location: apps/dashboard/

Initial stack:

- Next.js
- Supabase client and SSR support
- Tailwind or shadcn-style components
- Server-side API routes for signed artifact links later

## Initial dashboard sections

1. Overview
   - Phase summaries
   - Pass rate
   - Cost
   - Runtime
   - Trial count
   - Artifact count

2. Runs
   - Filter by phase, mode, arm, provider family, model, task, date, and status
   - Show run status, pass rate, cost, runtime, artifact count, and audit status

3. Arms
   - Read the current arm registry from configs/arms/*.yaml
   - Show provider family, backend model, router model, harness, and active status
   - Show pass-rate, cost, and runtime summaries once results are backfilled

4. Tasks
   - Task-level pass/fail matrix
   - Identify tasks that separate model families

5. Artifacts
   - List R2 object keys, sizes, hashes, and artifact types
   - Later: add signed artifact links through a server-side endpoint

6. Audits
   - Secret scans
   - Benchmark-contamination scans
   - Tool-deny checks
   - Methodology checks

7. Qualitative review
   - Human notes
   - Failure classifications
   - Trajectory observations
   - Model behavior summaries

8. Figures
   - Reuse report figures
   - Add dashboard-native plots from Supabase views

9. Runner fleet
   - Registered runners
   - Labels
   - Last seen
   - Active or idle status
   - Assigned job
   - Host class and provider

10. Sweep planner
   - Select phase, mode, arms, tasks, and attempts
   - Estimate cost and runtime
   - Generate a workflow-dispatch payload

11. Arm scaffold helper
   - Generate proposed YAML/config snippets for new arms
   - Do not silently activate arms
   - All arm changes go through git review and secret scans

## Runner fleet strategy

The current OVH VPS should be treated as a single benchmark worker. True concurrency should come from multiple runners, ideally one runner per VPS.

Near-term runner labels:

- ovh-runner-01: phase3, ovh, x64, docker, smoke
- ovh-runner-02: phase3, ovh, x64, docker, smoke
- ovh-runner-03: phase3, ovh, x64, docker, smoke

GitHub Actions matrix jobs can use max-parallel equal to the number of available runner hosts.

## Automation levels

Level A: Manual pool, dashboard-aware

- Manually create 2-4 OVH VPS instances.
- Run the bootstrap script.
- Register each instance as a GitHub self-hosted runner.
- Dashboard shows runner health and labels.

Level B: Semi-automated runner bootstrap

- Add scripts under infra/ovh/.
- Install Docker, uv, Node, Claude Code, repo checkout, runner config, and runner service.
- Require a fresh GitHub runner registration token during setup.

Level C: Terraform/OpenTofu-managed pool

- Add OVH infrastructure definitions.
- Use cloud-init or equivalent bootstrap.
- Keep infrastructure changes behind git review or explicit workflow dispatch.

## Arm scaffold policy

The dashboard may generate proposed arm YAML/config snippets, but it should not silently activate new benchmark arms.

Expected flow:

1. Dashboard or helper script proposes a new arm config.
2. User reviews the generated config.
3. Repo checks and secret scans run.
4. Change is committed on the active phase branch.
5. GitHub workflow dispatch runs a canary for the new arm.

## Implementation order

1. Make ingestion idempotent.
2. Add Supabase dashboard views.
3. Backfill Phase 3 canaries and smokes.
4. Backfill Phase 1 and Phase 2 summaries.
5. Scaffold apps/dashboard.
6. Build the read-only dashboard first.
7. Add the arm scaffold helper.
8. Add the runner fleet status page.
9. Add the sweep planner.
10. Add OVH bootstrap/provisioning automation.
