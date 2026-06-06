# Phase 3 Remote Runner Options

This document defines the initial remote execution plan for Phase 3 smoke and later full-sweep benchmarking. The goal is to move benchmark execution off a local workstation while keeping the process reproducible, auditable, and easy to launch asynchronously.

## Decision

Initial remote runner stack:

- Compute: OVHcloud x86 VPS
- Orchestration: GitHub Actions with a self-hosted runner
- Benchmark worker: Docker-capable Linux host running Harbor, Terminal-Bench 2.0, Claude Code, and LiteLLM
- Metadata database: Supabase Postgres, initially kept within the free tier if possible
- Artifact storage: Cloudflare R2, initially kept within the free tier if possible
- Repository: GitHub remains the source of truth for scripts, configs, docs, and selected small CSV/JSON outputs

This avoids AWS for now while preserving a migration path to other runners, databases, and artifact stores later.

## Why remote execution

Remote execution should make benchmark work:

- Launchable from anywhere through GitHub Actions
- Less dependent on one developer workstation
- More reproducible across canary, smoke, and full-sweep modes
- Easier to parallelize later with additional self-hosted runners
- Easier to hand off to sponsor-side or collaborator-side infrastructure
- Easier to connect to a future dashboard and metadata database

## Recommended pilot topology

GitHub Actions manual dispatch triggers a workflow on the self-hosted runner. The runner checks out the repo, starts or verifies the LiteLLM router, runs `scripts/run_arm.sh`, writes results under `results/phase3/...`, runs evidence extraction and contamination audits, uploads large artifacts to R2, and inserts structured metadata into Supabase Postgres.

High-level flow:

1. User starts a GitHub Actions workflow manually.
2. Workflow targets a self-hosted runner labeled for Phase 3 benchmark work.
3. Runner executes one canary or smoke job.
4. Benchmark outputs are written locally first.
5. Post-run processing extracts structured metrics.
6. Large artifacts are uploaded to R2.
7. Run, trial, arm, model, cost, and artifact metadata are inserted into Postgres.
8. Selected small summaries may still be committed or attached as GitHub Actions artifacts.

## Initial OVHcloud VPS target

Preferred starting point:

- OS: Ubuntu 22.04 or 24.04 LTS
- Architecture: x86_64
- CPU: 4 vCore minimum; 6 to 8 vCore preferred if budget permits
- RAM: 8 GB minimum; 12 to 24 GB preferred for future parallelism
- Disk: 75 GB minimum; 100 GB or more preferred
- Docker: native Docker Engine
- Network: outbound HTTPS to provider APIs, GitHub, Supabase, and Cloudflare R2
- Runner mode: GitHub self-hosted runner installed as a service
- Benchmark concurrency: begin with `n_concurrent=1`

OVHcloud VPS-1 is a reasonable starting class for a remote canary/smoke pilot. Upgrade to VPS-2 or VPS-3 only if Docker image storage, task parallelism, or runtime pressure requires it.

Reference:
- OVHcloud VPS pricing/specs: https://us.ovhcloud.com/vps/

## Why self-hosted GitHub runner

A self-hosted GitHub runner gives us GitHub Actions as the control plane while keeping full control over the benchmark environment.

Benefits:

- Manual dispatch from GitHub
- Native integration with repo branches and commits
- GitHub secrets and environment controls
- Logs and job history in GitHub Actions
- Full Linux/Docker control on the VPS
- Easy migration to additional runners later

Cautions:

- The runner host must be treated as sensitive infrastructure.
- Secrets must never be printed to logs.
- Workspaces should be cleaned between runs.
- The runner should be scoped tightly to this repository or organization.
- Benchmark jobs need timeouts and concurrency limits.
- Provider API spend can exceed VPS spend if runs are launched accidentally.

Reference:
- GitHub self-hosted runners: https://docs.github.com/actions/hosting-your-own-runners

## Why not Fly.io or Railway for the benchmark worker

Fly.io, Railway, Render, and similar platforms may be useful later for a lightweight dashboard, webhook receiver, or router service, but they are not the first choice for the Harbor/Terminal-Bench worker because the benchmark worker needs a Docker-capable Linux environment that may itself launch or interact with task containers.

The benchmark worker is better suited to a normal VPS with Docker installed directly.

## Recommended run modes

### Remote canary

Purpose:

- Confirm the remote runner, secrets, Docker, LiteLLM, provider API access, artifact upload, and DB insert path.

Recommended first target:

- One cheap, known-good arm
- One known canary task
- `n_attempts=1`
- `n_concurrent=1`

### Funded 5-task smoke

Purpose:

- Replace one-task canary-scaled cost estimates with multi-task cost/runtime evidence.
- Confirm per-provider reliability and failure modes before full sweep.

Recommended settings:

- 13 active canary-green arms
- 5 selected tasks
- 1 attempt per task initially, unless the smoke design explicitly requires more
- `n_concurrent=1` until provider rate limits and cost behavior are confirmed

### Full sweep

Purpose:

- Execute sponsor-approved full comparison after smoke results confirm cost behavior.

Recommended gate:

- Do not run full sweep until smoke cost/rate-limit behavior is reviewed.

## Security considerations

- Keep `.secrets/` ignored and never committed.
- Prefer GitHub Actions secrets or environment secrets for remote runs.
- Avoid printing environment variables.
- Run `make secret-scan` before committing any benchmark outputs.
- Keep provider keys separate from R2 and Supabase credentials.
- Use least-privilege R2 bucket credentials.
- Use least-privilege Supabase credentials for ingestion if possible.
- Consider a separate Supabase service role only for ingestion scripts, not notebooks or dashboards.
- Rotate credentials if logs ever expose secret-like values.

## Cost controls

Initial guardrails:

- Use one runner only.
- Use `n_concurrent=1`.
- Require manual dispatch for smoke/full-sweep jobs.
- Add workflow inputs for phase, mode, arm list, task list, attempts, and dry-run.
- Add max runtime per job.
- Add a pre-run cost estimate printout.
- Add explicit confirmation flags for full sweeps.
- Keep Supabase and R2 within free tier initially.
- Upload only needed artifacts to R2.

Expected infrastructure cost range, excluding model API usage:

- Cheapest pilot: roughly $7 to $15 per month.
- Practical shared pilot: roughly $10 to $25 per month if Supabase and R2 stay free.
- More robust setup: roughly $25 to $60 per month if the VPS is upgraded or managed database/storage paid tiers become necessary.

## Implementation milestones

1. Add documentation for remote runner and DB/artifact strategy.
2. Provision OVHcloud x86 VPS.
3. Install Docker, uv, git, GitHub runner, and benchmark prerequisites.
4. Register self-hosted GitHub runner with label such as `phase3-smoke-x86`.
5. Add GitHub Actions workflow for manual remote benchmark dispatch.
6. Configure Supabase project and minimal schema.
7. Configure Cloudflare R2 bucket and least-privilege credentials.
8. Add ingestion script for run/trial/artifact metadata.
9. Run one remote canary.
10. Review DB rows, R2 artifacts, logs, and cost.
11. Run funded 5-task smoke.
