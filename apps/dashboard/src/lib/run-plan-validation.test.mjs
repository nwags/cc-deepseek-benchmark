import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(here, "run-plan-validation.ts");
const source = await readFile(sourcePath, "utf8");

const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl = `data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`;
const { hasFinding, validateRunPlan } = await import(moduleUrl);

const gpt = {
  arm_id: "router-gpt-5.5",
  provider: "openai",
  backend_model: "gpt-5.5",
};

const geminiPro = {
  arm_id: "router-gemini-3.1-pro",
  provider: "google-gemini",
  backend_model: "gemini-3.1-pro-preview",
};

const geminiFlash = {
  arm_id: "router-gemini-flash",
  provider: "google-gemini",
  backend_model: "gemini-3.5-flash",
};

const anthropic = {
  arm_id: "router-anthropic-opus",
  provider: "anthropic",
  backend_model: "claude-opus-4-7",
};

const qwen = {
  arm_id: "router-qwen-3.7-plus",
  provider: "dashscope",
  backend_model: "qwen3.7-plus",
};

const fable = {
  arm_id: "router-anthropic-fable-5",
  provider: "anthropic",
  backend_model: "claude-fable-5",
};

function plan(overrides) {
  return validateRunPlan({
    selectedArms: [],
    runMode: "smoke",
    dryRun: true,
    confirmPaidRun: false,
    nConcurrent: "1",
    runnerSlots: 3,
    ...overrides,
  });
}

test("3 arms with n_concurrent=1 gives effective concurrency 3", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic], nConcurrent: "1" });
  assert.equal(result.effectiveTaskParallelism, 3);
  assert.equal(result.harborConcurrency, 1);
  assert.equal(result.status, "clear");
});

test("3 arms with n_concurrent=2 warns and gives effective concurrency 6", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic], nConcurrent: "2" });
  assert.equal(result.effectiveTaskParallelism, 6);
  assert.equal(result.harborConcurrency, 2);
  assert.equal(result.status, "review");
  assert.equal(hasFinding(result, "Harbor concurrency above checked-in assumption", "warning"), true);
});

test("2 Gemini arms is blocked", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, geminiFlash] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Gemini provider-family concurrency exceeded", "blocker"), true);
});

test("Qwen full mode is blocked", () => {
  const result = plan({ selectedArms: [qwen], runMode: "full" });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Qwen full sweep blocked", "blocker"), true);
});

test("Fable selected is blocked", () => {
  const result = plan({ selectedArms: [fable] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Fable planner gate", "blocker"), true);
});

test("4 selected arms exceeds 3-slot runner capacity", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic, qwen] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Runner-slot capacity exceeded", "blocker"), true);
});
