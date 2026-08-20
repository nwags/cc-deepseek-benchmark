# Dashboard DR-303 Spend Decomposition Plan — 2026-08-19

**Status:** Contract defined; implementation pending
**Repository:** `cc-deepseek-bench`
**Branch:** `dashboard-dr303-spend-decomposition`
**Base:** `304cac4a4198d6fd21631eedd242379d85e235d1`
**Requirement:** DR-303 — Spend decomposition by arm

## Purpose

Implement the requested spend-decomposition-by-arm view without rewriting
frozen benchmark history, fabricating missing trial cost, double-counting
reconstructed dollars, weakening the reviewed F1 cost contract, or treating
Kimi K3's provider-log reconstruction as invoice-level or trial-allocated
spend.

DR-302 failure composition is complete and is outside this branch's behavior
changes.

## Contract decision

The primary DR-303 stack is a decomposition of each arm's selected reviewed
cost basis into:

1. recorded clean-success spend;
2. recorded normal-failure spend;
3. recorded exception-failure spend;
4. recorded exception-with-success-signal spend;
5. known accounting gap.

The first four segments are mutually exclusive recorded trial-cost dollars.
The fifth segment is not an outcome classification. It is the reviewed known
difference between the selected reviewed cost basis and recorded trial cost.

For historical core arms:

    selected reviewed cost = adjusted known cost
    known accounting gap = adjusted known cost - recorded cost

For Kimi K3:

    selected reviewed cost = qualified retained-rate estimate
    known accounting gap = qualified retained-rate estimate - recorded trial cost

Missing or unresolved cost rows remain explicit evidence counts. DR-303 must
not manufacture a dollar value for an unresolved row.

## Why the primary stack uses recorded outcome spend

The retained Phase 3 cost layer contains both recorded trial cost and
reconstructed adjusted-known cost.

For the historical 15-arm core, reconstructed dollars can often be assigned
to an outcome bucket because the retained trial-cost source contains an
`adjusted_cost_usd` value and an `outcome_bucket`.

Those reconstructed dollars are also exactly what create the known
accounting gap between recorded cost and adjusted known cost.

Therefore this would be invalid:

    adjusted clean-success spend
    + adjusted normal-failure spend
    + adjusted exception-failure spend
    + adjusted exception-with-success-signal spend
    + accounting gap

It would double-count reconstructed dollars.

DR-303 instead uses recorded outcome dollars for the four outcome segments
and adds the known accounting gap once.

Historical adjusted-outcome allocation may be shown as secondary evidence,
but it must never be added on top of the primary five-part stack.

## Authoritative reviewed populations

DR-303 uses the existing frozen reviewed Phase 3 scopes.

### Phase 3 extended — default

- scope: `phase3-extended`;
- 16 arms;
- 960 reviewed trials;
- 60 trials per arm;
- 562 raw successes;
- current reviewed comparison date: 2026-08-05.

The 960 exact Comprehensive Review trial IDs partition into:

- 900 historical core trial-cost IDs;
- 60 Kimi K3 reviewed trial IDs.

Those sets are disjoint and their union is exactly the 960-row Comprehensive
Review population.

### Phase 3 core — historical alternate

- scope: `phase3-core`;
- 15 arms;
- 900 reviewed trials;
- 60 trials per arm;
- 515 successes.

The 900 historical trial-cost IDs are exactly equal to the 900 non-Kimi
Comprehensive Review IDs.

DR-303 must not mix either reviewed scope with all-imported, latest-run,
operational, smoke, canary, live, or database-selected populations.

## Frozen sources

Primary retained sources:

### Historical core trial-level cost allocation

`results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv`

Expected SHA-256:

`dda44c435b555d3f358a47b5885c659b9ae0554511959ca9d40f76bc9539f5a3`

Expected shape:

- 900 rows;
- 900 unique trial IDs;
- 15 arms;
- 60 rows per arm;
- only these outcome buckets:
  - `clean_success`;
  - `normal_failure`;
  - `exception_failure`;
  - `exception_with_success_signal`.

### Historical core arm-level cost evidence

`results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv`

Expected SHA-256:

`59cd8eeabd98be1695ec4f0b199bf4935a3bf4c9bdde744669b8188db1845150`

### Frozen Comprehensive Review

`results/manual_verification/comprehensive_review_20260731/trial_review.csv`

Expected SHA-256:

`c6945d114e3a2e0610dfd091bad8ea4e9bc17707db678e90f4e0f8058fc56501`

Expected shape:

- 960 rows;
- 960 unique trial IDs;
- 16 arms;
- 60 rows per arm.

DR-303 uses this source for exact reviewed membership and for the retained
Kimi K3 trial-level recorded-cost/outcome split.

### Reviewed F1 comparison contract

`results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json`

Expected SHA-256:

`49445ab5ef77f8a660e63857e811740a2631520eb9164a191b6dea4644c4231d`

F1 remains authoritative for:

- scope identity;
- arm identity;
- recorded arm cost;
- adjusted-known core arm cost;
- Kimi qualified retained-rate arm cost;
- known accounting gap;
- missing recorded-cost count;
- unresolved cost count;
- cost basis;
- cost confidence;
- pricing-provenance status;
- arm/run allocation confidence;
- trial-allocation status;
- billing-reconciliation status;
- outcome-cost-allocation status.

DR-303 must not weaken or regenerate F1.

## Exact membership requirements

The quantitative model must fail closed unless all of the following remain
true:

- core trial-cost source has 900 unique IDs;
- Comprehensive Review has 960 unique IDs;
- Comprehensive Review has exactly 900 non-Kimi IDs;
- Comprehensive Review has exactly 60 Kimi K3 IDs;
- core trial-cost IDs exactly equal Comprehensive Review non-Kimi IDs;
- Kimi IDs are disjoint from core IDs;
- core IDs plus Kimi IDs exactly equal all 960 Comprehensive Review IDs;
- exact-ID arm identity agrees;
- exact-ID task identity agrees;
- every reviewed arm contains 60 trials.

No prefix, run-date, latest-run, approximate-name, or row-order join is
permitted.

## Outcome classification

### Historical core

Use the retained `outcome_bucket` field from the frozen historical
trial-cost source.

DR-303 does not reclassify those rows.

### Kimi K3

The retained historical cost source predates Kimi K3, so Kimi's recorded
outcome split is derived only from its exact frozen Comprehensive Review
rows using the same reward/exception semantics as the retained Phase 3 cost
generator:

1. raw reward `1` and no exception:
   `clean_success`;
2. raw reward `1` and exception present:
   `exception_with_success_signal`;
3. non-success with exception present:
   `exception_failure`;
4. raw reward `0` and no exception:
   `normal_failure`;
5. anything else:
   fail closed as unexpected for the current frozen Kimi population.

Current Kimi frozen counts:

| Bucket | Trials |
|---|---:|
| Clean success | 44 |
| Normal failure | 5 |
| Exception failure | 8 |
| Exception with success signal | 3 |
| **Total** | **60** |

These reproduce F1's:

- 47 successes;
- 44 clean successes;
- 3 exception-with-success-signal trials;
- 13 failure/incomplete trials.

## Recorded outcome dollars

For each arm, sum only non-null retained recorded trial cost within each
outcome bucket.

A missing recorded-cost row contributes:

- to its trial-count evidence;
- to missing/unresolved evidence as applicable;
- **no invented recorded dollars**.

For every historical core arm:

    sum(four recorded outcome buckets) == F1 recordedCostUsd

For Kimi K3:

    sum(four recorded outcome buckets) == 25.207213

The current Kimi recorded outcome split is:

| Bucket | Trials | Recorded cost | Missing recorded-cost rows |
|---|---:|---:|---:|
| Clean success | 44 | $20.394023 | 0 |
| Normal failure | 5 | $3.717660 | 0 |
| Exception failure | 8 | $1.095530 | 7 |
| Exception with success signal | 3 | $0 | 3 |
| **Total** | **60** | **$25.207213** | **10** |

## Exception-with-success-signal zero-dollar semantics

The current frozen reviewed population contains 19
exception-with-success-signal trials:

- 16 historical core;
- 3 Kimi K3.

All 19 lack recorded trial cost.

Therefore the primary DR-303 **recorded**
`exception_with_success_signal` dollar segment is currently `$0` across the
entire extended population.

That is a real evidence result, not an absent category or chart defect.

Historical core secondary adjusted-known evidence attributes
`$28.525409825839` to its 16 exception-with-success-signal trials.

Kimi's three such trials remain part of Kimi's unresolved trial-level
allocation; DR-303 must not distribute Kimi's provider-log remainder among
them.

The primary legend and exact table must retain this category even when its
recorded-dollar geometry has zero width.

## Known accounting gap

The fifth segment is the existing F1 arm-level `accountingGapUsd`.

It means:

    selected reviewed arm cost - recorded arm cost

For historical core arms, this gap may contain reconstructed dollars that
the historical trial source can secondarily associate with outcomes.

For Kimi K3, the gap is the difference between qualified retained-rate cost
and recorded trial cost, and trial-level allocation remains unresolved.

The gap must not be described as:

- invoice-level missing spend;
- provider-billed spend;
- an outcome bucket;
- entirely unresolved spend;
- zero-cost trials;
- a proportional allocation across outcomes.

## Missing versus unresolved evidence

`missingRecordedCostCount` and `unresolvedCostCount` are evidence counts,
not dollar buckets.

A missing recorded-cost row may still have a reconstructed adjusted-known
cost.

An unresolved row has no supported adjusted dollar amount in the retained
historical cost layer.

Therefore:

- missing does not mean `$0`;
- unresolved does not mean `$0`;
- unresolved row counts must remain visible;
- no synthetic unresolved dollar value may be added to the bar;
- the selected reviewed cost basis remains a known/qualified measure, not a
  claim of complete provider invoice spend.

## Per-arm reconciliation

For every historical core arm:

    recorded clean success
    + recorded normal failure
    + recorded exception failure
    + recorded exception-with-success-signal
    + F1 known accounting gap
    = F1 adjustedKnownCostUsd

For Kimi K3:

    recorded clean success
    + recorded normal failure
    + recorded exception failure
    + recorded exception-with-success-signal
    + 5.6071064 known accounting gap
    = 30.8143194 qualified retained-rate estimate

The implementation must fail closed if any arm does not reconcile exactly
under decimal arithmetic.

## Frozen scope totals

### Phase 3 core

| Segment | USD |
|---|---:|
| Recorded clean success | 607.88236925 |
| Recorded normal failure | 189.07357825 |
| Recorded exception failure | 23.81878125 |
| Recorded exception with success signal | 0 |
| Known accounting gap | 151.395116739198 |
| **Selected reviewed cost** | **972.169845489198** |

### Phase 3 extended

| Segment | USD |
|---|---:|
| Recorded clean success | 628.27639225 |
| Recorded normal failure | 192.79123825 |
| Recorded exception failure | 24.91431125 |
| Recorded exception with success signal | 0 |
| Summed arm-level known accounting gap | 157.002223139198 |
| **Summed selected arm costs** | **1002.984164889198** |

F1's authoritative extended scope-level qualified adjusted-cost estimate is:

`1002.9841648891979`

The difference between the exact summed arm values and F1's scope value is:

`0.0000000000001 USD`

This is within F1's existing `1e-12` reconciliation guard.

DR-303 must:

- preserve the exact F1 scope headline;
- preserve exact F1 per-arm values;
- not distribute the `1e-13` scope/arm serialization difference into any
  outcome or gap segment;
- disclose or test the existing tolerance rather than silently rewriting
  source decimals.

## Kimi K3 qualifications

Kimi K3 must remain visibly qualified:

- recorded trial cost: `$25.207213`;
- qualified retained-rate estimate: `$30.8143194`;
- known accounting gap: `$5.6071064`;
- missing recorded-cost rows: 10;
- unresolved cost rows: 10;
- outcome-cost allocation status: `unavailable`;
- trial allocation status: `unresolved`;
- cost confidence: `low`;
- arm/run allocation confidence: `low`;
- pricing-source provenance: `incomplete`;
- billing reconciliation:
  `not_invoice_level_or_provider_billed`.

DR-303 may classify the **recorded** Kimi dollars by exact frozen trial
outcome.

It must not claim that the `$5.6071064` provider-log remainder has been
allocated to Kimi outcomes.

## Presentation target

Primary surface: `/cost-coverage`.

DR-303 should live with the reviewed cost evidence, after the reviewed
headline/Kimi qualification material and before the optional operational
cost-provenance focus.

The page already has the authoritative reviewed scope selector.

Required behavior:

- `phase3-extended` remains the default;
- the DR-303 panel follows the page's selected reviewed scope;
- `phase3-core` remains the explicit historical alternate;
- no independent dynamic/latest/all-imported scope is introduced.

## Primary visualization

Use horizontal stacked dollar bars.

Required geometry:

- one row per arm;
- shared dollar scale across visible arms;
- friendly arm/model label primary;
- canonical arm ID visible;
- four recorded-outcome segments;
- one known-accounting-gap segment;
- selected reviewed arm total visible;
- no normalization that hides absolute spend differences.

Required fixed legend:

1. Recorded clean-success spend
2. Recorded normal-failure spend
3. Recorded exception-failure spend
4. Recorded exception-with-success-signal spend
5. Known accounting gap

The exception-with-success-signal category must remain present in the
legend/table even though its current recorded-dollar geometry is zero.

## Accessible exact table

Provide a visible non-hover table containing the same primary values.

At minimum expose per arm:

- friendly label;
- canonical arm ID;
- recorded clean-success dollars;
- recorded normal-failure dollars;
- recorded exception-failure dollars;
- recorded exception-with-success-signal dollars;
- total recorded dollars;
- known accounting gap;
- selected reviewed cost;
- selected cost basis;
- missing recorded-cost row count;
- unresolved cost row count;
- cost confidence;
- allocation qualification.

Shares may be shown, but dollar values remain primary.

Where historical adjusted-outcome values are shown as secondary evidence,
label them explicitly as adjusted-known and never add them into the primary
five-part total.

## Evidence links

Do not create approximate cost links.

Existing exact reviewed arm/run cost-provenance links may be reused only
when they preserve:

- selected reviewed scope;
- exact arm ID;
- exact frozen selected run where required;
- existing fail-closed no-match behavior.

A segment must not link to a destination that cannot reproduce its exact
predicate.

Plain evidence is preferable to an approximate operational link.

## Fail-closed requirements

The DR-303 data/model layer must reject:

- source-hash mismatch;
- duplicate trial IDs;
- missing expected trial IDs;
- extra trial IDs;
- core/Comprehensive Review membership mismatch;
- Kimi/core overlap;
- arm or task identity mismatch;
- arm population other than 60 reviewed trials per arm;
- unexpected outcome bucket;
- Kimi outcome other than the four expected current buckets;
- recorded bucket sums that disagree with F1 recorded arm cost;
- missing/unresolved counts that disagree with F1;
- five-part per-arm totals that disagree with the arm's selected reviewed
  cost basis;
- unsupported Kimi adjusted-outcome allocation;
- DB/R2/HTTP/live/latest-run fallback;
- conversion of unresolved rows into invented dollars.

## Implementation structure

### DR303-A — contract

This document plus the bounded pointer/status update in the parent dashboard
revision specification.

No dashboard behavior changes.

### DR303-B — reviewed spend source and pure quantitative model

Implement the minimum reviewed-source/model layer required to reproduce this
contract.

Requirements:

- preserve F1 as authoritative for reviewed arm/scope cost facts;
- reuse existing validated Comprehensive Review access where practical;
- bind the historical 900-row trial-cost source to its exact retained hash;
- avoid runtime database, R2, HTTP, live-analysis, or latest-run dependence;
- preserve decimal text/decimal arithmetic for reconciliation;
- expose exact per-arm and scope facts;
- fail closed on every contract violation above.

Do not regenerate or rewrite the historical Phase 3 result sources.

Focused tests must cover:

- 900/960/60 exact population identities;
- exact core membership equality;
- exact arm/task identity;
- 15 core arms plus Kimi;
- four outcome buckets only;
- exact recorded bucket reconciliation for every arm;
- exact F1 missing/unresolved count agreement;
- exact five-part per-arm reconciliation;
- Kimi 44/5/8/3 outcome counts;
- Kimi `$25.207213` recorded total;
- Kimi `$5.6071064` gap;
- Kimi `$30.8143194` qualified total;
- Kimi adjusted-outcome allocation remains unavailable;
- exception-with-success-signal primary recorded spend remains zero rather
  than absent;
- core and extended frozen global totals;
- existing F1 `1e-12` scope reconciliation tolerance;
- no synthetic unresolved dollars;
- no operational fallback.

### DR303-C — presentation integration

Add the accessible stacked-dollar presentation and equivalent table to Cost
Coverage.

Reuse existing presentation, friendly-label, terminology, scope, and exact
cost-provenance-link conventions where they already satisfy the contract.

No new chart dependency is required.

Do not modify DR-301 quantitative logic merely to implement DR-303.

### DR303-D — validation and production acceptance

After implementation:

- focused model/component tests;
- dashboard Node suite;
- Python suite;
- typecheck;
- one production build;
- `make check`;
- `make secret-scan`;
- `git diff --check`;
- protected-boundary inspection;
- production route check;
- bounded production manual visual review at 1920px, 1440px, and 1280px;
- documentation closeout only after acceptance.

Do not rerun benchmarks, provider probes, migration 009, Supabase writes,
R2 writes, F1 generation, Comprehensive Review generation, J2 generation,
or historical cost-report generation.

## Protected boundaries

DR-303 must not modify:

- `results/manual_verification/**`;
- frozen Phase 1/2/3 result evidence;
- existing reviewed F1 comparison JSON;
- existing generated F1 comparison mirror;
- reviewed run-selection artifacts;
- arm configurations;
- migrations;
- canonical failure-taxonomy registry/generated mirror;
- J2 classifier/generator/evidence;
- DR-302 failure-composition semantics.

A new DR-303-specific derived dashboard module or generated presentation
artifact is permitted only if it is deterministic, source-hash-bound,
reviewable, and does not replace any frozen source of truth.

## Completion boundary

DR-303 is complete only when:

- exact frozen population/membership contracts pass;
- every arm reconciles its primary five-part stack;
- recorded and adjusted/qualified cost semantics remain visibly distinct;
- missing/unresolved evidence is not converted to zero dollars;
- Kimi's provider-log remainder remains visibly unallocated by outcome;
- the zero recorded exception-success segment remains visible as a real
  evidence result;
- scope-level decimal reconciliation preserves F1 rather than rewriting it;
- accessible chart/table facts agree exactly;
- production visual acceptance passes;
- protected/frozen boundaries remain unchanged.

**Disposition:** DR-303 contract defined 2026-08-19; implementation pending.
