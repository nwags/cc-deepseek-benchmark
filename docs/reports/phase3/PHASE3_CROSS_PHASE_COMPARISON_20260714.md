# Cross-phase adjusted cost comparison

Phase 1, Phase 2, and Phase 3 are compared using an adjusted-cost layer for all phases.

Phase 1 and Phase 2 source aggregates remain frozen. Their adjusted-cost coverage tables are derived reporting artifacts. Phase 3 uses the existing valid-only sponsor summary with adjusted known cost.

The comparison is apples-to-apples at the benchmark-unit level: 20 tasks × 3 attempts per arm. The routing path remains explicit because Phase 3 used LiteLLM/router infrastructure.

## Task-suite comparability basis

Task-suite comparability is checked in `PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md` and the accompanying task-membership TSV. The intended scored-arm unit is 20 tasks × 3 attempts = 60 trials per arm. The cost/performance comparison should be read together with that audit.

## Cost accounting basis

Phase 1 and Phase 2 recorded costs remain the frozen historical headline values. The adjusted-cost columns in this report are retrospective derived reporting artifacts.

For Phase 1, every row already had recorded effective cost, so recorded and adjusted cost are identical.

For Phase 2, the derived adjusted layer found missing `effective_cost_usd` rows with token metadata. Those rows are reconstructed using the same-arm empirical effective USD-per-token policy used for Phase 3 missing-cost coverage. This is why Phase 2 Opus increases from $50.93 recorded to $68.47 adjusted, and Phase 2 Sonnet increases from $28.36 recorded to $29.82 adjusted. Confidence labels remain visible because those reconstructed rows are not provider-invoice-confirmed trial costs.

Phase 3 uses the existing valid-only sponsor summary and adjusted known cost layer.


## Phase totals

| Phase | Arms | Trials | Successes | Pass rate | Recorded cost | Adjusted known cost |
|---|---:|---:|---:|---:|---:|---:|
| phase1 | 3 | 180 | 118 | 65.6% | $40.41 | $40.41 |
| phase2 | 5 | 300 | 185 | 61.7% | $96.03 | $115.03 |
| phase3 | 15 | 900 | 515 | 57.2% | $820.77 | $972.17 |

## Arm table

| Phase | Arm | Routing path | Pass rate | Adjusted cost | Cost / clean success | Confidence |
|---|---|---|---:|---:|---:|---|
| phase1 | `arm-b-deepseek-pro` | phase1_direct | 70.0% | $2.01 | $0.05 | high |
| phase1 | `arm-a-anthropic` | phase1_direct | 65.0% | $37.30 | $0.98 | high |
| phase1 | `arm-c-deepseek-flash` | phase1_direct | 61.7% | $1.10 | $0.03 | high |
| phase2 | `arm-anthropic-opus` | phase2_direct | 75.0% | $68.47 | $1.59 | mixed |
| phase2 | `arm-anthropic-sonnet` | phase2_direct | 66.7% | $29.82 | $0.76 | medium |
| phase2 | `arm-deepseek-pro` | phase2_direct | 65.0% | $1.71 | $0.05 | high |
| phase2 | `arm-deepseek-flash` | phase2_direct | 58.3% | $0.72 | $0.02 | high |
| phase2 | `arm-anthropic-haiku` | phase2_direct | 43.3% | $14.31 | $0.57 | high |
| phase3 | `router-gpt-5.5` | litellm_router | 73.3% | $183.96 | $4.38 | mixed |
| phase3 | `router-deepseek-flash` | litellm_router | 66.7% | $56.80 | $1.42 | medium |
| phase3 | `router-anthropic-fable-5` | litellm_router | 65.0% | $37.69 | $1.02 | medium |
| phase3 | `router-anthropic-opus` | litellm_router | 65.0% | $64.49 | $1.65 | mixed |
| phase3 | `router-gpt-5.4` | litellm_router | 65.0% | $183.65 | $4.83 | low |
| phase3 | `router-glm-5.2` | litellm_router | 63.3% | $25.32 | $0.72 | medium |
| phase3 | `router-gemini-3.1-pro` | litellm_router | 63.3% | $46.47 | $1.29 | low |
| phase3 | `router-deepseek-pro` | litellm_router | 61.7% | $50.44 | $1.36 | medium |
| phase3 | `router-glm-5.1` | litellm_router | 60.0% | $20.30 | $0.58 | mixed |
| phase3 | `router-grok-build-0.1` | litellm_router | 60.0% | $53.15 | $1.48 | mixed |
| phase3 | `router-qwen-3.7-plus` | litellm_router | 55.0% | $34.94 | $1.09 | mixed |
| phase3 | `router-kimi-k2.6` | litellm_router | 50.0% | $35.13 | $1.17 | low |
| phase3 | `router-anthropic-sonnet` | litellm_router | 46.7% | $52.79 | $1.89 | mixed |
| phase3 | `router-anthropic-haiku-sanitized` | litellm_router | 41.7% | $83.51 | $3.34 | high |
| phase3 | `router-gemini-flash` | litellm_router | 21.7% | $43.53 | $4.84 | mixed |
