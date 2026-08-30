# Evidence Review page guide

## Executive summary

Evidence Review is the frozen, manifest-validated qualitative review surface. It exposes the
complete reviewed-trial population, a separately filtered manual-review queue, control strata, arm
summaries, and task disagreements. It fails closed when the validated snapshot is unavailable and
never rewrites raw benchmark scores or immutable evidence.

## Route and implementation

- Dashboard route: `/comprehensive-review`.
- Page source: `apps/dashboard/src/app/comprehensive-review/page.tsx`.
- The navigation label is Evidence Review; the implementation route remains `/comprehensive-review`
  for compatibility.

## Data sources

- `getComprehensiveReviewData()` loads the checked-in comprehensive-review snapshot and validates
  its manifest relationship.
- Reviewed trial filters operate only over the frozen validated trial rows.
- Evidence links can preserve a reviewed source scope, normally Phase 3 extended.

## Population and authority

- The reviewed-trials section is the complete frozen comprehensive-review population.
- The manual-review queue is a subset/priority workflow and must not be mistaken for the complete
  reviewed population.
- Control strata and disagreement rows are derived from the same validated review package.
- Snapshot classifications are evidence-conditioned qualitative labels; raw outcome remains
  separate.

## How to read the page

- Start with coverage, manifest schema/generator/fingerprint, and evidence-completeness counts.
- Use the complete reviewed-trials table for exact classifications across outcome, failure,
  execution, activity, termination, policy, confidence, and review state.
- Use the queue for human-review prioritization, not prevalence estimates over the whole corpus.
- Use controls to compare suspicious cases against ordinary or deliberately matched evidence strata.

## Controls and filters

- `source_scope` selects the reviewed evidence context used by deep links.
- Reviewed-trial filters include trial, arm, run, task, raw outcome, failure subtype, execution
  validity, termination subtype, and policy disposition.
- The queue filters priority, arm, task, reason, and stratum; default queue priority is high.
- Disagreement filters include arm, task, category, outcome, and policy; tables support 25/50/100
  row page sizes.

## Caveats and non-inferences

- If the snapshot/manifest contract is unavailable or invalid, the page displays no substitute
  operational review rows.
- Classification confidence is categorical evidence strength, not a probability.
- The page never changes rewards, pass rates, denominators, quality flags, Supabase rows, or R2
  artifacts.
- A qualitative label is not permission to rescore a raw success or failure.

## Common workflows

- For an unsuccessful trial, compare raw outcome with reviewed failure/execution/termination/policy
  labels and then open exact evidence.
- For a sponsor-facing qualitative claim, sample exact reviewed trials plus appropriate control
  strata.
- For arm/task disagreement, use the filtered disagreement table and inspect both sides' exact trial
  evidence.

## Evidence tracing

- Reviewed row → exact trial detail with reviewed source scope → supporting artifacts.
- Arm summary count → exact filtered reviewed-trial population → individual cases.
- Review-queue reason → exact trial → evidence links and manual-review context.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Project Glossary](../../reference/GLOSSARY.md) for canonical terminology.
- [Trial Quality page guide](TRIAL_QUALITY.md).
- [Artifacts page guide](ARTIFACTS.md).
