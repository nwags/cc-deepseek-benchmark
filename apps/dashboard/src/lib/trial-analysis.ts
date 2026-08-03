import type { ArtifactDetailRow, TrialEvidenceRow } from "./dashboard-data";
import { readArtifactForAnalysis } from "./artifact-content";
import { deriveEvidenceCompleteness } from "./artifact-types";
import {
  ArtifactTextInput,
  TrialAnalysis,
  classifyTrialEvidence
} from "./trial-analysis-core";

const analysisArtifactTypes = new Set([
  "result", "agent_transcript", "trajectory", "verifier_stdout", "verifier_ctrf", "exception", "config"
]);
// Two configurable structured reads are each absolutely capped at 32 MiB by
// artifact-content; the five supporting reads add at most 7 MiB. This is the
// hard per-trial ceiling even under the largest supported override.
export const MAX_TRIAL_ANALYSIS_BYTES = 71 * 1024 * 1024;
const liveAnalysisCache = new Map<string, Promise<TrialAnalysis>>();
const MAX_LIVE_ANALYSIS_CACHE_ENTRIES = 100;
const comparisonAxes = [
  "raw_outcome", "execution_validity", "activity_subtype", "policy_disposition",
  "failure_subtype", "termination_subtype", "telemetry_status"
] as const;

export function changedAnalysisAxes(
  snapshot: Record<string, unknown>,
  live: Record<string, unknown>
) {
  return comparisonAxes.filter((field) => String(snapshot[field] ?? "") !== String(live[field] ?? ""));
}

export function liveAnalysisKey(trial: TrialEvidenceRow, artifacts: ArtifactDetailRow[]) {
  return JSON.stringify([
    trial.trial_id, trial.reward, trial.exception_type, trial.exception_summary, trial.input_tokens, trial.cache_tokens, trial.output_tokens, trial.cost_usd,
    artifacts.map((artifact) => [artifact.artifact_id, artifact.sha256, artifact.size_bytes, artifact.r2_uri]).sort()
  ]);
}

export function analyzeTrialArtifactsCached(trial: TrialEvidenceRow, artifacts: ArtifactDetailRow[]) {
  const key = liveAnalysisKey(trial, artifacts);
  const existing = liveAnalysisCache.get(key);
  if (existing) return existing;
  const pending = analyzeTrialArtifacts(trial, artifacts).catch((error) => {
    liveAnalysisCache.delete(key);
    throw error;
  });
  liveAnalysisCache.set(key, pending);
  if (liveAnalysisCache.size > MAX_LIVE_ANALYSIS_CACHE_ENTRIES) {
    const oldest = liveAnalysisCache.keys().next().value;
    if (oldest) liveAnalysisCache.delete(oldest);
  }
  return pending;
}

export async function analyzeTrialArtifacts(
  trial: TrialEvidenceRow,
  artifacts: ArtifactDetailRow[]
): Promise<TrialAnalysis> {
  const candidates = artifacts
    .filter((artifact) => analysisArtifactTypes.has(artifact.artifact_type ?? ""))
    .sort((left, right) => {
      const typeOrder = String(left.artifact_type).localeCompare(String(right.artifact_type));
      if (typeOrder !== 0) return typeOrder;
      const storageOrder = Number(Boolean(right.r2_uri)) - Number(Boolean(left.r2_uri));
      if (storageOrder !== 0) return storageOrder;
      const createdOrder = String(right.created_at ?? "").localeCompare(String(left.created_at ?? ""));
      return createdOrder || left.artifact_id.localeCompare(right.artifact_id);
    });
  const duplicateTypes = new Set<string>();
  const selectedByType = new Map<string, ArtifactDetailRow>();
  for (const artifact of candidates) {
    const artifactType = artifact.artifact_type ?? "unknown";
    if (selectedByType.has(artifactType)) {
      duplicateTypes.add(artifactType);
      continue;
    }
    selectedByType.set(artifactType, artifact);
  }
  const selected = [...selectedByType.values()].slice(0, analysisArtifactTypes.size);
  const previews = await Promise.all(selected.map(async (artifact): Promise<ArtifactTextInput> => {
    const preview = await readArtifactForAnalysis(artifact);
    return {
      artifactType: artifact.artifact_type ?? "unknown",
      artifactId: artifact.artifact_id,
      text: preview.text,
      available: preview.available,
      truncated: preview.truncated,
      malformed: preview.completeness === "malformed",
      completeness: preview.completeness,
      bytesRead: preview.bytes_read,
      totalBytes: preview.total_bytes
    };
  }));
  const completeness = deriveEvidenceCompleteness(
    artifacts,
    "trial",
    Boolean(trial.exception_type || trial.exception_summary)
  );
  return classifyTrialEvidence({
    reward: trial.reward,
    runtimeSeconds: trial.runtime_seconds,
    exceptionType: trial.exception_type,
    databaseExceptionSummary: trial.exception_summary,
    databaseInputTokens: trial.input_tokens,
    databaseCacheTokens: trial.cache_tokens,
    databaseOutputTokens: trial.output_tokens,
    databaseCostUsd: trial.cost_usd,
    artifacts: previews,
    routerObservability: completeness.router_observability,
    canonicalEvidenceComplete: completeness.canonical_present_count === completeness.canonical_expected_count,
    artifactSelectionAmbiguous: duplicateTypes.size > 0
  });
}
