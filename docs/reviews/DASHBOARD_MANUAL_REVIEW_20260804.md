# Dashboard Manual Review — 2026-08-04

**Repository:** `cc-deepseek-bench`
**Branch:** `dashboard-revision-scope-and-stale-pages`
**Status:** Second comprehensive manual visual acceptance passed 2026-08-12
**Review type:** Post-merge manual dashboard acceptance and revision tracking

## Source material

- `Dashboard_Observations.md`
- Dashboard screenshots captured 2026-08-04
- `DASHBOARD_REVISION_SPEC_20260804.md`
- Databricks coding-agent benchmark paper
- Phase 3 Databricks comparison
- Prior interactive cost/performance chart
- Manual visual review performed 2026-08-05 at approximately 1920×1080
- Second comprehensive manual visual acceptance performed 2026-08-12 at 1920px, 1440px, and 1280px widths
- `docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md`
- `docs/reports/phase3/KIMI_K3_PROVIDER_EXPORT_DUPLICATE_CHECK_20260805.md`
- `results/phase3/reporting/kimi_k3_provider_log_reconciliation_20260805.csv`

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

- [x] DR-001 Central dashboard corpus-scope model — implemented; visual acceptance passed
- [x] DR-002 Visible Phase 3 core versus extended scope — implemented; visually accepted after the reviewed extended comparison and explicit historical core alternate were added
- [x] DR-003 Historical report provenance preserved — implemented; visual acceptance passed for historical provenance

### Stale operational pages

- [x] DR-004 Runner Fleet page contained or retired safely — implemented; containment and corrected body alignment visually accepted
- [x] DR-005 Route Readiness page contained or marked historical — implemented; visual acceptance passed

### Architecture

- [x] DR-006 Current execution, scoring, live publication, Supabase, R2, and VPS flow documented — implementation expanded through Group I2 and visually accepted

### Review traceability

- [x] DR-007 This record contains both manual-review outcomes; the second comprehensive acceptance pass is recorded below as PASS

### Corrective implementation status

- [x] DR-008 Qualified Kimi K3 cost evidence integrated — implemented and visually accepted 2026-08-12
- [x] DR-009 Reviewed Phase 3 extended comparison defaulted with core alternate — implemented and visually accepted 2026-08-12
- [x] DR-012 Frozen reviewed-run identity and cost reconciliation on Overview — implemented and visually accepted 2026-08-12
- [x] DR-010 freshness/provenance is implemented across Overview, index/inventory, detail, artifact-byte, live, live-artifact, raw-download, and API health routes; visually accepted 2026-08-12
- [x] DR-011 / DR-301 interactive cost/performance frontier implementation — Groups H1/H2 complete and visually accepted 2026-08-12
- [x] DR-013 visual layout corrections — Group I1 complete and visually accepted 2026-08-12
- [x] DR-014 Architecture/Data Model expansion — Group I2 complete and visually accepted 2026-08-12
- [x] DR-015 contextual glossary links — Group I2 complete and visually accepted 2026-08-12

## Observations versus confirmed defects

| ID | Observation | Status | Evidence | Resolution |
|---|---|---|---|---|
| O-001 | Overview and Cross-phase appear to use different Phase 3 populations | Confirmed | Overview full-suite comparison 16/960; the first-pass Cross-phase implementation used 15/900. Inspection also found Overview inventory metrics use all valid imported canary, smoke, full, and other valid runs. | Group F2 defaults Cross-phase and Cost Coverage to the reviewed 16-arm extended comparison while retaining Phase 3 core as an explicit historical alternate. The corrected scope presentation passed the second visual acceptance. |
| O-002 | Cost Coverage appears to use the earlier 15-arm accounting layer | Confirmed | $972.17 adjusted known cost; sanitized Kimi K3 provider-log retained-rate reconstruction | Group F2 uses the shared reviewed layer and includes qualified Kimi K3 cost evidence by default, with pricing, allocation, and billing limitations visible. The corrected presentation passed the second visual acceptance. |
| O-003 | Runner Fleet hardcodes current runner state | Confirmed | `/runners` page text | Stale fleet-state containment passed the first visual review; the Group I1 body-alignment correction passed the second visual acceptance. |
| O-004 | Route Readiness contains static historical route findings | Confirmed | `/readiness` page rows | The 2026-08-05 visual review passed historical/non-live containment. |
| O-005 | Architecture omits current live publication and VPS path | Confirmed | `/architecture` page and source inspection of the workflow, live wrapper, final publisher, manifest/ingestion helper, live data path, and artifact reader | The structural flow passed the first visual review. The Group I2 scoring/evidence/control detail, audited Data Model reference, and final terminology containment correction passed the second visual acceptance. |
| O-006 | Evals was initially labeled all-imported | Confirmed | `getEvalRows()` reads `benchmark.v_valid_eval_arm_comparison`, whose underlying valid-only view excludes entries in `benchmark.benchmark_invalid_arm_runs`. | The valid-imported source correction remains implemented. This route was not separately assessed in the supplied 2026-08-05 visual review. |

The Implementation log below preserves the status recorded when each earlier group was completed. Those historical entries are superseded for current visual status by the dated second-pass record under “2026-08-12 second comprehensive manual visual acceptance.”

## Implementation log

| Date | Requirement | Change | Files | Validation | Result |
|---|---|---|---|---|---|
| 2026-08-04 | DR-007 | Created review scaffold | This file | Document review | Pending |
| 2026-08-04 | DR-001 | Added the immutable four-scope registry, explicit historical/current/dynamic presentation kinds, safe lookup and partial-count comparison helpers, and reusable visible scope notice. The additional `valid-imported` scope records the mixed-scope Overview discovery. | `apps/dashboard/src/lib/corpus-scopes.ts`; `apps/dashboard/src/lib/corpus-scopes.test.mjs`; `apps/dashboard/src/components/CorpusScopeNotice.tsx`; `apps/dashboard/package.json` | Dashboard Node tests; typecheck; production build | Passed; manual acceptance pending |
| 2026-08-04 | DR-002 | Separated Overview extended comparison metrics from valid-imported inventory metrics; labeled Arms all-imported and Evals valid-imported according to its valid-only source view; added warnings when supplied observed counts contradict a fixed denominator. | `apps/dashboard/src/app/page.tsx`; `apps/dashboard/src/app/arms/page.tsx`; `apps/dashboard/src/app/evals/page.tsx`; `tests/test_live_dashboard.py` | Source assertions; production build; `make check` | Passed; manual acceptance pending |
| 2026-08-04 | DR-003 | Labeled Cross-phase and Cost Coverage as the reviewed 15-arm core snapshot, stated Kimi K3 exclusion and cost limitations, and preserved historical inputs. | `apps/dashboard/src/app/cross-phase/page.tsx`; `apps/dashboard/src/app/cost-coverage/page.tsx`; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | File-backed summary observed at 15 arms / 900 trials / 515 successes / $972.1698454891979; `make secret-scan`; `git diff --check` | Passed; manual acceptance pending |
| 2026-08-05 | DR-004 | Removed Runner Fleet from primary navigation and retained `/runners` as a non-live deprecation destination linking to execution observations and completed-run evidence. | `apps/dashboard/src/components/AppShell.tsx`; `apps/dashboard/src/app/runners/page.tsx`; `tests/test_live_dashboard.py` | Dashboard tests; typecheck; production build; repository checks | Passed; manual acceptance pending |
| 2026-08-05 | DR-005 | Removed Route Readiness from primary navigation and retained `/readiness` as a dated historical planning snapshot with neutral source/date notes. | `apps/dashboard/src/components/AppShell.tsx`; `apps/dashboard/src/app/readiness/page.tsx`; `tests/test_live_dashboard.py`; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | Dashboard tests; typecheck; production build; repository checks | Passed; manual acceptance pending |
| 2026-08-05 | DR-006 | Replaced the simplified Architecture diagram with separate execution/scoring, optional live-observation, canonical-publication, and storage/read-path views; documented the workflow publisher and helper relationship; replaced public compatibility-field terminology. | `apps/dashboard/src/app/architecture/page.tsx`; `apps/dashboard/src/lib/glossary.ts`; `tests/test_live_dashboard.py`; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md`; this file | Source assertions; dashboard Node tests; typecheck; production build; repository checks | Passed; manual acceptance pending |
| 2026-08-05 | DR-007 | Recorded the first manual visual acceptance pass, its passing observations, and the corrective findings that prevent acceptance. | This file; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | Manual review at approximately 1920×1080 | Failed; corrective work and a second pass are required, so DR-007 remains pending |
| 2026-08-05 | DR-008 | Recorded sanitized provider-log token arithmetic, pricing-provenance limitations, allocation confidence, and duplicate-export provenance without retaining raw request logs. Dashboard integration remains open. | `docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md`; `docs/reports/phase3/KIMI_K3_PROVIDER_EXPORT_DUPLICATE_CHECK_20260805.md`; `results/phase3/reporting/kimi_k3_provider_log_reconciliation_20260805.csv` | Sanitized evidence review; repository validation | Evidence recorded; DR-008 implementation remains open |
| 2026-08-07 | DR-008; DR-009 — Group F1 | Added one validated, deterministic reviewed Phase 3 data layer containing immutable core and qualified extended scopes, exact source hashes, separate cost/provenance/allocation fields, and partial outcome-cost coverage semantics. | `results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json`; `apps/dashboard/src/generated/phase3-reviewed-comparison-data.ts`; `apps/dashboard/src/lib/phase3-reviewed-comparison.ts`; generator and focused tests | Focused generator/loader tests; typecheck; production build; repository checks | Passed; integration proceeded to Group F2 |
| 2026-08-08 | DR-008; DR-009 — Group F2 | Made the reviewed extended scope the default for Cross-phase and Cost Coverage, added an accessible query-parameter selector for the historical core alternate, removed the Cost Coverage split-source Supabase path, and exposed qualified Kimi cost limitations and partial outcome coverage. | `apps/dashboard/src/app/cross-phase/page.tsx`; `apps/dashboard/src/app/cost-coverage/page.tsx`; `apps/dashboard/src/components/CorpusScopeSelector.tsx`; `apps/dashboard/src/components/CorpusScopeNotice.tsx`; `apps/dashboard/src/lib/cross-phase-reporting.ts`; focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; `make check`; secret scan; diff/protected-path checks | Passed; DR-008 and DR-009 implementation is complete pending second manual visual acceptance. |
| 2026-08-09 | DR-012 — Group G1 | Added a deterministic reviewed run-selection contract containing one frozen complete valid full-suite run label for each F1 core/extended arm, with Kimi provider-log allocation limitations retained separately. | `results/phase3/reporting/phase3_reviewed_run_selection_20260809.json`; `apps/dashboard/src/generated/phase3-reviewed-run-selection-data.ts`; `apps/dashboard/src/lib/phase3-reviewed-run-selection.ts`; generator and focused tests | Focused generator/loader tests; typecheck; production build; repository checks | Passed; integration proceeded to Group G2. |
| 2026-08-10 | DR-012 — Group G2 | Replaced Overview's mutable suite/arm aggregate leaderboard and latest-20 health population with F1 reviewed facts, G1 frozen run identities, and explicit reconciliation against exact-label valid arm-run and adjusted-cost evidence. Added encoded run links, selected-run cost/source/confidence presentation, unavailable/error states, and distinct labeling for the retained dynamic heatmap and difficulty aggregates. | `apps/dashboard/src/app/page.tsx`; `apps/dashboard/src/lib/dashboard-data.ts`; `apps/dashboard/src/lib/overview-reviewed-comparison.ts`; focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; `make check`; secret scan; diff/protected-path checks | Passed; DR-012 implementation is complete pending second manual visual acceptance. |
| 2026-08-10 | DR-010 — Group G3 | Added the typed freshness/provenance contract, central Overview source registry, explicit snapshot semantics, deterministic age calculations, unavailable/unknown states, and separate Overview notices for reviewed comparison facts, reviewed run selection, exact-label stored evidence, valid-imported inventory, and dynamic suite aggregates. Canonical publication remains explicitly not recorded and no general stale threshold was invented. | `apps/dashboard/src/lib/data-freshness.ts`; `apps/dashboard/src/lib/data-freshness-sources.ts`; `apps/dashboard/src/components/DataFreshnessNotice.tsx`; Overview/data-loader integration; focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; repository checks | Freshness foundation and Overview integration implemented; remaining dynamic-route rollout pending Group G4, so DR-010 remains globally incomplete. |
| 2026-08-11 | DR-010 — Group G4a | Rolled the shared freshness contract out to the primary cloud-backed index and inventory routes with central source definitions, population-aligned `finished_at` metadata, explicit unrecorded canonical publication, and isolated secondary-metadata failure handling. Corrected Tasks to its all-imported population and Eval Suites to distinct-arm valid-only comparison semantics. | `/arms`; `/artifacts`; `/eval-suites`; `/evals`; `/runs`; `/tasks`; `/trial-quality`; `apps/dashboard/src/lib/data-freshness-sources.ts`; `apps/dashboard/src/lib/data-freshness-server.ts`; dashboard loaders and focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; repository checks | Primary index/inventory rollout implemented; detail, artifact-byte, live, and API route rollout remains pending, so DR-010 remains globally incomplete. |
| 2026-08-11 | DR-010 — Group G4b | Added exact-identity freshness/provenance to artifact, trial, run, eval-suite, and eval/task detail routes; separated Supabase metadata from bounded R2 byte evidence; exposed retrieval completeness and supportable integrity facts; and made duplicate Phase 3 run-label matches fail closed. The arm-run route remains an exact-ID compatibility redirect. | Detail routes; `apps/dashboard/src/components/ArtifactProvenanceNotice.tsx`; freshness source registry; artifact-content and dashboard-data helpers; focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; repository checks | Detail metadata and artifact-byte provenance implemented; live, live-artifact, and API rollout remains pending, so DR-010 remains globally incomplete. |
| 2026-08-11 | DR-010 — Group G4c | Completed the production-route freshness rollout for Live Runs, live-artifact metadata and bounded R2 bytes, raw live-artifact download source/failure semantics, and API health. Added a pure live-heartbeat liveness contract whose 90-second threshold is confined to live reporting, and kept explicitly enabled local NDJSON fallback separate from unavailable cloud state. | `/runs/live`; `/live-artifacts/[artifactId]`; `/live-artifacts/[artifactId]/download`; `/api/health`; live source registry and liveness notice; focused tests; specification and this record | Focused Node/Python tests; typecheck; production build; repository checks | DR-010 implementation complete pending second manual visual acceptance; no overall acceptance is claimed. |
| 2026-08-11 | DR-011; DR-301 — Group H1 | Established the reviewed chart data contract, explicit metric-availability rules, frozen G1 selected-run links, canonical presentation provider-family filters that retain raw F1 provider values, deterministic Pareto-frontier computation, select-all/clear semantics, and an accessible non-hover table/model. Kimi K3 retains its qualified retained-rate cost basis for adjusted cost per attempt while unsupported cost-per-clean-success and failure/incomplete-spend fields remain unavailable rather than zero. | `apps/dashboard/src/lib/cost-performance-chart.ts`; `apps/dashboard/src/components/CostPerformanceChartTable.tsx`; focused Node/Python tests; package test wiring; specification and this record | Focused H1 tests; full dashboard Node tests; typecheck; production build; live-dashboard source tests; `make check`; secret scan; diff/protected-path checks | Passed; DR-011/DR-301 remain open pending H2 interactive visual rendering and control integration. |
| 2026-08-12 | DR-011; DR-301 — Group H2 | Integrated one responsive interactive SVG frontier into Overview after the reviewed leaderboard and before the dynamic-population boundary. The current reviewed G2 headline/leaderboard remains extended, while the chart's explicit `chart_scope` query state independently selects reviewed extended or historical core arms. Added a client-safe H1 view module, native chart-scope/metric/provider/arm controls, stable normalized-provider colors, H1-frontier rendering, fixed point sizing, categorical qualification/gap rings, focusable points with persistent evidence details, explicit empty/unavailable states, and the visible H1 evidence table. Kimi K3 remains plotted only where H1 permits and its retained-rate, provenance, allocation, exclusivity, billing, and accounting-gap qualifications remain prominent. | `apps/dashboard/src/components/CostPerformanceChart.tsx`; `apps/dashboard/src/lib/cost-performance-chart-view.ts`; `apps/dashboard/src/lib/cost-performance-chart-geometry.ts`; Overview and scoped CSS integration; focused Node/Python tests; package test wiring; specification and this record | Focused H1/H2 tests; full dashboard Node tests; typecheck; production build; live-dashboard source tests; repository and protected-path checks | Implementation complete; second manual visual acceptance pending. Review axes, clipping, provider colors, frontier readability, Kimi qualification visibility, controls, keyboard focus, the non-hover table, Overview height, and narrow viewport behavior. |
| 2026-08-12 | DR-013 — Group I1 | Corrected the bounded layout defects from the first visual pass: canonical heatmap headers now wrap without truncation; Cross-phase source-backed phase summaries use structured cards; decorative secondary ARM identity values are omitted when empty, duplicated, or an em dash while evidence-level unavailable values remain explicit; Runner Fleet body content aligns to its retained deprecation panel; and shared table containment exposes horizontal overflow with wrapping headers, long IDs, and targeted right-edge evidence cells. No reviewed facts, loaders, H1/H2 quantitative logic, or chart interactions changed. | `apps/dashboard/src/components/SuiteHeatmap.tsx`; Cross-phase, Cost Coverage, Runner Fleet, Overview, and Trial Quality presentation markup; scoped/shared dashboard CSS; focused source tests; specification and this record | Focused DR-013/H1/H2 tests followed by the full dashboard and repository validation suite | Implementation complete; second manual visual acceptance pending. Review heatmap header readability, phase-card coherence, secondary ARM identity lines, Runner Fleet alignment, reachable table edges, absence of page-wide horizontal scroll, 1920px/1440px/1280px usability, and the unaffected H2 chart. |
| 2026-08-12 | DR-014; DR-015 — Group I2 | Preserved the existing four-part Architecture foundation while adding a plain-language held-out verifier explanation, concrete retained Harbor evidence types, audited live/publication switch behavior and defaults, and prominent final-publisher responsibilities. Added a no-query Data Model route with six explicit source layers, audited live/canonical relationships, the sole direct live-to-canonical FK, external R2 storage references, reviewed snapshots, representative consumers, a checked-in Mermaid source, and complete semantic HTML/text fallback. Extended the authoritative typed glossary registry with static internal related links; rendered full link sets on Glossary and a primary contextual link in the existing portal-backed `TermInfo` popover while retaining internal compatibility terminology. | `/architecture`; `/data-model`; `docs/diagrams/DASHBOARD_DATA_MODEL_20260812.mmd`; Glossary registry/page/popover; AppShell navigation; scoped responsive CSS; focused source tests; specification and this record | Focused DR-014/DR-015 plus DR-013/H1/H2 regression tests followed by the full dashboard and repository validation suite | Implementation complete; second manual visual acceptance pending. Review Architecture comprehension/evidence/control/publisher hierarchy and clipping; Data Model layer/direct-versus-reconciliation/R2 boundaries and 1920px/1440px/1280px readability; contextual-link meaning and TermInfo keyboard/touch behavior; and secondary compatibility terminology. |
| 2026-08-12 | DR-007; DR-008–DR-015; DR-301 — second manual acceptance | Recorded the comprehensive responsive and interactive acceptance pass, the two corrected presentation findings, and the transient local database incident followed by a successful production recapture. | This file; `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md` | Manual review at 1920px, 1440px, and 1280px; targeted production recapture; final containment-fix checks | Passed; DR-007 and the implementation-complete corrective requirements covered by this pass are accepted. |

Commit Group C used source inspection only. No provider, LiteLLM, Claude Code, Harbor, router, runner, or infrastructure probes were run, and no external operational service was queried.

Commit Group D used source inspection of `.github/workflows/phase3-arm-dispatch-v2.yml`, `scripts/run_arm_live.py`, `scripts/publish_phase3_run.py`, `scripts/ingest_phase3_run_metadata.py`, `docs/runbooks/LIVE_RUN_SUPERVISION.md`, `apps/dashboard/src/app/runs/live/page.tsx`, `apps/dashboard/src/lib/live-data.ts`, and `apps/dashboard/src/lib/artifact-content.ts`. No workflow, script, runbook, migration, result, or operational implementation file was changed. No probe, benchmark job, migration, external query, Supabase write, or R2 write was performed.

Validation summary for Commit Group D:

- dashboard run-plan Node test: passed;
- dashboard analysis/registry Node test command: passed;
- targeted dashboard source tests: 23 passed;
- dashboard TypeScript typecheck: passed;
- dashboard production build: passed;
- `make check`: passed;
- `make secret-scan`: passed;
- `git diff --check`: passed;
- `apps/dashboard/next-env.d.ts`: unchanged.

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

## Kimi K3 provider-log retained-rate reconstruction

The sanitized provider-log review reached these conclusions without changing the historical Kimi K3 addendum:

| Measure | Reviewed value |
|---|---:|
| Provider-log requests | 1,273 |
| Duplicate request IDs | 0 |
| Provider-log input tokens | 39,996,874 |
| Cached tokens | 38,341,888 |
| Uncached input tokens | 1,654,986 |
| Output tokens | 956,453 |
| Provider-log retained-rate reconstruction | $30.814319 |
| Recorded trial cost | $25.207213 |
| Known accounting gap | $5.607106 |
| Reviewed Phase 3 core adjusted cost | $972.169845 |
| Reviewed Phase 3 extended qualified adjusted-cost estimate | $1,002.984165 |
| Extended corpus | 16 arms / 960 trials / 562 successes |
| Pricing provenance | Retained 2026-07-22 repository rate constants; no retained official provider page or dated pricing snapshot |
| Retained-rate arithmetic status | Verified under retained rates; pricing-source provenance incomplete |
| Arm-run/provider-log allocation confidence | Low |
| Trial-level allocation status | Unresolved |

Cached input is a subset of `Input Tokens`; the prior interpretation that added both fields as independent input totals double-counted cached input and is retired. This resolves the token-field arithmetic under the retained rates, but it does not make the result fully pricing-provenance-complete. The incomplete pricing provenance and low arm-run allocation confidence qualify the estimate; they do not justify omitting Kimi K3 from the reviewed extended comparison.

The provider timestamps have no retained timezone, so direct alignment with the canonical full-run interval is not proven. Retained same-day Kimi K3 canary and smoke outputs and the absence of a request-to-run join mean the evidence does not prove that unrelated Kimi K3 requests were absent. This is not invoice-level reconciliation because the request export contains no charged-dollar, tax, credit, or fee-adjustment field. Exact trial-level allocation would require joining request timestamps or IDs to retained trial evidence. The two uploaded exports were byte-for-byte identical, so the second added no new usage evidence. Raw request logs remain outside version control because they contain sensitive request, project, and API-key identifiers.

## 2026-08-05 manual visual acceptance

The review was performed at approximately 1920×1080.

**Outcome:** Failed pending corrective work. No regression requiring rollback of Commit Groups B–D was found.

### Requirement-level visual status

| Requirement | Implementation | Visual status |
|---|---|---|
| DR-001 | Implemented | Passed |
| DR-002 | Implemented | Partial: visible scope separation passed; current extended Cross-phase and Cost Coverage follow-up remains |
| DR-003 | Implemented | Passed for historical provenance |
| DR-004 | Implemented | Partial: stale claims are contained; body alignment needs correction |
| DR-005 | Implemented | Passed |
| DR-006 | Implemented | Partial: core flows are clear; explanatory and data-model expansion remains |
| DR-007 | Pending | A second acceptance pass must be recorded after corrective work |

### Passing observations

#### Overview

- The extended comparison and valid-imported inventory were visibly distinct.
- Corpus notices were readable and did not overlap.

#### Cross-phase

- Historical Phase 3 core labeling was clear.
- The 15-arm / 900-trial provenance did not appear current.

#### Runner Fleet

- Runner Fleet was absent from primary navigation.
- Deprecated/non-live labeling was clear.
- No hardcoded fleet-count or capacity claim remained.

#### Route Readiness

- Route Readiness was absent from primary navigation.
- The page was clearly historical/non-live.
- 2026-08-05 was presented as the containment-review date.

#### Architecture

- Execution/scoring, optional live observation, canonical publication, and storage/read paths were visually distinct.
- Arrows and descriptions did not overlap.
- Verifier authority and the no-LLM-judge wording were prominent.
- Local versus GitHub Actions topology was understandable.
- Supabase metadata and R2 bytes were distinct.
- Live supervision did not appear mandatory.

#### Glossary

- New public terms were present.
- Internal compatibility terms were appropriately labeled.
- Architecture tooltips stayed within the viewport and were keyboard accessible.

### Failed or incomplete observations

#### Overview

- Leaderboard ARM values are not linked to the canonical selected run.
- The public label should distinguish an arm from the selected arm run.
- Heatmap headers need two-line wrapping.
- Full arm-run health shows recorded cost but not adjusted known cost.
- The dynamic inventory has no visible freshness or canonical-publication timestamp.
- The requested interactive cost/performance chart remains missing.

Group H2 now addresses this first-pass implementation finding. It is not visually accepted by this dated record; the second pass must inspect axis legibility, point clipping, provider-color distinction, frontier readability, Kimi qualification prominence, native control behavior, visible keyboard focus, non-hover table usability, overall Overview height/clutter, and narrow-viewport behavior.

#### Cross-phase

- The current default excludes Kimi K3.
- Historical provenance must be retained, but it cannot substitute for a current reviewed 16-arm comparison.
- Phase-summary cards have poor line structure and spacing.

#### Cost Coverage

- The current default excludes Kimi K3.
- Taxonomy language focuses on a prior dashboard undercount rather than current accounting meaning.
- The second ARM-line placeholder renders “—” for every row and should be populated or omitted.

Group F2 addresses the dated Cross-phase and Cost Coverage default-scope, Kimi inclusion, and cost-taxonomy findings above. These remain recorded as first-pass observations until the revised pages complete the second manual visual acceptance pass.

#### Runner Fleet

- Body links and text are not aligned with the surrounding panel content.

Group I1 now addresses the dated DR-013 layout findings across Overview heatmaps and dense evidence tables, Cross-phase phase summaries, Cost Coverage secondary ARM identity, and Runner Fleet panel alignment. This source/test implementation is not visually accepted by this dated record; the second pass must confirm readable wrapped headers, coherent phase cards, no meaningless secondary ARM dashes, aligned Runner Fleet content, reachable rightmost table content without page-wide horizontal scrolling, usability at 1920px, 1440px, and 1280px, and no H2 chart regression.

#### Architecture

- Held-out verifier/tests need a plain-language explanation.
- Optional live supervision needs a more concrete explanation.
- “Harbor output” must name actual result and artifact evidence.
- “The publisher” must identify `scripts/publish_phase3_run.py`.
- A dedicated Data Model page and a more complete checked-in diagram are needed.

#### Glossary

- Relevant dashboard navigation links should be available for suitable terms.

### Freshness rule

Dynamic pages must expose their data source, latest included evidence, canonical-publication freshness, render/query time, and stale-data state. No dashboard element should silently become stale.

## 2026-08-12 second comprehensive manual visual acceptance

The second pass reviewed the relevant dashboard surfaces at 1920px, 1440px, and 1280px widths. It included Overview, Architecture, Data Model, Glossary, Cross-phase, Cost Coverage, Runner Fleet/deprecation treatment, Trial Quality, and the other rendered surfaces in the acceptance scope.

**Outcome:** PASS.

### Requirement-level disposition

| Requirement | Final disposition |
|---|---|
| DR-007 | Accepted; this record now includes the failed first pass, completed corrective work, and passing second pass |
| DR-008 / DR-009 | Implemented and visually accepted |
| DR-010 | Implemented through G3/G4a/G4b/G4c and visually accepted |
| DR-011 / DR-301 | Implemented through H1/H2 and visually accepted |
| DR-012 | Implemented through G1/G2 and visually accepted |
| DR-013 | Implemented through I1 and visually accepted |
| DR-014 / DR-015 | Implemented through I2 and visually accepted |

### Responsive and interactive evidence

- The initial comprehensive screenshots covered the three reviewed widths. The final Architecture recapture confirmed four contained terminology cards in one row at 1920px and 1440px, and three cards plus Recorded cost on a second row at 1280px.
- Overview chart controls, point details/tooltips, and evidence deep links passed. Trial Quality dense-content and responsive behavior passed.
- `TermInfo` passed mouse opening, keyboard opening and focus, focus transfer into the popover without premature closure, Escape closure, contextual and Glossary destinations, and viewport-aware placement.
- Cross-phase, Cost Coverage, Data Model, Glossary, Runner Fleet/deprecation treatment, and the other reviewed surfaces were accepted at the reviewed widths.

### Findings corrected during acceptance

1. Overview initially emitted a React warning because an SVG `<title>` received two child values. `CostPerformanceChart` was changed to supply one computed string child, and a focused regression test was added. The correction did not change chart facts, controls, accessibility semantics, or reviewed scope/cost policy.
2. The initial local capture returned tenant/user connection failures for `/trial-quality`, `/arms`, `/evals`, `/runs`, and `/artifacts`. `apps/dashboard/.env.local` and `.secrets/supabase.env` supplied the same sanitized `SUPABASE_DB_URL` fingerprint, and each source subsequently passed an independent read-only `SELECT 1`. A production-build targeted recapture returned HTTP 200 for `/`, `/trial-quality`, `/arms`, `/evals`, `/runs`, and `/artifacts` in three consecutive rounds (18/18 requests), with no server warning/error output. The incident is classified as transient local acceptance-environment behavior, not an application/query defect; no fallback, secret, query, or database semantic change was made.
3. The final Architecture review found that the long Result source/storage location term and its information trigger crowded the adjacent card. Scoped wrapping and shrink containment corrected the layout while retaining the accepted `TermInfo` interaction and accessibility behavior. The final three-width recapture showed every terminology label and trigger contained and readable.

### Acceptance boundary

No benchmark rerun, paid provider probe, migration 009 execution, Supabase write, or R2 write was performed. The pass did not regenerate reviewed artifacts or alter historical benchmark evidence.

## Open questions

1. Commit Group F2 decision: Overview, Cross-phase, and Cost Coverage default to the reviewed Phase 3 extended comparison; Cross-phase and Cost Coverage expose Phase 3 core as a historical alternate. Overview inventory and Evals use valid-imported, and Arms uses all-imported.
2. Commit Group C decision: `/runners` remains a deprecation page because Live Runs exposes execution observations rather than a complete fleet model.
3. Commit Group C decision: `/readiness` remains a historical planning snapshot until a separately reviewed data-backed readiness model exists.
4. Kimi K3 token arithmetic is reconciled under the retained rates and integrated as qualified evidence in the reviewed extended comparison. Official pricing-source provenance, invoice-level reconciliation, arm-run exclusivity, and exact trial-level allocation remain incomplete and visibly qualified.

## Final disposition

**Status:** PASS — second comprehensive manual visual acceptance completed 2026-08-12.

### Blockers

- No blocker remains within the corrective second-pass scope.
- DR-007 is accepted. DR-008 through DR-015, including the joint DR-011/DR-301 chart requirement, are implemented and accepted.
- Later DR-101 through DR-203 and DR-302/DR-303 work remains outside this corrective acceptance disposition where not otherwise implemented; it does not block this PASS.

### Misleading representations

- No regression requiring rollback of Commit Groups B–D was found.
- Cross-phase and Cost Coverage default to the reviewed extended comparison, retain the historical core alternate, and passed second-pass visual acceptance.
- Overview distinguishes reviewed snapshot provenance from operational populations; index/inventory and detail routes disclose population-specific execution freshness; artifact routes distinguish database metadata from bounded R2 evidence; and Live Runs keeps cloud state, heartbeat liveness, and local fallback separate. API health names its ordinary database source without borrowing the live threshold.
- Charting, bounded layout corrections, Architecture/Data Model expansion, and contextual glossary links are implementation-complete and visually accepted.

### Usability findings

- Recorded above and mapped to DR-011 through DR-015; all passed at 1920px, 1440px, and 1280px.

### Acceptance decision

Passed. DR-007 is complete, and DR-008 through DR-015, including DR-011/DR-301, are accepted. The transient local database incident was cleared by the successful production recapture and did not require a product change.
