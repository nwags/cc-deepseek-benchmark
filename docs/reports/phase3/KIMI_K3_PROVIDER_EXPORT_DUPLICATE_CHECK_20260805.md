# Moonshot Kimi K3 export duplicate check — 2026-08-05

## Conclusion

The two uploaded Moonshot request-log archives are byte-for-byte identical despite having different date-range filenames.

## Compared archives

1. `MoonshotAI Openplatform Request Log_20260716-20260806_0d2ac768.zip`
2. `MoonshotAI Openplatform Request Log_20260701-20260805_10bcc8e1.zip`

Both archives have:

- ZIP SHA-256: `0b5628a3495c1ab76524d2f867fa105aaaa550133925398948a68c4b0fde9b67`
- Inner file: `request_log_part_0001.csv`
- Inner CSV SHA-256: `c2faf25aedf04855f1b2b1af5fbe32524f6bd9a6f564b9749dbed78f66dee1b4`
- Rows: 1,273
- Model: `kimi-k3`
- Recorded request timestamps: 2026-07-22 22:29:03 through 2026-07-23 04:44:16
- Input tokens: 39,996,874
- Cached input tokens: 38,341,888
- Uncached input tokens: 1,654,986
- Output tokens: 956,453

## Reconciliation impact

The second archive adds no new requests, tokens, or billing evidence. The existing sanitized Kimi K3 provider-log retained-rate reconstruction remains unchanged:

- provider-log retained-rate reconstruction: `$30.814319`
- Phase 3 extended qualified adjusted-cost estimate: `$1,002.984165`

The raw archives contain request, project, and API-key identifiers and should not be committed. This sanitized duplicate check can be retained as provenance evidence.
