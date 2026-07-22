# Phase 3 Cost Coverage (20260712)

This report distinguishes recorded benchmark cost from reconstructed and unresolved missing-cost rows.

## Summary

- Trial rows: 900
- Recorded cost rows: 721
- Missing recorded-cost rows: 179
- Missing-cost rows with visible tokens: 150
- Configured-price reconstructed missing-cost rows: 54
- Same-arm empirical reconstructed missing-cost rows: 96
- Unresolved missing-cost rows: 29
- Recorded cost USD: $820.774729
- Configured-price reconstructed missing cost USD: $58.692740
- Same-arm empirical reconstructed missing cost USD: $92.702376
- Adjusted known cost USD: $972.169845

## Outcome-cost breakdown

- Clean-success trials: 499
- Exception-with-success-signal trials: 16
- Exception-failure trials: 190
- Normal-failure trials: 195
- Unknown/incomplete trials: 0
- Adjusted clean-success cost USD: $607.882369
- Adjusted exception-with-success-signal cost USD: $28.525410
- Adjusted failure/incomplete cost USD: $335.762066

## Cost source taxonomy

- `recorded_artifact`: `cost_usd` was present in imported benchmark metadata.
- `token_reconstructed_from_configured_price_snapshot`: `cost_usd` was missing, but DB token usage and a configured pricing snapshot were available.
- `empirical_reconstructed_from_same_arm_recorded_rows`: `cost_usd` was missing and no configured pricing snapshot was available, but enough same-arm rows had both token usage and recorded cost to estimate an empirical effective USD-per-token rate.
- `unresolved_missing_pricing`: token usage exists, but no configured pricing snapshot or empirical estimate was available.
- `unresolved_no_token_metadata`: neither cost nor token usage was recorded.

Provider-reconciled billing is intentionally not claimed by this report. This report repairs per-trial benchmark charting where possible; provider invoices/dashboards remain separate evidence.

