# Project Guides - Required Handoff and Onboarding Index

> **Required for every incoming team member.**
>
> If you are joining, taking over, supervising, or beginning substantive work
> on the Claude Code Backend Benchmark, start here and complete this onboarding
> sequence before proposing broad engineering changes or new paid benchmark
> execution.

This file is the successor-team entry point for the project.

**Reading the root `README.md` alone is not sufficient onboarding.**

**Looking only at the dashboard Overview page is not sufficient dashboard
review.**

If a required document, dashboard surface, credential, or evidence path is
unavailable or unclear, record the problem and ask about it. Do not silently
skip it and mark onboarding complete.

## Required onboarding checklist

Before considering onboarding complete, each incoming team member should be
able to check every item below:

- [ ] I read this guide index.
- [ ] I read the Dashboard Research Guide.
- [ ] I read the Codebase Guide.
- [ ] I read the Project Handoff and Future Roadmap.
- [ ] I obtained access to the dashboard or documented an access blocker.
- [ ] I opened and reviewed all 15 principal dashboard surfaces listed below.
- [ ] I completed the required evidence-tracing exercises below.
- [ ] I understand which evidence is frozen, reviewed, canonical, dynamic,
      provisional, or historical.
- [ ] I understand that Phase 3 is closed and Phase 4 is not activated.
- [ ] I understand that Kimi K3 is a Phase-3-compatible reviewed addendum, not
      Phase 4.
- [ ] I understand that the Planner is review-first/read-only and does not
      currently dispatch benchmark work.
- [ ] I understand that Migration 009 was already applied historically and
      must not be rerun as an onboarding step.
- [ ] I know which runbooks apply to the work I am about to do.
- [ ] I know that onboarding does not authorize a paid sweep, provider probe,
      database/R2 benchmark write, protected dispatch implementation, or
      modification of frozen evidence.

## How to access the dashboard

If the team provides a shared dashboard URL, use that URL and confirm that all
15 principal surfaces below are available.

If no shared dashboard is available, the repository's local setup instructions
are authoritative in:

    apps/dashboard/README.md

The current local setup is:

    cd apps/dashboard
    cp .env.local.example .env.local
    # Set SUPABASE_DB_URL in .env.local.
    # This is a server-side secret. Do not commit .env.local.
    npm install
    npm run dev

Then open the local URL printed by Next.js.

If you do not have the required `SUPABASE_DB_URL` or other access needed to
load the dashboard, request it from the project owner/team lead. **Lack of
credentials is an onboarding blocker to record and resolve, not a reason to
skip dashboard review and call onboarding complete.**

The dashboard application-specific README is:

    apps/dashboard/README.md

The research interpretation guide is:

    docs/guides/DASHBOARD_RESEARCH_GUIDE.md

## Authoritative format and PDF convenience snapshots

The Markdown files are the **authoritative project documentation**.

The PDFs are generated convenience snapshots for reading, sharing, or offline
review. They are not an independent source of truth.

If a PDF and its Markdown source ever disagree, **the Markdown controls**.

| Guide | Authoritative Markdown | PDF snapshot |
|---|---|---|
| Dashboard Research Guide | [`DASHBOARD_RESEARCH_GUIDE.md`](DASHBOARD_RESEARCH_GUIDE.md) | [`DASHBOARD_RESEARCH_GUIDE.pdf`](DASHBOARD_RESEARCH_GUIDE.pdf) |
| Codebase Guide | [`CODEBASE_GUIDE.md`](CODEBASE_GUIDE.md) | [`CODEBASE_GUIDE.pdf`](CODEBASE_GUIDE.pdf) |
| Project Handoff and Future Roadmap | [`PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md`](PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md) | [`PROJECT_HANDOFF_AND_FUTURE_ROADMAP.pdf`](PROJECT_HANDOFF_AND_FUTURE_ROADMAP.pdf) |

The current PDF snapshots were generated on **2026-08-23** from the substantive
guide content present at the hand-off baseline merged into `main` at
`9e66c00f99408c506a0195d26d8028a61563fed2`.

When one of the authoritative Markdown guides changes materially, regenerate
its PDF snapshot rather than editing the PDF independently.

## Required reading order

### 1. Dashboard Research Guide

Authoritative source:

    docs/guides/DASHBOARD_RESEARCH_GUIDE.md

Start here.

Use it to learn:

- the dashboard's research purpose;
- fixed reviewed versus dynamic imported scopes;
- failure-analysis and evidence-review surfaces;
- cost layers and coverage qualifications;
- artifact provenance and evidence completeness;
- reproducible research workflows;
- how to turn existing evidence into questions before proposing new runs.

Primary question:

> What can we learn from the evidence already collected?

### 2. Codebase Guide

Authoritative source:

    docs/guides/CODEBASE_GUIDE.md

Read this after the initial dashboard exploration.

Use it to understand:

- configuration and arm identity;
- Harbor and Claude Code execution;
- live supervision;
- canonical publication;
- reviewed snapshots;
- Supabase/R2 boundaries;
- dashboard loaders;
- validation and secret controls;
- safe modification points;
- historical versus current operating instructions.

Primary question:

> Why does the platform behave this way, and which implementation boundaries
> protect the research meaning?

### 3. Project Handoff and Future Roadmap

Authoritative source:

    docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md

Read this before proposing the next project phase or major platform work.

Use it for:

- current project state;
- successor-team sequencing;
- the six-runner infrastructure horizon;
- deferred protected dispatch;
- Phase 4 activation criteria;
- Phase 5 direction;
- work that should remain intentionally deferred.

Primary question:

> What should the successor team do next?

## Required complete dashboard walkthrough

**"Review the dashboard" means open all 15 principal dashboard surfaces.**

Do not infer the dashboard's capabilities from Overview alone. Do not mark this
walkthrough complete merely because several pages share navigation or data.

| Dashboard surface | Minimum thing the reviewer should understand |
|---|---|
| **Overview** | Which headline population is fixed/current-reviewed, which lower-level views are dynamic, and what the headline cost/performance numbers do and do not represent. |
| **Architecture** | The execution path from configuration and dispatch through runner, Harbor, Claude Code, provider routing, verifier, publication, and optional live observation. |
| **Data Model** | The distinction among live state, canonical metadata, derived data, R2 artifact bytes, checked-in reviewed snapshots, and dashboard consumers. |
| **Glossary** | The project's canonical terminology before interpreting labels elsewhere in the dashboard. |
| **Trial Quality** | Raw verifier outcomes versus reviewed diagnosis/taxonomy layers, denominator exclusions, and why review axes do not silently rescore raw outcomes. |
| **Cross-phase** | How Phase 1, Phase 2, and Phase 3 evidence is combined, and which cost basis is used for the current Phase 3 comparison. |
| **Eval Suites** | What benchmark/evaluation-suite populations exist and how scope affects what is being counted. |
| **Evals** | How task/eval drilldown differs from aggregate arm-level or run-level views. |
| **Runs** | The canonical imported run inventory and why exact run identity matters. |
| **Live Runs** | Why live supervision is mutable/provisional observation rather than a replacement for canonical publication. |
| **Arms** | Model, provider, route, and canonical arm identity distinctions. |
| **Artifacts** | How retained evidence is located, what provenance/integrity states mean, and why indexed bytes are not automatically verified complete evidence. |
| **Evidence Review** | The frozen reviewed population, manifest validation, and the role of reviewed evidence in qualitative conclusions. |
| **Planner** | That the Planner is currently review-first/read-only and **does not dispatch benchmark work**. |
| **Cost Coverage** | The distinction between current selected/provider-aware cost evidence, historical reviewed DR-303 evidence, allocation gaps, and unresolved/missing evidence. |

For each page, a reviewer should be able to explain its purpose in their own
words and identify whether the displayed evidence is fixed/reviewed, canonical
operational state, dynamic inventory, live/provisional state, or a derived
presentation layer where applicable.

If a page is confusing, use the Dashboard Research Guide and Codebase Guide to
resolve it. If the guides and the current dashboard appear inconsistent, record
the discrepancy rather than inventing an interpretation.

## Required evidence-tracing exercises

A new team member should complete these exercises before claiming familiarity
with the project.

### Exercise 1: result-to-evidence trace

Choose at least one reviewed Phase 3 arm/run/trial and trace it through the
relevant dashboard surfaces into retained evidence.

Be able to identify the exact run/trial identity and locate the available
result, transcript, verifier evidence, trajectory, configuration, exception, or
other retained artifacts where applicable.

The goal is to demonstrate that a dashboard observation can be tied back to
specific evidence rather than treated as an isolated chart value.

### Exercise 2: failure-semantics trace

Choose at least one unsuccessful trial.

Using Trial Quality and Evidence Review, explain the distinction among:

- the raw verifier outcome;
- exception/termination evidence;
- comprehensive reviewed diagnosis;
- J2/failure-taxonomy presentation;
- evidence confidence/completeness.

Do not turn a qualitative diagnosis into a different raw benchmark score.

### Exercise 3: cost-semantics trace

Using Overview, Cross-phase, and Cost Coverage, explain:

- current selected/provider-aware Phase 3 cost;
- historical reviewed cost;
- recorded versus adjusted/provider-billed evidence where applicable;
- why aggregate provider cost cannot automatically be allocated to individual
  trials, outcomes, or failure categories;
- why Kimi's selected aggregate estimate does not create fabricated
  trial-level outcome-cost allocation.

### Exercise 4: operational-state trace

Using Runs, Live Runs, Planner, Architecture, and the relevant runbooks,
explain:

- canonical imported evidence versus mutable live observation;
- why a successful live observation is not itself canonical publication;
- why Planner does not currently authorize or dispatch a paid run;
- why Migration 009 is already-applied historical state;
- what additional authorization would be required before a new benchmark
  experiment.

## Minimum concepts to understand before substantive work

A team member who has completed onboarding should be able to explain, without
guessing:

- fixed reviewed evidence versus dynamic imported evidence;
- raw benchmark/verifier outcome versus qualitative review/taxonomy;
- canonical publication versus live observation;
- current provider-aware cost versus historical reviewed cost;
- known cost versus missing, unresolved, or qualified cost;
- why provider aggregate costs cannot be fabricated into unsupported
  per-trial/per-outcome allocations;
- exact run/arm identity and why "latest similar run" is not a safe substitute;
- artifact indexing versus verified complete bytes;
- Phase 3 core versus the reviewed extended population including Kimi K3;
- why Kimi K3 is not Phase 4;
- why Phase 3 is closed;
- why Phase 4 is planned but not yet activated;
- why protected dashboard dispatch remains deferred;
- why Migration 009 must not be reapplied;
- which result/review/configuration paths are frozen or protected.

If any of those distinctions are unclear, return to the guides before changing
the implementation or proposing a new experiment.

## Goal-based starting points after onboarding

| Goal | Start here |
|---|---|
| Discover insights | `docs/guides/DASHBOARD_RESEARCH_GUIDE.md` |
| Understand the implementation | `docs/guides/CODEBASE_GUIDE.md` |
| Access/run the dashboard locally | `apps/dashboard/README.md` |
| Operate the benchmark | `docs/runbooks/RUNBOOK.md`, then `docs/runbooks/EVAL_OPERATIONS.md` |
| Inspect retained evidence and artifacts | `docs/guides/DASHBOARD_RESEARCH_GUIDE.md`, `docs/runbooks/ARTIFACT_POLICY.md` |
| Observe live executions | `docs/runbooks/LIVE_RUN_SUPERVISION.md` |
| Check contamination controls | `docs/runbooks/BENCHMARK_CONTAMINATION.md` |
| Understand collaboration practices | `docs/runbooks/COLLABORATION.md` |
| Understand repository layout | `docs/runbooks/REPO_MAP.md` |
| Understand future work | `docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md` |

Use specialized runbooks for operational detail rather than treating the three
broad hand-off guides as replacements for those procedures.

## Current project state

- Phase 1: complete and frozen.
- Phase 2: complete and frozen.
- Phase 3: complete and closed.
- Kimi K3: Phase-3-compatible reviewed addendum, not Phase 4.
- DR-302: complete.
- DR-303: complete.
- DR-304: complete.
- Phase 4: planned future harness-comparison work; **not activated**.
- Phase 5: planned after Phase 4.
- Dashboard protected dispatch: deferred future platform work.
- Migration 009: already applied historically; do not rerun it.
- Six-runner infrastructure: existing topology remains available; onboarding
  does not require redesigning it.

## What onboarding does not authorize

Do not interpret completion of this checklist as authorization to:

- start Phase 4 or Phase 5;
- run a full paid benchmark sweep;
- run provider probes merely for orientation;
- implement protected dashboard dispatch;
- redesign the runner fleet;
- reapply database migrations;
- write benchmark state to Supabase or R2;
- regenerate or overwrite frozen benchmark/review evidence;
- change rewards, DR-302/DR-303 semantics, or publication fingerprint identity
  semantics.

Those actions require their own research justification and project decision.

## When historical documents disagree with current guidance

The repository intentionally preserves historical plans, runbooks, and
implementation provenance.

Some historical documents therefore describe a project state that was correct
at the time but is no longer current.

For present-tense project state, start with:

    docs/guides/README.md
    docs/guides/DASHBOARD_RESEARCH_GUIDE.md
    docs/guides/CODEBASE_GUIDE.md
    docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md

Then consult the relevant current-facing runbook and later closeout/review
documents.

Do not reactivate historical instructions merely because they remain in Git.

## Working principle

Use this order:

    evidence
      -> insight
      -> question
      -> targeted engineering
      -> controlled experiment
      -> new evidence

The platform exists to expose useful ideas and evidence. Software is supporting
machinery, not the primary deliverable.

Do not begin successor work with broad refactoring or a new paid sweep.
