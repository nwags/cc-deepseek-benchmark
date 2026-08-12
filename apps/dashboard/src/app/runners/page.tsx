import Link from "next/link";
import { AppShell } from "../../components/AppShell";

export default function RunnersPage() {
  return (
    <AppShell
      title="Runner Fleet — deprecated operational page"
      description="Retained for old links; this page is not a live fleet-status source."
    >
      <section className="quality-context-panel">
        <strong>Deprecated destination retained for old links.</strong> This page is not a live fleet-status source
        and does not assert runner count, availability, capacity, or queue depth.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Use execution evidence instead</h2>
            <p>No redirect is performed because the available pages do not provide a complete fleet model.</p>
          </div>
        </div>
        <div className="runner-fleet-body">
          <p>
            <Link href="/runs/live">Live Runs</Link> shows execution-level runner names, active or stale execution state,
            and heartbeat timestamps associated with executions. It does not establish independent fleet availability or capacity.
          </p>
          <p>
            <Link href="/runs">Runs</Link> is the canonical index for completed benchmark evidence.
          </p>
        </div>
      </section>
    </AppShell>
  );
}
