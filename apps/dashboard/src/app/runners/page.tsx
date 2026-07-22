import { AppShell } from "../../components/AppShell";
import { PlaceholderPanel } from "../../components/PlaceholderPanel";

export default function RunnersPage() {
  return (
    <AppShell
      title="Runner Fleet"
      description="Future view for OVH/GitHub self-hosted runner status, capacity, and queued benchmark jobs."
    >
      <PlaceholderPanel title="Runner fleet status">
        <p>
          Current state: one OVH x86 self-hosted runner is active. Next pass can add
          a static runner registry and later GitHub workflow status integration.
        </p>
      </PlaceholderPanel>
    </AppShell>
  );
}
