# xAI Provider Evidence Ingestion — 2026-08-27

## Status

xAI / Grok historical provider-evidence normalization and database
ingestion is complete.

The permanent ingestion was performed from reviewed and pushed commit:

- commit: `d69be6a62c86839b47855d3757c49a01872b8641`
- subject: `Add xAI provider evidence ingestion`

The ingestion was subsequently verified by:

1. the importer's second-connection verification;
2. the importer's read-only post-apply check; and
3. an importer-independent direct-SQL audit.

Do not rerun the xAI `--apply` path. Any future change to this
normalized state requires an explicit reviewed repair/addition plan.

## Reviewed implementation

- sanitized supplemental snapshot:
  `results/phase3/supplemental/xai_provider_evidence_snapshot_20260827.json`
- snapshot SHA-256:
  `dbb0adaa14460adf1b02b9ac140c7eb430702e4dc9c45d8b879ebd9de9a8b3dc`
- importer:
  `scripts/ingest_xai_provider_evidence.py`
- importer SHA-256:
  `c50e43fe98f7128834e959f00beba2a1212a0540caf8b9ee5e205d28d531c2ad`
- tests:
  `tests/test_ingest_xai_provider_evidence.py`
- tests SHA-256:
  `96fc4af062b98f569ad770ed83fec4489a8156423c0e2fa67005a70c2522ced0`

Reviewed private plan:

- `.run/review/xai-provider-evidence-plan-20260827-01.json`
- SHA-256:
  `eac1bc5e7070ef46d6ae9488ac4ea7f03874a9a91bf215fe48a32fb7ae9aba49`

Private `.run/review` files remain ignored. Their hashes are retained in
this report for durable provenance.

## Canonical selected run

- arm: `router-grok-build-0.1`
- arm-run UUID:
  `f01af7ae-e335-41e5-853f-18e020d08814`
- selected run:
  `router-grok-build-0.1/2026-06-28__13-28-55`
- backend model: `grok-build-0.1`
- selected trial count: `60`

## Provider evidence semantics

The retained xAI evidence contains two provider dashboard aggregates.

### 2026-06-19 dashboard observation

- amount: `$6.36`
- canonical retained token total: `5,927,385`
- separately observed token total: `5,927,462`
- cost kind: `provider_dashboard_total`
- allocation scope: `provider_window`
- completeness: `aggregate_only`
- selected arm-run allocation: none
- selected trial allocation: none
- selected provider model: none
- relation to selected run: predates selected run

The 77-token difference between the two observed token totals remains
explicit rather than being reconciled by inference.

### 2026-08-27 dashboard observation

- amount: `$42.40`
- displayed semantics: `total credits usage`
- displayed window: rolling last 90 days
- approximate window: `2026-05-29` through `2026-08-27`
- exact window boundaries retained: no
- API-key filter state established: no
- other xAI traffic excluded: no
- cost kind: `provider_dashboard_total`
- allocation scope: `provider_window`
- completeness: `aggregate_only`
- selected arm-run allocation: none
- selected trial allocation: none
- selected provider model: none

The selected June 28 run falls within this rolling window, but the
`$42.40` total is not selected-run allocable.

Neither dashboard amount is normalized as selected-run
`provider_billed_cost_usd`.

The retained xAI evidence has no granular selected-run provider
model/request export. Therefore:

- normalized provider usage evidence rows: `0`
- provider-observed selected-run model: `NULL`
- selected-run provider billed cost: `NULL`
- dashboard totals remain provider-window context only
- configured model identity is not relabeled as provider observation

## Selected usage and cost reconciliation

Retained selected harness usage:

- input tokens: `2,913,256`
- cached input tokens: `0`
- output tokens: `1,752,719`
- retained usage-bearing trials: `59/60`
- unresolved trials: `1`

The unresolved trial is `polyglot-rust-c`.

It has zero retained token metadata and a zero-metric retained
trajectory, but this does not prove zero provider spend. Missing usage
or cost is not synthesized as zero.

Reviewed reconstruction rates:

- input: `$1/M`
- output: `$2/M`

Arithmetic:

`2,913,256 × $1/M + 1,752,719 × $2/M = $6.418694`

Selected reconciliation:

- historical harness-reported cost: `$38.149845`
- historical reviewed cost context: `$53.153814003353`
- provider billed cost: `NULL`
- provider-rate reconstructed cost: `$6.418694`
- selected cost: `$6.418694`
- selected basis: `lower_bound_provider_evidence`
- selected relation: `lower_bound`
- selected usage authority: `harness_usage_validated`
- validation: `validated_qualified`

The selected amount is a retained-accounting lower bound. Additional
spend from the unresolved trial may exist.

## Pre-apply verification

### Read-only check

Audit:

- `.run/review/xai-provider-evidence-check-only-20260827-01.json`
- SHA-256:
  `7bd9567c3c4e09d52d4571961d2eb2fbd7a6663ee2c4b5650be25c717ed1c486`

Result:

- exit: `0`
- status: `ready`
- target state: `xai_empty`
- all nine xAI-scoped target counts: `0`
- canonical run resolution: pass
- token geometry: pass
- rate reconstruction: pass
- read-only transaction: pass

### Rollback-only transaction

Audit:

- `.run/review/xai-provider-evidence-rollback-only-20260827-01.json`
- SHA-256:
  `17339e0565546fe86931ca6ee2d1965f643bf122d1b71ae7769575ff2e0b28e5`

Result:

- exit: `0`
- status: `passed`
- commit state: `not_committed`
- transactional insert: pass
- transactional verification: pass
- provider-evidence verification: pass
- rollback: pass
- second-connection zero persistence: pass

Transactional row counts before rollback:

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 3 |
| `benchmark_provider_usage_evidence` | 0 |
| `benchmark_provider_pricing_snapshots` | 1 |
| `benchmark_provider_cost_evidence` | 2 |
| `benchmark_usage_reconciliations` | 1 |
| `benchmark_usage_reconciliation_sources` | 2 |
| `benchmark_cost_reconciliations` | 1 |
| `benchmark_cost_reconciliation_sources` | 3 |
| `benchmark_evidence_promotion_gates` | 0 |

All nine xAI-scoped targets returned to zero after rollback.

Independent post-rollback audit:

- `.run/review/xai-provider-evidence-rollback-postcheck-20260827-01.json`
- SHA-256:
  `7bd9567c3c4e09d52d4571961d2eb2fbd7a6663ee2c4b5650be25c717ed1c486`
- status: `ready`
- target state: `xai_empty`

## Apply-wrapper preflight corrections

Two wrapper/preflight issues occurred before the permanent apply.

First, the shell wrapper attempted to source the ignored Supabase env
file under Bash `nounset`; a local environment-variable reference was
therefore reported as unbound. The wrapper was corrected to follow the
repository's existing env-loading convention.

Second, a whitespace-sensitive source-text assertion attempted to match
the multi-line `xai_empty` guard as one literal string. It failed before
the database environment was loaded. The check was replaced with an AST
audit that structurally verified:

- `apply_permanent()` refuses an already-applied `exact_xai_state`;
- permanent apply requires `xai_empty`;
- both guards fail closed with `IntegrationSafetyError`;
- the importer has no `UPDATE`, `DELETE`, `TRUNCATE`, `DROP TABLE`,
  `MERGE INTO`, `ALTER TABLE`, or `ON CONFLICT` SQL path;
- the write surface is INSERT-only; and
- the permanent path contains one explicit commit.

Neither wrapper failure reached permanent database mutation.

## Immediate permanent-apply preflight

Audit:

- `.run/review/xai-provider-evidence-preapply-check-20260827-01.json`
- SHA-256:
  `7bd9567c3c4e09d52d4571961d2eb2fbd7a6663ee2c4b5650be25c717ed1c486`

Result:

- exit: `0`
- status: `ready`
- target state: `xai_empty`
- all nine xAI-scoped target counts: `0`

## Permanent apply

Audit:

- `.run/review/xai-provider-evidence-apply-20260827-01.json`
- SHA-256:
  `3e98d68d382717f1121974b4e9d852a904699efbf6ed00254d9d73b2ac0d5545`

Result:

- exit: `0`
- status: `applied`
- commit state: `committed`
- target state: `exact_xai_state`

All permanent-apply checks passed:

- reviewed input hashes
- advisory lock
- provider-scoped empty preflight
- canonical run resolution
- transactional insert
- transactional verification
- commit
- second-connection verification

Persisted row counts:

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 3 |
| `benchmark_provider_usage_evidence` | 0 |
| `benchmark_provider_pricing_snapshots` | 1 |
| `benchmark_provider_cost_evidence` | 2 |
| `benchmark_usage_reconciliations` | 1 |
| `benchmark_usage_reconciliation_sources` | 2 |
| `benchmark_cost_reconciliations` | 1 |
| `benchmark_cost_reconciliation_sources` | 3 |
| `benchmark_evidence_promotion_gates` | 0 |

The permanent operation was additive. The reviewed importer contains no
existing-row update, delete, truncate, replacement, or upsert path.

## Post-apply importer verification

Audit:

- `.run/review/xai-provider-evidence-postapply-check-20260827-01.json`
- SHA-256:
  `f40ab478e2c2ddd23aa8192b522000e9f432f9aaeaabd570ad37e4a85eb9f6d0`

Result:

- exit: `0`
- status: `already_applied`
- target state: `exact_xai_state`
- exact content verification: pass
- read-only transaction: pass

## Importer-independent SQL verification

Audit:

- `.run/review/xai-provider-evidence-direct-sql-audit-20260827-01.json`
- SHA-256:
  `fcbaf820b0f1fa66b6a1210ce1864bfdd47f5fae19204720d1685fd407a0d0bf`

Result:

- status: `pass`
- audit type: `xai-provider-evidence-direct-sql-v1`
- transaction mode: read-only

Independent SQL confirmed:

- exact selected arm-run resolution
- provider evidence sources: `3`
- provider usage evidence rows: `0`
- pricing snapshots: `1`
- provider dashboard cost rows: `2`
- dashboard context amounts: `$6.36` and `$42.40`
- both dashboard rows remain unallocated provider-window context
- usage reconciliations: `1`
- cost reconciliations: `1`
- promotion gates: `0`
- provider billed selected-run cost: `NULL`
- selected cost: `$6.418694`
- selected basis: `lower_bound_provider_evidence`
- selected relation: `lower_bound`
- selected usage authority: `harness_usage_validated`
- validation: `validated_qualified`

## Source provenance

Normalized database sources:

1. `results/phase3/supplemental/xai_provider_evidence_snapshot_20260827.json`
   - SHA-256:
     `dbb0adaa14460adf1b02b9ac140c7eb430702e4dc9c45d8b879ebd9de9a8b3dc`

2. `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`
   - SHA-256:
     `43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256`

3. `results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv`
   - SHA-256:
     `e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218`

Additional hash-pinned reviewed inputs:

- `docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md`
  - SHA-256:
    `29604cf5ce8e8b866aff51cec5ae92ef3c675def10277abae76c9143bd6962d4`

- `results/phase3/provider_usage/normalized/provider_reconciliation_ledger_2026-06-19.csv`
  - SHA-256:
    `a803e70495886551ea7f810b3ee82cf8913aa70fb32e861a8b4fd5bf72225f0c`

- `results/phase3/reporting/phase3_provider_run_chronology_20260825.csv`
  - SHA-256:
    `3ad11e7e760c1efaac72b9083a145470671ff5c2ebc149be41082379fb5c7b77`

## Final methodological status

xAI now has a normalized historical evidence state that preserves the
distinction between:

- provider dashboard context;
- retained selected-run harness usage;
- provider-rate reconstructed selected-run cost;
- unavailable selected-run provider billing;
- unavailable granular selected-run provider usage/model observation;
- the unresolved selected trial; and
- historical harness/reviewed cost context.

The June 19 `$6.36` dashboard total predates the selected run.

The August 27 `$42.40` rolling-window total contains the selected-run
date but is not selected-run billing authority.

Neither dashboard amount was synthetically allocated to the selected
run.

No provider usage rows were fabricated from harness usage.

No missing `polyglot-rust-c` usage or cost was synthesized as zero.

No historical raw result or cost record was rewritten.

No promotion decision was created.

Future first-party granular xAI request or billing evidence should
supplement and reconcile against this retained historical state rather
than replace it.
