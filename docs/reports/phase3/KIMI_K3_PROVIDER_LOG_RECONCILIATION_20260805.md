# Kimi K3 provider-log retained-rate reconstruction — 2026-08-05

## Source

- Uploaded archive: `MoonshotAI Openplatform Request Log_20260716-20260806_0d2ac768.zip`
- Archive SHA-256: `0b5628a3495c1ab76524d2f867fa105aaaa550133925398948a68c4b0fde9b67`
- Inner CSV: `request_log_part_0001.csv`
- Inner CSV SHA-256: `c2faf25aedf04855f1b2b1af5fbe32524f6bd9a6f564b9749dbed78f66dee1b4`
- Raw identifiers are intentionally not reproduced in this report.

## Provider-log coverage

- Model: `kimi-k3`
- Requests: 1,273
- Duplicate request IDs: 0
- First timestamp in export: 2026-07-22 22:29:03
- Last timestamp in export: 2026-07-23 04:44:16
- All rows satisfy `Cached Tokens <= Input Tokens`: True

## Token totals

| Category | Tokens |
|---|---:|
| Input Tokens | 39,996,874 |
| Cached Tokens | 38,341,888 |
| Uncached input (`Input - Cached`) | 1,654,986 |
| Output Tokens | 956,453 |
| Cache share of input | 95.8622% |

## Retained-rate reconstruction

### Pricing provenance

The reconstruction uses the Kimi K3 rate constants retained in `scripts/recompute_kimi_k3_costs.py`. Git history dates the initial rate-bearing utility to **2026-07-22**, which is the repository pricing-record date used here; it is not a verified provider pricing-snapshot date.

| Token category | Applied rate |
|---|---:|
| Uncached input | $3.00 / 1M tokens |
| Cached input | $0.30 / 1M tokens |
| Output | $15.00 / 1M tokens |

No durable copy of an official Moonshot provider pricing page and no dated provider pricing snapshot containing these rates was found in the repository. `docs/reports/phase3/KIMI_K3_ADDENDUM_SUMMARY_20260722.md` and `results/phase3/reporting/kimi_k3_full_cost_recompute_20260722.tsv` independently retain the resulting recomputation outputs, but neither independently records the source provenance for all three unit rates. The result is therefore **not fully pricing-provenance-complete**. DR-008 requires retaining an official provider page or dated pricing snapshot before that stronger description may be used.

### Arithmetic

Rates applied:

- uncached input: $3.00 / 1M tokens
- cached input: $0.30 / 1M tokens
- output: $15.00 / 1M tokens

| Component | Calculation | Cost |
|---|---|---:|
| Uncached input | 1,654,986 × $3.00/1M | $4.964958 |
| Cached input | 38,341,888 × $0.30/1M | $11.502566 |
| Output | 956,453 × $15.00/1M | $14.346795 |
| **Total** |  | **$30.814319** |

## Reconciliation scope and confidence

| Dimension | Status | Evidence basis |
|---|---|---|
| Retained-rate token arithmetic | Verified for the exported token totals under the retained 2026-07-22 rate constants; pricing-source provenance remains incomplete | All 1,273 rows satisfy `Cached Tokens <= Input Tokens`; the component arithmetic reproduces $30.814319 |
| Arm-run/provider-log allocation | Low confidence | The export is limited to `kimi-k3`, but its timestamps have no retained timezone and no request-to-run join proves that every row belongs to the selected full run |
| Trial-level allocation | Unresolved | No retained request-ID/timestamp-to-trial join allocates the aggregate export to individual trials |

The selected full run is retained as `router-kimi-k3/2026-07-22__17-51-05`, with canonical review metadata spanning **2026-07-22 17:51:06 UTC through 20:46:14 UTC**. The provider export spans **2026-07-22 22:29:03 through 2026-07-23 04:44:16**, but the sanitized export record does not establish a timezone. A direct timestamp alignment with the full-run interval therefore cannot be proven from retained evidence.

Retained Kimi K3 canary and smoke outputs also exist for the same date, and the aggregate export contains no retained join proving that unrelated Kimi K3 requests were absent from its interval. Exact request-to-trial allocation remains unresolved unless request timestamps or IDs can be joined to retained run/trial evidence.

## Reconciliation conclusion

The provider export resolves the token-field arithmetic in favor of treating `Input Tokens` as the total input count and `Cached Tokens` as a subset. The billable uncached input is therefore `Input Tokens - Cached Tokens`. The arithmetic is verified under the retained rates, while pricing-source provenance and provider-log allocation remain qualified as described above.

The previously retained interpretation that added all input tokens and cached tokens separately would produce $145.839983; that double-counts cached input and should be retired for this export.

The provider-log reconstruction is not invoice-level reconciliation. The request export contains no charged-dollar, tax, credit, or fee-adjustment field, so the reconstruction applies the retained Kimi K3 rate constants but cannot reproduce invoice-level adjustments.

For the reviewed aggregate comparison, the provider-export reconstruction is included as a **qualified retained-rate estimate** for Kimi K3 with low arm-run allocation confidence. Using the reviewed Phase 3 core adjusted cost of $972.169845, the Phase 3 extended qualified adjusted-cost estimate becomes **$1,002.984165** before any separately documented billing adjustments. Pricing-source provenance and exact run/trial allocation remain incomplete; those limitations qualify the estimate but do not justify omitting Kimi K3 from the reviewed extended corpus. The extended corpus contains 16 arms, 960 trials, and 562 successes.

## Comparison to existing Kimi K3 artifact accounting

Existing addendum report values:

- observed trial cost sum: $25.207213
- Harbor-token official-price estimate: $26.570403
- provider-request-log retained-rate reconstruction: $30.814319

The provider-log total exceeds the Harbor-token estimate by **$4.243916** and the recorded trial cost of **$25.207213** by **$5.607106**. The latter is the known accounting gap relative to the provider-log reconstruction. Possible explanations include retries, timeout-related requests, or other request-path usage, but the retained aggregate export does not establish a causal allocation. Exact trial-level allocation requires joining provider request timestamps or IDs to retained trial evidence.

The separately reviewed duplicate-export check confirms that the two uploaded exports were byte-for-byte identical. The second export added no new requests, tokens, or usage evidence. Raw request logs are excluded from version control because they contain sensitive request, project, and API-key identifiers.
