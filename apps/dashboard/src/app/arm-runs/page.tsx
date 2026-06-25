import Link from "next/link";
import { TermInfo } from "../../components/TermInfo";
import { AppShell } from "../../components/AppShell";
import { ArmRunSummaryRow, getArmRunRows } from "../../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

function runHealthLabel(row: ArmRunSummaryRow) {
  if (row.status === "completed") return "completed";
  if (row.status === "errors" && row.trial_count > 0) {
    return row.logical_mode === "full" ? "imported with trial errors" : "trial errors";
  }
  return row.status;
}

function ArmRunTable({ rows }: { rows: ArmRunSummaryRow[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Arm run</th>
            <th>Suite</th>
            <th>Mode</th>
            <th>Health</th>
            <th>Trials</th>
            <th><span className="term-label">Pass rate <TermInfo term="Pass rate" /></span></th>
            <th><span className="term-label">Median runtime <TermInfo term="Median runtime" /></span></th>
            <th><span className="term-label">Recorded cost <TermInfo term="Recorded cost" /></span></th>
            <th><span className="term-label">R2 artifacts <TermInfo term="R2 artifact" /></span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.arm_run_id}>
              <td>
                <Link href={`/arm-runs/${row.arm_run_id}`}>{row.arm_id}</Link>
                <div className="mono">{row.run_label}</div>
              </td>
              <td className="mono">{row.suite_id ?? "—"}</td>
              <td>{row.logical_mode}{row.storage_mode ? ` / ${row.storage_mode}` : ""}</td>
              <td><span className={`status status-${row.status}`}>{runHealthLabel(row)}</span></td>
              <td>{formatNumber(row.trial_count)}</td>
              <td>{formatPercent(row.pass_rate)}</td>
              <td>{formatSeconds(row.median_runtime_seconds)}</td>
              <td>{formatRecordedCost(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
              <td>{formatNumber(row.r2_artifact_count)} / {formatNumber(row.artifact_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function ArmRunsPage() {
  const rows = await getArmRunRows(200);
  const fullRows = rows.filter((row) => row.logical_mode === "full");
  const diagnosticRows = rows.filter((row) => row.logical_mode !== "full");

  return (
    <AppShell
      title="Arm Runs"
      description="One concrete model arm execution within a canary, smoke, or full suite."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Full-suite arm runs</h2>
          <p>Primary sponsor-facing runs. Trial errors indicate benchmark attempt failures, not ingestion failure.</p>
        </div>
        <ArmRunTable rows={fullRows} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Diagnostic canary and smoke runs</h2>
          <p>Route validation, smoke tests, failed canaries, and historical diagnostic runs.</p>
        </div>
        <ArmRunTable rows={diagnosticRows} />
      </section>
    </AppShell>
  );
}
