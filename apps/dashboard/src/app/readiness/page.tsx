import { AppShell } from "../../components/AppShell";

const readinessRows = [
  {
    area: "Direct provider API",
    requiredFor: "New or gated providers/models",
    evidence: "Tiny provider-native response probe"
  },
  {
    area: "LiteLLM route",
    requiredFor: "Every router arm",
    evidence: "/v1/models plus one minimal route completion"
  },
  {
    area: "Claude Code route",
    requiredFor: "Every provider family before Harbor canary",
    evidence: "claude --print probe through local LiteLLM"
  },
  {
    area: "Harbor canary",
    requiredFor: "Smoke eligibility",
    evidence: "modernize-scientific-stack canary run"
  },
  {
    area: "Runner firewall",
    requiredFor: "Remote Harbor runs",
    evidence: "Docker-to-host LiteLLM firewall doctor"
  },
  {
    area: "Hosted NVIDIA NIM",
    requiredFor: "Future NIM arm",
    evidence: "NVIDIA hosted API probe, then LiteLLM nvidia_nim route probe"
  }
];

const statusRows = [
  {
    route: "router-anthropic-fable-5",
    status: "canary-passed",
    note: "Initial timeout was Docker/UFW infrastructure; rerun passed after firewall fix."
  },
  {
    route: "claude-mythos-5",
    status: "gated",
    note: "Direct Anthropic probe returned 404/not_found for this account."
  },
  {
    route: "opusplan",
    status: "phase2-discovery-only",
    note: "Alias accepted in Phase 2 but observed execution did not show a true plan/execute cycle."
  },
  {
    route: "hosted NVIDIA NIM",
    status: "planned-probe",
    note: "Hosted provider-layer candidate. Self-hosted NIM is tabled."
  },
  {
    route: "local open-weight serving",
    status: "tabled",
    note: "Requires separate GPU/local-serving infrastructure plan."
  }
];

export default function ReadinessPage() {
  return (
    <AppShell
      title="Route Readiness"
      description="Provider, router, Claude Code, Harbor, and runner readiness gates before smoke/full-sweep work."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Readiness gates</h2>
          <p>Each new provider layer moves through these gates before smoke planning.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Area</th>
                <th>Required for</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {readinessRows.map((row) => (
                <tr key={row.area}>
                  <td>{row.area}</td>
                  <td>{row.requiredFor}</td>
                  <td>{row.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Special route status</h2>
          <p>Current non-standard model/provider findings that affect planning.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Route/provider</th>
                <th>Status</th>
                <th>Planning note</th>
              </tr>
            </thead>
            <tbody>
              {statusRows.map((row) => (
                <tr key={row.route}>
                  <td className="mono">{row.route}</td>
                  <td><span className="status">{row.status}</span></td>
                  <td>{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
