# Planner page guide

## Executive summary

Planner is a review-first, read-only planning surface. It has one mode for constructing benchmark
run commands and another for drafting future arm YAML. Run planning reads checked-in configuration
plus the current fail-closed promotion-gate view. Planner can withhold or display commands, but it
does not write a gate, modify reconciliation, create a waiver, dispatch a workflow, or mutate
benchmark evidence.

## Route and implementation

- Dashboard route: `/planner`.
- Page source: `apps/dashboard/src/app/planner/page.tsx`.

## Data sources

- Checked-in arm YAML under `configs/arms` and checked-in task-set configuration.
- Run-planning rules from `run-plan-validation.ts`, including runner-slot and provider-family
  safeguards.
- Current promotion evidence from `getCurrentEvidencePromotionGates()`, backed by the fail-closed
  `benchmark.v_evidence_promotion_gate` view.
- Arm-draft mode reads existing configs and emits reviewable YAML text only.

## Population and authority

- Canary planning has no predecessor promotion-gate requirement.
- Smoke requires an effective current Canary-to-Smoke gate for every selected arm.
- Full requires an effective current Smoke-to-Full gate for every selected arm.
- A stored waiver is visible provenance but is not effective authorization.

## How to read the page

- Treat checked-in runner slots, per-job concurrency, and provider-family rules as planning
  assumptions, not live capacity/readiness facts.
- For Smoke/Full, inspect source arm run, usage/cost reconciliation states, reviewer, limitations,
  blockers, and exact evidence-chain IDs.
- Evidence qualification is necessary but still requires local confirmation that the human reviewed
  the displayed promotion and relevant qualitative evidence.
- A clear Planner state means command text may be copied; it does not mean the dashboard has
  dispatched anything.

## Controls and filters

- `mode=run` plans benchmark commands; `mode=arm` drafts new arm configuration YAML.
- Run mode controls arm selection, run mode, task set/file, concurrency, dry-run/paid confirmation,
  and local promotion-review acknowledgement.
- The acknowledgement is bound to the exact selected arm set/mode/evidence packet and resets when
  that packet changes.
- Blocked plans replace command output with a withheld-command message.

## Caveats and non-inferences

- If the promotion-gate database read is unavailable, Smoke and Full fail closed; Canary planning
  remains usable.
- Planner cannot turn a waived or stale gate into authorization.
- Planner does not establish actual runner availability, provider quota, API access, or service
  readiness.
- The current gate scope remains arm plus target mode; Phase 4 must review experiment/suite scoping
  before its first paid Canary.
- Protected server-side dashboard dispatch remains deferred.

## Common workflows

- For a next-stage run, first establish durable promotion review with the CLI/runbook, then reopen
  Planner and inspect the exact current gate.
- Use run mode to produce reviewable CLI/workflow command text only after all blockers are resolved.
- Use arm mode to draft configuration, then review and commit it through Git rather than writing
  config from the dashboard.

## Evidence tracing

- Selected arm/mode → current gate view → exact source arm run → usage reconciliation → cost
  reconciliation → provider evidence.
- Planner blocker → durable Evidence Promotion Review runbook → Plan/Check/Rollback/Apply CLI
  workflow.
- Generated command → human copy/review → separate external execution step; no dashboard dispatch
  occurs.

## Related documentation

- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Evidence Promotion Review runbook](../../runbooks/EVIDENCE_PROMOTION_REVIEW.md).
- [Usage and Cost Evidence Model](../../methodology/USAGE_AND_COST_EVIDENCE_MODEL.md).
- [Architecture page guide](ARCHITECTURE.md).
