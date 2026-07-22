# Phase 5 Plan: Plan-Mode Incorporation and Plan-Execute Benchmark Study

## Status

Phase 5 is planned future work.

This phase executes the incorporation of plan mode into the benchmark methodology. It is motivated by the Phase 2 `opusplan` canary, which accepted the alias but did not show a visible true planning cycle under the non-interactive Harbor execution path.

## Research question

```text
Does explicitly incorporating plan mode into the benchmark improve Claude Code / Terminal-Bench task success, cost, latency, and failure behavior?
```

Unlike Phase 2 and Phase 3, this phase changes the agent procedure. It should therefore be reported separately from pure backend/model comparisons.

## Motivation

Human use of coding agents often follows a plan-then-execute pattern:

1. Ask the agent to inspect the repository.
2. Ask for a plan.
3. Review or modify the plan.
4. Approve execution.
5. Let the agent edit files and run tests.

Terminal-Bench / Harbor automation usually invokes the agent directly in autonomous execution mode. That is reproducible, but it does not test whether explicit planning improves outcomes.

The Phase 2 `opusplan` canary did not establish true plan-mode execution under Harbor. Phase 5 should implement plan mode explicitly rather than relying on a model alias.

## Proposed architecture

```text
Harbor trial
  │
  ├── Planning pass
  │     ├── model = planner model
  │     ├── no persistent edits
  │     ├── inspect task/repo
  │     ├── write plan artifact
  │     └── save planner trajectory
  │
  ├── Execution pass
  │     ├── model = executor model
  │     ├── input = original task + saved plan
  │     ├── edit files and run commands
  │     └── save executor trajectory
  │
  └── Verifier
        ├── normal Terminal-Bench scoring
        └── result artifacts include plan/execution metadata
```

## Variants

### Variant A: auto-accept one-shot plan

The first generated plan is always passed to the executor.

Advantages:

- simplest
- reproducible
- no additional reviewer model
- good first implementation target

Disadvantages:

- bad plans are not corrected
- less realistic than human review

### Variant B: bounded reviewer loop

A reviewer model or static checklist evaluates the plan and may request revisions.

Advantages:

- closer to real plan-review workflows
- can detect missing test strategy or risky edits before execution

Disadvantages:

- adds another model/harness variable
- harder to interpret causally
- more expensive

### Variant C: human-reviewed plan replay

A human reviews plans once and records approval/revision decisions. The benchmark replays accepted plans.

Advantages:

- realistic
- useful for sponsor workflows

Disadvantages:

- not fully automated
- less scalable
- harder to reproduce by third parties

## Initial implementation target

Start with Variant A.

Minimum behavior:

1. Start from a clean task environment.
2. Run planner pass in no-edit or non-persistent mode.
3. Save `plan.md`.
4. Start execution pass in the real task environment.
5. Provide the executor with the original task prompt and `plan.md`.
6. Run the normal Terminal-Bench verifier.
7. Save both planner and executor artifacts.

## Candidate planner/executor pairs

| Arm | Planner | Executor | Purpose |
|---|---|---|---|
| `planexecute-opus-sonnet` | Opus | Sonnet | Closest analogue to desired OpusPlan behavior |
| `planexecute-opus-opus` | Opus | Opus | Maximum reasoning throughout |
| `planexecute-sonnet-sonnet` | Sonnet | Sonnet | Controls for two-pass procedure |
| `planexecute-sonnet-haiku` | Sonnet | Haiku | Strong plan, cheap execution |
| `planexecute-haiku-haiku` | Haiku | Haiku | Cheap two-pass baseline |
| `planexecute-deepseek-pro-pro` | DeepSeek Pro | DeepSeek Pro | DeepSeek two-pass analogue |
| `planexecute-deepseek-pro-flash` | DeepSeek Pro | DeepSeek Flash | Strong planner, cheap executor |
| `planexecute-gpt-gpt` | GPT via router | GPT via router | Router-mediated OpenAI plan-execute |
| `planexecute-gemini-gemini` | Gemini via router | Gemini via router | Router-mediated Gemini plan-execute |

## Metrics

Reuse prior metrics:

- success
- reward
- wall-clock seconds
- agent execution seconds
- token counts
- cost
- observed model
- exception type
- failure mode
- agent turns
- tool calls
- Bash calls
- edit/write calls
- read/search calls

Add plan-execute-specific metrics:

- planner model
- executor model
- planning wall-clock seconds
- execution wall-clock seconds
- planning tokens
- execution tokens
- planning cost
- execution cost
- plan length
- plan step count
- whether executor followed plan
- whether executor deviated from plan
- whether failure was traceable to bad plan or bad execution

## Output paths

Phase 5 outputs should go under:

```text
results/phase5/
```

Subdirectories:

```text
results/phase5/canary/
results/phase5/smoke/
results/phase5/raw/
results/phase5/supplemental/
```

Aggregate:

```text
results/phase5/combined.csv
```

Figures:

```text
figures/phase5/
```

Reports:

```text
docs/reports/phase5/
```

Each trial should preserve:

```text
planner/plan.md
planner/trajectory.json
planner/claude-code.txt or equivalent
executor/trajectory.json
executor/claude-code.txt or equivalent
verifier/
result.json
```

## Candidate task set

Start with the same 20 selected Terminal-Bench tasks for comparability.

A smaller canary/smoke subset should include:

- `modernize-scientific-stack`
- `query-optimize`
- `cancel-async-tasks`
- `build-cython-ext`
- `schemelike-metacircular-eval`

These cover scientific Python, database optimization, async control flow, compiled extension migration, and symbolic implementation.

## Acceptance criteria for a custom Harbor agent

A Phase 5 custom agent should:

- run under Harbor
- preserve normal Terminal-Bench task environments and verifiers
- isolate planning from execution
- save planner artifacts
- save executor artifacts
- support separate planner/executor model configs
- support Anthropic, DeepSeek, and router-mediated backends where possible
- expose enough metadata for cost and timing aggregation
- avoid leaking secrets into artifacts

## Failure taxonomy additions

Additional plan-execute labels:

- `bad-plan`
- `plan-missed-critical-file`
- `plan-missed-verifier-contract`
- `plan-too-vague`
- `executor-ignored-good-plan`
- `executor-followed-bad-plan`
- `planner-overfit-visible-tests`
- `executor-overfit-visible-tests`
- `plan-execute-mismatch`
- `planning-timeout`
- `execution-timeout`

## Comparison baselines

Every plan-execute result should be compared against:

- single-pass Sonnet from Phase 2
- single-pass Opus from Phase 2
- single-pass DeepSeek Pro from Phase 2
- single-pass DeepSeek Flash from Phase 2
- any Phase 3 router-mediated single-pass controls if available

Do not compare Phase 5 directly as if it were only a model/backend change. It changes the agent procedure.

## Threats to validity

- Planning pass changes token budget and time budget.
- Good plans may not be followed.
- Bad plans may harm otherwise successful execution.
- A planner may reveal solution structure that changes the nature of the task.
- Two-pass runs may simply spend more time/tokens.
- Planner/executor model pairings add combinatorial complexity.
- Human-reviewed variants are less reproducible.
- Router-mediated planner/executor pairs introduce router confounds.

## Recommended first experiment

Start with a small canary/smoke:

| Arm | Planner | Executor |
|---|---|---|
| `planexecute-sonnet-sonnet` | Sonnet | Sonnet |
| `planexecute-opus-sonnet` | Opus | Sonnet |
| `planexecute-deepseek-pro-flash` | DeepSeek Pro | DeepSeek Flash |

Run the 5-task smoke list. Compare against Phase 2 single-pass results on the same five tasks.

Only run the full 20-task x 3-attempt design after the two-pass harness is stable.

## Deliverables

Minimum deliverables:

- custom plan-mode / plan-execute agent or script prototype
- canary results
- smoke results
- saved plan artifacts
- aggregate with planning/execution split
- qualitative review of plan quality

Preferred deliverables:

- scored full sweep
- planner/executor matrix comparison
- cost-aware recommendation
- patch proposal for Harbor
- report separating plan-execute results from model-backend results
