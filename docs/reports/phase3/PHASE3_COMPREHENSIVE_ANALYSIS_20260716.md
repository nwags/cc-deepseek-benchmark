# Phase 3 comprehensive benchmark analysis (20260716)

## Scope

This report extends the Phase 3 benchmark analysis with router-associated comparisons, task-family analysis, cost efficiency, wastage, and behavioral profiling.

Primary generated artifacts:

- results/phase3/reporting/router_effect_comparison_20260716.tsv
- docs/reports/phase3/PHASE3_ROUTER_EFFECT_COMPARISON_20260716.md
- configs/tasks/phase3_task_taxonomy.tsv
- results/phase3/reporting/phase3_task_family_arm_matrix_20260716.tsv
- results/phase3/reporting/phase3_arm_behavior_profile_20260716.tsv

Existing inputs incorporated:

- docs/reports/phase3/PHASE3_BENCHMARK_ANALYSIS_20260713.md
- docs/reports/phase3/PHASE3_COST_COVERAGE_20260712.md
- docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md
- docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md
- results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv
- results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv
- results/phase3/reporting/phase3_arm_qualitative_summary_20260712.tsv

## Executive summary

- Phase 3 valid full-suite layer covers 15 arms, 900 trials, and 515 raw successes.
- Aggregate Phase 3 raw pass rate across arms is 57.2%.
- Aggregate adjusted known cost across Phase 3 valid arms is $972.17.
- Aggregate unclean spend is $364.29, or 37.5% of adjusted known cost.

## Highest raw pass-rate arms

| Arm | Successes | Pass rate | Adjusted cost | Cost per clean success | Unclean spend share |
|---|---:|---:|---:|---:|---:|
| router-gpt-5.5 | 44/60 | 73.3% | $183.96 | $4.38 | 26.1% |
| router-deepseek-flash | 40/60 | 66.7% | $56.80 | $1.42 | 24.4% |
| router-anthropic-fable-5 | 39/60 | 65.0% | $37.69 | $1.02 | 46.1% |
| router-anthropic-opus | 39/60 | 65.0% | $64.49 | $1.65 | 47.7% |
| router-gpt-5.4 | 39/60 | 65.0% | $183.65 | $4.83 | 21.6% |
| router-glm-5.2 | 38/60 | 63.3% | $25.32 | $0.72 | 32.5% |
| router-gemini-3.1-pro | 38/60 | 63.3% | $46.47 | $1.29 | 31.1% |

## Lowest adjusted cost per clean success

| Arm | Successes | Pass rate | Adjusted cost | Cost per clean success | Behavior tags |
|---|---:|---:|---:|---:|---|
| router-glm-5.1 | 36/60 | 60.0% | $20.30 | $0.58 | mid-pass-rate;cost-efficient-clean-success;exception-heavy;lower-token-success-pattern |
| router-glm-5.2 | 38/60 | 63.3% | $25.32 | $0.72 | mid-pass-rate;cost-efficient-clean-success;exception-heavy;lower-token-success-pattern |
| router-anthropic-fable-5 | 39/60 | 65.0% | $37.69 | $1.02 | mid-pass-rate;cost-efficient-clean-success;exception-heavy;middle-token-success-pattern |
| router-qwen-3.7-plus | 33/60 | 55.0% | $34.94 | $1.09 | lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern |
| router-kimi-k2.6 | 30/60 | 50.0% | $35.13 | $1.17 | lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern |
| router-gemini-3.1-pro | 38/60 | 63.3% | $46.47 | $1.29 | mid-pass-rate;cost-efficient-clean-success;exception-heavy;middle-token-success-pattern |
| router-deepseek-pro | 37/60 | 61.7% | $50.44 | $1.36 | mid-pass-rate;cost-efficient-clean-success;higher-token-success-pattern |

## Highest unclean spend share

| Arm | Pass rate | Adjusted cost | Unclean spend share | Failure/incomplete token share | Qualitative flags |
|---|---:|---:|---:|---:|---|
| router-anthropic-haiku-sanitized | 41.7% | $83.51 | 65.6% | 65.7% | lower-pass-rate;high-unclean-spend;higher-token-success-pattern |
| router-kimi-k2.6 | 50.0% | $35.13 | 62.8% | 56.2% | lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern |
| router-gemini-flash | 21.7% | $43.53 | 60.8% | 51.7% | lower-pass-rate;expensive-clean-success;exception-heavy;high-unclean-spend;suspect-noop-present;middle-token-success-pattern |
| router-grok-build-0.1 | 60.0% | $53.15 | 56.1% | 54.9% | mid-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern |
| router-qwen-3.7-plus | 55.0% | $34.94 | 54.8% | 45.5% | lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern |
| router-anthropic-opus | 65.0% | $64.49 | 47.7% | 21.8% | mid-pass-rate;higher-token-success-pattern |
| router-anthropic-fable-5 | 65.0% | $37.69 | 46.1% | 16.7% | mid-pass-rate;cost-efficient-clean-success;exception-heavy;middle-token-success-pattern |

## Task-family performance

Task families are generated as a reviewable heuristic taxonomy in configs/tasks/phase3_task_taxonomy.tsv. The taxonomy should be treated as an analysis aid, not as a benchmark ground truth.

| Task family | Trials | Successes | Pass rate | Adjusted cost | Unclean cost share |
|---|---:|---:|---:|---:|---:|
| data-processing | 45 | 43 | 95.6% | $19.81 | 2.3% |
| optimization-finance | 45 | 40 | 88.9% | $28.43 | 10.9% |
| build-packaging | 90 | 70 | 77.8% | $134.70 | 26.3% |
| security-crypto | 180 | 132 | 73.3% | $141.80 | 19.6% |
| web-networking | 90 | 62 | 68.9% | $38.69 | 18.0% |
| database-storage | 90 | 44 | 48.9% | $64.34 | 52.8% |
| concurrency-async | 45 | 21 | 46.7% | $17.28 | 57.5% |
| systems-low-level | 90 | 37 | 41.1% | $141.60 | 39.2% |
| language-implementation | 45 | 18 | 40.0% | $159.59 | 56.3% |
| ml-scientific | 180 | 48 | 26.7% | $225.93 | 44.8% |

## Router-associated findings

The focused router comparison is emitted separately and summarized here. It compares matched direct Phase 1/2 arms to Phase 3 LiteLLM-router arms where a model-family counterpart exists.

| Model family | Direct phase | Router arm | Pass delta | Cost ratio | Runtime ratio | Interpretation |
|---|---|---|---:|---:|---:|---|
| Anthropic Sonnet | phase1 | router-anthropic-sonnet | -18.3 pp | 1.42 | 0.64 | router-associated pass rate lower; adjusted cost broadly similar |
| Anthropic Sonnet | phase2 | router-anthropic-sonnet | -20.0 pp | 1.77 | 0.63 | router-associated pass rate lower; router run materially more expensive |
| DeepSeek Pro | phase1 | router-deepseek-pro | -8.3 pp | 25.09 | 0.53 | router-associated pass rate lower; router run materially more expensive |
| DeepSeek Pro | phase2 | router-deepseek-pro | -3.3 pp | 29.45 | 0.57 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |
| DeepSeek Flash | phase1 | router-deepseek-flash | 5.0 pp | 51.49 | 1.14 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |
| DeepSeek Flash | phase2 | router-deepseek-flash | 8.3 pp | 79.31 | 1.05 | router-associated pass rate higher; router run materially more expensive; router run had lower unclean spend share |
| Anthropic Opus | phase2 | router-anthropic-opus | -10.0 pp | 0.94 | 1.19 | router-associated pass rate lower; adjusted cost broadly similar |
| Anthropic Haiku | phase2 | router-anthropic-haiku-sanitized | -1.7 pp | 5.84 | 0.97 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |

## Behavioral interpretation layer

The behavior profile table groups arms by observed cost, token, exception, and wastage signatures. It is intended to guide follow-up qualitative review rather than replace manual artifact inspection.

Examples of generated behavior tags:

- high-pass-rate: raw pass rate at or above 70%.
- cost-efficient-clean-success: adjusted cost per clean success at or below $1.50.
- exception-heavy: at least 10 exception-classified trials.
- high-unclean-spend: at least half of adjusted spend went to failures, incomplete outcomes, or exception-with-success-signal rows.
- lower-token-success-pattern / higher-token-success-pattern: median successful-attempt visible tokens are materially below or above the suite median.

## Caveats

- Router-associated differences are not causal proof of LiteLLM effects.
- Cross-phase comparisons are confounded by time, provider-side model revisions, runner configuration, routing path, invalid-run policy, and accounting changes.
- The Phase 3 Haiku sanitized arm includes an Anthropic sanitizer path and should not be treated as a pure router-only comparison.
- Task-family taxonomy is heuristic and reviewable.
- Visible token sums are derived from imported token fields and are best used for relative behavioral profiling, not provider billing reconciliation.
