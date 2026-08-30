# Runs page guide

## Executive summary

Runs is the canonical operational index of imported arm executions. It separates full-suite rows
from diagnostic canary/smoke/history, retains invalid or quarantined runs for audit, and links
aggregate results to exact run evidence. Exact run identity matters more than 'latest similar run.'

## Route and implementation

- Dashboard route: `/runs`.
- Page source: `apps/dashboard/src/app/runs/page.tsx`.
- `/arm-runs` is a legacy compatibility redirect to `/runs`; it is not a separate principal index.
- `/arm-runs/[armRunId]` remains an ID-based detail surface used by some exact evidence links.

## Data sources

- Supabase canonical arm-run summaries through `getArmRunRows(200)`.
- Operational arm-run quality summaries and invalid/quarantined records for the displayed labels.
- R2 artifact counts come from canonical artifact metadata associated with each imported run.

## Population and authority

- The index currently loads up to 200 canonical imported arm-run rows.
- Full rows are those with logical mode `full`; every other imported mode appears in the diagnostic
  section.
- Invalid/quarantined runs remain in the index but are excluded from valid-only comparison surfaces.
- Recorded cost is imported benchmark metadata, not necessarily reviewed provider-billed economic
  authority.

## How to read the page

- Use validity, health, raw/qualified pass, suspect-no-op count, runtime, recorded cost, and
  artifact count together.
- An `errors` run with trials can still be a structurally imported execution with trial errors
  rather than an ingestion failure.
- Open exact run detail before drawing conclusions from an aggregate card elsewhere.

## Controls and filters

- The index has no filter form; links provide per-run Trial Quality and Artifact drilldowns.
- The exact run detail route resolves by run label and fails closed if a Phase 3 label is ambiguous
  rather than choosing the newest row.

## Caveats and non-inferences

- Qualified pass rate is diagnostic and does not replace raw pass rate.
- Recorded cost can be incomplete when cost rows are missing.
- Diagnostic canary/smoke rows should not be read as full-suite model-quality comparisons.
- A run being present here means canonical metadata was imported; it does not imply every optional
  artifact exists.

## Common workflows

- Use Runs to locate the exact execution behind an Overview, Cross-phase, Trial Quality, or Artifact
  claim.
- For a problematic run, open Trial Quality and Artifacts from the same row before attributing a
  failure.
- For reviewed comparisons, verify that the run label matches the frozen selected-run contract.

## Evidence tracing

- Run row → `/runs/[runLabel]` → trials → exact trial evidence → artifacts.
- Run validity/quality flag → Trial Quality filtered to the same run → supporting artifacts.
- Reviewed selected-run link → exact canonical run; never substitute another same-arm run.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Live Runs page guide](LIVE_RUNS.md).
- [Trial Quality page guide](TRIAL_QUALITY.md).
- [Artifacts page guide](ARTIFACTS.md).
