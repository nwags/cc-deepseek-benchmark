# Project Guides

These guides are the current successor-team entry points for the Claude Code
Backend Benchmark.

## Recommended reading order

### 1. Dashboard Research Guide

```text
docs/guides/DASHBOARD_RESEARCH_GUIDE.md
```

Start here.

Use it to learn the current dashboard scopes, evidence surfaces, cost layers,
failure analysis, and reproducible research workflows.

Primary question:

> What can we learn from the evidence already collected?

### 2. Codebase Guide

```text
docs/guides/CODEBASE_GUIDE.md
```

Read this after initial dashboard exploration.

Use it to understand configuration, Harbor execution, live supervision,
canonical publication, reviewed snapshots, Supabase/R2 boundaries, dashboard
loaders, validation, and safe modification points.

Primary question:

> Why does the platform behave this way, and which implementation boundaries
> protect the research meaning?

### 3. Project Handoff and Future Roadmap

```text
docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md
```

Use this for successor-team sequencing, infrastructure horizon, deferred
platform work, Phase 4 activation criteria, and Phase 5 direction.

Primary question:

> What should the successor team do next?

## Goal-based starting points

| Goal | Start here |
|---|---|
| Discover insights | `docs/guides/DASHBOARD_RESEARCH_GUIDE.md` |
| Understand the implementation | `docs/guides/CODEBASE_GUIDE.md` |
| Operate the benchmark | `docs/runbooks/RUNBOOK.md`, then `docs/runbooks/EVAL_OPERATIONS.md` |
| Inspect retained evidence and artifacts | `docs/guides/DASHBOARD_RESEARCH_GUIDE.md`, `docs/runbooks/ARTIFACT_POLICY.md` |
| Observe live executions | `docs/runbooks/LIVE_RUN_SUPERVISION.md` |
| Check contamination controls | `docs/runbooks/BENCHMARK_CONTAMINATION.md` |
| Understand collaboration practices | `docs/runbooks/COLLABORATION.md` |
| Understand future work | `docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md` |

Use the specialized runbooks for operational detail rather than treating the
three broad handoff guides as replacements for those procedures.

## Current project state

- Phase 1: complete and frozen.
- Phase 2: complete and frozen.
- Phase 3: complete and closed.
- Kimi K3: Phase-3-compatible reviewed addendum, not Phase 4.
- DR-304: complete.
- Phase 4: planned future harness-comparison work; not yet activated.
- Phase 5: planned after Phase 4.
- Dashboard protected dispatch: deferred future platform work.
- Migration 009: already applied historically; do not rerun it.

## Working principle

Use this order:

```text
evidence
  -> insight
  -> question
  -> targeted engineering
  -> controlled experiment
  -> new evidence
```

Do not begin successor work with broad refactoring or a new paid sweep.
