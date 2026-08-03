import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { ArtifactEvidenceGuide } from "../../components/ArtifactEvidenceGuide";
import { ArtifactTypeLabel } from "../../components/ArtifactTypeInfo";
import { ValidityBadge } from "../../components/ValidityContext";
import { buildSuspectNoopHref } from "../../components/QualityContext";
import {
  ArtifactBrowserFilters,
  ArtifactBrowserGroup,
  getArtifactBrowserFilterOptions,
  getArtifactBrowserPage,
  getInvalidArmRunRowsByRunLabels
} from "../../lib/dashboard-data";
import { deriveEvidenceCompleteness } from "../../lib/artifact-types";
import { formatBytes, formatNumber } from "../../lib/format";
import { redactSecretsInText } from "../../lib/safe-display";

export const dynamic = "force-dynamic";

type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function cleanParam(value: string | string[] | undefined) {
  const text = firstParam(value)?.trim();
  return text || undefined;
}

function parsePositiveInteger(value: string | string[] | undefined, fallback: number) {
  const parsed = Number(cleanParam(value));
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : fallback;
}

function formatReward(value: number | string | null | undefined) {
  return value === null || value === undefined || value === "" ? "not recorded" : formatNumber(value);
}

function safeDisplay(value: string) {
  return redactSecretsInText(value);
}

function modeLabel(logicalMode: string | null, storageMode: string | null) {
  if (!logicalMode && !storageMode) return "not recorded";
  if (logicalMode === storageMode || !storageMode) return logicalMode ?? storageMode;
  return `${logicalMode} / ${storageMode}`;
}

function qualityBadgeClass(group: ArtifactBrowserGroup) {
  return group.quality_flag === "suspect_noop_zero_token"
    || group.quality_flag === "exception"
    || group.quality_flag === "exception_with_success"
    ? "quality-badge quality-badge-warn"
    : "quality-badge";
}

function buildArtifactQualityHref(group: ArtifactBrowserGroup) {
  if (group.quality_flag === "suspect_noop_zero_token") {
    return buildSuspectNoopHref({
      suite_id: group.suite_id,
      arm_id: group.arm_id,
      run_label: group.run_label,
      task_id: group.task_id
    });
  }
  const params = new URLSearchParams({ run_label: group.run_label });
  if (group.suite_id) params.set("suite_id", group.suite_id);
  if (group.arm_id) params.set("arm_id", group.arm_id);
  if (group.task_id) params.set("task_id", group.task_id);
  if (group.quality_flag) params.set("quality", group.quality_flag);
  return `/trial-quality?${params.toString()}#suspect-noop-trials`;
}

const filterLabels: Record<string, string> = {
  run_label: "Run", suite_id: "Suite", arm_id: "Arm", task_id: "Task",
  quality_flag: "Quality", exception_type: "Exception", artifact_type: "Artifact type", q: "Search"
};

function activeFilterEntries(filters: ArtifactBrowserFilters): Array<[string, string]> {
  return ([
    ["run_label", filters.run_label], ["suite_id", filters.suite_id], ["arm_id", filters.arm_id],
    ["task_id", filters.task_id], ["quality_flag", filters.quality_flag],
    ["exception_type", filters.exception_type], ["artifact_type", filters.artifact_type ?? filters.artifact_kind],
    ["q", filters.q]
  ] as Array<[string, string | undefined]>).filter((entry): entry is [string, string] => Boolean(entry[1]));
}

function paginationHref(filters: ArtifactBrowserFilters, page: number) {
  const params = new URLSearchParams();
  for (const [key, value] of activeFilterEntries(filters)) params.set(key, value);
  params.set("page", String(page));
  params.set("page_size", String(filters.page_size ?? 25));
  return `/artifacts?${params.toString()}`;
}

function SelectFilter({ label, name, value, options }: {
  label: string; name: string; value?: string; options: string[];
}) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <select name={name} defaultValue={value ?? ""}>
        <option value="">All</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

export default async function ArtifactsPage({ searchParams }: { searchParams?: PageSearchParams }) {
  const params = searchParams ? await searchParams : {};
  const requestedPageSize = parsePositiveInteger(params.page_size, 25);
  const filters: ArtifactBrowserFilters = {
    run_label: cleanParam(params.run_label), suite_id: cleanParam(params.suite_id),
    arm_id: cleanParam(params.arm_id), task_id: cleanParam(params.task_id),
    quality_flag: cleanParam(params.quality_flag), exception_type: cleanParam(params.exception_type),
    artifact_type: cleanParam(params.artifact_type) ?? cleanParam(params.artifact_kind),
    q: cleanParam(params.q), page: parsePositiveInteger(params.page, 1),
    page_size: [10, 25, 50, 100].includes(requestedPageSize) ? requestedPageSize : 25
  };
  const [browserPage, options] = await Promise.all([
    getArtifactBrowserPage(filters),
    getArtifactBrowserFilterOptions()
  ]);
  const activeFilters = activeFilterEntries(filters);
  const invalidRows = await getInvalidArmRunRowsByRunLabels(
    Array.from(new Set(browserPage.groups.map((group) => group.run_label)))
  );
  const invalidByRun = new Map(invalidRows.map((row) => [row.run_label, row]));

  return (
    <AppShell
      title="Artifacts"
      description="Trial-grouped evidence browser for Harbor results, Claude Code activity, verifier output, and router observability."
    >
      <section className="quality-context-panel">
        This audit view may include invalid or quarantined runs. Filtering selects matching evidence groups and then expands every artifact in each group. It never changes stored rewards, pass rates, denominators, or quality flags.
      </section>

      <ArtifactEvidenceGuide />

      <section className="panel">
        <div className="panel-heading">
          <div><h2>Evidence-group filters</h2><p>Known fields use database-backed values; free text searches paths, run labels, tasks, notes, and exception summaries.</p></div>
          <Link href="/artifacts">Clear filters</Link>
        </div>
        <form className="artifact-filter-grid" action="/artifacts" method="get">
          <SelectFilter label="Run label" name="run_label" value={filters.run_label} options={options.run_labels} />
          <SelectFilter label="Suite" name="suite_id" value={filters.suite_id} options={options.suite_ids} />
          <SelectFilter label="Arm" name="arm_id" value={filters.arm_id} options={options.arm_ids} />
          <SelectFilter label="Task" name="task_id" value={filters.task_id} options={options.task_ids} />
          <SelectFilter label="Quality flag" name="quality_flag" value={filters.quality_flag} options={options.quality_flags} />
          <SelectFilter label="Exception type" name="exception_type" value={filters.exception_type} options={options.exception_types} />
          <SelectFilter label="Artifact type" name="artifact_type" value={filters.artifact_type} options={options.artifact_types} />
          <label className="form-field"><span>Search</span><input name="q" defaultValue={filters.q ?? ""} placeholder="path, run, task, note" /></label>
          <label className="form-field"><span>Groups per page</span><select name="page_size" defaultValue={String(filters.page_size)}>{[10, 25, 50, 100].map((size) => <option key={size}>{size}</option>)}</select></label>
          <div className="artifact-filter-actions"><button type="submit">Apply filters</button><Link href="/artifacts">Clear</Link></div>
        </form>
      </section>

      {activeFilters.length > 0 ? (
        <section className="active-filter-summary" aria-label="Active artifact filters">
          <strong>Active filters</strong>
          <div className="filter-chip-list">{activeFilters.map(([key, value]) => <span className="filter-chip" key={key}>{filterLabels[key] ?? key}: {safeDisplay(value)}</span>)}</div>
          <Link href="/artifacts">Clear all</Link>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Artifact evidence groups</h2>
            <p>
              {formatNumber(browserPage.total_group_count)} matching group{browserPage.total_group_count === 1 ? "" : "s"}; {formatNumber(browserPage.matching_artifact_count)} matching artifact{browserPage.matching_artifact_count === 1 ? "" : "s"}; {formatNumber(browserPage.expanded_artifact_count)} artifact rows expanded on this page.
            </p>
          </div>
          <span className="status">Page {browserPage.page} of {browserPage.total_pages}</span>
        </div>

        {browserPage.groups.length === 0 ? (
          <div className="placeholder-body">No evidence groups matched these filters.</div>
        ) : (
          <div className="evidence-group-list">
            {browserPage.groups.map((group) => {
              const completeness = deriveEvidenceCompleteness(group.artifacts, group.trial_id ? "trial" : "run", Boolean(group.exception_type));
              const matchingCount = group.artifacts.filter((artifact) => artifact.matching_artifact).length;
              const invalidRow = invalidByRun.get(group.run_label);
              return (
                <article className="evidence-group" key={group.group_key}>
                  <header className="evidence-group-header">
                    <div>
                      <p className="eyebrow">{group.trial_id ? "Trial evidence" : "Run-root evidence"}</p>
                      <h3>{group.task_id ?? group.run_label}</h3>
                      <p>
                        <Link href={`/runs/${encodeURIComponent(group.run_label)}`}>{group.run_label}</Link>
                        {group.trial_id ? ` · Task ${group.task_ordinal ?? "?"} of ${group.run_task_count ?? "?"} · Attempt ${group.task_attempt_number ?? "?"} of ${group.task_attempt_count ?? "?"} · Run trial #${group.run_trial_number ?? "?"}` : " · shared run-level files"}
                      </p>
                    </div>
                    <div className="evidence-group-badges">
                      <ValidityBadge row={invalidRow} />
                      <span className={qualityBadgeClass(group)}>{group.quality_flag ?? (group.trial_id ? "unflagged" : "run root")}</span>
                    </div>
                  </header>

                  <div className="evidence-completeness-grid">
                    <div><span>Canonical evidence</span><strong>{completeness.canonical_present_count}/{completeness.canonical_expected_count} present</strong></div>
                    <div><span>Storage</span><strong>{completeness.r2_indexed_count}/{completeness.canonical_expected_count} R2 indexed</strong></div>
                    <div><span>Router observability</span><strong>{completeness.router_observability.replace("_", " ")}</strong></div>
                    <div><span>Filter expansion</span><strong>{matchingCount} matched · {group.artifacts.length} shown</strong></div>
                  </div>
                  {completeness.missing_types.length > 0 || completeness.exception_metadata_without_artifact ? (
                    <div className="evidence-warning">
                      {completeness.missing_types.length > 0 ? `Missing canonical types: ${completeness.missing_types.join(", ")}.` : ""}
                      {completeness.exception_metadata_without_artifact ? " Exception metadata exists, but no exception artifact is attached." : ""}
                    </div>
                  ) : null}

                  {group.trial_id ? (
                    <div className="evidence-group-context">
                      <span>{group.suite_id ?? "no suite"}</span><span>{modeLabel(group.logical_mode, group.storage_mode)}</span>
                      <span>{group.arm_id ?? "no arm"}</span><span>reward {formatReward(group.reward)}</span>
                      {group.exception_type ? <span>{safeDisplay(group.exception_type)}</span> : null}
                    </div>
                  ) : null}

                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Artifact</th><th>Path</th><th>Size</th><th>Storage</th><th>Review</th></tr></thead>
                      <tbody>{group.artifacts.map((artifact) => (
                        <tr key={artifact.artifact_id} className={artifact.matching_artifact ? "artifact-match" : ""}>
                          <td><ArtifactTypeLabel artifactType={artifact.artifact_type} />{artifact.matching_artifact && activeFilters.length > 0 ? <div className="muted">matched filter</div> : null}</td>
                          <td><details className="path-details"><summary>{safeDisplay(artifact.artifact_path).split("/").at(-1) ?? safeDisplay(artifact.artifact_path)}</summary><div className="mono">{safeDisplay(artifact.artifact_path)}</div>{artifact.r2_uri ? <div className="mono">{safeDisplay(artifact.r2_uri)}</div> : null}</details></td>
                          <td>{formatBytes(artifact.size_bytes)}</td>
                          <td>{artifact.r2_uri ? "R2 indexed" : "not R2 indexed"}</td>
                          <td><Link href={`/artifacts/${artifact.artifact_id}`}>View artifact</Link></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                  <footer className="artifact-link-bar">
                    {group.trial_id ? <Link href={`/trials/${group.trial_id}`}>Quick diagnosis</Link> : null}
                    <Link href={`/runs/${encodeURIComponent(group.run_label)}`}>Run detail</Link>
                    {group.task_id ? <Link href={`/evals/${encodeURIComponent(group.task_id)}`}>Eval task</Link> : null}
                    {group.trial_id ? <Link href={buildArtifactQualityHref(group)}>Trial Quality filter</Link> : null}
                  </footer>
                </article>
              );
            })}
          </div>
        )}

        <nav className="pagination-bar" aria-label="Artifact evidence group pages">
          {browserPage.page > 1 ? <Link href={paginationHref(filters, browserPage.page - 1)}>← Previous</Link> : <span>← Previous</span>}
          <strong>Page {browserPage.page} of {browserPage.total_pages}</strong>
          {browserPage.page < browserPage.total_pages ? <Link href={paginationHref(filters, browserPage.page + 1)}>Next →</Link> : <span>Next →</span>}
        </nav>
      </section>
    </AppShell>
  );
}
