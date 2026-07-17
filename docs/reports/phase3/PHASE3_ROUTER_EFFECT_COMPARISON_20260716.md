# Phase 3 router-associated comparison (20260716)

## Scope

This report compares matched model families that have direct Claude Code runs in Phase 1 and/or Phase 2 and LiteLLM-router runs in Phase 3.

This is an observational comparison, not causal proof. Routing path changed along with date, provider-side model revisions, runner setup, invalid-run handling, cost accounting, and in one case an Anthropic sanitizer path.

## Matched comparisons

| Model family | Direct baseline | Router arm | Pass delta | Cost ratio | Clean-success cost ratio | Runtime ratio | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| Anthropic Sonnet | phase1 39/60 | router-anthropic-sonnet 28/60 | -18.3 pp | 1.42 | 1.92 | 0.64 | router-associated pass rate lower; adjusted cost broadly similar |
| Anthropic Sonnet | phase2 40/60 | router-anthropic-sonnet 28/60 | -20.0 pp | 1.77 | 2.47 | 0.63 | router-associated pass rate lower; router run materially more expensive |
| DeepSeek Pro | phase1 42/60 | router-deepseek-pro 37/60 | -8.3 pp | 25.09 | 27.80 | 0.53 | router-associated pass rate lower; router run materially more expensive |
| DeepSeek Pro | phase2 39/60 | router-deepseek-pro 37/60 | -3.3 pp | 29.45 | 30.25 | 0.57 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |
| DeepSeek Flash | phase1 37/60 | router-deepseek-flash 40/60 | 5.0 pp | 51.49 | 46.34 | 1.14 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |
| DeepSeek Flash | phase2 35/60 | router-deepseek-flash 40/60 | 8.3 pp | 79.31 | 69.40 | 1.05 | router-associated pass rate higher; router run materially more expensive; router run had lower unclean spend share |
| Anthropic Opus | phase2 45/60 | router-anthropic-opus 39/60 | -10.0 pp | 0.94 | 1.04 | 1.19 | router-associated pass rate lower; adjusted cost broadly similar |
| Anthropic Haiku | phase2 26/60 | router-anthropic-haiku-sanitized 25/60 | -1.7 pp | 5.84 | 5.84 | 0.97 | pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share |

## Notes

- Cost ratios use adjusted known cost where available.
- Runtime ratios use median wall-clock seconds when both sides are available.
- For Phase 3 router arms, median runtime is computed from trial-level runtime fields because the cross-phase adjusted summary does not carry router median wall-clock values.
- The Haiku comparison is especially confounded because the Phase 3 arm is the sanitized router path.
- Source table: results/phase3/reporting/router_effect_comparison_20260716.tsv
