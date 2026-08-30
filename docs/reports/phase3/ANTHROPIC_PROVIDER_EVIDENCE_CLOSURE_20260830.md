# Anthropic Provider Evidence Closure — 2026-08-30

## Status

Anthropic provider-evidence review is closed for the four current retained
Phase 3 Anthropic arms:

1. `router-anthropic-fable-5`
2. `router-anthropic-haiku-sanitized`
3. `router-anthropic-opus`
4. `router-anthropic-sonnet`

This closure is deliberately **documentation-only**.

No Anthropic provider-evidence rows are synthesized or ingested into the
normalized provider-evidence tables because the reviewed retained corpus
contains no first-party Anthropic provider source for the selected runs, and
the currently available project credential set does not contain the Anthropic
Admin API key required by the first-party collector.

This does **not** mean that Anthropic lacks provider usage or cost APIs.
The repository collector explicitly supports both. The limitation in this
review is retained evidence plus currently available credentials and
allocation provenance.

No migration, importer application, database mutation, network collection,
historical benchmark-result rewrite, or fabricated zero-usage/zero-cost record
is part of this closure.

## Reviewed private evidence

The closure relies on the following ignored, private review artifacts.

| Review artifact | SHA-256 |
| --- | --- |
| `.run/review/all-provider-corpus-reaudit-v2-20260828-01.json` | `3b0a912aa1e89414aa8719c1416e6a49ce6c5dd00131aa7f7b302ace24804f20` |
| `.run/review/all-provider-archive-metadata-map-20260828-01.json` | `51acf7cecd0476faf811d0337bea38ce794bd8b5ee8b226e011bb41a139660ac` |
| `.run/review/anthropic-provider-api-run-window-inventory-20260826-01.json` | `f588048c9bda588a5f42e39f6787ec7a500243d541d79cd952f7bd1f31c18e69` |
| `.run/review/cross-provider-consistency-contract-20260828-01.json` | `a7d6f1518a97b922d8c2a087c76f06e216251c629a59e27bd5ee8952085abeb0` |
| `.run/review/cross-provider-evidence-inventory-20260828-01.json` | `7c3ffad57afdfa4c672152178281699652f14b4d739336ba793076c603b3ac24` |

Committed reviewed comparison:

- `results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json`
- SHA-256:
  `39bf269938ae2792d045449b2cde23749e8442c6b0978addda9ac3b59e41a968`

First-party evidence collector:

- `scripts/collect_provider_evidence.py`
- SHA-256:
  `aafe945ed043435131aa1b51a57048ac548bcaeac23641392827453a68afda43`

The archive metadata map is retained as supporting inventory context. Its lack
of Anthropic scalar references is not treated by itself as proof of absence.
The explicit retained-corpus absence finding comes from the v2 corpus
re-audit.

## Canonical selected runs

| Arm | Backend model | Selected run |
| --- | --- | --- |
| `router-anthropic-fable-5` | `claude-fable-5` | `router-anthropic-fable-5/2026-07-11__12-15-55` |
| `router-anthropic-haiku-sanitized` | `claude-haiku-4-5-20251001` | `router-anthropic-haiku-sanitized/2026-07-12__03-25-22` |
| `router-anthropic-opus` | `claude-opus-4-7` | `router-anthropic-opus/2026-07-01__12-15-57` |
| `router-anthropic-sonnet` | `claude-sonnet-4-6` | `router-anthropic-sonnet/2026-06-27__01-30-11` |

These are the current reviewed identities. Historical references to
`router-anthropic-haiku` must not replace the current selected
`router-anthropic-haiku-sanitized` identity.

## Retained-corpus finding

The v2 all-provider corpus re-audit reports the following Anthropic state:

- selected arm count: `4`
- archive explicit raw absence: `true`
- archive member count: `0`
- raw first-party member count: `0`
- derived member count: `0`
- unclassified member count: `0`
- metadata-bound raw member count: `0`
- raw hash match count: `0`
- database provider-source count: `0`
- normalized selected-arm count: `0`

The cross-provider consistency contract independently classifies all four
selected Anthropic arms as:

`accepted_absence_anthropic_not_normalized`

Its reason is that selected-run reporting retains rate-reconstructed cost
evidence, but no first-party Anthropic provider evidence is normalized into
the provider-evidence tables.

The expected and observed Anthropic accepted-absence counts are both `4`.

## Existing selected-run accounting

Absence of normalized first-party provider evidence does not erase the
retained benchmark accounting.

The current reviewed layer contains:

| Arm | Selected retained cost | Basis | Relation | Provider-billed selected-run cost |
| --- | ---: | --- | --- | --- |
| `router-anthropic-fable-5` | `$64.80504500` | `provider_rate_reconstructed_retained_usage` | `exact` | unavailable |
| `router-anthropic-haiku-sanitized` | `$16.70224485` | `provider_rate_reconstructed_retained_usage` | `exact` | unavailable |
| `router-anthropic-opus` | `$50.28831125` | `provider_rate_reconstructed_retained_usage_lower_bound` | `lower_bound` | unavailable |
| `router-anthropic-sonnet` | `$38.38591710` | `provider_rate_reconstructed_retained_usage_lower_bound` | `lower_bound` | unavailable |

The reviewed provider billing status for all four is
`provider_invoice_unavailable`.

Fable and Haiku therefore retain exact cost reconstructions for the retained
selected-run usage geometry.

Opus and Sonnet remain lower bounds. Their exception paths contain unresolved
API-response/accounting gaps, so the retained reconstruction must not be
promoted to an exact provider-billed amount.

None of these reconstructed costs is reclassified here as a first-party
provider invoice or provider-observed selected-run billing value.

## First-party Anthropic API capability

The repository collector explicitly supports Anthropic first-party usage and
cost APIs.

Collector capability:

- actual usage API: `true`
- actual cost API: `true`
- required credential: `ANTHROPIC_ADMIN_API_KEY`
- usage allocation dimensions:
  - `api_key_id`
  - `workspace_id`
  - `model`
- cost allocation dimensions:
  - `workspace_id`
  - `description`

Known collector limitations include:

- `admin_api_key_required`
- `standard_cost_api_daily_granularity`
- `standard_cost_api_not_api_key_allocable`
- `priority_tier_cost_not_in_standard_cost_endpoint`
- `usage_run_attribution_requires_distinguishable_allocation_dimensions`
- `cost_run_attribution_requires_workspace_day_isolation_or_independent_allocation`
- `overlapping_indistinguishable_runs_must_not_be_allocated`

The previously prepared four-run query inventory also warns that daily
provider cost can include non-benchmark Anthropic activity. Therefore an Admin
API response would still require allocation review before any selected-run
promotion.

## Credential boundary

The ignored `.secrets/anthropic.env` file was inspected for variable names
only.

Observed credential shape:

- `.secrets/anthropic.env` exists;
- `ANTHROPIC_API_KEY` variable name is present;
- `ANTHROPIC_ADMIN_API_KEY` variable name is absent;
- neither Anthropic key was loaded in the current shell during the closure
  validation.

The ordinary inference key is not treated as a substitute for the Admin API
credential.

No credential values are committed or reproduced by this report.

## Forced-clean collector validation

The Anthropic collector was exercised with both Anthropic credential
variables explicitly removed from the process environment.

Plan-mode result:

- provider: `anthropic`
- required credential: `ANTHROPIC_ADMIN_API_KEY`
- credential available: `false`
- collection eligible: `false`
- limitation code: `missing_admin_api_key`
- network requests performed: `false`

Collection-mode refusal:

- exit code: `2`
- status: `provider_evidence_unavailable`
- collection status: `unavailable`
- limitation code: `missing_admin_api_key`
- network requests performed: `false`
- provider evidence output created: `false`

This validates the credential boundary without contacting Anthropic and
without creating provider evidence.

## No-ingestion decision

The reviewed state does not support creation of Anthropic normalized
first-party evidence for these selected runs.

This closure therefore does not create or synthesize:

- provider evidence sources;
- provider usage evidence;
- provider pricing evidence;
- provider cost evidence;
- usage reconciliations claiming first-party support;
- cost reconciliations claiming provider-billed selected-run authority;
- evidence-promotion gates based on unavailable first-party evidence.

It also does not create zero-valued usage or cost rows. Lack of first-party
evidence is represented as absence, not as evidence of zero usage or zero
cost.

This is a deliberate non-ingestion decision, not a missing execution step.

## Historical accounting preservation

Existing retained benchmark/accounting evidence remains valid within its
documented scope.

In particular:

- retained trial and aggregate usage remains benchmark evidence;
- official-rate reconstruction remains usable where already reviewed;
- Fable and Haiku retain exact reconstructed selected costs;
- Opus and Sonnet retain lower-bound reconstructed selected costs;
- historical internal accounting is not silently rewritten;
- no retained accounting value is promoted to provider-billed authority by
  this closure.

Historical June reconciliation language such as
`accepted-internal-no-provider-export` remains historical context. It should
not be read as a claim that Anthropic has no first-party API capability.

## Cross-provider interpretation

The durable cross-provider state for these four arms is:

`accepted_absence_anthropic_not_normalized`

That state means:

1. the arm and selected run are valid reviewed benchmark entities;
2. retained accounting evidence exists;
3. no retained first-party Anthropic source currently supports normalized
   selected-run provider evidence;
4. the currently available credential set cannot collect the required
   first-party evidence because it lacks an Anthropic Admin API key; and
5. no unsupported provider-evidence row should be manufactured to make the
   provider matrix appear complete.

Dashboard and report surfaces should preserve the distinction between:

- retained/reconstructed benchmark cost;
- provider-observed usage;
- provider-billed selected-run cost; and
- accepted provider-evidence absence.

## Privacy and retention

No raw Anthropic provider export is committed.

No credential value is committed.

Private review artifacts remain under ignored `.run/review` storage and are
referenced only by path and SHA-256.

The report contains only sanitized arm/model/run identifiers, reviewed
aggregate accounting values already present in repository reporting, collector
capability metadata, and private-audit hash provenance.

## Reopening criteria

Anthropic provider-evidence normalization should be reopened if materially
stronger first-party evidence becomes available, for example:

- access to a valid `ANTHROPIC_ADMIN_API_KEY`;
- a first-party Anthropic usage export covering the selected-run windows;
- a first-party Anthropic billing export with a reviewable allocation bridge;
- usage records whose API-key/workspace/model dimensions distinguish the
  selected run;
- cost evidence where workspace/day isolation or another independent bridge
  supports selected-run allocation.

Possession of an Admin API key alone would not automatically justify
promotion. Any collected usage/cost evidence must still pass allocation,
overlap, privacy, and provenance review.

Any reopening should use a new reviewed evidence pass with source hashes,
dry-run/read-only validation, allocation checks, and guarded database
application if normalization is ultimately justified.

## Closure

Anthropic provider-evidence normalization is closed for the current retained
evidence and credential set.

The durable conclusion is:

- four canonical Anthropic selected arms remain in benchmark accounting;
- retained reconstructed costs remain available with their existing exact or
  lower-bound semantics;
- no retained first-party Anthropic provider source exists for the selected
  runs in the reviewed corpus;
- the current project credential set lacks the required Anthropic Admin API
  key;
- first-party Anthropic usage and cost APIs do exist and are supported by the
  collector;
- no provider network request was made during closure validation;
- no provider evidence was fabricated;
- no normalized Anthropic provider-evidence row is added;
- no database mutation is required;
- future normalization requires stronger first-party evidence plus a valid
  selected-run allocation bridge.
