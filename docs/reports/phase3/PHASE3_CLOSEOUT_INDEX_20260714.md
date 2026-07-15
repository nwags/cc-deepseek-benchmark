# Phase 3 closeout index

This index collects the final Phase 3 benchmark artifacts, cross-phase comparisons, accounting audits, and sponsor-facing summaries.

## Primary sponsor artifacts

- `docs/reports/phase3/PHASE3_SPONSOR_SUMMARY_20260713.md`
- `docs/reports/phase3/PHASE3_SPONSOR_SUMMARY_20260713.pdf`
- `docs/reports/phase3/PHASE3_BENCHMARK_ANALYSIS_20260713.md`
- `docs/reports/phase3/PHASE3_BENCHMARK_ANALYSIS_20260713.pdf`
- `docs/reports/phase3/PHASE3_DATABRICKS_COMPARISON_20260713.md`
- `docs/reports/phase3/PHASE3_DATABRICKS_COMPARISON_20260713.pdf`

## Cross-phase comparison artifacts

- `docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md`
- `docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md`
- `results/phase3/reporting/cross_phase_adjusted_comparison_20260714.tsv`
- `results/phase3/reporting/cross_phase_task_arm_audit_20260714.tsv`
- `results/phase3/reporting/cross_phase_task_membership_20260714.tsv`
- `results/phase3/reporting/cross_phase_task_audit_issues_20260714.tsv`

## Phase 3 cost accounting artifacts

- `docs/reports/phase3/PHASE3_COST_COVERAGE_20260712.md`
- `results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv`
- `results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv`
- `results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv`
- `results/phase3/reporting/phase3_token_outcome_breakdown_20260713.tsv`

## Frontier chart artifacts

- `results/phase3/reporting/phase3_adjusted_cost_frontier_20260713.svg`
- `results/phase3/reporting/phase3_adjusted_cost_frontier_20260713.png`
- `results/phase3/reporting/phase3_adjusted_cost_frontier_20260713.html`
- `results/phase3/reporting/phase3_adjusted_cost_frontier_interactive_20260713.html`

## Source-of-truth aggregate files

- `results/phase1/combined.csv`
- `results/phase2/combined.csv`
- `results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv`
- `results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv`

## Current interpretation

The Phase 3 full-suite comparison is valid-only and contains 15 valid arms × 60 trials = 900 scored trials. Phase 1 and Phase 2 remain frozen historical baselines, but the cross-phase report adds a retrospective adjusted-cost layer so costs can be compared using the same missing-cost policy.

The task-suite audit confirms that Phase 1, Phase 2, and Phase 3 use the same 20-task suite and that every scored arm has 20 tasks × 3 attempts = 60 trials.

The cross-phase comparison should therefore be read as task-suite-equivalent and cost-accounting-adjusted, while still keeping routing path explicit: Phase 1/2 direct paths versus Phase 3 LiteLLM/router paths.

## Closeout integrity audit

- `scripts/audit_phase3_closeout_artifacts.py`
- `results/phase3/reporting/phase3_closeout_artifact_audit_20260715.tsv`

The closeout artifact audit verifies that the files referenced by this index exist in the repository.
