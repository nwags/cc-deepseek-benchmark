import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { DataFreshnessNotice } from "../../../components/DataFreshnessNotice";
import { ArtifactEvidenceGuide } from "../../../components/ArtifactEvidenceGuide";
import { ArtifactTypeLabel } from "../../../components/ArtifactTypeInfo";
import { FailureTaxonomyDetails } from "../../../components/FailureTaxonomyDetails";
import { InvalidReason, ValidityBadge } from "../../../components/ValidityContext";
import { buildSuspectNoopHref } from "../../../components/QualityContext";
import {
  ArtifactDetailRow,
  InvalidArmRunRow,
  TrialEvidenceRow,
  getArtifactsForTrial,
  getTrialEvidence
} from "../../../lib/dashboard-data";
import { getTaskInstructionPreview } from "../../../lib/artifact-content";
import { deriveEvidenceCompleteness } from "../../../lib/artifact-types";
import { analyzeTrialArtifactsCached, changedAnalysisAxes } from "../../../lib/trial-analysis";
import { buildArtifactHref } from "../../../lib/links";
import { formatBytes, formatCurrency, formatNumber, formatSeconds } from "../../../lib/format";
import { sanitizeDisplayedUri, sanitizeEvidenceText } from "../../../lib/safe-display";
import { getComprehensiveTrialReview } from "../../../lib/review-data";
import { getFailureTaxonomyForTrial } from "../../../lib/failure-taxonomy-snapshot";
import { buildRegisteredOperationalFreshness } from "../../../lib/data-freshness-server";
import { DETAIL_ROUTE_FRESHNESS_SOURCES } from "../../../lib/data-freshness-sources";

export const dynamic = "force-dynamic";

type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;
const firstParam = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;
const snapshotBoolean = (value: string | undefined) => value === "True" || value === "true";

function compactPath(value: string | null | undefined) {
  if (!value) return "not recorded";
  const safeValue = sanitizeDisplayedUri(value) ?? "not recorded";
  const parts = safeValue.split("/");
  return parts.length <= 7 ? safeValue : `…/${parts.slice(-5).join("/")}`;
}

function safeDisplay(value: string | null | undefined) {
  return value ? sanitizeEvidenceText(value) ?? "not recorded" : "not recorded";
}

function recordedNumber(value: number | string | null | undefined) {
  return value === null || value === undefined || value === "" ? "not recorded" : formatNumber(value);
}

function recordedCurrency(value: number | string | null | undefined) {
  return value === null || value === undefined || value === "" ? "not recorded" : formatCurrency(value);
}

function invalidRowFromTrial(row: TrialEvidenceRow): InvalidArmRunRow | null {
  if (!row.invalid_reason || !row.suite_id || !row.arm_id) return null;
  return {
    suite_id: row.suite_id, arm_id: row.arm_id, run_label: row.run_label,
    provider_run_id: row.invalid_provider_run_id, reason: row.invalid_reason,
    invalidated_at: row.invalidated_at, invalidated_by: row.invalidated_by,
    raw_metadata: row.invalid_raw_metadata
  };
}

function trialQualityHref(row: TrialEvidenceRow) {
  return row.quality_flag === "suspect_noop_zero_token"
    ? buildSuspectNoopHref({ suite_id: row.suite_id, arm_id: row.arm_id, run_label: row.run_label, task_id: row.task_id })
    : "/trial-quality";
}

function firstArtifact(artifacts: ArtifactDetailRow[], artifactType: string) {
  return artifacts.find((artifact) => artifact.artifact_type === artifactType);
}

function artifactLink(artifact: ArtifactDetailRow | undefined, fallback = "not available") {
  return artifact ? <Link href={`/artifacts/${artifact.artifact_id}`}>{fallback === "not available" ? "View evidence" : fallback}</Link> : <span>{fallback}</span>;
}

const diagnosisLabels: Record<string, string> = {
  substantive: "substantive execution",
  invalid_response_path: "invalid response path",
  invalid_transport_or_setup: "invalid transport or setup",
  policy_blocked: "policy blocked",
  questionable: "questionable — review",
  unknown: "unknown",
  none_detected: "none detected",
  provider_policy_refusal: "provider-policy refusal",
  consistent: "consistent",
  database_missing_transcript_present: "database missing; transcript usage present",
  database_zero_transcript_nonzero: "database zero; transcript usage nonzero",
  nonzero_mismatch: "nonzero telemetry mismatch",
  zero_usage_empty_completion: "zero-usage empty completion",
  partial: "partially recorded telemetry",
  incomplete_evidence: "telemetry evidence incomplete",
  retained: "retained",
  not_retained: "not retained",
  substantive_agent_activity: "substantive agent activity",
  empty_completion_zero_usage: "empty completion — zero usage",
  empty_completion_after_long_api_path_wait: "empty completion after long API-path wait",
  thinking_only_empty_completion: "thinking-only empty completion",
  synthetic_retry_empty_completion: "synthetic-retry empty completion",
  setup_or_transport_exception: "setup or transport exception",
  timeout_after_meaningful_activity: "timeout after meaningful activity",
  telemetry_missing_activity_present: "activity present; telemetry missing",
  questionable_success_no_activity: "questionable success with no activity",
  activity_unknown: "activity unknown"
};

export default async function TrialEvidencePage({
  params, searchParams
}: {
  params: Promise<{ trialId: string }>;
  searchParams?: PageSearchParams;
}) {
  const { trialId } = await params;
  const decodedTrialId = decodeURIComponent(trialId);
  const trial = await getTrialEvidence(decodedTrialId);
  if (!trial) notFound();

  const [artifacts, taskInstruction, comprehensiveReview, failureTaxonomy] = await Promise.all([
    getArtifactsForTrial(decodedTrialId),
    getTaskInstructionPreview(trial.task_id),
    getComprehensiveTrialReview(decodedTrialId),
    getFailureTaxonomyForTrial(decodedTrialId),
  ]);
  const query = searchParams ? await searchParams : {};
  const liveRequested = firstParam(query.live_analysis) === "1";
  const liveAnalysis = !comprehensiveReview || liveRequested
    ? await analyzeTrialArtifactsCached(trial, artifacts) : null;
  const completeness = deriveEvidenceCompleteness(
    artifacts,
    "trial",
    Boolean(trial.exception_type || trial.exception_summary)
  );
  const invalidRow = invalidRowFromTrial(trial);
  const evidenceByType = new Map(artifacts.map((artifact) => [artifact.artifact_type, artifact]));
  const configuration = comprehensiveReview?.snapshot_configuration ?? liveAnalysis?.configuration ?? {
    task_repository: null, task_commit: null, task_checksum: null, task_path: null,
    model_alias: null, resolved_model: null, claude_code_version: null, router_endpoint: null,
    timeout_multipliers: null, disallowed_tools: null, verifier_configuration: null
  };
  const display = comprehensiveReview ? {
    raw_outcome: comprehensiveReview.raw_outcome,
    execution_validity: comprehensiveReview.execution_validity,
    activity_subtype: comprehensiveReview.activity_subtype,
    policy_disposition: comprehensiveReview.policy_disposition,
    failure_subtype: comprehensiveReview.failure_subtype,
    termination_subtype: comprehensiveReview.termination_subtype,
    telemetry_status: comprehensiveReview.telemetry_status,
    database_result_consistency: comprehensiveReview.database_result_consistency,
    router_observability: comprehensiveReview.router_observability,
    confidence: comprehensiveReview.classification_confidence,
    manual_review_required: snapshotBoolean(comprehensiveReview.manual_review_required),
    manual_review_priority: comprehensiveReview.manual_review_priority,
    evidence_complete: snapshotBoolean(comprehensiveReview.evidence_complete),
    analyzer_version: comprehensiveReview.analyzer_version,
    summary: comprehensiveReview.snapshot_summary ?? "Validated snapshot classification; open the supporting artifacts for manual confirmation.",
    evidence: comprehensiveReview.snapshot_evidence ?? [],
    result_reward_present: snapshotBoolean(comprehensiveReview.result_reward_present),
    result_reward_value: comprehensiveReview.result_reward_value,
    result_exception_present: snapshotBoolean(comprehensiveReview.result_exception_present),
    result_exception_type: comprehensiveReview.result_exception_type,
    result_termination_reason: comprehensiveReview.result_termination_reason,
    result_status: comprehensiveReview.result_status,
    database_exception_summary_present: snapshotBoolean(comprehensiveReview.database_exception_summary_present),
    database_exception_summary_trusted_markers: comprehensiveReview.database_exception_summary_trusted_markers
  } : liveAnalysis!;
  const liveDifferences = comprehensiveReview && liveAnalysis
    ? changedAnalysisAxes(comprehensiveReview, liveAnalysis)
    : [];
  const queriedAt = new Date().toISOString();
  const metadataFreshness = buildRegisteredOperationalFreshness(
    DETAIL_ROUTE_FRESHNESS_SOURCES.trialMetadata,
    { queryStatus: "available", value: trial.run_finished_at },
    queriedAt,
  );

  const readNext = [
    ["Start here: Harbor result", "result"],
    ["What the agent received and did: transcript", "agent_transcript"],
    ["Why the final workspace passed or failed: verifier stdout", "verifier_stdout"],
    ["Structured behavior: trajectory", "trajectory"],
    ["Audit configuration", "config"],
    ["Harness and infrastructure log", "log"],
    ["Explicit exception", "exception"],
    ["Structured test confirmation", "verifier_ctrf"],
    ["Raw reward confirmation", "verifier_reward"]
  ] as const;

  return (
    <AppShell title="Trial evidence" description="Derived diagnosis with transparent links to one task attempt's immutable evidence.">
      <DataFreshnessNotice freshness={metadataFreshness} />
      <section className="quality-context-panel" aria-label="Trial artifact-byte boundary">
        <p><strong>Artifact references:</strong> Supabase metadata lists {artifacts.length} related artifact row(s).</p>
        {liveAnalysis ? (
          <p>
            <strong>Artifact-byte analysis:</strong> bounded R2-first analysis was requested or used as fallback. This page does not assert complete per-object retrieval or integrity; open an artifact detail page for object-specific provenance.
          </p>
        ) : (
          <p>
            <strong>Artifact-byte retrieval:</strong> not performed by this render. The validated review snapshot is shown, and artifact links are metadata references until opened.
          </p>
        )}
        <p className="muted">An R2 URI or indexed artifact row does not prove that bytes were read or verified.</p>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{trial.trial_id}</h2>
            <p><Link href={buildArtifactHref({ run_label: trial.run_label, task_id: trial.task_id })}>Back to grouped artifacts</Link></p>
          </div>
          <ValidityBadge row={invalidRow} />
        </div>
        <div className="detail-grid">
          <div><span>Run</span><strong><Link href={`/runs/${encodeURIComponent(trial.run_label)}`}>{safeDisplay(trial.run_label)}</Link></strong></div>
          <div><span>Suite</span><strong className="mono">{safeDisplay(trial.suite_id)}</strong></div>
          <div><span>Arm</span><strong className="mono">{safeDisplay(trial.arm_id)}</strong></div>
          <div><span>Task</span><strong className="mono">{safeDisplay(trial.task_id)}</strong></div>
          <div><span>Task position</span><strong>Task {trial.task_ordinal ?? "?"} of {trial.run_task_count ?? "?"}</strong></div>
          <div><span>Task-local attempt</span><strong>Attempt {trial.task_attempt_number ?? "?"} of {trial.task_attempt_count ?? "?"}</strong></div>
          <div><span>Run trial number</span><strong>#{trial.run_trial_number ?? "not recorded"}</strong></div>
          <div><span>Stored quality flag</span><strong>{safeDisplay(trial.quality_flag)}</strong></div>
          <div><span>Reward</span><strong>{recordedNumber(trial.reward)}</strong></div>
          <div><span>Runtime</span><strong>{trial.runtime_seconds === null ? "not recorded" : formatSeconds(trial.runtime_seconds)}</strong></div>
          <div><span>Cost</span><strong>{recordedCurrency(trial.cost_usd)}</strong></div>
          <div><span>Input tokens</span><strong>{recordedNumber(trial.input_tokens)}</strong></div>
          <div><span>Cache tokens</span><strong>{recordedNumber(trial.cache_tokens)}</strong></div>
          <div><span>Output tokens</span><strong>{recordedNumber(trial.output_tokens)}</strong></div>
          <div><span>Result path</span><strong className="mono">{compactPath(trial.result_local_path)}</strong></div>
          <div><span>Result artifact URI</span><strong className="mono">{compactPath(trial.result_artifact_uri)}</strong></div>
        </div>
      </section>

      <FailureTaxonomyDetails result={failureTaxonomy} />

      <section className="panel diagnosis-panel">
        <div className="panel-heading">
          <div>
            <h2>Quick diagnosis <span className="derived-label">derived</span></h2>
            <p>{safeDisplay(display.summary)}</p>
          </div>
          <div className="evidence-group-badges"><span className="derived-label">{comprehensiveReview ? "validated snapshot" : "live fallback"}</span><span className={display.confidence === "high" ? "quality-badge" : "quality-badge quality-badge-warn"}>{display.confidence} confidence</span>{display.manual_review_required ? <span className="quality-badge quality-badge-warn">manual review required · {display.manual_review_priority}</span> : null}</div>
        </div>
        <div className="diagnosis-grid">
          <article><span>Raw outcome</span><strong>{display.raw_outcome}</strong><small>Database reward remains the source of truth.</small></article>
          <article><span>Execution validity</span><strong>{diagnosisLabels[display.execution_validity]}</strong><small>Derived independently from the raw outcome.</small></article>
          <article><span>Agent activity</span><strong>{diagnosisLabels[display.activity_subtype]}</strong><small>{liveAnalysis ? `${liveAnalysis.tool_calls} tools · ${liveAnalysis.workspace_changing_calls} workspace-changing · ${liveAnalysis.visible_assistant_events} visible assistant events` : "Counts are retained in the snapshot evidence notes; live artifact reads are optional."}</small></article>
          <article><span>Policy disposition</span><strong>{diagnosisLabels[display.policy_disposition]}</strong><small>Independent from transport/setup validity.</small></article>
          <article><span>Verifier failure subtype</span><strong>{display.failure_subtype === "none" ? "no verifier failure classified" : display.failure_subtype.replaceAll("_", " ")}</strong><small>Separate from how execution terminated.</small></article>
          <article><span>Termination / exception</span><strong>{display.termination_subtype.replaceAll("_", " ")}</strong><small>{display.result_exception_present ? `Harbor result exception: ${display.result_exception_type || "type not recorded"}` : "No result-side exception recorded."}</small></article>
          <article><span>Evidence completeness</span><strong>{completeness.canonical_present_count}/{completeness.canonical_expected_count} canonical</strong><small>{completeness.missing_types.length ? `Missing: ${completeness.missing_types.join(", ")}` : "Expected Harbor evidence present."}</small></article>
          {comprehensiveReview ? <article><span>R2 evidence</span><strong>{comprehensiveReview.r2_indexed_completeness} indexed</strong><small>Read {comprehensiveReview.r2_read_availability} · analyzed-artifact integrity {comprehensiveReview.analyzed_artifact_integrity_status} · size metadata {comprehensiveReview.size_metadata_status}</small></article> : null}
          <article><span>Database/result consistency</span><strong>{display.database_result_consistency.replaceAll("_", " ")}</strong><small>Result evidence never replaces the stored database reward.</small></article>
          <article><span>Telemetry</span><strong>{diagnosisLabels[display.telemetry_status]}</strong><small>Null is displayed as not recorded, never coerced to zero.</small></article>
          <article><span>Router observability</span><strong>{diagnosisLabels[display.router_observability]}</strong><small>Separate from canonical evidence completeness.</small></article>
        </div>
        <div className="diagnosis-evidence">
          <h3>Evidence supporting the derived diagnosis</h3>
          <dl>{display.evidence.map((item) => (
            <div key={item.label}>
              <dt>{safeDisplay(item.label)}</dt><dd>{safeDisplay(item.value)} {item.artifactId ? <Link href={`/artifacts/${item.artifactId}`}>{safeDisplay(item.artifactType ?? "artifact")} source</Link> : <span className="muted">source: {safeDisplay(item.source.replaceAll("_", " "))}</span>}</dd>
            </div>
          ))}</dl>
          <p><strong>Harbor result evidence:</strong> reward {display.result_reward_present ? display.result_reward_value ?? "recorded but non-numeric" : "not recorded"} · status {safeDisplay(display.result_status)} · termination {safeDisplay(display.result_termination_reason)}. Database reward remains authoritative.</p>
          {liveAnalysis?.verifier_failure_headline ? <p><strong>Live verifier headline:</strong> {safeDisplay(liveAnalysis.verifier_failure_headline)} {artifactLink(firstArtifact(artifacts, "verifier_stdout"), "source")}</p> : null}
          <p className="muted">Analyzer {display.analyzer_version} · evidence {display.evidence_complete ? "complete for this diagnosis" : "incomplete or ambiguous"}.</p>
          {comprehensiveReview ? <p className="muted"><Link href="/comprehensive-review">Open corpus review</Link> · {liveRequested ? <Link href={`/trials/${decodedTrialId}`}>Hide optional live reanalysis</Link> : <Link href={`/trials/${decodedTrialId}?live_analysis=1`}>Run optional cached live reanalysis</Link>}</p> : <p className="muted">No validated corpus snapshot covers this trial; showing bounded live fallback analysis.</p>}
          {liveDifferences.length ? <div className="evidence-warning"><strong>Snapshot/live difference:</strong> optional live reanalysis differs for {liveDifferences.join(", ")}. The validated snapshot remains primary until regeneration.</div> : null}
          <p className="muted">Thinking event counts may be used as metadata. Thinking and reasoning content is not parsed or displayed.</p>
        </div>
      </section>

      <ArtifactEvidenceGuide compact />

      <section className="panel">
        <div className="panel-heading"><div><h2>Read next</h2><p>Ordered evidence path for manual confirmation.</p></div></div>
        <ol className="read-next-list">
          {readNext.filter(([, type]) => type !== "exception" || evidenceByType.has("exception")).map(([label, type]) => {
            const artifact = evidenceByType.get(type);
            return <li key={type}><strong>{label}</strong>{artifact ? <Link href={`/artifacts/${artifact.artifact_id}`}>Open {type}</Link> : <span>not available</span>}</li>;
          })}
          {display.router_observability === "retained" ? (
            <li><strong>Router evidence</strong>{artifactLink(evidenceByType.get("router_log_slice") ?? evidenceByType.get("router_log"), "Open router evidence")}</li>
          ) : (
            <li><strong>Router evidence</strong><span>{display.router_observability === "not_retained" ? "not retained under the historical evidence contract" : "status unknown"}</span></li>
          )}
        </ol>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><h2>Configuration and comparability</h2><p>Available facts only; endpoint differences are context and not automatically fairness failures.</p></div>{artifactLink(firstArtifact(artifacts, "config"), "Config evidence")}</div>
        <div className="detail-grid">
          <div><span>Task repository</span><strong>{safeDisplay(configuration.task_repository)}</strong></div>
          <div><span>Task commit</span><strong className="mono">{safeDisplay(configuration.task_commit)}</strong></div>
          <div><span>Task checksum</span><strong className="mono">{safeDisplay(configuration.task_checksum)}</strong></div>
          <div><span>Task path</span><strong className="mono">{safeDisplay(configuration.task_path)}</strong></div>
          <div><span>Model alias</span><strong className="mono">{safeDisplay(configuration.model_alias ?? trial.router_model ?? trial.arm_id)}</strong></div>
          <div><span>Resolved model</span><strong className="mono">{safeDisplay(trial.backend_model ?? configuration.resolved_model)}</strong></div>
          <div><span>Provider family</span><strong>{safeDisplay(trial.provider_family)}</strong></div>
          <div><span>Claude Code version</span><strong>{safeDisplay(configuration.claude_code_version)}</strong></div>
          <div><span>Router endpoint/deployment</span><strong className="mono">{safeDisplay(configuration.router_endpoint)}</strong></div>
          <div><span>Timeout multipliers</span><strong>{safeDisplay(configuration.timeout_multipliers)}</strong></div>
          <div><span>Disallowed tools</span><strong>{safeDisplay(configuration.disallowed_tools)}</strong></div>
          <div><span>Verifier</span><strong>{safeDisplay(configuration.verifier_configuration)}</strong></div>
          <div><span>Run timestamp</span><strong>{safeDisplay(trial.run_started_at)}</strong></div>
        </div>
        <div className="placeholder-body">Authentication tokens, API keys, credential values, and secret environment variables are never included in this summary.</div>
      </section>

      {invalidRow ? <section className="panel warning-panel"><div className="panel-heading"><div><h2>Invalid / quarantined context</h2><p><InvalidReason row={invalidRow} /></p></div><ValidityBadge row={invalidRow} /></div></section> : null}

      <section className="panel">
        <div className="panel-heading"><div><h2>Evidence links</h2><p>Move between the run, task, quality audit, and grouped evidence.</p></div></div>
        <div className="artifact-link-bar">
          <Link href={`/runs/${encodeURIComponent(trial.run_label)}`}>Run detail</Link><Link href={trialQualityHref(trial)}>Trial Quality</Link>
          {trial.task_id ? <Link href={`/evals/${encodeURIComponent(trial.task_id)}`}>Eval task</Link> : null}
          <Link href={buildArtifactHref({ run_label: trial.run_label, task_id: trial.task_id, quality_flag: trial.quality_flag })}>Artifact browser</Link>
        </div>
      </section>

      {trial.exception_type || trial.exception_summary ? <section className="panel warning-panel"><div className="panel-heading"><div><h2>Exception context</h2><p>{safeDisplay(trial.exception_type ?? "exception")}</p></div>{artifactLink(firstArtifact(artifacts, "exception"), "Exception evidence")}</div><div className="placeholder-body">{safeDisplay(trial.exception_summary)}</div></section> : null}

      <section className="panel">
        <div className="panel-heading"><div><h2>Related artifacts</h2><p>{completeness.canonical_present_count}/{completeness.canonical_expected_count} canonical present · {completeness.r2_indexed_count}/{completeness.canonical_expected_count} R2 indexed · router {completeness.router_observability.replace("_", " ")}.</p></div></div>
        {completeness.exception_metadata_without_artifact ? <div className="evidence-warning">Exception metadata is recorded, but no exception artifact is attached.</div> : null}
        {artifacts.length === 0 ? <div className="placeholder-body">No artifact rows are attached to this trial.</div> : (
          <div className="table-wrap"><table><thead><tr><th>Artifact</th><th>Full path</th><th>Storage</th><th>Size</th><th>Preview</th></tr></thead><tbody>
            {artifacts.map((artifact) => { const path = safeDisplay(artifact.local_path ?? artifact.r2_uri ?? artifact.artifact_id); return <tr key={artifact.artifact_id}><td><ArtifactTypeLabel artifactType={artifact.artifact_type} /></td><td><details className="path-details"><summary>{path.split("/").at(-1)}</summary><div className="mono">{safeDisplay(artifact.local_path)}</div>{artifact.r2_uri ? <div className="mono">{safeDisplay(artifact.r2_uri)}</div> : null}</details></td><td>{artifact.r2_uri ? "R2 indexed" : "not R2 indexed"}</td><td>{formatBytes(artifact.size_bytes)}</td><td><Link href={`/artifacts/${artifact.artifact_id}`}>View artifact</Link></td></tr>; })}
          </tbody></table></div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading"><div><h2>Task text</h2><p>{safeDisplay(taskInstruction.message)}</p></div>{taskInstruction.path ? <span className="mono">{safeDisplay(taskInstruction.path)}</span> : null}</div>
        {taskInstruction.text ? <pre className="content-preview content-preview-compact">{safeDisplay(taskInstruction.text)}</pre> : <div className="placeholder-body">No task instruction text is available in this dashboard context.</div>}
      </section>
    </AppShell>
  );
}
