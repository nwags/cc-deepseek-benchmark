# Data Model page guide

## Executive summary

Data Model is the checked-in map of evidence authority and relationships. It does not query Supabase
or R2. Its seven layers separate mutable live observations, canonical benchmark identity, provider
evidence and reviewed promotion authority, derived query views, R2 bytes, reviewed snapshots, and
dashboard consumers.

## Route and implementation

- Dashboard route: `/data-model`.
- Page source: `apps/dashboard/src/app/data-model/page.tsx`.
- The semantic HTML is the accessible text equivalent of
  `docs/diagrams/DASHBOARD_DATA_MODEL_20260830.mmd`.

## Data sources

- Current checked-in database migrations and audited dashboard read relationships.
- `docs/diagrams/DASHBOARD_DATA_MODEL_20260830.mmd` is the current diagram source; the August 12
  diagram remains historical provenance.
- Provider-evidence relationships reflect Migration 011; adjusted-cost semantics remain governed by
  Migration 010.

## Population and authority

- Layer A is non-canonical live state.
- Layer B is canonical benchmark metadata and experimental identity.
- Layer C is normalized provider evidence, current reconciliations, and durable promotion authority.
- Layer D is derived/query state and is not a second benchmark truth.
- Layer E is external R2 byte storage, Layer F is checked-in reviewed provenance, and Layer G
  identifies representative consumers.

## How to read the page

- Use foreign-key statements only where the page explicitly says a direct relationship exists.
- Live trials/artifacts are reconciled during publication; do not invent per-row live-to-canonical
  foreign keys.
- Provider observations do not become selected economic or usage authority until reconciliation
  selects them.
- A promotion gate pins an exact source arm run and exact current reconciliation IDs; the
  fail-closed view derives effective advancement.

## Controls and filters

- There are no query controls. Cross-links take the reviewer to Architecture, Glossary, Live Runs,
  Runs, Planner, Artifacts, and Cross-phase.

## Caveats and non-inferences

- This route is not a live schema inspector and does not prove the currently deployed database has
  every checked-in migration.
- An R2 URI proves a stored reference, not successful byte retrieval or integrity verification.
- Phase 4 and Phase 5 fields are extension seams only. No future-phase rows or authorization are
  created by this documentation.
- The current promotion-gate unique/current slot is still arm plus target mode; experiment/suite
  scoping must be reviewed before Phase 4 activation.

## Common workflows

- Use Layer B when deciding where experimental identity belongs.
- Use Layer C when deciding whether a provider value is raw evidence, selected reconciliation
  authority, or advancement authorization.
- Use Layers E/F when distinguishing immutable evidence bytes from checked-in reviewed summaries.

## Evidence tracing

- Live execution → `live_runs` → optional canonical arm-run link after publication.
- Canonical trial → arm run / task / run → artifact metadata → R2 reference.
- Provider source → normalized usage/cost evidence → current reconciliation → promotion gate →
  fail-closed view.

## Related documentation

- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Architecture page guide](ARCHITECTURE.md).
- [Planner page guide](PLANNER.md).
- [Usage and Cost Evidence Model](../../methodology/USAGE_AND_COST_EVIDENCE_MODEL.md).
