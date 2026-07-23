# Phase 3 Manual Verification Notes — 2026-07-22

## Purpose

This file records human review of selected Phase 3 and Phase-3-compatible addendum trials.

Manual verification is intended to answer whether automated benchmark outcomes are believable after inspecting the underlying artifacts, including result metadata, agent trajectory, verifier output, exception files, and trial logs.

## Review labels

Use one of the following labels:

- valid_success
- valid_failure
- valid_exception_failure
- questionable_success
- questionable_failure
- near_miss
- timeout_after_meaningful_progress
- no_op_or_suspicious
- needs_second_review

## Initial suspect / high-priority review targets

These were identified from the Phase 3 evidence audit as suspect no-op or high-priority manual-review targets.

| Priority | Arm | Task | Attempt | Trial ID | Artifact Path | Automated Classification | Status |
|---:|---|---|---:|---|---|---|---|
| 1 | router-gemini-flash | mteb-retrieve | 30 | 7eceb1c8-4a7b-4899-9650-b54f7d432d24 | /artifacts/7e374687-f760-4275-ad1e-08d8d492bd03 | suspect_noop_zero_token | pending |
| 2 | router-gemini-flash | polyglot-rust-c | 45 | b59e45f0-050e-448e-8a97-abee2f4b89c6 | /artifacts/07dc3d1b-a075-447c-83c0-c3662e3121a8 | suspect_noop_zero_token | pending |
| 3 | router-gpt-5.5 | model-extraction-relu-logits | 22 | 9ce7bde7-ce6e-4f32-93af-04848273f93c | /artifacts/748e6917-aa09-483a-a42a-aca97da10f8a | suspect_noop_zero_token | pending |
| 4 | router-gpt-5.5 | model-extraction-relu-logits | 23 | 6ebd9061-3c69-443d-8a76-be789b50344d | /artifacts/e1a329b4-5a86-4b3c-a666-6cdf3b50d76a | suspect_noop_zero_token | pending |

## Additional exception-heavy comparison targets

These are useful for comparison against the suspect no-op cases.

| Priority | Arm | Task | Attempt | Trial ID | Artifact Path | Automated Classification | Status |
|---:|---|---|---:|---|---|---|---|
| 5 | router-anthropic-sonnet | model-extraction-relu-logits | 22 | 10998537-5bc0-4749-9299-48d16ef26f88 | /artifacts/036daad0-6b91-4880-a7b4-c36bc9fc37c9 | exception | pending |
| 6 | router-anthropic-sonnet | model-extraction-relu-logits | 23 | 4f35a1b9-b99b-43a2-a02a-7acfb4b8698e | /artifacts/438f618f-7560-4ad6-abe3-cef5ec49ac03 | exception | pending |
| 7 | router-anthropic-sonnet | polyglot-rust-c | 45 | 1f3d875e-1130-4a7c-89e3-673433602229 | /artifacts/32e6890c-d058-4758-95f8-18f5b0522002 | exception | pending |

## Kimi K3 addendum review targets

Kimi K3 produced a strong raw full-sweep result, but also had 11 exceptions. Review a sample of exception-with-success-signal and timeout-heavy trials.

| Priority | Arm | Task | Trial | Automated Result | Reason | Status |
|---:|---|---|---|---|---|---|
| 8 | router-kimi-k3 | cancel-async-tasks | cancel-async-tasks__PoLPSBR | reward=1, AgentTimeoutError | exception with success signal | pending |
| 9 | router-kimi-k3 | cancel-async-tasks | cancel-async-tasks__oYSfUTH | reward=1, AgentTimeoutError | exception with success signal | pending |
| 10 | router-kimi-k3 | torch-pipeline-parallelism | torch-pipeline-parallelism__Hb4cpXY | reward=1, AgentTimeoutError | exception with success signal | pending |
| 11 | router-kimi-k3 | schemelike-metacircular-eval | all 3 trials | reward=0, AgentTimeoutError | timeout-heavy task | pending |
| 12 | router-kimi-k3 | polyglot-rust-c | all 3 trials | 0/3 success | hard task / compare against other arms | pending |

## Review template

Copy this block for each reviewed trial.

~~~text
phase:
arm:
task:
attempt:
trial:
trial_id:
artifact_path:
automated_result:
exception_status:
cost_status:
manual_label:
confidence:
reviewer:
artifact_evidence:
  result_json:
  trial_log:
  trajectory_json:
  claude_code_transcript:
  verifier_reward:
  verifier_stdout:
  exception_txt:
notes:
~~~

## Reviews

### Review 1 — pending

~~~text
phase:
arm:
task:
attempt:
trial:
trial_id:
artifact_path:
automated_result:
exception_status:
cost_status:
manual_label:
confidence:
reviewer:
artifact_evidence:
  result_json:
  trial_log:
  trajectory_json:
  claude_code_transcript:
  verifier_reward:
  verifier_stdout:
  exception_txt:
notes:
~~~
