import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

const pgStubSource = `
class Pool {
  constructor(config) {
    globalThis.__dbTestPoolConfig = config;
  }

  async connect() {
    return globalThis.__dbTestClient;
  }
}

export default { Pool };
`;

const pgStubUrl =
  `data:text/javascript;base64,${
    Buffer.from(pgStubSource).toString("base64")
  }`;

const source = await readFile(
  join(here, "db.ts"),
  "utf8",
);

const rewrittenSource = source.replace(
  'from "pg"',
  `from "${pgStubUrl}"`,
);

const compiled = ts.transpileModule(
  rewrittenSource,
  {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  },
).outputText;

process.env.SUPABASE_DB_URL =
  "postgresql://user:password@example.test/database"
  + "?sslmode=require&uselibpqcompat=true";

const database = await import(
  `data:text/javascript;base64,${
    Buffer.from(compiled).toString("base64")
  }`
);

test("queryRows wraps successful dashboard reads in an explicit read-only transaction", async () => {
  const calls = [];
  let releases = 0;

  globalThis.__dbTestClient = {
    async query(sql, params) {
      calls.push({ sql, params });

      if (sql === "select value from example where id = $1") {
        return {
          rows: [{ value: "ok" }],
        };
      }

      return { rows: [] };
    },

    release() {
      releases += 1;
    },
  };

  const rows = await database.queryRows(
    "select value from example where id = $1",
    ["example-id"],
  );

  assert.deepEqual(rows, [{ value: "ok" }]);

  assert.deepEqual(
    calls,
    [
      {
        sql: "begin read only",
        params: undefined,
      },
      {
        sql: "select value from example where id = $1",
        params: ["example-id"],
      },
      {
        sql: "commit",
        params: undefined,
      },
    ],
  );

  assert.equal(releases, 1);

  assert.equal(
    globalThis.__dbTestPoolConfig.ssl.rejectUnauthorized,
    false,
  );

  assert.doesNotMatch(
    globalThis.__dbTestPoolConfig.connectionString,
    /sslmode=/,
  );

  assert.doesNotMatch(
    globalThis.__dbTestPoolConfig.connectionString,
    /uselibpqcompat=/,
  );
});

test("queryRows rolls back and releases the connection when a dashboard query fails", async () => {
  const calls = [];
  let releases = 0;

  globalThis.__dbTestClient = {
    async query(sql, params) {
      calls.push({ sql, params });

      if (sql === "select explode") {
        throw new Error("synthetic query failure");
      }

      return { rows: [] };
    },

    release() {
      releases += 1;
    },
  };

  await assert.rejects(
    database.queryRows("select explode"),
    /synthetic query failure/,
  );

  assert.deepEqual(
    calls,
    [
      {
        sql: "begin read only",
        params: undefined,
      },
      {
        sql: "select explode",
        params: [],
      },
      {
        sql: "rollback",
        params: undefined,
      },
    ],
  );

  assert.equal(releases, 1);
});

test("dashboard DB source has no direct pool query bypass in queryRows", () => {
  assert.match(
    source,
    /await client\.query\("begin read only"\)/,
  );

  assert.match(
    source,
    /await client\.query\("commit"\)/,
  );

  assert.match(
    source,
    /await client\.query\("rollback"\)/,
  );

  assert.doesNotMatch(
    source,
    /getPool\(\)\.query\(/,
  );
});
