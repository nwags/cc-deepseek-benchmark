export type ProviderPresentation = Readonly<{
  familyKey: string;
  label: string;
}>;

const MODEL_LABELS: Readonly<Record<string, string>> = Object.freeze({
  "claude-fable-5": "Claude Fable 5",
  "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
  "anthropic/claude-haiku-4-5-20251001": "Claude Haiku 4.5",
  "claude-opus-4-7": "Claude Opus 4.7",
  "claude-sonnet-4-6": "Claude Sonnet 4.6",
  "anthropic/claude-sonnet-4-6": "Claude Sonnet 4.6",

  "deepseek-v4-flash": "DeepSeek V4 Flash",
  "deepseek-v4-pro": "DeepSeek V4 Pro",
  "deepseek-v4-pro[1m]": "DeepSeek V4 Pro",

  "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
  "gemini-3.5-flash": "Gemini 3.5 Flash",

  "glm-5": "GLM 5",
  "glm-5.1": "GLM 5.1",
  "glm-5.2": "GLM 5.2",

  "gpt-5.3": "GPT-5.3",
  "gpt-5.4": "GPT-5.4",
  "gpt-5.5": "GPT-5.5",

  "grok-3": "Grok 3",
  "grok-build-0.1": "Grok Build 0.1",

  "kimi-k2.5": "Kimi K2.5",
  "kimi-k2.6": "Kimi K2.6",
  "kimi-k3": "Kimi K3",

  "qwen-3.5": "Qwen 3.5",
  "qwen3.7-plus": "Qwen 3.7 Plus",
});

const ARM_MODEL_LABELS: Readonly<Record<string, string>> = Object.freeze({
  "arm-a-anthropic": "Claude Sonnet 4.6",
  "arm-b-deepseek-pro": "DeepSeek V4 Pro",
  "arm-c-deepseek-flash": "DeepSeek V4 Flash",

  "arm-anthropic-haiku": "Claude Haiku 4.5",
  "arm-anthropic-opus": "Claude Opus 4.7",
  "arm-anthropic-sonnet": "Claude Sonnet 4.6",
  "arm-deepseek-flash": "DeepSeek V4 Flash",
  "arm-deepseek-pro": "DeepSeek V4 Pro",

  "anthropic-haiku": "Claude Haiku 4.5",
  "anthropic-opus": "Claude Opus 4.7",
  "anthropic-sonnet": "Claude Sonnet 4.6",
  "deepseek-flash": "DeepSeek V4 Flash",
  "deepseek-pro": "DeepSeek V4 Pro",

  "router-anthropic-fable-5": "Claude Fable 5",
  "router-anthropic-haiku": "Claude Haiku 4.5",
  "router-anthropic-haiku-sanitized": "Claude Haiku 4.5",
  "router-anthropic-opus": "Claude Opus 4.7",
  "router-anthropic-sonnet": "Claude Sonnet 4.6",

  "router-deepseek-flash": "DeepSeek V4 Flash",
  "router-deepseek-pro": "DeepSeek V4 Pro",

  "router-gemini-3.1-pro": "Gemini 3.1 Pro Preview",
  "router-gemini-flash": "Gemini 3.5 Flash",

  "router-glm-5": "GLM 5",
  "router-glm-5.1": "GLM 5.1",
  "router-glm-5.2": "GLM 5.2",

  "router-gpt-5.3": "GPT-5.3",
  "router-gpt-5.4": "GPT-5.4",
  "router-gpt-5.5": "GPT-5.5",

  "router-grok-3": "Grok 3",
  "router-grok-build-0.1": "Grok Build 0.1",

  "router-kimi-k2.5": "Kimi K2.5",
  "router-kimi-k2.6": "Kimi K2.6",
  "router-kimi-k3": "Kimi K3",

  "router-qwen-3.5": "Qwen 3.5",
  "router-qwen-3.7-plus": "Qwen 3.7 Plus",
});

const PROVIDER_PRESENTATIONS: Readonly<Record<string, ProviderPresentation>> =
  Object.freeze({
    anthropic: Object.freeze({
      familyKey: "anthropic",
      label: "Anthropic",
    }),
    deepseek: Object.freeze({
      familyKey: "deepseek",
      label: "DeepSeek",
    }),
    "google-gemini": Object.freeze({
      familyKey: "google-gemini",
      label: "Google / Gemini",
    }),
    openai: Object.freeze({
      familyKey: "openai",
      label: "OpenAI",
    }),
    xai: Object.freeze({
      familyKey: "xai",
      label: "xAI / Grok",
    }),
    moonshot: Object.freeze({
      familyKey: "moonshot-kimi",
      label: "Moonshot / Kimi",
    }),
    "moonshot-kimi": Object.freeze({
      familyKey: "moonshot-kimi",
      label: "Moonshot / Kimi",
    }),
    "dashscope-qwen": Object.freeze({
      familyKey: "dashscope-qwen",
      label: "Alibaba / Qwen",
    }),
    "zai-glm": Object.freeze({
      familyKey: "zai-glm",
      label: "Z.AI / GLM",
    }),
  });

const ROUTING_LABELS: Readonly<Record<string, string>> = Object.freeze({
  litellm: "LiteLLM-routed",
  "litellm-routed": "LiteLLM-routed",
  litellm_router: "LiteLLM-routed",
  phase1_direct: "Phase 1 direct",
  phase2_direct: "Phase 2 direct",
  phase3_router_addendum: "LiteLLM-routed",
  direct: "Direct",
});

function sourceValue(value: string | null | undefined): string {
  return value === null || value === undefined || value === "" ? "—" : value;
}

export function friendlyModelLabel(
  value: string | null | undefined,
): string {
  const source = sourceValue(value);
  return MODEL_LABELS[source] ?? source;
}

export function friendlyArmLabel(
  armId: string | null | undefined,
  backendModel?: string | null,
): string {
  if (backendModel !== null && backendModel !== undefined && backendModel !== "") {
    return friendlyModelLabel(backendModel);
  }

  const source = sourceValue(armId);
  return ARM_MODEL_LABELS[source] ?? source;
}

export function providerPresentation(
  value: string | null | undefined,
): ProviderPresentation {
  const source = sourceValue(value);
  if (source === "—") {
    return Object.freeze({ familyKey: "unknown", label: "—" });
  }

  return PROVIDER_PRESENTATIONS[source]
    ?? Object.freeze({ familyKey: source, label: source });
}

export function friendlyProviderLabel(
  value: string | null | undefined,
): string {
  return providerPresentation(value).label;
}

export function friendlyRoutingLabel(
  value: string | null | undefined,
): string {
  const source = sourceValue(value);
  return ROUTING_LABELS[source] ?? source;
}
