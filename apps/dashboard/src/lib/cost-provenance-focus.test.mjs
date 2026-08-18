import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dbStub = `data:text/javascript;base64,${Buffer.from(`
  export async function queryRows(sql, params = []) {
    return globalThis.__costFocusQueryHandler(sql, params);
  }
`).toString("base64")}`;
const source = await readFile(join(here, "dashboard-data.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText.replace('from "./db"', `from "${dbStub}"`);
const dashboardData = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("cost focus query uses parameterized exact identities against the valid-only view", async () => {
  let call;
  globalThis.__costFocusQueryHandler = async (sql, params) => {
    call = { sql, params };
    return [];
  };
  await dashboardData.getCostProvenanceFocusRows({
    trialId: "00000000-0000-0000-0000-000000000001",
    runLabel: "arm-a/run-1",
    armId: "arm-a",
  });

  assert.deepEqual(call.params, [
    "00000000-0000-0000-0000-000000000001",
    "arm-a/run-1",
    "arm-a",
    50,
  ]);
  assert.match(call.sql, /from benchmark\.v_trial_adjusted_cost_coverage/);
  assert.match(call.sql, /trial_id = \$1::uuid/);
  assert.match(call.sql, /run_label = \$2/);
  assert.match(call.sql, /arm_id = \$3/);
  assert.match(call.sql, /limit \$4::int/);
  assert.doesNotMatch(call.sql, /\blike\b|latest|prefix/i);
  assert.doesNotMatch(call.sql, /insert|update|delete/i);
});

test("conflicting exact focus returns no match without a second or fallback query", async () => {
  const calls = [];
  globalThis.__costFocusQueryHandler = async (sql, params) => {
    calls.push({ sql, params });
    return [];
  };
  const rows = await dashboardData.getCostProvenanceFocusRows({
    trialId: "00000000-0000-0000-0000-000000000001",
    runLabel: "different/run",
    armId: null,
  });
  assert.deepEqual(rows, []);
  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /trial_id = \$1::uuid[\s\S]+and run_label = \$2/);
});

test("unfocused cost query fails before database access", async () => {
  let called = false;
  globalThis.__costFocusQueryHandler = async () => {
    called = true;
    return [];
  };
  await assert.rejects(
    dashboardData.getCostProvenanceFocusRows({ trialId: null, runLabel: null, armId: null }),
    /requires at least one exact identity/,
  );
  assert.equal(called, false);
});
