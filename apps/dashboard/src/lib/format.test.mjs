import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "format.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl =
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const formatting = await import(moduleUrl);

test("dashboard decimal ceiling is four fractional places", () => {
  assert.equal(formatting.DASHBOARD_MAX_FRACTION_DIGITS, 4);
});

test("high-precision values truncate toward zero rather than round", () => {
  assert.equal(
    formatting.truncateDecimalPlaces(12.345678),
    12.3456,
  );
  assert.equal(
    formatting.truncateDecimalPlaces(-12.345678),
    -12.3456,
  );
  assert.equal(
    formatting.truncateDecimalPlaces("1.999999"),
    1.9999,
  );
});

test("high-precision number presentation is capped at four decimals", () => {
  assert.equal(
    formatting.formatTruncatedNumber("1234.567899"),
    "1,234.5678",
  );
  assert.equal(
    formatting.formatTruncatedNumber("-9.87659"),
    "-9.8765",
  );
});

test("high-precision currency presentation is capped at four decimals", () => {
  assert.equal(
    formatting.formatTruncatedCurrency("12.345678"),
    "$12.3456",
  );
  assert.equal(
    formatting.formatTruncatedCurrency("-0.123456"),
    "-$0.1234",
  );
  assert.equal(
    formatting.formatTruncatedCurrency("12.3"),
    "$12.30",
  );
});

test("helpers reject presentation precision above the dashboard ceiling", () => {
  assert.throws(
    () => formatting.formatTruncatedCurrency("1.23", 5),
    RangeError,
  );
  assert.throws(
    () => formatting.formatTruncatedNumber("1.23", 5),
    RangeError,
  );
});

test("production dashboard source requests no presentation precision above four decimals", async () => {
  const { readdir } = await import("node:fs/promises");
  const { resolve } = await import("node:path");

  const sourceRoot = resolve(here, "..");
  const productionFiles = [];

  async function collect(path) {
    for (const entry of await readdir(path, { withFileTypes: true })) {
      const child = resolve(path, entry.name);

      if (entry.isDirectory()) {
        await collect(child);
        continue;
      }

      if (
        entry.isFile()
        && (
          entry.name.endsWith(".ts")
          || entry.name.endsWith(".tsx")
        )
      ) {
        productionFiles.push(child);
      }
    }
  }

  await collect(sourceRoot);

  const violations = [];

  const prohibited = [
    {
      label: "toFixed above four",
      pattern: /\.toFixed\(\s*(?:[5-9]|[1-9][0-9]+)\s*\)/g,
    },
    {
      label: "Intl fraction digits above four",
      pattern: /(?:minimum|maximum)FractionDigits\s*:\s*(?:[5-9]|[1-9][0-9]+)/g,
    },
    {
      label: "dashboard cost formatter request above four",
      pattern: /\b(?:formatMoney|linkedMoney|formatCost|linkedCost|formatTruncatedCurrency|formatTruncatedNumber)\([^;\n]*?,\s*(?:[5-9]|[1-9][0-9]+)\s*\)/g,
    },
  ];

  for (const path of productionFiles) {
    const text = await readFile(path, "utf8");

    for (const rule of prohibited) {
      for (const match of text.matchAll(rule.pattern)) {
        violations.push(
          `${rule.label}: ${path}: ${match[0]}`,
        );
      }
    }
  }

  assert.deepEqual(violations, []);
});

test("structured presentation data truncates decimal leaves without rewriting identifiers or short values", () => {
  const input = {
    numeric: 12.3456789,
    numericString: "0.1234567",
    shortDecimal: "1.2345",
    integer: 42,
    model: "gpt-5.4",
    nested: [
      {
        rate: "-9.876543",
        label: "provider-rate-v1.234567",
      },
    ],
  };

  assert.deepEqual(
    formatting.truncateStructuredDecimalsForDisplay(input),
    {
      numeric: 12.3456,
      numericString: "0.1234",
      shortDecimal: "1.2345",
      integer: 42,
      model: "gpt-5.4",
      nested: [
        {
          rate: "-9.8765",
          label: "provider-rate-v1.234567",
        },
      ],
    },
  );

  assert.deepEqual(input, {
    numeric: 12.3456789,
    numericString: "0.1234567",
    shortDecimal: "1.2345",
    integer: 42,
    model: "gpt-5.4",
    nested: [
      {
        rate: "-9.876543",
        label: "provider-rate-v1.234567",
      },
    ],
  });
});
