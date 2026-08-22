# DR-304 — Provider-Billed Cost Reconciliation

**Date:** 2026-08-21
**Status:** DR-304 complete — merged to `main` via PR #17 on 2026-08-22
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

- Phase 3 core arm-summed selected cost: **$682.961171493867**
- Phase 3 extended arm-summed selected cost: **$713.775490893867**

The frozen 2026-08-05 extended scope carries a pre-existing
**-$0.0000000000001** source-scope reconciliation residual: its qualified
scope total is `$1002.9841648891979`, while its exact 16-arm reviewed-cost sum
is `$1002.984164889198`. Applying the OpenAI replacements to the former yields
`$713.7754908938669`; summing the selected arm costs yields
`$713.775490893867`.

DR-304 uses the exact arm-summed value as the primary selected reporting total
and preserves the source-scope value plus the **-$0.0000000000001** residual
as provenance. No arm-level cost may be altered to absorb this residual.

The generator must reproduce these values independently before they are
accepted.

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

## Branch acceptance and closeout — 2026-08-22

Implementation and production acceptance were completed on
`dashboard-dr304-provider-billed-cost`. The accepted branch was merged to `main`
via PR #17 as merge commit `dd318d7c` on 2026-08-22, satisfying the plan's
final merge criterion.

Implemented sequence:

- DR-304A established sanitized/hash-bound provider evidence and the correction
  contract without changing frozen historical results.
- DR-304B added the current reviewed provider-aware cost model.
- DR-304C migrated the decision-facing cost/performance frontier, Overview,
  Cost Coverage, corpus-scope presentation, and Cross-phase reporting to the
  selected current reviewed cost while retaining historical evidence
  separately.
- DR-304D added the selected-cost outcome-allocation firewall. Provider
  aggregate totals cannot inherit or fabricate historical trial/outcome
  allocation; the historical DR-303 spend-decomposition model remains
  unchanged.
- DR-304E added prospective runtime provenance capture without changing the
  canonical publication fingerprint or historical result artifacts.

Accepted decision-facing OpenAI anchors:

- GPT-5.4 selected/provider-billed cost: **$29.7919335**
- GPT-5.5 selected/provider-billed cost: **$48.604914**
- combined selected OpenAI full-sweep provider cost: **$78.3968475**

Historical harness and reviewed adjusted values remain separately traceable and
do not drive the default current comparison when superior provider evidence is
available. Provider-billed OpenAI totals remain explicitly unavailable for
trial-level and outcome-level cost allocation and are never proportionally
redistributed across historical DR-303 buckets.

The accepted current reviewed scope retains:

- Phase 3 core selected arm-summed cost:
  **$682.961171493867**
- Phase 3 extended selected arm-summed cost:
  **$713.775490893867**
- Phase 3 extended historical reviewed arm sum:
  **$1002.984164889198**

Kimi K3 remains a separately qualified retained-rate estimate rather than
provider-billed spend. Its aggregate selected-cost efficiency may be shown
where supported, while trial-level allocation remains unresolved and
outcome-cost allocation remains unavailable.

DR-304E runtime provenance records future execution evidence rather than
retroactively guessing historical versions. Future final publication stores
structured run-level provenance for the installed Harbor distribution, the
actual isolated `.tools/litellm-proxy` LiteLLM distribution, runner-side Claude
Code CLI evidence, and Claude Code versions observed in retained
`system`/`init` agent records. Missing evidence remains explicitly unavailable.
`runtime_versions` is intentionally outside the existing publication
fingerprint contract, and `scripts/lib/publication_fingerprint.py` was not
changed.

The historical LiteLLM proxy version for runs where no reliable version was
retained remains unreconstructable. Versions observed during this 2026-08-22
closeout environment must not be presented as historical run versions.

Branch acceptance evidence:

- full dashboard Node suite: **270/270 passed**;
- full Python suite after the runtime-provenance addition:
  **450/450 passed**;
- strict review-output scan: clean;
- secret scan: passed;
- `git diff --check`: clean;
- production Next.js build: passed;
- production HTTP checks returned 200 for Overview, Cost Coverage core and
  extended, and Cross-phase core and extended;
- rendered current/historical boundary checks passed;
- manual production review passed at 1920px, 1440px, and 1280px for Overview,
  Cost Coverage core/extended, and Cross-phase core/extended;
- no frozen Phase 3 result, reviewed historical source, DR-303 implementation,
  or publication-fingerprint implementation was modified.

Key prevention commits:

- `5d3fdc4d` — selected-cost allocation firewall;
- `082486eb` — benchmark runtime provenance capture.

No benchmark rerun, paid provider probe, migration execution, Supabase write,
R2 write, frozen-result regeneration, historical-cost rewrite, or fabricated
provider trial/outcome allocation was performed during branch acceptance.

**Final outcome:** PASS. DR-304A–E are implementation-complete, accepted, and
merged to `main` via PR #17 as `dd318d7c`. The plan's final `main` acceptance
criterion is satisfied; DR-304 is complete as of 2026-08-22.
