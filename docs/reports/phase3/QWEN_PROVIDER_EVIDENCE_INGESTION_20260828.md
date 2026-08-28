# Qwen Provider Evidence Ingestion — 2026-08-28

## Status

DashScope/Qwen historical provider-evidence normalization and database ingestion is complete for the retained Phase 3 Qwen arm:

- `router-qwen-3.7-plus`

The permanent ingestion was performed from reviewed and pushed commit:

- commit: `067a651fc4565aec04980ba03078197252f0b8e5`
- subject: `Add Qwen provider evidence ingestion`

The ingestion was subsequently verified by:

1. the importer's second-connection verification;
2. the importer's read-only post-apply check; and
3. an importer-independent direct-SQL audit.

Do not rerun the Qwen `--apply` path. Any future change to this normalized state requires an explicit reviewed repair/addition plan.

## Reviewed implementation

- sanitized supplemental snapshot:
  `results/phase3/supplemental/qwen_provider_evidence_snapshot_20260828.json`
- snapshot SHA-256:
  `c334c57d143dc59cf3c81af24a233ed061f07a8902f95431da1d2401e53ab556`
- importer:
  `scripts/ingest_qwen_provider_evidence.py`
- importer SHA-256:
  `7e37db40b6b950d4c4c517ae3408be66ec5a795e081f803c23c4ac84b5294d55`
- tests:
  `tests/test_ingest_qwen_provider_evidence.py`
- tests SHA-256:
  `9a1ca0b6d9191ba59dae6c0449a2e9d405d081f2f2ca49486ffe4ed9ff1a3a68`

Reviewed private plan:

- `.run/review/qwen-provider-evidence-plan-20260828-01.json`
- SHA-256:
  `0836cdb8b0078f9524f736f099d68d2d6138c8f068b2ec074bdb931b456db119`

Private `.run/review` files remain ignored. Their hashes are retained in this report for durable provenance.

## Canonical selected run

### Qwen 3.7 Plus

- arm: `router-qwen-3.7-plus`
- arm-run UUID: `a71f20b4-1926-4ace-8c13-2677af5dc62d`
- selected run: `router-qwen-3.7-plus/2026-06-29__03-16-06`
- backend model: `qwen3.7-plus`
- provider: `dashscope-qwen`
- suite: `phase3-full-20`
- logical mode: `full`
- storage mode: `raw`
- selected trial count: `60`
- complete trial-cost count: `59`
- unresolved trial count: `1`
- selected input tokens: `3,177,366`
- selected cached input tokens: `0`
- selected output tokens: `1,162,240`

The unresolved selected trial is attempt 58 for
`terminal-bench-2.0:torch-pipeline-parallelism`. It has reward `0`, an
exception-failure outcome, and no retained token/cost metadata. The selected
cost therefore remains a lower bound rather than an exact total.

## Provider evidence semantics

The normalized Qwen evidence deliberately separates the June historical
Alibaba account/billing window from the selected June 29 benchmark run.

The retained first-party Alibaba billing export covers June 4 through June 16,
2026 and predates the selected run. It is retained as historical account-window
context and rate-validation evidence only. It is not selected-run usage or
selected-run billing authority.

### Historical Alibaba account window

The reviewed raw billing export records:

- billing rows: `111`
- inference billing rows: `109`
- non-inference billing rows: `2`
- original tokens: `5,122,074`
- deducted/free tokens: `1,000,458`
- billable tokens: `4,121,616`
- account gross: `$31.63861240`
- account discount: `$0.327722480`
- account payable: `$31.310889920`
- inference gross: `$1.63861240`
- inference discount: `$0.327722480`
- inference payable: `$1.310889920`
- subscription/account overhead: `$30`
- selected-run allocation: none
- relation to selected run: `predates_selected_run`

The `$30` non-inference amount is the retained Alibaba Cloud Model Studio
Token Plan Team Edition prepaid subscription purchase. It is normalized as
account overhead, not marginal inference cost.

The normalized provider-cost rows are therefore:

1. `account_spend` = `$31.310889920`
2. `overhead` = `$30`
3. `provider_rate_reconstruction` = `$1.310889920`

All three rows use `allocation_scope=account_window`, have no selected arm-run
or trial allocation, and explicitly retain
`selected_run_allocable=false`.

### Billing rows are not API requests

The Alibaba export contains billing line items, not first-party API request
records.

Accordingly:

- normalized `benchmark_provider_usage_evidence` rows: `0`
- no provider request count is synthesized;
- no provider selected-run token fields are synthesized;
- the `109` inference billing rows are not mislabeled as `109` requests.

This is deliberate. `benchmark_provider_usage_evidence.request_count` is
mandatory and must be positive, so using the billing-line count would create a
false request-level claim.

Historical usage/rate information from the billing export is retained through
source provenance, pricing metadata, historical cost evidence, and
reconciliation context rather than through fabricated request-usage rows.

## Retained pricing semantics

The historical Alibaba bill exactly validates the effective discounted rates
used for the selected retained-usage reconstruction:

- ordinary input: `$0.32/M`
- cached input: `$0.064/M`
- output: `$1.28/M`

The raw export list-price buckets are:

- ordinary input: `$0.40/M`
- cached input: `$0.08/M`
- output: `$1.60/M`

The payable fraction is exactly `0.8`, corresponding to a 20% provider
discount.

Historical PAYG arithmetic:

- `3,854,351 × $0.32/M = $1.23339232`
- `217,600 × $0.064/M = $0.0139264`
- `49,665 × $1.28/M = $0.0635712`
- total = `$1.31088992`

That reconstruction matches the historical inference payable
`$1.310889920`.

The normalized pricing row has no `effective_from` or `effective_until`
because no independently dated official provider pricing snapshot is retained.
The historical billing window validates the rate semantics; it is not
normalized as a provider effective-date claim.

The selected run's largest retained aggregate-input trial decomposes into
`86` requests, with maximum observed request size `45,509` tokens. All
retained selected usage-bearing requests are therefore within the reviewed
`<=256,000` token tier used for the reconstruction.

## Selected usage and cost reconciliation

### Selected usage

- harness input tokens: `3,177,366`
- harness cached input tokens: `0`
- harness output tokens: `1,162,240`
- selected usage authority: `harness_usage_validated`
- provider selected-run ordinary input tokens: `NULL`
- provider selected-run cached input tokens: `NULL`
- provider selected-run cache-creation tokens: `NULL`
- provider selected-run output tokens: `NULL`
- provider request count: `NULL`
- provider-observed selected-run model: `NULL`
- model identity status: `matched`
- validation: `validated_qualified`

`model_identity_status=matched` denotes the reviewed configured/backend
identity. It does not claim an independent provider-observed selected-run
model, which remains `NULL`.

### Selected cost

- historical harness-reported cost: `$20.43072`
- provider-billed selected-run cost: `NULL`
- provider-rate reconstructed selected-run cost: `$2.50442432`
- selected cost: `$2.50442432`
- selected basis: `lower_bound_provider_evidence`
- selected relation: `lower_bound`
- validation: `validated_qualified`

Selected retained-usage arithmetic:

`3,177,366 × $0.32/M + 1,162,240 × $1.28/M = $2.50442432`

Because one selected trial has no retained token/cost metadata, possible
additional spend remains unresolved. The selected cost must not be promoted
from `lower_bound` to `exact`.

Qwen limitation codes:

- `selected_run_provider_usage_unavailable`
- `selected_run_provider_billing_unavailable`
- `one_selected_trial_usage_unresolved`
- `historical_provider_bill_predates_selected_run`
- `historical_provider_context_not_selected_run_allocable`
- `selected_cost_is_lower_bound_due_unresolved_trial`

## Normalized row counts

| Table | Rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | 5 |
| `benchmark_provider_usage_evidence` | 0 |
| `benchmark_provider_pricing_snapshots` | 1 |
| `benchmark_provider_cost_evidence` | 3 |
| `benchmark_usage_reconciliations` | 1 |
| `benchmark_usage_reconciliation_sources` | 3 |
| `benchmark_cost_reconciliations` | 1 |
| `benchmark_cost_reconciliation_sources` | 3 |
| `benchmark_evidence_promotion_gates` | 0 |

There are `6` reconciliation/source links in total: three usage links and
three cost links.

No promotion decision was created.

## Provider evidence sources

Five normalized source rows are retained:

1. first-party Alibaba consumedetailbillv2 billing export provenance;
2. `docs/reports/phase3/PHASE3_PROVIDER_USAGE_RECONCILIATION_2026-06-19.md`;
3. `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`;
4. `results/phase3/reporting/phase3_provider_cost_evidence_matrix_20260825.csv`;
5. `configs/arms/router-qwen-3.7-plus.yaml`.

The raw Alibaba export itself is not committed. The normalized source row
retains only safe provenance, including:

- raw export SHA-256:
  `51b2220da055056fa80fa761fe0f13a25fafe736ed3df8ccaeb44c65bece308b`
- raw export size:
  `243,803` bytes
- integrity status:
  `sha256_verified`

No private filesystem path, account-identifying filename prefix, buyer email,
billing line identifier, order identifier, resource identifier, API key, or
database credential is retained in the committed supplemental snapshot.

## Raw-provider reconciliation

Authoritative private raw-export reconciliation:

- `.run/review/qwen-provider-raw-export-reconciliation-20260828-05.json`
- SHA-256:
  `646ab02da293337f0575e0fe2e4fb7b5f77519b1cb6d904c5cbefa6baf1d8628`

Result:

- raw provider bill reconciled: pass
- list-price versus payable-discount semantics: verified
- subscription overhead separation: verified
- historical effective rates: verified
- selected-run allocation: false
- privacy scan: pass
- database access: none
- database writes: none

An earlier discovery-only audit exposed identity-bearing fields and nested
usage JSON and was therefore rejected as normalization authority. Revision 5
is the authoritative private raw-bill reconciliation.

## Initial database inventory

Read-only inventory audit:

- `.run/review/qwen-provider-db-inventory-20260828-01.json`
- SHA-256:
  `14dc1310f670b3dfac3cadacf87f99a1142a3959c1c4914ae60b7881ba123646`

Result:

- canonical arm-run resolution: pass
- canonical arm-run UUID:
  `a71f20b4-1926-4ace-8c13-2677af5dc62d`
- selected run geometry: pass
- target state: `qwen_empty`
- all nine Qwen-scoped target counts: `0`
- transaction mode: read-only
- database writes: none

The first inventory wrapper failed before database connection because the
secret env file was sourced under `set -u` while referencing another env
variable. The corrected inventory used a parse-only env reader and did not
execute shell commands from the env file.

## Pre-apply verification

### Clean-worktree preflight interruption

The first importer `--check-only` wrapper stopped before loading database
credentials because the worktree contained one untracked path named `re`.

Inspection proved that path was a zero-byte regular file:

- size: `0`
- SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- secret/path indicators: none

The file was removed and the repository returned to a clean state. No database
connection or database write occurred during the interrupted attempt.

### Successful read-only check

Result:

- exit: `0`
- status: `ready`
- target state: `qwen_empty`
- all nine Qwen-scoped target counts: `0`
- canonical run resolution: pass
- selected-run token geometry: pass
- selected-run lower-bound reconstruction: pass
- transaction mode: read-only
- commit state: `not_committed`

### Rollback-only transaction

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

Transactional row counts before rollback matched the normalized row-count table
above. All nine Qwen-scoped targets returned to zero after rollback.

Critically, the rollback verification confirmed:

- provider usage evidence rows remained `0`;
- selected provider token fields remained `NULL`;
- provider-billed selected cost remained `NULL`;
- selected cost remained `$2.50442432`;
- selected relation remained `lower_bound`.

## Permanent apply

Private apply audit:

- `.run/review/qwen-provider-evidence-apply-20260828-01.json`
- SHA-256:
  `96d6b904668b38553efe4bc459fae64bf3228f0db5d8311161d06f6466644297`

Result:

- status: `applied`
- commit state: `committed`
- target state: `exact_qwen_state`

All permanent-apply checks passed:

- reviewed input hashes
- advisory lock
- provider-scoped empty preflight
- canonical run resolution
- transactional insert
- transactional verification
- commit
- second-connection verification

The permanent operation was additive. The reviewed importer has an INSERT-only
write surface for this ingestion and contains no existing-row update, delete,
truncate, replacement, upsert, or migration path.

No historical benchmark result or historical raw cost row was rewritten.

## Post-apply importer verification

Private post-apply audit:

- `.run/review/qwen-provider-evidence-post-apply-check-20260828-01.json`
- SHA-256:
  `c1b8d40ee1203256f12dbef9e17b94d1f7b8e620dbcef4eedaa02a2d79315f1b`

Result:

- status: `already_applied`
- target state: `exact_qwen_state`
- exact content verification: pass
- all expected persistent row counts: verified
- transaction mode: read-only
- commit state: `not_committed`
- database writes: none

## Importer-independent direct-SQL verification

Private direct-SQL audit:

- `.run/review/qwen-provider-evidence-direct-sql-audit-20260828-01.json`
- SHA-256:
  `5ef707a9dd12998e3b7f81d476c39f425f1f1fab5b5d8ceeb1689923da095b11`

Result:

- status: `pass`
- transaction mode: read-only
- importer imported: no
- importer executed: no
- database writes: none

Independent SQL confirmed:

- exact selected arm-run UUID;
- exact selected trial/token geometry;
- provider evidence sources: `5`;
- provider usage evidence rows: `0`;
- pricing snapshots: `1`;
- provider cost evidence rows: `3`;
- usage reconciliations: `1`;
- cost reconciliations: `1`;
- usage reconciliation/source links: `3`;
- cost reconciliation/source links: `3`;
- promotion gates: `0`;
- exact source SHA provenance and integrity status;
- historical Alibaba account/billing evidence remains unallocated to the selected run;
- the `$30` Token Plan remains account overhead;
- the historical `$1.310889920` inference reconstruction remains account-window context;
- the effective `$0.32/M`, `$0.064/M`, and `$1.28/M` rate semantics are preserved;
- pricing effective dates remain `NULL`;
- provider usage evidence remains empty;
- selected provider-observed model remains `NULL`;
- selected provider token and request fields remain `NULL`;
- provider-billed selected cost remains `NULL`;
- selected usage authority remains `harness_usage_validated`;
- selected cost remains `$2.50442432`;
- selected basis remains `lower_bound_provider_evidence`;
- selected relation remains `lower_bound`;
- validation remains `validated_qualified`;
- all six limitation codes are preserved;
- all six source links match the reviewed plan.

This audit did not import or execute the Qwen ingestion script. It independently
validated the persisted database state through direct SQL.

## Source-link semantics

Usage reconciliation links:

1. provider evidence matrix -> `aggregate_usage`
2. Qwen arm config -> `model_identity`
3. raw Alibaba billing export provenance -> `context`

Cost reconciliation links:

1. current selected-run reconciliation -> `lower_bound`
2. raw Alibaba billing export provenance -> `pricing`
3. June 19 provider reconciliation -> `context`

The source-link roles preserve the distinction between selected-run retained
harness accounting and historical provider context.

## Privacy and retention

Committed artifacts do not contain:

- raw Alibaba billing-export bytes;
- the private raw-export filesystem path;
- the identity-bearing raw-export filename prefix;
- buyer email or nested buyer metadata;
- billing line IDs, order IDs, resource IDs, or instance IDs;
- Supabase database URLs;
- API keys or other provider credentials.

Private audit files under `.run/review` are ignored and are referenced only by
SHA-256 in this report.

The raw provider export remains private and hash-pinned; only the sanitized
snapshot and safe provenance are committed.

## Closure

Qwen provider-evidence normalization is closed.

The durable normalized state is:

- one selected Qwen 3.7 Plus arm;
- selected usage authority from validated retained harness accounting;
- no synthesized selected-run provider usage;
- no synthesized selected-run provider billing;
- historical Alibaba account/billing evidence retained as context and rate validation;
- provider billing-line count not mislabeled as API request count;
- subscription overhead separated from inference cost;
- selected lower-bound cost `$2.50442432`;
- one unresolved selected trial prevents exact-cost promotion;
- exact persisted database state independently verified.

Do not rerun the Qwen permanent apply. Any future change must be handled as a
new reviewed repair/addition with its own provenance and verification trail.
