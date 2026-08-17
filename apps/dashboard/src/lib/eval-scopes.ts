export type EvalInventoryScopeId = "valid-imported" | "all-imported";

export type EvalInventoryScopeSelection = Readonly<{
  scopeId: EvalInventoryScopeId;
  warning: "invalid_scope" | "repeated_scope" | null;
  warningMessage: string | null;
  usedDefault: boolean;
}>;

export const DEFAULT_EVAL_INVENTORY_SCOPE: EvalInventoryScopeId = "valid-imported";

export function selectEvalInventoryScope(
  value: string | readonly string[] | null | undefined,
): EvalInventoryScopeSelection {
  if (value === null || value === undefined) {
    return {
      scopeId: DEFAULT_EVAL_INVENTORY_SCOPE,
      warning: null,
      warningMessage: null,
      usedDefault: true,
    };
  }
  if (Array.isArray(value)) {
    return {
      scopeId: DEFAULT_EVAL_INVENTORY_SCOPE,
      warning: "repeated_scope",
      warningMessage: "Repeated scope values are not supported; Valid imported was selected.",
      usedDefault: true,
    };
  }
  if (value === "valid-imported" || value === "all-imported") {
    return {
      scopeId: value,
      warning: null,
      warningMessage: null,
      usedDefault: false,
    };
  }
  return {
    scopeId: DEFAULT_EVAL_INVENTORY_SCOPE,
    warning: "invalid_scope",
    warningMessage: "Unknown scope value; Valid imported was selected.",
    usedDefault: true,
  };
}
