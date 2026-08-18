export type ReviewedTrialFilterRow = Readonly<{
  trial_id: string;
  arm_id: string;
  run_label: string;
  task_id: string;
  raw_outcome: string;
  failure_subtype: string;
}>;

export type ReviewedTrialFilters = Readonly<{
  trialId: string;
  armId: string;
  runLabel: string;
  taskId: string;
  rawOutcome: string;
  failureSubtype: string;
}>;

export type ReviewedTrialFilterSelection = Readonly<{
  filters: ReviewedTrialFilters;
  repeatedFilterNames: readonly string[];
  warningMessage: string | null;
}>;

const FILTER_KEYS = Object.freeze([
  ["trial_id", "trialId"],
  ["trial_arm", "armId"],
  ["trial_run", "runLabel"],
  ["trial_task", "taskId"],
  ["trial_outcome", "rawOutcome"],
  ["trial_failure", "failureSubtype"],
] as const);
const FILTER_QUERY_KEYS = new Set<string>(FILTER_KEYS.map(([queryKey]) => queryKey));

export function selectReviewedTrialFilters(
  params: Readonly<Record<string, string | readonly string[] | undefined>>,
): ReviewedTrialFilterSelection {
  const selected: Record<string, string> = {};
  const repeatedFilterNames: string[] = [];
  for (const [queryKey, field] of FILTER_KEYS) {
    const value = params[queryKey];
    if (Array.isArray(value)) {
      selected[field] = "";
      repeatedFilterNames.push(queryKey);
    } else {
      selected[field] = typeof value === "string" ? value : "";
    }
  }
  return Object.freeze({
    filters: Object.freeze(selected as ReviewedTrialFilters),
    repeatedFilterNames: Object.freeze(repeatedFilterNames),
    warningMessage: repeatedFilterNames.length
      ? `Repeated reviewed-trial filters were ignored: ${repeatedFilterNames.join(", ")}.`
      : null,
  });
}

export function matchesReviewedTrial(
  row: ReviewedTrialFilterRow,
  filters: ReviewedTrialFilters,
): boolean {
  return (!filters.trialId || row.trial_id === filters.trialId)
    && (!filters.armId || row.arm_id === filters.armId)
    && (!filters.runLabel || row.run_label === filters.runLabel)
    && (!filters.taskId || row.task_id === filters.taskId)
    && (!filters.rawOutcome || row.raw_outcome === filters.rawOutcome)
    && (!filters.failureSubtype || row.failure_subtype === filters.failureSubtype);
}

export function sortReviewedTrialsById<T extends { trial_id: string }>(rows: readonly T[]): T[] {
  return [...rows].sort((left, right) => left.trial_id.localeCompare(right.trial_id));
}

export function buildReviewedTrialPageHref(
  rawParams: Readonly<Record<string, string | readonly string[] | undefined>>,
  filters: ReviewedTrialFilters,
  page: number,
  pageSize: number,
): string {
  const params = new URLSearchParams();
  for (const [key, rawValue] of Object.entries(rawParams)) {
    if (FILTER_QUERY_KEYS.has(key) || key === "trial_page" || key === "trial_page_size") continue;
    const values = Array.isArray(rawValue) ? rawValue : rawValue === undefined ? [] : [rawValue];
    for (const value of values) {
      if (value) params.append(key, value);
    }
  }
  for (const [queryKey, field] of FILTER_KEYS) {
    const value = filters[field];
    if (value) params.set(queryKey, value);
  }
  params.set("trial_page", String(page));
  params.set("trial_page_size", String(pageSize));
  return `/comprehensive-review?${params.toString()}#reviewed-trials`;
}
