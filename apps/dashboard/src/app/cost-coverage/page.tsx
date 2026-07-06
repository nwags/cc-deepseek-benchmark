import { AppShell } from "../../components/AppShell";

const costCategories = [
  {
    category: "Recorded cost",
    meaning: "Provider usage and cost were imported for the trial.",
    action: "Use normally in cost summaries."
  },
  {
    category: "Missing cost",
    meaning: "The trial completed or produced usage evidence, but cost was not recorded.",
    action: "Keep visible in audit views; do not treat as free."
  },
  {
    category: "Zero-token infrastructure failure",
    meaning: "The run failed before a real provider response or usage record.",
    action: "Classify as infrastructure evidence, not model quality."
  },
  {
    category: "Usage-recorded cost-missing",
    meaning: "Token usage exists but provider cost is missing.",
    action: "Escalate as a cost-ingestion or provider-metering anomaly."
  }
];

const auditChecks = [
  "Review missing_cost_count before using any dashboard cost total.",
  "Separate infrastructure timeouts from model failures.",
  "Do not count missing-cost rows as zero-cost wins.",
  "Preserve canary cost anomalies in reports and external summaries.",
  "Use phase-specific aggregates or imported dashboard views as source of truth."
];

export default function CostCoveragePage() {
  return (
    <AppShell
      title="Cost Coverage"
      description="Audit guidance for recorded cost, missing cost, zero-token failures, and usage-recorded anomalies."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Cost coverage categories</h2>
          <p>Interpretation rules for Phase 3 dashboard cost totals.</p>
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

      <section className="panel">
        <div className="panel-heading">
          <h2>Audit checklist</h2>
          <p>Use before reporting cost comparisons or approving smoke/full-sweep runs.</p>
        </div>
        <div className="placeholder-body">
          <ol>
            {auditChecks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ol>
          <p>
            Current dashboard cost strings distinguish recorded rows from missing rows using the imported
            cost coverage counters.
          </p>
        </div>
      </section>
    </AppShell>
  );
}
