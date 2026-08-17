import assert from "node:assert/strict";
import test from "node:test";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const here = dirname(fileURLToPath(import.meta.url));
const source = await readFile(join(here, "data-freshness.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText;
const freshnessModuleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
const freshness = await import(freshnessModuleUrl);
const serverSource = await readFile(join(here, "data-freshness-server.ts"), "utf8");
const serverCompiled = ts
  .transpileModule(serverSource, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
  })
  .outputText.replace('"./data-freshness"', JSON.stringify(freshnessModuleUrl));
const freshnessServer = await import(
  `data:text/javascript;base64,${Buffer.from(serverCompiled).toString("base64")}`
);

const operationalBase = {
  sourceLabel: "Supabase/Postgres test source",
  sourceRelations: ["benchmark.v_test"],
  populationLabel: "Test population",
  queryStatus: "available",
  queriedAt: "2026-08-10T12:00:00Z",
  latestIncludedExecutionAt: "2026-08-10T11:00:00Z",
  latestCanonicalPublishedAt: null,
  staleAfterSeconds: null,
  warningMessage: null,
};
const expectedSelectedLabels = Array.from({ length: 16 }, (_, index) => `arm-${index + 1}/run`);
const registeredOperationalSource = Object.freeze({
  sourceKind: "operational",
  sourceLabel: "Registered operational test source",
  sourceRelations: Object.freeze(["benchmark.v_test"]),
  populationLabel: "Registered test population",
  reviewedAt: null,
  schemaVersion: null,
  provenanceIdentifier: null,
});

test("freshness metadata reads preserve success and isolate secondary read failure", async () => {
  const available = await freshnessServer.readFreshnessMetadata(async () =>
    "2026-08-10T11:00:00Z"
  );
  assert.deepEqual(available, {
    queryStatus: "available",
    value: "2026-08-10T11:00:00Z",
  });

  const unavailable = await freshnessServer.readFreshnessMetadata(async () => {
    throw new Error("database unavailable");
  });
  assert.deepEqual(unavailable, { queryStatus: "unavailable", value: null });
});

test("arm-run identity coverage warns about unresolved stored execution evidence", () => {
  const warning = freshnessServer.armRunFreshnessCoverageWarning({
    expectedIdentityCount: 4,
    resolvedIdentityCount: 2,
    unresolvedIdentities: [{}],
    duplicateIdentities: [{}],
    missingFinishedAtIdentities: [{}],
  });
  assert.match(warning, /resolved exactly for 2 of 4 displayed arm-run identities/);
  assert.match(warning, /could not be resolved/);
  assert.match(warning, /matched more than one Phase 3 arm run/);
  assert.match(warning, /no usable execution completion timestamp/);
  assert.match(warning, /No substitute run was selected/);

  assert.equal(freshnessServer.armRunFreshnessCoverageWarning({
    expectedIdentityCount: 1,
    resolvedIdentityCount: 1,
    unresolvedIdentities: [],
    duplicateIdentities: [],
    missingFinishedAtIdentities: [],
  }), null);
});

test("registered operational freshness keeps canonical publication and threshold unset", () => {
  const result = freshnessServer.buildRegisteredOperationalFreshness(
    registeredOperationalSource,
    { queryStatus: "available", value: "2026-08-10T11:00:00Z" },
    "2026-08-10T12:00:00Z",
  );
  assert.equal(result.queryStatus, "available");
  assert.equal(result.freshnessStatus, "unknown");
  assert.equal(result.freshnessReason, "threshold_not_configured");
  assert.equal(result.canonicalPublicationStatus, "not_recorded");
  assert.equal(result.latestCanonicalPublishedAt, null);
  assert.equal(result.publicationLagSeconds, null);
});

test("failed or timestamp-free metadata never becomes current", () => {
  const unavailable = freshnessServer.buildRegisteredOperationalFreshness(
    registeredOperationalSource,
    { queryStatus: "unavailable", value: null },
    "2026-08-10T12:00:00Z",
  );
  assert.equal(unavailable.queryStatus, "unavailable");
  assert.equal(unavailable.freshnessStatus, "unavailable");

  const unknown = freshnessServer.buildRegisteredOperationalFreshness(
    registeredOperationalSource,
    { queryStatus: "available", value: null },
    "2026-08-10T12:00:00Z",
  );
  assert.equal(unknown.queryStatus, "available");
  assert.equal(unknown.freshnessStatus, "unknown");
  assert.equal(unknown.freshnessReason, "execution_timestamp_missing");
  assert.equal(unknown.dataAgeSeconds, null);
});

test("exact-label coverage accepts 16 unique expected labels", () => {
  const coverage = freshness.summarizeExpectedLabelCoverage(
    expectedSelectedLabels,
    expectedSelectedLabels,
  );
  assert.deepEqual(coverage, {
    expectedCount: 16,
    returnedRowCount: 16,
    uniqueExpectedReturnedCount: 16,
    missingLabels: [],
    duplicateLabels: [],
    unexpectedLabels: [],
    isComplete: true,
  });
  assert.equal(freshness.expectedLabelCoverageWarning("Stored run-summary evidence", coverage), null);
});

test("exact-label coverage reports a missing selected label", () => {
  const coverage = freshness.summarizeExpectedLabelCoverage(
    expectedSelectedLabels,
    expectedSelectedLabels.slice(0, 15),
  );
  assert.equal(coverage.uniqueExpectedReturnedCount, 15);
  assert.deepEqual(coverage.missingLabels, [expectedSelectedLabels[15]]);
  assert.equal(coverage.isComplete, false);
  assert.match(
    freshness.expectedLabelCoverageWarning("Stored run-summary evidence", coverage),
    /available for 15 of 16 selected labels.*Missing labels:/,
  );
});

test("equal row count remains incomplete with one missing and one duplicate label", () => {
  const returned = [...expectedSelectedLabels.slice(0, 15), expectedSelectedLabels[0]];
  const coverage = freshness.summarizeExpectedLabelCoverage(expectedSelectedLabels, returned);
  assert.equal(coverage.returnedRowCount, 16);
  assert.equal(coverage.uniqueExpectedReturnedCount, 15);
  assert.deepEqual(coverage.missingLabels, [expectedSelectedLabels[15]]);
  assert.deepEqual(coverage.duplicateLabels, [expectedSelectedLabels[0]]);
  assert.equal(coverage.isComplete, false);
});

test("unexpected labels are warned and do not satisfy expected coverage", () => {
  const returned = [...expectedSelectedLabels.slice(0, 15), "unexpected-arm/run"];
  const coverage = freshness.summarizeExpectedLabelCoverage(expectedSelectedLabels, returned);
  assert.equal(coverage.returnedRowCount, 16);
  assert.equal(coverage.uniqueExpectedReturnedCount, 15);
  assert.deepEqual(coverage.missingLabels, [expectedSelectedLabels[15]]);
  assert.deepEqual(coverage.unexpectedLabels, ["unexpected-arm/run"]);
  assert.match(
    freshness.expectedLabelCoverageWarning("Stored run-summary evidence", coverage),
    /Unexpected labels: unexpected-arm\/run/,
  );
});

test("partial adjusted-cost and quality evidence produce distinct warnings without zero fabrication", () => {
  const partialCost = freshness.summarizeExpectedLabelCoverage(
    expectedSelectedLabels,
    expectedSelectedLabels.slice(0, 14),
  );
  const qualityRows = expectedSelectedLabels.slice(0, 15).map((run_label) => ({
    run_label,
    suspect_noop_count: 0,
  }));
  const partialQuality = freshness.summarizeExpectedLabelCoverage(
    expectedSelectedLabels,
    qualityRows.map((row) => row.run_label),
  );
  const qualityByLabel = new Map(qualityRows.map((row) => [row.run_label, row]));

  assert.match(
    freshness.expectedLabelCoverageWarning("Stored adjusted-cost evidence", partialCost),
    /available for 14 of 16 selected labels/,
  );
  const qualityWarning = freshness.expectedLabelCoverageWarning(
    "Stored quality context",
    partialQuality,
  );
  assert.match(qualityWarning, /Stored quality context is available for 15 of 16 selected labels/);
  assert.equal(qualityByLabel.get(expectedSelectedLabels[15]), undefined);
  assert.notEqual(qualityByLabel.get(expectedSelectedLabels[15]), 0);

  const operational = freshness.buildOperationalFreshness({
    ...operationalBase,
    warningMessage: `${freshness.expectedLabelCoverageWarning("Stored adjusted-cost evidence", partialCost)} ${qualityWarning}`,
  });
  assert.equal(operational.queryStatus, "available");
  assert.equal(operational.freshnessStatus, "unknown");
  assert.equal(operational.freshnessReason, "threshold_not_configured");
  assert.match(operational.warningMessage, /14 of 16/);
  assert.match(operational.warningMessage, /15 of 16/);
});

test("reviewed provenance remains a snapshot rather than live freshness", () => {
  const result = freshness.buildReviewedSnapshotFreshness({
    sourceLabel: "Reviewed source",
    populationLabel: "Frozen population",
    reviewedAt: "2026-08-05",
    schemaVersion: "reviewed-v1",
    provenanceIdentifier: "results/reviewed.json",
  });
  assert.equal(result.freshnessStatus, "snapshot");
  assert.equal(result.freshnessReason, "reviewed_snapshot");
  assert.equal(result.queryStatus, "not_applicable");
  assert.equal(result.canonicalPublicationStatus, "not_applicable");
  assert.equal(result.dataAgeSeconds, null);
});

test("available operational evidence has unknown freshness without repository policy", () => {
  const result = freshness.buildOperationalFreshness(operationalBase);
  assert.equal(result.queryStatus, "available");
  assert.equal(result.freshnessStatus, "unknown");
  assert.equal(result.freshnessReason, "threshold_not_configured");
  assert.equal(result.dataAgeSeconds, 3600);
  assert.equal(result.canonicalPublicationStatus, "not_recorded");
  assert.equal(result.latestCanonicalPublishedAt, null);
  assert.equal(result.publicationLagSeconds, null);
  assert.equal(freshness.canonicalPublicationText(result), "Not recorded");
});

test("operational freshness preserves canonical RFC3339 behavior", () => {
  const result = freshness.buildOperationalFreshness({
    ...operationalBase,
    queriedAt: "2026-07-31T17:09:09.208Z",
    latestIncludedExecutionAt: "2026-07-31T16:09:09.208Z",
  });
  assert.equal(result.freshnessReason, "threshold_not_configured");
  assert.equal(result.dataAgeSeconds, 3600);
  assert.equal(result.latestIncludedExecutionAt, "2026-07-31T16:09:09.208Z");
});

test("operational freshness accepts constrained PostgreSQL timestamptz text", () => {
  const cases = [
    "2026-07-31 16:09:09.208372+00",
    "2026-07-31 12:09:09.208372-04",
    "2026-07-31 21:39:09.123456+05:30",
  ];

  for (const latestIncludedExecutionAt of cases) {
    const result = freshness.buildOperationalFreshness({
      ...operationalBase,
      queriedAt: "2026-07-31T17:09:09.208Z",
      latestIncludedExecutionAt,
    });
    assert.equal(result.freshnessReason, "threshold_not_configured");
    assert.notEqual(result.dataAgeSeconds, null);
    assert.equal(result.latestIncludedExecutionAt, latestIncludedExecutionAt);
  }
});

test("unavailable operational query cannot become current", () => {
  const result = freshness.buildOperationalFreshness({
    ...operationalBase,
    queryStatus: "unavailable",
    latestIncludedExecutionAt: null,
  });
  assert.equal(result.queryStatus, "unavailable");
  assert.equal(result.freshnessStatus, "unavailable");
  assert.equal(result.freshnessReason, "query_unavailable");
  assert.equal(result.dataAgeSeconds, null);
  assert.match(result.warningMessage, /database read was unavailable/);
});

test("missing and malformed timestamps fail safely", () => {
  const missing = freshness.buildOperationalFreshness({
    ...operationalBase,
    latestIncludedExecutionAt: null,
  });
  assert.equal(missing.freshnessStatus, "unknown");
  assert.equal(missing.freshnessReason, "execution_timestamp_missing");
  assert.equal(missing.dataAgeSeconds, null);

  const malformedExecution = freshness.buildOperationalFreshness({
    ...operationalBase,
    latestIncludedExecutionAt: "not-a-timestamp",
  });
  assert.equal(malformedExecution.freshnessReason, "execution_timestamp_invalid");
  assert.equal(malformedExecution.dataAgeSeconds, null);

  const malformedQuery = freshness.buildOperationalFreshness({
    ...operationalBase,
    queriedAt: "2026-08-10",
  });
  assert.equal(malformedQuery.freshnessReason, "query_timestamp_invalid");
  assert.equal(malformedQuery.dataAgeSeconds, null);

  for (const malformedTimestamp of [
    "2026-08-10",
    "2026-07-31 16:09:09.208372",
    "July 31, 2026 16:09 UTC",
  ]) {
    const malformedPostgres = freshness.buildOperationalFreshness({
      ...operationalBase,
      latestIncludedExecutionAt: malformedTimestamp,
    });
    assert.equal(malformedPostgres.freshnessReason, "execution_timestamp_invalid");
    assert.equal(malformedPostgres.dataAgeSeconds, null);
  }
});

test("future execution completion reports possible clock skew without negative age", () => {
  const result = freshness.buildOperationalFreshness({
    ...operationalBase,
    latestIncludedExecutionAt: "2026-08-10T12:00:01Z",
  });
  assert.equal(result.freshnessStatus, "unknown");
  assert.equal(result.freshnessReason, "execution_timestamp_in_future");
  assert.equal(result.dataAgeSeconds, null);
  assert.match(result.warningMessage, /clock skew/);
});

test("a test-only threshold can classify current and stale without setting repository policy", () => {
  const current = freshness.buildOperationalFreshness({
    ...operationalBase,
    staleAfterSeconds: 3600,
  });
  assert.equal(current.freshnessStatus, "current");
  assert.equal(current.freshnessReason, "within_configured_threshold");

  const stale = freshness.buildOperationalFreshness({
    ...operationalBase,
    staleAfterSeconds: 3599,
  });
  assert.equal(stale.freshnessStatus, "stale");
  assert.equal(stale.freshnessReason, "exceeds_configured_threshold");
});

test("created_at input cannot stand in for canonical publication", () => {
  const result = freshness.buildOperationalFreshness({
    ...operationalBase,
    created_at: "2026-08-10T11:30:00Z",
  });
  assert.equal(result.canonicalPublicationStatus, "not_recorded");
  assert.equal(result.latestCanonicalPublishedAt, null);
  assert.equal(freshness.canonicalPublicationText(result), "Not recorded");
});

test("latest execution selection is deterministic and reports malformed values", () => {
  const result = freshness.findLatestIncludedExecutionAt([
    "2026-08-09T00:00:00Z",
    null,
    "invalid",
    "2026-08-10T00:00:00Z",
  ]);
  assert.deepEqual(result, {
    latestTimestamp: "2026-08-10T00:00:00Z",
    invalidTimestampCount: 1,
  });
});

test("latest execution selection compares mixed timestamp syntax and preserves source text", () => {
  const selectedSourceTimestamp = "2026-07-31 12:09:10.208372-04";
  const result = freshness.findLatestIncludedExecutionAt([
    "2026-07-31T16:09:09.208Z",
    "2026-07-31 21:39:09.123456+05:30",
    "not-a-timestamp",
    selectedSourceTimestamp,
  ]);
  assert.deepEqual(result, {
    latestTimestamp: selectedSourceTimestamp,
    invalidTimestampCount: 1,
  });
});

test("live heartbeat threshold is an explicit liveness-only boundary", () => {
  const atBoundary = freshness.buildLiveHeartbeatLiveness({
    queryStatus: "available",
    observedAt: "2026-08-11T12:01:30Z",
    latestHeartbeatAt: "2026-08-11T12:00:00Z",
    latestEventAt: "2026-08-11T12:00:30Z",
    heartbeatThresholdSeconds: 90,
  });
  assert.equal(atBoundary.livenessStatus, "active");
  assert.equal(atBoundary.heartbeatAgeSeconds, 90);
  assert.equal(atBoundary.livenessReason, "heartbeat_within_live_threshold");

  const delayed = freshness.buildLiveHeartbeatLiveness({
    ...atBoundary,
    observedAt: "2026-08-11T12:01:30.001Z",
  });
  assert.equal(delayed.livenessStatus, "delayed");
  assert.ok(delayed.heartbeatAgeSeconds > 90);
  assert.equal(delayed.livenessReason, "heartbeat_exceeds_live_threshold");

  const ordinary = freshness.buildOperationalFreshness(operationalBase);
  assert.equal(ordinary.freshnessStatus, "unknown");
  assert.equal(ordinary.freshnessReason, "threshold_not_configured");
});

test("live heartbeat accepts constrained PostgreSQL timestamptz text", () => {
  const postgresHeartbeat = "2026-07-31 16:09:09.208372+00";
  const result = freshness.buildLiveHeartbeatLiveness({
    queryStatus: "available",
    observedAt: "2026-07-31T16:10:00Z",
    latestHeartbeatAt: postgresHeartbeat,
    latestEventAt: null,
    heartbeatThresholdSeconds: 90,
  });
  assert.equal(result.livenessStatus, "active");
  assert.equal(result.livenessReason, "heartbeat_within_live_threshold");
  assert.equal(result.latestHeartbeatAt, postgresHeartbeat);
});

test("live heartbeat missing, malformed, future, and failed reads never become active", () => {
  const base = {
    queryStatus: "available",
    observedAt: "2026-08-11T12:00:00Z",
    latestHeartbeatAt: "2026-08-11T11:59:30Z",
    latestEventAt: null,
    heartbeatThresholdSeconds: 90,
  };
  const missing = freshness.buildLiveHeartbeatLiveness({ ...base, latestHeartbeatAt: null });
  assert.equal(missing.livenessStatus, "unknown");
  assert.equal(missing.livenessReason, "heartbeat_missing");

  const malformed = freshness.buildLiveHeartbeatLiveness({ ...base, latestHeartbeatAt: "invalid" });
  assert.equal(malformed.livenessStatus, "unknown");
  assert.equal(malformed.livenessReason, "heartbeat_timestamp_invalid");

  const future = freshness.buildLiveHeartbeatLiveness({ ...base, latestHeartbeatAt: "2026-08-11T12:00:01Z" });
  assert.equal(future.livenessStatus, "unknown");
  assert.equal(future.livenessReason, "heartbeat_timestamp_in_future");
  assert.equal(future.heartbeatAgeSeconds, null);

  const unavailable = freshness.buildLiveHeartbeatLiveness({
    ...base,
    queryStatus: "unavailable",
    latestHeartbeatAt: null,
  });
  assert.equal(unavailable.livenessStatus, "unavailable");
  assert.equal(unavailable.livenessReason, "live_query_unavailable");
});

test("latest live observation selection ignores null and reports malformed timestamps", () => {
  assert.deepEqual(freshness.findLatestObservedTimestamp([
    null,
    "2026-08-11T11:00:00Z",
    "malformed",
    "2026-08-11T12:00:00Z",
  ]), {
    latestTimestamp: "2026-08-11T12:00:00Z",
    invalidTimestampCount: 1,
  });
});
