# Eval Suites page guide

## Executive summary

Eval Suites is a dynamic operational index of Terminal-Bench suite groupings and their
valid-imported comparison totals. It is useful for understanding canary, smoke, and full workloads,
but it is not the fixed reviewed selected-run leaderboard population used by Overview.

## Route and implementation

- Dashboard route: `/eval-suites`.
- Page source: `apps/dashboard/src/app/eval-suites/page.tsx`.

## Data sources

- Supabase-backed `getEvalSuites()` operational query and Phase 3 suite freshness metadata.
- Suite/task membership stored in canonical eval-suite relations.
- Valid-imported comparison rows exclude invalid/quarantined arm runs.

## Population and authority

- Each row is one named suite and aggregates valid imported arm-run evidence represented for that
  suite.
- Canary, smoke, and full suites serve different diagnostic/comparison purposes; their pass rates
  are not interchangeable denominators.
- Displayed operational cost is not a substitute for the reviewed provider-aware Cost Coverage
  layer.

## How to read the page

- Use suite type and item count to understand the workload before comparing arm/trial totals.
- Open suite detail to inspect task-level and arm-level patterns inside one workload.
- Use full-suite views for substantive model comparison; canary/smoke remain primarily
  route/readiness diagnostics.

## Controls and filters

- The index has no scope selector; clicking a suite opens `/eval-suites/[suiteId]`.
- Freshness describes the operational population represented by the current valid-imported query.

## Caveats and non-inferences

- A suite aggregate can include a different set/count of valid imported runs than the frozen
  reviewed exact-run cohort.
- Do not compare a smoke pass rate with a full-suite pass rate as if workload difficulty and
  denominator were identical.
- Invalid/quarantined evidence is retained elsewhere for audit rather than silently included here.

## Common workflows

- Start here to answer 'what exactly was in this canary/smoke/full workload?'
- From a suite detail, move to the hard task or arm and then inspect exact run/trial evidence.

## Evidence tracing

- Suite row → suite detail → task/arm aggregate → exact run/trial → artifacts.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Evals page guide](EVALS.md).
- [Runs page guide](RUNS.md).
- [Trial Quality page guide](TRIAL_QUALITY.md).
