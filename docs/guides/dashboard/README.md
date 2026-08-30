# Dashboard page guides

## Executive summary

These guides are the page-specific companion to the
[Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md). They cover the 15
principal surfaces in the dashboard navigation and explain each page's evidence
source, population, authority, controls, caveats, research workflows, and
evidence-tracing path.

They **augment rather than replace** the cross-page Research Guide. Read the
Research Guide first when the question spans several pages or evidence classes.

## Principal dashboard manual

| Surface | Route | Guide | Primary authority |
|---|---|---|---|
| Overview | `/` | [Overview](OVERVIEW.md) | Fixed current-reviewed comparison plus separately labeled dynamic operational discovery |
| Architecture | `/architecture` | [Architecture](ARCHITECTURE.md) | Checked-in documentation |
| Data Model | `/data-model` | [Data Model](DATA_MODEL.md) | Checked-in schema/read-path documentation |
| Glossary | `/glossary` | [Glossary](GLOSSARY.md) | Checked-in definitions |
| Trial Quality | `/trial-quality` | [Trial Quality](TRIAL_QUALITY.md) | Frozen J2 review plus separate operational audit sections |
| Cross-phase | `/cross-phase` | [Cross-phase](CROSS_PHASE.md) | Frozen Phase 1/2 plus current-reviewed Phase 3 |
| Eval Suites | `/eval-suites` | [Eval Suites](EVAL_SUITES.md) | Dynamic valid-imported operational suite aggregates |
| Evals | `/evals` | [Evals](EVALS.md) | Valid-imported default; all-imported alternate |
| Runs | `/runs` | [Runs](RUNS.md) | Canonical operational imported-run inventory |
| Live Runs | `/runs/live` | [Live Runs](LIVE_RUNS.md) | Mutable live Supabase/R2 observation |
| Arms | `/arms` | [Arms](ARMS.md) | All-imported operational arm inventory |
| Artifacts | `/artifacts` | [Artifacts](ARTIFACTS.md) | Canonical artifact metadata plus retained byte/storage evidence |
| Evidence Review | `/comprehensive-review` | [Evidence Review](EVIDENCE_REVIEW.md) | Frozen manifest-validated comprehensive-review snapshot |
| Planner | `/planner` | [Planner](PLANNER.md) | Checked-in config plus read-only current promotion authority |
| Cost Coverage | `/cost-coverage` | [Cost Coverage](COST_COVERAGE.md) | Current-reviewed V4 cost plus separate historical DR-303 provenance |

## How to use these guides

For every page, answer these questions in order:

1. What question is this page designed to answer?
2. What exact source or sources feed it?
3. What population is displayed?
4. Which layer is authoritative for the claim I am making?
5. Which control changes the population versus only the presentation?
6. What inference does the page explicitly *not* support?
7. How can I trace the value back to one exact run, trial, artifact, reviewed
   snapshot, or provider-evidence chain?

When two pages disagree numerically, first assume that their populations or
authority layers differ. Do **not** average, merge, or silently substitute them.

## Authority classes used throughout the manual

### Checked-in documentation

Architecture, Data Model, and Glossary describe reviewed repository contracts.
They are not live infrastructure/schema probes.

### Frozen or current-reviewed file-backed evidence

Overview's reviewed comparison, Cross-phase, Cost Coverage, and Evidence Review
use checked-in reviewed artifacts for at least part of their decision-facing
content. Their dates, source hashes, scope, and provenance boundaries matter.

### Canonical operational database

Runs and canonical artifact/trial metadata represent published benchmark
evidence in Supabase/Postgres.

### Dynamic imported aggregate

Eval Suites, Evals, Arms, and parts of Overview/Trial Quality query current
operational imports. Their denominator can change when legitimate new imports
are added and therefore may not match a fixed reviewed cohort.

### Live state

Live Runs is mutable in-progress observation. It is intentionally non-canonical
until final publication succeeds.

### Derived interpretation

Failure taxonomy, composition, selected-cost presentation, and other derived
views explain retained evidence. They do not silently rewrite raw benchmark
rewards.

## Non-principal and compatibility routes

The 15 guides above match the 15-item `AppShell` navigation.

Other routes exist but are not separate principal manual entries:

- `/arm-runs` is a compatibility redirect to `/runs`.
- `/arm-runs/[armRunId]` remains an ID-oriented detail surface.
- `/readiness` is a contained historical planning/readiness snapshot, not live
  operational readiness.
- `/runners` explains the limits of runner-fleet inference.
- `/scaffold` and `/tasks` are support/compatibility surfaces.
- detail routes under `/runs`, `/trials`, `/evals`, `/eval-suites`,
  `/artifacts`, and `/live-artifacts` are evidence-tracing surfaces documented
  by the relevant principal-page guide.

## Cross-page evidence workflows

### Result to evidence

Overview or Cross-phase → exact Runs identity → trial evidence → Artifacts.

### Failure semantics

Trial Quality → Evidence Review → exact trial → verifier/transcript/trajectory
evidence.

### Cost semantics

Overview or Cross-phase → Cost Coverage → exact selected run → provider
evidence/reconciliation class → explicit allocation limitations.

### Promotion to execution

Durable promotion review → Planner → human-reviewed external execution → Live Runs during
supervised execution → Runs after canonical publication.

## Future-phase boundary

This manual documents the current post-Phase-3 system. It does not activate
Phase 4 or Phase 5.

`agent_harness` is already canonical arm identity and therefore provides the
planned Phase 4 comparison seam, but the promotion-gate experiment/suite scope
and harness-version contract must be reviewed before the first paid Phase 4
Canary.

Phase 5 procedure/planner-executor concepts remain future schema and methodology
work after Phase 4.
