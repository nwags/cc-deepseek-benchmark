import Link from "next/link";
import { TermInfo } from "../../components/TermInfo";
import { AppShell } from "../../components/AppShell";
import { DataFreshnessNotice } from "../../components/DataFreshnessNotice";
import { QualityBadge, QualityPassRate, buildSuspectNoopHref } from "../../components/QualityContext";
import { InvalidReason, ValidityBadge } from "../../components/ValidityContext";
import { buildArtifactHref } from "../../lib/links";
import { buildExactRunHref } from "../../lib/evidence-links";
import {
  ArmRunQualitySummaryRow,
  ArmRunSummaryRow,
  InvalidArmRunRow,
  getArmRunQualityByRunLabels,
  getArmRunRows,
  getInvalidArmRunRowsByRunLabels
} from "../../lib/dashboard-data";
import { findLatestIncludedExecutionAt } from "../../lib/data-freshness";
import { INDEX_ROUTE_FRESHNESS_SOURCES } from "../../lib/data-freshness-sources";
import { buildRegisteredOperationalFreshness } from "../../lib/data-freshness-server";
import { formatRecordedCost, formatNumber, formatSeconds } from "../../lib/format";
import {
  friendlyArmLabel,
  friendlyProviderLabel,
} from "../../lib/presentation-labels";

export const dynamic = "force-dynamic";

function runHealthLabel(row: ArmRunSummaryRow) {
  if (row.status === "completed") return "completed";
  if (row.status === "errors" && row.trial_count > 0) {
    return row.logical_mode === "full" ? "imported with trial errors" : "trial errors";
  }
  return row.status;
}

function fallbackQuality(row: ArmRunSummaryRow): ArmRunQualitySummaryRow {
  return {
    phase: "phase3",
    logical_mode: row.logical_mode,
    storage_mode: row.storage_mode,
    suite_id: row.suite_id,
    arm_id: row.arm_id,
    run_label: row.run_label,
    trial_count: row.trial_count,
    success_count: row.success_count,
    raw_pass_rate: row.pass_rate,
    suspect_noop_count: 0,
    exception_count: 0,
    normal_failed_count: Math.max(0, row.trial_count - row.success_count),
    qualified_trial_count: row.trial_count,
    qualified_success_count: row.success_count,
    qualified_pass_rate: row.pass_rate,
    recorded_cost_usd: row.trial_cost_usd,
    missing_cost_count: row.missing_cost_count
  };
}

function RunsTable({
  rows,
  qualityByRun,
  invalidByRun
}: {
  rows: ArmRunSummaryRow[];
  qualityByRun: Map<string, ArmRunQualitySummaryRow>;
  invalidByRun: Map<string, InvalidArmRunRow>;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th className="sticky-id-column">Run</th>
            <th>Suite</th>
            <th>Mode</th>
            <th>Validity</th>
            <th>Health</th>
            <th>Trials</th>
            <th><span className="term-label">Raw / qualified pass <TermInfo term="Raw pass rate" /></span></th>
            <th><span className="term-label">Suspect no-op <TermInfo term="Suspect no-op zero-token" /></span></th>
            <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
            <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
            <th><span className="term-label">R2 artifacts <TermInfo term="R2 artifact" /></span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const quality = qualityByRun.get(row.run_label) ?? fallbackQuality(row);
            const invalidRow = invalidByRun.get(row.run_label);
            return (
              <tr key={row.arm_run_id}>
                <td className="sticky-id-column">
                  <strong>
                    <Link href={buildExactRunHref(row.run_label, "all-imported")}>
                      {friendlyArmLabel(row.arm_id, row.backend_model)}
                    </Link>
                  </strong>
                  <div className="muted mono">{row.arm_id}</div>
                  <div className="muted">{friendlyProviderLabel(row.provider_family)}</div>
                  <div className="mono">{row.run_label}</div>
                  <div className="row-action-links">
                    <Link href={buildExactRunHref(row.run_label, "all-imported")}>Run detail</Link>
                    <Link href={`/trial-quality?run_label=${encodeURIComponent(row.run_label)}`}>Trial quality</Link>
                    <Link href={buildArtifactHref({ run_label: row.run_label })}>Artifacts</Link>
                  </div>
                </td>
                <td className="mono">{row.suite_id ?? "—"}</td>
                <td>{row.logical_mode}{row.storage_mode ? ` / ${row.storage_mode}` : ""}</td>
                <td>
                  <ValidityBadge row={invalidRow} />
                  {invalidRow ? (
                    <div className="muted">
                      <InvalidReason row={invalidRow} includeProvider={false} />
                    </div>
                  ) : null}
                </td>
                <td><span className={`status status-${row.status}`}>{runHealthLabel(row)}</span></td>
                <td>{formatNumber(row.trial_count)}</td>
                <td><QualityPassRate row={quality} /></td>
                <td>
                  {quality.suspect_noop_count > 0 ? (
                    <Link href={buildSuspectNoopHref({ run_label: row.run_label })}>
                      <QualityBadge count={quality.suspect_noop_count} />
                    </Link>
                  ) : (
                    <QualityBadge count={quality.suspect_noop_count} />
                  )}
                </td>
                <td>{formatSeconds(row.median_runtime_seconds)}</td>
                <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                <td>
                  {formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}
                  <div><Link href={buildArtifactHref({ run_label: row.run_label })}>Artifacts</Link></div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default async function RunsPage() {
  const rows = await getArmRunRows(200);
  const runLabels = rows.map((row) => row.run_label);
  const [qualityRows, invalidRows] = await Promise.all([
    getArmRunQualityByRunLabels(runLabels),
    getInvalidArmRunRowsByRunLabels(runLabels)
  ]);
  const qualityByRun = new Map(qualityRows.map((row) => [row.run_label, row]));
  const invalidByRun = new Map(invalidRows.map((row) => [row.run_label, row]));

  const fullRows = rows.filter((row) => row.logical_mode === "full");
  const diagnosticRows = rows.filter((row) => row.logical_mode !== "full");
  const latestExecution = findLatestIncludedExecutionAt(rows.map((row) => row.finished_at));
  const freshness = buildRegisteredOperationalFreshness(
    INDEX_ROUTE_FRESHNESS_SOURCES.runs,
    { queryStatus: "available", value: latestExecution.latestTimestamp },
    new Date().toISOString(),
    latestExecution.invalidTimestampCount
      ? `${latestExecution.invalidTimestampCount} displayed run completion timestamp(s) were invalid and excluded from the latest-execution calculation.`
      : null,
  );

  return (
    <AppShell title="Runs">
      <section className="quality-context-panel">
        Invalid/quarantined runs are retained for audit but excluded from valid-only comparison views.
      </section>
      <DataFreshnessNotice freshness={freshness} />

      <section className="panel">
        <div className="panel-heading">
          <h2>Full-suite runs</h2>
          <p>Complete imported arm executions for the full benchmark suite.</p>
        </div>
        <RunsTable rows={fullRows} qualityByRun={qualityByRun} invalidByRun={invalidByRun} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Diagnostic canary and smoke runs</h2>
          <p>Route validation, smoke tests, failed canaries, and historical diagnostic runs.</p>
        </div>
        <RunsTable rows={diagnosticRows} qualityByRun={qualityByRun} invalidByRun={invalidByRun} />
      </section>
    </AppShell>
  );
}
