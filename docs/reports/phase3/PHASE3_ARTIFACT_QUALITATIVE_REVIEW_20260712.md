# Phase 3 Artifact Qualitative Review 20260712

## Purpose

Prepare a reproducible evidence inventory for the Phase 3 qualitative investigation pass. This scaffold is focused on Sonnet exceptions and suspect no-op zero-token trials first, while preserving dashboard links into the artifact browser and trial evidence pages.

Do not run Haiku or Fable from this scaffold. Those runs remain gated on drilldown readiness and ingestion automation.

## Source Files Generated

- `results/phase3/reporting/phase3_trial_evidence_audit_20260712.tsv`
- `results/phase3/reporting/phase3_exception_audit_20260712.tsv`
- `results/phase3/reporting/phase3_suspect_noop_audit_20260712.tsv`
- `results/phase3/reporting/phase3_arm_task_qualitative_matrix_20260712.tsv`
- `results/phase3/reporting/phase3_arm_qualitative_summary_20260712.tsv`
- `results/phase3/reporting/phase3_task_qualitative_summary_20260712.tsv`
- `results/phase3/reporting/phase3_exception_review_targets_20260712.tsv`
- `docs/reports/phase3/PHASE3_ARTIFACT_QUALITATIVE_REVIEW_20260712.md`

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

- Selected trial rows: 900.
- Evidence-audit rows emitted: 401.
- Successes in selected rows: 515.
- Exceptions in selected rows: 206.
- Suspect no-op rows in selected rows: 4.
- Normal failures in selected rows: 191.
- Missing-cost rows in selected rows: 179.
- Artifact references indexed: 7386 artifacts across 900 selected trials.

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

Use `phase3_exception_review_targets_20260712.tsv` for direct exception.txt artifact links.

Dashboard starting links:

- [Sonnet exception artifacts](/artifacts?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11&quality_flag=exception).
- [Sonnet run detail](/runs/router-anthropic-sonnet%2F2026-06-27__01-30-11).
- [Sonnet trial quality](/trial-quality?run_label=router-anthropic-sonnet%2F2026-06-27__01-30-11).

Review notes:

- Pending: classify representative exception artifacts by root cause.
- Pending: compare exception summaries against R2 preview contents.
- Pending: check whether missing-cost rows line up with exception boundaries or ingestion gaps.

## Suspect No-op Review

- Start from `phase3_suspect_noop_audit_20260712.tsv`.
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

- `exception_info`: 206

## Task-level Observations

- `terminal-bench-2.0:model-extraction-relu-logits`: trials=45, successes=1, exceptions=23, suspect_noops=2, normal_failures=19, priority=high
- `terminal-bench-2.0:polyglot-rust-c`: trials=45, successes=1, exceptions=22, suspect_noops=1, normal_failures=21, priority=high
- `terminal-bench-2.0:query-optimize`: trials=45, successes=6, exceptions=31, suspect_noops=0, normal_failures=10, priority=high
- `terminal-bench-2.0:mteb-retrieve`: trials=45, successes=6, exceptions=1, suspect_noops=1, normal_failures=37, priority=medium
- `terminal-bench-2.0:torch-pipeline-parallelism`: trials=45, successes=10, exceptions=18, suspect_noops=0, normal_failures=18, priority=high
- `terminal-bench-2.0:schemelike-metacircular-eval`: trials=45, successes=18, exceptions=27, suspect_noops=0, normal_failures=4, priority=high
- `terminal-bench-2.0:configure-git-webserver`: trials=45, successes=20, exceptions=7, suspect_noops=0, normal_failures=19, priority=high
- `terminal-bench-2.0:cancel-async-tasks`: trials=45, successes=21, exceptions=5, suspect_noops=0, normal_failures=20, priority=high
- `terminal-bench-2.0:password-recovery`: trials=45, successes=21, exceptions=17, suspect_noops=0, normal_failures=7, priority=high
- `terminal-bench-2.0:build-cython-ext`: trials=45, successes=27, exceptions=8, suspect_noops=0, normal_failures=11, priority=high

## Automated First-Pass Exception Classification

Source files:

- `results/phase3/reporting/phase3_exception_classification_20260712.tsv`
- `results/phase3/reporting/phase3_exception_classification_summary_20260712.tsv`

This is deterministic, rule-based, evidence-assisted first-pass classification from exception artifacts and related same-trial artifacts when available. It now records matched signals and source artifacts for traceability. It is not final human judgment; the output should guide manual spot checks and root-cause review.

Summary by category:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| agent_timeout | 153 | 0 | high | AgentTimeoutError |
| nonzero_agent_exit | 45 | 0 | high | NonZeroAgentExitCodeError |
| model_loop_or_stall | 4 | 0 | medium | loop |
| verifier_or_test_failure_exception | 4 | 0 | medium | AssertionError |

Summary by category and runtime band:

| Arm | Category | Runtime band | Count | Missing cost | Manual review | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| router-anthropic-fable-5 | agent_timeout | long_exception_over_1200s | 3 | 3 | 0 | high | AgentTimeoutError |
| router-anthropic-fable-5 | nonzero_agent_exit | fast_exception_under_90s | 6 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-anthropic-fable-5 | nonzero_agent_exit | mid_exception_90_to_1200s | 3 | 0 | 0 | high | NonZeroAgentExitCodeError |
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
| router-deepseek-pro | model_loop_or_stall | long_exception_over_1200s | 2 | 0 | 0 | medium | loop |
| router-deepseek-pro | verifier_or_test_failure_exception | long_exception_over_1200s | 1 | 0 | 0 | medium | AssertionError |
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
| router-glm-5.2 | model_loop_or_stall | long_exception_over_1200s | 1 | 0 | 0 | medium | loop |
| router-glm-5.2 | verifier_or_test_failure_exception | long_exception_over_1200s | 1 | 0 | 0 | medium | AssertionError |
| router-gpt-5.4 | agent_timeout | long_exception_over_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-gpt-5.4 | agent_timeout | mid_exception_90_to_1200s | 2 | 2 | 0 | high | AgentTimeoutError |
| router-gpt-5.4 | nonzero_agent_exit | mid_exception_90_to_1200s | 1 | 0 | 0 | high | NonZeroAgentExitCodeError |
| router-gpt-5.4 | verifier_or_test_failure_exception | long_exception_over_1200s | 2 | 0 | 0 | medium | AssertionError |
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

High-confidence direct categories observed: `agent_timeout`, `nonzero_agent_exit` (198 rows).

Categories marked `needs_manual_review`: none (0 rows).

Sonnet-specific observations:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| nonzero_agent_exit | 15 | 0 | high | NonZeroAgentExitCodeError |
| agent_timeout | 8 | 0 | high | AgentTimeoutError |

## Automated First-Pass Normal Failure Classification

Source files:

- `results/phase3/reporting/phase3_normal_failure_classification_20260712.tsv`
- `results/phase3/reporting/phase3_normal_failure_classification_summary_20260712.tsv`

This is deterministic, rule-based, evidence-assisted first-pass classification from verifier stdout, CTRF, reward, result, log, transcript, and trajectory artifacts when available. It is not final human judgment and does not change scoring semantics.

Summary by category:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 125 | 4 | medium | =================================== FAILURES ========================... |
| runtime_exception_in_solution | 27 | 0 | high | AttributeError, Traceback (most recent call last), ValueError |
| wrong_file_or_path | 24 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F..., FileNotFoundError, path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| dependency_or_import_error | 14 | 0 | high | ModuleNotFoundError, ImportError |
| syntax_or_compile_error | 1 | 0 | high | Failed to compile |

Summary by arm and category:

| Arm | Category | Count | Manual review | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- | --- |
| router-anthropic-fable-5 | test_assertion_failure | 11 | 0 | high | =================================== FAILURES ========================... |
| router-anthropic-haiku-sanitized | dependency_or_import_error | 2 | 0 | high | ModuleNotFoundError |
| router-anthropic-haiku-sanitized | runtime_exception_in_solution | 5 | 0 | high | AttributeError,Traceback (most recent call last),ValueError |
| router-anthropic-haiku-sanitized | syntax_or_compile_error | 1 | 0 | high | Failed to compile |
| router-anthropic-haiku-sanitized | test_assertion_failure | 23 | 2 | medium | =================================== FAILURES ========================... |
| router-anthropic-haiku-sanitized | wrong_file_or_path | 4 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F...,FileNotFoundError |
| router-anthropic-opus | dependency_or_import_error | 2 | 0 | high | ModuleNotFoundError,ImportError |
| router-anthropic-opus | test_assertion_failure | 7 | 0 | high | =================================== FAILURES ========================... |
| router-anthropic-opus | wrong_file_or_path | 5 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F...,path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-anthropic-sonnet | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-flash | dependency_or_import_error | 1 | 0 | high | ImportError |
| router-deepseek-flash | runtime_exception_in_solution | 4 | 0 | high | ValueError |
| router-deepseek-flash | test_assertion_failure | 5 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-flash | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-deepseek-pro | dependency_or_import_error | 2 | 0 | high | ModuleNotFoundError,ImportError |
| router-deepseek-pro | runtime_exception_in_solution | 5 | 0 | high | AttributeError,ValueError |
| router-deepseek-pro | test_assertion_failure | 7 | 0 | high | =================================== FAILURES ========================... |
| router-deepseek-pro | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F...,path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-gemini-3.1-pro | runtime_exception_in_solution | 2 | 0 | high | ValueError |
| router-gemini-3.1-pro | test_assertion_failure | 4 | 0 | high | =================================== FAILURES ========================... |
| router-gemini-3.1-pro | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-gemini-flash | runtime_exception_in_solution | 1 | 0 | high | ValueError |
| router-gemini-flash | test_assertion_failure | 5 | 2 | medium | =================================== FAILURES ========================... |
| router-gemini-flash | wrong_file_or_path | 2 | 0 | high | No such file or directory,FileNotFoundError |
| router-glm-5.1 | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-glm-5.1 | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |
| router-glm-5.2 | test_assertion_failure | 6 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.4 | dependency_or_import_error | 1 | 0 | high | ImportError |
| router-gpt-5.4 | runtime_exception_in_solution | 3 | 0 | high | ValueError |
| router-gpt-5.4 | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.4 | wrong_file_or_path | 3 | 0 | high | No such file or directory |
| router-gpt-5.5 | runtime_exception_in_solution | 2 | 0 | high | AttributeError,ValueError |
| router-gpt-5.5 | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-gpt-5.5 | wrong_file_or_path | 1 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-grok-build-0.1 | dependency_or_import_error | 1 | 0 | high | ModuleNotFoundError |
| router-grok-build-0.1 | test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |
| router-grok-build-0.1 | wrong_file_or_path | 1 | 0 | high | path = \"/app/check_cert.py\" assert os.path.exists(script_path), \"P... |
| router-kimi-k2.6 | dependency_or_import_error | 4 | 0 | high | ModuleNotFoundError,ImportError |
| router-kimi-k2.6 | runtime_exception_in_solution | 4 | 0 | high | AttributeError,Traceback (most recent call last),ValueError |
| router-kimi-k2.6 | test_assertion_failure | 6 | 0 | high | =================================== FAILURES ========================... |
| router-kimi-k2.6 | wrong_file_or_path | 2 | 0 | high | path = Path(\"/app/stolen_A1.npy\") assert stolen_path.exists(), f\"F... |
| router-qwen-3.7-plus | runtime_exception_in_solution | 1 | 0 | high | AttributeError |
| router-qwen-3.7-plus | test_assertion_failure | 8 | 0 | high | =================================== FAILURES ========================... |

Rows marked `needs_manual_review`: 4 of 191.

Comparison against exception classifications:

Exception classifications for the same date cover 206 exception rows across `agent_timeout`, `model_loop_or_stall`, `nonzero_agent_exit`, `verifier_or_test_failure_exception`. Normal-failure classification covers verifier failures that did not raise a harness exception and should be reviewed as solution/verifier evidence, not scoring changes.

Sonnet normal failures:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 9 | 0 | high | =================================== FAILURES ========================... |

Gemini Flash normal failures:

| Primary category | Count | Manual-review flagged | Confidence floor | Matched signals |
| --- | --- | --- | --- | --- |
| test_assertion_failure | 5 | 2 | medium | =================================== FAILURES ========================... |
| wrong_file_or_path | 2 | 0 | high | No such file or directory, FileNotFoundError |
| runtime_exception_in_solution | 1 | 0 | high | ValueError |

## Open Questions and Recommended Actions

- Confirm whether task text is available for each reviewed trial; if not, keep task text ingestion on the qualitative-review readiness checklist.
- Decide whether any invalid/quarantined labels or reasons need refinement before final Phase 3 reporting.
- Capture representative artifact links for each root-cause category before resuming paid full runs.
- Do not run Haiku or Fable until drilldown review and ingestion automation are ready.
