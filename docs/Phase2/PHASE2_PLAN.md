# Phase 2 Plan: Expanded Claude Code Model Matrix and Behavioral Failure Analysis

Phase 1 is frozen on `main`.

This branch extends the benchmark to answer the sponsor's follow-up questions:

1. Add more model arms.
2. Test Claude Code default/auto model selection.
3. Test Haiku.
4. Analyze why tasks pass/fail and what models do differently.

Phase 2 will preserve Phase 1 results and write new results under:

    results/phase2/

Initial model arms:

- `anthropic-default`
- `anthropic-sonnet`
- `anthropic-haiku`
- `anthropic-opus`
- `anthropic-opusplan`
- `deepseek-pro`
- `deepseek-flash`

Phase 2 analysis will add deeper trajectory features:

- agent turns
- tool calls
- Bash/Edit/Read/Write/Glob/Grep counts
- repeated commands
- files touched
- first test run
- last verifier error
- timeout phase
- whether visible tests were run
- whether the final answer was given before verification
- failure-mode refinements

## Plan Mode / OpusPlan finding

A canary run with `--model opusplan` succeeded, but the observed trajectory used `claude-sonnet-4-6` throughout and did not show a real `EnterPlanMode` / `ExitPlanMode` cycle. Therefore, `opusplan` is not currently included as a full scored Phase 2 arm.

A future benchmark may add a custom two-pass Harbor agent that explicitly runs a planning pass and then an execution pass. That future plan-execute benchmark should be reported separately because it changes the agent procedure rather than only changing the model/backend.
