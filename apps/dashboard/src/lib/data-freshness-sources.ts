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
