import Link from "next/link";
import {
  CHART_X_AXIS_OPTIONS,
  buildAccessibleChartRows,
  type ChartArmDatum,
  type ChartEvidenceAmount,
  type ChartMetricValue,
  type ChartScope,
  type ChartXAxisMetric,
} from "../lib/cost-performance-chart-view";

export type CostPerformanceChartTableProps = Readonly<{
  arms: readonly ChartArmDatum[];
  xMetric: ChartXAxisMetric;
  caption?: string;
}>;

function xMetricLabel(metric: ChartXAxisMetric): string {
  return CHART_X_AXIS_OPTIONS.find((option) => option.metric === metric)?.label ?? metric;
}

function scopeLabel(scope: ChartScope): string {
  return scope === "phase3-core" ? "Phase 3 core" : "Phase 3 extended";
}

function metricText(value: ChartMetricValue): string {
  if (value.status === "unavailable") return `Unavailable — ${value.reason}`;
  return `$${value.decimalUsd}${value.qualification ? ` — ${value.qualification}` : ""}`;
}

function evidenceAmountText(value: ChartEvidenceAmount): string {
  if (value.status === "unavailable") return `Unavailable — ${value.reason}`;
  return `$${value.decimalUsd}`;
}

function linkedMetric(value: ChartMetricValue, href: string) {
  const text = metricText(value);
  return value.status === "available" ? <Link href={href}>{text}</Link> : text;
}

function linkedEvidenceAmount(value: ChartEvidenceAmount, href: string) {
  const text = evidenceAmountText(value);
  return value.status === "available" ? <Link href={href}>{text}</Link> : text;
}

function evidenceStatusLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export function CostPerformanceChartTable({
  arms,
  xMetric,
  caption,
}: CostPerformanceChartTableProps) {
  const rows = buildAccessibleChartRows(arms, xMetric);
  const metricLabel = xMetricLabel(xMetric);

  return (
    <section aria-label="Accessible cost and performance chart data">
      <div className="table-wrap">
        <table>
          <caption>
            {caption ?? `Non-hover equivalent for the cost/performance chart. Current x-axis: ${metricLabel}.`}
          </caption>
          <thead>
            <tr>
              <th scope="col">Arm</th>
              <th scope="col">Provider family</th>
              <th scope="col">Scope membership</th>
              <th scope="col">Selected reviewed run</th>
              <th scope="col">Successes / trials</th>
              <th scope="col">Pass rate</th>
              <th scope="col">{metricLabel}</th>
              <th scope="col">Cost basis</th>
              <th scope="col">Confidence and provenance</th>
              <th scope="col">Accounting gap</th>
              <th scope="col">Failure / incomplete spend</th>
              <th scope="col">Qualification</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row) => (
              <tr key={row.armId}>
                <th scope="row">
                  <div>{row.displayName}</div>
                  <div className="mono">{row.armId}</div>
                  <div className="row-action-links">
                    <Link href={row.armHref}>Arm evidence</Link>
                  </div>
                </th>
                <td>
                  <div>{row.providerFamilyLabel}</div>
                  {row.reviewedProvider !== row.providerFamily ? (
                    <div>Reviewed provider value: <span className="mono">{row.reviewedProvider}</span></div>
                  ) : null}
                </td>
                <td>{row.scopeMembership.map(scopeLabel).join(" · ")}</td>
                <td>
                  <Link className="mono" href={row.selectedRunHref}>{row.selectedRunLabel}</Link>
                </td>
                <td>{row.successCount} / {row.trialCount}</td>
                <td>{(row.passRate * 100).toFixed(1)}%</td>
                <td>{linkedMetric(row.xMetricValue, row.costProvenanceHref)}</td>
                <td>
                  <div>{row.costBasisLabel}</div>
                  <div className="mono">{row.costBasis}</div>
                  <div>Selected total: ${row.selectedCostUsd}</div>
                  {row.selectedCostUsd !== row.historicalReviewedCostUsd ? (
                    <div>
                      Historical reviewed total:{" "}
                      <Link href={row.costProvenanceHref}>
                        ${row.historicalReviewedCostUsd}
                      </Link>
                    </div>
                  ) : null}
                  <div>Selected sources: {row.costSources.join(", ")}</div>
                </td>
                <td>
                  <div>Cost confidence: {row.costConfidence}</div>
                  <div>Historical pricing provenance: {evidenceStatusLabel(row.pricingProvenanceStatus)}</div>
                  <div>Historical arm/run allocation: {evidenceStatusLabel(row.armRunAllocationConfidence)}</div>
                  <div>Selected trial allocation: {evidenceStatusLabel(row.trialAllocationStatus)}</div>
                  <div>Provider billing reconciliation: {evidenceStatusLabel(row.billingReconciliationStatus)}</div>
                  {row.providerSelectedRunLabel ? (
                    <div>
                      Provider-reconciled run:{" "}
                      <span className="mono">{row.providerSelectedRunLabel}</span>
                    </div>
                  ) : null}
                  <div>Provider-log exclusivity: {row.providerLogExclusivityStatus
                    ? evidenceStatusLabel(row.providerLogExclusivityStatus)
                    : "not separately qualified in G1"}</div>
                </td>
                <td>
                  <div>Historical reviewed gap</div>
                  <Link href={row.costProvenanceHref}>${row.accountingGapUsd}</Link>
                </td>
                <td>{linkedEvidenceAmount(row.failureIncompleteSpend, row.costProvenanceHref)}</td>
                <td>{row.qualificationText ?? "No additional qualification beyond the listed reviewed evidence statuses."}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={12}>No arms are currently selected and visible.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
