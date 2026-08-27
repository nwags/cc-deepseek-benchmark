# Gemini Provider Evidence Ingestion — 2026-08-27

## Status

Gemini historical provider-evidence normalization and database ingestion is complete.

The permanent ingestion was performed from reviewed and pushed commit:

- commit: `f00bc4919461ba0ef22c92b99f1c1b839ea206d2`
- subject: `Add Gemini provider evidence ingestion`

The ingestion was subsequently verified by:

1. the importer's read-only postcheck; and
2. an importer-independent direct-SQL audit.

Do not rerun the Gemini `--apply` path. Any future change to this
normalized state requires an explicit reviewed repair/addition plan.

## Reviewed implementation

- importer:
  `scripts/ingest_gemini_provider_evidence.py`
- importer SHA-256:
  `0bfeedbf7a9a0889daffa7b5eb5ec4ad4dbb2c60e707f824b194fe17b3a70ad0`
- tests:
  `tests/test_ingest_gemini_provider_evidence.py`
- tests SHA-256:
  `f1f183b5f51ba5e636fc7fd0cd0b6d4e6651ffb6b6e727e8b1a2602e645c2556`

Reviewed private plan:

- `.run/review/gemini-provider-evidence-plan-20260826-02.json`
- SHA-256:
  `10fae2e8984b8cec14a0a22d04f95e3020acc7894f43f86d530033c9649de9d5`

The private `.run/review` files are audit evidence and remain ignored;
their hashes are recorded here for durable provenance.

## Canonical selected runs

### Gemini 3.1 Pro

- arm: `router-gemini-3.1-pro`
- arm-run UUID:
  `96642f57-b684-40bd-9a5e-8111383df340`
- selected run:
  `router-gemini-3.1-pro/2026-06-30__14-57-05`
- backend model:
  `gemini-3.1-pro-preview`

### Gemini Flash

- arm: `router-gemini-flash`
- arm-run UUID:
  `873394f6-e9e7-465e-8028-08ab219ff18a`
- selected run:
  `router-gemini-flash/2026-06-27__01-30-20`
- backend model:
  `gemini-3.5-flash`

## Provider evidence semantics

The retained Google provider evidence contains one shared Gemini API
billing subtotal:

- unrounded amount: `$26.371228`
- cost kind: `account_spend`
- allocation scope: `account_window`
- completeness status: `complete`
- selected `arm_run_id`: `NULL`
- selected provider model: `NULL`

This provider amount is intentionally normalized exactly once.

It is **not** allocated to either selected Gemini arm and is **not**
used as `provider_billed_cost_usd` for either selected run.

The retained Google billing evidence lacks selected-run model/token
detail. Therefore:

- normalized provider usage evidence rows: `0`
- provider-observed model on selected reconciliations: `NULL`
- selected harness/session usage is not relabeled as provider usage
- configured/reviewed model identity is not relabeled as provider
  observation

Detailed AI Studio model/token logging was not available for the
historical provider evidence.

## Selected usage and cost reconciliation

### Gemini 3.1 Pro

Validated selected harness usage:

- input tokens: `25,122,141`
- cached input tokens: `20,368,769`
- output tokens: `509,693`

The selected run is supported by the retained R2 trajectory audit:

- trajectories: `60`
- retained model responses: `930`
- maximum reviewed prompt: `66,438` tokens
- all reviewed requests were within the applicable reviewed
  `<=200K` request tier

Selected cost:

- provider billed cost: unavailable
- provider-rate reconstructed cost: `$19.6968138`
- selected cost: `$19.6968138`
- selected basis:
  `provider_rate_reconstructed_harness_usage_validated`
- selected relation: `estimate`
- validation: `validated_qualified`

This is a qualified provider-rate reconstruction, not a claim of
Google provider-billed exact cost.

### Gemini Flash

Retained selected harness usage:

- input tokens: `17,250,634`
- cached input tokens: `10,792,465`
- output tokens: `534,977`

Usage/cost metadata is retained for `56/60` selected trials.

Four selected trials have no token metadata, and the selected R2
trajectory archive is unavailable. Missing usage or cost is not
synthesized as zero.

Selected cost:

- provider billed cost: unavailable
- retained provider-rate reconstruction: `$16.12091625`
- selected cost: `$16.12091625`
- selected basis: `lower_bound_provider_evidence`
- selected relation: `lower_bound`
- validation: `validated_qualified`

This is a strict retained-accounting lower bound; additional spend from
the four unresolved trials may exist.

## Pre-apply verification

### Read-only preflight

Audit:

- `.run/review/gemini-provider-evidence-check-only-20260827-01.json`
- SHA-256:
  `1d9407e419818673cb4ae4b56af582f0994b0e8848c8096e05dcb51aabdb0547`

Result:

- exit: `0`
- status: `ready`
- target state: `gemini_empty`
- all nine Gemini-scoped target counts: `0`
- canonical run resolution: pass
- read-only transaction: pass
- reviewed input hashes: pass
- selected-run rate reconstruction: pass
- selected-run token geometry: pass

### Rollback-only transaction

Audit:

- `.run/review/gemini-provider-evidence-rollback-only-20260827-01.json`
- SHA-256:
  `29f008ad61fd02bb69d9ecd0159cd3598f76eab0be70caf5a718d3f84199c5f7`

Result:

- exit: `0`
- status: `passed`
- commit state: `not_committed`
- transactional insert: pass
- transactional verification: pass
- rollback: pass
- second-connection zero-persistence verification: pass

All nine Gemini-scoped tables returned to zero after rollback.

## Permanent apply

Audit:

- `.run/review/gemini-provider-evidence-apply-20260827-01.json`
- SHA-256:
  `f385bdef77daf8fa4f2e4a36f712629314633b9a3539a3d441385d804c5854fc`

Result:

- exit: `0`
- status: `applied`
- commit state: `committed`
- target state: `exact_gemini_state`

All checks passed:

- reviewed input hashes
- advisory lock
- provider-scoped empty preflight
- canonical run resolution
- transactional insert
- transactional verification
- commit
- second-connection verification

Persisted Gemini-scoped row counts:

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 3 |
| `benchmark_provider_usage_evidence` | 0 |
| `benchmark_provider_pricing_snapshots` | 2 |
| `benchmark_provider_cost_evidence` | 1 |
| `benchmark_usage_reconciliations` | 2 |
| `benchmark_usage_reconciliation_sources` | 4 |
| `benchmark_cost_reconciliations` | 2 |
| `benchmark_cost_reconciliation_sources` | 6 |
| `benchmark_evidence_promotion_gates` | 0 |

## Post-apply importer verification

Audit:

- `.run/review/gemini-provider-evidence-postcheck-20260827-01.json`
- SHA-256:
  `3fe246a48d70093e7efbf0c846c92d210bbf9ea360c4d680a5451c2e2a828f85`

Result:

- exit: `0`
- status: `already_applied`
- commit state: `not_committed`
- target state: `exact_gemini_state`
- exact content verification: pass
- read-only transaction: pass
- reviewed input hashes: pass

The observed row counts exactly matched the permanent apply.

## Importer-independent SQL verification

### Failed first audit attempt

The first independent audit attempt is retained as provenance:

- stdout:
  `.run/review/gemini-provider-evidence-independent-sql-audit-20260827-01.json`
- stdout SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- stderr:
  `.run/review/gemini-provider-evidence-independent-sql-audit-20260827-01.stderr`
- stderr SHA-256:
  `f49a1b5fc9815227e7fd4f78e0fe1a72fb1b0cdfa3863d627cbb1c9d30bbda66`

This attempt did not complete because the handwritten independent audit
incorrectly assumed that
`benchmark.benchmark_evidence_promotion_gates` contained an
`arm_run_id` column.

The error was:

`psycopg.errors.UndefinedColumn: column "arm_run_id" does not exist`

No database writes were attempted; the transaction was read-only.

### Promotion-gate schema diagnostic

Audit:

- `.run/review/gemini-promotion-gate-schema-diagnostic-20260827-01.json`
- SHA-256:
  `0f681a29b3297ac59dfda76dfc900389912a2afc5f0db5cee5c969f917b79da0`

The live schema and migration contract confirmed:

- promotion gates are scoped by `arm_id`
- the source execution is stored as `source_arm_run_id`
- the live promotion-gate table contained `0` total rows

The repository importer already used the correct `arm_id` scope.

### Corrected independent direct-SQL audit

Audit:

- `.run/review/gemini-provider-evidence-independent-sql-audit-20260827-02.json`
- SHA-256:
  `c776d99b3cbee75bd2562612eadd0cdd824ed3e3e6d61fb5edcf5b2aa39941d9`

Empty stderr SHA-256:

`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Result:

- exit: `0`
- status: `passed`
- audit type: `importer-independent-direct-sql-v2`
- transaction mode: `read_only`

All independent checks passed:

- exact table counts
- exact canonical arm-run IDs
- exact retained source paths and SHA-256 values
- exactly one shared `$26.371228` account-window provider-cost row
- no provider usage rows
- qualified usage semantics
- exact retained usage values
- Pro cost semantics
- Flash lower-bound cost semantics
- zero Gemini promotion gates

## Source provenance

Normalized provider/reconciliation sources include:

1. `results/phase3/supplemental/gemini_family_reconciliation_2026-06-17.json`
   - SHA-256:
     `c28ec21baec0759ac02939f9007635f98b82a9faf5f85c564ad47f3c510c6751`

2. `scripts/generate_phase3_provider_evidence_audit_20260825.py`
   - SHA-256:
     `45b98842469dcd72275fa26a9aaeae6a7f524080044d7667f08bf17fe7b88a74`

3. `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`
   - SHA-256:
     `43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256`

The historical raw Google Cloud Billing CSV basename is known, but its
raw SHA-256/source artifact is not retained. That limitation remains
explicit and is not repaired by inference.

## Final methodological status

Gemini now has a normalized historical evidence state that preserves
the distinction between:

- provider-supplied account-window billing context;
- harness usage that has been independently qualified;
- provider-rate reconstructed selected-run cost;
- unavailable selected-run provider billing;
- unavailable selected-run provider usage/model observation; and
- unresolved Flash usage/cost.

The shared Google billing subtotal is evidence, but not selected-run
billing authority.

No synthetic allocation of the provider account subtotal was made.

No missing Flash usage or cost was synthesized as zero.

No promotion decision was created as part of this historical
normalization.

Any future first-party API evidence should supplement and reconcile
against this retained historical state rather than replace it.
