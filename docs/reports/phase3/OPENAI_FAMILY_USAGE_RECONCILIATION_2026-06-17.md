# OpenAI Family Usage Reconciliation

This report reconciles OpenAI provider-dashboard exports against benchmark result artifacts.

Raw provider identifiers from CSV exports are intentionally omitted.

## Provider family totals

| Date | Requests | Input | Cached input | Uncached input | Output | Provider cost |
|---|---:|---:|---:|---:|---:|---:|
| 2026-06-03 | 39 | 640,637 | 449,024 | 191,613 | 5,740 | $1.181299 |
| 2026-06-16 | 189 | 5,689,928 | 2,107,904 | 3,582,024 | 194,241 | $15.662944 |

## Model-level reconciliation

| Date | Model | Provider input | Benchmark input | Input diff | Provider output | Benchmark output | Output diff | Provider cost | Benchmark cost | Cost diff | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-06-03 | `gpt-5.4` | 146,861 | 146,861 | 0 | 2,602 | 2,602 | 0 | $0.173479 | $0.799355 | $-0.625877 | tokens confirmed |
| 2026-06-03 | `gpt-5.5` | 493,776 | 493,763 | 13 | 3,138 | 3,119 | 19 | $1.007820 | $2.546790 | $-1.538970 | token mismatch |
| 2026-06-16 | `gpt-5.4` | 4,109,382 | 4,015,719 | 93,663 | 130,329 | 128,012 | 2,317 | $9.128358 | $22.081000 | $-12.952642 | token mismatch |
| 2026-06-16 | `gpt-5.5` | 1,580,546 | 1,580,546 | 0 | 63,912 | 63,912 | 0 | $6.534586 | $9.500530 | $-2.965944 | tokens confirmed |

## Benchmark aggregate artifacts included

| Date | Arm | Trials | Completed | Errors | Input | Output | Cost | Path |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-06-03 | `router-gpt-5.4` | 1 | 1 | 0 | 146,861 | 2,602 | $0.799355 | `results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05/result.json` |
| 2026-06-03 | `router-gpt-5.5` | 1 | 1 | 1 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-05-01/result.json` |
| 2026-06-03 | `router-gpt-5.5` | 1 | 1 | 1 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-15-10/result.json` |
| 2026-06-03 | `router-gpt-5.5` | 1 | 1 | 1 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-35-38/result.json` |
| 2026-06-03 | `router-gpt-5.5` | 1 | 1 | 0 | 493,763 | 3,119 | $2.546790 | `results/phase3/canary/arm-router-gpt-5.5/2026-06-03__00-46-21/result.json` |
| 2026-06-16 | `router-gpt-5.4` | 5 | 5 | 1 | 4,015,719 | 128,012 | $22.081000 | `/tmp/phase3-openai-gpt54/phase3-router-gpt-5.4-smoke-27594664296/results/phase3/smoke/arm-router-gpt-5.4/2026-06-16__04-43-35/result.json` |
| 2026-06-16 | `router-gpt-5.5` | 5 | 5 | 0 | 1,580,546 | 63,912 | $9.500530 | `/tmp/phase3-openai-smoke-27641152143/phase3-router-gpt-5.5-smoke-27641152143/results/phase3/smoke/arm-router-gpt-5.5/2026-06-16__19-04-01/result.json` |

## Interpretation notes

- Reconcile provider dashboards at the API-key/project/family level first.
- Use model-level provider breakdowns when available to attribute family usage to benchmark arms.
- Provider cost is the funding source of truth because it accounts for cached input billing and other provider-side billing rules.
- Benchmark cost remains useful as an internal estimator but may differ from provider-billed cost.
- If provider usage appears without a benchmark artifact, download the corresponding GitHub Actions artifact and rerun this script.
