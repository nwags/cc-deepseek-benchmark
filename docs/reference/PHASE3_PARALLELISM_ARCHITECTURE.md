# Phase 3 Parallelism Architecture

Status: design guardrail for smoke-to-full-sweep planning.

Phase 3 should not treat the current OVH VPS as a finished benchmark farm. The long-term architecture is a persistent control plane plus an elastic worker pool.

## Current safe operating mode

Current safe mode is:

- one self-hosted GitHub Actions runner job at a time,
- one arm per dispatch,
- `n_attempts=1` for smoke,
- `n_concurrent=1` until runtime, Docker behavior, provider rate limits, and cost behavior are measured.

This is sufficient for conservative smoke waves. It is not sufficient for the full sweep.

## Control plane vs worker pool

The intended architecture has two layers.

### Persistent control plane

A small always-on OVH VPS or equivalent host should run:

- dashboard,
- planner UI,
- run-status views,
- artifact/status ingestion helpers,
- optional dispatch backend,
- optional lightweight route/readiness probes.

The control plane should not be the main full-sweep execution farm.

### Elastic worker pool

Benchmark execution should move toward disposable or isolated workers:

- GitHub self-hosted runner slots,
- Docker,
- Harbor,
- Claude Code,
- LiteLLM route access,
- provider API traffic,
- results/artifact upload,
- cleanup after completion.

For the full sweep, horizontal worker instances are preferred over relying on one larger VPS.

## Concurrency model

There are two independent concurrency layers:

- workflow-level concurrency: number of GitHub Actions runner jobs active at once,
- Harbor-level concurrency: `--n-concurrent` inside each benchmark job.

Effective execution load is approximately:

    effective_task_parallelism = active_runner_jobs * harbor_n_concurrent

Do not increase both layers at the same time until cost, quotas, Docker cleanup, and artifact upload are proven.

## Runner slot contract

A runner slot is an isolated execution lane. Each slot should have:

- `slot_id`,
- unique GitHub runner name,
- unique runner label,
- isolated checkout/workspace root,
- isolated `.run` directory,
- isolated result/artifact path,
- LiteLLM port or clearly shared LiteLLM policy,
- max `n_concurrent`,
- Docker cleanup policy,
- health/doctor checks,
- provider-family concurrency limits,
- cost guardrails.

Example single-host slot layout:

    phase3-slot-1 -> label phase3-slot-1 -> LiteLLM 4001 -> /srv/phase3/slot-1
    phase3-slot-2 -> label phase3-slot-2 -> LiteLLM 4002 -> /srv/phase3/slot-2
    phase3-slot-3 -> label phase3-slot-3 -> LiteLLM 4003 -> /srv/phase3/slot-3

A single-host slot layout is useful as a bridge, but the full-sweep target should be horizontally scalable worker instances.

## OVH scaling approach

Use a hybrid plan.

### Near term

Use the existing OVH VPS as:

- control plane,
- one conservative runner,
- firewall/readiness validation host,
- dashboard host.

Run smoke waves serially.

### Intermediate

Either:

- add two or three isolated runner slots to a larger host, or
- add a small number of separate worker instances.

This phase proves runner-slot isolation and safe concurrent dispatch.

### Full sweep

Use horizontally provisioned OVH Public Cloud worker instances or equivalent disposable workers.

The preferred full-sweep flow is:

    provision worker
      -> bootstrap Docker, uv, node, Claude Code, Harbor, LiteLLM
      -> register ephemeral GitHub runner
      -> run one bounded benchmark job
      -> upload artifacts/results
      -> deregister runner
      -> destroy worker

Vertical resizing of one VPS can help a control plane or a temporary multi-slot host, but it should not be the primary full-sweep scaling mechanism.

## LiteLLM policy

Two patterns are possible.

### Shared LiteLLM

One LiteLLM service is shared by several runner jobs.

Advantages:

- simpler setup,
- one router config,
- easier model routing edits.

Risks:

- shared logs,
- shared failure domain,
- harder per-run isolation,
- harder per-slot throughput diagnosis.

### Per-slot LiteLLM

Each slot starts its own LiteLLM service on a unique port.

Advantages:

- cleaner isolation,
- per-slot logs,
- easier debugging,
- better match for disposable workers.

Risks:

- more workflow/config complexity,
- more ports/firewall rules,
- more startup overhead.

For full sweep, per-slot or per-worker LiteLLM is preferred.

## Full-sweep blockers

Do not run the full sweep until all of these are true:

1. Smoke wave 0 succeeds serially.
2. Runner-slot abstraction is documented and implemented.
3. At least two concurrent dry-run dispatches succeed without workspace, Docker, or artifact collisions.
4. At least two cheap paid canaries or smoke jobs run concurrently and upload artifacts correctly.
5. Cost ingestion distinguishes real zero cost from missing cost.
6. Provider-family concurrency caps are defined.
7. A kill switch exists for canceling queued/running benchmark jobs.
8. Secrets remain isolated and uncommitted.
9. Docker cleanup is verified after successful and failed runs.
10. Dashboard/runner state makes it clear which worker/slot produced each result.

## Recommended smoke-to-full-sweep path

1. Smoke wave 0: serial, `n_attempts=1`, `n_concurrent=1`.
2. Smoke wave 1: serial or very limited parallelism after wave 0.
3. Parallelism milestone: implement runner slots and prove two concurrent dry-runs.
4. Paid parallelism milestone: prove two cheap concurrent jobs.
5. Full-sweep readiness review.
6. Full sweep with explicit cost, quota, and concurrency approval.
