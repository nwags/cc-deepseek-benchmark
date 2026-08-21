# DR-304 — Provider-Billed Cost Reconciliation

**Date:** 2026-08-21
**Status:** DR-304A source contract in progress
**Base:** `main` at `886e893167d1026b1033ec87c8133143928063d3`
**Branch:** `dashboard-dr304-provider-billed-cost`

## Purpose

Correct decision-oriented Phase 3 cost reporting after authoritative OpenAI
provider exports demonstrated that the historical Claude Code / Harbor cost
telemetry substantially overstated GPT-5.4 and GPT-5.5 spend.

The correction must preserve frozen benchmark history while making current
tables, charts, comparisons, and sponsor-facing reporting use the best
available cost evidence.

## Authoritative OpenAI findings

Complete project-period provider usage from 2026-05-01 through 2026-08-21:

- provider spend: **$95.2410900**
- requests: **2,964**
- input tokens: **74,364,964**
- cached input: **66,424,320**
- uncached input: **7,940,644**
- output tokens: **2,047,316**
- active provider projects: **1**
- active API keys: **1**

Selected full sweeps:

| Arm | Provider-billed | Historical harness recorded | Historical reviewed adjusted |
|---|---:|---:|---:|
| GPT-5.4 | **$29.7919335** | $173.094830 | $183.646689146806 |
| GPT-5.5 | **$48.604914** | $168.708375 | $183.958832348525 |

Combined authoritative OpenAI full-sweep cost: **$78.3968475**.

## Core reporting rule

For current comparative reporting:

1. exact provider-billed arm cost, when reconciled to the exact selected run;
2. otherwise reviewed adjusted-known cost;
3. otherwise a separately qualified retained-rate estimate;
4. otherwise unavailable.

Historical harness cost remains provenance, not the preferred comparison cost
when superior provider evidence exists.

## Required cost fields

The new reviewed contract must distinguish:

- historical harness-recorded cost;
- historical reviewed adjusted cost;
- provider-billed cost;
- provider reconciliation status;
- selected reporting cost;
- selected reporting cost basis;
- trial-allocation status;
- outcome-allocation status.

## Allocation rule

An exact arm-level provider total does not imply exact trial- or outcome-level
allocation.

For reconciled OpenAI full sweeps:

- arm-level provider billing: exact;
- trial-level provider-cost allocation: unavailable;
- outcome-level provider-cost allocation: unavailable.

No proportional allocation may be fabricated.

## Frozen boundaries

Do not modify:

- Phase 1 frozen results;
- Phase 2 frozen results;
- raw Phase 3 result artifacts;
- historical Phase 3 trial rewards/tokens;
- `results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv`;
- `results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv`;
- `results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json`;
- DR-303 historical spend-decomposition sources.

Private provider exports must not be committed.

## Commit groups

### DR-304A — provider evidence and correction contract

- sanitize and hash-bind authoritative OpenAI provider evidence;
- validate exact selected-run linkage;
- preserve old harness/reviewed values as diagnostics;
- document root cause and frozen boundaries;
- add source-contract tests.

No dashboard behavior change.

### DR-304B — current reviewed cost model

Create a new reviewed reporting layer rather than overwriting the 2026-08-05
snapshot.

The model must select provider-billed OpenAI arm totals and retain historical
estimates separately.

Expected selected-cost anchors, if every non-OpenAI selected cost remains
unchanged:

- Phase 3 core: **$682.961171493867**
- Phase 3 extended: **$713.7754908938669**

The generator must reproduce these independently before they are accepted.

### DR-304C — dashboard reporting and cost/performance charts

Update all decision-relevant consumers to use selected reporting cost:

- Overview cost/performance frontier;
- Cost Coverage headline and arm table;
- Cross-phase tables and phase summaries;
- cost-per-attempt;
- cost-per-clean-success;
- router cost ratios;
- sponsor-facing current reporting.

OpenAI rows must visibly say `Provider billed`.

Historical harness/reviewed estimates remain available as secondary
diagnostics.

### DR-304D — spend-decomposition semantics

Do not present historical OpenAI outcome-dollar decomposition as actual spend.

For OpenAI, current selected provider cost must remain unallocated unless
provider evidence supports trial/outcome mapping.

The DR-303 decomposition may remain as a clearly labeled historical
harness-estimate diagnostic.

### DR-304E — prevention, acceptance, and closeout

- make provider-vs-harness cost semantics explicit;
- pin or otherwise record future router/runtime versions required for
  reproducibility;
- add regression tests preventing a harness estimate from masquerading as
  provider billing;
- production build;
- bounded responsive manual review;
- update current status/acceptance documentation;
- merge to `main`.

## Acceptance criteria

DR-304 is not complete until current reporting on `main` shows:

- GPT-5.4 selected cost: **$29.7919335**
- GPT-5.5 selected cost: **$48.604914**

everywhere decision-relevant.

Old OpenAI harness estimates must remain traceable but must not drive the
default cost/performance comparison.

Quality/performance outcomes are unchanged.

No private provider IDs or raw provider exports may enter the repository.
