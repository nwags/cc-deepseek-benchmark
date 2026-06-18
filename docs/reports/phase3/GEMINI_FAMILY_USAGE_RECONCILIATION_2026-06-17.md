# Gemini Family Usage Reconciliation

This report reconciles available Google/Gemini billing evidence against Phase 3 Gemini benchmark artifacts.

AI Studio detailed request logging was off, so provider-side model/token attribution is unavailable. The available provider evidence is service-level Google Cloud Billing plus a coarse Cloud Monitoring request-count export by response code.

Raw Google project identifiers and service IDs from exports are intentionally omitted. Raw billing/monitoring CSV exports should not be committed.

Session rows are grouped by assistant-message timestamp converted to UTC date, because provider billing is UTC-date based while benchmark run directory names may differ.

## Provider billing summary

| Service | Unrounded subtotal | Rounded subtotal |
|---|---:|---:|
| Gemini API | $26.371228 | $26.370000 |

- Provider-billed Gemini API total in uploaded June billing export: **$26.371228**.
- Artifact-side internal estimated Gemini cost across retained canary/smoke aggregates: **$46.158838**.
- Because AI Studio detailed logging was off, the provider total cannot be split by Gemini model or token class from these exports.

## Cloud Monitoring request activity

The monitoring export contains response-code time buckets. The raw chart values are fractional, so the approximate-count column is shown only as contextual activity evidence, not as billing truth.

| Response code | Raw value sum | Approx count if hourly-rate values |
|---:|---:|---:|
| 200 | 0.047 | 168.667 |
| 404 | 0.000 | 0.667 |
| 429 | 0.025 | 91 |
| 503 | 0.008 | 27.333 |

## Session-side token totals

| UTC date | Model/arm family | Input | Cache | Output | Assistant messages |
|---|---|---:|---:|---:|---:|
| 2026-06-02 | `gemini-flash` | 121,594 | 178,877 | 8,887 | 13 |
| 2026-06-03 | `gemini-3.1-pro` | 41,402 | 89,103 | 1,580 | 8 |
| 2026-06-03 | `gemini-flash` | 504,112 | 0 | 13,075 | 24 |
| 2026-06-16 | `gemini-3.1-pro` | 2,759,726 | 1,531,257 | 56,527 | 130 |
| 2026-06-16 | `gemini-flash` | 11,241,467 | 430,941 | 180,394 | 304 |

## Benchmark aggregate artifacts included

| Date | Arm | Model | Trials | Completed | Errors | Input | Cache | Output | Est. cost | Path |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-06-02 | `router-gemini-3.1-pro` | `gemini-3.1-pro` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-gemini-3.1-pro/2026-06-02__21-10-28/result.json` |
| 2026-06-02 | `router-gemini-3.1-pro` | `gemini-3.1-pro` | 1 | 1 | 0 | 130,505 | 89,103 | 1,580 | $0.291061 | `results/phase3/canary/arm-router-gemini-3.1-pro/2026-06-02__22-17-25/result.json` |
| 2026-06-02 | `router-gemini-flash` | `gemini-flash` | 1 | 1 | 0 | 300,471 | 178,877 | 8,887 | $0.919583 | `results/phase3/canary/arm-router-gemini-flash/2026-06-02__17-59-33/result.json` |
| 2026-06-02 | `router-gemini-flash` | `gemini-flash` | 1 | 1 | 1 | 70,980 | 0 | 1,652 | $0.396200 | `results/phase3/canary/arm-router-gemini-flash/2026-06-02__20-30-15/result.json` |
| 2026-06-02 | `router-gemini-flash` | `gemini-flash` | 1 | 1 | 0 | 433,132 | 0 | 11,423 | $2.451235 | `results/phase3/canary/arm-router-gemini-flash/2026-06-02__20-59-54/result.json` |
| 2026-06-16 | `router-gemini-3.1-pro` | `gemini-3.1-pro` | 5 | 5 | 3 | 2,255,522 | 807,305 | 26,141 | $8.018022 | `/tmp/phase3-gemini-3-1-pro-27641156327/phase3-router-gemini-3.1-pro-smoke-27641156327/results/phase3/smoke/arm-router-gemini-3.1-pro/2026-06-16__19-04-01/result.json` |
| 2026-06-16 | `router-gemini-flash` | `gemini-flash` | 5 | 5 | 3 | 6,300,763 | 121,971 | 81,119 | $17.289900 | `/tmp/phase3-gemini-flash-27586688012/phase3-router-gemini-flash-smoke-27586688012/results/phase3/smoke/arm-router-gemini-flash/2026-06-16__00-58-08/result.json` |
| 2026-06-16 | `router-gemini-flash` | `gemini-flash` | 5 | 5 | 4 | 3,805,021 | 268,335 | 67,627 | $16.792836 | `/tmp/phase3-gemini-flash-27641161172/phase3-router-gemini-flash-smoke-27641161172/results/phase3/smoke/arm-router-gemini-flash/2026-06-16__19-04-09/result.json` |

## Interpretation notes

- Treat the Google Cloud Billing total as the provider-side cost source of truth for Gemini spend to date.
- Treat benchmark aggregate costs as internal estimates; they are not provider-billed costs and currently exceed the available service-level billing total.
- Detailed model/token reconciliation is blocked because AI Studio logging was off and the billing export is service-level.
- The monitoring export is useful for confirming request activity timing and response-code mix, but it does not expose model/token/cost dimensions.
- Dashboard implication: store run start time, run end time, run directory timestamp, session message UTC dates, and provider billing UTC date separately.
