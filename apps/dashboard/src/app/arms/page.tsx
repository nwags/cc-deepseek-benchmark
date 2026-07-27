import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { getArmRows } from "../../lib/dashboard-data";
import { buildArtifactHref } from "../../lib/links";
import { formatCurrency, formatNumber, formatPercent, formatSeconds } from "../../lib/format";

export const dynamic = "force-dynamic";

function recordedCostLowerBound(
  costUsd: number | null,
  costRowCount: number,
  missingCostCount: number
) {
  const known = formatCurrency(costUsd);
  const missing = Number(missingCostCount ?? 0);
  const costRows = Number(costRowCount ?? 0);

  if (missing <= 0) {
    return (
      <div>
        <div>{known}</div>
        <div className="muted">{formatNumber(costRows)} recorded cost row{costRows === 1 ? "" : "s"}</div>
      </div>
    );
  }

  return (
    <div>
      <div>{known} recorded lower bound</div>
      <div className="muted">
        {formatNumber(missing)} raw cost row{missing === 1 ? "" : "s"} need coverage review · <Link href="/cost-coverage">Cost coverage</Link>
      </div>
    </div>
  );
}

export default async function ArmsPage() {
  const arms = await getArmRows();

  return (
    <AppShell title="Arms" description="All-imported model/backend aggregate. For valid full-suite comparisons, use Overview, Runs, or Eval Suites.">
      <section className="panel">
        <div className="panel-heading">
          <h2>Arm comparison</h2>
          <p>
            All imported runs by arm. This page can include canary, smoke, legacy, and diagnostic imports, so pass rates may differ from valid full-suite views.
          </p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm</th>
                <th>Runs</th>
                <th>Trials</th>
                <th>Successes</th>
                <th title="All-imported pass rate across every imported run for this arm. Use Runs or Overview for valid full-suite pass rates.">Pass rate</th>
                <th>Median runtime</th>
                <th title="Recorded cost lower bound for all imported rows. Missing raw cost rows may have adjusted estimates on Cost Coverage.">Recorded cost</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((row) => (
                <tr key={row.arm_id}>
                  <td className="sticky-id-column">
                    <div className="mono">{row.arm_id}</div>
                    <div className="row-action-links">
                      <Link href={`/trial-quality?arm_id=${encodeURIComponent(row.arm_id)}`}>Trial quality</Link>
                      <Link href={buildArtifactHref({ arm_id: row.arm_id })}>Artifacts</Link>
                      <Link href="/runs">Runs</Link>
                    </div>
                  </td>
                  <td>{formatNumber(row.run_count)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatNumber(row.success_count)}</td>
                  <td>{formatPercent(row.pass_rate)}</td>
                  <td>{formatSeconds(row.median_runtime_seconds)}</td>
                  <td>{recordedCostLowerBound(row.trial_cost_usd, row.cost_row_count, row.missing_cost_count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
