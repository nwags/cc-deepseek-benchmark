# Phase 3 Smoke Plan

> **Historical status — 2026-08-23:** The Phase 3 smoke program
> is complete historical work. This file preserves the smoke-wave design and
> provider/runner lessons; it is not current authorization to restart Phase 3
> smoke or full-sweep execution. Current successor guidance is
> `docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md`.

Status: planning document for the first Phase 3 smoke wave.

This plan follows the Phase 3 parallelism architecture. Initial smoke runs are deliberately serial and conservative. The full sweep remains blocked until runner-slot parallelism has been implemented and validated.

## Objectives

Phase 3 smoke should answer:

1. Which canary-green router arms remain stable beyond a single canary task?
2. Which provider families show cost, latency, quota, or tool-compatibility issues before the full sweep?
3. Which arms should advance to full-sweep eligibility?
4. Which infrastructure pieces must be improved before parallel execution?

## Active smoke-eligible arms

The active smoke pool is limited to arms that have passed Phase 3 canary or equivalent route validation.

Recommended smoke-eligible arms:

- `router-anthropic-haiku-sanitized`
- `router-anthropic-sonnet`
- `router-anthropic-opus`
- `router-anthropic-fable-5`
- `router-deepseek-flash`
- `router-deepseek-pro`
- `router-gemini-flash`
- `router-gemini-3.1-pro`
- `router-gpt-5.4`
- `router-gpt-5.5`
- `router-grok-build-0.1`
- `router-kimi-k2.6`
- `router-qwen-3.7-plus`
- `router-glm-5.1`

## Excluded, retired, or discovery-only arms

Do not include these in Phase 3 smoke:

- NVIDIA NIM: retired from active Phase 3 planning.
- Anthropic Mythos 5: gated/unavailable for this account after direct API 404.
- OpusPlan: Phase 2 discovery-only; not a normal Phase 3 model arm.
- Failed or superseded earlier slugs:
  - `router-glm-5`
  - `router-grok-3`
  - `router-kimi-k2.5`
  - `router-qwen-3.5`

## Smoke wave 0

Wave 0 should be a conservative, broad-provider sample. It should run serially.

Recommended wave 0 arms:

- `router-anthropic-fable-5`
- `router-deepseek-flash`
- `router-gemini-flash`
- `router-gpt-5.4`
- `router-kimi-k2.6`
- `router-qwen-3.7-plus`
- `router-glm-5.1`

Default wave 0 settings:

- `mode=smoke`
- `dry_run=true` first
- paid dispatch only after command review
- `confirm_paid_run=true` only for reviewed paid dispatch
- `n_attempts=1`
- `n_concurrent=1`
- one active benchmark dispatch at a time

## Smoke wave 1

Wave 1 should be selected after wave 0 results are reviewed.

Likely wave 1 candidates:

- remaining Anthropic comparison arms:
  - `router-anthropic-haiku-sanitized`
  - `router-anthropic-sonnet`
  - `router-anthropic-opus`
- remaining expensive or high-interest frontier arms:
  - `router-anthropic-fable-5`, if wave 0 is stable and cost is acceptable
  - `router-gpt-5.5`
  - `router-gemini-3.1-pro`
  - `router-deepseek-pro`

Wave 1 should still default to serial dispatch unless wave 0 shows stable runtime, cleanup, and cost behavior.

## Task set

Use the existing Phase 3/Phase 2 smoke task file if present. The planner should show the available task files from `configs/tasks`.

Preferred task-file order:

1. `configs/tasks/phase3-smoke.txt`, if created later.
2. `configs/tasks/phase2-smoke.txt`, if present.
3. `configs/tasks/terminal-bench-20.txt`, if present.
4. Another reviewed smoke-sized task list.

Do not create a new task set from memory without reviewing available task coverage and historical Phase 1/Phase 2 comparability.

## Dispatch pattern

Dry-run example:

    gh workflow run phase3-arm-dispatch.yml \
      --ref main \
      -f arm_id=router-deepseek-flash \
      -f mode=smoke \
      -f dry_run=true \
      -f confirm_paid_run=false \
      -f n_attempts=1 \
      -f n_concurrent=1 \
      -f task_id= \
      -f task_file= \
      -f ad_hoc_label=

Paid dispatch template, after review:

    gh workflow run phase3-arm-dispatch.yml \
      --ref main \
      -f arm_id=<ARM_ID> \
      -f mode=smoke \
      -f dry_run=false \
      -f confirm_paid_run=true \
      -f n_attempts=1 \
      -f n_concurrent=1 \
      -f task_id= \
      -f task_file= \
      -f ad_hoc_label=

## Review criteria

After each smoke arm completes, record:

- pass/fail count,
- wall-clock runtime,
- model/provider cost,
- missing-cost rows,
- timeout or nonzero agent exit errors,
- Docker/container cleanup issues,
- LiteLLM/API errors,
- artifact upload status,
- whether the arm remains full-sweep eligible.

## Full-sweep blocker

Do not run the full sweep until:

- smoke wave 0 is complete and reviewed,
- at least one follow-up smoke wave is complete or deliberately waived,
- cost coverage is understood,
- provider-family concurrency caps are documented,
- runner-slot parallelism is implemented and tested,
- at least two concurrent dry-runs succeed,
- at least two cheap paid jobs run concurrently without collisions,
- dashboard or reports clearly show worker/slot provenance.

## GLM-5.2 same-family addition

`router-glm-5.2` is a same-provider/same-family successor to the already validated `router-glm-5.1` route.

Policy:

- keep `router-glm-5.1` results intact;
- add `router-glm-5.2` as a separate Phase 3 arm;
- require a cheap route/model probe before any paid Harbor work;
- use Z.AI published GLM-5.2 rates: `$1.40/M` input, `$0.26/M` cached input, `$4.40/M` output;
- do not merge GLM-5.2 results into GLM-5.1 evidence.
