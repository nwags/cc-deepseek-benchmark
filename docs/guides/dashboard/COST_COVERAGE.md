# Cost Coverage page guide

## Executive summary

Cost Coverage is the provenance-sensitive economic view. Current decision-facing Phase 3 arm costs
come from the 2026-08-25 current-reviewed V4 layer, while historical DR-303 benchmark-side
adjusted-cost and outcome-spend reconstruction is retained separately. A dollar value is not
interpretable without its evidence basis, relation, allocation state, and limitations.

## Route and implementation

- Dashboard route: `/cost-coverage`.
- Page source: `apps/dashboard/src/app/cost-coverage/page.tsx`.

## Data sources

- Current selected-cost facts from
  `results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json`.
- Frozen exact selected-run membership used by current cost/performance links.
- Historical DR-303 reviewed comparison and spend-decomposition evidence preserved as provenance.
- Supabase cost-provenance drilldowns and historical adjusted-cost coverage for exact run/trial
  context where available.

## Population and authority

- The scope selector chooses reviewed Phase 3 core or extended membership.
- Current selected arm costs may use exact provider billing, qualified provider-rate reconstruction,
  retained-accounting lower bounds, or explicit historical fallback depending on the arm.
- Historical DR-303 outcome-cost decomposition belongs to the earlier benchmark-side reconstructed
  layer and must not be silently recomputed from later provider totals.
- Provider aggregate selected cost can support aggregate per-attempt or per-clean-success ratios
  without supporting trial-level or outcome-level allocation.

## How to read the page

- Start with current selected cost, basis, relation, confidence, provider billing reconciliation,
  and trial/outcome allocation status.
- Use historical recorded/adjusted cost and accounting-gap fields to understand what the
  benchmark-side metadata captured or missed.
- Treat historical spend decomposition as provenance-sensitive diagnostic evidence, not as an
  allocation of later provider-billed aggregates.
- For Kimi K3, distinguish the V4 current-reviewed provider-rate reconstructed selected-run basis
  from the normalized reconciliation vocabulary; it is not invoice-level spend.

## Controls and filters

- `scope` selects reviewed Phase 3 core or extended population.
- Evidence deep links can focus the page by arm, run, or trial and preserve an evidence source
  scope.
- Current cost/performance controls link the selected arm to the exact frozen run and associated
  provenance.

## Caveats and non-inferences

- Never convert missing or unresolved evidence to zero.
- Do not fabricate per-trial or per-outcome dollars from an aggregate provider total when allocation
  is unsupported.
- A small numeric cost difference is not equivalent across exact billing, qualified estimate, and
  lower-bound evidence classes.
- Legacy/historical DR-303 labels describe the retained historical layer and do not supersede
  current V4 selected-cost authority.
- Kimi's selected trial reconstruction and unavailable reviewed outcome join are distinct:
  trial-level reconstruction does not create outcome-category allocation.

## Common workflows

- For an economic arm comparison, inspect both arms' selected evidence classes before comparing
  cost-per-success.
- For a suspicious accounting gap, trace from arm to exact run/trial coverage and the retained
  evidence source.
- For historical failure-spend analysis, stay within the historical DR-303 allocation contract.

## Evidence tracing

- Overview/Cross-phase selected cost → Cost Coverage arm → exact selected run → evidence
  basis/reconciliation/limitations.
- Historical accounting gap → exact run/trial adjusted-cost coverage → recorded usage/cost evidence.
- Current provider-aware value → provider evidence/reconciliation class; unsupported allocation
  remains explicit rather than inferred.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Overview page guide](OVERVIEW.md).
- [Cross-phase page guide](CROSS_PHASE.md).
- [Usage and Cost Evidence Model](../../methodology/USAGE_AND_COST_EVIDENCE_MODEL.md).
