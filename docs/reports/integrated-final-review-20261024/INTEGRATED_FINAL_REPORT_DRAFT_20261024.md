# Claude Code backend benchmark: integrated final report

**Review draft — 2026-10-24. Controller/human approval pending.**

Repository: `nwags/cc-deepseek-benchmark`. Evidence baseline: live `main` at
`79f790fdd9067e33a29e0409c15f8890068ff22d`, checked for this review.
Draft branch: `analysis/integrated-final-report-20261024`.
“Current” below means the latest accepted interpretation in that repository
baseline, not a claim about models, prices, or services available today.

## Findings that affect the decision

The benchmark supports a workload-specific shortlist, with cost authority and
operational behavior attached to every recommendation. It does not establish a
universal model ranking.

- **DeepSeek Flash is the value anchor in this experiment:** 40 raw and 40 clean
  successes out of 60; selected cost **$1.0798358032**, a qualified rate estimate.
- **Kimi K3 has the highest observed success count:** 47 raw and 44 clean
  successes out of 60; selected cost **$26.570403**, a qualified estimate with
  incomplete dated pricing provenance. It is the extended Phase-3-compatible
  addendum, not Phase 4.
- **GPT-5.5 supplies a different assurance/speed tradeoff:** 44 raw and 42 clean
  successes; exact selected-run provider billing **$48.604914**; median retained
  trial runtime approximately 173 seconds, versus 499 seconds for Kimi K3.
  These medians are end-to-end retained trial measurements, not provider-only
  response latency.
- **Failure mechanisms change the interpretation:** nine policy refusals are
  concentrated in Fable; Gemini Flash is strongly timeout-associated; Haiku's
  selected sanitized route is predominantly verifier/task-failure-associated.
  A refusal remains an unsuccessful benchmark outcome. No counterfactual pass
  is credited.
- **Later accounting materially changes the economic ranking.** The 16-arm
  selected-cost sum is **$343.4494304572**. It combines bills, reconstructions,
  estimates, and lower bounds; it is neither an exact total invoice nor a
  global lower bound. The earlier $1,002.984164889198 arm sum is preserved as
  historical accounting, not silently replaced. These are changes in measurement
  interpretation, not realized spending savings. [S04] [S06] [S08] [S09]

## Scope, authority, and chronology

The experiment holds Claude Code as the principal agent harness and varies
model/backend/provider routes. Harbor orchestrates execution; task-specific
Terminal-Bench verifiers determine the raw reward. The workload is a **selected
20-task Terminal-Bench 2.0 subset**, with three attempts per task per arm. “Full
suite” in the repository means that selected workload, not all Terminal-Bench
tasks. The three attempts are repeated attempts, not a reported `pass@3` metric.

Phase 1 and Phase 2 remain frozen. Phase 3 is complete and closed. This report
adds analysis without changing scored results, existing review classifications,
or historical reporting files. Phase 4 and Phase 5 remain inactive. [S01] [S02]

| Evidence milestone | Authority retained in this report |
|---|---|
| July 12 cost coverage; July 13 benchmark/sponsor reports; July 14 closeout index and task audit; July 16 comprehensive/router analysis | Original 15-arm/900-trial core; historical benchmark-side recorded/reconstructed costs; original heuristic task-family and behavioral findings. Older frontier and routing-cost claims stay historical. |
| July 22 Kimi K3 addendum | One additional reviewed 60-trial run, with 47 raw and 44 clean successes. |
| Comprehensive review folder dated July 31, generated August 2 | Manifest-bound 960-trial qualitative review; folder date is not generation time. |
| August 5 extended comparison | Frozen 16-arm quality scope and historical qualified extended cost, including the Kimi provider-log estimate with allocation qualifications. |
| August 9 run selection | Exact reviewed run labels; no “latest similar run” substitution. |
| August 13 J2 taxonomy, subsequently retained under its manifest | Independent response-path, verifier, assertion, and trajectory axes; interpretation does not rescore reward. DR-302 later partitions raw failures for display. |
| August 21 comparison / DR-304 | Exact aggregate OpenAI provider-cost correction; all other arm costs still came from the then-selected historical layer. Preserved intermediate authority. |
| August 24 V3; August 25 ledger and V4 | Additive successor selected-cost layers. V4 is the decision-facing cost source wired into the current dashboard. |
| August 28 cross-provider consistency, with August 30 clarifications | Normalized authority/accepted-absence contract; OpenAI nonselected-source repair and Anthropic closure do not alter selected costs. |
| August 31 guides and handoff; August 31 ingestion/relay plans | Present-tense operating/status guidance. The new acquisition/relay designs are planning only, not deployed capability or authorization. |

This ordering resolves apparent conflicts without editing history. In
particular, the root operating guide still names the August 21 comparison as a
starting point; the later guides, V4 generator, and dashboard loader identify
August 25 as the current decision-facing layer. Historical July merge notes
describing `main` as the Phase 1 baseline do not override live `main` or the
August handoff. Markdown controls over convenience PDFs. [S01] [S02] [S03] [S04] [S05] [S06] [S07] [S08] [S09] [S10] [S11] [S23] [S26] [S27]

## Population and headline reproduction

The independent validation joins exact trial IDs, run labels, arms, tasks, and
attempts. It checks the comprehensive-review and J2 output hashes, byte sizes,
row counts, producer hashes, and snapshot input hashes. It also reproduces all
150 historical core arm/family count cells.

| Reviewed scope | Arms | Trials | Raw success | Explicit raw failure | Raw outcome not recorded | Clean success |
|---|---:|---:|---:|---:|---:|---:|
| Phase 3 core | 15 | 900 | 515 (57.22%) | 357 | 28 | 499 (55.44%) |
| Phase 3 extended | 16 | 960 | 562 (58.54%) | 370 | 28 | 543 (56.56%) |

The pass-rate denominator retains every selected trial. The extended set has
**398 non-successes**, comprising 370 explicit raw failures and 28 not-recorded
outcomes. DR-302 partitions only the 370 explicit failures. Historical
“failure/incomplete” accounting uses a broader bucket and therefore need not
equal the DR-302 failure count. “Clean success” here is the reviewed accounting
definition: a success without a retained benchmark exception. It is not a claim
that the transcript is free from every anomaly. All 19 exception-bearing
successes have meaningful timeout evidence and remain raw successes. [S03]
[S04] [S08]

The exact core trial-ID set has SHA-256
`a41fc86f461d5ea4d15a651da6f98c93744dbf8370a58b4b7924f3ff5a86c8fc`;
the extended set has SHA-256
`d8b04ba14576e3c14843a6b168e2ce09b67a70165bdccd0f4710b40b92bd75ef`.
The latter reproduces the comprehensive manifest's retained trial-ID digest.
Both digest sorted IDs joined with newline and no trailing newline. The exact
membership CSV, derived core/extended membership manifests, and selected-run
table accompany this report. These exports do not replace the source manifests.

### Frozen direct-path baselines

| Phase | Canonical arm | Successes | Recorded effective cost | Missing cost rows | Median wall clock (s) |
|---|---|---|---|---|---|
| phase1 | arm-a-anthropic | 39/60 | $37.295538 | 0 | 255.7 |
| phase1 | arm-b-deepseek-pro | 42/60 | $2.010415 | 0 | 617.5 |
| phase1 | arm-c-deepseek-flash | 37/60 | $1.102981 | 0 | 262.7 |
| phase2 | arm-anthropic-haiku | 26/60 | $14.310610 | 0 | 154.7 |
| phase2 | arm-anthropic-opus | 45/60 | $50.928168 | 4 | 246.8 |
| phase2 | arm-anthropic-sonnet | 40/60 | $28.362903 | 5 | 259.3 |
| phase2 | arm-deepseek-flash | 35/60 | $0.716124 | 0 | 283.4 |
| phase2 | arm-deepseek-pro | 39/60 | $1.712668 | 0 | 566.6 |

Phase 1 totals reproduce **118/180** successes and approximately **$40.41**
recorded effective cost. Phase 2 reproduces **185/300** and approximately
**$96.03** recorded cost. The retrospective July adjusted Phase 2 comparison is
approximately **$115.03**, chiefly because Opus and Sonnet have missing cost
rows; it is not a revision to their frozen source aggregates. [S12] [S13] [S22]

Comparing aggregate phase pass rates is descriptive only: different phases
contain different arm mixes. The matched Phase 2→3 raw deltas include Sonnet
−20.0 percentage points, Opus −10.0, DeepSeek Pro −3.33, Flash +8.33, and Haiku
−1.67. The Haiku comparison additionally changes the sanitizer path. The old
25–79× DeepSeek routing-cost ratios belong to the **historical accounting
layer**; current DeepSeek estimates do not support repeating those ratios as
today's selected-cost conclusion. Neither set of deltas isolates router
causation. [S05] [S12]

### All 16 reviewed arms

Every row contains 60 trials. Runtime is the median of the committed
comprehensive review's retained `runtime_seconds`, not a fresh runtime test.

| Arm | Raw successes / 60 | Clean successes / 60 | Explicit failures | Not recorded | Median runtime (s) |
|---|---|---|---|---|---|
| Kimi K3 | 47 | 44 | 13 | 0 | 499.1 |
| GPT-5.5 | 44 | 42 | 15 | 1 | 173.4 |
| DeepSeek Flash | 40 | 40 | 19 | 1 | 298.7 |
| Fable 5 | 39 | 37 | 21 | 0 | 149.5 |
| Opus | 39 | 39 | 18 | 3 | 292.8 |
| GPT-5.4 | 39 | 38 | 18 | 3 | 209.5 |
| Gemini 3.1 Pro | 38 | 36 | 20 | 2 | 860.3 |
| GLM 5.2 | 38 | 35 | 19 | 3 | 705.7 |
| DeepSeek Pro | 37 | 37 | 20 | 3 | 325.7 |
| GLM 5.1 | 36 | 35 | 21 | 3 | 373.8 |
| Grok Build 0.1 | 36 | 36 | 23 | 1 | 341.2 |
| Qwen 3.7 Plus | 33 | 32 | 24 | 3 | 457.9 |
| Kimi K2.6 | 30 | 30 | 28 | 2 | 452.9 |
| Sonnet | 28 | 28 | 32 | 0 | 164.2 |
| Haiku (sanitized) | 25 | 25 | 35 | 0 | 149.7 |
| Gemini Flash | 13 | 9 | 44 | 3 | 949.4 |

Display names map to canonical arm IDs and exact selected run labels in
`validation/arm_comparison.csv`. No alternate run is substituted.

Kimi's 5-point raw lead over GPT-5.5 is only three additional successes. An
exploratory paired task-cluster bootstrap, preserving each task's three-attempt
average, gives an approximate 95% percentile interval of **−10.0 to +21.67
percentage points** for Kimi minus GPT-5.5. This sensitivity analysis resamples
these 20 selected tasks; it does not justify statistical superiority or
representative-workload confidence. The clean-success difference is two trials.

## Failure, refusal, and trajectory findings

| DR-302 display category | Explicit raw failures | Share of 370 |
|---|---:|---:|
| Verifier/task failure | 167 | 45.14% |
| Timeout after meaningful activity | 127 | 34.32% |
| Provider-policy refusal | 9 | 2.43% |
| Invalid response path | 4 | 1.08% |
| Missing required output | 7 | 1.89% |
| Extraneous output artifacts | 22 | 5.95% |
| Unknown/incomplete evidence | 34 | 9.19% |
| **Total** | **370** | **100%** |

The partition uses explicit presentation precedence and preserves the
independent J2 axes. The 19 successful timeout anomalies and 28 not-recorded
outcomes remain outside it. Across all 960 trials, 174 have activity classified
as timeout after meaningful activity: 127 explicit failures, 19 successes, and
28 not-recorded outcomes. A timeout marker alone cannot determine correctness.

The following contrasts are supported by the frozen joined rows:

- **Gemini Flash:** 32 of its 44 explicit failures are timeout-after-meaningful-
  activity cases. It has only 9 clean successes, three not-recorded outcomes,
  and a median retained runtime near 949 seconds. Low observed success should
  not be reduced to a generic wrong-code rate.
- **Sanitized Haiku:** 32 of 35 explicit failures fall in verifier/task failure,
  and three in extraneous artifacts. Its cheap model class did not guarantee
  high task success. The selected sanitized run is distinct from historical
  invalid unsanitized/service-failure diagnostics.
- **Kimi K3:** eight of 13 failures are timeout-after-meaningful-activity, three
  verifier/task failures, and two extraneous artifacts; three additional
  timeout-bearing trials succeeded. Its high aggregate score coexists with
  operational timeout risk.
- **Fable:** all nine reviewed provider-policy refusals occur in this arm
  (15% of its 60 trials; 9/21 explicit failures), across three task identities
  with three attempts each. Six have refusal-only activity classification;
  three show meaningful activity before the policy event. It also has eight
  verifier/task failures, three extraneous-artifact failures, and one timeout
  failure. None of the other 15 arms has a reviewed policy-refusal label.
- **Sonnet:** 15 of 32 failures occupy the residual unknown/incomplete display
  category, with eight verifier/task failures, eight meaningful-activity
  timeouts, and one extraneous-artifact failure. This limits explanations of
  the direct-versus-routed score difference. [S08] [S09]

Six deterministic representative/counterexample traces are retained in
`validation/evidence_traces.json`, with exact trial/run identity, independent
review/J2 fields, completeness, and supporting artifact IDs. These trace
committed review evidence; they do not claim fresh full-artifact reads.

The safe refusal index contains the nine exact public trial IDs, selected run,
attempt, completeness state, and supporting artifact IDs. It reproduces no
task payloads, refusal excerpts, credentials, or provider account identifiers.
All nine show canonical `9/9` artifact completeness in the retained review;
that historical assertion is not a new R2 download/integrity check.

The 34 residual failures are not all missing-artifact cases. The accepted
display model distinguishes 27 complete-evidence/no-substantive-attempt cases
and seven incomplete/indeterminate cases. Across the entire review, 911 trials
have complete/high-confidence evidence and 49 incomplete/medium-confidence
evidence. Router observability is `unknown` for all 960, so these classifications
do not localize fault to a provider or router. [S08] [S09]

## Costs: selected authority and historical accounting

### Current selected-arm ledger

Selected arm totals below retain source precision; the aggregate ratios are
rounded to four fractional digits, with full values in the companion CSV. “Exact reconstruction” means
complete retained-usage accounting under accepted rates; it does **not** mean an
invoice was available. A cost-per-clean-success figure is an aggregate arm
total divided by the clean-success count, not the dollars allocated to a
particular successful trial. [S06] [S07]

| Arm | Selected arm cost | Authority / qualification | Cost ÷ clean count | Outcome allocation |
|---|---|---|---|---|
| Kimi K3 | $26.570403 | Qualified rate estimate | $0.6039 | Unavailable: no reviewed outcome join |
| GPT-5.5 | $48.604914 | Exact provider bill | $1.1573 | Unavailable: provider aggregate |
| DeepSeek Flash | $1.0798358032 | Qualified rate estimate | $0.0270 | Available with stated basis |
| Fable 5 | $64.80504500 | Exact retained-usage reconstruction; normalized absence | $1.7515 | Available with stated basis |
| Opus | $50.28831125 | Retained-usage lower bound | $1.2894 | Available with stated basis |
| GPT-5.4 | $29.7919335 | Exact provider bill | $0.7840 | Unavailable: provider aggregate |
| Gemini 3.1 Pro | $19.6968138 | Qualified rate estimate | $0.5471 | Available with stated basis |
| GLM 5.2 | $8.9016736 | Rate estimate; normalized absence | $0.2543 | Available with stated basis |
| DeepSeek Pro | $1.899724634 | Qualified rate estimate | $0.0513 | Available with stated basis |
| GLM 5.1 | $5.3316552 | Partial estimate; normalized absence | $0.1523 | Available with stated basis |
| Grok Build 0.1 | $6.418694 | Retained-usage lower bound | $0.1783 | Available with stated basis |
| Qwen 3.7 Plus | $2.50442432 | Retained-usage lower bound | $0.0783 | Available with stated basis |
| Kimi K2.6 | $6.34692415 | Qualified rate estimate | $0.2116 | Available with stated basis |
| Sonnet | $38.38591710 | Retained-usage lower bound | $1.3709 | Available with stated basis |
| Haiku (sanitized) | $16.70224485 | Exact retained-usage reconstruction; normalized absence | $0.6681 | Available with stated basis |
| Gemini Flash | $16.12091625 | Retained-usage lower bound | $1.7912 | Available with stated basis |

There are two different count systems:

| Layer | Exact/billed | Estimates | Lower bounds | Accepted normalized absence |
|---|---:|---:|---:|---:|
| V4 reporting relations, all 16 arms | 4 exact relations, including **2 bills and 2 retained-usage reconstructions** | 7 | 5 | Not a reporting relation |
| August 28 normalized authority | **2 exact provider-billed** | 5 qualified | 3 qualified | 6 (4 Anthropic, 2 GLM) |

All 16 arms have reporting reconciliation rows. Only ten have normalized
selected-run usage/cost chains. Anthropic's four accepted absences reflect no
retained first-party selected-run source under the reviewed evidence/credential
set; the separate Admin credential is required by its collector. GLM 5.1's
historical provider context is not allocable to the selected run; comparable
selected-run first-party evidence was not retained for GLM 5.2. Neither absence
means zero cost or automatic ingestion failure. [S07] [S14]

Six arms retain unquantified additional-cost exposure: Opus, Sonnet, Gemini
Flash, GLM 5.1, Grok, and Qwen. GLM 5.1 is a **partial estimate**, not a strict
lower bound, because five trials remain unresolved and cache classification is
unverified. Qwen's discounted regional rates and per-request context tier are
part of its qualified lower-bound basis. Gemini Pro's request-level tier audit
resolved the applicable below-200K rate; the selected maximum retained prompt
was 66,438 tokens. These qualifications are specific to the historical selected
runs. [S06]

### Accounting chronology, without overwriting earlier authority

| Reviewed layer | Core arm cost sum | Extended arm cost sum | Meaning |
|---|---:|---:|---|
| August 5 historical layer | $972.169845489198 | $1,002.984164889198 | Historical benchmark-side adjusted core plus qualified Kimi provider-log reconstruction |
| August 21 / DR-304 | $682.961171493867 | $713.775490893867 | Exact OpenAI corrections; other costs retain the then-selected historical basis |
| August 24 / V3 | $510.405678806867 | $541.219998206867 | Intermediate provider-aware successor |
| August 25 / V4 | $316.8790274572 | $343.4494304572 | Latest selected-arm evidence mixture; no historical fallback arms |

These are arithmetic sums of arm values, not a sequence of fully exact bills.
The historical extended scope field is `1002.9841648891979`, while its decimal
arm sum is `1002.984164889198`; V4 explicitly preserves the corresponding
sub-cent source reconciliation residual. The core historical trial-row sum is
`972.169845489205`, only `0.000000000007` above its arm sum. Validation preserves
these precision differences instead of altering frozen evidence.

### Independently supported OpenAI correction

| Selected arm | Historical harness-recorded | Historical adjusted | Exact selected provider bill |
|---|---:|---:|---:|
| GPT-5.4 | $173.094830 | $183.646689146806 | **$29.7919335** |
| GPT-5.5 | $168.708375 | $183.958832348525 | **$48.604914** |

The exact selected sum is **$78.3968475**, distinct from the broader project-
period provider total of **$95.2410900**. Sanitized provider records support the
reviewed reconciliation; private raw exports were not re-obtained in this
review. Provider input was approximately 94% cached for each selected sweep.

The retained GPT-5.4 canary independently reproduces the client-price
fingerprint: 146,861 input tokens × $5/M plus 2,602 output tokens × $25/M equals
**$0.799355**, with zero retained cache tokens. Cost propagated from Claude
Code's `total_cost_usd` through Harbor's `agent_result.cost_usd`, ingestion, and
historical reporting. The retained full-sweep reconciliation documents the
same pricing/cache mismatch. This supports an upstream telemetry/accounting
defect; it does not establish one exact dependency release or the precise
estimator dispatch mechanism. Custom routing and compatibility translation are
supported explanatory leads, with that mechanism unresolved. [S10] [S15]

OpenAI's exact totals are aggregate-only. Trial and outcome provider-cost
allocation remain `unavailable_provider_aggregate`. No historical success or
failure shares are applied to those totals.

### Kimi's three distinct amounts

Kimi K3 retains **$25.207213** in observed trial costs, **$30.8143194** from the
broader provider-request-log retained-rate reconstruction, and **$26.570403** as
the current selected-run estimate. The log has 1,273 requests and 95.86% cached
input, but its timezone and request-to-run/trial allocation are not established.
It cannot automatically replace the cleaner selected-run reconstruction.
Official dated pricing provenance remains incomplete. V4 supports selected
trial-rate reconstruction but records
`unavailable_no_reviewed_outcome_join` for outcome allocation. That prevents
claiming a selected Kimi failure-spend total. [S04] [S06] [S16]

### Failed and operationally unclean spend

The July core historical layer records **$820.77472875**, reconstructs missing
cost where feasible, and reaches **$972.169845489198** adjusted known cost. It
has 179 missing recorded-cost rows, 150 reconstructed rows, and 29 unresolved
rows. Historical failure/incomplete spend is **$335.762066413360**; including
exception-bearing successes gives approximately **$364.287476239199** unclean
spend. The corresponding historical token volumes are 213,482,015 and
218,979,987 input-plus-output tokens. Cache tokens are a subset and are not
added again. These are historical diagnostics, not allocations of current
provider billing. [S05] [S20]

Where V4 has an outcome join, current selected failed/unclean spending can be
examined within its own authority. Examples are Flash **$0.5985406728** on
non-success outcomes (55.43% of its selected estimate), sanitized Haiku
**$10.96421775** (65.65%), and GLM 5.2 **$5.4430538** including exception-bearing
successes (61.15%). Flash's historical unclean-spend share was 24.4%; carrying
that old fraction into the current cost layer would be misleading. There is
**no complete current 16-arm outcome-spend decomposition**: the two OpenAI arms
and Kimi K3 lack the required selected-outcome allocation.

## Task-family profiles

Task families are a retained heuristic taxonomy, not benchmark ground truth.
Some families contain one task. The following new extended counts join the
same taxonomy to the exact 960 reviewed trial IDs; they are kept separate from
the original July core findings. No selected provider cost is allocated to
families without a supported join. [S05] [S17]

| Heuristic family | Tasks | Historical core raw | Extended raw | Extended clean |
|---|---|---|---|---|
| build-packaging | 2 | 70/90 (77.8%) | 76/96 (79.2%) | 74/96 |
| concurrency-async | 1 | 21/45 (46.7%) | 24/48 (50.0%) | 21/48 |
| data-processing | 1 | 43/45 (95.6%) | 46/48 (95.8%) | 45/48 |
| database-storage | 2 | 44/90 (48.9%) | 49/96 (51.0%) | 47/96 |
| language-implementation | 1 | 18/45 (40.0%) | 18/48 (37.5%) | 14/48 |
| ml-scientific | 4 | 48/180 (26.7%) | 56/192 (29.2%) | 53/192 |
| optimization-finance | 1 | 40/45 (88.9%) | 43/48 (89.6%) | 43/48 |
| security-crypto | 4 | 132/180 (73.3%) | 144/192 (75.0%) | 143/192 |
| systems-low-level | 2 | 37/90 (41.1%) | 39/96 (40.6%) | 38/96 |
| web-networking | 2 | 62/90 (68.9%) | 67/96 (69.8%) | 65/96 |

Four-arm profiles illustrate why aggregate leadership is insufficient:

| Family | Flash | GLM 5.2 | GPT-5.5 | Kimi K3 |
|---|---:|---:|---:|---:|
| Build/packaging (2 tasks) | 6/6 | 6/6 | 5/6 | 6/6 |
| Concurrency/async (1 task) | 3/3 | 0/3 | 2/3 | 3/3 |
| Database/storage (2 tasks) | 5/6 | 3/6 | 5/6 | 5/6 |
| Language implementation (1 task) | 0/3 | 1/3 | 2/3 | 0/3 |
| ML/scientific/retrieval (4 tasks) | 3/12 | 4/12 | 5/12 | 8/12 |
| Security/crypto/recovery (4 tasks) | 9/12 | 11/12 | 12/12 | 12/12 |
| Systems/low-level (2 tasks) | 3/6 | 4/6 | 3/6 | 2/6 |

Kimi leads these four on ML/scientific counts but has no language-implementation
success and a weaker systems count. GPT-5.5 is a counterexample to assuming
Kimi's aggregate lead applies to every family. GLM 5.2's security strength
coexists with 0/3 on the single async task. Such small cells support follow-up
questions, not dependable production routing rules.

At task level, `polyglot-rust-c` is 1/48, model extraction 3/48, query
optimization 8/48, retrieval 9/48, and pipeline parallelism 12/48. At the other
end, scientific-stack modernization and data merging are each 46/48. The
systems family combines 38/48 on memory debugging with 1/48 on polyglot work;
its aggregate therefore hides a large within-family difference. Full counts
are in the attached task and family CSVs; no solution content is included.

## Recommendations and uncertainty

**For a budget-constrained workload resembling this subset, use DeepSeek Flash
as the historical value reference.** Its 40/60 raw and clean score is supported
at a selected estimated cost near $1.08. DeepSeek Pro costs more here and
scores lower, so this experiment supplies no aggregate quality-cost reason to
prefer Pro; a different task mix could change that conclusion.

**For the highest observed score, shortlist Kimi K3 with its evidence and
timeout qualifications.** It lies with Flash on the nominal selected-cost/raw-
quality frontier; using clean success produces the same two frontier arms.
That frontier is descriptive and uses mixed-authority point values. It does
not resolve estimate uncertainty, latency, policy behavior, or incomplete
accounting. It differs from the five-arm historical July frontier because both
cost authority and corpus membership changed.

**For exact-billing assurance and faster observed execution, retain the OpenAI
options.** GPT-5.5 has higher raw/clean counts than GPT-5.4 at greater exactly
billed aggregate cost. Kimi's higher observed quality and lower estimated cost
do not make it dominate GPT-5.5 on evidence assurance or runtime. The exact-
provider-billed-only comparison contains two OpenAI arms, which is a restricted
evidence subset, not proof that other providers are inferior.

**Evaluate GLM 5.2 as a qualified lower-cost alternative where its task profile
fits.** Its $8.9016736 selected estimate, 38 raw/35 clean successes, timeout
profile, and accepted normalized absence should travel together. Treat Fable's
refusal cluster and the weak Sonnet/Gemini Flash route observations as tested-
configuration risks; do not generalize them to all versions or harnesses.

The next useful work is read-only: challenge task-specific hypotheses, inspect
representative failures and counterexamples, and resolve provenance questions
where retained sources permit. Any new experiment needs separate scope,
methodology, cost authority, and human authorization. This report activates
nothing. The August 31 handoff's provider-collection prerequisites and
planning-only relay/import designs remain in force. [S01] [S02] [S11]

Material limitations are:

1. **Selection and dependence:** 20 public tasks, three attempts each, one
   reviewed run per arm; repeated attempts are not 60 independent task draws.
   Multiple arm/family comparisons are exploratory.
2. **Historical configuration:** date, model/provider revisions, Claude Code
   runtime versions, runner state, invalid-run policy, route, and sanitizer can
   differ. Fixed harness identity does not imply an identical binary/runtime
   across every phase or run. Cross-phase observations do not identify a
   causal router effect.
3. **Public-task contamination:** the repository documents actual historical
   Phase 1/2 WebSearch/WebFetch events. Frozen scores are retained with that
   caveat. Tool denial and audits are not proof of total network isolation;
   a retained `allow_internet=false` diagnostic still allowed public egress.
   This review did not establish contamination-free selected Phase 3 execution
   by freshly reading every full-sweep artifact. [S18]
4. **Economic authority:** estimates can move; lower bounds omit unknown usage;
   GLM 5.1 is partial; normalized absence is explicit. Credits, taxes, provider
   windows, rate tiers, region, and model composition matter where applicable.
5. **Evidence access:** the committed checkout has no `results/phase3/raw/`
   full-sweep tree and no `results/phase3/combined.csv`. Headline reproduction
   therefore uses committed exact manifest-bound review/cost/reporting data,
   not a fresh raw-to-verifier rederivation. No full-sweep R2 bytes, live
   database, private normalized inventory, or original private provider exports
   were revalidated.
6. **Dashboard access:** all 16 page contracts were reviewed, but there is no
   accessible shared dashboard URL or configured database credential here. A
   local launch started; separate read requests could not reach that runtime.
   No rendered/interactive walkthrough is claimed. See the access matrix.

## Evidence and claim matrix

The companion CSV includes exact public paths, last-change commit SHA, source
precision, and verification limits. All links below resolve at the pinned
baseline; linked repository evidence supplies the factual basis.

| Claim | Status | Authority / reproduction | Practical limit |
|---|---|---|---|
| C01: phases frozen/closed; Kimi addendum; future phases inactive | VERIFIED repository state | [S01] [S02] | Does not establish live infrastructure availability |
| C02: exact 900/960 populations and 515/562 successes | VERIFIED committed data | [S03] [S04] [S08]; ID joins and hashes | Full-sweep remote bytes not reread |
| C03: 499/543 clean successes and 19 successful timeouts | VERIFIED committed data | [S04] [S08] [S09] | Clean accounting definition, not anomaly-free proof |
| C04: 370 failure partition and 28 not-recorded outcomes | VERIFIED derived presentation | [S08] [S09] [S24] [S25]; reproduced precedence | Does not replace raw scoring |
| C05: nine policy refusals concentrated in Fable | VERIFIED reviewed classification | [S08] [S24]; nine-ID safe index | No counterfactual capability or personal discovery attribution |
| C06: $343.4494304572 selected sum | VERIFIED mixed-authority arithmetic | [S06]; decimal sum across 16 arms | Neither invoice total nor global lower bound |
| C07: two exact OpenAI bills sum to $78.3968475 | VERIFIED sanitized reconciliation | [S10] [S15] | Original private exports not independently reread |
| C08: client price/cache mismatch propagated downstream | VERIFIED fingerprint and documented lineage | [S10] [S15]; retained canary arithmetic | Precise estimator dispatch mechanism and dependency release unresolved |
| C09: V4 exact relations ≠ normalized invoice count | VERIFIED cross-layer distinction | [S06] [S07] [S14] | Private normalized inventory not freshly checked |
| C10: Kimi $26.570403 is qualified, not invoice-level | VERIFIED reviewed authority | [S06] [S16] | Pricing provenance/outcome join incomplete |
| C11: historical spending and frontier differ from current economics | VERIFIED arithmetic; interpretation qualified | [S04] [S05] [S06] [S20] [S21] | Not realized savings or current outcome allocations |
| C12: extended task/family counts | VERIFIED new offline derivation | [S08] [S17] [S24]; frozen-ID/taxonomy join | Heuristic families; small cells |
| C13: Flash and Kimi nominal frontier | VERIFIED point-value derivation | [S06]; dominance calculation | No uncertainty-, latency-, or risk-adjusted frontier claim |
| C14: Kimi statistically outperforms GPT-5.5 | NOT ESTABLISHED | Paired task-cluster sensitivity includes zero | Three-success raw difference; no universal superiority claim |
| C15: router caused cross-phase score changes | NOT ESTABLISHED | [S05] [S12] retain confounds | Observational comparison only |
| C16: complete live dashboard acceptance | NOT TESTED / ACCESS UNAVAILABLE | Sixteen-surface matrix and access output | Source/model tests are not a UI walkthrough |

## Tested / not-tested matrix

### What the experiments cover

| Question | Coverage in the reviewed evidence |
|---|---|
| Backend choice within Claude Code | Tested within each phase's selected arms and workload |
| Haiku | Frozen Phase 2 direct arm; selected Phase 3 **sanitized** route; incompatible/invalid diagnostics kept separate |
| Default/auto selection or `opusplan` as a scored arm | Not established by the scored Phase 1–3 populations; historical plans/smokes do not supply a scored comparison |
| Kimi K3 | Reviewed 60-trial Phase-3-compatible addendum |
| Raw correctness | Task-specific verifier/reward; no dashboard LLM judge rescores it |
| Clean success / refusal / timeout / trajectory diagnosis | Tested as independent reviewed axes, not adjusted rewards |
| Causal router effect or alternative harnesses | Not tested by a controlled same-time harness/route experiment here |
| Phase 4/5 harness/procedure hypotheses | Not activated or tested by this review |
| Current production reliability, today's prices, arbitrary workloads | Not tested |
| Counterfactual success without policy refusals or with longer timeouts | Not tested |

### What this review actually executed

| Check | Result | Evidence / limit |
|---|---|---|
| Offline report checks | PASS | Read-only hashes, IDs, 20×3 shape, arithmetic, cost authority, family counts, nominal frontiers; exact count in validation_summary.json |
| Focused Python snapshot/frozen-aggregate tests | PASS | 80 passed; python_tests.log |
| Cross-provider consistency tests without frozen-output writer | PASS | 12 passed, 1 deliberately deselected; cross_provider_tests.log |
| Dashboard model/component/contract tests | PASS | 296 passed; dashboard_tests.log |
| Repository script syntax checks | PASS | check passed; syntax_check.log |
| Comprehensive-review strict output scan | PASS | strict_output_scan clean; review_privacy_scan.log |
| Strict secret scan / report privacy / source preservation | PASS | Secret scan passed; final package scan and tracked-file preservation record accompany the bundle |
| Live dashboard walkthrough, all 16 surfaces | UNAVAILABLE | No shared URL or database credential; local separate HTTP requests refused |
| Raw Phase 3 full-sweep verifier rederivation / fresh R2 reads | NOT TESTED | Full raw tree absent from committed checkout; frozen derived evidence validated |
| Original private provider exports / live normalized DB inventory | NOT TESTED | Committed sanitized contracts retained; no fresh first-party verification |
| Full make check, dashboard build/typecheck | NOT RUN | Targeted data/model checks above executed; no release-wide claim |
| Paid runs, provider probes, migrations, DB/R2 writes, publication, merge, push | NOT PERFORMED | Outside this review scope |

The cross-provider test that invokes a historical generator and writes its
frozen outputs was deliberately deselected. Other generator comparisons used
pure builders or temporary test outputs. The report validator reads source
snapshots and writes only this new review directory. No paid sweep, provider
probe, migration, DB/R2 benchmark write, publication, merge, commit, or push was
performed.

## Complete dashboard access matrix

The page manuals, principal navigation, and relevant source contracts cover all
16 surfaces. **Every live/rendered surface remains unavailable in this review.**
There was no shared URL, no `SUPABASE_DB_URL`, and no configured local dashboard
credential. The recorded local HTTP access attempts returned connection
refused. Historical visual acceptance records are provenance, not acceptance
performed by this reviewer. [S02] [S19]

| Surface | Route | Contract understood from committed material | Live / interactive review |
|---|---|---|---|
| Overview | `/` | Fixed V4 upper comparison; dynamic lower discovery | Unavailable |
| Architecture | `/architecture` | Execution/scoring, observation, publication, evidence/promotion | Unavailable |
| Data Model | `/data-model` | Live, canonical, provider authority, R2, reviewed layers | Unavailable |
| Glossary | `/glossary` | Checked-in terminology; categorical confidence | Unavailable |
| Trial Quality | `/trial-quality` | Frozen J2/DR-302 separate from operational audits | Unavailable |
| Cross-phase | `/cross-phase` | Frozen Phases 1/2; V4 Phase 3; historical router context | Unavailable |
| Eval Suites | `/eval-suites` | Dynamic valid-imported suite aggregates | Unavailable |
| Evals | `/evals` | Valid-imported default / all-imported alternate | Unavailable |
| Runs | `/runs` | Canonical inventory, diagnostics, exact identity | Unavailable |
| Live Runs | `/runs/live` | Mutable/provisional shared observation | Unavailable |
| Arms | `/arms` | All-imported inventory; canonical harness identity | Unavailable |
| Artifacts | `/artifacts` | Grouped metadata; indexed/retrieved/verified distinction | Unavailable |
| Provider Evidence | `/provider-evidence` | Dynamic normalized sources; reconciliation selects authority | Unavailable |
| Evidence Review | `/comprehensive-review` | Manifest-bound full review; queue is a subset | Unavailable |
| Planner | `/planner` | Read-only fail-closed promotion consumer; no dispatch | Unavailable |
| Cost Coverage | `/cost-coverage` | V4 selected costs; separate historical DR-303 | Unavailable |

The four onboarding evidence traces are complete only **offline**: exact
run/trial→retained review metadata; failure→J2/DR-302; selected cost→ledger/
normalized contract; and operational-state→documented read-only/live/canonical
contracts. Fresh dashboard→R2 traversal and runtime operational inspection are
unavailable. Full dashboard onboarding is therefore not marked complete.

## Controller/human gate

This package is ready for review, not release approval. The controller should
check cost-authority wording, exact scope membership, and the recommendation
tradeoffs; review the safe refusal index and selected evidence traces; and
decide whether unavailable live dashboard/R2 inspection blocks the intended
release. Any additional source acquisition remains a separate authorized task.
Preserve the source baseline, validation outputs, and any human corrections as
an additive review record. Publication, merge, push, frozen-result repair,
future-phase activation, and protected writes require separate authorization.

## Source links

The full source inventory records exact paths, SHA-256, byte count, last-change
commit, and pinned-baseline URL. A last-change commit is file provenance, not a
claim about individual authorship of discovery or remediation.

- **S01**: `AGENTS.md`
- **S02**: `docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md`
- **S03**: `results/phase3/reporting/phase3_reviewed_run_selection_20260809.json`
- **S04**: `results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json`
- **S05**: `docs/reports/phase3/PHASE3_COMPREHENSIVE_ANALYSIS_20260716.md`
- **S06**: `results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json`
- **S07**: `docs/reports/phase3/PHASE3_CROSS_PROVIDER_CONSISTENCY_20260828.md`
- **S08**: `results/manual_verification/comprehensive_review_20260731/review_manifest.json`
- **S09**: `results/manual_verification/failure_taxonomy_20260813/failure_taxonomy_manifest.json`
- **S10**: `docs/reports/phase3/OPENAI_FULL_SWEEP_PROVIDER_COST_RECONCILIATION_20260821.md`
- **S11**: `docs/plans/TEAM_PROVIDER_EVIDENCE_RELAY_API_PLAN_20260831.md`
- **S12**: `docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md`
- **S13**: `results/phase2/combined.csv`
- **S14**: `docs/reports/phase3/ANTHROPIC_PROVIDER_EVIDENCE_CLOSURE_20260830.md`
- **S15**: `results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05/modernize-scientific-stack__WACxyXT/result.json`
- **S16**: `docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md`
- **S17**: `configs/tasks/phase3_task_taxonomy.tsv`
- **S18**: `docs/runbooks/BENCHMARK_CONTAMINATION.md`
- **S19**: `docs/guides/dashboard/README.md`
- **S20**: `results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv`
- **S21**: `results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv`
- **S22**: `results/phase1/combined.csv`
- **S23**: `docs/plans/PROVIDER_EVIDENCE_IMPORT_AND_STAGE_CAPTURE_PLAN_20260831.md`
- **S24**: `results/manual_verification/comprehensive_review_20260731/trial_review.csv`
- **S25**: `apps/dashboard/src/lib/failure-composition.ts`
- **S26**: `docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md`
- **S27**: `results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json`

[S01]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/AGENTS.md
[S02]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md
[S03]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_reviewed_run_selection_20260809.json
[S04]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_extended_reviewed_comparison_20260805.json
[S05]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/PHASE3_COMPREHENSIVE_ANALYSIS_20260716.md
[S06]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_current_reviewed_comparison_20260825.json
[S07]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/PHASE3_CROSS_PROVIDER_CONSISTENCY_20260828.md
[S08]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/manual_verification/comprehensive_review_20260731/review_manifest.json
[S09]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/manual_verification/failure_taxonomy_20260813/failure_taxonomy_manifest.json
[S10]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/OPENAI_FULL_SWEEP_PROVIDER_COST_RECONCILIATION_20260821.md
[S11]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/plans/TEAM_PROVIDER_EVIDENCE_RELAY_API_PLAN_20260831.md
[S12]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md
[S13]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase2/combined.csv
[S14]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/ANTHROPIC_PROVIDER_EVIDENCE_CLOSURE_20260830.md
[S15]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/canary/arm-router-gpt-5.4/2026-06-03__00-58-05/modernize-scientific-stack__WACxyXT/result.json
[S16]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/KIMI_K3_PROVIDER_LOG_RECONCILIATION_20260805.md
[S17]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/configs/tasks/phase3_task_taxonomy.tsv
[S18]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/runbooks/BENCHMARK_CONTAMINATION.md
[S19]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/guides/dashboard/README.md
[S20]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv
[S21]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_current_arm_cost_reconciliation_20260825.csv
[S22]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase1/combined.csv
[S23]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/plans/PROVIDER_EVIDENCE_IMPORT_AND_STAGE_CAPTURE_PLAN_20260831.md
[S24]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/manual_verification/comprehensive_review_20260731/trial_review.csv
[S25]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/apps/dashboard/src/lib/failure-composition.ts
[S26]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md
[S27]: https://github.com/nwags/cc-deepseek-benchmark/blob/79f790fdd9067e33a29e0409c15f8890068ff22d/results/phase3/reporting/phase3_current_reviewed_comparison_20260821.json
