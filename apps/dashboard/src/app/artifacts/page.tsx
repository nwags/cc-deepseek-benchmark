import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { ValidityBadge } from "../../components/ValidityContext";
import { buildSuspectNoopHref } from "../../components/QualityContext";
import {
  ArtifactBrowserFilters,
  ArtifactBrowserRow,
  getArtifactBrowserRows,
  getInvalidArmRunRowsByRunLabels
} from "../../lib/dashboard-data";
import { formatBytes, formatNumber } from "../../lib/format";

export const dynamic = "force-dynamic";

type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;

function firstParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) return value[0];
  return value;
}

function cleanParam(value: string | string[] | undefined) {
  const text = firstParam(value)?.trim();
  return text || undefined;
}

function parseLimit(value: string | string[] | undefined) {
  const raw = cleanParam(value);
  if (!raw) return undefined;

  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return undefined;
  return Math.min(Math.max(Math.trunc(parsed), 1), 1000);
}

function compactPath(value: string | null | undefined) {
  if (!value) return "—";

  const parts = value.split("/");
  if (parts.length <= 7) return value;
  return `…/${parts.slice(-5).join("/")}`;
}

function formatReward(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toFixed(0);
}

function modeLabel(logicalMode: string | null, storageMode: string | null) {
  if (!logicalMode && !storageMode) return "—";
  if (logicalMode === storageMode || !storageMode) return logicalMode ?? storageMode;
  return `${logicalMode} / ${storageMode}`;
}

function qualityBadgeClass(row: ArtifactBrowserRow) {
  if (row.quality_flag === "suspect_noop_zero_token") return "quality-badge quality-badge-warn";
  if (row.quality_flag === "exception" || row.quality_flag === "exception_with_success") {
    return "quality-badge quality-badge-warn";
  }
  return "quality-badge";
}

function buildArtifactQualityHref(row: ArtifactBrowserRow) {
  if (row.quality_flag === "suspect_noop_zero_token") {
    return buildSuspectNoopHref({
      suite_id: row.suite_id,
      arm_id: row.arm_id,
      run_label: row.run_label,
      task_id: row.task_id
    });
  }

  const params = new URLSearchParams();
  params.set("run_label", row.run_label);
  if (row.suite_id) params.set("suite_id", row.suite_id);
  if (row.arm_id) params.set("arm_id", row.arm_id);
  if (row.task_id) params.set("task_id", row.task_id);
  if (row.quality_flag) params.set("quality", row.quality_flag);

  return `/trial-quality?${params.toString()}#suspect-noop-trials`;
}

function activeFilterEntries(filters: ArtifactBrowserFilters): Array<[string, string]> {
  return ([
    ["run_label", filters.run_label],
    ["suite_id", filters.suite_id],
    ["arm_id", filters.arm_id],
    ["task_id", filters.task_id],
    ["quality_flag", filters.quality_flag],
    ["exception_type", filters.exception_type],
    ["artifact_type", filters.artifact_type ?? filters.artifact_kind],
    ["q", filters.q],
    ["limit", filters.limit ? String(filters.limit) : undefined]
  ] as Array<[string, string | undefined]>).filter((entry): entry is [string, string] => Boolean(entry[1]));
}

export default async function ArtifactsPage({
  searchParams
}: {
  searchParams?: PageSearchParams;
}) {
  const params = searchParams ? await searchParams : {};
  const filters: ArtifactBrowserFilters = {
    run_label: cleanParam(params.run_label),
    suite_id: cleanParam(params.suite_id),
    arm_id: cleanParam(params.arm_id),
    task_id: cleanParam(params.task_id),
    quality_flag: cleanParam(params.quality_flag),
    exception_type: cleanParam(params.exception_type),
    artifact_type: cleanParam(params.artifact_type) ?? cleanParam(params.artifact_kind),
    q: cleanParam(params.q),
    limit: parseLimit(params.limit)
  };
  const activeFilters = activeFilterEntries(filters);
  const rows = await getArtifactBrowserRows(filters);
  const invalidRows = await getInvalidArmRunRowsByRunLabels(
    Array.from(new Set(rows.map((row) => row.run_label)))
  );
  const invalidByRun = new Map(invalidRows.map((row) => [row.run_label, row]));

  return (
    <AppShell
      title="Artifacts"
      description="Audit browser for result files, logs, trajectories, and verifier evidence. This provenance view includes all imported runs."
    >
      <section className="quality-context-panel">
        Artifact rows are audit evidence and may include invalid/quarantined runs. Signed download links are not exposed from this page.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Artifact filters</h2>
            <p>Filter by run, suite, arm, task, quality flag, exception type, artifact kind, or text search.</p>
          </div>
          <Link href="/artifacts">Clear filters</Link>
        </div>

        <form className="artifact-filter-grid" action="/artifacts" method="get">
          <label className="form-field">
            <span>Run label</span>
            <input name="run_label" defaultValue={filters.run_label ?? ""} placeholder="router-sonnet/..." />
          </label>
          <label className="form-field">
            <span>Suite</span>
            <input name="suite_id" defaultValue={filters.suite_id ?? ""} placeholder="phase3-full-20" />
          </label>
          <label className="form-field">
            <span>Arm</span>
            <input name="arm_id" defaultValue={filters.arm_id ?? ""} placeholder="router-anthropic-sonnet" />
          </label>
          <label className="form-field">
            <span>Task</span>
            <input name="task_id" defaultValue={filters.task_id ?? ""} placeholder="terminal-bench task id" />
          </label>
          <label className="form-field">
            <span>Quality flag</span>
            <input name="quality_flag" defaultValue={filters.quality_flag ?? ""} placeholder="suspect_noop_zero_token" />
          </label>
          <label className="form-field">
            <span>Exception type</span>
            <input name="exception_type" defaultValue={filters.exception_type ?? ""} placeholder="TimeoutError" />
          </label>
          <label className="form-field">
            <span>Artifact type</span>
            <input name="artifact_type" defaultValue={filters.artifact_type ?? filters.artifact_kind ?? ""} placeholder="result_json" />
          </label>
          <label className="form-field">
            <span>Search</span>
            <input name="q" defaultValue={filters.q ?? ""} placeholder="path, run, task, note" />
          </label>
          <label className="form-field">
            <span>Limit</span>
            <input name="limit" defaultValue={filters.limit ? String(filters.limit) : ""} placeholder="250" inputMode="numeric" />
          </label>
          <div className="artifact-filter-actions">
            <button type="submit">Apply filters</button>
            <Link href="/artifacts">Clear</Link>
          </div>
        </form>
      </section>

      {activeFilters.length > 0 ? (
        <section className="quality-context-panel">
          <strong>Active artifact filters:</strong>{" "}
          {activeFilters.map(([key, value]) => `${key}=${value}`).join(" · ")}{" "}
          <Link href="/artifacts">Clear filters</Link>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Artifact evidence</h2>
            <p>{formatNumber(rows.length)} artifact row{rows.length === 1 ? "" : "s"} shown.</p>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="placeholder-body">
            No artifact rows matched these filters. Try clearing filters, searching by run label, or starting from a suspect no-op link.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Artifact</th>
                  <th>Context</th>
                  <th>Quality</th>
                  <th>Size</th>
                  <th>Storage</th>
                  <th>Links</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const invalidRow = invalidByRun.get(row.run_label);
                  return (
                    <tr key={row.artifact_id}>
                      <td>
                        <div className="mono" title={row.artifact_path}>{compactPath(row.artifact_path)}</div>
                        <div className="muted">{row.artifact_type ?? "unknown"} · {row.created_at ?? "unknown date"}</div>
                      </td>
                      <td>
                        <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>{row.run_label}</Link>
                        <div className="muted">
                          {row.suite_id ?? "no suite"} · {modeLabel(row.logical_mode, row.storage_mode)} · {row.arm_id ?? "no arm"}
                        </div>
                        <div className="mono">
                          {row.task_id ?? "run-root artifact"}
                          {row.attempt_index !== null && row.attempt_index !== undefined ? ` · attempt ${row.attempt_index}` : ""}
                        </div>
                      </td>
                      <td>
                        <div>
                          <span className={qualityBadgeClass(row)}>{row.quality_flag ?? "run artifact"}</span>
                        </div>
                        <div className="muted">
                          reward {formatReward(row.reward)}
                          {row.exception_type ? ` · ${row.exception_type}` : ""}
                        </div>
                        {row.exception_summary ? <div className="muted">{row.exception_summary}</div> : null}
                        <div><ValidityBadge row={invalidRow} /></div>
                      </td>
                      <td>{formatBytes(row.size_bytes)}</td>
                      <td>
                        <span className={row.r2_uri ? "quality-badge" : "quality-badge quality-badge-warn"}>
                          {row.r2_uri ? "R2 indexed" : "local only"}
                        </span>
                        <div className="mono" title={row.r2_uri ?? row.artifact_path}>
                          {compactPath(row.r2_uri ?? row.artifact_path)}
                        </div>
                      </td>
                      <td>
                        <div className="artifact-link-list">
                          <Link href={`/artifacts/${row.artifact_id}`}>View artifact</Link>
                          <Link href={`/runs/${encodeURIComponent(row.run_label)}`}>Run detail</Link>
                          <Link href={buildArtifactQualityHref(row)}>Trial Quality filter</Link>
                          {row.task_id ? (
                            <Link href={`/evals/${encodeURIComponent(row.task_id)}`}>Eval task</Link>
                          ) : null}
                          {row.trial_id ? (
                            <Link href={`/trials/${row.trial_id}`}>Trial evidence</Link>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AppShell>
  );
}
