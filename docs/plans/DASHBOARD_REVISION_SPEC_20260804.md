# Dashboard Revision Specification

**Date:** 2026-08-04
**Status:** P2 completion accepted 2026-08-19; DR-302 and DR-303 remain later P3 requirements
**Target repository:** `cc-deepseek-bench`
**Target branch:** `dashboard-revision-scope-and-stale-pages`
**P2 closeout branch:** `dashboard-p2-completion`
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
| P0 | Kimi cost integration and current extended comparison | Reviewed cost evidence and the 16-arm corpus become the current comparison inputs |
| P0 | Dashboard freshness contracts (`DR-010`) | Dynamic pages disclose source, included evidence, publication freshness, render time, age, and stale state |
| P0 | Interactive cost/performance chart (`DR-011` / `DR-301`) | The requested accessible chart is complete before the second manual acceptance pass |
| P0 | Overview selected-run and cost contracts (`DR-012`) | The frozen reviewed run and recorded-versus-reviewed cost evidence are explicit, linked, and reconciled against exact-label stored evidence |
| P1 | Navigation consolidation | Tasks/Evals, Runner Fleet, Route Readiness, and Arm Scaffold have clear homes |
| P1 | Failure taxonomy and no-op retirement | Current diagnoses replace legacy “suspected no-op” language |
| P1 | Evidence-aware deep links | Arm, run, trial, and cost links land on the relevant filtered evidence |
| P2 | Shared tooltips and terminology | Column meanings and confidence semantics are available consistently |
| P2 | Global width and overflow | Dense pages use 1920px displays effectively |
| P3 | Additional failure and spend charts | Later composition views build on corrected scope and taxonomy |

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

**Acceptance status:** Passed 2026-08-12. The dated review record now preserves the failed first pass and the successful comprehensive second pass.

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

## 6A. Corrective requirements confirmed by the 2026-08-05 manual review

These requirements record the corrective work required by the failed 2026-08-05 review. DR-008 and DR-009 were implemented through Commit Groups F1/F2, DR-012 through Commit Groups G1/G2, DR-010 through Groups G3/G4a/G4b/G4c, DR-011/DR-301 through Groups H1/H2, DR-013 through Group I1, and DR-014/DR-015 through Group I2. The comprehensive second manual visual acceptance passed on 2026-08-12.

### DR-008 — Reconcile and integrate Kimi K3 cost evidence

**Priority:** P0

**Implementation status:** Implemented in Commit Groups F1/F2; visually accepted 2026-08-12.

Required outcome:

- Retain the historical 15-arm Phase 3 core.
- Include the Kimi K3 retained-rate reconstruction of $30.814319 as a qualified retained-rate estimate rather than omitting the arm.
- Publish the Phase 3 extended qualified adjusted-cost estimate of $1,002.984165.
- Preserve the recorded trial cost of $25.207213 separately from the adjusted estimate.
- Preserve the accounting gap of $5.607106 separately from both cost measures.
- Display low arm-run/provider-log allocation confidence, unresolved trial-level allocation, and incomplete pricing-source provenance.
- State that the estimate is not invoice-level or provider-billed spend and is not proven to be attributable only to the selected full run.
- Preserve retained-rate arithmetic status, arm-run/provider-log allocation confidence, and trial-level allocation status separately.
- Retain an official provider pricing page or dated provider pricing snapshot for full pricing-source provenance; its current absence does not block qualified dashboard inclusion.
- Do not commit raw provider logs.

### DR-009 — Make Phase 3 extended the current reviewed comparison

**Priority:** P0

**Implementation status:** Implemented in Commit Groups F1/F2; visually accepted 2026-08-12.

Required outcome:

- Cross-phase and Cost Coverage default to the reviewed 16-arm extended corpus.
- Phase 3 core remains available as an explicit historical snapshot.
- No historical source file is overwritten.
- Selection may use a visible toggle, tabs, or a stable query parameter.
- Kimi K3 is not omitted merely because the core snapshot predates it.

### DR-010 — Add dashboard freshness contracts

**Priority:** P0

**Implementation status:** Implemented through Groups G3/G4a/G4b/G4c; visually accepted 2026-08-12.

Every dynamic Supabase-backed page must expose:

- source or view name;
- latest included run completion;
- latest canonical publication time;
- query or render timestamp;
- data age;
- warning state for stale or publication-lagged data.

Do not label data “live” without these qualifications.

Group G3 establishes the shared contract without inventing a repository-wide age threshold or canonical-publication timestamp. Overview now presents the F1 and G1 reviewed layers as dated snapshots rather than live inventory, and presents separate operational notices for exact selected-run evidence, valid-imported inventory, and dynamic heatmap/difficulty aggregates. Ordinary imported data remains `unknown` when no staleness threshold is configured; failed reads remain `unavailable`; and canonical publication is explicitly `not_recorded` because the current schema has no authoritative field.

Group G4a applies that contract to `/arms`, `/artifacts`, `/eval-suites`, `/evals`, `/runs`, `/tasks`, and `/trial-quality`. Each notice names the page's actual operational relations and population, derives latest included execution from `finished_at` for that same population, keeps canonical publication explicitly unrecorded, and leaves the ordinary staleness threshold unconfigured. A failed secondary freshness-metadata read does not hide otherwise available page data.

Group G4b applies exact-identity metadata provenance to artifact, trial, run, eval-suite, and eval/task detail pages. It separates Supabase metadata from bounded Cloudflare R2 byte retrieval, exposes complete/partial/unavailable and verified/mismatch/not-checked evidence without treating an R2 URI as verification, and fails closed when a Phase 3 run label matches multiple storage modes. `/arm-runs/[armRunId]` remains an exact-ID compatibility redirect; the destination run page retains the ambiguity guard. Canonical publication remains unrecorded and the ordinary stale threshold remains unconfigured.

Group G4c completes the production-route rollout. `/runs/live` names the exact live Supabase relations, keeps failed cloud reads unavailable when an explicitly enabled local NDJSON fallback is shown, and applies the existing 90-second threshold only to live heartbeat liveness. `/live-artifacts/[artifactId]` separates exact live metadata from R2-first bounded byte provenance and labels `uploaded_at` only as artifact upload time. Its raw download route remains an exact-metadata, fail-closed, unredacted R2 response with no local fallback. `/api/health` reports its actual `benchmark.v_dashboard_runs` source and ordinary threshold-unconfigured freshness without borrowing live heartbeat policy. The route inventory found no remaining production cloud route without source/freshness semantics; reviewed, historical, configuration, static, redirect, raw download, and development routes retain their appropriate non-operational contracts.

### DR-011 — Restore the requested interactive cost/performance chart

**Priority:** P0 — prerequisite for the second manual acceptance pass

**Implementation status:** Groups H1/H2 implementation complete and visually accepted 2026-08-12.

DR-301 is the detailed interaction and presentation specification for this requirement; DR-011 and DR-301 describe one chart, not two duplicate chart requirements.

Group H1 established the reviewed chart data contract, metric-availability rules, frozen selected-run links, canonical presentation provider-family filters that retain raw F1 provider values, deterministic Pareto-frontier computation, and accessible non-hover table/model. It uses F1 reviewed facts for quantitative values and G1 only for frozen run identity. It preserves Kimi K3's qualified retained-rate basis for the adjusted-cost-per-attempt comparison while leaving its F1-null cost-per-clean-success and outcome-spend values unavailable.

Group H2 renders that contract as the single responsive Overview SVG frontier. The surrounding G2 Overview headline and leaderboard remain the current reviewed Phase 3 extended comparison. The chart has its own explicit reviewed scope control, persisted as `chart_scope=phase3-extended` or `chart_scope=phase3-core`, so selecting historical core does not imply a page-wide scope change. Native chart-scope, metric, provider-family, and arm controls retain independent selection semantics; the client-safe view module delegates plotted eligibility and frontier membership to the single H1 implementation without importing the reviewed F1/G1 construction layer into the browser. Provider-family color, a categorical qualification/accounting-gap ring, focusable points, Enter/Space activation, a persistent evidence inspector, explicit empty/unavailable states, and the committed visible evidence table provide the required non-hover material facts and frozen arm/run links. Point size remains fixed, so no unavailable failure/incomplete-spend evidence is presented as zero. The second pass accepted the chart's controls, interactions, tooltip/deep links, accessible non-hover evidence, responsive presentation, and corrected single-string SVG title.

Required outcome:

- Use the reviewed extended corpus by default.
- Support cost-versus-quality comparison.
- Expose the selected cost measure, cost basis, confidence, and accounting gap.
- Link chart points to arm and selected-run evidence.
- Preserve accessibility without requiring pointer hover.
- Satisfy the detailed controls, presentation, and accessible-equivalent requirements in DR-301.

### DR-012 — Correct Overview run identity and cost presentation

**Priority:** P0

**Implementation status:** Implemented in Commit Groups G1/G2; visually accepted 2026-08-12.

Required outcome:

- Identify the frozen selected reviewed arm run, not just the arm, without implying a database canonical-run flag.
- Link rows to run detail.
- Disclose the reviewed run-selection rule and its frozen 2026-08-09 labels.
- Resolve current stored evidence only for those exact run labels; never substitute a newer run.
- Show recorded cost and the applicable reviewed cost basis: adjusted known cost for core arms or the qualified retained-rate estimate for Kimi K3.
- Show missing-cost count, unresolved-cost count, accounting gap, source, confidence, and reconciliation state.
- Keep missing, duplicate, wrong-arm, wrong-suite, count, and cost reconciliation states explicit.
- Preserve Kimi K3 pricing-provenance, provider-log exclusivity, allocation-confidence, trial-allocation, and non-invoice/provider-billed qualifications.

### DR-013 — Correct visual layout defects

**Priority:** P1

**Implementation status:** Implemented in Group I1 and visually accepted 2026-08-12.

Required outcome:

- Wrap heatmap headers.
- Use structured phase-summary cards.
- Remove meaningless “—” secondary ARM values.
- Align Runner Fleet body content.
- Verify table overflow and right-edge readability.
- Preserve a usable layout at 1920×1080 and narrower desktop widths.

Group I1 retains the existing visual language while allowing canonical heatmap headers to wrap without truncation, converting the Cross-phase summaries into structured source-backed cards, and omitting only empty or em-dash secondary ARM identity labels. Runner Fleet retains its non-live deprecation semantics with body content aligned to the panel geometry. Shared table containment provides explicit horizontal scrolling, wrapping headers and long identifiers, and targeted wrapping for dense right-edge evidence cells without introducing page-wide overflow suppression. These behaviors and the unaffected H2 chart passed the second visual review at 1920px, 1440px, and 1280px.

### DR-014 — Expand Architecture and add a Data Model page

**Priority:** P1

**Implementation status:** Implemented in Group I2 and visually accepted 2026-08-12.

Required outcome:

- Explain “held out” in plain language.
- Identify concrete Harbor results and artifacts.
- Identify `scripts/publish_phase3_run.py` as the final publisher.
- Explain how live supervision is enabled or disabled.
- Add a `/data-model` page.
- Show live tables, canonical tables/views, R2 relationships, live-to-canonical linkage, file-backed snapshots, and dashboard consumers.
- Use a checked-in Mermaid source plus generated SVG or another reviewable, accessible equivalent.
- Provide an HTML/text fallback.

Group I2 preserves the four-part Architecture foundation while explaining held-out verifier scoring in plain language, naming representative retained Harbor evidence, separating `supervise_live`, `progressive_artifacts`, and `publish_results` behavior from current workflow defaults, and identifying `scripts/publish_phase3_run.py` as the final canonical publisher. The new no-query `/data-model` documentation route separates live state, canonical metadata, derived views, external R2 bytes, checked-in reviewed snapshots, and dashboard consumers. It shows only audited direct relationships, identifies `live_runs.canonical_arm_run_id -> benchmark_arm_runs.id` as the sole direct live-to-canonical foreign key, and keeps per-trial/per-artifact reconciliation distinct from a database FK. The checked-in Mermaid source and complete semantic HTML/text representation document the same intentional model without a runtime diagram dependency.

### DR-015 — Add contextual glossary links

**Priority:** P1

**Implementation status:** Implemented in Group I2 and visually accepted 2026-08-12.

Required outcome:

- Relevant glossary entries link to dashboard pages or evidence views.
- Links are explicit and accessible.
- Internal compatibility entries remain technical and do not replace public labels.

Group I2 extends the existing typed glossary registry with optional static internal links. The Glossary page renders complete explicit related-link sets, while the portal-backed `TermInfo` popover exposes only the primary contextual destination plus its existing glossary anchor. Keyboard, Escape, viewport positioning, click/touch, and type-safe term behavior remain intact. `Logical mode` and `Storage mode` remain compatibility entries beneath the public `Benchmark run class` and `Result source/storage location` language.

## 7. P1 requirements

### DR-101 — Retire “suspected no-op” as a primary diagnosis

**Implementation status:** Complete. Groups J2A/J2B produced the frozen, manifest-bound 960-trial offline derived snapshot, J2C added fail-closed dashboard consumption, and J2D representative/manual evidence and visual review were accepted 2026-08-16 after the bounded Quick diagnosis wording recapture passed.

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

**Implementation status:** Complete. Groups J2A/J2B produced the frozen primary/secondary derived classifications without changing the accepted comprehensive review, J2C added registry-derived filters and evidence drilldown, and J2D representative/manual evidence and visual review were accepted 2026-08-16 after the bounded Quick diagnosis wording recapture passed.

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

**Implementation status:** Complete. Groups J2A/J2B produced the frozen independent trajectory axis, including ordinary-success fallback behavior, J2C added manifest-bound dashboard consumption, and J2D representative/manual evidence and visual review were accepted 2026-08-16 after the bounded Quick diagnosis wording recapture passed.

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

### Group J1 — Offline failure/trajectory taxonomy foundation

Group J1 establishes `configs/dashboard/failure_taxonomy_v1.json` as the single machine-readable registry for DR-101, DR-102, and DR-103. Python generation consumes that canonical JSON directly. Dashboard TypeScript consumes the byte-identical generated mirror at `apps/dashboard/src/generated/failure_taxonomy_v1.json`, with tests enforcing the canonical SHA-256 plus byte and parsed equality before the dependency-free loader validates it. Its full design and evidence rules are recorded in [DASHBOARD_FAILURE_TAXONOMY_J1.md](DASHBOARD_FAILURE_TAXONOMY_J1.md).

The accepted comprehensive review under `results/manual_verification/comprehensive_review_20260731/` remains a frozen input. J2 must be an offline second-stage derivation bound to the exact checked-in review manifest, scope fingerprint, input hashes, taxonomy hash, and classifier implementation hash. Initial generation requires no Supabase or R2 reread and must not use `.review-cache` as canonical evidence. The derived snapshot must remain separate from raw reward, raw outcome, exception fields, historical quality flags, and the existing comprehensive-review classifications.

The public `response_path_class` is separate from existing `ActivitySubtype` and `ExecutionValidity` fields. Existing `empty_completion_zero_usage` normalizes to public `empty_completion`; `suspect_noop_zero_token` and `suspect_noop_count` remain compatibility data only and are not new primary diagnoses. The trajectory axis includes `successful_completion` because ordinary successful trials must not be forced into `indeterminate` merely because no failure narrative applies. It is an ordinary-success fallback only when retained evidence supports no more specific anomalous trajectory disposition; a successful raw outcome never overrides stronger positive trajectory evidence.

The J1 evidence policy is conservative: absence-sensitive labels require complete or explicitly adequate coverage; compound diagnoses require positive support for every constituent; generic failure, zero reward, elapsed time, or missing excerpts do not justify specific narratives. The verifier axis is independent from response-path, policy, and termination axes: `none` may describe an independently explained non-success, `unclassified_failure` requires an established verifier/task/solution failure, and `timeout_inside_verifier` requires verifier-specific timeout evidence. Incomplete or nonspecific evidence uses only the fallback justified for that axis. Registry `order` fields are display order, never implicit classifier precedence; J2 defines and tests its classifier precedence explicitly. No hidden or private model reasoning may be required, retained, inferred, or displayed.

Groups J2A/J2B freeze the accepted offline derivation at `results/manual_verification/failure_taxonomy_20260813/`. Group J2C implements server-side manifest/hash/schema/scope/trial-set validation, exact trial-ID-only joins, registry-derived filters and display metadata, explicit outside-scope availability, and structured evidence drilldown on Trial Quality and trial detail. The manifest-bound snapshot, accepted hashes, distributions, producer policy, J2C fail-closed consumption boundary, and J2D acceptance are recorded in [DASHBOARD_FAILURE_TAXONOMY_J2.md](DASHBOARD_FAILURE_TAXONOMY_J2.md). The 960-row derived snapshot does not alter the accepted comprehensive review or raw benchmark truth. DR-101, DR-102, and DR-103 are complete as of the accepted J2D review on 2026-08-16.

J2D's deterministic packet covered all 960 frozen trials and the exact 243-trial review queue: all four response anomalies, all five dependency/import cases, both missing-file/content cases, the successful-timeout control and its 19-case raw-success population, deterministic high/medium no-substantive controls, ordinary success, indeterminate, and a real out-of-scope dashboard control. Trial Quality and representative details passed visual review. The out-of-scope trial correctly showed J2 unavailable rather than `response_path_class=not_applicable`, with no database, live, or browser taxonomy substitute. The only finding was ambiguous adjacent “live fallback” wording on the independent Quick diagnosis surface; the bounded “operational live analysis” correction and explicit non-replacement statement passed post-fix recapture.

Final visual acceptance used production mode because Next 16 Turbopack development mode separately exhibited React Client Manifest errors and approximately 50-second application-code renders. Local production observations were approximately 1.50 seconds for `/`, 0.80 seconds for filtered `/trial-quality`, 2.24 seconds for a representative detail, 0.52 seconds for the successful-timeout detail, 4.07 seconds for the initial out-of-scope detail, and 1.78 seconds for the post-fix out-of-scope recapture. These observations are not performance guarantees. The development-mode defect was separate from J2 acceptance and was subsequently isolated to the broadened Turbopack filesystem/package-resolution boundary. Keeping repository-rooted production tracing, compiling from a byte-identical app-local registry mirror, and removing the broad Turbopack root restored bounded Turbopack development requests without changing J2 semantics; production J2D acceptance and DR-101/102/103 remain complete.

### DR-104 — Consolidate Tasks and Evals

**Implementation status:** Complete and manually/visually accepted 2026-08-17.

Accepted design:

- `Evals` is the single primary inventory surface and remains `valid-imported` by default.
- `/evals?scope=valid-imported` preserves the established `benchmark.v_valid_eval_arm_comparison` population: invalid/quarantined arm runs are excluded, multiple valid imported run classes may contribute, and the inventory is not a fixed full-suite denominator.
- `/evals?scope=all-imported` exposes the broader former Tasks population from `benchmark.v_dashboard_tasks` and its underlying imported trial/run relations. It retains run classes and validity states excluded from the valid-only view and is likewise not a fixed full-suite denominator.
- `/tasks` is a compatibility redirect to `/evals?scope=all-imported`; Tasks is no longer an independent table or primary-navigation destination.
- Index-to-detail and Back links preserve the selected scope. Valid detail remains valid-only; all-imported detail aggregates the same broader trial population and visibly distinguishes invalid/quarantined and unlinked evidence.
- Index and detail freshness definitions are scope-specific. Recorded-cost totals retain row coverage, so unrecorded or partially recorded cost is never displayed as a complete zero-cost fact.
- Unknown or repeated scope values fail safely to `valid-imported` with a visible warning.

Counts can differ because `valid-imported` applies the established invalid/quarantined exclusion while `all-imported` retains the broader imported evidence population. Neither dynamic inventory should be called “valid full-suite” or used as a fixed leaderboard denominator.

The production-mode DR-104 review passed on 2026-08-17 at 1920px, 1440px, and 1280px. Both selector states, invalid/repeated-scope fallback warnings, `/tasks` compatibility redirect, scope-preserving index/detail/Back links, scope-aligned freshness, recorded-cost coverage, all-imported validity presentation, and responsive tables/layout were accepted. `terminal-bench-2.0:multi-source-data-merger` served as the known differing-population control: valid-imported rendered 48 trials / 46 successes / 95.8%, while all-imported rendered 57 trials / 47 successes / 82.5%, with the corresponding recorded-cost coverage differences retained. The accepted all-imported label is “Linked / unflagged,” which reports the directly established linkage/invalidation state without overstating membership in the valid-only view. DR-104 did not change J2 or frozen-result semantics.

### DR-105 — Consolidate Planner and Arm Scaffold

**Implementation status:** Complete and manually/visually accepted 2026-08-17.

`/planner` is the single primary planning surface with two explicit URL-backed modes:

- `/planner` and `/planner?mode=run` — Plan benchmark run
- `/planner?mode=arm` — Draft new arm configuration

Missing mode defaults to run. Empty, unknown, or repeated mode values visibly warn and fall back to run. `/scaffold` is retained only as a compatibility redirect to `/planner?mode=arm`, and Arm Scaffold is removed from primary navigation.

Run mode retains the existing repository-backed arm/task-set inventory, run-plan validation, and reviewable GitHub Actions command text without a dispatch action. Its unchanged numeric and provider gates are now explicitly presented as checked-in planning assumptions rather than live runner-capacity, provider-availability, quota, or readiness observations.

Arm mode remains read-only and emits a deterministic, safely quoted YAML draft plus a suggested future `configs/arms/<arm-id>.yaml` destination. It creates no file, requests or generates no credential values, launches no workflow, and warns on an exact existing-arm collision. Provider/router-specific environment, secret mapping, safety, and validation fields remain for normal review against an audited existing arm. All resulting configuration changes must go through normal Git review. DR-106 evidence-aware links remain separate and open.

The production-mode DR-105 manual review passed on 2026-08-17 at 1920px, 1440px, and 1280px. Run and arm-draft modes remained contained; malformed-mode fallback was visible; direct, LiteLLM-routed, existing-arm collision, and unsafe-ID/YAML-escaping controls behaved as designed. The `/scaffold` compatibility redirect and read-only/no-dispatch boundary were also confirmed.

### DR-106 — Add evidence-aware deep links

**Implementation status:** Complete and manually/visually accepted 2026-08-18. DR-106A destination/filter foundation is committed as `d01ef831`; DR-106B source-surface wiring passed production acceptance.

DR-106A establishes small typed evidence-link contracts rather than a generic or inference-based URL builder. Exact run and trial links require an established `run_label` or `trial_id`; the explicitly reviewed aggregate-arm helper targets the frozen Comprehensive Review population with exact arm equality and never invents a “latest” run. Operational/all-imported arm-only rows remain deliberately unlinked where no destination reproduces their population faithfully; DR-106B does not invent or select a run for those aggregates. Reviewed Phase 3 Cost Coverage links accept only `phase3-core` or `phase3-extended`, while `source_scope` may carry one validated reviewed or inventory scope solely as navigation context through Cost Coverage, Comprehensive Review, and exact run/trial drilldown. That context never changes a destination population or Cost Coverage headline scope, and invalid or repeated values are visibly ignored.

Cost Coverage retains its checked-in reviewed headline denominator and cost semantics. Optional exact `arm_id`, `run_label`, and `trial_id` focus parameters populate a separate, bounded, read-only provenance table from the valid-only `benchmark.v_trial_adjusted_cost_coverage` view. All supplied identities are combined with parameterized exact predicates; conflicting identities produce no match, arm-only focus selects no run, and no prefix/latest/alternate fallback changes the reviewed totals or Kimi K3 qualifications.

Comprehensive Review now exposes a separate `#reviewed-trials` surface over all manifest-validated frozen `trial_review.csv` rows. Namespaced exact-equality filters cover trial, arm, run, task, raw outcome, retained failure subtype, execution validity, termination subtype, and policy disposition with deterministic pagination. This complete frozen population remains distinct from the unchanged default high-priority manual-review queue, raw benchmark results, and J2. Its reviewed-trial, queue, and control rows put their exact Trial action in the first visible column.

DR-106B wires the supported contracts into the reviewed Overview leaderboard and cost/performance chart/table, Cost Coverage reviewed arm table, Phase 3 rows in Cross-phase, exact Runs inventory identities, frozen Trial Quality taxonomy trials, and run-detail trial rows. Reviewed arm/run pairs use only the exact frozen G1 selected-run label for the active reviewed scope. Available reviewed cost values carry the reviewed scope, exact arm and selected-run identity, navigation-only source scope, and the `#cost-provenance-focus` destination; unavailable values remain plain and Kimi K3 qualifications remain unchanged. Phase 1/2 Cross-phase aggregates receive no fabricated Phase 3 run or cost link. Run-detail one-trial rows now expose the exact trial action in the leftmost visible column.

The frozen Comprehensive Review arm summary links only predicates proven equal against the same 960-row reviewed population: total reviewed, substantive success/failure (raw outcome plus substantive execution), provider-policy refusal, timeout termination, and setup/transport termination. Empty-completion, telemetry, unknown-classification, and manual-review-queue counts remain unlinked because they are multi-value or different predicates. Operational Trial Quality counters, suspect-no-op flags, all-imported arm-only aggregates, and operational/imported cost totals likewise remain outside the frozen-review builders; no similarly named destination is substituted. Production-mode manual/visual acceptance passed 2026-08-18. Reviewed extended and core cost links preserved the exact reviewed scope, arm, frozen selected-run identity, navigation-only source scope, and `#cost-provenance-focus` destination. An exact Kimi K3 focus with no valid stored cost row failed closed with an explicit no-match state rather than selecting another run. Comprehensive Review interaction checks reproduced a 35-row substantive-failure count and a 9-row provider-policy count exactly, while Empty, Telemetry, Unknown, and Queue remained deliberately unlinked. Responsive production captures showed no DR-106 containment regression. DR-106 is accepted.

Required:

- arm names link to the relevant arm/run view;
- trial actions appear in the leftmost visible columns;
- cost values link to cost provenance filtered to the relevant arm/run/trial;
- failure counts link to filtered Evidence Review results;
- links preserve selected corpus scope.

## 8. P2 requirements

**2026-08-18 gap audit:** residual DR-201/DR-202/DR-203 work is scoped in [`DASHBOARD_P2_COMPLETION_20260818.md`](DASHBOARD_P2_COMPLETION_20260818.md). The audit treats already accepted terminology, responsive containment, sticky identity columns, and canonical evidence identity as foundations to preserve rather than reimplement.

**2026-08-19 P2 closeout:** DR-201, DR-202, and DR-203 are complete. P2-B completed the shared terminology contract, P2-C completed presentation-only friendly labels with canonical fallback, and P2-D completed the residual large-desktop/overflow work. Production validation and the 1920px/1440px/1280px manual visual acceptance passed. DR-302 and DR-303 remain later P3 requirements outside this closeout.

### DR-201 — Shared tooltip registry

**Implementation status:** Complete. P2-B commit `0604ca9f` extended the shared conceptual glossary/`TermInfo` contract to the required P2 terms while keeping the failure-taxonomy registry authoritative for individual taxonomy enums and preserving raw identity values.

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

**Implementation status:** Complete and production-mode manually/visually accepted 2026-08-19. P2-D commit `062dd97f` widened the large-desktop shell, added reusable column-width and opt-in sticky-header contracts, local navigation on Comprehensive Review / Trial Evidence / Live Runs, bounded Live Runs Tool Activity and Event Tail regions, and moved the progressive-artifact Preview action into the left sticky identity/action column. Existing horizontal containment and narrower responsive behavior were retained.

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

**Implementation status:** Complete. P2-C commit `126ccebb` added one pure presentation-label layer for model, arm, provider, and routing display; unknown values fall back to the canonical source value and persisted IDs, URLs, reviewed artifacts, exports, and raw evidence identities remain unchanged.

Display friendly model/arm names prominently while retaining canonical IDs in details.

Example:

- `GLM 5.2`
- `router-glm-5.2`
- `LiteLLM-routed`
- `Z.AI / GLM`

Do not mass-rename canonical IDs.

## 9. Chart requirements

Scope and Kimi cost integration must be completed first so chart inputs are stable. DR-301 is then completed as corrective P0 work before the second manual acceptance pass. DR-302 and DR-303 remain later chart requirements.

### DR-301 — Interactive cost/performance frontier

**Priority:** P0 — detailed implementation specification for DR-011

**Implementation status:** Groups H1/H2 implementation complete and visually accepted 2026-08-12.

DR-301 is promoted into the corrective pre-second-acceptance work. It supplies the detailed interaction and presentation requirements for DR-011 and is not a separate duplicate chart requirement.

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
- point click-through to arm and selected-run evidence;
- tooltip with numerator, denominator, cost basis, confidence, gap, and unclean spend;
- keyboard-focusable points or controls and an equivalent accessible non-hover presentation of the same material facts.

Group H2 uses fixed point sizing, the option explicitly permitted above. It adds no chart dependency and introduces no client-side metric or Pareto derivation: scale geometry is presentation-only, and H1 remains authoritative for all quantitative values, availability, filtering, and frontier output.

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

### Corrective pre-second-acceptance sequence

1. Scope selection and qualified Kimi pricing-provenance/cost integration (`DR-008`, `DR-009`) were completed in Commit Groups F1/F2 and now provide the stable reviewed inputs.
2. The reviewed run-selection and Overview run/cost contract (`DR-012`) was completed in Commit Groups G1/G2 against those stable inputs.
3. The Group G3/G4a/G4b/G4c freshness rollout (`DR-010`) completed the freshness implementation.
4. Groups H1/H2 completed the reviewed data/model/accessibility foundation and interactive Overview SVG rendering for the single chart specified jointly by `DR-011` and `DR-301`.
5. Group I1 completed the required bounded layout corrections (`DR-013`), and Group I2 completed the Architecture/Data Model and glossary-link corrections (`DR-014`, `DR-015`).
6. The comprehensive second manual visual acceptance passed on 2026-08-12, completing `DR-007` and accepting the implementation-complete corrective requirements above.

Additional taxonomy, failure-composition, and spend-decomposition work may follow later; the DR-011/DR-301 chart no longer waits until after P0 acceptance.

## 11. Initial P0 validation matrix — Commit Groups B–D

This matrix preserves the implemented first-pass baseline for Commit Groups B–D. Its Phase 3 core Cross-phase and Cost Coverage rows record what that pass intentionally delivered; the corrective matrix below supersedes those rows as the target for the next acceptance pass.

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

### Corrective pre-second-acceptance validation matrix

| Check | Required result |
|---|---|
| Cross-phase default | Reviewed Phase 3 extended corpus |
| Cost Coverage default | Reviewed Phase 3 extended corpus |
| Historical alternate | Phase 3 core remains explicitly available as a historical snapshot |
| Kimi K3 cost inclusion | Qualified retained-rate estimate is included with visible allocation-confidence and pricing-provenance caveats |
| Historical evidence | No frozen historical input is rewritten |
| Freshness contract | Source/view, latest included run, canonical publication time, render/query time, data age, and warning state are visible |
| Overview run identity | Frozen selected reviewed arm run is identified and linked; current database evidence is resolved only for that exact label |
| Overview cost evidence | Recorded cost, applicable reviewed cost basis, missing/unresolved counts, accounting gap, source, confidence, and reconciliation state are visible |
| Cost/performance chart | The DR-011/DR-301 chart is present and accessible without pointer hover |
| Layout corrections | Required heatmap, phase-card, table, overflow, and alignment fixes are complete |
| Architecture and Data Model | Required explanations and `/data-model` are complete |
| Contextual glossary | Required dashboard and evidence links are complete |
| Repository gates | Repository checks, secret and protected-path checks, typecheck, build, and tests pass |

## 12. Initial P0 manual acceptance checklist — first pass

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

### Corrective second manual acceptance checklist

At 1920px, 1440px, and 1280px desktop widths:

- [x] Confirm Cross-phase and Cost Coverage default to the reviewed Phase 3 extended corpus and provide an explicit Phase 3 core historical alternate.
- [x] Confirm Kimi K3 is included with qualified retained-rate wording, low arm-run/provider-log allocation confidence, unresolved trial allocation, incomplete pricing-source provenance, and a clear statement that the estimate is not invoice-level/provider-billed spend.
- [x] Confirm dynamic pages show source/view, latest included run, canonical publication time, render/query time, data age, and stale or publication-lag warning state.
- [x] Confirm Overview identifies and links each frozen selected reviewed arm run, discloses the run-selection rule, and does not substitute newer database runs.
- [x] Confirm Overview distinguishes recorded cost from adjusted known or qualified retained-rate cost and shows missing/unresolved counts, accounting gap, source, confidence, and reconciliation state.
- [x] Exercise the DR-011/DR-301 chart controls, arm/run links, cost basis, confidence and accounting-gap disclosure, keyboard navigation, and accessible non-hover equivalent.
- [x] Confirm heatmap headers wrap without truncation, phase-summary cards are visually coherent, no meaningless secondary ARM dashes remain, Runner Fleet body content is aligned, and rightmost table content remains reachable.
- [x] Confirm Architecture explains held-out tests without benchmark jargon, names concrete result/transcript/verifier/trajectory evidence, makes live enable/disable and publication behavior understandable, visibly identifies `scripts/publish_phase3_run.py` as the final publisher, and has no overlap or clipping.
- [x] Confirm `/data-model` makes live/canonical and direct-FK/reconciliation boundaries obvious, keeps R2 visibly external, provides understandable checked-in diagram source and HTML/text fallback, and remains readable at 1920px, 1440px, and 1280px.
- [x] Confirm Glossary contextual links are visible and meaningful, `TermInfo` remains keyboard/touch usable, and internal `Logical mode` / `Storage mode` compatibility fields remain secondary to public terminology.
- [x] Confirm the corrected pages remain usable at 1920px, 1440px, and 1280px desktop widths without accidental page-wide horizontal scroll, overlap, or inaccessible right-edge content, and confirm the H2 chart remains unaffected.
- [x] Confirm no frozen historical evidence changed.

### 2026-08-12 second-pass closeout evidence

- The comprehensive responsive review covered the relevant Overview, Architecture, Data Model, Glossary, Cross-phase, Cost Coverage, Runner Fleet/deprecation, Trial Quality, and other rendered dashboard surfaces at 1920px, 1440px, and 1280px.
- Overview chart controls, point details/tooltips and deep links, keyboard behavior, and the accessible non-hover evidence presentation passed. `TermInfo` mouse, keyboard, focus-transfer, Escape, contextual-link, Glossary-link, and viewport-placement behavior also passed.
- Acceptance found a React warning because an SVG `<title>` received two child values. It was corrected to one computed string child and covered by a regression test before acceptance.
- The first local capture saw tenant/user connection failures on database-backed routes. The two configured local sources had the same sanitized connection fingerprint and each subsequently passed a read-only `SELECT 1`. A production-build recapture returned HTTP 200 for `/`, `/trial-quality`, `/arms`, `/evals`, `/runs`, and `/artifacts` in three consecutive rounds (18/18), with an empty server warning/error audit. This was treated as transient local acceptance-environment behavior, not an application/query defect; no fallback or database semantic change was introduced.
- The final Architecture terminology containment defect was corrected with scoped wrapping/shrink containment. At 1920px and 1440px all four terminology cards remained in one row; at 1280px three cards remained on the first row and Recorded cost moved to a second row, with every label and information trigger contained and readable.
- No benchmark rerun, paid provider probe, migration 009 execution, Supabase write, or R2 write was performed during acceptance.
- **Outcome:** PASS. DR-007 is complete; DR-008 through DR-015 and DR-301 are accepted. DR-302 and DR-303 remain later requirements outside this acceptance closeout.

## 13. Out of scope for the first implementation pass

This list preserves the boundary of the initial Commit Groups B–D pass. Chart implementation was out of scope for that pass, but DR-011/DR-301 is now promoted into the corrective pre-second-acceptance sequence. Broad visual redesign also remains out of scope, while the specific bounded layout corrections in DR-013 are now required before the second acceptance pass.

- New benchmark runs
- Provider probes
- Migration execution
- Supabase/R2 writes
- Historical result regeneration
- Full taxonomy reclassification
- Chart implementation
- Broad CSS redesign
- Branch deletion or history rewriting
