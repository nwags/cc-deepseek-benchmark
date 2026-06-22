import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { getArmRunRows } from "../../lib/dashboard-data";
import { formatRecordedCost, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

export default async function ArmRunsPage() {
  const rows = await getArmRunRows(200);

  return (
    <AppShell
      title="Arm Runs"
      description="One concrete model arm execution within a canary, smoke, or full suite."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Imported arm runs</h2>
          <p>Use this page to drill from arm-level outcome into task attempts and artifacts.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm run</th>
                <th>Suite</th>
                <th>Mode</th>
                <th>Status</th>
                <th>Trials</th>
                <th>Pass rate</th>
                <th>Median runtime</th>
                <th>Cost</th>
                <th>R2 artifacts</th>
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
                  <td><span className={`status status-${row.status}`}>{row.status}</span></td>
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
      </section>
    </AppShell>
  );
}
