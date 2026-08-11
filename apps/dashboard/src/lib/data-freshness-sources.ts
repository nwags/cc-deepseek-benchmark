import {
  PHASE3_REVIEWED_COMPARISON,
  PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION,
} from "./phase3-reviewed-comparison";
import {
  PHASE3_REVIEWED_RUN_SELECTION,
  PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION,
} from "./phase3-reviewed-run-selection";
import type { DataSourceKind } from "./data-freshness";

export type DashboardDataSourceDefinition = Readonly<{
  sourceKind: DataSourceKind;
  sourceLabel: string;
  sourceRelations: readonly string[];
  populationLabel: string;
  reviewedAt: string | null;
  schemaVersion: string | null;
  provenanceIdentifier: string | null;
}>;

export const OVERVIEW_FRESHNESS_SOURCES = Object.freeze({
  reviewedComparison: Object.freeze({
    sourceKind: "reviewed",
    sourceLabel: "Phase 3 reviewed comparison",
    sourceRelations: Object.freeze([]),
    populationLabel: "Phase 3 extended reviewed comparison (16 arms / 960 trials)",
    reviewedAt: PHASE3_REVIEWED_COMPARISON.reviewedAt,
    schemaVersion: PHASE3_REVIEWED_COMPARISON_SCHEMA_VERSION,
    provenanceIdentifier:
      "results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json",
  } satisfies DashboardDataSourceDefinition),
  reviewedRunSelection: Object.freeze({
    sourceKind: "reviewed",
    sourceLabel: "Phase 3 reviewed run selection",
    sourceRelations: Object.freeze([]),
    populationLabel: "Frozen selected full-suite run label for each reviewed Phase 3 arm",
    reviewedAt: PHASE3_REVIEWED_RUN_SELECTION.reviewedAt,
    schemaVersion: PHASE3_REVIEWED_RUN_SELECTION_SCHEMA_VERSION,
    provenanceIdentifier:
      "results/phase3/reporting/phase3_reviewed_run_selection_20260809.json",
  } satisfies DashboardDataSourceDefinition),
  selectedRunEvidence: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres selected-run stored evidence",
    sourceRelations: Object.freeze([
      "benchmark.v_valid_arm_run_summary",
      "benchmark.benchmark_trials",
      "benchmark.v_trial_adjusted_cost_coverage",
      "benchmark.v_arm_run_quality_summary",
    ]),
    populationLabel: "Exact 16 frozen reviewed run labels",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  validImportedInventory: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres valid-imported Overview inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_valid_arm_run_summary",
      "benchmark.v_dashboard_runs",
    ]),
    populationLabel: "All imported Phase 3 rows belonging to valid runs",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  dynamicSuiteAggregates: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres dynamic full-suite task aggregates",
    sourceRelations: Object.freeze([
      "benchmark.v_valid_eval_arm_comparison",
      "benchmark.v_valid_arm_run_summary",
    ]),
    populationLabel: "Current valid-imported phase3-full-20 suite/arm aggregates",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
});

export const INDEX_ROUTE_FRESHNESS_SOURCES = Object.freeze({
  arms: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres all-imported arm inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_dashboard_arms",
      "benchmark.benchmark_arms",
      "benchmark.benchmark_trials",
      "benchmark.benchmark_runs",
    ]),
    populationLabel: "All registered arms; latest execution is derived from imported trial-bearing runs across run classes",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  artifacts: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres Phase 3 artifact metadata inventory",
    sourceRelations: Object.freeze([
      "benchmark.benchmark_artifacts",
      "benchmark.benchmark_runs",
      "benchmark.benchmark_trials",
      "benchmark.benchmark_arm_runs",
      "benchmark.v_trial_quality_flags",
      "benchmark.benchmark_invalid_arm_runs",
    ]),
    populationLabel: "Phase 3 artifact metadata matching the active evidence-browser filters",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  evalSuites: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres Phase 3 eval-suite inventory",
    sourceRelations: Object.freeze([
      "benchmark.benchmark_eval_suites",
      "benchmark.benchmark_eval_suite_items",
      "benchmark.v_valid_suite_arm_comparison",
      "benchmark.v_valid_arm_run_summary",
    ]),
    populationLabel: "Phase 3 suite catalog with valid-imported comparison rows",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  evals: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres valid-imported eval inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_valid_eval_arm_comparison",
      "benchmark.v_valid_arm_run_summary",
    ]),
    populationLabel: "Task rows from valid imported arm runs with trials",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  runs: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres imported arm-run inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_arm_run_summary",
      "benchmark.v_arm_run_quality_summary",
      "benchmark.benchmark_invalid_arm_runs",
    ]),
    populationLabel: "The latest 200 imported arm-run rows shown on this page",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  tasks: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres all-imported task inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_dashboard_tasks",
      "benchmark.benchmark_tasks",
      "benchmark.benchmark_trials",
      "benchmark.benchmark_runs",
    ]),
    populationLabel: "All registered tasks; latest execution is derived from imported trial-bearing runs across run classes",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  trialQuality: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres quality and validity inventory",
    sourceRelations: Object.freeze([
      "benchmark.v_arm_run_quality_summary",
      "benchmark.v_trial_quality_flags",
      "benchmark.benchmark_invalid_arm_runs",
      "benchmark.v_arm_run_summary",
    ]),
    populationLabel: "Displayed Phase 3 quality rows plus imported invalid-run audit rows",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
});

export const DETAIL_ROUTE_FRESHNESS_SOURCES = Object.freeze({
  artifactMetadata: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres artifact metadata",
    sourceRelations: Object.freeze([
      "benchmark.benchmark_artifacts",
      "benchmark.benchmark_runs",
      "benchmark.benchmark_trials",
      "benchmark.benchmark_arm_runs",
      "benchmark.v_trial_quality_flags",
      "benchmark.benchmark_invalid_arm_runs",
    ]),
    populationLabel: "The exact Phase 3 artifact record and its associated run/trial context",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  trialMetadata: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres trial evidence metadata",
    sourceRelations: Object.freeze([
      "benchmark.benchmark_trials",
      "benchmark.benchmark_runs",
      "benchmark.v_arm_run_summary",
      "benchmark.v_trial_quality_flags",
      "benchmark.benchmark_tasks",
      "benchmark.benchmark_invalid_arm_runs",
      "benchmark.benchmark_artifacts",
    ]),
    populationLabel: "The exact Phase 3 trial and its associated run, quality, validity, and artifact metadata",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  runDetail: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres Phase 3 run detail",
    sourceRelations: Object.freeze([
      "benchmark.v_dashboard_runs",
      "benchmark.benchmark_trials",
      "benchmark.benchmark_artifacts",
      "benchmark.v_arm_run_quality_summary",
      "benchmark.benchmark_invalid_arm_runs",
    ]),
    populationLabel: "One unambiguous Phase 3 run identity plus its stored trial, artifact, quality, and validity rows",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  evalSuiteDetail: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres eval-suite detail",
    sourceRelations: Object.freeze([
      "benchmark.benchmark_eval_suites",
      "benchmark.benchmark_eval_suite_items",
      "benchmark.v_valid_suite_arm_comparison",
      "benchmark.v_valid_eval_arm_comparison",
      "benchmark.v_valid_suite_arm_quality_summary",
      "benchmark.v_valid_arm_run_summary",
    ]),
    populationLabel: "The exact suite definition and valid-imported comparison population for that suite",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
  evalTaskDetail: Object.freeze({
    sourceKind: "operational",
    sourceLabel: "Supabase/Postgres eval/task detail",
    sourceRelations: Object.freeze([
      "benchmark.v_valid_eval_arm_comparison",
      "benchmark.v_valid_arm_run_summary",
      "benchmark.benchmark_trials",
    ]),
    populationLabel: "Valid-imported comparison rows that contain the exact displayed task",
    reviewedAt: null,
    schemaVersion: null,
    provenanceIdentifier: null,
  } satisfies DashboardDataSourceDefinition),
});
