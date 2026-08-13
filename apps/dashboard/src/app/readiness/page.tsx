import Link from "next/link";
import { AppShell } from "../../components/AppShell";

const historicalPlanningChecklist = [
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
  }
];

const LEGACY_SOURCE_DATE = "Legacy dashboard planning note · original event date not recorded";

const historicalRouteNotes = [
  {
    route: "router-anthropic-fable-5",
    note: "The legacy page recorded a successful rerun after a Docker/UFW firewall correction. The event date was not stored on this page.",
    sourceDate: LEGACY_SOURCE_DATE
  },
  {
    route: "claude-mythos-5",
    note: "The legacy page recorded a 404/not_found response for the account used at that time. The observation has not been revalidated.",
    sourceDate: LEGACY_SOURCE_DATE
  },
  {
    route: "opusplan",
    note: "The legacy page recorded that the alias was accepted during Phase 2, without evidence of a distinct plan/execute cycle.",
    sourceDate: LEGACY_SOURCE_DATE
  },
  {
    route: "hosted NVIDIA NIM",
    note: "The legacy page recorded removal from benchmark planning and cautioned against free-tier or account-circumvention approaches.",
    sourceDate: LEGACY_SOURCE_DATE
  },
  {
    route: "local open-weight serving",
    note: "The legacy page recorded this work as deferred pending separate local-serving infrastructure.",
    sourceDate: LEGACY_SOURCE_DATE
  }
];

export default function ReadinessPage() {
  return (
    <AppShell
      title="Route Readiness — historical planning snapshot"
      description="Retained historical planning material; this page is not live operational readiness or current provider/route status."
    >
      <section className="quality-context-panel">
        <p><strong>Historical planning snapshot — not live operational readiness.</strong></p>
        <p>Last reviewed for dashboard containment: 2026-08-05.</p>
        <p>No provider, LiteLLM, Claude Code, Harbor, or runner probes were run for this review. The underlying observations were not revalidated.</p>
        <p>Original event dates are not recorded by this page unless a row explicitly contains one.</p>
        <p>
          Use <Link href="/planner">Planner</Link> for current configuration-based planning,{" "}<Link href="/runs/live">Live Runs</Link> for observed live execution state, and{" "}<Link href="/runs">Runs</Link> for completed benchmark evidence.
        </p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Historical planning checklist</h2>
          <p>This process reference does not prove that any gate is currently satisfied.</p>
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
              {historicalPlanningChecklist.map((row) => (
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
          <h2>Historical route and provider notes</h2>
          <p>Legacy planning observations preserved without presenting them as current route or provider status.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Route/provider</th>
                <th>Historical note</th>
                <th>Source/date</th>
              </tr>
            </thead>
            <tbody>
              {historicalRouteNotes.map((row) => (
                <tr key={row.route}>
                  <td className="mono">{row.route}</td>
                  <td>{row.note}</td>
                  <td>{row.sourceDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
