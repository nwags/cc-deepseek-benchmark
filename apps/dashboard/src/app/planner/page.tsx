import fs from "node:fs";
import path from "node:path";
import { ArmConfigDraftBuilder } from "../../components/ArmConfigDraftBuilder";
import { AppShell } from "../../components/AppShell";
import { PlannerModeSelector } from "../../components/PlannerModeSelector";
import { RunPlanBuilder } from "../../components/RunPlanBuilder";
import { getCurrentEvidencePromotionGates } from "../../lib/dashboard-data";
import { selectPlannerMode } from "../../lib/planner-modes";
import type {
  ArmOption,
  PromotionGateLoadStatus,
  PromotionGateRow,
  TaskSetOption,
} from "../../lib/planner-types";

export const dynamic = "force-dynamic";

function repoRoot(): string {
  return path.resolve(process.cwd(), "../..");
}

function readYamlScalar(text: string, key: string): string | null {
  const pattern = new RegExp(`^${key}:\\s*["']?([^"'#\\n]+)["']?\\s*(?:#.*)?$`, "m");
  const match = text.match(pattern);
  return match?.[1]?.trim() ?? null;
}

function readArms(): ArmOption[] {
  const armsDir = path.join(repoRoot(), "configs", "arms");

  if (!fs.existsSync(armsDir)) {
    return [];
  }

  return fs
    .readdirSync(armsDir)
    .filter((fileName) => fileName.endsWith(".yaml"))
    .map((fileName) => {
      const text = fs.readFileSync(path.join(armsDir, fileName), "utf8");
      return {
        arm_id: readYamlScalar(text, "arm_id") ?? fileName.replace(/\.yaml$/, ""),
        file_name: fileName,
        provider: readYamlScalar(text, "provider"),
        model: readYamlScalar(text, "model"),
        backend_model: readYamlScalar(text, "backend_model"),
        job_dir_name: readYamlScalar(text, "job_dir_name")
      };
    })
    .sort((left, right) => left.arm_id.localeCompare(right.arm_id));
}

function readTaskSets(): TaskSetOption[] {
  const tasksDir = path.join(repoRoot(), "configs", "tasks");

  if (!fs.existsSync(tasksDir)) {
    return [];
  }

  return fs
    .readdirSync(tasksDir)
    .filter((fileName) => fileName.endsWith(".txt"))
    .map((fileName) => {
      const tasks = fs
        .readFileSync(path.join(tasksDir, fileName), "utf8")
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line && !line.startsWith("#"));

      return {
        id: fileName,
        file_name: fileName,
        task_count: tasks.length,
        sample_tasks: tasks.slice(0, 5)
      };
    })
    .sort((left, right) => left.file_name.localeCompare(right.file_name));
}

type PlannerPageProps = {
  searchParams?: Promise<{ mode?: string | string[] }>;
};

export default async function PlannerPage({ searchParams }: PlannerPageProps) {
  const query = await (searchParams ?? Promise.resolve<{ mode?: string | string[] }>({}));
  const selection = selectPlannerMode(query.mode);
  const arms = readArms();
  const taskSets = selection.mode === "run" ? readTaskSets() : [];

  let promotionGateLoadStatus: PromotionGateLoadStatus = "available";
  let promotionGates: PromotionGateRow[] = [];

  if (selection.mode === "run") {
    try {
      promotionGates = await getCurrentEvidencePromotionGates();
    } catch {
      promotionGateLoadStatus = "unavailable";
    }
  }

  return (
    <AppShell
      title="Planner"
      description="One read-only surface for reviewing benchmark run plans and drafting future arm configuration YAML."
    >
      {selection.warningMessage ? (
        <p className="warning-text" role="alert">
          <strong>Planner mode warning:</strong> {selection.warningMessage}
        </p>
      ) : null}
      <PlannerModeSelector selectedMode={selection.mode} />

      {selection.mode === "run" ? (
        <>
          <section className="quality-context-panel">
            <h2>Checked-in planning assumptions</h2>
            <p>
              Runner-slot, per-job concurrency, and provider-family gates below are repository planning rules.
              They are not live runner-capacity, provider-availability, quota, or readiness observations.
              Review current operational evidence separately before executing any copied command.
            </p>
          </section>

          <RunPlanBuilder
            arms={arms}
            taskSets={taskSets}
            promotionGateLoadStatus={promotionGateLoadStatus}
            promotionGates={promotionGates}
          />

          <section className="panel">
            <div className="panel-heading">
              <h2>Available task sets</h2>
              <p>Parsed from configs/tasks for planning visibility.</p>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Task file</th>
                    <th>Tasks</th>
                    <th>Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {taskSets.map((taskSet) => (
                    <tr key={taskSet.id}>
                      <td className="mono">{taskSet.file_name}</td>
                      <td>{taskSet.task_count}</td>
                      <td className="mono">{taskSet.sample_tasks.join(", ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <h2>Available arms</h2>
              <p>Parsed from configs/arms. Generated commands use these arm IDs.</p>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Arm</th>
                    <th>Provider</th>
                    <th>Model</th>
                    <th>Backend model</th>
                  </tr>
                </thead>
                <tbody>
                  {arms.map((arm) => (
                    <tr key={arm.arm_id}>
                      <td className="mono">{arm.arm_id}</td>
                      <td>{arm.provider ?? "—"}</td>
                      <td className="mono">{arm.model ?? "—"}</td>
                      <td className="mono">{arm.backend_model ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : (
        <ArmConfigDraftBuilder existingArmIds={arms.map((arm) => arm.arm_id)} />
      )}
    </AppShell>
  );
}
