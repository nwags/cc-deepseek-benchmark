"use client";

import { useMemo, useState } from "react";
import type { ArmOption, TaskSetOption } from "./PlannerCommandBuilder";

type RunMode = "canary" | "smoke" | "full";
type Severity = "ok" | "warning" | "blocker";

type Finding = {
  severity: Severity;
  title: string;
  detail: string;
};

const RUNNER_SLOTS = 3;

const DEFAULT_SELECTED_ARMS = [
  "router-gpt-5.5",
  "router-gemini-3.1-pro",
  "router-gemini-flash",
];

function classifyProviderFamily(arm: ArmOption): string {
  const haystack = [
    arm.arm_id,
    arm.provider,
    arm.model,
    arm.backend_model,
    arm.job_dir_name,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (haystack.includes("gemini") || haystack.includes("google")) return "gemini";
  if (haystack.includes("qwen") || haystack.includes("dashscope") || haystack.includes("alibaba")) return "qwen";
  if (haystack.includes("fable")) return "fable";
  if (haystack.includes("anthropic") || haystack.includes("claude")) return "anthropic";
  if (haystack.includes("deepseek")) return "deepseek";
  if (haystack.includes("gpt") || haystack.includes("openai")) return "openai";
  if (haystack.includes("grok") || haystack.includes("xai")) return "xai";
  if (haystack.includes("kimi") || haystack.includes("moonshot")) return "moonshot";
  if (haystack.includes("glm") || haystack.includes("zai")) return "zai";

  return "unknown";
}

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

  const plan = useMemo(() => {
    const parsedNConcurrent = Number.parseInt(nConcurrent, 10);
    const harborConcurrency =
      Number.isFinite(parsedNConcurrent) && parsedNConcurrent > 0 ? parsedNConcurrent : 1;

    const findings: Finding[] = [];

    if (selectedArms.length === 0) {
      findings.push({
        severity: "blocker",
        title: "No arms selected",
        detail: "Select at least one arm before copying dispatch commands.",
      });
    }

    if (selectedArms.length > RUNNER_SLOTS) {
      findings.push({
        severity: "blocker",
        title: "Runner-slot capacity exceeded",
        detail: `${selectedArms.length} workflow jobs requested across ${RUNNER_SLOTS} current runner slots. Split the wave or add runners.`,
      });
    } else {
      findings.push({
        severity: "ok",
        title: "Runner-slot capacity",
        detail: `${selectedArms.length} workflow jobs requested across ${RUNNER_SLOTS} current runner slots.`,
      });
    }

    if (harborConcurrency > 1) {
      findings.push({
        severity: "warning",
        title: "Harbor concurrency above current safe setting",
        detail: `n_concurrent=${harborConcurrency}; current Phase 3 safe setting is n_concurrent=1 per runner job.`,
      });
    }

    if (!dryRun && !confirmPaidRun) {
      findings.push({
        severity: "blocker",
        title: "Paid run is not confirmed",
        detail: "Paid dispatch commands require confirm_paid_run=true.",
      });
    }

    const providerCounts = selectedArms.reduce<Record<string, number>>((accumulator, arm) => {
      const providerFamily = classifyProviderFamily(arm);
      accumulator[providerFamily] = (accumulator[providerFamily] ?? 0) + 1;
      return accumulator;
    }, {});

    if ((providerCounts.gemini ?? 0) > 1) {
      findings.push({
        severity: "blocker",
        title: "Gemini provider-family concurrency exceeded",
        detail:
          "Gemini is capped at 1 concurrent arm until quota/rate-limit behavior is verified or raised.",
      });
    } else if ((providerCounts.gemini ?? 0) === 1) {
      findings.push({
        severity: "ok",
        title: "Gemini provider-family concurrency",
        detail: "One Gemini-family arm selected.",
      });
    }

    const hasQwen = selectedArms.some((arm) => classifyProviderFamily(arm) === "qwen");
    if (hasQwen && runMode === "full") {
      findings.push({
        severity: "blocker",
        title: "Qwen full sweep blocked",
        detail:
          "Qwen full-sweep dispatch is blocked until Alibaba identity verification and usage-metering reconciliation are complete.",
      });
    } else if (hasQwen) {
      findings.push({
        severity: "warning",
        title: "Qwen billing-verification risk",
        detail:
          "Qwen is allowed only for reviewed diagnostics/smoke while Alibaba verification and usage-metering reconciliation remain open.",
      });
    }

    const hasFable = selectedArms.some((arm) => classifyProviderFamily(arm) === "fable");
    if (hasFable) {
      findings.push({
        severity: "blocker",
        title: "Fable availability blocked",
        detail: "Fable remains blocked until provider availability/access is restored.",
      });
    }

    const hasBlocker = findings.some((finding) => finding.severity === "blocker");
    const hasWarning = findings.some((finding) => finding.severity === "warning");

    return {
      findings,
      harborConcurrency,
      effectiveTaskParallelism: selectedArms.length * harborConcurrency,
      status: hasBlocker ? "blocked" : hasWarning ? "review" : "clear",
    };
  }, [confirmPaidRun, dryRun, nConcurrent, runMode, selectedArms]);

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
            Select arms from the registry, validate runner/provider constraints, then copy reviewed
            dispatch commands. The dashboard still does not launch runs.
          </p>
        </div>
        <a href="/scaffold">Create new arm YAML</a>
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
            <strong>n_concurrent</strong>
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
          <div className="metric-label">Runner slots</div>
          <div className="metric-value">
            {selectedArms.length} / {RUNNER_SLOTS}
          </div>
          <div className="metric-detail">workflow jobs requested</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Task parallelism</div>
          <div className="metric-value">{plan.effectiveTaskParallelism}</div>
          <div className="metric-detail">jobs × n_concurrent</div>
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
