# Cross-phase task-set audit

This report verifies whether Phase 1, Phase 2, and Phase 3 are comparable at the task-suite level.

The expected scored-arm shape is 20 tasks × 3 attempts = 60 trials per arm.

## Phase task counts

| Phase | Unique tasks |
|---|---:|
| phase1 | 20 |
| phase2 | 20 |
| phase3 | 20 |

## Arm shape audit

| Phase | Arm | Trials | Unique tasks | Attempt counts present | Status |
|---|---|---:|---:|---|---|
| phase1 | `arm-a-anthropic` | 60 | 20 | 3 | pass |
| phase1 | `arm-b-deepseek-pro` | 60 | 20 | 3 | pass |
| phase1 | `arm-c-deepseek-flash` | 60 | 20 | 3 | pass |
| phase2 | `arm-anthropic-haiku` | 60 | 20 | 3 | pass |
| phase2 | `arm-anthropic-opus` | 60 | 20 | 3 | pass |
| phase2 | `arm-anthropic-sonnet` | 60 | 20 | 3 | pass |
| phase2 | `arm-deepseek-flash` | 60 | 20 | 3 | pass |
| phase2 | `arm-deepseek-pro` | 60 | 20 | 3 | pass |
| phase3 | `router-anthropic-fable-5` | 60 | 20 | 3 | pass |
| phase3 | `router-anthropic-haiku-sanitized` | 60 | 20 | 3 | pass |
| phase3 | `router-anthropic-opus` | 60 | 20 | 3 | pass |
| phase3 | `router-anthropic-sonnet` | 60 | 20 | 3 | pass |
| phase3 | `router-deepseek-flash` | 60 | 20 | 3 | pass |
| phase3 | `router-deepseek-pro` | 60 | 20 | 3 | pass |
| phase3 | `router-gemini-3.1-pro` | 60 | 20 | 3 | pass |
| phase3 | `router-gemini-flash` | 60 | 20 | 3 | pass |
| phase3 | `router-glm-5.1` | 60 | 20 | 3 | pass |
| phase3 | `router-glm-5.2` | 60 | 20 | 3 | pass |
| phase3 | `router-gpt-5.4` | 60 | 20 | 3 | pass |
| phase3 | `router-gpt-5.5` | 60 | 20 | 3 | pass |
| phase3 | `router-grok-build-0.1` | 60 | 20 | 3 | pass |
| phase3 | `router-kimi-k2.6` | 60 | 20 | 3 | pass |
| phase3 | `router-qwen-3.7-plus` | 60 | 20 | 3 | pass |

## Issues

No task-set or attempt-count issues found.
