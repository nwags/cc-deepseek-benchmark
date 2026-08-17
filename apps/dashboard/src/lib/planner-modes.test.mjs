import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "planner-modes.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const plannerModes = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

test("planner mode selection defaults safely and validates URL state", () => {
  assert.deepEqual(plannerModes.selectPlannerMode(undefined), {
    mode: "run",
    warning: null,
    warningMessage: null,
    usedDefault: true,
  });
  assert.deepEqual(plannerModes.selectPlannerMode("run"), {
    mode: "run",
    warning: null,
    warningMessage: null,
    usedDefault: false,
  });
  assert.deepEqual(plannerModes.selectPlannerMode("arm"), {
    mode: "arm",
    warning: null,
    warningMessage: null,
    usedDefault: false,
  });

  for (const invalid of ["", "unknown"]) {
    const selected = plannerModes.selectPlannerMode(invalid);
    assert.equal(selected.mode, "run");
    assert.equal(selected.warning, "invalid_mode");
    assert.match(selected.warningMessage, /Unknown or empty planner mode/);
  }

  const repeated = plannerModes.selectPlannerMode(["arm", "run"]);
  assert.equal(repeated.mode, "run");
  assert.equal(repeated.warning, "repeated_mode");
  assert.match(repeated.warningMessage, /Repeated planner mode values/);
});

test("planner mode options expose the two canonical URL values in display order", () => {
  assert.deepEqual(plannerModes.PLANNER_MODE_OPTIONS, [
    { id: "run", label: "Plan benchmark run" },
    { id: "arm", label: "Draft new arm configuration" },
  ]);
});
