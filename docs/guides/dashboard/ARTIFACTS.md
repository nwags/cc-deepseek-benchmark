# Artifacts page guide

## Executive summary

Artifacts is the main canonical evidence browser. It groups retained evidence by trial or run root,
lets filters select matching evidence groups, and then deliberately expands every artifact in each
selected group so surrounding context is not hidden. The browser can include invalid/quarantined
runs because it is an audit surface.

## Route and implementation

- Dashboard route: `/artifacts`.
- Page source: `apps/dashboard/src/app/artifacts/page.tsx`.

## Data sources

- Canonical artifact metadata and trial/run context from Supabase.
- R2 URI/index state and bounded artifact previews/downloads where available.
- Local-path and other retained metadata remain provenance fields; display paths and evidence text
  are sanitized.
- Validity metadata is joined for the matching run labels.

## Population and authority

- The browser is all relevant canonical Phase 3 evidence matching the filter contract, including
  invalid/quarantined audit evidence.
- Filtering first selects matching evidence groups; all artifacts in those groups are then expanded.
- Canonical evidence completeness and R2 indexing are separate dimensions.

## How to read the page

- Read group context first: run, task, attempt, arm, reward, validity, quality flag, and evidence
  completeness.
- Use artifact type to distinguish result, transcript, verifier, trajectory, configuration,
  exception, and observability evidence.
- Treat `R2 indexed` as metadata indicating an object reference, not automatic proof that bytes were
  retrieved and hash-verified in this view.

## Controls and filters

- Database-backed filters include run label, suite, arm, task, quality flag, exception type, and
  artifact type.
- Free-text search covers paths, run labels, tasks, notes, and exception summaries.
- Group page size supports 10, 25, 50, or 100; pagination preserves active filters.
- Artifact detail, trial diagnosis, run detail, eval task, and Trial Quality links preserve the
  evidence context.

## Caveats and non-inferences

- The audit browser does not change reward, pass rate, denominator, validity, or quality flags.
- Missing optional artifact types do not automatically mean the trial itself is invalid.
- R2 indexing, artifact completeness, and R2 byte integrity are distinct claims.
- A single matching artifact does not hide non-matching sibling evidence because the entire group is
  expanded intentionally.

## Common workflows

- For a questionable result, filter by exact run/task/trial context and inspect result, verifier,
  transcript, and trajectory evidence together.
- For a provider/runtime anomaly, add exception or quality filters and then open the exact trial
  diagnosis.
- For completeness/integrity questions, move from group summary to artifact detail and inspect
  provenance.

## Evidence tracing

- Aggregate claim → exact run/trial → Artifacts group → artifact detail/preview.
- Failure diagnosis → Trial Quality/Evidence Review → exact trial → supporting artifact IDs.
- R2 reference → artifact detail → retained hash/size/provenance and bounded byte access where
  supported.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Trial Quality page guide](TRIAL_QUALITY.md).
- [Evidence Review page guide](EVIDENCE_REVIEW.md).
- [Artifact Policy runbook](../../runbooks/ARTIFACT_POLICY.md).
