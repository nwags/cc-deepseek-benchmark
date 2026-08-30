# Phase 3 Provider Cost Evidence Audit — 2026-08-25

## Purpose

This audit extends the frozen 2026-08-24 current-cost reconciliation without modifying that snapshot. It resolves the remaining Phase 3 provider/model arms using selected-run retained usage, provider-side historical evidence, official or retained price evidence, and where available durable R2 trajectories.

Two rules govern the successor layer:

1. A provider snapshot that predates a selected run cannot reconcile or confirm that selected run's billed cost.
2. Provider-family/window aggregates remain context when they cannot be cleanly allocated to the selected run; selected-run token reconstructions are reported separately.

## Newly audited selected-run costs

| Arm | Selected cost | Relation | Complete trials | Unresolved | Basis |
|---|---:|---|---:|---:|---|
| `router-grok-build-0.1` | `$6.418694` | `lower_bound` | 59/60 | 1 | `provider_rate_reconstructed_retained_usage_lower_bound` |
| `router-glm-5.1` | `$5.3316552` | `estimate` | 55/60 | 5 | `provider_rate_reconstructed_retained_usage_partial` |
| `router-glm-5.2` | `$8.9016736` | `estimate` | 60/60 | 0 | `provider_rate_reconstructed_selected_run` |
| `router-gemini-3.1-pro` | `$19.6968138` | `estimate` | 60/60 | 0 | `provider_rate_reconstructed_selected_run_request_tier` |
| `router-gemini-flash` | `$16.12091625` | `lower_bound` | 56/60 | 4 | `provider_rate_reconstructed_retained_usage_lower_bound` |
| `router-qwen-3.7-plus` | `$2.50442432` | `lower_bound` | 59/60 | 1 | `provider_rate_reconstructed_retained_usage_lower_bound` |
| `router-kimi-k2.6` | `$6.34692415` | `estimate` | 60/60 | 0 | `provider_rate_reconstructed_selected_run` |
| `router-kimi-k3` | `$26.570403` | `estimate` | 60/60 | 0 | `provider_rate_reconstructed_selected_run` |

## Key findings

- **Grok Build 0.1:** R2 trajectories exactly match retained coverage. One zero-token `polyglot-rust-c` trial also has zero trajectory metrics. `$6.418694` is therefore a retained-usage lower bound, not provider-billed selected-run cost.
- **GLM 5.1:** all five zero-token trials also have zero-metric R2 trajectories. Selected-run cache classification remains unverified, so `$5.3316552` is a partial rate estimate with five unresolved trials, not a strict lower bound.
- **GLM 5.2:** all 60 trials retain usage. `$8.9016736` is a complete selected-run rate reconstruction; the historical Z.AI bill is GLM 5.1 evidence and is not attributed to GLM 5.2.
- **Gemini 3.1 Pro:** 60 trajectories / 930 model responses exactly reproduce selected-run token totals. Every request is below Google's 200K tier boundary (max prompt 66,438), resolving the selected-run reconstruction to `$19.6968138`.
- **Gemini 3.5 Flash:** 56 trials retain usage and four do not. The selected run is absent from R2 even under a broad arm-prefix search, so trajectory recovery is unavailable. `$16.12091625` remains a lower bound.
- **Qwen 3.7 Plus:** historical Alibaba PAYG billing exactly validates the discounted Singapore token rates. Request-level trajectory evidence proves all retained selected-run requests are below 256K. One zero-metric trial remains unresolved, producing a `$2.50442432` lower bound.
- **Kimi K2.6:** historical Moonshot request logs and the dashboard total independently validate the token semantics/rate formula. All 60 selected trials retain usage; selected reconstruction is `$6.34692415`.
- **Kimi K3:** all 60 selected trials retain usage and reconstruct to `$26.570403`. The broader provider request log reconstructs to `$30.8143194`, but request-to-run allocation is low-confidence and official dated pricing-source provenance remains incomplete.

## Provider context chronology

See `results/phase3/reporting/phase3_provider_run_chronology_20260825.csv` for the dated evidence/run sequence. In particular, the historical xAI, GLM 5.1, Gemini, Qwen, and Kimi K2.6 provider-side totals precede their selected full sweeps and are therefore context/calibration evidence rather than selected-run billing.

## Immutable prior layer

The following 2026-08-24 artifacts remain frozen and are not modified:

- `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260824.csv`
- `results/phase3/reporting/phase3_anthropic_exception_lower_bound_reconciliation_20260824.csv`
- `results/phase3/reporting/phase3_current_reviewed_comparison_20260824.json`
- the generated V3 dashboard source.

The new `phase3_current_arm_cost_reconciliation_20260825.csv` is an additive successor evidence layer. Dashboard/current-comparison promotion should occur only after this new layer is reviewed and validated.
