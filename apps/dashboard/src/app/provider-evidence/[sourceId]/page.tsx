import Link from "next/link";
import { notFound } from "next/navigation";

import { AppShell } from "../../../components/AppShell";
import {
  getProviderEvidenceSourceDetail,
  type ProviderEvidenceReconciliationSourceLink,
  type ProviderEvidenceSourceBrowserRow,
} from "../../../lib/dashboard-data";
import {
  formatBytes,
  formatNumber,
  formatTruncatedCurrency,
  formatTruncatedNumber,
  truncateStructuredDecimalsForDisplay,
} from "../../../lib/format";
import { friendlyProviderLabel } from "../../../lib/presentation-labels";
import {
  sanitizeDisplayedUri,
  sanitizeEvidenceOutput,
  sanitizeEvidenceText,
} from "../../../lib/safe-display";

export const dynamic = "force-dynamic";

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

function tokenValue(value: string | null) {
  return value === null ? "—" : formatNumber(value);
}

function costValue(value: string | null) {
  return value === null ? "—" : formatTruncatedCurrency(value);
}

function limitationText(values: string[]) {
  return values.length
    ? values.map(humanize).join(", ")
    : "none recorded";
}

function sanitizedRules(value: unknown) {
  const safe = sanitizeEvidenceOutput(value);
  const decimalSafe =
    truncateStructuredDecimalsForDisplay(safe);
  return JSON.stringify(decimalSafe, null, 2) ?? "—";
}

function displayedCostAmount(
  value: string,
  currency: string,
) {
  return currency === "USD"
    ? formatTruncatedCurrency(value)
    : `${safeText(currency)} ${formatTruncatedNumber(value)}`;
}

function EvidenceSourceChain({
  links,
  currentSourceId,
}: {
  links: ProviderEvidenceReconciliationSourceLink[];
  currentSourceId: string;
}) {
  if (links.length === 0) {
    return <span>none recorded</span>;
  }

  return (
    <div className="evidence-link-list">
      {links.map((link, index) => (
        <div
          key={`${link.source_id}:${link.evidence_role}:${index}`}
          className="table-cell-wrap"
        >
          <Link
            href={`/provider-evidence/${encodeURIComponent(
              link.source_id,
            )}`}
          >
            {friendlyProviderLabel(link.provider)}
            {" · "}
            {humanize(link.evidence_kind)}
          </Link>
          {" "}
          <span className="muted">
            ({humanize(link.evidence_role)}
            {link.source_id === currentSourceId
              ? ", this source"
              : ""}
            )
          </span>
        </div>
      ))}
    </div>
  );
}

function SourceContext({
  source,
}: {
  source: ProviderEvidenceSourceBrowserRow;
}) {
  return (
    <div className="detail-grid">
      <div>
        <span>Provider</span>
        <strong>{friendlyProviderLabel(source.provider)}</strong>
      </div>
      <div>
        <span>Evidence kind</span>
        <strong>{humanize(source.evidence_kind)}</strong>
      </div>
      <div>
        <span>Source scope</span>
        <strong>{humanize(source.source_scope)}</strong>
      </div>
      <div>
        <span>Integrity</span>
        <strong>{humanize(source.integrity_status)}</strong>
      </div>
      <div>
        <span>Captured</span>
        <strong>{formatTimestamp(source.captured_at)}</strong>
      </div>
      <div>
        <span>Size</span>
        <strong>{formatBytes(source.size_bytes)}</strong>
      </div>
      <div>
        <span>Format</span>
        <strong>{safeText(source.source_format)}</strong>
      </div>
      <div>
        <span>Associated phase(s)</span>
        <strong>
          {source.phases.length
            ? source.phases.map(safeText).join(", ")
            : "unallocated"}
        </strong>
      </div>
      <div>
        <span>Associated arm(s)</span>
        <strong className="mono">
          {source.arm_ids.length
            ? source.arm_ids.map(safeText).join(", ")
            : "unallocated"}
        </strong>
      </div>
      <div>
        <span>Associated run(s)</span>
        <strong>
          {source.run_labels.length
            ? source.run_labels.map((runLabel, index) => (
                <span key={runLabel}>
                  {index > 0 ? ", " : ""}
                  <Link
                    href={`/runs/${encodeURIComponent(runLabel)}`}
                  >
                    {safeText(runLabel)}
                  </Link>
                </span>
              ))
            : "unallocated"}
        </strong>
      </div>
    </div>
  );
}

export default async function ProviderEvidenceSourcePage({
  params,
}: {
  params: Promise<{ sourceId: string }>;
}) {
  const { sourceId } = await params;
  const detail = await getProviderEvidenceSourceDetail(
    decodeURIComponent(sourceId),
  );

  if (!detail) {
    notFound();
  }

  const { source } = detail;

  return (
    <AppShell
      title="Provider Evidence Source"
      description="Normalized provider usage, cost, pricing, provenance, and reconciliation detail for one evidence source."
    >
      <section className="quality-context-panel">
        <strong>Privacy-safe review surface.</strong>
        {" "}
        This page intentionally omits private raw provider payload
        metadata. Displayed notes, references, URIs, and structured
        pricing rules are sanitized before rendering.
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{friendlyProviderLabel(source.provider)}</h2>
            <p>
              <Link href="/provider-evidence">
                Back to Provider Evidence
              </Link>
            </p>
          </div>
          <span className="status">
            {humanize(source.integrity_status)}
          </span>
        </div>

        <SourceContext source={source} />

        <div className="table-wrap">
          <table>
            <tbody>
              <tr>
                <th>Source ID</th>
                <td className="mono">{source.source_id}</td>
              </tr>
              <tr>
                <th>Provider reference</th>
                <td className="table-cell-wrap">
                  {safeText(source.provider_reference)}
                </td>
              </tr>
              <tr>
                <th>Source URI</th>
                <td className="mono table-cell-wrap">
                  {safeUri(source.source_uri)}
                </td>
              </tr>
              <tr>
                <th>SHA-256</th>
                <td className="mono table-cell-wrap">
                  {source.source_sha256 ?? "not recorded"}
                </td>
              </tr>
              <tr>
                <th>Provider window</th>
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
                <th>Notes</th>
                <td className="table-cell-wrap">
                  {safeText(source.notes)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {source.artifact_id ? (
          <p>
            <Link
              href={`/artifacts/${encodeURIComponent(
                source.artifact_id,
              )}`}
            >
              Open linked artifact provenance
            </Link>
          </p>
        ) : null}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Normalized usage</h2>
            <p>
              Provider usage rows retained independently from cost
              evidence.
            </p>
          </div>
          <span className="status">
            {formatNumber(detail.usage_rows.length)} rows
          </span>
        </div>

        {detail.usage_rows.length === 0 ? (
          <div className="placeholder-body">
            No normalized usage rows reference this source.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Context</th>
                  <th>Model / request</th>
                  <th>Input</th>
                  <th>Cache read</th>
                  <th>Cache create</th>
                  <th>Output</th>
                  <th>Requests</th>
                  <th>Allocation</th>
                  <th>Completeness</th>
                </tr>
              </thead>
              <tbody>
                {detail.usage_rows.map((row) => (
                  <tr key={row.evidence_id}>
                    <td className="table-cell-wrap">
                      {row.run_label ? (
                        <Link
                          href={`/runs/${encodeURIComponent(
                            row.run_label,
                          )}`}
                        >
                          {safeText(row.run_label)}
                        </Link>
                      ) : (
                        "unallocated"
                      )}
                      <div className="muted mono">
                        {safeText(row.arm_id)}
                      </div>
                      {row.trial_id ? (
                        <div>
                          <Link href={`/trials/${row.trial_id}`}>
                            trial
                          </Link>
                        </div>
                      ) : null}
                    </td>
                    <td className="table-cell-wrap">
                      {safeText(row.provider_model)}
                      <div className="muted mono">
                        {safeText(row.provider_request_id)}
                      </div>
                    </td>
                    <td>{tokenValue(row.ordinary_input_tokens)}</td>
                    <td>{tokenValue(row.cache_read_input_tokens)}</td>
                    <td>
                      {tokenValue(row.cache_creation_input_tokens)}
                    </td>
                    <td>{tokenValue(row.output_tokens)}</td>
                    <td>{formatNumber(row.request_count)}</td>
                    <td>{humanize(row.allocation_scope)}</td>
                    <td>
                      {humanize(row.completeness_status)}
                      {row.notes ? (
                        <div className="muted">
                          {safeText(row.notes)}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Normalized cost</h2>
            <p>
              Provider cost rows remain distinct from usage and from
              the later selected reconciliation authority.
            </p>
          </div>
          <span className="status">
            {formatNumber(detail.cost_rows.length)} rows
          </span>
        </div>

        {detail.cost_rows.length === 0 ? (
          <div className="placeholder-body">
            No normalized cost rows reference this source.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Context</th>
                  <th>Model</th>
                  <th>Cost kind</th>
                  <th>Amount</th>
                  <th>Allocation</th>
                  <th>Completeness</th>
                  <th>Pricing snapshot</th>
                </tr>
              </thead>
              <tbody>
                {detail.cost_rows.map((row) => (
                  <tr key={row.evidence_id}>
                    <td className="table-cell-wrap">
                      {row.run_label ? (
                        <Link
                          href={`/runs/${encodeURIComponent(
                            row.run_label,
                          )}`}
                        >
                          {safeText(row.run_label)}
                        </Link>
                      ) : (
                        "unallocated"
                      )}
                      <div className="muted mono">
                        {safeText(row.arm_id)}
                      </div>
                      {row.trial_id ? (
                        <div>
                          <Link href={`/trials/${row.trial_id}`}>
                            trial
                          </Link>
                        </div>
                      ) : null}
                    </td>
                    <td>{safeText(row.provider_model)}</td>
                    <td>{humanize(row.cost_kind)}</td>
                    <td>
                      {displayedCostAmount(
                        row.amount_usd,
                        row.currency,
                      )}
                    </td>
                    <td>{humanize(row.allocation_scope)}</td>
                    <td>
                      {humanize(row.completeness_status)}
                      {row.notes ? (
                        <div className="muted">
                          {safeText(row.notes)}
                        </div>
                      ) : null}
                    </td>
                    <td className="mono">
                      {safeText(row.pricing_snapshot_id)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Pricing snapshots</h2>
            <p>
              Time-aware normalized pricing evidence associated with
              this source.
            </p>
          </div>
          <span className="status">
            {formatNumber(detail.pricing_snapshots.length)} rows
          </span>
        </div>

        {detail.pricing_snapshots.length === 0 ? (
          <div className="placeholder-body">
            No pricing snapshot rows reference this source.
          </div>
        ) : (
          <div className="evidence-group-list">
            {detail.pricing_snapshots.map((row) => (
              <article
                className="evidence-group"
                key={row.pricing_snapshot_id}
              >
                <header className="evidence-group-header">
                  <div>
                    <h3>{safeText(row.provider_model)}</h3>
                    <p>{humanize(row.pricing_semantics)}</p>
                  </div>
                  <span className="quality-badge">
                    {safeText(row.currency)}
                  </span>
                </header>

                <div className="evidence-group-context">
                  <span>
                    effective {formatTimestamp(row.effective_from)}
                    {" → "}
                    {formatTimestamp(row.effective_until)}
                  </span>
                  <span className="mono">
                    {safeUri(row.official_source_uri)}
                  </span>
                </div>

                <details>
                  <summary>Normalized pricing rules</summary>
                  <pre className="artifact-preview">
                    {sanitizedRules(row.pricing_rules)}
                  </pre>
                </details>

                {row.notes ? (
                  <p>{safeText(row.notes)}</p>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Usage reconciliations</h2>
            <p>
              Independent usage authority, identity validation, and
              source-role decisions.
            </p>
          </div>
          <span className="status">
            {formatNumber(detail.usage_reconciliations.length)} rows
          </span>
        </div>

        {detail.usage_reconciliations.length === 0 ? (
          <div className="placeholder-body">
            This source is not attached to a usage reconciliation.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Context</th>
                  <th>Role</th>
                  <th>Validation</th>
                  <th>Model identity</th>
                  <th>Selected authority</th>
                  <th>Provider usage</th>
                  <th>Evidence sources</th>
                  <th>Limitations</th>
                </tr>
              </thead>
              <tbody>
                {detail.usage_reconciliations.map((row) => (
                  <tr
                    key={`${row.reconciliation_id}:${row.evidence_role}`}
                  >
                    <td className="table-cell-wrap">
                      {row.run_label ? (
                        <Link
                          href={`/runs/${encodeURIComponent(
                            row.run_label,
                          )}`}
                        >
                          {safeText(row.run_label)}
                        </Link>
                      ) : (
                        "—"
                      )}
                      <div className="muted mono">
                        {safeText(row.arm_id)}
                      </div>
                      <div className="muted">
                        {row.is_current ? "current" : "historical"}
                      </div>
                    </td>
                    <td>{humanize(row.evidence_role)}</td>
                    <td>{humanize(row.validation_status)}</td>
                    <td>
                      {humanize(row.model_identity_status)}
                      <div className="muted">
                        provider:{" "}
                        {safeText(row.provider_observed_model)}
                      </div>
                      <div className="muted">
                        harness:{" "}
                        {safeText(row.harness_observed_model)}
                      </div>
                    </td>
                    <td>
                      {humanize(row.selected_usage_authority)}
                    </td>
                    <td>
                      <div>
                        ordinary input:{" "}
                        {tokenValue(
                          row.provider_ordinary_input_tokens,
                        )}
                      </div>
                      <div>
                        cache read:{" "}
                        {tokenValue(
                          row.provider_cache_read_input_tokens,
                        )}
                      </div>
                      <div>
                        cache create:{" "}
                        {tokenValue(
                          row.provider_cache_creation_input_tokens,
                        )}
                      </div>
                      <div>
                        output:{" "}
                        {tokenValue(row.provider_output_tokens)}
                      </div>
                      <div>
                        requests:{" "}
                        {row.provider_request_count === null
                          ? "—"
                          : formatNumber(
                              row.provider_request_count,
                            )}
                      </div>
                    </td>
                    <td>
                      <EvidenceSourceChain
                        links={row.evidence_sources}
                        currentSourceId={source.source_id}
                      />
                    </td>
                    <td className="table-cell-wrap">
                      {limitationText(row.limitation_codes)}
                      {row.notes ? (
                        <div className="muted">
                          {safeText(row.notes)}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Cost reconciliations</h2>
            <p>
              Independent selected cost basis, relation, validation
              status, and limitations.
            </p>
          </div>
          <span className="status">
            {formatNumber(detail.cost_reconciliations.length)} rows
          </span>
        </div>

        {detail.cost_reconciliations.length === 0 ? (
          <div className="placeholder-body">
            This source is not attached to a cost reconciliation.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Context</th>
                  <th>Role</th>
                  <th>Validation</th>
                  <th>Selected cost</th>
                  <th>Evidence amounts</th>
                  <th>Evidence chain</th>
                  <th>Limitations</th>
                </tr>
              </thead>
              <tbody>
                {detail.cost_reconciliations.map((row) => (
                  <tr
                    key={`${row.reconciliation_id}:${row.evidence_role}`}
                  >
                    <td className="table-cell-wrap">
                      {row.run_label ? (
                        <Link
                          href={`/runs/${encodeURIComponent(
                            row.run_label,
                          )}`}
                        >
                          {safeText(row.run_label)}
                        </Link>
                      ) : (
                        "—"
                      )}
                      <div className="muted mono">
                        {safeText(row.arm_id)}
                      </div>
                      <div className="muted">
                        {row.is_current ? "current" : "historical"}
                      </div>
                    </td>
                    <td>{humanize(row.evidence_role)}</td>
                    <td>{humanize(row.validation_status)}</td>
                    <td>
                      <strong>
                        {costValue(row.selected_cost_usd)}
                      </strong>
                      <div>
                        {humanize(row.selected_cost_basis)}
                      </div>
                      <div className="muted">
                        relation:{" "}
                        {humanize(row.selected_cost_relation)}
                      </div>
                    </td>
                    <td>
                      <div>
                        provider billed:{" "}
                        {costValue(row.provider_billed_cost_usd)}
                      </div>
                      <div>
                        provider-rate reconstruction:{" "}
                        {costValue(
                          row.provider_rate_reconstructed_cost_usd,
                        )}
                      </div>
                      <div>
                        harness reported:{" "}
                        {costValue(
                          row.harness_reported_cost_usd,
                        )}
                      </div>
                    </td>
                    <td className="table-cell-wrap">
                      <EvidenceSourceChain
                        links={row.evidence_sources}
                        currentSourceId={source.source_id}
                      />

                      <div className="muted">
                        pricing snapshot:{" "}
                        {safeText(row.pricing_snapshot_id)}
                      </div>

                      {row.pricing_source_id ? (
                        <div>
                          pricing source:{" "}
                          <Link
                            href={`/provider-evidence/${encodeURIComponent(
                              row.pricing_source_id,
                            )}`}
                          >
                            {friendlyProviderLabel(
                              row.pricing_source_provider
                                ?? "unknown",
                            )}
                            {" · "}
                            {humanize(
                              row.pricing_source_evidence_kind,
                            )}
                          </Link>
                        </div>
                      ) : (
                        <div className="muted">
                          pricing source: not recorded
                        </div>
                      )}
                    </td>
                    <td className="table-cell-wrap">
                      {limitationText(row.limitation_codes)}
                      {row.notes ? (
                        <div className="muted">
                          {safeText(row.notes)}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AppShell>
  );
}
