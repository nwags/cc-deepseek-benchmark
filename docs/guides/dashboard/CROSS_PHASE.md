# Cross-phase page guide

## Executive summary

Cross-phase is the file-backed comparison surface for Phases 1–3. Phase 1 and Phase 2 remain frozen
baselines. Phase 3 uses the selected current-reviewed 2026-08-25 cost layer for either the core or
extended reviewed scope, while historical Phase 3 cost decomposition, behavior tags, and router
comparisons remain visibly separate provenance.

## Route and implementation

- Dashboard route: `/cross-phase`.
- Page source: `apps/dashboard/src/app/cross-phase/page.tsx`.

## Data sources

- Frozen Phase 1/2 reporting rows from `cross-phase-reporting.ts`.
- Current reviewed Phase 3 V4 selected-cost data from `phase3-current-reviewed-comparison.ts`.
- Frozen exact selected-run membership from the reviewed run-selection contract, checked against
  chart membership.
- Historical Phase 3 behavior/router comparison data retained from the earlier reviewed core layer.

## Population and authority

- The scope selector chooses Phase 3 core or Phase 3 extended reviewed membership.
- Phase 1/2 rows remain frozen historical aggregates rather than being recomputed from the Phase 3
  operational database.
- The router-associated comparison section is historical Phase 3 core evidence and does not inherit
  Kimi K3 or the extended denominator.

## How to read the page

- Compare pass rate and comparison cost only after reading each phase/arm cost basis.
- For current Phase 3 rows, inspect selected cost relation/confidence and allocation status as well
  as the dollar value.
- Treat historical unclean-spend shares and behavior tags as historical evidence; they are not
  recomputed from later provider-billed selected totals.
- Use the cost-efficient clean-success table as aggregate efficiency, not per-outcome allocation.

## Controls and filters

- `scope` selects `phase3-core` or `phase3-extended`; unsupported/repeated scope input produces a
  visible warning and safe selection.
- Deep links preserve the selected Phase 3 scope when moving to Cost Coverage.

## Caveats and non-inferences

- Direct-versus-routed differences are observational and are not causal proof of LiteLLM impact;
  date, provider revisions, runner setup, run validity, and accounting policy also changed.
- Provider-billed aggregate totals are not redistributed across trials or outcomes.
- Do not treat historical Phase 3 router-cost ratios as though they were recomputed from current
  provider-billing corrections.

## Common workflows

- Use this page when the question explicitly spans benchmark phases or routing generations.
- For a Phase 3 economic claim, follow the arm into Cost Coverage and the exact selected run rather
  than stopping at the aggregate row.
- For route-effect hypotheses, use the historical comparison as a lead and inspect
  trajectories/artifacts before making a causal claim.

## Evidence tracing

- Phase 3 arm row → exact selected run → Artifacts / Trial Quality.
- Comparison cost → Cost Coverage with same scope → current and historical evidence classes.
- Historical router comparison → retained Phase 3 core reporting source → exact historical run
  evidence where available.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Overview page guide](OVERVIEW.md).
- [Cost Coverage page guide](COST_COVERAGE.md).
- [Artifacts page guide](ARTIFACTS.md).
