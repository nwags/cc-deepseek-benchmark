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

- [x] DR-001 Central dashboard corpus-scope model — implemented; manual acceptance pending
- [x] DR-002 Visible Phase 3 core versus extended scope — implemented; manual acceptance pending
- [x] DR-003 Historical report provenance preserved — implemented; manual acceptance pending

### Stale operational pages

- [x] DR-004 Runner Fleet page contained or retired safely — implemented; manual acceptance pending
- [x] DR-005 Route Readiness page contained or marked historical — implemented; manual acceptance pending

### Architecture

- [ ] DR-006 Current execution, scoring, live publication, Supabase, R2, and VPS flow documented

### Review traceability

- [ ] DR-007 This record updated with implementation and acceptance results

## Observations versus confirmed defects

| ID | Observation | Status | Evidence | Resolution |
|---|---|---|---|---|
| O-001 | Overview and Cross-phase appear to use different Phase 3 populations | Confirmed | Overview full-suite comparison 16/960; Cross-phase 15/900. Inspection also found Overview inventory metrics use all valid imported canary, smoke, full, and other valid runs. | Implemented pending manual acceptance: extended, core, and valid-imported scopes are now distinct and visible. |
| O-002 | Cost Coverage appears to use the earlier 15-arm accounting layer | Confirmed | $972.17 adjusted known cost | Implemented pending manual acceptance: labeled as the historical Phase 3 core layer with Kimi K3 excluded. |
| O-003 | Runner Fleet hardcodes current runner state | Confirmed | `/runners` page text | Implemented pending manual acceptance: the hardcoded claim is removed and the retained route is an explicit non-live deprecation destination. |
| O-004 | Route Readiness contains static historical route findings | Confirmed | `/readiness` page rows | Implemented pending manual acceptance: the route is a dated historical planning snapshot with neutral notes and no current-status badges. |
| O-005 | Architecture omits current live publication and VPS path | Confirmed | `/architecture` page | Pending |
| O-006 | Evals was initially labeled all-imported | Confirmed | `getEvalRows()` reads `benchmark.v_valid_eval_arm_comparison`, whose underlying valid-only view excludes entries in `benchmark.benchmark_invalid_arm_runs`. | Corrected to valid-imported; implementation remains pending manual acceptance. |

## Implementation log

| Date | Requirement | Change | Files | Validation | Result |
|---|---|---|---|---|---|
| 2026-08-04 | DR-007 | Created review scaffold | This file | Document review | Pending |
| 2026-08-04 | DR-001 | Added the immutable four-scope registry, explicit historical/current/dynamic presentation kinds, safe lookup and partial-count comparison helpers, and reusable visible scope notice. The additional `valid-imported` scope records the mixed-scope Overview discovery. | `apps/dashboard/src/lib/corpus-scopes.ts`; `apps/dashboard/src/lib/corpus-scopes.test.mjs`; `apps/dashboard/src/components/CorpusScopeNotice.tsx`; `apps/dashboard/package.json` | Dashboard Node tests; typecheck; production build | Passed; manual acceptance pending |
| 2026-08-04 | DR-002 | Separated Overview extended comparison metrics from valid-imported inventory metrics; labeled Arms all-imported and Evals valid-imported according to its valid-only source view; added warnings when supplied observed counts contradict a fixed denominator. | `apps/dashboard/src/app/page.tsx`; `apps/dashboard/src/app/arms/page.tsx`; `apps/dashboard/src/app/evals/page.tsx`; `tests/test_live_dashboard.py` | Source assertions; production build; `make check` | Passed; manual acceptance pending |
| 2026-08-04 | DR-003 | Labeled Cross-phase and Cost Coverage as the reviewed 15-arm core snapshot, stated Kimi K3 exclusion and cost limitations, and preserved historical inputs. | `apps/dashboard/src/app/cross-phase/page.tsx`; `apps/dashboard/src/app/cost-coverage/page.tsx`; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | File-backed summary observed at 15 arms / 900 trials / 515 successes / $972.1698454891979; `make secret-scan`; `git diff --check` | Passed; manual acceptance pending |
| 2026-08-05 | DR-004 | Removed Runner Fleet from primary navigation and retained `/runners` as a non-live deprecation destination linking to execution observations and completed-run evidence. | `apps/dashboard/src/components/AppShell.tsx`; `apps/dashboard/src/app/runners/page.tsx`; `tests/test_live_dashboard.py` | Dashboard tests; typecheck; production build; repository checks | Passed; manual acceptance pending |
| 2026-08-05 | DR-005 | Removed Route Readiness from primary navigation and retained `/readiness` as a dated historical planning snapshot with neutral source/date notes. | `apps/dashboard/src/components/AppShell.tsx`; `apps/dashboard/src/app/readiness/page.tsx`; `tests/test_live_dashboard.py`; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | Dashboard tests; typecheck; production build; repository checks | Passed; manual acceptance pending |

Commit Group C used source inspection only. No provider, LiteLLM, Claude Code, Harbor, router, runner, or infrastructure probes were run, and no external operational service was queried.

Validation summary for Commit Group C:

- dashboard run-plan Node test: 1 passed;
- dashboard analysis/registry Node test command: 5 test files passed;
- targeted dashboard source tests: 21 passed;
- dashboard TypeScript typecheck: passed;
- dashboard production build: passed with `/runners` and `/readiness` retained;
- `make check`: passed, including 71 Node subtests, 295 Python tests, and the strict generated-output scan;
- `make secret-scan`: passed;
- `git diff --check`: passed;
- `apps/dashboard/next-env.d.ts`: unchanged.

Validation summary for Commit Group B:

- dashboard run-plan Node test: 1 passed;
- dashboard analysis/registry Node test command: 5 test files passed;
- dashboard TypeScript typecheck: passed;
- dashboard production build: passed;
- `make check`: passed, including 71 Node subtests, 292 Python tests, and the strict generated-output scan;
- `make secret-scan`: passed;
- `git diff --check`: passed;
- `apps/dashboard/next-env.d.ts`: unchanged.

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

1. Commit Group B decision: each page identifies the population its existing data supports. Overview comparison uses Phase 3 extended, Overview inventory and Evals use valid-imported, Cross-phase and Cost Coverage retain Phase 3 core, and Arms uses all-imported.
2. Commit Group C decision: `/runners` remains a deprecation page because Live Runs exposes execution observations rather than a complete fleet model.
3. Commit Group C decision: `/readiness` remains a historical planning snapshot until a separately reviewed data-backed readiness model exists.
4. Is Kimi K3 cost evidence sufficiently reconciled for an extended Cost Coverage view? Until resolved, no extended adjusted-cost total is shown.

## Final disposition

**Status:** Pending implementation and manual acceptance.

### Blockers

- None recorded yet.

### Misleading representations

- Scope differences are explicit in the implementation; manual visual acceptance remains pending.
- The two static operational pages are contained in the implementation; manual visual acceptance remains pending.

### Usability findings

- Deferred to the later layout and tooltip pass.

### Acceptance decision

Pending.
