"Shared run-plan validation logic for the benchmark dashboard.";

import type {
  PromotionGateLoadStatus,
  PromotionGateRow,
} from "./planner-types";

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
  promotionGateLoadStatus?: PromotionGateLoadStatus;
  promotionGates?: readonly PromotionGateRow[];
  promotionReviewConfirmed?: boolean;
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

export function promotionReviewEvidenceKey(input: {
  selectedArmIds: readonly string[];
  runMode: RunMode;
  promotionGateLoadStatus: PromotionGateLoadStatus;
  promotionGates: readonly PromotionGateRow[];
}): string {
  const selectedArmIds = [...new Set(input.selectedArmIds)].sort();
  const selected = new Set(selectedArmIds);

  const gates = input.promotionGates
    .filter(
      (gate) =>
        selected.has(gate.arm_id)
        && gate.target_mode === input.runMode,
    )
    .map((gate) => ({
      gate_id: gate.gate_id,
      arm_id: gate.arm_id,
      source_arm_run_id: gate.source_arm_run_id,
      usage_reconciliation_id: gate.usage_reconciliation_id,
      cost_reconciliation_id: gate.cost_reconciliation_id,
      source_mode: gate.source_mode,
      target_mode: gate.target_mode,
      decision: gate.decision,
      blocker_codes: [...(gate.blocker_codes ?? [])].sort(),
      derived_blocker_codes: [
        ...(gate.derived_blocker_codes ?? []),
      ].sort(),
      waiver_reason: gate.waiver_reason,
      effective_can_advance: gate.effective_can_advance,
      reviewed_by: gate.reviewed_by,
      reviewed_at: gate.reviewed_at,
      usage_validation_status: gate.usage_validation_status,
      cost_validation_status: gate.cost_validation_status,
      selected_usage_authority: gate.selected_usage_authority,
      selected_cost_basis: gate.selected_cost_basis,
      selected_cost_relation: gate.selected_cost_relation,
      selected_cost_usd: gate.selected_cost_usd,
      usage_limitation_codes: [
        ...(gate.usage_limitation_codes ?? []),
      ].sort(),
      cost_limitation_codes: [
        ...(gate.cost_limitation_codes ?? []),
      ].sort(),
    }))
    .sort((left, right) =>
      `${left.arm_id}:${left.gate_id}`.localeCompare(
        `${right.arm_id}:${right.gate_id}`,
      ),
    );

  return JSON.stringify({
    run_mode: input.runMode,
    load_status: input.promotionGateLoadStatus,
    selected_arm_ids: selectedArmIds,
    gates,
  });
}

export function validateRunPlan(input: RunPlanValidationInput): RunPlanValidationResult {
  const runnerSlots = input.runnerSlots ?? DEFAULT_RUNNER_SLOTS;
  const harborConcurrency = parseHarborConcurrency(input.nConcurrent);
  const findings: RunPlanFinding[] = [];

  if (
    input.selectedArms.length > 0
    && input.promotionGateLoadStatus !== undefined
  ) {
    if (input.runMode === "canary") {
      findings.push({
        severity: "ok",
        title: "Canary is the entry evidence stage",
        detail:
          "No predecessor promotion gate is required for Canary. Review the resulting provider evidence and qualitative artifacts before planning Smoke.",
      });
    } else if (input.promotionGateLoadStatus === "unavailable") {
      findings.push({
        severity: "blocker",
        title: "Promotion evidence unavailable",
        detail:
          "The current promotion-gate view could not be read. The Planner remains usable, but Smoke/Full commands are withheld until current promotion evidence can be reviewed.",
      });
    } else {
      const expectedSourceMode = input.runMode === "smoke" ? "canary" : "smoke";
      let allEvidenceQualified = true;

      for (const arm of input.selectedArms) {
        const gate = (input.promotionGates ?? []).find(
          (candidate) =>
            candidate.arm_id === arm.arm_id
            && candidate.target_mode === input.runMode,
        );

        if (!gate) {
          allEvidenceQualified = false;
          findings.push({
            severity: "blocker",
            title: `Promotion gate missing: ${arm.arm_id}`,
            detail:
              `No current ${expectedSourceMode} → ${input.runMode} promotion review exists for this arm.`,
          });
          continue;
        }

        if (gate.source_mode !== expectedSourceMode) {
          allEvidenceQualified = false;
          findings.push({
            severity: "blocker",
            title: `Promotion transition mismatch: ${arm.arm_id}`,
            detail:
              `The current gate is ${gate.source_mode} → ${gate.target_mode}; expected ${expectedSourceMode} → ${input.runMode}.`,
          });
          continue;
        }

        const derivedBlockers = gate.derived_blocker_codes ?? [];
        const reviewedBlockers = gate.blocker_codes ?? [];
        const visibleBlockers = [...new Set([...reviewedBlockers, ...derivedBlockers])];

        if (gate.decision === "waived") {
          allEvidenceQualified = false;
          findings.push({
            severity: "blocker",
            title: `Promotion waiver is not authorization: ${arm.arm_id}`,
            detail:
              `Waiver provenance is recorded${gate.waiver_reason ? `: ${gate.waiver_reason}` : "."} `
              + "The evidence contract intentionally does not convert a waiver into effective advancement.",
          });
          continue;
        }

        if (gate.decision !== "pass") {
          allEvidenceQualified = false;
          findings.push({
            severity: "blocker",
            title: `Promotion review blocked: ${arm.arm_id}`,
            detail:
              visibleBlockers.length > 0
                ? `Current blocker codes: ${visibleBlockers.join(", ")}.`
                : "The current reviewed gate decision is blocked.",
          });
          continue;
        }

        if (!gate.effective_can_advance) {
          allEvidenceQualified = false;
          findings.push({
            severity: "blocker",
            title: `Promotion evidence is stale or inconsistent: ${arm.arm_id}`,
            detail:
              visibleBlockers.length > 0
                ? `Derived blocker codes: ${visibleBlockers.join(", ")}.`
                : "The reviewed decision says pass, but the fail-closed promotion view does not currently authorize advancement.",
          });
          continue;
        }

        findings.push({
          severity: "ok",
          title: `Promotion evidence qualified: ${arm.arm_id}`,
          detail:
            `${gate.source_mode} → ${gate.target_mode}; usage=${gate.usage_validation_status}; `
            + `cost=${gate.cost_validation_status}. Qualitative review is still a separate human step.`,
        });
      }

      if (allEvidenceQualified) {
        if (input.promotionReviewConfirmed) {
          findings.push({
            severity: "ok",
            title: "Human promotion review confirmed",
            detail:
              "The operator confirmed review of the displayed promotion evidence and relevant qualitative evidence for this exact arm set and mode.",
          });
        } else {
          findings.push({
            severity: "blocker",
            title: "Human promotion review not confirmed",
            detail:
              "Evidence qualification alone is not the execution decision. Confirm review of the current evidence and relevant qualitative artifacts before copying the next-stage commands.",
          });
        }
      }
    }
  }

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
      detail: `${input.selectedArms.length} workflow jobs requested against the ${runnerSlots}-slot configured planner assumption. Split the planned wave and verify actual runner capacity separately.`,
    });
  } else {
    findings.push({
      severity: "ok",
      title: "Runner-slot capacity",
      detail: `${input.selectedArms.length} workflow jobs requested against the ${runnerSlots}-slot configured planner assumption.`,
    });
  }

  if (harborConcurrency > 1) {
    findings.push({
      severity: "warning",
      title: "Harbor concurrency above checked-in assumption",
      detail: `n_concurrent=${harborConcurrency}; the checked-in planner concurrency assumption is n_concurrent=1 per runner job.`,
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
        "The checked-in planner rule caps Gemini at 1 concurrent arm; it does not establish current quota, availability, or readiness.",
    });
  } else if ((providerCounts.gemini ?? 0) === 1) {
    findings.push({
      severity: "ok",
      title: "Gemini provider-family concurrency",
      detail: "One Gemini-family arm satisfies the checked-in planner rule; current provider readiness is not verified here.",
    });
  }

  const hasQwen = input.selectedArms.some((arm) => classifyProviderFamily(arm) === "qwen");
  if (hasQwen && input.runMode === "full") {
    findings.push({
      severity: "blocker",
      title: "Qwen full sweep blocked",
      detail:
        "The checked-in planner rule blocks Qwen full sweeps while Alibaba identity and usage-metering review remains unresolved; this is not a live provider observation.",
    });
  } else if (hasQwen) {
    findings.push({
      severity: "warning",
      title: "Qwen billing-verification risk",
      detail:
        "The checked-in planner rule permits Qwen only for reviewed diagnostics/smoke while Alibaba identity and usage-metering review remains unresolved.",
    });
  }

  const hasFable = input.selectedArms.some((arm) => classifyProviderFamily(arm) === "fable");
  if (hasFable) {
    findings.push({
      severity: "blocker",
      title: "Fable planner gate",
      detail: "The checked-in planner rule blocks Fable; it does not establish current provider availability, access, or readiness.",
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
