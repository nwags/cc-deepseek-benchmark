# Dashboard Revision Specification

**Date:** 2026-08-04
**Status:** Draft v0.1 for implementation
**Target repository:** `cc-deepseek-bench`
**Target branch:** `dashboard-revision-scope-and-stale-pages`
**Primary objective:** Correct dashboard scope/provenance inconsistencies and contain stale operational pages before layout polish or new charts.

## 1. Purpose

This specification converts the manual dashboard observations into an ordered implementation plan. The first implementation pass is intentionally limited to data-scope correctness, stale operational content, and the architecture narrative. It must not become a broad visual redesign.

The dashboard currently mixes:

- the original 15-arm / 900-trial Phase 3 corpus;
- the extended 16-arm / 960-trial corpus that includes Kimi K3;
- all-imported diagnostic, smoke, canary, and legacy rows;
- static operational pages that no longer describe current infrastructure.

That makes otherwise accurate figures appear inconsistent and can make historical planning notes look like current operational state.

## 2. Source material

The specification is based on:

- `Dashboard_Observations.md`;
- the 2026-08-04 dashboard screenshots;
- `Benchmarking Coding Agents on Databricks’ Multi-Million Line Codebase`;
- `PHASE3_DATABRICKS_COMPARISON_20260713.pdf`;
- the prior interactive cost/performance HTML chart;
- the merged comprehensive evidence-review and live-supervision implementation on `main`.

## 3. Non-negotiable invariants

1. **Do not rewrite frozen benchmark history.**
   - Phase 1 remains frozen.
   - Historical Phase 2 and Phase 3 reports remain intact.
   - Existing raw rewards, trial rows, cost records, and generated review outputs are not retroactively modified merely to make dashboard totals align.

2. **Do not silently merge unlike populations.**
   - Valid full-suite rows, all-imported rows, historical snapshots, and the Kimi K3 addendum must remain distinguishable.

3. **Do not rerun migration 009.**
   - It was already applied historically.

4. **No paid benchmark runs or provider probes are required for this work.**

5. **No Supabase or R2 writes are required for the specification pass.**
   - Read-only inspection is allowed.
   - Any later data migration or publication work requires a separate reviewed plan.

6. **Canonical IDs remain stable.**
   - Stored arm IDs such as `router-glm-5.2` remain unchanged.
   - Human-friendly display labels may be added.

7. **Derived diagnoses never overwrite raw truth.**
   - Raw reward, stored quality flags, verifier evidence, execution validity, and trajectory interpretation remain separate axes.

## 4. Definitions

### 4.1 Phase 3 core

The original valid full-suite Phase 3 population:

- 15 arms
- 900 trials
- 515 successes
- adjusted known cost of $972.17 in the existing reviewed reporting layer

This remains the population used by the original Phase 3 report and the July 13 Databricks comparison.

### 4.2 Phase 3 extended

The Phase 3 core population plus the Kimi K3 addendum:

- 16 arms
- 960 trials
- 562 successes

The extended view is the preferred default for current comparative dashboard views when all required metrics exist.

### 4.3 Valid imported

All imported rows belonging to runs that remain valid, potentially including:

- full-suite runs;
- canaries;
- smoke runs;
- other valid run classes represented by a live aggregate.

This is a dynamic evidence-inventory population, not a fixed full-suite leaderboard denominator. It was added after implementation inspection showed that the Overview inventory metrics use all valid imported runs while the comparison sections use the full-suite population.

### 4.4 All imported

All imported rows for the selected entity, potentially including:

- full-suite runs;
- canaries;
- smoke runs;
- diagnostic runs;
- legacy imports;
- incomplete imports.

This is not a valid leaderboard denominator unless explicitly selected and labeled.

### 4.5 Display name versus canonical ID

Example:

- display name: `GLM 5.2`
- canonical arm ID: `router-glm-5.2`
- routing label: `LiteLLM-routed`
- provider label: `Z.AI / GLM`

Canonical IDs remain available in details, tooltips, URLs, and exports.

## 5. Priority summary

| Priority | Workstream | Outcome |
|---|---|---|
| P0 | Corpus scope model | Every major total has an explicit, consistent population |
| P0 | Scope banners and denominator disclosure | Users can tell why 15/900 and 16/960 both exist |
| P0 | Stale operational page containment | Hardcoded or historical state no longer looks live |
| P0 | Architecture correction | Current run, scoring, publication, VPS, Supabase, and R2 flow is documented |
| P1 | Navigation consolidation | Tasks/Evals, Runner Fleet, Route Readiness, and Arm Scaffold have clear homes |
| P1 | Failure taxonomy and no-op retirement | Current diagnoses replace legacy “suspected no-op” language |
| P1 | Evidence-aware deep links | Arm, run, trial, and cost links land on the relevant filtered evidence |
| P2 | Shared tooltips and terminology | Column meanings and confidence semantics are available consistently |
| P2 | Global width and overflow | Dense pages use 1920px displays effectively |
| P3 | Cost/performance and failure charts | Interactive charts build on corrected scope and taxonomy |

## 6. P0 requirements

### DR-001 — Introduce a central dashboard corpus-scope model

Create one shared scope definition used by all comparative pages.

Required scope IDs:

- `phase3-core`
- `phase3-extended`
- `valid-imported`
- `all-imported`

The shared model must include, at minimum:

- stable scope ID;
- display label;
- concise description;
- included and excluded populations;
- arm count;
- trial count;
- success count;
- cost coverage state;
- whether the scope is valid for leaderboard comparisons;
- presentation kind independent of whether the denominator is fixed or dynamic;
- provenance/source label;
- snapshot or generation date where applicable.

Implementation guidance:

- Prefer a single typed module in `apps/dashboard/src/lib/`.
- Do not duplicate hardcoded scope descriptions across pages.
- Do not infer scope solely from the presence of one arm ID.
- Scope selection must be explicit in data-loading functions.
- A page that cannot support a requested scope must say so rather than silently falling back.

Acceptance criteria:

- The same scope ID yields the same arm/trial/success counts on every page.
- Unit tests cover all four scope definitions.
- No comparative page presents an unlabeled 15-arm or 16-arm total.
- “All imported” is never presented as a valid full-suite leaderboard without a warning.

### DR-002 — Make Phase 3 core versus extended visible

Add a reusable scope banner or selector to:

- Overview;
- Cross-phase;
- Arms;
- Cost Coverage;
- Evals;
- relevant run/quality summary pages.

Implemented Commit Group B page mapping:

- Overview comparison: `phase3-extended`;
- Overview inventory: `valid-imported`;
- Cross-phase: `phase3-core`;
- Cost Coverage: `phase3-core`;
- Arms: `all-imported`;
- Evals: `valid-imported`, matching `benchmark.v_valid_eval_arm_comparison` and its exclusion of invalid/quarantined arm runs.

Required wording characteristics:

- `Phase 3 core` must identify the original 15-arm / 900-trial reviewed snapshot.
- `Phase 3 extended` must identify the 16-arm / 960-trial view including Kimi K3.
- Historical reports must retain their original population and receive a visible historical-snapshot label.
- The selected denominator must be visible near headline metrics, not hidden in a tooltip only.

Default behavior:

- Use `phase3-extended` for current comparison views when metrics are complete.
- If cost metrics for Kimi K3 are not reconciled into the same cost layer, Cost Coverage must default to `phase3-core` and visibly state why.
- Never fabricate an extended adjusted-cost total by mixing incompatible evidence.

Acceptance criteria:

- Overview cannot show 16/960 while Cross-phase silently shows 15/900 without both pages explaining the scope difference.
- Overview separates its Phase 3 extended full-suite comparison from its dynamic valid-imported evidence inventory.
- Cost Coverage explicitly states the population and whether Kimi K3 is included.
- A user can switch or navigate between core and extended views where data supports both.
- Scope survives links between pages, preferably through a stable query parameter.

### DR-003 — Preserve historical report provenance

Historical artifacts and reports must not be regenerated merely to adopt the extended corpus.

Required behavior:

- Original Phase 3 report and Databricks comparison remain labeled `Phase 3 core`.
- Kimi K3 is represented as an addendum or extended view.
- Dashboard links to historical documents must state the document’s population.
- Historical values remain byte-for-byte unchanged unless a separate correction process is approved.

Acceptance criteria:

- No frozen result file changes in this pass.
- Tests or snapshot fixtures verify that historical labels are present.
- The dashboard never describes the July 13 comparison as a 16-arm analysis.

### DR-004 — Contain the stale Runner Fleet page

The current Runner Fleet page contains a hardcoded statement about one OVH runner and is not a live operational source.

Immediate P0 action:

- Remove `Runner Fleet` from primary navigation.
- Remove the hardcoded “current state” assertion.
- Keep `/runners` reachable for old links, but render a deprecation/redirect panel pointing to Live Runs.
- The page must not claim runner count, availability, or capacity unless sourced from current data.
- Prefer a redirect only after Live Runs contains an equivalent runner-status section.

Implemented Commit Group C decision:

- `/runners` remains reachable as an explicit deprecation destination for old links rather than redirecting.
- Live Runs is linked as the execution-observation page, but it is not described as a complete fleet model: it does not establish fleet capacity, availability, queue depth, or runner heartbeat independent of executions.
- The completed Runs index is linked as the canonical completed-run evidence destination.

Future P1 target:

- Live Runs contains a compact runner-status summary with:
  - runner/slot name;
  - online, offline, idle, or busy state;
  - current workflow/run;
  - capacity;
  - last heartbeat;
  - queue depth;
  - evidence timestamp and source.

Acceptance criteria:

- No page claims “one runner is active” from a hardcoded constant.
- Primary navigation has no Runner Fleet entry.
- Old `/runners` links produce a clear, non-misleading destination.
- Tests verify the stale assertion is absent.

### DR-005 — Contain the stale Route Readiness page

The current page uses hardcoded provider and route findings that can be mistaken for current operational status.

Immediate P0 action:

- Remove `Route Readiness` from primary navigation.
- Keep `/readiness` reachable for old links.
- Replace current-state language with an explicit historical-planning-snapshot banner.
- Include a “last reviewed” date and identify that the rows are not live probes.
- Link users to Planner, Live Runs, or current runbooks for operational work.
- Do not run provider probes to refresh the page as part of this task.

Implemented Commit Group C decision:

- `/readiness` remains reachable as a historical planning snapshot, not a live status board.
- `2026-08-05` is the dashboard containment-review date; it is not a provider, route, runner, or benchmark observation date.
- The legacy route notes retain their substance, explicitly state when the original event date was not recorded, and carry no current-status badge.
- No provider, LiteLLM, Claude Code, Harbor, runner, or infrastructure probe was performed to refresh these notes.

Future P1 target:

A data-backed readiness matrix built from:

- current arm configuration;
- latest direct provider probe;
- latest LiteLLM route probe;
- latest Claude Code route probe;
- latest Harbor canary;
- latest runner/firewall doctor;
- last-checked timestamp;
- evidence link.

Acceptance criteria:

- The page cannot be read as a live status board.
- Mythos, opusplan, NVIDIA NIM, and similar historical notes are clearly historical or removed.
- No static status badge uses words such as “current,” “passed,” or “active” without a timestamp and source.

### DR-006 — Correct the Architecture page

The Architecture page must describe the merged system rather than the earlier simplified ingestion path.

Required execution/scoring flow:

1. Benchmark questions and comparison design
2. Arm/config selection
3. Local or GitHub Actions dispatch
4. Self-hosted runner / OVH VPS execution environment
5. Harbor task container
6. Claude Code agent harness
7. LiteLLM route when applicable
8. Provider/model backend
9. Held-out verifier/test execution
10. Raw reward and result creation

Required evidence/publication flow:

1. Harbor result directory and canonical trial artifacts
2. Live wrapper and progressive event/artifact capture
3. Publication eligibility and path-safety checks
4. Live metadata/events in Supabase
5. Artifact bytes in Cloudflare R2
6. Final publisher / ingestion reconciliation
7. Dashboard read path
8. Historical file-backed review snapshots where applicable

Required wording changes:

- `Sponsor questions` → `Benchmark questions`
- `Model-arm plan` → `Benchmark design and arm selection`
- Explain that verifier/tests determine correctness.
- State that no LLM judge determines the benchmark reward.
- Include the VPS/self-hosted runner role.
- Explain live versus historical ingestion paths.
- Replace public-facing `Logical mode` and `Storage mode` with:
  - `Benchmark run class`
  - `Result source/storage location`
- Keep internal field names only in tooltips or advanced glossary text.
- Remove “Sponsor-facing.”

Acceptance criteria:

- `ingest_phase3_run_metadata.py` is not presented as the sole current ingestion path.
- Supabase metadata and R2 artifact responsibilities are distinguished.
- Live and final publication paths are both represented.
- The scoring/test step is visible.
- The architecture page contains no stale runner-count assertion.

Implemented Commit Group D design:

- Benchmark execution and scoring are shown as a forward ten-stage flow ending with held-out verifier/tests and Harbor's raw reward/result evidence; no LLM judge determines the reward.
- Optional live observation and after-execution canonical publication are separate paths. Final publication remains possible when live supervision was not used.
- `scripts/publish_phase3_run.py` is identified as the workflow final publisher. It reuses manifest/ingestion functionality from `scripts/ingest_phase3_run_metadata.py`, which also remains a separate historical/operator ingestion path rather than the sole current workflow entry.
- The dashboard distinguishes Supabase live/canonical metadata and relationships from Cloudflare R2 evidence bytes and server-side dashboard reads. Historical file-backed review snapshots remain a separate frozen-provenance source.
- Public Architecture terminology now uses `Benchmark run class` and `Result source/storage location`; the internal `logical_mode` and `storage_mode` names remain compatibility glossary entries.

### DR-007 — Add a dated post-merge dashboard review record

Create a new review document rather than modifying the July 31/August 1 acceptance evidence.

Suggested path:

`docs/reviews/DASHBOARD_MANUAL_REVIEW_20260804.md`

It should include:

- source screenshots and observation file;
- confirmed issues;
- decisions made by this specification;
- open questions;
- implementation status by requirement ID;
- regression findings;
- later manual acceptance results.

Acceptance criteria:

- Existing manual-verification artifacts remain unchanged.
- The new document distinguishes observations from confirmed defects.
- Each implementation change references one or more `DR-*` requirements.

## 7. P1 requirements

### DR-101 — Retire “suspected no-op” as a primary diagnosis

Use current response-path classifications:

- `synthetic_retry_empty_completion`
- `empty_completion_after_long_api_path_wait`
- `thinking_only_empty_completion`
- `empty_completion`
- `invalid_response_path`
- `unknown`

Rules:

- “Suspected no-op” may appear only as a legacy alias or migration note.
- Do not claim the provider or LiteLLM caused the event unless retained evidence supports that attribution.
- Preserve raw reward and exception fields independently.

### DR-102 — Surface verifier failure taxonomy

Primary verifier/failure categories:

- verifier environment issue
- syntax or compile error
- dependency or import error
- wrong file or path
- timeout inside verifier
- runtime exception in solution
- test assertion failure
- missing or wrong output
- no meaningful code change
- partial solution

Secondary assertion categories:

- performance threshold failure
- numerical or data mismatch
- missing expected file or content
- behavior mismatch
- output mismatch

Requirements:

- Provide a dashboard legend and tooltips.
- Use the same enums in filters, badges, and summary counts.
- Preserve internal enum values while showing friendly labels.
- Link definitions to representative evidence.

### DR-103 — Add trajectory-disposition as a separate axis

Proposed values:

- no substantive attempt
- early abandonment
- partial implementation
- plausible but incorrect completion
- near miss: cleanup or packaging only
- near miss: one behavioral defect
- repeated unproductive iteration
- timeout after meaningful progress
- completed work with verifier/infrastructure issue
- indeterminate

Every disposition must include:

- confidence;
- evidence basis;
- artifact links;
- manual-review requirement.

### DR-104 — Consolidate Tasks and Evals

Preferred result:

- Keep `Evals` as the primary page.
- Add scope toggle:
  - valid full-suite
  - all imported
- Redirect `/tasks` to the valid-imported Evals view; a future explicit scope toggle may expose an all-imported alternative.
- Explain why counts differ by scope.

### DR-105 — Consolidate Planner and Arm Scaffold

Planner receives two modes or tabs:

- Plan benchmark run
- Draft new arm configuration

The arm helper remains read-only and emits reviewable YAML/config snippets. Writes continue through Git review.

### DR-106 — Add evidence-aware deep links

Required:

- arm names link to the relevant arm/run view;
- trial actions appear in the leftmost visible columns;
- cost values link to cost provenance filtered to the relevant arm/run/trial;
- failure counts link to filtered Evidence Review results;
- links preserve selected corpus scope.

## 8. P2 requirements

### DR-201 — Shared tooltip registry

Create one reusable column/term definition registry for:

- attempt;
- confidence;
- unresolved;
- recorded cost;
- adjusted known cost;
- accounting gap;
- routing path;
- execution validity;
- activity class;
- failure subtype;
- policy disposition;
- telemetry consistency;
- artifact completeness;
- R2 integrity.

Tooltips must be keyboard accessible and usable on touch devices.

### DR-202 — Global desktop layout and overflow

Target large displays of at least 1920×1080.

Requirements:

- wider main content region;
- wrapped table headers;
- explicit column min/max widths;
- `overflow-wrap:anywhere` for long IDs;
- sticky table headers on long tables;
- sticky identity/action column where useful;
- visible horizontal-scroll affordance;
- local section navigation on very long pages;
- bounded vertical scroll for Live Runs tool activity and event tail;
- primary action links not hidden at the far right.

### DR-203 — Friendly labels

Display friendly model/arm names prominently while retaining canonical IDs in details.

Example:

- `GLM 5.2`
- `router-glm-5.2`
- `LiteLLM-routed`
- `Z.AI / GLM`

Do not mass-rename canonical IDs.

## 9. P3 chart requirements

Charts must be implemented only after scope and cost populations are explicit.

### DR-301 — Interactive cost/performance frontier

Controls:

- arm selection;
- select all / clear;
- provider-family filters;
- Phase 3 core / extended scope;
- x-axis:
  - adjusted cost per attempt;
  - cost per clean success;
  - recorded cost per attempt.

Presentation:

- pass rate on y-axis;
- Pareto frontier recalculated from visible arms;
- color by provider;
- optional point size by failure/incomplete spend;
- confidence/accounting-gap marker;
- point click-through to arm details;
- tooltip with numerator, denominator, cost basis, confidence, gap, and unclean spend.

### DR-302 — Failure composition by arm

Stacked counts or shares for:

- verifier/task failure;
- timeout after meaningful activity;
- provider-policy refusal;
- invalid response path;
- missing required output;
- extraneous output artifacts;
- unknown/incomplete evidence.

### DR-303 — Spend decomposition by arm

Show:

- clean-success spend;
- normal-failure spend;
- exception-failure spend;
- exception with success signal;
- unresolved/accounting gap.

## 10. Recommended implementation sequence

### Commit group A — Specification only

- add this specification;
- add the dated manual-review record scaffold;
- no dashboard behavior changes.

### Commit group B — Scope foundation

- central scope model;
- scope tests;
- scope banner/selector component;
- Overview, Cross-phase, Arms, Evals, and Cost Coverage integration.

### Commit group C — Stale page containment

- remove Runner Fleet and Route Readiness from primary navigation;
- replace hardcoded current-state claims;
- add deprecation/historical banners and safe links;
- add tests.

### Commit group D — Architecture correction

- replace old diagrams and terminology;
- document scoring and publication;
- update glossary definitions;
- add content tests.

Visual polish, taxonomy expansion, deep links, and charts follow only after P0 acceptance.

## 11. P0 validation matrix

| Check | Required result |
|---|---|
| Scope unit tests | all pass |
| Overview scope | Phase 3 extended comparison and valid-imported inventory are separate |
| Cross-phase scope | Phase 3 core historical snapshot |
| Arms scope | all-imported |
| Evals scope | valid-imported; invalid/quarantined arm runs excluded |
| Cost Coverage scope | Phase 3 core population and Kimi K3 exclusion stated |
| Historical reports | unchanged |
| Runner Fleet nav | removed |
| Runner hardcoded active count | absent |
| Route Readiness nav | removed |
| Readiness historical status | explicit |
| Architecture scoring | held-out verifier/tests shown |
| Architecture infrastructure | GitHub Actions/self-hosted runner/VPS shown |
| Architecture storage | Supabase metadata versus R2 bytes distinguished |
| Migration 009 | not executed |
| Paid runs/probes | none |
| `make check` | pass |
| `make secret-scan` | pass |
| `git diff --check` | pass |

## 12. Manual acceptance checklist for P0

At 1920×1080:

1. Open Overview and identify the selected corpus within five seconds.
2. Navigate to Cross-phase and explain any 15/900 versus 16/960 difference from visible text alone.
3. Open Cost Coverage and determine whether Kimi K3 is included.
4. Confirm Runner Fleet is absent from primary navigation.
5. Visit `/runners` directly and confirm it does not claim a live runner count.
6. Confirm Route Readiness is absent from primary navigation.
7. Visit `/readiness` directly and confirm it is marked as historical/non-live.
8. Read Architecture and identify:
   - where tasks run;
   - where Claude Code runs;
   - where routing occurs;
   - how correctness is scored;
   - where metadata is stored;
   - where artifact bytes are stored;
   - how live and final publication differ.
9. Confirm no historical report or frozen result file changed.
10. Record findings in `docs/reviews/DASHBOARD_MANUAL_REVIEW_20260804.md`.

## 13. Out of scope for the first implementation pass

- New benchmark runs
- Provider probes
- Migration execution
- Supabase/R2 writes
- Historical result regeneration
- Full taxonomy reclassification
- Chart implementation
- Broad CSS redesign
- Branch deletion or history rewriting
