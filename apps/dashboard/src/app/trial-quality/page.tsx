import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { DataFreshnessNotice } from "../../components/DataFreshnessNotice";
import { FailureTaxonomyCompactDiagnosis } from "../../components/FailureTaxonomyDetails";
import { TermInfo } from "../../components/TermInfo";
import { QualityBadge, buildSuspectNoopHref } from "../../components/QualityContext";
import { InvalidReason, ValidityBadge, invalidCategory } from "../../components/ValidityContext";
import { buildArtifactHref } from "../../lib/links";
import { redactSecretsInText } from "../../lib/safe-display";
import {
  deduplicateDisplayedArmRunFreshnessIdentities,
  getArmRunQualitySummaryRows,
  getDisplayedArmRunFreshnessResolution,
  getInvalidArmRunRows,
  getSuspectNoopTrialRowsFiltered,
  SuspectNoopTrialFilters
} from "../../lib/dashboard-data";
import { INDEX_ROUTE_FRESHNESS_SOURCES } from "../../lib/data-freshness-sources";
import {
  FAILURE_TAXONOMY_REGISTRY,
  getFailureTaxonomyAxis,
  type FailureTaxonomyAxisId,
} from "../../lib/failure-taxonomy";
import {
  FAILURE_TAXONOMY_AXIS_IDS,
  filterFailureTaxonomyRows,
  getFailureTaxonomySnapshot,
  normalizeFailureTaxonomyFilters,
  type FailureTaxonomyFilters,
} from "../../lib/failure-taxonomy-snapshot";
import {
  armRunFreshnessCoverageWarning,
  buildRegisteredOperationalFreshness,
  readFreshnessMetadata,
} from "../../lib/data-freshness-server";

export const dynamic = "force-dynamic";

function pct(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function money(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return `$${Number(value).toFixed(2)}`;
}

function modeLabel(logicalMode: string | null, storageMode: string | null) {
  if (!logicalMode && !storageMode) return "—";
  if (logicalMode === storageMode || !storageMode) return logicalMode ?? storageMode;
  return `${logicalMode} / ${storageMode}`;
}

type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;

function firstParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) return value[0];
  return value;
}

function cleanParam(value: string | string[] | undefined) {
  const text = firstParam(value)?.trim();
  return text || undefined;
}

function formatFilterValue(key: string, value: string) {
  return `${key}=${value}`;
}

const TAXONOMY_PAGE_SIZES = [25, 50, 100] as const;

function positiveInteger(value: string | undefined, fallback: number) {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function taxonomyPageHref(filters: FailureTaxonomyFilters, page: number, pageSize: number) {
  const query = new URLSearchParams();
  for (const axisId of FAILURE_TAXONOMY_AXIS_IDS) {
    if (filters[axisId]) query.set(axisId, filters[axisId]!);
  }
  query.set("taxonomy_page", String(page));
  query.set("taxonomy_page_size", String(pageSize));
  return `/trial-quality?${query.toString()}#failure-taxonomy`;
}

export default async function TrialQualityPage({
  searchParams
}: {
  searchParams?: PageSearchParams;
}) {
  const params = searchParams ? await searchParams : {};
  const rawTaxonomyFilters = Object.fromEntries(FAILURE_TAXONOMY_AXIS_IDS.map((axisId) => [
    axisId,
    cleanParam(params[axisId]),
  ])) as Partial<Record<FailureTaxonomyAxisId, string | undefined>>;
  const taxonomyFilters = normalizeFailureTaxonomyFilters(rawTaxonomyFilters);
  const invalidTaxonomyFilters = FAILURE_TAXONOMY_AXIS_IDS.filter((axisId) =>
    rawTaxonomyFilters[axisId] && !taxonomyFilters[axisId]);
  const requestedTaxonomyPageSize = positiveInteger(cleanParam(params.taxonomy_page_size), 25);
  const taxonomyPageSize = TAXONOMY_PAGE_SIZES.includes(requestedTaxonomyPageSize as 25 | 50 | 100)
    ? requestedTaxonomyPageSize : 25;
  const requestedTaxonomyPage = positiveInteger(cleanParam(params.taxonomy_page), 1);
  const quality = cleanParam(params.quality);
  const suspectFilters: SuspectNoopTrialFilters = {
    suite_id: cleanParam(params.suite_id),
    arm_id: cleanParam(params.arm_id),
    run_label: cleanParam(params.run_label),
    task_id: cleanParam(params.task_id)
  };
  const activeFilterEntries: Array<[string, string]> = [];
  if (quality === "suspect_noop_zero_token") activeFilterEntries.push(["quality", quality]);
  if (suspectFilters.suite_id) activeFilterEntries.push(["suite_id", suspectFilters.suite_id]);
  if (suspectFilters.arm_id) activeFilterEntries.push(["arm_id", suspectFilters.arm_id]);
  if (suspectFilters.run_label) activeFilterEntries.push(["run_label", suspectFilters.run_label]);
  if (suspectFilters.task_id) activeFilterEntries.push(["task_id", suspectFilters.task_id]);

  const [summaries, suspectTrials, invalidRows, taxonomySnapshot] = await Promise.all([
    getArmRunQualitySummaryRows(120),
    getSuspectNoopTrialRowsFiltered(suspectFilters, 120),
    getInvalidArmRunRows(),
    getFailureTaxonomySnapshot(),
  ]);
  const matchingTaxonomyRows = taxonomySnapshot.available
    ? filterFailureTaxonomyRows(taxonomySnapshot.rows, taxonomyFilters) : [];
  const taxonomyPageCount = Math.max(1, Math.ceil(matchingTaxonomyRows.length / taxonomyPageSize));
  const taxonomyPage = Math.min(requestedTaxonomyPage, taxonomyPageCount);
  const taxonomyPageRows = matchingTaxonomyRows.slice(
    (taxonomyPage - 1) * taxonomyPageSize,
    taxonomyPage * taxonomyPageSize,
  );
  const displayedArmRunIdentities = deduplicateDisplayedArmRunFreshnessIdentities([
    ...summaries.map((row) => ({
      suite_id: row.suite_id,
      arm_id: row.arm_id,
      run_label: row.run_label,
    })),
    ...suspectTrials.map((row) => ({
      suite_id: row.suite_id,
      arm_id: row.arm_id,
      run_label: row.run_label,
    })),
    ...invalidRows.map((row) => ({
      suite_id: row.suite_id,
      arm_id: row.arm_id,
      run_label: row.run_label,
    })),
  ]);
  const freshnessRead = await readFreshnessMetadata(
    () => getDisplayedArmRunFreshnessResolution(displayedArmRunIdentities),
  );
  const freshness = buildRegisteredOperationalFreshness(
    INDEX_ROUTE_FRESHNESS_SOURCES.trialQuality,
    {
      queryStatus: freshnessRead.queryStatus,
      value: freshnessRead.value?.latestIncludedExecutionAt ?? null,
    },
    new Date().toISOString(),
    freshnessRead.value ? armRunFreshnessCoverageWarning(freshnessRead.value) : null,
  );

  const invalidByRun = new Map(invalidRows.map((row) => [row.run_label, row]));
  const totalSuspect = summaries.reduce((acc, row) => acc + Number(row.suspect_noop_count ?? 0), 0);
  const affectedRuns = summaries.filter((row) => Number(row.suspect_noop_count ?? 0) > 0).length;
  const affectedFullRuns = summaries.filter(
    (row) => row.logical_mode === "full" && Number(row.suspect_noop_count ?? 0) > 0
  ).length;

  return (
    <AppShell
      eyebrow="Benchmark interpretation layer"
      title="Trial quality"
      description="Raw benchmark outcomes remain the source of truth. This page adds diagnostic flags so no-op exits, exceptions, and normal failures are not interpreted as the same kind of model behavior."
    >

      <section className="panel warning-panel">
        <div className="panel-heading">
          <div>
            <h2>Validity and provenance</h2>
            <p>
              Raw benchmark outcomes are preserved. Primary full-suite comparison views are valid-only.
              The audit tables on this page include imported runs, including invalid/quarantined runs.
              Invalid/quarantined runs are excluded from scored comparisons but retained for diagnosis.
            </p>
          </div>
        </div>
      </section>
      <DataFreshnessNotice freshness={freshness} />

      <section className="panel taxonomy-list-panel" id="failure-taxonomy" aria-labelledby="failure-taxonomy-heading">
        <div className="panel-heading">
          <div>
            <h2 id="failure-taxonomy-heading">Frozen failure and trajectory taxonomy <span className="derived-label">derived</span></h2>
            <p>
              Four independent J2 axes derived offline from the manifest-bound 960-trial reviewed Phase 3 extended corpus.
              Raw outcome and historical quality fields remain unchanged.
            </p>
          </div>
          {taxonomySnapshot.available ? <span className="quality-badge">manifest verified</span> : <span className="quality-badge quality-badge-warn">unavailable</span>}
        </div>
        {taxonomySnapshot.available && taxonomySnapshot.provenance ? (
          <>
            <div className="taxonomy-provenance" aria-label="Failure taxonomy snapshot provenance">
              <strong>{taxonomySnapshot.provenance.snapshotId}</strong>
              <span>{taxonomySnapshot.provenance.scope}</span>
              <span>{taxonomySnapshot.provenance.trialCount} exact trial IDs</span>
              <span>{taxonomySnapshot.provenance.reviewQueueCount} review-queue trials</span>
              <span>taxonomy {taxonomySnapshot.provenance.taxonomyVersion}</span>
              <span>classifier {taxonomySnapshot.provenance.classifierVersion}</span>
              <span>source review {taxonomySnapshot.provenance.sourceGeneratedAt}</span>
              <span>scope fingerprint <code>{taxonomySnapshot.provenance.scopeFingerprint}</code></span>
            </div>
            <form className="filter-grid taxonomy-filter-grid" method="get" action="/trial-quality#failure-taxonomy">
              {FAILURE_TAXONOMY_AXIS_IDS.map((axisId) => {
                const axis = getFailureTaxonomyAxis(axisId);
                return (
                  <label key={axisId}>
                    {axis.label}
                    <select name={axisId} defaultValue={taxonomyFilters[axisId] ?? ""}>
                      <option value="">All values</option>
                      {axis.entries.map((entry) => <option key={entry.id} value={entry.id}>{entry.label}</option>)}
                    </select>
                  </label>
                );
              })}
              <label>
                Rows per page
                <select name="taxonomy_page_size" defaultValue={String(taxonomyPageSize)}>
                  {TAXONOMY_PAGE_SIZES.map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <div className="filter-actions">
                <button type="submit">Apply exact filters</button>
                <Link href="/trial-quality#failure-taxonomy">Clear</Link>
              </div>
            </form>
            {invalidTaxonomyFilters.length ? (
              <div className="evidence-warning">
                Ignored unsupported taxonomy filter value(s) for: {invalidTaxonomyFilters.map((axisId) => getFailureTaxonomyAxis(axisId).label).join(", ")}.
                Filters accept only canonical registry IDs.
              </div>
            ) : null}
            <details className="taxonomy-help">
              <summary>Axis definitions and filter help</summary>
              <div className="taxonomy-help-grid">
                {FAILURE_TAXONOMY_REGISTRY.axes.map((axis) => (
                  <article key={axis.id}>
                    <h3>{axis.label}</h3>
                    <p>{axis.definition}</p>
                    <dl>{axis.entries.map((entry) => <div key={entry.id}><dt>{entry.label}</dt><dd>{entry.definition}</dd></div>)}</dl>
                  </article>
                ))}
              </div>
            </details>
            <p className="taxonomy-result-summary">
              Showing {taxonomyPageRows.length} of {matchingTaxonomyRows.length} matching frozen trials. Taxonomy values are exact registry values; “Not applicable” is a diagnosis, while trials outside this snapshot have a separate unavailable state.
            </p>
            <div className="table-wrap">
              <table className="taxonomy-table">
                <thead><tr><th>Trial</th><th>Raw outcome</th><th>Response path</th><th>Verifier failure</th><th>Assertion failure</th><th>Trajectory</th><th>Review</th></tr></thead>
                <tbody>
                  {taxonomyPageRows.length ? taxonomyPageRows.map((row) => {
                    const reviewRequired = FAILURE_TAXONOMY_AXIS_IDS.some((axisId) => row[axisId].manual_review_required);
                    return (
                      <tr key={row.trial_id}>
                        <td>
                          <Link className="mono" href={`/trials/${encodeURIComponent(row.trial_id)}#failure-taxonomy`}>{row.trial_id}</Link>
                          <div className="muted mono">{row.arm_id}</div>
                          <div className="muted mono">{row.task_id}</div>
                        </td>
                        <td>{row.raw_outcome}</td>
                        {FAILURE_TAXONOMY_AXIS_IDS.map((axisId) => <td key={axisId}><FailureTaxonomyCompactDiagnosis axisId={axisId} diagnosis={row[axisId]} /></td>)}
                        <td>{reviewRequired ? <span className="quality-badge quality-badge-warn">required</span> : <span className="muted">not required</span>}</td>
                      </tr>
                    );
                  }) : <tr><td colSpan={7}>No frozen taxonomy trials match these exact filters.</td></tr>}
                </tbody>
              </table>
            </div>
            <nav className="pagination" aria-label="Failure taxonomy pagination">
              {taxonomyPage > 1 ? <Link href={taxonomyPageHref(taxonomyFilters, taxonomyPage - 1, taxonomyPageSize)}>Previous</Link> : <span>Previous</span>}
              <span>Page {taxonomyPage} of {taxonomyPageCount}</span>
              {taxonomyPage < taxonomyPageCount ? <Link href={taxonomyPageHref(taxonomyFilters, taxonomyPage + 1, taxonomyPageSize)}>Next</Link> : <span>Next</span>}
            </nav>
            <p className="taxonomy-boundary-note">
              The dashboard does not reclassify these trials and does not use database, R2, or live-analysis fallback taxonomy. Open a trial for structured evidence facts and exact supporting artifact links.
            </p>
          </>
        ) : (
          <div className="evidence-warning">
            <strong>Frozen taxonomy unavailable.</strong> {taxonomySnapshot.message} No rows are displayed and no operational source is substituted.
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Invalid / quarantined runs</h2>
            <p>Runs excluded from valid-only scored comparisons while retained for audit.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run label</th>
                <th>Arm</th>
                <th>Suite</th>
                <th>Validity</th>
                <th>Category</th>
                <th>Provider/workflow id</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {invalidRows.length === 0 ? (
                <tr>
                  <td colSpan={7}>No invalid/quarantined runs recorded.</td>
                </tr>
              ) : (
                invalidRows.map((row) => (
                  <tr key={`${row.suite_id}-${row.arm_id}-${row.run_label}`}>
                    <td>
                      <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                    </td>
                    <td className="mono">{row.arm_id}</td>
                    <td className="mono">{row.suite_id}</td>
                    <td><ValidityBadge row={row} /></td>
                    <td>{invalidCategory(row) ?? "—"}</td>
                    <td className="mono">{row.provider_run_id ?? "—"}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel warning-panel">
        <h2>Interpretation policy</h2>
        <p>
          Canary and smoke suites are diagnostic route/provider tests. They are useful for
          readiness and anomaly detection, but they should not be read as definitive model-quality
          comparisons. Full sweeps are the primary comparison layer, but they still need
          anomaly flags when suspicious trial behavior appears.
        </p>
        <div className="concept-grid">
          <article>
            <h3>Raw pass rate <TermInfo term="Pass rate" /></h3>
            <p>Successes divided by all imported trials. This remains the auditable benchmark outcome.</p>
          </article>
          <article>
            <h3>Qualified pass rate</h3>
            <p>Successes divided by trials after excluding suspect no-op zero-token exits.</p>
          </article>
          <article>
            <h3>Suspect no-op exit</h3>
            <p>A failed trial with no exception, no recorded tokens, no recorded cost, and an empty completed agent result or DB-equivalent zero-token signature.</p>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Definitions</h2>
            <p>Failure categories used by the audit tables.</p>
          </div>
        </div>
        <div className="concept-grid">
          <article>
            <h3>Normal failure</h3>
            <p>Trial completed without captured exception, but verifier did not pass.</p>
          </article>
          <article>
            <h3>Exception failure</h3>
            <p>Abnormal failure such as timeout, nonzero agent exit, provider/API error, connection error, or runtime service failure.</p>
          </article>
          <article>
            <h3>Suspect no-op zero-token</h3>
            <p>Failed trial with no exception, no recorded tokens, no recorded cost, and an empty completed-agent signature.</p>
          </article>
          <article>
            <h3>Explicit note</h3>
            <p>Haiku and the invalid Opus run have 0 suspect no-op because their failures were explicit exceptions, not silent no-op exits.</p>
          </article>
        </div>
      </section>

      <section className="metric-grid metric-grid-compact">
        <article className="metric-card">
          <span className="metric-label">Suspect no-op trials</span>
          <strong>{totalSuspect}</strong>
          <span className="metric-subtitle">Imported benchmark rows</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Affected arm runs</span>
          <strong>{affectedRuns}</strong>
          <span className="metric-subtitle">Any mode</span>
        </article>
        <article className="metric-card">
          <span className="metric-label">Affected full runs</span>
          <strong>{affectedFullRuns}</strong>
          <span className="metric-subtitle">Should be zero or investigated</span>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Arm-run quality summary</h2>
            <p>Shows raw and qualified pass rates side by side. Qualified rate only removes suspect no-op zero-token exits.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="sticky-id-column">Arm run</th>
                <th>Mode</th>
                <th>Validity</th>
                <th>Raw pass</th>
                <th>Qualified pass</th>
                <th>Suspect no-op</th>
                <th>Exceptions</th>
                <th>Normal failures</th>
                <th>Cost</th>
                <th>Artifacts</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((row) => {
                const invalidRow = invalidByRun.get(row.run_label);
                return (
                  <tr key={row.run_label}>
                    <td className="sticky-id-column">
                      <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                      {row.suite_id ? <div className="muted">{row.suite_id}</div> : null}
                      <div className="row-action-links">
                        <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>Run detail</Link>
                        <Link href={buildArtifactHref({ run_label: row.run_label })}>Artifacts</Link>
                      </div>
                    </td>
                    <td>{modeLabel(row.logical_mode, row.storage_mode)}</td>
                    <td>
                      <ValidityBadge row={invalidRow} />
                      {invalidRow ? (
                        <div className="muted">
                          <InvalidReason row={invalidRow} includeProvider={false} />
                        </div>
                      ) : null}
                    </td>
                    <td>{row.success_count}/{row.trial_count} · {pct(row.raw_pass_rate)}</td>
                    <td>
                      {row.qualified_success_count}/{row.qualified_trial_count} · {pct(row.qualified_pass_rate)}
                    </td>
                    <td>
                      {row.suspect_noop_count > 0 ? (
                        <Link href={buildSuspectNoopHref({ run_label: row.run_label })}>
                          <QualityBadge count={row.suspect_noop_count} />
                        </Link>
                      ) : (
                        <QualityBadge count={row.suspect_noop_count} />
                      )}
                    </td>
                    <td>{row.exception_count}</td>
                    <td>{row.normal_failed_count}</td>
                    <td>
                      {money(row.recorded_cost_usd)}
                      {row.missing_cost_count > 0 ? <div className="muted">{row.missing_cost_count} missing</div> : null}
                    </td>
                    <td>
                      {invalidRow || row.exception_count > 0 ? (
                        <Link href={buildArtifactHref({ run_label: row.run_label })}>Artifacts</Link>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" id="suspect-noop-trials">
        <div className="panel-heading">
          <div>
            <h2>Legacy suspect no-op zero-token compatibility rows</h2>
            <p>This historical stored heuristic remains available for compatibility; it is not a primary J2 failure or trajectory diagnosis.</p>
          </div>
        </div>
        {activeFilterEntries.length > 0 ? (
          <div className="quality-context-panel">
            <strong>Active drilldown filter:</strong>{" "}
            {activeFilterEntries.map(([key, value]) => formatFilterValue(key, value)).join(" · ")}{" "}
            <Link href="/trial-quality#suspect-noop-trials">Clear filter</Link>
          </div>
        ) : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Mode</th>
                <th>Validity</th>
                <th>Run label</th>
                <th>Arm</th>
                <th>Suite</th>
                <th>Task</th>
                <th>Attempt</th>
                <th>Runtime</th>
                <th>Tokens</th>
                <th>Cost</th>
                <th>Exception type</th>
                <th>Exception summary</th>
                <th>Artifacts</th>
              </tr>
            </thead>
            <tbody>
              {suspectTrials.length === 0 ? (
                <tr>
                  <td colSpan={13}>No suspect no-op zero-token trials found.</td>
                </tr>
              ) : (
                suspectTrials.map((row) => {
                  const invalidRow = invalidByRun.get(row.run_label);
                  return (
                    <tr key={`${row.run_label}-${row.task_id}-${row.attempt_index ?? "attempt"}`}>
                      <td>{modeLabel(row.logical_mode, row.storage_mode)}</td>
                      <td><ValidityBadge row={invalidRow} /></td>
                      <td>
                        <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                      </td>
                      <td className="mono">{row.arm_id}</td>
                      <td className="mono">{row.suite_id ?? "—"}</td>
                      <td className="mono">{row.task_id}</td>
                      <td>{row.attempt_index ?? "—"}</td>
                      <td>{row.runtime_seconds ? `${Number(row.runtime_seconds).toFixed(1)}s` : "—"}</td>
                      <td>{Number(row.input_tokens ?? 0).toLocaleString()} in / {Number(row.output_tokens ?? 0).toLocaleString()} out</td>
                      <td>{money(row.cost_usd)}</td>
                      <td>{redactSecretsInText(row.exception_type ?? "—")}</td>
                      <td className="table-cell-wrap">{redactSecretsInText(row.exception_summary ?? "—")}</td>
                      <td>
                        <Link
                          href={buildArtifactHref({
                            run_label: row.run_label,
                            task_id: row.task_id,
                            quality_flag: "suspect_noop_zero_token"
                          })}
                        >
                          Artifacts
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
