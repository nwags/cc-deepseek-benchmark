import Link from "next/link";
import { TermInfo } from "./TermInfo";
import { formatNumber, formatPercent } from "../lib/format";

export type QualityContextData = {
  raw_pass_rate?: number | string | null;
  qualified_pass_rate?: number | string | null;
  trial_count?: number | string | null;
  success_count?: number | string | null;
  qualified_trial_count?: number | string | null;
  qualified_success_count?: number | string | null;
  suspect_noop_count?: number | string | null;
  exception_count?: number | string | null;
  normal_failed_count?: number | string | null;
};

export type SuspectNoopHrefFilters = {
  suite_id?: string | null;
  arm_id?: string | null;
  run_label?: string | null;
  task_id?: string | null;
};

function n(value: number | string | null | undefined) {
  return Number(value ?? 0);
}

export function buildSuspectNoopHref(filters: SuspectNoopHrefFilters = {}) {
  const params = new URLSearchParams();
  params.set("quality", "suspect_noop_zero_token");

  for (const key of ["suite_id", "arm_id", "run_label", "task_id"] as const) {
    const value = filters[key];
    if (value) {
      params.set(key, value);
    }
  }

  return `/trial-quality?${params.toString()}#suspect-noop-trials`;
}

export function hasQualityCaveat(row: QualityContextData | null | undefined) {
  return n(row?.suspect_noop_count) > 0;
}

export function QualityPassRate({
  row,
  compact = false
}: {
  row: QualityContextData | null | undefined;
  compact?: boolean;
}) {
  const suspect = n(row?.suspect_noop_count);
  const rawText = `${formatNumber(row?.success_count ?? 0)}/${formatNumber(row?.trial_count ?? 0)} · ${formatPercent(row?.raw_pass_rate ?? null)}`;

  if (!suspect) {
    return <span>{formatPercent(row?.raw_pass_rate ?? null)}</span>;
  }

  const qualifiedText = `${formatNumber(row?.qualified_success_count ?? 0)}/${formatNumber(row?.qualified_trial_count ?? 0)} · ${formatPercent(row?.qualified_pass_rate ?? null)}`;

  return (
    <span className="quality-pass-rate">
      <span><span className="term-label">raw <TermInfo term="Raw pass rate" /></span> {compact ? formatPercent(row?.raw_pass_rate ?? null) : rawText}</span>
      <span className="quality-qualified"><span className="term-label">qualified <TermInfo term="Qualified pass rate" /></span> {compact ? formatPercent(row?.qualified_pass_rate ?? null) : qualifiedText}</span>
      <Link className="quality-caveat-link" href={buildSuspectNoopHref()}>
        {formatNumber(suspect)} suspect no-op
      </Link>
    </span>
  );
}

export function QualityBadge({ count }: { count: number | string | null | undefined }) {
  const value = n(count);
  return (
    <span className={value > 0 ? "quality-badge quality-badge-warn" : "quality-badge"}>
      {formatNumber(value)}
    </span>
  );
}

export function QualityNotice({
  mode,
  suspectNoopCount,
  affectedFullRuns
}: {
  mode?: string | null;
  suspectNoopCount?: number | string | null;
  affectedFullRuns?: number | string | null;
}) {
  const suspect = n(suspectNoopCount);
  const affectedFull = n(affectedFullRuns);

  if (!suspect && mode !== "smoke" && mode !== "canary") {
    return null;
  }

  return (
    <section className="quality-context-panel">
      <strong>Result interpretation:</strong>{" "}
      {mode === "smoke" || mode === "canary" ? (
        <span>
          This is a diagnostic {mode} suite. Treat it as route/provider readiness evidence, not a definitive model-quality ranking.
        </span>
      ) : (
        <span>Raw benchmark results remain the source of truth.</span>
      )}{" "}
      {suspect > 0 ? (
        <span>
          This view includes <Link href="/trial-quality">{formatNumber(suspect)} suspect no-op zero-token trial{suspect === 1 ? "" : "s"}</Link>;
          show raw and qualified rates side by side where applicable.
        </span>
      ) : (
        <span>No suspect no-op zero-token trials are currently flagged in this view.</span>
      )}{" "}
      {affectedFull > 0 ? (
        <span>{formatNumber(affectedFull)} full-run arm execution{affectedFull === 1 ? "" : "s"} require review.</span>
      ) : null}
    </section>
  );
}
