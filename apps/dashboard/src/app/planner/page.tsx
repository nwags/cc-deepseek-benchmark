import { AppShell } from "../../components/AppShell";

const runTypes = [
  {
    name: "canary",
    purpose: "One known canary task; infrastructure/model-route gate.",
    dispatchMode: "canary",
    scored: "Readiness evidence only"
  },
  {
    name: "smoke",
    purpose: "Small multi-task gate; next benchmark milestone.",
    dispatchMode: "smoke",
    scored: "Preliminary benchmark evidence"
  },
  {
    name: "full-sweep",
    purpose: "Large multi-task benchmark battery.",
    dispatchMode: "full",
    scored: "Phase 3 scored source of truth after approval"
  },
  {
    name: "ad-hoc",
    purpose: "One-off diagnostic run for a model, route, task, or runner issue.",
    dispatchMode: "canary/smoke/full with explicit notes",
    scored: "Not scored unless explicitly promoted"
  }
];

const plannerChecks = [
  "Confirm the target arm exists in configs/arms.",
  "Confirm the provider secret exists locally or in GitHub Actions.",
  "Confirm runner doctor and Docker-to-host LiteLLM firewall checks passed.",
  "Confirm direct provider and LiteLLM route probes for new providers.",
  "Review expected runtime, cost, task count, attempts, and concurrency.",
  "Use dry_run=true unless this is an explicitly approved paid run."
];

export default function PlannerPage() {
  return (
    <AppShell
      title="Planner"
      description="Review-only planner for canary, smoke, full-sweep, and ad-hoc Phase 3 dispatches."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Run types</h2>
          <p>Planner vocabulary and current GitHub Actions dispatch mapping.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run type</th>
                <th>Purpose</th>
                <th>Workflow mode</th>
                <th>Scored status</th>
              </tr>
            </thead>
            <tbody>
              {runTypes.map((runType) => (
                <tr key={runType.name}>
                  <td className="mono">{runType.name}</td>
                  <td>{runType.purpose}</td>
                  <td className="mono">{runType.dispatchMode}</td>
                  <td>{runType.scored}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Dispatch payload template</h2>
          <p>Copy, review, and run from the GitHub Actions page or local gh CLI.</p>
        </div>
        <div className="placeholder-body">
          <pre className="mono">{`gh workflow run phase3-arm-dispatch.yml \\
  --ref main \\
  -f arm_id=<router-arm-id> \\
  -f mode=<canary|smoke|full> \\
  -f dry_run=true \\
  -f confirm_paid_run=false \\
  -f n_attempts= \\
  -f n_concurrent=`}</pre>
          <p>
            Use <span className="mono">full</span> for the current workflow when the dashboard label is{" "}
            <span className="mono">full-sweep</span>. Keep paid runs gated by explicit review.
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Pre-dispatch checklist</h2>
          <p>Run these checks before launching paid benchmark work.</p>
        </div>
        <div className="placeholder-body">
          <ol>
            {plannerChecks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ol>
        </div>
      </section>
    </AppShell>
  );
}
