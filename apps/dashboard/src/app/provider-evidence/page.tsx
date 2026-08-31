import Link from "next/link";

import { AppShell } from "../../components/AppShell";
import {
  getProviderEvidenceBrowserFilterOptions,
  getProviderEvidenceBrowserLatestCapturedAt,
  getProviderEvidenceBrowserPage,
  type ProviderEvidenceBrowserFilters,
} from "../../lib/dashboard-data";
import { formatBytes, formatNumber } from "../../lib/format";
import { friendlyProviderLabel } from "../../lib/presentation-labels";
import {
  sanitizeDisplayedUri,
  sanitizeEvidenceText,
} from "../../lib/safe-display";

export const dynamic = "force-dynamic";

type PageSearchParams =
  Promise<Record<string, string | string[] | undefined>>;

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function cleanParam(value: string | string[] | undefined) {
  const text = firstParam(value)?.trim();
  return text || undefined;
}

function parsePositiveInteger(
  value: string | string[] | undefined,
  fallback: number,
) {
  const parsed = Number(cleanParam(value));
  return Number.isFinite(parsed) && parsed > 0
    ? Math.trunc(parsed)
    : fallback;
}

function humanize(value: string | null | undefined) {
  if (!value) return "—";
  return value.replaceAll("_", " ");
}

function safeText(value: string | null | undefined) {
  return sanitizeEvidenceText(value) ?? "—";
}

function safeUri(value: string | null | undefined) {
  return sanitizeDisplayedUri(value) ?? "—";
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return "not recorded";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? safeText(value)
    : date.toLocaleString();
}

function compactSha(value: string | null) {
  if (!value) return "not recorded";
  return value.length > 16 ? `${value.slice(0, 16)}…` : value;
}

const filterLabels: Record<string, string> = {
  provider: "Provider",
  evidence_kind: "Evidence kind",
  source_scope: "Source scope",
  integrity_status: "Integrity",
  phase: "Phase",
  arm_id: "Arm",
  run_label: "Run",
  q: "Search",
};

function activeFilterEntries(
  filters: ProviderEvidenceBrowserFilters,
): Array<[string, string]> {
  return ([
    ["provider", filters.provider],
    ["evidence_kind", filters.evidence_kind],
    ["source_scope", filters.source_scope],
    ["integrity_status", filters.integrity_status],
    ["phase", filters.phase],
    ["arm_id", filters.arm_id],
    ["run_label", filters.run_label],
    ["q", filters.q],
  ] as Array<[string, string | undefined]>).filter(
    (entry): entry is [string, string] => Boolean(entry[1]),
  );
}

function paginationHref(
  filters: ProviderEvidenceBrowserFilters,
  page: number,
) {
  const params = new URLSearchParams();

  for (const [key, value] of activeFilterEntries(filters)) {
    params.set(key, value);
  }

  params.set("page", String(page));
  params.set("page_size", String(filters.page_size ?? 25));

  return `/provider-evidence?${params.toString()}`;
}

function SelectFilter({
  label,
  name,
  value,
  options,
}: {
  label: string;
  name: string;
  value?: string;
  options: string[];
}) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <select name={name} defaultValue={value ?? ""}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export default async function ProviderEvidencePage({
  searchParams,
}: {
  searchParams?: PageSearchParams;
}) {
  const params = searchParams ? await searchParams : {};
  const requestedPageSize = parsePositiveInteger(
    params.page_size,
    25,
  );

  const filters: ProviderEvidenceBrowserFilters = {
    provider: cleanParam(params.provider),
    evidence_kind: cleanParam(params.evidence_kind),
    source_scope: cleanParam(params.source_scope),
    integrity_status: cleanParam(params.integrity_status),
    phase: cleanParam(params.phase),
    arm_id: cleanParam(params.arm_id),
    run_label: cleanParam(params.run_label),
    q: cleanParam(params.q),
    page: parsePositiveInteger(params.page, 1),
    page_size: [10, 25, 50, 100].includes(requestedPageSize)
      ? requestedPageSize
      : 25,
  };

  const [browserPage, options, latestCapturedAt] =
    await Promise.all([
      getProviderEvidenceBrowserPage(filters),
      getProviderEvidenceBrowserFilterOptions(),
      getProviderEvidenceBrowserLatestCapturedAt(filters),
    ]);

  const activeFilters = activeFilterEntries(filters);

  return (
    <AppShell
      title="Provider Evidence"
      description="Read-only browser for provider-supplied usage, cost, pricing, provenance, and reconciliation evidence."
    >
      <section className="quality-context-panel">
        <strong>Normalized evidence, not a raw-provider-data viewer.</strong>
        {" "}
        This surface exposes the reviewed provider-evidence contract and
        privacy-safe provenance needed to audit provider usage and cost
        conclusions. Private raw provider payload metadata is not rendered.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Provider evidence filters</h2>
            <p>
              Filters apply to provider sources and to run/arm context
              inferred from normalized usage, normalized cost, artifact,
              and reconciliation links.
            </p>
          </div>
          <Link href="/provider-evidence">Clear filters</Link>
        </div>

        <form
          className="artifact-filter-grid"
          action="/provider-evidence"
          method="get"
        >
          <SelectFilter
            label="Provider"
            name="provider"
            value={filters.provider}
            options={options.providers}
          />
          <SelectFilter
            label="Evidence kind"
            name="evidence_kind"
            value={filters.evidence_kind}
            options={options.evidence_kinds}
          />
          <SelectFilter
            label="Source scope"
            name="source_scope"
            value={filters.source_scope}
            options={options.source_scopes}
          />
          <SelectFilter
            label="Integrity"
            name="integrity_status"
            value={filters.integrity_status}
            options={options.integrity_statuses}
          />
          <SelectFilter
            label="Phase"
            name="phase"
            value={filters.phase}
            options={options.phases}
          />
          <SelectFilter
            label="Arm"
            name="arm_id"
            value={filters.arm_id}
            options={options.arm_ids}
          />
          <SelectFilter
            label="Run label"
            name="run_label"
            value={filters.run_label}
            options={options.run_labels}
          />

          <label className="form-field">
            <span>Search</span>
            <input
              name="q"
              defaultValue={filters.q ?? ""}
              placeholder="provider, reference, URI, hash, note"
            />
          </label>

          <label className="form-field">
            <span>Sources per page</span>
            <select
              name="page_size"
              defaultValue={String(filters.page_size)}
            >
              {[10, 25, 50, 100].map((size) => (
                <option key={size}>{size}</option>
              ))}
            </select>
          </label>

          <div className="artifact-filter-actions">
            <button type="submit">Apply filters</button>
            <Link href="/provider-evidence">Clear</Link>
          </div>
        </form>
      </section>

      {activeFilters.length > 0 ? (
        <section
          className="active-filter-summary"
          aria-label="Active provider evidence filters"
        >
          <strong>Active filters</strong>
          <div className="filter-chip-list">
            {activeFilters.map(([key, value]) => (
              <span className="filter-chip" key={key}>
                {filterLabels[key] ?? key}: {safeText(value)}
              </span>
            ))}
          </div>
          <Link href="/provider-evidence">Clear all</Link>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Provider evidence sources</h2>
            <p>
              {formatNumber(browserPage.total_source_count)} matching
              {" "}
              source
              {browserPage.total_source_count === 1 ? "" : "s"}.
              {" "}
              Latest matching capture:
              {" "}
              {formatTimestamp(latestCapturedAt)}.
            </p>
          </div>
          <span className="status">
            Page {browserPage.page} of {browserPage.total_pages}
          </span>
        </div>

        {browserPage.sources.length === 0 ? (
          <div className="placeholder-body">
            No provider evidence sources matched these filters.
          </div>
        ) : (
          <div className="evidence-group-list">
            {browserPage.sources.map((source) => (
              <article
                className="evidence-group"
                key={source.source_id}
              >
                <header className="evidence-group-header">
                  <div>
                    <p className="eyebrow">
                      {friendlyProviderLabel(source.provider)}
                    </p>
                    <h3>{humanize(source.evidence_kind)}</h3>
                    <p>
                      <code>{source.source_id}</code>
                    </p>
                  </div>

                  <div className="evidence-group-badges">
                    <span className="quality-badge">
                      {humanize(source.integrity_status)}
                    </span>
                    <span className="quality-badge">
                      {humanize(source.source_scope)}
                    </span>
                  </div>
                </header>

                <div className="evidence-completeness-grid">
                  <div>
                    <span>Normalized usage</span>
                    <strong>
                      {formatNumber(source.usage_row_count)} rows
                    </strong>
                  </div>
                  <div>
                    <span>Normalized cost</span>
                    <strong>
                      {formatNumber(source.cost_row_count)} rows
                    </strong>
                  </div>
                  <div>
                    <span>Pricing snapshots</span>
                    <strong>
                      {formatNumber(source.pricing_snapshot_count)}
                    </strong>
                  </div>
                  <div>
                    <span>Reconciliations</span>
                    <strong>
                      {formatNumber(source.usage_reconciliation_count)}
                      {" "}usage ·{" "}
                      {formatNumber(source.cost_reconciliation_count)}
                      {" "}cost
                    </strong>
                  </div>
                </div>

                <div className="evidence-group-context">
                  <span>
                    phases:{" "}
                    {source.phases.length
                      ? source.phases.map(safeText).join(", ")
                      : "unallocated"}
                  </span>
                  <span>
                    arms:{" "}
                    {source.arm_ids.length
                      ? source.arm_ids.map(safeText).join(", ")
                      : "unallocated"}
                  </span>
                  <span>
                    captured {formatTimestamp(source.captured_at)}
                  </span>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Provenance field</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Provider reference</td>
                        <td className="table-cell-wrap">
                          {safeText(source.provider_reference)}
                        </td>
                      </tr>
                      <tr>
                        <td>Source URI</td>
                        <td className="mono table-cell-wrap">
                          {safeUri(source.source_uri)}
                        </td>
                      </tr>
                      <tr>
                        <td>SHA-256</td>
                        <td>
                          {source.source_sha256 ? (
                            <details className="path-details">
                              <summary>
                                {compactSha(source.source_sha256)}
                              </summary>
                              <div className="mono">
                                {source.source_sha256}
                              </div>
                            </details>
                          ) : (
                            "not recorded"
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>Size / format</td>
                        <td>
                          {formatBytes(source.size_bytes)}
                          {" · "}
                          {safeText(source.source_format)}
                        </td>
                      </tr>
                      <tr>
                        <td>Provider window</td>
                        <td>
                          {formatTimestamp(
                            source.provider_window_started_at,
                          )}
                          {" → "}
                          {formatTimestamp(
                            source.provider_window_finished_at,
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>Notes</td>
                        <td className="table-cell-wrap">
                          {safeText(source.notes)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {source.run_labels.length > 0 ? (
                  <div className="artifact-link-bar">
                    {source.run_labels.map((runLabel) => (
                      <Link
                        href={`/runs/${encodeURIComponent(runLabel)}`}
                        key={runLabel}
                      >
                        {safeText(runLabel)}
                      </Link>
                    ))}
                  </div>
                ) : null}

                <footer className="artifact-link-bar">
                  <Link
                    href={`/provider-evidence/${encodeURIComponent(
                      source.source_id,
                    )}`}
                  >
                    View provider evidence source
                  </Link>

                  {source.artifact_id ? (
                    <Link
                      href={`/artifacts/${encodeURIComponent(
                        source.artifact_id,
                      )}`}
                    >
                      Linked artifact
                    </Link>
                  ) : null}
                </footer>
              </article>
            ))}
          </div>
        )}

        <nav
          className="pagination-bar"
          aria-label="Provider evidence source pages"
        >
          {browserPage.page > 1 ? (
            <Link
              href={paginationHref(
                filters,
                browserPage.page - 1,
              )}
            >
              ← Previous
            </Link>
          ) : (
            <span>← Previous</span>
          )}

          <strong>
            Page {browserPage.page} of {browserPage.total_pages}
          </strong>

          {browserPage.page < browserPage.total_pages ? (
            <Link
              href={paginationHref(
                filters,
                browserPage.page + 1,
              )}
            >
              Next →
            </Link>
          ) : (
            <span>Next →</span>
          )}
        </nav>
      </section>
    </AppShell>
  );
}
