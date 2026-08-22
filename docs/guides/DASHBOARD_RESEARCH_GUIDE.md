# Dashboard Research Guide

## Purpose

This guide explains how to use the Claude Code Backend Benchmark dashboard as
a **research instrument**.

The primary objective is not to learn every page or admire the implementation.
It is to use the existing benchmark corpus, reviewed evidence, cost
reconciliation, failure taxonomy, and artifact drilldown to discover defensible
insights about coding-agent behavior.

The recommended successor-team workflow is:

1. start with a research question;
2. use the dashboard to find a pattern;
3. identify the population and evidence basis behind that pattern;
4. follow the pattern down to runs, trials, and artifacts;
5. test alternative explanations;
6. state the finding only as strongly as the evidence permits;
7. read the relevant implementation when deeper confidence or methodological
   understanding is needed;
8. change the platform only after understanding what the current behavior is
   protecting.

The codebase is a tool for manifesting and testing ideas. The ideas, evidence,
comparisons, anomalies, and conclusions are the research product.

## Current research baseline

At the time this guide was written:

- Phase 1 is a frozen direct-path baseline;
- Phase 2 is a frozen expanded direct-path Claude Code backend comparison;
- Phase 3 is complete and closed;
- Phase 3 introduced the router-mediated provider expansion;
- the original Phase 3 reviewed core contains 15 arms and 900 trials;
- the reviewed Phase 3 extended population contains 16 arms and 960 trials;
- Kimi K3 is the extended-only Phase-3-compatible addendum arm;
- the comprehensive evidence review covers the 960 reviewed extended trials;
- the J2 failure/trajectory snapshot covers the same 960 exact trial IDs;
- DR-302 provides a display-only failure composition over the 370 raw failures;
- DR-303 preserves the historical reviewed spend decomposition;
- DR-304 supplies the current provider-aware selected-cost layer while
  preserving historical benchmark-side cost evidence separately.

For current Phase 3 decision-oriented cost comparisons, use the current
reviewed cost layer shown by Overview, Cross-phase, and Cost Coverage. Do not
silently substitute the older historical adjusted-cost figures when superior
provider-billed evidence is available.

## Start with questions, not pages

A productive dashboard session normally begins with a question such as:

- Which models offer the best quality/cost tradeoff?
- Does an inexpensive model have a narrow task-family weakness?
- Are two similar pass rates produced by different failure mechanisms?
- Is a poor arm actually failing because of model quality, or because of
  timeouts, policy refusals, invalid response paths, or infrastructure?
- Does a strong raw pass rate remain attractive after clean-success and cost
  qualifications are considered?
- Are failures concentrated in a small number of task types?
- Do direct-path and router-mediated versions of a model family behave
  differently?
- Is a surprising result backed by complete evidence?
- Are successful trials always clean successes?
- Which apparently expensive models became more attractive after provider
  billing reconciliation?
- Which conclusions are robust enough for sponsor-facing reporting?
- Which observations deserve a new experiment rather than a stronger claim?

Use the dashboard to answer these questions in layers rather than trying to
extract a conclusion from one number.

## The three levels of a defensible finding

A useful mental model is:

### Level 1 — Observation

Something visible in the data.

Examples:

- one arm has a higher reviewed pass rate than another;
- an arm has many timeout-classified failures;
- one task has a low pass rate across many arms;
- a current selected cost differs materially from historical benchmark-side
  telemetry.

An observation is not automatically an explanation.

### Level 2 — Supported interpretation

An interpretation that combines multiple independent evidence layers.

Examples:

- an arm's low pass rate is heavily associated with timeouts after meaningful
  activity rather than verifier-detected incorrect solutions;
- an apparent cost disadvantage was primarily an accounting artifact because
  provider billing shows much lower actual arm-level spend;
- a raw failure is better described as a provider-policy refusal than a model
  solution failure.

The dashboard's reviewed layers are designed to support this level.

### Level 3 — Causal claim

A statement that one mechanism caused another.

Examples:

- LiteLLM caused the pass-rate difference;
- the provider caused the timeout;
- one harness feature caused a task failure.

The existing corpus often cannot establish these claims by itself. Use causal
language only when the retained evidence and experimental design support it.
Many valuable findings should remain observations or supported interpretations.

## Know the population before reading the number

One of the most important dashboard rules is that similarly named metrics can
represent different populations.

### Phase 3 core

`phase3-core`

- fixed reviewed population;
- 15 arms;
- 900 trials;
- 515 raw successes;
- 60 reviewed trials per arm;
- does not include Kimi K3;
- preserves the original Phase 3 full-suite reporting population.

Use it when comparing with the original Phase 3 report or when a historical
core-only analysis is specifically required.

### Phase 3 extended

`phase3-extended`

- fixed reviewed population;
- 16 arms;
- 960 trials;
- 562 raw successes;
- 60 reviewed trials per arm;
- includes Kimi K3;
- default current reviewed Phase 3 comparison population.

Use this for most current reviewed Phase 3 comparisons.

### Valid imported

`valid-imported`

A dynamic operational inventory.

It can contain:

- full-suite runs;
- smoke runs;
- canary runs;
- diagnostic runs;
- legacy imports;
- other imported run classes that remain valid.

Invalid and quarantined arm runs are excluded.

It does **not** have a fixed full-suite denominator.

### All imported

`all-imported`

The broadest dynamic imported evidence inventory.

It can include:

- valid imports;
- invalid or quarantined runs;
- diagnostics;
- canaries;
- smoke runs;
- legacy imports;
- unlinked or otherwise broader imported evidence represented by the relevant
  view.

It is an audit/inventory population, not a leaderboard denominator.

## Why these populations must stay separate

Suppose Overview says an arm succeeded on 47 of 60 reviewed trials while Arms
shows a different pass rate.

That is not necessarily a contradiction.

Overview's reviewed comparison is tied to one frozen reviewed run per arm.
Arms deliberately aggregates all imported evidence for each arm.

Likewise, Evals may combine multiple valid imported run classes. Its task-level
counts are useful for discovery but are not automatically the same population
as the fixed 16-arm reviewed comparison.

Before comparing two numbers, ask:

1. Are they from the same scope?
2. Are they fixed reviewed evidence or dynamic imported evidence?
3. Are invalid/quarantined runs excluded?
4. Is one exact run per arm selected, or can multiple runs contribute?
5. Is the metric current reviewed, historical reviewed, or raw operational?

If those answers differ, do not subtract or rank the numbers as though they
were one population.

## Overview is intentionally two dashboards in one page

The Overview page is the best starting point, but it intentionally contains two
different research populations.

### Upper portion: fixed reviewed comparison

The upper comparison uses the reviewed Phase 3 extended population by default.

It provides:

- reviewed arms;
- reviewed trials;
- reviewed pass rate;
- current selected cost;
- historical reviewed cost;
- one exact selected reviewed run per arm;
- selected cost basis and confidence;
- provider-billing reconciliation state;
- trial-allocation and outcome-allocation state;
- historical benchmark-side cost evidence;
- missing/unresolved historical cost coverage;
- an interactive cost/performance frontier.

The exact reviewed run labels are frozen by the reviewed run-selection
contract. A newer database run is not silently substituted.

### Lower portion: dynamic valid-imported suite evidence

The lower heatmap and hardest-eval sections use dynamic valid-imported
`phase3-full-20` suite aggregates.

Multiple valid imported runs can contribute to an arm.

This section is excellent for:

- discovering difficult tasks;
- spotting broad task × arm patterns;
- deciding where to drill down next.

It should not silently replace the fixed reviewed comparison above.

## The evidence authority model

The dashboard contains several kinds of truth and interpretation.

Keep them conceptually separate.

### Raw benchmark outcome

The stored benchmark reward/outcome is the raw scoring fact.

Terminal-Bench's task-specific verifier/tests determine correctness. There is
no dashboard LLM judge that changes the reward.

The dashboard may explain a result but does not rescore it.

### Canonical imported metadata

Supabase canonical tables and views make runs, trials, costs, validity, and
artifact metadata queryable.

These rows support operational inventory and drilldown.

### Reviewed comprehensive evidence

The comprehensive evidence-review snapshot is a manifest-validated,
checked-in interpretation layer over the reviewed corpus.

It includes independent fields for concepts such as:

- raw outcome;
- execution validity;
- activity;
- policy disposition;
- failure subtype;
- termination subtype;
- telemetry;
- evidence completeness;
- classification confidence.

It does not overwrite raw reward.

### J2 failure and trajectory taxonomy

J2 is a second-stage, frozen, manifest-bound taxonomy over the exact reviewed
extended trial set.

Its principal axes are:

- response path class;
- verifier failure category;
- assertion failure category;
- trajectory disposition.

Those axes are independent. One value does not automatically determine another.

J2 is also separate from the comprehensive-review classifications from which it
was derived.

### Presentation-only compositions

DR-302 and DR-303 create useful display partitions, but neither should be
mistaken for a new raw source of truth.

DR-302 maps the 370 raw failures into one mutually exclusive display
composition.

DR-303 decomposes historical reviewed spend using recorded outcome spend plus
the known accounting gap.

### Current provider-aware cost layer

DR-304 supplies the preferred current arm-level cost for decision-oriented
reporting.

It can use stronger evidence than the historical benchmark telemetry without
rewriting that historical telemetry.

## Cost evidence after DR-304

Cost is one of the easiest areas to misinterpret.

Use the following hierarchy for **current comparative reporting**:

1. exact provider-billed selected-run arm total, where reconciled;
2. otherwise reviewed adjusted-known cost;
3. otherwise separately qualified retained-rate estimate;
4. otherwise unavailable.

### Recorded cost

Cost recorded in the retained benchmark/trial evidence.

It may be incomplete.

A missing recorded-cost row is not zero.

### Adjusted known cost

Historical reviewed cost reconstruction used for the Phase 3 core where
missing recorded cost could be reconstructed from retained evidence.

It remains important historical provenance.

### Provider-billed cost

An exact provider-reconciled arm total for the selected run.

For GPT-5.4 and GPT-5.5, this is now the preferred current selected cost.

It does **not** provide a trial-by-trial or outcome-by-outcome allocation.

### Qualified retained-rate estimate

Used for Kimi K3.

It is a reviewed aggregate estimate with explicit limitations.

It is not invoice-level or provider-billed spend.

### Accounting gap

The difference between recorded trial cost and the historical reviewed selected
cost basis.

A gap is evidence about accounting coverage, not a failure category.

## Current OpenAI cost example

DR-304 materially changes how the OpenAI full sweeps should be discussed.

### GPT-5.4

Current selected provider-billed cost:

    $29.7919335

Historical harness-recorded cost:

    $173.09483

Historical reviewed adjusted cost:

    $183.646689146806

Current selected cost per attempt:

    $0.496532225

Current selected cost per clean success:

    $0.78399825

The current arm total is exact provider billing for the selected run.

Trial-level provider-cost allocation:

    unavailable_provider_aggregate

Outcome-level provider-cost allocation:

    unavailable_provider_aggregate

Therefore it is valid to say that the reviewed GPT-5.4 full sweep cost
$29.7919335 at the provider level.

It is **not** valid to proportionally distribute that total across individual
trials, failures, or successes without additional evidence.

### GPT-5.5

Current selected provider-billed cost:

    $48.604914

Historical harness-recorded cost:

    $168.708375

Historical reviewed adjusted cost:

    $183.958832348525

Current selected cost per attempt:

    $0.8100819

Current selected cost per clean success:

    approximately $1.15726

The same aggregate-only allocation restriction applies.

### Combined OpenAI selected full-sweep provider cost

    $78.3968475

This correction is a major example of why the dashboard keeps historical
telemetry and current decision-facing cost as separate layers.

## Kimi K3 cost example

Kimi K3 belongs only to the Phase 3 extended reviewed population.

Reviewed raw result:

- 47 successes / 60 trials;
- 78.33% raw pass rate;
- 44 clean successes.

Historical recorded trial cost:

    $25.207213

Known aggregate gap:

    $5.6071064

Current selected qualified retained-rate estimate:

    $30.8143194

Selected cost per attempt:

    $0.51357199

Selected cost per clean success:

    approximately $0.70033

Important qualifications:

- cost basis is `qualified_retained_rate_estimate`;
- cost confidence is low;
- provider-log exclusivity was not proven;
- ten recorded-cost rows are missing;
- ten cost rows remain unresolved;
- selected trial allocation is unresolved;
- selected outcome allocation is unavailable;
- the estimate is not provider-billed or invoice-level spend.

Kimi K3 is therefore a strong candidate for economic investigation, but its
cost language must remain qualified.

## Aggregate ratios versus allocated dollars

An aggregate arm total can support a ratio such as:

    selected arm cost / clean success count

without supporting a claim that a particular clean-success trial cost a
particular number of dollars.

This distinction is important for OpenAI provider-billed totals and Kimi K3.

The cost/performance chart can show aggregate cost-per-attempt or
cost-per-clean-success metrics while separately marking failure/incomplete
outcome spend as unavailable when the selected arm total has no valid outcome
allocation.

## Historical DR-303 spend decomposition

Cost Coverage also contains the historical DR-303 decomposition.

Do not confuse it with the current provider-aware selected cost.

Its extended historical reviewed accounting layer has:

- 960 reviewed trials;
- recorded outcome spend of $845.98194175;
- summed arm-level accounting gap of $157.002223139198;
- historical reviewed selected arm sum of $1002.984164889198.

It remains valuable for questions such as:

- how much historical recorded spend was associated with clean successes?
- where was historical cost coverage incomplete?
- which arms accumulated large known accounting gaps?

It should not be used to allocate the later OpenAI provider-billed totals.

## Failure interpretation: do not treat every failure alike

A raw failure is an outcome, not a behavioral explanation.

DR-302 partitions the 370 raw failures in the frozen extended reviewed
population into:

| Display category | Raw failures |
|---|---:|
| Verifier/task failure | 167 |
| Timeout after meaningful activity | 127 |
| Provider-policy refusal | 9 |
| Invalid response path | 4 |
| Missing required output | 7 |
| Extraneous output artifacts | 22 |
| Unknown / incomplete evidence | 34 |
| **Total** | **370** |

Also present in the reviewed population:

- 562 raw successes;
- 28 not-recorded outcomes;
- 19 successful trials with timeout-after-meaningful-activity evidence.

Those 19 successful timeout cases remain successes and are **not** part of the
370-failure composition.

This is a useful reminder that execution behavior and raw outcome are
independent dimensions.

## Read the independent axes independently

### Response path class

Answers questions such as:

- Was there an explicitly empty completion?
- Was it a synthetic-retry empty completion?
- Was there a long observable API-path wait?
- Was there thinking activity but no substantive completion?
- Was the response path invalid?
- Is the evidence insufficient?

It should not be used to infer provider or router fault automatically.

### Verifier failure category

Answers:

- Did the verifier establish a solution/task failure?
- Was it a compile/syntax issue?
- Dependency/import issue?
- Wrong file/path?
- Runtime exception?
- Assertion failure?
- Missing/wrong output?
- Partial solution?
- Another established but nonspecific verifier failure?

Raw failure alone does not establish a verifier-failure category.

### Assertion failure category

Refines a specific assertion failure, such as:

- performance threshold;
- numerical/data mismatch;
- missing expected file/content;
- behavior mismatch;
- output mismatch.

### Trajectory disposition

Describes observable progress independently from reward.

Examples include:

- successful completion;
- no substantive attempt;
- early abandonment;
- partial implementation;
- plausible but incorrect completion;
- near miss;
- repeated unproductive iteration;
- timeout after meaningful progress;
- indeterminate.

A successful raw outcome does not erase stronger anomalous trajectory evidence.

## Confidence and evidence completeness

The dashboard deliberately distinguishes:

- high confidence;
- medium confidence;
- low confidence;
- incomplete/ambiguous evidence;
- unavailable evidence.

Confidence is categorical rather than a fabricated numeric score.

A useful research habit is to ask two questions for every surprising
classification:

1. What positive evidence supports this label?
2. What important evidence is missing?

Do not treat an `unknown` result as proof that nothing happened.

Do not treat missing telemetry as zero telemetry.

Do not treat an R2 URI as proof that the referenced bytes were read and
verified.

## Current, historical, operational, and live are different

### Reviewed snapshot

A checked-in, frozen evidence population.

Best for:

- reproducible comparisons;
- sponsor-facing findings;
- exact reviewed run identities;
- historical interpretation.

### Canonical operational database

Published benchmark metadata in Supabase.

Best for:

- run inventory;
- exact run/trial lookup;
- artifacts;
- current operational metadata.

### Dynamic imported aggregate

A current query over operational imports.

Best for:

- discovering patterns;
- examining broader evidence;
- finding recent or diagnostic records.

It may not match a fixed reviewed population.

### Live state

Mutable in-progress observation.

Best for:

- current execution monitoring;
- warnings;
- tool activity;
- observable process output;
- partial trials;
- progressive artifacts.

It is not canonical benchmark truth.

## Dashboard navigation map

| Surface | Primary research use | Population / authority |
|---|---|---|
| Overview | Current reviewed Phase 3 comparison, cost/performance, discovery | Fixed reviewed comparison at top; dynamic valid-imported discovery below |
| Architecture | Understand execution, scoring, live observation, publication | Checked-in documentation |
| Data Model | Understand live/canonical/derived/R2/reviewed layers | Checked-in documentation |
| Glossary | Resolve shared terminology | Checked-in definitions |
| Trial Quality | Failure taxonomy, DR-302 composition, validity, quality diagnostics | Frozen J2 plus operational audit sections |
| Cross-phase | Compare Phases 1–3 without hiding route/cost differences | Frozen Phase 1/2 + current reviewed Phase 3 |
| Eval Suites | Within-suite arm/task patterns | Dynamic valid-imported suite views |
| Evals | Task-level discovery | Valid-imported default; all-imported alternate |
| Runs | Find exact imported executions | Canonical operational inventory |
| Live Runs | Observe in-progress executions | Mutable live Supabase/R2 state |
| Arms | Broad arm inventory | All imported; not a leaderboard |
| Artifacts | Inspect retained evidence | Canonical metadata plus R2/local evidence state |
| Evidence Review | Complete reviewed trial filters, queue, controls, disagreements | Frozen comprehensive-review snapshot |
| Planner | Review future run plans / draft arm YAML | Checked-in configs; no dispatch |
| Cost Coverage | Current selected cost plus historical cost provenance | Current reviewed + historical DR-303 layers |

## A useful page-by-page research workflow

### Overview

Start here when the question is about:

- overall quality;
- cost efficiency;
- the current reviewed comparison;
- frontier arms;
- strong/weak reviewed models;
- which task patterns deserve follow-up.

First determine whether you are reading the fixed reviewed upper section or the
dynamic suite sections below it.

Use the reviewed cost/performance chart to:

- switch core versus extended;
- switch selected cost per attempt, cost per clean success, and recorded cost
  per attempt;
- isolate provider families;
- isolate individual arms;
- identify the Pareto frontier;
- inspect qualification details;
- follow exact run and cost-provenance links.

Lower cost and higher pass rate are better, but frontier membership is not the
same thing as "best model." A model can sit on the frontier while still having
important qualitative weaknesses.

### Cross-phase

Use Cross-phase when the question spans Phase 1, Phase 2, and Phase 3.

Good questions:

- Did a model family behave differently on the router-mediated path?
- Did relative cost/quality rankings change across phases?
- Does an apparent router-associated difference persist after accounting for
  model/version/time/provider confounds?

Keep routing path explicit.

Do not interpret a direct-versus-routed delta as causal proof of LiteLLM impact.

### Eval Suites

Use Eval Suites to study a benchmark workload as a suite.

The full-suite detail is useful for:

- cross-arm comparison;
- heatmap inspection;
- identifying difficult tasks;
- locating broad arm × task patterns.

These are dynamic valid-imported suite views, not the fixed reviewed exact-run
population.

### Evals

Use Evals to start from a task rather than a model.

The default `valid-imported` view excludes invalid/quarantined runs.

Switch to `all-imported` when the research question specifically concerns the
broader imported evidence.

Task detail is useful for:

- comparing arms on one task;
- seeing whether a weakness is broad or arm-specific;
- checking whether invalid/quarantined evidence changes the apparent pattern.

### Runs

Use Runs when you need the actual execution behind an aggregate.

The page separates:

- full-suite runs;
- diagnostic canary/smoke runs.

Run detail exposes:

- exact run identity;
- validity state;
- suite/mode;
- raw and qualified pass context;
- runtime;
- recorded cost;
- tokens;
- runner metadata;
- exact trial rows;
- artifacts.

If a bare run label is ambiguous, the dashboard fails closed rather than
choosing the newest matching run.

### Trial Quality

Use Trial Quality when "failure" is too coarse.

Start with:

- J2 taxonomy;
- DR-302 failure composition;
- invalid/quarantined runs.

Then use the operational summary and legacy no-op sections only for their
documented audit/compatibility purposes.

The old `suspect_noop_zero_token` flag is not the preferred final explanation
when a frozen J2 diagnosis exists.

### Evidence Review

Use Evidence Review when you need the complete reviewed trial population rather
than an operational query.

It provides:

- review coverage;
- all 960 reviewed trial rows;
- exact filters;
- the manual-review queue;
- control strata;
- arm summaries;
- task disagreements.

The complete reviewed-trials section is not the same thing as the manual-review
queue.

### Artifacts

Use Artifacts when a claim needs direct evidence.

Filtering can use:

- run;
- suite;
- arm;
- task;
- quality flag;
- exception type;
- artifact type;
- free-text search.

Filtering selects matching evidence groups and then expands the artifacts in
each group.

This is intentional: once a trial matches your question, the surrounding
evidence should remain visible.

### Trial evidence

A trial detail page is often the best place to reconcile several stories about
one attempt.

Read:

- raw outcome;
- J2 failure/trajectory taxonomy;
- comprehensive-review quick diagnosis;
- configuration;
- artifacts;
- task text.

When a validated comprehensive-review snapshot exists, it is the default
diagnosis.

Operational live artifact analysis does not replace an unavailable J2 result.

### Live Runs

Use Live Runs for execution observation, not final benchmark analysis.

It can show:

- heartbeat/liveness;
- warnings;
- observable tool activity;
- observable process output;
- partial trials;
- progressive artifacts;
- event tail.

Partial trial values may change before final publication.

### Arms

Use Arms for broad inventory, not ranking.

It aggregates all imported evidence, so canary, smoke, diagnostic, legacy, and
full rows may contribute.

A recorded cost with missing rows is displayed as a lower bound rather than as
a complete total.

### Planner

Planner is intentionally review-first.

Its assumptions are checked-in planning rules, not live runner, quota, or
provider-readiness facts.

It does not dispatch a benchmark.

Protected server-side dashboard dispatch is deferred future work.

## Evidence reading order

For a trial-level investigation, a useful default reading order is:

1. `result.json` — final Harbor result and outcome context;
2. `claude-code.txt` — visible Claude Code execution;
3. verifier `test-stdout.txt` — why the final workspace passed or failed;
4. `trajectory.json` — structured observable activity;
5. `config.json` — reproducibility/configuration context;
6. `trial.log` — harness/environment activity;
7. `exception.txt` when present;
8. CTRF and reward artifacts for structured confirmation;
9. router evidence when it was retained.

Do not require every optional artifact to exist.

A normal trial commonly has eight canonical trial artifacts; an explicit
exception artifact can make the expected set nine.

## Three evidence triangles

When investigating a surprising trial, ask for evidence in three different
directions.

### Outcome triangle

    result -> reward -> verifier

Question:

Did the benchmark pass or fail, and why did the verifier score it that way?

### Activity triangle

    transcript -> trajectory -> verifier result

Question:

What observable work did the agent actually perform?

### Infrastructure triangle

    config -> trial log -> exception/router evidence

Question:

Could the environment, route, policy, timeout, or harness path explain the
result better than model capability?

A strong interpretation normally considers all three.

## Research workflow: from hypothesis to finding

Use the following sequence for serious analysis.

### Step 1 — Write the question before filtering

Prefer:

> Why does Arm A fail more often than Arm B on database/storage tasks?

over:

> Find something bad about Arm A.

A predeclared question reduces hindsight-driven interpretation.

### Step 2 — Select the right population

For a current reviewed Phase 3 comparison, normally start with
`phase3-extended`.

For a historical original Phase 3 comparison, use `phase3-core`.

For task discovery across current valid imports, use `valid-imported`.

Use `all-imported` only when the broader audit population is itself part of the
question.

### Step 3 — Establish the aggregate pattern

Record:

- denominator;
- numerator;
- pass rate;
- selected cost basis;
- relevant confidence/qualification;
- exact arms/runs involved.

Do this before inspecting individual anecdotes.

### Step 4 — Decompose the pattern

Depending on the question, break it down by:

- task;
- task family;
- provider;
- failure composition;
- response path;
- verifier failure;
- trajectory;
- policy;
- termination;
- execution validity;
- cost coverage.

### Step 5 — Inspect representative evidence

Select examples that represent:

- the dominant pattern;
- at least one counterexample;
- an incomplete/ambiguous case when relevant.

Avoid selecting only the most dramatic trial.

### Step 6 — Test alternative explanations

Before saying "model weakness," consider:

- provider-policy refusal;
- timeout;
- invalid response path;
- tool/harness issue;
- verifier/environment issue;
- missing required output;
- packaging/cleanup near miss;
- incomplete evidence;
- cost telemetry defect;
- different population or run selection.

### Step 7 — Check whether the code changes the interpretation

Read implementation when necessary to answer questions such as:

- How was this population selected?
- Does this filter use exact equality?
- Is there a fallback?
- Is the cost value current or historical?
- Is an axis independent or derived from another?
- Is an R2 reference being treated as verified content?
- Does this page read a frozen snapshot or a live database view?

### Step 8 — Write the finding with provenance

A strong finding should state:

- population;
- metric;
- evidence basis;
- interpretation;
- uncertainty;
- alternative explanations;
- representative evidence links.

## Worked research exercise 1 — Re-evaluate OpenAI economics after DR-304

### Question

How much did the cost interpretation of GPT-5.4 and GPT-5.5 change after
authoritative provider billing became available?

### Dashboard path

1. Open Overview.
2. Keep the reviewed chart on Phase 3 extended.
3. Select "Selected cost per attempt."
4. Isolate OpenAI.
5. Inspect GPT-5.4 and GPT-5.5.
6. Switch to Cost Coverage.
7. Follow the exact arm/run cost-provenance focus.
8. Compare current selected cost with historical harness and historical
   reviewed cost.

### Expected anchors

GPT-5.4:

- provider-billed selected cost: $29.7919335;
- historical harness: $173.09483;
- historical reviewed: $183.646689146806.

GPT-5.5:

- provider-billed selected cost: $48.604914;
- historical harness: $168.708375;
- historical reviewed: $183.958832348525.

Combined selected provider-billed full-sweep cost:

- $78.3968475.

### Research interpretation

A strong conclusion:

> Historical benchmark-side telemetry substantially overstated the selected
> OpenAI full-sweep cost relative to authoritative provider billing.

An unsupported conclusion:

> Every GPT-5.5 success or failure cost some reconstructed fraction of
> $48.604914.

The provider totals are exact at the selected arm/run level but not allocated
to trials or outcomes.

### Follow-up question

Does the lower provider-billed cost materially change which OpenAI points are
Pareto-efficient under selected cost per attempt or cost per clean success?

That is a useful dashboard question because DR-304 can change economic
interpretation without changing a single benchmark reward.

## Worked research exercise 2 — Investigate Kimi K3 as a strong but qualified arm

### Question

Does Kimi K3 look attractive after quality and cost qualifications are
considered together?

### Dashboard path

1. Open Overview.
2. Use Phase 3 extended.
3. Inspect Kimi K3 in the reviewed comparison.
4. Inspect its point on selected cost per attempt.
5. Switch to cost per clean success.
6. Open Cost Coverage for Kimi K3.
7. Open the exact reviewed run.
8. Inspect its exceptions and evidence in Trial Quality/Evidence Review.

### Expected anchors

- 47/60 raw successes;
- 78.33% raw pass rate;
- 44 clean successes;
- current selected estimate: $30.8143194;
- selected cost per attempt: $0.51357199;
- selected cost per clean success: about $0.70033;
- 10 missing recorded-cost rows;
- 10 unresolved cost rows;
- low cost confidence;
- trial allocation unresolved;
- outcome allocation unavailable.

### Research interpretation

A useful finding might be:

> Kimi K3 combines a high reviewed raw pass rate with a low aggregate
> selected-cost ratio, making it a strong candidate for further study, but its
> economics remain less certain than provider-billed OpenAI evidence because
> the selected Kimi value is a qualified retained-rate estimate with unresolved
> trial allocation.

Do not shorten that to "Kimi K3 costs $0.70 per successful trial" without the
qualification. The ratio is aggregate and "clean success" is a denominator,
not an allocated provider invoice.

## Worked research exercise 3 — Detect a population mismatch before calling it a contradiction

### Question

Why can an arm's pass rate differ between Overview and Arms or Evals?

### Dashboard path

1. Record the reviewed arm's pass rate on Overview.
2. Open Arms and find the same arm.
3. Open Runs and inspect how many imported runs exist.
4. Open Evals in valid-imported mode.
5. If useful, switch Evals to all-imported.
6. Compare the scope banners and page descriptions.

### What to discover

Overview's upper comparison:

- fixed reviewed population;
- one selected reviewed full-suite run per arm.

Arms:

- all imported;
- canary/smoke/diagnostic/legacy/full evidence can contribute.

Evals valid-imported:

- may combine multiple valid run classes;
- invalid/quarantined excluded.

### Research interpretation

The discrepancy can itself be useful.

It may reveal:

- later diagnostic runs;
- multiple imports;
- invalid/quarantined evidence;
- different run classes;
- changing operational evidence.

But it should not be described as a scoring inconsistency until the populations
are made equal.

## Worked research exercise 4 — Find hard tasks without overgeneralizing task families

### Question

Which tasks appear broadly difficult, and do those difficulties cluster by
task type?

### Dashboard path

1. Open Overview.
2. Inspect the dynamic valid-imported hardest-eval table.
3. Open the `phase3-full-20` Eval Suite.
4. Inspect task difficulty and the eval × arm heatmap.
5. Open individual Evals for the hardest tasks.
6. Compare arms on those tasks.
7. Use the historical task-family taxonomy only as a hypothesis aid.

### Historical hypothesis seeds

The historical Phase 3 core task-family analysis reported large differences,
including:

- data-processing: 95.6%;
- optimization-finance: 88.9%;
- build-packaging: 77.8%;
- database-storage: 48.9%;
- concurrency-async: 46.7%;
- systems-low-level: 41.1%;
- language-implementation: 40.0%;
- ml-scientific: 26.7%.

These figures come from the historical core analysis and a heuristic task
taxonomy.

They are **not** current reviewed extended ground truth.

Use them to ask better questions, such as:

- Does the extended evidence preserve the apparent ML/scientific weakness?
- Is the weakness broad across arms or concentrated in a subset?
- Do the failures share a verifier category?
- Does one model family break the pattern?

## Worked research exercise 5 — Compare failure mechanisms, not just failure rates

### Question

Do two arms with similar pass rates fail in the same way?

### Dashboard path

1. Open Trial Quality.
2. Inspect DR-302 failure composition by arm.
3. Choose two arms with comparable raw pass rates.
4. Compare their failure category distributions.
5. Filter J2 by response path, verifier category, and trajectory.
6. Follow representative trials.
7. Open artifacts for those trials.

### Global reference distribution

Across the 370 raw failures:

- 167 verifier/task failures;
- 127 timeouts after meaningful activity;
- 9 provider-policy refusals;
- 4 invalid response paths;
- 7 missing required outputs;
- 22 extraneous output artifact failures;
- 34 unknown/incomplete-evidence failures.

### Research payoff

Two arms can have the same pass rate but different operational profiles.

That distinction can matter for:

- expected reliability;
- retry strategy;
- timeout policy;
- model choice;
- harness design;
- future Phase 4 experiments.

## Worked research exercise 6 — Study successful timeout anomalies

### Question

Can a trial succeed even when the execution trajectory contains timeout
evidence?

### Dashboard path

1. Open Trial Quality.
2. Filter the frozen taxonomy/trajectory evidence for timeout-related
   dispositions.
3. Restrict attention to raw successes.
4. Follow exact trial links.
5. Compare raw outcome, termination evidence, trajectory, verifier result, and
   artifacts.

### Known reviewed fact

There are 19 successful reviewed trials with timeout-after-meaningful-activity
or timeout-after-meaningful-progress evidence.

They remain raw successes.

### Research interpretation

This is a good demonstration of independent axes:

> A timeout signal does not automatically imply benchmark failure.

Questions to investigate:

- Did useful work complete before the timeout?
- Did the verifier observe a correct final workspace?
- Is the timeout an execution-cleanliness concern rather than a correctness
  concern?
- Would another harness recover or terminate differently?

This is a potentially valuable seed for Phase 4.

## Worked research exercise 7 — Separate provider-policy refusal from model-quality failure

### Question

How often are raw failures better described as provider-policy events rather
than incorrect coding solutions?

### Dashboard path

1. Open Trial Quality.
2. Inspect the provider-policy refusal segment in DR-302.
3. Filter the relevant reviewed/J2 evidence.
4. Open several exact trials.
5. Inspect transcript, exception, policy, activity, and verifier evidence.
6. Check whether meaningful activity happened before the refusal.

### Known reviewed fact

DR-302 contains 9 provider-policy refusal raw failures.

### Research interpretation

A defensible statement:

> Nine reviewed raw failures fall into the display category
> provider-policy refusal under the accepted evidence contract.

A stronger claim requiring more evidence:

> The model would have solved all nine tasks if the provider had not refused.

The dashboard helps distinguish event type from counterfactual capability.

## Worked research exercise 8 — Retire "zero-token no-op" as an explanation

### Question

What was actually happening in trials historically flagged as suspect no-op
zero-token?

### Dashboard path

1. Open Trial Quality.
2. Use the legacy no-op section to identify affected trials.
3. Follow those trials into the frozen J2 taxonomy.
4. Compare response-path classes.
5. Open Trial Evidence and Artifacts.
6. Inspect transcript/trajectory/result/verifier evidence.

### Research principle

`suspect_noop_zero_token` is a compatibility/audit flag.

It is not the preferred final behavioral diagnosis when stronger reviewed
evidence exists.

A zero in one telemetry field can coexist with:

- visible transcript usage;
- an empty response path;
- a synthetic retry;
- a timeout;
- incomplete evidence;
- another telemetry contradiction.

The research question should move from:

> Was this a no-op?

to:

> What response path and observable trajectory does the retained evidence
> support?

## Worked research exercise 9 — Audit invalid/quarantined evidence without polluting the leaderboard

### Question

What kinds of evidence were excluded from scored comparisons, and would they
mislead an analyst if mixed back in?

### Dashboard path

1. Open Trial Quality and inspect invalid/quarantined runs.
2. Open Runs for exact invalid executions.
3. Compare valid-imported and all-imported Evals.
4. Open relevant artifacts.
5. Compare the excluded run's characteristics with the reviewed comparison.

### Research interpretation

Invalid/quarantined evidence is valuable for:

- diagnosing infrastructure;
- understanding ingestion problems;
- studying route failures;
- validating exclusion policy.

It should not be silently counted in the valid reviewed leaderboard.

A good handoff exercise is to find one task whose all-imported population
differs materially from valid-imported and explain exactly why.

## Worked research exercise 10 — Investigate evidence completeness before interpreting "unknown"

### Question

Does an unknown diagnosis mean the agent did nothing, or does it mean the
evidence cannot support a stronger conclusion?

### Dashboard path

1. Open Evidence Review.
2. inspect coverage and incomplete-evidence counts.
3. Filter for low/unknown confidence or review-required rows.
4. Open a representative trial.
5. Inspect its Artifact Evidence Guide.
6. Check canonical artifact completeness.
7. Open individual artifacts and read their provenance notice.

### Key boundaries

- missing is not zero;
- incomplete evidence is not absence;
- an R2 URI means indexed reference, not successful retrieval;
- a bounded preview is not automatically a complete artifact read;
- router evidence can be unavailable without invalidating canonical trial
  evidence;
- absence-sensitive labels require sufficiently complete evidence.

### Research interpretation

A correct conclusion can be:

> The retained evidence is insufficient to classify this trajectory more
> specifically.

That is more informative and defensible than inventing a narrative.

## Worked research exercise 11 — Use historical router-associated comparisons as hypotheses

### Question

Do matched direct-path and router-mediated model families appear to behave
differently?

### Dashboard path

1. Open Cross-phase.
2. Identify matched model families.
3. Record direct and routed pass rates, runtime, and route identity.
4. Open exact Phase 3 reviewed runs.
5. Inspect failure patterns.
6. Check historical router-associated analysis.
7. List confounds before interpreting the delta.

### Historical hypothesis seeds

The historical core analysis found examples such as:

- Phase 2 Sonnet versus router Sonnet: router-associated pass rate lower;
- Phase 2 DeepSeek Pro versus router DeepSeek Pro: pass rate broadly similar;
- Phase 2 DeepSeek Flash versus router DeepSeek Flash: router-associated pass
  rate higher;
- Phase 2 Opus versus router Opus: router-associated pass rate lower.

These are associations, not causal router effects.

Potential confounds include:

- time;
- provider-side model revisions;
- runner configuration;
- direct versus routed path;
- accounting differences;
- invalid-run policy;
- sanitization or other arm-specific behavior.

### Good next-step thinking

Instead of writing "LiteLLM caused X," ask:

> Which matched-task failures changed category across the two paths, and what
> controlled experiment would isolate the route from model/provider changes?

That question can inform Phase 4 or a later dedicated routing study.

## Worked research exercise 12 — Reproduce one sponsor-facing claim end to end

### Question

Can another researcher independently verify one dashboard insight down to
specific retained evidence?

### Suggested claim

Choose one of:

- an OpenAI provider-cost correction;
- a Kimi K3 quality/cost qualification;
- an arm's timeout-heavy failure profile;
- a difficult task;
- a provider-policy refusal cluster;
- a successful timeout anomaly.

### Reproduction path

1. Record the Overview/Cross-phase aggregate.
2. Record the exact scope.
3. Record the exact selected run.
4. Open the exact run.
5. identify the relevant trial(s).
6. Open Trial Evidence.
7. inspect the raw outcome.
8. inspect comprehensive-review fields.
9. inspect J2 taxonomy.
10. open result, transcript, verifier, trajectory, and exception artifacts as
    applicable.
11. record evidence-completeness and confidence limits.
12. verify that the written claim does not exceed the evidence.

### Success criterion

A second researcher should be able to reproduce:

- what population was used;
- what the metric means;
- what exact evidence supports the interpretation;
- what evidence is unavailable;
- why plausible alternative explanations were rejected or retained.

This is the standard to aim for in sponsor-facing findings.

## How to write a sponsor-facing finding

A useful compact structure is:

### Finding

State the observation.

### Why it matters

Explain the operational, economic, or methodological consequence.

### Evidence

State:

- scope;
- denominator;
- exact comparison;
- cost basis where relevant;
- failure/trajectory evidence where relevant;
- representative run/trial evidence.

### Qualification

State:

- evidence gaps;
- non-causal status;
- allocation limitations;
- population limitations;
- known confounds.

### Next question

End with the experiment or analysis that would most increase confidence.

Example:

> **Finding:** GPT-5.4's selected Phase 3 full-sweep cost is materially lower
> under provider billing than the historical benchmark telemetry suggested.
>
> **Why it matters:** This changes its position in cost/performance analysis
> without changing benchmark quality.
>
> **Evidence:** The exact selected run is reconciled to a $29.7919335
> provider-billed arm total, compared with $173.09483 historical harness
> recorded cost and $183.646689146806 historical reviewed adjusted cost.
>
> **Qualification:** The provider total is aggregate-only and is not allocated
> to individual trials or outcomes.
>
> **Next question:** Does the corrected economics change the preferred model
> under different quality thresholds or task-family requirements?

## Language calibration

Prefer language such as:

- "the reviewed evidence shows";
- "is associated with";
- "the retained evidence supports";
- "the display partition classifies";
- "provider billing reconciles";
- "the current selected-cost layer uses";
- "is consistent with";
- "suggests a hypothesis";
- "cannot distinguish";
- "remains unavailable".

Use stronger causal language only when the design supports it.

Avoid:

- "proved the model is bad";
- "the provider caused this";
- "the router caused this";
- "zero tokens means no work";
- "R2 has it, so the artifact was verified";
- "all failures are wrong solutions";
- "all successes are clean";
- "missing cost means free";
- "latest run" when the reviewed comparison uses a frozen exact run;
- "Phase 3 pass rate" without specifying core/extended/dynamic population when
  ambiguity matters.

## Common analytical traps

### Trap 1 — Treating Arms as the leaderboard

Arms is all-imported inventory.

Use Overview or the appropriate reviewed comparison for fixed full-suite
ranking.

### Trap 2 — Treating Evals as a fixed 960-trial population

Evals is an inventory view.

Its denominator depends on selected valid-imported/all-imported scope.

### Trap 3 — Comparing historical OpenAI cost with current selected cost without
labeling them

Both are intentionally preserved.

They answer different provenance questions.

### Trap 4 — Allocating provider-billed dollars by historical outcome shares

DR-304 explicitly prevents this.

### Trap 5 — Converting every timeout into a failure

Nineteen reviewed successes carry meaningful timeout evidence.

### Trap 6 — Converting every raw failure into verifier/task failure

DR-302 shows many failures belong to other evidence-supported categories.

### Trap 7 — Treating policy refusal as proof of inability

It is an observed policy event.

Counterfactual capability remains a separate question.

### Trap 8 — Treating an old suspect-no-op flag as a final diagnosis

Use J2 and trial evidence when available.

### Trap 9 — Inferring provider-only latency from an API-path duration

Without retained router/provider timing evidence, the wait belongs only to the
observable end-to-end path.

### Trap 10 — Treating complete artifact indexing as substantive work

Artifact completeness and agent activity are different concepts.

### Trap 11 — Selecting anecdotes first

Establish the aggregate pattern before choosing representative trials.

### Trap 12 — Refactoring before understanding the provenance contract

Some apparent implementation duplication protects historical/current,
raw/derived, or canonical/reviewed boundaries.

Read the relevant tests before simplifying it.

## When to read the code

The successor team is encouraged to inspect implementation because doing so
increases confidence in the research.

The best time to read code is **after a dashboard question has identified a
specific methodological issue**.

Examples:

Question:

> Why did this reviewed arm not switch to a newer imported run?

Read:

- reviewed run-selection loader;
- exact evidence-link helpers;
- Overview reviewed-comparison logic.

Question:

> Why is an OpenAI failure-spend number unavailable even though total cost is
> known?

Read:

- current reviewed cost model;
- selected outcome-allocation firewall;
- cost-performance chart model.

Question:

> Why does this task count differ between Evals scopes?

Read:

- eval scope selector;
- valid-imported versus all-imported database loaders.

Question:

> Why does this trial say "unknown" rather than "no substantive attempt"?

Read:

- failure-taxonomy registry;
- J2 snapshot loader;
- classifier evidence policy.

Question:

> Why does the artifact page say "R2 indexed" but not "verified"?

Read:

- artifact provenance/content reader;
- R2 bounded-preview logic.

The future Codebase Guide expands this approach into a complete
implementation map.

## Suggested first-week research program

The successor team's first week should prioritize comprehension and findings,
not platform changes.

### Day 1 — Learn the evidence boundaries

Read:

- this guide;
- Dashboard Architecture;
- Data Model;
- Glossary.

Then answer:

- What is raw truth?
- What is reviewed interpretation?
- What is dynamic?
- What is live?
- What is frozen?

### Day 2 — Reproduce the headline comparisons

Use:

- Overview;
- Cross-phase;
- Cost Coverage.

Reproduce:

- reviewed Phase 3 extended population;
- current selected cost total;
- GPT-5.4/GPT-5.5 provider corrections;
- Kimi K3 qualifications.

### Day 3 — Study failure mechanisms

Use:

- Trial Quality;
- DR-302 composition;
- J2 taxonomy;
- Evidence Review.

Choose two arms and compare *why* they fail.

### Day 4 — Study task patterns

Use:

- Eval Suites;
- Evals;
- heatmaps;
- individual task pages.

Create three hypotheses about task-specific or task-family behavior.

### Day 5 — Trace evidence

Choose at least three interesting observations.

For each:

- exact run;
- exact trial;
- raw outcome;
- reviewed interpretation;
- J2 taxonomy;
- key artifacts;
- evidence completeness;
- alternative explanation.

At the end of the week, produce a short memo containing:

- three findings;
- three unresolved questions;
- three candidate follow-up analyses;
- no platform changes unless an actual research blocker was found.

## Suggested first-month research program

A productive first month could proceed as:

### Week 1 — Orientation and reproduction

Reproduce existing important findings and learn evidence boundaries.

### Week 2 — Independent insight generation

Investigate:

- task-level strengths/weaknesses;
- failure-mechanism clusters;
- cost/performance niches;
- provider-family patterns;
- direct/router-associated differences.

### Week 3 — Evidence challenge

For the strongest candidate findings:

- search for counterexamples;
- inspect incomplete evidence;
- test alternative populations;
- challenge cost assumptions;
- read relevant code/tests.

### Week 4 — Research backlog

Produce a prioritized list:

1. findings already supported by existing evidence;
2. analyses possible with existing dashboard/data;
3. dashboard improvements that would unlock high-value analysis;
4. questions requiring a new experiment;
5. Phase 4 hypotheses worth testing later.

This backlog should drive engineering rather than the other way around.

## Current high-value research directions

The present platform appears especially well suited for investigating:

- provider-corrected cost/performance frontiers;
- quality versus clean-success economics;
- task-specific model specialization;
- task-family weakness concentration;
- timeout-heavy versus verifier-heavy model behavior;
- policy-refusal susceptibility;
- response-path reliability;
- near-miss versus substantive failure behavior;
- successful but operationally unclean trials;
- direct-versus-router-associated differences;
- evidence completeness and telemetry inconsistency;
- whether cheap models fail differently from expensive models;
- whether strong aggregate models have concentrated failure niches;
- which findings should motivate Phase 4 harness comparisons.

These are starting points, not conclusions.

## Key dashboard source files for researchers

You do not need to read these before using the dashboard, but they are useful
when challenging a finding.

Navigation:

    apps/dashboard/src/components/AppShell.tsx

Overview:

    apps/dashboard/src/app/page.tsx

Cross-phase:

    apps/dashboard/src/app/cross-phase/page.tsx

Cost Coverage:

    apps/dashboard/src/app/cost-coverage/page.tsx

Trial Quality:

    apps/dashboard/src/app/trial-quality/page.tsx

Evidence Review:

    apps/dashboard/src/app/comprehensive-review/page.tsx

Evals:

    apps/dashboard/src/app/evals/page.tsx
    apps/dashboard/src/app/evals/[taskId]/page.tsx

Eval Suites:

    apps/dashboard/src/app/eval-suites/page.tsx
    apps/dashboard/src/app/eval-suites/[suiteId]/page.tsx

Runs:

    apps/dashboard/src/app/runs/page.tsx
    apps/dashboard/src/app/runs/[runLabel]/page.tsx

Live Runs:

    apps/dashboard/src/app/runs/live/page.tsx

Artifacts:

    apps/dashboard/src/app/artifacts/page.tsx
    apps/dashboard/src/app/artifacts/[artifactId]/page.tsx
    apps/dashboard/src/components/ArtifactEvidenceGuide.tsx

Trial evidence:

    apps/dashboard/src/app/trials/[trialId]/page.tsx

Architecture and data model:

    apps/dashboard/src/app/architecture/page.tsx
    apps/dashboard/src/app/data-model/page.tsx

Planner:

    apps/dashboard/src/app/planner/page.tsx

## Key reviewed evidence and reporting sources

Current selected Phase 3 comparison:

    results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json

Historical reviewed Phase 3 comparison:

    results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json

Frozen reviewed run selection:

    results/phase3/reporting/phase3_reviewed_run_selection_20260809.json

Comprehensive review:

    results/manual_verification/comprehensive_review_20260731/

Failure taxonomy:

    configs/dashboard/failure_taxonomy_v1.json
    results/manual_verification/failure_taxonomy_20260813/

Historical Phase 3 cost coverage:

    results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv
    results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv

OpenAI provider reconciliation:

    docs/reports/phase3/OPENAI_FULL_SWEEP_PROVIDER_COST_RECONCILIATION_20260821.md

Historical comprehensive analysis:

    docs/reports/phase3/PHASE3_COMPREHENSIVE_ANALYSIS_20260716.md

## Specialized documentation

For benchmark operation:

    docs/runbooks/EVAL_OPERATIONS.md
    docs/runbooks/RUNBOOK.md

For live supervision:

    docs/runbooks/LIVE_RUN_SUPERVISION.md

For artifacts:

    docs/runbooks/ARTIFACT_POLICY.md

For contamination controls:

    docs/runbooks/BENCHMARK_CONTAMINATION.md

For collaboration:

    docs/runbooks/COLLABORATION.md

For the dashboard data model diagram:

    docs/diagrams/DASHBOARD_DATA_MODEL_20260812.mmd

For historical dashboard requirements and acceptance:

    docs/plans/DASHBOARD_REVISION_SPEC_20260804.md
    docs/reviews/DASHBOARD_MANUAL_REVIEW_20260804.md

Some older operational documents still contain historical Phase 3 wording.
The project-handoff documentation program will synchronize those current-status
statements separately without rewriting their historical record.

## Guide maintenance rules

When the dashboard changes, update this guide if any of the following change:

- primary navigation;
- scope semantics;
- reviewed population membership;
- current cost-selection hierarchy;
- evidence authority;
- taxonomy axes;
- run-selection policy;
- validity policy;
- live/canonical boundary;
- artifact provenance behavior;
- protected dispatch status;
- Phase 4 activation state.

Do not update historical examples by silently replacing the evidence they were
meant to illustrate.

When a newer reviewed layer supersedes a current decision-facing metric:

1. preserve the historical value and its provenance;
2. identify the new preferred value;
3. explain why the preference changed;
4. preserve allocation limitations;
5. update examples that are explicitly labeled "current."

## Final research principle

The dashboard is most valuable when it helps a researcher move from:

    leaderboard number

to:

    pattern

to:

    evidence-backed interpretation

to:

    unresolved question

to:

    better experiment

The successor team should use the current platform to extract as much
knowledge as possible before deciding what the next version of the platform
needs to become.
