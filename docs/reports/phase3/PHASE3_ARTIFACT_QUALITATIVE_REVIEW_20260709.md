# Phase 3 Artifact Qualitative Review 20260709

## Purpose

Prepare a reproducible evidence inventory for the Phase 3 qualitative investigation pass. This scaffold is focused on Sonnet exceptions and suspect no-op zero-token trials first, while preserving dashboard links into the artifact browser and trial evidence pages.

Do not run Haiku or Fable from this scaffold. Those runs remain gated on drilldown readiness and ingestion automation.

## Source Files Generated

- `results/phase3/reporting/phase3_trial_evidence_audit_20260709.tsv`
- `results/phase3/reporting/phase3_exception_audit_20260709.tsv`
- `results/phase3/reporting/phase3_suspect_noop_audit_20260709.tsv`
- `results/phase3/reporting/phase3_arm_task_qualitative_matrix_20260709.tsv`
- `results/phase3/reporting/phase3_arm_qualitative_summary_20260709.tsv`
- `results/phase3/reporting/phase3_task_qualitative_summary_20260709.tsv`
- `results/phase3/reporting/phase3_exception_review_targets_20260709.tsv`
- `docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_20260709.md`

## Review Method

- Suite: `phase3-full-20`.
- Focus arms: all arms.
- Invalid/quarantined runs: excluded from generated trial rows.
- Generation command:

```bash
uv run --with 'psycopg[binary]' python scripts/generate_phase3_qualitative_audit.py --suite-id phase3-full-20
```

- Start with exception and suspect no-op rows, then compare against normal failures and representative successes only when needed.
- Use `/artifacts/<artifact_id>` for R2-backed content preview and `/trials/<trial_id>` for trial evidence context.
- Record whether each anomaly appears to be model behavior, provider behavior, harness behavior, or ingestion/reporting behavior.

## Initial Aggregate Observations

- Selected trial rows: 780.
- Evidence-audit rows emitted: 343.
- Successes in selected rows: 451.
- Exceptions in selected rows: 194.
- Suspect no-op rows in selected rows: 4.
- Normal failures in selected rows: 145.
- Missing-cost rows in selected rows: 176.
- Artifact references indexed: 6414 artifacts across 780 selected trials.

## Sonnet Exception Review

### `router-anthropic-sonnet/2026-06-27__01-30-11`

Planned first focus counts:

- Trials: 60.
- Successes: 28.
- Exception failures: 23.
- Normal failures: 9.
- Missing-cost trials: 22.

Generated row check for this run in the current inventory:

- Rows: 60.
- Successes: 28.
- Exceptions: 23.
- Normal failures: 9.
- Missing-cost rows: 22.

Use `phase3_exception_review_targets_20260709.tsv` for direct exception.txt artifact links.

Dashboard starting links:

- [Sonnet exception artifacts](/artifacts?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11&quality_flag=exception).
- [Sonnet run detail](/runs/router-anthropic-sonnet%2F2026-06-27__01-30-11).
- [Sonnet trial quality](/trial-quality?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11).

Review notes:

- Pending: classify representative exception artifacts by root cause.
- Pending: compare exception summaries against R2 preview contents.
- Pending: check whether missing-cost rows line up with exception boundaries or ingestion gaps.

## Suspect No-op Review

- Start from `phase3_suspect_noop_audit_20260709.tsv`.
- For each row, open `trial_dashboard_path`, then `first_artifact_dashboard_path` when present.
- Confirm whether zero tokens/cost reflects provider non-start, harness no-op, ingestion omission, or legitimate empty accounting.

## Gemini Flash Review

- Pending after the Sonnet exception pass.
- Use the exception and suspect no-op inventories to select representative Gemini Flash rows.
- Keep invalid/quarantined evidence labeled if `--include-invalid` is used for a follow-up pass.

## Invalid/Quarantined Run Review

- `router-anthropic-haiku-sanitized` / `router-anthropic-haiku-sanitized/2026-07-02__02-01-16`: Runtime service/API path failure; Claude Code reported ConnectionRefused via sanitizer/LiteLLM path; zero API tokens/cost across all trials
- `router-anthropic-opus` / `router-anthropic-opus/2026-06-28__13-28-56`: Anthropic workspace API usage limit until 2026-07-01 00:00 UTC
- `router-gemini-3.1-pro` / `router-gemini-3.1-pro/2026-06-30__01-23-54`: Gemini project monthly spending cap exceeded; 429 RESOURCE_EXHAUSTED provider-limit failures

## Cross-arm Exception Patterns

- `exception_info`: 194

## Task-level Observations

- `terminal-bench-2.0:polyglot-rust-c`: trials=39, successes=1, exceptions=22, suspect_noops=1, normal_failures=15, priority=high
- `terminal-bench-2.0:model-extraction-relu-logits`: trials=39, successes=1, exceptions=20, suspect_noops=2, normal_failures=16, priority=high
- `terminal-bench-2.0:query-optimize`: trials=39, successes=6, exceptions=31, suspect_noops=0, normal_failures=4, priority=high
- `terminal-bench-2.0:mteb-retrieve`: trials=39, successes=5, exceptions=1, suspect_noops=1, normal_failures=32, priority=medium
- `terminal-bench-2.0:torch-pipeline-parallelism`: trials=39, successes=7, exceptions=18, suspect_noops=0, normal_failures=15, priority=high
- `terminal-bench-2.0:schemelike-metacircular-eval`: trials=39, successes=15, exceptions=24, suspect_noops=0, normal_failures=2, priority=high
- `terminal-bench-2.0:cancel-async-tasks`: trials=39, successes=16, exceptions=5, suspect_noops=0, normal_failures=19, priority=high
- `terminal-bench-2.0:configure-git-webserver`: trials=39, successes=20, exceptions=7, suspect_noops=0, normal_failures=13, priority=high
- `terminal-bench-2.0:password-recovery`: trials=39, successes=21, exceptions=14, suspect_noops=0, normal_failures=4, priority=high
- `terminal-bench-2.0:build-cython-ext`: trials=39, successes=24, exceptions=8, suspect_noops=0, normal_failures=8, priority=high

## Automated First-Pass Exception Classification

Source files:

- `results/phase3/reporting/phase3_exception_classification_20260709.tsv`
- `results/phase3/reporting/phase3_exception_classification_summary_20260709.tsv`

This is deterministic, rule-based, evidence-assisted first-pass classification from exception artifacts and related same-trial artifacts when available. It now records matched signals and source artifacts for traceability. It is not final human judgment; the output should guide manual spot checks and root-cause review.

Summary by category:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| agent_timeout | 150 | 0 | high | AgentTimeoutError |
| nonzero_agent_exit | 36 | 0 | high | NonZeroAgentExitCodeError |
| model_loop_or_stall | 8 | 0 | medium | loop |

Summary by category and runtime band:

| Arm | Category | Runtime band | Count | Missing cost | Manual review | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| router-anthropic-opus | agent_timeout | long_exception_over_1200s | 5 | 5 | 0 | high | AgentTimeoutError |
| router-anthropic-opus | agent_timeout | mid_exception_90_to_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-anthropic-sonnet | agent_timeout | long_exception_over_1200s | 4 | 4 | 0 | high | AgentTimeoutError |
| router-anthropic-sonnet | agent_timeout | mid_exception_90_to_1200s | 4 | 4 | 0 | high | AgentTimeoutError |
| router-anthropic-sonnet | nonzero_agent_exit | fast_exception_under_90s | 12 | 12 | 0 | high | NonZeroAgentExitCodeError |
| router-anthropic-sonnet | nonzero_agent_exit | long_exception_over_1200s | 1 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-anthropic-sonnet | nonzero_agent_exit | mid_exception_90_to_1200s | 2 | 2 | 0 | high | NonZeroAgentExitCodeError |
| router-deepseek-flash | agent_timeout | long_exception_over_1200s | 3 | 3 | 0 | high | AgentTimeoutError |
| router-deepseek-flash | agent_timeout | mid_exception_90_to_1200s | 4 | 4 | 0 | high | AgentTimeoutError |
| router-deepseek-flash | model_loop_or_stall | long_exception_over_1200s | 1 | 0 | 0 | medium | loop |
| router-deepseek-pro | agent_timeout | long_exception_over_1200s | 1 | 1 | 0 | high | AgentTimeoutError |
| router-deepseek-pro | agent_timeout | mid_exception_90_to_1200s | 3 | 3 | 0 | high | AgentTimeoutError |
| router-deepseek-pro | model_loop_or_stall | long_exception_over_1200s | 3 | 0 | 0 | medium | loop |
| router-gemini-3.1-pro | agent_timeout | long_exception_over_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-gemini-3.1-pro | agent_timeout | mid_exception_90_to_1200s | 14 | 14 | 0 | high | AgentTimeoutError |
| router-gemini-flash | agent_timeout | long_exception_over_1200s | 10 | 10 | 0 | high | AgentTimeoutError |
| router-gemini-flash | agent_timeout | mid_exception_90_to_1200s | 28 | 28 | 0 | high | AgentTimeoutError |
| router-gemini-flash | nonzero_agent_exit | long_exception_over_1200s | 1 | 1 | 0 | high | NonZeroAgentExitCodeError |
| router-gemini-flash | nonzero_agent_exit | mid_exception_90_to_1200s | 2 | 1 | 0 | high | NonZeroAgentExitCodeError |
| router-glm-5.1 | agent_timeout | long_exception_over_1200s | 4 | 4 | 0 | high | AgentTimeoutError |
| router-glm-5.1 | agent_timeout | mid_exception_90_to_1200s | 6 | 6 | 0 | high | AgentTimeoutError |
| router-glm-5.1 | nonzero_agent_exit | mid_exception_90_to_1200s | 6 | 5 | 0 | high | NonZeroAgentExitCodeError |
| router-glm-5.2 | agent_timeout | long_exception_over_1200s | 8 | 8 | 0 | high | AgentTimeoutError |
| router-glm-5.2 | agent_timeout | mid_exception_90_to_1200s | 9 | 9 | 0 | high | AgentTimeoutError |
| router-glm-5.2 | model_loop_or_stall | long_exception_over_1200s | 2 | 0 | 0 | medium | loop |
| router-gpt-5.4 | agent_timeout | long_exception_over_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-gpt-5.4 | agent_timeout | mid_exception_90_to_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-gpt-5.4 | model_loop_or_stall | long_exception_over_1200s | 2 | 0 | 0 | medium | loop |
| router-gpt-5.4 | nonzero_agent_exit | mid_exception_90_to_1200s | 1 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-gpt-5.5 | agent_timeout | long_exception_over_1200s | 4 | 4 | 0 | high | AgentTimeoutError |
| router-grok-build-0.1 | agent_timeout | long_exception_over_1200s | 5 | 5 | 0 | high | AgentTimeoutError |
| router-grok-build-0.1 | agent_timeout | mid_exception_90_to_1200s | 5 | 5 | 0 | high | AgentTimeoutError |
| router-grok-build-0.1 | nonzero_agent_exit | long_exception_over_1200s | 1 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-grok-build-0.1 | nonzero_agent_exit | mid_exception_90_to_1200s | 2 | 1 | 0 | high | NonZeroAgentExitCodeError |
| router-kimi-k2.6 | agent_timeout | long_exception_over_1200s | 6 | 6 | 0 | high | AgentTimeoutError |
| router-kimi-k2.6 | agent_timeout | mid_exception_90_to_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-kimi-k2.6 | nonzero_agent_exit | mid_exception_90_to_1200s | 6 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-qwen-3.7-plus | agent_timeout | long_exception_over_1200s | 9 | 9 | 0 | high | AgentTimeoutError |
| router-qwen-3.7-plus | agent_timeout | mid_exception_90_to_1200s | 8 | 8 | 0 | high | AgentTimeoutError |
| router-qwen-3.7-plus | nonzero_agent_exit | mid_exception_90_to_1200s | 2 | 0 | 0 | high | NonZeroAgentExitCodeError |

High-confidence direct categories observed: `agent_timeout`, `nonzero_agent_exit` (186 rows).

Categories marked `needs_manual_review`: none (0 rows).

Sonnet-specific observations:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| nonzero_agent_exit | 15 | 0 | high | NonZeroAgentExitCodeError |
| agent_timeout | 8 | 0 | high | AgentTimeoutError |

## Automated First-Pass Normal Failure Classification

Source files:

- `results/phase3/reporting/phase3_normal_failure_classification_20260709.tsv`
- `results/phase3/reporting/phase3_normal_failure_classification_summary_20260709.tsv`

This is deterministic, rule-based, evidence-assisted first-pass classification from verifier stdout, CTRF, reward, result, log, transcript, and trajectory artifacts when available. It is not final human judgment and does not change scoring semantics.

Summary by category:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 95 | 0 | high | =================================== FAILURES ========================... |
| runtime_exception_in_solution | 22 | 0 | high | ValueError, AttributeError, Traceback (most recent call last) |
| wrong_file_or_path | 20 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F..., path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P..., No such file or directory |
| dependency_or_import_error | 8 | 0 | high | ModuleNotFoundError, ImportError |

Summary by arm and category:

| Arm | Category | Count | Manual review | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- | --- |
| router-anthropic-opus | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-anthropic-opus | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |
| router-anthropic-opus | wrong_file_or_path | 5 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F...,path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-anthropic-sonnet | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-flash | dependency_or_import_error | 1 | 0 | high | ImportError |
| router-deepseek-flash | runtime_exception_in_solution | 4 | 0 | high | ValueError |
| router-deepseek-flash | test_assertion_failure | 5 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-flash | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-deepseek-pro | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-deepseek-pro | runtime_exception_in_solution | 5 | 0 | high | AttributeError,ValueError |
| router-deepseek-pro | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-pro | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F...,path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-gemini-3.1-pro | runtime_exception_in_solution | 2 | 0 | high | ValueError |
| router-gemini-3.1-pro | test_assertion_failure | 4 | 0 | high | =================================== FAILURES ========================... |
| router-gemini-3.1-pro | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-gemini-flash | runtime_exception_in_solution | 1 | 0 | high | ValueError |
| router-gemini-flash | test_assertion_failure | 5 | 0 | high | =================================== FAILURES ========================... |
| router-gemini-flash | wrong_file_or_path | 2 | 0 | high | No such file or directory,FileNotFoundError |
| router-glm-5.1 | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-glm-5.1 | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |
| router-glm-5.2 | test_assertion_failure | 6 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.4 | runtime_exception_in_solution | 3 | 0 | high | ValueError |
| router-gpt-5.4 | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.4 | wrong_file_or_path | 3 | 0 | high | No such file or directory |
| router-gpt-5.5 | runtime_exception_in_solution | 2 | 0 | high | AttributeError,ValueError |
| router-gpt-5.5 | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.5 | wrong_file_or_path | 1 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-grok-build-0.1 | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-grok-build-0.1 | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-grok-build-0.1 | wrong_file_or_path | 1 | 0 | high | path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-kimi-k2.6 | dependency_or_import_error | 3 | 0 | high | ModuleNotFoundError |
| router-kimi-k2.6 | runtime_exception_in_solution | 4 | 0 | high | AttributeError,Traceback (most recent call last),ValueError |
| router-kimi-k2.6 | test_assertion_failure | 7 | 0 | high | =================================== FAILURES ========================... |
| router-kimi-k2.6 | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-qwen-3.7-plus | runtime_exception_in_solution | 1 | 0 | high | AttributeError |
| router-qwen-3.7-plus | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |

Rows marked `needs_manual_review`: 0 of 145.

Comparison against exception classifications:

Exception classifications for the same date cover 194 exception rows across `agent_timeout`, `model_loop_or_stall`, `nonzero_agent_exit`. Normal-failure classification covers verifier failures that did not raise a harness exception and should be reviewed as solution/verifier evidence, not scoring changes.

Sonnet normal failures:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |

Gemini Flash normal failures:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 5 | 0 | high | =================================== FAILURES ========================... |
| wrong_file_or_path | 2 | 0 | high | No such file or directory, FileNotFoundError |
| runtime_exception_in_solution | 1 | 0 | high | ValueError |

## Qualitative Findings and Interpretation

Executive readout:

- Phase 3 failures are not homogeneous. The artifact evidence separates harness-level exceptions, ordinary verifier failures, wrong-output/path failures, runtime exceptions in attempted solutions, and rare suspect no-op rows.
- Exceptions are dominated by agent timeouts overall: `agent_timeout` accounts for 150 of 194 classified exceptions.
- Sonnet is an exception-shape outlier because most Sonnet exceptions are `NonZeroAgentExitCodeError`: 15 `nonzero_agent_exit` rows versus 8 `agent_timeout` rows.
- Normal verifier failures are mostly ordinary test assertion failures: `test_assertion_failure` accounts for 95 of 145 classified normal failures.
- Wrong-file/path and runtime-exception categories expose task-specific failure patterns, especially `model-extraction-relu-logits` and `torch-pipeline-parallelism`-style tasks.
- Suspect no-op rows remain rare, with 4 rows across 780 selected trials, and should be treated separately from exceptions.

These classifications are deterministic first-pass labels based on artifact evidence. They are intended to structure follow-up review, not to change pass/fail scoring. Manual spot checks are still useful before drawing final sponsor-facing conclusions, especially for categories that imply provider, harness, or task-specific failure modes.

Exact classification totals:

- Exception classifications: `agent_timeout` 150; `nonzero_agent_exit` 36; `model_loop_or_stall` 8.
- Normal failure classifications: `test_assertion_failure` 95; `runtime_exception_in_solution` 22; `wrong_file_or_path` 20; `dependency_or_import_error` 8.
- Sonnet: 23 exceptions (`nonzero_agent_exit` 15, `agent_timeout` 8) and 9 normal failures (`test_assertion_failure` 9).
- Gemini Flash: 41 exceptions (`agent_timeout` 38, `nonzero_agent_exit` 3) and 8 normal failures (`test_assertion_failure` 5, `wrong_file_or_path` 2, `runtime_exception_in_solution` 1).
- GPT-5.5: 4 exceptions (`agent_timeout` 4) and 12 normal failures (`test_assertion_failure` 9, `runtime_exception_in_solution` 2, `wrong_file_or_path` 1).

| arm_id | exceptions | dominant_exception_category | normal_failures | dominant_normal_failure_category | interpretation |
| --- | ---: | --- | ---: | --- | --- |
| router-anthropic-opus | 7 | `agent_timeout` (7/7) | 14 | `test_assertion_failure` (8/14) | Timeout-only exception profile; normal failures mix ordinary assertions with wrong-file/path evidence. |
| router-anthropic-sonnet | 23 | `nonzero_agent_exit` (15/23) | 9 | `test_assertion_failure` (9/9) | Exception-shape outlier; most failures that reach verification are conventional assertion failures. |
| router-deepseek-flash | 8 | `agent_timeout` (7/8) | 12 | `test_assertion_failure` (5/12) | Mostly timeout exceptions; normal failures are mixed across assertion, runtime, path, and import categories. |
| router-deepseek-pro | 7 | `agent_timeout` (4/7) | 16 | `test_assertion_failure` (8/16) | Lower exception volume but split between timeout and loop/stall; normal failures include runtime and path issues. |
| router-gemini-3.1-pro | 16 | `agent_timeout` (16/16) | 8 | `test_assertion_failure` (4/8) | Timeout-only exception profile; verifier failures split across assertion, runtime, and path evidence. |
| router-gemini-flash | 41 | `agent_timeout` (38/41) | 8 | `test_assertion_failure` (5/8) | Highest exception burden in this set, dominated by timeouts, with rare suspect no-op rows handled separately. |
| router-glm-5.1 | 16 | `agent_timeout` (10/16) | 9 | `test_assertion_failure` (8/9) | Exception profile mixes timeouts and nonzero exits; normal failures are almost entirely assertions. |
| router-glm-5.2 | 19 | `agent_timeout` (17/19) | 6 | `test_assertion_failure` (6/6) | Timeout-heavy exception profile; normal failures are conventional assertion failures. |
| router-gpt-5.4 | 7 | `agent_timeout` (4/7) | 15 | `test_assertion_failure` (9/15) | Lower exception count but heterogeneous exception categories; normal failures include runtime and path evidence. |
| router-gpt-5.5 | 4 | `agent_timeout` (4/4) | 12 | `test_assertion_failure` (9/12) | Low exception count, all timeout-labeled; normal failures are mostly assertions with some runtime/path cases. |
| router-grok-build-0.1 | 13 | `agent_timeout` (10/13) | 11 | `test_assertion_failure` (9/11) | Timeout-dominant exceptions with a small nonzero-exit tail; normal failures are mostly assertions. |
| router-kimi-k2.6 | 14 | `agent_timeout` (8/14) | 16 | `test_assertion_failure` (7/16) | Mixed exception profile and the broadest normal-failure mix, including import, runtime, and path issues. |
| router-qwen-3.7-plus | 19 | `agent_timeout` (17/19) | 9 | `test_assertion_failure` (8/9) | Timeout-heavy exceptions; normal verifier failures are mostly assertions. |

Task-level observations:

- `model-extraction-relu-logits`: 39 trials produced 1 success, 20 exceptions, 16 normal failures, and 2 suspect no-op rows. The normal-failure split is sharply task-specific: 15 `wrong_file_or_path` rows and 1 `dependency_or_import_error` row. Exceptions were also common, with 17 `agent_timeout` rows and 3 `nonzero_agent_exit` rows.
- `schemelike-metacircular-eval`: 39 trials produced 15 successes, 24 exceptions, and 2 normal failures. The exception mix was timeout-heavy: 19 `agent_timeout` rows and 5 `nonzero_agent_exit` rows.
- `mteb-retrieve`: 39 trials produced 5 successes, 1 exception, 1 suspect no-op row, and 32 normal failures. All 32 classified normal failures were `test_assertion_failure`, making this primarily an assertion-failure-heavy task rather than an exception-heavy one.
- `torch-pipeline-parallelism`: 39 trials produced 7 successes, 18 exceptions, and 15 normal failures. The normal-failure evidence is concentrated in solution runtime errors: all 15 classified normal failures were `runtime_exception_in_solution`; exceptions were mostly `agent_timeout` (17) with 1 `nonzero_agent_exit`.
- `query-optimize`: 39 trials produced 6 successes, 31 exceptions, and 4 normal failures. The exception evidence shows the clearest loop/stall and timeout pattern: 22 `agent_timeout`, 8 `model_loop_or_stall`, and 1 `nonzero_agent_exit`; the 4 normal failures were `test_assertion_failure`.

## Open Questions and Recommended Actions

- Confirm whether task text is available for each reviewed trial; if not, keep task text ingestion on the qualitative-review readiness checklist.
- Decide whether any invalid/quarantined labels or reasons need refinement before final Phase 3 reporting.
- Capture representative artifact links for each root-cause category before resuming paid full runs.
- Do not run Haiku or Fable until drilldown review and ingestion automation are ready.
