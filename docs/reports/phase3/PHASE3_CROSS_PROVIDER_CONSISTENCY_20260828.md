# Phase 3 Cross-Provider Evidence Consistency — 2026-08-28

## Scope

This layer freezes the cross-provider consistency interpretation for the 16 reviewed Phase 3 selected full-suite arms. It does not rewrite the 2026-08-25 cost ledger, prior provider evidence, historical benchmark results, or Phase 1.

- Selected arms: **16**
- Provider families: **8**
- Selected arms with normalized current usage and cost reconciliations: **10**
- Accepted normalized-absence arms: **6**

## Frozen provenance

- Reviewed selected-run ledger SHA-256: `43e731eeceb01b78e51a071b53f1b25bd9a1aaccc5ba3cc30722c1322d914256`
- Private read-only normalized inventory SHA-256: `7c3ffad57afdfa4c672152178281699652f14b4d739336ba793076c603b3ac24`
- Private derived consistency contract SHA-256: `a7d6f1518a97b922d8c2a087c76f06e216251c629a59e27bd5ee8952085abeb0`
- Repaired OpenAI source manifest SHA-256: `1f8b6f52aa2d46d8dbcfb87d97a67e62317c4f0a8849a52c81e5ee6686c1ea20`
- Anthropic provider-evidence closure SHA-256: `7da0313380bb690c0e4ec09371eb41eead5a5c7ada73a1c02328ad212864f789`

The private inventory was generated against Supabase with a read-only transaction, reported no attempted or performed writes, and passed its privacy scan. The private inputs are intentionally ignored and are not required for ordinary CI regeneration.

## Contract principles

1. **Reviewed selected-run identity remains authoritative.** This layer consumes the checked-in 2026-08-25 selected-run ledger rather than selecting replacement runs.
2. **Absence is not automatically an ingestion defect.** Anthropic and GLM have explicit accepted absence states for different evidentiary reasons.
3. **Provider source rows do not have to be arm-run scoped.** A provider-window or account-window source may legitimately support a selected run through normalized child allocation and reconciliation links.
4. **Provider-family isolation is mandatory.** A selected-run reconciliation must not link evidence from another provider family.
5. **Normalized selected cost must agree with reviewed reporting.** For reconciled arms, the normalized selected cost and cost relation must equal the reviewed selected-run ledger.
6. **Exact, estimate, and lower-bound semantics remain distinct.** The normalized basis, relation, validation status, and evidence roles must preserve that distinction.
7. **Historical context is not selected-run authority by default.** Provider/model/account-window evidence is not promoted to selected-run authority without allocable evidence.
8. **Promotion gates and nonselected reconciliations are outside this frozen selected-full-run completeness contract.** Their current population is informational rather than a required row count.

## State counts

| State | Arms |
| --- | ---: |
| `accepted_absence_anthropic_not_normalized` | 4 |
| `accepted_absence_glm_deliberate_empty` | 2 |
| `normalized_exact_provider_billed` | 2 |
| `normalized_qualified_lower_bound` | 3 |
| `normalized_qualified_rate_estimate` | 5 |

## Selected-arm consistency matrix

| Arm | Provider | Reviewed cost | Relation | Contract state | Usage authority | Cost basis |
| --- | --- | ---: | --- | --- | --- | --- |
| `router-anthropic-fable-5` | `anthropic` | $64.80504500 | `exact` | `accepted_absence_anthropic_not_normalized` | `accepted absence` | `accepted absence` |
| `router-anthropic-haiku-sanitized` | `anthropic` | $16.70224485 | `exact` | `accepted_absence_anthropic_not_normalized` | `accepted absence` | `accepted absence` |
| `router-anthropic-opus` | `anthropic` | $50.28831125 | `lower_bound` | `accepted_absence_anthropic_not_normalized` | `accepted absence` | `accepted absence` |
| `router-anthropic-sonnet` | `anthropic` | $38.38591710 | `lower_bound` | `accepted_absence_anthropic_not_normalized` | `accepted absence` | `accepted absence` |
| `router-deepseek-flash` | `deepseek` | $1.0798358032 | `estimate` | `normalized_qualified_rate_estimate` | `harness_usage_validated` | `provider_rate_reconstructed_harness_usage_validated` |
| `router-deepseek-pro` | `deepseek` | $1.899724634 | `estimate` | `normalized_qualified_rate_estimate` | `harness_usage_validated` | `provider_rate_reconstructed_harness_usage_validated` |
| `router-gemini-3.1-pro` | `google-gemini` | $19.6968138 | `estimate` | `normalized_qualified_rate_estimate` | `harness_usage_validated` | `provider_rate_reconstructed_harness_usage_validated` |
| `router-gemini-flash` | `google-gemini` | $16.12091625 | `lower_bound` | `normalized_qualified_lower_bound` | `harness_usage_validated` | `lower_bound_provider_evidence` |
| `router-glm-5.1` | `zai-glm` | $5.3316552 | `estimate` | `accepted_absence_glm_deliberate_empty` | `accepted absence` | `accepted absence` |
| `router-glm-5.2` | `zai-glm` | $8.9016736 | `estimate` | `accepted_absence_glm_deliberate_empty` | `accepted absence` | `accepted absence` |
| `router-gpt-5.4` | `openai` | $29.7919335 | `exact` | `normalized_exact_provider_billed` | `provider_aggregate_usage` | `provider_billed` |
| `router-gpt-5.5` | `openai` | $48.604914 | `exact` | `normalized_exact_provider_billed` | `provider_aggregate_usage` | `provider_billed` |
| `router-grok-build-0.1` | `xai` | $6.418694 | `lower_bound` | `normalized_qualified_lower_bound` | `harness_usage_validated` | `lower_bound_provider_evidence` |
| `router-kimi-k2.6` | `moonshot-kimi` | $6.34692415 | `estimate` | `normalized_qualified_rate_estimate` | `harness_usage_validated` | `provider_rate_reconstructed_harness_usage_validated` |
| `router-kimi-k3` | `moonshot-kimi` | $26.570403 | `estimate` | `normalized_qualified_rate_estimate` | `harness_usage_validated` | `provider_rate_reconstructed_harness_usage_validated` |
| `router-qwen-3.7-plus` | `dashscope-qwen` | $2.50442432 | `lower_bound` | `normalized_qualified_lower_bound` | `harness_usage_validated` | `lower_bound_provider_evidence` |

## Accepted normalized absence

### Anthropic

The four Anthropic selected arms remain represented by the reviewed reporting layer, including official-rate reconstruction and lower-bound qualifications where applicable. No first-party Anthropic provider evidence was normalized into the migration-011 evidence tables for these selected runs. This is recorded as an accepted evidence state, not silently filled with synthetic normalized rows.

### Z.AI / GLM

Both selected GLM arms remain deliberately empty in the normalized provider-evidence layer. Historical GLM 5.1 provider context is not allocable to the selected GLM 5.1 run, and comparable selected-run first-party evidence is not retained for GLM 5.2. The 2026-08-28 private inventory observed zero GLM provider sources, usage rows, cost rows, pricing rows, and selected-arm normalized rows.

## Normalized authority classes

- **OpenAI (2 arms):** exact selected-run provider usage and provider-billed cost.
- **Qualified rate estimates (5 arms):** DeepSeek Flash, DeepSeek Pro, Gemini 3.1 Pro, Kimi K2.6, and Kimi K3 use validated harness usage plus provider evidence and provider rates.
- **Qualified lower bounds (3 arms):** Grok Build 0.1, Gemini Flash, and Qwen 3.7 Plus retain lower-bound cost authority.

## Post-review provenance clarifications — 2026-08-30

### OpenAI source-manifest repair

The OpenAI private-source manifest was re-audited after the original 2026-08-28 consistency snapshot. Six nonselected May/July/August files were corrected from provider usage/cost export labels to `provider_time_grid_no_metrics` because the reviewed bytes contain only start/end time-grid fields and no usage or cost metrics.

The selected June usage and cost exports supporting GPT-5.4 and GPT-5.5 were unchanged. Therefore this provenance repair does not change either OpenAI selected-run contract state, selected cost, cost relation, or authority class. The CSV matrix remains unchanged.

### Anthropic evidence closure

The 2026-08-30 Anthropic closure confirms the existing `accepted_absence_anthropic_not_normalized` state for all four selected Anthropic arms. The accepted absence means that no retained first-party Anthropic selected-run provider source was available for normalization under the reviewed evidence and credential set.

It is not a claim that Anthropic lacks provider APIs. The repository collector supports first-party Anthropic usage and cost APIs, but collection requires `ANTHROPIC_ADMIN_API_KEY`; the reviewed credential set does not contain that Admin key. Any future collection would still require allocation review before selected-run promotion.

## Reproducibility

Ordinary regeneration is offline and secret-free:

```bash
uv run python scripts/generate_phase3_cross_provider_consistency_20260828.py
```

To re-verify the original private normalized snapshot before regeneration, supply both ignored inputs:

```bash
uv run python scripts/generate_phase3_cross_provider_consistency_20260828.py --inventory .run/review/cross-provider-evidence-inventory-20260828-01.json --contract .run/review/cross-provider-consistency-contract-20260828-01.json
```

The second mode verifies the frozen private hashes and semantic contract but performs no database access itself.
