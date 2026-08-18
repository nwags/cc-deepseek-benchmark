export type ArmDraftRouteKind = "direct" | "litellm-routed";

export type ArmConfigDraftInput = Readonly<{
  routeKind: ArmDraftRouteKind;
  armId: string;
  displayName: string;
  provider: string;
  model: string;
  backendModel: string;
  expectedObservedModel: string;
  jobDirName: string;
  notes: string;
}>;

export type ArmConfigDraft = Readonly<{
  yaml: string;
  suggestedDestination: string;
  destinationArmIdIsValid: boolean;
  existingArmCollision: boolean;
  missingFields: readonly string[];
}>;

export const ARM_DRAFT_OMITTED_PROVIDER_FIELDS = Object.freeze([
  "secret_file",
  "secret_env_map",
  "env",
  "agent_env_keys",
  "clear_env",
  "agent_kwargs",
  "endpoint URLs",
] as const);

const ARM_ID_PATTERN = /^[a-z0-9][a-z0-9._-]*$/;

function quoteYamlScalar(value: string): string {
  return JSON.stringify(value)
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}

export function buildArmConfigDraft(
  input: ArmConfigDraftInput,
  existingArmIds: readonly string[],
): ArmConfigDraft {
  const lines = [
    `arm_id: ${quoteYamlScalar(input.armId)}`,
    `display_name: ${quoteYamlScalar(input.displayName)}`,
    `provider: ${quoteYamlScalar(input.provider)}`,
    "agent: claude-code",
  ];

  if (input.routeKind === "litellm-routed") {
    lines.push("router: litellm");
  }

  lines.push(`model: ${quoteYamlScalar(input.model)}`);
  if (input.backendModel !== "") {
    lines.push(`backend_model: ${quoteYamlScalar(input.backendModel)}`);
  }
  lines.push(`expected_observed_model: ${quoteYamlScalar(input.expectedObservedModel)}`);
  lines.push(`job_dir_name: ${quoteYamlScalar(input.jobDirName)}`);
  if (input.notes !== "") {
    lines.push("notes:", `  - ${quoteYamlScalar(input.notes)}`);
  }

  const requiredFields: ReadonlyArray<readonly [string, string]> = [
    ["arm_id", input.armId],
    ["display_name", input.displayName],
    ["provider", input.provider],
    ["model", input.model],
    ["expected_observed_model", input.expectedObservedModel],
    ["job_dir_name", input.jobDirName],
    ...(input.routeKind === "litellm-routed"
      ? [["backend_model", input.backendModel] as const]
      : []),
  ];
  const missingFields = requiredFields
    .filter(([, value]) => value.trim() === "")
    .map(([field]) => field);
  const destinationArmIdIsValid = ARM_ID_PATTERN.test(input.armId);

  return Object.freeze({
    yaml: `${lines.join("\n")}\n`,
    suggestedDestination: destinationArmIdIsValid
      ? `configs/arms/${input.armId}.yaml`
      : "configs/arms/<valid-arm-id>.yaml",
    destinationArmIdIsValid,
    existingArmCollision: existingArmIds.includes(input.armId),
    missingFields: Object.freeze(missingFields),
  });
}
