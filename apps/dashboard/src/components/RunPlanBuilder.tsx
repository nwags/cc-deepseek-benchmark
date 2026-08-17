"use client";

import { useMemo, useState } from "react";
import type { ArmOption, TaskSetOption } from "../lib/planner-types";
import {
  DEFAULT_RUNNER_SLOTS,
  classifyProviderFamily,
  validateRunPlan,
  type RunMode,
  type Severity,
} from "../lib/run-plan-validation";

const RUNNER_SLOTS = DEFAULT_RUNNER_SLOTS;

const DEFAULT_SELECTED_ARMS = [
  "router-gpt-5.5",
  "router-gemini-3.1-pro",
  "router-gemini-flash",
];

function severityLabel(severity: Severity): string {
  if (severity === "blocker") return "BLOCK";
  if (severity === "warning") return "WARN";
  return "OK";
}

function shellValue(value: string): string {
  return value.replace(/'/g, "'\"'\"'");
}

function buildDispatchCommand(options: {
  armId: string;
  runMode: RunMode;
  dryRun: boolean;
  confirmPaidRun: boolean;
  nAttempts: string;
  nConcurrent: string;
  taskFile: string;
  adHocLabel: string;
}): string {
  const confirmPaidRun = options.dryRun ? false : options.confirmPaidRun;

  return [
    "gh workflow run phase3-arm-dispatch.yml \\",
    "  --ref main \\",
    `  -f arm_id='${shellValue(options.armId)}' \\`,
    `  -f mode=${options.runMode} \\`,
    `  -f dry_run=${options.dryRun ? "true" : "false"} \\`,
    `  -f confirm_paid_run=${confirmPaidRun ? "true" : "false"} \\`,
    `  -f n_attempts='${shellValue(options.nAttempts)}' \\`,
    `  -f n_concurrent='${shellValue(options.nConcurrent)}' \\`,
    "  -f task_id= \\",
    `  -f task_file='${shellValue(options.taskFile)}' \\`,
    `  -f ad_hoc_label='${shellValue(options.adHocLabel)}'`,
  ].join("\n");
}

export function RunPlanBuilder({
  arms,
  taskSets,
}: {
  arms: ArmOption[];
  taskSets: TaskSetOption[];
}) {
  const defaultSelected = DEFAULT_SELECTED_ARMS.filter((armId) =>
    arms.some((arm) => arm.arm_id === armId),
  );

  const [selectedArmIds, setSelectedArmIds] = useState<string[]>(defaultSelected);
  const [runMode, setRunMode] = useState<RunMode>("smoke");
  const [dryRun, setDryRun] = useState(true);
  const [confirmPaidRun, setConfirmPaidRun] = useState(false);
  const [nAttempts, setNAttempts] = useState("1");
  const [nConcurrent, setNConcurrent] = useState("1");
  const [taskFile, setTaskFile] = useState("");
  const [adHocLabel, setAdHocLabel] = useState("");
  const [filter, setFilter] = useState("");

  const armMap = useMemo(() => new Map(arms.map((arm) => [arm.arm_id, arm])), [arms]);

  const selectedArms = selectedArmIds
    .map((armId) => armMap.get(armId))
    .filter((arm): arm is ArmOption => Boolean(arm));

  const filteredArms = useMemo(() => {
    const normalized = filter.trim().toLowerCase();

    if (!normalized) return arms;

    return arms.filter((arm) =>
      [arm.arm_id, arm.provider, arm.model, arm.backend_model, arm.job_dir_name]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(normalized),
    );
  }, [arms, filter]);

  const plan = useMemo(
    () =>
      validateRunPlan({
        selectedArms,
        runMode,
        dryRun,
        confirmPaidRun,
        nConcurrent,
      }),
    [confirmPaidRun, dryRun, nConcurrent, runMode, selectedArms],
  );

  const dispatchCommands = selectedArms
    .map((arm) =>
      buildDispatchCommand({
        armId: arm.arm_id,
        runMode,
        dryRun,
        confirmPaidRun,
        nAttempts,
        nConcurrent,
        taskFile,
        adHocLabel,
      }),
    )
    .join("\n\n");

  function toggleArm(armId: string) {
    setSelectedArmIds((current) =>
      current.includes(armId)
        ? current.filter((value) => value !== armId)
        : [...current, armId],
    );
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Run plan builder</h2>
          <p>
            Select arms from the registry, review checked-in runner/provider planning rules, then copy reviewed
            dispatch commands. The dashboard still does not launch runs.
          </p>
        </div>
        <a href="/planner?mode=arm">Draft new arm configuration</a>
      </div>

      <div className="run-plan-layout">
        <div className="run-plan-controls">
          <label>
            <strong>Run mode</strong>
            <select value={runMode} onChange={(event) => setRunMode(event.target.value as RunMode)}>
              <option value="canary">canary</option>
              <option value="smoke">smoke</option>
              <option value="full">full sweep</option>
            </select>
          </label>

          <label>
            <strong>Task file override</strong>
            <select value={taskFile} onChange={(event) => setTaskFile(event.target.value)}>
              <option value="">phase default</option>
              {taskSets.map((taskSet) => (
                <option key={taskSet.id} value={`configs/tasks/${taskSet.file_name}`}>
                  {taskSet.file_name} ({taskSet.task_count})
                </option>
              ))}
            </select>
          </label>

          <label>
            <strong>n_attempts</strong>
            <input value={nAttempts} onChange={(event) => setNAttempts(event.target.value)} />
          </label>

          <label>
            <strong>Harbor n_concurrent per arm job</strong>
            <input value={nConcurrent} onChange={(event) => setNConcurrent(event.target.value)} />
          </label>

          <label>
            <strong>ad_hoc_label</strong>
            <input value={adHocLabel} onChange={(event) => setAdHocLabel(event.target.value)} />
          </label>

          <label className="checkbox-row">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            <span>dry_run=true</span>
          </label>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={confirmPaidRun}
              disabled={dryRun}
              onChange={(event) => setConfirmPaidRun(event.target.checked)}
            />
            <span>confirm_paid_run=true</span>
          </label>
        </div>

        <div className="arm-picker">
          <div className="arm-picker-heading">
            <label>
              <strong>Filter arms</strong>
              <input value={filter} onChange={(event) => setFilter(event.target.value)} />
            </label>
            <button type="button" onClick={() => setSelectedArmIds([])}>
              Clear selection
            </button>
          </div>

          <div className="arm-option-list">
            {filteredArms.map((arm) => (
              <label className="arm-option" key={arm.arm_id}>
                <input
                  type="checkbox"
                  checked={selectedArmIds.includes(arm.arm_id)}
                  onChange={() => toggleArm(arm.arm_id)}
                />
                <span>
                  <strong className="mono">{arm.arm_id}</strong>
                  <small>
                    {classifyProviderFamily(arm)} · {arm.provider ?? "unknown"} ·{" "}
                    {arm.backend_model ?? arm.model ?? "unknown model"}
                  </small>
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="metric-grid compact-metric-grid">
        <div className="metric-card">
          <div className="metric-label">Plan status</div>
          <div className="metric-value">{plan.status}</div>
          <div className="metric-detail">blocked / review / clear</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Planner slots</div>
          <div className="metric-value">
            {selectedArms.length} / {RUNNER_SLOTS}
          </div>
          <div className="metric-detail">configured planner slot assumption</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Max task concurrency</div>
          <div className="metric-value">{plan.effectiveTaskParallelism}</div>
          <div className="metric-detail">selected arms × n_concurrent</div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Finding</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {plan.findings.map((finding) => (
              <tr key={`${finding.severity}-${finding.title}`}>
                <td className="mono">{severityLabel(finding.severity)}</td>
                <td>{finding.title}</td>
                <td>{finding.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Selected arm</th>
              <th>Provider family</th>
              <th>Provider</th>
              <th>Backend model</th>
            </tr>
          </thead>
          <tbody>
            {selectedArms.map((arm) => (
              <tr key={arm.arm_id}>
                <td className="mono">{arm.arm_id}</td>
                <td>{classifyProviderFamily(arm)}</td>
                <td>{arm.provider ?? "—"}</td>
                <td className="mono">{arm.backend_model ?? arm.model ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="generated-command">
        <div className="panel-heading flush-heading">
          <h3>Generated dispatch commands</h3>
          <p>Review before copying. No dashboard dispatch happens here.</p>
        </div>
        <pre>{dispatchCommands || "# Select at least one arm to generate commands."}</pre>
      </div>
    </section>
  );
}
