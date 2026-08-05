export type GlossaryEntry = {
  term: string;
  slug: string;
  shortDefinition: string;
  definition: string;
};

export const glossaryEntries = [
  {
    term: "Arm",
    slug: "arm",
    shortDefinition: "A configured model/backend route being benchmarked.",
    definition: "An arm is one configured model backend or router route, such as router-gpt-5.4, router-deepseek-pro, or router-glm-5.2. Arms are what the benchmark compares."
  },
  {
    term: "Arm run",
    slug: "arm-run",
    shortDefinition: "One concrete execution of one arm.",
    definition: "An arm run is a specific execution of one arm against a canary, smoke, or full eval suite. It has its own trials, artifacts, cost records, status, and timestamps."
  },
  {
    term: "Eval",
    slug: "eval",
    shortDefinition: "One Terminal-Bench task.",
    definition: "An eval is one Terminal-Bench task, such as query-optimize or build-cython-ext. The dashboard compares how different arms perform on each eval."
  },
  {
    term: "Eval suite",
    slug: "eval-suite",
    shortDefinition: "A named group of evals.",
    definition: "An eval suite is a named collection of Terminal-Bench evals. Current benchmark imports use canary, smoke, and full suites to separate route validation from full benchmark comparisons."
  },
  {
    term: "Trial",
    slug: "trial",
    shortDefinition: "One attempt at one eval by one arm.",
    definition: "A trial is one benchmark attempt: one arm running one eval once. In the full suite, each imported arm runs 20 evals with 3 attempts each, for 60 trials."
  },
  {
    term: "Success",
    slug: "success",
    shortDefinition: "A trial with reward 1.",
    definition: "A success is a trial where the benchmark/verifier awarded reward 1. Failures and errored attempts are not counted as successes."
  },
  {
    term: "Pass rate",
    slug: "pass-rate",
    shortDefinition: "Successes divided by trials.",
    definition: "Pass rate is success_count divided by trial_count. For example, 39 successes out of 60 trials is a 65.0% pass rate."
  },
  {
    term: "Raw pass rate",
    slug: "raw-pass-rate",
    shortDefinition: "Successes divided by all imported trials.",
    definition: "Raw pass rate is successes divided by all imported trials. It remains the benchmark source of truth, including failed, errored, and suspect no-op trials."
  },
  {
    term: "Qualified pass rate",
    slug: "qualified-pass-rate",
    shortDefinition: "Diagnostic pass rate excluding suspect no-op exits.",
    definition: "Qualified pass rate is successes divided by trials after excluding suspect no-op zero-token exits. It is a diagnostic interpretation aid, especially for canary and smoke runs, and does not replace the raw benchmark result."
  },
  {
    term: "Suspect no-op zero-token",
    slug: "suspect-noop-zero-token",
    shortDefinition: "A failed trial with an empty zero-token agent result.",
    definition: "A suspect no-op zero-token trial is a failed trial with no exception, no recorded input or output tokens, no recorded cost, and an apparently empty completed agent result. Treat it as a possible route, provider, or harness anomaly until trajectory review confirms what happened."
  },
  {
    term: "Mean reward",
    slug: "mean-reward",
    shortDefinition: "Average reward across trials.",
    definition: "Mean reward is the average of trial rewards. For binary Terminal-Bench rewards it usually tracks pass rate, but missing or errored reward rows can make it differ from a simple successes/trials count."
  },
  {
    term: "Median runtime",
    slug: "median-runtime",
    shortDefinition: "Middle runtime among available trial runtimes.",
    definition: "Median runtime is the middle observed wall-clock runtime after sorting available trial runtimes. It is less sensitive to extreme outliers than the mean."
  },
  {
    term: "Recorded cost",
    slug: "recorded-cost",
    shortDefinition: "Known cost from rows where cost was captured.",
    definition: "Recorded cost is the sum of cost_usd values available in imported metadata. If missing cost rows exist, recorded cost should be treated as a lower bound rather than a complete provider bill."
  },
  {
    term: "Missing cost",
    slug: "missing-cost",
    shortDefinition: "Trials without captured cost metadata.",
    definition: "Missing cost means some trials did not have a cost_usd value in the imported result metadata. This can happen due to provider/router reporting gaps or failed/errored trials."
  },
  {
    term: "R2 artifact",
    slug: "r2-artifact",
    shortDefinition: "Benchmark evidence bytes stored in Cloudflare R2.",
    definition: "R2 stores benchmark evidence bytes such as result JSON, logs, transcripts, trajectories, and verifier outputs. Objects may be published progressively during supervised execution, by final canonical publication, or by a separately reviewed historical/operator ingestion path. Supabase stores the corresponding metadata and relationships."
  },
  {
    term: "Trajectory",
    slug: "trajectory",
    shortDefinition: "Detailed record of what the agent did.",
    definition: "A trajectory is supporting evidence showing the agent's behavior during a trial: tool calls, outputs, intermediate decisions, logs, and related execution traces when available."
  },
  {
    term: "Canary",
    slug: "canary",
    shortDefinition: "Smallest route validation run.",
    definition: "A canary is a minimal benchmark run used to check that a provider route, credentials, model mapping, and ingestion path are basically working before spending more time or money."
  },
  {
    term: "Smoke",
    slug: "smoke",
    shortDefinition: "Small validation suite before full sweep.",
    definition: "A smoke suite is a small set of representative evals used to validate model/router behavior before launching a full sweep."
  },
  {
    term: "Full sweep",
    slug: "full-sweep",
    shortDefinition: "The main full benchmark suite.",
    definition: "A full sweep is the primary benchmark execution: the selected full suite of Terminal-Bench tasks, usually with 3 attempts per task for each arm."
  },
  {
    term: "Benchmark run class",
    slug: "benchmark-run-class",
    shortDefinition: "User-facing interpretation of a benchmark execution.",
    definition: "Benchmark run class describes the user-facing interpretation of an execution, such as canary, smoke, full, ad-hoc, diagnostic, or dry-run where applicable."
  },
  {
    term: "Result source/storage location",
    slug: "result-source-storage-location",
    shortDefinition: "Where result evidence originated or is retained.",
    definition: "Result source/storage location identifies where result evidence originated or is retained, including Harbor or local result directories, live Supabase state, canonical Supabase records, Cloudflare R2 objects, and historical file-backed snapshots."
  },
  {
    term: "Logical mode",
    slug: "logical-mode",
    shortDefinition: "Internal compatibility field for benchmark run class.",
    definition: "logical_mode is an internal field used to represent benchmark run class, such as canary, smoke, full, or ad-hoc. It remains documented for compatibility with stored metadata and ingestion code."
  },
  {
    term: "Storage mode",
    slug: "storage-mode",
    shortDefinition: "Internal compatibility field for result-directory storage.",
    definition: "storage_mode is an internal field used for the physical result-directory or legacy ingestion key, such as raw, smoke, or canary. It remains separate from benchmark run class to preserve compatibility and idempotent ingestion."
  },
  {
    term: "Trial errors",
    slug: "trial-errors",
    shortDefinition: "Failures inside benchmark attempts.",
    definition: "Trial errors mean some benchmark attempts failed or raised exceptions. This does not necessarily mean ingestion failed or the arm run is unusable."
  },
  {
    term: "Imported with trial errors",
    slug: "imported-with-trial-errors",
    shortDefinition: "Run imported, but some attempts failed.",
    definition: "Imported with trial errors means the run metadata and artifacts were imported, but one or more benchmark trials failed, errored, or did not produce complete cost/reward metadata."
  },

  {
    term: "Adjusted known cost",
    slug: "adjusted-known-cost",
    shortDefinition: "Recorded cost plus reconstructed missing-cost estimates.",
    definition: "Adjusted known cost is recorded cost plus missing-cost rows that could be reconstructed from configured pricing snapshots or same-arm empirical estimates. It is the preferred benchmark cost for reviewed benchmark comparisons, while still preserving cost-source confidence."
  },
  {
    term: "Known accounting gap",
    slug: "known-accounting-gap",
    shortDefinition: "The difference between adjusted known cost and recorded cost.",
    definition: "Known accounting gap is adjusted known cost minus recorded cost. It quantifies how much the raw recorded-cost dashboard understated spend because some trials had usage or cost evidence that was not captured in cost_usd."
  },
  {
    term: "Failure/incomplete spend",
    slug: "failure-incomplete-spend",
    shortDefinition: "Adjusted cost spent on trials that did not produce a passing result.",
    definition: "Failure/incomplete spend is adjusted known cost for normal failures, exception failures, and unknown or incomplete outcomes. It is useful for quantifying money spent on non-passing benchmark attempts."
  },
  {
    term: "Unclean spend share",
    slug: "unclean-spend-share",
    shortDefinition: "Share of adjusted spend not attributable to clean successes.",
    definition: "Unclean spend share is the portion of adjusted known cost spent on failures, incomplete outcomes, and exception-with-success-signal rows. It is broader than failure/incomplete spend share because it treats exception-with-success-signal rows as operationally unclean even when reward is 1."
  },
  {
    term: "Cost per clean success",
    slug: "cost-per-clean-success",
    shortDefinition: "Adjusted known cost divided by clean successes.",
    definition: "Cost per clean success divides adjusted known cost by the number of trials with reward 1 and no exception marker. It is stricter than cost per any success because it excludes exception-with-success-signal rows from the denominator."
  },
  {
    term: "Exception with success signal",
    slug: "exception-with-success-signal",
    shortDefinition: "A trial with reward 1 and an exception marker.",
    definition: "Exception with success signal means the verifier reward was 1, but the trial also carried an exception marker. These rows are kept separate from clean successes because they may be correct by verifier outcome but operationally unclean."
  },

] as const satisfies readonly GlossaryEntry[];

export type GlossaryTerm = (typeof glossaryEntries)[number]["term"];

export function getGlossaryEntry(term: GlossaryTerm): GlossaryEntry {
  const entry = glossaryEntries.find((item) => item.term === term);
  if (!entry) {
    throw new Error(`Missing glossary entry: ${term}`);
  }
  return entry;
}
