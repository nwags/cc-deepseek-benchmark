# Remaining Provider Artifact Status

This report summarizes Phase 3 artifact-side evidence for Grok, Kimi, Qwen, and GLM.

Provider billing/usage exports have not yet been reconciled for these families, so the costs below are benchmark/internal estimates, not provider-billed source-of-truth costs.

## Provider-family aggregate summary

| Provider family | Aggregate runs | Trials | Errors | Input | Cache | Output | Internal est. cost | Reconciliation status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| glm | 3 | 7 | 3 | 1,282,014 | 28,800 | 90,974 | $6.482015 | provider export pending |
| grok | 3 | 7 | 3 | 5,251,091 | 832 | 188,271 | $29.251326 | provider export pending |
| kimi | 3 | 7 | 2 | 1,530,983 | 50,688 | 68,005 | $9.126944 | provider export pending |
| qwen | 3 | 7 | 3 | 4,458,766 | 0 | 141,760 | $13.148865 | provider export pending |

## Aggregate artifacts

| Run | Provider | Arm | Trials | Completed | Errors | Input | Cache | Output | Internal est. cost | Path |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-06-03__02-38-35 | glm | `router-glm-5` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-glm-5/2026-06-03__02-38-35/result.json` |
| 2026-06-04__12-40-42 | glm | `router-glm-5.1` | 1 | 1 | 0 | 40,707 | 28,800 | 1,334 | $0.107285 | `results/phase3/canary/arm-router-glm-5.1/2026-06-04__12-40-42/result.json` |
| 2026-06-16__14-53-29 | glm | `router-glm-5.1` | 5 | 5 | 2 | 1,241,307 | 0 | 89,640 | $6.374730 | `results/phase3/smoke/arm-router-glm-5.1/2026-06-16__14-53-29/result.json` |
| 2026-06-03__02-28-35 | grok | `router-grok-3` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-grok-3/2026-06-03__02-28-35/result.json` |
| 2026-06-04__03-06-37 | grok | `router-grok-build-0.1` | 1 | 1 | 0 | 129,262 | 832 | 2,698 | $0.710016 | `results/phase3/canary/arm-router-grok-build-0.1/2026-06-04__03-06-37/result.json` |
| 2026-06-16__14-53-30 | grok | `router-grok-build-0.1` | 5 | 5 | 2 | 5,121,829 | 0 | 185,573 | $28.541310 | `results/phase3/smoke/arm-router-grok-build-0.1/2026-06-16__14-53-30/result.json` |
| 2026-06-03__02-29-50 | kimi | `router-kimi-k2.5` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-kimi-k2.5/2026-06-03__02-29-50/result.json` |
| 2026-06-04__03-08-21 | kimi | `router-kimi-k2.6` | 1 | 1 | 0 | 127,263 | 50,688 | 2,278 | $0.465169 | `results/phase3/canary/arm-router-kimi-k2.6/2026-06-04__03-08-21/result.json` |
| 2026-06-16__04-43-33 | kimi | `router-kimi-k2.6` | 5 | 5 | 1 | 1,403,720 | 0 | 65,727 | $8.661775 | `results/phase3/smoke/arm-router-kimi-k2.6/2026-06-16__04-43-33/result.json` |
| 2026-06-03__02-34-10 | qwen | `router-qwen-3.5` | 1 | 1 | 1 | 0 | 0 | 0 | $0.000000 | `results/phase3/canary/arm-router-qwen-3.5/2026-06-03__02-34-10/result.json` |
| 2026-06-04__02-32-42 | qwen | `router-qwen-3.7-plus` | 1 | 1 | 0 | 72,731 | 0 | 3,194 | $0.443505 | `results/phase3/canary/arm-router-qwen-3.7-plus/2026-06-04__02-32-42/result.json` |
| 2026-06-15__22-23-20 | qwen | `router-qwen-3.7-plus` | 5 | 5 | 2 | 4,386,035 | 0 | 138,566 | $12.705360 | `results/phase3/smoke/arm-router-qwen-3.7-plus/2026-06-15__22-23-20/result.json` |

## Session-side token totals

| UTC date | Provider | Arm | Input | Cache | Output | Assistant messages |
|---|---|---|---:|---:|---:|---:|
| 2026-06-03 | glm | `router-glm-5` | 0 | 0 | 0 | 1 |
| 2026-06-04 | glm | `router-glm-5.1` | 11,907 | 28,800 | 1,334 | 4 |
| 2026-06-16 | glm | `router-glm-5.1` | 1,303,967 | 0 | 90,754 | 101 |
| 2026-06-03 | grok | `router-grok-3` | 0 | 0 | 0 | 1 |
| 2026-06-04 | grok | `router-grok-build-0.1` | 128,430 | 832 | 2,698 | 7 |
| 2026-06-16 | grok | `router-grok-build-0.1` | 5,394,070 | 0 | 191,831 | 142 |
| 2026-06-03 | kimi | `router-kimi-k2.5` | 0 | 0 | 0 | 1 |
| 2026-06-04 | kimi | `router-kimi-k2.6` | 76,575 | 50,688 | 2,278 | 7 |
| 2026-06-16 | kimi | `router-kimi-k2.6` | 1,403,720 | 0 | 65,727 | 86 |
| 2026-06-03 | qwen | `router-qwen-3.5` | 0 | 0 | 0 | 1 |
| 2026-06-04 | qwen | `router-qwen-3.7-plus` | 72,731 | 0 | 3,194 | 4 |
| 2026-06-15 | qwen | `router-qwen-3.7-plus` | 4,522,036 | 0 | 141,506 | 136 |

## Interpretation notes

- This is artifact-side status only. Provider-family billing should be added when export data becomes available.
- Reconcile provider family totals first; split by model only when provider exports expose reliable model-level rows.
- Dashboard implication: keep run directory timestamp, run start/end, session message UTC dates, provider billing UTC date, routed arm, observed backend, internal estimate, provider billed cost, and reconciliation status as separate fields.
- These artifacts are enough to characterize smoke-run behavior and internal estimated spend, but not enough to validate external provider invoices.
