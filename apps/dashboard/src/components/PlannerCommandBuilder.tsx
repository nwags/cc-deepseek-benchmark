"use client";

import { useMemo, useState } from "react";

export type ArmOption = {
  arm_id: string;
  file_name: string;
  provider: string | null;
  model: string | null;
  backend_model: string | null;
  job_dir_name: string | null;
};

export type TaskSetOption = {
  id: string;
  file_name: string;
  task_count: number;
  sample_tasks: string[];
};

type RunType = "canary" | "smoke" | "full-sweep" | "ad-hoc";
type WorkflowMode = "canary" | "smoke" | "full";

const runTypes: Array<{
  value: RunType;
  label: string;
  purpose: string;
}> = [
  {
    value: "canary",
    label: "canary",
    purpose: "One known canary task; infrastructure/model-route gate."
  },
  {
    value: "smoke",
    label: "smoke",
    purpose: "Small multi-task gate; next benchmark milestone."
  },
  {
    value: "full-sweep",
    label: "full-sweep",
    purpose: "Large multi-task benchmark battery; final Phase 3 comparison after approval."
  },
  {
    value: "ad-hoc",
    label: "ad-hoc",
    purpose: "One-off diagnostic run; marked non-scored unless explicitly promoted."
  }
];

function shellQuote(value: string): string {
  if (value === "") {
    return "''";
  }

  if (/^[A-Za-z0-9_./:=+-]+$/.test(value)) {
    return value;
  }

  return `'${value.replaceAll("'", "'\"'\"'")}'`;
}

function workflowField(key: string, value: string): string {
  return shellQuote(`${key}=${value}`);
}

function workflowModeFor(runType: RunType, adHocWorkflowMode: WorkflowMode): WorkflowMode {
  if (runType === "full-sweep") {
    return "full";
  }

  if (runType === "ad-hoc") {
    return adHocWorkflowMode;
  }

  return runType;
}

function defaultTaskSetFor(runType: RunType, taskSets: TaskSetOption[]): string {
  const candidates: Record<RunType, string[]> = {
    canary: ["phase2-canary.txt", "tasks.txt"],
    smoke: ["phase2-smoke.txt", "terminal-bench-20.txt", "tasks.txt"],
    "full-sweep": ["tasks.full.txt", "terminal_bench_2_all_tasks.txt", "terminal-bench-20.txt"],
    "ad-hoc": ["phase2-canary.txt", "phase2-smoke.txt", "tasks.txt"]
  };

  for (const fileName of candidates[runType]) {
    const match = taskSets.find((taskSet) => taskSet.file_name === fileName);
    if (match) {
      return match.id;
    }
  }

  return taskSets[0]?.id ?? "";
}

export function PlannerCommandBuilder({
  arms,
  taskSets
}: {
  arms: ArmOption[];
  taskSets: TaskSetOption[];
}) {
  const [armId, setArmId] = useState(arms[0]?.arm_id ?? "");
  const [runType, setRunType] = useState<RunType>("canary");
  const [taskSetId, setTaskSetId] = useState(defaultTaskSetFor("canary", taskSets));
  const [adHocWorkflowMode, setAdHocWorkflowMode] = useState<WorkflowMode>("canary");
  const [dryRun, setDryRun] = useState(true);
  const [confirmPaidRun, setConfirmPaidRun] = useState(false);
  const [nAttempts, setNAttempts] = useState("");
  const [nConcurrent, setNConcurrent] = useState("");
  const [taskId, setTaskId] = useState("");
  const [taskFile, setTaskFile] = useState("");
  const [adHocLabel, setAdHocLabel] = useState("manual-diagnostic");

  const selectedArm = arms.find((arm) => arm.arm_id === armId) ?? arms[0] ?? null;
  const selectedRunType = runTypes.find((item) => item.value === runType) ?? runTypes[0];
  const selectedTaskSet = taskSets.find((taskSet) => taskSet.id === taskSetId) ?? taskSets[0] ?? null;
  const workflowMode = workflowModeFor(runType, adHocWorkflowMode);
  const isAdHoc = runType === "ad-hoc";
  const hasAmbiguousAdHocTaskSource = taskId.trim() !== "" && taskFile.trim() !== "";

  const command = useMemo(() => {
    const emittedTaskId = isAdHoc ? taskId.trim() : "";
    const emittedTaskFile = isAdHoc ? taskFile.trim() : "";
    const emittedAdHocLabel = isAdHoc ? adHocLabel.trim() : "";

    const lines = [
      "# Review this command before running. It does not launch from the dashboard.",
      `# Planner run type: ${runType}`,
      `# Workflow mode: ${workflowMode}`,
      selectedTaskSet
        ? `# Selected task set for review: ${selectedTaskSet.file_name} (${selectedTaskSet.task_count} tasks)`
        : "# Selected task set for review: none",
      ...(isAdHoc
        ? [
            "# Ad-hoc note: task_id/task_file/ad_hoc_label are now supported by the Phase 3 dispatch workflow.",
            "# Ad-hoc results are non-scored unless explicitly promoted in a reviewed follow-up."
          ]
        : []),
      "gh workflow run phase3-arm-dispatch.yml \\",
      "  --ref main \\",
      `  -f ${workflowField("arm_id", selectedArm?.arm_id ?? "")} \\`,
      `  -f ${workflowField("mode", workflowMode)} \\`,
      `  -f ${workflowField("dry_run", dryRun ? "true" : "false")} \\`,
      `  -f ${workflowField("confirm_paid_run", !dryRun && confirmPaidRun ? "true" : "false")} \\`,
      `  -f ${workflowField("n_attempts", nAttempts.trim())} \\`,
      `  -f ${workflowField("n_concurrent", nConcurrent.trim())} \\`,
      `  -f ${workflowField("task_id", emittedTaskId)} \\`,
      `  -f ${workflowField("task_file", emittedTaskFile)} \\`,
      `  -f ${workflowField("ad_hoc_label", emittedAdHocLabel)}`
    ];

    return lines.join("\n");
  }, [
    adHocLabel,
    confirmPaidRun,
    dryRun,
    isAdHoc,
    nAttempts,
    nConcurrent,
    runType,
    selectedArm?.arm_id,
    selectedTaskSet,
    taskFile,
    taskId,
    workflowMode
  ]);

  function updateRunType(nextRunType: RunType) {
    setRunType(nextRunType);
    setTaskSetId(defaultTaskSetFor(nextRunType, taskSets));
  }

  return (
    <>
      <section className="panel">
        <div className="panel-heading">
          <h2>Planner controls</h2>
          <p>Select an arm and run type to generate a reviewable dispatch command.</p>
        </div>

        <div className="planner-grid">
          <label className="form-field">
            <span>Arm</span>
            <select value={armId} onChange={(event) => setArmId(event.target.value)}>
              {arms.map((arm) => (
                <option value={arm.arm_id} key={arm.arm_id}>
                  {arm.arm_id}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>Run type</span>
            <select
              value={runType}
              onChange={(event) => updateRunType(event.target.value as RunType)}
            >
              {runTypes.map((item) => (
                <option value={item.value} key={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          {isAdHoc ? (
            <label className="form-field">
              <span>Ad-hoc workflow mode</span>
              <select
                value={adHocWorkflowMode}
                onChange={(event) => setAdHocWorkflowMode(event.target.value as WorkflowMode)}
              >
                <option value="canary">canary</option>
                <option value="smoke">smoke</option>
                <option value="full">full</option>
              </select>
            </label>
          ) : null}

          <label className="form-field">
            <span>Task set for review</span>
            <select value={taskSetId} onChange={(event) => setTaskSetId(event.target.value)}>
              {taskSets.map((taskSet) => (
                <option value={taskSet.id} key={taskSet.id}>
                  {taskSet.file_name} ({taskSet.task_count})
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>n_attempts override</span>
            <input
              value={nAttempts}
              onChange={(event) => setNAttempts(event.target.value)}
              placeholder="blank = phase default"
            />
          </label>

          <label className="form-field">
            <span>n_concurrent override</span>
            <input
              value={nConcurrent}
              onChange={(event) => setNConcurrent(event.target.value)}
              placeholder="blank = safe default"
            />
          </label>

          {isAdHoc ? (
            <>
              <label className="form-field">
                <span>task_id</span>
                <input
                  value={taskId}
                  onChange={(event) => setTaskId(event.target.value)}
                  placeholder="modernize-scientific-stack"
                />
              </label>

              <label className="form-field">
                <span>task_file</span>
                <input
                  value={taskFile}
                  onChange={(event) => setTaskFile(event.target.value)}
                  placeholder="configs/tasks/phase2-canary.txt"
                />
              </label>

              <label className="form-field">
                <span>ad_hoc_label</span>
                <input
                  value={adHocLabel}
                  onChange={(event) => setAdHocLabel(event.target.value)}
                  placeholder="short diagnostic label"
                />
              </label>
            </>
          ) : null}

          <label className="check-field">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(event) => {
                setDryRun(event.target.checked);
                if (event.target.checked) {
                  setConfirmPaidRun(false);
                }
              }}
            />
            <span>dry_run=true</span>
          </label>

          <label className="check-field">
            <input
              type="checkbox"
              checked={confirmPaidRun}
              disabled={dryRun}
              onChange={(event) => setConfirmPaidRun(event.target.checked)}
            />
            <span>confirm_paid_run=true</span>
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Generated dispatch command</h2>
          <p>Copy only after review. The dashboard does not launch this command.</p>
        </div>

        <div className="placeholder-body">
          <pre className="mono command-box">{command}</pre>
          {!dryRun && !confirmPaidRun ? (
            <p className="warning-text">
              Paid run guard: confirm_paid_run is currently false, so the workflow should refuse a paid run.
            </p>
          ) : null}
          {hasAmbiguousAdHocTaskSource ? (
            <p className="warning-text">
              Ad-hoc task source guard: task_id and task_file are mutually exclusive. Clear one before running.
            </p>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Selected route metadata</h2>
          <p>Metadata parsed from configs/arms.</p>
        </div>
        <div className="detail-grid">
          <div><span>Arm</span><strong className="mono">{selectedArm?.arm_id ?? "—"}</strong></div>
          <div><span>Provider</span><strong>{selectedArm?.provider ?? "—"}</strong></div>
          <div><span>Model</span><strong className="mono">{selectedArm?.model ?? "—"}</strong></div>
          <div><span>Backend model</span><strong className="mono">{selectedArm?.backend_model ?? "—"}</strong></div>
          <div><span>Job dir</span><strong className="mono">{selectedArm?.job_dir_name ?? "—"}</strong></div>
          <div><span>Purpose</span><strong>{selectedRunType.purpose}</strong></div>
        </div>
      </section>
    </>
  );
}
