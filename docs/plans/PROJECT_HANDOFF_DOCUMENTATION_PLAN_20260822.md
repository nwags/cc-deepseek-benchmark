# Project Handoff Documentation Plan — 2026-08-22

## Status

Active documentation and handoff work.

This plan begins after completion of the Phase 3 benchmark, the Phase 3
evidence/review program, the dashboard corrective program through DR-304, and
the merge of the final DR-304 closeout documentation to `main`.

This work does **not** start Phase 4.

## Purpose

Prepare the Claude Code Backend Benchmark research platform for transfer to a
successor team.

The principal goal is not merely to document the software. It is to transfer
the research ideas, evidence model, analytical methods, operational knowledge,
and future roadmap well enough that the successor team can:

1. use the existing dashboard to discover valuable findings before changing it;
2. understand how dashboard claims are grounded in benchmark evidence;
3. inspect the codebase to gain confidence in results and assumptions;
4. distinguish raw facts, reviewed interpretation, and derived presentation;
5. know which historical boundaries must not be rewritten;
6. understand the available infrastructure;
7. know which platform improvements were intentionally deferred;
8. prepare Phase 4 when the team is ready;
9. keep Phase 5 methodologically after Phase 4.

The codebase is a research instrument. Its value is in making defensible ideas,
comparisons, anomalies, economic findings, and behavioral insights easier to
discover and verify.

## Current project state

At the start of this plan:

- `main` is the active baseline;
- Phase 1 is complete and frozen;
- Phase 2 is complete and frozen;
- Phase 3 is complete and closed;
- Kimi K3 remains a Phase-3-compatible post-Phase-3 addendum;
- the comprehensive evidence review is complete and preserved;
- the dashboard corrective program is accepted through DR-304;
- current provider-aware OpenAI cost reporting is reconciled through DR-304;
- historical cost evidence remains preserved separately;
- current reviewed and historical reviewed reporting remain distinct;
- the existing dashboard is a research and evidence-navigation platform, not
  merely a benchmark leaderboard;
- protected dashboard dispatch is intentionally deferred;
- Phase 4 is planned but must not begin as part of this handoff branch;
- Phase 5 remains planned after Phase 4.

## Successor-team working philosophy

The recommended order of work for the successor team is:

1. **Find insights with the current dashboard.**
2. **Trace important findings into their evidence.**
3. **Read the relevant code to understand how those findings are constructed.**
4. **Challenge assumptions and identify limitations.**
5. **Only then prioritize changes to the platform or benchmark methodology.**

The successor team should not begin by refactoring the repository simply
because the implementation is complex.

Understanding the code is strongly encouraged because it improves confidence
in the results, reveals provenance and methodological boundaries, and helps the
team design better analyses. It is not intended to become a prerequisite for
using the dashboard to conduct useful research.

## Infrastructure continuity

The current six-slot self-hosted runner topology remains operationally relevant.

The existing VPS arrangement is available through **December 2026**. The
successor team may continue to use that infrastructure until then.

Before the end of that period, the successor team should choose a longer-term
runner/infrastructure arrangement.

This handoff work must document the existing topology and transition horizon,
but it must not redesign or replace the runner infrastructure.

## Protected dashboard dispatch

Protected server-side dashboard dispatch is **not** to be implemented during
this handoff work.

The successor team should be made aware that this is planned future platform
work.

The documentation must preserve the intended direction:

- server-side GitHub credentials only;
- no browser-exposed dispatch token;
- allow-listed benchmark arms and modes;
- dry-run-first behavior;
- explicit paid-run authorization;
- runner-slot and provider-family concurrency validation;
- audit records for dispatched runs;
- links from planned/dispatched work to GitHub Actions execution;
- final ingestion/publication status linked back to the plan;
- no silent bypass of existing benchmark safety boundaries.

The current review-first Planner remains an intentional safe boundary until
such a system is implemented and reviewed.

## Live supervision

The current live-supervision and final-publication implementation is existing
platform capability, not a handoff TODO to rebuild from scratch.

The documentation must explain:

- the purpose of live supervision;
- the six-runner topology;
- Supabase live metadata;
- Cloudflare R2 progressive and final artifacts;
- final canonical publication;
- live-versus-canonical state;
- publication transactionality;
- immutable/replay behavior;
- publication fingerprints;
- runtime provenance;
- failure/recovery behavior;
- the distinction between implemented capability and possible future
  improvements.

Future live-supervision improvements may be documented for the successor team,
but this branch must not implement them.

## Phase 4

Phase 4 remains the next planned experimental phase, but it is **not the
immediate next activity**.

The successor team should first become familiar with the existing research
platform and extract useful findings from the current benchmark corpus.

When Phase 4 is activated, its purpose remains agent-harness comparison:
holding benchmark substrate as comparable as practical while varying the
coding-agent harness.

The Phase 4 handoff material must make clear:

- why it is methodologically separate from Phases 1–3;
- candidate harnesses;
- canary-before-smoke-before-full methodology;
- artifact and metric normalization requirements;
- causal/confounding risks;
- cost constraints;
- how current dashboard/evidence infrastructure can support Phase 4;
- that the current Phase 4 plan should be reviewed and refreshed before paid
  execution.

No Phase 4 benchmark run belongs in this branch.

## Phase 5

Phase 5 remains after Phase 4.

Its research question remains explicit plan-then-execute methodology rather
than simple model/backend substitution.

The successor team should preserve the methodological distinction between:

- backend/model comparison;
- agent-harness comparison;
- agent-procedure comparison.

No Phase 5 implementation or run belongs in this branch.

## Primary documentation deliverables

### 1. Dashboard Research Guide

Create:

`docs/guides/DASHBOARD_RESEARCH_GUIDE.md`

This is the primary guide for researchers using the current platform.

It must explain:

- the research purpose of the dashboard;
- the major dashboard surfaces;
- which evidence population each surface represents;
- Phase 3 core, extended, valid-imported, and all-imported scope semantics;
- raw outcome versus reviewed interpretation;
- current reviewed versus historical reviewed cost;
- recorded, adjusted, provider-billed, and qualified cost evidence;
- why provider aggregate cost must not be fabricated into trial/outcome cost;
- execution validity;
- failure taxonomy;
- response path;
- trajectory disposition;
- policy and timeout evidence;
- evidence completeness and confidence;
- live versus canonical data;
- reviewed exact-run versus latest operational evidence;
- aggregate-to-arm-to-run-to-trial-to-artifact navigation;
- how to form and test research hypotheses;
- how to word conclusions at the strength supported by the evidence.

The guide should include approximately **8–12 worked research exercises**.

Exercises should include topics such as:

- cost/performance frontier interpretation;
- comparing current provider-billed cost with historical benchmark telemetry;
- task-family strengths and weaknesses;
- timeout-heavy versus verifier-heavy failure profiles;
- policy refusals versus model-quality failures;
- successful trials with anomalous trajectory evidence;
- router-mediated versus historical direct-path comparisons;
- evidence-completeness limits;
- identifying concentrated model weaknesses hidden by aggregate scores;
- reproducing a dashboard insight down to concrete trial/artifact evidence.

The guide should favor genuine research questions over interface cataloging.

### 2. Codebase Guide

Create:

`docs/guides/CODEBASE_GUIDE.md`

This guide is for researchers and engineers who need to understand why the
dashboard says what it says and how the evidence pipeline works.

It must be concept-first rather than merely directory-first.

The principal evidence flow is:

    benchmark configuration
      -> GitHub Actions / runner
      -> Harbor
      -> Claude Code
      -> direct provider or LiteLLM route
      -> Terminal-Bench verifier
      -> raw run/trial/artifact evidence
      -> R2 / Supabase / checked-in reviewed evidence
      -> review and reconciliation layers
      -> dashboard loaders/models
      -> dashboard presentation

The guide must describe:

- phase, arm, and task configuration;
- benchmark workflow and runner execution;
- Claude Code and Harbor responsibilities;
- direct versus router-mediated provider paths;
- raw result structure;
- ingestion and publication;
- Supabase roles;
- R2 roles;
- live supervision;
- canonical publication;
- reviewed immutable snapshots;
- comprehensive evidence review;
- failure taxonomy/J2;
- DR-302 failure composition;
- DR-303 historical spend decomposition;
- DR-304 current provider-aware cost selection;
- current versus historical reporting layers;
- publication fingerprints;
- runtime provenance;
- dashboard server/client boundaries;
- evidence-aware links;
- test and validation boundaries;
- frozen-result protections.

It should include practical "where do I change X?" examples.

Examples should cover:

- adding a dashboard-only metric;
- adding a new benchmark arm;
- changing a display label without renaming canonical identity;
- introducing a new cost interpretation;
- introducing a new diagnosis/classification;
- adding a new benchmark phase;
- changing live-publication behavior;
- modifying evidence links;
- updating reviewed snapshots;
- identifying when a proposed simplification would cross a provenance boundary.

### 3. Project Handoff and Future Roadmap

Create:

`docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md`

This is the authoritative takeover document.

It must include:

- project purpose;
- current phase status;
- what is frozen;
- what is current;
- what is historical;
- what the successor team should do first;
- why insight discovery precedes platform changes;
- how code inspection supports confidence;
- current six-runner topology;
- VPS availability through December 2026;
- infrastructure transition planning;
- protected dashboard dispatch as deferred work;
- the intended protected-dispatch architecture;
- current live-supervision capability;
- potential live-supervision improvements;
- likely dashboard research/platform improvements;
- Phase 4 plan and activation criteria;
- Phase 5 plan and sequencing;
- safe benchmark-change workflow;
- handoff risks and common misinterpretations;
- a suggested first-week / first-month successor-team program.

## Supporting documentation synchronization

Update current-status material where necessary so the repository does not give
contradictory instructions.

Expected synchronization targets include:

- `README.md`;
- `AGENTS.md`;
- `docs/runbooks/RUNBOOK.md`;
- `docs/runbooks/REPO_MAP.md`;
- relevant Phase 3 plan headers/status notes;
- `docs/plans/DASHBOARD_REVISION_SPEC_20260804.md`;
- `docs/reviews/DASHBOARD_MANUAL_REVIEW_20260804.md`.

Historical plans must remain preserved as historical provenance.

Do not rewrite old plan bodies to pretend they were written after completion.
Prefer clear status banners or supersession notes.

## Documentation index

Create:

`docs/guides/README.md`

It should direct a successor-team member to the appropriate guide based on
their goal:

- discover insights;
- understand the code;
- operate the benchmark;
- inspect evidence;
- understand future work.

It should link to existing specialized runbooks and reference documents rather
than duplicating all of their detailed content.

## Proposed commit sequence

### Commit A — Define handoff documentation scope

- add this plan only.

### Commit B — Add Dashboard Research Guide

- add `docs/guides/README.md` if useful at this stage;
- add the comprehensive Dashboard Research Guide;
- include worked research exercises;
- preserve current dashboard semantics exactly.

### Commit C — Add Codebase Guide

- add the concept-first Codebase Guide;
- cross-reference authoritative code, plans, runbooks, and evidence layers;
- include safe modification examples.

### Commit D — Add Handoff and Future Roadmap

- add the authoritative takeover roadmap;
- document six-runner/VPS transition horizon;
- document deferred protected dispatch;
- document live-supervision future opportunities;
- document Phase 4 and Phase 5 sequencing.

### Commit E — Synchronize current repository guidance

Update stale current-state wording in top-level/runbook/plan documents.

Mark obsolete Phase 3 planning statements historical or superseded where
necessary.

Do not erase the historical sequence.

### Commit F — Handoff documentation acceptance

Perform final cross-document review for:

- terminology consistency;
- scope consistency;
- links;
- examples;
- successor-team usability;
- current-versus-historical clarity;
- future-work clarity;
- frozen-result boundaries.

Record final acceptance in this plan.

## Non-goals

This branch must not:

- start Phase 4;
- start Phase 5;
- add a benchmark arm;
- run a benchmark;
- run a provider probe;
- implement protected dashboard dispatch;
- redesign runner infrastructure;
- change the six-runner topology;
- apply a migration;
- write Supabase benchmark data;
- write Cloudflare R2 benchmark artifacts;
- regenerate frozen benchmark results;
- regenerate frozen reviewed evidence;
- change benchmark rewards;
- change DR-302 classifications;
- change DR-303 historical allocation semantics;
- fabricate trial/outcome allocation for provider-billed aggregate cost;
- change publication fingerprint identity semantics;
- expose secrets.

## Protected historical boundaries

At minimum, this documentation program must leave unchanged:

- `results/phase1/`;
- `results/phase2/`;
- frozen Phase 3 raw/scored results;
- accepted Phase 3 reviewed/reporting snapshots except where a documentation
  artifact explicitly records current status;
- `results/manual_verification/`;
- existing benchmark rewards;
- accepted J2 taxonomy output;
- DR-302 source semantics;
- DR-303 source semantics.

Documentation may explain these sources. It must not rewrite them.

## Validation

Before every commit, run:

    make check
    make secret-scan
    git diff --check
    git status --short

Also inspect:

    git diff --cached --stat
    git diff --cached --name-only
    git diff --cached

Stage exact paths only.

Do not use broad staging commands such as `git add .` or `git add -A`.

## Final acceptance criteria

The documentation program is complete when a technically capable successor who
did not build the project can answer all of the following without relying on
oral history:

1. What research question did each benchmark phase ask?
2. Which results are frozen?
3. Which dashboard population am I looking at?
4. What is raw benchmark truth versus reviewed interpretation?
5. Which cost number should I use for a current decision?
6. Why can some cost totals not be allocated to trials or outcomes?
7. How do I trace an aggregate observation to concrete evidence?
8. How do I distinguish a model failure from provider, harness, policy, timeout,
   verifier, or infrastructure behavior?
9. How do I use the dashboard to generate new research hypotheses?
10. Which conclusions are strong and which are qualified by incomplete evidence?
11. How does benchmark execution become dashboard data?
12. What do Supabase and R2 each store?
13. How does live evidence differ from canonical publication?
14. Which files enforce the reviewed evidence and cost boundaries?
15. What must I understand before changing a diagnosis or cost model?
16. What runner infrastructure is currently available and for how long?
17. What is the plan for protected dashboard dispatch?
18. What live-supervision improvements remain reasonable future work?
19. Why should the team investigate the existing corpus before refactoring?
20. What is Phase 4, when should it begin, and why is it separate?
21. Why does Phase 5 come after Phase 4?
22. What should the successor team do during its first week and first month?

The documentation should leave the successor team with both confidence and
productive unanswered research questions.
