# Dashboard P2 completion plan — 2026-08-18

## Purpose

This document records the post-DR-106 gap audit for DR-201, DR-202, and
DR-203 from `DASHBOARD_REVISION_SPEC_20260804.md`.

Audit baseline:

- branch point: `650cdbdd07d47ae6ac4b3cddfd718ae787a62112`
- repository state: clean
- DR-106: merged and accepted
- frozen benchmark/review results remain unchanged

The audit is static/read-only. It does not run benchmarks, provider probes,
migrations, Supabase writes, or R2 writes.

## Decision

P2 is not a greenfield rewrite.

Prior corrective work already implemented substantial terminology,
accessibility, overflow, responsive containment, identity-column, and friendly
presentation infrastructure. P2 will complete only the residual requirements
without replacing accepted behavior or changing canonical evidence identity.

## DR-201 — Shared tooltip registry

Status: PARTIAL.

Already satisfied:

- `apps/dashboard/src/lib/glossary.ts` is a typed reusable conceptual-term
  registry.
- `TermInfo` is a reusable portal-backed information control.
- `TermInfo` already supports focus, click/touch, Escape, focus transfer,
  viewport-aware placement, `aria-describedby`, and `role="tooltip"`.
- Its keyboard/touch behavior passed prior production manual acceptance.
- Recorded cost is already registered and used contextually.
- Adjusted known cost and Known accounting gap already exist in the glossary.
- The failure-taxonomy registry remains authoritative for individual taxonomy
  enum values and definitions.

Residual work:

- add or explicitly map the conceptual terms:
  - Attempt
  - Confidence
  - Unresolved
  - Routing path
  - Execution validity
  - Activity class
  - Failure subtype
  - Policy disposition
  - Telemetry consistency
  - Artifact completeness
  - R2 integrity
- retain existing Recorded cost, Adjusted known cost, and Known accounting gap;
- wire the shared conceptual terms into the important cost/evidence table
  headings where the corresponding values are displayed;
- do not duplicate failure-taxonomy enum definitions into the glossary;
- do not replace raw enum/identity values.

## DR-202 — Global desktop layout and overflow

Status: PARTIAL.

Already satisfied:

- shared horizontal table containment;
- wrapped table headings;
- extensive `overflow-wrap:anywhere` handling for long identities;
- sticky identity columns on the major dense run/arm/trial/evidence tables;
- responsive containment previously accepted at 1920px, 1440px, and 1280px;
- important run/trial actions moved to leftmost identity columns by DR-106.

Residual work:

- increase effective large-desktop content width beyond the current 1480px
  AppShell cap while retaining the existing responsive breakpoint behavior;
- establish reusable explicit compact/context/identity column width contracts;
- add sticky top headers to genuinely long scrollable tables;
- add reusable local section navigation to genuinely long pages, initially:
  - Comprehensive Review
  - Live Runs
  - Trial detail
- bound the visible height of Live Runs tool activity and observable
  event/output history with internal vertical scrolling;
- audit remaining primary actions so important actions are not reachable only
  at a far-right table edge.

Existing accepted horizontal-scroll and wrapping behavior must not regress.

## DR-203 — Friendly labels

Status: PARTIAL.

Already satisfied:

- canonical arm IDs, run labels, provider values, and backend model values are
  retained throughout evidence identity, URLs, and data contracts;
- reviewed chart code already has presentation fields such as `displayName`
  and `providerFamilyLabel`;
- Live Runs already displays model context beneath canonical arm identity;
- arm configuration includes checked-in `display_name` metadata.

Residual work:

- add one pure presentation-only label helper rather than page-local mappings;
- provide friendly model labels such as:
  - `GLM 5.2`
  - `GPT-5.5`
  - `DeepSeek V4 Pro`
  - `Gemini 3.5 Flash`
  - `Claude Sonnet 4.6`
  - `Kimi K3`
- provide friendly provider-family labels such as:
  - `Anthropic`
  - `DeepSeek`
  - `Google / Gemini`
  - `OpenAI`
  - `xAI / Grok`
  - `Moonshot / Kimi`
  - `Alibaba / Qwen`
  - `Z.AI / GLM`
- provide routing presentation such as `LiteLLM-routed` while retaining raw
  routing identity where evidence detail requires it;
- show the friendly value prominently and canonical ID immediately as
  secondary identity;
- unknown values must fall back safely to the canonical source value;
- do not rename persisted IDs, generated reviewed artifacts, URLs, exports, or
  frozen source data.

Primary adoption surfaces:

- Overview reviewed leaderboard/chart/table
- Cost Coverage
- Cross-phase Phase 3 rows
- Runs
- Arms
- Trial Quality arm/run summaries
- Live Runs where model/arm presentation is already shown

## Implementation groups

### P2-A — Audit contract

Documentation only: this completion plan plus the parent revision-spec pointer.
No dashboard behavior changes.

### P2-B — DR-201 terminology completion

Extend the existing conceptual glossary and apply existing `TermInfo`
interaction to the required P2 concepts. Keep the failure-taxonomy registry
authoritative for individual taxonomy values.

### P2-C — DR-203 presentation labels

Add a pure, deterministic presentation-label module with tests and safe
canonical fallback. Apply friendly model/provider/routing presentation without
changing identity or evidence contracts.

### P2-D — DR-202 layout completion

Complete the large-desktop width, long-table sticky-header/column contract,
long-page section navigation, Live Runs bounded-scroll regions, and remaining
left-action treatment. Avoid unrelated restyling.

## Protected boundaries

P2 must not modify:

- frozen Phase 1/2/3 benchmark results;
- `results/manual_verification`;
- reviewed Phase 3 generated comparison/run-selection artifacts;
- failure-taxonomy canonical snapshot or classifier;
- `configs/arms/*.yaml`;
- migrations;
- benchmark/provider execution behavior.

No paid benchmark run or provider probe is required.

## Validation strategy

Each implementation group receives focused tests first.

Before final acceptance:

- dashboard typecheck;
- relevant Node suites;
- relevant Python dashboard contract tests;
- one production build;
- `make check`;
- `make secret-scan`;
- `git diff --check`;
- protected-boundary inspection.

Production manual review will focus on surfaces changed by P2 at 1920px,
1440px, and 1280px.

## Later work

DR-302 failure composition and DR-303 spend decomposition remain separate P3
work. P2 must not introduce those charts.
