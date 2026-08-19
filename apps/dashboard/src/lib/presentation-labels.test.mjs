import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "presentation-labels.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl = `data:text/javascript;base64,${
  Buffer.from(compiled).toString("base64")
}`;
const labels = await import(moduleUrl);

test("friendly model labels cover reviewed model families", () => {
  assert.equal(labels.friendlyModelLabel("glm-5.2"), "GLM 5.2");
  assert.equal(labels.friendlyModelLabel("gpt-5.5"), "GPT-5.5");
  assert.equal(
    labels.friendlyModelLabel("deepseek-v4-pro"),
    "DeepSeek V4 Pro",
  );
  assert.equal(
    labels.friendlyModelLabel("gemini-3.5-flash"),
    "Gemini 3.5 Flash",
  );
  assert.equal(
    labels.friendlyModelLabel("claude-sonnet-4-6"),
    "Claude Sonnet 4.6",
  );
  assert.equal(labels.friendlyModelLabel("kimi-k3"), "Kimi K3");
  assert.equal(
    labels.friendlyModelLabel("deepseek-v4-pro[1m]"),
    "DeepSeek V4 Pro",
  );
  assert.equal(
    labels.friendlyModelLabel("anthropic/claude-haiku-4-5-20251001"),
    "Claude Haiku 4.5",
  );
  assert.equal(
    labels.friendlyModelLabel("qwen3.7-plus"),
    "Qwen 3.7 Plus",
  );
});

test("friendly arm labels do not depend on config display_name", () => {
  assert.equal(
    labels.friendlyArmLabel("router-kimi-k3"),
    "Kimi K3",
  );
  assert.equal(
    labels.friendlyArmLabel(
      "router-anthropic-haiku-sanitized",
      "claude-haiku-4-5-20251001",
    ),
    "Claude Haiku 4.5",
  );
});

test("provider presentation keeps canonical grouping keys", () => {
  assert.deepEqual(
    labels.providerPresentation("anthropic"),
    { familyKey: "anthropic", label: "Anthropic" },
  );
  assert.deepEqual(
    labels.providerPresentation("google-gemini"),
    { familyKey: "google-gemini", label: "Google / Gemini" },
  );
  assert.deepEqual(
    labels.providerPresentation("moonshot"),
    { familyKey: "moonshot-kimi", label: "Moonshot / Kimi" },
  );
  assert.deepEqual(
    labels.providerPresentation("moonshot-kimi"),
    { familyKey: "moonshot-kimi", label: "Moonshot / Kimi" },
  );
  assert.equal(
    labels.friendlyProviderLabel("dashscope-qwen"),
    "Alibaba / Qwen",
  );
  assert.equal(
    labels.friendlyProviderLabel("zai-glm"),
    "Z.AI / GLM",
  );
});

test("routing labels retain route distinctions", () => {
  assert.equal(
    labels.friendlyRoutingLabel("litellm_router"),
    "LiteLLM-routed",
  );
  assert.equal(
    labels.friendlyRoutingLabel("phase1_direct"),
    "Phase 1 direct",
  );
  assert.equal(
    labels.friendlyRoutingLabel("phase3_router_addendum"),
    "LiteLLM-routed",
  );
});

test("unknown canonical values fail safe to their source value", () => {
  assert.equal(
    labels.friendlyModelLabel("future-model-v9"),
    "future-model-v9",
  );
  assert.equal(
    labels.friendlyArmLabel("future-arm-v9"),
    "future-arm-v9",
  );
  assert.deepEqual(
    labels.providerPresentation("future-provider"),
    {
      familyKey: "future-provider",
      label: "future-provider",
    },
  );
  assert.equal(
    labels.friendlyRoutingLabel("future_route"),
    "future_route",
  );
});
