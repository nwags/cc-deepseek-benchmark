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
    definition: "An eval suite is a named collection of Terminal-Bench evals. Phase 3 currently uses canary, smoke, and full suites to separate route validation from full benchmark comparisons."
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
    shortDefinition: "Evidence file uploaded to Cloudflare R2.",
    definition: "An R2 artifact is a benchmark evidence file uploaded to Cloudflare R2, such as result JSON, logs, trajectories, or other files collected during ingestion."
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
    shortDefinition: "The main Phase 3 benchmark suite.",
    definition: "A full sweep is the primary Phase 3 benchmark execution: the selected full suite of 20 Terminal-Bench tasks, usually with 3 attempts per task for each arm."
  },
  {
    term: "Logical mode",
    slug: "logical-mode",
    shortDefinition: "Sponsor-facing run type.",
    definition: "Logical mode is the dashboard/user-facing meaning of a run, such as canary, smoke, or full. A full run can still have storage_mode raw because of how Harbor stores full results."
  },
  {
    term: "Storage mode",
    slug: "storage-mode",
    shortDefinition: "Physical result directory mode.",
    definition: "Storage mode is the physical results directory or legacy ingestion key, such as raw, smoke, or canary. It is kept separate from logical mode to preserve idempotent ingestion."
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
  }
] as const satisfies readonly GlossaryEntry[];

export type GlossaryTerm = (typeof glossaryEntries)[number]["term"];

export function getGlossaryEntry(term: GlossaryTerm): GlossaryEntry {
  const entry = glossaryEntries.find((item) => item.term === term);
  if (!entry) {
    throw new Error(`Missing glossary entry: ${term}`);
  }
  return entry;
}
