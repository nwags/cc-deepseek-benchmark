import { AppShell } from "../../components/AppShell";
import { PlaceholderPanel } from "../../components/PlaceholderPanel";

export default function ScaffoldPage() {
  return (
    <AppShell
      title="Arm Scaffold"
      description="Future helper for proposing new model arms without directly mutating benchmark configuration."
    >
      <PlaceholderPanel title="Read-only arm scaffold helper">
        <p>
          Next pass: render provider/model input fields and generate reviewable YAML
          snippets for configs/arms. Writes should still go through Git review.
        </p>
      </PlaceholderPanel>
    </AppShell>
  );
}
