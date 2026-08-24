import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(
  join(here, "current-cost-presentation.ts"),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl =
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const presentation = await import(moduleUrl);

test("current cost relation markers preserve all four evidence relations", () => {
  assert.equal(
    presentation.formatCurrentCostRelation("$1.23", "exact"),
    "= $1.23",
  );
  assert.equal(
    presentation.formatCurrentCostRelation("$1.23", "estimate"),
    "~ $1.23",
  );
  assert.equal(
    presentation.formatCurrentCostRelation("$1.23", "lower_bound"),
    "≥ $1.23",
  );
  assert.equal(
    presentation.formatCurrentCostRelation(
      "$1.23",
      "historical_fallback",
    ),
    "$1.23 · historical fallback",
  );
  assert.equal(
    presentation.formatCurrentCostRelation("$1.23", null),
    "$1.23",
  );
});

test("relation labels remain explicit", () => {
  assert.equal(
    presentation.currentCostRelationLabel("exact"),
    "exact",
  );
  assert.equal(
    presentation.currentCostRelationLabel("estimate"),
    "estimate",
  );
  assert.equal(
    presentation.currentCostRelationLabel("lower_bound"),
    "lower bound",
  );
  assert.equal(
    presentation.currentCostRelationLabel("historical_fallback"),
    "historical fallback",
  );
});
