# Evals page guide

## Executive summary

Evals starts from the Terminal-Bench task rather than the model. The default view is valid-imported
operational evidence; an all-imported alternate deliberately includes invalid/quarantined and other
diagnostic evidence. Neither view is a fixed reviewed full-suite leaderboard denominator.

## Route and implementation

- Dashboard route: `/evals`.
- Page source: `apps/dashboard/src/app/evals/page.tsx`.

## Data sources

- Supabase task-level operational aggregates through `getEvalRows()` for valid imported evidence.
- `getAllImportedEvalRows()` supplies the broader all-imported alternate.
- Population-specific freshness queries track the exact displayed task population.

## Population and authority

- `valid-imported` excludes invalid/quarantined arm runs but can include valid full, smoke, canary,
  diagnostic, legacy, or other imports.
- `all-imported` applies no validity exclusion and may therefore show higher counts or different
  rates.
- Task-level recorded cost is operational metadata and should not be promoted to provider-aware
  selected cost authority.

## How to read the page

- Use the task row to identify tasks with broad weakness, then open task detail to see which
  arms/runs contribute.
- Switch to all-imported when investigating whether excluded invalid/quarantined evidence changes
  the apparent task pattern.
- Read trial count and arm count with pass rate; a task with more contributing imports has a
  different denominator.

## Controls and filters

- `scope` selects valid-imported or all-imported inventory.
- Task detail links preserve the selected scope.
- Invalid/repeated scope input is normalized by the scope selector and surfaced as a warning.

## Caveats and non-inferences

- The default task index can combine multiple valid imports from the same arm.
- Do not infer the reviewed 16-run comparison denominator from an Evals row.
- All-imported is an audit/discovery population, not a fair leaderboard.

## Common workflows

- For a difficult task, compare valid-imported and all-imported views, then open task detail.
- For an arm-specific weakness, trace task detail to the exact run/trial and inspect
  verifier/trajectory evidence.

## Evidence tracing

- Eval row → `/evals/[taskId]` with same scope → contributing arm/run/trial → trial evidence /
  artifacts.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Eval Suites page guide](EVAL_SUITES.md).
- [Trial Quality page guide](TRIAL_QUALITY.md).
- [Artifacts page guide](ARTIFACTS.md).
