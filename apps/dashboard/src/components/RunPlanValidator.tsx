"use client";

import { useMemo, useState } from "react";
import type { ArmOption } from "./PlannerCommandBuilder";

type RunPlanMode = "canary" | "smoke" | "full-sweep";
type Severity = "ok" | "warning" | "blocker";

type Finding = {
  severity: Severity;
  title: string;
  detail: string;
};

const RUNNER_SLOTS = 3;

const DEFAULT_PREFERRED_WAVE = [
  "router-gpt-5.5",
  "router-gemini-3.1-pro",
  "router-gemini-flash",
];

function parseArmIds(text: string): string[] {
  return text
    .split(/[\s,]+/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function classifyProviderFamily(arm: ArmOption | null, armId: string): string {
  const haystack = [
    armId,
    arm?.provider,
    arm?.model,
    arm?.backend_model,
    arm?.job_dir_name,
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

function defaultArmText(arms: ArmOption[]): string {
  const available = new Set(arms.map((arm) => arm.arm_id));
  const preferred = DEFAULT_PREFERRED_WAVE.filter((armId) => available.has(armId));

  if (preferred.length > 0) {
    return preferred.join("\n");
  }

  return arms.slice(0, 3).map((arm) => arm.arm_id).join("\n");
}

export function RunPlanValidator({ arms }: { arms: ArmOption[] }) {
  const [armText, setArmText] = useState(defaultArmText(arms));
  const [runMode, setRunMode] = useState<RunPlanMode>("smoke");
  const [nConcurrent, setNConcurrent] = useState("1");

  const armMap = useMemo(() => new Map(arms.map((arm) => [arm.arm_id, arm])), [arms]);

  const plan = useMemo(() => {
    const armIds = parseArmIds(armText);
    const parsedNConcurrent = Number.parseInt(nConcurrent, 10);
    const harborConcurrency =
      Number.isFinite(parsedNConcurrent) && parsedNConcurrent > 0 ? parsedNConcurrent : 1;

    const rows = armIds.map((armId) => {
      const arm = armMap.get(armId) ?? null;
      const providerFamily = classifyProviderFamily(arm, armId);
      return { armId, arm, providerFamily };
    });

    const findings: Finding[] = [];

    const missingArmIds = rows.filter((row) => row.arm === null).map((row) => row.armId);
    if (missingArmIds.length > 0) {
      findings.push({
        severity: "blocker",
        title: "Unknown arm IDs",
        detail: `These arms are not present in configs/arms: ${missingArmIds.join(", ")}.`,
      });
    }

    const duplicateArmIds = armIds.filter((armId, index) => armIds.indexOf(armId) !== index);
    if (duplicateArmIds.length > 0) {
      findings.push({
        severity: "warning",
        title: "Duplicate arms",
        detail: `The plan repeats: ${Array.from(new Set(duplicateArmIds)).join(", ")}.`,
      });
    }

    if (armIds.length === 0) {
      findings.push({
        severity: "blocker",
        title: "No arms selected",
        detail: "Add at least one arm ID to validate a run plan.",
      });
    }

    if (armIds.length > RUNNER_SLOTS) {
      findings.push({
        severity: "blocker",
        title: "Runner-slot capacity exceeded",
        detail: `${armIds.length} workflow jobs requested across ${RUNNER_SLOTS} current runner slots. Split the wave or add runners.`,
      });
    } else {
      findings.push({
        severity: "ok",
        title: "Runner-slot capacity",
        detail: `${armIds.length} workflow jobs requested across ${RUNNER_SLOTS} current runner slots.`,
      });
    }

    if (harborConcurrency > 1) {
      findings.push({
        severity: "warning",
        title: "Harbor concurrency above current safe setting",
        detail: `n_concurrent=${harborConcurrency}; current Phase 3 safe setting is n_concurrent=1 per runner job.`,
      });
    }

    const providerCounts = rows.reduce<Record<string, number>>((accumulator, row) => {
      accumulator[row.providerFamily] = (accumulator[row.providerFamily] ?? 0) + 1;
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

    const qwenRows = rows.filter((row) => row.providerFamily === "qwen");
    if (qwenRows.length > 0 && runMode === "full-sweep") {
      findings.push({
        severity: "blocker",
        title: "Qwen full-sweep blocked",
        detail:
          "Qwen full-sweep dispatch is blocked until Alibaba identity verification and usage-metering reconciliation are complete.",
      });
    } else if (qwenRows.length > 0) {
      findings.push({
        severity: "warning",
        title: "Qwen billing-verification risk",
        detail:
          "Qwen is allowed only for reviewed diagnostics/smoke while Alibaba verification and usage-metering reconciliation remain open.",
      });
    }

    const fableRows = rows.filter((row) => row.providerFamily === "fable");
    if (fableRows.length > 0) {
      findings.push({
        severity: "blocker",
        title: "Fable availability blocked",
        detail: "Fable remains blocked until provider availability/access is restored.",
      });
    }

    const hasBlocker = findings.some((finding) => finding.severity === "blocker");
    const hasWarning = findings.some((finding) => finding.severity === "warning");

    return {
      rows,
      findings,
      harborConcurrency,
      effectiveTaskParallelism: armIds.length * harborConcurrency,
      status: hasBlocker ? "blocked" : hasWarning ? "review" : "clear",
    };
  }, [armMap, armText, nConcurrent, runMode]);

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Run-plan validator</h2>
        <p>
          Stage B preview: validate runner slots and provider-family limits before any dashboard
          dispatch button exists.
        </p>
      </div>

      <div className="placeholder-body">
        <label>
          <strong>Run mode</strong>
          <select value={runMode} onChange={(event) => setRunMode(event.target.value as RunPlanMode)}>
            <option value="canary">canary</option>
            <option value="smoke">smoke</option>
            <option value="full-sweep">full-sweep</option>
          </select>
        </label>

        <label>
          <strong>Harbor n_concurrent per runner job</strong>
          <input
            value={nConcurrent}
            onChange={(event) => setNConcurrent(event.target.value)}
            inputMode="numeric"
            placeholder="1"
          />
        </label>

        <label>
          <strong>Arm IDs, one per line or space-separated</strong>
          <textarea
            value={armText}
            onChange={(event) => setArmText(event.target.value)}
            rows={6}
            spellCheck={false}
          />
        </label>

        <div className="metric-grid compact-metric-grid">
          <div className="metric-card">
            <div className="metric-label">Plan status</div>
            <div className="metric-value">{plan.status}</div>
            <div className="metric-detail">blocked / review / clear</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Runner slots</div>
            <div className="metric-value">
              {plan.rows.length} / {RUNNER_SLOTS}
            </div>
            <div className="metric-detail">workflow jobs requested</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Task parallelism</div>
            <div className="metric-value">{plan.effectiveTaskParallelism}</div>
            <div className="metric-detail">jobs × n_concurrent</div>
          </div>
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
              <th>Arm</th>
              <th>Provider family</th>
              <th>Provider</th>
              <th>Backend model</th>
              <th>Arm config</th>
            </tr>
          </thead>
          <tbody>
            {plan.rows.map((row) => (
              <tr key={row.armId}>
                <td className="mono">{row.armId}</td>
                <td>{row.providerFamily}</td>
                <td>{row.arm?.provider ?? "—"}</td>
                <td className="mono">{row.arm?.backend_model ?? row.arm?.model ?? "—"}</td>
                <td className="mono">{row.arm?.file_name ?? "missing"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
