# Overview page guide

## Executive summary

Overview is the main decision-facing entry point, but it is deliberately not one homogeneous
population. The top comparison is the fixed reviewed Phase 3 extended cohort with current-reviewed
V4 selected costs and frozen selected-run identities. Lower discovery sections use current dynamic
valid-imported data. Read the population labels before comparing numbers across sections.

## Route and implementation

- Dashboard route: `/`.
- Page source: `apps/dashboard/src/app/page.tsx`.
- The interactive cost/performance chart can switch between reviewed Phase 3 core and extended scope
  without changing the top table's fixed extended comparison.

## Data sources

- Current reviewed Phase 3 V4 facts from
  `results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json` through
  `phase3-current-reviewed-comparison.ts`.
- Frozen exact reviewed run selection through `phase3-reviewed-run-selection.ts`; the database is
  asked only for those exact labels and does not select a newer similar run.
- Supabase operational reads for exact selected-run evidence, adjusted historical cost coverage,
  quality context, invalid-run audit state, valid-imported inventory, and dynamic full-suite task
  aggregates.
- The cost/performance chart derives from the same current-reviewed scope plus the frozen
  selected-run membership contract.

## Population and authority

- The headline reviewed comparison is Phase 3 extended: 16 selected reviewed full-suite runs, 20
  tasks and three attempts per arm.
- The current V4 selected-cost layer is decision-facing; the historical August 5 reviewed cost layer
  remains separate provenance.
- The headline mixed best-supported arm sum combines arm-level evidence classes. It is neither an
  exact provider invoice for the whole scope nor a global lower bound.
- The heatmap and hardest-eval sections are dynamic valid-imported `phase3-full-20` aggregates and
  may combine more than one valid import for an arm.
- The bottom valid-imported inventory includes valid canary, smoke, and full Phase 3 rows and is not
  the frozen selected-run cohort.

## How to read the page

- Use the top table for the current reviewed arm comparison and always inspect selected-cost basis,
  relation, confidence, provider-billing state, and allocation state alongside the dollar value.
- Use the selected reviewed run cards to move from reviewed aggregate facts to the exact stored run
  evidence.
- Use the chart to explore cost/pass-rate tradeoffs, not to replace qualitative artifact review.
- Treat the heatmap and hardest-eval list as discovery tools for current valid imports, not as
  extensions of the frozen 16-run comparison.

## Controls and filters

- `chart_scope` selects the chart's Phase 3 core or extended reviewed population; invalid values
  fail back with a visible warning.
- The chart itself supports arm selection, provider-family filtering, and alternative cost metrics;
  those controls only change the chart view.
- Deep links lead to selected run evidence, Trial Quality, Artifacts, Eval Suites, Evals, and Cost
  Coverage without changing the stored benchmark.

## Caveats and non-inferences

- Do not compare a dynamic valid-imported task aggregate directly with a fixed reviewed arm total as
  though the denominators were identical.
- A database outage does not cause Overview to substitute a newer run for missing selected-run
  evidence; the reviewed snapshot remains visible and the operational evidence is shown as
  unavailable.
- Provider aggregate selected costs are not redistributed to trials or outcome categories unless the
  reviewed allocation contract supports that precision.
- Raw recorded cost in the valid-imported inventory is not the same authority as current reviewed
  selected cost.

## Common workflows

- For 'which reviewed arm performed best?', start with the top reviewed comparison and then inspect
  the exact selected run and qualitative evidence.
- For 'which tasks look difficult right now?', use the dynamic heatmap/hardest-eval sections and
  then open the task detail.
- For economic comparison, open Cost Coverage from the selected arm/run and compare evidence classes
  before interpreting small cost differences.

## Evidence tracing

- Reviewed arm row → exact selected run link → run detail → trial detail → canonical artifacts.
- Reviewed cost → Cost Coverage → current selected-cost basis/relation → exact run → provider
  evidence or stated allocation limitation.
- Dynamic task signal → Evals task detail → exact contributing operational runs/trials → Artifacts
  or Trial Quality.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Codebase Guide](../CODEBASE_GUIDE.md) for implementation and provenance boundaries.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Cost Coverage page guide](COST_COVERAGE.md).
- [Runs page guide](RUNS.md).
