# Dashboard DR-302 Failure Composition Plan — 2026-08-19

**Status:** Implementation contract complete; dashboard implementation pending
**Repository:** `cc-deepseek-bench`
**Branch:** `dashboard-dr302-failure-composition`
**Base:** `b67e7d6b42eb48a6fa8356ef54b84497f4a8b723`
**Requirement:** DR-302 — Failure composition by arm

## Purpose

Implement the requested failure-composition-by-arm view without rewriting
frozen benchmark history, regenerating J2, collapsing independent taxonomy
axes into raw truth, or mixing the reviewed Phase 3 population with dynamic
or all-imported evidence.

DR-303 spend decomposition is explicitly outside this branch.

## Authoritative population

DR-302 uses only the frozen Phase 3 extended reviewed population:

- scope: `phase3-extended`;
- 16 arms;
- 960 exact trial IDs;
- 60 reviewed trials per arm;
- source Comprehensive Review:
  `results/manual_verification/comprehensive_review_20260731`;
- source J2 taxonomy:
  `results/manual_verification/failure_taxonomy_20260813`;
- source and J2 rows join by exact `trial_id`;
- both frozen sources must contain exactly the same 960 trial IDs.

No Supabase, R2, live-analysis, all-imported, latest-run, or runtime
classifier fallback is permitted.

The existing manifest/hash validation remains authoritative. DR-302 must not
regenerate or modify either frozen source.

## Chart denominator

The composition denominator is raw benchmark failure:

`raw_outcome == "failure"`

Current frozen totals:

- raw failure: 370;
- not recorded: 28;
- success: 562.

The 28 `not_recorded` trials are not failures and are excluded from the
stack. The 562 successful trials are also excluded.

The frozen evidence additionally contains 19 successful trials with
timeout-after-meaningful-activity / timeout-after-meaningful-progress
evidence. They remain successful raw outcomes and are not included in a
failure-composition denominator.

The chart must disclose these exclusions rather than silently treating
"non-success" as equivalent to failure.

## Independent source axes versus display partition

The accepted Comprehensive Review and J2 contracts keep raw outcome,
execution validity, response path, activity, verifier failure, policy,
termination, trajectory, confidence, and evidence completeness as
independent axes.

DR-302 nevertheless requests one stacked composition. Therefore DR-302
defines a display-only partition over raw failures.

This partition:

- does not alter any source diagnosis;
- does not establish classifier precedence;
- does not use taxonomy registry display order as precedence;
- does not overwrite raw truth;
- exists only to make every eligible raw-failure trial contribute to exactly
  one DR-302 segment.

## Display-partition selection precedence

For a trial with `raw_outcome == "failure"`, assign the first matching
display bucket below:

1. `provider_policy_refusal`
   - source `policy_disposition == "provider_policy_refusal"`.

2. `invalid_response_path`
   - source `execution_validity == "invalid_response_path"`.

3. `missing_required_output`
   - source `failure_subtype == "missing_required_output"`.

4. `extraneous_output_artifacts`
   - source `failure_subtype == "extraneous_output_artifacts"`.

5. `timeout_after_meaningful_activity`
   - source `activity_subtype == "timeout_after_meaningful_activity"`.

6. `verifier_task_failure`
   - J2 `verifier_failure_category.value != "none"`.

7. `unknown_or_incomplete_evidence`
   - any remaining raw failure.

This ordering is a DR-302 presentation rule only.

### Why invalid response path precedes missing output

The frozen source contains four raw failures with:

- `execution_validity == "invalid_response_path"`;
- `failure_subtype == "missing_required_output"`.

J2 further refines their public response paths into specific empty-response
subclasses and assigns a broader `missing_or_wrong_output` verifier category.

If missing output were selected first, DR-302's requested invalid-response-
path segment would become zero despite four accepted source classifications.

DR-302 therefore selects invalid response path first while retaining every
underlying source value unchanged.

### Why verifier/task failure is selected after output-specific buckets

J2's `missing_or_wrong_output` verifier category intentionally combines the
source's missing-required-output and extraneous-output-artifact cases.

DR-302 explicitly requests those source categories separately. The specific
source buckets are therefore selected before the broader J2 verifier bucket.

## Frozen expected global partition

In DR-302 display order:

| Bucket | Count |
|---|---:|
| Verifier/task failure | 167 |
| Timeout after meaningful activity | 127 |
| Provider-policy refusal | 9 |
| Invalid response path | 4 |
| Missing required output | 7 |
| Extraneous output artifacts | 22 |
| Unknown / incomplete evidence | 34 |
| **Total raw failures** | **370** |

The implementation must fail closed if the global partition does not sum to
the exact raw-failure count.

## Unknown / incomplete evidence semantics

`unknown_or_incomplete_evidence` is a conservative residual label, not an
alias for `evidence_complete == False`.

The current 34 frozen residual failures are:

- 34 source `execution_validity == "unknown"`;
- 34 source `activity_subtype == "activity_unknown"`;
- 34 J2 `response_path_class.value == "unknown"`;
- 34 J2 `verifier_failure_category.value == "none"`;
- 34 manual-review-required trials.

Within those 34:

- 27 are evidence-complete, high-confidence
  `trajectory_disposition == "no_substantive_attempt"`;
- 7 are evidence-incomplete, medium-confidence
  `trajectory_disposition == "indeterminate"`.

Public copy must explain that "unknown" means retained evidence does not
justify one of the preceding DR-302 failure buckets; it does not imply that
all evidence is missing.

## Presentation target

Primary surface: `/trial-quality`.

Place the DR-302 view with the frozen J2 evidence material, before the
operational/all-imported quality sections.

Required presentation:

- heading clearly identifies the frozen Phase 3 extended population;
- 16 arm rows;
- friendly arm/model label primary;
- canonical arm ID retained visibly;
- horizontal stacked counts;
- fixed category legend;
- accessible non-hover table containing the same counts;
- table also exposes each category's share of that arm's raw failures;
- per-arm category counts sum exactly to that arm's raw-failure count;
- global category counts sum exactly to 370;
- no category is represented as zero merely because evidence is unavailable;
- explicit note states that 28 not-recorded and 562 successful trials are
  outside the failure denominator;
- explicit note states that 19 successful timeout-after-meaningful-activity
  cases remain successful and are excluded.

Counts, not normalized shares, are the primary chart geometry so differences
in total failures by arm remain visible. Shares may be shown in the
accessible table.

## Evidence links

Do not create approximate links.

Arm identity may link to the existing exact frozen reviewed-arm evidence
population.

A category segment/count may link only if the destination reproduces the
exact DR-302 partition predicate. If no existing destination can express the
partition exactly, keep the count as plain evidence rather than substituting
a similarly named operational or taxonomy filter.

## Implementation structure

### DR302-A — contract

This document and a pointer from the parent revision specification only.

No dashboard behavior.

### DR302-B — pure data model and tests

Add a dedicated DR-302 model under `apps/dashboard/src/lib/`.

The quantitative builder must:

- accept validated Comprehensive Review rows and validated J2 rows;
- exact-join by `trial_id`;
- require 960 unique rows on both sides;
- require identical trial-ID membership;
- require the Phase 3 extended 16-arm population;
- preserve canonical arm IDs;
- apply raw-failure eligibility before category assignment;
- apply only the display precedence documented here;
- expose explicit excluded success and not-recorded counts;
- expose per-arm and global exact counts;
- fail closed on duplicates, missing rows, unexpected membership, or
  partition mismatch.

Tests must cover:

- exact frozen 960/960 join;
- 16 arms and 60 reviewed trials per arm;
- 370 eligible raw failures;
- exact seven-bucket global counts;
- invalid-response-path precedence over missing output;
- missing/extraneous output precedence over broader verifier category;
- successful timeout anomaly exclusion;
- not-recorded timeout exclusion;
- residual unknown/incomplete semantics;
- every per-arm partition sums to raw failures;
- category ordering is presentation-only and does not mutate J2;
- frozen source hashes/files remain unchanged;
- no DB, R2, HTTP, live-analysis, or runtime-classifier fallback.

### DR302-C — presentation integration

Add the accessible stacked-count presentation and equivalent table to
Trial Quality.

Reuse existing dashboard presentation conventions where appropriate, but do
not couple DR-302 quantitative derivation to the DR-301 cost/Pareto data
model.

No new chart dependency is required.

### DR302-D — validation and production acceptance

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
- bounded manual visual review at 1920px, 1440px, and 1280px.

Do not rerun benchmarks, provider probes, migration 009, Supabase writes,
R2 writes, J2 generation, or frozen-review generation.

## Protected boundaries

DR-302 must not modify:

- `results/manual_verification/**`;
- frozen Phase 1/2/3 results;
- arm configurations;
- migrations;
- canonical failure-taxonomy registry/generated mirror;
- J2 classifier or generator;
- reviewed Phase 3 comparison/run-selection artifacts;
- DR-303 spend-decomposition behavior.

## Completion boundary

DR-302 is complete only when:

- the frozen quantitative contract passes;
- the accessible chart/table reproduces the same facts;
- all seven requested categories remain distinct;
- the denominator is visibly raw failure rather than generic non-success;
- unknown/incomplete wording preserves the 27 evidence-complete unknown cases;
- production visual acceptance passes;
- protected/frozen boundaries remain unchanged.

DR-303 remains separate future work.
