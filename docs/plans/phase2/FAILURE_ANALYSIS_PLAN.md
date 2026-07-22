# Failure Analysis Plan

Phase 2 should explain not just which arm won, but why.

For each trial, extract:

- success
- failure_mode
- exception_type
- wall_clock_seconds
- agent_execution_seconds
- input/cache/output tokens
- cost
- agent_turns
- tool_calls
- Bash/Edit/Read/Write/Glob/Grep counts
- repeated Bash commands
- files edited
- tests run
- verifier failure text
- last meaningful action before failure

Additional failure labels to investigate:

- produced-wrong-output
- timed-out
- looped
- refused-to-try
- ran-out-of-budget
- setup-or-routing-error
- dependency-assumption-error
- exact-output-format-error
- partial-fix-visible-tests-only
- overbroad-refactor
- underexploration
- tool-format/API-compatibility issue
