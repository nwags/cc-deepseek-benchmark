import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "eval-scopes.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const scopes = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("Evals defaults safely to valid-imported", () => {
  assert.equal(scopes.DEFAULT_EVAL_INVENTORY_SCOPE, "valid-imported");
  assert.deepEqual(scopes.selectEvalInventoryScope(undefined), {
    scopeId: "valid-imported",
    warning: null,
    warningMessage: null,
    usedDefault: true,
  });
});

test("Evals accepts only the two explicit inventory scopes", () => {
  for (const scopeId of ["valid-imported", "all-imported"]) {
    assert.deepEqual(scopes.selectEvalInventoryScope(scopeId), {
      scopeId,
      warning: null,
      warningMessage: null,
      usedDefault: false,
    });
  }
});

test("unknown and repeated Evals scopes warn and fall back to valid-imported", () => {
  const invalid = scopes.selectEvalInventoryScope("phase3-core");
  assert.equal(invalid.scopeId, "valid-imported");
  assert.equal(invalid.warning, "invalid_scope");
  assert.match(invalid.warningMessage, /Unknown scope value/);

  const empty = scopes.selectEvalInventoryScope("");
  assert.equal(empty.scopeId, "valid-imported");
  assert.equal(empty.warning, "invalid_scope");

  const repeated = scopes.selectEvalInventoryScope(["all-imported", "valid-imported"]);
  assert.equal(repeated.scopeId, "valid-imported");
  assert.equal(repeated.warning, "repeated_scope");
  assert.match(repeated.warningMessage, /Repeated scope values/);
});
