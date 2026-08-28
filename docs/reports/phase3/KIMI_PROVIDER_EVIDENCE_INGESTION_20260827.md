# Kimi Provider Evidence Ingestion — 2026-08-27

## Status

Moonshot/Kimi historical provider-evidence normalization and database ingestion is complete for both retained Phase 3 Kimi arms:

1. `router-kimi-k2.6`
2. `router-kimi-k3`

The permanent ingestion was performed from reviewed and pushed commit:

- commit: `61565c37135afa6be5dc4cc100711343fc3e4b80`
- subject: `Add Kimi provider evidence ingestion`

The ingestion was subsequently verified by:

1. the importer's second-connection verification;
2. the importer's read-only post-apply check; and
3. an importer-independent direct-SQL audit.

Do not rerun the Kimi `--apply` path. Any future change to this normalized state requires an explicit reviewed repair/addition plan.

## Reviewed implementation

- sanitized supplemental snapshot:
  `results/phase3/supplemental/kimi_provider_evidence_snapshot_20260827.json`
- snapshot SHA-256:
  `929d489496b730ac053a2fa57f8f5c8e1d5701905fd482be788c67913a909f1d`
- importer:
  `scripts/ingest_kimi_provider_evidence.py`
- importer SHA-256:
  `b006d82471cdf7256abf0708888b7505c53ac15506ed24fc748625664a50b488`
- tests:
  `tests/test_ingest_kimi_provider_evidence.py`
- tests SHA-256:
  `19e8c22cdee0ab56e07836c5366818c9e99ceae7705a79c3b7db3580cd8e85dd`

Reviewed private plan:

- `.run/review/kimi-provider-evidence-plan-20260827-01.json`
- SHA-256:
  `c6ca40c1c0958373b87ff2298a71f7da69022c1a10a33087cd920c972f4594cb`

Private `.run/review` files remain ignored. Their hashes are retained in this report for durable provenance.

## Canonical selected runs

### Kimi K2.6

- arm: `router-kimi-k2.6`
- arm-run UUID: `0bc7a2df-1094-4707-b905-e1b4fa110355`
- selected run: `router-kimi-k2.6/2026-06-28__13-28-55`
- backend model: `kimi-k2.6`
- suite: `phase3-full-20`
- logical mode: `full`
- storage mode: `raw`
- selected trial count: `60`
- selected input tokens: `1,754,257`
- selected cached input tokens: `0`
- selected output tokens: `1,170,095`

### Kimi K3

- arm: `router-kimi-k3`
- arm-run UUID: `cd53c19f-7b6f-41b7-aa8f-f0f3a7de2cba`
- selected run: `router-kimi-k3/2026-07-22__17-51-05`
- backend model: `kimi-k3`
- suite: `phase3-full-20`
- logical mode: `full`
- storage mode: `raw`
- selected trial count: `60`
- selected input tokens: `35,753,434`
- selected cached input tokens: `34,309,120`
- selected ordinary/uncached input tokens: `1,444,314`
- selected output tokens: `796,315`

## Provider evidence semantics

The normalized Kimi evidence deliberately separates selected-run harness accounting from first-party provider-window/model-window context. Provider context is retained without synthetic selected-run allocation.

### Historical K2.6 provider context

The retained canonical June 19 reconciliation records a first-party Moonshot K2.6 request-log window from June 4 through June 16, 2026:

- requests: `103`
- total input including cache: `2,608,591`
- ordinary/uncached input: `1,545,150`
- cached input: `1,063,441`
- output: `70,089`
- allocation scope: `model_window`
- selected arm-run allocation: none
- selected trial allocation: none
- provider request IDs normalized: none
- normalized DB request timestamps: `NULL`
- raw K2.6 request-log archive hash retained: no

This provider window predates the selected June 28 K2.6 run and is not selected-run usage.

Historical K2.6 cost context:

- Moonshot dashboard Total Consumption: `$1.91830`
- dashboard cost kind: `provider_dashboard_total`
- dashboard allocation scope: `provider_window`
- dashboard completeness: `aggregate_only`
- retained-rate reconstruction of historical request-log usage: `$1.918399`
- reconstruction allocation scope: `model_window`

The close agreement validates the retained K2.6 rate formula for that historical window, but neither amount is selected-run billing authority.

### K3 provider request-log context

The retained first-party Moonshot K3 request-log export contains:

- requests: `1,273`
- total input including cache: `39,996,874`
- ordinary/uncached input: `1,654,986`
- cached input: `38,341,888`
- output: `956,453`
- retained timestamp strings: `2026-07-22 22:29:03` through `2026-07-23 04:44:16`
- proven timezone: no
- normalized DB request timestamps: `NULL`
- request-to-selected-run join: unavailable
- allocation scope: `model_window`
- selected arm-run allocation: none
- selected trial allocation: none

Raw K3 archive provenance:

- ZIP SHA-256: `0b5628a3495c1ab76524d2f867fa105aaaa550133925398948a68c4b0fde9b67`
- inner CSV SHA-256: `c2faf25aedf04855f1b2b1af5fbe32524f6bd9a6f564b9749dbed78f66dee1b4`
- duplicate archives reviewed: byte-identical
- independent exports counted: `1`

K3 provider-log cost context reconstructed under the retained rates:

- amount: `$30.8143194`
- cost kind: `provider_rate_reconstruction`
- allocation scope: `model_window`
- provider billed: no
- excess versus selected-run reconstruction: `$4.2439164`

The request log has no charged-dollar field and is not invoice-level evidence. Because request-to-run allocation and timezone provenance are unavailable, this amount remains provider/model-window context rather than selected-run billing.

## Retained pricing semantics

### K2.6 retained rates

- ordinary input: `$0.95/M`
- cached input: `$0.16/M`
- output: `$4/M`
- effective provider date normalized: no
- official dated provider pricing snapshot retained: no

### K3 retained rates

- ordinary input: `$3/M`
- cached input: `$0.30/M`
- output: `$15/M`
- repository pricing record date: `2026-07-22`
- provider effective date normalized from that repository date: no
- official dated provider pricing snapshot retained: no

The repository record date is provenance for the retained pricing record, not evidence of an independently verified provider effective date.

## Selected usage and cost reconciliation

### Kimi K2.6

Selected-run usage:

- harness input tokens: `1,754,257`
- harness cached input tokens: `0`
- harness output tokens: `1,170,095`
- selected usage authority: `harness_usage_validated`
- provider selected-run token fields: `NULL`
- provider-observed selected-run model: `NULL`
- model identity status: `matched`
- validation: `validated_qualified`

Selected-run cost:

- historical harness-reported cost: `$25.98573`
- provider billed cost: `NULL`
- provider-rate reconstructed cost: `$6.34692415`
- selected cost: `$6.34692415`
- selected basis: `provider_rate_reconstructed_harness_usage_validated`
- selected relation: `estimate`
- validation: `validated_qualified`

Rate arithmetic:

`1,754,257 × $0.95/M + 1,170,095 × $4/M = $6.34692415`

K2.6 limitation codes:

- `selected_run_provider_usage_unavailable`
- `selected_run_provider_billing_unavailable`
- `historical_provider_request_log_predates_selected_run`
- `historical_dashboard_total_not_selected_run_allocable`
- `raw_k2_request_log_hash_not_retained`

### Kimi K3

Selected-run usage:

- harness input tokens: `35,753,434`
- harness cached input tokens: `34,309,120`
- harness ordinary/uncached input tokens: `1,444,314`
- harness output tokens: `796,315`
- selected usage authority: `harness_usage_validated`
- provider selected-run token fields: `NULL`
- provider-observed selected-run model: `NULL`
- model identity status: `matched`
- validation: `validated_qualified`

Selected-run cost:

- historical harness-reported cost: `$25.207213`
- provider billed cost: `NULL`
- provider-rate reconstructed cost: `$26.570403`
- selected cost: `$26.570403`
- selected basis: `provider_rate_reconstructed_harness_usage_validated`
- selected relation: `estimate`
- validation: `validated_qualified`

Rate arithmetic:

`1,444,314 × $3/M + 34,309,120 × $0.30/M + 796,315 × $15/M = $26.570403`

K3 limitation codes:

- `selected_run_provider_billing_unavailable`
- `provider_log_request_to_run_join_unavailable`
- `provider_log_timezone_unproven`
- `provider_log_not_invoice_level`
- `official_dated_pricing_snapshot_missing`
- `provider_context_excess_not_selected_run_allocable`

For both arms, `model_identity_status=matched` denotes the reviewed configured/backend identity. It does not claim an independent provider-observed selected-run model, which remains `NULL`.

## Normalized row counts

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 6 |
| `benchmark_provider_usage_evidence` | 2 |
| `benchmark_provider_pricing_snapshots` | 2 |
| `benchmark_provider_cost_evidence` | 3 |
| `benchmark_usage_reconciliations` | 2 |
| `benchmark_usage_reconciliation_sources` | 6 |
| `benchmark_cost_reconciliations` | 2 |
| `benchmark_cost_reconciliation_sources` | 6 |
| `benchmark_evidence_promotion_gates` | 0 |

There are `12` reconciliation/source links in total: six usage links and six cost links.

No promotion decision was created.

## Pre-apply verification

### Initial read-only wrapper failure

Audit:

- `.run/review/kimi-provider-evidence-check-only-20260827-01.json`
- SHA-256: `06432a9122407e24c51e73c66b1db5bee2d26691c814d23efbbf698497e4a7ec`

Result:

- status: `failed`
- error type: `ModuleNotFoundError`
- stage: `database_environment`
- commit state: `not_committed`

The first wrapper invoked plain `uv run python`, while the repository intentionally supplies PostgreSQL support ephemerally with `uv run --with 'psycopg[binary]' python`. The failure occurred while importing `psycopg`, before a database connection was attempted. No database writes occurred.

### Successful read-only check

Audit:

- `.run/review/kimi-provider-evidence-check-only-20260827-02.json`
- SHA-256: `69727ff288182d70b871fcb1cbd49253ed753a721910d99e1c58ea84af87f454`

Result:

- exit: `0`
- status: `ready`
- target state: `kimi_empty`
- all nine Kimi-scoped target counts: `0`
- canonical K2.6 run resolution: pass
- canonical K3 run resolution: pass
- selected-run token geometry: pass
- selected-run rate reconstruction: pass
- transaction mode: read-only
- commit state: `not_committed`

### Rollback-only transaction

Audit:

- `.run/review/kimi-provider-evidence-rollback-only-20260827-01.json`
- SHA-256: `076203b952ebdf264869cba692df1a36e14aaf1ee60ec5394b0db3f3746dab44`

Result:

- exit: `0`
- status: `passed`
- commit state: `not_committed`
- advisory lock: pass
- provider-scoped empty preflight: pass
- canonical run resolution: pass
- transactional insert: pass
- transactional verification: pass
- provider-evidence verification: pass
- rollback: pass
- second-connection zero persistence: pass

Transactional row counts before rollback matched the normalized row-count table above. All nine Kimi-scoped targets returned to zero after rollback, and a final independent read-only importer check again returned `kimi_empty`.

## Permanent apply

Audit:

- `.run/review/kimi-provider-evidence-apply-20260827-01.json`
- SHA-256: `6ef0ce5d4d3e2b4ce0d4ba56fb3a242bd21d89057f87cca15d7e493f2a3c5448`

Result:

- exit: `0`
- status: `applied`
- commit state: `committed`
- target state: `exact_kimi_state`

All permanent-apply checks passed:

- reviewed input hashes
- advisory lock
- provider-scoped empty preflight
- canonical run resolution
- transactional insert
- transactional verification
- commit
- second-connection verification

The permanent operation was additive. The reviewed importer has an INSERT-only write surface for this ingestion and contains no existing-row update, delete, truncate, replacement, upsert, or migration path.

No historical benchmark result or historical raw cost row was rewritten.

## Post-apply importer verification

Audit:

- `.run/review/kimi-provider-evidence-post-apply-check-20260827-01.json`
- SHA-256: `20559b22eea316792ecac205ff12cb1fe91b80a95199b7eb6e2a5cc572684884`

Result:

- exit: `0`
- status: `already_applied`
- target state: `exact_kimi_state`
- exact content verification: pass
- transaction mode: read-only
- commit state: `not_committed`

## Importer-independent direct-SQL verification

The first direct-SQL audit wrapper reached the read-only validation path but failed in the audit code because an unaliased `pricing.provider` column was later referenced as `pricing_provider`. This was an audit-checker bug, not a database-content failure. The transaction had already been set read-only and the helper admitted only `SELECT` statements; no database writes occurred.

The corrected audit used explicit unique aliases for joined provider/model columns and numeric `Decimal` comparisons.

Audit:

- `.run/review/kimi-provider-evidence-direct-sql-audit-20260827-02.json`
- SHA-256: `04094b88d6c8b338ee2e367776b6b7ce67af411cda712e36f72c3953a72751e4`

Result:

- status: `pass`
- audit type: `kimi-provider-evidence-direct-sql-v1`
- audit revision: `2`
- transaction mode: read-only
- importer module imported: no

Independent SQL confirmed:

- exact K2.6 and K3 selected arm-run UUIDs
- exact selected token geometry for both arms
- provider evidence sources: `6`
- provider usage evidence rows: `2`
- pricing snapshots: `2`
- provider cost evidence rows: `3`
- usage reconciliations: `2`
- cost reconciliations: `2`
- reconciliation/source links: `12`
- promotion gates: `0`
- source SHA provenance and integrity status
- K2.6 historical request-log context remains unallocated
- K3 provider-log context remains unallocated
- K3 normalized timestamp fields remain `NULL`
- duplicate K3 archives count as one independent export
- K2.6 dashboard `$1.91830` remains provider-window context
- K2.6 historical reconstruction `$1.918399` remains model-window context
- K3 provider-log reconstruction `$30.8143194` remains model-window context and not provider billing
- selected provider token fields remain `NULL`
- selected provider-observed models remain `NULL`
- selected provider billed costs remain `NULL`
- selected K2.6 cost remains `$6.34692415`
- selected K3 cost remains `$26.570403`
- selected usage authority remains `harness_usage_validated`
- selected validation remains `validated_qualified`

## Source provenance

Normalized database sources:

1. `docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md`
   - SHA-256: `29604cf5ce8e8b866aff51cec5ae92ef3c675def10277abae76c9143bd6962d4`

2. `docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md`
   - SHA-256: `e18d9213e540683e6d025027424848f8c511539b176a99f85e33a474ab629604`

3. `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`
   - SHA-256: `43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256`

4. `results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv`
   - SHA-256: `e87a15f086da17a16b116a6741599ce336494ddda5b0bb50289fc550286f4218`

5. `scripts/generate_phase3_provider_evidence_audit_20260825.py`
   - SHA-256: `45b98842469dcd72275fa26a9aaeae6a7f524080044d7667f08bf17fe7b88a74`

6. `scripts/recompute_kimi_k3_costs.py`
   - SHA-256: `9cd599a0ff75a638280a4cf0bc65bc0849b0f3d66b116ebc488c6cd0812e55b6`

Additional reviewed provenance-only inputs:

- `docs/reports/phase3/KIMI_K3_PROVIDER_EXPORT_DUPLICATE_CHECK_20260805.md`
  - SHA-256: `30f50208cdb8b6442438ea3e3165c7ef14a7786a117ef1935ea8701436101ca7`
- `results/phase3/reporting/kimi_k3_full_cost_recompute_20260722.tsv`
  - SHA-256: `3a3e82cb5565211ac0938800a100f9e9dc14c84c449e78046e894ac0b3e31a53`
- `results/phase3/reporting/phase3_provider_run_chronology_20260825.csv`
  - SHA-256: `3ad11e7e760c1efaac72b9083a145470671ff5c2ebc149be41082379fb5c7b77`

## Final methodological status

Kimi now has a normalized historical evidence state that preserves the distinction between:

- selected-run harness usage;
- historical/model-window first-party provider usage context;
- provider dashboard context;
- provider-log rate-reconstruction context;
- retained pricing records with explicit provenance limitations;
- provider-rate reconstructed selected-run cost;
- unavailable selected-run provider billing;
- unavailable selected-run provider token allocation;
- unavailable independent selected-run provider model observation; and
- frozen historical harness/reviewed cost context.

No K2.6 historical request-log usage was reclassified as selected-run usage.

No K2.6 historical dashboard total was reclassified as selected-run billing.

No K3 provider-log aggregate was synthetically allocated to the selected run.

No K3 provider-log reconstruction was relabeled as provider-billed cost.

No unproven K3 timezone was normalized into timestamp fields.

No duplicate K3 archive was counted as independent evidence.

No provider-selected-run token values were fabricated from harness usage.

No configured model was relabeled as independently provider-observed.

No historical benchmark result or raw historical cost record was rewritten.

No migration was run during Kimi ingestion.

No promotion decision was created.

Future first-party granular Moonshot selected-run request or billing evidence should supplement and reconcile against this retained state rather than replace it.
