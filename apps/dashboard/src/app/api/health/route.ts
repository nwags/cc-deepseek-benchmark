import { queryRows } from "../../../lib/db";
import { buildRegisteredOperationalFreshness } from "../../../lib/data-freshness-server";
import { LIVE_ROUTE_FRESHNESS_SOURCES } from "../../../lib/data-freshness-sources";

export async function GET() {
  try {
    const rows = await queryRows<{
      runs: number;
      trials: number;
      latest_included_execution_at: string | null;
    }>(`
      select
        count(*)::int as runs,
        coalesce(sum(trial_count), 0)::int as trials,
        max(finished_at)::text as latest_included_execution_at
      from benchmark.v_dashboard_runs
      where phase = 'phase3'
    `);
    const queriedAt = new Date().toISOString();
    const row = rows[0] ?? { runs: 0, trials: 0, latest_included_execution_at: null };
    const freshness = buildRegisteredOperationalFreshness(
      LIVE_ROUTE_FRESHNESS_SOURCES.apiHealth,
      { queryStatus: "available", value: row.latest_included_execution_at },
      queriedAt,
    );

    return Response.json({
      ok: true,
      phase: "phase3",
      runs: row.runs,
      trials: row.trials,
      source: freshness.sourceLabel,
      source_relations: freshness.sourceRelations,
      query_status: freshness.queryStatus,
      queried_at: freshness.queriedAt,
      latest_included_execution_at: freshness.latestIncludedExecutionAt,
      canonical_publication_status: freshness.canonicalPublicationStatus,
      freshness_status: freshness.freshnessStatus,
      freshness_reason: freshness.freshnessReason,
    });
  } catch {
    const queriedAt = new Date().toISOString();
    const freshness = buildRegisteredOperationalFreshness(
      LIVE_ROUTE_FRESHNESS_SOURCES.apiHealth,
      { queryStatus: "unavailable", value: null },
      queriedAt,
    );
    return Response.json({
      ok: false,
      phase: "phase3",
      source: freshness.sourceLabel,
      source_relations: freshness.sourceRelations,
      query_status: freshness.queryStatus,
      queried_at: freshness.queriedAt,
      latest_included_execution_at: null,
      canonical_publication_status: freshness.canonicalPublicationStatus,
      freshness_status: freshness.freshnessStatus,
      freshness_reason: freshness.freshnessReason,
    }, { status: 503 });
  }
}
