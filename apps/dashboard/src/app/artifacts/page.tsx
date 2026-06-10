import { AppShell } from "../../components/AppShell";
import { PlaceholderPanel } from "../../components/PlaceholderPanel";

export default function ArtifactsPage() {
  return (
    <AppShell
      title="Artifacts"
      description="Future artifact browser for R2-backed result files, logs, trajectories, rewards, and verifier output."
    >
      <PlaceholderPanel title="Artifact browser">
        <p>
          Next pass: add a server-side query over benchmark.v_run_artifact_summary and
          benchmark.benchmark_artifacts, then add signed R2 links only through server routes.
        </p>
      </PlaceholderPanel>
    </AppShell>
  );
}
