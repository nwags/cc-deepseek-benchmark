# DeepSeek Family Usage Reconciliation

This report reconciles DeepSeek provider-dashboard archive exports against benchmark result artifacts.

Raw provider identifiers from archive exports are intentionally omitted. Provider ZIP archives should not be committed.

Session rows are grouped by assistant-message timestamp converted to UTC date, because provider billing is UTC-date based while benchmark run directory names may not be.

For DeepSeek Anthropic-compatible usage, session cache-miss input is calculated as `input_tokens + cache_creation_input_tokens`; cache-hit input is `cache_read_input_tokens`.

## Provider family totals

| Date | Model | Cache-hit input | Cache-miss input | Total input | Output | Requests | Provider cost |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-05-13 | `deepseek-v4-flash` | 2,318,592 | 61,941 | 2,380,533 | 14,464 | 49 | $0.019214 |
| 2026-05-13 | `deepseek-v4-pro` | 26,143,104 | 1,515,160 | 27,658,264 | 570,587 | 570 | $1.250274 |
| 2026-05-14 | `deepseek-v4-flash` | 66,125,184 | 2,765,447 | 68,890,631 | 2,005,259 | 1,161 | $1.133786 |
| 2026-05-14 | `deepseek-v4-pro` | 22,102,784 | 985,684 | 23,088,468 | 416,919 | 445 | $0.871615 |
| 2026-05-18 | `deepseek-v4-flash` | 4,341,248 | 197,059 | 4,538,307 | 206,404 | 97 | $0.097537 |
| 2026-05-18 | `deepseek-v4-pro` | 5,069,184 | 174,970 | 5,244,154 | 101,667 | 122 | $0.182938 |
| 2026-05-19 | `deepseek-v4-flash` | 34,279,040 | 2,349,955 | 36,628,995 | 1,371,719 | 828 | $0.809056 |
| 2026-05-19 | `deepseek-v4-pro` | 37,553,920 | 2,086,630 | 39,640,550 | 871,089 | 880 | $1.801664 |
| 2026-05-31 | `deepseek-v4-flash` | 33,505,408 | 150,641 | 33,656,049 | 411,427 | 297 | $0.230104 |
| 2026-06-01 | `deepseek-v4-flash` | 3,224,832 | 28,385 | 3,253,217 | 22,273 | 85 | $0.019240 |
| 2026-06-01 | `deepseek-v4-pro` | 11,977,856 | 99,746 | 12,077,602 | 139,163 | 277 | $0.207881 |
| 2026-06-15 | `deepseek-v4-flash` | 17,726,720 | 200,187 | 17,926,907 | 175,514 | 191 | $0.126805 |
| 2026-06-16 | `deepseek-v4-pro` | 4,906,624 | 164,407 | 5,071,031 | 71,255 | 116 | $0.151295 |

## Session-level reconciliation

| Date | Model | Provider cache-hit | Session cache-hit | Hit diff | Provider cache-miss | Session cache-miss | Miss diff | Provider output | Session output | Output diff | Provider requests | Session messages | Provider cost | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05-13 | `deepseek-v4-flash` | 2,318,592 | 0 | 2,318,592 | 61,941 | 0 | 61,941 | 14,464 | 0 | 14,464 | 49 | 0 | $0.019214 | provider usage outside retained artifacts |
| 2026-05-13 | `deepseek-v4-pro` | 26,143,104 | 0 | 26,143,104 | 1,515,160 | 0 | 1,515,160 | 570,587 | 0 | 570,587 | 570 | 0 | $1.250274 | provider usage outside retained artifacts |
| 2026-05-14 | `deepseek-v4-flash` | 66,125,184 | 0 | 66,125,184 | 2,765,447 | 0 | 2,765,447 | 2,005,259 | 0 | 2,005,259 | 1,161 | 0 | $1.133786 | provider usage outside retained artifacts |
| 2026-05-14 | `deepseek-v4-pro` | 22,102,784 | 0 | 22,102,784 | 985,684 | 0 | 985,684 | 416,919 | 0 | 416,919 | 445 | 0 | $0.871615 | provider usage outside retained artifacts |
| 2026-05-18 | `deepseek-v4-flash` | 4,341,248 | 0 | 4,341,248 | 197,059 | 0 | 197,059 | 206,404 | 0 | 206,404 | 97 | 0 | $0.097537 | provider usage outside retained artifacts |
| 2026-05-18 | `deepseek-v4-pro` | 5,069,184 | 0 | 5,069,184 | 174,970 | 0 | 174,970 | 101,667 | 0 | 101,667 | 122 | 0 | $0.182938 | provider usage outside retained artifacts |
| 2026-05-19 | `deepseek-v4-flash` | 34,279,040 | 0 | 34,279,040 | 2,349,955 | 0 | 2,349,955 | 1,371,719 | 0 | 1,371,719 | 828 | 0 | $0.809056 | provider usage outside retained artifacts |
| 2026-05-19 | `deepseek-v4-pro` | 37,553,920 | 0 | 37,553,920 | 2,086,630 | 0 | 2,086,630 | 871,089 | 0 | 871,089 | 880 | 0 | $1.801664 | provider usage outside retained artifacts |
| 2026-05-31 | `deepseek-v4-flash` | 33,505,408 | 16,676,480 | 16,828,928 | 150,641 | 10,266 | 140,375 | 411,427 | 213,947 | 197,480 | 297 | 156 | $0.230104 | partial retained artifacts / additional same-day provider usage |
| 2026-06-01 | `deepseek-v4-flash` | 3,224,832 | 1,552,640 | 1,672,192 | 28,385 | 4,008 | 24,377 | 22,273 | 11,023 | 11,250 | 85 | 44 | $0.019240 | partial retained artifacts / additional same-day provider usage |
| 2026-06-01 | `deepseek-v4-pro` | 11,977,856 | 5,839,872 | 6,137,984 | 99,746 | 11,066 | 88,680 | 139,163 | 86,351 | 52,812 | 277 | 143 | $0.207881 | partial retained artifacts / additional same-day provider usage |
| 2026-06-15 | `deepseek-v4-flash` | 17,726,720 | 17,726,720 | 0 | 200,187 | 200,187 | 0 | 175,514 | 175,514 | 0 | 191 | 191 | $0.126805 | session tokens confirmed |
| 2026-06-16 | `deepseek-v4-pro` | 4,906,624 | 4,906,624 | 0 | 164,407 | 164,407 | 0 | 71,255 | 71,255 | 0 | 116 | 116 | $0.151295 | session tokens confirmed |

## Benchmark aggregate artifacts included

| Date | Arm | Model | Trials | Completed | Errors | Input | Cache | Output | Est. cost | Path |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05-31 | `router-deepseek-flash` | `deepseek-v4-flash` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-deepseek-flash/2026-05-31__01-05-43/result.json` |
| 2026-05-31 | `router-deepseek-flash` | `deepseek-v4-flash` | 1 | 1 | 0 | 86,585 | 86,400 | 2,827 | $0.114800 | `results/phase3/canary/arm-router-deepseek-flash/2026-05-31__18-23-35/result.json` |
| 2026-05-31 | `router-deepseek-flash` | `deepseek-v4-flash` | 5 | 5 | 5 | 0 | 0 | 0 | $0.000000 | `results/phase3/smoke/arm-router-deepseek-flash/2026-05-31__09-22-11/result.json` |
| 2026-05-31 | `router-deepseek-flash` | `deepseek-v4-flash` | 5 | 5 | 1 | 18,156,809 | 18,142,720 | 222,143 | $14.695380 | `results/phase3/smoke/arm-router-deepseek-flash/2026-05-31__18-45-34/result.json` |
| 2026-05-31 | `router-deepseek-pro` | `deepseek-v4-pro` | 1 | 1 | 0 | 85,734 | 85,248 | 1,885 | $0.092179 | `results/phase3/canary/arm-router-deepseek-pro/2026-05-31__21-44-33/result.json` |
| 2026-05-31 | `router-deepseek-pro` | `deepseek-v4-pro` | 5 | 5 | 0 | 5,765,204 | 5,754,624 | 84,466 | $5.041862 | `results/phase3/smoke/arm-router-deepseek-pro/2026-05-31__22-00-54/result.json` |
| 2026-06-15 | `router-deepseek-flash` | `deepseek-v4-flash` | 5 | 5 | 0 | 17,926,907 | 17,726,720 | 175,514 | $14.252145 | `/tmp/phase3-deepseek-flash-27574094546/phase3-router-deepseek-flash-smoke-27574094546/results/phase3/smoke/arm-router-deepseek-flash/2026-06-15__20-25-49/result.json` |
| 2026-06-16 | `router-deepseek-pro` | `deepseek-v4-pro` | 5 | 5 | 1 | 5,071,031 | 4,906,624 | 71,255 | $5.056722 | `/tmp/phase3-deepseek-pro-27626419084/phase3-router-deepseek-pro-smoke-27626419084/results/phase3/smoke/arm-router-deepseek-pro/2026-06-16__14-53-23/result.json` |

## Interpretation notes

- Reconcile DeepSeek at the API-key/provider-family level first, then split by provider model when the archive exposes model rows.
- Provider cost is the funding source of truth because it reflects provider-side cache-hit/cache-miss billing.
- Session JSONL assistant-message usage is the preferred token source for billing reconciliation, especially for timeout-edge trials.
- Current retained June smoke artifacts should reconcile exactly for `2026-06-15 deepseek-v4-flash` and `2026-06-16 deepseek-v4-pro`.
- Older May rows may remain historical/provider-family usage that is only partially covered, or not covered, by retained benchmark artifacts.
- Dashboard implication: store run start time, run end time, run directory timestamp, and provider billing UTC date separately.
- Harbor aggregate `result.json` costs remain useful as internal estimates, but they may diverge from provider-billed costs.
- Raw provider identifiers, API key names, masked API-key strings, user IDs, and raw provider ZIP exports are intentionally omitted from this report and JSON output.
