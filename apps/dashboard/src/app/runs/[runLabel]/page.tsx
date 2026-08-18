import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { DataFreshnessNotice } from "../../../components/DataFreshnessNotice";
import { EvidenceSourceContextNotice } from "../../../components/EvidenceSourceContextNotice";
import { MetricCard } from "../../../components/MetricCard";
import { QualityBadge, QualityPassRate, buildSuspectNoopHref } from "../../../components/QualityContext";
import { InvalidReason, ValidityBadge, invalidCategory, validityLabel } from "../../../components/ValidityContext";
import { buildArtifactHref } from "../../../lib/links";
import {
  getArmRunQualityByRunLabels,
  getInvalidArmRunRowsByRunLabels,
  getRunArtifacts,
  getRunDetailResolution,
  getRunTrials
} from "../../../lib/dashboard-data";
import { buildRegisteredOperationalFreshness } from "../../../lib/data-freshness-server";
import { DETAIL_ROUTE_FRESHNESS_SOURCES } from "../../../lib/data-freshness-sources";
import {
  formatBytes,
  formatRecordedCost, formatCurrency,
  formatNumber,
  formatPercent,
  formatSeconds
} from "../../../lib/format";
import { redactSecretsInText, sanitizeDisplayedUri } from "../../../lib/safe-display";

export const dynamic = "force-dynamic";

const safeText = (value: string | null | undefined, fallback = "—") => value ? redactSecretsInText(value) : fallback;

function compactArtifactPath(value: string): string {
  const safeValue = sanitizeDisplayedUri(value) ?? "—";
  const parts = safeValue.split("/");
  if (parts.length <= 7) {
    return safeValue;
  }

  return `…/${parts.slice(-5).join("/")}`;
}

export default async function RunDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ runLabel: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { runLabel } = await params;
  const query = searchParams ? await searchParams : {};
  const decodedRunLabel = decodeURIComponent(runLabel);
  const resolution = await getRunDetailResolution(decodedRunLabel);

  if (resolution.status === "not_found") {
    notFound();
  }

  if (resolution.status === "ambiguous") {
    const queriedAt = new Date().toISOString();
    const freshness = buildRegisteredOperationalFreshness(
      DETAIL_ROUTE_FRESHNESS_SOURCES.runDetail,
      { queryStatus: "available", value: null },
      queriedAt,
      `The run label matches ${resolution.matches.length} Phase 3 records across run modes. Exact run identity is ambiguous, so no record or execution timestamp was selected.`,
    );
    return (
      <AppShell title="Run identity ambiguous" description="The requested run label does not identify exactly one Phase 3 database row.">
        <EvidenceSourceContextNotice value={query.source_scope} />
        <DataFreshnessNotice freshness={freshness} />
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Multiple Phase 3 runs share this label</h2>
              <p>No latest row or alternate phase/mode was selected. This bare-label route cannot render one record without a stronger identity.</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Run label</th><th>Mode</th><th>Run id</th><th>Finished</th></tr></thead>
              <tbody>{resolution.matches.map((match) => (
                <tr key={match.run_id}>
                  <td className="mono">{safeText(match.run_label)}</td>
                  <td>{safeText(match.mode)}</td>
                  <td className="mono">{match.run_id}</td>
                  <td>{match.finished_at ?? "Unavailable"}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      </AppShell>
    );
  }

  const run = resolution.run;

  const [trials, artifacts, qualityRows, invalidRows] = await Promise.all([
    getRunTrials(run.run_id),
    getRunArtifacts(run.run_id),
    getArmRunQualityByRunLabels([run.run_label]),
    getInvalidArmRunRowsByRunLabels([run.run_label])
  ]);
  const quality = qualityRows[0] ?? null;
  const invalidRow = invalidRows[0] ?? null;
  const suspectNoopCount = quality?.suspect_noop_count ?? 0;
  const queriedAt = new Date().toISOString();
  const freshness = buildRegisteredOperationalFreshness(
    DETAIL_ROUTE_FRESHNESS_SOURCES.runDetail,
    { queryStatus: "available", value: run.finished_at },
    queriedAt,
  );

  return (
    <AppShell title="Run detail">
      <EvidenceSourceContextNotice value={query.source_scope} />
      <DataFreshnessNotice freshness={freshness} />
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2 className="mono">{safeText(run.run_label)}</h2>
            <p>
              <Link href="/runs">← Back to runs</Link>
            </p>
          </div>
          <span className={`status status-${run.status}`}>{run.status}</span>
        </div>

        <div className="metric-grid">
          <MetricCard label="Trials" value={formatNumber(run.trial_count)} />
          <MetricCard label="Raw pass rate" value={formatPercent(run.pass_rate)} />
          <MetricCard label="Qualified pass rate" value={formatPercent(quality?.qualified_pass_rate ?? run.pass_rate)} />
          <MetricCard
            label="Suspect no-op"
            value={suspectNoopCount > 0 ? (
              <Link href={buildSuspectNoopHref({ run_label: run.run_label })}>
                <QualityBadge count={suspectNoopCount} />
              </Link>
            ) : (
              <QualityBadge count={suspectNoopCount} />
            )}
          />
          <MetricCard label="Cost" value={formatRecordedCost(run.trial_cost_usd, run.cost_row_count, run.missing_cost_count)} />
          <MetricCard label="Median runtime" value={formatSeconds(run.median_runtime_seconds)} />
          <MetricCard label="Artifacts in R2" value={`${formatNumber(run.r2_artifact_count)} / ${formatNumber(run.artifact_count)}`} />
          <MetricCard label="Audit events" value={formatNumber(run.audit_count)} />
        </div>
        <div className="placeholder-body">
          Suspect no-op drilldown opens the affected zero-token trials in Trial Quality.
        </div>
      </section>

      {invalidRow ? (
        <section className="panel warning-panel">
          <div className="panel-heading">
            <div>
              <h2>Invalid / quarantined run</h2>
              <p>This run is retained for audit but excluded from valid-only scored comparisons.</p>
            </div>
            <ValidityBadge row={invalidRow} />
          </div>
          <div className="detail-grid">
            <div><span>Validity</span><strong>{validityLabel(invalidRow)}</strong></div>
            <div><span>Category</span><strong>{invalidCategory(invalidRow) ?? "—"}</strong></div>
            <div><span>Provider/workflow id</span><strong className="mono">{safeText(invalidRow.provider_run_id)}</strong></div>
            <div><span>Reason</span><strong><InvalidReason row={invalidRow} includeProvider={false} /></strong></div>
            <div><span>Invalidated by</span><strong>{safeText(invalidRow.invalidated_by)}</strong></div>
            <div><span>Invalidated at</span><strong>{invalidRow.invalidated_at ?? "—"}</strong></div>
          </div>
        </section>
      ) : (
        <section className="quality-context-panel">
          <strong>Validity:</strong> <ValidityBadge row={invalidRow} />
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <h2>Run metadata</h2>
          <p>Branch, commit, runner, timing, tokens, and contamination counters.</p>
        </div>

        <div className="detail-grid">
          <div><span>Phase</span><strong>{run.phase}</strong></div>
          <div><span>Arm</span><strong className="mono">{quality?.arm_id ?? "—"}</strong></div>
          <div><span>Logical mode</span><strong>{quality?.logical_mode ?? run.mode}</strong></div>
          <div><span>Storage mode</span><strong>{quality?.storage_mode ?? run.mode}</strong></div>
          <div><span>Suite</span><strong className="mono">{quality?.suite_id ?? "—"}</strong></div>
          <div><span>Branch</span><strong>{safeText(run.branch)}</strong></div>
          <div><span>Git commit</span><strong className="mono">{run.git_commit ?? "—"}</strong></div>
          <div><span>Runner</span><strong>{safeText(run.runner_name)}</strong></div>
          <div><span>Runner provider</span><strong>{safeText(run.runner_provider)}</strong></div>
          <div><span>Started</span><strong>{run.started_at ?? "—"}</strong></div>
          <div><span>Finished</span><strong>{run.finished_at ?? "—"}</strong></div>
          <div><span>Input tokens</span><strong>{formatNumber(run.input_tokens)}</strong></div>
          <div><span>Cache tokens</span><strong>{formatNumber(run.cache_tokens)}</strong></div>
          <div><span>Output tokens</span><strong>{formatNumber(run.output_tokens)}</strong></div>
          <div><span>Qualified pass</span><strong><QualityPassRate row={quality ?? {
            raw_pass_rate: run.pass_rate,
            trial_count: run.trial_count,
            success_count: Math.round((run.pass_rate ?? 0) * (run.trial_count ?? 0)),
            qualified_pass_rate: run.pass_rate,
            qualified_trial_count: run.trial_count,
            qualified_success_count: Math.round((run.pass_rate ?? 0) * (run.trial_count ?? 0)),
            suspect_noop_count: 0
          }} /></strong></div>
          <div>
            <span>Suspect no-op</span>
            <strong>
              {suspectNoopCount > 0 ? (
                <Link href={buildSuspectNoopHref({ run_label: run.run_label })}>
                  <QualityBadge count={suspectNoopCount} />
                </Link>
              ) : (
                <QualityBadge count={suspectNoopCount} />
              )}
            </strong>
          </div>
          <div><span>Artifact bytes</span><strong>{formatBytes(run.artifact_size_bytes)}</strong></div>
          <div><span>WebSearch events</span><strong>{formatNumber(run.websearch_events)}</strong></div>
          <div><span>WebFetch events</span><strong>{formatNumber(run.webfetch_events)}</strong></div>
          <div><span>Forbidden tools available</span><strong>{formatNumber(run.forbidden_tools_available)}</strong></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Trials</h2>
          <p>Task-level trial rows imported for this run.</p>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Attempt</th>
                <th>Arm</th>
                <th>Reward</th>
                <th>Runtime</th>
                <th>Cost</th>
                <th>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {trials.map((trial) => (
                <tr key={trial.trial_id}>
                  <td className="mono">{safeText(trial.task_id)}</td>
                  <td>Attempt {trial.task_attempt} <span className="muted">(run #{trial.run_trial_ordinal ?? "not recorded"})</span></td>
                  <td className="mono">{safeText(trial.arm_id)}</td>
                  <td>{trial.reward ?? "—"}</td>
                  <td>{formatSeconds(trial.runtime_seconds)}</td>
                  <td>{formatCurrency(trial.cost_usd)}</td>
                  <td>
                    {formatNumber(trial.input_tokens ?? 0)} in / {formatNumber(trial.output_tokens ?? 0)} out
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Artifacts</h2>
            <p>First 100 artifact records. Signed download links will come in a later pass.</p>
          </div>
          <div className="artifact-link-list">
            <Link href={buildArtifactHref({ run_label: run.run_label })}>Open in artifact browser</Link>
            {suspectNoopCount > 0 ? (
              <Link href={buildArtifactHref({ run_label: run.run_label, quality_flag: "suspect_noop_zero_token" })}>
                Suspect no-op artifacts
              </Link>
            ) : null}
          </div>
        </div>

        <div className="artifact-list">
          {artifacts.map((artifact) => (
            <article className="artifact-card" key={artifact.artifact_path}>
              <div className="artifact-path mono" title={sanitizeDisplayedUri(artifact.artifact_path) ?? undefined}>
                {compactArtifactPath(artifact.artifact_path)}
              </div>
              <div className="artifact-meta">
                <span>{safeText(artifact.artifact_kind, "unknown")}</span>
                <span>{formatBytes(artifact.size_bytes)}</span>
                <span>{artifact.r2_uri ? "R2 indexed" : "local only"}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
