# OpenAI Full-Sweep Provider Cost Reconciliation

**Date:** 2026-08-21
**Status:** Authoritative provider reconciliation complete
**Scope:** OpenAI API usage from 2026-05-01 through 2026-08-21

## Executive finding

The OpenAI provider account is fully reconcilable for the project period.

The complete provider exports total:

- **$95.2410900** of OpenAI API spend;
- **2,964 requests**;
- **74,364,964 input tokens**;
- **66,424,320 cached input tokens**;
- **7,940,644 uncached input tokens**;
- **2,047,316 output tokens**;
- exactly **one active project ID**;
- exactly **one active API-key ID**.

The provider total rounds to the OpenAI dashboard value of **$95.24**.

All nonzero project activity occurs on June 3, June 16, June 19, and June 27.

The two selected Phase 3 full sweeps are reconciled exactly:

| Arm | Selected run | Provider date | Provider-billed cost |
|---|---|---:|---:|
| `router-gpt-5.4` | `router-gpt-5.4/2026-06-19__13-47-51` | 2026-06-19 | **$29.7919335** |
| `router-gpt-5.5` | `router-gpt-5.5/2026-06-27__01-30-18` | 2026-06-27 | **$48.604914** |
| **Combined** | | | **$78.3968475** |

These provider-billed totals supersede the historical harness/reviewed estimates for current decision-oriented cost reporting.

The historical estimates remain preserved as provenance and diagnostic evidence.

## Full-sweep usage

### GPT-5.4

Provider model: `gpt-5.4-2026-03-05`

- requests: 1,256
- total input: 32,807,457
- cached input: 30,833,664
- uncached input: 1,973,793
- output: 1,143,269
- provider-billed cost: **$29.7919335**

Cached input is approximately 94% of total input.

Historical repository cost values:

- harness-recorded cost: **$173.094830**
- historical reviewed adjusted cost: **$183.646689146806**

### GPT-5.5

Provider model: `gpt-5.5-2026-04-23`

- requests: 1,480
- total input: 35,226,942
- cached input: 33,033,728
- uncached input: 2,193,214
- output: 704,066
- provider-billed cost: **$48.604914**

Cached input is approximately 94% of total input.

Historical repository cost values:

- harness-recorded cost: **$168.708375**
- historical reviewed adjusted cost: **$183.958832348525**

## Cost lineage

The historical Phase 3 dollar values originated before dashboard reporting.

Retained Claude Code artifacts show that the routed OpenAI sessions emitted
`total_cost_usd` themselves. Harbor retained that value as
`agent_result.cost_usd`, and Phase 3 ingestion copied the field into stored
trial metadata.

A retained GPT-5.4 canary provides an exact arithmetic fingerprint:

- input tokens: 146,861
- cache tokens reported to Claude Code: 0
- output tokens: 2,602
- emitted cost: $0.799355

The emitted value is exactly:

`146,861 × $5/M + 2,602 × $25/M = $0.799355`.

Full-sweep retained trial artifacts show the same effective `$5/M input +
$25/M output` client-side estimate for the custom GPT router aliases.

At the same time, the authoritative OpenAI provider export shows that roughly
94% of full-sweep input was billed as cached input.

Therefore two mechanisms are established in retained evidence:

1. the custom routed OpenAI sessions were assigned an incorrect client-side
   cost estimate; and
2. the OpenAI cached-input dimension did not appear in Claude Code's retained
   Anthropic-compatible usage accounting, where cache tokens were recorded as
   zero.

The repository does not retain enough runtime-version information to attribute
the underlying translation behavior to one exact LiteLLM release. The most
likely mechanism is the custom OpenAI-to-Anthropic compatibility path combined
with custom router alias pricing.

## Downstream propagation

The later reporting layers did not independently create the error.

1. Claude Code emitted the client-side cost estimate.
2. Harbor retained it in `agent_result.cost_usd`.
3. `scripts/ingest_phase3_run_metadata.py` copied that value.
4. `scripts/generate_phase3_cost_coverage.py` treated an existing cost as
   `recorded_artifact`.
5. OpenAI models were not present in the configured reconstruction rate table,
   so missing OpenAI rows were estimated from the same-arm empirical rate.
6. The reviewed 2026-08-05 layer faithfully preserved that historical
   benchmark accounting and explicitly marked it as non-invoice-level.

This is therefore an upstream benchmark cost-telemetry defect, not an OpenAI
billing discrepancy and not a DR-303 arithmetic defect.

## Reporting correction contract

Current comparative reporting must use:

- GPT-5.4: **$29.7919335**
- GPT-5.5: **$48.604914**

as the selected arm-level costs.

The historical harness/reviewed estimates remain visible only as historical
diagnostic values.

The provider exports establish exact arm totals but do not allocate provider
billing to individual benchmark trials or outcome buckets. Therefore DR-304
must not proportionally fabricate success/failure or per-trial provider spend.

Where an exact provider-billed arm total exists, provider-billed cost takes
precedence over the historical harness estimate for current comparisons.

## Frozen-history rule

DR-304 must not edit or overwrite:

- raw Phase 3 `result.json` files;
- historical trial rewards or token fields;
- `phase3_trial_cost_coverage_20260712.tsv`;
- `phase3_arm_cost_coverage_20260712.tsv`;
- `phase3_extended_reviewed_comparison_20260805.json`;
- the DR-303 source decomposition.

Those remain historical evidence of what the benchmark harness recorded at the
time.

DR-304 instead creates a new current reviewed reporting layer.

## Sanitized checked-in evidence

The private raw provider exports are not committed.

Their SHA-256 fingerprints and sanitized evidence are retained in:

- `results/phase3/provider_usage/normalized/openai_provider_source_manifest_20260821.csv`
- `results/phase3/provider_usage/normalized/openai_provider_activity_20260821.csv`
- `results/phase3/provider_usage/normalized/openai_provider_reconciliation_20260821.csv`

The raw exports contain provider account identifiers and must remain private.
