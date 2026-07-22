"Shared run-plan validation logic for the benchmark dashboard.";

export type RunMode = "canary" | "smoke" | "full";
export type ProviderFamily =
  | "anthropic"
  | "deepseek"
  | "fable"
  | "gemini"
  | "moonshot"
  | "openai"
  | "qwen"
  | "unknown"
  | "xai"
  | "zai";

export type Severity = "ok" | "warning" | "blocker";

export type RunPlanArm = {
  arm_id: string;
  provider?: string | null;
  model?: string | null;
  backend_model?: string | null;
  job_dir_name?: string | null;
};

export type RunPlanFinding = {
  severity: Severity;
  title: string;
  detail: string;
};

export type RunPlanValidationInput = {
  selectedArms: RunPlanArm[];
  runMode: RunMode;
  dryRun: boolean;
  confirmPaidRun: boolean;
  nConcurrent: string | number;
  runnerSlots?: number;
};

export type RunPlanValidationResult = {
  findings: RunPlanFinding[];
  harborConcurrency: number;
  effectiveTaskParallelism: number;
  status: "blocked" | "review" | "clear";
  runnerSlots: number;
};

export const DEFAULT_RUNNER_SLOTS = 3;

export function classifyProviderFamily(arm: RunPlanArm): ProviderFamily {
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

export function parseHarborConcurrency(value: string | number): number {
  if (typeof value === "number") {
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 1;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export function validateRunPlan(input: RunPlanValidationInput): RunPlanValidationResult {
  const runnerSlots = input.runnerSlots ?? DEFAULT_RUNNER_SLOTS;
  const harborConcurrency = parseHarborConcurrency(input.nConcurrent);
  const findings: RunPlanFinding[] = [];

  if (input.selectedArms.length === 0) {
    findings.push({
      severity: "blocker",
      title: "No arms selected",
      detail: "Select at least one arm before copying dispatch commands.",
    });
  }

  if (input.selectedArms.length > runnerSlots) {
    findings.push({
      severity: "blocker",
      title: "Runner-slot capacity exceeded",
      detail: `${input.selectedArms.length} workflow jobs requested across ${runnerSlots} current runner slots. Split the wave or add runners.`,
    });
  } else {
    findings.push({
      severity: "ok",
      title: "Runner-slot capacity",
      detail: `${input.selectedArms.length} workflow jobs requested across ${runnerSlots} current runner slots.`,
    });
  }

  if (harborConcurrency > 1) {
    findings.push({
      severity: "warning",
      title: "Harbor concurrency above current safe setting",
      detail: `n_concurrent=${harborConcurrency}; current safe setting is n_concurrent=1 per runner job.`,
    });
  }

  if (!input.dryRun && !input.confirmPaidRun) {
    findings.push({
      severity: "blocker",
      title: "Paid run is not confirmed",
      detail: "Paid dispatch commands require confirm_paid_run=true.",
    });
  }

  const providerCounts = input.selectedArms.reduce<Record<string, number>>((accumulator, arm) => {
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

  const hasQwen = input.selectedArms.some((arm) => classifyProviderFamily(arm) === "qwen");
  if (hasQwen && input.runMode === "full") {
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

  const hasFable = input.selectedArms.some((arm) => classifyProviderFamily(arm) === "fable");
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
    effectiveTaskParallelism: input.selectedArms.length * harborConcurrency,
    status: hasBlocker ? "blocked" : hasWarning ? "review" : "clear",
    runnerSlots,
  };
}

export function hasFinding(result: RunPlanValidationResult, title: string, severity?: Severity): boolean {
  return result.findings.some((finding) => {
    if (finding.title !== title) return false;
    return severity ? finding.severity === severity : true;
  });
}
