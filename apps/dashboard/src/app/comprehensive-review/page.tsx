import Link from "next/link";
import { AppShell } from "../../components/AppShell";
import { EvidenceSourceContextNotice } from "../../components/EvidenceSourceContextNotice";
import { getComprehensiveReviewData, ReviewQueueRow } from "../../lib/review-data";
import {
  buildExactTrialHref,
  buildReviewedTrialEvidenceHref,
  selectEvidenceSourceScope,
} from "../../lib/evidence-links";
import { formatNumber } from "../../lib/format";
import {
  buildReviewedTrialPageHref,
  matchesReviewedTrial,
  selectReviewedTrialFilters,
  sortReviewedTrialsById,
} from "../../lib/reviewed-trial-filters";
import { sanitizeEvidenceText } from "../../lib/safe-display";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
const first = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] ?? "" : value ?? "";
const safe = (value: string | null | undefined) => sanitizeEvidenceText(value) ?? "not recorded";

function parsedTrialLinks(value: string) {
  try {
    const links = JSON.parse(value) as unknown;
    return Array.isArray(links) ? links.filter((item): item is string => typeof item === "string").slice(0, 6) : [];
  } catch { return []; }
}

function matchesQueue(row: ReviewQueueRow, filters: Record<string, string>) {
  return (!filters.priority || filters.priority === "all" || row.manual_review_priority === filters.priority)
    && (!filters.arm || row.arm_id === filters.arm)
    && (!filters.task || row.task_id === filters.task)
    && (!filters.reason || row.review_reasons.split(";").includes(filters.reason))
    && (!filters.stratum || row.review_strata.split(";").includes(filters.stratum));
}

function options(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort();
}

function pageSize(value: string, fallback = 25) {
  const parsed = Number(value);
  return [25, 50, 100].includes(parsed) ? parsed : fallback;
}

function positivePage(value: string) {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1;
}

function pageHref(params: Record<string, string | string[] | undefined>, updates: Record<string, string | number>) {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const values = Array.isArray(value) ? value : value === undefined ? [] : [value];
    for (const selected of values) {
      if (selected) next.append(key, selected);
    }
  }
  for (const [key, value] of Object.entries(updates)) next.set(key, String(value));
  return `/comprehensive-review?${next.toString()}`;
}

function matchesDisagreement(row: Record<string, string>, filters: Record<string, string>) {
  const outcomeA = row.arm_a_raw_outcome_summary || row.arm_a_raw_outcome;
  const outcomeB = row.arm_b_raw_outcome_summary || row.arm_b_raw_outcome;
  return (!filters.arm || row.arm_a === filters.arm || row.arm_b === filters.arm)
    && (!filters.task || row.task_id === filters.task)
    && (!filters.category || row.disagreement_category === filters.category)
    && (!filters.outcome || outcomeA.split(";").some((item) => item.startsWith(`${filters.outcome}:`)) || outcomeB.split(";").some((item) => item.startsWith(`${filters.outcome}:`)))
    && (!filters.policy || row.arm_a_policy_summary.includes(filters.policy) || row.arm_b_policy_summary.includes(filters.policy));
}

export default async function ComprehensiveReviewPage({ searchParams }: { searchParams?: SearchParams }) {
  const params = searchParams ? await searchParams : {};
  const sourceScopeSelection = selectEvidenceSourceScope(params.source_scope);
  const reviewedSourceScope = sourceScopeSelection.sourceScope ?? "phase3-extended";
  const trialFilterSelection = selectReviewedTrialFilters(params);
  const trialFilters = trialFilterSelection.filters;
  const trialPageSize = pageSize(first(params.trial_page_size));
  const requestedTrialPage = positivePage(first(params.trial_page));
  const filters = {
    priority: first(params.priority) || "high",
    arm: first(params.arm), task: first(params.task), reason: first(params.reason), stratum: first(params.stratum)
  };
  const queuePageSize = pageSize(first(params.queue_page_size));
  const requestedQueuePage = positivePage(first(params.queue_page));
  const disagreementFilters = {
    arm: first(params.disagreement_arm), task: first(params.disagreement_task),
    category: first(params.disagreement_category), outcome: first(params.disagreement_outcome),
    policy: first(params.disagreement_policy)
  };
  const disagreementPageSize = pageSize(first(params.disagreement_page_size));
  const requestedDisagreementPage = positivePage(first(params.disagreement_page));
  const review = await getComprehensiveReviewData();
  const coverage = review.coverage;
  const matchingReviewedTrials = sortReviewedTrialsById(
    review.reviewedTrials.filter((row) => matchesReviewedTrial(row, trialFilters)),
  );
  const trialPageCount = Math.max(Math.ceil(matchingReviewedTrials.length / trialPageSize), 1);
  const trialPage = Math.min(requestedTrialPage, trialPageCount);
  const trialStart = (trialPage - 1) * trialPageSize;
  const reviewedTrials = matchingReviewedTrials.slice(trialStart, trialStart + trialPageSize);
  const matchingQueue = review.queue.filter((row) => matchesQueue(row, filters));
  const queuePageCount = Math.max(Math.ceil(matchingQueue.length / queuePageSize), 1);
  const queuePage = Math.min(requestedQueuePage, queuePageCount);
  const queueStart = (queuePage - 1) * queuePageSize;
  const queue = matchingQueue.slice(queueStart, queueStart + queuePageSize);
  const matchingDisagreements = review.disagreements.filter((row) => matchesDisagreement(row, disagreementFilters));
  const disagreementPageCount = Math.max(Math.ceil(matchingDisagreements.length / disagreementPageSize), 1);
  const disagreementPage = Math.min(requestedDisagreementPage, disagreementPageCount);
  const disagreementStart = (disagreementPage - 1) * disagreementPageSize;
  const disagreements = matchingDisagreements.slice(disagreementStart, disagreementStart + disagreementPageSize);
  const reasons = options(review.queue.flatMap((row) => row.review_reasons.split(";")));
  const strata = options(review.queue.flatMap((row) => row.review_strata.split(";")));

  return (
    <AppShell title="Comprehensive evidence review" description="Manifest-validated derived snapshot across outcome, execution, activity, policy, telemetry, integrity, and retained evidence.">
      <section className="quality-context-panel">
        This view never changes benchmark rewards, pass rates, denominators, quality flags, Supabase rows, or immutable R2 artifacts. Snapshot labels remain evidence-conditioned and manually reviewable.
      </section>
      <EvidenceSourceContextNotice value={params.source_scope} />

      {!review.available || !coverage ? (
        <section className="panel warning-panel">
          <div className="panel-heading"><div><h2>Review snapshot {safe(review.state.replaceAll("_", " "))}</h2><p>{safe(review.message)}</p></div></div>
          <div className="placeholder-body">The dashboard will not mix or display unvalidated comprehensive-review files.</div>
        </section>
      ) : <>
        <section className="panel">
          <div className="panel-heading">
            <div><h2>Review coverage <span className="derived-label">validated snapshot</span></h2><p>Analyzer {safe(coverage.analyzer_version)} · generated {safe(coverage.generated_at)}</p></div>
            <span className="quality-badge">{formatNumber(coverage.trials_reviewed)} trials reviewed</span>
          </div>
          <div className="diagnosis-grid">
            <article><span>Runs reviewed</span><strong>{coverage.valid_runs_reviewed}</strong><small>{coverage.runs_discovered} full-suite candidates discovered</small></article>
            <article><span>Evidence complete</span><strong>{coverage.complete_evidence_trials}</strong><small>{coverage.incomplete_evidence_trials} incomplete or ambiguous</small></article>
            <article><span>Confidence</span><strong>{coverage.confidence.high ?? 0} high</strong><small>{coverage.confidence.medium ?? 0} medium · {coverage.confidence.low ?? 0} low · {coverage.confidence.unknown ?? 0} unknown</small></article>
            <article><span>Review queue size</span><strong>{coverage.manual_review_queue}</strong><small>This count is backed by the filtered queue below.</small></article>
            <article><span>Task disagreements</span><strong>{coverage.task_disagreement_rows}</strong><small>Arm-specific evidence summaries</small></article>
            <article><span>Targeted packet</span><strong>{coverage.targeted_evidence_packet ?? 0}</strong><small>Safe derived evidence rows</small></article>
          </div>
          <p className="muted">Manifest {safe(review.manifest?.schema_version)} · generator {safe(review.manifest?.generator_version)} · scope {safe(review.manifest?.scope_fingerprint.slice(0, 12))}…</p>
        </section>

        <section className="panel" id="reviewed-trials">
          <div className="panel-heading">
            <div>
              <h2>Reviewed trial results</h2>
              <p>Exact filters over the manifest-validated frozen comprehensive-review population.</p>
            </div>
            <span className="quality-badge">{formatNumber(review.reviewedTrials.length)} frozen trials</span>
          </div>
          <div className="quality-context-panel">
            This is the complete frozen reviewed-trial result surface, not the {formatNumber(coverage.manual_review_queue)}-row manual-review queue below.
            Filtering does not modify raw benchmark results, rerun the analyzer/classifier, or change J2.
          </div>
          {trialFilterSelection.warningMessage ? (
            <p className="warning-text" role="alert">{trialFilterSelection.warningMessage}</p>
          ) : null}
          <form className="filter-grid" method="get" action="/comprehensive-review#reviewed-trials">
            <input type="hidden" name="trial_page" value="1" />
            {sourceScopeSelection.sourceScope ? <input type="hidden" name="source_scope" value={sourceScopeSelection.sourceScope} /> : null}
            <label>Trial ID<input name="trial_id" defaultValue={trialFilters.trialId} /></label>
            <label>Arm<select name="trial_arm" defaultValue={trialFilters.armId}><option value="">All arms</option>{options(review.reviewedTrials.map((row) => row.arm_id)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Run<select name="trial_run" defaultValue={trialFilters.runLabel}><option value="">All runs</option>{options(review.reviewedTrials.map((row) => row.run_label)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Task<select name="trial_task" defaultValue={trialFilters.taskId}><option value="">All tasks</option>{options(review.reviewedTrials.map((row) => row.task_id)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Raw outcome<select name="trial_outcome" defaultValue={trialFilters.rawOutcome}><option value="">All outcomes</option>{options(review.reviewedTrials.map((row) => row.raw_outcome)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Failure subtype<select name="trial_failure" defaultValue={trialFilters.failureSubtype}><option value="">All failure subtypes</option>{options(review.reviewedTrials.map((row) => row.failure_subtype)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Rows per page<select name="trial_page_size" defaultValue={String(trialPageSize)}>{[25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
            <button type="submit">Apply reviewed-trial filters</button><Link href={buildReviewedTrialEvidenceHref({}, sourceScopeSelection.sourceScope)}>Clear reviewed-trial filters</Link>
          </form>
          <p className="muted">Displaying {matchingReviewedTrials.length ? trialStart + 1 : 0}–{trialStart + reviewedTrials.length} of {matchingReviewedTrials.length} exact matching frozen rows.</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th className="sticky-id-column">Trial</th><th>Arm</th><th>Run</th><th>Task</th><th>Raw outcome</th><th>Failure subtype</th><th>Execution / activity</th><th>Confidence / review</th></tr></thead>
              <tbody>{reviewedTrials.map((row) => <tr key={row.trial_id}>
                <td className="sticky-id-column mono"><Link href={buildExactTrialHref(row.trial_id, reviewedSourceScope)}>{safe(row.trial_id)}</Link></td>
                <td className="mono">{safe(row.arm_id)}</td>
                <td className="mono">{safe(row.run_label)}</td>
                <td className="mono">{safe(row.task_id)}</td>
                <td>{safe(row.raw_outcome)}</td>
                <td>{safe(row.failure_subtype)}</td>
                <td>{safe(row.execution_validity)} / {safe(row.activity_subtype)}</td>
                <td>{safe(row.classification_confidence)} / manual review {safe(row.manual_review_required)}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <nav className="pagination" aria-label="Reviewed trial results pagination">
            {trialPage > 1 ? <Link href={buildReviewedTrialPageHref(params, trialFilters, trialPage - 1, trialPageSize)}>Previous</Link> : <span>Previous</span>}
            <span>Page {trialPage} of {trialPageCount}</span>
            {trialPage < trialPageCount ? <Link href={buildReviewedTrialPageHref(params, trialFilters, trialPage + 1, trialPageSize)}>Next</Link> : <span>Next</span>}
          </nav>
        </section>

        <section className="panel">
          <div className="panel-heading"><div><h2>High-priority review queue and case filters</h2><p>Correctness anomalies, telemetry/integrity cases, disagreements, and high-cost failures are independent, overlapping strata. The default filter is high priority.</p></div></div>
          <div className="diagnosis-grid">
            {Object.entries(coverage.review_queue_strata ?? {}).map(([key, count]) => <article key={key}><span>{safe(key.replaceAll("_", " "))}</span><strong>{count}</strong></article>)}
          </div>
          <form className="filter-grid" method="get">
            <input type="hidden" name="queue_page" value="1" />
            <label>Priority<select name="priority" defaultValue={filters.priority}><option value="all">All</option>{["high", "medium", "low"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label>Arm<select name="arm" defaultValue={filters.arm}><option value="">All arms</option>{options(review.queue.map((row) => row.arm_id)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Task<select name="task" defaultValue={filters.task}><option value="">All tasks</option>{options(review.queue.map((row) => row.task_id)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Reason<select name="reason" defaultValue={filters.reason}><option value="">All reasons</option>{reasons.map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Stratum<select name="stratum" defaultValue={filters.stratum}><option value="">All strata</option>{strata.map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Rows per page<select name="queue_page_size" defaultValue={String(queuePageSize)}>{[25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
            <button type="submit">Apply filters</button><Link href="/comprehensive-review?priority=all">Clear</Link>
          </form>
          <p className="muted">Displaying {matchingQueue.length ? queueStart + 1 : 0}–{queueStart + queue.length} of {matchingQueue.length} matching rows; default view is the high-priority queue.</p>
          <div className="table-wrap"><table><thead><tr><th className="sticky-id-column">Trial</th><th>Priority</th><th>Arm</th><th>Task</th><th>Strata</th><th>Reasons</th></tr></thead><tbody>
            {queue.map((row) => <tr key={row.trial_id}><td className="sticky-id-column mono"><Link href={buildExactTrialHref(row.trial_id, reviewedSourceScope)}>{safe(row.trial_id)}</Link></td><td><span className={row.manual_review_priority === "high" ? "quality-badge quality-badge-warn" : "quality-badge"}>{safe(row.manual_review_priority)}</span></td><td className="mono">{safe(row.arm_id)}</td><td className="mono">{safe(row.task_id)}</td><td>{safe(row.review_strata.replaceAll(";", ", "))}</td><td>{safe(row.review_reasons.replaceAll(";", ", "))}</td></tr>)}
          </tbody></table></div>
          <nav className="pagination" aria-label="Review queue pagination">
            {queuePage > 1 ? <Link href={pageHref(params, { queue_page: queuePage - 1, queue_page_size: queuePageSize })}>Previous</Link> : <span>Previous</span>}
            <span>Page {queuePage} of {queuePageCount}</span>
            {queuePage < queuePageCount ? <Link href={pageHref(params, { queue_page: queuePage + 1, queue_page_size: queuePageSize })}>Next</Link> : <span>Next</span>}
          </nav>
        </section>

        <section className="panel">
          <div className="panel-heading"><div><h2>Control strata</h2><p>Strict ordinary controls are separate from timeout, telemetry-mismatch, exception-success, and incomplete-evidence controls.</p></div></div>
          <div className="diagnosis-grid">{Object.entries(coverage.manual_control_strata ?? {}).map(([key, count]) => <article key={key}><span>{safe(key.replaceAll("_", " "))}</span><strong>{count}</strong></article>)}</div>
          <div className="table-wrap"><table><thead><tr><th className="sticky-id-column">Trial</th><th>Stratum</th><th>Arm</th><th>Task</th></tr></thead><tbody>{review.controls.slice(0, 250).map((row) => <tr key={`${row.sample_stratum}-${row.trial_id}`}><td className="sticky-id-column mono"><Link href={buildExactTrialHref(row.trial_id, reviewedSourceScope)}>{safe(row.trial_id)}</Link></td><td>{safe(row.sample_stratum.replaceAll("_", " "))}</td><td className="mono">{safe(row.arm_id)}</td><td className="mono">{safe(row.task_id)}</td></tr>)}</tbody></table></div>
        </section>

        <section className="panel">
          <div className="panel-heading"><div><h2>Arm summaries</h2><p>Fixed-corpus classifications, not replacement pass rates.</p></div></div>
          <div className="table-wrap"><table><thead><tr><th>Arm</th><th>Reviewed</th><th>Substantive success</th><th>Substantive failure</th><th>Policy</th><th>Empty</th><th>Timeout</th><th>Setup/transport</th><th>Telemetry</th><th>Unknown</th><th>Queue</th></tr></thead><tbody>{review.arms.map((arm) => <tr key={arm.arm_id}><th className="mono">{safe(arm.arm_id)}</th><td>{arm.trials_reviewed}</td><td>{arm.substantive_successes}</td><td>{arm.substantive_failures}</td><td>{arm.policy_refusals}</td><td>{arm.empty_completions}</td><td>{arm.timeouts}</td><td>{arm.setup_transport_failures}</td><td>{arm.telemetry_mismatches}</td><td>{arm.unknown_classifications}</td><td>{arm.manual_review_queue}</td></tr>)}</tbody></table></div>
        </section>

        <section className="panel">
          <div className="panel-heading"><div><h2>Task disagreements</h2><p>Categories use arm-specific activity, policy, timeout, setup/transport, and verifier summaries.</p></div></div>
          <form className="filter-grid" method="get">
            <input type="hidden" name="priority" value={filters.priority} />
            <input type="hidden" name="disagreement_page" value="1" />
            <label>Arm<select name="disagreement_arm" defaultValue={disagreementFilters.arm}><option value="">All arms</option>{options(review.disagreements.flatMap((row) => [row.arm_a, row.arm_b])).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Task<select name="disagreement_task" defaultValue={disagreementFilters.task}><option value="">All tasks</option>{options(review.disagreements.map((row) => row.task_id)).map((value) => <option key={value} value={value}>{safe(value)}</option>)}</select></label>
            <label>Category<select name="disagreement_category" defaultValue={disagreementFilters.category}><option value="">All categories</option>{options(review.disagreements.map((row) => row.disagreement_category)).map((value) => <option key={value} value={value}>{safe(value.replaceAll("_", " "))}</option>)}</select></label>
            <label>Outcome<select name="disagreement_outcome" defaultValue={disagreementFilters.outcome}><option value="">All outcomes</option>{["success", "failure", "not_recorded"].map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label>Policy<select name="disagreement_policy" defaultValue={disagreementFilters.policy}><option value="">All policy states</option>{["provider_policy_refusal", "none_detected"].map((value) => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
            <label>Rows per page<select name="disagreement_page_size" defaultValue={String(disagreementPageSize)}>{[25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
            <button type="submit">Apply disagreement filters</button><Link href={pageHref(params, { disagreement_arm: "", disagreement_task: "", disagreement_category: "", disagreement_outcome: "", disagreement_policy: "", disagreement_page: 1 })}>Clear disagreement filters</Link>
          </form>
          <p className="muted">Displaying {matchingDisagreements.length ? disagreementStart + 1 : 0}–{disagreementStart + disagreements.length} of {matchingDisagreements.length} matching disagreement rows.</p>
          <div className="table-wrap"><table><thead><tr><th>Task</th><th>Pair</th><th>Category</th><th>Raw outcomes</th><th>Activity</th><th>Policy / timeout / setup / verifier</th><th>Evidence</th></tr></thead><tbody>{disagreements.map((row, index) => {
            const links = parsedTrialLinks(row.supporting_trial_links);
            return <tr key={`${row.task_id}-${row.arm_a}-${row.arm_b}-${index}`}><th>{safe(row.task_id)}</th><td className="mono">{safe(row.arm_a)}<br />{safe(row.arm_b)}</td><td>{safe(row.disagreement_category.replaceAll("_", " "))}</td><td>{safe(row.arm_a_raw_outcome_summary ?? row.arm_a_raw_outcome)}<br />{safe(row.arm_b_raw_outcome_summary ?? row.arm_b_raw_outcome)}</td><td className="mono">{safe(row.arm_a_activity_summary)}<br />{safe(row.arm_b_activity_summary)}</td><td className="mono">policy {safe(row.arm_a_policy_summary)} / {safe(row.arm_b_policy_summary)}<br />timeout {safe(row.arm_a_timeout_summary)} / {safe(row.arm_b_timeout_summary)}<br />setup {safe(row.arm_a_setup_transport_summary)} / {safe(row.arm_b_setup_transport_summary)}<br />verifier {safe(row.arm_a_verifier_summary)} / {safe(row.arm_b_verifier_summary)}</td><td>{links.map((link, i) => <span key={link}><Link href={link}>trial {i + 1}</Link>{i < links.length - 1 ? " · " : ""}</span>)}</td></tr>;
          })}</tbody></table></div>
          <nav className="pagination" aria-label="Task disagreement pagination">
            {disagreementPage > 1 ? <Link href={pageHref(params, { disagreement_page: disagreementPage - 1, disagreement_page_size: disagreementPageSize })}>Previous</Link> : <span>Previous</span>}
            <span>Page {disagreementPage} of {disagreementPageCount}</span>
            {disagreementPage < disagreementPageCount ? <Link href={pageHref(params, { disagreement_page: disagreementPage + 1, disagreement_page_size: disagreementPageSize })}>Next</Link> : <span>Next</span>}
          </nav>
        </section>

        <section className="panel"><div className="panel-heading"><div><h2>Interpretation boundary</h2></div></div><div className="placeholder-body">Raw end-to-end, execution-qualified, and inference-conditioned rates remain future separate views. No aggregate rate or denominator is changed here.</div></section>
      </>}
    </AppShell>
  );
}
