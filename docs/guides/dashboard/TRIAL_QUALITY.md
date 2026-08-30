# Trial Quality page guide

## Executive summary

Trial Quality explains why a raw success or failure occurred without changing the raw benchmark
outcome. The page intentionally combines a frozen, manifest-bound J2 failure/trajectory taxonomy
over the reviewed 960-trial Phase 3 extended corpus with operational audit tables for imported runs,
invalid/quarantined state, and the legacy suspect-no-op heuristic.

## Route and implementation

- Dashboard route: `/trial-quality`.
- Page source: `apps/dashboard/src/app/trial-quality/page.tsx`.

## Data sources

- Frozen failure-taxonomy snapshot and registry through `failure-taxonomy-snapshot.ts` and
  `failure-taxonomy.ts`.
- Frozen failure-composition model built from the validated reviewed source relationship.
- Operational Supabase quality summaries, suspect-no-op rows, invalid/quarantined arm-run records,
  and exact freshness identities.
- Exact run/trial and artifact deep links preserve the evidence identity being diagnosed.

## Population and authority

- The J2 taxonomy is the frozen manifest-bound 960-trial reviewed Phase 3 extended population.
- Invalid/quarantined runs are excluded from primary valid-only scored comparisons but remain
  visible in audit sections.
- Arm-run summary and legacy suspect-no-op tables are operational imported evidence and are not the
  same fixed population as J2.
- Raw verifier outcome remains source-of-truth scoring; taxonomy axes are derived interpretation.

## How to read the page

- Start with the four independent frozen taxonomy axes and raw outcome rather than collapsing all
  failures into one behavior.
- Use failure composition for arm-level diagnostic structure, not a replacement pass rate.
- Use invalid-run records to understand why a run is retained for audit but excluded from valid-only
  comparisons.
- Treat `suspect_noop_zero_token` as legacy compatibility evidence when a frozen J2 diagnosis is
  available.

## Controls and filters

- Taxonomy filters accept only canonical registry IDs and support page sizes 25, 50, or 100.
- URL drilldowns can constrain suspect-no-op rows by suite, arm, run, task, and legacy quality flag.
- Exact trial links carry the reviewed source scope into trial evidence.

## Caveats and non-inferences

- The dashboard does not reclassify the frozen J2 rows from live database or R2 fallback data.
- Qualified pass rate is a diagnostic denominator that excludes legacy suspect no-ops; it does not
  replace raw benchmark pass rate.
- A timeout, setup/transport failure, provider-policy refusal, or verifier failure should not be
  inferred merely from reward 0.
- Snapshot unavailability fails closed: no operational taxonomy is silently substituted.

## Common workflows

- For a suspicious failure, filter J2 to the relevant axis value, open the exact trial, and inspect
  supporting artifacts.
- For an anomalous run, start with the arm-run quality summary, validity state, and
  suspect-no-op/exception counts before attributing the issue to the model.
- For arm-level failure mix, use the frozen composition panel and then sample exact trials.

## Evidence tracing

- Taxonomy row → exact trial → failure-taxonomy facts → supporting verifier/transcript/trajectory
  artifacts.
- Operational arm-run anomaly → exact run → Trial Quality rows → Artifacts.
- Invalid-run badge → invalid-run reason/provider-workflow identity → exact retained run evidence.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Evidence Review page guide](EVIDENCE_REVIEW.md).
- [Artifacts page guide](ARTIFACTS.md).
- [Runs page guide](RUNS.md).
