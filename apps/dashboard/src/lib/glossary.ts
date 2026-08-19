export type GlossaryEntry = {
  term: string;
  slug: string;
  shortDefinition: string;
  definition: string;
  links?: readonly {
    href: string;
    label: string;
  }[];
};

export const glossaryEntries = [
  {
    term: "Arm",
    slug: "arm",
    shortDefinition: "A configured model/backend route being benchmarked.",
    definition: "An arm is one configured model backend or router route, such as router-gpt-5.4, router-deepseek-pro, or router-glm-5.2. Arms are what the benchmark compares.",
    links: [{ href: "/arms", label: "Open Arms" }]
  },
  {
    term: "Arm run",
    slug: "arm-run",
    shortDefinition: "One concrete execution of one arm.",
    definition: "An arm run is a specific execution of one arm against a canary, smoke, or full eval suite. It has its own trials, artifacts, cost records, status, and timestamps.",
    links: [{ href: "/runs", label: "Open Runs" }]
  },
  {
    term: "Eval",
    slug: "eval",
    shortDefinition: "One Terminal-Bench task.",
    definition: "An eval is one Terminal-Bench task, such as query-optimize or build-cython-ext. The dashboard compares how different arms perform on each eval.",
    links: [{ href: "/evals", label: "Open Evals" }]
  },
  {
    term: "Eval suite",
    slug: "eval-suite",
    shortDefinition: "A named group of evals.",
    definition: "An eval suite is a named collection of Terminal-Bench evals. Current benchmark imports use canary, smoke, and full suites to separate route validation from full benchmark comparisons.",
    links: [{ href: "/eval-suites", label: "Open Eval Suites" }]
  },
  {
    term: "Trial",
    slug: "trial",
    shortDefinition: "One attempt at one eval by one arm.",
    definition: "A trial is one benchmark attempt: one arm running one eval once. In the full suite, each imported arm runs 20 evals with 3 attempts each, for 60 trials.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
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
    definition: "Raw pass rate is successes divided by all imported trials. It remains the benchmark source of truth, including failed, errored, and suspect no-op trials.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
  },
  {
    term: "Qualified pass rate",
    slug: "qualified-pass-rate",
    shortDefinition: "Diagnostic pass rate excluding suspect no-op exits.",
    definition: "Qualified pass rate is successes divided by trials after excluding suspect no-op zero-token exits. It is a diagnostic interpretation aid, especially for canary and smoke runs, and does not replace the raw benchmark result.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
  },
  {
    term: "Suspect no-op zero-token",
    slug: "suspect-noop-zero-token",
    shortDefinition: "A failed trial with an empty zero-token agent result.",
    definition: "A suspect no-op zero-token trial is a failed trial with no exception, no recorded input or output tokens, no recorded cost, and an apparently empty completed agent result. Treat it as a possible route, provider, or harness anomaly until trajectory review confirms what happened.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
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
    definition: "Recorded cost is the sum of cost_usd values available in imported metadata. If missing cost rows exist, recorded cost should be treated as a lower bound rather than a complete provider bill.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Missing cost",
    slug: "missing-cost",
    shortDefinition: "Trials without captured cost metadata.",
    definition: "Missing cost means some trials did not have a cost_usd value in the imported result metadata. This can happen due to provider/router reporting gaps or failed/errored trials.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "R2 artifact",
    slug: "r2-artifact",
    shortDefinition: "Benchmark evidence bytes stored in Cloudflare R2.",
    definition: "R2 stores benchmark evidence bytes such as result JSON, logs, transcripts, trajectories, and verifier outputs. Objects may be published progressively during supervised execution, by final canonical publication, or by a separately reviewed historical/operator ingestion path. Supabase stores the corresponding metadata and relationships.",
    links: [
      { href: "/artifacts", label: "Open Artifacts" },
      { href: "/data-model", label: "Open Data Model" }
    ]
  },
  {
    term: "Trajectory",
    slug: "trajectory",
    shortDefinition: "Detailed record of what the agent did.",
    definition: "A trajectory is supporting evidence showing the agent's observable behavior during a trial: tool calls, outputs, logs, and related execution traces when available. Private model reasoning is not exposed.",
    links: [{ href: "/artifacts", label: "Open Artifacts" }]
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
    definition: "Benchmark run class describes the user-facing interpretation of an execution, such as canary, smoke, full, ad-hoc, diagnostic, or dry-run where applicable.",
    links: [
      { href: "/runs", label: "Open Runs" },
      { href: "/architecture", label: "Open Architecture" }
    ]
  },
  {
    term: "Result source/storage location",
    slug: "result-source-storage-location",
    shortDefinition: "Where result evidence originated or is retained.",
    definition: "Result source/storage location identifies where result evidence originated or is retained, including Harbor or local result directories, live Supabase state, canonical Supabase records, Cloudflare R2 objects, and historical file-backed snapshots.",
    links: [{ href: "/data-model", label: "Open Data Model" }]
  },
  {
    term: "Logical mode",
    slug: "logical-mode",
    shortDefinition: "Internal compatibility field for benchmark run class.",
    definition: "logical_mode is an internal field used to represent benchmark run class, such as canary, smoke, full, or ad-hoc execution intent. It remains documented for compatibility with stored metadata and ingestion code; Benchmark run class remains the public primary label.",
    links: [{ href: "/data-model", label: "Open Data Model" }]
  },
  {
    term: "Storage mode",
    slug: "storage-mode",
    shortDefinition: "Internal compatibility field for result-directory storage.",
    definition: "storage_mode is an internal field used for the physical result-directory or legacy ingestion key, such as raw, smoke, or canary. It remains separate from the public Result source/storage location label to preserve compatibility and idempotent ingestion.",
    links: [{ href: "/data-model", label: "Open Data Model" }]
  },
  {
    term: "Trial errors",
    slug: "trial-errors",
    shortDefinition: "Failures inside benchmark attempts.",
    definition: "Trial errors mean some benchmark attempts failed or raised exceptions. This does not necessarily mean ingestion failed or the arm run is unusable.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
  },
  {
    term: "Imported with trial errors",
    slug: "imported-with-trial-errors",
    shortDefinition: "Run imported, but some attempts failed.",
    definition: "Imported with trial errors means the run metadata and artifacts were imported, but one or more benchmark trials failed, errored, or did not produce complete cost/reward metadata.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
  },

  {
    term: "Adjusted known cost",
    slug: "adjusted-known-cost",
    shortDefinition: "Recorded cost plus reconstructed missing-cost estimates.",
    definition: "Adjusted known cost is recorded cost plus missing-cost rows that could be reconstructed from configured pricing snapshots or same-arm empirical estimates. It is the preferred benchmark cost for reviewed benchmark comparisons, while still preserving cost-source confidence.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Known accounting gap",
    slug: "known-accounting-gap",
    shortDefinition: "The difference between adjusted known cost and recorded cost.",
    definition: "Known accounting gap is adjusted known cost minus recorded cost. It quantifies how much the raw recorded-cost dashboard understated spend because some trials had usage or cost evidence that was not captured in cost_usd.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Failure/incomplete spend",
    slug: "failure-incomplete-spend",
    shortDefinition: "Adjusted cost spent on trials that did not produce a passing result.",
    definition: "Failure/incomplete spend is adjusted known cost for normal failures, exception failures, and unknown or incomplete outcomes. It is useful for quantifying money spent on non-passing benchmark attempts.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Unclean spend share",
    slug: "unclean-spend-share",
    shortDefinition: "Share of adjusted spend not attributable to clean successes.",
    definition: "Unclean spend share is the portion of adjusted known cost spent on failures, incomplete outcomes, and exception-with-success-signal rows. It is broader than failure/incomplete spend share because it treats exception-with-success-signal rows as operationally unclean even when reward is 1.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Cost per clean success",
    slug: "cost-per-clean-success",
    shortDefinition: "Adjusted known cost divided by clean successes.",
    definition: "Cost per clean success divides adjusted known cost by the number of trials with reward 1 and no exception marker. It is stricter than cost per any success because it excludes exception-with-success-signal rows from the denominator.",
    links: [
      { href: "/", label: "Open Overview Chart" },
      { href: "/cost-coverage", label: "Open Cost Coverage" }
    ]
  },
  {
    term: "Exception with success signal",
    slug: "exception-with-success-signal",
    shortDefinition: "A trial with reward 1 and an exception marker.",
    definition: "Exception with success signal means the verifier reward was 1, but the trial also carried an exception marker. These rows are kept separate from clean successes because they may be correct by verifier outcome but operationally unclean.",
    links: [{ href: "/trial-quality", label: "Open Trial Quality" }]
  },


  {
    term: "Attempt",
    slug: "attempt",
    shortDefinition: "One repeated benchmark execution of an eval within a run.",
    definition: "Attempt means one repetition of an eval for an arm within a benchmark run. A task-local attempt number describes repetition of that task; a run-wide trial ordinal and a GitHub workflow run attempt are different ordering or infrastructure fields and must not be interpreted as the task-local benchmark attempt.",
    links: [{ href: "/runs", label: "Open Runs" }]
  },
  {
    term: "Confidence",
    slug: "confidence",
    shortDefinition: "Categorical strength of retained evidence for a derived diagnosis or reviewed estimate.",
    definition: "Confidence is a categorical statement about how strongly retained evidence supports a derived diagnosis or reviewed estimate. It is not a probability, fabricated numeric score, or model self-assessment. The surrounding evidence contract remains authoritative: the frozen failure-taxonomy registry defines diagnosis-confidence values, while reviewed cost surfaces retain their separate cost and allocation confidence fields.",
    links: [
      { href: "/comprehensive-review", label: "Open Evidence Review" },
      { href: "/trial-quality", label: "Open Trial Quality" }
    ]
  },
  {
    term: "Unresolved",
    slug: "unresolved",
    shortDefinition: "Retained evidence is insufficient to assign the relevant value without fabrication.",
    definition: "Unresolved means the retained evidence is insufficient to assign the relevant value without fabrication. On Cost Coverage, an unresolved adjusted-cost row remains distinct from both zero cost and a reconstructed cost value. The surrounding field identifies what remains unresolved.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Accounting gap",
    slug: "accounting-gap",
    shortDefinition: "Selected reviewed cost measure minus recorded cost.",
    definition: "Accounting gap is the selected reviewed cost measure minus recorded cost. For reviewed adjusted-known-cost rows this is the known accounting gap. When a scope uses a separately qualified cost estimate, such as the Kimi K3 retained-rate estimate, that cost basis remains explicit and is not relabeled as adjusted known cost.",
    links: [{ href: "/cost-coverage", label: "Open Cost Coverage" }]
  },
  {
    term: "Routing path",
    slug: "routing-path",
    shortDefinition: "The documented execution route used to reach a model backend.",
    definition: "Routing path describes how a configured arm reached its backend, such as through the LiteLLM router or another documented benchmark route. It is execution and provenance context; routing-path presence alone does not attribute a failure to the router, provider, harness, or infrastructure.",
    links: [{ href: "/architecture", label: "Open Architecture" }]
  },
  {
    term: "Execution validity",
    slug: "execution-validity",
    shortDefinition: "Derived review state describing whether the retained attempt represents a supported execution path.",
    definition: "Execution validity is a derived review axis based on retained execution evidence. It is interpreted independently from the raw benchmark outcome, so a raw success or failure does not by itself determine execution validity.",
    links: [{ href: "/comprehensive-review", label: "Open Evidence Review" }]
  },
  {
    term: "Activity class",
    slug: "activity-class",
    shortDefinition: "Derived class of observable retained agent activity.",
    definition: "Activity class summarizes observable retained activity for the attempt and corresponds to the existing activity-subtype review field. It remains separate from raw reward, execution validity, policy disposition, and the frozen second-stage trajectory-disposition taxonomy.",
    links: [{ href: "/comprehensive-review", label: "Open Evidence Review" }]
  },
  {
    term: "Failure subtype",
    slug: "failure-subtype",
    shortDefinition: "Review classification of retained verifier, task, or solution failure evidence.",
    definition: "Failure subtype is the comprehensive-review field describing retained verifier, task, or submitted-solution failure evidence. It remains separate from execution termination and policy disposition. The frozen failure-taxonomy registry owns the definitions of its individual verifier-failure categories; this glossary entry does not replace those canonical definitions.",
    links: [
      { href: "/comprehensive-review", label: "Open Evidence Review" },
      { href: "/trial-quality", label: "Open Trial Quality" }
    ]
  },
  {
    term: "Policy disposition",
    slug: "policy-disposition",
    shortDefinition: "Derived policy-refusal state retained independently from other execution axes.",
    definition: "Policy disposition records whether retained evidence supports a provider-policy refusal or another supported policy state. It remains independent from raw outcome, execution validity, termination state, and prior observable activity; a refusal can occur before or after other activity.",
    links: [{ href: "/comprehensive-review", label: "Open Evidence Review" }]
  },
  {
    term: "Telemetry consistency",
    slug: "telemetry-consistency",
    shortDefinition: "Whether available usage telemetry agrees across retained evidence sources.",
    definition: "Telemetry consistency describes whether available token or usage evidence is consistent, mismatched, partially recorded, or otherwise incomplete. Missing telemetry remains not recorded rather than being coerced to zero, and telemetry interpretation never replaces the raw benchmark outcome.",
    links: [{ href: "/comprehensive-review", label: "Open Evidence Review" }]
  },
  {
    term: "Artifact completeness",
    slug: "artifact-completeness",
    shortDefinition: "How much of the expected canonical evidence inventory is present.",
    definition: "Artifact completeness compares retained artifact rows with the canonical evidence inventory expected for a run or trial. It is separate from R2 byte availability and integrity verification: indexed metadata or an R2 URI alone does not prove that object bytes were read or verified.",
    links: [{ href: "/artifacts", label: "Open Artifacts" }]
  },
  {
    term: "R2 integrity",
    slug: "r2-integrity",
    shortDefinition: "Whether retrieved R2 evidence bytes were verified against retained integrity evidence.",
    definition: "R2 integrity describes object-byte verification for evidence read from Cloudflare R2. It remains separate from artifact indexing, read completeness, size metadata, and local-cache fallback. An R2 URI alone does not verify object bytes.",
    links: [{ href: "/artifacts", label: "Open Artifacts" }]
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
