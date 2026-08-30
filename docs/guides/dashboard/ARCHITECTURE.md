# Architecture page guide

## Executive summary

Architecture is a checked-in documentation surface, not a live topology or readiness monitor. It
separates benchmark execution and verifier scoring, optional live observation, final canonical
publication, provider-evidence reconciliation and promotion review, and dashboard storage/read
paths.

## Route and implementation

- Dashboard route: `/architecture`.
- Page source: `apps/dashboard/src/app/architecture/page.tsx`.
- The page is dynamically rendered by Next.js but its architecture content is checked-in
  documentation rather than a live infrastructure probe.

## Data sources

- Checked-in workflow, runner, Harbor, publication, provider-evidence, and dashboard architecture
  encoded directly in the page source.
- Current provider-evidence and promotion concepts correspond to Migration 011 and the guarded
  promotion-review CLI.
- Current live/publication switch descriptions reflect repository workflow behavior, not measured
  provider or runner availability.

## Population and authority

- This page describes system responsibilities and boundaries rather than a trial population.
- Phases 1–3 use Claude Code as the fixed principal agent harness; `agent_harness` is already
  canonical arm metadata.
- Phase 4 and Phase 5 material is explicitly prospective compatibility guidance, not active
  experiment state.

## How to read the page

- Read the numbered flows independently: scoring, live observation, canonical publication, provider
  evidence/promotion, then dashboard storage.
- Keep Harbor's held-out verifier/test result as scoring authority; dashboard diagnosis does not
  rescore a trial.
- Treat Supabase as metadata/state and R2 as evidence-byte storage; neither is a direct connection
  from the dashboard to the runner or Docker.
- Treat the Planner as a consumer of promotion evidence, not as the writer of that evidence.

## Controls and filters

- There are no population filters. Cross-links move to Glossary, Artifacts, Trial Quality, Live
  Runs, Runs, Data Model, and Planner.
- Displayed workflow switch values explain behavior and current dispatch defaults; they are not
  interactive controls on this page.

## Caveats and non-inferences

- Live supervision is optional and failure-isolated; failure to publish live state does not change
  Harbor's benchmark result.
- Canonical publication is an after-execution path and does not depend on live supervision having
  run.
- Runner topology language does not establish fleet size, current availability, queue depth, or
  capacity.
- A future harness experiment requires methodology and promotion-scope review before any paid Phase
  4 Canary.

## Common workflows

- Use this page when diagnosing which subsystem owns a fact: scoring, live state, canonical
  publication, provider billing evidence, or dashboard presentation.
- Before changing publication or promotion behavior, follow the corresponding flow into Codebase
  Guide and the relevant runbook.

## Evidence tracing

- Execution claim → arm/suite config → workflow/local dispatch → Harbor result directory → verifier
  result.
- Live-state claim → `run_arm_live.py` → live Supabase relations/R2 object → Live Runs.
- Promotion claim → canonical arm run → provider evidence → usage/cost reconciliations → promotion
  gate view → Planner.

## Related documentation

- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Data Model page guide](DATA_MODEL.md).
- [Live Runs page guide](LIVE_RUNS.md).
- [Planner page guide](PLANNER.md).
- [Evidence Promotion Review runbook](../../runbooks/EVIDENCE_PROMOTION_REVIEW.md).
