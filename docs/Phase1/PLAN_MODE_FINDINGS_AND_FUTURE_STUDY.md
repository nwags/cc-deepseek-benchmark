# Plan Mode Findings and Future Benchmark Proposal

## Summary

Claude Code is commonly used interactively as a plan-then-execute coding agent: first the user asks Claude to inspect the codebase and propose a plan, then the user approves or revises the plan, and only then does Claude edit files and run tests. This resembles common Codex workflows as well.

However, the current Harbor Claude Code benchmark path is non-interactive. Harbor invokes Claude Code as an autonomous terminal agent, and the observed traces use `--permission-mode=bypassPermissions`. This is appropriate for Terminal-Bench automation, but it does not model the human plan-approval loop.

## What we observed

A canary run with `--model opusplan` succeeded on `modernize-scientific-stack`, but the transcript showed `claude-sonnet-4-6` throughout. The trajectory did not show a real `EnterPlanMode` / `ExitPlanMode` cycle. Therefore, in the current Harbor non-interactive execution path, `opusplan` behaved like Sonnet execution rather than a confirmed Opus-plan/Sonnet-execute workflow.

A separate `anthropic-default` canary was run by omitting `--model` entirely. This succeeded and the transcript showed Claude Code resolved the actual model to `claude-opus-4-7[1m]`. Therefore, the Phase 2 `anthropic-default` arm should mean “no explicit model flag,” not `--model default`.

## Implication for Phase 2

For the main Phase 2 model/backend matrix, `opusplan` should be treated as an experimental canary finding, not a full scored arm, unless a reliable way is found to activate plan mode and then proceed to execution automatically.

The clean Phase 2 arms should remain:

- `anthropic-default`: no explicit `--model`; observed canary resolved to `claude-opus-4-7[1m]`
- `anthropic-sonnet`: pinned or alias Sonnet
- `anthropic-haiku`: pinned `claude-haiku-4-5-20251001`
- `anthropic-opus`: pinned or alias Opus, budget permitting
- `deepseek-pro`: DeepSeek V4-Pro via Anthropic-compatible endpoint
- `deepseek-flash`: DeepSeek V4-Flash via Anthropic-compatible endpoint

## Future study: custom plan-execute Harbor agent

A future benchmark should patch Harbor or add a custom Harbor agent that explicitly performs two passes:

1. Planning pass:
   - Run Claude Code in plan mode or prompt-only planning mode.
   - Capture the proposed plan.
   - Do not edit the task environment.

2. Execution pass:
   - Run Claude Code again in normal autonomous execution mode.
   - Provide the original task plus the captured plan.
   - Let the executor edit files and run tests.

This benchmark would test whether explicit planning improves:

- success rate
- pass@k
- wall-clock time
- token use
- cost per resolved task
- number of tool calls
- number of repeated commands
- verifier failure rate
- failure-mode distribution

## Plan rejection / revision variants

A realistic interactive workflow allows the user to reject or revise the plan before execution. For a reproducible benchmark, this could be modeled in phases:

### Variant A: auto-accept one-shot plan

The first generated plan is always passed to the executor. This is the simplest and most reproducible version.

### Variant B: bounded reviewer loop

A reviewer model or static checklist evaluates the plan and may request one or two revisions before execution. This is more realistic but introduces another model/harness variable.

### Variant C: human-reviewed plan replay

A human reviews plans once, records decisions, and the benchmark replays accepted plans. This is realistic but less scalable and should be separated from fully automated benchmark results.

## Model combinations to test

The plan-execute harness can be tested with many planner/executor pairs:

| Arm | Planner | Executor | Purpose |
|---|---|---|---|
| planexecute-opus-sonnet | Opus | Sonnet | Closest analogue to intended OpusPlan behavior |
| planexecute-opus-opus | Opus | Opus | High-reasoning throughout |
| planexecute-sonnet-sonnet | Sonnet | Sonnet | Controls for two-pass procedure |
| planexecute-sonnet-haiku | Sonnet | Haiku | Strong plan, cheap execution |
| planexecute-haiku-haiku | Haiku | Haiku | Cheap baseline |
| planexecute-deepseek-pro-pro | DeepSeek Pro | DeepSeek Pro | DeepSeek two-pass analogue |
| planexecute-deepseek-pro-flash | DeepSeek Pro | DeepSeek Flash | DeepSeek planner/executor split analogue |

## Recommended patch direction

The patch should be implemented in Harbor, not Terminal-Bench tasks. Terminal-Bench provides the task environments and verifiers; Harbor controls how Claude Code is invoked.

The custom agent should:

1. Clone or initialize the task environment.
2. Run a planning pass with no persistent edits.
3. Store the plan under the trial artifacts.
4. Run an execution pass in the real task environment.
5. Store both planning and execution trajectories.
6. Preserve normal Terminal-Bench verifier scoring.
7. Add aggregate fields for planning tokens, execution tokens, plan length, and plan/execution model names.

## Reporting guidance

This future study should be reported separately from the Phase 2 model/backend matrix because it changes the agent procedure, not just the model. It should be labeled as a plan-execute harness benchmark rather than a pure model comparison.
