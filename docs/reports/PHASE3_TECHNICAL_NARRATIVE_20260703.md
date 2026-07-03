# Phase 3 Technical Narrative and Artifact Review

## What changed in Phase 3

Phase 3 moved from a smaller Claude Code backend comparison to a broader routed-model benchmark. The harness remained Claude Code, Terminal-Bench 2.0 remained the task source, and each valid full arm used 20 tasks × 3 attempts = 60 trials. Model routing was handled through LiteLLM and provider-specific arm configs.

The current clean result set uses valid-only aggregation. Invalid full runs are excluded by run label and provider run id, rather than by arm, so reruns remain eligible and the final table does not accidentally discard corrected results.

## Important technical challenges and resolutions

### Provider caps and invalid runs

Two early full runs were contaminated by provider limits rather than model behavior: an Anthropic Opus run hit a workspace usage limit, and a Gemini 3.1 Pro run hit a monthly spending cap with 429 `RESOURCE_EXHAUSTED` failures. Both were excluded, then successfully rerun. The invalid-run exclusion logic was hardened so exclusions are run-specific and do not remove later valid reruns for the same arm.

### Haiku and Claude Code parameter compatibility

Haiku required a sanitizer sidecar because Claude Code emitted fields that the target Anthropic-compatible Haiku path did not accept. A local sanitizer proxy was added to strip unsupported fields such as `effort`, `thinking`, `reasoning_effort`, and `output_config` before forwarding requests to LiteLLM.

A canary initially failed because the sanitizer upstream assumed LiteLLM was on port 4000. On multi-runner infrastructure, LiteLLM may start on another port, such as 4001. The sanitizer startup script was fixed to derive its upstream from `LITELLM_PORT`. The next Haiku canary successfully started LiteLLM, started the sanitizer, and ran the arm.

### Haiku full-run quarantine

The long Haiku full run later produced 60/60 errors and zero recorded cost. Artifact inspection showed `API Error: Unable to connect to API (ConnectionRefused)`, zero API duration, zero tokens, and zero cost. The run was therefore quarantined as infrastructure/runtime contamination rather than counted as model performance.

This motivates the next infrastructure hardening item: add a watchdog that continuously checks LiteLLM and sanitizer health during long benchmark runs and fails fast when the API path becomes unreachable.

## Artifact review approach

The benchmark artifacts are useful beyond pass/fail. Each trial contains result metadata, verifier output, Claude Code logs, trajectory files, and exception traces. The most important artifact-derived fields for reporting are:

- success count and pass rate,
- qualified pass rate after suspect no-op exclusions,
- exception count versus normal verifier failures,
- missing-cost count,
- total recorded cost,
- run labels and provider run ids for exclusion provenance,
- sidecar logs for routed arms.

The current qualitative read is that the leading arms differ not only in pass rate but in failure mode. Some models fail by normal verifier mismatch, while others fail through harness exceptions, API retries, or cost/accounting gaps. Future trajectory analysis should compare how high-performing and low-performing arms use tools, recover from errors, and terminate.
