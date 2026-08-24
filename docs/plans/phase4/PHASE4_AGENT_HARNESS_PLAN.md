# Phase 4 Plan: Agent Harness Comparison

## Status

Phase 4 is planned future work.

Phase 1, Phase 2, and Phase 3 hold Claude Code as the primary agent harness. Phase 4 changes that variable. It asks how much of the benchmark result comes from the model/backend and how much comes from the agent harness itself.

## Research question

```text
How do different coding-agent harnesses perform on the same Terminal-Bench tasks when model/provider choices are controlled as much as possible?
```

Phase 4 changes the system under test from:

```text
Claude Code fixed + varying backend
```

to:

```text
varying agent harness + comparable model/provider choices
```

This is methodologically separate from Phase 2 and Phase 3.

## Candidate harnesses

Potential agent harnesses:

| Harness | Notes |
|---|---|
| Claude Code | Existing benchmark harness and control |
| Codex / OpenAI-native coding agent | Candidate OpenAI-native agent workflow |
| Gemini CLI / Gemini coding agent | Candidate Google-native agent workflow if available and scriptable |
| OpenHands / SWE-agent-style harness | Potential open-source coding-agent harness |
| Custom Harbor agent | Useful for controlled plan-execute or router experiments |
| Other Harbor-supported agents | Add if supported by Harbor and practical to run |

## Goals

1. Determine whether Claude Code's harness is a major driver of performance.
2. Compare backend substitution against harness substitution.
3. Identify tasks where harness choice matters more than model choice.
4. Preserve comparability by using the same selected Terminal-Bench tasks where possible.
5. Keep Phase 4 results separate from Phase 1/2/3 results.

## Proposed experimental design

### Minimal design

Use the same 20 selected Terminal-Bench 2.0 tasks:

```text
configs/tasks/terminal-bench-20.txt
```

Use 3 attempts per task per harness/model arm where budget permits.

A minimal Phase 4 scored design might be:

| Arm | Harness | Model/backend | Purpose |
|---|---|---|---|
| `claude-code-sonnet` | Claude Code | Sonnet | Control from Phase 1/2 |
| `codex-openai` | Codex/OpenAI-native | comparable OpenAI model | OpenAI-native harness |
| `gemini-cli-gemini` | Gemini CLI or equivalent | Gemini model | Google-native harness |
| `openhands-sonnet-or-openai` | OpenHands/SWE-style harness | chosen model | open-source harness comparison |

### Expanded design

If infrastructure and budget allow, test harness/model pairs:

| Harness | Model/backend |
|---|---|
| Claude Code | Sonnet |
| Claude Code | GPT via router |
| Claude Code | Gemini via router |
| Codex/OpenAI-native | GPT |
| Gemini-native harness | Gemini |
| OpenHands/SWE-agent-style | GPT or Claude |
| Custom Harbor agent | selected model |

## Methodological challenges

Agent harnesses differ in:

- prompt structure
- tool schema
- file editing method
- shell execution policy
- planning loop
- retry behavior
- memory/context strategy
- permission model
- working directory assumptions
- how they report token/cost metadata
- how they interact with Harbor

Therefore Phase 4 must be careful not to present results as pure model rankings.

## Required infrastructure work

1. Identify which harnesses Harbor can invoke directly.
2. For unsupported harnesses, implement a Harbor-compatible adapter.
3. Ensure each harness operates in the same Terminal-Bench task container.
4. Capture raw transcripts/artifacts in a common directory structure.
5. Normalize metrics across harnesses.
6. Add harness-specific failure labels where necessary.
7. Keep cost accounting explicit.
8. Record routing alias separately from canonical backend/provider model
   identity. If one arm invokes multiple cost-bearing provider models, preserve
   that model composition rather than collapsing it to one pricing identity.
9. Define the provider-evidence source and expected cache/pricing semantics
   before paid execution.
10. Reconcile harness-recorded or reconstructed cost against provider-side
    evidence after canary, smoke, and scored execution, preserving both the
    original estimate and the reviewed current interpretation.

Provider reconciliation should report evidence scope explicitly. An exact
run/arm bill, a provider-day aggregate, a provider-month total, a
pricing-derived estimate, and an internal harness estimate are not equivalent
forms of evidence.

## Output paths

Phase 4 outputs should go under:

```text
results/phase4/
```

Subdirectories:

```text
results/phase4/canary/
results/phase4/smoke/
results/phase4/raw/
results/phase4/supplemental/
```

Aggregate:

```text
results/phase4/combined.csv
```

Figures:

```text
figures/phase4/
```

Reports:

```text
docs/reports/phase4/
```

## Metrics

Reuse the cross-phase metrics where possible:

- success
- reward
- wall-clock seconds
- agent execution seconds
- token counts
- cost
- observed model
- harness name
- harness version
- exception type
- failure mode
- turns/steps
- tool calls
- shell calls
- edit operations
- repeated commands
- files modified
- tests run

Harness-specific metrics may need adapters.

## Failure analysis

Phase 4 should distinguish:

- model failure
- harness failure
- tool-adapter failure
- environment/setup failure
- verifier-contract failure
- planning failure
- edit-application failure
- shell-command failure
- timeout
- budget/context exhaustion

Qualitative transcript review is especially important because harness differences may not be visible in aggregate scores alone.

## Canary plan

For each candidate harness:

1. Run a trivial non-paid local or minimal API smoke if available.
2. Run one Terminal-Bench canary task.
3. Confirm artifact capture.
4. Confirm verifier scoring.
5. Confirm no secrets leak into artifacts.
6. Confirm cost tracking or document why not available.
7. Confirm the recorded model identity is sufficient to map the run to the
   canonical provider model, or ordered set of cost-bearing provider models,
   rather than only a harness/router alias.
8. Capture the expected provider pricing/cache semantics and identify the
   provider evidence that will later be used to check the benchmark estimate.

Recommended canary task:

```text
modernize-scientific-stack
```

## Smoke plan

Use the existing 5-task smoke list:

```text
configs/tasks/phase2-smoke.txt
```

Smoke acceptance criteria:

- harness starts reliably
- basic tool/file operations work
- verifier runs
- outputs are parseable by the aggregate script or a harness-specific adapter
- failures are task/model/harness failures, not launch failures

## Scored sweep plan

Only run a full scored Phase 4 sweep after the harness canary and smoke pass.

Candidate design:

```text
20 tasks x 3 attempts x selected harness/model arms
```

The number of arms should be budget-controlled. A smaller harness comparison with good raw artifacts is more valuable than a large inconsistent run.

## Threats to validity

- Harnesses may not expose equivalent tools.
- Some harnesses may have better task-specific prompting.
- Cost and token accounting may not be comparable.
- Some harnesses may not support the same permission model.
- Local setup differences may affect results.
- Comparing native harnesses can conflate model and harness advantages.
- Router-mediated models add another layer of confounding.

## Deliverables

Minimum deliverables:

- Phase 4 plan
- harness compatibility matrix
- canary results for at least two harnesses
- documented blockers if harnesses cannot be run through Harbor

Preferred deliverables:

- scored Phase 4 aggregate
- cross-harness report
- qualitative transcript review
- recommendation on whether future work should focus on model routing or harness selection

## Relationship to other phases

- Phase 1: baseline model/backend substitution.
- Phase 2: expanded Claude Code backend matrix.
- Phase 3: router-mediated provider expansion while keeping Claude Code.
- Phase 4: harness comparison.
- Phase 5: plan-mode incorporation / plan-execute workflow.

Phase 4 should not overwrite Phase 1, Phase 2, or Phase 3 outputs.
