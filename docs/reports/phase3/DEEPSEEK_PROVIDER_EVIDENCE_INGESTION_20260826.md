# DeepSeek Provider Evidence Ingestion — 2026-08-26

- **Provider:** DeepSeek
- **Phase:** Phase 3
- **Application date:** 2026-08-26
- **Application commit:** `968ac1c6fbc2d9d8a3daa4fd8c36cd9967004037`
- **Result:** complete and independently verified

## Purpose

This report records permanent ingestion of reviewed DeepSeek provider
evidence into the normalized Phase 3 provider-evidence schema.

The ingestion deliberately does not claim selected-run provider billing or
selected-run provider token aggregates that were not retained.

For the selected full sweeps:

- usage authority is `harness_usage_validated`;
- usage validation is `validated_qualified`;
- selected cost is reconstructed from validated harness usage and retained
  benchmark-era DeepSeek rates;
- selected cost relation is `estimate`;
- selected cost validation is `validated_qualified`;
- provider smoke evidence remains unallocated to selected runs and trials;
- no per-trial or outcome-level provider allocation is fabricated.

The governing methodology remains:

> A successful benchmark execution does not establish that its telemetry is
> correct.

> Harness telemetry is evidence, not authority, until independently
> qualified.

## Application implementation and schema pins

The permanent application was performed from reviewed commit
`968ac1c6fbc2d9d8a3daa4fd8c36cd9967004037`.

The exact committed application implementation was:

`scripts/ingest_deepseek_provider_evidence.py`

SHA-256:
`750431c4942268b7e7aa3eb175bda7ba3816b69e8304762d859fde74013444c2`

The focused application test file was:

`tests/test_ingest_deepseek_provider_evidence.py`

SHA-256:
`11c3ceda642091c72b1c50c740b42c99703a466ab58908efb281fb15b74c1bb3`

The normalized cost-authority and provider-evidence database contracts were
defined by:

`db/migrations/phase3/010_cost_authority_semantics.sql`

SHA-256:
`20b87b8836fa76298d20349c69392fa03cc1df105849fea1bab9eecc6b5e9c45`

and:

`db/migrations/phase3/011_provider_evidence_contract.sql`

SHA-256:
`3d76c40b28e9aee8f8d99a1e73ac3d6411cf4cf1590b1fb750950321f613630b`

Migrations 010 and 011 were already part of the permanent Phase 3 schema;
this DeepSeek ingestion did not modify or reapply them.

## Normalized evidence sources

Exactly three DeepSeek evidence-source rows are persisted.

1. Provider reconciliation evidence:

   `results/phase3/supplemental/deepseek_family_reconciliation_2026-06-17.json`

   SHA-256:
   `3e8c68b6888d825caa07023d834dffe43e878b38581a9665fdab8645b7457aff`

   Scope: `provider_window`.

2. Benchmark-era pricing evidence:

   `scripts/lib/costs.py`

   SHA-256:
   `965e9f52dc8499c4acf0b0e4f35004e90a7bfa127f97aac762eab993e44a7050`

   Scope: `pricing_snapshot`.

3. Selected-run reconciliation evidence:

   `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`

   SHA-256:
   `43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256`

   Scope: `other`.

The selected-run CSV spans multiple providers and arms and is therefore not
represented as a provider-window artifact.

## Supporting reconciliation material

The human-readable DeepSeek family reconciliation report is retained at:

`docs/reports/phase3/DEEPSEEK_FAMILY_USAGE_RECONCILIATION_2026-06-17.md`

SHA-256:
`ea173208461f2be437639c5631210bf99108fc323dfed99c3a954f82738cb540`

The supporting reconciler currently committed in the repository is:

`scripts/reconcile_deepseek_family_usage.py`

SHA-256:
`6fade0524917ebe9fcfe1419f11c0583dd2aede836bbaeb9e00c97df8ccbe46d`

Git history shows that reconciler content was introduced by commit
`49c394947ebaa8243f9e9ad3c6cd92ac9887c6f3`.

The reconciler is supporting methodology rather than one of the three
normalized DeepSeek database evidence-source rows.

## Provider smoke evidence

### DeepSeek V4 Flash

Provider UTC date:
`2026-06-15`

- cache-hit input: `17,726,720`
- combined cache-miss input:
  `200,187`
- output: `175,514`
- requests: `191`
- provider cost: `$0.126804916`

Ordinary input and cache-creation input remain `NULL`; the retained evidence
only exposes their combined cache-miss class.

### DeepSeek V4 Pro

Provider UTC date:
`2026-06-16`

- cache-hit input: `4,906,624`
- combined cache-miss input:
  `164,407`
- output: `71,255`
- requests: `116`
- provider cost: `$0.151295407`

The smoke provider usage/cost rows remain unallocated to selected arm runs
or individual trials.

## Benchmark-era pricing

| Model | Cache miss / M | Cache hit / M | Output / M |
|---|---:|---:|---:|
| DeepSeek V4 Flash | $0.14 | $0.0028 | $0.28 |
| DeepSeek V4 Pro | $0.435 | $0.003625 | $0.87 |

These retained rates exactly reproduce the provider smoke bills.

No retained official provider pricing URI or independently retained complete
effective-through interval proves that the same rates remained authoritative
through each selected full-sweep date. Selected full-run cost therefore
remains a qualified estimate.

## Selected full-sweep runs

### DeepSeek Flash

Selected run:
`router-deepseek-flash/2026-06-28__13-28-50`

Canonical arm-run UUID:
`5fafae0d-ae1e-4db6-aaa9-12329a437581`

- harness input tokens:
  `102,663,832`
- cache-read tokens:
  `100,425,344`
- output tokens:
  `1,733,059`
- derived cache-miss input:
  `2,238,488`
- historical harness-reported cost:
  `$56.35246`
- selected reconstructed cost:
  `$1.0798358032`
- usage authority:
  `harness_usage_validated`
- selected cost basis:
  `provider_rate_reconstructed_harness_usage_validated`
- relation:
  `estimate`
- validation:
  `validated_qualified`

Selected-run provider-billed cost remains `NULL`.

### DeepSeek Pro

Selected run:
`router-deepseek-pro/2026-06-19__13-47-59`

Canonical arm-run UUID:
`3d026a95-93e0-488e-ab7b-44505626f2f9`

- harness input tokens:
  `44,293,924`
- cache-read tokens:
  `42,372,608`
- output tokens:
  `1,046,381`
- derived cache-miss input:
  `1,921,316`
- historical harness-reported cost:
  `$50.203188`
- selected reconstructed cost:
  `$1.899724634`
- usage authority:
  `harness_usage_validated`
- selected cost basis:
  `provider_rate_reconstructed_harness_usage_validated`
- relation:
  `estimate`
- validation:
  `validated_qualified`

Selected-run provider-billed cost remains `NULL`.

## Persisted normalized cardinalities

| Table | DeepSeek rows |
|---|---:|
| `benchmark_provider_evidence_sources` | 3 |
| `benchmark_provider_usage_evidence` | 2 |
| `benchmark_provider_pricing_snapshots` | 2 |
| `benchmark_provider_cost_evidence` | 2 |
| `benchmark_usage_reconciliations` | 2 |
| `benchmark_usage_reconciliation_sources` | 4 |
| `benchmark_cost_reconciliations` | 2 |
| `benchmark_cost_reconciliation_sources` | 6 |
| `benchmark_evidence_promotion_gates` | 0 |

## Evidence-source links

Each selected usage reconciliation has:

- `model_identity` → retained provider reconciliation evidence;
- `context` → retained provider reconciliation evidence.

Each selected cost reconciliation has:

- `rate_reconstruction` → selected-run reconciliation evidence;
- `pricing` → benchmark-era pricing evidence;
- `context` → retained provider reconciliation evidence.

No DeepSeek evidence-promotion gate exists.

## Historical same-day context was not promoted

Historical reviewed same-day context totals were:

- DeepSeek Flash: `$1.1502775424`;
- DeepSeek Pro: `$1.963511004`.

These totals do not have retained source lineage sufficient to establish
isolated selected-run provider billing.

The independent direct SQL audit found:

- provider-cost matches: `0`;
- selected/current reconciliation matches: `0`.

They remain historical context only.

## Verification chain

### Pre-application read-only verification

Capture:

`.run/review/deepseek-provider-evidence-check-only-20260826-03.json`

SHA-256:
`c03b8ef36cb1b63b7af464d7bbadf2a063d137f501985be6f67818f17bf460d7`

Result:

- `status = ready`
- `mode = check-only`
- `commit_state = not_committed`
- `target_state = deepseek_empty`

All nine DeepSeek normalized counts were zero.

### Real rollback-only verification

Capture:

`.run/review/deepseek-provider-evidence-rollback-only-20260826-01.json`

SHA-256:
`d67090b94d577fe48edde6f75d29d35a3c526ce10a18fb1ca4fb10dab870fd59`

Result:

- `status = passed`
- `mode = rollback-only`
- `commit_state = not_committed`
- `target_state = deepseek_empty`

Transactional insertion and exact verification passed, rollback completed, and
a second connection independently proved zero persistence.

### Permanent application

Application commit:

`968ac1c6fbc2d9d8a3daa4fd8c36cd9967004037`

Capture:

`.run/review/deepseek-provider-evidence-apply-20260826-01.json`

SHA-256:
`bb78903c77db37bfb8f8df86432f848bb3272c9dd8282d1d18c4955e76fdc34b`

Result:

- `status = applied`
- `mode = apply`
- `commit_state = committed`
- `target_state = exact_deepseek_state`

Transactional verification, commit, and second-connection verification all
passed.

### Fresh post-application read-only check

Capture:

`.run/review/deepseek-provider-evidence-postapply-check-20260826-01.json`

SHA-256:
`f7cc0f670a48386c1235b1de9f950316b764bcd1f445f0013c45a139ecfa07ad`

Result:

- `status = already_applied`
- `mode = check-only`
- `commit_state = not_committed`
- `target_state = exact_deepseek_state`

Exact-content verification passed in a fresh read-only transaction.

### Independent direct SQL audit

Capture:

`.run/review/deepseek-provider-evidence-direct-sql-audit-20260826-01.json`

SHA-256:
`f97951ccdbdf2170f6a23e4d07bbb322dc60496c7a01379983fb365f7a764ce3`

Result:

- `status = passed`
- `mode = direct-sql-read-only-audit`
- `database_writes_performed = False`
- `transaction_read_only = True`

The direct SQL audit independently verified normalized source provenance,
smoke evidence semantics, pricing semantics, current usage/cost
reconciliations, evidence-source links, zero promotion gates, and
non-promotion of historical same-day context.

## Limitations

Usage limitations retained for both selected runs:

- `provider_validation_scope_smoke_not_selected_run`
- `selected_run_provider_usage_unavailable`
- `provider_model_observed_in_same_route_smoke_not_selected_full_run`
- `cache_miss_collapses_ordinary_and_cache_creation`
- `raw_provider_archive_hash_unavailable`

Cost limitations retained for both selected runs:

- `selected_run_provider_billing_unavailable`
- `selected_run_provider_usage_unavailable`
- `pricing_effective_through_selected_run_not_independently_retained`
- `raw_provider_archive_hash_unavailable`
- `historical_same_day_context_not_promoted`

Additional boundaries:

- raw provider ZIP SHA-256 values were not retained;
- selected-full-run provider usage is unavailable;
- selected-full-run provider billing is unavailable;
- official provider pricing URI was not retained;
- full pricing effective-through coverage was not independently retained;
- provider smoke windows are not selected full-sweep windows;
- smoke evidence is not allocated to selected runs or trials;
- no per-trial or outcome-level provider cost allocation is inferred.

## Private review artifacts

The supporting private captures remain ignored and mode 600:

- `.run/review/deepseek-provider-evidence-plan-20260826-03.json` — `b5f105095c2b2243b0c3b2cea9a29a0a7564a37a9de812bfd5fd9ea918ff2a21`
- `.run/review/deepseek-provider-evidence-check-only-20260826-03.json` — `c03b8ef36cb1b63b7af464d7bbadf2a063d137f501985be6f67818f17bf460d7`
- `.run/review/deepseek-provider-evidence-rollback-only-20260826-01.json` — `d67090b94d577fe48edde6f75d29d35a3c526ce10a18fb1ca4fb10dab870fd59`
- `.run/review/deepseek-provider-evidence-apply-20260826-01.json` — `bb78903c77db37bfb8f8df86432f848bb3272c9dd8282d1d18c4955e76fdc34b`
- `.run/review/deepseek-provider-evidence-postapply-check-20260826-01.json` — `f7cc0f670a48386c1235b1de9f950316b764bcd1f445f0013c45a139ecfa07ad`
- `.run/review/deepseek-provider-evidence-direct-sql-audit-20260826-01.json` — `f97951ccdbdf2170f6a23e4d07bbb322dc60496c7a01379983fb365f7a764ce3`

Their associated stderr captures are empty and their recorded exit statuses
are zero.

## Final status

DeepSeek provider-evidence ingestion is complete.

The permanent normalized state was verified by:

1. transactional exact verification before commit;
2. a second connection immediately after commit;
3. a fresh post-application importer read-only check;
4. a direct SQL read-only audit independent of the importer.

Current selected DeepSeek reporting therefore uses:

- DeepSeek Flash: `$1.0798358032`;
- DeepSeek Pro: `$1.899724634`;
- usage authority: `harness_usage_validated`;
- cost basis:
  `provider_rate_reconstructed_harness_usage_validated`;
- cost relation: `estimate`;
- validation: `validated_qualified`.

No selected-run provider billing or provider usage was fabricated, and the
unsupported historical same-day totals were not promoted.

No further DeepSeek `--apply` execution is required or appropriate for this
reviewed state.
