# Dashboard Manual Review — 2026-08-04

**Repository:** `cc-deepseek-bench`
**Branch:** `dashboard-revision-scope-and-stale-pages`
**Status:** In progress
**Review type:** Post-merge manual dashboard acceptance and revision tracking

## Source material

- `Dashboard_Observations.md`
- Dashboard screenshots captured 2026-08-04
- `DASHBOARD_REVISION_SPEC_20260804.md`
- Databricks coding-agent benchmark paper
- Phase 3 Databricks comparison
- Prior interactive cost/performance chart

## Review boundaries

This record does not modify or replace:

- frozen Phase 1 results;
- historical Phase 2 results;
- the July 31 comprehensive evidence-review outputs;
- the August 1 browser acceptance record;
- the original 15-arm Phase 3 reporting snapshot.

Migration 009 must not be rerun. No paid benchmark runs, provider probes, Supabase writes, or R2 writes are required for this review.

## Confirmed issues

### Scope and provenance

- [ ] DR-001 Central dashboard corpus-scope model
- [ ] DR-002 Visible Phase 3 core versus extended scope
- [ ] DR-003 Historical report provenance preserved

### Stale operational pages

- [ ] DR-004 Runner Fleet page contained or retired safely
- [ ] DR-005 Route Readiness page contained or marked historical

### Architecture

- [ ] DR-006 Current execution, scoring, live publication, Supabase, R2, and VPS flow documented

### Review traceability

- [ ] DR-007 This record updated with implementation and acceptance results

## Observations versus confirmed defects

| ID | Observation | Status | Evidence | Resolution |
|---|---|---|---|---|
| O-001 | Overview and Cross-phase appear to use different Phase 3 populations | Confirmed | Overview 16/960; Cross-phase 15/900 | Pending |
| O-002 | Cost Coverage appears to use the earlier 15-arm accounting layer | Confirmed | $972.17 adjusted known cost | Pending |
| O-003 | Runner Fleet hardcodes current runner state | Confirmed | `/runners` page text | Pending |
| O-004 | Route Readiness contains static historical route findings | Confirmed | `/readiness` page rows | Pending |
| O-005 | Architecture omits current live publication and VPS path | Confirmed | `/architecture` page | Pending |

## Implementation log

| Date | Requirement | Change | Files | Validation | Result |
|---|---|---|---|---|---|
| 2026-08-04 | DR-007 | Created review scaffold | This file | Document review | Pending |

## P0 manual acceptance

Test at 1920×1080.

- [ ] Overview identifies selected corpus immediately.
- [ ] Cross-phase explains 15/900 versus 16/960 visibly.
- [ ] Cost Coverage states whether Kimi K3 is included.
- [ ] Runner Fleet is absent from primary navigation.
- [ ] `/runners` contains no hardcoded live runner count.
- [ ] Route Readiness is absent from primary navigation.
- [ ] `/readiness` is explicitly historical/non-live.
- [ ] Architecture shows task execution, Claude Code, routing, verifier scoring, VPS/runner, Supabase metadata, R2 bytes, and live/final publication.
- [ ] Existing historical result and manual-verification files remain unchanged.
- [ ] `make check` passes.
- [ ] `make secret-scan` passes.
- [ ] `git diff --check` passes.

## Open questions

1. Should the dashboard default globally to Phase 3 extended, or should each page choose the newest fully supported scope?
2. Should `/runners` redirect immediately, or remain as a deprecation page until Live Runs has a data-backed runner summary?
3. Should `/readiness` remain as a historical snapshot, or redirect after a data-backed readiness matrix is implemented?
4. Is Kimi K3 cost evidence sufficiently reconciled for an extended Cost Coverage view?

## Final disposition

**Status:** Pending implementation and manual acceptance.

### Blockers

- None recorded yet.

### Misleading representations

- Scope differences are not yet explicit.
- Static operational pages may be read as current state.

### Usability findings

- Deferred to the later layout and tooltip pass.

### Acceptance decision

Pending.
