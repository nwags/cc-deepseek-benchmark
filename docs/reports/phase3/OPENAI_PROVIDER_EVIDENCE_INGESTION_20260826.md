# OpenAI Provider Evidence Database Ingestion

**Application date:** 2026-08-26
**Provider:** OpenAI
**Scope:** selected Phase 3 full sweeps for `router-gpt-5.4` and `router-gpt-5.5`

## Purpose

This record documents permanent ingestion of the previously reviewed OpenAI
provider evidence into the Phase 3 provider-evidence and reconciliation schema.

The ingestion does not rewrite historical benchmark trials, benchmark runs,
arm runs, historical cost-coverage rows, or frozen reviewed result artifacts.

The authoritative evidence findings remain documented in:

`docs/reports/phase3/OPENAI_FULL_SWEEP_PROVIDER_COST_RECONCILIATION_20260821.md`

## Application code checkpoint

Permanent application was performed from the exact reviewed Git checkpoint:

- commit:
  `b3f702858605e9b8b42e1538b6774d6936bb94ff`
- commit subject:
  `Add guarded OpenAI provider evidence application`
- committed ingestion-script SHA-256:
  `43b3e459dea94d7d76e8ea1c8d752628e262cb7225621fc9292b394eed3d4e36`

The application implementation:

- requires an explicit `--apply`;
- acquires a PostgreSQL advisory transaction lock;
- refuses application unless the provider-evidence target state is empty;
- distinguishes an already-correct OpenAI state from partial or unexpected
  state;
- verifies the inserted evidence inside the transaction before committing;
- has one explicit commit point;
- verifies the committed state again through an independent second database
  connection;
- refuses duplicate permanent application once the exact OpenAI state exists.

## Reviewed normalized inputs

The normalized OpenAI evidence inputs were hash-pinned before application:

| Input | SHA-256 |
| --- | --- |
| `openai_provider_source_manifest_20260821.csv` | `2c458c3122c012b97aea5bc8c7a14d566dfae69292263add9d7f4bb3c8a901f8` |
| `openai_provider_activity_20260821.csv` | `69004a2c5d13aa40091122a818047d1fbd44a23bad611f7912abf985302ebc28` |
| `openai_provider_reconciliation_20260821.csv` | `5da12494743dc7265c3c08ffc08aa988451fbc308940453cf9b3bc6cdf71e452` |

The reviewed generated ingestion plan had SHA-256:

`17e2617251be2722f3306ba24bad62835634b75061bbd1a7d5044f184953e20e`

The plan hash remained unchanged when permanent application support was added.

## Pre-application verification

A real-database `--check-only` preflight immediately before permanent
application reported:

- `status = ready`
- `target_state = empty`
- `commit_state = not_committed`
- all nine provider-evidence/reconciliation target tables at zero rows.

Final pre-application check evidence SHA-256:

`d42bed8d2d597c115e097e66465e686edff8c6cdaef4b52dde1946027444ecf6`

The revised rollback-only implementation was also exercised against the real
database before permanent application. It verified the complete planned state
inside a transaction and then proved zero persistence from a second connection.

Rollback-only evidence SHA-256:

`971e8fe4fb4d16bc72e0e868adce2a38a381208063988161aefac1cc5eef3435`

## Permanent application result

The one-time permanent application exited successfully and reported:

- `status = applied`
- `mode = apply`
- `commit_state = committed`
- `target_state = exact_openai_state`
- advisory lock: pass
- empty-target preflight: pass
- canonical run resolution: pass
- transactional insert: pass
- transactional verification: pass
- commit: pass
- second-connection verification: pass

Application evidence SHA-256:

`4f03530604c4e123f2192035bbe2a8fc36e6e3de3e7e576f652d52765dd5c366`

## Canonical selected arm runs

| Arm | Canonical arm-run ID |
| --- | --- |
| `router-gpt-5.4` | `b640e008-88be-4e8a-9fc8-4d4f00fd6a60` |
| `router-gpt-5.5` | `ed133fd0-ea3f-45b9-a748-2b8d19858d3c` |

## Persisted provider sources

| Evidence kind | Provider reference | SHA-256 |
| --- | --- | --- |
| billing export | `cost_2026-06-01_2026-07-01.csv` | `04cea7cd630c0dd7a4aef144d005eb3640a70072f24f4c6a5132016ea3bfd12d` |
| usage export | `completions_usage_2026-06-01_2026-07-01.csv` | `9c4dc05dd36164ba34cb387f9ca97fb63255b8ac0aeff2782b00784a6cf2d108` |

Both sources are represented by sanitized provenance and reviewed SHA-256
identity. The private raw provider-export bytes are not committed to Git.

## Persisted reconciliations

| Arm | Provider model | Ordinary input | Cache-read input | Cache-creation input | Output | Requests | Selected cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `router-gpt-5.4` | `gpt-5.4-2026-03-05` | 1,973,793 | 30,833,664 | unavailable | 1,143,269 | 1,256 | $29.7919335 |
| `router-gpt-5.5` | `gpt-5.5-2026-04-23` | 2,193,214 | 33,033,728 | unavailable | 704,066 | 1,480 | $48.604914 |

For both selected arms:

- model identity is matched;
- usage authority is `provider_aggregate_usage`;
- usage validation is `validated_exact`;
- selected cost basis is `provider_billed`;
- selected cost relation is `exact`;
- cost validation is `validated_exact`.

OpenAI provider evidence exposes cached versus uncached input but does not
establish a separate Anthropic-style cache-creation token dimension.
Cache-creation input therefore remains NULL rather than being fabricated as
zero.

The provider exports establish exact selected arm-run aggregates. They do not
establish per-trial or success/failure cost allocation. No such allocation was
created during ingestion.

## Persisted table counts immediately after application

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 2 |
| `benchmark_provider_usage_evidence` | 2 |
| `benchmark_provider_pricing_snapshots` | 0 |
| `benchmark_provider_cost_evidence` | 2 |
| `benchmark_usage_reconciliations` | 2 |
| `benchmark_usage_reconciliation_sources` | 2 |
| `benchmark_cost_reconciliations` | 2 |
| `benchmark_cost_reconciliation_sources` | 2 |
| `benchmark_evidence_promotion_gates` | 0 |

At the time of this ingestion, OpenAI was the first provider permanently
represented in these tables.

## Independent post-application verification

A separate `--check-only` execution after the permanent commit reported:

- `status = already_applied`
- `mode = check-only`
- `target_state = exact_openai_state`
- `commit_state = not_committed`
- persisted table counts exactly matching the reviewed write plan.

Post-application check evidence SHA-256:

`4aa0e83c23b041bf22d173789e0fdab2fa0589f29ab444bbb7dcf13651241ed2`

A subsequent read-only SQL audit independently re-read the source identities,
usage reconciliation, cost reconciliation, and global evidence-table counts.

Read-only post-application audit SHA-256:

`4c04a45eee534acf5a86beb20c702d726c2307fd1aeb0575a8baae82438210bc`

## Resulting authority boundary

The database now carries exact provider-side evidence for the two selected
OpenAI Phase 3 full sweeps.

The permanent ingestion changes the evidence available to current reporting;
it does not rewrite the historical benchmark record.

Specifically:

- exact OpenAI provider-billed arm totals supersede historical harness-derived
  cost estimates for decision-oriented current reporting;
- historical harness and reviewed costs remain provenance;
- aggregate provider usage is authoritative only at the supported arm-run
  scope;
- trial-level and outcome-level spend remain unavailable;
- benchmark execution success remains separate from usage and cost validity.
