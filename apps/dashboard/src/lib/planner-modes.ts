export type PlannerMode = "run" | "arm";

export type PlannerModeSelection = Readonly<{
  mode: PlannerMode;
  warning: "invalid_mode" | "repeated_mode" | null;
  warningMessage: string | null;
  usedDefault: boolean;
}>;

export const DEFAULT_PLANNER_MODE: PlannerMode = "run";

export const PLANNER_MODE_OPTIONS: readonly Readonly<{
  id: PlannerMode;
  label: string;
}>[] = Object.freeze([
  Object.freeze({ id: "run", label: "Plan benchmark run" }),
  Object.freeze({ id: "arm", label: "Draft new arm configuration" }),
]);

export function selectPlannerMode(
  value: string | readonly string[] | null | undefined,
): PlannerModeSelection {
  if (value === null || value === undefined) {
    return {
      mode: DEFAULT_PLANNER_MODE,
      warning: null,
      warningMessage: null,
      usedDefault: true,
    };
  }
  if (Array.isArray(value)) {
    return {
      mode: DEFAULT_PLANNER_MODE,
      warning: "repeated_mode",
      warningMessage: "Repeated planner mode values are not supported; Plan benchmark run was selected.",
      usedDefault: true,
    };
  }
  if (value === "run" || value === "arm") {
    return {
      mode: value,
      warning: null,
      warningMessage: null,
      usedDefault: false,
    };
  }
  return {
    mode: DEFAULT_PLANNER_MODE,
    warning: "invalid_mode",
    warningMessage: "Unknown or empty planner mode; Plan benchmark run was selected.",
    usedDefault: true,
  };
}
