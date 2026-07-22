import { AppShell } from "../../components/AppShell";
import { MetricCard } from "../../components/MetricCard";
import {
  getAdjustedCostArmRows,
  getAdjustedCostOverview,
  getAdjustedOutcomeCostRows
} from "../../lib/dashboard-data";
import { formatCurrency, formatNumber, formatPercent } from "../../lib/format";

export const dynamic = "force-dynamic";

const SUITE_ID = "phase3-full-20";

const costCategories = [
  {
    category: "Recorded cost",
    meaning: "Cost explicitly captured in imported benchmark metadata.",
    action: "Treat as a lower bound when missing-cost rows exist."
  },
  {
    category: "Adjusted known cost",
    meaning: "Recorded cost plus reconstructed missing-cost rows using configured pricing or same-arm empirical estimates.",
    action: "Use as the preferred sponsor-facing benchmark cost while keeping confidence labels visible."
  },
  {
    category: "Known accounting gap",
    meaning: "Adjusted known cost minus recorded cost.",
    action: "Use to quantify how much the raw dashboard undercounted."
  },
  {
    category: "Failure/incomplete spend",
    meaning: "Adjusted known cost spent on normal failures, exception failures, or incomplete outcomes.",
    action: "Use to quantify money spent on non-passing outcomes."
  },
  {
    category: "Exception with success signal",
    meaning: "A trial had reward=1 but also an exception marker.",
    action: "Keep separate from clean success; operationally unclean but not automatically a wrong answer."
  }
];

function labelList(value: string | null): string {
  return value ? value.split(",").join(", ") : "—";
}

function outcomeLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default async function CostCoveragePage() {
  const [overview, arms, outcomes] = await Promise.all([
    getAdjustedCostOverview(SUITE_ID),
    getAdjustedCostArmRows(SUITE_ID),
    getAdjustedOutcomeCostRows(SUITE_ID)
  ]);

  return (
    <AppShell
      title="Cost Coverage"
      description="Adjusted cost coverage, accounting gaps, and nonproductive spend for the valid full benchmark suite."
    >
      <section className="metric-grid">
        <MetricCard
          label="Recorded cost"
          value={formatCurrency(overview.recorded_cost_usd)}
          detail="Captured directly in benchmark metadata."
        />
        <MetricCard
          label="Adjusted known cost"
          value={formatCurrency(overview.adjusted_known_cost_usd)}
          detail="Recorded plus reconstructed known missing-cost rows."
        />
        <MetricCard
          label="Known accounting gap"
          value={formatCurrency(overview.known_accounting_gap_usd)}
          detail={`${formatNumber(overview.unresolved_cost_count)} unresolved rows remain.`}
        />
        <MetricCard
          label="Failure/incomplete spend"
          value={formatCurrency(overview.adjusted_failure_or_incomplete_cost_usd)}
          detail={formatPercent(overview.failure_or_incomplete_spend_share)}
        />
        <MetricCard
          label="Clean-success spend"
          value={formatCurrency(overview.adjusted_clean_success_cost_usd)}
          detail={`${formatNumber(overview.clean_success_count)} clean successes.`}
        />
        <MetricCard
          label="Unclean spend share"
          value={formatPercent(overview.nonproductive_or_unclean_spend_share)}
          detail="Includes failures, incomplete outcomes, and exception-with-success-signal rows."
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Adjusted cost frontier inputs</h2>
          <p>
            Valid-only full-suite arms ranked by adjusted known cost. Recorded cost remains preserved;
            adjusted known cost repairs missing-cost rows where the evidence supports it.
          </p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Arm</th>
                <th>Pass rate</th>
                <th>Recorded cost</th>
                <th>Adjusted known cost</th>
                <th>Gap</th>
                <th>Failure spend</th>
                <th>Failure share</th>
                <th>Cost / clean success</th>
                <th>Unresolved</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {arms.map((row) => (
                <tr key={row.arm_id}>
                  <td>
                    <strong>{row.arm_id}</strong>
                    <div className="muted">{row.backend_model ?? row.provider_family ?? "—"}</div>
                  </td>
                  <td>
                    {formatNumber(row.success_count)}/{formatNumber(row.trial_count)}
                    <div className="muted">{formatPercent(row.raw_pass_rate)}</div>
                  </td>
                  <td>{formatCurrency(row.recorded_cost_usd)}</td>
                  <td>{formatCurrency(row.adjusted_known_cost_usd)}</td>
                  <td>{formatCurrency(row.known_accounting_gap_usd)}</td>
                  <td>{formatCurrency(row.adjusted_failure_or_incomplete_cost_usd)}</td>
                  <td>{formatPercent(row.failure_or_incomplete_spend_share)}</td>
                  <td>{formatCurrency(row.adjusted_cost_per_clean_success)}</td>
                  <td>{formatNumber(row.unresolved_cost_count)}</td>
                  <td>
                    {labelList(row.cost_confidence_present)}
                    <div className="muted">{labelList(row.cost_sources_present)}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Outcome-cost breakdown</h2>
          <p>Suite-level adjusted known cost by outcome bucket.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Outcome bucket</th>
                <th>Trials</th>
                <th>Recorded cost</th>
                <th>Adjusted known cost</th>
                <th>Known gap</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.map((row) => (
                <tr key={row.outcome_bucket}>
                  <td>{outcomeLabel(row.outcome_bucket)}</td>
                  <td>{formatNumber(row.trial_count)}</td>
                  <td>{formatCurrency(row.recorded_cost_usd)}</td>
                  <td>{formatCurrency(row.adjusted_known_cost_usd)}</td>
                  <td>{formatCurrency(row.known_accounting_gap_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Cost source taxonomy</h2>
          <p>Interpretation rules for adjusted cost coverage.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Meaning</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {costCategories.map((row) => (
                <tr key={row.category}>
                  <td>{row.category}</td>
                  <td>{row.meaning}</td>
                  <td>{row.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
