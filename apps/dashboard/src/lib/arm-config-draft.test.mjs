import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "arm-config-draft.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const drafts = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

const directInput = {
  routeKind: "direct",
  armId: "direct-example",
  displayName: "Direct Example",
  provider: "example-provider",
  model: "provider/example-model",
  backendModel: "",
  expectedObservedModel: "example-model",
  jobDirName: "arm-direct-example",
  notes: "Draft for normal Git review.",
};

test("direct arm draft emits only supportable fields without a LiteLLM router", () => {
  const result = drafts.buildArmConfigDraft(directInput, []);
  assert.equal(result.yaml, [
    'arm_id: "direct-example"',
    'display_name: "Direct Example"',
    'provider: "example-provider"',
    "agent: claude-code",
    'model: "provider/example-model"',
    'expected_observed_model: "example-model"',
    'job_dir_name: "arm-direct-example"',
    "notes:",
    '  - "Draft for normal Git review."',
    "",
  ].join("\n"));
  assert.doesNotMatch(result.yaml, /^router:/m);
  assert.doesNotMatch(result.yaml, /^backend_model:/m);
  assert.equal(result.suggestedDestination, "configs/arms/direct-example.yaml");
  assert.deepEqual(result.missingFields, []);
});

test("LiteLLM-routed arm draft emits router and backend-model identity", () => {
  const result = drafts.buildArmConfigDraft({
    ...directInput,
    routeKind: "litellm-routed",
    armId: "router-example",
    displayName: "Router Example",
    model: "router-example",
    backendModel: "provider/backend-model",
    expectedObservedModel: "router-example",
    jobDirName: "arm-router-example",
  }, []);
  assert.match(result.yaml, /^router: litellm$/m);
  assert.match(result.yaml, /^backend_model: "provider\/backend-model"$/m);
  assert.deepEqual(result.missingFields, []);
});

test("YAML scalar quoting is deterministic and blocks top-level key injection", () => {
  const injection = {
    ...directInput,
    armId: "draft-arm\nrouter: litellm",
    displayName: 'Quoted "name" # review',
    notes: "first line\nsecret_file: .secrets/should-not-exist.env",
  };
  const first = drafts.buildArmConfigDraft(injection, []);
  const second = drafts.buildArmConfigDraft(injection, []);
  assert.equal(first.yaml, second.yaml);
  assert.match(first.yaml, /draft-arm\\nrouter: litellm/);
  assert.match(first.yaml, /first line\\nsecret_file:/);
  assert.doesNotMatch(first.yaml, /^router: litellm$/m);
  assert.doesNotMatch(first.yaml, /^secret_file:/m);
  assert.equal(first.destinationArmIdIsValid, false);
  assert.equal(first.suggestedDestination, "configs/arms/<valid-arm-id>.yaml");
});

test("ordinary draft values remain data and no provider credential fields are generated", () => {
  const result = drafts.buildArmConfigDraft({
    ...directInput,
    provider: "token-named-provider",
    notes: "API key mapping must be reviewed separately.",
  }, []);
  assert.match(result.yaml, /provider: "token-named-provider"/);
  assert.match(result.yaml, /API key mapping must be reviewed separately/);
  for (const key of [
    "secret_file",
    "secret_env_map",
    "env",
    "agent_env_keys",
    "clear_env",
    "agent_kwargs",
  ]) {
    assert.doesNotMatch(result.yaml, new RegExp(`^${key}:`, "m"));
  }
  assert.doesNotMatch(source, /process\.env|Deno\.env|Bun\.env|readFile|writeFile|fetch\(/);
});

test("existing arm collision is exact, visible in the result, and does not mutate IDs", () => {
  const existingArmIds = ["direct-example", "another-arm"];
  const retained = [...existingArmIds];
  assert.equal(drafts.buildArmConfigDraft(directInput, existingArmIds).existingArmCollision, true);
  assert.equal(drafts.buildArmConfigDraft({ ...directInput, armId: "Direct-Example" }, existingArmIds).existingArmCollision, false);
  assert.deepEqual(existingArmIds, retained);
});

test("routed drafts identify backend_model as required without guessing it", () => {
  const result = drafts.buildArmConfigDraft({
    ...directInput,
    routeKind: "litellm-routed",
    backendModel: "",
  }, []);
  assert.deepEqual(result.missingFields, ["backend_model"]);
  assert.doesNotMatch(result.yaml, /^backend_model:/m);
});
