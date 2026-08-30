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

export type PromotionGateDecision = "pass" | "blocked" | "waived";

export type PromotionGateRow = {
  gate_id: string;
  arm_id: string;
  source_arm_run_id: string;
  usage_reconciliation_id: string;
  cost_reconciliation_id: string;
  source_mode: "canary" | "smoke";
  target_mode: "smoke" | "full";
  decision: PromotionGateDecision;
  blocker_codes: string[];
  derived_blocker_codes: string[];
  waiver_reason: string | null;
  effective_can_advance: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  usage_validation_status: string;
  cost_validation_status: string;
  selected_usage_authority: string;
  selected_cost_basis: string;
  selected_cost_relation: string;
  selected_cost_usd: string | null;
  usage_limitation_codes: string[];
  cost_limitation_codes: string[];
};

export type PromotionGateLoadStatus = "available" | "unavailable";
