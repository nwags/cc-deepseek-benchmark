export type DataSourceKind =
  | "operational"
  | "artifact"
  | "reviewed"
  | "historical"
  | "configuration";

export type QueryStatus = "available" | "unavailable" | "not_applicable";

export type FreshnessStatus =
  | "current"
  | "stale"
  | "publication_lagged"
  | "unknown"
  | "unavailable"
  | "snapshot";

export type CanonicalPublicationStatus =
  | "available"
  | "not_recorded"
  | "not_applicable";

export type FreshnessReason =
  | "reviewed_snapshot"
  | "query_unavailable"
  | "query_timestamp_missing"
  | "query_timestamp_invalid"
  | "execution_timestamp_missing"
  | "execution_timestamp_invalid"
  | "execution_timestamp_in_future"
  | "threshold_not_configured"
  | "within_configured_threshold"
  | "exceeds_configured_threshold";

export type DataFreshnessContract = Readonly<{
  sourceKind: DataSourceKind;
  sourceLabel: string;
  sourceRelations: readonly string[];
  populationLabel: string;
  provenanceIdentifier: string | null;
  queryStatus: QueryStatus;
  queriedAt: string | null;
  latestIncludedExecutionAt: string | null;
  latestCanonicalPublishedAt: string | null;
  canonicalPublicationStatus: CanonicalPublicationStatus;
  dataAgeSeconds: number | null;
  publicationLagSeconds: number | null;
  freshnessStatus: FreshnessStatus;
  freshnessReason: FreshnessReason;
  reviewedAt: string | null;
  schemaVersion: string | null;
  warningMessage: string | null;
}>;

export type OperationalFreshnessInput = Readonly<{
  sourceLabel: string;
  sourceRelations: readonly string[];
  populationLabel: string;
  queryStatus: "available" | "unavailable";
  queriedAt: string | null;
  latestIncludedExecutionAt: string | null;
  latestCanonicalPublishedAt: string | null;
  staleAfterSeconds: number | null;
  warningMessage: string | null;
}>;

export type ReviewedSnapshotFreshnessInput = Readonly<{
  sourceLabel: string;
  populationLabel: string;
  reviewedAt: string;
  schemaVersion: string;
  provenanceIdentifier: string;
}>;

export type LatestTimestampResult = Readonly<{
  latestTimestamp: string | null;
  invalidTimestampCount: number;
}>;

export type ExpectedLabelCoverage = Readonly<{
  expectedCount: number;
  returnedRowCount: number;
  uniqueExpectedReturnedCount: number;
  missingLabels: readonly string[];
  duplicateLabels: readonly string[];
  unexpectedLabels: readonly string[];
  isComplete: boolean;
}>;

export type LiveLivenessStatus = "active" | "delayed" | "unavailable" | "unknown";

export type LiveLivenessReason =
  | "heartbeat_within_live_threshold"
  | "heartbeat_exceeds_live_threshold"
  | "live_query_unavailable"
  | "heartbeat_missing"
  | "heartbeat_timestamp_invalid"
  | "observation_timestamp_invalid"
  | "heartbeat_timestamp_in_future";

export type LiveHeartbeatLivenessContract = Readonly<{
  queryStatus: "available" | "unavailable";
  observedAt: string;
  latestHeartbeatAt: string | null;
  latestEventAt: string | null;
  heartbeatAgeSeconds: number | null;
  heartbeatThresholdSeconds: number;
  livenessStatus: LiveLivenessStatus;
  livenessReason: LiveLivenessReason;
  warningMessage: string | null;
}>;

export type LiveHeartbeatLivenessInput = Readonly<{
  queryStatus: "available" | "unavailable";
  observedAt: string;
  latestHeartbeatAt: string | null;
  latestEventAt: string | null;
  heartbeatThresholdSeconds: number;
}>;

const ISO_TIMESTAMP_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

function parseIsoTimestamp(value: string): number | null {
  if (!ISO_TIMESTAMP_PATTERN.test(value)) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function buildLiveHeartbeatLiveness(
  input: LiveHeartbeatLivenessInput,
): LiveHeartbeatLivenessContract {
  if (!Number.isFinite(input.heartbeatThresholdSeconds) || input.heartbeatThresholdSeconds <= 0) {
    throw new Error("Live heartbeat threshold must be a positive number");
  }
  const base = {
    queryStatus: input.queryStatus,
    observedAt: input.observedAt,
    latestHeartbeatAt: input.latestHeartbeatAt,
    latestEventAt: input.latestEventAt,
    heartbeatThresholdSeconds: input.heartbeatThresholdSeconds,
  };
  if (input.queryStatus === "unavailable") {
    return Object.freeze({
      ...base,
      heartbeatAgeSeconds: null,
      livenessStatus: "unavailable",
      livenessReason: "live_query_unavailable",
      warningMessage: "The live source is unavailable; heartbeat liveness cannot be established.",
    });
  }
  const observedMilliseconds = parseIsoTimestamp(input.observedAt);
  if (observedMilliseconds === null) {
    return Object.freeze({
      ...base,
      heartbeatAgeSeconds: null,
      livenessStatus: "unknown",
      livenessReason: "observation_timestamp_invalid",
      warningMessage: "The liveness observation timestamp is malformed.",
    });
  }
  if (input.latestHeartbeatAt === null) {
    return Object.freeze({
      ...base,
      heartbeatAgeSeconds: null,
      livenessStatus: "unknown",
      livenessReason: "heartbeat_missing",
      warningMessage: "No live heartbeat timestamp is available; the run is not classified as active.",
    });
  }
  const heartbeatMilliseconds = parseIsoTimestamp(input.latestHeartbeatAt);
  if (heartbeatMilliseconds === null) {
    return Object.freeze({
      ...base,
      heartbeatAgeSeconds: null,
      livenessStatus: "unknown",
      livenessReason: "heartbeat_timestamp_invalid",
      warningMessage: "The latest live heartbeat timestamp is malformed.",
    });
  }
  if (heartbeatMilliseconds > observedMilliseconds) {
    return Object.freeze({
      ...base,
      heartbeatAgeSeconds: null,
      livenessStatus: "unknown",
      livenessReason: "heartbeat_timestamp_in_future",
      warningMessage: "The latest live heartbeat is in the future relative to observation time; possible clock skew prevents an active classification.",
    });
  }
  const heartbeatAgeSeconds = (observedMilliseconds - heartbeatMilliseconds) / 1000;
  const active = heartbeatAgeSeconds <= input.heartbeatThresholdSeconds;
  return Object.freeze({
    ...base,
    heartbeatAgeSeconds,
    livenessStatus: active ? "active" : "delayed",
    livenessReason: active
      ? "heartbeat_within_live_threshold"
      : "heartbeat_exceeds_live_threshold",
    warningMessage: active
      ? null
      : `The latest live heartbeat exceeds the ${input.heartbeatThresholdSeconds}-second live-liveness threshold.`,
  });
}

export function findLatestObservedTimestamp(
  timestamps: readonly (string | null)[],
): LatestTimestampResult {
  return findLatestIncludedExecutionAt(timestamps);
}

function joinWarnings(...warnings: Array<string | null>): string | null {
  const retained = warnings.filter((warning): warning is string => Boolean(warning));
  return retained.length ? retained.join(" ") : null;
}

export function summarizeExpectedLabelCoverage(
  expectedLabels: readonly string[],
  returnedLabels: readonly string[],
): ExpectedLabelCoverage {
  if (expectedLabels.some((label) => !label)) {
    throw new Error("Expected labels must be non-empty strings");
  }
  const expected = new Set(expectedLabels);
  if (expected.size !== expectedLabels.length) {
    throw new Error("Expected labels must be unique");
  }

  const returnedCounts = new Map<string, number>();
  for (const label of returnedLabels) {
    returnedCounts.set(label, (returnedCounts.get(label) ?? 0) + 1);
  }

  const missingLabels = expectedLabels.filter((label) => !returnedCounts.has(label));
  const duplicateLabels = expectedLabels.filter((label) => (returnedCounts.get(label) ?? 0) > 1);
  const unexpectedLabels = [...returnedCounts.keys()].filter((label) => !expected.has(label));
  const uniqueExpectedReturnedCount = expectedLabels.length - missingLabels.length;
  const isComplete = missingLabels.length === 0
    && duplicateLabels.length === 0
    && unexpectedLabels.length === 0;

  return Object.freeze({
    expectedCount: expectedLabels.length,
    returnedRowCount: returnedLabels.length,
    uniqueExpectedReturnedCount,
    missingLabels: Object.freeze(missingLabels),
    duplicateLabels: Object.freeze(duplicateLabels),
    unexpectedLabels: Object.freeze(unexpectedLabels),
    isComplete,
  });
}

export function expectedLabelCoverageWarning(
  evidenceLabel: string,
  coverage: ExpectedLabelCoverage,
): string | null {
  if (coverage.isComplete) return null;
  const details = [
    `${evidenceLabel} is available for ${coverage.uniqueExpectedReturnedCount} of ${coverage.expectedCount} selected labels (${coverage.returnedRowCount} row(s) returned).`,
  ];
  if (coverage.missingLabels.length) {
    details.push(`Missing labels: ${coverage.missingLabels.join(", ")}.`);
  }
  if (coverage.duplicateLabels.length) {
    details.push(`Duplicate labels: ${coverage.duplicateLabels.join(", ")}.`);
  }
  if (coverage.unexpectedLabels.length) {
    details.push(`Unexpected labels: ${coverage.unexpectedLabels.join(", ")}.`);
  }
  return details.join(" ");
}

export function findLatestIncludedExecutionAt(
  timestamps: readonly (string | null)[],
): LatestTimestampResult {
  let latestTimestamp: string | null = null;
  let latestMilliseconds = Number.NEGATIVE_INFINITY;
  let invalidTimestampCount = 0;

  for (const timestamp of timestamps) {
    if (timestamp === null) continue;
    const milliseconds = parseIsoTimestamp(timestamp);
    if (milliseconds === null) {
      invalidTimestampCount += 1;
      continue;
    }
    if (milliseconds > latestMilliseconds) {
      latestMilliseconds = milliseconds;
      latestTimestamp = timestamp;
    }
  }

  return Object.freeze({ latestTimestamp, invalidTimestampCount });
}

export function buildReviewedSnapshotFreshness(
  input: ReviewedSnapshotFreshnessInput,
): DataFreshnessContract {
  return Object.freeze({
    sourceKind: "reviewed",
    sourceLabel: input.sourceLabel,
    sourceRelations: Object.freeze([]),
    populationLabel: input.populationLabel,
    provenanceIdentifier: input.provenanceIdentifier,
    queryStatus: "not_applicable",
    queriedAt: null,
    latestIncludedExecutionAt: null,
    latestCanonicalPublishedAt: null,
    canonicalPublicationStatus: "not_applicable",
    dataAgeSeconds: null,
    publicationLagSeconds: null,
    freshnessStatus: "snapshot",
    freshnessReason: "reviewed_snapshot",
    reviewedAt: input.reviewedAt,
    schemaVersion: input.schemaVersion,
    warningMessage: null,
  });
}

export function buildOperationalFreshness(
  input: OperationalFreshnessInput,
): DataFreshnessContract {
  const canonicalMilliseconds = input.latestCanonicalPublishedAt === null
    ? null
    : parseIsoTimestamp(input.latestCanonicalPublishedAt);
  const canonicalRecorded = input.latestCanonicalPublishedAt !== null
    && canonicalMilliseconds !== null;
  const canonicalPublicationStatus: CanonicalPublicationStatus = canonicalRecorded
    ? "available"
    : "not_recorded";
  const latestCanonicalPublishedAt = canonicalRecorded
    ? input.latestCanonicalPublishedAt
    : null;

  const base = {
    sourceKind: "operational" as const,
    sourceLabel: input.sourceLabel,
    sourceRelations: Object.freeze([...input.sourceRelations]),
    populationLabel: input.populationLabel,
    provenanceIdentifier: null,
    queryStatus: input.queryStatus,
    queriedAt: input.queriedAt,
    latestIncludedExecutionAt: input.latestIncludedExecutionAt,
    latestCanonicalPublishedAt,
    canonicalPublicationStatus,
    reviewedAt: null,
    schemaVersion: null,
  };

  if (input.queryStatus === "unavailable") {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unavailable",
      freshnessReason: "query_unavailable",
      warningMessage: joinWarnings(
        "The operational database read was unavailable; freshness cannot be established.",
        input.warningMessage,
      ),
    });
  }

  if (input.queriedAt === null) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unknown",
      freshnessReason: "query_timestamp_missing",
      warningMessage: joinWarnings("The query/render timestamp is unavailable.", input.warningMessage),
    });
  }
  const queriedMilliseconds = parseIsoTimestamp(input.queriedAt);
  if (queriedMilliseconds === null) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unknown",
      freshnessReason: "query_timestamp_invalid",
      warningMessage: joinWarnings("The query/render timestamp is invalid.", input.warningMessage),
    });
  }

  if (input.latestIncludedExecutionAt === null) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unknown",
      freshnessReason: "execution_timestamp_missing",
      warningMessage: joinWarnings("No included execution completion timestamp is available.", input.warningMessage),
    });
  }
  const executionMilliseconds = parseIsoTimestamp(input.latestIncludedExecutionAt);
  if (executionMilliseconds === null) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unknown",
      freshnessReason: "execution_timestamp_invalid",
      warningMessage: joinWarnings("The included execution completion timestamp is invalid.", input.warningMessage),
    });
  }

  const ageSeconds = (queriedMilliseconds - executionMilliseconds) / 1000;
  if (ageSeconds < 0) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: null,
      publicationLagSeconds: null,
      freshnessStatus: "unknown",
      freshnessReason: "execution_timestamp_in_future",
      warningMessage: joinWarnings(
        "The included execution completion is later than the query/render time; clock skew may be present.",
        input.warningMessage,
      ),
    });
  }

  const publicationLagSeconds = canonicalMilliseconds === null
    ? null
    : Math.max(0, (canonicalMilliseconds - executionMilliseconds) / 1000);

  if (input.staleAfterSeconds === null) {
    return Object.freeze({
      ...base,
      dataAgeSeconds: ageSeconds,
      publicationLagSeconds,
      freshnessStatus: "unknown",
      freshnessReason: "threshold_not_configured",
      warningMessage: input.warningMessage,
    });
  }
  if (!Number.isFinite(input.staleAfterSeconds) || input.staleAfterSeconds < 0) {
    throw new Error("staleAfterSeconds must be null or a non-negative finite number");
  }

  const stale = ageSeconds > input.staleAfterSeconds;
  return Object.freeze({
    ...base,
    dataAgeSeconds: ageSeconds,
    publicationLagSeconds,
    freshnessStatus: stale ? "stale" : "current",
    freshnessReason: stale ? "exceeds_configured_threshold" : "within_configured_threshold",
    warningMessage: stale
      ? joinWarnings("The latest included execution exceeds the configured freshness threshold.", input.warningMessage)
      : input.warningMessage,
  });
}

export function canonicalPublicationText(contract: DataFreshnessContract): string {
  if (contract.canonicalPublicationStatus === "not_recorded") return "Not recorded";
  if (contract.canonicalPublicationStatus === "not_applicable") return "Not applicable";
  return contract.latestCanonicalPublishedAt ?? "Unavailable";
}
