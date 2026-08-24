import type {
  CurrentSelectedCostRelation,
} from "./current-cost-relation";

export function currentCostRelationLabel(
  relation: CurrentSelectedCostRelation,
): string {
  if (relation === "exact") return "exact";
  if (relation === "estimate") return "estimate";
  if (relation === "lower_bound") return "lower bound";
  return "historical fallback";
}

export function currentCostRelationMarker(
  relation: CurrentSelectedCostRelation,
): "=" | "~" | "≥" | null {
  if (relation === "exact") return "=";
  if (relation === "estimate") return "~";
  if (relation === "lower_bound") return "≥";
  return null;
}

export function formatCurrentCostRelation(
  formattedValue: string,
  relation: CurrentSelectedCostRelation | null,
): string {
  if (relation === null) return formattedValue;

  const marker = currentCostRelationMarker(relation);

  if (marker !== null) {
    return `${marker} ${formattedValue}`;
  }

  return `${formattedValue} · historical fallback`;
}
