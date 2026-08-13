import { buildOperationalFreshness, type DataFreshnessContract } from "./data-freshness";
import type { DashboardDataSourceDefinition } from "./data-freshness-sources";

export type FreshnessMetadataRead<T> = Readonly<{
  queryStatus: "available" | "unavailable";
  value: T | null;
}>;

export type ArmRunFreshnessCoverage = Readonly<{
  expectedIdentityCount: number;
  resolvedIdentityCount: number;
  unresolvedIdentities: readonly unknown[];
  duplicateIdentities: readonly unknown[];
  missingFinishedAtIdentities: readonly unknown[];
}>;

export async function readFreshnessMetadata<T>(
  read: () => Promise<T>,
): Promise<FreshnessMetadataRead<T>> {
  try {
    return Object.freeze({ queryStatus: "available", value: await read() });
  } catch {
    return Object.freeze({ queryStatus: "unavailable", value: null });
  }
}

export function armRunFreshnessCoverageWarning(
  coverage: ArmRunFreshnessCoverage,
): string | null {
  const details: string[] = [];
  if (coverage.unresolvedIdentities.length) {
    details.push(`${coverage.unresolvedIdentities.length} displayed identity/identities could not be resolved.`);
  }
  if (coverage.duplicateIdentities.length) {
    details.push(`${coverage.duplicateIdentities.length} displayed identity/identities matched more than one Phase 3 arm run.`);
  }
  if (coverage.missingFinishedAtIdentities.length) {
    details.push(`${coverage.missingFinishedAtIdentities.length} resolved identity/identities have no usable execution completion timestamp.`);
  }
  if (details.length === 0) return null;
  return [
    `Execution evidence resolved exactly for ${coverage.resolvedIdentityCount} of ${coverage.expectedIdentityCount} displayed arm-run identities.`,
    ...details,
    "No substitute run was selected.",
  ].join(" ");
}

export function buildRegisteredOperationalFreshness(
  source: DashboardDataSourceDefinition,
  read: FreshnessMetadataRead<string>,
  queriedAt: string,
  warningMessage: string | null = null,
): DataFreshnessContract {
  if (source.sourceKind !== "operational") {
    throw new Error("Registered operational freshness requires an operational source");
  }
  return buildOperationalFreshness({
    sourceLabel: source.sourceLabel,
    sourceRelations: source.sourceRelations,
    populationLabel: source.populationLabel,
    queryStatus: read.queryStatus,
    queriedAt,
    latestIncludedExecutionAt: read.value,
    latestCanonicalPublishedAt: null,
    staleAfterSeconds: null,
    warningMessage,
  });
}
